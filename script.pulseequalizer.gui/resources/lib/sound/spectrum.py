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
import re

from basic import handle

class Spectrum():
	def __init__(self, freq_db = []):
		self.freq_db = []
		self.index = -1
		self.size = 0

		self.maxval=None
		self.minval=None

		self.freq_db = freq_db
		self.size = len(freq_db)

	def __str__(self):
		return repr(self.freq_db)

	#def __repr__(self):
	#	return self.freq_db

	def __len__(self):
		return self.size

	def __iter__(self):
		self.index = -1
		return self

	def __next__(self):
		self.index = self.index + 1
		if self.index >= self.size:
			raise StopIteration
		return self.freq_db[self.index]

	def iter(self):
		self.index = -1
		return self

	def next(self):
		self.index = self.index + 1
		if self.index >= self.size - 1:
			raise StopIteration

		return (self.freq_db[self.index] + self.freq_db[self.index + 1])

	@staticmethod
	def add(v1, v2): return v1 + v2
	@staticmethod
	def sub(v1, v2): return v1 - v2
	@staticmethod
	def mul(v1, v2): return v1 * v2
	@staticmethod
	def div(v1, v2): return v1 / v2

	def __add__(self, other):
		return self.merge(other, "add")
	def __sub__(self, other):
		return self.merge(other, "sub")
	def __mul__(self, other):
		return self.merge(other, "mul")
	def __div__(self, other):
		return self.merge(other, "div")

	def merge(self, other, func ="add"):
		if other is None: return self

		func = getattr(self , func)

		it = self.iter()
		ot = other.iter()

		itf1, itv1, itf2, itv2 = it.next()
		otf1, otv1, otf2, otv2 = ot.next()

		result = []
		try:
			# first value
			if itf1 < otf1:
				while itf2 < otf1: itf1, itv1, itf2, itv2 = it.next()
				m = (itv2 - itv1) / (itf2 - itf1)
				val = (otf2 - itf1) * m + itv1
				result.append((otf1,func(val, otv1)))

			elif itf1 > otf1:
				while otf2 < itf1: otf1, otv1, otf2, otv2 = ot.next()
				m = (otv2 - otv1) / (otf2 - otf1)
				val = (itf2 - otf1) * m + otv1
				result.append((itf1,func(itv1,val)))

			while True:
				m = (otv2 - otv1) / (otf2 - otf1)
				while itf2 < otf2:
					val = (itf2 - otf1) * m + otv1
					result.append((itf2, func(itv2, val)))
					itf1, itv1, itf2, itv2 = it.next()

				m = (itv2 - itv1) / (itf2 - itf1)
				while otf2 < itf2:
					val = (otf2 - itf1) * m + itv1
					result.append((otf2, func(val, otv2)))
					otf1, otv1, otf2, otv2 = ot.next()

				if itf2 == otf2:
					result.append((itf2, func(itv2,  otv2)))
					itf1, itv1, itf2, itv2 = it.next()
					otf1, otv1, otf2, otv2 = ot.next()
		except StopIteration: pass

		return Spectrum(result)

	def convert(self, freq):
		result = []
		it = self.iter()
		itf1, itv1, itf2, itv2 = it.next()
		m = (itv2 - itv1) / (itf2 - itf1)

		fr = iter(freq)
		f = next(fr)

		while f < itf1:
			result.append((f , itv1))
			f = next(fr)

		try:
			while True:
				if f <= itf2:
					val = (f - itf1) * m + itv1
					result.append((f , val))
					f = next(fr)
				else:
					try:
						itf1, itv1, itf2, itv2 = it.next()
						m = (itv2 - itv1) / (itf2 - itf1)
					except StopIteration:
						try:
							while True:
								result.append((f , itv2))
								f = next(fr)
						except StopIteration: pass
						break
		except StopIteration: pass
		return Spectrum(result)

	def _import(self, fn):
		self.load(fn)
		if self.size < 2: raise IOError(100,"No 'frequency' 'value' pairs found")

		try:
			it = self.iter()
			while True:
				itf1, _, itf2, _ = it.next()
				if itf1 >= itf2:
					self.freq_db = []
					self.size = 0
					raise IOError(101,"frequencies are not in the correct order at line %s frequency %s" % (it.index, itf1))
		except StopIteration: pass
		return self

	def load(self, fn):
		with open(fn) as f: content = f.read().replace(",",".")
		p = content.rfind("(dB)")
		if p > -1: content = content[p+4:]

		res = re.compile('\s*([0-9\.]+)\s*[;\t]\s*([\-0-9\.]+)\s*', re.DOTALL | re.I).findall(content)
		self.freq_db = [(float(f),float(v)) for f,v in res]
		self.size = len(self.freq_db)
		return self

	def save(self, fn):
		if not self.freq_db: return
		t = ""
		for f, v in self.freq_db:
			t = t + "%s\t%s\n" % (str(f),str(v))
		with open(fn,"w") as f: f.write(t.replace(".",","))
		return self

	def as_coef(self):
		result = []
		for f,v in self.freq_db:
			coef = 10**(v / 20)

			result.append((f,coef))
		return Spectrum(result)

	def shift_inverse(self, manshift):
		mi = 10000
		for f,v in self.freq_db:
			if f < 100: continue
			if f > 10000: break
			if mi > v: mi = v

		mi = mi + manshift
		result = []
		for f,v in self.freq_db:
			v = mi - v
			result.append((f,v))

		return Spectrum(result)

	def smooth(self):
		result = []
		freq_db = self.freq_db

		size = len(self.freq_db)
		for i in range(0,size):
			fre,val = freq_db[i]
			if fre < 500:
				result.append((fre,val))
				continue

			if fre < 1000: delta = 1
			elif fre < 5000: delta = 4
			elif fre < 10000: delta = 6
			elif fre < 15000: delta = 8
			else: delta = 12

			low = i-delta
			if low < 0: low = 0
			hi = i + delta
			if hi >= size: hi = size - 1

			su = 0
			for n in range(low,hi):
				_, v = freq_db[n]
				su = su + v
			val = su / (hi-low)

			result.append((fre,val))

		return Spectrum(result)

	def get_freqs(self):
		return [f for f,v in self.freq_db]

	def get_coefs(self):
		return [v for f,v in self.freq_db]

	def set_coefs(self, coefs):
		result = []
		it = iter(coefs)
		for f,_ in self.freq_db:
			nv = next(it)
			result.append((f,nv))

		self.freq_db = result

	def set_filter_range(self, maxf):
		f0, c = self.freq_db[0]
		f1, c = self.freq_db[-1]
		if f0 == 0 and f1 == maxf: return self

		result = []
		f, c = self.freq_db[0]
		if f != 0: result.append((0,c))

		for f,c in self.freq_db:
			if f > maxf: break
			result.append((f,c))

		f, c = self.freq_db[-1]
		if f != maxf: result.append((maxf,c))

		return Spectrum(result)

	def cut_positives(self):
		result = []
		for f,v in self.freq_db:
			if v > 0: v = 0
			result.append((f,v))

		return Spectrum(result)

	def update_minmax(self):
		minval = None
		maxval = None
		try:
			it = iter(self.freq_db)

			f,v = next(it)
			maxval = v

			while f < 200:
				f,v = next(it)
				if v > maxval: maxval = v

			minval = v
			while f < 8000:
				f,v = next(it)
				if v > maxval: maxval = v
				if v < minval: minval = v

			while True:
				f,v = next(it)
				if v > maxval: maxval = v

		except StopIteration: pass
		except Exception as e: handle(e)

		self.maxval = maxval
		self.minval = minval

		return self
