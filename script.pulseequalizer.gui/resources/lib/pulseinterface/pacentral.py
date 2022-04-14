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
#    Each message from pulseaudio sytem or user interface arrives here for further processing
#
#
#    ------------------     ------------        -------------      ---------------
#    | MessageCentral | --> | dispatch | ->|<-> | paDatabase| <--> | pulse audio |
#    ------------------ |   ------------   |    -------------      ---------------
#                       |                  |    --------
#                       |                  |--> | self |
#                       |                  |    --------
#         ----------    |                  |    -------------       --------      ----------------
#     --->| update | -->|                  |--> | EqControl |  <--> | dbus | <--> | pa equalizer |
#         ---------                        |    -------------       --------      ----------------
#                                          |    -------------------      ---------------
#                                          |--> | paModuleManager | --> | pulse audio |
#                                               -------------------      ---------------
#
# dispatch: send pa-messages to paDatabase, collect them
#           non pa-messages, such the ones from user interface, are sent to the other modules
# update:   comes 100ms after the last pa-message, triggers the processing of the previoues pa-messages
#           paDatabase caches pulse audio configuration and generates aggregated messages, that are sent to the other modules
# self:     handels some specific requests, such as latency set/get, etc
# EqControl interface to the current equalizer, mainly called on client requests, such ad get_profile/ set_profile, etc
# paModuleManager: reconfigures the playback stream dependend on current configuration and connected devices and playback status

from .pulsecontrol import PulseControl

from pulsectl import PulseError

from .pamodule import paModuleManager

from .padb import paDatabase

from .eqcontrol import EqControl

from helper import SocketCom
from helper import Config

from basic import handle
from basic import opthandle
from basic import log
from basic import logerror

from sound import SoundGen

class MessageCentral():
	def __init__(self):
		# init class structure

		self.pc = PulseControl()
		self.eq = EqControl(self.pc)
		self.config = Config()

		self.padb = paDatabase(self.pc)
		self.sg = SoundGen(self.padb, self.pc)
		self.pamm = paModuleManager(self.pc, self.eq, self.padb, self.config)

	#
	#	start message, called if pulse audio gets connected
	#

	def on_pulse_connect(self):
		log("pact: start pulse control")
		self.pc.start()
		self.padb.on_pa_connect()
		self.pamm.on_pa_connect()

		SocketCom("kodi").call_func("up","service",[])
		SocketCom("kodi").call_func("get","player",[])

	#
	# Dispatch messages
	#

	def on_message(self, target, func, arg, conn):
		try:
			# filter messages
			if self.padb.on_message(target, func, arg): return

			# other messages are just forwarded

			cmd = "on_" + target + "_" + func
			methods = []

			for cl in [self.padb, self, self.pamm, self.eq, self.sg]:
				try:methods.append( getattr(cl,cmd))
				except AttributeError: pass
				except Exception as e: opthandle(e)

			if len(methods) == 0:
				SocketCom.respond(conn, None)
				return

			for method in methods:
				ret = method(*arg)
				SocketCom.respond(conn, ret)

		except PulseError as e:
			handle(e)
			logerror("pact: in {},{},{}".format( target, func, str(arg)))
			logerror("pact: try to recover")

			try:
				self.pc.stop()
				self.on_pulse_connect()
			except Exception as e:
				handle(e)
				logerror("pact: recover failed")

		except Exception as e:
			logerror("pact: in {},{},{}".format( target, func, str(arg)))
			handle(e)

	#
	#	message collector, just collect fast incomeing messages from pulse audio
	#	handle them after a timeout
	#

	def on_pa_update(self):
		log("pact: on_pa_update")

		messages = self.padb.do_update()

		for message,arg in messages:
			try:
				method = getattr(self.pamm, message)
			except Exception:	continue
			method(*arg)

		self.pamm.do_update()
		log("pact: %s" % str(self.padb))

		for message,arg in messages:
			try:
				method = getattr(self.sg, message)
			except Exception:	continue
			method(*arg)

	#
	#	message handler of self
	#

	#def on_outlist_get(self):
	#	return self.padb.get_outlist()

	def on_latency_get(self):
		return self.padb.get_latency()

	def on_latency_set(self,latency_info):
		self.pc.set_port_latency(latency_info)

		if self.padb.output_sink:
			if self.padb.cureq_sink:
				self.config.set("eq_latency", int(latency_info["latency"]),self.padb.output_sink.name)
			else:
				self.config.set("latency", int(latency_info["latency"]),self.padb.output_sink.name)

	# just save the current selected profile to config file
	def on_eq_profile_load(self,_index, profile):
		if self.padb.output_sink:
			self.config.set("eq_profile", profile,self.padb.output_sink.name)

	# just save the current selected room correction to config file
	def on_room_correction_set(self,_index, name):
		if self.padb.output_sink:
			self.config.set("eq_correction", name,self.padb.output_sink.name)

	# just remove the current selected room correction from config file
	def on_room_correction_unset(self, _index):
		if self.padb.output_sink:
			self.config.set("eq_correction", None,self.padb.output_sink.name)

	# helper
	def on_pa_module_log(self):
		for key,val in list(vars(self.pamm).items()):
			log(key+"="+ str(val))
