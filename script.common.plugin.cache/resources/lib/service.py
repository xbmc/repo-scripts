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
import threading

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

settings = xbmcaddon.Addon(id='script.common.plugin.cache')


def run():
    if settings.getSetting("autostart") == "true":
        sleep_time = 10
        server_thread = None

        monitor = xbmc.Monitor()
        while not monitor.abortRequested():
            if not server_thread:
                server_thread = ServerThread()

            if monitor.waitForAbort(sleep_time):
                break

        if server_thread:
            server_thread.abort()
            server_thread.join()


class ServerThread(threading.Thread):
    def __init__(self):
        super(ServerThread, self).__init__()

        self.server = None

        self.daemon = True
        self.start()

    def run(self):
        addon_path = settings.getAddonInfo('path')
        if isinstance(addon_path, bytes):
            addon_path = addon_path.decode('utf-8')

        sys.path = [os.path.join(addon_path, "resources", "lib", "storage_server")] + sys.path

        from storage_server import StorageServer
        self.server = StorageServer.StorageServer(False)

        xbmc.log("[%s] Service loaded, starting server ..." % self.server.plugin, xbmc.LOGDEBUG)

        self.server.run()

    def abort(self):
        self.server.force_abort = True
