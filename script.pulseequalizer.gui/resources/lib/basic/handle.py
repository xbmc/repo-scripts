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

import sys

from .log import logerror
from .log import log

def filename(fn):
	return fn[fn.rfind("/")+1:]

def format_trace(e, pre):
	n = 2

	_, _, tb = sys.exc_info()

	trace = ""
	while tb  is not None:
		f = tb.tb_frame
		trace = "{}@{}({}), ".format(f.f_code.co_name,filename(f.f_code.co_filename),tb.tb_lineno) + trace
		tb = tb.tb_next

	try:
		while True:
			obj = sys._getframe(n)

			fn = filename(obj.f_code.co_filename)
			if fn == "threading.py" : break
			trace = trace + "{}@{}({}), ".format(obj.f_code.co_name, fn ,obj.f_lineno)

			n = n + 1
	except ValueError: pass
	trace = trace[:-2] if len(trace)>2 else ""
	return "{}: {}: {}:({})".format(pre, type(e).__name__, trace , ",".join([str(x) for x in e.args]))

def handle(e):
	logerror(format_trace(e,"exc_err"))

def infhandle(e):
	log(format_trace(e,"exc_nce"))

def opthandle(e):
	log(format_trace(e,"exc info"))
