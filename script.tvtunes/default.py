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
    loop = __addon__.getSetting("loop")
    downvolume = __addon__.getSetting("downvolume")
    smb = __addon__.getSetting("smb_share")
    username = __addon__.getSetting("smb_login")
    password = __addon__.getSetting("smb_psw")
    downvolume = downvolume.split(",")[0]
    downvolume = downvolume.split(".")[0]
    if xbmc.getInfoLabel( "Window(10025).Property(TvTunesIsRunning)" ) != "true":
        xbmc.executebuiltin('XBMC.RunScript(%s,loop=%s&downvolume=%s&smb=%s&user=%s&password=%s)' % (os.path.join(__resource__ , "tvtunes_backend.py"), loop , downvolume , smb , username , password))

elif params.get("mode", False ) == "solo":
    xbmc.executebuiltin('XBMC.RunScript(%s,mode=solo&name=%s&path=%s)' % (os.path.join(__resource__ , "tvtunes_scraper.py") , params.get("tvname", False ) , params.get("tvpath", False )))

else: 
    xbmc.executebuiltin('XBMC.RunScript(%s)' % os.path.join( __resource__ , "tvtunes_scraper.py"))
