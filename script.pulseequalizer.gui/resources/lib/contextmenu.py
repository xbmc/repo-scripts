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
import xbmcgui

import os
import re

from helper import handle, opthandle, log, path_addon, path_tmp, path_skin
from skin import get_current_skin, getSkinColors, create_temp_structure

class ContextGui(  xbmcgui.WindowXMLDialog  ):
	'''Main Context Menu

		the context menu is build dynamically
	'''

	result = None
	index = None

	items = []
	funcs = []
	def __init__(self, *args, **kwargs ):
		try:
			self.items = kwargs["items"]
			self.index = self.items.index(kwargs["default"])
		except Exception: self.index = None

		try: self.funcs = kwargs["funcs"]
		except Exception: self.funcs = []

	def onInit( self ):
		if self.index is not None:
			self.setFocusId(5000 + self.index)

		iid = 5000
		for label in self.items:
			self.getControl(iid).setLabel(label)
			iid = iid + 1

		for label,_ in self.funcs:
			self.getControl(iid).setLabel(label)
			iid = iid + 1

	def onAction( self, action ):
		aid = action.getId()

		#OK pressed
		if aid in [7,100]:
			iid = self.getFocusId()
			if iid >= 5000: self.result = iid - 5000
			self.close()

		#Cancel
		if aid in [92,10]:
			self.close()

def contextMenu(**kwargs):
	try: items = kwargs["items"]
	except Exception: items = []

	try: default = kwargs["default"]
	except Exception: default = None

	try: callback = kwargs["callback"]
	except Exception: callback = None

	try: funcs = kwargs["funcs"]
	except Exception: funcs = []

	try: fwidth = int( kwargs["width"] )
	except Exception: fwidth = None

	try:
		skin = get_current_skin()
		skincol = skin
		log("skin: '%s'"%skin)
		if not os.path.exists(path_addon + path_skin.format(skin=skin) + "ContextMenu.xml"):
			skin = "Default"
	except Exception as e:
		handle(e)
		skin = "Default"
		skincol = skin

	#
	#	create path structure
	#

	fn_dialog_name = "ContextMenu.xml"
	fn_path = path_skin.format(skin=skin)
	fn_path_template = path_addon + fn_path
	fn_path_dialog = path_tmp + fn_path
	create_temp_structure(skin)

	#
	#	get skin color scheme
	#

	colors = getSkinColors(skincol)

	col_select = 	colors["col_select"]
	col_focus = 	colors["col_textfocus"]
	col_text = 		colors["col_text"]

	#
	#	prepare template
	#

	with open( fn_path_template +  fn_dialog_name) as f: template = f.read()

	header, group, bottom = template.split("<!-- item group -->")
	gheader, button, gbottom = group.split("<!-- button -->")

	# get info from the template
	bh = int(re.search('<height>(.*?)</height>',button).group(1))

	if fwidth:
		bw = fwidth
		button = re.sub('<width>.*?</width>','<width>%s</width>'% bw,button)
	else: bw = int(re.search('<width>(.*?)</width>',button).group(1))

	try: itemgap = int(re.search('<itemgap>(.*?)</itemgap>',gheader, re.DOTALL | re.I).group(1))
	except Exception: itemgap = 10

	#
	#	create button lists
	#
	l_cnt = 0
	if len(funcs) > 0:
		onright = "701"
		l_cnt = l_cnt + 1
	else:
		onright = ""

	if len(items) > 0:
		onleft = "700"
		l_cnt = l_cnt + 1
	else:
		onleft = ""

	max_width = bw if l_cnt == 1 else l_cnt * bw + 20

	iid=5000
	item_but = ''
	func_but = ''

	call = []

	for item in items:
		if item == default:
			txt_col = col_select
			foc_col = col_select
		else:
			txt_col = col_text
			foc_col = col_focus

		item_but = item_but +"\n" + button.format(id=iid, label=item.encode('utf-8'), onleft= "", onright = onright,
					txt_col=txt_col, foc_col=foc_col, **colors)

		iid = iid + 1
		call.append((callback,[item]))

	for item, cb in funcs:
		func_but = func_but +"\n" + button.format(id=iid, label=item.encode('utf-8'), onleft= onleft, onright = "",
					txt_col=col_text, foc_col=col_focus, **colors)

		iid = iid + 1
		call.append((cb,[]))

	#
	#	build item group
	#

	left = 0
	max_height = 0
	cnt = len(items)
	default_id = ""

	if cnt:
		if cnt > 11: cnt = 11
		height = cnt * (bh + itemgap)
		max_height = height
		default_id = "700"

		item_group = gheader.format(left = left, gid = "700", width = bw, height=height, **colors) + item_but + gbottom
		left = bw + 20
	else: item_group = ''

	#
	#	build func group
	#

	cnt = len(funcs)

	if cnt:
		if cnt > 11: cnt = 11
		height = cnt * (bh + itemgap)
		if height > max_height: max_height = height
		if not default_id: default_id = "701"

		func_group = gheader.format(left = left, gid = "701", width = bw, height=height, **colors) + func_but + gbottom
	else: func_group = ''

	#
	#	build and save final xml
	#

	ypos = (1080 - max_height) / 2
	xpos = (1920 - max_width ) / 2

	main = header.format(default = default_id, ypos = ypos, xpos = xpos, **colors) + item_group + func_group + bottom

	with open(fn_path_dialog + fn_dialog_name, "w") as f: f.write(main)

	#
	#	run Dialog
	#

	ui = ContextGui(fn_dialog_name, path_tmp, "Default", "720p", **kwargs)
	ui.doModal()
	#os.remove(fn_path_dialog + fn_dialog_name)

	#
	#	process result
	#
	log("result %s"%ui.result)
	if ui.result is None: return None
	try:
		method, args = call[ui.result]
		if method:
			method(*args)
			return None
	except Exception as e: opthandle(e)

	return ui.result

