# -*- coding: utf-8 -*-
import sys
import os
import xbmc
import xbmcgui
import xbmcaddon


__addon__ = xbmcaddon.Addon(id='service.addonsync')
__icon__ = __addon__.getAddonInfo('icon')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__lib__ = xbmc.translatePath(os.path.join(__resource__, 'lib').encode("utf-8")).decode("utf-8")

sys.path.append(__resource__)
sys.path.append(__lib__)

# Import the common settings
from settings import log
from core import AddonSync


#########################
# Main
#########################
if __name__ == '__main__':
    log("AddonSync: Started Manually")

    # Print message that we have started
    xbmcgui.Dialog().notification(__addon__.getLocalizedString(32001).encode('utf-8'), __addon__.getLocalizedString(32019).encode('utf-8'), __icon__, 3000, False)

    addonSync = AddonSync()

    completed = addonSync.startSync()

    # Only show the complete message if we have not shown an error
    if completed:
        xbmcgui.Dialog().notification(__addon__.getLocalizedString(32001).encode('utf-8'), __addon__.getLocalizedString(32020).encode('utf-8'), __icon__, 3000, False)

    del addonSync

    log("AddonSync: End Manual Running")
