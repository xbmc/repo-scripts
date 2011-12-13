# -*- coding: utf-8 -*-
# modules
import os
import time
import xbmc
import xbmcaddon
import xbmcvfs

#import libraries
from resources.lib import utils
from resources.lib.utils import _log as log
from resources.lib.settings import _settings

# starts update/sync
def autostart():
        settings = _settings()
        settings._get()
        addondir = xbmc.translatePath( utils.__addon__.getAddonInfo('profile') )
        tempdir = os.path.join(addondir, 'temp')
        service_runtime  = "%s:00" % settings.service_runtime
        log('Service - Run at startup: %s'%settings.service_startup, xbmc.LOGNOTICE)        
        log('Service - Run as service: %s'%settings.service_enable, xbmc.LOGNOTICE)
        log('Service - Time: %s:00'%service_runtime, xbmc.LOGNOTICE)
        xbmcvfs.rmdir(tempdir)
        if settings.service_startup:
            time.sleep(10)
            xbmc.executebuiltin('XBMC.RunScript(script.artwork.downloader,silent=true)')
        if settings.service_enable:
            while (not xbmc.abortRequested):
                time.sleep(60)
                if not(time.strftime('%H:%M') == service_runtime):
                    pass
                else:
                    if not xbmcvfs.exists(tempdir):
                        log('Time is %s:%s, Scheduled run starting' % (time.strftime('%H'), time.strftime('%M')))
                        xbmc.executebuiltin('XBMC.RunScript(script.artwork.downloader,silent=true)')
                    else:
                        log('Addon already running, scheduled run aborted', xbmc.LOGNOTICE)
autostart()
