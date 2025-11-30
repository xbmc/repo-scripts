# -*- coding: utf-8 -*-
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

from __future__ import unicode_literals

import time

import xbmc

from .gismeteo import GismeteoError, GismeteoClient
from .simpleweather import Weather as SW_Weather
from .simpleweather import WeatherProperties, Addon, WebClient, WebClientError

__all__ = ['GismeteoError', 'Gismeteo', 'WebClientError',
           'Location', 'Weather']


class Gismeteo(GismeteoClient):

    def __init__(self, *args, **kwargs):
        super(Gismeteo, self).__init__(*args, **kwargs)

        addon = Addon()

        headers = self._client.headers
        if addon.kodi_major_version() >= '17':
            headers['User-Agent'] = xbmc.getUserAgent()

        self._client = WebClient(headers)


class Weather(SW_Weather, WeatherProperties):

    def __init__(self, *args, **kwargs):

        super(Weather, self).__init__(*args, **kwargs)

        self.TEMPUNIT = self.tempunit
        self.SPEEDUNIT = self.speedunit
        self.DATEFORMAT = self.date_format
        self.TIMEFORMAT = self.time_format
        self.PRESUNIT = ['mmHg', 'hPa', 'mbar', 'inHg'][self.get_setting('PresUnit')]
        self.PRECIPUNIT = ['mm', 'inch'][self.get_setting('PrecipUnit')]
        self.TIME_ZONE = self.get_setting('TimeZone')
        self.WEEKENDS = self._weekends()

        self.LANG = self._lang()
        self.WEATHER_CODES = self._weather_codes()
        self.WIND_DIRECTIONS = self.wind_directions()
        self.MONTH_NAME_LONG = self.month_name_long()
        self.MONTH_NAME_SHORT = self.month_name_short()
        self.WEEK_DAY_LONG = self.week_day_long()
        self.WEEK_DAY_SHORT = self.week_day_short()
        self.KODILANGUAGE = xbmc.getLanguage().lower()

        iconpack_installed = xbmc.getCondVisibility('System.HasAddon(resource.images.weatherprovidericons.gismeteo)')
        self.use_provider_icon = self.get_setting('UseProviderIcons') and iconpack_installed

    def gismeteo_lang(self):

        lang_id = self.get_setting('Language')
        if lang_id == 0:  # System interface
            lang = self.LANG[self.KODILANGUAGE] or 'en'
        elif lang_id == 1:
            lang = 'ru'
        elif lang_id == 2:
            lang = 'ua'
        elif lang_id == 3:
            lang = 'lt'
        elif lang_id == 4:
            lang = 'lv'
        elif lang_id == 5:
            lang = 'en'
        elif lang_id == 6:
            lang = 'ro'
        elif lang_id == 7:
            lang = 'de'
        elif lang_id == 8:
            lang = 'pl'
        else:
            lang = 'en'

        return lang

    def get_weather_code(self, item):

        return self.WEATHER_CODES.get(item['icon'], 'na')

    def get_wind_direction(self, value):
        wind_direction_code = self.WIND_DIRECTIONS.get(value)

        if wind_direction_code is not None:
            return xbmc.getLocalizedString(wind_direction_code)
        elif value == '0':
            return self.gettext('calm')
        else:
            return self.gettext('n/a')

    def get_time(self, date):
        date_time = self._get_timestamp(date)

        if self.TIMEFORMAT != '/':
            local_time = time.strftime('%I:%M%p', date_time)
        else:
            local_time = time.strftime('%H:%M', date_time)

        return local_time

    def convert_date(self, date):
        date_time = self._get_timestamp(date)

        if self.DATEFORMAT[1] == 'd' or self.DATEFORMAT[0] == 'D':
            localdate = time.strftime('%d-%m-%Y', date_time)
        elif self.DATEFORMAT[1] == 'm' or self.DATEFORMAT[0] == 'M':
            localdate = time.strftime('%m-%d-%Y', date_time)
        else:
            localdate = time.strftime('%Y-%m-%d', date_time)
        if self.TIMEFORMAT != '/':
            localtime = time.strftime('%I:%M%p', date_time)
        else:
            localtime = time.strftime('%H:%M', date_time)

        return localtime + '  ' + localdate

    def is_weekend(self, day):
        return self.get_weekday(day['date'], 'x') in self.WEEKENDS

    def get_weekday(self, date, form):
        date_time = self._get_timestamp(date)

        weekday = time.strftime('%w', date_time)
        if form == 's':
            return xbmc.getLocalizedString(self.WEEK_DAY_SHORT[weekday])
        elif form == 'l':
            return xbmc.getLocalizedString(self.WEEK_DAY_LONG[weekday])
        else:
            return int(weekday)

    def get_month(self, date, form):
        date_time = self._get_timestamp(date)

        month = time.strftime('%m', date_time)
        day = time.strftime('%d', date_time)
        if form == 'ds':
            label = day + ' ' + xbmc.getLocalizedString(self.MONTH_NAME_SHORT[month])
        elif form == 'dl':
            label = day + ' ' + xbmc.getLocalizedString(self.MONTH_NAME_LONG[month])
        elif form == 'ms':
            label = xbmc.getLocalizedString(self.MONTH_NAME_SHORT[month]) + ' ' + day
        elif form == 'ml':
            label = xbmc.getLocalizedString(self.MONTH_NAME_LONG[month]) + ' ' + day
        else:
            label = ''

        return label

    def _weekends(self):
        weekend = self.get_setting('Weekend')

        if weekend == 2:
            weekends = [4, 5]
        elif weekend == 1:
            weekends = [5, 6]
        else:
            weekends = [6, 0]

        return weekends

    @staticmethod
    def _lang():

        return {  # kodi lang name          # gismeteo code
                'afrikaans':             '',
                'albanian':              '',
                'amharic':               '',
                'arabic':                '',
                'armenian':              '',
                'azerbaijani':           '',
                'basque':                '',
                'belarusian':            'ru',
                'bosnian':               '',
                'bulgarian':             '',
                'burmese':               '',
                'catalan':               '',
                'chinese (simple)':      '',
                'chinese (traditional)': '',
                'croatian':              '',
                'czech':                 '',
                'danish':                '',
                'dutch':                 '',
                'english':               'en',
                'english (us)':          'en',
                'english (australia)':   'en',
                'english (new zealand)': 'en',
                'esperanto':             '',
                'estonian':              '',
                'faroese':               '',
                'finnish':               '',
                'french':                '',
                'galician':              '',
                'german':                'de',
                'greek':                 '',
                'georgian':              '',
                'hebrew':                '',
                'hindi (devanagiri)':    '',
                'hungarian':             '',
                'icelandic':             '',
                'indonesian':            '',
                'italian':               '',
                'japanese':              '',
                'korean':                '',
                'latvian':               'lt',
                'lithuanian':            'li',
                'macedonian':            '',
                'malay':                 '',
                'malayalam':             '',
                'maltese':               '',
                'maori':                 '',
                'mongolian (mongolia)':  '',
                'norwegian':             '',
                'ossetic':               '',
                'persian':               '',
                'persian (iran)':        '',
                'polish':                'pl',
                'portuguese':            '',
                'portuguese (brazil)':   '',
                'romanian':              'ro',
                'russian':               'ru',
                'serbian':               '',
                'serbian (cyrillic)':    '',
                'sinhala':               '',
                'slovak':                '',
                'slovenian':             '',
                'spanish':               '',
                'spanish (argentina)':   '',
                'spanish (mexico)':      '',
                'swedish':               '',
                'tajik':                 '',
                'tamil (india)':         '',
                'telugu':                '',
                'thai':                  '',
                'turkish':               '',
                'ukrainian':             'ua',
                'uzbek':                 '',
                'vietnamese':            '',
                'welsh':                 '',
                }

    @staticmethod
    def _weather_codes():

        return {
                'c4':          '26',
                'c4.st':       '26',
                'c4.r1':       '11',
                'c4.r1.st':    '4',
                'c4.r2':       '11',
                'c4.r2.st':    '4',
                'c4.r3':       '12',
                'c4.r3.st':    '4',
                'c4.s1':       '16',
                'c4.s1.st':    '16',
                'c4.s2':       '16',
                'c4.s2.st':    '16',
                'c4.s3':       '16',
                'c4.s3.st':    '16',
                'c4.rs1':      '5',
                'c4.rs1.st':   '5',
                'c4.rs2':      '5',
                'c4.rs2.st':   '5',
                'c4.rs3':      '5',
                'c4.rs3.st':   '5',
                'd':           '32',
                'd.st':        '32',
                'd.c2':        '30',
                'd.c2.r1':     '39',
                'd.c2.r1.st':  '37',
                'd.c2.r2':     '39',
                'd.c2.r2.st':  '37',
                'd.c2.r3':     '39',
                'd.c2.r3.st':  '37',
                'd.c2.rs1':    '42',
                'd.c2.rs1.st': '42',
                'd.c2.rs2':    '42',
                'd.c2.rs2.st': '42',
                'd.c2.rs3':    '42',
                'd.c2.rs3.st': '42',
                'd.c2.s1':     '41',
                'd.c2.s1.st':  '41',
                'd.c2.s2':     '41',
                'd.c2.s2.st':  '41',
                'd.c2.s3':     '41',
                'd.c2.s3.st':  '41',
                'd.c3':        '28',
                'd.c3.r1':     '11',
                'd.c3.r1.st':  '38',
                'd.c3.r2':     '11',
                'd.c3.r2.st':  '38',
                'd.c3.r3':     '11',
                'd.c3.r3.st':  '38',
                'd.c3.s1':     '14',
                'd.c3.s1.st':  '14',
                'd.c3.s2':     '14',
                'd.c3.s2.st':  '14',
                'd.c3.s3':     '14',
                'd.c3.s3.st':  '14',
                'd.c3.rs1':    '42',
                'd.c3.rs1.st': '42',
                'd.c3.rs2':    '42',
                'd.c3.rs2.st': '42',
                'd.c3.rs3':    '42',
                'd.c3.rs3.st': '42',
                'n':           '31',
                'n.st':        '31',
                'n.c2':        '29',
                'n.c2.r1':     '45',
                'n.c2.r1.st':  '47',
                'n.c2.r2':     '45',
                'n.c2.r2.st':  '47',
                'n.c2.r3':     '45',
                'n.c2.r3.st':  '47',
                'n.c2.rs1':    '42',
                'n.c2.rs1.st': '42',
                'n.c2.rs2':    '42',
                'n.c2.rs2.st': '42',
                'n.c2.rs3':    '42',
                'n.c2.rs3.st': '42',
                'n.c2.s1':     '46',
                'n.c2.s1.st':  '46',
                'n.c2.s2':     '46',
                'n.c2.s2.st':  '46',
                'n.c2.s3':     '46',
                'n.c2.s3.st':  '46',
                'n.c3':        '27',
                'n.c3.r1':     '11',
                'n.c3.r1.st':  '4',
                'n.c3.r2':     '11',
                'n.c3.r2.st':  '4',
                'n.c3.r3':     '11',
                'n.c3.r3.st':  '4',
                'n.c3.rs1':    '42',
                'n.c3.rs1.st': '42',
                'n.c3.rs2':    '42',
                'n.c3.rs2.st': '42',
                'n.c3.rs3':    '42',
                'n.c3.rs3.st': '42',
                'n.c3.s1':     '14',
                'n.c3.s1.st':  '14',
                'n.c3.s2':     '14',
                'n.c3.s2.st':  '14',
                'n.c3.s3':     '14',
                'n.c3.s3.st':  '14',
                'mist':        '32',
                'r1.mist':     '11',
                'r1.st.mist':  '38',
                'r2.mist':     '11',
                'r2.st.mist':  '38',
                'r3.mist':     '11',
                'r3.st.mist':  '38',
                's1.mist':     '14',
                's1.st.mist':  '14',
                's2.mist':     '14',
                's2.st.mist':  '14',
                's3.mist':     '14',
                's3.st.mist':  '14',
                'rs1.mist':    '42',
                'rs1.st.mist': '42',
                'rs2.mist':    '42',
                'rs2.st.mist': '42',
                'rs3.mist':    '42',
                'rs3.st.mist': '42',
                'nodata':      'na',
                }

    def _get_timestamp(self, date):
        if self.TIME_ZONE == 0:
            stamp = time.localtime(date['unix'])
        else:
            stamp = time.gmtime(date['unix'] + date['offset'] * 60)

        return stamp


class Location(object):

    def __init__(self, data=None):

        self._data = data or {}

    @property
    def name(self):

        location_name = self._data.get('name', '')
        if self._data.get('kind') == 'A':
            addon = Addon()
            addon.initialize_gettext()

            location_name = '{0} {1}'.format(addon.gettext('a/p'), location_name)

        return location_name

    @property
    def id(self):

        return '{0}'.format(self._data.get('id', ''))

    @property
    def district(self):

        return self._data.get('district', '')

    @property
    def country(self):

        return self._data.get('country', '')

    @property
    def label(self):

        if self.district:
            return '{0} ({1}, {2})'.format(self.name, self.district, self.country)
        else:
            return '{0} ({1})'.format(self.name, self.country)
