import sys

import xbmc
import xbmcaddon

Addon = xbmcaddon.Addon('script.game.whatthemovie')

# Script constants
__addonname__ = Addon.getAddonInfo('name')
__id__ = Addon.getAddonInfo('id')
__version__ = Addon.getAddonInfo('version')
__path__ = Addon.getAddonInfo('path')

xbmc.log('[ADDON][%s] Version %s started'
         % (__addonname__, __version__), level=xbmc.LOGNOTICE)

if (__name__ == '__main__'):
    import resources.lib.gui as gui
    ui = gui.GUI('script-%s-main.xml' % __addonname__,
                 __path__,
                 'default',
                 '720p')
    ui.doModal()
    xbmc.log('[ADDON][%s] Version %s exited'
             % (__addonname__, __version__), level=xbmc.LOGNOTICE)
    del ui

sys.modules.clear()
