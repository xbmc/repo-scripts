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
import xbmc

from helper import KeyMapFile
from helper import translate_keycode

from basic import handle
from basic import log
from basic import parse_xml

from skin import tr

from skin import get_template
from skin import write_dialog
from skin import run_dialog

from skin import localize

class GroupInfo():pass

class KeyMapGui(  xbmcgui.WindowXMLDialog  ):
	def __init__( self, *args, **_kwargs ):
		self.build_dialog(**_kwargs)

		self.cwd = args[1]
		self.skin = args[2]

		self.success = False
		self.keycount = 3

	@staticmethod
	def group_var(group):
		ginfo = GroupInfo()
		ginfo.left = int(group["attr"]["left"][1:-1])
		ginfo.height = int(group["attr"]["height"][1:-1])
		ginfo.gap = int(group["attr"]["gap"][1:-1])
		ginfo.items = group["val"].split(",")

		return ginfo

	@classmethod
	def get_butlab_info(cls, keystruct,ginfo):
		key = keystruct["key"]
		return {
			"bid":ginfo.cid,
			"lid":ginfo.cid + 0x100,
			"btop":ginfo.top,
			"bheight":ginfo.height,
			"align":"left",
			"lbutton":tr(keystruct["name"]),
			"llable":cls.format_key(key, translate_keycode(key), True)
			}

	def build_dialog(self,**kwargs):
		color = kwargs["color"]
		file_s = kwargs["file_s"]

		header_t, pageformat_t,	group_t, button_t, label_t,	groupclose_t, close_t = get_template(
								file_s,
								["<!-- page format -->",
								"<!-- group template -->",
								"<!-- button template -->",
								"<!-- label template -->",
								"<!-- label template end -->",
								"<!-- group template end -->"]
								)

		butlab_t = button_t + label_t
		groups = parse_xml(pageformat_t)["butgroup"][0]["items"]

		self.kmf = KeyMapFile()
		self.kmf.parse_keymap_file()

		self.index = {}
		self.maxy = []

		final_txt = ""
		glob = {}

		id_iter = iter([0x1000,0x2000, 0x3000])

		for group in groups:
			ginfo = self.group_var(group)
			ginfo.cid = next(id_iter)
			ginfo.top = 0

			group_txt = ""
			# bulid button list
			for item in ginfo.items:
				if item == "GAP":
					ginfo.top += ginfo.gap
					continue

				self.index[ginfo.cid]=item
				keystruct = self.kmf.get_info(item)
				butinfo = self.get_butlab_info(keystruct,ginfo)

				group_txt = group_txt + butlab_t.format(**butinfo,**color)

				ginfo.top += ginfo.height
				ginfo.cid += 1

			ginfo.top += ginfo.height

			#append SAVE, CANCEL
			if ginfo.cid & 0xF000 in [0x1000,0x2000]:
				ipos = ginfo.cid >> 12
				if ipos == 1:
					glob["default"] = ginfo.cid
					glob["gtop"] = (1080 - (ginfo.top + ginfo.height)) / 2
					self.cancel = ginfo.cid

				self.index[ginfo.cid]=["CANCEL","SAVE"][ipos-1]

				butinfo = {
					"bid":ginfo.cid,
					"btop":ginfo.top,
					"bheight":ginfo.height,
					"align":"center",
					"lbutton":[tr(32752),tr(32751)][ipos-1]
					}
				ginfo.cid += 1

				group_txt = group_txt + button_t.format(**butinfo,**color)

			#build final group string
			final_txt = final_txt + group_t.format(gleft = ginfo.left) + group_txt + groupclose_t

			self.maxy.append((ginfo.cid & 0xFF) - 1)

		write_dialog(file_s,
				localize(header_t.format(**glob, **color)) +
				final_txt +
				close_t
				)

	def onInit( self ):
		self.kmf.lock()
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
		y = cid & 0xFF
		x = (cid >> 12) - 1
		return (x,y)

	@staticmethod
	def get_cid(x,y):
		return ((x+1) << 12) + y

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
	def format_key(but,keycode, xml=False):
		if but == 0: return "-"
		if keycode and  keycode["keyname"]:
			if keycode["mods"]:
				app = "[{}]".format("".join(x[0] for x in keycode["mods"]))
			else:
				app = ""

			if "char" in keycode["keyname"]:
				kn = keycode["keyname"]["char"]

				if xml:
					try: kn = "$NUMBER[{}]".format(int(kn))
					except ValueError: pass

			elif "tr" in keycode["keyname"]:
				kn = tr(keycode["keyname"]["tr"])
			else:
				kn = keycode["keyname"]["name"]

			return "{} {}".format(app,kn)
		else:
			return "key {}".format(but)

	def set_key(self, fid, but, val):
		try:
			self.kmf.set_info(self.index[fid], but)
			lab_ctl = self.getControl(fid | 0x100)
			lab_ctl.reset()
			lab_ctl.addLabel(val)
		except RuntimeError: pass

	def check_end(self, button_name):
		if button_name == "CANCEL":
			self.end_gui_cancel()
		elif button_name == "SAVE":
			self.end_gui_ok()
		else:
			return False
		return True

	def navigate(self, command_name, fid):
		if command_name in ["return","select","enter"]:
			if self.check_end(self.index[fid]):
				return True
			else:
				self.set_key(fid, 0, "-")
				return True

		elif command_name in ["back","backspace"]:
			if self.check_end(self.index[fid]):
				return True
			else:
				self.setFocusId(self.cancel)
				return True

		elif command_name == 'up':
			self.on_up_down(fid,-1)
		elif command_name == 'down':
			self.on_up_down(fid,+1)
		elif command_name == 'left':
			self.on_left_right(fid,-1)
		elif command_name == 'right':
			self.on_left_right(fid,+1)
		else:
			return False

		self.success = True
		return True

	def onAction( self, action ):
		try:
			aid = action.getId()
			fid = self.getFocusId()
			but = action.getButtonCode()

			log("action id {} button {:x}".format(aid,but))

			if aid == 0 and not self.success:
				self.keycount -= 1
				if self.keycount == 0:
					# no direction keyes pressed, maybe not supported device
					xbmcgui.Dialog().notification(tr(32753),tr(32754))
					self.end_gui_cancel()
					return

			if but == 0:
				if aid in [107,203]:
					return
				#mouse click
				if aid == 100 and self.check_end(self.index[fid]):
					return True

				xbmcgui.Dialog().notification(tr(32753),tr(32754))
				self.end_gui_cancel()
				return

			keycode = translate_keycode(but)

			if self.kmf.is_mapped(but):
				xbmcgui.Dialog().notification(tr(32755),self.format_key(but,keycode), time=700)

			log("translated keycode {}".format(str(keycode)))

			if keycode and keycode["mods"]==[]:
				self.kmf.unlock()

				if self.navigate(keycode["keyname"]["name"],fid):
					return
			try:
				if self.index[fid] not in ["CANCEL","SAVE"]:
					self.set_key(fid, but, self.format_key(but,keycode))

			except KeyError: pass
		except Exception as e:
			handle(e)
			self.end_gui_cancel()

def keymapDialog(**kwargs):
	run_dialog(KeyMapGui, "KeyMapDialog.xml", **kwargs)
