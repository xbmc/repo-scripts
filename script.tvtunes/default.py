# -*- coding: utf-8 -*-
import sys
import os
import xbmcaddon

__addon__     = xbmcaddon.Addon()
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
    xbmc.executebuiltin('XBMC.RunScript(%s,mode=solo)' % (os.path.join(__resource__ , "tvtunes_scraper.py")))

else: 
    xbmc.executebuiltin('XBMC.RunScript(%s)' % os.path.join( __resource__ , "tvtunes_scraper.py"))
