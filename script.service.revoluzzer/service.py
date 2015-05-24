# -*- coding: utf-8 -*- 
'''
	REvoluzzer for KODI
	Copyright (C) 2015 icordforum.com

	This program is free software: you can redistribute it and/or modify
	it under the terms of the GNU General Public License as published by
	the Free Software Foundation, either version 3 of the License, or
	(at your option) any later version.

	This program is distributed in the hope that it will be useful,
	but WITHOUT ANY WARRANTY; without even the implied warranty of
	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
	GNU General Public License for more details.

	You should have received a copy of the GNU General Public License
	along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import socket
import time
import telnetlib
import xbmc, xbmcaddon, xbmcgui
 
# Constants
DIR_BASEDIR = '/mnt/hd1/revoluzzer'
URL_DOWNLOAD = 'http://icordforum.com/addonDownload/'

TELNETPORT_EVO = 60001		# Port for built in Telnet
TELNETIND_EVO = 'root:> '	# Wait indicator for built in Telnet

TELNETPORT_OUR = 2323 	# Port for own Telnet
TELNETIND_OUR = '# '	# Wait indicator for own Telnet

TELNET_TO_DEF 	=    10	# Standard Timeout for Telnet
TELNET_TO_DL 	= 10000	# Timeout for Downloads

STATE_OFF 		=   0	# Device unreachable
STATE_ON 		=  10	# Device reachable at built in telnet port 
STATE_TELNET 	=  20	# Device reachable at our telnet port
STATE_ACTIVE 	= 100	# Revo up and running on device
STATE_OUTDATED	= 150	# Revo running but outdated
STATE_FINE 		= 200	# Revo running with current version

WAITRESPONSE = 60	# Time retrying for Standard Telnet from first contact

# Initialize values
__addon__  = xbmcaddon.Addon()
dialog = xbmcgui.Dialog()


class Settings():
	def __init__( self, *args, **kwargs ):
		self.hosts = []
		self.interval = 30
		self.autoupdate = 1
		self.messages = True
		self.showtime = 5000
		self.start()

	def start(self):
		del self.hosts[:]
		for count in range(0,2):
			self.hosts.append([__addon__.getSetting('receiver%s' % count), STATE_OFF, 0.])
		self.interval = float(__addon__.getSetting('interval'))
		self.autoupdate = int(float(__addon__.getSetting('autoupdate')))
		self.messages = __addon__.getSetting('messages') == 'true'
		self.showtime = 1000 * int(float(__addon__.getSetting('showtime')))


# Monitorclass to react on changed settings
class MyMonitor( xbmc.Monitor ):
	def __init__( self, *args, **kwargs ):
		xbmc.Monitor.__init__( self )

	def onSettingsChanged( self ):
		mySet.start()

	
# Check for open port on host
def HostPortOpen(host, port):
	try:
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.settimeout(2)
		response = sock.connect_ex((host, port))
	except socket.timeout:
		return False
	except socket.gaierror:
		xbmc.log('Host %s could not be resolved' % host, level=xbmc.LOGDEBUG)
		return False
	except socket.error:
		xbmc.log('Could not connect to host %s' % host, level=xbmc.LOGDEBUG)
		return False
	return bool(response==0)

	
# Send Command to host via Telnet
def TelnetCommand(host, port, indicator, command, timeout):
	tn = telnetlib.Telnet(host, port, timeout)
	tn.read_until(indicator)
	tn.write(command + "\n")
	result = tn.read_until(indicator)
	tn.close()
	return result
	
def EvoTelnetCommand(host, command, timeout=TELNET_TO_DEF):
	return TelnetCommand(host, TELNETPORT_EVO, TELNETIND_EVO, command, timeout)

def OwnTelnetCommand(host, command, timeout=TELNET_TO_DEF):
	return TelnetCommand(host, TELNETPORT_OUR, TELNETIND_OUR, command, timeout)


# Starts init script - returns new state
def InitRevo(host, state):
	# Try to start REvo and oTelnet on device
	EvoTelnetCommand(host, DIR_BASEDIR + '/otelnetd -p 2323 -l /bin/sh')
	time.sleep(1)
	if HostPortOpen(host, TELNETPORT_OUR):
		state = STATE_TELNET
		response = OwnTelnetCommand(host, DIR_BASEDIR + '/init')
		if 'services' in response:
			state = STATE_ACTIVE
			if mySet.messages:
				dialog.notification('REvoluzzer', __addon__.getLocalizedString(30100) % host, xbmcgui.NOTIFICATION_INFO, mySet.showtime, False)
	return state

	
# Downloads file from iCordForum addon area
def DownloadFile(host, filename, targetdir, useown, executable):
	result = False
	# Download File
	command = 'wget ' + URL_DOWNLOAD + filename + ' -P ' + targetdir
	if useown:
		response = OwnTelnetCommand(host, command, TELNET_TO_DL)
		if '100%' in response:
			result = True
		else:
			return False
	else:
		EvoTelnetCommand(host, command, TELNET_TO_DL)
		result = True
		
	# Make it executable if selected
	if executable:
		command = 'chmod +x ' + targetdir + '/' + filename
		if useown:
			OwnTelnetCommand(host, command)		
		else:
			EvoTelnetCommand(host, command)
	return result
	

mySet = Settings()

if  __name__ == '__main__':
	xbmc_monitor   = MyMonitor()

while True:
	# Sleep/wait for abort
	if xbmc_monitor.waitForAbort(mySet.interval):
        # Abort was requested while waiting. We should exit
		break
		
	for count in range(0,2):
		host = mySet.hosts[count][0]
		state = mySet.hosts[count][1]
		firsttry = mySet.hosts[count][2]
		
		# Check for existing setting
		if host != '':
			if HostPortOpen(host, TELNETPORT_EVO):
			
				if state == STATE_OFF:
					state = STATE_ON
					state = InitRevo(host, state)
					
				elif state == STATE_ON:
					state = InitRevo(host, state)
					if state == STATE_ON:
						if firsttry == float(0):
							firsttry = time.time()
							mySet.hosts[count][2] = firsttry
						elif (time.time() - firsttry) > float(WAITRESPONSE):
							# Try to install and start oTelnet on device
							EvoTelnetCommand(host, 'mkdir -p ' + DIR_BASEDIR)							
							DownloadFile(host, 'otelnetd', DIR_BASEDIR, False, True)
							state = InitRevo(host, state)
							mySet.hosts[count][2] = float(0)
					else:
						mySet.hosts[count][2] = float(0)
						
				elif state == STATE_TELNET:
					state = InitRevo(host, state)
					if state == STATE_TELNET:
						# Try to install and start Base installation
						installed = DownloadFile(host, 'busybox', DIR_BASEDIR, True, True)
						installed = DownloadFile(host, 'opt.tar.gz', DIR_BASEDIR, True, False) and installed
						installed = DownloadFile(host, 'init', DIR_BASEDIR, True, True) and installed
						installed = DownloadFile(host, 'version', DIR_BASEDIR, True, False) and installed
						if installed:
							if mySet.messages:
								dialog.notification('REvoluzzer', __addon__.getLocalizedString(30101) % host, xbmcgui.NOTIFICATION_INFO, mySet.showtime, False)
							state = InitRevo(host, state)
							
				elif state == STATE_ACTIVE:
					# Check Version
					DownloadFile(host, 'version', '/tmp',  True, False)
					newVer = OwnTelnetCommand(host, 'cat /tmp/version')
					newVerArr = newVer.split('\n')
					curVer = OwnTelnetCommand(host, 'cat ' + DIR_BASEDIR + '/version')
					curVerArr = curVer.split('\n')
					if newVerArr[1] == curVerArr[1]:
						state = STATE_FINE
					else:
						state = STATE_OUTDATED
					OwnTelnetCommand(host, 'rm -f /tmp/version')
				
				elif state == STATE_OUTDATED:
					if mySet.autoupdate == 0:
						decision = False
					elif mySet.autoupdate == 1:
						decision = dialog.yesno('REvoluzzer', __addon__.getLocalizedString(30200) % host)
					elif mySet.autoupdate == 2:
						decision = True
						
					if decision:
						# Delete current installation and restart
						EvoTelnetCommand(host, 'killall otelnetd')
						EvoTelnetCommand(host, 'rm -rf ' + DIR_BASEDIR)
						EvoTelnetCommand(host, 'reboot')
						state = STATE_OFF
					else:
						state = STATE_FINE
					
			else:
				state = STATE_OFF
			
			mySet.hosts[count][1] = state

del xbmc_monitor