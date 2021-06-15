# coding: utf-8
# (c) 2018, Roman Miroshnychenko <roman1972@gmail.com>
# License: GPL v. 3 <http://www.gnu.org/licenses/gpl-3.0.en.html>

from __future__ import unicode_literals

import os

from kodi_six.xbmc import getInfoLabel
from kodi_six.xbmcaddon import Addon

try:
    from kodi_six.xbmcvfs import translatePath
except (ImportError, AttributeError):
    from kodi_six.xbmc import translatePath

__all__ = ['ADDON', 'ADDON_ID', 'ADDON_VERSION', 'ADDON_PATH', 'ICON']

ADDON = Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_VERSION = ADDON.getAddonInfo('version')
ADDON_PATH = translatePath(ADDON.getAddonInfo('path'))
ICON = os.path.join(ADDON_PATH, 'icon.png')
KODI_VERSION = getInfoLabel('System.BuildVersion')[:2]
