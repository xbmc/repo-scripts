import datetime

from google.appengine.ext import ndb
from google.appengine.ext.ndb import polymodel


def age_calc(self):
    if not self.birth_date:
        return

    age_days = datetime.date(2000, 1, 1) - self.birth_date

    if not age_days.days:
        return

    return age_days.days / 365


class SuperModel(ndb.Model):
    name = ndb.StringProperty()
    height = ndb.FloatProperty()
    birth_date = ndb.DateProperty()
    age_in_2000 = ndb.ComputedProperty(age_calc)
    measurements = ndb.IntegerProperty(repeated=True)


class Pet(ndb.Model):
    """
    All super models have pets .. right!?
    """
    name = ndb.StringProperty()
    model = ndb.KeyProperty(kind=SuperModel)


class SimpleEntity(ndb.Model):
    """Simplest GAE NDB Entity you can get."""


class SuperHero(ndb.Expando):
    name = ndb.StringProperty()
    can_fly = ndb.BooleanProperty()
    slogan = ndb.TextProperty()


class Contact(polymodel.PolyModel):
    phone_number = ndb.StringProperty()
    address = ndb.StringProperty()


class Person(Contact):
    first_name = ndb.StringProperty()
    last_name = ndb.StringProperty()


class Company(Contact):
    name = ndb.StringProperty()


class SPAddress(ndb.Model):
    type = ndb.StringProperty()  # E.g., 'home', 'work'
    street = ndb.StringProperty()
    city = ndb.StringProperty()


class SPContact(ndb.Model):
    name = ndb.StringProperty()
    addresses = ndb.StructuredProperty(SPAddress, repeated=True)


class LSPContact(ndb.Model):
    name = ndb.StringProperty()
    addresses = ndb.LocalStructuredProperty(SPAddress, repeated=True)
