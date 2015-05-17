# -*- coding: utf-8 -*-
import sys
import os
import xbmcaddon
import xbmc


__addon__ = xbmcaddon.Addon(id='script.tvtunes')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__version__ = __addon__.getAddonInfo('version')
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__lib__ = xbmc.translatePath(os.path.join(__resource__, 'lib').encode("utf-8")).decode("utf-8")

sys.path.append(__resource__)
sys.path.append(__lib__)

# Import the common settings
from settings import log

from scraper import TvTunesScraper
from backend import runBackend
from screensaver import launchScreensaver


#########################
# Main
#########################
if __name__ == '__main__':
    log('script version %s started' % __version__)

    try:
        # parse sys.argv for params
        try:
            params = dict(arg.split("=") for arg in sys.argv[1].split("&"))
        except:
            params = dict(sys.argv[1].split("="))
    except:
        # no params passed
        params = {}

    log("params %s" % params)

    if params.get("backend", False):
        runBackend()

    elif params.get("mode", False) == "solo":
        TvTunesScraper()

    elif params.get("screensaver", False):
        launchScreensaver()

    else:
        # Close any open dialogs
        xbmc.executebuiltin("Dialog.Close(all, true)", True)

        log("TvTunes: Running as Addon/Plugin")
        xbmc.executebuiltin("RunAddon(script.tvtunes)")
