import os
import xbmc
import xbmcaddon
import xbmcgui

from strings import *


xbmc.log("Clearing TVGuide [script.tvguide] caches...")
cachePath = xbmc.translatePath(xbmcaddon.Addon(id = 'script.tvguide').getAddonInfo('profile'))

for file in os.listdir(cachePath):
    if file != 'settings.xml':
        os.unlink(os.path.join(cachePath, file))

xbmcgui.Dialog().ok(strings(CLEAR_CACHE), strings(CLEAR_CACHE_DONE))

xbmc.log("Clearing TVGuide [script.tvguide] caches. Done!")