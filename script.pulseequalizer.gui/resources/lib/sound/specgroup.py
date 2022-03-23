#!/usr/bin/python3

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

from .spectrum import Spectrum
from helper import handle, log, path_addon, path_filter

class SpecGroup():
	def __init__(self, speclist={}, src=None):
		self.name = None
		self.preamp = 1.0
		self.speclist = {}

		self.filenames = {}
		self.relvol = {}
		self.count = 0

		if src :
			self.name = src.name
			self.preamp = src.preamp
			self.speclist = src.speclist
			self.filenames = src.filenames
			self.count = src.count
			self.relvol = src.relvol

		if speclist: self.speclist = speclist
		log("SPEC %s" % repr(self.speclist))

	def load(self, filename):
		path, fn = os.path.split(filename)
		name, ext = os.path.splitext(fn)
		name, nr  = os.path.splitext(name)

		self.name = name

		cnt = 0

		try:
			nr = int(nr[1:])

			for i in range(1,10):
				fn = "%s/%s.%s%s" % (path, name, i, ext)
				if not os.path.exists(fn): continue
				log("load %s" % fn)

				self.speclist[i] = Spectrum().load(fn)
				self.filenames[i] = "%s.%s%s" % (name, i, ext)
				cnt = cnt + 1
		except ValueError: pass
		except Exception as e: handle(e)

		if not cnt:
			if os.path.exists(filename):
				self.speclist[0] = Spectrum().load(filename)
				self.filenames[0] = fn
				cnt = 1

		self.count = cnt
		return self

	def load_filter(self, name, channels):
		self.speclist = {}
		self.filenames = {}
		self.name = name

		path = path_addon + path_filter + name + "/%s.fil"
		if os.path.exists(path % "all" ):
			channels = ["all"]

		cnt = 0
		for n in channels:
			fn = path % n
			if os.path.exists(fn):
				log("load room correction %s:  %s.fil" % (name, n))
				self.speclist[cnt] = Spectrum().load(fn)
				self.filenames[cnt] = "%s.%s" % (name, cnt)
				cnt = cnt + 1
			else:
				log("missing channel in room correction %s: requires: %s" % (name,repr(channels)))
				return None

		return self

	def apply_profile(self, prof_spec):
		speclist = {}

		for key, spec in self.speclist.items():
			speclist[key] = spec * prof_spec

		return SpecGroup(speclist,self)

	def get_coefs(self):
		result = []
		for _, spec in self.speclist.items():
			result.append(spec.get_coefs())

		return result

	def set_filter_range(self, maxf):
		speclist = {}

		for key, spec in self.speclist.items():
			speclist[key] = spec.set_filter_range(maxf)

		return SpecGroup(speclist,self)

	def get_freqs(self):
		try: return self.speclist[0].get_freqs()
		except Exception: return None

	def update_relvol(self):
		speclist = {}
		relvol = {}
		minval = None #smallest maxval
		for key, spec in self.speclist.items():
			ns = spec.update_minmax()
			speclist[key] = ns
			if minval is None:  minval = ns.maxval
			elif minval > ns.maxval: minval = ns.maxval

		for key, spec in speclist.items():
			relvol[key] = minval - spec.maxval

		self.speclist = speclist
		self.relvol = relvol

		return self

