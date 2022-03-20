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
import time
import threading

from helper import log, SocketCom

class VolumeGui(  xbmcgui.WindowXMLDialog  ):

	def __init__( self, *args, **kwargs ):
		self.sock = SocketCom("server")
		
		self.path = os.path.join(args[1],"resources/skins/"+args[2]+"/media")

		self.progress1 = None
		self.updown = kwargs["updown"]
		
		self.key_up = None
		self.key_down = None
		self.updating = False

		
		self.vol = self.sock.call_func("get","volume")
		if self.updown == "up":
			self.vol_up() 
		else: 
			self.vol_down()
			
		self.last = time.time()
		threading.Thread(target=self.check_close).start()

		
	def check_close(self):
		while True:
			if time.time() - self.last > 1:
				break
			time.sleep(0.5)
		self.close()
		

	def onInit( self ):
		self.progress1 = self.getControl(1900)
		self.label = self.getControl(1901)

		self.set_vol_gui()

	# slow down messages to server
	def update_to_pulse(self):
		time.sleep(0.3)
		self.sock.call_func("set","volume",[self.vol])
		self.updating = False

	def update(self):
		if not self.updating:
			self.updating = True
			threading.Thread(target=self.update_to_pulse).start()

	def vol_up(self):
		if self.vol is None: return
		self.vol = self.vol + float(0.01)
		if self.vol > float(1.5): self.vol = float(1.5)
		self.update()
		
		
	def vol_down(self):
		if self.vol is None: return
		self.vol = self.vol - float(0.01)
		if self.vol < 0: self.vol = float(0)
		self.update()

	def set_vol_gui(self):
		self.last = time.time()

		if self.progress1 is None: return
		if self.vol is None:return
		
		v = (self.vol / 1.5) * 100
		if v > 100: v = 100
		
		self.progress1.setPercent(v if v > 0 else 0.1)
		self.label.setLabel("{:d} %".format(int(self.vol*100)))


	def onAction( self, action ):
		aid = action.getId()
		log("action %d" %aid)
		
		#OK pressed
		if aid == 7:
			self.close()
		
		#Cancel
		if aid in [92,10]:
			self.close()
			
		aid = action.getButtonCode() & 255
		#log("action %d" %aid)
		
		if aid == self.key_up:
			self.vol_up()
			self.set_vol_gui()
			#log("key up")
		elif aid == self.key_down:
			self.vol_down()
			self.set_vol_gui()
			#log("key down")
		else:
			if self.updown == "up":
				if self.key_up is None:
					self.key_up = aid
					self.vol_up()
				elif self.key_down is None:
					self.key_down = aid
					self.vol_down()
			else:
				if self.key_down is None:
					self.key_down = aid
					self.vol_down()
				elif self.key_up is None:
					self.key_up = aid
					self.vol_up()

			self.set_vol_gui()
					
			
		

		
