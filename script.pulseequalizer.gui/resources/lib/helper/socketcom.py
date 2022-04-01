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
import os
import sys

from .fjson import json

from threading import Thread

from basic import log
from basic import handle
from basic import infhandle
from basic import opthandle

class SocketCom():
	exit_str = "slgeife3"
	life_str = "gklwers6"
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
		return result.decode("utf-8"), conn

	def listen_loop(self, callback):
		log("socket: start socket loop")
		sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
		sock.settimeout(None)

		try: os.remove(self.sock_name)
		except OSError:	pass

		sock.bind(self.sock_name)

		while True:
			try:
				result, conn = self.get_from_socket(sock)

				#log("socket: {} receive '{}'".format(self.sock_name, result))

				if result == self.exit_str:
					conn.close()
					break
				if result == self.life_str:
					self._send(conn,self.life_str)
					continue

				callback(conn, result)

			except Exception as e: infhandle(e)
		log("socket: stop socket loop")

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
			self._send(s, msg)
			data = s.recv(8192)
			self._close(s)
			if data == b'': return None
			return data.decode("utf-8")
		except Exception as e:
			opthandle(e)
			return None

	def send(self, func, target, args=[]):
		self.send_to_server(json.dumps([func,target,args]))

	def call_func(self, func, target, args=[]):
		send_string = json.dumps([func,target,args])
		log("socket: call_func send '{}'".format(send_string))
		result = self.send_to_server(send_string)
		log("socket: call_func receive '{}'".format(result))

		if result is not None:
			try: return json.loads(result)
			except Exception as e: infhandle(e)
		return None

	def dispatch(self, conn, msg):
		try:
			try:
				func,target,args = json.loads(msg)
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

	@classmethod
	def respond(cls, conn, result):
		if conn  is None:
			#log("socket: no connection, nothing to respond")
			return

		ret = json.dumps(result)

		if result is not None:
			log("socket: respond {}".format(ret))

		try:
			cls._send(conn, ret)
			cls._close(conn)
		except Exception as e: opthandle(e)

	@staticmethod
	def _send(sock,text):
		if sys.version_info[0] > 2:
			try:
				sock.send(bytes(text,"utf-8"))
			except BrokenPipeError: pass
		else:
			try:
				sock.send(text)
			except socket.error: pass

	@staticmethod
	def _close(sock):
		if sys.version_info[0] > 2:
			try:
				sock.close()
			except BrokenPipeError: pass
		else:
			try:
				sock.close()
			except socket.error: pass
