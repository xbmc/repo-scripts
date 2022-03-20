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
except: 
	# this is the python service, running independent of kodi
	# so to log into kodi-log, we need to send the log info to kodi-addon-service.py 
	import socket 
	import pickle
	from helper.path import *
	
	# as we do not have access to xbmc import, we need to fake it.
	class xbmc():
		LOGDEBUG = 0
		LOGERROR = 3
		LOGFATAL = 4
		LOGINFO = 1
		LOGNONE = 5
		LOGWARNING = 2
		
		sock_name = path_socket + "kodi.0"

	
		@staticmethod
		def log(text, level): 
			msg = pickle.dumps(["write","log",[text,level]], protocol=2)
			try:
				s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
				s.settimeout(1.0)
				s.connect(xbmc.sock_name)
				s.send(msg)
				s.close()
			except: pass

			
			

def log(text):
	xbmc.log("eq: " + text, xbmc.LOGDEBUG)
	
def loginfo(text):
	xbmc.log("eq: " + text, xbmc.LOGINFO)

def logerror(text):
	xbmc.log("eq: " + text, xbmc.LOGERROR)
	
