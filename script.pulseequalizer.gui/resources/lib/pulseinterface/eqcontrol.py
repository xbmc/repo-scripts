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
#   main interface to the equalizer via dbus
#   uses SpecManager to load/save/change equalizer/room correction profiles 
#   and to caputure slider changes
#   if needed, send changes to equalizer. 
#
#   user request <-> spec manager -> dbus <-> equalizer


import sys
import json
import padbus

from padbus import DBusInterface as IF
from padbus import PulseDBus
from helper import *
from sound import SpecManager
from .pulsecontrol import PulseControl


class FilterParam(): pass

class EqControl():
	default_freq = [31.75,63.5,125,250,500,1e3,2e3,4e3,8e3,16e3]
	frequencies = [31.75,63.5,125,250,500,1e3,2e3,4e3,8e3,16e3]
	
	#current_id = None
	
	def __init__(self, pc):
		self.pc = pc
		self.eq_param = {}
		self.spec = SpecManager()
		
	def on_pa_connect(self):
		self.pulse_dbus = PulseDBus()
		
	def get_filter_param(self, index):
		
		try: return self.eq_param[index]
		except: pass
		
		param = FilterParam()

		param.path = "/org/pulseaudio/core1/sink" + str(index)
		param.channels = self.pc.get_sink_channel(index)
		param.channel = len(param.channels)
		param.sample_rate = self.pulse_dbus.get_property(IF.EQUALIZER_I, param.path, 'SampleRate')
		param.filter_rate = self.pulse_dbus.get_property(IF.EQUALIZER_I, param.path, 'FilterSampleRate')

		self.eq_param[index] = param
		return self.eq_param[index]

	def eq_filter_get(self, index, filter_freq):
		param = self.get_filter_param(index)
		coefs, preamp = self.pulse_dbus.call_func(IF.EQUALIZER_I,param.path,'FilterAtPoints',"uau",param.channel,filter_freq)
		preamp = preamp[1] if sys.version_info[0] > 2 else preamp
		return [preamp, coefs]
	
	def eq_filter_set(self, param, filter_freq, preamp, coefs):
		if len(coefs) == 1:
			self.pulse_dbus.call_func(IF.EQUALIZER_I,param.path,'SeedFilter',"uauadd",param.channel, filter_freq, coefs[0], preamp)
		else:
			for channel in range(len(coefs)):
				self.pulse_dbus.call_func(IF.EQUALIZER_I,param.path,'SeedFilter',"uauadd",channel, filter_freq, coefs[channel], preamp)

	def eq_state_save(self, index):
		param = self.get_filter_param(index)
		self.pulse_dbus.call_func(IF.EQUALIZER_I,param.path,'SaveState')

	def eq_profile_load(self,index, profile):
		param = self.get_filter_param(index)
		self.pulse_dbus.call_func(IF.EQUALIZER_I,param.path,'LoadProfile',"us", param.channel, profile)

	def eq_profile_save(self,index, profile):
		param = self.get_filter_param(index)
		self.pulse_dbus.call_func(IF.EQUALIZER_I,param.path,'SaveProfile',"us",param.channel,profile)
	
	def eq_base_profile_get(self, index):
		param = self.get_filter_param(index)
		return self.pulse_dbus.call_func(IF.EQUALIZER_I,param.path,'BaseProfile',"u", param.channel)

	def eq_profiles_get(self):
		return self.pulse_dbus.get_property(IF.MANAGER_I,IF.MANAGER_P, 'Profiles')
		
	def eq_profile_remove(self,profile):
		self.pulse_dbus.call_func(IF.MANAGER_I,IF.MANAGER_P,'RemoveProfile',"s", profile)
		
	@staticmethod
	def freq_extend(sample_rate, xs):
		return [0]+xs+[sample_rate//2]

	@staticmethod
	def translate_rates(dst,src,rates):
		return list([x*dst/src for x in rates])

	def calc_filter_freq(self, filter_rate, sample_rate, frequencies):
		return [int(round(x)) for x in self.translate_rates(filter_rate,sample_rate,self.freq_extend(sample_rate, frequencies))]


	#
	#**************** new ********************************************
	#


	def seed(self, index):
		param = self.get_filter_param(index)
		filter_freq, preamp, coefs = self.spec.get_ffreq_coef(param.filter_rate, param.sample_rate)
		self.eq_filter_set(param, filter_freq, preamp, coefs)
	
	def on_room_corrections_get(self):
		return self.spec.get_fil_specs()
		
	def on_room_correction_get(self):
		return self.spec.get_spec_name()
		
	def on_room_correction_set(self,index,name):
		self.spec.select_spec(name, self.get_filter_param(index).channels)
		self.seed(index)
		
	def on_room_correction_unset(self, index):
		self.spec.unselect_spec()
		self.seed(index)
		
	def on_room_correction_remove(self,name):
		self.spec.remove_spec(name)
		
	def on_eq_base_profile_get(self):
		return self.spec.get_base_profile()

	def on_eq_frequencies_get(self):
		return self.spec.get_frequencies()
	
	def on_eq_frequencies_set(self, freqs):
		return self.spec.set_frequencies(freqs)
		
	def on_eq_filter_get(self):
		return self.spec.get_coefs()
		
	def on_eq_filter_set(self, index, preamp, coefs):
		self.spec.set_coefs(preamp, coefs)
		self.seed(index)
		
	def on_eq_profiles_get(self):
		return self.spec.profiles_get()
		
	def on_eq_profile_load(self, index, name):
		self.spec.profile_load(name)
		self.seed(index)
		
	def on_eq_profile_unload(self, index):
		self.spec.profile_unload()
		self.seed(index)
		
	def on_eq_profile_save(self, name):
		return self.spec.profile_save(name)
		
	def on_eq_profile_remove(self, name):
		self.spec.profile_remove(name)
		
	def on_eq_defaults_set(self):
		self.spec.set_defaults()
		


