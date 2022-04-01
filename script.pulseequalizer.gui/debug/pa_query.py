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

from basic import handle

from pulseinterface import PulseControl

pc = PulseControl()
pc.start()

try:
	si = pc.get_server_info()
	for key in vars(si):
		print(key, getattr(si,key))

	print(sys.argv)
	cmd =  sys.argv[1]
	result = pc.get_list(cmd)

	for obj in result:
		print(obj.index, obj.name)
		for key,val in vars(obj).items():
			if key == "proplist":
				print("\tproplist:")
				for k,v in val.items():
					print("\t\t%s=%s" %(k,v))
			else:
				print("\t%s=%s" %(key,val))
		print("***************************************************")

except Exception as e: handle(e)
