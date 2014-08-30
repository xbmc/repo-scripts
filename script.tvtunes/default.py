# -*- coding: utf-8 -*-
import sys
import os
import xbmcaddon
import xbmc

if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

__addon__ = xbmcaddon.Addon(id='script.tvtunes')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__version__ = __addon__.getAddonInfo('version')
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__lib__ = xbmc.translatePath(os.path.join(__resource__, 'lib').encode("utf-8")).decode("utf-8")

sys.path.append(__resource__)
sys.path.append(__lib__)

# Import the common settings
from settings import Settings
from settings import log


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
        xbmc.executebuiltin('XBMC.RunScript(%s)' % (os.path.join(__resource__, "tvtunes_backend.py")))

    elif params.get("mode", False) == "solo":
        xbmc.executebuiltin('XBMC.RunScript(%s)' % (os.path.join(__resource__, "tvtunes_scraper.py")))

    else:
        # Close any open dialogs
        xbmc.executebuiltin("Dialog.Close(all, true)", True)

        if Settings.getXbmcMajorVersion() > 12:
            log("TvTunes: Running as Addon/Plugin")
            xbmc.executebuiltin("RunAddon(script.tvtunes)")
        else:
            log("TvTunes: Navigating to Plugin")
            # Default to the plugin method
            xbmc.executebuiltin("xbmc.ActivateWindow(Video, addons://sources/video/)", True)

            # It is a bit hacky, but the only way I can get it to work
            # After loading the plugin screen, navigate to the TvTunes entry and select it
            maxChecks = 100
            selectedTitle = None
            while selectedTitle != 'TvTunes' and maxChecks > 0:
                maxChecks = maxChecks - 1
                json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Input.Up", "params": { }, "id": 1}')
                json_query = unicode(json_query, 'utf-8', errors='ignore')
                json_response = simplejson.loads(json_query)
                log(json_response)

                # Allow time for the command to be reflected on the screen
                xbmc.sleep(100)

                selectedTitle = xbmc.getInfoLabel('ListItem.Label')
                log("TvTunes: plugin screen selected Title=%s" % selectedTitle)

            # Now select the menu item if it is TvTunes
            if selectedTitle == 'TvTunes':
                json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Input.Select", "params": { }, "id": 1}')
                json_query = unicode(json_query, 'utf-8', errors='ignore')
                json_response = simplejson.loads(json_query)
                log(json_response)
