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

from .minixml import parse_xml
from .minixml import arr_to_dic

from .path import path_profile
from .path import path_settings

def get_user_setting(setting_id, default):
	try:
		with open(path_profile + path_settings + "/settings.xml") as f:
			content = arr_to_dic("id",parse_xml(f.read())["settings"][0]["setting"])

		return content[setting_id]["val"]
	except OSError:
		return default
