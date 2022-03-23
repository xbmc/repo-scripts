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
import sys
import traceback

from .log import logerror, log

if sys.version_info[0] > 2:
	
	def format_tracepack(e, result):
		traceback = e.__traceback__
		while traceback:
			p,fn = os.path.split(traceback.tb_frame.f_code.co_filename)
			result = result + "%s (%s), " % (fn,traceback.tb_lineno)
			traceback = traceback.tb_next

		result = result + "{}: {}".format(type(e).__name__, e.args)
		return result
	
	def handle(e):
		logerror(format_tracepack(e,"in: "))

	def infhandle(e):
		log(format_tracepack(e,"nce: in: "))

	def opthandle(e):
		log(format_tracepack(e,"opt: in: "))

else:
	
	def handle(e):
		lines = traceback.format_exc().splitlines()
		for l in lines:
			logerror(l)
		logerror("{}: {}".format(type(e).__name__, e.args))

	def infhandle(e):
		lines = traceback.format_exc().splitlines()
		for l in lines:log("nce: " + l)
		log("nce: {}: {}".format(type(e).__name__, e.args))

	def opthandle(e):
		lines = traceback.format_exc().splitlines()
		for l in lines:log("opt: " + l)
		log("opt: {}: {}".format(type(e).__name__, e.args))

