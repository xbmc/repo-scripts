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
import sys

# default

path_tmp = "/run/user/%d/pa/" % os.geteuid()
path_pipe = "/run/user/%d/pa/" % os.geteuid()

path_addon = None
path_kodi = None
path_profile = None
path_masterprofile = None

path_settings = "addon_data/pulseequalizer/settings/"
path_filter = "addon_data/pulseequalizer/settings/spectrum/"

path_keymap = "keymaps/"

path_lib = "resources/lib/"
path_skin = "resources/skins/{skin}/1080i/"
path_skin_root = "resources/skins/"

try:
	if sys.version_info[0] > 2:
		from xbmcvfs import translatePath
	else:
		from xbmc import translatePath

	import xbmcaddon

	# ~/.kodi/addons/script.pulseequalizer.gui/
	path_addon = xbmcaddon.Addon().getAddonInfo('path') + "/"
	# ~/.kodi
	path_kodi = translatePath("special://home/")
	# specific
	path_profile = translatePath("special://profile/")
	# ~/.kodi/userdata
	path_masterprofile = translatePath("special://masterprofile/")

except ImportError:
	try:
		with open(path_tmp + "paths") as f:
			path_kodi, path_addon, path_masterprofile, path_profile = f.read().split(',')
	except OSError:
		p = os.path.realpath(__file__)
		path_addon = p[:p.rfind("/resources/") + 1]
		path_kodi = os.environ['HOME']+"/.kodi/"
		path_masterprofile = path_kodi + ".kodi/userdata/"
		path_profile = path_masterprofile

def try_copy(src, dst, is_dir=False):
	if os.path.exists(src):
		import shutil

		try:
			if is_dir  is True:
				shutil.copytree(src,dst)
			else:
				shutil.copy(src,dst)
		except OSError: pass

def assert_dir(dst):
	if not os.path.exists(dst):
		try: os.makedirs(dst)
		except OSError: pass

def create_paths():
	assert_dir(path_tmp)
	assert_dir(path_pipe)

	# migrate config data
	if not os.path.exists(path_profile + path_settings):
		assert_dir(path_profile + path_settings)

		try_copy(path_addon + "settings/config.json", path_profile + path_settings + "config.json")
		try_copy(path_addon + "settings/spectrum/profiles.json", path_profile + path_settings + "profiles.json")

	if not os.path.exists(path_masterprofile + path_filter):
		assert_dir(path_masterprofile + path_settings)

		try_copy(path_addon + "settings/spectrum",path_masterprofile + path_settings + "spectrum", True)

		assert_dir(path_masterprofile + path_filter)

		if os.path.exists(path_masterprofile + path_filter + "profiles.json"):
			os.remove(path_masterprofile + path_filter + "profiles.json")

	try:
		with open(path_tmp + "paths", "w") as f:
			f.write(",".join([path_kodi, path_addon, path_masterprofile, path_profile]))
	except OSError: pass
