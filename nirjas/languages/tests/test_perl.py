#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Contract tests for Perl extractor."""

import os
import unittest

from nirjas.languages import perl
from nirjas.languages.tests._contract import (
    assert_scan_output_contract,
    assert_source_extractor_contract,
)


class PerlTest(unittest.TestCase):
    """Contract tests for Perl language support."""

    testfile = os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        "TestFiles/textcomment.pl",
    )

    def test_output_contract(self):
        """Verify extractor schema and metadata invariants."""

        scan_result = perl.perlExtractor(self.testfile).get_dict()
        assert_scan_output_contract(self, scan_result, self.testfile, 'Perl')

    def test_source_contract(self):
        """Verify source extraction API contract."""

        assert_source_extractor_contract(self, perl.perlSource, self.testfile)
