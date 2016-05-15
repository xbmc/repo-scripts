# -*- coding: utf-8 -*-
import sys
import xbmcaddon
import xbmc

# Import the common settings
from resources.lib.settings import log
from resources.lib.scraper import TvTunesScraper

ADDON = xbmcaddon.Addon(id='script.tvtunes')


#########################
# Main
#########################
if __name__ == '__main__':
    log('script version %s started' % ADDON.getAddonInfo('version'))

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
        log("TvTunes: Ignoring manual call to run backend")

    elif params.get("mode", False) == "solo":
        themeScraper = TvTunesScraper()
        del themeScraper
    else:
        # Close any open dialogs
        xbmc.executebuiltin("Dialog.Close(all, true)", True)

        log("TvTunes: Running as Addon/Plugin")
        xbmc.executebuiltin("RunAddon(script.tvtunes)")
