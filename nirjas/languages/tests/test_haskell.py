#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Contract tests for Haskell extractor."""

import os
import unittest

from nirjas.languages import haskell
from nirjas.languages.tests._contract import (
    assert_scan_output_contract,
    assert_source_extractor_contract,
)


class HaskellTest(unittest.TestCase):
    """Contract tests for Haskell language support."""

    testfile = os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        "TestFiles/textcomment.hs",
    )

    def test_output_contract(self):
        """Verify extractor schema and metadata invariants."""

        scan_result = haskell.haskellExtractor(self.testfile).get_dict()
        assert_scan_output_contract(self, scan_result, self.testfile, 'Haskell')

    def test_source_contract(self):
        """Verify source extraction API contract."""

        assert_source_extractor_contract(self, haskell.haskellSource, self.testfile)
