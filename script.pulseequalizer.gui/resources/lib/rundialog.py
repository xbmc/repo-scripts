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
import time

from basic import log
from basic import path_tmp

from skin import get_valid_skin
from skin import file_struct
from skin import localize
from skin import write_dialog

def runDialog(dialog, name ,**kwargs):
	name = "{}.xml".format(name)
	skin, color = get_valid_skin()
	file_s = file_struct(skin, name)

	#
	#	prepare template
	#

	with open( file_s["template"]) as f: template = f.read()

	write_dialog(file_s,localize(template.format(**color)))

	#
	#	run Dialog
	#
	log("runDialog")

	ui = dialog(name, path_tmp, "Default", "720p", **kwargs)
	ui.doModal()

	os.remove(file_s["tmp_dialog"])

	# wait for animation finished
	time.sleep(0.2)
