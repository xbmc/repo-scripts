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

import xbmcaddon
import xbmcgui
import xbmc
import time

from helper import KeyMapFile
from helper import translate_keycode

from basic import handle
from basic import log

addon = xbmcaddon.Addon()
def tr(lid):
	return addon.getLocalizedString(lid)

class KeyMapGui(  xbmcgui.WindowXMLDialog  ):
	def __init__( self, *args, **_kwargs ):
		self.cwd = args[1]
		self.skin = args[2]

		self.kmf = KeyMapFile()
		self.kmf.parse_keymap_file()
		self.index = {}
		self.maxy = [8,8,7]
		self.success = False
		self.keycount = 3

	def onInit( self ):
		self.kmf.lock()
		xbmc.executebuiltin('Action(reloadkeymaps)')
		self.setFocusId(3008)
		self.getControl(3008).setLabel(tr(37502))
		self.getControl(4008).setLabel(tr(37501))

		for but_main_id in [3000,4000,5000]:
			for but_sub_id in range(8):
				but_id = but_main_id + but_sub_id
				lab_id = int(but_main_id / 10) + but_sub_id

				but_ctl = self.getControl(but_id)
				lab_ctl = self.getControl(lab_id)
				name = but_ctl.getLabel()

				self.index[but_id] = (name, lab_id)
				vals = self.kmf.get_info(name)

				if vals:
					but_ctl.setLabel(tr(vals["name"]))
					but = int(vals["key"])
					if but == 0:
						lab_ctl.reset()
						lab_ctl.addLabel("-")
					else:
						lab_ctl.reset()
						keycode = translate_keycode(but)
						lab_ctl.addLabel(self.format_key(but,keycode))

	@staticmethod
	def send_reload_keymaps():
		time.sleep(1)
		xbmc.executebuiltin('Action(reloadkeymaps)')

	def end_gui_ok(self):
		self.kmf.save()
		self.kmf.unlock()
		xbmc.executebuiltin('Action(reloadkeymaps)')
		# we have to create delayed action otherwise the reloadkeymaps action will
		# be swallowed by the window animations
		#threading.Thread(target = self.send_reload_keymaps).start()
		self.close()

	def end_gui_cancel(self):
		self.kmf.unlock()
		xbmc.executebuiltin('Action(reloadkeymaps)')
		self.close()

	@staticmethod
	def get_pos(cid):
		x = int(cid / 1000)
		y = cid - (x * 1000)
		x = x - 3
		return (x,y)

	@staticmethod
	def get_cid(x,y):
		return (x + 3) * 1000 + y

	def on_left_right(self, fid, step):
		x,y = self.get_pos(fid)
		log("{} {}".format(x,y))
		x += step
		if x < 0: x = 2
		if x > 2: x = 0
		if y > self.maxy[x]: y = self.maxy[x]
		self.setFocusId(self.get_cid(x,y))

	def on_up_down(self, fid, step):
		x,y = self.get_pos(fid)
		y += step
		if y < 0: y = self.maxy[x]
		if y > self.maxy[x]: y = 0
		self.setFocusId(self.get_cid(x,y))

	@staticmethod
	def format_key(but,keycode):
		if keycode:
			if keycode["mods"]:
				app = "[{}]".format("".join(x[0] for x in keycode["mods"]))
			else:
				app = ""
			return "{} {}".format(app,keycode["keyname"])
		else:
			return str(but)

	def onAction( self, action ):
		try:
			aid = action.getId()
			fid = self.getFocusId()
			but = action.getButtonCode()

			log("action id {} button {:x}".format(aid,but))

			if aid == 203:
				self.kmf.unlock()
				return

			if aid == 0 and not self.success:
				self.keycount -= 1
				if self.keycount == 0:
					# no direction keyes pressed, maybe not supported device
					xbmcgui.Dialog().notification(tr(37503),tr(37504))
					self.end_gui_cancel()
					return

			if but == 0:
				if aid in [107,203]:
					return
				#mouse click
				if aid == 100:
					if fid == 3008:
						self.end_gui_cancel()
						return
					if fid == 4008:
						self.end_gui_ok()
						return

				xbmcgui.Dialog().notification(tr(37503),tr(37504))
				self.end_gui_cancel()
				return

			keycode = translate_keycode(but)

			if self.kmf.is_mapped(but):
				xbmcgui.Dialog().notification(tr(37505),self.format_key(but,keycode), time=700)

			log("translated keycode {}".format(str(keycode)))

			if keycode and keycode["mods"]==[]:
				if keycode["keyname"] in ["return","select","enter"]:
					self.success = True
					if fid == 3008:
						self.end_gui_cancel()
						return
					if fid == 4008:
						self.end_gui_ok()
						return

					name, lab_id = self.index[fid]
					self.kmf.set_info(name,0)
					lab_ctl = self.getControl(lab_id)
					lab_ctl.reset()
					lab_ctl.addLabel("-")
					return

				elif keycode["keyname"] == 'up':
					self.on_up_down(fid,-1)
					self.success = True
					return
				elif keycode["keyname"] == 'down':
					self.on_up_down(fid,+1)
					self.success = True
					return
				elif keycode["keyname"] == 'left':
					self.on_left_right(fid,-1)
					self.success = True
					return
				elif keycode["keyname"] == 'right':
					self.on_left_right(fid,+1)
					self.success = True
					return

			try:
				if fid not in [3008,4008]:
					name, lab_id = self.index[fid]
					self.kmf.set_info(name, but)

					lab_ctl = self.getControl(lab_id)
					lab_ctl.reset()
					lab_ctl.addLabel(self.format_key(but,keycode))

			except KeyError: pass
		except Exception as e:
			handle(e)
			self.end_gui_cancel()
