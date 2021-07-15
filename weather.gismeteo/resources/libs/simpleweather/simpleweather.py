# -*- coding: utf-8 -*-
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

from __future__ import unicode_literals

import math
import sys

import simpleplugin
import xbmc
import xbmcgui
from future.utils import PY3, python_2_unicode_compatible
from simpleplugin import py2_encode, py2_decode, translate_path

from .dialogs import Dialogs

if PY3:
    basestring = str

__all__ = ['WeatherProperties', 'Weather',
           'Addon', 'py2_encode', 'py2_decode']


class WeatherProperties(object):

    @staticmethod
    def prop_current():
        return {  # standart properties
            'Location': '',
            'Condition': '',
            'Temperature': '',
            'Wind': '',
            'WindDirection': '',
            'Humidity': '',
            'FeelsLike': '',
            'DewPoint': '',
            'OutlookIcon': '',
            'FanartCode': '',

            # extenden properties
            'Pressure': '',
            'Precipitation': '',
            'ProviderIcon': '',
        }

    @staticmethod
    def prop_today():
        return {  # extended properties
            'Sunrise': '',
            'Sunset': '',
        }

    @staticmethod
    def prop_day():
        return {  # standart properties
            'Title': '',
            'HighTemp': '',
            'LowTemp': '',
            'Outlook': '',
            'OutlookIcon': '',
            'FanartCode': '',

            # extended properties
            'ProviderIcon': '',
        }

    @staticmethod
    def prop_daily():
        return {  # extenden properties
            'LongDay': '',
            'ShortDay': '',
            'LongDate': '',
            'ShortDate': '',
            'Outlook': '',
            'OutlookIcon': '',
            'FanartCode': '',
            'WindSpeed': '',
            'MaxWind': '',
            'WindDirection': '',
            'Humidity': '',
            'MinHumidity': '',
            'MaxHumidity': '',
            'HighTemperature': '',
            'LowTemperature': '',
            'DewPoint': '',
            'TempMorn': '',
            'TempDay': '',
            'TempEve': '',
            'TempNight': '',
            'Pressure': '',
            'Precipitation': '',
            'ProviderIcon': '',
        }

    @staticmethod
    def prop_hourly():
        return {  # extenden properties
            'Time': '',
            'LongDate': '',
            'ShortDate': '',
            'Outlook': '',
            'OutlookIcon': '',
            'FanartCode': '',
            'WindSpeed': '',
            'WindDirection': '',
            'Humidity': '',
            'Temperature': '',
            'DewPoint': '',
            'FeelsLike': '',
            'Pressure': '',
            'Precipitation': '',
            'ProviderIcon': '',
        }

    @staticmethod
    def prop_36hour():
        return {  # extenden properties
            'Heading': '',
            'TemperatureHeading': '',
            'LongDay': '',
            'ShortDay': '',
            'LongDate': '',
            'ShortDate': '',
            'Outlook': '',
            'OutlookIcon': '',
            'FanartCode': '',
            'WindSpeed': '',
            'WindDirection': '',
            'Humidity': '',
            'Temperature': '',
            'DewPoint': '',
            'FeelsLike': '',
            'Pressure': '',
            'Precipitation': '',
            'ProviderIcon': '',
        }

    @staticmethod
    def prop_forecast():
        return {  # extenden properties
            'City': '',
            'Country': '',
            'Latitude': '',
            'Longitude': '',
            'Updated': '',
        }

    @staticmethod
    def prop_description():
        return {  # standard properties
            'WeatherProvider': '',
            'WeatherProviderLogo': '',

            # extenden properties
            'Forecast.IsFetched': '',
            'Current.IsFetched': '',
            'Today.IsFetched': '',
            'Daily.IsFetched': '',
            'Weekend.IsFetched': '',
            '36Hour.IsFetched': '',
            'Hourly.IsFetched': '',
            'Alerts.IsFetched': '',
            'Map.IsFetched': '',
        }


