"""
Tests for PyAMF support of google.appengine.ext.ndb
"""

import datetime

import pyamf
from pyamf.adapters.tests import google


if google.has_appengine_sdk():
    from google.appengine.ext import ndb

    from . import _ndb_models as models

    adapter = pyamf.get_adapter('google.appengine.ext.ndb')


class EncodeModelTestCase(google.BaseTestCase):
    """
    Tests for encoding an L{ndb.Model} instance.
    """

    def test_simple(self):
        """
        The simplest encode possible - anonymous class, no properties
        """
        entity = models.SimpleEntity()

        self.assertEncodes(entity, (
            '\x03\x00',
            '\x04_key\x05\x00'
            '\x00\t'
        ), encoding=pyamf.AMF0)

        self.assertEncodes(entity, (
            '\n\x0b'
            '\x01\t_key\x01'
            '\x01'
        ), encoding=pyamf.AMF3)

    def test_simple_named_alias(self):
        """
        Register SimpleEntity as a named class.
        """
        pyamf.register_class(models.SimpleEntity, 'foo.bar')

        entity = models.SimpleEntity()

        self.assertEncodes(entity, (
            b'\x10\x00',
            b'\x07foo.bar',
            b'\x00\x04_key\x05',
            b'\x00\x00\t'
        ), encoding=pyamf.AMF0)

        self.assertEncodes(entity, (
            '\n\x0b\x0ffoo.bar\t_key\x01\x01'
        ), encoding=pyamf.AMF3)

    def test_encode_properties(self):
        """
        An entity with various properties declared should be able to be encoded
        """
        heidi_klum = models.SuperModel(
            # ty wikipedia
            name='Heidi Klum',
            height=1.765,
            birth_date=datetime.date(1973, 6, 1),
            measurements=[1, 2, 3]
        )

        self.assertEncodes(heidi_klum, (
            b'\x03', (
                b'\x00\x04name\x02\x00\nHeidi Klum',
                b'\x00\x04_key\x05',
                b'\x00\x0cmeasurements\n\x00\x00\x00\x03\x00?\xf0\x00\x00\x00',
                b'\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x00\x00@\x08\x00'
                b'\x00\x00\x00\x00\x00',
                b'\x00\x06height\x00?\xfc=p\xa3\xd7\n=',
                b'\x00\nbirth_date\x0bB9\x15\xda$\x00\x00\x00\x00\x00',
                b'\x00\x0bage_in_2000\x00@:\x00\x00\x00\x00\x00\x00',
            ),
            b'\x00\x00\t'
        ), encoding=pyamf.AMF0)

        self.assertEncodes(heidi_klum, (
            b'\n\x0b\x01', (
                b'\t_key\x01',
                b'\tname\x06\x15Heidi Klum',
                b'\x19measurements\t\x07\x01\x04\x01\x04\x02\x04\x03',
                b'\rheight\x05?\xfc=p\xa3\xd7\n=',
                b'\x15birth_date\x08\x01B9\x15\xda$\x00\x00\x00',
                b'\x17age_in_2000\x04\x1a',
            ),
            b'\x01'
        ), encoding=pyamf.AMF3)


class EncodeTestCase(google.BaseTestCase):
    """
    Tests for encoding various ndb related objects.
    """

    def test_key_no_entity(self):
        """
        Attempting to encode an `ndb.Key` that does not have a matching entity
        in the datastore must be `None`.
        """
        key = ndb.Key('SimpleEntity', 'bar')

        self.assertIsNone(key.get())

        self.assertEncodes(key, (
            b'\x05',
        ), encoding=pyamf.AMF0)

        self.assertEncodes(key, (
            b'\x01'
        ), encoding=pyamf.AMF3)

    def test_key_with_entity(self):
        """
        Attempting to encode an `ndb.Key` that DOES have a matching entity
        in the datastore must encode that entity.
        """
        key = ndb.Key('SimpleEntity', 'bar')
        entity = models.SimpleEntity(key=key)

        entity.put()

        self.assertEncodes(key, (
            b'\x03', (
                b'\x00\x04_key\x02\x002agx0ZXN0YmVkLXRlc3RyFQsSDFNpbXBsZUVudGl'
                b'0eSIDYmFyDA'
            ),
            '\x00\x00\t'
        ), encoding=pyamf.AMF0)

        self.assertEncodes(key, (
            '\n\x0b\x01', (
                '\t_key\x06eagx0ZXN0YmVkLXRlc3RyFQsSDFNpbXBsZUVudGl0eSIDYmFyDA'
            ),
            '\x01'
        ), encoding=pyamf.AMF3)

    def test_query(self):
        """
        Encoding a L{ndb.Query} should be returned as a list.
        """
        query = models.SimpleEntity.query()

        self.assertIsInstance(query, ndb.Query)

        self.assertEncodes(query, (
            '\n\x00\x00\x00\x00'
        ), encoding=pyamf.AMF0)

        self.assertEncodes(query, (
            '\t\x01\x01'
        ), encoding=pyamf.AMF3)


