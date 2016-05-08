'''
    Kodi video capturer for Hyperion

	Copyright (c) 2013-2016 Hyperion Team

	Permission is hereby granted, free of charge, to any person obtaining a copy
	of this software and associated documentation files (the "Software"), to deal
	in the Software without restriction, including without limitation the rights
	to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
	copies of the Software, and to permit persons to whom the Software is
	furnished to do so, subject to the following conditions:

	The above copyright notice and this permission notice shall be included in
	all copies or substantial portions of the Software.

	THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
	IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
	FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
	AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
	LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
	OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
	THE SOFTWARE.
'''
import xbmc
import xbmcaddon

from misc import log

class MyMonitor (xbmc.Monitor):
	'''Class to capture changes in settings and screensaver state
	'''

	def __init__(self, settings):
		xbmc.Monitor.__init__(self)
		self.__settings = settings
		self.__settings.screensaver = xbmc.getCondVisibility("System.ScreenSaverActive")
		self.__settings.abort = xbmc.abortRequested

	def onAbortRequested(self):
		self.__settings.abort = False

	def onSettingsChanged(self):
		self.__settings.readSettings()

	def onScreensaverDeactivated(self):
		self.__settings.screensaver = False

	def onScreensaverActivated(self):
		self.__settings.screensaver = True


class Settings:
	'''Class which contains all addon settings and xbmc state items of interest
	'''

	def __init__(self):
		'''Constructor
		'''
		self.rev = 0
		self.__monitor = MyMonitor(self)
		self.__player = xbmc.Player()
		self.readSettings()

	def __del__(self):
		'''Destructor
		'''
		del self.__monitor
		del self.__player

	def readSettings(self):
		'''(Re-)read all settings
		'''
		log("Reading settings")
		addon = xbmcaddon.Addon()
		self.enable = bool(addon.getSetting("hyperion_enable"))
		self.enableScreensaver = bool(addon.getSetting("screensaver_enable"))
		self.address = addon.getSetting("hyperion_ip")
		self.port = int(addon.getSetting("hyperion_port"))
		self.priority = int(addon.getSetting("hyperion_priority"))
		self.timeout = int(addon.getSetting("reconnect_timeout"))
		self.capture_width = int(addon.getSetting("capture_width"))
		self.capture_height = int(addon.getSetting("capture_height"))
		self.framerate = int(addon.getSetting("framerate"))

		self.showErrorMessage = True
		self.rev += 1

	def grabbing(self):
		'''Check if we grabbing is requested based on the current state and settings
		'''
		return self.enable and self.__player.isPlayingVideo() \
			and (self.enableScreensaver or not self.screensaver)
