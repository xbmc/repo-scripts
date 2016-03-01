import os, sys, urllib
import xbmc, xbmcaddon

ADDON        = xbmcaddon.Addon()
ADDONID      = ADDON.getAddonInfo('id')
ADDONVERSION = ADDON.getAddonInfo('version')
LANGUAGE     = ADDON.getLocalizedString
CWD          = ADDON.getAddonInfo('path').decode('utf-8')
RESOURCE   = xbmc.translatePath( os.path.join( CWD, 'resources', 'lib' ).encode('utf-8') ).decode('utf-8')

sys.path.append(RESOURCE)


if ( __name__ == '__main__' ):
    searchstring = None
    try:
        params = dict( arg.split( '=' ) for arg in sys.argv[ 1 ].split( '&' ) )
    except:
        params = {}
    searchstring = params.get('searchstring','')
    searchstring = urllib.unquote_plus(searchstring)
    if searchstring == '':
        keyboard = xbmc.Keyboard( '', LANGUAGE(32101), False )
        keyboard.doModal()
        if ( keyboard.isConfirmed() ):
            searchstring = keyboard.getText()
    else:
        del params['searchstring']
    if searchstring:
        import gui
        ui = gui.GUI( 'script-globalsearch-main.xml', CWD, 'default', searchstring=searchstring, params=params )
        ui.doModal()
        del ui
