import os, sys
import xbmc, xbmcaddon

__addon__        = xbmcaddon.Addon()
__addonid__      = __addon__.getAddonInfo('id')
__addonversion__ = __addon__.getAddonInfo('version')
__language__     = __addon__.getLocalizedString
__cwd__          = __addon__.getAddonInfo('path').decode("utf-8")
__resource__   = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ).encode("utf-8") ).decode("utf-8")

sys.path.append(__resource__)


if ( __name__ == "__main__" ):
    searchstring = None
    try:
        params = dict( arg.split( "=" ) for arg in sys.argv[ 1 ].split( "&" ) )
        searchstring = params.get("searchstring")
        searchstring = urllib.unquote_plus(searchstring)
    except:
        keyboard = xbmc.Keyboard( '', __language__(32101), False )
        keyboard.doModal()
        if ( keyboard.isConfirmed() ):
            searchstring = keyboard.getText()
    if searchstring:
        import gui
        ui = gui.GUI( "script-globalsearch-main.xml", __cwd__, "Default", searchstring=searchstring )
        ui.doModal()
        del ui
