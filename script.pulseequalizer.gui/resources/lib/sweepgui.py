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

from helper import SocketCom
from basic import log

class SweepGui(  xbmcgui.WindowXMLDialog  ):
	def __init__( self, *_args, **kwargs ):
		self.sock = SocketCom("server")
		self.rec = SocketCom("sweep")

		self.channel = kwargs["channel"]
		self.count = kwargs["count"]

		result = self.sock.call_func("get","eq_channel")
		if result is None: return

		self.eqid, self.name, _ = (result)

		self.rec.start_func_server(self)

	def onInit( self ):
		self.prog1 = self.getControl(1900)
		self.prog2 = self.getControl(1901)
		self.prog1.setPercent(0.1)
		self.prog2.setPercent(0.1)
		#self.getControl(101).setLabel("%s - %s" % (self.name, tr(32410)))

		self.sock.call_func("play","sweep",[self.count, self.channel])

	@staticmethod
	def on_sound_play( nr):
		log("on_sound_play %s"% nr)

	def on_sound_stop(self):
		log("on_sound_stop")
		self.rec.stop_server()
		self.close()

	def on_chunk_play(self, c_nr, c_size,  c_cnt,  c_total):
		self.prog1.setPercent(c_cnt * 100 / (c_total-1))
		self.prog2.setPercent(c_nr * 100 / (c_size-1))

	def end_gui(self):
		self.sock.call_func("stop","tone")
		self.sock.call_func("stop","pulseplayer")
		self.rec.stop_server()
		self.close()

	def onAction( self, action ):
		#OK pressed
		if action.getId() in [7, 100]:
			self.end_gui()

		#Cancel
		if action.getId() in [92,10]:
			self.end_gui()