class DecodeModelTestCase(google.BaseTestCase):
    """
    """

    def setUp(self):
        super(DecodeModelTestCase, self).setUp()

        pyamf.register_class(models.SuperModel, 'pyamf.SM')

    def test_amf0(self):
        data = (
            b'\x10\x00\x08pyamf.SM\x00\x04_key\x05\x00\x0bage_in_2000\x00@:'
            b'\x00\x00\x00\x00\x00\x00\x00\nbirth_date\x0bB9\x15\xda$\x00\x00'
            b'\x00\x00\x00\x00\x06height\x00?\xfc=p\xa3\xd7\n=\x00\x0cmeasurem'
            b'ents\n\x00\x00\x00\x03\x00?\xf0\x00\x00\x00\x00\x00\x00\x00@\x00'
            b'\x00\x00\x00\x00\x00\x00\x00@\x08\x00\x00\x00\x00\x00\x00\x00\x04'
            b'name\x02\x00\nHeidi Klum\x00\x00\t'
        )

        decoder = pyamf.decode(data, encoding=pyamf.AMF0)

        heidi = decoder.next()

        self.assertEqual(heidi, models.SuperModel(
            birth_date=datetime.date(1973, 6, 1),
            name='Heidi Klum',
            measurements=[1, 2, 3],
            height=1.765
        ))

    def test_amf3(self):
        data = (
            b'\nk\x11pyamf.SM\t_key\x17age_in_2000\x15birth_date\rheight\x19me'
            b'asurements\tname\x01\x04\x1a\x08\x01B9\x15\xda$\x00\x00\x00\x05?'
            b'\xfc=p\xa3\xd7\n=\t\x07\x01\x04\x01\x04\x02\x04\x03\x06\x15Heidi'
            b' Klum\x01'
        )

        decoder = pyamf.decode(data, encoding=pyamf.AMF3)

        heidi = decoder.next()

        self.assertEqual(heidi, models.SuperModel(
            birth_date=datetime.date(1973, 6, 1),
            name='Heidi Klum',
            measurements=[1, 2, 3],
            height=1.765
        ))


class KeyPropertyTestCase(google.BaseTestCase):
    """
    """

    def test_not_set(self):
        """
        .model is None - pyamf must handle the encode and decode cases
        """
        pyamf.register_class(models.Pet, 'pet')
        key = ndb.Key('Pet', 'foobar')
        pet = models.Pet(key=key)

        pet.put()

        self.assertIsNone(pet.model)

        bytes = (
            b'\n\x0b\x07pet', (
                b'\t_key\x06Uagx0ZXN0YmVkLXRlc3RyDwsSA1BldCIGZm9vYmFyDA',
                b'\x0bmodel\x01',
                b'\tname\x01',
            ),
            b'\x01'
        )

        self.assertEncodes(pet, bytes)
        self.assertDecodes(bytes, pet)

    def test_but_missing(self):
        """
        .model is set to a key but the entity does not exist - pyamf must
        handle the encode and decode cases.
        """
        pyamf.register_class(models.Pet, 'pet')
        pyamf.register_class(models.SuperModel, 'supermodel')

        pet_key = ndb.Key('Pet', 'foobar')
        model_key = ndb.Key('SuperModel', 'barfoo')

        self.assertIsNone(model_key.get())

        pet = models.Pet(key=pet_key, model=model_key)

        pet.put()

        bytes = (
            b'\n\x0b\x07pet', (
                b'\t_key\x06Uagx0ZXN0YmVkLXRlc3RyDwsSA1BldCIGZm9vYmFyDA',
                b'\x0bmodel\x06gagx0ZXN0YmVkLXRlc3RyFgsSClN1cGVyTW9kZWwiBmJhcm'
                b'Zvbww',
                b'\tname\x01',
            ),
            b'\x01'
        )

        self.assertEncodes(pet, bytes)
        self.assertDecodes(bytes, pet)


class ExpandoTestCase(google.BaseTestCase):
    """
    Tests for expando entities.
    """

    def test_expando(self):
        pyamf.register_class(models.SuperHero, 'SH')
        superman = models.SuperHero(name='Clark Kent', can_fly=True)

        superman.has_cape = True

        bytes = (
            b'\n\x0b\x05SH', (
                b'\x0fcan_fly\x03',
                b'\rslogan\x01',
                b'\tname\x06\x15Clark Kent',
                b'\x11has_cape\x03',
                b'\t_key\x01',
            ),
            b'\x01'
        )

        self.assertEncodes(superman, bytes)

        def check_superman(ret):
            self.assertIsInstance(ret, models.SuperHero)
            self.assertEqual(ret, superman)
            self.assertTrue(ret.has_cape)

        self.assertDecodes(bytes, check_superman)


