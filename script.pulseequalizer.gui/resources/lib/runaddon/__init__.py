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

from basic import path_pipe
from basic import get_user_setting
from basic import log
from basic import handle

def run_direct(cmd):
	from menus import Menu

	try:
		log("addon: start script.pulseequalizer.gui addon")

		m = Menu()
		m.sel_menu(cmd)

		log("addon: end script.pulseequalizer.gui addon")

	except Exception as e: handle(e)

def run_on_service(cmd):
	try:
		pname = "{}menu.{}".format(path_pipe,os.getppid())
		cmd = "{}".format(cmd)
		with open(pname, "w") as f: f.write(cmd)

	except Exception as e:
		from resources.lib.basic import handle
		handle(e)

def run_addon():
	lock = path_pipe + "lock"

	if not os.path.exists( lock ):
		# check if another instance of this script is already running
		# only allow one instance or the script per user
		service_mode = False
		try: cmd = sys.argv[1]
		except Exception:	cmd = "None"

		try:
			open(lock,'w')
			if get_user_setting("servermode","true") == "true":
				service_mode = True
				run_on_service(cmd)
			else:
				run_direct(cmd)

		except OSError: pass
		finally:
			if not service_mode:
				try: os.remove(lock)
				except OSError: pass
