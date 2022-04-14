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
import time

from basic import opthandle
from basic import log

from skin import read_next_tag
from skin import get_template
from skin import write_dialog
from skin import run_dialog

class ContextGui(  xbmcgui.WindowXMLDialog  ):
	'''Main Context Menu

		the context menu is build dynamically
	'''

	def __init__(self, *_args, **kwargs ):
		self.result = {"type":"item", "index":None}
		self.index = None

		self.build_dialog(**kwargs)

	@staticmethod
	def get_arg(item, gdefault, **kwargs):
		if item in kwargs:
			return kwargs[item]
		else:
			return gdefault

	def build_dialog(self, **kwargs):
		color = kwargs["color"]
		file_s = kwargs["file_s"]
		self.cmds = None

		items = self.get_arg("items",[],**kwargs)
		funcs = self.get_arg("funcs",[],**kwargs)

		default = self.get_arg("default",None,**kwargs)
		fwidth = self.get_arg("width",None,**kwargs)

		body_t, settings_t, group_t, button_t, groupend_t, bodyend_t = get_template(
			file_s,
			["<!-- button settings -->",
			"<!-- item group -->",
			"<!-- button -->",
			"<!-- button -->",
			"<!-- item group -->"])

		if not items:
			items = [func for func,_ in funcs]
			self.cmds = [cmd for _,cmd in funcs]
			self.result = {"type":"func"}
		else:
			if funcs:
				body_t = body_t + settings_t

		but_width = int(read_next_tag("width",button_t,0)) if not fwidth else fwidth
		but_height = int(read_next_tag("height",button_t,0))

		height = but_height * len(items)
		if height > 900:
			height = 900

		glob = {
			"xpos":int((1920 - but_width) / 2),
			"ypos":int((1080 - height) / 2),
			"default":5000,
			"height":height,
			"width":but_width
			}

		selected = color["selected"]
		text = color["text"]
		focused = color["focused"]

		button_list_txt = ""
		iid = 5000
		for item in items:
			if default == item:
				color["button_textcolor"]= "<textcolor>{col}</textcolor><focusedcolor>{col}</focusedcolor>".format(col=selected)
			else:
				color["button_textcolor"]= "<textcolor>{col}</textcolor><focusedcolor>{foccol}</focusedcolor>".format(col=text, foccol= focused)

			item_r = {"id":iid, "label":item, "width":but_width}

			button_list_txt = button_list_txt + button_t.format(**item_r, **color)
			iid+=1

		write_dialog(file_s,
			body_t.format(**glob,**color) +
			group_t.format(**glob,**color) +
			button_list_txt +
			groupend_t +
			bodyend_t)

	def onAction( self, action ):
		aid = action.getId()

		#OK pressed
		if aid in [7,100]:
			index = self.getFocusId()
			if index == 4000:
				self.result =  {'type': 'settings', 'index': 0}
			else:
				index -= 5000
				self.result["index"] = self.cmds[index] if self.cmds else index
			self.close()

		#Cancel
		if aid in [92,10]:
			self.result["index"] = None
			self.close()

def contextMenu(**kwargs):
	while True:
		result=run_dialog(ContextGui, "ContextMenu.xml", **kwargs)
		log("contextMenu: selected: {}".format(result))

		#wait for animation
		time.sleep(0.3)

		if result["index"] is None:
			return None

		if result["type"]=="item":
			return result["index"]

		if result["type"]=="func":
			try:
				method = result["index"]
				if method:
					method()
					return None
			except Exception as e: opthandle(e)

		if result["type"]=="settings":
			kwargs["items"]=[]

	return None
