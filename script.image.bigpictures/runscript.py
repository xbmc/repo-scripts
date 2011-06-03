import sys
import xbmcaddon
import xbmc

Addon = xbmcaddon.Addon('script.image.bigpictures')

# Script constants
__scriptname__ = Addon.getAddonInfo('name')
__id__ = Addon.getAddonInfo('id')
__author__ = Addon.getAddonInfo('author')
__version__ = Addon.getAddonInfo('version')
__path__ = Addon.getAddonInfo('path')
__cachedir__ = xbmc.translatePath('special://profile/addon_data/%s/cache/'
                                  % __id__)

print '[SCRIPT][%s] version %s initialized!' % (__scriptname__, __version__)

if (__name__ == '__main__'):
    import resources.lib.gui as gui
    ui = gui.GUI('script-%s-main.xml' % __scriptname__,
                 __path__,
                 'default',
                 '720p')
    ui.doModal()
    print '[SCRIPT][%s] version %s exited!' % (__scriptname__, __version__)
    del ui
    sys.modules.clear()
