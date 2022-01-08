# -*- coding: utf-8 -*-
"""
    Copyright (C) 2013-2021 Skin Shortcuts (script.skinshortcuts)
    This file is part of script.skinshortcuts
    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

import os

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON_ID = 'script.skinshortcuts'
ADDON = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_VERSION = ADDON.getAddonInfo('version')

KODI_VERSION = xbmc.getInfoLabel("System.BuildVersion").split(".")[0]

CWD = ADDON.getAddonInfo('path')

DEFAULT_PATH = xbmcvfs.translatePath(os.path.join(CWD, 'resources', 'shortcuts'))
DATA_PATH = xbmcvfs.translatePath("special://profile/addon_data/%s/" % ADDON_ID)
SKIN_SHORTCUTS_PATH = xbmcvfs.translatePath("special://skin/shortcuts/")
RESOURCE_PATH = xbmcvfs.translatePath(os.path.join(CWD, 'resources', 'lib'))
MASTER_PATH = xbmcvfs.translatePath("special://masterprofile/addon_data/%s/" % ADDON_ID)
SKIN_PATH = xbmcvfs.translatePath("special://skin/")
PROFILE_PATH = xbmcvfs.translatePath("special://profile/")
KODI_PATH = xbmcvfs.translatePath("special://xbmc/")
SKIN_DIR = xbmc.getSkinDir()
PROPERTIES_FILE = os.path.join(DATA_PATH, "%s.properties" % SKIN_DIR)
HASH_FILE = os.path.join(MASTER_PATH, "%s.hash" % SKIN_DIR)
LANGUAGE = ADDON.getLocalizedString
HOME_WINDOW = xbmcgui.Window(10000)
