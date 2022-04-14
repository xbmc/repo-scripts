#	This file is part of PulseEqualizerGui for Kodi.
#
#	Copyright (C) 2022 wastis    https://github.com/wastis/PulseEqualizerGui
#
#	PulseEqualizerGui is free software; you can redistribute it and/or modify
#	it under the terms of the GNU Lesser General Public License as published
#	by the Free Software Foundation; either version 3 of the License,
#	or (at your option) any later version.
#
#

import os

from basic import path_profile
from basic import path_keymap
from basic import handle
from basic import path_addon
from basic import parse_xml
from .fjson import json

class KeyMapFile():
	sec_list = ["global","fullscreenvideo","fullscreenradio","seekbar","fullscreenlivetv", "visualisation"]

	def __init__(self, file_name = "zEqualizer.xml"):
		self.file_name = path_profile + path_keymap + file_name
		self.lock_name = path_profile + path_keymap + "zzzlock.xml"

		self.reset()

	def reset(self):
		with open(path_addon + "resources/keymap.json") as f:
			self.struct = json.loads(f.read())

		self.index = {}

		for _, val in list(self.struct.items()):
			self.index[val["cmd"]]=val

	def parse_keymap_file(self):
		self.reset()
		print(self.file_name)
		if not os.path.exists(self.file_name):
			return

		with open(self.file_name) as f: content=parse_xml(f.read())

		#pprint.pprint(content)

		for val in content["keymap"]:
			for _, subval in list(val.items()):
				for kb in  subval:
					if "keyboard" not in kb:
						continue
					for keys in kb["keyboard"][0]["key"]:
						if keys["val"] in self.index:
							self.index[keys["val"]]["key"]=int(keys["attr"]["id"][1:-1])

	def create_xml(self):
		templ_keymap = "<keymap>\n{}\n</keymap>"
		templ_sec = '\t<{}>\n\t\t<keyboard>\n{}\t\t</keyboard>\n\t</{}>\n\n'
		templ_key = '\t\t\t<key id="{}">{}</key>\n'

		fin_struct = {}
		for _, val in list(self.struct.items()):
			if val["key"] == 0: continue

			for sec in val["in"]:
				if sec not in fin_struct:
					fin_struct[sec] = []

				fin_struct[sec].append(templ_key.format(val["key"], val["cmd"]))

			if "global" not in val["in"]:
				if "global" not in fin_struct:
					fin_struct["global"] = []
				fin_struct["global"].append(templ_key.format(val["key"], "noop"))

		xml_result = ""
		for sec_name in self.sec_list:
			if sec_name not in fin_struct: continue

			xml_result = xml_result + templ_sec.format(sec_name,"".join(fin_struct[sec_name]),sec_name)

		if xml_result: xml_result = templ_keymap.format(xml_result)
		return xml_result

	def lock(self):
		lock = "<keymap><global><keyboard>"
		for mod in [0, 0xf000, 0x1f000,0x2f000,0x3f000]:
			for i in range(1,256):
				lock=lock + '<key id="{}"></key>'.format(mod + i)
		lock=lock + "</keyboard></global></keymap>"

		with open(self.lock_name,"w") as f:
			f.write(lock)

	def unlock(self):
		if os.path.exists(self.lock_name):
			os.remove(self.lock_name)

	def save(self):
		try:
			xml = self.create_xml()
			if xml != "":
				with open(self.file_name, "w") as f: f.write(xml)
			else:
				os.remove(self.file_name)
		except OSError: pass
		except Exception as e: handle(e)

	def get_info(self,name):
		try:
			return self.struct[name]
		except KeyError: return ""

	def set_info(self,name,key):
		try:
			self.struct[name]["key"]=key
		except KeyError: return

	def is_mapped(self,key):
		for _,val in list(self.struct.items()):
			if int(val["key"]) == key:
				return True
		return False
