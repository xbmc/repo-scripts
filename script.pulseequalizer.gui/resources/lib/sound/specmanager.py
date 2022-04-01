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

import os
import shutil

from helper.fjson import json

from basic import handle
from basic import infhandle
from basic import opthandle
from basic import log
from basic import path_filter
from basic import path_masterprofile
from basic import path_profile
from basic import path_settings

from .spectrum import Spectrum

from .specgroup import SpecGroup

## first one must be flat as it is used as filter for room correction
presets = [
("default", 1.0, [(0,1.0),(125,1.0),(250,1.0),(500,1.0),(1e3,1.0),(2e3,1.0),(4e3,1.0),(8e3,1.0),(16e3,1.0)]),
("Flat", 1.0, [(0,1.0),(125,1.0),(250,1.0),(500,1.0),(1e3,1.0),(2e3,1.0),(4e3,1.0),(8e3,1.0),(16e3,1.0)]),
("Bass", 0.6, [(0, 2.2), (64, 2.2), (125, 1.5), (250, 1.0), (500, 1.0), (750, 1.0), (1000, 1.0), (2000, 1.0), (3000, 1.0), (4000, 1.0), (8000, 1.0), (16000, 1.0)]),
("Speech", 0.4, [(0, 1.0), (64, 1.0), (125, 1.0), (250, 1.0), (500, 0.7), (750, 0.6), (1000, 0.63), (2000, 1.3), (3000, 2), (4000, 2.5), (8000, 1.0), (16000, 1.0)]),
("Super Speech", 0.4, [(0, 0.7), (64, 0.7), (125, 0.7), (250, 0.57), (500, 0.5), (750, 0.5), (1000, 0.6), (2000, 1.0), (3000, 2), (4000, 2.5), (8000, 1.0), (16000, 1.0)])
]

class EqProfile():
	def __init__(self, args = presets[0]):
		self.name = args[0]
		self.preamp = args[1]
		self.spec = Spectrum(args[2])

