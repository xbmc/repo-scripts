#!/usr/bin/env python3

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

sys.path.append ('./resources/lib/')
sys.path.append ('./fakekodi')

from helper import SocketCom

sc = SocketCom("server")
if not sc.is_server_running():
	print("server is not running")
	sys.exit(0)

try:
	func = sys.argv[1]

	if func == "exit":
		sc.stop_server()
		sys.exit(0)

	target = sys.argv[2]
	try: args = sys.argv[3:]
	except Exception: args = []
except Exception:
	print('usage: query.py func target args...')
	sys.exit(0)

print(func,target,args)

print(sc.call_func(func,target,args))
