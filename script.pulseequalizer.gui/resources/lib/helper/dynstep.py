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

import time

class DynStep():
	def __init__(self, step, fstep, min_step, keycnt):
		# dynamic key step management
		self.keycnt = keycnt
		self.same_key_count = keycnt
		self.last_buc = 0
		self.min_dt = float(1)

		self.last_key = time.time()

		self.min_step = min_step #min step size
		self.step = step #normal step size
		self.fstep = fstep #fast step size
		self.dynstep = step #dynamic step size

	def dynamic_step(self, buc):
		t = time.time()
		dt = t - self.last_key
		self.last_key = t

		if buc == 0: return #mouse
		if dt < float(0.1): return #fast remote
		if self.step != float(self.min_step): return #manually configured step

		if dt - self.min_dt > float(0.15):
			self.dynstep = self.step
			self.same_key_count = self.keycnt
			self.min_dt = float(1)

		elif dt >= float(0.7):
			self.dynstep = self.step
			self.same_key_count = self.keycnt
			self.min_dt = float(1)

		elif buc != self.last_buc:
			self.dynstep = self.step
			self.same_key_count = self.keycnt
			self.min_dt = float(1)

		else:
			if self.same_key_count == 0:
				self.dynstep = self.fstep

			else: self.same_key_count -= 1

		if self.min_dt > dt: self.min_dt = dt
		self.last_buc = buc
