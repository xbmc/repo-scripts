#!/usr/bin/python3

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

import sys
import time
import subprocess
import os

from basic import log

class PulseService:
	def start(self):
		if sys.version_info[0] > 2:
			self.ps = subprocess.Popen(["python3",os.path.realpath(__file__), str(os.getpid())])
		else:
			self.ps = subprocess.Popen(["python2",os.path.realpath(__file__), str(os.getpid())])

	def stop(self):
		from helper.socketcom import SocketCom
		sc = SocketCom("server")
		sc.send("stop","service",[str(os.getpid())])
		self.ps.wait()

if __name__ == '__main__':
	from pulseinterface import PulseInterfaceService
	log("pulseservice start")
	try: gid = sys.argv[1]
	except Exception: gid = 0

	em = PulseInterfaceService(gid)

	if em.service_owner:
		while True:
			time.sleep(0.2)
			if not em.pulseloop: break

	else:
		log("service is already running")

log("pulseservice ended")
