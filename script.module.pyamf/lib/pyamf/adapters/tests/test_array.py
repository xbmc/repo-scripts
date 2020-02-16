# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Tests for the L{array} L{pyamf.adapters._array} module.

@since: 0.5
"""

try:
    import array
except ImportError:
    array = None

import unittest

import pyamf


class ArrayTestCase(unittest.TestCase):
    """
    """

    def setUp(self):
        if not array:
            self.skipTest("'array' not available")

        self.orig = [ord('f'), ord('o'), ord('o')]

        self.obj = array.array('b')

        self.obj.append(ord('f'))
        self.obj.append(ord('o'))
        self.obj.append(ord('o'))

    def encdec(self, encoding):
        return next(pyamf.decode(
            pyamf.encode(self.obj, encoding=encoding),
            encoding=encoding))

    def test_amf0(self):
        self.assertEqual(self.encdec(pyamf.AMF0), self.orig)

    def test_amf3(self):
        self.assertEqual(self.encdec(pyamf.AMF3), self.orig)
