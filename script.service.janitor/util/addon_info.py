#!/usr/bin/python
# -*- coding: utf-8 -*-

from xbmcaddon import Addon
from xbmcvfs import translatePath

ADDON_ID = "script.service.janitor"
ADDON = Addon()
ADDON_NAME = ADDON.getAddonInfo("name")
ADDON_PROFILE = translatePath(ADDON.getAddonInfo("profile"))
ADDON_ICON = translatePath(ADDON.getAddonInfo("icon"))
