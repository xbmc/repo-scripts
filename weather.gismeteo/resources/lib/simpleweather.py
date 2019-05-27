# -*- coding: utf-8 -*-
# Module: simpleweather
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

from __future__ import unicode_literals
from future.utils import (PY3, python_2_unicode_compatible)

import sys
from .simpleplugin import Plugin, py2_encode, py2_decode
import xbmc
import xbmcgui

if PY3:
    basestring = str

@python_2_unicode_compatible
class Weather(Plugin):
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

    def set_properties(self, properties, category, count=None, sep='.'):
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
        category_name = category if count is None else '%s%s%i' % (category, sep, count)
        for name, value in list(properties.items()):
            self.set_property('%s.%s' % (category_name, name), value)

    @property
    def name(self):
        """
        Addon name

        :return: addon name
        :rtype: str
        """
        return self._addon.getAddonInfo('name')

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