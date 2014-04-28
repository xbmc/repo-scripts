# -*- coding: utf-8 -*-
import sys
import os
import xbmcaddon
import xbmc

if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

__addon__     = xbmcaddon.Addon(id='script.tvtunes')
__addonid__   = __addon__.getAddonInfo('id')
__addonname__ = __addon__.getAddonInfo('name')
__cwd__       = __addon__.getAddonInfo('path').decode("utf-8")
__author__    = __addon__.getAddonInfo('author')
__version__   = __addon__.getAddonInfo('version')
__language__  = __addon__.getLocalizedString
__resource__  = xbmc.translatePath( os.path.join( __cwd__, 'resources' ).encode("utf-8") ).decode("utf-8")

sys.path.append(__resource__)

def log(txt):
    if __addon__.getSetting( "logEnabled" ) == "true":
        if isinstance (txt,str):
            txt = txt.decode("utf-8")
        message = u'%s: %s' % (__addonid__, txt)
        xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)

log('script version %s started' % __version__)

try:
    # parse sys.argv for params
    try:
        params = dict( arg.split( "=" ) for arg in sys.argv[ 1 ].split( "&" ) )
    except:
        params = dict( sys.argv[ 1 ].split( "=" ))
except:
    # no params passed
    params = {}

log( "params %s" % params )
    
if params.get("backend", False ): 
    xbmc.executebuiltin('XBMC.RunScript(%s)' % (os.path.join(__resource__ , "tvtunes_backend.py")))

elif params.get("mode", False ) == "solo":
    xbmc.executebuiltin('XBMC.RunScript(%s)' % (os.path.join(__resource__ , "tvtunes_scraper.py")))

else: 
    # Close any open dialogs
    xbmc.executebuiltin("Dialog.Close(all, true)", True)

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
        log( json_response )

        # Allow time for the command to be reflected on the screen      
        xbmc.sleep(100)

        selectedTitle = xbmc.getInfoLabel('ListItem.Label')
        log("TvTunes: plugin screen selected Title=%s" % selectedTitle)

    # Now select the menu item if it is TvTunes
    if selectedTitle == 'TvTunes':
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Input.Select", "params": { }, "id": 1}')
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        log( json_response )
            

