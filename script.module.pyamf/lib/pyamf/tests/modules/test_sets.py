# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Tests for the C{sets} module integration.
"""

import unittest

import pyamf
from pyamf.tests.util import check_buffer


class ImmutableSetTestCase(unittest.TestCase):
    def test_amf0_encode(self):
        x = frozenset(['1', '2', '3'])

        self.assertTrue(check_buffer(
            pyamf.encode(x, encoding=pyamf.AMF0).getvalue(), (
                b'\n\x00\x00\x00\x03', (
                    b'\x02\x00\x011',
                    b'\x02\x00\x013',
                    b'\x02\x00\x012'
                )
            )
        ))

    def test_amf3_encode(self):
        x = frozenset(['1', '2', '3'])

        self.assertTrue(check_buffer(
            pyamf.encode(x, encoding=pyamf.AMF3).getvalue(), (
                b'\t\x07\x01', (
                    b'\x06\x031',
                    b'\x06\x033',
                    b'\x06\x032'
                )
            )
        ))
