#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared helpers for language extractor contract tests."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable


def _count_lines(file_path: str) -> int:
    with open(file_path, encoding="utf-8", errors="replace") as source_file:
        return sum(1 for _ in source_file)


def _count_blank_lines(file_path: str) -> int:
    with open(file_path, encoding="utf-8", errors="replace") as source_file:
        return sum(1 for line in source_file if line.strip() == "")


def _count_comment_lines(scan_output: dict) -> int:
    single_line_comments = len(scan_output["single_line_comment"])

    contiguous_single_line_comments = sum(
        entry["end_line"] - entry["start_line"] + 1
        for entry in scan_output["cont_single_line_comment"]
    )

    multi_line_comments = sum(
        entry["end_line"] - entry["start_line"] + 1
        for entry in scan_output["multi_line_comment"]
    )

    return single_line_comments + contiguous_single_line_comments + multi_line_comments


def assert_scan_output_contract(
    testcase,
    scan_output: dict,
    file_path: str,
    language_name: str,
) -> None:
    """Validate schema + metadata invariants for extractor output."""

    testcase.assertIsInstance(scan_output, dict)

    metadata = scan_output.get("metadata")
    testcase.assertIsInstance(metadata, dict)

    total_lines = _count_lines(file_path)
    blank_lines = _count_blank_lines(file_path)

    testcase.assertEqual(metadata.get("filename"), os.path.basename(file_path))
    testcase.assertEqual(metadata.get("lang"), language_name)
    testcase.assertEqual(metadata.get("total_lines"), total_lines)
    testcase.assertEqual(metadata.get("blank_lines"), blank_lines)

    for section in [
        "single_line_comment",
        "cont_single_line_comment",
        "multi_line_comment",
    ]:
        testcase.assertIn(section, scan_output)
        testcase.assertIsInstance(scan_output[section], list)

    for single_line_comment in scan_output["single_line_comment"]:
        testcase.assertIn("line_number", single_line_comment)
        testcase.assertIn("comment", single_line_comment)
        testcase.assertGreaterEqual(single_line_comment["line_number"], 1)
        testcase.assertLessEqual(single_line_comment["line_number"], total_lines)

    for contiguous_comment in scan_output["cont_single_line_comment"]:
        testcase.assertIn("start_line", contiguous_comment)
        testcase.assertIn("end_line", contiguous_comment)
        testcase.assertIn("comment", contiguous_comment)
        testcase.assertLessEqual(contiguous_comment["start_line"], contiguous_comment["end_line"])
        testcase.assertGreaterEqual(contiguous_comment["start_line"], 1)
        testcase.assertLessEqual(contiguous_comment["end_line"], total_lines)

    for multi_line_comment in scan_output["multi_line_comment"]:
        testcase.assertIn("start_line", multi_line_comment)
        testcase.assertIn("end_line", multi_line_comment)
        testcase.assertIn("comment", multi_line_comment)
        testcase.assertLessEqual(multi_line_comment["start_line"], multi_line_comment["end_line"])
        testcase.assertGreaterEqual(multi_line_comment["start_line"], 1)
        testcase.assertLessEqual(multi_line_comment["end_line"], total_lines)

    total_comment_lines = _count_comment_lines(scan_output)
    testcase.assertEqual(metadata.get("total_lines_of_comments"), total_comment_lines)
    testcase.assertEqual(
        metadata.get("sloc"),
        total_lines - (metadata.get("total_lines_of_comments") + blank_lines),
    )


def assert_source_extractor_contract(
    testcase,
    source_extractor: Callable[[str, str], str],
    source_file: str,
) -> None:
    """Validate source extraction API contract."""

    with tempfile.TemporaryDirectory() as temp_dir:
        output_file = os.path.join(temp_dir, "source.txt")
        returned_path = source_extractor(source_file, output_file)

        testcase.assertEqual(returned_path, output_file)
        testcase.assertTrue(os.path.exists(output_file))
