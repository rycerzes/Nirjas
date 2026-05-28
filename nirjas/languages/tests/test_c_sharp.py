#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Contract tests for C# extractor."""

import os
import unittest

from nirjas.languages import c_sharp
from nirjas.languages.tests._contract import (
    assert_scan_output_contract,
    assert_source_extractor_contract,
)


class CSharpTest(unittest.TestCase):
    """Contract tests for C# language support."""

    testfile = os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        "TestFiles/textcomment.cs",
    )

    def test_output_contract(self):
        """Verify extractor schema and metadata invariants."""

        scan_result = c_sharp.c_sharpExtractor(self.testfile).get_dict()
        assert_scan_output_contract(self, scan_result, self.testfile, 'C#')

    def test_source_contract(self):
        """Verify source extraction API contract."""

        assert_source_extractor_contract(self, c_sharp.c_sharpSource, self.testfile)
