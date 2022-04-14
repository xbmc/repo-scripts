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

from contextmenu import contextMenu

from rundialog import runDialog

from sweepgui import SweepGui

from helper import SocketCom

from basic import opthandle

from skin import tr

chan_num = ["front-left","front-right","rear-left","rear-right","front-center","lfe","side-left","side-right","aux1"]

class SweepGenGui(  xbmcgui.WindowXMLDialog  ):
	name = None
	eqid = None

	channel_id = []
	channel = []
	channel_sel = 0

	profiles= []
	save_profile = None
	sel_profile = 0

	corrections=[]
	save_correction=None
	sel_correction=0

	repeats = 0

	def __init__( self, *args, **_kwargs ):
		self.cwd = args[1]
		self.skin = args[2]

		self.sock = SocketCom("server")

		result = self.sock.call_func("get","eq_channel")
		if result is None: return

		self.eqid, self.name, channel = (result)

		self.channel_id = channel

		ch_index = []
		for ch_name in channel:
			try:
				index = chan_num.index(ch_name)
				ch_index.append(index)
			except Exception as e: opthandle(e)

		self.channel = ch_index

		self.profiles = [tr(32413)] + self.sock.call_func("get","eq_profiles")
		self.save_profile = self.sock.call_func("get","eq_base_profile")
		self.sock.call_func("unload","eq_profile",[self.eqid])

		self.corrections =[tr(32411)] + self.sock.call_func("get","room_corrections")
		self.save_correction = self.sock.call_func("get","room_correction")
		self.sock.call_func("unset","room_correction" , [self.eqid])

	def onInit( self ):
		if self.name is None: self.close()
		self.getControl(300).setLabel(self.profiles[self.sel_profile])
		self.getControl(301).setLabel(self.corrections[self.sel_correction])

	def on_sel_profile(self):
		nsel = contextMenu(items = self.profiles, default = self.profiles[self.sel_profile])

		if nsel is None: return

		if nsel == 0: self.sock.call_func("unload","eq_profile",[self.eqid])
		else: self.sock.call_func("load","eq_profile" , [self.eqid, self.profiles[nsel]])
		self.sel_profile = nsel
		self.getControl(300).setLabel(self.profiles[self.sel_profile])

	def on_sel_correction(self):
		nsel = contextMenu(items = self.corrections, default = self.corrections[self.sel_correction])
		if nsel is None: return

		if nsel == 0: self.sock.call_func("unset","room_correction", [self.eqid])
		else: self.sock.call_func("set","room_correction" , [self.eqid, self.corrections[nsel]])
		self.sel_correction = nsel

		self.getControl(301).setLabel(self.corrections[nsel])

	def on_sel_channel(self):
		sel_list = [tr(32412) + "  (0)"] + [tr(32500 + i)+ "  (%s)"%(i+1) for i in self.channel]

		nsel = contextMenu(items = sel_list, default = sel_list[self.channel_sel])
		if nsel is None: return

		self.channel_sel=nsel
		self.getControl(302).setLabel(sel_list[nsel])

	def on_sel_repeats(self):
		numbers = ["- %s -" % str(i+1) for i in range(10)]

		nsel = contextMenu(items = numbers, default = numbers[self.repeats])
		if nsel is None: return

		self.repeats = nsel
		self.getControl(303).setLabel(str(nsel+1))

	def on_sel_play(self):
		channel = None if self.channel_sel == 0 else self.channel_id[self.channel_sel-1]
		runDialog(SweepGui,"Sweep",channel=channel , count = self.repeats + 1)

	def handleOK(self):
		fid = self.getFocusId()
		if fid == 3000: self.on_sel_profile()
		elif fid == 3001: self.on_sel_correction()
		elif fid == 3002: self.on_sel_channel()
		elif fid == 3003: self.on_sel_repeats()
		elif fid == 3004: self.on_sel_play()

	def end_gui(self):
		if self.save_profile:
			self.sock.call_func("load","eq_profile",[self.eqid, self.save_profile])
		if self.save_correction:
			self.sock.call_func("set","room_correction" , [self.eqid, self.save_correction])
		self.close()

	def onAction( self, action ):
		#OK pressed
		if action.getId() in [7, 100]:
			self.handleOK()

		#Cancel
		if action.getId() in [92,10]:
			self.end_gui()
