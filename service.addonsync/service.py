# -*- coding: utf-8 -*-
import sys
import os
import xbmc
import xbmcaddon


__addon__ = xbmcaddon.Addon(id='service.addonsync')
__icon__ = __addon__.getAddonInfo('icon')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__lib__ = xbmc.translatePath(os.path.join(__resource__, 'lib').encode("utf-8")).decode("utf-8")

sys.path.append(__lib__)

# Import the common settings
from settings import log
from settings import Settings
from core import AddonSync


##################################
# Main of the Addon Sync Service
##################################
if __name__ == '__main__':
    log("AddonSync: Service Started")

    # Check if we should be running sync when the system starts
    if Settings.isRunOnStartup():
        addonSync = AddonSync()
        addonSync.startSync()
        del addonSync
    else:
        log("AddonSync: Not running at startup")

    log("AddonSync: Service Ended")
