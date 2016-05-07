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

from hyperion.Hyperion import Hyperion
from misc import log
from misc import notify

class DisconnectedState:
	'''
	Default state class when disconnected from the Hyperion server
	'''

	def __init__(self, settings):
		'''Constructor
			- settings: Settings structure
		'''
		log("Entering disconnected state")
		self.__settings = settings

	def execute(self):
		'''Execute the state
			- return: The new state to execute
		'''
		# check if we are enabled
		if not self.__settings.grabbing():
			xbmc.sleep(500)
			return self

		# we are enabled and want to advance to the connected state
		try:
			nextState = ConnectedState(self.__settings)
			return nextState
		except Exception, e:
			# unable to connect. notify and go to the error state
			if self.__settings.showErrorMessage:
				notify(xbmcaddon.Addon().getLocalizedString(32100))
				self.__settings.showErrorMessage = False

			# continue in the error state
			return ErrorState(self.__settings)

class ConnectedState:
	'''
	State class when connected to Hyperion and grabbing video
	'''

	def __init__(self, settings):
		'''Constructor
			- settings: Settings structure
		'''
		log("Entering connected state")

		self.__settings = settings
		self.__hyperion = None
		self.__capture = None
		self.__captureState = None
		self.__data = None
		self.__useLegacyApi = True

		# try to connect to hyperion
		self.__hyperion = Hyperion(self.__settings.address, self.__settings.port)

		# create the capture object
		self.__capture = xbmc.RenderCapture()
		self.__capture.capture(self.__settings.capture_width, self.__settings.capture_height)

	def __del__(self):
		'''Destructor
		'''
		del self.__hyperion
		del self.__capture
		del self.__captureState
		del self.__data
		del self.__useLegacyApi

	def execute(self):
		'''Execute the state
			- return: The new state to execute
		'''
		# check if we still need to grab
		if not self.__settings.grabbing():
			# return to the disconnected state
			return DisconnectedState(self.__settings)

		# check the xbmc API Version
		try:
			self.__capture.getCaptureState()
		except:
			self.__useLegacyApi = False

		# capture an image
		startReadOut = False
		if self.__useLegacyApi:
			self.__capture.waitForCaptureStateChangeEvent(200)
			self.__captureState = self.__capture.getCaptureState()
			if self.__captureState == xbmc.CAPTURE_STATE_DONE:
				startReadOut = True
		else:
			self.__data = self.__capture.getImage()
			if len(self.__data) > 0:
				startReadOut = True

		if startReadOut:
			if self.__useLegacyApi:
				self.__data = self.__capture.getImage()

			# retrieve image data and reformat into rgb format
			if self.__capture.getImageFormat() == 'ARGB':
				del self.__data[0::4]
			elif self.__capture.getImageFormat() == 'BGRA':
				del self.__data[3::4]
				self.__data[0::3], self.__data[2::3] = self.__data[2::3], self.__data[0::3]

			try:
				#send image to hyperion
				self.__hyperion.sendImage(self.__capture.getWidth(), self.__capture.getHeight(), str(self.__data), self.__settings.priority, 500)
			except Exception, e:
				# unable to send image. notify and go to the error state
				notify(xbmcaddon.Addon().getLocalizedString(32101))
				return ErrorState(self.__settings)

		if self.__useLegacyApi:
			if self.__captureState != xbmc.CAPTURE_STATE_WORKING:
				#the current capture is processed or it has failed, we request a new one
				self.__capture.capture(self.__settings.capture_width, self.__settings.capture_height)

		#limit the maximum number of frames sent to hyperion
		xbmc.sleep( int(1. / self.__settings.framerate * 1000) )

		return self

class ErrorState:
	'''
	State class which is activated upon an error
	'''

	def __init__(self, settings):
		'''Constructor
			- settings: Settings structure
		'''
		log("Entering error state")
		self.__settings = settings

	def execute(self):
		'''Execute the state
			- return: The new state to execute
		'''
		# take note of the current revision of the settings
		rev = self.__settings.rev

		#stay in error state for the specified timeout or until the settings have been changed
		i = 0
		while (i < self.__settings.timeout) and (rev == self.__settings.rev):
			if self.__settings.abort:
				return self
			else:
				xbmc.sleep(1000)
			i += 1

		# continue in the disconnected state
		return DisconnectedState(self.__settings)
