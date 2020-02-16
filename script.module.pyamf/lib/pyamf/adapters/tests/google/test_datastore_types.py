"""
Tests for PyAMF integration with L{google.appengine.api.datastore_types}
"""

import pyamf
from pyamf.adapters.tests import google


if google.has_appengine_sdk():
    from google.appengine.api import datastore_types

    adapter = pyamf.get_adapter('google.appengine.api.datastore_types')


class GeoPtTestCase(google.BaseTestCase):
    """
    Tests for PyAMF integration with L{datastore_types.GeoPt}
    """

    def test_encode(self):
        point = datastore_types.GeoPt(lat=1.23456, lon=-23.9876)

        self.assertEncodes(point, (
            b'\x10\x00*google.appengine.api.datastore_types.GeoPt', (
                b'\x00\x03lat\x00?\xf3\xc0\xc1\xfc\x8f28',
                b'\x00\x03lon\x00\xc07\xfc\xd3Z\x85\x87\x94',
            ),
            b'\x00\x00\t'
        ), encoding=pyamf.AMF0)

        self.assertEncodes(point, (
            b'\n#Ugoogle.appengine.api.datastore_types.GeoPt'
            b'\x07lat\x07lon'
            b'\x05?\xf3\xc0\xc1\xfc\x8f28\x05'
            b'\xc07\xfc\xd3Z\x85\x87\x94'
        ), encoding=pyamf.AMF3)

    def test_decode(self):
        def check_point(ret):
            self.assertIsInstance(ret, datastore_types.GeoPt)
            self.assertEqual(ret.lat, 1.23456)
            self.assertEqual(ret.lon, -23.9876)

        self.assertDecodes(
            b'\x10\x00*google.appengine.api.datastore_types.GeoPt\x00\x03lat'
            b'\x00?\xf3\xc0\xc1\xfc\x8f28\x00\x03lon\x00\xc07\xfc\xd3Z\x85'
            b'\x87\x94\x00\x00\t',
            check_point,
            encoding=pyamf.AMF0
        )

        self.assertDecodes(
            b'\n#Ugoogle.appengine.api.datastore_types.GeoPt'
            b'\x07lat\x07lon'
            b'\x05?\xf3\xc0\xc1\xfc\x8f28\x05'
            b'\xc07\xfc\xd3Z\x85\x87\x94',
            check_point,
            encoding=pyamf.AMF3
        )
