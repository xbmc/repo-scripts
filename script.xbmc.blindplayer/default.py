import sys
import os
import xbmc
import xbmcaddon

__scriptid__   = "script.xbmc.blindplayer"
__addon__      = xbmcaddon.Addon(id=__scriptid__)
__language__   = __addon__.getLocalizedString
__version__    = __addon__.getAddonInfo('version')
__cwd__        = __addon__.getAddonInfo('path')
__scriptname__ = "A player with remote control sufficient."
__author__     = "prudy"
__resource__   = xbmc.translatePath( os.path.join( __cwd__, 'resources') )
__lib__        = xbmc.translatePath( os.path.join( __resource__, 'lib' ) )

sys.path.append (__lib__)

xbmc.log("### [%s] - Version: %s" % (__scriptname__,__version__,),level=xbmc.LOGDEBUG )

if ( __name__ == "__main__" ):
    import gui
    if len(sys.argv) > 1:
       gui.BlindPlayer(sys.argv[1])
    else:
       gui.BlindPlayer()
    sys.modules.clear()
