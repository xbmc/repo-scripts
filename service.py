import xbmc
import xbmcaddon
import os
import time
import xbmcvfs

import sys
if sys.version > '3':
    xbmc.translatePath = xbmcvfs.translatePath

Addon = xbmcaddon.Addon('script.bluetooth.delay')

XML = xbmc.translatePath('special://profile/addon_data/script.bluetooth.delay/settings.xml')
while not os.path.exists(XML):
	time.sleep(1)
time14 = os.path.getmtime(XML)

ft = xbmc.translatePath('special://profile/keymaps/bluetooth_delay_toggle.xml')
f1 = xbmc.translatePath('special://profile/keymaps/bluetooth_delay_device1.xml')
f2 = xbmc.translatePath('special://profile/keymaps/bluetooth_delay_device2.xml')

monitor = xbmc.Monitor()
while not monitor.abortRequested():

	time13 = os.path.getmtime(XML)
	if time14 != time13:

		st = Addon.getSetting('Toggle')
		s1 = Addon.getSetting('s1')
		s2 = Addon.getSetting('s2')

		if st == "None":
			if os.path.exists(ft):
				os.remove(ft)
		else:
			f = open(ft, 'w')
			f.write("<keymap><Global><keyboard><" + st + ">RunScript(special://home/addons/script.bluetooth.delay/AudioDelay.py)</" + st + "></keyboard></Global></keymap>")
			f.close()

		if s1 == "None":
			if os.path.exists(f1):
				os.remove(f1)
		else:
			f = open(f1, 'w')
			f.write("<keymap><Global><keyboard><" + s1 + ">RunScript(special://home/addons/script.bluetooth.delay/Device1.py)</" + s1 + "></keyboard></Global></keymap>")
			f.close()

		if s2 == "None":
			if os.path.exists(f2):
				os.remove(f2)
		else:
			f = open(f2, 'w')
			f.write("<keymap><Global><keyboard><" + s2 + ">RunScript(special://home/addons/script.bluetooth.delay/Device2.py)</" + s2 + "></keyboard></Global></keymap>")
			f.close()

		time.sleep(1)
		xbmc.executebuiltin('Action(reloadkeymaps)')
		xbmc.executebuiltin('Action(reloadkeymaps)')

	time14 = os.path.getmtime(XML)
	monitor.waitForAbort(1)