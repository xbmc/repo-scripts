# main import's 
import sys
import os
import xbmc
import xbmcaddon
# Script constants 
__scriptname__ = "CU Lyrics"
__author__ = "Amet, ZorMonkey"
__url__ = "http://xbmc.org/forum/showthread.php?p=449687"
__scriptid__ = "script.cu.lyrics"
__credits__ = "EnderW,Nuka1195"
__version__ = "0.8.5"
__XBMC_Revision__ = "29565"

# Shared resources 
BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( os.getcwd(), 'resources', 'lib' ) )

sys.path.append (BASE_RESOURCE_PATH)

__settings__ = xbmcaddon.Addon(id='script.xbmc.subtitles')
__language__ = __settings__.getLocalizedString
if ( __name__ == "__main__" ):
    if ( xbmc.Player().isPlayingAudio() ):
        import gui as gui
        window = "main"
        ui = gui.GUI( "script-XBMC_Lyrics-main.xml" , os.getcwd(), "Default" )
        ui.doModal()
        del ui
    else:
        __settings__.openSettings()
    
    
    sys.modules.clear()