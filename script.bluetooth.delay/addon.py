import xbmc
import xbmcaddon
import os
import xbmcvfs

import sys
if sys.version > '3':
    xbmc.translatePath = xbmcvfs.translatePath

Addon = xbmcaddon.Addon('script.bluetooth.delay')

firstRun = Addon.getSetting('firstRun')
if firstRun == "false":
	import xbmcgui
	dialog = xbmcgui.Dialog()
	dialog.ok(Addon.getLocalizedString(30013), Addon.getLocalizedString(30014))
	Addon.setSettingBool('firstRun', 1)


d1 = Addon.getSetting('Device1')
d2 = Addon.getSetting('Device2')
script = xbmc.translatePath(os.path.join('special://home/addons/script.bluetooth.delay/AudioDelay.py'))

if d2 == d1:
	xbmcaddon.Addon().openSettings()
else:
	import AudioDelay
