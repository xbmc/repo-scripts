
import os
import sys
import xbmcaddon
__scriptname__ = "GmailChecker"
__author__ = "Amet"
__url__ = ""
__svn_url__ = ""
__credits__ = ""
__version__ = "1.0.4"
__XBMC_Revision__ = "22240"


__settings__   = xbmcaddon.Addon(id='script.gmail.checker')
__language__   = __settings__.getLocalizedString
__cwd__        = __settings__.getAddonInfo('path')

BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) )
sys.path.append (BASE_RESOURCE_PATH)

if __name__ == "__main__":
    import gui
    ui = gui.GUI( "script-GmailChecker-main.xml" , __cwd__, "Default")
    ui.doModal()
    del ui
    sys.modules.clear()
            
