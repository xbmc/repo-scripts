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
import xbmcaddon
import os
import re
import math
import time

from threading import Thread

from helper import json
from helper import SocketCom
from helper import DynStep

from basic import handle
from basic import opthandle
from basic import logerror
from basic import path_addon
from basic import path_tmp
from basic import path_settings
from basic import path_skin
from basic import path_profile

from time import sleep

from skin import get_current_skin
from skin import get_skin_colors
from skin import create_temp_structure

from contextmenu import contextMenu

#from basic import log

addon = xbmcaddon.Addon()
def tr(lid):
	return addon.getLocalizedString(lid)

class EqGui(  xbmcgui.WindowXMLDialog  ):
	''' Eqaulizer Dialog

		The equalizer dialog is build up dynamically
	'''
	result = None
	index = None

	updating=False

	controlId = 2000
	reopen=False

	def __init__(self, *args, **kwargs ):
		self.cwd = args[1]
		self.sock = SocketCom("server")
		self.freqs = kwargs["freqs"]
		self.eqid = kwargs["eqid"]
		self.desc = kwargs["desc"]
		step = kwargs["step"]

		self.dyn_step = DynStep(step,5,1,3)

		self.sock.call_func("set","eq_frequencies",[self.freqs])
		self.profile = self.sock.call_func("get","eq_base_profile")

		self.preamp, self.coef = self.sock.call_func("get","eq_filter")

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
		lid = 2100
		self.getControl(3500).setLabel(self.profile)
		self.getControl(3501).setLabel(self.desc)
		self.getControl(3502).setLabel("0 dB      ")

		for f in self.freqs:
			self.getControl(lid).setLabel(self.str(f))
			lid = lid + 1

		#set slider
		i = 0
		for coef in self.coef[1:]:
			self.getControl(2000 + i).setInt(self.coef2slider(coef), 0, 0, 100)
			i = i + 1

		# set preamp slider
		self.getControl(2999).setLabel(tr(32037))
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

	def sel_edit_freq(self):
		freq = xbmcgui.Dialog().input(tr(32621),".".join([str(f) for f in self.freqs]))
		if freq == "": return

		try: freqs = sorted([int(f) for f in freq.split(".")])
		except Exception: return

		flist = []
		try:
			it = iter(freqs)
			cur = next(it)
			flist.append(cur)
			while True:
				new = next(it)
				if new == cur: continue

				cur = new
				flist.append(cur)
		except Exception as e: opthandle(e)

		fn = path_profile + path_settings + "settings.json"
		try:
			with open(fn) as f: se = json.loads(f.read())
		except Exception: se = {}

		se["freqs"] = flist

		try:
			with open(fn, 'w') as f: f.write(json.dumps(se))
		except Exception as e:
			handle(e)
			return

		self.reopen = True
		self.load_profile()
		self._close()

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
			contextMenu(funcs = [(tr(32622),self.sel_cancel),(tr(32623),self.sel_save),(tr(32621),self.sel_edit_freq)])

		self.dyn_step.dynamic_step(buc)

		if aid in [3,104]:
			ctl = self.getControl(self.controlId)
			pos = ctl.getInt()+self.dyn_step.dynstep
			if pos > 100: pos = 100
			ctl.setInt(pos,0,0,100)

		if aid in [4,105]:
			ctl = self.getControl(self.controlId)
			pos = ctl.getInt()-self.dyn_step.dynstep
			if pos < 0: pos = 0
			ctl.setInt(pos,0,0,100)

		if aid in [3,4,104,105,106]:
			self.setFocusId(self.controlId)
			self.setFilter()

		self.last_key = t

def eqBuild(**kwargs):
	fn = path_profile + path_settings + "settings.json"
	try:
		with open(fn) as f: se = json.loads(f.read())
		freqs = se["freqs"]
	except Exception:
		freqs = [64, 125, 250, 500, 750, 1000,  2000,  3000,  4000,  8000, 16000]

	kwargs["freqs"] = freqs

	try:
		skin = get_current_skin()
		skincol = skin
		if not os.path.exists(path_addon + path_skin.format(skin=skin) + "EqualizerDialog.xml"):
			skin = "Default"
	except Exception as e:
		handle(e)
		skin = "Default"
		skincol = skin
	#
	#	create path structure
	#

	fn_dialog_name = "EqualizerDialog.xml"
	fn_path = path_skin.format(skin=skin)
	fn_path_template = path_addon + fn_path
	fn_path_dialog = path_tmp + fn_path
	create_temp_structure(skin)

	#
	#	get skin color scheme
	#

	colors = get_skin_colors(skincol)

	#
	#	prepare template
	#

	with open( fn_path_template +  fn_dialog_name) as f: template = f.read()

	# find slider group
	b = re.search('<!-- element begin -->(.*?)<!-- element end -->', template, re.DOTALL | re.I)
	if b is None:
		logerror("no button template found in %s" % (fn_path_template +  fn_dialog_name))
		return

	main = template.replace(b.group(0),"{grouplist}")
	element = b.group(1)

	ew = int(re.search('<width>(.*?)</width>',element).group(1))

	if len(freqs) < 15:
		oig = re.search('<optitemgap>(.*?)</optitemgap>', main)
		if oig:
			main = main.replace(oig.group(0),"<itemgap>%s</itemgap>" % oig.group(1))
			ew = ew + int(oig.group(1))

	slider_width = ew * len(freqs)
	if slider_width > 1700: slider_width = 1700
	total_width = slider_width + 100
	xpos = (1920 - total_width) / 2

	r = ''
	iid = 2000
	left = 0
	for f in freqs:
		if int(f) < 1000: label = str(f)
		elif int(f) < 10000: label = str(f)[0]+"k"+ str(f)[1]
		else: label = str(f)[:2]+"k"

		r = r + element.format(id = iid, left = left, label= label, onright = iid + 1, onleft = iid - 1, lid = iid + 100, **colors)
		iid = iid + 1

	main = main.format(grouplist = r, xpos = xpos, total_width=total_width, slider_width=slider_width, **colors)

	with open(fn_path_dialog + fn_dialog_name, "w") as f: f.write(main)

	return kwargs, fn_dialog_name, path_tmp, fn_path_dialog

def eqDialog(**kwargs):
	while True:
		kwargs, fn_dialog_name, path_tmp, fn_path_dialog = eqBuild(**kwargs)

		ui = EqGui(fn_dialog_name, path_tmp, "Default", "720p", **kwargs)
		ui.doModal()

		if not ui.reopen:
			os.remove(fn_path_dialog + fn_dialog_name)
			break
