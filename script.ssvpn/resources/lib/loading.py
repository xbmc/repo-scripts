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
import os
import api
import json
import apputils
import dashboard
import time
import socket
import openvpn
import kodiutils
import subprocess

settings = kodisettings.KodiSettings()

addonpath = settings.get_path()
addonname = settings.get_name()
openvpnbin = settings['openvpn']
userdata = settings.get_datapath()
ip = settings['ip']
port = int(settings['port'])
args = settings['args']
sudo = (settings['sudo'] == 'true')
sudopassword = settings['sudopassword']
vpnmode = settings['vpn_mode']
_timeout = 15

conn_name = "kodi"

(disconnected, failed, connecting, disconnecting, connected) = range(5)
state = disconnected

class loading(xbmcgui.WindowXMLDialog):

	def __init__( self, *args, **kwargs ):
		self.connected = kwargs["connected"]
		self.action = kwargs["action"]
		self.serverip = ""
		self.hostname = ""

	def onInit(self):
		backimg = ""
		if self.connected:
			backimg = os.path.join(addonpath,"resources","images","connected.png")
		else:
			backimg = os.path.join(addonpath,"resources","images","disconnected.png")
		self.getControl(33003).setImage(backimg)
		self.getControl(33000).setImage(os.path.join(addonpath,"resources","images","ellipse-1.png"))
		self.getControl(33001).setImage(os.path.join(addonpath,"resources","images","ellipse-2.png"))

		self.processing(self.action)

	def onClick(self, controlId):
		pass

	def input_credential(self):
		email = xbmcgui.Dialog().input("Email", "")
		settings.__setitem__("email", email)
		password = xbmcgui.Dialog().input("Password", "")
		settings.__setitem__("password", password)

	def processing(self, action):
		if action == "preinstall":
			self.getControl(33002).setLabel(settings.get_string(3105))
			cmdline = "chmod +x " + settings.get_path('bin/preinstall.sh')
			apputils.run_cmd_with_sudo(cmdline, sudopassword)

			cmdline = settings.get_path('bin/preinstall.sh') + " " + settings.get_path('bin')

			apputils.run_cmd_with_sudo(cmdline, sudopassword)

			self.close()
			show_loading(connected=True, action="login")
		elif action == "login":
			auto_login = (settings['auto_login'] == 'true')
			email = settings['email']
			password = settings['password']
			# Login process
			if auto_login:
				if (email == "" or password == ""):
					self.input_credential()
					email = settings['email']
					password = settings['password']
			else:
				self.input_credential()
				email = settings['email']
				password = settings['password']

			self.getControl(33002).setLabel(settings.get_string(3100))
			jsonObj = api.login_process_with_email(email, password)

			self.close()
			if jsonObj == None or jsonObj['error'] == True or jsonObj['authentication'] != True:
				apputils.display_notification(settings.get_string(3003))
			else:
				show_loading(connected=True, action="get_servlist")

		elif action == "get_servlist":
			self.getControl(33002).setLabel(settings.get_string(3101))
			serverList = api.get_servlist()

			if serverList == None:
				self.close()
				apputils.display_notification(settings.get_string(3015))
			else:
				dashboard.serverList = serverList

				connectedIP = apputils.get_connected_ip()
				if connectedIP == "":
					recommended = self.getRecommended(serverList)
					dashboard.serverID = recommended['server_id']
				else:
					for server in serverList:
						if server['ipaddr'] == connectedIP:
							dashboard.serverID = server['server_id']

				self.close()
				dashboard.show_dashboard()

		elif action == "connecting":
			self.getControl(33002).setLabel(settings.get_string(3102))

			for server in dashboard.serverList:
				if server['server_id'] == dashboard.serverID:
					self.serverip = server['ipaddr']
					self.hostname = server['hostname']

			if self.serverip != "":
				vpnmode = settings['vpn_mode']
				if vpnmode == 0:
					self.connect_openvpn()
				elif vpnmode == 1:
					self.connect_ipsec()
			else:
				self.close()
				apputils.display_notification(settings.get_string(3007))

		elif action == "disconnecting":
			self.getControl(33002).setLabel(settings.get_string(3103))

			vpnmode = settings['vpn_mode']
			if vpnmode == 0:
				self.disconnect_openvpn(True)
			elif vpnmode == 1:
				self.disconnect_ipsec(True)
		else:
			self.close()

	def connect_openvpn(self):
		apputils.log_debug("Connecting openvpn...")
		global state

		email = settings['email']
		password = settings['password']
		jsonObj = api.get_vpn_credential(email, password)
		if (jsonObj['error'] != False or jsonObj['vpn_credentials'] != True):
			ok(addonname, settings.get_string(3008))
			sys.exit()

		apputils.create_auth_file(jsonObj)
		apputils.create_ovpn_config(self.serverip, sudopassword)

		openvpnproc = openvpn.OpenVPN(openvpnbin, settings.get_datapath(
			'config.ovpn'), ip=ip, port=port, args=args, sudo=sudo, sudopwd=sudopassword, debug=(settings['debug'] == 'true'))
		try:
			openvpnproc.connect()
			state = connected
			openvpnproc.interface.disconnect()

			# diable ipv6
			apputils.setup_ipv6_interfaces(True, sudopassword)

			apputils.create_status_file(self.serverip)

			# create local network file
			local_networks = settings.get_datapath('localnetworks')
			cmdline = "ip ro | grep 'scope link src' | awk '{split($0,a,\" \"); print a[1]}' > " + local_networks
			apputils.run_cmd_with_sudo(cmdline, sudopassword);
			apputils.apply_killswitch(self.serverip, sudopassword)
			self.close()

			# notify about connected VPN
			apputils.display_notification(settings.get_string(4001))
			dashboard.show_dashboard()

		except openvpn.OpenVPNError as exception:
			if exception.errno == 1:
				state = connected
				if kodiutils.yesno(settings.get_string(3002), settings.get_string(3009), settings.get_string(3010)):
					apputils.log_debug('User has decided to restart OpenVPN')

					self.disconnect_openvpn(False)
					time.sleep(1)
					state = disconnected

					self.connect_openvpn()
				else:
					apputils.log_debug('User has decided not to restart OpenVPN')
					self.close()
					connectedIP = apputils.get_connected_ip()
					for server in dashboard.serverList:
						if server['ipaddr'] == connectedIP:
							dashboard.serverID = server['server_id']
					dashboard.show_dashboard()

			else:
				kodiutils.ok(settings.get_string(3002), settings.get_string(3011), exception.string)
				state = failed
				self.close()

	def disconnect_openvpn(self, notification):
		apputils.log_debug("Disconnecting openvpn...");
		global state
		state = disconnecting

		try:
			response = openvpn.is_running(ip, port)
			if response[0]:
				openvpn.disconnect(ip, port)

		except openvpn.OpenVPNError as exception:
			# kill openvpn process
			apputils.run_cmd_with_sudo("killall openvpn", sudopassword)

		# enable ipv6 Interface
		apputils.setup_ipv6_interfaces(False, sudopassword)

		# clean killswitch
		ipaddr = apputils.get_connected_ip()
		apputils.clean_killswitch(ipaddr, sudopassword)

		# remove openvpn config and authfile
		os.remove(settings.get_datapath('config.ovpn'))
		os.remove(settings.get_datapath('authfile'))
		os.remove(settings.get_datapath('connected'))
		os.remove(settings.get_datapath('localnetworks'))

		state = disconnected
		apputils.log_debug('Disconnect OpenVPN successful')

		if notification:
			self.close()
			apputils.display_notification(settings.get_string(4002))
			dashboard.show_dashboard()

	def connect_ipsec(self):
		apputils.log_debug("Connecting IKEv2...")
		# get username/password for vpn connect
		email = settings['email']
		password = settings['password']
		jsonObj = api.get_vpn_credential(email, password)
		if (jsonObj['error'] != False or jsonObj['vpn_credentials'] != True):
			ok(addonname, settings.get_string(3008))
			sys.exit()

		# create ipsec.conf
		apputils.create_ipsec_conf(jsonObj['login'], self.hostname)

		# create ipsec.secrets
		apputils.create_ipsec_secrets(jsonObj['login'], jsonObj['password'])

		# config ipsec daemon
		apputils.config_ipsec(sudopassword)

		apputils.reload_ipsec(sudopassword)
		time.sleep(3)

		while True:
			available_connections = apputils.get_connections()
			status = 0
			for key in available_connections:
				if key == conn_name:
					apputils.log_debug("service reloaded")
					status = 1
			if status == 1:
				break;

		apputils.connection_up(sudopassword)

		interval = 0
		while True:
			conn_state = apputils.check_vpn_connection()
			if conn_state == "ESTABLISHED":
				apputils.display_notification("VPN Connected")
				apputils.setup_ipv6_interfaces(True, sudopassword)
				apputils.create_status_file(self.serverip)
				# create local network file
				local_networks = settings.get_datapath('localnetworks')
				cmdline = "ip ro | grep 'scope link src' | awk '{split($0,a,\" \"); print a[1]}' > " + local_networks
				apputils.run_cmd_with_sudo(cmdline, sudopassword);
				apputils.apply_killswitch(self.serverip, sudopassword)
				self.close()
				break;

			if interval > _timeout:
				apputils.display_notification("VPN connect failed")
				self.close()
				break;

			time.sleep(1)
			interval = interval + 1

		dashboard.show_dashboard()

	def disconnect_ipsec(self, notification):
		apputils.log_debug("Disconnecting IKEv2...")
		apputils.connection_down(sudopassword)

		while True:
			conn_state = apputils.check_vpn_connection()
			if conn_state == "":
				if notification:
					apputils.display_notification("VPN Disconnected")

				apputils.setup_ipv6_interfaces(False, sudopassword)
				# clean killswitch
				ipaddr = apputils.get_connected_ip()
				apputils.clean_killswitch(ipaddr, sudopassword)
				# remove openvpn config and authfile
				os.remove(settings.get_datapath('ipsec.conf'))
				os.remove(settings.get_datapath('ipsec.secrets'))
				os.remove(settings.get_datapath('connected'))
				os.remove(settings.get_datapath('localnetworks'))

				self.close()
				dashboard.show_dashboard()
				break;

	def extract_cpu(self, json):
		try:
			return int(json['tags']['cpu'])
		except KeyError:
			return 0

	def getConnectTime(self, ipaddr):
		starttime = time.time()

		try:
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			s.connect((ipaddr, 443))
		except socket.error as err:
			print "socket creation failed with error %s" %(err)
			return 0

		endtime = time.time()
		s.close()

		return endtime - starttime

	def getRecommended(self, serverList):
		serverList.sort(key=self.extract_cpu)

		serverList_by_cpu = []

		for server in serverList:
			count = 0;
			for server1 in serverList_by_cpu:
				if server1['tags']['countryC'] == server['tags']['countryC']:
					count += 1
			if count < 3:
				serverList_by_cpu.append(server)

		recommended = serverList_by_cpu[0]

		for server in serverList_by_cpu:
			if self.getConnectTime(server['ipaddr']) != 0 and self.getConnectTime(recommended['ipaddr']) > self.getConnectTime(server['ipaddr']):
				recommended = server

		return recommended

def show_loading(connected=None, action=None):
	main = loading('script-ssvpn-loading.xml',
		addonpath, 'default', '',
		connected=connected,
		action=action)
	main.doModal()
	del main
