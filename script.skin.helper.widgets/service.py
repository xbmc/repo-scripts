#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    script.skin.helper.widgets
    Main service entry point
'''

from resources.lib.utils import log_msg
from resources.lib.kodi_monitor import KodiMonitor
import xbmc
import xbmcgui
import time

TASK_INTERVAL = 520
WIN = xbmcgui.Window(10000)
MONITOR = KodiMonitor(win=WIN)
log_msg('Backgroundservice started', xbmc.LOGNOTICE)

# keep the kodi monitor alive which processes database updates to refresh widgets
while not MONITOR.abortRequested():

    # set generic widget reload
    if TASK_INTERVAL >= 300:
        WIN.setProperty("widgetreload2", time.strftime("%Y%m%d%H%M%S", time.gmtime()))
        TASK_INTERVAL = 0
    else:
        TASK_INTERVAL += 10

    # sleep for 10 seconds
    MONITOR.waitForAbort(10)

log_msg('Backgroundservice stopped', xbmc.LOGNOTICE)
