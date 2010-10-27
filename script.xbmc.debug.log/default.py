import sys
import os
import xbmc
import xbmcaddon

__scriptid__   = "script.xbmc.debug.log"
__settings__   = xbmcaddon.Addon(id=__scriptid__)
__language__   = __settings__.getLocalizedString
__version__    = __settings__.getAddonInfo('version')
__cwd__        = __settings__.getAddonInfo('path')
__scriptname__ = "XBMC Debug Log"
__author__     = "Team XBMC"

BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) )
sys.path.append (BASE_RESOURCE_PATH)

xbmc.output("### [%s] - Version: %s" % (__scriptname__,__version__,),level=xbmc.LOGDEBUG )

if ( __name__ == "__main__" ):
    import gui
    ui = gui.GUI( "script-XBMC-debug-log-main.xml" , __cwd__ , "Default")
    ui.doModal()
    del ui
    sys.modules.clear()


  