class Helper(object):

    @classmethod
    def kodi_major_version(cls):
        return cls.kodi_version().split('.')[0]

    @staticmethod
    def kodi_version():
        return xbmc.getInfoLabel('System.BuildVersion').split(' ')[0]

    @staticmethod
    def get_keyboard_text(line='', heading='', hidden=False):
        kbd = xbmc.Keyboard(line, heading, hidden)
        kbd.doModal()
        if kbd.isConfirmed():
            return kbd.getText()

        return ''

    @staticmethod
    def wind_directions():
        return {
            '1': 71,
            '2': 73,
            '3': 75,
            '4': 77,
            '5': 79,
            '6': 81,
            '7': 83,
            '8': 85,
        }

    @staticmethod
    def month_name_long():
        return {
            '01': 21,
            '02': 22,
            '03': 23,
            '04': 24,
            '05': 25,
            '06': 26,
            '07': 27,
            '08': 28,
            '09': 29,
            '10': 30,
            '11': 31,
            '12': 32,
        }

    @staticmethod
    def month_name_short():
        return {
            '01': 51,
            '02': 52,
            '03': 53,
            '04': 54,
            '05': 55,
            '06': 56,
            '07': 57,
            '08': 58,
            '09': 59,
            '10': 60,
            '11': 61,
            '12': 62,
        }

    @staticmethod
    def week_day_long():
        return {
            '0': 17,
            '1': 11,
            '2': 12,
            '3': 13,
            '4': 14,
            '5': 15,
            '6': 16,
        }

    @staticmethod
    def week_day_short():
        return {
            '0': 47,
            '1': 41,
            '2': 42,
            '3': 43,
            '4': 44,
            '5': 45,
            '6': 46,
        }


class Addon(simpleplugin.Addon, Helper, Dialogs):

    def __init__(self, id_=''):
        """
        Class constructor
        """
        super(Addon, self).__init__(id_)

        self._reg_tempunit = py2_decode(xbmc.getRegion('tempunit'))
        self._reg_tempunit = py2_decode(xbmc.getRegion('tempunit'))
        self._reg_speedunit = xbmc.getRegion('speedunit')
        self._reg_dateshort = xbmc.getRegion('dateshort')
        self._reg_meridiem = xbmc.getRegion('meridiem')

    @property
    def tempunit(self):
        """
        Regions setting temperature unit

        :return: temperature unit
        :rtype: str
        """
        return self._reg_tempunit

    @property
    def speedunit(self):
        """
        Regions setting speed unit

        :return: speed unit
        :rtype: str
        """
        return self._reg_speedunit

    @property
    def date_format(self):
        """
        Regions setting date format

        :return: date format
        :rtype: str
        """
        return self._reg_dateshort

    @property
    def time_format(self):
        """
        Regions setting time format

        :return: time format
        :rtype: str
        """
        return self._reg_meridiem

    @property
    def weather_icon(self):
        """
        Weather icon for curren KODI version

        :return: weather icon
        :rtype: str
        """
        major_version = xbmc.getInfoLabel('System.BuildVersion')[:2]
        if major_version < '16':
            weather_icon = py2_decode(translate_path('special://temp/weather/%s.png'))
        else:
            weather_icon = py2_decode(translate_path('%s.png'))

        return weather_icon

    def SPEED(self, mps):
        SPEEDUNIT = self.speedunit

        if SPEEDUNIT == 'km/h':
            speed = mps * 3.6
        elif SPEEDUNIT == 'm/min':
            speed = mps * 60
        elif SPEEDUNIT == 'ft/h':
            speed = mps * 11810.88
        elif SPEEDUNIT == 'ft/min':
            speed = mps * 196.84
        elif SPEEDUNIT == 'ft/s':
            speed = mps * 3.281
        elif SPEEDUNIT == 'mph':
            speed = mps * 2.237
        elif SPEEDUNIT in ['knots', 'kts']:
            speed = mps * 1.944
        elif SPEEDUNIT == 'Beaufort':
            speed = self.KPHTOBFT(mps * 3.6)
        elif SPEEDUNIT == 'inch/s':
            speed = mps * 39.37
        elif SPEEDUNIT == 'yard/s':
            speed = mps * 1.094
        elif SPEEDUNIT == 'Furlong/Fortnight':
            speed = mps * 6012.886
        else:
            speed = mps

        if isinstance(speed, basestring):
            return speed
        else:
            return '{0}'.format(int(round(speed)))

    def TEMP(self, deg):
        TEMPUNIT = self.tempunit

        if TEMPUNIT == '°F':
            temp = deg * 1.8 + 32
        elif TEMPUNIT == 'K':
            temp = deg + 273.15
        elif TEMPUNIT == '°Ré':
            temp = deg * 0.8
        elif TEMPUNIT == '°Ra':
            temp = deg * 1.8 + 491.67
        elif TEMPUNIT == '°Rø':
            temp = deg * 0.525 + 7.5
        elif TEMPUNIT in ['°D', '°De']:
            temp = deg / -0.667 + 150
        elif TEMPUNIT == '°N':
            temp = deg * 0.33
        else:
            temp = deg

        return '{0}'.format(int(round(temp)))

    @staticmethod
    def KPHTOBFT(spd):
        if (spd < 1.0):
            bft = '0'
        elif (spd >= 1.0) and (spd < 5.6):
            bft = '1'
        elif (spd >= 5.6) and (spd < 12.0):
            bft = '2'
        elif (spd >= 12.0) and (spd < 20.0):
            bft = '3'
        elif (spd >= 20.0) and (spd < 29.0):
            bft = '4'
        elif (spd >= 29.0) and (spd < 39.0):
            bft = '5'
        elif (spd >= 39.0) and (spd < 50.0):
            bft = '6'
        elif (spd >= 50.0) and (spd < 62.0):
            bft = '7'
        elif (spd >= 62.0) and (spd < 75.0):
            bft = '8'
        elif (spd >= 75.0) and (spd < 89.0):
            bft = '9'
        elif (spd >= 89.0) and (spd < 103.0):
            bft = '10'
        elif (spd >= 103.0) and (spd < 118.0):
            bft = '11'
        elif (spd >= 118.0):
            bft = '12'
        else:
            bft = ''
        return bft

    #### thanks to FrostBox @ http://forum.kodi.tv/showthread.php?tid=114637&pid=937168#pid937168
    def DEW_POINT(self, Tc=0, RH=93, ext=True, minRH=(0, 0.075)[0]):
        Es = 6.11 * 10.0 ** (7.5 * Tc / (237.7 + Tc))
        RH = RH or minRH
        E = (RH * Es) / 100
        try:
            DewPoint = (-430.22 + 237.7 * math.log(E)) / (-math.log(E) + 19.08)
        except ValueError:
            DewPoint = 0
        if ext:
            return self.TEMP(DewPoint)
        else:
            return '{0}'.format(int(round(DewPoint)))

    def PRESSURE(self, mmHg):
        if self.PRESUNIT == 'mmHg':
            return '%.0f' % (float(mmHg))
        elif self.PRESUNIT in ['hPa', 'mbar']:
            return '%.0f' % (float(mmHg * 1.3332239))
        elif self.PRESUNIT == 'inHg':
            return '%.2f' % (float(mmHg * 0.0393701))

    def PRECIPITATION(self, mm):
        if self.PRECIPUNIT == 'mm':
            return '%.1f' % (float(mm))
        elif self.PRECIPUNIT == 'inch':
            return '%.2f' % (float(mm) * 0.0393701)


