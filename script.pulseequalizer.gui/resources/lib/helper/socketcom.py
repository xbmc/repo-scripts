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
#	implements the communication between user interface on Kodi and the unerlying service
#	is a file socket
#

import socket
import pickle
import os
import sys

from threading import Thread
from .log import log
from .handle import handle, infhandle, opthandle

class SocketCom():
	exit_str = b"slgeife3"
	life_str = b"gklwers6"
	rec_class = None

	def __init__(self, name, gid = 0):
		self.path = "/run/user/%d/pa/" % os.geteuid()
		try: os.makedirs(self.path)
		except OSError: pass
		#except Exception as e: opthandle(e)

		self.sock_name = self.path + "%s.%d" % (name , gid)

	def is_server_running(self):
		if not os.path.exists(self.sock_name): return False

		if self.send_to_server(self.life_str) == self.life_str:
			return True
		return None

	@staticmethod
	def get_from_socket(sock):
		sock.listen(1)
		conn, _ = sock.accept()

		result = conn.recv(8192)
		return result, conn

	def listen_loop(self, callback):
		log("start socket loop")
		sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
		sock.settimeout(None)

		try: os.remove(self.sock_name)
		except OSError:	pass

		sock.bind(self.sock_name)

		while True:
			try:
				result, conn = self.get_from_socket(sock)

				if result == self.exit_str:
					conn.close()
					break
				if result == self.life_str:
					conn.send(self.life_str)
					continue

				callback(conn, result)

			except Exception as e: infhandle(e)
		log("stop socket loop")

		try: os.remove(self.sock_name)
		except OSError:	pass

	def start_server(self, callback):
		Thread(target = self.listen_loop, args = (callback,)).start()

	def start_func_server(self, rec_class, block = False):
		self.rec_class = rec_class
		th = Thread(target = self.listen_loop, args = (self.dispatch,))
		th.start()
		if block: th.join()

	def stop_server(self):
		self.send_to_server(self.exit_str)

	def send_to_server(self, msg):
		try:
			s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
			s.settimeout(1.0)
			s.connect(self.sock_name)
			s.send(msg)
			data = s.recv(2048)
			s.close()
			if data == b'': return None
			return data
		except Exception: return None

	def send(self, func, target, args=[]):
		self.send_to_server(pickle.dumps([func,target,args], protocol=2))

	def call_func(self, func, target, args=[]):
		result = self.send_to_server(pickle.dumps([func,target,args], protocol=2))
		if result is not None:
			try:	return pickle.loads(result)
			except Exception as e: infhandle(e)
		return None

	def dispatch(self, conn, msg):
		try:
			try:
				func,target,args = pickle.loads(msg)
				cmd = "on_%s_%s" % (target,func)
			except Exception:
				#log(repr(msg))
				try:conn.close()
				except Exception as e: opthandle(e)
				return

			try: method = getattr(self.rec_class,cmd)
			except Exception: method = None

			result = method(*args) if method else None

			self.respond(conn,result)

			try:conn.close()
			except Exception as e: opthandle(e)

		except Exception as e: handle(e)

	@staticmethod
	def respond(conn, result):
		if conn is not None:
			if sys.version_info[0] > 2:
				try:
					conn.send(pickle.dumps(result, protocol=2))
				except BrokenPipeError: pass   #requestor did not wait for response => broken pipe
				except Exception as e: opthandle(e)
			else:
				try:
					conn.send(pickle.dumps(result, protocol=2))
				except IOError: pass   #requestor did not wait for response, broken pipe
				except Exception as e: opthandle(e)

