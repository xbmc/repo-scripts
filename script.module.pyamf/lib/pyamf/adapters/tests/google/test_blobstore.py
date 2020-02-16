# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
PyAMF tests for google.appengine.ext.blobstore.
"""

import datetime

import pyamf

from pyamf.adapters.tests import google

if google.has_appengine_sdk():
    from google.appengine.ext import blobstore

    adapter = pyamf.get_adapter('google.appengine.ext.blobstore')


class BlobStoreTestCase(google.BaseTestCase):
    """
    Tests for L{blobstore}
    """

    bytes = (
        '\n\x0bOgoogle.appengine.ext.blobstore.BlobInfo', (
            '\tsize\x04\xcb\xad\x07',
            '\x11creation\x08\x01Br\x9c\x1d\xbeh\x80\x00',
            '\x07key\x06\rfoobar',
            '\x19content_type\x06\x15text/plain',
            '\x11filename\x06\x1fnot-telling.ogg'
        ), '\x01')

    values = {
        'content_type': 'text/plain',
        'size': 1234567,
        'filename': 'not-telling.ogg',
        'creation': datetime.datetime(2010, 7, 11, 14, 15, 1)
    }

    def setUp(self):
        super(BlobStoreTestCase, self).setUp()

        self.key = blobstore.BlobKey('foobar')
        self.info = blobstore.BlobInfo(self.key, self.values)

    def test_class_alias(self):
        alias_klass = pyamf.get_class_alias(blobstore.BlobInfo)

        self.assertIdentical(
            alias_klass.__class__,
            adapter.BlobInfoClassAlias
        )

    def test_encode(self):
        self.assertEncodes(self.info, self.bytes)

    def test_decode(self):
        def check(ret):
            self.assertEqual(ret.key(), self.key)

        self.assertDecodes(self.bytes, check)
