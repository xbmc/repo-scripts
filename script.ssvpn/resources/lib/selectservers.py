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
import kodisettings
import kodiutils
import os
import apputils
import dashboard
import loading

settings = kodisettings.KodiSettings()

addonpath = settings.get_path()
sudo = (settings['sudo'] == 'true')
sudopassword = settings['sudopassword']

class selectServers(xbmcgui.WindowXMLDialog):

	def __init__( self, *args, **kwargs ):
		self.serverTable = []
		self.connectedIP = ""

	def onInit(self):
		self.getControl(32001).setLabel('Select Servers')
		self.showServList()

	def showServList(self):
		self.connectedIP = apputils.get_connected_ip()

		if dashboard.serverList == None:
			pass

		for server in dashboard.serverList:
			if server['status'] == "available":
				item = xbmcgui.ListItem(server['server_id'])
				flagPath = os.path.join(addonpath, "resources", "images", "flags", server['tags']['countryC'] + "_48.png")
				item.setArt({'thumb': flagPath})
				item.setProperty('serverid', server['server_id'])
				item.setProperty('country', server['tags']['countryN'])
				item.setProperty('city', server['tags']['city'])
				item.setProperty('ipaddr', server['ipaddr'])
				item.setProperty('number', self.getServerNumber(server['hostname']))

				statusPath = ""
				if self.connectedIP == server['ipaddr']:
					statusPath = os.path.join(addonpath, "resources", "images", "switch_on.png")
					item.setProperty('status', '1')
				else:
					statusPath = os.path.join(addonpath, "resources", "images", "switch_off.png")
					item.setProperty('status', '0')
				item.setProperty('statusimg', statusPath)

				self.serverTable.append(item)

		self.getControl(32003).addItems(self.serverTable)
		self.setFocusId(32003)

		return

	def getServerNumber(self, hostname):
		hostItems = hostname.split(".")
		number = hostItems[0][3:]
		return "#" + number

	def onClick(self, controlId):
		if controlId == 32003:
			dashboard.serverID = self.getControl(controlId).getSelectedItem().getProperty("serverid")
			self.close()
			if self.connectedIP == "":
				dashboard.show_dashboard()
			else:
				if self.connectedIP == self.getControl(controlId).getSelectedItem().getProperty("ipaddr"):
					dashboard.show_dashboard()
				else:
					loading.show_loading(connected=True, action="connecting")

def show_servers():
	main = selectServers('script-ssvpn-selectservers.xml', addonpath, 'default', '')
	main.doModal()
	del main
