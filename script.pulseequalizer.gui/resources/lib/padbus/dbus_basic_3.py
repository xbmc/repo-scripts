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
#  dbus wraper for Python 3.x
#

import os
import sys

from . import dbussy as dbus
from .dbussy import DBUS, DBusError
from . import interface as IF
from .pulseerror import PulseDBusError
from helper import log

class PulseDBus:
	def __init__( self, *args, **kwargs ):
		destination = 'org.PulseAudio1'
		object_path = '/org/pulseaudio/server_lookup1'
		interface_name = 'org.PulseAudio.ServerLookup1'
		try:
			if 'PULSE_DBUS_SERVER' in os.environ:
				address = os.environ['PULSE_DBUS_SERVER']
				log("got dbus address from environment: %s" % address)
			else:
				conn = dbus.Connection.bus_get(DBUS.BUS_SESSION,private = False)

				request = dbus.Message.new_method_call (
					destination = dbus.valid_bus_name(destination),
					path = dbus.valid_path(object_path),
					iface = IF.INTERFACE_PROPERTIES,
					method = "Get"
				)

				request.append_objects("ss", dbus.valid_interface(interface_name),'Address')
				reply = conn.send_with_reply_and_block(request)

				address = reply.expect_return_objects("v")[0][1]
				log("got dbus address from pulseaudio: %s" % address)

			self.conn = dbus.Connection.open(address,0)
		except DBusError as e:
			fb = "/run/user/%s/pulse/dbus-socket" % os.geteuid()
			address = 'unix:path=' + fb

			if os.path.exists(fb):
				try:
					log("fallback dbus: %s" % address)
					self.conn = dbus.Connection.open(address,0)
				except DBusError as ex: self.handle_exception(ex,"python3","on connect")
			else:
				log("fallback did not work: %s" % address)
				self.handle_exception(e,"python3","on connect")

	def print_introspect(self, interface, d_path ):
		try:
			request = dbus.Message.new_method_call(
					destination = dbus.valid_bus_name(interface),
					path = d_path,
					iface = IF.INTERFACE_INTROSPECTABLE,
					method = "Introspect"
				)

			reply = self.conn.send_with_reply_and_block(request)
			sys.stdout.write(reply.expect_return_objects("s")[0])
		except DBusError as e: self.handle_exception(e,"python3","on dbus function call")

	def get_property(self, interface, d_path, p_name):
		try:
			request = dbus.Message.new_method_call (
				destination = dbus.valid_bus_name(interface),
				path = d_path,
				iface = IF.INTERFACE_PROPERTIES,
				method = "Get"
			)
			request.append_objects("ss", dbus.valid_interface(interface),p_name)
			reply = self.conn.send_with_reply_and_block(request)

			return reply.expect_return_objects("v")[0][1]
		except DBusError as e: self.handle_exception(e,"python3","on dbus function call")

	def set_property(self, interface, d_path, p_name, *p_val):
		try:
			request = dbus.Message.new_method_call (
				destination = dbus.valid_bus_name(interface),
				path = d_path,
				iface = IF.INTERFACE_PROPERTIES,
				method = "Set"
			)
			request.append_objects("ssv", dbus.valid_interface(interface),p_name, p_val)
			self.conn.send_with_reply_and_block(request)
		except DBusError as e: self.handle_exception(e,"python3","on dbus function call")

	def get_all_property(self, interface, d_path):
		try:
			request = dbus.Message.new_method_call (
				destination = dbus.valid_bus_name(interface),
				path = d_path,
				iface = IF.INTERFACE_PROPERTIES,
				method = "GetAll"
			)
			request.append_objects("s", dbus.valid_interface(interface))
			reply = self.conn.send_with_reply_and_block(request)

			return reply.expect_return_objects("a{sv}")[1]
		except DBusError as e:  self.handle_exception(e,"python3","on dbus function call")

	def call_func(self, interface, d_path, func, *args):
		try:
			request = dbus.Message.new_method_call (
				destination = dbus.valid_bus_name(interface),
				path = d_path,
				iface = dbus.valid_bus_name(interface),
				method = func
			)
			if len(args) > 0:
				request.append_objects(*args)
			reply = self.conn.send_with_reply_and_block(request).all_objects

			if   len(reply) == 0 :return None
			elif len(reply) == 1 :return reply[0]
			else:	return reply
		except DBusError as e: self.handle_exception(e,"python3","on dbus function call")

	@staticmethod
	def handle_exception(e,python,func):
		raise(PulseDBusError(e.name,e.message,python,func))

