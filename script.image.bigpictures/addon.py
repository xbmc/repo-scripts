import os
import sys
import xbmcaddon
import xbmc

Addon = xbmcaddon.Addon('script.image.bigpictures')

__addon_name__ = Addon.getAddonInfo('name')
__version__ = Addon.getAddonInfo('version')

ADDON_PATH = Addon.getAddonInfo('path').decode('utf-8')
CACHE_PATH = xbmc.translatePath(Addon.getAddonInfo('profile').decode('utf-8'))
SCRAPERS_PATH = os.path.join(ADDON_PATH, 'resources', 'lib', 'scrapers')


def log(text):
    xbmc.log('%s: %s' % (__addon_name__, text))

if (__name__ == '__main__'):
    if 'plugin' in sys.argv[0]:
        log('addon version: %s started in PLUGIN-mode' % __version__)
        import resources.lib.plugin as plugin
        plugin.run()
        log('addon: PLUGIN-mode exited')
    else:
        log('addon version: %s started in SCRIPT-mode' % __version__)
        import resources.lib.script as script
        skin = 'script-%s-main.xml' % __addon_name__
        script.GUI(skin, ADDON_PATH).doModal()
        log('addon: SCRIPT-mode exited')
