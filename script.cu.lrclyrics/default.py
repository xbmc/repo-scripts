# main import's 
import sys
import os
import xbmc
import xbmcaddon

# Script constants 
__addon__     = xbmcaddon.Addon()
__addonname__ = __addon__.getAddonInfo('name')
__cwd__       = xbmc.translatePath(__addon__.getAddonInfo('path')).decode("utf-8")
__profile__   = xbmc.translatePath(__addon__.getAddonInfo('profile')).decode("utf-8")
__language__  = __addon__.getLocalizedString

# Shared resources
BASE_RESOURCE_PATH = os.path.join(__cwd__, 'resources', 'lib')
sys.path.append (BASE_RESOURCE_PATH)

# Start the main gui
if ( __name__ == "__main__" ):
    import gui
    ui = gui.GUI( "script-XBMC_Lyrics-main.xml" , __cwd__, "Default" )
    ui.doModal()
    del ui
    sys.modules.clear()
