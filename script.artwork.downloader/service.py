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
__addonprofile__= xbmc.translatePath( __addon__.getAddonInfo('profile') ).decode('utf-8')

#import libraries
from resources.lib.utils import *
from resources.lib.settings import settings

# starts update/sync
def autostart():
        xbmcaddon.Addon().setSetting(id="files_overwrite", value='false')
        setting = settings()
        setting._get_general()
        tempdir = os.path.join(__addonprofile__, 'temp')
        service_runtime  = str(setting.service_runtime + ':00')
        log('## Service - Run at startup: %s'%setting.service_startup, xbmc.LOGNOTICE)        
        log('## Service - Delayed startup: %s minutes'%setting.service_startupdelay, xbmc.LOGNOTICE)   
        log('## Service - Run as service: %s'%setting.service_enable, xbmc.LOGNOTICE)
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
        if setting.service_startup and not xbmcvfs.exists(tempdir):
            xbmc.executebuiltin('XBMC.AlarmClock(ArtworkDownloader,XBMC.RunScript(script.artwork.downloader,silent=true),00:%s:15,silent)' %setting.service_startupdelay) 
        if setting.service_enable:
            while (not xbmc.abortRequested):
                xbmc.sleep(5000)
                if not(time.strftime('%H:%M') == service_runtime):
                    pass
                else:
                    if not xbmcvfs.exists(tempdir):
                        log('Time is %s:%s, Scheduled run starting' % (time.strftime('%H'), time.strftime('%M')))
                        xbmc.executebuiltin('XBMC.RunScript(script.artwork.downloader,silent=true)')
                        # Because we now use the commoncache module the script is run so fast it is possible it is started twice
                        # within the one minute window. So keep looping until it goes out of that window
                        while (not xbmc.abortRequested and time.strftime('%H:%M') == service_runtime):
                            xbmc.sleep(5000)
                    else:
                        log('Addon already running, scheduled run aborted', xbmc.LOGNOTICE)

if (__name__ == "__main__"):
    log("######## Extrafanart Downloader Service: Initializing........................")
    log('## Add-on ID   = %s' % str(__addonid__))
    log('## Add-on Name = %s' % str(__addonname__))
    log('## Authors     = %s' % str(__author__))
    log('## Version     = %s' % str(__version__))
    autostart()