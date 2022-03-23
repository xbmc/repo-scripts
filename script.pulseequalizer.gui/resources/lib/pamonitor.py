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
import json

from pulseservice import PulseService
from helper import SocketCom
from time import sleep

class PaMonitor( xbmc.Monitor ):
	def __init__( self , pid = 0):
		#strat process
		xbmc.Monitor.__init__( self )
		xbmc.log("eq: start PulesEqualizer service",xbmc.LOGDEBUG)

		self.server_sock = SocketCom("kodi")
		if not self.server_sock.is_server_running():
			self.server_sock.start_func_server(self)
		else: self.server_sock = None

		self.sock = SocketCom("server")

		ps = PulseService()
		ps.start()
		sleep(0.5)
		self.sock.call_func("set","device",[self.get_device()])

		while not self.abortRequested():
			if self.waitForAbort( 10 ):
				break

		ps.stop()
		if self.server_sock:
			self.server_sock.stop_server()

	@staticmethod
	def get_device():
		device = ""
		r_dict = json.loads(xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Settings.GetSettings", "params":{ "filter": {"section":"system", "category":"audio"}}, "id":1}'))
		for s in r_dict["result"]["settings"]:
			if s["id"] == "audiooutput.audiodevice":
				device = s["value"]
				break
		return device

	def on_device_get(self):
		result = self.get_device()
		xbmc.log("eq: kodi service: on_device_get %s" % result,xbmc.LOGDEBUG)
		return result

	@staticmethod
	def on_player_get():
		r_dict = json.loads(xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Player.GetActivePlayers","id":0}'))
		try: return r_dict["result"]
		except Exception: return None

	@staticmethod
	def on_log_write(message, level):
		xbmc.log(message, level)

	def onNotification( self, sender, method, data ):
		target,func = method.lower().replace("on","").split(".")
		if target in ["system", "player"]:
			self.sock.call_func(func, target)

