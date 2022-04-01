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

try: import xbmc
except Exception:
	# this is the python service, started outside from kodi
	# so to log into kodi-log, we need to send the log info to kodi-addon-service.py
	import sys
	import socket
	from .path import path_pipe

	# as we do not have access to xbmc import, we need to fake it.
	class xbmc():
		LOGDEBUG = 0
		LOGERROR = 3
		LOGFATAL = 4
		LOGINFO = 1
		LOGNONE = 5
		LOGWARNING = 2

		sock_name = path_pipe + "kodi.0"

		@staticmethod
		def log(text, level):
			msg = str(["write","log",["s"+text[1:],level]])
			if sys.version_info[0] > 2:
				msg = bytes(msg,"utf-8")
			try:
				s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
				s.settimeout(1.0)
				s.connect(xbmc.sock_name)
				s.send(msg)
				s.close()
			except OSError: pass
			except Exception as e:
				print("{} {}".format(type(e).__name__, ",".join([str(x) for x in e.args])))

'''
PRE="s_"

class xbmc():
	LOGDEBUG = "DEBUG"
	LOGERROR = "ERROR"
	LOGFATAL = "FATAL"
	LOGINFO = "INFO"
	LOGNONE = "NONE"
	LOGWARNING = "WARNING"

	try:
		import xbmc
		global PRE
		PRE="c_"
	except Exception:
		pass

	@staticmethod
	def log(text, level):
		if "padb: re:" in text: return
		text = "{}: {}{}".format(level,PRE,text)
		with open("/var/tmp/kodi.log","a") as f: f.write(text + "\n")
'''

def log(text):
	xbmc.log("c_eq: " + text, xbmc.LOGDEBUG)

def loginfo(text):
	xbmc.log("c_eq: " + text, xbmc.LOGINFO)

def logerror(text):
	xbmc.log("c_eq: " + text, xbmc.LOGERROR)