class PolymodelTestCase(google.BaseTestCase):
    """
    Tests for polymodel entitities.
    """

    def test_person(self):
        pyamf.register_class(models.Person, 'Person')

        person_key = ndb.Key('Contact', 'p')
        person = models.Person(
            key=person_key,
            first_name='Foo',
            last_name='Bar',
        )

        bytes = (
            b'\n\x0b\rPerson', (
                b'\t_key\x06Qagx0ZXN0YmVkLXRlc3RyDgsSB0NvbnRhY3QiAXAM',
                b'\x19phone_number\x01',
                b'\x0faddress\x01',
                b'\x15first_name\x06\x07Foo',
                b'\x13last_name\x06\x07Bar',
            ),
            b'\x01'
        )

        self.assertEncodes(person, bytes)

        def check_person(ret):
            self.assertIsInstance(ret, models.Person)
            self.assertEqual(ret, person)

        self.assertDecodes(bytes, check_person)

    def test_company(self):
        pyamf.register_class(models.Company, 'Company')

        company_key = ndb.Key('Contact', 'c')

        company = models.Company(
            key=company_key,
            name='Acme Ltd',
        )

        bytes = (
            b'\n\x0b\x0fCompany', (
                b'\t_key\x06Qagx0ZXN0YmVkLXRlc3RyDgsSB0NvbnRhY3QiAWMM',
                b'\x19phone_number\x01',
                b'\x0faddress\x01',
                b'\tname\x06\x11Acme Ltd',
            ),
            b'\x01'
        )

        self.assertEncodes(company, bytes)

        def check_company(ret):
            self.assertIsInstance(ret, models.Company)
            self.assertEqual(ret, company)

        self.assertDecodes(bytes, check_company)


class StructuredTestCase(google.BaseTestCase):
    """
    Tests for structured properties
    """

    def test_structured(self):
        pyamf.register_class(models.SPContact, 'SPContact')
        pyamf.register_class(models.SPAddress, 'SPAddress')

        guido_key = ndb.Key('SPContact', 'guido')
        guido = models.SPContact(
            key=guido_key,
            name='Guido',
            addresses=[
                models.SPAddress(
                    type='home',
                    city='Amsterdam'
                ),
                models.SPAddress(
                    type='work',
                    street='Spear St',
                    city='SF'
                )
            ]
        )

        guido.put()

        bytes = (
            b'\n\x0b\x13SPContact\t_key\x06aagx0ZXN0YmVkLXRlc3RyFAsSCVNQQ29udG'
            b'FjdCIFZ3VpZG8M\x13addresses\t\x05\x01\n\x0b\x13SPAddress\x02\x01'
            b'\tcity\x06\x13Amsterdam\rstreet\x01\ttype\x06\thome\x01\n\x05'
            b'\x02\x01\n\x06\x05SF\x0e\x06\x11Spear St\x10\x06\twork\x01\tname'
            b'\x06\x0bGuido\x01'
        )

        self.assertEncodes(guido, bytes)

        def check_guido(ret):
            self.assertIsInstance(ret, models.SPContact)
            self.assertEqual(ret.key, guido_key)
            self.assertEqual(ret, guido)

            self.assertEqual(guido.addresses, ret.addresses)

        self.assertDecodes(bytes, check_guido)


class LocalStructuredPropertyTestCase(google.BaseTestCase):
    """
    Test for local structured properties
    """

    def test_localstructured(self):
        pyamf.register_class(models.LSPContact, 'LSPContact')
        pyamf.register_class(models.SPAddress, 'SPAddress')

        guido_key = ndb.Key('LSPContact', 'guido')
        guido = models.LSPContact(
            key=guido_key,
            name='Guido',
            addresses=[
                models.SPAddress(
                    type='home',
                    city='Amsterdam'
                ),
                models.SPAddress(
                    type='work',
                    street='Spear St',
                    city='SF'
                )
            ]
        )

        guido.put()

        bytes = (
            b'\n\x0b\x15LSPContact\t_key\x06eagx0ZXN0YmVkLXRlc3RyFQsSCkxTUENv'
            b'bnRhY3QiBWd1aWRvDA\x13addresses\t\x05\x01\n\x0b\x13SPAddress\tc'
            b'ity\x06\x13Amsterdam\x02\x01\rstreet\x01\ttype\x06\thome\x01\n'
            b'\x05\n\x06\x05SF\x02\x01\x0e\x06\x11Spear St\x10\x06\twork\x01\t'
            b'name\x06\x0bGuido\x01'
        )

        self.assertEncodes(guido, bytes)

        def check_guido(ret):
            self.assertIsInstance(ret, models.LSPContact)
            self.assertEqual(ret.key, guido_key)
            self.assertEqual(ret, guido)

            self.assertEqual(guido.addresses, ret.addresses)

        self.assertDecodes(bytes, check_guido)
