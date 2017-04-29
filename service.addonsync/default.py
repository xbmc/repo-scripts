# -*- coding: utf-8 -*-
import xbmcgui
import xbmcaddon

# Import the common settings
from resources.lib.settings import log
from resources.lib.core import AddonSync

ADDON = xbmcaddon.Addon(id='service.addonsync')
ICON = ADDON.getAddonInfo('icon')


#########################
# Main
#########################
if __name__ == '__main__':
    log("AddonSync: Started Manually")

    # Print message that we have started
    xbmcgui.Dialog().notification(ADDON.getLocalizedString(32001).encode('utf-8'), ADDON.getLocalizedString(32019).encode('utf-8'), ICON, 3000, False)

    addonSync = AddonSync()

    completed = addonSync.startSync()

    # Only show the complete message if we have not shown an error
    if completed:
        xbmcgui.Dialog().notification(ADDON.getLocalizedString(32001).encode('utf-8'), ADDON.getLocalizedString(32020).encode('utf-8'), ICON, 3000, False)

    del addonSync

    log("AddonSync: End Manual Running")
