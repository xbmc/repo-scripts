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
import os, re

try: path_addon = re.findall(".*?/resources/", os.path.realpath(__file__),re.DOTALL | re.I)[0][:-10]
except Exception: path_addon = None

path_socket = "/run/user/%d/pa/" % os.geteuid()
path_tmp = "/run/user/%d/pa/" % os.geteuid()
path_settings = "settings/"
path_filter = "settings/spectrum/"
path_lib = "resources/lib/"
path_skin = "resources/skins/{skin}/1080i/"
path_skin_root = "resources/skins/"

