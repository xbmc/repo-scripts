import os, sys
import xbmc, xbmcaddon

__addon__    = xbmcaddon.Addon()
__addonid__  = __addon__.getAddonInfo('id')
__cwd__      = __addon__.getAddonInfo('path').decode("utf-8")
__language__ = __addon__.getLocalizedString
__resource__ = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ).encode("utf-8") ).decode("utf-8")

sys.path.append(__resource__)

from utils import *

if __name__ == '__main__':
    import gui
    screensaver_gui = gui.Screensaver('script-python-slideshow.xml', __cwd__, 'default')
    screensaver_gui.doModal()
    del screensaver_gui
