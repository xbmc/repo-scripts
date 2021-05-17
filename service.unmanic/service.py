#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     06 Dec 2020, (7:21 AM)

    Copyright:
        Copyright (C) 2021 Josh Sunnex

        This program is free software: you can redistribute it and/or modify it under the terms of the GNU General
        Public License as published by the Free Software Foundation, version 3.

        This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the
        implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
        for more details.

        You should have received a copy of the GNU General Public License along with this program.
        If not, see <https://www.gnu.org/licenses/>.

"""

import xbmc
import xbmcvfs
import xbmcaddon
from resources import main

__addon__ = xbmcaddon.Addon()
__path__ = __addon__.getAddonInfo('path')
__addonname__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')
__icon__ = __addon__.getAddonInfo('icon')
__ID__ = __addon__.getAddonInfo('id')
__language__ = __addon__.getLocalizedString
__profile__ = xbmcvfs.translatePath(__addon__.getAddonInfo('profile'))


class MyMonitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
        self.unmanic_service_handle = main.UnmanicServiceHandle.__call__()

    def onSettingsChanged(self):
        # Fetch the unmanic service handle
        # Stop the process
        self.stop_unmanic()
        # Wait for process to terminate
        while not monitor.abortRequested():
            monitor.waitForAbort(2)
            if self.unmanic_service_handle.poll() is None:
                continue
            else:
                xbmc.log("Unmanic process stopped", level=xbmc.LOGINFO)
                break
        # Wait for a couple of seconds before restarting
        monitor.waitForAbort(2)
        # Start the Unmanic process
        self.start_unmanic()

    def start_unmanic(self):
        self.unmanic_service_handle.start()

    def stop_unmanic(self):
        self.unmanic_service_handle.stop()


if __name__ == '__main__':
    monitor = MyMonitor()

    monitor.start_unmanic()

    while not monitor.abortRequested():
        if monitor.waitForAbort(1):
            break

    monitor.stop_unmanic()
