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
import re

from .skincolor import *
from helper import log, path_addon, path_tmp, path_skin, path_skin_root
from xbmc import executeJSONRPC

def get_current_skin():
	return re.findall(".*?skin\.(.*?)\"",executeJSONRPC('{"jsonrpc":"2.0", "method":"Settings.GetSettingValue", "params":{ "setting":"lookandfeel.skin"}, "id":1}'))[0].lower()

def find_file(file_name, directory_name):
	files_found = []
	for path, subdirs, files in os.walk(directory_name):
		for name in files:
			if(file_name == name.lower()):
				file_path = os.path.join(path,name)
				files_found.append(file_path)
	return files_found

def create_temp_structure(skin):
	srcpath = path_addon + path_skin_root + "%s/" % skin
	dstpath = path_tmp   + path_skin_root + "%s/" % skin

	xmlpath = dstpath + "1080i/"
	if not os.path.exists(xmlpath):os.makedirs(xmlpath)

	for fn in os.listdir(srcpath):
		if not os.path.exists(dstpath+fn): os.symlink(srcpath+fn, dstpath+fn)

def tags(content):
	result = {}
	tags = re.compile('<\s*([^\s>]+)([^>]*?)>(.*?)<\s*/', re.DOTALL | re.I).findall(content)
	for tag, inner, value in tags:
		result[tag]=(inner,value)

	return result

def scan_file(file_name, wants):
	with open(file_name) as f: content = f.read()
	objects = re.compile('<default\s+type=\"([^\"]*?)\"[^>]*?>\s*(.*?)</default>', re.DOTALL | re.I).findall(content)
	result = {}
	for name, data in objects:
		if name in wants: result[name]=tags(data)

	return result

def scan_context_menu(file_name):
	with open(file_name) as f: content = f.read()
	result = {}
	try: result["image"] =  tags(re.compile('<control\s+type\s*=\s*"image"\s*id\s*=\s*"999".*?>(.*?)</control>', re.DOTALL | re.I).findall(content)[0])
	except Exception: result["image"] = {}

	try: result["button"] =  tags(re.compile('<control\s+type\s*=\s*"button"\s*id\s*=\s*"1000".*?>(.*?)</control>', re.DOTALL | re.I).findall(content)[0])
	except Exception: result["button"] = {}

	return result

def get_default_control( skin , controls):
	path_addons , c = os.path.split(path_addon[:-1])

	objects = {}
	files = find_file("defaults.xml",path_addons + "/skin." + skin)
	for fn in files:
		objects = scan_file(fn, controls)
		if objects: break

	return objects

def get_context_menu(skin):
	path_addons , c = os.path.split(path_addon[:-1])
	objects = {}
	files = find_file("dialogcontextmenu.xml",path_addons + "/skin." + skin)

	for fn in files:
		objects = scan_context_menu(fn)
		if objects: break

	return objects

def scan_obj(content, obj, tag):
	control = re.search('<default\s+type\s*=\s*"%s".*?</default>' % obj,content, re.DOTALL | re.I)
	if not control: return None
	col = re.search('<%s.*?>(.*?)</%s>' % (tag,tag),control.group(0), re.DOTALL | re.I)
	if not col: return None
	return col.group(1)

def get_sel_color(skin):
	path_addons , c = os.path.split(path_addon[:-1])
	col = None
	files = find_file("defaults.xml",path_addons + "/skin." + skin)
	for fn in files:
		with open(fn) as f: content = f.read()
		col = scan_obj(content,"label","selectedcolor")
		but = scan_obj(content,"button","textcolor")
		but_sel = scan_obj(content,"button","selectedcolor")
		if col or but or but_sel: break
	return but, but_sel, col

def scan_bk_image(file_name):
	with open(file_name) as f: content = f.read()
	img = re.search('<control\s+type\s*=\s*"image"\s*id\s*=\s*"999".*?>.*?</control>', content, re.DOTALL | re.I)
	if not img: return None
	tex = re.search('<texture[\s+>].*?</texture>', img.group(0), re.DOTALL | re.I)
	if tex:	return tex.group(0)

	inc = re.search('<include>(.*?)</include>', img.group(0), re.DOTALL | re.I)
	if not inc: return None

	path , c = os.path.split(file_name)
	file_name = find_file("includes.xml",path)
	if not file_name: return None
	with open(file_name[0]) as f: content = f.read()

	img = re.search('<include\s+name\s*=\s*"%s".*?</include>' % inc.group(1), content, re.DOTALL | re.I)
	if not img: return None

	tex = re.search('<texture[\s+>].*?</texture>', img.group(0), re.DOTALL | re.I)
	if tex:	return tex.group(0)
	return None

def get_bk_image(skin):
	path_addons , c = os.path.split(path_addon[:-1])
	bk = None
	files = find_file("dialogcontextmenu.xml",path_addons + "/skin." + skin)

	for fn in files:
		bk = scan_bk_image(fn)
		if bk:
			bk = re.sub('\s+border\s*=\s*".*?"','',bk)
			break

	return bk

