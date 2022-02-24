import os
import sys
import socket
import requests
import time
import _strptime
import math
import re
import codecs
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon()
ADDONNAME = ADDON.getAddonInfo('name')
ADDONID = ADDON.getAddonInfo('id')
ADDONVERSION = ADDON.getAddonInfo('version')
CWD = ADDON.getAddonInfo('path')
LANGUAGE = ADDON.getLocalizedString
DEBUG = ADDON.getSettingBool('Debug')

WEATHER_WINDOW = xbmcgui.Window(12600)
WEATHER_ICON = xbmcvfs.translatePath('%s.png')
TEMPUNIT   = xbmc.getRegion('tempunit')
DATEFORMAT = xbmc.getRegion('dateshort')
TIMEFORMAT = xbmc.getRegion('meridiem')
SPEEDUNIT = xbmc.getRegion('speedunit')

MAXDAYS = 6

socket.setdefaulttimeout(10)


# debug logging
def log(txt):
    if DEBUG:
        message = '%s: %s' % (ADDONID, txt)
        xbmc.log(msg=message, level=xbmc.LOGDEBUG)

# set weather window property
def set_property(name, value):
    WEATHER_WINDOW.setProperty(name, value)



