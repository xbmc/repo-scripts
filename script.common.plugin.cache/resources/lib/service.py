"""
    Cache service for Kodi
    Version 0.8

    Copyright (C) 2010-2011 Tobias Ussing And Henrik Mosgaard Jensen
    Copyright (C) 2019 anxdpanic

    This file is part of script.common.plugin.cache

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only.txt for more information.
"""

import os
import sys
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

settings = xbmcaddon.Addon(id='script.common.plugin.cache')


def run():
    if settings.getSetting("autostart") == "true":

        addon_path = settings.getAddonInfo('path')
        if isinstance(addon_path, bytes):
            addon_path = addon_path.decode('utf-8')

        sys.path = [os.path.join(addon_path, "resources", "lib", "storage_server")] + sys.path

        from storage_server import StorageServer
        s = StorageServer.StorageServer(False)

        xbmc.log("[%s] Service loaded, starting server ..." % s.plugin, xbmc.LOGDEBUG)

        s.run()
