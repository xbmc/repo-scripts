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

import xbmc
import xbmcaddon
import xbmcgui

import time
import shutil
import os

from helper import *
from sound import createGraphdB, createGrid, SpecManager, Spectrum, SpecGroup,createGraph2, createGrid2
from contextmenu import contextMenu

from threading import Thread


chan_num = ["front-left","front-right","rear-left","rear-right","front-center","lfe","side-left","side-right","aux1"]

addon = xbmcaddon.Addon()
def tr(id):
	return addon.getLocalizedString(id)

class ImportGui(  xbmcgui.WindowXMLDialog  ):

	name = None
	eqid = None

	channel_name=[]
	load_channel_name = []
	file_name=[]

	mic_file=None
	mic_name=tr(32413)
	
	spec_group = None
	shift = {}
	img = 0
	
	block_image = False
	image_change = False

	def __init__( self, *args, **kwargs ):
		self.sock = SocketCom("server")
		
		result = self.sock.call_func("get","eq_channel")
		if result is None: return
		
		self.eqid, self.name, channel = (result)
		
		ch_index = []
		ch_index.append((-1,tr(32412),tr(32411)))
		
		channel_name = [tr(32412)]
		file_name = [tr(32411)]
		
		i = 0
		for ch_name in channel:
			try:
				index = chan_num.index(ch_name)
				channel_name.append(tr(32500 + i))
				file_name.append(tr(32411))
			except: 
				channel_name.append(tr(32612))
				file_name.append(tr(32411))
				
			i=i+1
			
			
			
		self.channel_name = channel_name
		self.file_name = file_name

	#
	#	Spectrum Creation
	#
	def process_spec(self, pos):

		try: 
			if self.spec_group.count == 1:
				spec = self.spec_group.speclist[0]
			else:
				spec = self.spec_group.speclist[pos + 1]
				
		except: return None
		
		try: shift = float(self.shift[pos]) / 5
		except: shift = 0
		
		if self.getControl(3102).isSelected():
			try: relvol = self.spec_group.relvol[pos]
			except: relvol = 0
		else: relvol = 0
		
		if self.mic_file:
			spec = spec - self.mic_file
		
		if  self.getControl(3101).isSelected():
			spec = spec.smooth()

		spec = spec.shift_inverse(shift + relvol)
		
		if  not self.getControl(3103).isSelected():
			spec = spec.cut_positives()

		return spec


	#
	#	Image creation
	#
	
	def image_loop(self):
		while True:
			self.draw_image()
			if not self.image_change: break
			self.image_change = False
		self.block_image = False
		
	def update_image(self):
		self.image_change = True
				
		if self.block_image: return

		self.block_image = True
		Thread(target= self.image_loop).start()

		
	def draw_image(self):
		fn = path_tmp + "%s.png" % self.img
		try: os.remove(fn)
		except: pass
		
		self.img =  self.img + 1
		fn = path_tmp + "%s.png" % self.img
		
		pos = self.getControl(2100).getSelectedPosition()
		if pos == -1: return
		
		spec = self.process_spec(pos)
		if spec:
			createGraph2(fn,spec, width = 1690, height = 480)
		
			self.getControl(1500).setImage(fn, False)
		
		
	#
	#	Room Correction Functions
	#
		
	def load_measurement(self):
		heading = tr(32607)
		
		defaultt="/home/user/Script/kodi/"
		file_name = xbmcgui.Dialog().browse(1, heading, "",defaultt=defaultt)
		if file_name == defaultt: return
		

		self.spec_group = SpecGroup().load(file_name).update_relvol()
		self.ch_config = [None] * self.spec_group.count
		
		self.file_name=[]
		self.load_channel_name = []
		fns =  self.spec_group.filenames
		for i in range(len(self.channel_name)):
			try: 
				self.file_name.append(fns[i])
				self.load_channel_name.append(self.channel_name[i])
			except: pass
		
		ctl = self.getControl(2100)
		ctl.reset()
		ctl.addItems([xbmcgui.ListItem(self.load_channel_name[i],self.file_name[i]) for i in range(len(self.load_channel_name))])
		
		self.update_image()
		
	def save_room_correction(self):
		if self.spec_group is None: return
		name = xbmcgui.Dialog().input(tr(32608),self.spec_group.name)

		if name is None: return
		fn = path_addon + path_filter + name + "/"
		if os.path.exists(fn):
			if xbmcgui.Dialog().yesno(tr(32608),tr(32609) %(name)) == False: return
			shutil.rmtree(fn)
		os.makedirs(fn)
		
		for chan in self.spec_group.speclist.keys():
			if chan == 0: 
				cn = "all"
				spec = self.process_spec(chan)
			else: 
				cn = chan_num[chan-1]
				spec = self.process_spec(chan-1)
			coef = spec.as_coef()
			coef.save("%s%s.fil" % (fn,cn))
			 
		

	#
	#	Microphone
	#

	def select_mic(self):
		spec = SpecManager()
		mics = spec.get_mic_specs()
				
		mic_sel = contextMenu(items = [tr(32610)] + mics, default = self.mic_name, funcs=[(tr(32203),self.import_mic)])
		
		if mic_sel is None: return
		if mic_sel == 0:
			self.mic_file = None
			self.mic_name = tr(32413)
			self.getControl(2020).setLabel(self.mic_name)
		else:
			self.mic_name = mics[mic_sel - 1]
			fn_mic = spec.spec_path + self.mic_name + ".mic"
			self.mic_file = Spectrum().load(fn_mic)
			self.getControl(2020).setLabel(self.mic_name)
		
		
		self.update_image()

	def import_mic(self):

		heading = tr(32611)
		
		defaultt="/home/user/Script/kodi/"
		file_name = xbmcgui.Dialog().browse(1, heading, "",defaultt=defaultt)
		if file_name == defaultt: return
		
		self.mic_name, self.mic_file =  SpecManager().import_mic_file(file_name)
		
		self.getControl(2020).setLabel(self.mic_name)
		self.update_image()

	#
	#	Dialog functions
	#

	def update_slider(self):
		pos = self.getControl(2100).getSelectedPosition()
		if pos == -1: return
		
		try: shift = self.shift[pos]
		except: shift = 0

		self.getControl(5001).setInt(50 + shift,0,1,100)

	def update_shift(self):
		pos = self.getControl(2100).getSelectedPosition()
		if pos == -1: return
		
		self.shift[pos] = self.getControl(5001).getInt()-50
		self.update_image()


	def onInit( self ):
		self.getControl(1001).setLabel(tr(32600))
		self.getControl(1002).setLabel(tr(32601))
		self.getControl(1003).setLabel(tr(32602))
		self.getControl(2010).setLabel(tr(32603))
		self.getControl(3101).setLabel(tr(32604))
		self.getControl(3102).setLabel(tr(32605))
		self.getControl(3103).setLabel(tr(32606))
		
		
		ctl = self.getControl(2100)
		ctl.addItems([xbmcgui.ListItem(self.channel_name[i],self.file_name[i]) for i in range(len(self.channel_name))])
		self.getControl(2020).setLabel(self.mic_name)
		self.getControl(4010).setLabel(self.name)
		self.getControl(3101).setSelected(True)
		self.getControl(3102).setSelected(True)
		self.getControl(3103).setSelected(False)
		self.getControl(5001).setInt(50,0,1,100)
		
	def end_gui(self):
		fn = path_tmp + "%s.png" % self.img
		try: os.remove(fn)
		except: pass

		self.close()
		
	def onOk(self):
		focusId = self.getFocusId()
		if focusId == 1001: self.load_measurement()
		if focusId == 1002: self.select_mic()
		if focusId == 1003: self.save_room_correction()
		if focusId in [3101,3102,3103]: self.update_image()
		
	def onAction( self, action ):
		aid = action.getId()
		fid = self.getFocusId()
		
		#OK pressed
		if aid in [7, 100]:
			self.onOk()
			
		#Cancel
		if aid in [92,10]:
			self.end_gui()
			
		if aid in [1,2,3,4]:
			if fid == 2100:
				self.update_slider()
				self.update_image()
				
		if aid in [3,4]:
			if fid == 5001:
				self.update_shift()
			
		#log("%s"%action.getId())
