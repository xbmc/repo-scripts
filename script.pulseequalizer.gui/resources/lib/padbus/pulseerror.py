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
class PulseDBusError(Exception) :
	slots__ = ("name", "message", "python","detail")

	def __init__(self, name, message, python ,detail) :
		self.args = ("%s\n%s\ndetail: %s %s" % (name, message, python, detail),)
		self.name = name
		self.message = message
		self.python	= python
		self.detail	= detail

	def get_advice(self):
		if(self.name == 'org.freedesktop.DBus.Error.UnknownMethod'):
			if(self.detail == 'on connect'):
				return "Cannot find pulseaudio dbus server.\nYou can try to set the environment variable PULSE_DBUS_SERVER\n to the pulseaudio dbus service PULSE_DBUS_SERVER='unix:path=PATH_TO SERVICE'."
			else:
				return "Cannot connect to pulseaudio-equalizer.\nMake sure pulseaudio-equalizer is installed and modules are loded by system.\nTry 'sudo apt install pulseaudio-equalizer' \nand/or 'pactl load-module module-equalizer-sink'\nor configure '/etc/pulse/default.pa'"

		if((self.name == 'org.freedesktop.DBus.Error.FileNotFound') and (self.detail == 'on connect')):
			return "Cannot connect to pulseaudio dbus server.\nPlease load the module 'module-dbus-protocol' via \n'pactl load-module module-dbus-protocol'\nor configure '/etc/pulse/default.pa'"

		if((self.name == 'org.freedesktop.DBus.Error.ServiceUnknown') and (self.detail == 'on connect')):
			return "Cannot find pulseaudio dbus server.\nYou can try to set the environment variable PULSE_DBUS_SERVER to the pulseaudio dbus service\n PULSE_DBUS_SERVER='unix:path=PATH_TO SERVICE'."

