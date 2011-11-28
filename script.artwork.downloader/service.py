# -*- coding: utf-8 -*-
# modules
import xbmc
import xbmcaddon

#import libraries
from resources.lib.utils import _log as log
from resources.lib.settings import _settings

# starts update/sync
def autostart():
        settings = _settings()
        settings._get()
        log('Service - Run at startup: %s'%settings.service_startup)        
        log('Service - Run as service: %s'%settings.service_enable)
        log('Service - Time interval: %s'%settings.service_time)
        if settings.service_startup:
            xbmc.executebuiltin('XBMC.AlarmClock(ArtworkDownloader,XBMC.RunScript(script.artwork.downloader,silent=true),00:00:10,silent)')
        if settings.service_enable:
            xbmc.executebuiltin('XBMC.AlarmClock(ArtworkDownloaderService,XBMC.RunScript(script.artwork.downloader,silent=true),%s:00:00,silent,loop)'%settings.service_time)
autostart()