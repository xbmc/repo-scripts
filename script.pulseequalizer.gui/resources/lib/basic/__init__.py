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

from .log import log,loginfo,logerror
from .handle import handle,infhandle,opthandle
from .path import path_tmp ,path_pipe,path_addon,path_kodi,path_profile,path_masterprofile,path_settings,path_filter,path_keymap,path_lib,path_skin,path_skin_root

def get_args(argv):
	try: cmd = argv[1]
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

def run_direct(argv):
	from basic import log
	from basic import handle
	from menus import Menu
	import xbmcaddon

	cwd	= xbmcaddon.Addon().getAddonInfo('path')
	try:
		log("addon: start script.pulseequalizer.gui addon")

		m = Menu(cwd)
		cmd,step = get_args(argv)
		m.sel_menu(cmd,step)

		log("addon: end script.pulseequalizer.gui addon")

	except Exception as e: handle(e)

def run_on_service(argv):
	try:
		pname = "{}menu.{}".format(path_pipe,os.getppid())
		cmd, step = get_args(argv)
		cmd = "{},{}".format(cmd,step)
		with open(pname, "w") as f: f.write(cmd)

	except Exception as e:
		from resources.lib.basic import handle
		handle(e)

def run_addon(argv):
	lock = path_pipe + "lock"
	service_mode = True

	if not os.path.exists( lock ):
		# check if another instance of this script is already running
		# only allow one instance or the script per user

		try:
			open(lock,'w')
			if service_mode:
				run_on_service(argv)
			else:
				run_direct(argv)
		except OSError: pass
		finally:
			if not service_mode:
				try: os.remove(lock)
				except OSError: pass
