# Qlock screensaver add-on by phil65
# credits to donabi & amet

import os
import sys
import xbmcaddon
import xbmc

__addon__ = xbmcaddon.Addon()
__addonid__ = __addon__.getAddonInfo('id')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib').encode("utf-8")).decode("utf-8")

sys.path.append(__resource__)

if __name__ == '__main__':
    import gui
    screensaver_gui = gui.Screensaver('script-python-qlock.xml', __cwd__, 'default')
    screensaver_gui.doModal()
