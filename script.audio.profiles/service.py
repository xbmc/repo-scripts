# -*- coding: utf-8 -*-

from kodi_six import xbmc
from resources.lib.apmonitor import Monitor as apMonitor

if ( __name__ == "__main__" ):
    monitor = apMonitor()
    xbmcMonitor = xbmc.Monitor()
    while not xbmcMonitor.abortRequested():
        if xbmcMonitor.waitForAbort(10):
            break
