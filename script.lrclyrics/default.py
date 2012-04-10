# main import's 
import sys
import os
import xbmc
import xbmcaddon

# Script constants 
__scriptname__ = "LRC Lyrics"
__scriptid__   = "script.lrclyrics"
__author__     = "Taxigps"
__credits__    = "EnderW,Nuka1195"
__settings__   = xbmcaddon.Addon(id=__scriptid__)
__language__   = __settings__.getLocalizedString
__version__    = __settings__.getAddonInfo('version')
__cwd__        = xbmc.translatePath( __settings__.getAddonInfo('path') )
__profile__    = xbmc.translatePath( __settings__.getAddonInfo('profile') )

# Shared resources 
BASE_RESOURCE_PATH = os.path.join( __cwd__, 'resources', 'lib' )

sys.path.append (BASE_RESOURCE_PATH.decode("utf-8"))

# Start the main gui
if ( __name__ == "__main__" ):
    import gui
    ui = gui.GUI( "script-XBMC_Lyrics-main.xml" , __cwd__, "Default" )
    ui.doModal()
    del ui
    sys.modules.clear()
