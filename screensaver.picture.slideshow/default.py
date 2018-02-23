import os, sys
import xbmc, xbmcaddon

ADDON        = xbmcaddon.Addon()
ADDONID      = ADDON.getAddonInfo('id')
CWD          = ADDON.getAddonInfo('path')
ADDONVERSION = ADDON.getAddonInfo('version')
LANGUAGE     = ADDON.getLocalizedString
RESOURCE     = xbmc.translatePath(os.path.join(CWD, 'resources', 'lib'))

sys.path.append(RESOURCE)

from utils import *

if __name__ == '__main__':
    log('script version %s started' % ADDONVERSION)
    import gui
    screensaver_gui = gui.Screensaver('script-python-slideshow.xml', CWD, 'default')
    screensaver_gui.doModal()
    del screensaver_gui
log('script stopped')
