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

#
#	stores user selections linked to pulseaudio-devices in the settings directory
#

import os
import json

from .handle import handle, log
from .path import path_addon, path_settings

class Config():
	config = {}
	name = ""

	def __init__(self):
		path_name = path_addon + path_settings
		if not os.path.exists(path_name): os. makedirs(path_name)
		self.file_name = os.path.join(path_name,"config.json")

	def __str__(self):
		return "%s: $%s" % (self.name , json.dumps(self.config))

	def load_config(self):
		log("conf: load_config %s" % self.file_name)
		try:
			with open(self.file_name,'r')as f: self.config = json.loads(f.read())
		except IOError:
			log("conf: cannot open config.json, settings is empty")
			self.config = {}
		except Exception as e:
			handle(e)
			self.config = {}

		#log(json.dumps(self.config))

	def save_config(self):
		try:
			with open(self.file_name,'w')as f: f.write(json.dumps(self.config))
		except Exception as e: handle(e)

	def set_name(self, name_first, name_last):
		self.name = "%s.%s" % (name_first, name_last)

	def get(self, key, default = None, name = None):
		#log("conf: get %s %s" % (key, name))
		if name is None: name = self.name
		if name is None: return default

		if self.config == {}: self.load_config()
		if self.config == {}:
			self.config[name] = {}

		#log(json.dumps(self.config))
		try: sec = self.config[name]
		except Exception: sec = {}

		try: return sec[key]
		except Exception:
			sec[key] = default
			self.config[name] = sec
			self.save_config()
			return default

	def set(self, key, val, name = None):
		if name is None: name = self.name
		if name == None: return

		try: sec = self.config[name]
		except Exception: sec = {}

		sec[key]= val
		self.config[name] = sec
		self.save_config()
