#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shared Tree-Sitter based comment extraction helpers.

SPDX-License-Identifier: LGPL-2.1
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable, Sequence

from nirjas.output import MultiLine, ScanOutput, SingleLine

try:
    from tree_sitter_language_pack import get_parser
except ImportError as exc:  # pragma: no cover - handled at runtime
    get_parser = None
    _IMPORT_ERROR = exc
else:  # pragma: no cover - simple assignment
    _IMPORT_ERROR = None


_LANGUAGE_NAME_ALIASES = {
    "c_sharp": "csharp",
    "c#": "csharp",
    "shell": "bash",
    "shellscript": "bash",
    "sh": "bash",
}

_PARSER_CACHE: dict[str, object] = {}


@dataclass(frozen=True)
class CommentRecord:
    """Internal representation of a parsed comment."""

    start_line: int
    end_line: int
    comment: str
    category: str  # single | multi


def normalize_language_name(language_name: str) -> str:
    """Normalize aliases used in Nirjas to Tree-Sitter language names."""

    return _LANGUAGE_NAME_ALIASES.get(language_name, language_name)


def _get_cached_parser(language_name: str):
    """Get parser instance from cache or create it once."""

    if get_parser is None:
        raise RuntimeError(
            "tree-sitter-language-pack is required for comment extraction. "
            "Install dependencies with: pip install ."
        ) from _IMPORT_ERROR

    normalized_name = normalize_language_name(language_name)
    parser = _PARSER_CACHE.get(normalized_name)
    if parser is None:
        parser = get_parser(normalized_name)
        _PARSER_CACHE[normalized_name] = parser
    return parser


def _iter_nodes_dfs(root_node) -> Iterable:
    """Depth-first traversal of a Tree-Sitter syntax tree."""

    stack = [root_node]
    while stack:
        current = stack.pop()
        yield current
        for index in range(current.child_count() - 1, -1, -1):
            stack.append(current.child(index))


def _extract_node_text(node, source_bytes: bytes) -> str:
    """Extract node source text from byte offsets."""

    byte_range = node.byte_range()
    return source_bytes[byte_range.start: byte_range.end].decode("utf-8", errors="replace")


def _collapse_multiline_text(text: str) -> str:
    """Normalize multi-line comment text into a single line string."""

    parts = [part.strip() for part in text.splitlines()]
    return " ".join([part for part in parts if part]).strip()


def _strip_single_line_prefix(text: str, prefixes: Sequence[str]) -> str:
    """Remove single-line comment prefix from text."""

    stripped = text.strip()
    for prefix in sorted(prefixes, key=len, reverse=True):
        if not stripped.startswith(prefix):
            continue

        if prefix == "#":
            return stripped.lstrip("#").strip()

        return stripped[len(prefix):].strip()

    return stripped


def _strip_multi_line_delimiters(
    text: str,
    delimiters: Sequence[tuple[str, str]],
) -> str:
    """Remove configured multi-line delimiters from text."""

    stripped = text.strip()
    for start_delimiter, end_delimiter in sorted(delimiters, key=lambda item: len(item[0]), reverse=True):
        if stripped.startswith(start_delimiter):
            stripped = stripped[len(start_delimiter):]
            stripped = stripped.strip()
            if end_delimiter and stripped.endswith(end_delimiter):
                stripped = stripped[: -len(end_delimiter)]
            break
    return _collapse_multiline_text(stripped)


def _is_comment_node(node_kind: str, extra_comment_node_kinds: set[str]) -> bool:
    """Decide whether a node kind should be considered as comment."""

    kind = node_kind.lower()
    if "comment" in kind:
        return True
    return node_kind in extra_comment_node_kinds


def _is_docstring_node(
    node,
    node_kind: str,
    node_text: str,
    docstring_node_kinds: set[str],
    docstring_parent_kinds: set[str],
    docstring_delimiters: Sequence[tuple[str, str]],
) -> bool:
    """Decide whether a string node should be treated as documentation comment."""

    if not docstring_node_kinds or node_kind not in docstring_node_kinds:
        return False

    parent = node.parent()
    if parent is None:
        return False

    if docstring_parent_kinds and parent.kind() not in docstring_parent_kinds:
        return False

    stripped = node_text.strip()
    for start_delimiter, _ in docstring_delimiters:
        if stripped.startswith(start_delimiter):
            return True

    return False


def _infer_comment_category(
    node_kind: str,
    comment_text: str,
    start_line: int,
    end_line: int,
    single_line_prefixes: Sequence[str],
    multi_line_delimiters: Sequence[tuple[str, str]],
    force_single_line_node_kinds: set[str],
    force_multi_line_node_kinds: set[str],
) -> str:
    """Infer whether a comment should be single-line or multi-line."""

    if node_kind in force_single_line_node_kinds:
        return "single"
    if node_kind in force_multi_line_node_kinds:
        return "multi"

    stripped = comment_text.strip()

    for start_delimiter, _ in sorted(multi_line_delimiters, key=lambda item: len(item[0]), reverse=True):
        if stripped.startswith(start_delimiter):
            return "multi"

    for prefix in sorted(single_line_prefixes, key=len, reverse=True):
        if stripped.startswith(prefix):
            return "single"

    kind_lower = node_kind.lower()
    if "line_comment" in kind_lower:
        return "single"
    if "block_comment" in kind_lower or "multiline_comment" in kind_lower:
        return "multi"

    if start_line != end_line:
        return "multi"

    return "single"


