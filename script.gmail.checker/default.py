
import os
import sys
import xbmcaddon

__author__     = "amet"
__scriptid__   = "script.gmail.checker"
__scriptname__ = "GmailChecker"

__addon__      = xbmcaddon.Addon(id=__scriptid__)

__cwd__        = __addon__.getAddonInfo('path')
__version__    = __addon__.getAddonInfo('version')
__language__   = __addon__.getLocalizedString

__profile__    = xbmc.translatePath( __addon__.getAddonInfo('profile') )
__resource__   = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) )

sys.path.append (__resource__)

if __name__ == "__main__":
    import gui
    ui = gui.GUI( "script-GmailChecker-main.xml" , __cwd__, "Default")
    ui.doModal()
    del ui
    sys.modules.clear()
            
