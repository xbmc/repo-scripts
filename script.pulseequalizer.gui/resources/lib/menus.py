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
import xbmcgui

from helper import json
from helper import SocketCom

from basic import handle
from basic import logerror
from basic import path_addon

from time import sleep

from volumegui import VolumeGui
from eqdialog import eqDialog
from sweepgengui import SweepGenGui
from rundialog import runDialog
from importgui import ImportGui
from latencygui import LatencyGui
from keymapgui import keymapDialog
from contextmenu import contextMenu

from skin import tr

class Menu():
	skin = "Default"

	def __init__(self):
		self.cwd = path_addon

	#
	#	Menu selectors
	#

	def sel_main_menu(self):
		contextMenu(funcs = [(tr(32006),self.sel_profile),
							(tr(32007),self.sel_equalizer),
							(tr(32008),self.sel_device),
							(tr(32027),self.sel_correction),
							(tr(32010),self.sel_latency),
							(tr(32036),self.sel_sysvol),
							(tr(32750),self.sel_keymap)])

	def sel_menu(self, command = "None"):
		if command == "None": self.sel_main_menu()
		else:
			func = 'sel_' + command
			try: method = getattr(self, func)
			except Exception:
				method = None
				logerror("unkonwn command: '%s'" %(func))

			if method: method()

	#
	#  helper
	#

	def check_func_available(self):
		self.current = SocketCom("server").call_func("get","eq_current")
		eqid, desc, is_playing, eq_profile, is_dyn = ( self.current )

		if eqid == -1:
			# Dialog equalizer not installed
			xbmcgui.Dialog().ok(tr(32004),tr(32035))
			return False, eqid, desc, is_playing, eq_profile, is_dyn

		if is_playing and eq_profile=='off' and is_dyn:
			# Dialog switch on?
			if not xbmcgui.Dialog().yesno(tr(32000), tr(32003)):
				return False, eqid, desc, is_playing, eq_profile, is_dyn
			else:
				SocketCom("server").call_func("switch","eq_on")

				count = 10
				while count > 0:
					count = count - 1
					self.current = SocketCom("server").call_func("get","eq_current")
					eqid, desc, is_playing, eq_profile, is_dyn = ( self.current )
					if eqid  is not None: return True , eqid, desc, is_playing, eq_profile, is_dyn
					sleep(0.1)
			# Dialog problem switch on
			xbmcgui.Dialog().ok(tr(32004),tr(32005))
			return False, eqid, desc, is_playing, eq_profile, is_dyn
		# all ok
		return True, eqid, desc, is_playing, eq_profile, is_dyn

	#
	#	different Menues
	#

	#
	#	select profile
	#

	def sel_profile(self):
		func_available, eqid, _, is_playing, _, is_dyn =  self.check_func_available()
		if not func_available: return

		self.eqid = eqid

		include_switch_off = is_dyn and is_playing

		profiles = SocketCom("server").call_func("get","eq_profiles")
		profile = SocketCom("server").call_func("get","eq_base_profile")

		if include_switch_off: profiles = [tr(32011)] + profiles

		funcs = [(tr(32014),self.sel_new_profile),(tr(32015),self.sel_delete_profile),(tr(32016),self.sel_load_defaults)]

		sel = contextMenu(items = profiles, default = profile, funcs = funcs)

		if sel is None: return
		if include_switch_off and sel == 0:
			SocketCom("server").call_func("switch","eq_off")
		else:
			SocketCom("server").call_func("load","eq_profile" , [eqid, profiles[sel]])

	#
	#	room correction
	#

	def sel_correction(self):
		func_available, eqid, _, _, _, _ =  self.check_func_available()
		if not func_available: return

		corrections = SocketCom("server").call_func("get","room_corrections")
		correction = SocketCom("server").call_func("get","room_correction")
		if correction is None: correction = tr(32411)

		corrections = [tr(32411)] + corrections

		funcs = [(tr(32033),self.sel_import_correction),(tr(32028), self.sel_delete_correction),(tr(32032),self.sel_playsweep)]

		sel = contextMenu(items = corrections, default = correction, funcs = funcs)

		if sel is None: return
		if sel == 0:
			SocketCom("server").call_func("unset","room_correction", [eqid])
			return

		SocketCom("server").call_func("set","room_correction" , [eqid, corrections[sel]])

	#
	#	configure equalizer
	#

	def sel_equalizer(self):
		try:
			func_available, eqid, desc, is_playing, _, _ =  self.check_func_available()
			if not func_available: return

			eqDialog(eqid = eqid, desc=desc, is_playing=is_playing)
		except Exception as e: handle(e)

	#
	#	select output device
	#

	@staticmethod
	def sel_device():
		response = xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Settings.GetSettings", "params":{ "filter": {"section":"system", "category":"audio"}}, "id":1}')
		r_dict = json.loads( response )

		settings = r_dict["result"]["settings"]
		for s in settings:
			if s["id"] == "audiooutput.audiodevice":
				value = s["value"]
				options = s["options"]

				sel_lables = []
				sel_values = []
				preselect = 0
				index = 0
				for o in options:
					if "eq-auto-load" in o["value"]: continue

					if o["value"] == value:
						preselect = index

					sel_values.append(o["value"])
					sel_lables.append(o["label"].replace("(PULSEAUDIO)",''))
					index = index + 1

		# device selection Dialog

		sel = contextMenu( items = sel_lables, default = sel_lables[preselect], width = 1000)

		if sel is None: return

		response = xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Settings.SetSettingValue", "params":{"setting":"audiooutput.audiodevice", "value":"%s"}, "id":1}' %(sel_values[sel]))
		SocketCom("server").call_func("set","device" , [sel_values[sel]])

	#
	#	manage profiles
	#

	def sel_manager(self):
		func_available, eqid, _, _, _, _ =  self.check_func_available()
		if not func_available: return

		self.eqid = eqid
		contextMenu(funcs = [(tr(32014),self.sel_new_profile),(tr(32015),self.sel_delete_profile),(tr(32016),self.sel_load_defaults)])

	def sel_new_profile(self):
		# Name for new Profile
		profile = xbmcgui.Dialog().input(tr(32017))
		if profile != '':
			SocketCom("server").call_func("save","eq_profile" , [profile])
			SocketCom("server").call_func("load","eq_profile" , [self.eqid, profile])
		self.sel_profile()

	def sel_delete_profile(self):
		profiles = SocketCom("server").call_func("get","eq_profiles")

		if not profiles: return

		nr = contextMenu(items = profiles)
		if nr is None: return

		# sure to delete
		del_profile = profiles[nr]
		if xbmcgui.Dialog().yesno(tr(32018) % del_profile,tr(32019) % del_profile)  is True:
				SocketCom("server").call_func("remove","eq_profile" , [del_profile])
		self.sel_profile()

	def sel_load_defaults(self):
		# load predefined
		SocketCom("server").call_func("set","eq_defaults")
		self.sel_profile()

	#
	#	manage corrections
	#

	def sel_cor_manager(self):
		contextMenu(funcs = [(tr(32033),self.sel_import_correction),(tr(32028), self.sel_delete_correction),(tr(32032),self.sel_playsweep)])
		self.sel_correction()

	def sel_delete_correction(self):
		corrections = SocketCom("server").call_func("get","room_corrections")

		if not corrections: return

		nr = contextMenu(items = corrections)
		if nr is None: return

		del_correction = corrections[nr]
		# sure to delete
		if xbmcgui.Dialog().yesno(tr(32030) % del_correction,tr(32031) % del_correction)  is True:
			SocketCom("server").call_func("remove","room_correction" , [del_correction])
		self.sel_correction()

	def sel_playsweep(self):
		runDialog(SweepGenGui,"SweepGen")
		self.sel_correction()

	def sel_import_correction(self):
		runDialog(ImportGui,"ImportDialog")
		self.sel_correction()

	#
	#	show latency slider
	#

	@staticmethod
	def sel_latency():
		runDialog(LatencyGui,"OsdLatencyOffset")

	#
	#	show volume progress bar
	#

	def sel_volup(self):
		volgui = VolumeGui("OsdVolume.xml" ,self.cwd, self.skin, updown = 'up')
		volgui.doModal()

	def sel_voldown(self):
		volgui = VolumeGui("OsdVolume.xml" , self.cwd, self.skin, updown = 'down')
		volgui.doModal()

	def sel_sysvol(self):
		volgui = VolumeGui("OsdVolume.xml" , self.cwd , self.skin, updown = "none")
		volgui.doModal()

	#
	#	keymap
	#

	@staticmethod
	def sel_keymap():
		keymapDialog()
