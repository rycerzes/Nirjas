#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression tests for Tree-Sitter based comment parsing.

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
import tempfile
import unittest

from nirjas.languages import c, javascript, python


class TreeSitterRegressionTest(unittest.TestCase):
    """Ensure string literals are not misidentified as comments."""

    def _extract_with_temp_file(self, suffix: str, content: str, extractor):
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=suffix,
            delete=False,
            encoding="utf-8",
        ) as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name

        try:
            return extractor(temp_path).get_dict()
        finally:
            os.unlink(temp_path)

    @staticmethod
    def _all_comment_texts(scan_output: dict) -> list[str]:
        comments = [
            entry["comment"] for entry in scan_output["single_line_comment"]
        ]
        comments.extend(
            entry["comment"] for entry in scan_output["cont_single_line_comment"]
        )
        comments.extend(
            entry["comment"] for entry in scan_output["multi_line_comment"]
        )
        return comments

    def test_hash_inside_python_string_is_not_comment(self):
        """`#` inside strings must not be detected as a comment."""

        scan_output = self._extract_with_temp_file(
            suffix=".py",
            content='value = "# not a comment"\n# real comment\n',
            extractor=python.pythonExtractor,
        )

        self.assertEqual(scan_output["metadata"]["total_lines_of_comments"], 1)
        self.assertEqual(len(scan_output["single_line_comment"]), 1)
        self.assertEqual(scan_output["single_line_comment"][0]["comment"], "real comment")

    def test_double_slash_inside_url_string_is_not_comment(self):
        """`//` inside URL/string literals must not be comments."""

        scan_output = self._extract_with_temp_file(
            suffix=".js",
            content=(
                'const url = "https://example.com/path";\n'
                'const marker = "// not a comment";\n'
                '// real comment\n'
            ),
            extractor=javascript.javascriptExtractor,
        )

        comment_texts = self._all_comment_texts(scan_output)
        self.assertEqual(scan_output["metadata"]["total_lines_of_comments"], 1)
        self.assertIn("real comment", comment_texts)
        self.assertFalse(any("example.com" in text for text in comment_texts))
        self.assertFalse(any("not a comment" in text for text in comment_texts))

    def test_c_block_comment_tokens_inside_string_are_not_comments(self):
        """`/* */` tokens inside C strings must not be parsed as comments."""

        scan_output = self._extract_with_temp_file(
            suffix=".c",
            content=(
                'const char *a = "/* not a comment */";\n'
                'const char *b = "// not a comment";\n'
                '// line comment\n'
                '/* block comment */\n'
            ),
            extractor=c.cExtractor,
        )

        comment_texts = self._all_comment_texts(scan_output)
        self.assertEqual(scan_output["metadata"]["total_lines_of_comments"], 2)
        self.assertIn("line comment", comment_texts)
        self.assertIn("block comment", comment_texts)
        self.assertFalse(any("not a comment" in text for text in comment_texts))
