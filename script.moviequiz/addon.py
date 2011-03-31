import xbmcaddon

from quizlib.gui import MenuGui

if __name__ == '__main__':
    addon = xbmcaddon.Addon(id = 'script.moviequiz')
    path = addon.getAddonInfo('path')

    w = MenuGui('script-moviequiz-menu.xml', path, addon = addon)
    w.doModal()
    del w

