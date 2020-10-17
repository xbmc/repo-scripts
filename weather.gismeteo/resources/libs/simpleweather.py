# -*- coding: utf-8 -*-
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

from __future__ import unicode_literals
from future.utils import PY3, PY26, python_2_unicode_compatible

import sys
import math
import xbmc
import xbmcgui
import requests

from .simpleplugin import Plugin, SimplePluginError, py2_encode, py2_decode
from .simpleplugin import Addon as SP_Addon

if PY3:
    basestring = str

__all__ = ['WeatherProperties', 'Weather', 'WebClientError', 'WebClient',
           'Addon', 'SimplePluginError', 'py2_encode', 'py2_decode']


class WebClientError(Exception):

    def __init__(self, error):

        self.message = error
        super(WebClientError, self).__init__(self.message)


class WebClient(requests.Session):

    _secret_data = ['password']

    def __init__(self, headers=None, cookie_file=None):
        super(WebClient, self).__init__()

        if cookie_file is not None:
            self.cookies = cookielib.LWPCookieJar(cookie_file)
            if os.path.exists(cookie_file):
                self.cookies.load(ignore_discard=True, ignore_expires=True)

        if headers is not None:
            self.headers.update(headers)

        self._addon = SP_Addon()

    def __save_cookies(self):
        if isinstance(self.cookies, cookielib.LWPCookieJar) \
           and self.cookies.filename:
            self.cookies.save(ignore_expires=True, ignore_discard=True)

    def post(self, url, **kwargs):

        func = super(WebClient, self).post
        return self._run(func, url, **kwargs)

    def get(self, url, **kwargs):

        func = super(WebClient, self).get
        return self._run(func, url, **kwargs)

    def put(self, url, **kwargs):

        func = super(WebClient, self).put
        return self._run(func, url, **kwargs)

    def delete(self, url, **kwargs):

        func = super(WebClient, self).delete
        return self._run(func, url, **kwargs)

    def _run(self, func, url, **kwargs):

        try:
            r = func(url, **kwargs)
            r.raise_for_status()
        except (requests.HTTPError, requests.ConnectionError) as e:
            self._log_error(e)
            raise WebClientError(e)
        else:
            self._log_debug(r)
            if r.headers.get('set-cookie') is not None:
                self.__save_cookies()
            return r

    def _log_debug(self, response):
        debug_info = []

        request = getattr(response, 'request', None)

        if request is not None:
            request_info = self._get_request_info(request)
            if request:
                debug_info.append(request_info)

        if response is not None:
            response_info = self._get_response_info(response)
            if response_info:
                debug_info.append(response_info)

        self._addon.log_debug('\n'.join(debug_info))

    def _log_error(self, error):
        error_info = [str(error)]

        response = getattr(error, 'response', None)
        request = getattr(error, 'request', None)

        if request is not None:
            request_info = self._get_request_info(request)
            if request:
                error_info.append(request_info)

        if response is not None:
            response_info = self._get_response_info(response)
            if response_info:
                error_info.append(response_info)

        self._addon.log_error('\n'.join(error_info))

    @staticmethod
    def _get_response_info(response):
        response_info = ['Response info', 'Status code: {0}'.format(response.status_code),
                         'Reason: {0}'.format(response.reason)]
        if not PY26:
             response_info.append('Elapsed: {0:.4f} sec'.format(response.elapsed.total_seconds()))
        if response.url:
            response_info.append('URL: {0}'.format(response.url))
        if response.headers:
            response_info.append('Headers: {0}'.format(response.headers))
        if response.text:
            response_info.append('Content: {0}'.format(response.text))

        return '\n'.join(response_info)

    @classmethod
    def _get_request_info(cls, request):
        request_info = ['Request info', 'Method: {0}'.format(request.method)]

        if request.url:
            request_info.append('URL: {0}'.format(request.url))
        if request.headers:
            request_info.append('Headers: {0}'.format(request.headers))
        if request.body:
            try:
                j = json.loads(request.body)
                for field in cls._secret_data:
                    if j.get(field) is not None:
                        j[field] = '<SECRET>'
                data = json.dumps(j)
            except ValueError:
                data = request.body
                for param in data.split('&'):
                    if '=' in param:
                        field, value = param.split('=')
                        if field in cls._secret_data:
                            data = data.replace(param, '{0}=<SECRET>'.format(field))
            request_info.append('Data: {0}'.format(data))

        return '\n'.join(request_info)


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


