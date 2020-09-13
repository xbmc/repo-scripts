import sys
from urllib.parse import unquote_plus
import xbmc
import xbmcaddon

LANGUAGE = xbmcaddon.Addon().getLocalizedString
CWD = xbmcaddon.Addon().getAddonInfo('path')

if (__name__ == '__main__'):
    try:
        params = dict(arg.split('=') for arg in sys.argv[1].split('&'))
    except:
        params = {}
    searchstring = unquote_plus(params.get('searchstring',''))
    if searchstring:
        del params['searchstring']
    else:
        keyboard = xbmc.Keyboard('', LANGUAGE(32101), False)
        keyboard.doModal()
        if (keyboard.isConfirmed()):
            searchstring = keyboard.getText()
    if searchstring:
        from lib import gui
        ui = gui.GUI('script-globalsearch.xml', CWD, 'default', '1080i', True, searchstring=searchstring, params=params)
        ui.doModal()
        del ui
