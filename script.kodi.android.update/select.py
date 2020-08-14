#  Copyright (C) 2020 Team-Kodi
#
#  This file is part of script.kodi.android.update
#
#  SPDX-License-Identifier: GPL-3.0-or-later
#  See LICENSES/README.md for more information.
#
# -*- coding: utf-8 -*-

import traceback
from kodi_six import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs

# Plugin Info
ADDON_ID      = 'script.kodi.android.update'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
ICON          = REAL_SETTINGS.getAddonInfo('icon')
LANGUAGE      = REAL_SETTINGS.getLocalizedString

## GLOBALS ##
DEBUG         = REAL_SETTINGS.getSetting('Enable_Debugging') == 'true'
CUSTOM        = REAL_SETTINGS.getSetting('Custom_Manager')

def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + (msg.encode("utf-8")), level)

def selectDialog(label, items, pselect=-1, uDetails=False):
    select = xbmcgui.Dialog().select(label, items, preselect=pselect, useDetails=uDetails)
    if select: return select
    return None
    
class Select(object):
    def __init__(self):
        items  = xbmcvfs.listdir('androidapp://sources/apps/')[1]
        select = selectDialog(LANGUAGE(30020),items)
        if select is None: return #return on cancel.
        REAL_SETTINGS.setSetting("Custom_Manager","%s"%(items[select]))

if __name__ == '__main__': Select()