class Helper():

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
                '01' : 21,
                '02' : 22,
                '03' : 23,
                '04' : 24,
                '05' : 25,
                '06' : 26,
                '07' : 27,
                '08' : 28,
                '09' : 29,
                '10' : 30,
                '11' : 31,
                '12' : 32,
                }

    @staticmethod
    def month_name_short():

        return {
                '01' : 51,
                '02' : 52,
                '03' : 53,
                '04' : 54,
                '05' : 55,
                '06' : 56,
                '07' : 57,
                '08' : 58,
                '09' : 59,
                '10' : 60,
                '11' : 61,
                '12' : 62,
                }

    @staticmethod
    def week_day_long():

        return {
                '0' : 17,
                '1' : 11,
                '2' : 12,
                '3' : 13,
                '4' : 14,
                '5' : 15,
                '6' : 16,
                }

    @staticmethod
    def week_day_short():

        return {
                '0' : 47,
                '1' : 41,
                '2' : 42,
                '3' : 43,
                '4' : 44,
                '5' : 45,
                '6' : 46,
                }


class Dialogs():

    def notify_error(self, error, show_dialog=False):
        heading = ''
        message = '{0}'.format(error)
        if isinstance(error, WebClientError):
            heading = self.gettext('Connection error')
        else:
            self.log_error(message)

        if show_dialog:
            if heading:
                self.dialog_ok(heading, message)
            else:
                self.dialog_ok(message)
        else:
            self.dialog_notification_error(heading, message)

    def dialog_notification_error(self, heading, message="", time=0, sound=True):
        self.dialog_notification(heading, message, xbmcgui.NOTIFICATION_ERROR, time, sound)

    def dialog_notification_info(self, heading, message="", time=0, sound=True):
        self.dialog_notification(heading, message, xbmcgui.NOTIFICATION_INFO, time, sound)

    def dialog_notification_warning(self, heading, message="", time=0, sound=True):
        self.dialog_notification(heading, message, xbmcgui.NOTIFICATION_WARNING, time, sound)

    def dialog_notification(self, heading, message="", icon="", time=0, sound=True):

        _message = message if message else heading

        if heading \
          and heading != _message:
            _heading = '{0}: {1}'.format(self.name, heading)
        else:
            _heading = self.name

        xbmcgui.Dialog().notification(_heading, _message, icon, time, sound)

    def dialog_ok(self, line1, line2="", line3=""):

        if self.kodi_major_version() >= '19':
            xbmcgui.Dialog().ok(self.name, self._join_strings(line1, line2, line3))
        else:
            xbmcgui.Dialog().ok(self.name, line1, line2, line3)

    def dialog_progress_create(self, heading, line1="", line2="", line3=""):
        progress = xbmcgui.DialogProgress()

        if self.kodi_major_version() >= '19':
            progress.create(heading, self._join_strings(line1, line2, line3))
        else:
            progress.create(heading, line1, line2, line3)

        return progress

    def dialog_progress_update(self, progress, percent, line1="", line2="", line3=""):

        if self.kodi_major_version() >= '19':
            progress.update(percent, self._join_strings(line1, line2, line3))
        else:
            progress.update(percent, line1, line2, line3)

        return progress

    @staticmethod
    def dialog_select(heading, _list, **kwargs):
        return xbmcgui.Dialog().select(heading, _list, **kwargs)

    @staticmethod
    def _join_strings(line1, line2="", line3=""):

        lines = []
        if line1: lines.append(line1)
        if line2: lines.append(line2)
        if line3: lines.append(line3)

        return '[CR]'.join(lines)


class Addon(SP_Addon, Helper, Dialogs):

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
            weather_icon = py2_decode(xbmc.translatePath('special://temp/weather/%s.png'))
        else:
            weather_icon = py2_decode(xbmc.translatePath('%s.png'))

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

        if isinstance(speed, str):
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
    def DEW_POINT(self, Tc=0, RH=93, ext=True, minRH=(0, 0.075)[ 0 ]):
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
class Weather(Plugin, Addon):

    def __init__(self, id_=''):
        """
        Class constructor
        """
        super(Weather, self).__init__(id_)
        self._url = 'plugin://{0}/'.format(self.id)
        self.actions = {}
        self._params = None

        self._window = xbmcgui.Window(12600)

        self._reg_tempunit = py2_decode(xbmc.getRegion('tempunit'))
        self._reg_speedunit = xbmc.getRegion('speedunit')
        self._reg_dateshort = xbmc.getRegion('dateshort')
        self._reg_meridiem = xbmc.getRegion('meridiem')

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