def _group_contiguous_single_line_comments(
    single_line_comments: list[CommentRecord],
) -> tuple[list[CommentRecord], list[tuple[int, int, str]]]:
    """Group contiguous single line comments into cont_single_line_comment output."""

    if not single_line_comments:
        return [], []

    grouped_comments: list[tuple[int, int, str]] = []
    remaining_single_comments: list[CommentRecord] = []

    current_group: list[CommentRecord] = [single_line_comments[0]]

    for comment in single_line_comments[1:]:
        previous = current_group[-1]
        if comment.start_line == previous.start_line + 1:
            current_group.append(comment)
            continue

        if len(current_group) > 1:
            grouped_comments.append(
                (
                    current_group[0].start_line,
                    current_group[-1].start_line,
                    "".join(f" {entry.comment}" for entry in current_group),
                )
            )
        else:
            remaining_single_comments.append(current_group[0])

        current_group = [comment]

    if len(current_group) > 1:
        grouped_comments.append(
            (
                current_group[0].start_line,
                current_group[-1].start_line,
                "".join(f" {entry.comment}" for entry in current_group),
            )
        )
    else:
        remaining_single_comments.append(current_group[0])

    return remaining_single_comments, grouped_comments


def extract_with_tree_sitter(
    file_path: str,
    display_language: str,
    parser_language: str,
    single_line_prefixes: Sequence[str] | None = None,
    multi_line_delimiters: Sequence[tuple[str, str]] | None = None,
    extra_comment_node_kinds: Sequence[str] | None = None,
    force_single_line_node_kinds: Sequence[str] | None = None,
    force_multi_line_node_kinds: Sequence[str] | None = None,
    docstring_node_kinds: Sequence[str] | None = None,
    docstring_parent_kinds: Sequence[str] | None = None,
    docstring_delimiters: Sequence[tuple[str, str]] | None = None,
    group_single_line_comments: bool = True,
) -> ScanOutput:
    """
    Extract comments for a file using Tree-Sitter and return ScanOutput.
    """

    single_line_prefixes = single_line_prefixes or []
    multi_line_delimiters = multi_line_delimiters or []
    extra_comment_node_kinds = set(extra_comment_node_kinds or [])
    force_single_line_node_kinds = set(force_single_line_node_kinds or [])
    force_multi_line_node_kinds = set(force_multi_line_node_kinds or [])
    docstring_node_kinds = set(docstring_node_kinds or [])
    docstring_parent_kinds = set(docstring_parent_kinds or [])
    docstring_delimiters = docstring_delimiters or []

    with open(file_path, encoding="utf-8", errors="replace") as source_file:
        source_text = source_file.read()

    source_lines = source_text.splitlines()
    total_lines = len(source_lines)
    blank_lines = sum(1 for line in source_lines if line.strip() == "")
    source_bytes = source_text.encode("utf-8", errors="replace")

    parser = _get_cached_parser(parser_language)
    syntax_tree = parser.parse(source_text)

    comment_records: list[CommentRecord] = []

    for node in _iter_nodes_dfs(syntax_tree.root_node()):
        node_kind = node.kind()
        node_text = _extract_node_text(node, source_bytes)

        is_comment = _is_comment_node(node_kind, extra_comment_node_kinds)
        is_docstring = _is_docstring_node(
            node=node,
            node_kind=node_kind,
            node_text=node_text,
            docstring_node_kinds=docstring_node_kinds,
            docstring_parent_kinds=docstring_parent_kinds,
            docstring_delimiters=docstring_delimiters,
        )

        if not (is_comment or is_docstring):
            continue

        start_line = node.start_position().row + 1
        end_line = node.end_position().row + 1

        category = _infer_comment_category(
            node_kind=node_kind,
            comment_text=node_text,
            start_line=start_line,
            end_line=end_line,
            single_line_prefixes=single_line_prefixes,
            multi_line_delimiters=multi_line_delimiters,
            force_single_line_node_kinds=force_single_line_node_kinds,
            force_multi_line_node_kinds=force_multi_line_node_kinds,
        )

        if is_docstring:
            category = "multi"
            clean_comment = _strip_multi_line_delimiters(node_text, docstring_delimiters)
        elif category == "single":
            clean_comment = _strip_single_line_prefix(node_text, single_line_prefixes)
        else:
            clean_comment = _strip_multi_line_delimiters(node_text, multi_line_delimiters)

        comment_records.append(
            CommentRecord(
                start_line=start_line,
                end_line=end_line,
                comment=clean_comment,
                category=category,
            )
        )

    # Keep order deterministic for output and tests.
    comment_records.sort(key=lambda entry: (entry.start_line, entry.end_line, entry.category))

    single_line_comments = [record for record in comment_records if record.category == "single"]
    multi_line_comments = [record for record in comment_records if record.category == "multi"]

    if group_single_line_comments:
        single_line_comments, grouped_single_line_comments = _group_contiguous_single_line_comments(
            single_line_comments
        )
    else:
        grouped_single_line_comments = []

    output = ScanOutput()
    output.filename = os.path.basename(file_path)
    output.lang = display_language
    output.total_lines = total_lines
    output.blank_lines = blank_lines

    for entry in single_line_comments:
        output.single_line_comment.append(SingleLine(entry.start_line, entry.comment))

    for start_line, end_line, comment in grouped_single_line_comments:
        output.cont_single_line_comment.append(MultiLine(start_line, end_line, comment))

    for entry in multi_line_comments:
        output.multi_line_comment.append(MultiLine(entry.start_line, entry.end_line, entry.comment))

    total_lines_of_comments = len(single_line_comments)
    total_lines_of_comments += sum(
        (end_line - start_line + 1)
        for start_line, end_line, _ in grouped_single_line_comments
    )
    total_lines_of_comments += sum(
        (entry.end_line - entry.start_line + 1) for entry in multi_line_comments
    )

    output.total_lines_of_comments = total_lines_of_comments

    return output
