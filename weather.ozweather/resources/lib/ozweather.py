# -*- coding: utf-8 -*-
import socket

from .forecast import *
from .locations import *
from .bom.bom_location import *
from .weatherzone.weatherzone_location import *


def run(args):
    """
    This is 'main' basically.
    TWO MAJOR MODES - SETTINGS and FORECAST RETRIEVAL

    :param args: sys.argv is passed directly through
    """

    footprints()
    socket.setdefaulttimeout(100)

    # Translate old, pre BOM api settings to the new equivalents
    # The old Weatherzone locations now become the fallback settings
    # (After a transition period (say after the Kodi N* release) - this should be removed)
    if ADDON.getSetting('Location1'):
        ADDON.setSetting('Location1Weatherzone', ADDON.getSetting('Location1'))
        ADDON.setSetting('Location1', '')
    if ADDON.getSetting('Location2'):
        ADDON.setSetting('Location2Weatherzone', ADDON.getSetting('Location2'))
        ADDON.setSetting('Location2', '')
    if ADDON.getSetting('Location3'):
        ADDON.setSetting('Location3Weatherzone', ADDON.getSetting('Location3'))
        ADDON.setSetting('Location3', '')
    if ADDON.getSetting('Location1UrlPath'):
        ADDON.setSetting('Location1WeatherzoneUrlPath', ADDON.getSetting('Location1UrlPath'))
        ADDON.setSetting('Location1UrlPath', '')
    if ADDON.getSetting('Location2UrlPath'):
        ADDON.setSetting('Location2WeatherzoneUrlPath', ADDON.getSetting('Location2UrlPath'))
        ADDON.setSetting('Location2UrlPath', '')
    if ADDON.getSetting('Location3UrlPath'):
        ADDON.setSetting('Location3WeatherzoneUrlPath', ADDON.getSetting('Location3UrlPath'))
        ADDON.setSetting('Location3UrlPath', '')

    # RUN MODE - ADDON CALLED FORM Kodi SETTINGS
    # the addon is being called from the settings section where the user enters their postcodes
    if args[1].startswith('Location'):
        if args[1].endswith('WeatherZone'):
            find_weatherzone_location()
        else:
            find_bom_location()

    # RUN MODE - GET WEATHER OBSERVATIONS AND FORECAST
    # script is being called in general use, not from the settings page
    # sys.argv[1] has the current location number (e.g. '1'), so fetch the weather data
    else:
        get_weather()

    # If location settings have changed, this kick starts an update
    refresh_locations()

    # and close out...
    footprints(startup=False)
