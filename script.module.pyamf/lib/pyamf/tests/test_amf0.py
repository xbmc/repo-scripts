# -*- coding: utf-8 -*-
#
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Tests for AMF0 Implementation.

@since: 0.1.0
"""

import unittest
import datetime

import pyamf
from pyamf import amf0, util, xml, python
from pyamf.tests.util import (
    EncoderMixIn, DecoderMixIn, ClassCacheClearingTestCase, Spam, ClassicSpam)


class TypesTestCase(unittest.TestCase):
    """
    Tests the type mappings.
    """

    def test_types(self):
        self.assertEqual(amf0.TYPE_NUMBER, b'\x00')
        self.assertEqual(amf0.TYPE_BOOL, b'\x01')
        self.assertEqual(amf0.TYPE_STRING, b'\x02')
        self.assertEqual(amf0.TYPE_OBJECT, b'\x03')
        self.assertEqual(amf0.TYPE_MOVIECLIP, b'\x04')
        self.assertEqual(amf0.TYPE_NULL, b'\x05')
        self.assertEqual(amf0.TYPE_UNDEFINED, b'\x06')
        self.assertEqual(amf0.TYPE_REFERENCE, b'\x07')
        self.assertEqual(amf0.TYPE_MIXEDARRAY, b'\x08')
        self.assertEqual(amf0.TYPE_OBJECTTERM, b'\x09')
        self.assertEqual(amf0.TYPE_ARRAY, b'\x0a')
        self.assertEqual(amf0.TYPE_DATE, b'\x0b')
        self.assertEqual(amf0.TYPE_LONGSTRING, b'\x0c')
        self.assertEqual(amf0.TYPE_UNSUPPORTED, b'\x0d')
        self.assertEqual(amf0.TYPE_RECORDSET, b'\x0e')
        self.assertEqual(amf0.TYPE_XML, b'\x0f')
        self.assertEqual(amf0.TYPE_TYPEDOBJECT, b'\x10')
        self.assertEqual(amf0.TYPE_AMF3, b'\x11')


class EncoderTestCase(ClassCacheClearingTestCase, EncoderMixIn):
    """
    Tests the output from the AMF0 L{Encoder<pyamf.amf0.Encoder>} class.
    """

    amf_type = pyamf.AMF0

    def setUp(self):
        ClassCacheClearingTestCase.setUp(self)
        EncoderMixIn.setUp(self)

    def test_number(self):
        self.assertEncoded(0, b'\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        self.assertEncoded(0.2, b'\x00\x3f\xc9\x99\x99\x99\x99\x99\x9a')
        self.assertEncoded(1, b'\x00\x3f\xf0\x00\x00\x00\x00\x00\x00')
        self.assertEncoded(42, b'\x00\x40\x45\x00\x00\x00\x00\x00\x00')
        self.assertEncoded(-123, b'\x00\xc0\x5e\xc0\x00\x00\x00\x00\x00')
        self.assertEncoded(1.23456789, b'\x00\x3f\xf3\xc0\xca\x42\x83\xde\x1b')

    def test_boolean(self):
        self.assertEncoded(True, b'\x01\x01')
        self.assertEncoded(False, b'\x01\x00')

    def test_string(self):
        self.assertEncoded('', b'\x02\x00\x00')
        self.assertEncoded('hello', b'\x02\x00\x05hello')
        # unicode taken from http://www.columbia.edu/kermit/utf8.html
        self.assertEncoded(
            u'ᚠᛇᚻ', b'\x02\x00\t\xe1\x9a\xa0\xe1\x9b\x87\xe1\x9a\xbb'
        )

    def test_null(self):
        self.assertEncoded(None, b'\x05')

    def test_undefined(self):
        self.assertEncoded(pyamf.Undefined, b'\x06')

    def test_list(self):
        self.assertEncoded([], b'\x0a\x00\x00\x00\x00')
        self.assertEncoded(
            [1, 2, 3],
            b'\x0a\x00\x00\x00\x03\x00\x3f\xf0\x00\x00\x00\x00\x00\x00\x00\x40'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x40\x08\x00\x00\x00\x00\x00\x00'
        )
        self.assertEncoded(
            (1, 2, 3),
            b'\x0a\x00\x00\x00\x03\x00\x3f\xf0\x00\x00\x00\x00\x00\x00\x00\x40'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x40\x08\x00\x00\x00\x00\x00\x00'
        )

    def test_list_references(self):
        x = []

        self.assertEqual(self.encode(x, x), b'\n\x00\x00\x00\x00\x07\x00\x00')

    def test_longstring(self):
        s = 'a' * 65537

        self.assertEncoded(s, b'\x0c\x00\x01\x00\x01' + s.encode())

    def test_dict(self):
        self.assertEncoded({'a': 'a'}, b'\x03\x00\x01a\x02\x00\x01a\x00\x00\t')

        self.assertEncoded({12: True, 42: "Testing"}, b'\x03', (
            b'\x00\x0242\x02\x00\x07Testing',
            b'\x00\x0212\x01\x01'
        ), b'\x00\x00\t')

    def test_mixed_array(self):
        d = pyamf.MixedArray(a=1, b=2, c=3)

        bytes = (b'\x08\x00\x00\x00\x00', (
            b'\x00\x01a\x00?\xf0\x00\x00\x00\x00\x00\x00',
            b'\x00\x01c\x00@\x08\x00\x00\x00\x00\x00\x00',
            b'\x00\x01b\x00@\x00\x00\x00\x00\x00\x00\x00'
        ), b'\x00\x00\t')

        self.assertEncoded(d, bytes)

        # test the reference
        self.assertEqual(self.encode(d), b'\x07\x00\x00')

    def test_date(self):
        self.assertEncoded(
            datetime.datetime(2005, 3, 18, 1, 58, 31),
            b'\x0bBp+6!\x15\x80\x00\x00\x00'
        )
        self.assertEncoded(
            datetime.date(2003, 12, 1),
            b'\x0bBo%\xe2\xb2\x80\x00\x00\x00\x00'
        )
        self.assertEncoded(
            datetime.datetime(2009, 3, 8, 23, 30, 47, 770122),
            b'\x0bBq\xfe\x86\xca5\xa1\xf4\x00\x00'
        )

        self.assertRaises(pyamf.EncodeError, self.encode, datetime.time(22, 3))

    def test_xml(self):
        blob = b'<a><b>hello world</b></a>'

        self.assertEncoded(
            xml.fromstring(blob),
            b'\x0f\x00\x00\x00\x19' + blob
        )

    def test_xml_references(self):
        blob = b'<a><b>hello world</b></a>'
        x = xml.fromstring(blob)

        self.assertEncoded(
            [x, x],
            b'\n\x00\x00\x00\x02' + (b'\x0f\x00\x00\x00\x19' + blob) * 2
        )

    def test_object(self):
        self.assertEncoded(
            {'a': 'b'},
            b'\x03\x00\x01a\x02\x00\x01b\x00\x00\x09'
        )

    def test_force_amf3(self):
        alias = pyamf.register_class(Spam, 'spam.eggs')
        alias.amf3 = True

        x = Spam()
        x.x = 'y'

        self.assertEncoded(x, b'\x11\n\x0b\x13spam.eggs\x03x\x06\x03y\x01')

    def test_typed_object(self):
        pyamf.register_class(Spam, alias='org.pyamf.spam')

        x = Spam()
        x.baz = 'hello'

        self.assertEncoded(
            x,
            b'\x10\x00\x0eorg.pyamf.spam\x00\x03baz\x02\x00\x05hello\x00\x00\t'
        )

    def test_complex_list(self):
        self.assertEncoded(
            [[1.0]],
            b'\x0a\x00\x00\x00\x01\x0a\x00\x00\x00\x01\x00\x3f\xf0\x00\x00\x00'
            b'\x00\x00\x00'
        )

        self.assertEncoded(
            [['test', 'test', 'test', 'test']],
            b'\x0a\x00\x00\x00\x01\x0a\x00\x00\x00\x04' +
            (b'\x02\x00\x04test' * 4)
        )

        x = {'a': 'spam', 'b': 'eggs'}

        try:
            self.assertEncoded(
                [[x, x]],
                b'\n\x00\x00\x00\x01\n\x00\x00\x00\x02\x03\x00\x01a\x02\x00\x04spam'
                b'\x00\x01b\x02\x00\x04eggs\x00\x00\t\x07\x00\x02'
            )
        except:
            self.assertEncoded(
                [[x, x]],
                b'\n\x00\x00\x00\x01\n\x00\x00\x00\x02\x03\x00\x01b\x02\x00\x04eggs'
                b'\x00\x01a\x02\x00\x04spam\x00\x00\t\x07\x00\x02'
            )

    def test_amf3(self):
        self.encoder.use_amf3 = True

        o = Spam()

        self.assertEncoded(o, b'\x11\n\x0b\x01\x01')

    def test_anonymous(self):
        pyamf.register_class(Spam)

        x = Spam()
        x.spam = 'eggs'
        x.hello = 'world'

        self.assertEncoded(
            x,
            b'\x03',
            (b'\x00\x05hello\x02\x00\x05world', b'\x00\x04spam\x02\x00\x04eggs'),
            b'\x00\x00\t'
        )

    def test_dynamic(self):
        x = Spam()

        x.foo = 'bar'
        x.hello = 'world'

        alias = pyamf.register_class(Spam)

        alias.exclude_attrs = ['foo']

        alias.compile()

        self.assertTrue(alias.dynamic)

        self.assertEncoded(x, b'\x03\x00\x05hello\x02\x00\x05world\x00\x00\t')

    def test_dynamic_static(self):
        x = Spam()

        x.foo = 'bar'
        x.hello = 'world'

        alias = pyamf.register_class(Spam)

        alias.static_attrs = ['hello']
        alias.compile()

        self.assertTrue(alias.dynamic)

        self.assertEncoded(
            x,
            b'\x03',
            (b'\x00\x05hello\x02\x00\x05world', b'\x00\x03foo\x02\x00\x03bar'),
            b'\x00\x00\t'
        )

    def test_dynamic_registered(self):
        x = Spam()

        x.foo = 'bar'
        x.hello = 'world'

        alias = pyamf.register_class(Spam, 'x')

        alias.exclude_attrs = ['foo']

        alias.compile()

        self.assertTrue(alias.dynamic)

        self.assertEncoded(
            x,
            b'\x10\x00\x01x',
            b'\x00\x05hello\x02\x00\x05world',
            b'\x00\x00\t'
        )

    def test_custom_type(self):
        def write_as_list(list_interface_obj, encoder):
            list_interface_obj.ran = True
            self.assertEqual(id(encoder), id(self.encoder))

            return list(list_interface_obj)

        class ListWrapper(object):
            ran = False

            def __iter__(self):
                return iter([1, 2, 3])

        pyamf.add_type(ListWrapper, write_as_list)
        x = ListWrapper()

        self.encoder.writeElement(x)
        self.assertEqual(x.ran, True)

        self.assertEqual(
            self.buf.getvalue(),
            b'\n\x00\x00\x00\x03\x00?\xf0\x00\x00\x00\x00\x00\x00\x00@\x00\x00'
            b'\x00\x00\x00\x00\x00\x00@\x08\x00\x00\x00\x00\x00\x00'
        )

    def test_old_style_classes(self):
        class Person:
            pass

        pyamf.register_class(Person, 'spam.eggs.Person')

        u = Person()
        u.family_name = 'Doe'
        u.given_name = 'Jane'

        self.encoder.writeElement(u)

        self.assertEncoded(u, b'\x10\x00\x10spam.eggs.Person', (
            b'\x00\x0bfamily_name\x02\x00\x03Doe',
            b'\x00\ngiven_name\x02\x00\x04Jane'
        ), b'\x00\x00\t')

    def test_slots(self):
        class Person(object):
            __slots__ = ('family_name', 'given_name')

        u = Person()
        u.family_name = 'Doe'
        u.given_name = 'Jane'

        self.assertEncoded(u, b'\x03', (
            b'\x00\x0bfamily_name\x02\x00\x03Doe',
            b'\x00\ngiven_name\x02\x00\x04Jane'
        ), b'\x00\x00\t')

    def test_slots_registered(self):
        class Person(object):
            __slots__ = ('family_name', 'given_name')

        u = Person()
        u.family_name = 'Doe'
        u.given_name = 'Jane'

        pyamf.register_class(Person, 'spam.eggs.Person')

        self.assertEncoded(u, b'\x10\x00\x10spam.eggs.Person', (
            b'\x00\x0bfamily_name\x02\x00\x03Doe',
            b'\x00\ngiven_name\x02\x00\x04Jane'
        ), b'\x00\x00\t')

    def test_elementtree_tag(self):
        """
        Pretend to look like an ElementTree object to try to fool PyAMF into
        encoding an xml type.
        """
        class NotAnElement(object):
            def items(self):
                return []

            def __iter__(self):
                return iter([])

        foo = NotAnElement()
        foo.tag = 'foo'
        foo.text = 'bar'
        foo.tail = None

        self.assertEncoded(
            foo,
            b'\x03', (
                b'\x00\x04text\x02\x00\x03bar',
                b'\x00\x04tail\x05',
                b'\x00\x03tag\x02\x00\x03foo',
            ),
            b'\x00\x00\t'
        )

    def test_funcs(self):
        def x():
            pass

        for i in (chr, self.assertRaises, lambda x: x, pyamf):
            self.assertRaises(pyamf.EncodeError, self.encoder.writeElement, i)

    def test_external_subclassed_list(self):
        class L(list):
            class __amf__:
                external = True

            def __readamf__(self, o):
                pass

            def __writeamf__(self, o):
                pass

        pyamf.register_class(L, 'a')

        a = L()

        a.append('foo')
        a.append('bar')

        self.assertEncoded(a, b'\x10\x00\x01a\x00\x00\t')

    def test_nonexternal_subclassed_list(self):
        class L(list):
            pass

        pyamf.register_class(L, 'a')

        a = L()

        a.append('foo')
        a.append('bar')

        self.assertEncoded(
            a, b'\n\x00\x00\x00\x02\x02\x00\x03foo\x02\x00\x03bar'
        )

    def test_amf3_xml(self):
        self.encoder.use_amf3 = True
        blob = '<root><sections><section /><section /></sections></root>'

        blob = xml.tostring(xml.fromstring(blob))

        bytes = self.encode(xml.fromstring(blob))

        buf = util.BufferedByteStream(bytes)

        self.assertEqual(buf.read_uchar(), 17)
        self.assertEqual(buf.read_uchar(), 11)
        self.assertEqual(buf.read_uchar() >> 1, buf.remaining())
        self.assertEqual(buf.read(), blob)

    def test_use_amf3(self):
        self.encoder.use_amf3 = True

        x = {'foo': 'bar', 'baz': 'gak'}

        try:
            self.assertEncoded(
                x,
                b'\x11\n\x0b'
                b'\x01\x07foo\x06\x07bar'
                b'\x07baz\x06\x07gak\x01'
            )
        except:
            self.assertEncoded(
                x,
                b'\x11\n\x0b'
                b'\x01\x07baz\x06\x07gak'
                b'\x07foo\x06\x07bar\x01'
            )

    def test_static_attrs(self):
        class Foo(object):
            class __amf__:
                static = ('foo', 'bar')

        pyamf.register_class(Foo)

        x = Foo()
        x.foo = 'baz'
        x.bar = 'gak'

        self.assertEncoded(
            x,
            b'\x03',
            (b'\x00\x03bar\x02\x00\x03gak', b'\x00\x03foo\x02\x00\x03baz'),
            b'\x00\x00\t'
        )

    def test_class(self):
        class Classic:
            pass

        class New(object):
            pass

        with self.assertRaises(pyamf.EncodeError):
            self.encoder.writeElement(Classic)

        with self.assertRaises(pyamf.EncodeError):
            self.encoder.writeElement(New)

    def test_timezone(self):
        d = datetime.datetime(2009, 9, 24, 14, 23, 23)
        self.encoder.timezone_offset = datetime.timedelta(hours=-5)

        self.assertEncoded(d, b'\x0bBr>\xd8\x1f\xff\x80\x00\x00\x00')

    def test_generators(self):
        def foo():
            yield [1, 2, 3]
            yield b'\xff'
            yield pyamf.Undefined

        self.assertEncoded(
            foo(),
            b'\n\x00\x00\x00\x03\x00?\xf0\x00\x00\x00\x00\x00\x00\x00@\x00\x00'
            b'\x00\x00\x00\x00\x00\x00@\x08\x00\x00\x00\x00\x00\x00\x02\x00\x01'
            b'\xff\x06'
        )

    def test_iterate(self):
        self.assertRaises(StopIteration, self.encoder.__next__)

        self.encoder.send('')
        self.encoder.send('hello')
        self.encoder.send(u'ƒøø')

        self.assertEqual(next(self.encoder), b'\x02\x00\x00')
        self.assertEqual(next(self.encoder), b'\x02\x00\x05hello')
        self.assertEqual(
            next(self.encoder),
            b'\x02\x00\x06\xc6\x92\xc3\xb8\xc3\xb8'
        )

        self.assertRaises(StopIteration, self.encoder.__next__)

        self.assertIdentical(iter(self.encoder), self.encoder)
        self.assertEqual(
            self.buf.getvalue(),
            b'\x02\x00\x00\x02\x00\x05hello\x02\x00\x06\xc6\x92\xc3\xb8\xc3\xb8'
        )

    def test_subclassed_tuple(self):
        """
        A subclassed tuple must encode an AMF list.

        @see: #830
        """
        class Foo(tuple):
            pass

        x = Foo([1, 2])

        self.encoder.send(x)

        self.assertEqual(
            next(self.encoder),
            b'\n\x00\x00\x00\x02\x00?\xf0\x00\x00\x00\x00\x00\x00\x00@\x00\x00'
            b'\x00\x00\x00\x00\x00'
        )


class DecoderTestCase(ClassCacheClearingTestCase, DecoderMixIn):
    """
    Tests the output from the AMF0 L{Decoder<pyamf.amf0.Decoder>} class.
    """

    amf_type = pyamf.AMF0

    def setUp(self):
        ClassCacheClearingTestCase.setUp(self)
        DecoderMixIn.setUp(self)

    def test_undefined(self):
        self.assertDecoded(pyamf.Undefined, b'\x06')

    def test_number(self):
        self.assertDecoded(0, b'\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        self.assertDecoded(0.2, b'\x00\x3f\xc9\x99\x99\x99\x99\x99\x9a')
        self.assertDecoded(1, b'\x00\x3f\xf0\x00\x00\x00\x00\x00\x00')
        self.assertDecoded(42, b'\x00\x40\x45\x00\x00\x00\x00\x00\x00')
        self.assertDecoded(-123, b'\x00\xc0\x5e\xc0\x00\x00\x00\x00\x00')
        self.assertDecoded(1.23456789, b'\x00\x3f\xf3\xc0\xca\x42\x83\xde\x1b')

    def test_number_types(self):
        nr_types = [
            (b'\x00\x00\x00\x00\x00\x00\x00\x00\x00', int),
            (b'\x00\x3f\xc9\x99\x99\x99\x99\x99\x9a', float),
            (b'\x00\x3f\xf0\x00\x00\x00\x00\x00\x00', int),
            (b'\x00\x40\x45\x00\x00\x00\x00\x00\x00', int),
            (b'\x00\xc0\x5e\xc0\x00\x00\x00\x00\x00', int),
            (b'\x00\x3f\xf3\xc0\xca\x42\x83\xde\x1b', float),
            (b'\x00\xff\xf8\x00\x00\x00\x00\x00\x00', float),  # nan
            (b'\x00\xff\xf0\x00\x00\x00\x00\x00\x00', float),  # -inf
            (b'\x00\x7f\xf0\x00\x00\x00\x00\x00\x00', float),  # inf
        ]

        for t in nr_types:
            bytes, expected_type = t
            self.buf.truncate()
            self.buf.write(bytes)
            self.buf.seek(0)
            self.assertEqual(type(self.decoder.readElement()), expected_type)

    def test_infinites(self):
        self.buf.truncate()
        self.buf.write(b'\x00\xff\xf8\x00\x00\x00\x00\x00\x00')
        self.buf.seek(0)
        x = self.decoder.readElement()
        self.assertTrue(python.isNaN(x))

        self.buf.truncate()
        self.buf.write(b'\x00\xff\xf0\x00\x00\x00\x00\x00\x00')
        self.buf.seek(0)
        x = self.decoder.readElement()
        self.assertTrue(python.isNegInf(x))

        self.buf.truncate()
        self.buf.write(b'\x00\x7f\xf0\x00\x00\x00\x00\x00\x00')
        self.buf.seek(0)
        x = self.decoder.readElement()
        self.assertTrue(python.isPosInf(x))

    def test_boolean(self):
        self.assertDecoded(True, b'\x01\x01')
        self.assertDecoded(False, b'\x01\x00')

    def test_string(self):
        self.assertDecoded('', b'\x02\x00\x00')
        self.assertDecoded('hello', b'\x02\x00\x05hello')
        self.assertDecoded(
            'ᚠᛇᚻ',
            b'\x02\x00\t\xe1\x9a\xa0\xe1\x9b\x87\xe1\x9a\xbb'
        )

    def test_longstring(self):
        a = 'a' * 65537

        self.assertDecoded(a, b'\x0c\x00\x01\x00\x01' + a.encode())

    def test_null(self):
        self.assertDecoded(None, b'\x05')

    def test_list(self):
        self.assertDecoded([], b'\x0a\x00\x00\x00\x00')
        self.assertDecoded(
            [1, 2, 3],
            b'\x0a\x00\x00\x00\x03\x00\x3f\xf0\x00\x00\x00\x00\x00\x00\x00\x40'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x40\x08\x00\x00\x00\x00\x00\x00'
        )

    def test_dict(self):
        bytes = b'\x08\x00\x00\x00\x00\x00\x01\x61\x02\x00\x01\x61\x00\x00\x09'

        self.assertDecoded({'a': 'a'}, bytes)

        self.buf.write(bytes)
        self.buf.seek(0)
        self.decoder.readElement()

    def test_mixed_array(self):
        bytes = (
            b'\x08\x00\x00\x00\x00\x00\x01a\x00?\xf0\x00\x00\x00\x00\x00\x00'
            b'\x00\x01c\x00@\x08\x00\x00\x00\x00\x00\x00\x00\x01b\x00@\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\t'
        )

        self.assertDecoded(pyamf.MixedArray(a=1, b=2, c=3), bytes)

        self.buf.write(bytes)
        self.buf.seek(0)
        self.decoder.readElement()

    def test_date(self):
        self.assertDecoded(
            datetime.datetime(2005, 3, 18, 1, 58, 31),
            b'\x0bBp+6!\x15\x80\x00\x00\x00'
        )
        self.assertDecoded(
            datetime.datetime(2009, 3, 8, 23, 30, 47, 770122),
            b'\x0bBq\xfe\x86\xca5\xa1\xf4\x00\x00'
        )

    def test_xml(self):
        e = b'<a><b>hello world</b></a>'
        ret = self.decode(b'\x0f\x00\x00\x00\x19' + e)

        self.assertEqual(xml.tostring(ret), e)

    def test_xml_references(self):
        self.buf.truncate(0)
        self.buf.write(
            b'\x0f\x00\x00\x00\x19<a><b>hello world</b></a>\x07\x00\x00'
        )
        self.buf.seek(0)

        self.assertEqual(
            xml.tostring(xml.fromstring('<a><b>hello world</b></a>')),
            xml.tostring(self.decoder.readElement()))

        self.assertEqual(
            xml.tostring(xml.fromstring('<a><b>hello world</b></a>')),
            xml.tostring(self.decoder.readElement()))

    def test_object(self):
        bytes = b'\x03\x00\x01a\x02\x00\x01b\x00\x00\x09'

        self.assertDecoded({'a': 'b'}, bytes)

        self.buf.write(bytes)
        self.buf.seek(0)
        self.decoder.readElement()

    def test_registered_class(self):
        pyamf.register_class(Spam, alias='org.pyamf.spam')

        bytes = (
            b'\x10\x00\x0eorg.pyamf.spam\x00\x03baz\x02\x00\x05hello\x00\x00'
            b'\x09'
        )

        obj = self.decode(bytes)

        self.assertEqual(type(obj), Spam)

        self.assertTrue(hasattr(obj, 'baz'))
        self.assertEqual(obj.baz, 'hello')

    def test_complex_list(self):
        x = datetime.datetime(2007, 11, 3, 8, 7, 37, 437000)

        self.assertDecoded(
            [['test', 'test', 'test', 'test']],
            b'\x0A\x00\x00\x00\x01\x0A\x00\x00\x00\x04\x02\x00\x04\x74\x65\x73'
            b'\x74\x02\x00\x04\x74\x65\x73\x74\x02\x00\x04\x74\x65\x73\x74\x02'
            b'\x00\x04\x74\x65\x73\x74'
        )
        self.assertDecoded(
            [x],
            b'\x0a\x00\x00\x00\x01\x0b\x42\x71\x60\x48\xcf\xed\xd0\x00\x00\x00'
        )
        self.assertDecoded(
            [[{u'a': u'spam', u'b': u'eggs'}, {u'a': u'spam', u'b': u'eggs'}]],
            '\n\x00\x00\x00\x01\n\x00\x00\x00\x02\x08\x00\x00\x00\x00\x00\x01'
            'a\x02\x00\x04spam\x00\x01b\x02\x00\x04eggs\x00\x00\t\x07\x00\x02')
        self.assertDecoded(
            [[1.0]],
            b'\x0A\x00\x00\x00\x01\x0A\x00\x00\x00\x01\x00\x3F\xF0\x00\x00\x00'
            b'\x00\x00\x00'
        )

    def test_amf3(self):
        self.buf.write('\x11\x04\x01')
        self.buf.seek(0)

        self.assertEqual(self.decoder.readElement(), 1)

    def test_dynamic(self):
        class Foo(pyamf.ASObject):
            pass

        x = Foo()

        x.foo = 'bar'

        alias = pyamf.register_class(Foo, 'x')
        alias.exclude_attrs = ['hello']

        self.assertDecoded(
            x,
            b'\x10\x00\x01x\x00\x03foo\x02\x00\x03bar\x00\x05hello\x02\x00\x05w'
            b'orld\x00\x00\t'
        )

    def test_classic_class(self):
        pyamf.register_class(ClassicSpam, 'spam.eggs')

        self.buf.write(
            b'\x10\x00\tspam.eggs\x00\x03foo\x02\x00\x03bar\x00\x00\t'
        )
        self.buf.seek(0)

        foo = self.decoder.readElement()

        self.assertEqual(foo.foo, 'bar')

    def test_not_strict(self):
        self.assertFalse(self.decoder.strict)

        # write a typed object to the stream
        self.buf.write(
            b'\x10\x00\tspam.eggs\x00\x03foo\x02\x00\x03bar\x00\x00\t'
        )
        self.buf.seek(0)

        self.assertFalse('spam.eggs' in pyamf.CLASS_CACHE)

        obj = self.decoder.readElement()

        self.assertTrue(isinstance(obj, pyamf.TypedObject))
        self.assertEqual(obj.alias, 'spam.eggs')
        self.assertEqual(obj, {'foo': 'bar'})

    def test_strict(self):
        self.decoder.strict = True

        self.assertTrue(self.decoder.strict)

        # write a typed object to the stream
        self.buf.write(
            b'\x10\x00\tspam.eggs\x00\x03foo\x02\x00\x03bar\x00\x00\t'
        )
        self.buf.seek(0)

        self.assertFalse('spam.eggs' in pyamf.CLASS_CACHE)

        self.assertRaises(pyamf.UnknownClassAlias, self.decoder.readElement)

    def test_slots(self):
        class Person(object):
            __slots__ = ('family_name', 'given_name')

        self.buf.write(
            b'\x03\x00\x0bfamily_name\x02\x00\x03Doe\x00\ngiven_name\x02\x00'
            b'\x04Jane\x00\x00\t'
        )
        self.buf.seek(0)

        foo = self.decoder.readElement()

        self.assertEqual(foo.family_name, 'Doe')
        self.assertEqual(foo.given_name, 'Jane')

    def test_slots_registered(self):
        class Person(object):
            __slots__ = ('family_name', 'given_name')

        pyamf.register_class(Person, 'spam.eggs.Person')

        self.buf.write(
            b'\x10\x00\x10spam.eggs.Person\x00\x0bfamily_name\x02\x00\x03Doe'
            b'\x00\ngiven_name\x02\x00\x04Jane\x00\x00\t'
        )
        self.buf.seek(0)

        foo = self.decoder.readElement()

        self.assertTrue(isinstance(foo, Person))
        self.assertEqual(foo.family_name, 'Doe')
        self.assertEqual(foo.given_name, 'Jane')

    def test_ioerror_buffer_position(self):
        """
        Test to ensure that if an IOError is raised by `readElement` that
        the original position of the stream is restored.
        """
        bytes = pyamf.encode(u'foo', [1, 2, 3], encoding=pyamf.AMF0).getvalue()

        self.buf.write(bytes[:-1])
        self.buf.seek(0)

        self.decoder.readElement()
        self.assertEqual(self.buf.tell(), 6)

        self.assertRaises(IOError, self.decoder.readElement)
        self.assertEqual(self.buf.tell(), 6)

    def test_timezone(self):
        self.decoder.timezone_offset = datetime.timedelta(hours=-5)

        self.buf.write(b'\x0bBr>\xc6\xf5w\x80\x00\x00\x00')
        self.buf.seek(0)

        f = self.decoder.readElement()

        self.assertEqual(f, datetime.datetime(2009, 9, 24, 9, 23, 23))

    def test_unsupported(self):
        self.assertDecoded(None, b'\x0D')

    def test_bad_reference(self):
        self.assertRaises(pyamf.ReferenceError, self.decode, b'\x07\x00\x03')

    def test_iterate(self):
        self.assertRaises(StopIteration, self.decoder.__next__)

        self.decoder.send(b'\x02\x00\x00')
        self.decoder.send(b'\x02\x00\x05hello')
        self.decoder.send(b'\x02\x00\t\xe1\x9a\xa0\xe1\x9b\x87\xe1\x9a\xbb')

        self.assertEqual(next(self.decoder), '')
        self.assertEqual(next(self.decoder), 'hello')
        self.assertEqual(next(self.decoder), u'\u16a0\u16c7\u16bb')

        self.assertRaises(StopIteration, self.decoder.__next__)

        self.assertIdentical(iter(self.decoder), self.decoder)

    def test_bad_type(self):
        self.assertRaises(pyamf.DecodeError, self.decode, b'\xff')

    def test_kwargs(self):
        """
        Python <= 3 demand that kwargs keys be bytes instead of unicode/string.
        """
        def f(**kwargs):
            self.assertEqual(kwargs, {'a': 'a'})

        kwargs = self.decode('\x03\x00\x01a\x02\x00\x01a\x00\x00\t')

        f(**kwargs)

    def test_numerical_keys_mixed_array(self):
        """
        Numerical keys in L{pyamf.MixedArray} must not cause a KeyError on
        decode.

        @see: #843
        """
        x = pyamf.MixedArray({'10': u'foobar'})

        bytes = pyamf.encode(x, encoding=pyamf.AMF0)

        d = list(pyamf.decode(bytes, encoding=pyamf.AMF0))

        self.assertEqual(d, [{10: u'foobar'}])

    def test_post_process(self):
        """
        Ensure that postprocessing happens when data has been decoded.
        """
        self.executed = False

        post_procs = pyamf.POST_DECODE_PROCESSORS[:]

        def restore_post_procs():
            pyamf.POST_DECODE_PROCESSORS = post_procs

        self.addCleanup(restore_post_procs)
        pyamf.POST_DECODE_PROCESSORS = []

        def postprocess(payload, context):
            self.assertEqual(payload, u'foo')
            self.assertEqual(context, {})

            self.executed = True

            return payload

        pyamf.add_post_decode_processor(postprocess)

        # setup complete
        bytes = pyamf.encode(u'foo', encoding=pyamf.AMF0).getvalue()

        self.decoder.send(bytes)
        ret = next(self.decoder)

        self.assertTrue(self.executed)
        self.assertEqual(ret, u'foo')


class RecordSetTestCase(unittest.TestCase, EncoderMixIn, DecoderMixIn):
    """
    Tests for L{amf0.RecordSet}
    """

    amf_type = pyamf.AMF0
    blob = (
        b'\x10\x00\tRecordSet\x00\nserverInfo\x03', (
            b'\x00\x06cursor\x00?\xf0\x00\x00\x00\x00\x00\x00',
            b'\x00\x0bcolumnNames\n\x00\x00\x00\x03\x02\x00\x01a\x02\x00\x01b'
            b'\x02\x00\x01c',
            b'\x00\x0binitialData\n\x00\x00\x00\x03\n\x00\x00\x00\x03\x00?\xf0'
            b'\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x00\x00'
            b'@\x08\x00\x00\x00\x00\x00\x00\n\x00\x00\x00\x03\x00@\x10\x00'
            b'\x00\x00\x00\x00\x00\x00@\x14\x00\x00\x00\x00\x00\x00\x00@\x18'
            b'\x00\x00\x00\x00\x00\x00\n\x00\x00\x00\x03\x00@\x1c\x00\x00'
            b'\x00\x00\x00\x00\x00@ \x00\x00\x00\x00\x00\x00\x00@"\x00\x00'
            b'\x00\x00\x00\x00',
            b'\x00\x07version\x00?\xf0\x00\x00\x00\x00\x00\x00',
            b'\x00\ntotalCount\x00@\x08\x00\x00\x00\x00\x00\x00'
        ),
        b'\x00\x00\t\x00\x00\t'
    )

    def setUp(self):
        unittest.TestCase.setUp(self)
        EncoderMixIn.setUp(self)
        DecoderMixIn.setUp(self)

    def test_create(self):
        x = amf0.RecordSet()

        self.assertEqual(x.columns, [])
        self.assertEqual(x.items, [])
        self.assertEqual(x.service, None)
        self.assertEqual(x.id, None)

        x = amf0.RecordSet(columns=['spam', 'eggs'], items=[[1, 2]])

        self.assertEqual(x.columns, ['spam', 'eggs'])
        self.assertEqual(x.items, [[1, 2]])
        self.assertEqual(x.service, None)
        self.assertEqual(x.id, None)

        x = amf0.RecordSet(service={}, id=54)

        self.assertEqual(x.columns, [])
        self.assertEqual(x.items, [])
        self.assertEqual(x.service, {})
        self.assertEqual(x.id, 54)

    def test_server_info(self):
        # empty recordset
        x = amf0.RecordSet()

        si = x.serverInfo

        self.assertTrue(isinstance(si, dict))
        self.assertEqual(si.cursor, 1)
        self.assertEqual(si.version, 1)
        self.assertEqual(si.columnNames, [])
        self.assertEqual(si.initialData, [])
        self.assertEqual(si.totalCount, 0)

        try:
            si.serviceName
        except AttributeError:
            pass

        try:
            si.id
        except AttributeError:
            pass

        # basic create
        x = amf0.RecordSet(columns=['a', 'b', 'c'], items=[
            [1, 2, 3], [4, 5, 6], [7, 8, 9]])

        si = x.serverInfo

        self.assertTrue(isinstance(si, dict))
        self.assertEqual(si.cursor, 1)
        self.assertEqual(si.version, 1)
        self.assertEqual(si.columnNames, ['a', 'b', 'c'])
        self.assertEqual(si.initialData, [[1, 2, 3], [4, 5, 6], [7, 8, 9]])
        self.assertEqual(si.totalCount, 3)

        try:
            si.serviceName
        except AttributeError:
            pass

        try:
            si.id
        except AttributeError:
            pass

        # with service & id
        service = {'name': 'baz'}

        x = amf0.RecordSet(
            columns=['spam'], items=[['eggs']], service=service, id='asdfasdf'
        )

        si = x.serverInfo

        self.assertTrue(isinstance(si, dict))
        self.assertEqual(si.cursor, 1)
        self.assertEqual(si.version, 1)
        self.assertEqual(si.columnNames, ['spam'])
        self.assertEqual(si.initialData, [['eggs']])
        self.assertEqual(si.totalCount, 1)
        self.assertEqual(si.serviceName, 'baz')
        self.assertEqual(si.id, 'asdfasdf')

    def test_encode(self):
        self.buf = self.encoder.stream

        x = amf0.RecordSet(columns=['a', 'b', 'c'], items=[
            [1, 2, 3], [4, 5, 6], [7, 8, 9]])

        self.assertEncoded(x, self.blob)

    def test_decode(self):
        self.buf = self.decoder.stream
        x = self.decode(self.blob)

        self.assertTrue(isinstance(x, amf0.RecordSet))
        self.assertEqual(x.columns, ['a', 'b', 'c'])
        self.assertEqual(x.items, [[1, 2, 3], [4, 5, 6], [7, 8, 9]])
        self.assertEqual(x.service, None)
        self.assertEqual(x.id, None)

    def test_repr(self):
        x = amf0.RecordSet(
            columns=['spam'],
            items=[['eggs']],
            service={'name': 'baz'},
            id='asdfasdf',
        )

        self.assertEqual(
            repr(x),
            "<pyamf.amf0.RecordSet id=asdfasdf service={'name': 'baz'} at "
            "0x%x>" % (id(x),)
        )


class ClassInheritanceTestCase(ClassCacheClearingTestCase, EncoderMixIn):

    amf_type = pyamf.AMF0

    def setUp(self):
        # wtf
        ClassCacheClearingTestCase.setUp(self)
        EncoderMixIn.setUp(self)

    def test_simple(self):
        class A(object):
            class __amf__:
                static = ('a')

        class B(A):
            class __amf__:
                static = ('b')

        pyamf.register_class(A, 'A')
        pyamf.register_class(B, 'B')

        x = B()
        x.a = 'spam'
        x.b = 'eggs'

        self.assertEncoded(
            x,
            b'\x10\x00\x01B', (
                b'\x00\x01a\x02\x00\x04spam',
                b'\x00\x01b\x02\x00\x04eggs'
            ),
            b'\x00\x00\t'
        )

    def test_deep(self):
        class A(object):
            class __amf__:
                static = ('a')

        class B(A):
            class __amf__:
                static = ('b')

        class C(B):
            class __amf__:
                static = ('c')

        pyamf.register_class(A, 'A')
        pyamf.register_class(B, 'B')
        pyamf.register_class(C, 'C')

        x = C()
        x.a = 'spam'
        x.b = 'eggs'
        x.c = 'foo'

        self.assertEncoded(
            x,
            b'\x10\x00\x01C', (
                b'\x00\x01a\x02\x00\x04spam',
                b'\x00\x01c\x02\x00\x03foo',
                b'\x00\x01b\x02\x00\x04eggs'
            ),
            b'\x00\x00\t'
        )


class ExceptionEncodingTestCase(ClassCacheClearingTestCase):
    """
    Tests for encoding exceptions.
    """

    def setUp(self):
        ClassCacheClearingTestCase.setUp(self)

        self.buffer = util.BufferedByteStream()
        self.encoder = amf0.Encoder(self.buffer)

    def test_exception(self):
        try:
            raise Exception('foo bar')
        except Exception as e:
            self.encoder.writeElement(e)

        value = self.buffer.getvalue()
        try:
            self.assertEqual(
                value,
                b'\x03\x00\x07message\x02\x00'
                b'\x07foo bar\x00\x04name\x02\x00\t'
                b'Exception\x00\x00\t'
            )
        except AssertionError:
            self.assertEqual(
                value,
                b'\x03\x00\x04name\x02\x00\t'
                b'Exception\x00'
                b'\x07message\x02\x00'
                b'\x07foo bar\x00\x00\t'
            )

    def test_user_defined(self):
        class FooBar(Exception):
            pass

        try:
            raise FooBar('foo bar')
        except Exception as e:
            self.encoder.writeElement(e)

        value = self.buffer.getvalue()
        try:
            self.assertEqual(
                value,
                b'\x03\x00\x07message\x02\x00'
                b'\x07foo bar\x00'
                b'\x04name\x02\x00'
                b'\x06FooBar\x00\x00\t'
            )
        except:
            self.assertEqual(
                value,
                b'\x03\x00\x04name\x02\x00'
                b'\x06FooBar\x00'
                b'\x07message\x02\x00'
                b'\x07foo bar\x00\x00\t'
            )

    def test_typed(self):
        class XYZ(Exception):
            pass

        pyamf.register_class(XYZ, 'foo.bar')

        try:
            raise XYZ('blarg')
        except Exception as e:
            self.encoder.writeElement(e)

        value = self.buffer.getvalue()
        try:
            self.assertEqual(
                value,
                b'\x10\x00\x07foo.bar\x00'
                b'\x07message\x02\x00'
                b'\x05blarg\x00'
                b'\x04name\x02\x00'
                b'\x03XYZ\x00\x00\t'
            )
        except:
            self.assertEqual(
                value,
                b'\x10\x00\x07foo.bar\x00'
                b'\x04name\x02\x00'
                b'\x03XYZ\x00'
                b'\x07message\x02\x00'
                b'\x05blarg\x00\x00\t'
            )


class AMF0ContextTestCase(unittest.TestCase):
    """
    """

    bytes = (
        b'\x00\x03\x00\x02\x00\x0eServiceLicense\x00\x00\x00\x00O\x11\n\x0b'
        b'\x01-serviceConfigurationId\x06\t1234\x15licenseKey\x06Axxxxxxxxxxxxx'
        b'xxxxxxxxxxxxxxxxxxx\x01\x00\tSessionId\x00\x00\x00\x00\xb2\x11\n\x0b'
        b'\x01\x0bToken\x06\x82Iyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy'
        b'yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy'
        b'yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy\x01\x00\x01\x00\x0cR'
        b'egisterUser\x00\x02/3\x00\x00\x01k\n\x00\x00\x00\x07\x11\n#\x01\rform'
        b'at\x0bvalue\x069urn:TribalDDB:identity:email\x06!tester@trial.com\x11'
        b'\n#\x01\x02\ttype\x06\x0fpasswrd\x06Kurn:TribalDDB:authentication:pas'
        b'sword\x11\nS\x01\x19EmailAddress\x15PostalCode\x17DateOfBirth\x11Last'
        b'Name\x13FirstName\x06\x06\x06\x0b12345\n3\x12\x0bmonth\x07day\tyear'
        b'\x04\x04\x04\x0f\x04\x8fF\x06\rewrwer\x06\x07wer\x11\n3\x1fSectionTra'
        b'cking\tCsId\x11TrtmntId\x13LocalCsId\x04\x00\x04\x86\x94z\x04\x00\x11'
        b'\n\x13\x11Tracking\x07CTC\x06\x07555\x11\t\x03\x01\n#\x13UserOptIn'
        b'\x1dliveModeEnable\x05id\x02\x04\x884\x02\x00\x10wwwwwwwwwwwwwwww'
    )

    def test_decode(self):
        from pyamf.remoting import decode

        e = decode(self.bytes)

        a, b, c, d, e, f, g = e['/3'].body

        self.assertEqual(a, {
            'value': u'tester@trial.com',
            'format': u'urn:TribalDDB:identity:email'
        })
        self.assertEqual(b, {
            'type': u'urn:TribalDDB:authentication:password',
            'value': u'passwrd'}
        )
        self.assertEqual(c, {
            'PostalCode': u'12345',
            'DateOfBirth': {'month': 4, 'day': 15, 'year': 1990},
            'EmailAddress': u'tester@trial.com',
            'FirstName': u'wer',
            'LastName': u'ewrwer'}
        )
        self.assertEqual(d, {'CsId': 0, 'TrtmntId': 100986, 'LocalCsId': 0})
        self.assertEqual(e, {'CTC': u'555'})
        self.assertEqual(f, [{'liveModeEnable': False, 'id': 1076}])
        self.assertEqual(g, u'wwwwwwwwwwwwwwww')
