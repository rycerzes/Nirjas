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

import unittest
from typing import Any

from nirjas.language_registry import (
    NotSupportedExtension,
    nirjas_name_from_path,
    parser_name,
    parser_name_for_path,
)
from nirjas.languages.language_config import LanguageConfig
from nirjas.languages.language_handlers import DefaultHandler, PythonHandler, get_handler
from nirjas.languages.parser_cache import parse_file
from nirjas.languages.tree_sitter.comment_span import CommentSpan


class LanguageRegistryTest(unittest.TestCase):
    def test_nirjas_name_from_path(self):
        self.assertEqual(nirjas_name_from_path("foo.py"), "python")
        self.assertEqual(nirjas_name_from_path("bar.cpp"), "cpp")

    def test_unsupported_extension_raises(self):
        with self.assertRaises(NotSupportedExtension):
            nirjas_name_from_path("file.xyz")

    def test_parser_name_aliases(self):
        self.assertEqual(parser_name("c_sharp"), "csharp")
        self.assertEqual(parser_name("shell"), "bash")
        self.assertEqual(parser_name("python"), "python")

    def test_parser_name_for_tsx(self):
        self.assertEqual(parser_name_for_path("component.tsx"), "tsx")
        self.assertEqual(parser_name_for_path("module.ts"), "typescript")


class LanguageConfigTest(unittest.TestCase):
    def test_frozen_config_fields(self):
        config = LanguageConfig(
            display_language="C",
            parser_language="c",
            comment_node_kinds=frozenset({"comment"}),
            single_line_prefixes=("//",),
            multi_line_delimiters=(("/*", "*/"),),
        )
        self.assertEqual(config.display_language, "C")
        self.assertEqual(config.comment_node_kinds, frozenset({"comment"}))


class CommentSpanTest(unittest.TestCase):
    def test_comment_span_is_frozen(self):
        span = CommentSpan(
            start_byte=0,
            end_byte=10,
            start_line=1,
            end_line=1,
            node_kind="comment",
            is_documentation=False,
            raw_text="# hello",
        )
        with self.assertRaises(AttributeError):
            span.start_byte = 5  # type: ignore[misc]


class LanguageHandlerTest(unittest.TestCase):
    def test_default_handler_returns_none(self):
        handler = DefaultHandler()
        self.assertIsNone(handler.is_documentation_comment(None, None, ""))

    def test_get_handler_fallback(self):
        self.assertIsInstance(get_handler(None), DefaultHandler)
        self.assertIsInstance(get_handler("unknown"), DefaultHandler)
        self.assertIsInstance(get_handler("python"), PythonHandler)

    def test_python_handler_docstring_under_module(self):
        source = '"""module doc"""\nx = 1\n'
        handler = PythonHandler()
        string_node, parent = _require_string_node(source)
        self.assertTrue(handler.is_documentation_comment(string_node, parent, source))

    def test_python_handler_string_literal_not_docstring(self):
        source = 'x = """not a doc"""\n'
        handler = PythonHandler()
        string_node, parent = _require_string_node(source)
        self.assertFalse(handler.is_documentation_comment(string_node, parent, source))

    def test_python_handler_skips_leading_comments(self):
        source = '# leading\n"""real doc"""\n'
        handler = PythonHandler()
        string_node, parent = _require_string_node(source)
        self.assertTrue(handler.is_documentation_comment(string_node, parent, source))


def _python_parser():
    from nirjas.languages.parser_cache import get_cached_parser

    return get_cached_parser("python")


def _require_string_node(source: str) -> tuple[Any, Any]:
    tree, _ = parse_file(_python_parser(), source)
    root = tree.root_node()
    found = _find_node(root, "string")
    if found is None:
        raise AssertionError("expected a string node in parse tree")
    return found


def _find_node(root: Any, kind: str) -> tuple[Any, Any] | None:
    if root.kind() == kind:
        return root, root.parent()

    for index in range(root.child_count()):
        found = _find_node(root.child(index), kind)
        if found is not None:
            return found
    return None


if __name__ == "__main__":
    unittest.main()
