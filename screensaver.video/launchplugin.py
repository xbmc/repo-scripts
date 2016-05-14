# -*- coding: utf-8 -*-
import xbmc
import xbmcaddon

# Import the common settings
from resources.lib.settings import log

ADDON = xbmcaddon.Addon(id='screensaver.video')

#########################
# Main
#########################
if __name__ == '__main__':
    log('script version %s started' % ADDON.getAddonInfo('version'))

    # Close any open dialogs
    xbmc.executebuiltin("Dialog.Close(all, true)", True)

    log("VideoScreensaver: Running as Addon/Plugin")
    xbmc.executebuiltin("RunAddon(screensaver.video)")
