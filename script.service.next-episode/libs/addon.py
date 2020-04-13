# coding: utf-8
# (c) 2018, Roman Miroshnychenko <roman1972@gmail.com>
# License: GPL v. 3 <http://www.gnu.org/licenses/gpl-3.0.en.html>

from __future__ import unicode_literals
import os
from kodi_six.xbmc import getInfoLabel
from kodi_six.xbmcaddon import Addon

__all__ = ['ADDON', 'ADDON_ID', 'ADDON_VERSION', 'ICON']

ADDON = Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_VERSION = ADDON.getAddonInfo('version')
ICON = os.path.join(ADDON.getAddonInfo('path'), 'icon.png')
KODI_VERSION = getInfoLabel('System.BuildVersion')[:2]
