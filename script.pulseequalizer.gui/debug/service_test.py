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
sys.path.append ('./resources/lib/')
sys.path.append ('./fakekodi')

from pulseinterface import PulseInterfaceService

em = PulseInterfaceService()

if sys.version_info[0] < 3:
	raw_input("Press Enter to continue...")
else:
	input("Press Enter to continue...")

em.stop_event_loop()
print("done")