@python_2_unicode_compatible
class Weather(simpleplugin.Plugin, Addon):

    def __init__(self, id_=''):
        """
        Class constructor
        """
        super(Weather, self).__init__(id_)
        self._url = 'plugin://{0}/'.format(self.id)
        self.actions = {}
        self._params = None

        self._window = xbmcgui.Window(12600)

    def __str__(self):
        return '<Weather {0}>'.format(sys.argv)

    def run(self):
        """
        Run plugin

        :raises SimplePluginError: if unknown action string is provided.
        """

        if sys.argv[1].isdigit():
            paramstring = 'id=%s' % (sys.argv[1])
        else:
            paramstring = sys.argv[1]

        self._params = self.get_params(paramstring)
        self.log_debug(str(self))
        self._resolve_function()

    def set_property(self, name, value):
        """
        Set property of weather window

        :name name: property name
        :type name: str
        :name value: property value
        :type value: str, int or unicode

        """
        if isinstance(value, int):
            self._window.setProperty(name, str(value))
        elif isinstance(value, basestring):
            self._window.setProperty(name, value)
        else:
            raise TypeError(
                'value parameter must be of int or str type!')

    def set_properties(self, properties, category='', count=None, sep='.'):
        """
        Set properties of weather window

        :name properties: a dict of category properties
        :type properties: dict
        :name category: category name
        :type category: str
        :name count: category count (optional)
        :type count: int
        :name sep: separator between category and count
        :type sep: str

        """
        category_name = category if count is None else '{0}{1}{2}'.format(category, sep, count)
        for name, value in list(properties.items()):
            if category_name:
                self.set_property('{0}.{1}'.format(category_name, name), value)
            else:
                self.set_property(name, value)
