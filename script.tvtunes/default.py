# -*- coding: utf-8 -*-
import sys
import os
import xbmcaddon

__addon__     = xbmcaddon.Addon()
__addonname__ = __addon__.getAddonInfo('name')
__cwd__       = __addon__.getAddonInfo('path')
__author__    = __addon__.getAddonInfo('author')
__version__   = __addon__.getAddonInfo('version')
__language__  = __addon__.getLocalizedString

RESOURCES_PATH = xbmc.translatePath( os.path.join( __cwd__, 'resources' ) ).decode('utf-8')
sys.path.append( RESOURCES_PATH )

def log(msg):
    xbmc.log( str( msg ),level=xbmc.LOGDEBUG )

log( "### %s starting ..." % __addonname__ )
log( "### author: %s" % __author__ )
log( "### version: %s" % __version__ )

try:
    # parse sys.argv for params
    try:
        params = dict( arg.split( "=" ) for arg in sys.argv[ 1 ].split( "&" ) )
    except:
        params = dict( sys.argv[ 1 ].split( "=" ))
except:
    # no params passed
    params = {}
if params.get("backend", False ): 

    loop = __addon__.getSetting("loop")
    downvolume = __addon__.getSetting("downvolume")
    smb = __addon__.getSetting("smb_share")
    username = __addon__.getSetting("smb_login")
    password = __addon__.getSetting("smb_psw")
    downvolume = downvolume.split(",")[0]
    downvolume = downvolume.split(".")[0]
    if xbmc.getInfoLabel( "Window(10025).Property(TvTunesIsRunning)" ) != "true":
        #log( '########################################################################%s,loop=%s&downvolume=%s&smb=%s&user=%spassword=%s' % (os.path.join( RESOURCES_PATH , "tvtunes_backend.py"), loop , downvolume , smb , username , password) )
        xbmc.executebuiltin('XBMC.RunScript(%s,loop=%s&downvolume=%s&smb=%s&user=%s&password=%s)' % (os.path.join( RESOURCES_PATH , "tvtunes_backend.py"), loop , downvolume , smb , username , password))

elif params.get("mode", False ) == "solo":
    log( "### params %s" % params )
    xbmc.executebuiltin('XBMC.RunScript(%s,mode=solo&name=%s&path=%s)' % (os.path.join( RESOURCES_PATH , "tvtunes_scraper.py") , params.get("tvname", False ) , params.get("tvpath", False ) ) )

else: 
    log( "### %s v%s" % ( __addon__.getAddonInfo("id") , __addon__.getAddonInfo("version") ) )
    xbmc.executebuiltin('XBMC.RunScript(%s)' % os.path.join( RESOURCES_PATH , "tvtunes_scraper.py"))