class SpecManager():
	def __init__(self):
		self.cur_spec = None
		self.name = None

		self.filter_freq = None
		self.filter_rate = None
		self.sample_rate = None

		self.profile = None
		self.profiles = {}

		self.spec_path = path_masterprofile + path_filter
		if not os.path.exists(self.spec_path): os.makedirs(self.spec_path)

		self.prof_path = path_profile + path_settings
		if not os.path.exists(self.prof_path): os.makedirs(self.prof_path)

	def import_mic_file(self,fn):
		name = os.path.split(fn)
		name_base = os.path.splitext(name[1])
		t_fn = self.spec_path +name_base[0]+".mic"
		log("copy to: " + t_fn)
		return name_base[0], Spectrum()._import(fn).save(t_fn)

	def get_mic_specs(self):
		result = []
		files = os.listdir(self.spec_path)
		for f in files:
			nb = os.path.splitext(f)
			try:
				if nb[1] ==  ".mic": result.append(nb[0])
			except Exception as e: opthandle(e)
		return result

	#
	#	filter interface
	#

	def get_fil_specs(self):
		log(self.spec_path)
		result = []
		if not os.path.exists(self.spec_path):
			os.makedirs(self.spec_path)
		files = os.listdir(self.spec_path)

		for f in files:
			log(f)
			if not os.path.isdir(self.spec_path + f): continue

			dfiles = os.listdir(self.spec_path + f)
			for df in dfiles:
				nb = os.path.splitext(df)
				try:
					if nb[1] ==  ".fil": result.append(f)
					break
				except Exception as e: opthandle(e)
		return result

	def select_spec(self, name, channel):
		self.cur_spec = SpecGroup().load_filter(name, channel)
		self.filter_freq = None

	def unselect_spec(self):
		self.cur_spec = None
		self.filter_freq = None

	def remove_spec(self, name):
		fn = self.spec_path + name
		if os.path.exists(fn):
			log("remove %s" % fn)
			shutil.rmtree(fn)

	def get_spec_name(self):
		if self.cur_spec is None: return None
		return  self.cur_spec.name

	#
	#	profiles management
	#

	def set_profile(self,name, preamp, freq_coef):
		self.profile = EqProfile((name, preamp, freq_coef))
		self.filter_freq = None

	def set_profile_default(self):
		self.profile = EqProfile()
		self.filter_freq = None

	def set_frequencies(self, freqs):
		if self.profile is None: self.set_profile_default()
		if freqs[0] != 0: freqs = [0] + freqs
		self.profile.spec = self.profile.spec.convert(freqs)
		self.filter_freq = None

	def get_frequencies(self):
		if self.profile is None: self.set_profile_default()
		return self.profile.spec.get_freqs()

	def get_coefs(self):
		if self.profile is None: self.set_profile_default()
		return self.profile.preamp, self.profile.spec.get_coefs()

	def set_coefs(self,preamp, coefs):
		if self.profile is None: self.set_profile_default()
		self.profile.spec.set_coefs(coefs)
		self.profile.preamp = preamp

	def get_base_profile(self):
		if self.profile is None: self.set_profile_default()
		return self.profile.name

	# profile load-save

	def set_defaults(self):
		if not self.profiles: self.profile_file_load()

		for name,preamp,freq_db in presets[1:]:
			self.profiles[name] = [preamp, freq_db]

		fn = self.prof_path + "profiles.json"
		with open(fn, "w") as f: f.write(json.dumps(self.profiles))

	def profile_file_load(self):
		fn = self.prof_path + "profiles.json"
		try:
			with open(fn) as f: self.profiles = json.loads(f.read())
			if not isinstance(self.profiles,dict):
				self.profiles={}
		except IOError: self.profiles = {}
		except Exception as e:
			infhandle(e)
			self.profiles = {}

	def profile_load(self, name):
		if not self.profiles: self.profile_file_load()
		try:
			self.profile = EqProfile([name] + self.profiles[name])
		except KeyError:
			log("cannot find %s, load default profile" % name)
			self.profile = EqProfile()
		except Exception as e: handle(e)
		self.filter_freq = None

	def profile_unload(self):
			self.profile = EqProfile()
			self.filter_freq = None

	def profile_save(self,name):
		if name == "default": return
		if not self.profiles: self.profile_file_load()
		if self.profile is None: self.set_profile_default()
		self.profiles[name] = [self.profile.preamp, self.profile.spec.freq_db]

		fn = self.prof_path + "profiles.json"
		with open(fn, "w") as f: f.write(json.dumps(self.profiles))

	def profiles_get(self):
		if not self.profiles: self.profile_file_load()
		try:
			return [x for x in self.profiles.keys()]
		except Exception: return []

	def profile_remove(self,name):
		if not self.profiles: self.profile_file_load()
		try:
			del self.profiles[name]
		except Exception as e: opthandle(e)

		fn = self.prof_path + "profiles.json"
		with open(fn, "w") as f: f.write(json.dumps(self.profiles))

	def calc_filter_freq(self, spec, filter_rate, sample_rate):
		self.filter_rate = filter_rate
		self.sample_rate = sample_rate
		fac = float(filter_rate) / float(sample_rate)
		self.filter_freq = [int(round(x * fac)) for x in spec.get_freqs()]

	def get_ffreq_coef(self,filter_rate, sample_rate):
		if self.profile is None: self.set_profile_default()
		if self.cur_spec and self.profile:
			spec =  self.cur_spec.apply_profile(self.profile.spec)
			preamp = self.profile.preamp
			info = "room correction %s and profile %s" % (self.cur_spec.name , self.profile.name)
		elif self.profile:
			spec =  self.profile.spec
			preamp = self.profile.preamp
			info = "profile %s and no room correction" % (self.profile.name)
		elif self.cur_spec:
			spec =  self.cur_spec
			preamp = 1.0
			info = "room correction %s and no profile" % (self.cur_spec.name)
		else:
			log("no room correction and no profile have been selected")
			return None

		spec = spec.set_filter_range(sample_rate // 2)

		if not self.filter_freq or filter_rate != self.filter_rate or sample_rate != self.sample_rate:
			self.calc_filter_freq(spec, filter_rate, sample_rate)

		if spec.__class__.__name__ == "Spectrum":
			coefs = [spec.get_coefs()]
		else: coefs = spec.get_coefs()

		log("%s, number of channels: %s" % (info, len(coefs)))

		return self.filter_freq, preamp, coefs
