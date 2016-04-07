# -*- coding: utf-8 -*-
import xbmcaddon
import xbmc
import xbmcgui

# Import the common settings
from resources.lib.settings import log

ADDON = xbmcaddon.Addon(id='script.pinsentry')


#########################
# Main
#########################
if __name__ == '__main__':
    log('script version %s started' % ADDON.getAddonInfo('version'))

    # Close any open dialogs
    xbmc.executebuiltin("Dialog.Close(all, true)", True)

    # Check if PinSentry is running for a restricted user, if that is the case
    # when the addon is run as a script we actually just display that users status
    if xbmcgui.Window(10000).getProperty("PinSentry_RestrictedUser") not in ["", None]:
        xbmcgui.Window(10000).setProperty("PinSentry_DisplayStatus", "true")
    else:
        # This provides a cut-through so that the PinSentry appears in the program
        # area, we could have make the "xbmc.python.pluginsource" extension point
        # also provide "executable", but that section does not allow for us to
        # put flags in the right hand of the display
        log("PinSentry: Running as Addon/Plugin")
        xbmc.executebuiltin("RunAddon(script.pinsentry)")
