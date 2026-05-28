#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Contract tests for SQL extractor."""

import os
import unittest

from nirjas.languages import sql
from nirjas.languages.tests._contract import (
    assert_scan_output_contract,
    assert_source_extractor_contract,
)


class SQLTest(unittest.TestCase):
    """Contract tests for SQL language support."""

    testfile = os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        "TestFiles/textcomment.sql",
    )

    def test_output_contract(self):
        """Verify extractor schema and metadata invariants."""

        scan_result = sql.sqlExtractor(self.testfile).get_dict()
        assert_scan_output_contract(self, scan_result, self.testfile, 'SQL')

    def test_source_contract(self):
        """Verify source extraction API contract."""

        assert_source_extractor_contract(self, sql.sqlSource, self.testfile)
