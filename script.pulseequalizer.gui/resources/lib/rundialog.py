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
import xbmcgui
from helper import *
from skin import get_current_skin, getSkinColors, create_temp_structure

def runDialog(dialog, template ,**kwargs):
	
	log("runDialog")
	try: 
		skin = get_current_skin()
		skincol = skin
		if not os.path.exists(path_addon + path_skin.format(skin=skin) + "%s.xml" % dialog): 
			skin = "Default"
	except Exception as e: 
		handle(e)
		skin = "Default"
		skincol = skin
	
	#
	#	create path structure
	#
		
	fn_dialog_name = "%s.xml" % template
	fn_path = path_skin.format(skin=skin)
	fn_path_template = path_addon + fn_path
	fn_path_dialog = path_tmp + fn_path
	create_temp_structure(skin)
	
	#
	#	get skin color scheme
	#

	colors = getSkinColors(skincol)

	#
	#	prepare template
	#


	
	with open( fn_path_template +  fn_dialog_name) as f: template = f.read()

	main = template.format(**colors)

	with open(fn_path_dialog + fn_dialog_name, "w") as f: f.write(main)

	#
	#	run Dialog
	#
	log("runDialog")
	dialog(fn_dialog_name, path_tmp, "Default", "720p", **kwargs).doModal()
	os.remove(fn_path_dialog + fn_dialog_name)
	
	
