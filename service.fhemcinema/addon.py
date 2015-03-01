# -*- coding: utf-8 -*-
# Copyright 2014 Leo Moll
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

# -- Imports ------------------------------------------------
import datetime,socket,subprocess,os
import xbmc,xbmcplugin,xbmcgui,xbmcaddon
import httplib

# -- Constants ----------------------------------------------
ADDON_ID = 'service.fhemcinema'

# -- Settings -----------------------------------------------
settings = xbmcaddon.Addon(id=ADDON_ID)

# -- I18n ---------------------------------------------------
language = xbmcaddon.Addon(id=ADDON_ID).getLocalizedString

# -- Functions ----------------------------------------------

# -- Classes ------------------------------------------------
class FhemHandler(xbmc.Player):

	def __init__ (self):
		xbmc.Player.__init__(self)
		self.isplayingvideo = False;

	def isDayTime(self):
		try:
			nowTime=datetime.datetime.now().time()
			xbmc.log ('nowTime: {0}:{1}'.format(nowTime.hour, nowTime.minute))
			fromTime=settings.getSetting('daytimefrom')
			toTime=settings.getSetting('daytimeto')
			tmp=fromTime.split(':')
			t1=datetime.time(int(tmp[0]),int(tmp[1]))
			tmp=toTime.split(':')
			t2=datetime.time(int(tmp[0]),int(tmp[1]))
			if t1 < t2:
				return nowTime >= t1 and nowTime <= t2
			else:
				return nowTime >= t2 or nowTime <= t1
		except Exception as e:
			# this should not really happen...
			xbmc.log('Cinema: Exception in isDayTime: '+str(e),xbmc.LOGERROR)
			return False

	def getCommand(self,command):
		if settings.getSetting('daytimeenable') == "true":
			if self.isDayTime():
				return settings.getSetting(command+'dt')
		return settings.getSetting(command)

	def SendCommand(self,command):
		endpointtype=settings.getSetting('endpointtype')
		if type(endpointtype) is str and endpointtype == "FHEM":
			self.SendFHEM(self.getCommand(command))
		elif type(endpointtype) is str and endpointtype == "CCU":
			self.SendCCU(command)
		else:
			xbmc.log ('Endpoint type not supported!')


	def SendFHEM(self,command=''):
		if type(command) is str and len(command) > 0:
			xbmc.log ('Sending command to FHEM: '+command)
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			s.connect((settings.getSetting('hostname'), int(settings.getSetting('port'))))
			s.send('\n{0}\nexit\n'.format(command))
			s.close()

	def SendCCU(self,command):
		ccusystemvar=settings.getSetting('ccusystemvar')
		if type(ccusystemvar) is str and len(ccusystemvar) > 0:
			hostname = settings.getSetting('hostname')
			xbmc.log ('Sending command to CCU '+hostname+': '+command)

			if command == "onstartup":
				state = 1
			elif command == "onshutdown":
				state = 2
			elif command == "onaudioplay":
				state = 3
			elif command == "onvideoplay":
				state = 4
			elif command == "onaudiostop":
				state = 5
			elif command == "onvideostop":
				state = 6
			elif command == "onaudiopause":
				state = 7
			elif command == "onvideopause":
				state = 8
			else:
				state = 0
			connection = httplib.HTTPConnection(hostname,8181,timeout=10)
			connection.connect();
			connection.set_debuglevel(9);
			params = 'v1=dom.GetObject(\"'+ccusystemvar+'\").State(\"' + str(state) + '\");';
			connection.request("POST", "/test.exe", params);
			response = connection.getresponse()
			connection.close();
			xbmc.log ( "CCU response code: "+str(response.status))
		else:
			xbmc.log ('No CCU Object configured')

	def Run(self):
		while(not xbmc.abortRequested):
			if xbmc.Player().isPlaying():
				if xbmc.Player().isPlayingVideo():
					self.isplayingvideo = True
				else:
					self.isplayingvideo = False
			xbmc.sleep(1000)

	def StartUp(self):
		xbmc.log('Starting up Cinema...')
		self.SendCommand('onstartup')

	def ShutDown(self):
		self.SendCommand('onshutdown')
		xbmc.log('Cinema shut down')

	def onPlayBackStarted(self):
		if xbmc.Player().isPlayingAudio():
			self.SendCommand('onaudioplay')
		else:
			self.isplayingvideo = True;
			self.SendCommand('onvideoplay')

	def onPlayBackEnded(self):
		if self.isplayingvideo:
			self.SendCommand('onvideostop')
		else:
			self.SendCommand('onaudiostop')

	def onPlayBackStopped(self):
		if self.isplayingvideo:
			self.SendCommand('onvideostop')
		else:
			self.SendCommand('onaudiostop')

	def onPlayBackPaused(self):
		if xbmc.Player().isPlayingAudio():
			self.SendCommand('onaudiopause')
		else:
			self.SendCommand('onvideopause')

	def onPlayBackResumed(self):
		if xbmc.Player().isPlayingAudio():
			self.SendCommand('onaudioplay')
		else:
			self.isplayingvideo = True;
			self.SendCommand('onvideoplay')

# -- Main Code ----------------------------------------------
handler=FhemHandler()
handler.StartUp()
handler.Run()
handler.ShutDown()
