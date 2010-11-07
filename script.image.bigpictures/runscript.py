import sys
import xbmcaddon

Addon = xbmcaddon.Addon('script.image.bigpictures')

# Script constants
__scriptname__ =  Addon.getAddonInfo('name')
__id__ = Addon.getAddonInfo('id')
__author__ = Addon.getAddonInfo('author')
__version__ = Addon.getAddonInfo('version')
__path__ = Addon.getAddonInfo('path')

print '[SCRIPT][%s] version %s initialized!' % (__scriptname__, __version__)

if (__name__ == '__main__'):
    import resources.lib.gui as gui
    ui = gui.GUI( 'script-' + __scriptname__ + '-main.xml', __path__, 'default' )
    ui.doModal()
    del ui
    sys.modules.clear()
