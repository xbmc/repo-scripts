# -*- coding: utf-8 -*-
#
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Tests for AMF utilities.

@since: 0.1.0
"""

import unittest

from datetime import datetime
from io import BytesIO

import pyamf
from pyamf import util
from pyamf.tests.util import replace_dict

PosInf = 1e300000
NegInf = -1e300000
NaN = PosInf / PosInf


def isNaN(val):
    return str(float(val)) == str(NaN)


def isPosInf(val):
    return str(float(val)) == str(PosInf)


def isNegInf(val):
    return str(float(val)) == str(NegInf)


class TimestampTestCase(unittest.TestCase):
    """
    Test UTC timestamps.
    """

    def test_get_timestamp(self):
        self.assertEqual(
            util.get_timestamp(datetime(2007, 11, 12)),
            1194825600
        )

    def test_get_datetime(self):
        self.assertEqual(util.get_datetime(1194825600), datetime(2007, 11, 12))

    def test_get_negative_datetime(self):
        self.assertEqual(util.get_datetime(-31536000), datetime(1969, 1, 1))

    def test_preserved_microseconds(self):
        dt = datetime(2009, 3, 8, 23, 30, 47, 770122)
        ts = util.get_timestamp(dt)
        self.assertEqual(util.get_datetime(ts), dt)


class StringIOTestCase(unittest.TestCase):

    def test_create(self):
        sp = util.BufferedByteStream()

        self.assertEqual(sp.tell(), 0)
        self.assertEqual(sp.getvalue(), b'')
        self.assertEqual(len(sp), 0)
        self.assertEqual(sp.getvalue(), b'')

        sp = util.BufferedByteStream(None)

        self.assertEqual(sp.tell(), 0)
        self.assertEqual(sp.getvalue(), b'')
        self.assertEqual(len(sp), 0)

        sp = util.BufferedByteStream('')

        self.assertEqual(sp.tell(), 0)
        self.assertEqual(sp.getvalue(), b'')
        self.assertEqual(len(sp), 0)

        sp = util.BufferedByteStream('spam')

        self.assertEqual(sp.tell(), 0)
        self.assertEqual(sp.getvalue(), b'spam')
        self.assertEqual(len(sp), 4)

        sp = util.BufferedByteStream(BytesIO('this is a test'.encode()))
        self.assertEqual(sp.tell(), 0)
        self.assertEqual(sp.getvalue(), b'this is a test')
        self.assertEqual(len(sp), 14)

        self.assertRaises(TypeError, util.BufferedByteStream, self)

    def test_getvalue(self):
        sp = util.BufferedByteStream()

        sp.write('asdfasdf')
        self.assertEqual(sp.getvalue(), b'asdfasdf')
        sp.write('spam')
        self.assertEqual(sp.getvalue(), b'asdfasdfspam')

    def test_read(self):
        sp = util.BufferedByteStream('this is a test')

        self.assertEqual(len(sp), 14)
        self.assertEqual(sp.read(1), b't')
        self.assertEqual(sp.getvalue(), b'this is a test')
        self.assertEqual(len(sp), 14)
        self.assertEqual(sp.read(10), b'his is a t')
        self.assertEqual(sp.read(), b'est')

    def test_seek(self):
        sp = util.BufferedByteStream('abcdefghijklmnopqrstuvwxyz')

        self.assertEqual(sp.getvalue(), b'abcdefghijklmnopqrstuvwxyz')
        self.assertEqual(sp.tell(), 0)

        # Relative to the beginning of the stream
        sp.seek(0, 0)
        self.assertEqual(sp.tell(), 0)
        self.assertEqual(sp.getvalue(), b'abcdefghijklmnopqrstuvwxyz')
        self.assertEqual(sp.read(1), b'a')
        self.assertEqual(len(sp), 26)

        sp.seek(10, 0)
        self.assertEqual(sp.tell(), 10)
        self.assertEqual(sp.getvalue(), b'abcdefghijklmnopqrstuvwxyz')
        self.assertEqual(sp.read(1), b'k')
        self.assertEqual(len(sp), 26)

        sp.seek(-5, 1)
        self.assertEqual(sp.tell(), 6)
        self.assertEqual(sp.getvalue(), b'abcdefghijklmnopqrstuvwxyz')
        self.assertEqual(sp.read(1), b'g')
        self.assertEqual(len(sp), 26)

        sp.seek(-3, 2)
        self.assertEqual(sp.tell(), 23)
        self.assertEqual(sp.getvalue(), b'abcdefghijklmnopqrstuvwxyz')
        self.assertEqual(sp.read(1), b'x')
        self.assertEqual(len(sp), 26)

    def test_tell(self):
        sp = util.BufferedByteStream('abcdefghijklmnopqrstuvwxyz')

        self.assertEqual(sp.getvalue(), b'abcdefghijklmnopqrstuvwxyz')
        self.assertEqual(len(sp), 26)

        self.assertEqual(sp.tell(), 0)
        sp.read(1)
        self.assertEqual(sp.tell(), 1)

        self.assertEqual(sp.getvalue(), b'abcdefghijklmnopqrstuvwxyz')
        self.assertEqual(len(sp), 26)

        sp.read(5)
        self.assertEqual(sp.tell(), 6)

    def test_truncate(self):
        sp = util.BufferedByteStream('abcdef')

        self.assertEqual(sp.getvalue(), b'abcdef')
        self.assertEqual(len(sp), 6)

        sp.truncate()
        self.assertEqual(sp.getvalue(), b'')
        self.assertEqual(len(sp), 0)

        sp = util.BufferedByteStream('hello')

        self.assertEqual(sp.getvalue(), b'hello')
        self.assertEqual(len(sp), 5)

        sp.truncate(3)

        self.assertEqual(sp.getvalue(), b'hel')
        self.assertEqual(len(sp), 3)

    def test_write(self):
        sp = util.BufferedByteStream()

        self.assertEqual(sp.getvalue(), b'')
        self.assertEqual(len(sp), 0)
        self.assertEqual(sp.tell(), 0)

        sp.write('hello')
        self.assertEqual(sp.getvalue(), b'hello')
        self.assertEqual(len(sp), 5)
        self.assertEqual(sp.tell(), 5)

        sp = util.BufferedByteStream(b'xyz')

        self.assertEqual(sp.getvalue(), b'xyz')
        self.assertEqual(len(sp), 3)
        self.assertEqual(sp.tell(), 0)

        sp.write('abc')
        self.assertEqual(sp.getvalue(), b'abc')
        self.assertEqual(len(sp), 3)
        self.assertEqual(sp.tell(), 3)

    def test_len(self):
        sp = util.BufferedByteStream()

        self.assertEqual(sp.getvalue(), b'')
        self.assertEqual(len(sp), 0)
        self.assertEqual(sp.tell(), 0)

        sp.write('xyz')

        self.assertEqual(len(sp), 3)

        sp = util.BufferedByteStream('foo')

        self.assertEqual(len(sp), 3)

        sp.seek(0, 2)
        sp.write('xyz')

        self.assertEqual(len(sp), 6)

    def test_consume(self):
        sp = util.BufferedByteStream()

        self.assertEqual(sp.getvalue(), b'')
        self.assertEqual(sp.tell(), 0)

        sp.consume()

        self.assertEqual(sp.getvalue(), b'')
        self.assertEqual(sp.tell(), 0)

        sp = util.BufferedByteStream('foobar')

        self.assertEqual(sp.getvalue(), b'foobar')
        self.assertEqual(sp.tell(), 0)

        sp.seek(3)

        self.assertEqual(sp.tell(), 3)
        sp.consume()

        self.assertEqual(sp.getvalue(), b'bar')
        self.assertEqual(sp.tell(), 0)

        # from ticket 451 - http://pyamf.org/ticket/451
        sp = util.BufferedByteStream('abcdef')
        # move the stream pos to the end
        sp.read()

        self.assertEqual(len(sp), 6)
        sp.consume()
        self.assertEqual(len(sp), 0)

        sp = util.BufferedByteStream('abcdef')
        sp.seek(6)
        sp.consume()
        self.assertEqual(sp.getvalue(), b'')


class DataTypeMixInTestCase(unittest.TestCase):
    endians = ('>', '<')  # big, little

    def _write_endian(self, obj, func, args, expected):
        old_endian = obj.endian

        for x in range(2):
            obj.truncate()
            obj.endian = self.endians[x]

            func(*args)

            self.assertEqual(obj.getvalue(), expected[x])

        obj.endian = old_endian

    def _read_endian(self, data, func, args, expected):
        for x in range(2):
            obj = util.BufferedByteStream(data[x])
            obj.endian = self.endians[x]

            result = getattr(obj, func)(*args)

            self.assertEqual(result, expected)

    def test_read_uchar(self):
        x = util.BufferedByteStream(b'\x00\xff')

        self.assertEqual(x.read_uchar(), 0)
        self.assertEqual(x.read_uchar(), 255)

    def test_write_uchar(self):
        x = util.BufferedByteStream()

        x.write_uchar(0)
        self.assertEqual(x.getvalue(), b'\x00')
        x.write_uchar(255)
        self.assertEqual(x.getvalue(), b'\x00\xff')

        self.assertRaises(OverflowError, x.write_uchar, 256)
        self.assertRaises(OverflowError, x.write_uchar, -1)
        self.assertRaises(TypeError, x.write_uchar, 'f')

    def test_read_char(self):
        x = util.BufferedByteStream(b'\x00\x7f\xff\x80')

        self.assertEqual(x.read_char(), 0)
        self.assertEqual(x.read_char(), 127)
        self.assertEqual(x.read_char(), -1)
        self.assertEqual(x.read_char(), -128)

    def test_write_char(self):
        x = util.BufferedByteStream()

        x.write_char(0)
        x.write_char(-128)
        x.write_char(127)

        self.assertEqual(x.getvalue(), b'\x00\x80\x7f')

        self.assertRaises(OverflowError, x.write_char, 128)
        self.assertRaises(OverflowError, x.write_char, -129)
        self.assertRaises(TypeError, x.write_char, 'f')

    def test_write_ushort(self):
        x = util.BufferedByteStream()

        self._write_endian(x, x.write_ushort, (0,), (b'\x00\x00', b'\x00\x00'))
        self._write_endian(x, x.write_ushort, (12345,), (b'09', b'90'))
        self._write_endian(
            x,
            x.write_ushort,
            (65535,),
            (b'\xff\xff', b'\xff\xff')
        )

        self.assertRaises(OverflowError, x.write_ushort, 65536)
        self.assertRaises(OverflowError, x.write_ushort, -1)
        self.assertRaises(TypeError, x.write_ushort, 'aa')

    def test_read_ushort(self):
        self._read_endian([b'\x00\x00', b'\x00\x00'], 'read_ushort', (), 0)
        self._read_endian(['09', '90'], 'read_ushort', (), 12345)
        self._read_endian([b'\xff\xff', b'\xff\xff'], 'read_ushort', (), 65535)

    def test_write_short(self):
        x = util.BufferedByteStream()

        self._write_endian(
            x,
            x.write_short,
            (-5673,),
            (b'\xe9\xd7', b'\xd7\xe9')
        )
        self._write_endian(
            x, x.write_short,
            (32767,),
            (b'\x7f\xff', b'\xff\x7f')
        )

        self.assertRaises(OverflowError, x.write_ushort, 65537)
        self.assertRaises(OverflowError, x.write_ushort, -1)
        self.assertRaises(TypeError, x.write_short, '\x00\x00')

    def test_read_short(self):
        self._read_endian([b'\xe9\xd7', b'\xd7\xe9'], 'read_short', (), -5673)
        self._read_endian([b'\x7f\xff', b'\xff\x7f'], 'read_short', (), 32767)

    def test_write_ulong(self):
        x = util.BufferedByteStream()

        self._write_endian(
            x,
            x.write_ulong,
            (0,),
            (b'\x00\x00\x00\x00', b'\x00\x00\x00\x00')
        )
        self._write_endian(
            x,
            x.write_ulong,
            (16810049,),
            (b'\x01\x00\x80A', b'A\x80\x00\x01')
        )
        self._write_endian(
            x,
            x.write_ulong,
            (4294967295,),
            (b'\xff\xff\xff\xff', b'\xff\xff\xff\xff')
        )

        self.assertRaises(OverflowError, x.write_ulong, 4294967296)
        self.assertRaises(OverflowError, x.write_ulong, -1)
        self.assertRaises(TypeError, x.write_ulong, '\x00\x00\x00\x00')

    def test_read_ulong(self):
        self._read_endian(
            [b'\x00\x00\x00\x00', b'\x00\x00\x00\x00'],
            'read_ulong',
            (),
            0
        )
        self._read_endian(
            [b'\x01\x00\x80A', b'A\x80\x00\x01'],
            'read_ulong',
            (),
            16810049
        )
        self._read_endian(
            [b'\xff\xff\xff\xff', b'\xff\xff\xff\xff'],
            'read_ulong',
            (),
            4294967295
        )

    def test_write_long(self):
        x = util.BufferedByteStream()

        self._write_endian(
            x,
            x.write_long,
            (0,),
            (b'\x00\x00\x00\x00', b'\x00\x00\x00\x00')
        )
        self._write_endian(
            x,
            x.write_long,
            (16810049,),
            (b'\x01\x00\x80A', b'A\x80\x00\x01')
        )
        self._write_endian(
            x,
            x.write_long,
            (2147483647,),
            (b'\x7f\xff\xff\xff', b'\xff\xff\xff\x7f')
        )
        self._write_endian(
            x,
            x.write_long,
            (-2147483648,),
            (b'\x80\x00\x00\x00', b'\x00\x00\x00\x80')
        )

        self.assertRaises(OverflowError, x.write_long, 2147483648)
        self.assertRaises(OverflowError, x.write_long, -2147483649)
        self.assertRaises(TypeError, x.write_long, '\x00\x00\x00\x00')

    def test_read_long(self):
        self._read_endian(
            [b'\xff\xff\xcf\xc7', b'\xc7\xcf\xff\xff'],
            'read_long',
            (),
            -12345
        )
        self._read_endian(
            [b'\x00\x00\x00\x00', b'\x00\x00\x00\x00'],
            'read_long',
            (),
            0
        )
        self._read_endian(
            [b'\x01\x00\x80A', b'A\x80\x00\x01'],
            'read_long',
            (),
            16810049
        )
        self._read_endian(
            [b'\x7f\xff\xff\xff', b'\xff\xff\xff\x7f'],
            'read_long',
            (),
            2147483647
        )

    def test_write_u24bit(self):
        x = util.BufferedByteStream()

        self._write_endian(
            x,
            x.write_24bit_uint,
            (0,),
            (b'\x00\x00\x00', b'\x00\x00\x00')
        )
        self._write_endian(
            x,
            x.write_24bit_uint,
            (4292609,),
            (b'A\x80\x01', b'\x01\x80A')
        )
        self._write_endian(
            x,
            x.write_24bit_uint,
            (16777215,),
            (b'\xff\xff\xff', b'\xff\xff\xff')
        )

        self.assertRaises(OverflowError, x.write_24bit_uint, 16777216)
        self.assertRaises(OverflowError, x.write_24bit_uint, -1)
        self.assertRaises(TypeError, x.write_24bit_uint, '\x00\x00\x00')

    def test_read_u24bit(self):
        self._read_endian(
            [b'\x00\x00\x00', b'\x00\x00\x00'], 'read_24bit_uint', (), 0
        )
        self._read_endian(
            [b'\x00\x00\x80', b'\x80\x00\x00'], 'read_24bit_uint', (), 128
        )
        self._read_endian(
            [b'\x80\x00\x00', b'\x00\x00\x80'], 'read_24bit_uint', (), 8388608
        )
        self._read_endian(
            [b'\xff\xff\x7f', b'\x7f\xff\xff'], 'read_24bit_uint', (), 16777087
        )
        self._read_endian(
            [b'\x7f\xff\xff', b'\xff\xff\x7f'], 'read_24bit_uint', (), 8388607
        )

    def test_write_24bit(self):
        x = util.BufferedByteStream()

        self._write_endian(
            x, x.write_24bit_int, (0,), (b'\x00\x00\x00', b'\x00\x00\x00')
        )
        self._write_endian(
            x, x.write_24bit_int, (128,), (b'\x00\x00\x80', b'\x80\x00\x00')
        )
        self._write_endian(
            x, x.write_24bit_int, (8388607,), (b'\x7f\xff\xff', b'\xff\xff\x7f')
        )
        self._write_endian(
            x, x.write_24bit_int, (-1,), (b'\xff\xff\xff', b'\xff\xff\xff')
        )
        self._write_endian(
            x, x.write_24bit_int, (-8388608,), (b'\x80\x00\x00', b'\x00\x00\x80')
        )

        self.assertRaises(OverflowError, x.write_24bit_int, 8388608)
        self.assertRaises(OverflowError, x.write_24bit_int, -8388609)
        self.assertRaises(TypeError, x.write_24bit_int, '\x00\x00\x00')

    def test_read_24bit(self):
        self._read_endian(
            [b'\x00\x00\x00', b'\x00\x00\x00'], 'read_24bit_int', (), 0
        )
        self._read_endian(
            [b'\x00\x00\x80', b'\x80\x00\x00'], 'read_24bit_int', (), 128
        )
        self._read_endian(
            [b'\x80\x00\x00', b'\x00\x00\x80'], 'read_24bit_int', (), -8388608
        )
        self._read_endian(
            [b'\xff\xff\x7f', b'\x7f\xff\xff'], 'read_24bit_int', (), -129
        )
        self._read_endian(
            [b'\x7f\xff\xff', b'\xff\xff\x7f'], 'read_24bit_int', (), 8388607
        )

    def test_write_float(self):
        x = util.BufferedByteStream()

        self._write_endian(
            x, x.write_float, (0.2,), (b'>L\xcc\xcd', b'\xcd\xccL>')
        )
        self.assertRaises(TypeError, x.write_float, 'foo')

    def test_read_float(self):
        self._read_endian(
            [b'?\x00\x00\x00', b'\x00\x00\x00?'], 'read_float', (), 0.5
        )

    def test_write_double(self):
        x = util.BufferedByteStream()

        self._write_endian(
            x,
            x.write_double,
            (0.2,),
            (b'?\xc9\x99\x99\x99\x99\x99\x9a', b'\x9a\x99\x99\x99\x99\x99\xc9?')
        )
        self.assertRaises(TypeError, x.write_double, 'foo')

    def test_read_double(self):
        self._read_endian(
            [b'?\xc9\x99\x99\x99\x99\x99\x9a', b'\x9a\x99\x99\x99\x99\x99\xc9?'],
            'read_double',
            (),
            0.2
        )

    def test_write_utf8_string(self):
        x = util.BufferedByteStream()

        self._write_endian(
            x,
            x.write_utf8_string,
            (u'ᚠᛇᚻ',),
            [b'\xe1\x9a\xa0\xe1\x9b\x87\xe1\x9a\xbb'] * 2
        )
        self.assertRaises(TypeError, x.write_utf8_string, 1)
        self.assertRaises(TypeError, x.write_utf8_string, 1.0)
        self.assertRaises(TypeError, x.write_utf8_string, object())
        x.write_utf8_string('\xff')

    def test_read_utf8_string(self):
        self._read_endian(
            [b'\xe1\x9a\xa0\xe1\x9b\x87\xe1\x9a\xbb'] * 2,
            'read_utf8_string',
            (9,),
            u'ᚠᛇᚻ'
        )

    def test_nan(self):
        x = util.BufferedByteStream(b'\xff\xf8\x00\x00\x00\x00\x00\x00')
        self.assertTrue(isNaN(x.read_double()))

        x = util.BufferedByteStream(b'\xff\xf0\x00\x00\x00\x00\x00\x00')
        self.assertTrue(isNegInf(x.read_double()))

        x = util.BufferedByteStream(b'\x7f\xf0\x00\x00\x00\x00\x00\x00')
        self.assertTrue(isPosInf(x.read_double()))

        # now test little endian
        x = util.BufferedByteStream(b'\x00\x00\x00\x00\x00\x00\xf8\xff')
        x.endian = '<'
        self.assertTrue(isNaN(x.read_double()))

        x = util.BufferedByteStream(b'\x00\x00\x00\x00\x00\x00\xf0\xff')
        x.endian = '<'
        self.assertTrue(isNegInf(x.read_double()))

        x = util.BufferedByteStream(b'\x00\x00\x00\x00\x00\x00\xf0\x7f')
        x.endian = '<'
        self.assertTrue(isPosInf(x.read_double()))

    def test_write_infinites(self):
        x = util.BufferedByteStream()

        self._write_endian(x, x.write_double, (NaN,), (
            b'\xff\xf8\x00\x00\x00\x00\x00\x00',
            b'\x00\x00\x00\x00\x00\x00\xf8\xff'
        ))

        self._write_endian(x, x.write_double, (PosInf,), (
            b'\x7f\xf0\x00\x00\x00\x00\x00\x00',
            b'\x00\x00\x00\x00\x00\x00\xf0\x7f'
        ))

        self._write_endian(x, x.write_double, (NegInf,), (
            b'\xff\xf0\x00\x00\x00\x00\x00\x00',
            b'\x00\x00\x00\x00\x00\x00\xf0\xff'
        ))


class BufferedByteStreamTestCase(unittest.TestCase):
    """
    Tests for L{BufferedByteStream<util.BufferedByteStream>}
    """

    def test_create(self):
        x = util.BufferedByteStream()

        self.assertEqual(x.getvalue(), b'')
        self.assertEqual(x.tell(), 0)

        x = util.BufferedByteStream('abc')

        self.assertEqual(x.getvalue(), b'abc')
        self.assertEqual(x.tell(), 0)

    def test_read(self):
        x = util.BufferedByteStream()

        self.assertEqual(x.tell(), 0)
        self.assertEqual(len(x), 0)
        self.assertRaises(IOError, x.read)

        self.assertRaises(IOError, x.read, 10)

        x.write('hello')
        x.seek(0)
        self.assertRaises(IOError, x.read, 10)
        self.assertEqual(x.read(), b'hello')

    def test_read_negative(self):
        """
        @see: #799
        """
        x = util.BufferedByteStream()

        x.write('*' * 6000)
        x.seek(100)
        self.assertRaises(IOError, x.read, -345)

    def test_peek(self):
        x = util.BufferedByteStream('abcdefghijklmnopqrstuvwxyz')

        self.assertEqual(x.tell(), 0)

        self.assertEqual(x.peek(), b'a')
        self.assertEqual(x.peek(5), b'abcde')
        self.assertEqual(x.peek(-1), b'abcdefghijklmnopqrstuvwxyz')

        x.seek(10)
        self.assertEqual(x.peek(50), b'klmnopqrstuvwxyz')

    def test_eof(self):
        x = util.BufferedByteStream()

        self.assertTrue(x.at_eof())
        x.write('hello')
        x.seek(0)
        self.assertFalse(x.at_eof())
        x.seek(0, 2)
        self.assertTrue(x.at_eof())

    def test_remaining(self):
        x = util.BufferedByteStream('spameggs')

        self.assertEqual(x.tell(), 0)
        self.assertEqual(x.remaining(), 8)

        x.seek(2)
        self.assertEqual(x.tell(), 2)
        self.assertEqual(x.remaining(), 6)

    def test_add(self):
        a = util.BufferedByteStream('a')
        b = util.BufferedByteStream('b')

        c = a + b

        self.assertTrue(isinstance(c, util.BufferedByteStream))
        self.assertEqual(c.getvalue(), b'ab')
        self.assertEqual(c.tell(), 0)

    def test_add_pos(self):
        a = util.BufferedByteStream(b'abc')
        b = util.BufferedByteStream(b'def')

        a.seek(1)
        b.seek(0, 2)

        self.assertEqual(a.tell(), 1)
        self.assertEqual(b.tell(), 3)

        self.assertEqual(a.tell(), 1)
        self.assertEqual(b.tell(), 3)

    def test_append_types(self):
        # test non string types
        a = util.BufferedByteStream()

        self.assertRaises(TypeError, a.append, 234234)
        self.assertRaises(TypeError, a.append, 234.0)
        self.assertRaises(TypeError, a.append, 234234)
        self.assertRaises(TypeError, a.append, [])
        self.assertRaises(TypeError, a.append, {})
        self.assertRaises(TypeError, a.append, lambda _: None)
        self.assertRaises(TypeError, a.append, ())
        self.assertRaises(TypeError, a.append, object())

    def test_append_string(self):
        """
        Test L{util.BufferedByteStream.append} with C{str} objects.
        """
        # test empty
        a = util.BufferedByteStream()

        self.assertEqual(a.getvalue(), b'')
        self.assertEqual(a.tell(), 0)
        self.assertEqual(len(a), 0)

        a.append('foo')

        self.assertEqual(a.getvalue(), b'foo')
        self.assertEqual(a.tell(), 0)  # <-- pointer hasn't moved
        self.assertEqual(len(a), 3)

        # test pointer beginning, some data

        a = util.BufferedByteStream('bar')

        self.assertEqual(a.getvalue(), b'bar')
        self.assertEqual(a.tell(), 0)
        self.assertEqual(len(a), 3)

        a.append('gak')

        self.assertEqual(a.getvalue(), b'bargak')
        self.assertEqual(a.tell(), 0)  # <-- pointer hasn't moved
        self.assertEqual(len(a), 6)

        # test pointer middle, some data

        a = util.BufferedByteStream('bar')
        a.seek(2)

        self.assertEqual(a.getvalue(), b'bar')
        self.assertEqual(a.tell(), 2)
        self.assertEqual(len(a), 3)

        a.append('gak')

        self.assertEqual(a.getvalue(), b'bargak')
        self.assertEqual(a.tell(), 2)  # <-- pointer hasn't moved
        self.assertEqual(len(a), 6)

        # test pointer end, some data

        a = util.BufferedByteStream('bar')
        a.seek(0, 2)

        self.assertEqual(a.getvalue(), b'bar')
        self.assertEqual(a.tell(), 3)
        self.assertEqual(len(a), 3)

        a.append('gak')

        self.assertEqual(a.getvalue(), b'bargak')
        self.assertEqual(a.tell(), 3)  # <-- pointer hasn't moved
        self.assertEqual(len(a), 6)

        class Foo(object):
            def getvalue(self):
                return b'foo'

            def __str__(self):
                raise AttributeError()

        a = util.BufferedByteStream()

        self.assertEqual(a.getvalue(), b'')
        self.assertEqual(a.tell(), 0)
        self.assertEqual(len(a), 0)

        a.append(Foo())

        self.assertEqual(a.getvalue(), b'foo')
        self.assertEqual(a.tell(), 0)
        self.assertEqual(len(a), 3)

    def test_append_unicode(self):
        """
        Test L{util.BufferedByteStream.append} with C{unicode} objects.
        """
        # test empty
        a = util.BufferedByteStream()

        self.assertEqual(a.getvalue(), b'')
        self.assertEqual(a.tell(), 0)
        self.assertEqual(len(a), 0)

        a.append('foo')

        self.assertEqual(a.getvalue(), b'foo')
        self.assertEqual(a.tell(), 0)  # <-- pointer hasn't moved
        self.assertEqual(len(a), 3)

        # test pointer beginning, some data

        a = util.BufferedByteStream('bar')

        self.assertEqual(a.getvalue(), b'bar')
        self.assertEqual(a.tell(), 0)
        self.assertEqual(len(a), 3)

        a.append('gak')

        self.assertEqual(a.getvalue(), b'bargak')
        self.assertEqual(a.tell(), 0)  # <-- pointer hasn't moved
        self.assertEqual(len(a), 6)

        # test pointer middle, some data

        a = util.BufferedByteStream('bar')
        a.seek(2)

        self.assertEqual(a.getvalue(), b'bar')
        self.assertEqual(a.tell(), 2)
        self.assertEqual(len(a), 3)

        a.append('gak')

        self.assertEqual(a.getvalue(), b'bargak')
        self.assertEqual(a.tell(), 2)  # <-- pointer hasn't moved
        self.assertEqual(len(a), 6)

        # test pointer end, some data

        a = util.BufferedByteStream('bar')
        a.seek(0, 2)

        self.assertEqual(a.getvalue(), b'bar')
        self.assertEqual(a.tell(), 3)
        self.assertEqual(len(a), 3)

        a.append('gak')

        self.assertEqual(a.getvalue(), b'bargak')
        self.assertEqual(a.tell(), 3)  # <-- pointer hasn't moved
        self.assertEqual(len(a), 6)

        class Foo(object):
            def getvalue(self):
                return u'foo'

            def __str__(self):
                raise AttributeError()

        a = util.BufferedByteStream()

        self.assertEqual(a.getvalue(), b'')
        self.assertEqual(a.tell(), 0)
        self.assertEqual(len(a), 0)

        a.append(Foo())

        self.assertEqual(a.getvalue(), b'foo')
        self.assertEqual(a.tell(), 0)
        self.assertEqual(len(a), 3)


class DummyAlias(pyamf.ClassAlias):
    pass


class AnotherDummyAlias(pyamf.ClassAlias):
    pass


class YADummyAlias(pyamf.ClassAlias):
    pass


class ClassAliasTestCase(unittest.TestCase):
    def setUp(self):
        self.old_aliases = pyamf.ALIAS_TYPES.copy()

    def tearDown(self):
        replace_dict(self.old_aliases, pyamf.ALIAS_TYPES)

    def test_simple(self):
        class A(object):
            pass

        pyamf.register_alias_type(DummyAlias, A)

        self.assertEqual(util.get_class_alias(A), DummyAlias)

    def test_nested(self):
        class A(object):
            pass

        class B(object):
            pass

        class C(object):
            pass

        pyamf.register_alias_type(DummyAlias, A, B, C)

        self.assertEqual(util.get_class_alias(B), DummyAlias)

    def test_multiple(self):
        class A(object):
            pass

        class B(object):
            pass

        class C(object):
            pass

        pyamf.register_alias_type(DummyAlias, A)
        pyamf.register_alias_type(AnotherDummyAlias, B)
        pyamf.register_alias_type(YADummyAlias, C)

        self.assertEqual(util.get_class_alias(B), AnotherDummyAlias)
        self.assertEqual(util.get_class_alias(C), YADummyAlias)
        self.assertEqual(util.get_class_alias(A), DummyAlias)

    def test_none_existant(self):
        self.assertEqual(util.get_class_alias(self.__class__), None)

    def test_subclass(self):
        class A(object):
            pass

        class B(A):
            pass

        pyamf.register_alias_type(DummyAlias, A)

        self.assertEqual(util.get_class_alias(B), DummyAlias)


class IsClassSealedTestCase(unittest.TestCase):
    """
    Tests for L{util.is_class_sealed}
    """

    def test_new_mixed(self):
        class A(object):
            __slots__ = ['foo', 'bar']

        class B(A):
            pass

        class C(B):
            __slots__ = ('spam', 'eggs')

        self.assertTrue(util.is_class_sealed(A))
        self.assertFalse(util.is_class_sealed(B))
        self.assertFalse(util.is_class_sealed(C))

    def test_deep(self):
        class A(object):
            __slots__ = ['foo', 'bar']

        class B(A):
            __slots__ = ('gak',)

        class C(B):
            pass

        self.assertTrue(util.is_class_sealed(A))
        self.assertTrue(util.is_class_sealed(B))
        self.assertFalse(util.is_class_sealed(C))


class GetClassMetaTestCase(unittest.TestCase):
    """
    Tests for L{util.get_class_meta}
    """

    def test_types(self):
        class A:
            pass

        class B(object):
            pass

        for t in ['', u'', 1, 1.0, 1, [], {}, object, object(), A(), B()]:
            self.assertRaises(TypeError, util.get_class_meta, t)

    def test_no_meta(self):
        class A:
            pass

        class B(object):
            pass

        empty = {
            'readonly_attrs': None,
            'static_attrs': None,
            'synonym_attrs': None,
            'proxy_attrs': None,
            'dynamic': None,
            'alias': None,
            'amf3': None,
            'exclude_attrs': None,
            'proxy_attrs': None,
            'external': None
        }

        self.assertEqual(util.get_class_meta(A), empty)
        self.assertEqual(util.get_class_meta(B), empty)

    def test_alias(self):
        class A:
            class __amf__:
                alias = 'foo.bar.Spam'

        class B(object):
            class __amf__:
                alias = 'foo.bar.Spam'

        meta = {
            'readonly_attrs': None,
            'static_attrs': None,
            'synonym_attrs': None,
            'proxy_attrs': None,
            'dynamic': None,
            'alias': 'foo.bar.Spam',
            'amf3': None,
            'proxy_attrs': None,
            'exclude_attrs': None,
            'external': None
        }

        self.assertEqual(util.get_class_meta(A), meta)
        self.assertEqual(util.get_class_meta(B), meta)

    def test_static(self):
        class A:
            class __amf__:
                static = ['foo', 'bar']

        class B(object):
            class __amf__:
                static = ['foo', 'bar']

        meta = {
            'readonly_attrs': None,
            'static_attrs': ['foo', 'bar'],
            'synonym_attrs': None,
            'proxy_attrs': None,
            'dynamic': None,
            'alias': None,
            'amf3': None,
            'exclude_attrs': None,
            'external': None
        }

        self.assertEqual(util.get_class_meta(A), meta)
        self.assertEqual(util.get_class_meta(B), meta)

    def test_exclude(self):
        class A:
            class __amf__:
                exclude = ['foo', 'bar']

        class B(object):
            class __amf__:
                exclude = ['foo', 'bar']

        meta = {
            'readonly_attrs': None,
            'exclude_attrs': ['foo', 'bar'],
            'synonym_attrs': None,
            'proxy_attrs': None,
            'dynamic': None,
            'alias': None,
            'amf3': None,
            'static_attrs': None,
            'proxy_attrs': None,
            'external': None
        }

        self.assertEqual(util.get_class_meta(A), meta)
        self.assertEqual(util.get_class_meta(B), meta)

    def test_readonly(self):
        class A:
            class __amf__:
                readonly = ['foo', 'bar']

        class B(object):
            class __amf__:
                readonly = ['foo', 'bar']

        meta = {
            'exclude_attrs': None,
            'readonly_attrs': ['foo', 'bar'],
            'synonym_attrs': None,
            'proxy_attrs': None,
            'dynamic': None,
            'alias': None,
            'amf3': None,
            'static_attrs': None,
            'external': None,
            'proxy_attrs': None,
        }

        self.assertEqual(util.get_class_meta(A), meta)
        self.assertEqual(util.get_class_meta(B), meta)

    def test_amf3(self):
        class A:
            class __amf__:
                amf3 = True

        class B(object):
            class __amf__:
                amf3 = True

        meta = {
            'exclude_attrs': None,
            'proxy_attrs': None,
            'synonym_attrs': None,
            'readonly_attrs': None,
            'proxy_attrs': None,
            'dynamic': None,
            'alias': None,
            'amf3': True,
            'static_attrs': None,
            'external': None
        }

        self.assertEqual(util.get_class_meta(A), meta)
        self.assertEqual(util.get_class_meta(B), meta)

    def test_dynamic(self):
        class A:
            class __amf__:
                dynamic = False

        class B(object):
            class __amf__:
                dynamic = False

        meta = {
            'exclude_attrs': None,
            'proxy_attrs': None,
            'synonym_attrs': None,
            'readonly_attrs': None,
            'proxy_attrs': None,
            'dynamic': False,
            'alias': None,
            'amf3': None,
            'static_attrs': None,
            'external': None
        }

        self.assertEqual(util.get_class_meta(A), meta)
        self.assertEqual(util.get_class_meta(B), meta)

    def test_external(self):
        class A:
            class __amf__:
                external = True

        class B(object):
            class __amf__:
                external = True

        meta = {
            'exclude_attrs': None,
            'proxy_attrs': None,
            'synonym_attrs': None,
            'readonly_attrs': None,
            'proxy_attrs': None,
            'dynamic': None,
            'alias': None,
            'amf3': None,
            'static_attrs': None,
            'external': True
        }

        self.assertEqual(util.get_class_meta(A), meta)
        self.assertEqual(util.get_class_meta(B), meta)

    def test_dict(self):
        meta = {
            'exclude': ['foo'],
            'readonly': ['bar'],
            'dynamic': False,
            'alias': 'spam.eggs',
            'proxy_attrs': None,
            'synonym_attrs': None,
            'amf3': True,
            'static': ['baz'],
            'external': True
        }

        class A:
            __amf__ = meta

        class B(object):
            __amf__ = meta

        ret = {
            'readonly_attrs': ['bar'],
            'static_attrs': ['baz'],
            'proxy_attrs': None,
            'dynamic': False,
            'alias': 'spam.eggs',
            'amf3': True,
            'exclude_attrs': ['foo'],
            'synonym_attrs': None,
            'proxy_attrs': None,
            'external': True
        }

        self.assertEqual(util.get_class_meta(A), ret)
        self.assertEqual(util.get_class_meta(B), ret)

    def test_proxy(self):
        class A:
            class __amf__:
                proxy = ['foo', 'bar']

        class B(object):
            class __amf__:
                proxy = ['foo', 'bar']

        meta = {
            'exclude_attrs': None,
            'readonly_attrs': None,
            'proxy_attrs': ['foo', 'bar'],
            'synonym_attrs': None,
            'dynamic': None,
            'alias': None,
            'amf3': None,
            'static_attrs': None,
            'external': None
        }

        self.assertEqual(util.get_class_meta(A), meta)
        self.assertEqual(util.get_class_meta(B), meta)

    def test_synonym(self):
        class A:
            class __amf__:
                synonym = {'foo': 'bar'}

        class B(object):
            class __amf__:
                synonym = {'foo': 'bar'}

        meta = {
            'exclude_attrs': None,
            'readonly_attrs': None,
            'proxy_attrs': None,
            'synonym_attrs': {'foo': 'bar'},
            'dynamic': None,
            'alias': None,
            'amf3': None,
            'static_attrs': None,
            'external': None
        }

        self.assertEqual(util.get_class_meta(A), meta)
        self.assertEqual(util.get_class_meta(B), meta)
