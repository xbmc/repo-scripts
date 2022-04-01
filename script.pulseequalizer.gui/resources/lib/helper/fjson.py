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
#	json modul is heavy and loads quite slow on slow devices.
#	this is a basic replacement for faster startup
#

#import re

import sys

class StructProblme(Exception):
	slots__ = ("message","detail")
	def __init__(self,  message, detail) :
		self.args = ("%s json: %s" % (message, detail),)
		self.message = message
		self.detail	= detail

class json():
	@classmethod
	def dumps(cls,arg):
		if arg  is None: return 'None'
		return str(arg)

	@staticmethod
	def _split(text):
		l = []
		s = ''
		it = iter(text)
		try:
			if sys.version_info[0] > 2:
				while True:
					c = next(it)
					if c in ',"\'{}[]():':
						l.append(s)
						l.append(c)
						s=''
					else:
						s=s+c
			else:
				while True:
					c = next(it)
					if c in ',"\'{}[]():':
						l.append(s.encode('utf-8'))
						l.append(c.encode('utf-8'))
						s=''
					else:
						s=s+c

		except StopIteration: pass
		if s: l.append(s)

		return l

	@classmethod
	def split(cls,text):
		l = cls._split(text)
		it = iter(l)
		result = []
		try:
			while True:
				c = next(it).strip()
				if c == '': continue
				if c == ',': continue
				if c in '{}:[]()': result.append(c)
				elif c in '"\'':
					s = ""
					while True:
						ci = next(it)
						if ci == c:
							try:
								if s[-1]=='\\':
									s = s[:-1]+ c
								else: break
							except: break
						else:
							s = s + ci
					result.append(s)
				else:
					try: result.append([None,False,True,None][['none','false','true','null'].index(c.lower())])
					except ValueError: pass
					try:
						if c[-1] == 'L':
							result.append(int(c[:-1]))
						else:
							result.append(int(c))
						continue
					except ValueError: pass
					try:
						result.append(float(c))
						continue
					except ValueError: pass

		except StopIteration: pass
		return result

	@classmethod
	def parse_dict(cls,it):
		result = {}
		try:
			while True:
				key =  next(it)
				if isinstance(key,str):
					if key == '}':
						return result
					if key in ')]':
						raise StopIteration

				c = next(it)
				if c != ':': raise StopIteration

				val = next(it)

				if not isinstance(val,str):
					result[key] = val
					continue

				if val == '':
					result[key] = val
					continue
				if val in '([':
					val = cls.parse_list(it)
				elif val == '{':
					val = cls.parse_dict(it)
				result[key] = val

		except StopIteration:
			raise StructProblme("structure problem",str(result))

	@classmethod
	def parse_list(cls,it):
		result = []
		try:
			while True:
				c = next(it)
				if not isinstance(c,str):
					result.append(c)
					continue
				if c == '':
					result.append(c)
					continue
				if c == '}':
					raise StopIteration
				if c in ')]':
					if c == ')':
						return tuple(result)
					else:
						return result
				elif c in '([':
					result.append(cls.parse_list(it))
				elif c == '{':
					result.append(cls.parse_dict(it))
				else:
					result.append(c)
		except StopIteration:
			raise StructProblme("structure problem", str(result))

	@classmethod
	def loads(cls,text):
		if not text or text=='None': return None

		ilist = cls.split(text)
		if not ilist: return text
		if len(ilist) == 1: return ilist[0]

		it = iter(ilist)

		c = next(it)
		if c == '{': return cls.parse_dict(it)
		elif c in '[(': return cls.parse_list(it)
		else: return ilist[0]
