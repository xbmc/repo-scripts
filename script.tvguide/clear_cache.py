import os
import xbmc
import xbmcaddon
import xbmcgui

from strings import *

xbmc.log("Clearing TVGuide [script.tvguide] caches...")
cachePath = xbmc.translatePath(xbmcaddon.Addon(id = 'script.tvguide').getAddonInfo('profile'))

for file in os.listdir(cachePath):
    if file not in ['settings.xml', 'notification.db']:
        os.unlink(os.path.join(cachePath, file))

xbmcgui.Dialog().ok(strings(CLEAR_CACHE), strings(DONE))

xbmc.log("Clearing TVGuide [script.tvguide] caches. Done!")