# main import's 
import sys
import os
import xbmc
import xbmcaddon

# Script constants 
__scriptname__ = "LRC Lyrics"
__scriptid__ = "script.lrclyrics"
__author__ = "Taxigps"
__url__ = "http://code.google.com/p/xbmc-addons-chinese/"
__credits__ = "EnderW,Nuka1195"
__version__ = "1.3.3"
__XBMC_Revision__ = "30001"

# Shared resources 
BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( os.getcwd(), 'resources', 'lib' ) )

sys.path.append (BASE_RESOURCE_PATH)

__settings__ = xbmcaddon.Addon(id=__scriptid__)
__language__ = __settings__.getLocalizedString

# Start the main gui
if ( __name__ == "__main__" ):
    import gui as gui
    window = "main"
    ui = gui.GUI( "script-XBMC_Lyrics-main.xml" , os.getcwd(), "Default" )
    ui.doModal()
    del ui
    sys.modules.clear()