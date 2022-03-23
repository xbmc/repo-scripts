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

from helper import handle, opthandle, log
import os

class MessagCollector():
	def __init__(self):
		self.new = []
		self.change = []
		self.remove = []

	def on_new(self, index):
		self.new.append(index)

	def on_change(self,index):
		if index in self.new: return
		self.change.append(index)

	def on_remove(self,index):
		try: self.change.remove(index)
		except Exception as e: opthandle(e)

		try: self.new.remove(index)
		except Exception: self.remove.append(index)

	def dispatch(self, rec_class, target):
		for l in ["change", "remove","new"]:
			index_list = getattr(self , l)
			cmd = "on_%s_%s" % (target, l)
			try:
				method = getattr(rec_class,cmd)
				for index in index_list:
					method(index)
			except Exception as e: opthandle(e)

class CurIndex():
	def __init__(self):
		self.index = None
		self.old = None
		self.update = False
		self.pending = None

	def __str__(self):
		return "index:%s update:%s" %(str(self.index), str(self.update))

	def set(self, index):
		self.update = True if index != self.index else False
		self.old = self.index
		self.index = index

	def set_pending(self, index):
		self.pending = index

	def commit(self):
		self.set(self.pending)
		self.pending = None

	def get(self):
		return self.index

class PaCurrent():
	KodiClient =  CurIndex()
	KodiSinkInput =  CurIndex()
	KodiDefaultOutput = CurIndex()
	KodiFirstSink = CurIndex()
	AutoEqSink =  CurIndex()
	AutoEqSinkInput =  CurIndex()

	target_list = ["sink", "sink_input", "client", "card"]
	collect = {}

	def __init__(self, pulsecontrol):
		self.pc = pulsecontrol

	def __str__(self):
		#return "\n".join(["%s=%s" %(key,val) for key,val in vars(self).items()])
		return str(self.KodiClient)

	def start(self):
		for target in self.target_list:
			self.update_list(target)

	def on_message(self, target, func, arg = ''):
		if target not in ["sink", "sink_input", "client", "card", "module"]: return False
		log("PaCurrent: %s_%s %s" % (target,func, str(arg)))

		l = "mes_" + target
		try: obj = getattr(self , l)
		except Exception: obj = MessagCollector()

		try:
			method =  getattr(obj , "on_"+func)
			method(arg)
			setattr(self, l, obj)
		except Exception: return False
		return True

	def on_pa_update(self):
		log("PaCurrent: on_pa_update" )
		self.update_changes()
		self.find_kodi_client()
		self.parse_sink_inputs()
		self.parse_sinks()
		self.send_messages()

	def update_changes(self):
		for target in self.target_list:
			l = "mes_" + target
			targets = target + "s"

			try:
				target_dic = getattr(self , targets)
				obj = getattr(self , l)

				index_list = getattr(obj,"remove")
				for index in index_list:
					try: del target_dic[index]
					except Exception as e: handle(e)

				for func in ["change", "new"]:
					index_list = getattr(obj,func)
					for index in index_list:
						target_dic[index] = self.pc.get_info(target,index)

				setattr(self, targets, target_dic)
			except Exception as e: opthandle(e)

	def send_messages(self):
		for target in self.target_list:
			l = "mes_" + target
			targets = target + "s"

			try:
				target_dic = getattr(self , targets)
				obj = getattr(self , l)

				for func in ["remove", "change", "new"]:
					index_list = getattr(obj,func)
					for index in index_list:
						target_dic[index] = self.pc.get_info(target,index)

				setattr(self, l, {})
			except Exception as e: opthandle(e)

	def update_list(self,target):
		targets = target + "s"
		result = {}
		for obj in self.pc.get_list(target):
			result[obj.index] = obj
		setattr(self, targets, result)

	def find_kodi_client(self):
		self.collect["c_kodi_client"] = None

		pid = str(os.getgid())
		for cid,client in self.clients.items():
			if client.name in ['Kodi'] and client.proplist['application.process.id']==pid:
				self.collect["c_kodi_client"] = cid

		#no kodi client with pid matching myself, I might be the develop script, so pick first kodi
		if self.collect["c_kodi_client"]  == None:
			for cid,client in self.clients.items():
				if client.name in ['Kodi']:
					self.collect["c_kodi_client"] = cid

	def parse_sink_inputs(self):
		self.collect["c_kodi_sink_input"] = None
		self.sink_input_by_owner = {}
		self.equalizer = {}

		for index, sink_input in self.sink_inputs.items():
			print(sink_input)
			# update lookup
			self.sink_input_by_owner[sink_input.owner_module] = index

			# update client
			if sink_input.client == self.KodiClient:
				self.collect["c_kodi_sink_input"] = index

	def parse_sinks(self):
		self.sink_by_name = {}

		for index, sink in self.sinks.items():
			self.sink_by_name[sink.name] = sink

			if sink.name == "eq-auto-load":
				self.collect["c_eq_auto_sink"] = index
				self.collect["c_eq_auto_sink_input"] = self.sink_input_by_owner[sink.owner_module]

	def find_kodi_default_output(self):
		if self.collect["c_kodi_sink_input"] is None: return

		sink = self.sinks[self.collect["c_kodi_sink_input"].sink]
		self.collect["c_kodi_first_sink"] = sink

		while True:
			try:
				sink = self.sink_by_name[sink.proplist["device.master_device"]]
			except Exception: break

		self.collect["c_kodi_first_sink"] = sink

