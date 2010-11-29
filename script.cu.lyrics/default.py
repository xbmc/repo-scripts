# main import's 
import sys
import os
import xbmc
import xbmcaddon
# Script constants 
__scriptname__ = "CU Lyrics"
__author__ = "Amet, ZorMonkey"
__url__ = ""
__scriptid__ = "script.cu.lyrics"
__credits__ = "EnderW,Nuka1195"
__version__ = "0.9.2"
__XBMC_Revision__ = "30001"

# Shared resources 
__settings__   = xbmcaddon.Addon(id=__scriptid__)
__language__   = __settings__.getLocalizedString
__cwd__        = __settings__.getAddonInfo('path')

BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) )

sys.path.append (BASE_RESOURCE_PATH)

if ( __name__ == "__main__" ):
    import gui as gui
    window = "main"
    ui = gui.GUI( "script-XBMC_Lyrics-main.xml" , __cwd__, "Default" )
    ui.doModal()
    del ui
    sys.modules.clear()