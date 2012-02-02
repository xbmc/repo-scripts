# -*- coding: utf-8 -*-
# modules
import os
import time
import xbmc
import xbmcaddon
import xbmcvfs

### get addon info
__addon__       = xbmcaddon.Addon(id='script.artwork.downloader')
__addonid__     = __addon__.getAddonInfo('id')
__addonname__   = __addon__.getAddonInfo('name')
__author__      = __addon__.getAddonInfo('author')
__version__     = __addon__.getAddonInfo('version')
__addonpath__   = __addon__.getAddonInfo('path')
__icon__        = __addon__.getAddonInfo('icon')
__localize__    = __addon__.getLocalizedString
__addondir__    = xbmc.translatePath( __addon__.getAddonInfo('profile') )

#import libraries
from resources.lib import utils
from resources.lib.utils import _log as log
from resources.lib.settings import _settings

# starts update/sync
def autostart():
        xbmcaddon.Addon().setSetting(id="files_overwrite", value='false')
        settings = _settings()
        settings._get_general()
        tempdir = os.path.join(__addondir__, 'temp')
        service_runtime  = str(settings.service_runtime + ':00')
        log('## Service - Run at startup: %s'%settings.service_startup, xbmc.LOGNOTICE)        
        log('## Service - Delayed startup: %s minutes'%settings.service_startupdelay, xbmc.LOGNOTICE)   
        log('## Service - Run as service: %s'%settings.service_enable, xbmc.LOGNOTICE)
        log('## Service - Time: %s'%service_runtime, xbmc.LOGNOTICE)
        log("##########........................")
        # Check if tempdir exists and remove it
        if xbmcvfs.exists(tempdir):
            xbmcvfs.rmdir(tempdir)
            log('Removing temp folder from previous aborted run.')
            xbmc.sleep(5000)
        # Run script when enabled and check on existence of tempdir.
        # This because it is possible that script was running even when we previously deleted it.
        # Could happen when switching profiles and service gets triggered again
        if settings.service_startup and not xbmcvfs.exists(tempdir):
            xbmc.executebuiltin('XBMC.AlarmClock(ArtworkDownloader,XBMC.RunScript(script.artwork.downloader,silent=true),00:%s:15,silent)' %settings.service_startupdelay) 
        if settings.service_enable:
            while (not xbmc.abortRequested):
                xbmc.sleep(5000)
                if not(time.strftime('%H:%M') == service_runtime):
                    pass
                else:
                    if not xbmcvfs.exists(tempdir):
                        log('Time is %s:%s, Scheduled run starting' % (time.strftime('%H'), time.strftime('%M')))
                        xbmc.executebuiltin('XBMC.RunScript(script.artwork.downloader,silent=true)')
                    else:
                        log('Addon already running, scheduled run aborted', xbmc.LOGNOTICE)

if (__name__ == "__main__"):
    log("######## Extrafanart Downloader Service: Initializing........................")
    log('## Add-on ID   = %s' % str(__addonid__))
    log('## Add-on Name = %s' % str(__addonname__))
    log('## Authors     = %s' % str(__author__))
    log('## Version     = %s' % str(__version__))
    autostart()