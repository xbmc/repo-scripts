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
import xbmcaddon

from basic import log
from basic import logerror
from basic import opthandle
from basic import path_addon
from basic import path_tmp
from basic import path_skin_root
from basic import path_skin
from basic import handle
from basic import get_user_setting

from helper.fjson import json

addon = xbmcaddon.Addon()
def tr(lid):
	return addon.getLocalizedString(lid)

def get_current_skin():
	resp = executeJSONRPC('{"jsonrpc":"2.0", "method":"Settings.GetSettingValue", "params":{ "setting":"lookandfeel.skin"}, "id":1}')
	skin = json.loads(resp)["result"]["value"][5:].lower()
	log("skin: {}".format(skin))
	return skin

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
		try:
			skicol = colors[skin]
			log("skin: {} defined".format(skin))
		except KeyError:
			log("skin: {} not defined".format(skin))
			skicol = {}

		for key,val in list(skicol.items()):
			defcol[key]= val

		defcol["button_tags"]="".join(defcol["button_tags"]).format(**defcol)
		defcol["button_textcolor"]="".join(defcol["button_textcolor"]).format(**defcol)
		defcol["button_radio"]="".join(defcol["button_radio"]).format(**defcol)
		defcol["progress_bar"]="".join(defcol["progress_bar"]).format(**defcol)
		defcol["background_img"]="".join(defcol["background_img"]).format(**defcol)

		return defcol

	except Exception as e: handle(e)

	return {}

def read_next_tag(tag_name, content, pos):
	start = content.find("<{}>".format(tag_name) ,pos)
	end = content.find("</{}>".format(tag_name) ,start)

	return content[start+len(tag_name) + 2:end]

def format_float(nr):
	if nr < 1000: return str(int(nr))
	fnr = float(nr) / 1000

	if round(fnr) == fnr:
		return "{:d}k".format(int(fnr))
	else:
		return "{:.1f}k".format(fnr)

def localize(content):
	follow_pos = 0
	result = []

	while True:
		pos = content.find("$LOCALIZE[",follow_pos)
		if pos < 0: break
		result.append(content[follow_pos: pos])

		follow_pos = pos + 10
		pos = content.find("]",follow_pos)

		lid = int(content[follow_pos: pos])
		result.append( addon.getLocalizedString(lid) )

		follow_pos = pos + 1

	result.append(content[follow_pos:])
	return "".join(result)

def get_valid_skin():
	try:
		skin = get_current_skin()
		skincol = skin
		if not os.path.exists(path_addon + path_skin.format(skin=skin) + "EqualizerDialog.xml"):
			skin = "Default"
	except Exception as e:
		handle(e)
		skin = "Default"
		skincol = skin

	color = get_skin_colors(skincol)

	return skin, color

def get_template(file_s, delimiter):
	with open(file_s["template"]) as f: content = f.read()

	result = []
	follow_pos = 0
	for deli in delimiter:
		pos = content.find(deli, follow_pos)
		if pos < 0:
			logerror("template not correct, did not find {}".format(deli))
			return []

		result.append(content[follow_pos: pos])
		follow_pos = pos + len(deli)

	result.append(content[follow_pos:])

	return result

def write_dialog(file_s, content):
	with open(file_s["tmp_dialog"], "w", encoding="utf-8") as f:
		f.write(content)

def file_struct(skin, fn_dialog_name):
	result = {}

	fn_path = path_skin.format(skin=skin)

	result["template"] = path_addon + fn_path + fn_dialog_name
	result["tmp_dialog"] = path_tmp + fn_path + fn_dialog_name

	create_temp_structure(skin)
	return result

def run_dialog(dialog, name, **kwargs):
	skin, color = get_valid_skin()
	file_s = file_struct(skin, name)

	kwargs["skin"]=skin
	kwargs["color"]=color
	kwargs["file_s"]=file_s

	with open( file_s["tmp_dialog"], "w"): pass

	ui = dialog(name, path_tmp, "Default", "720p", **kwargs)
	ui.doModal()

	os.remove(file_s["tmp_dialog"])

	try:
		return ui.result
	except Exception: return None

def get_frequencies():
	result = []
	default = "64, 125, 250, 500, 750, 1000,  2000,  3000,  4000,  8000, 16000"
	freqs = get_user_setting("frequencies",default).split(",")

	for freq in freqs:
		try:
			if freq[-1]=='k':
				result.append(float(freq[:-1])*1000)
			else:
				result.append(float(freq))
		except ValueError as e:
			opthandle(e)

	if len(result) > 1:
		return sorted(result)

	return [float(x) for x in default]
