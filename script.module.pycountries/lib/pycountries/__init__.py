# vim:fileencoding=utf-8
"""pycountry 17.5.14b"""

import os.path
import pycountries.db
import xbmc, xbmcgui, xbmcplugin, xbmcvfs, xbmcaddon

# Plugin Info
ADDON_ID      = 'script.module.pycountries'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path').decode('utf-8')
LOCALES_DIR  =  xbmc.translatePath(os.path.join(ADDON_PATH, 'lib', 'pycountries', 'locales'))
DATABASE_DIR =  xbmc.translatePath(os.path.join(ADDON_PATH, 'lib', 'pycountries', 'databases'))

class ExistingCountries(pycountries.db.Database):
    """Provides access to an ISO 3166 database (Countries)."""

    data_class_name = 'Country'
    root_key = '3166-1'


class HistoricCountries(pycountries.db.Database):
    """Provides access to an ISO 3166-3 database
    (Countries that have been removed from the standard)."""

    # These fields are computed in a case-by-base basis
    # `alpha_2` is not set in ISO-3166-3, so, we extract it from `alpha4`

    data_class_name = 'Country'
    root_key = '3166-3'


class Scripts(pycountries.db.Database):
    """Provides access to an ISO 15924 database (Scripts)."""

    data_class_name = 'Script'
    root_key = '15924'


class Currencies(pycountries.db.Database):
    """Provides access to an ISO 4217 database (Currencies)."""

    data_class_name = 'Currency'
    root_key = '4217'


class Languages(pycountries.db.Database):
    """Provides access to an ISO 639-1/2T/3 database (Languages)."""

    no_index = ['status', 'scope', 'type', 'inverted_name', 'common_name']
    data_class_name = 'Language'
    root_key = '639-3'


class Subdivision(pycountries.db.Data):

    def __init__(self, **kw):
        if 'parent' in kw:
            kw['parent_code'] = kw['parent']
        else:
            kw['parent_code'] = None
        super(Subdivision, self).__init__(**kw)
        self.country_code = self.code.split('-')[0]
        if self.parent_code is not None:
            self.parent_code = '%s-%s' % (self.country_code, self.parent_code)

    @property
    def country(self):
        return countries.get(alpha_2=self.country_code)

    @property
    def parent(self):
        if not self.parent_code:
            return None
        return subdivisions.get(code=self.parent_code)


class Subdivisions(pycountries.db.Database):

    # Note: subdivisions can be hierarchical to other subdivisions. The
    # parent_code attribute is related to other subdivisons, *not*
    # the country!

    data_class_base = Subdivision
    data_class_name = 'Subdivision'
    no_index = ['name', 'parent_code', 'parent', 'type']
    root_key = '3166-2'

    def _load(self, *args, **kw):
        super(Subdivisions, self)._load(*args, **kw)

        # Add index for the country code.
        self.indices['country_code'] = {}
        for subdivision in self:
            divs = self.indices['country_code'].setdefault(
                subdivision.country_code, set())
            divs.add(subdivision)

    def get(self, **kw):
        try:
            return super(Subdivisions, self).get(**kw)
        except KeyError:
            if 'country_code' in kw:
                # This propagates a KeyError if the country does not exists
                # and returns an empty list if it exists but we it does not
                # have (or we do not know) any sub-divisions.
                countries.get(alpha_2=kw['country_code'])
                return []


countries = ExistingCountries(os.path.join(DATABASE_DIR, 'iso3166-1.json'))
historic_countries = HistoricCountries(
    os.path.join(DATABASE_DIR, 'iso3166-3.json'))
scripts = Scripts(os.path.join(DATABASE_DIR, 'iso15924.json'))
currencies = Currencies(os.path.join(DATABASE_DIR, 'iso4217.json'))
languages = Languages(os.path.join(DATABASE_DIR, 'iso639-3.json'))
subdivisions = Subdivisions(os.path.join(DATABASE_DIR, 'iso3166-2.json'))
