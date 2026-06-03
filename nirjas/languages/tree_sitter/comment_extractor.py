#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Copyright (C) 2020  Ayush Bhardwaj (classicayush@gmail.com),
Kaushlendra Pratap (kaushlendrapratap.9837@gmail.com)

SPDX-License-Identifier: LGPL-2.1

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Sequence

from nirjas.languages.language_config import LanguageConfig
from nirjas.languages.language_handlers import get_handler
from nirjas.languages.parser_cache import get_cached_parser_for_path, parse_file
from nirjas.languages.tree_sitter.comment_span import CommentSpan
from nirjas.languages.tree_sitter.comment_visitor import collect_comment_spans
from nirjas.output import MultiLine, SingleLine
from nirjas.output import ScanOutput


@dataclass(frozen=True)
class _CommentRecord:
    start_line: int
    end_line: int
    comment: str
    category: str


def extract_comments(syntax: LanguageConfig, file_path: str) -> ScanOutput:
    """Extract comments from a source file using the shared Tree-Sitter pipeline."""

    with open(file_path, encoding="utf-8", errors="replace") as source_file:
        source_text = source_file.read()

    source_lines = source_text.splitlines()
    total_lines = len(source_lines)
    blank_lines = sum(1 for line in source_lines if line.strip() == "")

    parser = get_cached_parser_for_path(file_path)
    syntax_tree, source_bytes = parse_file(parser, source_text)
    spans = collect_comment_spans(
        syntax_tree.root_node(),
        source_bytes,
        syntax,
        get_handler(syntax.handler_name),
    )

    records = [_span_to_record(span, syntax) for span in spans]
    records.sort(key=lambda entry: (entry.start_line, entry.end_line, entry.category))

    single_line_comments = [record for record in records if record.category == "single"]
    multi_line_comments = [record for record in records if record.category == "multi"]

    if syntax.group_contiguous_single_lines:
        single_line_comments, grouped_single_line_comments = (
            _group_contiguous_single_line_comments(single_line_comments)
        )
    else:
        grouped_single_line_comments = []

    output = ScanOutput()
    output.filename = os.path.basename(file_path)
    output.lang = syntax.display_language
    output.total_lines = total_lines
    output.blank_lines = blank_lines

    for entry in single_line_comments:
        output.single_line_comment.append(SingleLine(entry.start_line, entry.comment))

    for start_line, end_line, comment in grouped_single_line_comments:
        output.cont_single_line_comment.append(MultiLine(start_line, end_line, comment))

    for entry in multi_line_comments:
        output.multi_line_comment.append(
            MultiLine(entry.start_line, entry.end_line, entry.comment)
        )

    output.total_lines_of_comments = len(single_line_comments)
    output.total_lines_of_comments += sum(
        (end_line - start_line + 1)
        for start_line, end_line, _ in grouped_single_line_comments
    )
    output.total_lines_of_comments += sum(
        (entry.end_line - entry.start_line + 1) for entry in multi_line_comments
    )

    return output


def _span_to_record(span: CommentSpan, syntax: LanguageConfig) -> _CommentRecord:
    category = _infer_comment_category(span, syntax)
    if span.is_documentation or category == "multi":
        clean_comment = _strip_multi_line_delimiters(
            span.raw_text,
            syntax.multi_line_delimiters,
        )
        category = "multi"
    else:
        clean_comment = _strip_single_line_prefix(
            span.raw_text,
            syntax.single_line_prefixes,
        )

    return _CommentRecord(
        start_line=span.start_line,
        end_line=span.end_line,
        comment=clean_comment,
        category=category,
    )


def _infer_comment_category(span: CommentSpan, syntax: LanguageConfig) -> str:
    stripped = span.raw_text.strip()
    if span.is_documentation:
        return "multi"

    kind_lower = span.node_kind.lower()
    if "line_comment" in kind_lower:
        return "single"
    if "block_comment" in kind_lower or "multiline_comment" in kind_lower:
        return "multi"

    for start_delimiter, _ in sorted(
        syntax.multi_line_delimiters,
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        if stripped.startswith(start_delimiter):
            return "multi"

    if span.start_line != span.end_line:
        return "multi"

    return "single"


def _collapse_multiline_text(text: str) -> str:
    parts = [part.strip() for part in text.splitlines()]
    return " ".join([part for part in parts if part]).strip()


def _strip_single_line_prefix(text: str, prefixes: Sequence[str]) -> str:
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
    stripped = text.strip()
    for start_delimiter, end_delimiter in sorted(
        delimiters,
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        if stripped.startswith(start_delimiter):
            stripped = stripped[len(start_delimiter):]
            stripped = stripped.strip()
            if end_delimiter and stripped.endswith(end_delimiter):
                stripped = stripped[: -len(end_delimiter)]
            break
    return _collapse_multiline_text(stripped)


def _group_contiguous_single_line_comments(
    single_line_comments: list[_CommentRecord],
) -> tuple[list[_CommentRecord], list[tuple[int, int, str]]]:
    if not single_line_comments:
        return [], []

    grouped_comments: list[tuple[int, int, str]] = []
    remaining_single_comments: list[_CommentRecord] = []
    current_group: list[_CommentRecord] = [single_line_comments[0]]

    for comment in single_line_comments[1:]:
        previous = current_group[-1]
        if comment.start_line == previous.start_line + 1:
            current_group.append(comment)
            continue

        _append_comment_group(
            current_group,
            grouped_comments,
            remaining_single_comments,
        )
        current_group = [comment]

    _append_comment_group(
        current_group,
        grouped_comments,
        remaining_single_comments,
    )
    return remaining_single_comments, grouped_comments


def _append_comment_group(
    current_group: list[_CommentRecord],
    grouped_comments: list[tuple[int, int, str]],
    remaining_single_comments: list[_CommentRecord],
) -> None:
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
