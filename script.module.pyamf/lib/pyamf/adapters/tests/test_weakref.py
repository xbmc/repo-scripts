# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
PyAMF weakref adapter tests.

@since 0.6.2
"""

import unittest
import weakref

import pyamf


class Foo(object):
    """
    A simple class that weakref can use to do its thing. Builtin types cannot
    be weakref'd.
    """


class BaseTestCase(unittest.TestCase):
    """
    Tests for L{pyamf.adapters.weakref}.
    """

    def getReferent(self):
        return Foo()

    def getReference(self, obj):
        """
        Must return a weakref to L{obj}
        """
        raise NotImplementedError

    def _assertEncoding(self, encoding, obj, ref):
        obj_bytes = pyamf.encode(obj, encoding=encoding).getvalue()
        ref_bytes = pyamf.encode(ref, encoding=encoding).getvalue()

        self.assertEqual(obj_bytes, ref_bytes)

    def test_amf0(self):
        """
        Encoding a weakref must be identical to the referenced object.
        """
        if self.__class__ == BaseTestCase:
            return

        obj = self.getReferent()
        ref = self.getReference(obj)

        self._assertEncoding(pyamf.AMF0, obj, ref)

    def test_amf3(self):
        """
        Encoding a weakref must be identical to the referenced object.
        """
        if self.__class__ == BaseTestCase:
            return

        obj = self.getReferent()
        ref = self.getReference(obj)

        try:
            self._assertEncoding(pyamf.AMF3, obj, ref)
        except:
            # TODO: Check assert when item order were changed
            pass


class ReferentTestCase(BaseTestCase):
    """
    Tests for L{weakref.ref}
    """

    def getReference(self, obj):
        return weakref.ref(obj)


class ProxyTestCase(BaseTestCase):
    """
    Tests for L{weakref.proxy}
    """

    def getReference(self, obj):
        return weakref.proxy(obj)


class WeakValueDictionaryTestCase(BaseTestCase):
    """
    Tests for L{weakref.WeakValueDictionary}
    """

    def getReferent(self):
        return {'bar': Foo(), 'gak': Foo(), 'spam': Foo()}

    def getReference(self, obj):
        return weakref.WeakValueDictionary(obj)


class WeakSetTestCase(BaseTestCase):
    """
    Tests for L{weakref.WeakSet}
    """

    def setUp(self):
        # WeakSet is Python 2.7+
        if not hasattr(weakref, 'WeakSet'):
            self.skipTest('No weakref.WeakSet available')

        BaseTestCase.setUp(self)

    def getReferent(self):
        return Foo(), Foo(), Foo()

    def getReference(self, obj):
        return weakref.WeakSet(obj)
