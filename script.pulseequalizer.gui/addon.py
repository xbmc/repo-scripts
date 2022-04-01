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
import os

import xbmcaddon

cwd	= xbmcaddon.Addon().getAddonInfo('path')
sys.path.append ( os.path.join( cwd, 'resources', 'lib' ))
sys.path.append ( os.path.join( cwd, 'resources', 'language' ))

from basic import run_addon

run_addon(sys.argv)
