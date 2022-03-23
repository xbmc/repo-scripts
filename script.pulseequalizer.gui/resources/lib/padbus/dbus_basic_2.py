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
#  dbus wraper for Python 2.x
#

from helper import log, logerror
try:
	import dbus
except ImportError:
	logerror("please install python-dbus")

import interface as IF
import sys
import os
from pulseerror import PulseDBusError

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
				bus = dbus.SessionBus()
				server_lookup = bus.get_object(destination,object_path)
				address = server_lookup.Get(interface_name, 'Address', dbus_interface=IF.INTERFACE_PROPERTIES)
				log("got dbus address from pulseaudio: %s" % address)
			self.conn = dbus.connection.Connection(address)

		except dbus.exceptions.DBusException as e:
			fb = "/run/user/%s/pulse/dbus-socket" % os.geteuid()
			address = 'unix:path=' + fb

			if os.path.exists(fb):
				try:
					log("fallback dbus: %s" % address)
					self.conn = dbus.connection.Connection(address)
				except dbus.exceptions.DBusException as ex: self.handle_exception(ex,"python2","on connect")
			else:
				log("fallback did not work: %s" % address)
				self.handle_exception(e,"python2","on connect")

	def print_introspect(self, interface, d_path ):
		try:
			res =  self.conn.call_blocking(interface,d_path,IF.INTERFACE_INTROSPECTABLE,"Introspect","",())
			sys.stdout.write(res)
		except dbus.exceptions.DBusException as e:self.handle_exception(e,"python2","on dbus function call")

	def get_property(self, interface, d_path, p_name):
		try:
			return self.conn.call_blocking(interface,d_path,IF.INTERFACE_PROPERTIES,"Get","ss",(interface,p_name))
		except dbus.exceptions.DBusException as e:self.handle_exception(e,"python2","on dbus function call")

	def set_property(self, interface, d_path, p_name, *p_val):
		try:
			return self.conn.call_blocking(interface,d_path,IF.INTERFACE_PROPERTIES,"Set","ssv",(interface,p_name, p_val[1]))
		except dbus.exceptions.DBusException as e:self.handle_exception(e,"python2","on dbus function call")

	def get_all_property(self, interface, d_path):
		try:
			return self.conn.call_blocking(interface,d_path,IF.INTERFACE_PROPERTIES,"GetAll","s",(interface,))
		except dbus.exceptions.DBusException as e:self.handle_exception(e,"python2","on dbus function call")

	def call_func(self, interface, d_path, func, *args):
		try:
			if(len(args)>0):
				sig = args[0]
				args = args[1:]
			else:
				sig = ''
				args = ()

			return self.conn.call_blocking(interface,d_path,interface,func,sig,args)
		except dbus.exceptions.DBusException as e: self.handle_exception(e,"python2","on dbus function call")

	@staticmethod
	def handle_exception(e,python,func):
		raise(PulseDBusError(e._dbus_error_name,e.message,python,func))

