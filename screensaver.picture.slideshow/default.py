import xbmcaddon

ADDON = xbmcaddon.Addon()
CWD = ADDON.getAddonInfo('path')
ADDONVERSION = ADDON.getAddonInfo('version')

from lib.utils import *

if __name__ == '__main__':
    log('script version %s started' % ADDONVERSION)
    from lib import gui
    screensaver_gui = gui.Screensaver('script-python-slideshow.xml', CWD, 'default')
    screensaver_gui.doModal()
    del screensaver_gui
log('script stopped')
