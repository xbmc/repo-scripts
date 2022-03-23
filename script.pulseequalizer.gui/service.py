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
import xbmc
import xbmcaddon
import sys, os

addon	  = xbmcaddon.Addon()
addonname  = addon.getAddonInfo('name')
addonid    = addon.getAddonInfo('id')
cwd		= addon.getAddonInfo('path')

if sys.version_info[0] > 2:
	import xbmcvfs
	lib_path   = xbmcvfs.translatePath( os.path.join( cwd, 'resources', 'lib' ))
else:
	lib_path   = xbmc.translatePath( os.path.join( cwd, 'resources', 'lib' )).decode("utf-8")

sys.path.append (lib_path)

from pamonitor import PaMonitor

if ( __name__ == "__main__" ):
	PaMonitor()
