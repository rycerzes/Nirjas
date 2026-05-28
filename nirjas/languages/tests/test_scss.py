#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Contract tests for Scss extractor."""

import os
import unittest

from nirjas.languages import scss
from nirjas.languages.tests._contract import (
    assert_scan_output_contract,
    assert_source_extractor_contract,
)


class ScssTest(unittest.TestCase):
    """Contract tests for Scss language support."""

    testfile = os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        "TestFiles/textcomment.scss",
    )

    def test_output_contract(self):
        """Verify extractor schema and metadata invariants."""

        scan_result = scss.scssExtractor(self.testfile).get_dict()
        assert_scan_output_contract(self, scan_result, self.testfile, 'Scss')

    def test_source_contract(self):
        """Verify source extraction API contract."""

        assert_source_extractor_contract(self, scss.scssSource, self.testfile)
