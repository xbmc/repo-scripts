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

from xbmc import executeJSONRPC

from basic import log
from basic import path_addon
from basic import path_tmp
from basic import path_skin_root
from basic import handle
from helper.fjson import json

def get_current_skin():
	resp = executeJSONRPC('{"jsonrpc":"2.0", "method":"Settings.GetSettingValue", "params":{ "setting":"lookandfeel.skin"}, "id":1}')
	return json.loads(resp)["result"]["value"][5:].lower()

def create_temp_structure(skin):
	srcpath = path_addon + path_skin_root + "%s/" % skin
	dstpath = path_tmp   + path_skin_root + "%s/" % skin

	xmlpath = dstpath + "1080i/"
	if not os.path.exists(xmlpath):os.makedirs(xmlpath)

	for fn in os.listdir(srcpath):
		if not os.path.exists(dstpath+fn): os.symlink(srcpath+fn, dstpath+fn)

def get_skin_colors(skin):
	try:
		with open(path_addon + "resources/skins/Default/skincolors.json") as f:
			colors = json.loads(f.read())

		defcol = colors["default"]
		try: skicol = colors[skin]
		except Exception: skicol = {}

		for key,val in list(skicol.items()):
			defcol[key]= val

		return defcol

	except Exception as e: handle(e)

	return {}
