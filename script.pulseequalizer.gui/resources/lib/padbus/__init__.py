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

if sys.version_info[0] > 2:
	from .dbus_basic_3 import PulseDBus
else:
	from .dbus_basic_2 import PulseDBus

from .pulseerror import PulseDBusError
from . import interface as DBusInterface

