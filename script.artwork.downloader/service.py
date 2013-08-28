# -*- coding: utf-8 -*-
# modules
import os
import time
import xbmc
import xbmcaddon
import xbmcvfs
import lib.common

### get addon info
__addon__        = lib.common.__addon__
__addonpath__    = lib.common.__addonpath__
__localize__     = lib.common.__localize__
__addonname__    = lib.common.__addonname__
__version__      = lib.common.__version__
__addonprofile__ = lib.common.__addonprofile__

#import libraries
from lib.settings import get
from lib.utils import log
setting = get()

# starts update/sync
def autostart():
        xbmcaddon.Addon().setSetting(id="files_overwrite", value='false')
        tempdir = os.path.join(__addonprofile__, 'temp')
        service_runtime  = str(setting.get('service_runtime') + ':00')
        log('## Service - Run at startup: %s'% setting.get('service_startup'), xbmc.LOGNOTICE)        
        log('## Service - Delayed startup: %s minutes'% setting.get('service_startupdelay'), xbmc.LOGNOTICE)   
        log('## Service - Run as service: %s'% setting.get('service_enable'), xbmc.LOGNOTICE)
        log('## Service - Time: %s'% service_runtime, xbmc.LOGNOTICE)
        log("##########........................")
        # Check if tempdir exists and remove it
        if xbmcvfs.exists(tempdir):
            xbmcvfs.rmdir(tempdir)
            log('Removing temp folder from previous aborted run.')
            xbmc.sleep(5000)
        # Run script when enabled and check on existence of tempdir.
        # This because it is possible that script was running even when we previously deleted it.
        # Could happen when switching profiles and service gets triggered again
        if setting.get('service_startup') and not xbmcvfs.exists(tempdir):
            xbmc.executebuiltin('XBMC.AlarmClock(ArtworkDownloader,XBMC.RunScript(script.artwork.downloader,silent=true),00:%s:15,silent)' % setting.get('setting.service_startupdelay')) 
        if setting.get('service_enable'):
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
    log("######## Artwork Downloader Service: Initializing........................")
    log('## Add-on Name = %s' % str(__addonname__))
    log('## Version     = %s' % str(__version__))
    autostart()