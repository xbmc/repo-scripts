#/*
# *
# * OpenVPN for Kodi.
# *
# * Copyright (C) 2018 Venus
# *
# * This program is free software: you can redistribute it and/or modify
# * it under the terms of the GNU General Public License as published by
# * the Free Software Foundation, either version 3 of the License, or
# * (at your option) any later version.
# *
# * This program is distributed in the hope that it will be useful,
# * but WITHOUT ANY WARRANTY; without even the implied warranty of
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# * GNU General Public License for more details.
# *
# * You should have received a copy of the GNU General Public License
# * along with this program.  If not, see <http://www.gnu.org/licenses/>.
# *
# */

import xbmcgui
import xbmc
import os
import json
import kodisettings
import selectservers
import loading
import openvpn
import apputils

settings = kodisettings.KodiSettings()

addonpath = settings.get_path()
ip = settings['ip']
port = int(settings['port'])

def serverInfoInit():
	global serverList
	serverList = []
	global serverID
	serverID = ""

class dashboard(xbmcgui.WindowXMLDialog):

	def __init__( self, *args, **kwargs ):
		self.connected = False

	def onInit(self):
		backimg = lockimg = lockbackimg = statusimg = ""
		country = countryname = ""
		connectedIP = apputils.get_connected_ip()
		if connectedIP != "":
			self.connected = True

		if self.connected:
			backimg = os.path.join(addonpath,"resources","images","connected.png")
			lockbackimg = os.path.join(addonpath,"resources","images","circle-green.png")
			lockimg = os.path.join(addonpath,"resources","images","lock.png")
			statusimg = os.path.join(addonpath,"resources","images","switch_on.png")
		else:
			backimg = os.path.join(addonpath,"resources","images","disconnected.png")
			lockbackimg = os.path.join(addonpath,"resources","images","circle-red.png")
			lockimg = os.path.join(addonpath,"resources","images","unlock.png")
			statusimg = os.path.join(addonpath,"resources","images","switch_off.png")

		for server in serverList:
			if server['server_id'] == serverID:
				country = server['tags']['countryC']
				countryname = server['tags']['countryN']

		self.getControl(31001).setImage(backimg)
		self.getControl(31002).setImage(os.path.join(addonpath,"resources","images","circle-white-bg.png"))
		flagimg = os.path.join(addonpath,"resources","images", "flags", country + "_96.png")
		self.getControl(31003).setImage(flagimg)
		self.getControl(31004).setImage(os.path.join(addonpath,"resources","images","circle-white-bg.png"))
			
		self.getControl(31005).setImage(lockbackimg)
		self.getControl(31006).setImage(lockimg)

		self.getControl(31007).setLabel(countryname)
		self.getControl(31008).setImage(statusimg)

	def onClick(self, controlID):
		if controlID == 31009:
			self.close()
			if self.connected:
				loading.show_loading(connected=True, action="disconnecting")
			else:
				loading.show_loading(connected=False, action="connecting")
		elif controlID == 31010:
			self.close()
			selectservers.show_servers()
		else:
			pass


def show_dashboard():
	main = dashboard('script-ssvpn-dashboard.xml',
		addonpath, 'default', '')
	main.doModal()
	del main
