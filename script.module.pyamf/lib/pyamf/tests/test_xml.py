# -*- coding: utf-8 -*-
#
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Tests for XML library integration

@since: 0.4
"""

import unittest

import pyamf.xml
from pyamf import util

import defusedxml


class _BaseTestCase(unittest.TestCase):
    """
    :ivar mod: The concrete xml module that will be used for this test.
    """

    def setUp(self):
        try:
            self.etree = util.get_module(self.mod)
        except ImportError:
            self.skipTest('%r is not available' % (self.mod,))

        previous_etree = pyamf.set_default_etree(self.etree)

        if previous_etree:
            self.addCleanup(lambda: pyamf.set_default_etree(previous_etree))

    @classmethod
    def cls_factory(cls, mod):
        mod_name = mod.replace('.', '_')

        new_cls = type('%s_%s' % (cls.__name__, mod_name), (cls,), {})

        new_cls.mod = mod

        return new_cls

    def check_amf0(self, bytes, xml):
        b = util.BufferedByteStream(bytes)

        self.assertEqual(b.read_char(), 15)

        l = b.read_ulong()

        self.assertEqual(l, b.remaining())
        self.assertEqual(b.read(), xml)

    def check_amf3(self, bytes, xml):
        b = util.BufferedByteStream(bytes)

        self.assertEqual(b.read_char(), 11)

        l = b.read_uchar()

        self.assertEqual(l >> 1, b.remaining())
        self.assertEqual(b.read(), xml)

    def fromstring(self, xml, **kwargs):
        return pyamf.xml.fromstring(xml, **kwargs)

    def tostring(self, element):
        return self.etree.tostring(element)


class ElementTreeTestCase(_BaseTestCase):
    """
    Tests the type mappings.
    """

    xml = '<foo bar="baz" />'

    def test_elementtree(self):
        element = self.fromstring(self.xml)
        xml = self.tostring(element)

        bytes = pyamf.encode(element, encoding=pyamf.AMF0).getvalue()
        self.check_amf0(bytes, xml)

        new_element = next(pyamf.decode(bytes, encoding=pyamf.AMF0))
        self.assertIdentical(type(element), type(new_element))

        bytes = pyamf.encode(element, encoding=pyamf.AMF3).getvalue()
        self.check_amf3(bytes, xml)

        new_element = next(pyamf.decode(bytes, encoding=pyamf.AMF3))
        self.assertIdentical(type(element), type(new_element))


class XXETestCaseTestCase(_BaseTestCase):
    """
    See http://codewhitesec.blogspot.fr/2015/08/cve-2015-3269-apache-flex-
    blazeds-xxe.html

    DTD processing can inadvertently change the payload that is provided to
    the application.

    :see: https://www.owasp.org/index.php/XML_External_Entity_(XXE)_
        Processing
    """

    def test_system_entity(self):
        """
        Ensure that any SYSTEM entities fail by default
        """
        xml = """
<!DOCTYPE x [ <!ENTITY foo SYSTEM "file:///etc/group"> ]>
<x>External entity 1: &foo;</x>
"""

        with self.assertRaises(defusedxml.EntitiesForbidden):
            self.fromstring(xml.strip(), forbid_dtd=False)

    def test_param_entity(self):
        """
        Ensure that any xml params that are decdoed into SYSTEM entities fail.
        """
        xml = """
<!DOCTYPE x [ <!ENTITY % foo SYSTEM "file:///etc/group"> %foo; ]>
<x>Parameter entity 1</x>
"""
        with self.assertRaises(defusedxml.EntitiesForbidden):
            self.fromstring(xml.strip(), forbid_dtd=False)

    def test_dtd(self):
        """
        Any DTD urls must fail by default.
        """
        xml = '<!DOCTYPE x SYSTEM "file:///etc/group"><x>Remote DTD 1</x>'

        with self.assertRaises(defusedxml.DTDForbidden):
            self.fromstring(xml.strip())


"""
This chunk of code turns any subclass of _BaseTestCase in to a set of test
cases that have a python xml lib module attached to them. This allows the test
writer to write the test once and ensure that it works for all the supported
xml modules.
"""
for name, value in list(globals().copy().items()):
    try:
        is_subclass = issubclass(value, _BaseTestCase)
    except TypeError:
        is_subclass = False

    if not is_subclass:
        continue

    if value is _BaseTestCase:
        continue

    for mod in pyamf.xml.ETREE_MODULES:
        mod_test_class = value.cls_factory(mod)
        globals()[mod_test_class.__name__] = mod_test_class

    del mod, mod_test_class

    globals().pop(name)

del name, value, is_subclass
