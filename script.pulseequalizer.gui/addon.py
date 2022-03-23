#	This file is part of PulseEqualizerGui for Kodi.
#
#	Copyright (C) 2021 wastis    https://github.com/wastis/PulseEqualizerGui
#
#	PulseEqualizerGui is free software; you can redistribute it and/or modify
#	it under the terms of the GNU Lesser General Public License as published
#	by the Free Software Foundation; either version 3 of the License,
#	or (at your option) any later version.
#
#

import os
import sys

lock = "/run/user/%d/pa/lock" % os.geteuid()


def sel_vol(cwd, updown, step):
	from volumegui import VolumeGui
	volgui = VolumeGui("OsdVolume.xml" , cwd, "Default", updown = updown, step=step)
	volgui.doModal()

def run_addon():
	try:

		import xbmc
		import xbmcaddon

		xbmc.log("eq: start script.pulseequalizer.gui addon" , xbmc.LOGDEBUG)

		cwd		= xbmcaddon.Addon().getAddonInfo('path')
		sys.path.append ( os.path.join( cwd, 'resources', 'lib' ))
		sys.path.append ( os.path.join( cwd, 'resources', 'language' ))

		try: cmd = sys.argv[1]
		except Exception:	cmd = False
		try: step = int(sys.argv[2])
		except Exception:	step = False

		# handle volup/voldown here to avoid unneccecary imports that slow down
		if cmd == "volup": sel_vol(cwd,"up",step)
		elif cmd == "voldown": sel_vol(cwd,"down",step)
		else:

			from helper import handle, log, logerror
			from menus import Menu

			if not step:
				try: 
					step = int(cmd)
					if step > 0: cmd = False
				except ValueError: step = 1

			if step < 1: step = 1

			m = Menu(cwd, step)
			if cmd:
				xbmc.log("eq: keypress %s startup, step: %d" % (cmd,step) , xbmc.LOGDEBUG)
				m.sel_menu(cmd)
			else:
				xbmc.log("eq: start main menu, step: %d" % step , xbmc.LOGDEBUG)
				m.sel_main_menu()

		xbmc.log("eq: end script.pulseequalizer.gui addon" , xbmc.LOGDEBUG)

	except Exception as e: handle(e)

if not os.path.exists( lock ):
	# check if another instance of this script is already running
	# only allow one instance or the script per user

	try:
		open(lock,'w')
		run_addon()
	finally:
		from helper import opthandle
		try:
			os.remove(lock)
		except Exception as e: opthandle(e)

