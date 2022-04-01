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

import xbmcaddon

cwd	= xbmcaddon.Addon().getAddonInfo('path')
sys.path.append ( os.path.join( cwd, 'resources', 'lib' ))
sys.path.append ( os.path.join( cwd, 'resources', 'language' ))

from basic import path_pipe

lock = path_pipe + "lock"

service_mode = True

def get_args():
	try: cmd = sys.argv[1]
	except Exception:	cmd = "None"
	try: step = int(sys.argv[2])
	except Exception:	step = False

	if not step:
		try:
			step = int(cmd)
			if step > 0: cmd = "None"
		except ValueError: step = 1

	if step < 1: step = 1
	return (cmd, step)

def run_addon():
	from basic import log
	from basic import handle
	from menus import Menu

	try:
		log("addon: start script.pulseequalizer.gui addon")

		m = Menu(cwd)
		cmd,step = get_args()
		m.sel_menu(cmd,step)

		log("addon: end script.pulseequalizer.gui addon")

	except Exception as e: handle(e)

def run_on_service():
	try:
		pname = "{}menu.{}".format(path_pipe,os.getppid())
		cmd, step = get_args()
		cmd = "{},{}".format(cmd,step)
		with open(pname, "w") as f: f.write(cmd)

	except Exception as e:
		from resources.lib.basic import handle
		handle(e)

if not os.path.exists( lock ):
	# check if another instance of this script is already running
	# only allow one instance or the script per user

	try:
		open(lock,'w')
		if service_mode:
			run_on_service()
		else:
			run_addon()
	except OSError: pass
	finally:
		if not service_mode:
			try: os.remove(lock)
			except OSError: pass
