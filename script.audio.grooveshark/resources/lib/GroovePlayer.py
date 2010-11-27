import sys
import os
import xbmc
import xbmcgui

class GroovePlayer(xbmc.Player):
	def __init__(self, *args, **kwargs):
		self.function = self.dummyFunc
		self.state = 0

	def onPlayBackStopped(self):
		self.state = 0
		self.function(0)

	def onPlayBackEnded(self):
		self.state = 0
		self.function(1, xbmcgui.getCurrentWindowId())

	def onPlayBackStarted(self):
		self.state = 2
		self.function(2)
		
	def onPlayBackPaused(self):
		self.state = 1
		self.function(3)

	def onPlayBackResumed(self):
		self.state = 2
		self.function(4)
		
	#def playnext(self):
	#	self.function(5)
		
	def isPaused(self):
		if self.state == 1:
			return True
		else:
			return False
			
	def isStopped(self):
		if self.state == 0:
			return True
		else:
			return False

	def setCallBackFunc(self, func):
		self.function = func
		
	def dummyFunc(self, event):
		pass
