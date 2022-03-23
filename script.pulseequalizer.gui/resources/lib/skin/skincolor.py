#	This file is part of PulseEqualizerGui for Kodi.
#
#	Copyright (C) 2021 wastis    https://github.com/wastis/PulseEqualizerGui
#
#	PulseEqualizerGui is free software; you can redistribute it and/or modify
#	it under the terms of the GNU Lesser General Public License as published
#	by the Free Software Foundation; either version 3 of the License,
#	or (at your option) any later version.

import json

from helper import handle, path_addon

def getSkinColors(skin):
	try:
		with open(path_addon + "resources/skins/Default/skincolors.json") as f:
			colors = json.loads(f.read())

		defcol = colors["default"]
		try: skicol = colors[skin]
		except Exception: skicol = {}

		for key,val in skicol.items():
			defcol[key]= val

		return defcol

	except Exception as e: handle(e)

	return {}
