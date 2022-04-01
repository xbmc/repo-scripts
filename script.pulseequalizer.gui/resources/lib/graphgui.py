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
import os

from helper import SocketCom

from basic import opthandle

from sound import createGraph2
from sound import SpecManager
from sound import Spectrum

addon = xbmcaddon.Addon()
def tr(lid):
	return addon.getLocalizedString(lid)

class GraphGui(  xbmcgui.WindowXMLDialog  ):
	spec_file = None
	mic_file = None

	def __init__( self, *args, **kwargs ):
		self.sock = SocketCom("server")
		self.cwd = args[1]
		self.sock = SocketCom("server")
		self.eqid = kwargs["eqid"]
		self.desc = kwargs["desc"]

		self.tmp_fn = self.sock.path + "graph_%s.png"
		self.cnt = 0

	def onInit( self ):
		self.setFocusId(3000)

		self.update_image()

	def update_image(self):
		fn = self.tmp_fn  % self.cnt
		try: os.remove(fn)
		except Exception as e: opthandle(e)

		self.cnt = self.cnt + 1
		fn = self.tmp_fn % self.cnt

		if self.spec_file and self.mic_file:
			spec = self.spec_file - self.mic_file
		elif self.spec_file:
			spec =  self.spec_file
		elif self.mic_file:
			spec =  self.mic_file
		else: spec = None

		if spec: createGraph2(fn,spec.as_coef())
		else: createGraph2(fn)

		self.getControl(1000).setImage(fn, False)

	def import_spec(self):
		heading = "Import Spectrum"

		defaultt="/home/user/Script/kodi/"
		file_name = xbmcgui.Dialog().browse(1, heading, "",defaultt=defaultt)
		if file_name == defaultt: return

		self.spec_file = Spectrum()._import(file_name)
		self.update_image()

	def import_mic(self):
		heading = "Import Microphone"

		defaultt="/home/user/Script/kodi/"
		file_name = xbmcgui.Dialog().browse(1, heading, "",defaultt=defaultt)
		if file_name == defaultt: return

		self.mic_file =  SpecManager().import_mic_file(file_name)

	def select_mic(self):
		spec = SpecManager()
		mics = spec.get_mic_specs()

		mic_name = None

		mic_sel = xbmcgui.Dialog().contextmenu(["no microphone"] + mics + ["Import Microphone"])

		if mic_sel < 0: return
		if mic_sel == 0:
			self.mic_file = None
		elif mic_sel == len(mics) + 1:
			self.import_mic()
		else:
			mic_name = mics[mic_sel - 1]
			fn_mic = spec.spec_path + mic_name + ".mic"
			self.mic_file = Spectrum().load(fn_mic)

		self.update_image()

	def handleOK(self):
		fid = self.getFocusId()
		if fid == 3000:	#edit
			self._close()
		elif fid == 3001:	#import
			self.import_spec()
		elif fid == 3002:	#import mic
			self.select_mic()

	def onAction( self, action ):
		#OK pressed
		if action.getId() in [7,100]:
			self.handleOK()

		#Cancel
		if action.getId() in [92,10]:
			self.close()
