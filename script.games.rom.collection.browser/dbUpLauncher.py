
import os
import sys
import time

import xbmc
import xbmcgui
import xbmcaddon

# Shared resources
addonPath = ''
addon = xbmcaddon.Addon(id='script.games.rom.collection.browser')
addonPath = addon.getAddonInfo('path')
		
BASE_RESOURCE_PATH = os.path.join(addonPath, "resources" )

sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib", "pyparsing" ) )
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib", "pyscraper" ) )

# append the proper platforms folder to our path, xbox is the same as win32
env = ( os.environ.get( "OS", "win32" ), "win32", )[ os.environ.get( "OS", "win32" ) == "xbox" ]
if env == 'Windows_NT':
	env = 'win32'
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "platform_libraries", 'Linux' ) )

from gamedatabase import *
from util import *
import dbupdate
import config


ALLOWEDWINDOWS = [10000]

class ProgressDialogBk:
	
	itemCount = 1
	label = None
	progress = None
	windowID = None
	
	
	def __init__(self):
		self.paintProgress()
	
	def paintProgress(self):
		print 'paintProgress'
		
		self.windowID = xbmcgui.getCurrentWindowId()
		self.window = xbmcgui.Window(self.windowID)
		self.image = xbmcgui.ControlImage(880, 630, 400, 60, "InfoMessagePanel.png", colorDiffuse='0xC0C0C0C0')
		self.window.addControl(self.image)
		self.image.setVisible(False)
		animations = [('Conditional', 'effect=slide start=1280,0 time=2000 condition=Control.IsVisible(%d)' % self.image.getId())]
		self.image.setAnimations(animations)
		
		self.header = xbmcgui.ControlLabel(900, 635, 400, 60, 'Scraping RCB', font='font10_title', textColor='0xFFEB9E17')
		self.window.addControl(self.header)
		self.header.setVisible(False)
		self.header.setAnimations(animations)
		
		self.label = xbmcgui.ControlLabel(900, 655, 400, 60, 'Scraping RCB', font='font10')
		self.window.addControl(self.label)
		self.label.setVisible(False)
		self.label.setAnimations(animations)

		self.progress = xbmcgui.ControlProgress(900, 675, 370, 8)
		self.window.addControl(self.progress)
		self.progress.setVisible(False)
		self.progress.setAnimations(animations)
		
		self.label.setVisible(True)
		self.image.setVisible(True)
		self.progress.setVisible(True)
		self.header.setVisible(True)
			
	
	def writeMsg(self, line1, line2, line3, count=0):
		print 'writeMsg'
		print 'count = ' +str(count)
		
		#If we are done, remove progress
		if(line1 == 'Done.'):
			try:
				self.window.removeControl(self.image)
				self.window.removeControl(self.header)
				self.window.removeControl(self.label)
				self.window.removeControl(self.progress)
			except:
				pass
			
			return False
				
		#check if action was canceled from RCB
		scrapeOnStartupAction = util.getSettings().getSetting(util.SETTING_RCB_SCRAPEONSTARTUPACTION)
		print 'scrapeOnStartupAction = ' +scrapeOnStartupAction
		if (scrapeOnStartupAction == 'cancel'):
			self.label.setLabel("%d %% - %s" % (100, 'Update canceled'))
			try:
				self.window.removeControl(self.image)
				self.window.removeControl(self.header)
				self.window.removeControl(self.label)
				self.window.removeControl(self.progress)
			except:
				pass
			
			return False
		
		if not self.label:
		  return True  
		elif (count > 0):
			print 'count > 0'
			percent = int(count * (float(100) / self.itemCount))
			self.header.setLabel(line1)
			self.label.setLabel("%d %% - %s" % (percent, line2))
			self.progress.setPercent(percent)
			
			
		if self.windowID != xbmcgui.getCurrentWindowId():
			self.windowID = xbmcgui.getCurrentWindowId()
			if xbmcgui.getCurrentWindowId() in ALLOWEDWINDOWS:			
				self.paintProgress()
			
		return True

def runUpdate():
	print 'runUpdate'
	
	gdb = GameDataBase(util.getAddonDataPath())
	gdb.connect()
	#create db if not existent and maybe update to new version
	gdb.checkDBStructure()
	
	configFile = config.Config(None)
	statusOk, errorMsg = configFile.readXml()
	
	settings = util.getSettings()
	scrapingMode = util.getScrapingMode(settings)
		 
	settings.setSetting(util.SETTING_RCB_SCRAPEONSTARTUPACTION, 'update')
	
	progress = ProgressDialogBk()
	dbupdate.DBUpdate().updateDB(gdb, progress, scrapingMode, configFile.romCollections, util.getSettings(), False)
	
	settings.setSetting(util.SETTING_RCB_SCRAPEONSTARTUPACTION, 'nothing')
	
if __name__ == "__main__":
	runUpdate()

