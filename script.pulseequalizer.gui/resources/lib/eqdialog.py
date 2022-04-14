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
import math
import time

from threading import Thread

from helper import SocketCom
from helper import DynStep

from basic import get_user_setting

from time import sleep

from skin import tr
from skin import read_next_tag
from skin import format_float
from skin import localize
from skin import get_frequencies

from skin import get_template
from skin import write_dialog
from skin import run_dialog

from contextmenu import contextMenu

#from basic import log

class EqGui(  xbmcgui.WindowXMLDialog  ):
	''' Equalizer Dialog

		The equalizer dialog is build up dynamically
	'''

	def __init__(self, *args, **kwargs ):
		self.build_dialog(**kwargs)

		self.index = None
		self.updating=False
		self.controlId = 2000

		self.cwd = args[1]
		self.sock = SocketCom("server")
		self.eqid = kwargs["eqid"]
		self.desc = kwargs["desc"]
		try: step = int(get_user_setting("equalstep",0))+1
		except Exception: step = int(1)

		self.dyn_step = DynStep(step,5,1,3)

		self.sock.call_func("set","eq_frequencies",[self.freqs])
		self.profile = self.sock.call_func("get","eq_base_profile")

		self.preamp, self.coef = self.sock.call_func("get","eq_filter")
		self.is_changed = False

	def build_dialog(self, **kwargs):
		self.freqs = get_frequencies()

		color = kwargs["color"]
		file_s = kwargs["file_s"]

		header_t, itemgap_t, templ_t, end_t = get_template(
								file_s,
								["<!-- item gap -->",
								"<!-- element begin -->",
								"<!-- element end -->"])

		itemgap = int(read_next_tag("itemgap",itemgap_t,0))

		num_freq = len(self.freqs)

		if num_freq >= 15:
			itemgap = 0

		itemgap_t = itemgap_t.format(itemgap=itemgap)

		width = int(read_next_tag("width",templ_t,0))

		slider_width = (width + itemgap) * num_freq
		if slider_width > 1700: slider_width=1700
		total_width = slider_width + 100
		xpos = (1920 - total_width) / 2

		items = ""
		i = 0

		max_id = 1999 + num_freq

		for freq in self.freqs:
			item_r = self.set_replace_item(2000 + i,freq, max_id)
			items = items + templ_t.format(**item_r, **color)
			i+=1

		glob = {
			"slider_width":slider_width,
			"total_width":total_width,
			"xpos":xpos
			}

		write_dialog(file_s,
			localize(header_t.format(**glob, **color) +
			itemgap_t +
			items +
			end_t))

	@staticmethod
	def set_replace_item(item_id,freq, max_id):
		item_r = {
			"sid":item_id,
			"lid":item_id + 100,
			"onleft":item_id - 1
			}

		if item_id < max_id:
			item_r["onright"] = item_id + 1
		else:
			item_r["onright"] = ""

		if freq < 1000:
			item_r["labelid"] = '$NUMBER[{}]'.format(int(freq))
		else:
			item_r["labelid"] = format_float(freq)

		return item_r

	@staticmethod
	def str(nr):
		if nr < 1000: return str(nr)
		fnr = float(nr) / 1000

		if round(fnr) == fnr:
			return "{:d}k".format(int(fnr))
		else:
			return "{:.1f}k".format(fnr)

	@staticmethod
	def slider2coef(val):
		#slider 0-100 into dB [-20db .. 20db] = [0.1 ... 10]
		return 10.0**((val-50.0)/50.0)

	@staticmethod
	def coef2slider(val):
		return int(math.log10( val )*50+50.0)

	def onInit( self ):
		self.setFocusId(2000)

		#set slider names
		self.getControl(3500).setLabel(self.profile)
		self.getControl(3501).setLabel(self.desc)
		self.getControl(3502).setLabel("0 dB      ")

		#set slider
		i = 0
		for coef in self.coef[1:]:
			self.getControl(2000 + i).setInt(self.coef2slider(coef), 0, 0, 100)
			i = i + 1

		# set preamp slider
		self.getControl(1999).setInt(self.coef2slider(self.preamp), 0, 0, 100)

	def onFocus(self, controlId):
		if controlId >=1999 and controlId <2100:
			self.controlId = controlId
			val = 2 * (self.getControl(self.controlId).getFloat() - 50) / 5
			self.getControl(3502).setLabel("{:.1f} dB      ".format(val))

	def set_filter(self):
		self.coef[0] = self.coef[1]
		self.sock.call_func("set","eq_filter",[self.eqid, self.preamp, self.coef])

	def load_profile(self):
		self.sock.call_func("load","eq_profile",[self.eqid, self.profile])

	def save_profile(self):
		self.sock.call_func("save","eq_profile",[self.profile])

	def update(self):
		sleep(0.3)
		self.set_filter()
		self.updating = False
		self.is_changed = True

	def setFilter(self):
		val = 2 * (self.getControl(self.controlId).getFloat() - 50) / 5
		self.getControl(3502).setLabel("{:.1f} dB      ".format(val))

		change = False
		for i in range(1, len(self.coef)- 2):
			c = self.slider2coef(self.getControl(1999 + i).getFloat())
			if c != self.coef[i]:
				self.coef[i] = c
				change = True

		c =  self.slider2coef(self.getControl(1999).getFloat())
		if c != self.preamp:
			self.preamp = c
			change = True

		if not change: return

		if not self.updating:
			self.updating = True
			Thread(target=self.update).start()

	def _close(self):
		self.close()

	def sel_cancel(self):
		self.load_profile()
		self._close()

	def sel_save(self):
		self.save_profile()
		self._close()

	def onAction( self, action ):
		t = time.time()
		aid = action.getId()
		fid = self.getFocusId()
		buc = action.getButtonCode() & 255
		#log("eqdialog: key: %s fid: %s"%(aid,fid))

		#OK pressed
		if aid in [7]:
			self.save_profile()
			self._close()

		if aid in [100]:
			if fid == 1800:
				#self.save_profile()
				self.load_profile()
				self._close()

		#Cancel
		if aid in [92,10]:
			if self.is_changed:
				contextMenu(funcs = [(tr(32622),self.sel_cancel),(tr(32623),self.sel_save)])
			else:
				self.close()

		self.dyn_step.dynamic_step(buc)

		if aid in [3,104]:
			ctl = self.getControl(self.controlId)
			new = ctl.getInt()+self.dyn_step.dynstep
			if ctl.getInt() < 50 and new > 50: new = 50
			pos = new
			if pos > 100: pos = 100
			ctl.setInt(pos,0,0,100)

		if aid in [4,105]:
			ctl = self.getControl(self.controlId)
			new = ctl.getInt()-self.dyn_step.dynstep
			if ctl.getInt() > 50 and new < 50: new = 50
			pos = new
			if pos < 0: pos = 0
			ctl.setInt(pos,0,0,100)

		if aid in [3,4,104,105,106]:
			self.setFocusId(self.controlId)
			self.setFilter()

		self.last_key = t

def eqDialog(**kwargs):
	run_dialog(EqGui, "EqualizerDialog.xml", **kwargs)
