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
#	collects pulseaudio messages (new/change/remove) and tacks the current status of sinks/input_streams
#	on request, sends the last message, that actually reflects the current pulseaudio status.
#

#from basic import log

class MessageCollector():
	msg_collector = {}

	@staticmethod
	def process_getlist(target, func):
		try: return target[func]
		except Exception: return []

	@classmethod
	def process_insert(cls,target, func, index):
		f_list = cls.process_getlist(target, func)
		if index in f_list: return target
		f_list.append(index)
		target[func] = f_list
		return target

	@staticmethod
	def process_del(li, index):
		try:
			li.remove(index)
			return True, li
		except Exception: return False, li

	@classmethod
	def process_new(cls,target, index):
		c_list = cls.process_getlist(target, "change")
		_, c_list = cls.process_del(c_list,index)
		target["change"] = c_list

		return cls.process_insert(target,"new", index)

	@classmethod
	def process_change(cls,target, index):
		# filter out changes of elements that are in new
		n_list = cls.process_getlist(target, "new")
		if index in n_list: return target

		# not found in new, so insert it into change
		return cls.process_insert(target,"change", index)

	@classmethod
	def process_remove(cls,target, index):
		# remove change messages of elements, that have been removed
		c_list = cls.process_getlist(target, "change")
		success, c_list = cls.process_del(c_list, index)
		target["change"] = c_list

		# remove added elements, that have been removed
		n_list = cls.process_getlist(target, "new")
		success, n_list = cls.process_del(n_list, index)
		target["new"] = n_list

		if success: return target

		# element had been added earlier, so keep remove
		return cls.process_insert(target,"remove", index)

	def collect_message(self,target,func,index):
		#log("collect on_%s_%s_%d"%(target,func,index))

		try: ctarget = self.msg_collector[target]
		except KeyError: ctarget = {}

		self.msg_collector[target] = getattr(MessageCollector, "process_"+func)(ctarget, index)

	def get_messages_and_clear(self):
		result = {"remove":[],"new":[],"change":[]}
		for target , func_list  in  self.msg_collector.items():
			for func, index_list in func_list.items():
				cmd = "on_%s_%s" % (target,func)
				for index in index_list:
					result[func].append((cmd,[index]))

		self.msg_collector = {}
		return result["remove"] + result["new"] + result["change"]
