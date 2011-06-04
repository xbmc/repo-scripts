
import xbmc, xbmcgui
import string, glob, time, array, os, sys, shutil, re
from threading import *

from util import *
import util
import dbupdate, helper, launcher, config
import dialogimportoptions, dialogcontextmenu
from config import *
from configxmlwriter import *
from configxmlupdater import *
from gamedatabase import *


#Action Codes
# See guilib/Key.h
ACTION_EXIT_SCRIPT = (10,)
ACTION_CANCEL_DIALOG = ACTION_EXIT_SCRIPT + (9,)
ACTION_MOVEMENT_LEFT = (1,)
ACTION_MOVEMENT_RIGHT = (2,)
ACTION_MOVEMENT_UP = (3,)
ACTION_MOVEMENT_DOWN = (4,)
ACTION_MOVEMENT = (1, 2, 3, 4, 5, 6, 159, 160)
ACTION_INFO = (11,)
ACTION_CONTEXT = (117,)


#ControlIds
CONTROL_CONSOLES = 500
CONTROL_GENRE = 600
CONTROL_YEAR = 700
CONTROL_PUBLISHER = 800
CONTROL_CHARACTER = 900
FILTER_CONTROLS = (500, 600, 700, 800, 900,)
GAME_LISTS = (50, 51, 52, 53, 54, 55, 56, 57, 58)
CONTROL_SCROLLBARS = (2200, 2201, 60, 61, 62)

CONTROL_GAMES_GROUP_START = 50
CONTROL_GAMES_GROUP_END = 59
CONTROL_VIEW_NO_VIDEOS = (55, 56, 57, 58)

CONTROL_BUTTON_UPDATEDB = 3100
CONTROL_BUTTON_CHANGE_VIEW = 2
CONTROL_BUTTON_VIDEOFULLSCREEN = (2900, 2901,)

CONTROL_LABEL_MSG = 4000



class MyPlayer(xbmc.Player):
	
	gui = None
	
	stoppedByRCB = False
	startedInPlayListMode = False
	
	def onPlayBackStarted(self):
		if(self.gui == None):
			print "RCB_WARNING: gui == None in MyPlayer"
			return				
			
		if (os.environ.get("OS", "xbox") != "xbox"):
			self.gui.saveViewState(True)
	
	def onPlayBackEnded(self):
		if(self.gui == None):
			print "RCB_WARNING: gui == None in MyPlayer"
			return
		
		#in PlayListMode we will move to the next item
		if(self.startedInPlayListMode):			
			self.gui.fullScreenVideoStarted = False
			return
		
		if(self.gui.gameinfoDialogOpen):
			return
				
		xbmc.sleep(util.WAITTIME_PLAYERSTOP)
				
		if (os.environ.get("OS", "xbox") != "xbox"):
			self.gui.loadViewState()
			
	def onPlayBackStopped(self):
		if(self.gui == None):
			print "RCB_WARNING: gui == None in MyPlayer"
			return						
		
		self.gui.fullScreenVideoStarted = False
		
		if(self.gui.gameinfoDialogOpen):
			return
		
		xbmc.sleep(util.WAITTIME_PLAYERSTOP)
				
		if (os.environ.get("OS", "xbox") != "xbox"):
			if(not self.stoppedByRCB):
				self.stoppedByRCB = False
				self.gui.loadViewState()
		


class ProgressDialogGUI:		
	
	def __init__(self):
		self.itemCount = 0
		self.dialog = xbmcgui.DialogProgress()				
			
	def writeMsg(self, line1, line2, line3, count=0):
		if (not count):
			self.dialog.create(line1)
		elif (count > 0):
			percent = int(count * (float(100) / self.itemCount))			
			self.dialog.update(percent, line1, line2, line3)
			if (self.dialog.iscanceled()):
				return False
			else: 
				return True
		else:
			self.dialog.close()


class UIGameDB(xbmcgui.WindowXML):	
	
	gdb = None	
	
	selectedControlId = 0
	selectedConsoleId = 0
	selectedGenreId = 0
	selectedYearId = 0
	selectedPublisherId = 0
	selectedCharacter = 'All'
	
	selectedConsoleIndex = 0
	selectedGenreIndex = 0
	selectedYearIndex = 0
	selectedPublisherIndex = 0	
	selectedCharacterIndex = 0				
	
	playVideoThread = None
	playVideoThreadStopped = False
	rcb_playList = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
	playlistOffsets = {}		
		
	#dummy to be compatible with ProgressDialogGUI
	itemCount = 0	
		
	# set flag if we are watching fullscreen video
	fullScreenVideoStarted = False
	# set flag if we opened GID
	gameinfoDialogOpen = False
	
	# set flag if we are currently running onAction
	onActionLastRun = 0	
			
	#cachingOption will be overwritten by config. Don't change it here.
	cachingOption = 3
	
	useRCBService = False
	
	
	def __init__(self, strXMLname, strFallbackPath, strDefaultName, forceFallback):
		# Changing the three varibles passed won't change anything
		# Doing strXMLname = "bah.xml" will not change anything.
		# don't put GUI sensitive stuff here (as the xml hasn't been read yet
		# Idea to initialize your variables here				
		Logutil.log("Init Rom Collection Browser: " + util.RCBHOME, util.LOG_LEVEL_INFO)
		
		self.Settings = util.getSettings()
				
		if(util.hasAddons()):			
			import xbmcaddon
	        addon = xbmcaddon.Addon(id='%s' %util.SCRIPTID)
	        Logutil.log("RCB version: " + addon.getAddonInfo('version'), util.LOG_LEVEL_INFO)
	        
	        #check if RCB service is available, otherwise we will use autoexec.py
	        try:
	        	serviceAddon = xbmcaddon.Addon(id='service.rom.collection.browser')
	        	Logutil.log("RCB service addon: " + str(serviceAddon), util.LOG_LEVEL_INFO)
	        	self.useRCBService = True
	        except:
	        	Logutil.log("No RCB service addon available. Will use autoexec.py for startup features.", util.LOG_LEVEL_INFO)
	        
		
		if self.checkUpdateInProgress():
			self.quit = True
			return
		
		#timestamp1 = time.clock()
		
		try:
			self.gdb = GameDataBase(util.getAddonDataPath())
			self.gdb.connect()
		except Exception, (exc):
			xbmcgui.Dialog().ok(util.SCRIPTNAME, 'Error accessing database', str(exc))
			print ('Error accessing database: ' +str(exc))
			self.quit = True
			return
		
		#check if we have an actual database
		#create new one or alter existing one
		doImport, errorMsg = self.gdb.checkDBStructure()
		
		#check if config.xml is up to date
		returnCode, message = ConfigxmlUpdater().updateConfig(self)
				
		
		self.quit = False
		if(doImport == -1):
			xbmcgui.Dialog().ok(util.SCRIPTNAME, errorMsg)			
			self.quit = True
			return
		elif(doImport == 2):
			xbmcgui.Dialog().ok(util.SCRIPTNAME, 'Database and config.xml updated to new version.', 'Please check your emulatorCmd to launch games.')			
		
		#check if we have config file 
		configFile = util.getConfigXmlPath()
		if(not os.path.isfile(configFile)):
			
			dialog = xbmcgui.Dialog()
		
			retValue = dialog.yesno('Rom Collection Browser', 'No config file found.', 'Do you want to create one?')
			if(retValue == False):
				self.quit = True
				return
			
			statusOk, errorMsg = self.createConfigXml(configFile)
		
		#read config.xml
		self.config = Config()
		statusOk, errorMsg = self.config.readXml()
		if(statusOk == False):
			xbmcgui.Dialog().ok(util.SCRIPTNAME, 'Error reading config.xml.', errorMsg)
			self.quit = True
			return
		
		self.gdb.commit()
		
		self.memDB = False			
		memDB = self.Settings.getSetting(util.SETTING_RCB_MEMDB)
		
		if memDB == 'true':
			self.memDB = True
			if self.gdb.toMem():
				Logutil.log("DB loaded to Mem!", util.LOG_LEVEL_INFO)
			else:
				Logutil.log("Load DB to Mem failed!", util.LOG_LEVEL_INFO)
		
		cachingOptionStr = self.Settings.getSetting(util.SETTING_RCB_CACHINGOPTION)
		if(cachingOptionStr == 'CACHEALL'):
			self.cachingOption = 0
		#elif(cachingOptionStr == 'CACHESELECTION'):
		#	self.cachingOption = 1
		elif(cachingOptionStr == 'CACHEITEM'):
			self.cachingOption = 2
		elif(cachingOptionStr == 'CACHEITEMANDNEXT'):
			self.cachingOption = 3
		
		
		self.checkImport(doImport)
		
		self.cacheItems()
		
		#timestamp2 = time.clock()
		#diff = (timestamp2 - timestamp1) * 1000		
		#print "RCB startup time: %d ms" % (diff)
		
		self.player = MyPlayer()
		self.player.gui = self
						
		
	def onInit(self):
		
		Logutil.log("Begin onInit", util.LOG_LEVEL_INFO)
		
		if(self.quit):			
			self.close()
			return
		
		self.clearList()
		self.rcb_playList.clear()
		xbmc.sleep(util.WAITTIME_UPDATECONTROLS)						
		
		self.updateControls()
		self.loadViewState()
		
		#check startup tasks done with autoexec.py
		if(not self.useRCBService):
			self.checkAutoExec()
			self.checkScrapStart()

		Logutil.log("End onInit", util.LOG_LEVEL_INFO)

	
	def onAction(self, action):
		
		Logutil.log("onAction: " +str(action.getId()), util.LOG_LEVEL_DEBUG)
		
		#Hack: prevent being invoked twice
		onActionCurrentRun = time.clock()
		
		Logutil.log("onActionCurrentRun: %d ms" % (onActionCurrentRun * 1000), util.LOG_LEVEL_INFO)
		Logutil.log("onActionLastRun: %d ms" % (self.onActionLastRun * 1000), util.LOG_LEVEL_INFO)
		
		diff = (onActionCurrentRun - self.onActionLastRun) * 1000
		Logutil.log("diff: %d ms" % (diff), util.LOG_LEVEL_INFO)
		
		waitTime = util.WAITTIME_ONACTION
		if (os.environ.get("OS", "xbox") == "xbox"):
			waitTime = util.WAITTIME_ONACTION_XBOX
		
		if(int(diff) <= waitTime):
			Logutil.log("Last run still active. Do nothing.", util.LOG_LEVEL_INFO)
			self.onActionLastRun = time.clock()
			return
		
		self.onActionLastRun = time.clock()
							
		try:
			if(action.getId() in ACTION_CANCEL_DIALOG):
				Logutil.log("onAction: ACTION_CANCEL_DIALOG", util.LOG_LEVEL_INFO)
							
				if(self.player.isPlayingVideo()):
					self.player.stoppedByRCB = True
					self.player.stop()
					xbmc.sleep(util.WAITTIME_PLAYERSTOP)
				
				self.onActionLastRun = time.clock()
				self.exit()
			elif(action.getId() in ACTION_MOVEMENT):
														
				Logutil.log("onAction: ACTION_MOVEMENT", util.LOG_LEVEL_DEBUG)
				
				control = self.getControlById(self.selectedControlId)
				if(control == None):
					Logutil.log("control == None in onAction", util.LOG_LEVEL_WARNING)
					self.onActionLastRun = time.clock()										
					return
					
				if(CONTROL_GAMES_GROUP_START <= self.selectedControlId <= CONTROL_GAMES_GROUP_END):
					if(not self.fullScreenVideoStarted):
						self.showGameInfo()
				
				#if(action.getId() in ACTION_MOVEMENT_UP or action.getId() in ACTION_MOVEMENT_DOWN):	
				if(self.selectedControlId in FILTER_CONTROLS):
					
					label = str(control.getSelectedItem().getLabel())
					label2 = str(control.getSelectedItem().getLabel2())
						
					filterChanged = False
					
					if (self.selectedControlId == CONTROL_CONSOLES):
						if(self.selectedConsoleIndex != control.getSelectedPosition()):
							self.selectedConsoleId = int(label2)
							self.selectedConsoleIndex = control.getSelectedPosition()
							filterChanged = True
							
					elif (self.selectedControlId == CONTROL_GENRE):
						if(self.selectedGenreIndex != control.getSelectedPosition()):
							self.selectedGenreId = int(label2)
							self.selectedGenreIndex = control.getSelectedPosition()
							filterChanged = True
					elif (self.selectedControlId == CONTROL_YEAR):
						if(self.selectedYearIndex != control.getSelectedPosition()):
							self.selectedYearId = int(label2)
							self.selectedYearIndex = control.getSelectedPosition()
							filterChanged = True
					elif (self.selectedControlId == CONTROL_PUBLISHER):
						if(self.selectedPublisherIndex != control.getSelectedPosition()):
							self.selectedPublisherId = int(label2)
							self.selectedPublisherIndex = control.getSelectedPosition()
							filterChanged = True
					elif (self.selectedControlId == CONTROL_CHARACTER):
						if(self.selectedCharacterIndex != control.getSelectedPosition()):
							self.selectedCharacter = label
							self.selectedCharacterIndex = control.getSelectedPosition()
							filterChanged = True
					if(filterChanged):					
						self.showGames()								
				
			elif(action.getId() in ACTION_INFO):
				Logutil.log("onAction: ACTION_INFO", util.LOG_LEVEL_DEBUG)
				
				control = self.getControlById(self.selectedControlId)
				if(control == None):
					Logutil.log("control == None in onAction", util.LOG_LEVEL_WARNING)
					self.onActionLastRun = time.clock()					
					return
				if(CONTROL_GAMES_GROUP_START <= self.selectedControlId <= CONTROL_GAMES_GROUP_END):
					self.showGameInfoDialog()
			elif (action.getId() in ACTION_CONTEXT):
				Logutil.log('onAction: ACTION_CONTEXT', util.LOG_LEVEL_INFO)
				self.showContextMenu()
		except Exception, (exc):
			print "RCB_ERROR: unhandled Error in onAction: " +str(exc)
			self.onActionLastRun = time.clock()
				
		self.onActionLastRun = time.clock()
			

	def onClick(self, controlId):
		
		Logutil.log("onClick: " + str(controlId), util.LOG_LEVEL_DEBUG)
				
		if (controlId == CONTROL_BUTTON_UPDATEDB):
			Logutil.log("onClick: Update DB", util.LOG_LEVEL_DEBUG)
			self.updateDB()		
		elif (controlId in FILTER_CONTROLS):
			Logutil.log("onClick: Show Game Info", util.LOG_LEVEL_DEBUG)
			self.setFocus(self.getControl(CONTROL_GAMES_GROUP_START))
			self.showGameInfo()
		elif (controlId in GAME_LISTS):
			Logutil.log("onClick: Launch Emu", util.LOG_LEVEL_DEBUG)
			self.launchEmu()
		elif (controlId in CONTROL_BUTTON_VIDEOFULLSCREEN):
			Logutil.log("onClick: Video fullscreen", util.LOG_LEVEL_DEBUG)
			self.startFullscreenVideo()


	def onFocus(self, controlId):
		Logutil.log("onFocus: " + str(controlId), util.LOG_LEVEL_DEBUG)
		self.selectedControlId = controlId
		
		
	def updateControls(self, rcDelete=False, rDelete=False):
		
		Logutil.log("Begin updateControls", util.LOG_LEVEL_DEBUG)
		
		#prepare FilterControls	
		self.showConsoles(rcDelete, rDelete)		
		self.showGenre(rcDelete, rDelete)		
		self.showYear(rcDelete, rDelete)
		self.showPublisher(rcDelete, rDelete)		
		self.showCharacterFilter()
		
		Logutil.log("End updateControls", util.LOG_LEVEL_DEBUG)
		
		
	def showConsoles(self, rcDelete=False, rDelete=False):
		Logutil.log("Begin showConsoles" , util.LOG_LEVEL_DEBUG)
				
		showEntryAllItems = self.Settings.getSetting(util.SETTING_RCB_SHOWENTRYALLCONSOLES).upper() == 'TRUE'
		
		consoles = []
		for romCollection in self.config.romCollections.values():
			consoleRow = []
			consoleRow.append(romCollection.id)
			consoleRow.append(romCollection.name)
			consoles.append(consoleRow)
		
		self.selectedConsoleId = self.showFilterControl(None, CONTROL_CONSOLES, showEntryAllItems, consoles, rcDelete, rDelete, True)
		
		Logutil.log("End showConsoles" , util.LOG_LEVEL_DEBUG)


	def showGenre(self, rcDelete=False, rDelete=False):
		Logutil.log("Begin showGenre" , util.LOG_LEVEL_DEBUG)
		
		showEntryAllItems = self.Settings.getSetting(util.SETTING_RCB_SHOWENTRYALLGENRES).upper() == 'TRUE'
		self.selectedGenreId = self.showFilterControl(Genre(self.gdb), CONTROL_GENRE, showEntryAllItems, None, rcDelete, rDelete)
		
		Logutil.log("End showGenre" , util.LOG_LEVEL_DEBUG)
		
	
	def showYear(self, rcDelete=False, rDelete=False):
		Logutil.log("Begin showYear" , util.LOG_LEVEL_DEBUG)
		
		showEntryAllItems = self.Settings.getSetting(util.SETTING_RCB_SHOWENTRYALLYEARS).upper() == 'TRUE'
		self.selectedYearId = self.showFilterControl(Year(self.gdb), CONTROL_YEAR, showEntryAllItems, None, rcDelete, rDelete)
		Logutil.log("End showYear" , util.LOG_LEVEL_DEBUG)
		
		
	def showPublisher(self, rcDelete=False, rDelete=False):
		Logutil.log("Begin showPublisher" , util.LOG_LEVEL_DEBUG)
		
		showEntryAllItems = self.Settings.getSetting(util.SETTING_RCB_SHOWENTRYALLPUBLISHER).upper() == 'TRUE'
		self.selectedPublisherId = self.showFilterControl(Publisher(self.gdb), CONTROL_PUBLISHER, showEntryAllItems, None, rcDelete, rDelete)
		
		Logutil.log("End showPublisher" , util.LOG_LEVEL_DEBUG)


	def showFilterControl(self, dbo, controlId, showEntryAllItems, rows, romCollectionDeleted=False, romsDeleted=False, handleConsole=False):
		
		Logutil.log("begin showFilterControl: " + str(controlId), util.LOG_LEVEL_DEBUG)
				
		if(dbo != None):				
			rows = dbo.getAllOrdered()
		
		control = self.getControlById(controlId)
		if(control == None):
			Logutil.log("control == None in showFilterControl", util.LOG_LEVEL_WARNING)
			return
		
		control.setVisible(1)
		control.reset()
		
		items = []
		if(showEntryAllItems):
			items.append(xbmcgui.ListItem("All", "0", "", ""))
		
		for row in rows:
			items.append(xbmcgui.ListItem(row[util.ROW_NAME], str(row[util.ROW_ID]), "", ""))
			
		control.addItems(items)
				
		#return selected id if we are not in "delete rom collection" mode  
		if((not romsDeleted and not romCollectionDeleted) or not handleConsole):
			label2 = str(control.getSelectedItem().getLabel2())
			return int(label2)
				
		rcSelected = False 
		consoleCount = 0
		newSelectedConsoleId = 0
			
		#get new index of selected rom collection
		for romCollection in self.config.romCollections.values():
			if(int(romCollection.id) == int(self.selectedConsoleId)):
				rcSelected = True
				newSelectedConsoleId = int(romCollection.id)
			consoleCount += 1
					
		if(rcSelected == False):
			#no RC selected
			return 0
		else:
			return int(newSelectedConsoleId)
			
	
	def showCharacterFilter(self):
		Logutil.log("Begin showCharacterFilter" , util.LOG_LEVEL_DEBUG)
		
		control = self.getControlById(CONTROL_CHARACTER)
		
		if(control == None):
			Logutil.log("control == None in showFilterControl", util.LOG_LEVEL_WARNING)
			return
			
		control.reset()
		
		showEntryAllItems = self.Settings.getSetting(util.SETTING_RCB_SHOWENTRYALLCHARS).upper() == 'TRUE'
		
		items = []		
		if(showEntryAllItems):
			items.append(xbmcgui.ListItem("All", "All", "", ""))
		items.append(xbmcgui.ListItem("0-9", "0-9", "", ""))
		
		for i in range(0, 26):
			char = chr(ord('A') + i)
			items.append(xbmcgui.ListItem(char, char, "", ""))
			
		control.addItems(items)
		Logutil.log("End showCharacterFilter" , util.LOG_LEVEL_DEBUG)
		

	def showGames(self):
		Logutil.log("Begin showGames" , util.LOG_LEVEL_INFO)
		
		preventUnfilteredSearch = self.Settings.getSetting(util.SETTING_RCB_PREVENTUNFILTEREDSEARCH).upper() == 'TRUE'			
		
		if(preventUnfilteredSearch):			
			if(self.selectedCharacter == 'All' and self.selectedConsoleId == 0 and self.selectedGenreId == 0 and self.selectedYearId == 0 and self.selectedPublisherId == 0):
				Logutil.log("preventing unfiltered search", util.LOG_LEVEL_WARNING)
				return				
		
		timestamp1 = time.clock()
		
		# build statement for character search (where name LIKE 'A%')
		likeStatement = helper.buildLikeStatement(self.selectedCharacter)
		games = Game(self.gdb).getFilteredGames(self.selectedConsoleId, self.selectedGenreId, self.selectedYearId, self.selectedPublisherId, likeStatement)
		
		if(games == None):
			Logutil.log("games == None in showGames", util.LOG_LEVEL_WARNING)
			return		
		
		fileDict = self.getFileDictForGamelist()
				
		timestamp2 = time.clock()
		diff = (timestamp2 - timestamp1) * 1000
		print "load games from db in %d ms" % (diff)
	
		self.writeMsg("loading games...")
		xbmcgui.lock()
		
		self.clearList()
		self.rcb_playList.clear()		
		
		count = 0
		for gameRow in games:
						
			romCollection = None
			try:
				romCollection = self.config.romCollections[str(gameRow[util.GAME_romCollectionId])]
			except:
				Logutil.log('Cannot get rom collection with id: ' +str(gameRow[util.GAME_romCollectionId]), util.LOG_LEVEL_ERROR)
		
			try:
				#images for gamelist
				imageGameList = self.getFileForControl(romCollection.imagePlacing.fileTypesForGameList, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
				imageGameListSelected = self.getFileForControl(romCollection.imagePlacing.fileTypesForGameListSelected, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)												
				
				#create ListItem
				item = xbmcgui.ListItem(gameRow[util.ROW_NAME], str(gameRow[util.ROW_ID]), imageGameList, imageGameListSelected)			
				item.setProperty('gameId', str(gameRow[util.ROW_ID]))
							
				#0 = cacheAll: load all game data at once
				if(self.cachingOption == 0):
					self.setAllItemData(item, gameRow, self.fileDict, romCollection)							
				
				self.addItem(item, False)
				
				# add video to playlist for fullscreen support
				self.addFullscreenVideoToPlaylist(gameRow, imageGameList, imageGameListSelected, count, fileDict, romCollection)
					
				count = count + 1
			except Exception, (exc):
				Logutil.log('Error loading game: %s' % str(exc), util.LOG_LEVEL_ERROR)
				
			
		xbmc.executebuiltin("Container.SortDirection")
		xbmcgui.unlock()				
		
		self.writeMsg("")
		
		timestamp3 = time.clock()
		diff = (timestamp3 - timestamp2) * 1000		
		print "load %i games to list in %d ms" % (self.getListSize(), diff)		
		
		Logutil.log("End showGames" , util.LOG_LEVEL_INFO)		
	
	
	def showGameInfo(self):
		Logutil.log("Begin showGameInfo" , util.LOG_LEVEL_INFO)
		
		self.writeMsg("")	
		
		if(self.playVideoThread != None and self.playVideoThread.isAlive()):			
			self.playVideoThreadStopped = True
		
		if(self.getListSize() == 0):
			Logutil.log("ListSize == 0 in showGameInfo", util.LOG_LEVEL_WARNING)			
			return
					
		pos = self.getCurrentListPosition()
		if(pos == -1):
			pos = 0						
		
		selectedGame, gameRow = self.getGameByPosition(self.gdb, pos)
		if(selectedGame == None or gameRow == None):
			Logutil.log("game == None in showGameInfo", util.LOG_LEVEL_WARNING)			
			return
		
		romCollection = None
		try:
			romCollection = self.config.romCollections[str(gameRow[util.GAME_romCollectionId])]
		except:
			Logutil.log('Cannot get rom collection with id: ' +str(gameRow[util.GAME_romCollectionId]), util.LOG_LEVEL_ERROR)
			
		self.loadVideoFiles(self.gdb, gameRow, selectedGame, romCollection)
		
		#gameinfos are already loaded with cachingOption 0 (cacheAll)
		if(self.cachingOption > 0):
			self.loadGameInfos(self.gdb, gameRow, selectedGame, pos, romCollection)
				
		Logutil.log("End showGameInfo" , util.LOG_LEVEL_INFO)
		
		
	def launchEmu(self):

		Logutil.log("Begin launchEmu" , util.LOG_LEVEL_INFO)

		if(self.getListSize() == 0):
			Logutil.log("ListSize == 0 in launchEmu", util.LOG_LEVEL_WARNING)
			return

		pos = self.getCurrentListPosition()
		if(pos == -1):
			pos = 0
		selectedGame = self.getListItem(pos)
		
		if(selectedGame == None):
			Logutil.log("selectedGame == None in launchEmu", util.LOG_LEVEL_WARNING)
			return
			
		gameId = selectedGame.getProperty('gameId')
		Logutil.log("launching game with id: " + str(gameId), util.LOG_LEVEL_INFO)
		
		#stop video (if playing)
		if(self.player.isPlayingVideo()):
			self.player.stoppedByRCB = True
			self.player.stop()
		
		launcher.launchEmu(self.gdb, self, gameId, self.config, self.Settings)
		Logutil.log("End launchEmu" , util.LOG_LEVEL_INFO)
		
		
	def startFullscreenVideo(self):
		Logutil.log("startFullscreenVideo" , util.LOG_LEVEL_INFO)

		self.fullScreenVideoStarted = True

		self.setFocus(self.getControl(CONTROL_GAMES_GROUP_START))
		
		#Hack: On xbox the list is cleared before starting the player
		if (os.environ.get("OS", "xbox") == "xbox"):
			self.saveViewState(True)
			
		pos = self.getCurrentListPosition()		
				
		#missing videos may lead to a wrong offset. We have to take care with our own hash
		if(len(self.playlistOffsets) != 0):
			try:
				pos = self.playlistOffsets[pos]
			except:
				Logutil.log("Error while reading playlist offset", util.LOG_LEVEL_WARNING)
			self.playlistOffsets = {}				
		
		#stop video (if playing)
		if(self.player.isPlayingVideo()):
			self.player.stoppedByRCB = True
			self.player.stop()
				
		self.player.startedInPlayListMode = True
		self.player.play(self.rcb_playList)		
		xbmc.executebuiltin('Playlist.PlayOffset(%i)' % pos)
		xbmc.executebuiltin('XBMC.PlayerControl(RepeatAll)')		
		
		self.fullScreenVideoStarted = False
		
		
	def updateDB(self):
		Logutil.log("Begin updateDB" , util.LOG_LEVEL_INFO)
		
		self.clearList()
		self.clearCache()
		self.checkImport(3)
		self.cacheItems()
		self.updateControls()
		
		Logutil.log("End updateDB" , util.LOG_LEVEL_INFO)
		
		
	def deleteGame(self, gameID):
		Logutil.log("Begin deleteGame" , util.LOG_LEVEL_INFO)
		
		Logutil.log("Delete Year" , util.LOG_LEVEL_INFO)
		Year(self.gdb).delete(gameID)
		Logutil.log("Delete Publisher" , util.LOG_LEVEL_INFO)
		Publisher(self.gdb).delete(gameID)
		Logutil.log("Delete Developer" , util.LOG_LEVEL_INFO)
		Developer(self.gdb).delete(gameID)
		Logutil.log("Delete Genre" , util.LOG_LEVEL_INFO)
		Genre(self.gdb).delete(gameID)
		Logutil.log("Delete File" , util.LOG_LEVEL_INFO)
		File(self.gdb).delete(gameID)
		Logutil.log("Delete Game" , util.LOG_LEVEL_INFO)
		Game(self.gdb).delete(gameID)
		
		Logutil.log("End deleteGame" , util.LOG_LEVEL_INFO)
	
	
	def deleteRCGames(self, rcID, rcDelete, rDelete):
		Logutil.log("begin Delete Games" , util.LOG_LEVEL_INFO)
		count = 0
		
		rcList = Game(self.gdb).getFilteredGames(rcID, 0, 0, 0, '0 = 0')
		progressDialog = ProgressDialogGUI()
		progressDialog.itemCount = len(rcList)
		
		if(rcList != None):
			progDialogRCDelStat	= "Deleting Rom (%i / %i)" %(count, progressDialog.itemCount)	
			progressDialog.writeMsg("Deleting Roms...", progDialogRCDelStat, "", count)
			for items in rcList:
				count = count + 1
				progDialogRCDelStat	= "Deleting Rom (%i / %i)" %(count, progressDialog.itemCount)	
				progressDialog.writeMsg("", progDialogRCDelStat, "",count)	
				self.deleteGame(items[util.ROW_ID])
					#time.sleep(.001)
			if(len(rcList)>0):
				progressDialog.writeMsg("", "Deleting Roms Complete", "",count)
			else:
				progressDialog.writeMsg("Deleting Roms Complete", "", "",count)
			time.sleep(1)
			self.gdb.commit()
			self.config = Config()
			self.config.readXml()
			self.clearList()
			self.rcb_playList.clear()
			xbmc.sleep(util.WAITTIME_UPDATECONTROLS)
			self.updateControls(rcDelete, rDelete)
			if(rDelete):
				self.selectedConsoleId = self.setFilterSelection(CONTROL_CONSOLES, self.selectedConsoleIndex)
				self.setFilterSelection(CONTROL_GAMES_GROUP_START, 0)
			self.showGames()

		rcList = None
		Logutil.log("end Delete Games" , util.LOG_LEVEL_INFO)
	
	
	def cleanDB(self):
		Logutil.log("Begin cleanDB" , util.LOG_LEVEL_INFO)

		count = 0
		removeCount = 0
		list = File(self.gdb).getFilesList()
		progressDialog2 = ProgressDialogGUI()
		progressDialog2.itemCount = len(list)
		progDialogCleanStat	= "Checking File (%i / %i)" %(count, progressDialog2.itemCount)	
		progressDialog2.writeMsg("Cleaning Database...", progDialogCleanStat, "")
		if(list != None):
			for items in list:
				count = count + 1
				progDialogCleanStat	= "Checking File (%i / %i)" %(count, progressDialog2.itemCount)	
				progressDialog2.writeMsg("", progDialogCleanStat, "",count)	
				if (os.path.exists(items[util.ROW_NAME]) != True):
					if(items[util.FILE_fileTypeId] == 0):
						self.deleteGame(items[util.FILE_parentId])
					else:
						File(self.gdb).deleteByFileId(items[util.ROW_ID])
					removeCount = removeCount + 1
				#time.sleep(.001)
			progressDialog2.writeMsg("", "Compressing Database...", "",count)
			self.gdb.compact()
			time.sleep(.5)
			progressDialog2.writeMsg("", "Database Clean-up Complete", "",count)
			time.sleep(1)
			self.showGames()
		list = None
		Logutil.log("End cleanDB" , util.LOG_LEVEL_INFO)
	
	
	def addRomCollection(self):
		Logutil.log("Begin addRomCollection" , util.LOG_LEVEL_INFO)
		
		consoleList = sorted(config.consoleDict.keys())
		id = 1
		
		rcIds = self.config.romCollections.keys()
		rcIds.sort()
		#read existing rom collection ids and names
		for rcId in rcIds:				
			
			#remove already configured consoles from the list			
			if(self.config.romCollections[rcId].name in consoleList):
				consoleList.remove(self.config.romCollections[rcId].name)
			#find highest id
			if(int(rcId) > int(id)):
				id = rcId
								
		id = int(id) +1
		
		success, romCollections = self.addRomCollections(id, consoleList, True)
		if(not success):
			Logutil.log('Action canceled. Config.xml will not be written', util.LOG_LEVEL_INFO)
			return False, 'Action canceled. Config.xml will not be written'
				
		configWriter = ConfigXmlWriter(False)
		success, message = configWriter.writeRomCollections(romCollections, False)
		
		#update self.config
		statusOk, errorMsg = self.config.readXml()
		if(statusOk == False):
			xbmcgui.Dialog().ok(util.SCRIPTNAME, 'Error reading config.xml.', errorMsg)
			Logutil.log('Error reading config.xml: ' +errorMsg, util.LOG_LEVEL_INFO)
			return False, 'Error reading config.xml: ' +errorMsg
		
		#import Games
		self.updateDB()
		
		Logutil.log("End addRomCollection" , util.LOG_LEVEL_INFO)
		
		
	def showGameInfoDialog(self):

		Logutil.log("Begin showGameInfoDialog", util.LOG_LEVEL_INFO)
		
		if(self.getListSize() == 0):
			Logutil.log("ListSize == 0 in saveViewState", util.LOG_LEVEL_WARNING)
			return
		
		selectedGameIndex = self.getCurrentListPosition()		
		if(selectedGameIndex == -1):
			selectedGameIndex = 0
		selectedGame = self.getListItem(selectedGameIndex)		
		if(selectedGame == None):
			Logutil.log("selectedGame == None in showGameInfoDialog", util.LOG_LEVEL_WARNING)
			return
		
		gameId = selectedGame.getProperty('gameId')
		
		fileDict = self.getFileDictForGamelist()
		
		self.saveViewMode()
		
		self.gameinfoDialogOpen = True
		
		#HACK: Dharma has a new parameter in Window-Constructor for default resolution
		constructorParam = 1
		if(util.hasAddons()):
			constructorParam = "PAL"		
		
		import gameinfodialog
		gid = gameinfodialog.UIGameInfoView("script-RCB-gameinfo.xml", util.getAddonInstallPath(), "Default", constructorParam, gdb=self.gdb, gameId=gameId,
			consoleId=self.selectedConsoleId, genreId=self.selectedGenreId, yearId=self.selectedYearId, publisherId=self.selectedPublisherId, selectedGameIndex=selectedGameIndex,
			consoleIndex=self.selectedConsoleIndex, genreIndex=self.selectedGenreIndex, yearIndex=self.selectedYearIndex, publisherIndex=self.selectedPublisherIndex,
			selectedCharacter=self.selectedCharacter, selectedCharacterIndex=self.selectedCharacterIndex, controlIdMainView=self.selectedControlId, fileDict=fileDict, config=self.config, settings=self.Settings)
		del gid
		
		self.gameinfoDialogOpen = False
				
		
		self.setFocus(self.getControl(CONTROL_GAMES_GROUP_START))
		self.showGames()
		self.setCurrentListPosition(selectedGameIndex)
		xbmc.sleep(util.WAITTIME_UPDATECONTROLS)
		self.showGameInfo()
		
		Logutil.log("End showGameInfoDialog", util.LOG_LEVEL_INFO)
		
	
	def showContextMenu(self):
		
		constructorParam = 1
		if(util.hasAddons()):
			constructorParam = "PAL"
		cm = dialogcontextmenu.ContextMenuDialog("script-RCB-contextmenu.xml", util.getAddonInstallPath(), "Default", constructorParam, gui=self)
		del cm
				
		
		
	"""
	******************
	* HELPER METHODS *
	******************
	"""
	
	
	def buildMediaTypeList(self, isUpdate):
		#build fileTypeList
		fileTypeList = []
		
		if(isUpdate):
			fileTypes = self.config.tree.findall('FileTypes/FileType')
		else:
			#build fileTypeList
			configFile = os.path.join(util.getAddonInstallPath(), 'resources', 'database', 'config_template.xml')
	
			if(not os.path.isfile(configFile)):
				Logutil.log('File config_template.xml does not exist. Place a valid config file here: ' +str(configFile), util.LOG_LEVEL_ERROR)
				return None, 'Error: File config_template.xml does not exist'
			
			tree = ElementTree().parse(configFile)			
			fileTypes = tree.findall('FileTypes/FileType')			
			
		for fileType in fileTypes:
			name = fileType.attrib.get('name')
			if(name != None):
				type = fileType.find('type')				
				if(type != None and type.text == 'video'):
					name = name +' (video)'
				fileTypeList.append(name)
				
		return fileTypeList, ''
	
	
	
	def getFileDictForGamelist(self):
		# 0 = cacheAll
		if(self.cachingOption == 0):
			fileDict = self.fileDict
		else:
			fileRows = File(self.gdb).getFilesForGamelist(self.config.fileTypeIdsForGamelist)
			if(fileRows == None):
				Logutil.log("fileRows == None in showGames", util.LOG_LEVEL_WARNING)
				return
					
			fileDict = self.cacheFiles(fileRows)
		
		return fileDict
		
		
	def getFileForControl(self, fileTypes, gameId, publisherId, developerId, romCollectionId, fileDict):
		files = helper.getFilesByControl_Cached(self.gdb, fileTypes, gameId, publisherId, developerId, romCollectionId, fileDict)		
		if(files != None and len(files) != 0):
			file = files[0]
		else:
			file = ""
			
		return file
		
		
	def getGamePropertyFromCache(self, gameRow, dict, key, index):
		
		result = ""
		try:
			itemRow = dict[gameRow[key]]			
			result = itemRow[index]
		except:
			pass
			
		return result
		
		
	def getGameProperty(self, property):
						
		try:
			result = str(property)
		except:
			result = ""
			
		return result
	
		
	def addFullscreenVideoToPlaylist(self, gameRow, imageGameList, imageGameListSelected, count, fileDict, romCollection):
		#create dummy ListItem for playlist
		dummyItem = xbmcgui.ListItem(gameRow[util.ROW_NAME], str(gameRow[util.ROW_ID]), imageGameList, imageGameListSelected)
		
		videosFullscreen = helper.getFilesByControl_Cached(self.gdb, romCollection.imagePlacing.fileTypesForMainViewVideoFullscreen, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
		
		#add video to playlist and compute playlistOffset (missing videos must be skipped)
		if(videosFullscreen != None and len(videosFullscreen) != 0):			
			video = videosFullscreen[0]						
			self.rcb_playList.add(video, dummyItem)			
			try:
				if(len(self.playlistOffsets) == 0 or count == 0):
					self.playlistOffsets[count] = 0					
				else:
					offset = self.playlistOffsets[count - 1]					
					self.playlistOffsets[count] = offset + 1					
			except:
				Logutil.log("Error while creating playlist offset", util.LOG_LEVEL_WARNING)
		else:
			if(len(self.playlistOffsets) == 0 or count == 0):
				self.playlistOffsets[count] = 0				
			else:
				offset = self.playlistOffsets[count - 1]
				self.playlistOffsets[count] = offset								
		
	
	def getGameByPosition(self, gdb, pos):
		Logutil.log("size = %i" % self.getListSize(), util.LOG_LEVEL_DEBUG)
		Logutil.log("pos = %s" % pos, util.LOG_LEVEL_DEBUG)
		
		selectedGame = self.getListItem(pos)

		if(selectedGame == None):
			Logutil.log("selectedGame == None in showGameInfo", util.LOG_LEVEL_WARNING)
			return None, None
		
		gameId = selectedGame.getProperty('gameId')
		gameRow = Game(gdb).getObjectById(gameId)				

		if(gameRow == None):			
			Logutil.log("gameId = %s" % gameId, util.LOG_LEVEL_WARNING)
			Logutil.log("gameRow == None in showGameInfo", util.LOG_LEVEL_WARNING)
			return None, None
			
		return selectedGame, gameRow			

		
	def getGameId(self, gdb, pos):
		Logutil.log("pos = %s" % pos, util.LOG_LEVEL_INFO)
		
		selectedGame = self.getListItem(pos)

		if(selectedGame == None):
			Logutil.log("selectedGame == No game selected", util.LOG_LEVEL_WARNING)
			return None
		
		gameId = selectedGame.getProperty('gameId')

		if(gameId == None):			
			Logutil.log("No Game Id Found", util.LOG_LEVEL_WARNING)
			return None
		
		Logutil.log("gameId = " + gameId, util.LOG_LEVEL_INFO)
		
		return gameId


	def loadVideoFiles(self, gdb, gameRow, selectedGame, romCollection):				
		
		viewSupportsVideo = True
		for controlId in CONTROL_VIEW_NO_VIDEOS:
			if (xbmc.getCondVisibility("Control.IsVisible(%i)" % controlId)):
				viewSupportsVideo = False
				break				
		
		#not all views should playback video		
		if (viewSupportsVideo):
		
			if(self.cachingOption == 0):
				fileDict = self.fileDict
			else:
				fileDict = self.getFileDictByGameRow(gdb, gameRow)
		
			#check if fullscreen video is configured (this will just show the button "Play fullscreen video")
			videosFullscreen = helper.getFilesByControl_Cached(self.gdb, romCollection.imagePlacing.fileTypesForMainViewVideoFullscreen, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
			if(videosFullscreen != None and len(videosFullscreen) != 0):				
				selectedGame.setProperty('mainviewvideofullscreen', 'fullscreen')
				
		
			video = ""			
			
			videosBig = helper.getFilesByControl_Cached(self.gdb, romCollection.imagePlacing.fileTypesForMainViewVideoWindowBig, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)			
			
			if(videosBig != None and len(videosBig) != 0):
				video = videosBig[0]				
				selectedGame.setProperty('mainviewvideosizebig', 'big')				
				
			else:
				videosSmall = helper.getFilesByControl_Cached(self.gdb, romCollection.imagePlacing.fileTypesForMainViewVideoWindowSmall, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
				if(videosSmall != None and len(videosSmall) != 0):
					video = videosSmall[0]					
					selectedGame.setProperty('mainviewvideosizesmall', 'small')
												
					
			if(video == "" or video == None):
				Logutil.log("video == None in loadVideoFiles", util.LOG_LEVEL_DEBUG)				
				
				if(self.player.isPlayingVideo()):
					self.player.stoppedByRCB = True
					self.player.stop()
				return							
				
				
			#stop video (if playing)
			if(self.player.isPlayingVideo()):			
				playingFile = self.player.getPlayingFile()				
				if(playingFile != video):
					self.player.stoppedByRCB = True
					self.player.stop()
				else:
					return								
			
			#start a new thread to playback video
			self.playVideoThread = Thread(target=self.playVideo, args=(video, selectedGame))
			self.playVideoThread.start()
			
		
	def playVideo(self, video, selectedGame):
		
		#we have to use a little wait timer before starting video playback: 
		#otherwise video could start in fullscreen if we scroll down the list too fast
		timestamp1 = time.clock()
		while True:
			timestamp2 = time.clock()
			diff = (timestamp2 - timestamp1) * 1000
			if(diff > util.WAITTIME_PLAYERSTART):				
				break
				
			if(self.playVideoThreadStopped):
				self.playVideoThreadStopped = False
				return				
		
		self.player.startedInPlayListMode = False
		self.player.play(video, selectedGame, True)
		
		
	def loadGameInfos(self, gdb, gameRow, selectedGame, pos, romCollection):
		Logutil.log("begin loadGameInfos", util.LOG_LEVEL_DEBUG)
		Logutil.log("gameRow = " +str(gameRow), util.LOG_LEVEL_DEBUG)
		
		if(self.getListSize() == 0):
			Logutil.log("ListSize == 0 in loadGameInfos", util.LOG_LEVEL_WARNING)
			return
		
		# > 1: cacheItem, cacheItemAndNext 
		if(self.cachingOption > 1):				
			fileDict = self.getFileDictByGameRow(gdb, gameRow)
			self.setAllItemData(selectedGame, gameRow, fileDict, romCollection)

		# > 2: cacheItemAndNext 
		if(self.cachingOption > 2):
			#prepare items before and after actual position		
			posBefore = pos - 1
			if(posBefore < 0):
				posBefore = self.getListSize() - 1
							
			selectedGame, gameRow = self.getGameByPosition(gdb, posBefore)
			if(selectedGame == None or gameRow == None):
				return
			fileDict = self.getFileDictByGameRow(gdb, gameRow)
			self.setAllItemData(selectedGame, gameRow, fileDict, romCollection)
			
			posAfter = pos + 1
			if(posAfter >= self.getListSize()):
				posAfter = 0
							
			selectedGame, gameRow = self.getGameByPosition(gdb, posAfter)
			if(selectedGame == None or gameRow == None):
				return
			fileDict = self.getFileDictByGameRow(gdb, gameRow)
			self.setAllItemData(selectedGame, gameRow, fileDict, romCollection)
			
		Logutil.log("end loadGameInfos", util.LOG_LEVEL_DEBUG)

	
	def getFileDictByGameRow(self, gdb, gameRow):				
		
		files = File(gdb).getFilesByParentIds(gameRow[util.ROW_ID], gameRow[util.GAME_romCollectionId], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId])
				
		fileDict = self.cacheFiles(files)
		
		return fileDict
		
		
	def setAllItemData(self, item, gameRow, fileDict, romCollection):				
		
		# all other images in mainwindow
		imagemainViewBackground = self.getFileForControl(romCollection.imagePlacing.fileTypesForMainViewBackground, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
		imageGameInfoBig = self.getFileForControl(romCollection.imagePlacing.fileTypesForMainViewGameInfoBig, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
		imageGameInfoUpperLeft = self.getFileForControl(romCollection.imagePlacing.fileTypesForMainViewGameInfoUpperLeft, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
		imageGameInfoUpperRight = self.getFileForControl(romCollection.imagePlacing.fileTypesForMainViewGameInfoUpperRight, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
		imageGameInfoLowerLeft = self.getFileForControl(romCollection.imagePlacing.fileTypesForMainViewGameInfoLowerLeft, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
		imageGameInfoLowerRight = self.getFileForControl(romCollection.imagePlacing.fileTypesForMainViewGameInfoLowerRight, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
		
		imageGameInfoUpper = self.getFileForControl(romCollection.imagePlacing.fileTypesForMainViewGameInfoUpper, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
		imageGameInfoLower = self.getFileForControl(romCollection.imagePlacing.fileTypesForMainViewGameInfoLower, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
		imageGameInfoLeft = self.getFileForControl(romCollection.imagePlacing.fileTypesForMainViewGameInfoLeft, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
		imageGameInfoRight = self.getFileForControl(romCollection.imagePlacing.fileTypesForMainViewGameInfoRight, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
		
		imageMainView1 = self.getFileForControl(romCollection.imagePlacing.fileTypesForMainView1, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
		imageMainView2 = self.getFileForControl(romCollection.imagePlacing.fileTypesForMainView2, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
		imageMainView3 = self.getFileForControl(romCollection.imagePlacing.fileTypesForMainView3, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)		
		
		#set images as properties for use in the skin
		item.setProperty(util.IMAGE_CONTROL_MV_BACKGROUND, imagemainViewBackground)
		item.setProperty(util.IMAGE_CONTROL_MV_GAMEINFO_BIG, imageGameInfoBig)
		item.setProperty(util.IMAGE_CONTROL_MV_GAMEINFO_UPPERLEFT, imageGameInfoUpperLeft)
		item.setProperty(util.IMAGE_CONTROL_MV_GAMEINFO_UPPERRIGHT, imageGameInfoUpperRight)
		item.setProperty(util.IMAGE_CONTROL_MV_GAMEINFO_LOWERLEFT, imageGameInfoLowerLeft)
		item.setProperty(util.IMAGE_CONTROL_MV_GAMEINFO_LOWERRIGHT, imageGameInfoLowerRight)		
		item.setProperty(util.IMAGE_CONTROL_MV_GAMEINFO_UPPER, imageGameInfoUpper)
		item.setProperty(util.IMAGE_CONTROL_MV_GAMEINFO_LOWER, imageGameInfoLower)
		item.setProperty(util.IMAGE_CONTROL_MV_GAMEINFO_LEFT, imageGameInfoLeft)
		item.setProperty(util.IMAGE_CONTROL_MV_GAMEINFO_RIGHT, imageGameInfoRight)
		item.setProperty(util.IMAGE_CONTROL_MV_1, imageMainView1)
		item.setProperty(util.IMAGE_CONTROL_MV_2, imageMainView2)
		item.setProperty(util.IMAGE_CONTROL_MV_3, imageMainView3)
		
		
		#set additional properties
		description = gameRow[util.GAME_description]
		if(description == None):
			description = ""			
		item.setProperty(util.TEXT_CONTROL_MV_GAMEDESC, description)
		
		try:			
			item.setProperty('romcollection', romCollection.name)			
			item.setProperty('console', romCollection.name)
		except:
			pass									
		
		item.setProperty('year', self.getGamePropertyFromCache(gameRow, self.yearDict, util.GAME_yearId, util.ROW_NAME))
		item.setProperty('publisher', self.getGamePropertyFromCache(gameRow, self.publisherDict, util.GAME_publisherId, util.ROW_NAME))
		item.setProperty('developer', self.getGamePropertyFromCache(gameRow, self.developerDict, util.GAME_developerId, util.ROW_NAME))
		item.setProperty('reviewer', self.getGamePropertyFromCache(gameRow, self.reviewerDict, util.GAME_reviewerId, util.ROW_NAME))
		
		genre = ""			
		try:
			#0 = cacheAll: load all game data at once
			if(self.cachingOption == 0):
				genre = self.genreDict[gameRow[util.ROW_ID]]
			else:				
				genres = Genre(self.gdb).getGenresByGameId(gameRow[util.ROW_ID])
				if (genres != None):
					for i in range(0, len(genres)):
						genreRow = genres[i]
						genre += genreRow[util.ROW_NAME]
						if(i < len(genres) -1):
							genre += ", "			
		except:				
			pass							
		item.setProperty('genre', genre)
		
		item.setProperty('maxplayers', self.getGameProperty(gameRow[util.GAME_maxPlayers]))
		item.setProperty('rating', self.getGameProperty(gameRow[util.GAME_rating]))
		item.setProperty('votes', self.getGameProperty(gameRow[util.GAME_numVotes]))
		item.setProperty('url', self.getGameProperty(gameRow[util.GAME_url]))	
		item.setProperty('region', self.getGameProperty(gameRow[util.GAME_region]))
		item.setProperty('media', self.getGameProperty(gameRow[util.GAME_media]))				
		item.setProperty('perspective', self.getGameProperty(gameRow[util.GAME_perspective]))
		item.setProperty('controllertype', self.getGameProperty(gameRow[util.GAME_controllerType]))
		item.setProperty('isfavorite', self.getGameProperty(gameRow[util.GAME_isFavorite]))
		item.setProperty('playcount', self.getGameProperty(gameRow[util.GAME_launchCount]))
		item.setProperty('originaltitle', self.getGameProperty(gameRow[util.GAME_originalTitle]))
		item.setProperty('alternatetitle', self.getGameProperty(gameRow[util.GAME_alternateTitle]))
		item.setProperty('translatedby', self.getGameProperty(gameRow[util.GAME_translatedBy]))
		item.setProperty('version', self.getGameProperty(gameRow[util.GAME_version]))
		
		return item	
	
	
	def createConfigXml(self, configFile):
				
		id = 1		
		consoleList = sorted(config.consoleDict.keys())
				
		success, romCollections = self.addRomCollections(id, consoleList, False)
		if(not success):
			Logutil.log('Action canceled. Config.xml will not be written', util.LOG_LEVEL_INFO)
			return False, 'Action canceled. Config.xml will not be written'
				
		configWriter = ConfigXmlWriter(True)
		success, message = configWriter.writeRomCollections(romCollections, False)
			
		return success, message		
	
	
	def addRomCollections(self, id, consoleList, isUpdate):
		
		romCollections = {}
		dialog = xbmcgui.Dialog()
		
		#scraping scenario
		scenarioIndex = dialog.select('Choose a scenario', ['Scrape game info and artwork online', 'Game info and artwork are available locally'])
		Logutil.log('scenarioIndex: ' +str(scenarioIndex), util.LOG_LEVEL_INFO)
		if(scenarioIndex == -1):
			del dialog
			Logutil.log('No scenario selected. Action canceled.', util.LOG_LEVEL_INFO)
			return False, romCollections
		
		while True:
					
			fileTypeList, errorMsg = self.buildMediaTypeList(isUpdate)
			romCollection = RomCollection()
			
			#console
			platformIndex = dialog.select('Choose a platform', consoleList)
			Logutil.log('platformIndex: ' +str(platformIndex), util.LOG_LEVEL_INFO)
			if(platformIndex == -1):
				Logutil.log('No Platform selected. Action canceled.', util.LOG_LEVEL_INFO)
				break
			elif(platformIndex == 0):				
				keyboard = xbmc.Keyboard()
				keyboard.setHeading('Enter platform name')			
				keyboard.doModal()
				if (keyboard.isConfirmed()):
					console = keyboard.getText()
					Logutil.log('Platform entered manually: ' +console, util.LOG_LEVEL_INFO)
				else:
					Logutil.log('No Platform entered. Action canceled.', util.LOG_LEVEL_INFO)
					break
			else:
				console = consoleList[platformIndex]
				consoleList.remove(console)
				Logutil.log('selected platform: ' +console, util.LOG_LEVEL_INFO)
			
			romCollection.name = console
			romCollection.id = id
			id = id +1
			
			#emulator
			#xbox games on xbox will be launched directly
			if (os.environ.get( "OS", "xbox" ) == "xbox" and romCollection.name == 'Xbox'):
				romCollection.emulatorCmd = '%ROM%'
				Logutil.log('emuCmd set to "%ROM%" on Xbox.', util.LOG_LEVEL_INFO)
			else:
				consolePath = dialog.browse(1, '%s Emulator' %console, 'files')
				Logutil.log('consolePath: ' +str(consolePath), util.LOG_LEVEL_INFO)
				if(consolePath == ''):
					Logutil.log('No consolePath selected. Action canceled.', util.LOG_LEVEL_INFO)
					break
				romCollection.emulatorCmd = consolePath
			
			#params
			#on xbox we will create .cut files without params
			if (os.environ.get( "OS", "xbox" ) == "xbox"):
				romCollection.emulatorParams = ''
				Logutil.log('emuParams set to "" on Xbox.', util.LOG_LEVEL_INFO)
			else:
				keyboard = xbmc.Keyboard()
				#TODO add all rom params here
				keyboard.setDefault('"%ROM%"')
				keyboard.setHeading('Emulator params ("%ROM%" is used for your rom files)')			
				keyboard.doModal()
				if (keyboard.isConfirmed()):
					emuParams = keyboard.getText()
					Logutil.log('emuParams: ' +str(emuParams), util.LOG_LEVEL_INFO)
				else:
					Logutil.log('No emuParams selected. Action canceled.', util.LOG_LEVEL_INFO)
					break
				romCollection.emulatorParams = emuParams
			
			#roms
			romPath = dialog.browse(0, '%s Roms' %console, 'files')
			if(romPath == ''):
				Logutil.log('No romPath selected. Action canceled.', util.LOG_LEVEL_INFO)
				break
			
			
			#filemask
			
			#xbox games always use default.xbe as executable
			if (os.environ.get( "OS", "xbox" ) == "xbox" and romCollection.name == 'Xbox'):
				Logutil.log('filemask "default.xbe" for Xbox games on Xbox.', util.LOG_LEVEL_INFO)
				romPathComplete = os.path.join(romPath, 'default.xbe')					
				romCollection.romPaths = []
				romCollection.romPaths.append(romPathComplete)
			else:
				keyboard = xbmc.Keyboard()
				keyboard.setHeading('File mask (comma-separated): e.g. *.zip, *.smc')			
				keyboard.doModal()
				if (keyboard.isConfirmed()):					
					fileMaskInput = keyboard.getText()
					Logutil.log('fileMask: ' +str(fileMaskInput), util.LOG_LEVEL_INFO)
					fileMasks = fileMaskInput.split(',')
					romCollection.romPaths = []
					for fileMask in fileMasks:
						romPathComplete = os.path.join(romPath, fileMask.strip())					
						romCollection.romPaths.append(romPathComplete)
				else:
					Logutil.log('No fileMask selected. Action canceled.', util.LOG_LEVEL_INFO)
					break
	
			if (os.environ.get( "OS", "xbox" ) == "xbox"):
				romCollection.xboxCreateShortcut = True
				romCollection.xboxCreateShortcutAddRomfile = True
				romCollection.xboxCreateShortcutUseShortGamename = False
				
				#TODO use flags for complete platform list (not only xbox)
				if(romCollection.name == 'Xbox'):
					romCollection.useFoldernameAsGamename = True
					romCollection.searchGameByCRC = False
					romCollection.maxFolderDepth = 1
			
			
			if(scenarioIndex == 0):
				artworkPath = dialog.browse(0, '%s Artwork' %console, 'files', '', False, False, romPath)
				Logutil.log('artworkPath: ' +str(artworkPath), util.LOG_LEVEL_INFO)
				if(artworkPath == ''):
					Logutil.log('No artworkPath selected. Action canceled.', util.LOG_LEVEL_INFO)
					break
				
				romCollection.descFilePerGame= True
				
				#mediaPaths
				romCollection.mediaPaths = []
				
				if(romCollection.name == 'MAME'):
					romCollection.mediaPaths.append(self.createMediaPath('boxfront', artworkPath, scenarioIndex))
					romCollection.mediaPaths.append(self.createMediaPath('action', artworkPath, scenarioIndex))
					romCollection.mediaPaths.append(self.createMediaPath('title', artworkPath, scenarioIndex))
					romCollection.mediaPaths.append(self.createMediaPath('cabinet', artworkPath, scenarioIndex))
					romCollection.mediaPaths.append(self.createMediaPath('marquee', artworkPath, scenarioIndex))					
				else:
					romCollection.mediaPaths.append(self.createMediaPath('boxfront', artworkPath, scenarioIndex))
					romCollection.mediaPaths.append(self.createMediaPath('boxback', artworkPath, scenarioIndex))
					romCollection.mediaPaths.append(self.createMediaPath('cartridge', artworkPath, scenarioIndex))
					romCollection.mediaPaths.append(self.createMediaPath('screenshot', artworkPath, scenarioIndex))
					romCollection.mediaPaths.append(self.createMediaPath('fanart', artworkPath, scenarioIndex))
				
				#other MAME specific properties
				if(romCollection.name == 'MAME'):
					romCollection.imagePlacing = ImagePlacing()
					romCollection.imagePlacing.name = 'gameinfomamecabinet'
					
					#MAME zip files contain several files but they must be passed to the emu as zip file
					romCollection.doNotExtractZipFiles = True
					
					#create MAWS scraper
					site = Site()
					site.name = 'maws.mameworld.info'
					scrapers = []
					scraper = Scraper()
					scraper.parseInstruction = '06 - maws.xml'
					scraper.source = 'http://maws.mameworld.info/maws/romset/%GAME%'
					scrapers.append(scraper)
					site.scrapers = scrapers
					site.platformId = '0'					
					romCollection.scraperSites = []
					romCollection.scraperSites.append(site)
			else:
				
				if(romCollection.name == 'MAME'):
					romCollection.imagePlacing = ImagePlacing()
					romCollection.imagePlacing.name = 'gameinfomamecabinet'
					#MAME zip files contain several files but they must be passed to the emu as zip file
					romCollection.doNotExtractZipFiles = True
				
				
				romCollection.mediaPaths = []
				
				lastArtworkPath = ''
				while True:
					
					fileTypeIndex = dialog.select('Choose an artwork type', fileTypeList)
					Logutil.log('fileTypeIndex: ' +str(fileTypeIndex), util.LOG_LEVEL_INFO)					
					if(fileTypeIndex == -1):
						Logutil.log('No fileTypeIndex selected.', util.LOG_LEVEL_INFO)
						break
					
					fileType = fileTypeList[fileTypeIndex]
					fileTypeList.remove(fileType)
					
					if(lastArtworkPath == ''):					
						artworkPath = dialog.browse(0, '%s Artwork (%s)' %(console, fileType), 'files', '', False, False, romPath)
					else:
						artworkPath = dialog.browse(0, '%s Artwork (%s)' %(console, fileType), 'files', '', False, False, lastArtworkPath)
					lastArtworkPath = artworkPath
					Logutil.log('artworkPath: ' +str(artworkPath), util.LOG_LEVEL_INFO)
					if(artworkPath == ''):
						Logutil.log('No artworkPath selected.', util.LOG_LEVEL_INFO)
						break
					
					romCollection.mediaPaths.append(self.createMediaPath(fileType, artworkPath, scenarioIndex))
					
					retValue = dialog.yesno('Rom Collection Browser', 'Do you want to add another Artwork Path?')
					if(retValue == False):
						break
				
				descIndex = dialog.select('Structure of your game descriptions', ['One description file per game', 'One description file for all games', 'Scrape game info online'])
				Logutil.log('descIndex: ' +str(descIndex), util.LOG_LEVEL_INFO)
				if(descIndex == -1):
					Logutil.log('No descIndex selected. Action canceled.', util.LOG_LEVEL_INFO)
					break
				
				romCollection.descFilePerGame = (descIndex != 1)
				
				if(descIndex == 2):
					#leave scraperSites empty - they will be filled in configwriter
					pass
				
				else:
					descPath = dialog.browse(1, '%s game description' %console, 'files', '', False, False, lastArtworkPath)
					Logutil.log('descPath: ' +str(descPath), util.LOG_LEVEL_INFO)
					if(descPath == ''):
						Logutil.log('No descPath selected. Action canceled.', util.LOG_LEVEL_INFO)
						break
					
					parserPath = dialog.browse(1, '%s parse instruction' %console, 'files', '', False, False, descPath)
					Logutil.log('parserPath: ' +str(parserPath), util.LOG_LEVEL_INFO)
					if(parserPath == ''):
						Logutil.log('No parserPath selected. Action canceled.', util.LOG_LEVEL_INFO)
						break
					
					#create scraper
					site = Site()
					site.name = console
					site.descFilePerGame = (descIndex == 0)
					site.searchGameByCRC = True
					scrapers = []
					scraper = Scraper()
					scraper.parseInstruction = parserPath
					scraper.source = descPath
					scraper.encoding = 'iso-8859-1'
					scrapers.append(scraper)
					site.scrapers = scrapers
					site.platformId = '0'
					romCollection.scraperSites = []
					romCollection.scraperSites.append(site)
			
			romCollections[romCollection.id] = romCollection						
			
			retValue = dialog.yesno('Rom Collection Browser', 'Do you want to add another Rom Collection?')
			if(retValue == False):
				break
		
		del dialog
		
		return True, romCollections
	
	
	def createMediaPath(self, type, path, scenarioIndex):
		
		if(type == 'gameplay (video)'):
			type = 'gameplay'
			
		fileMask = '%GAME%.*'
		if(type == 'romcollection'):
			fileMask = '%ROMCOLLECTION%.*'
		if(type == 'developer'):
			fileMask = '%DEVELOPER%.*'
		if(type == 'publisher'):
			fileMask = '%PUBLISHER%.*'
		
		fileType = FileType()
		fileType.name = type
		
		mediaPath = MediaPath()
		mediaPath.fileType = fileType
		if(scenarioIndex == 0):
			mediaPath.path = os.path.join(path, type, fileMask)
		else:
			mediaPath.path = os.path.join(path, fileMask)
				
		return mediaPath
	
	
	def checkImport(self, doImport):
		
		#doImport: 0=nothing, 1=import Settings and Games, 2=import Settings only, 3=import games only
		if(doImport == 0):
			return
		
		#Show options dialog if user wants to see it
		#Import is started from dialog
		showImportOptionsDialog = self.Settings.getSetting(util.SETTING_RCB_SHOWIMPORTOPTIONSDIALOG).upper() == 'TRUE'
		if(showImportOptionsDialog):
			constructorParam = 1
			if(util.hasAddons()):
				constructorParam = "PAL"
			iod = dialogimportoptions.ImportOptionsDialog("script-RCB-importoptions.xml", util.getAddonInstallPath(), "Default", constructorParam, gui=self)
			del iod
		else:
						
			message = 'Do you want to import Games now?'		
		
			dialog = xbmcgui.Dialog()
			retGames = dialog.yesno('Rom Collection Browser', 'Import Games', message)
			if(retGames == True):
				
				scrapingMode = util.getScrapingMode(self.Settings)
				#Import Games
				self.doImport(scrapingMode, self.config.romCollections)
		
		
	def doImport(self, scrapingmode, romCollections):
		progressDialog = ProgressDialogGUI()
		progressDialog.writeMsg("Import games...", "", "")
		dbupdate.DBUpdate().updateDB(self.gdb, progressDialog, scrapingmode, romCollections)
		progressDialog.writeMsg("", "", "", -1)
		del progressDialog


	def checkUpdateInProgress(self):
		
		scrapeOnStartupAction = self.Settings.getSetting(util.SETTING_RCB_SCRAPEONSTARTUPACTION)
		if (scrapeOnStartupAction == 'update'):
			retCancel = xbmcgui.Dialog().yesno('Rom Collection Browser', 'Import in Progress', 'Do you want to cancel current import?')
			if(retCancel == True):
				self.Settings.setSetting(util.SETTING_RCB_SCRAPEONSTARTUPACTION, 'cancel')
			return True
		
		elif (scrapeOnStartupAction == 'cancel'):
			xbmcgui.Dialog().ok('Rom Collection Browser', 'Cancelling in Progress', 'Import is still being cancelled. Please try again later.')
			return True
		
		return False


	# Handle autoexec.py script to add/remove background scraping on startup
	def checkScrapStart(self):
		Logutil.log("Begin checkScrapStart" , util.LOG_LEVEL_INFO)
		
		autoexecFile = util.getAutoexecPath()
		path = os.path.join(util.RCBHOME, 'dbUpLauncher.py')
		if(util.getEnvironment() == 'win32'):
			#HACK: There is an error with "\a" in autoexec.py on winidows, so we need "\A"
			path = path.replace('\\addons', '\\Addons')
		launchLine = 'xbmc.executescript("%s")' % path
		try:
			fp = open(autoexecFile, 'r+')
		except:
			Logutil.log("Error opening autoexec.py" , util.LOG_LEVEL_WARNING)
			return
		xbmcImported = False
		alreadyCreated = False
		for line in fp:
			if line.startswith('import xbmc'):
				Logutil.log("import xbmc line found!" , util.LOG_LEVEL_INFO)
				xbmcImported = True
			if launchLine in line:
				Logutil.log("executescript line found!", util.LOG_LEVEL_INFO)
				alreadyCreated = True
				
		if self.Settings.getSetting(util.SETTING_RCB_SCRAPONSTART) == 'true':
			
			if not xbmcImported:
				Logutil.log("adding import xbmc line", util.LOG_LEVEL_INFO)
				fp.write('\nimport xbmc')
			if not alreadyCreated:
				Logutil.log("adding executescript line", util.LOG_LEVEL_INFO)
				fp.write('\n' + launchLine)
				
			fp.close()
		elif alreadyCreated:
			Logutil.log("Deleting executescript line" , util.LOG_LEVEL_INFO)
			if alreadyCreated:
				fp.seek(0)
				lines = fp.readlines()
				fp.close()
				os.remove(autoexecFile)
				fp = open(autoexecFile, 'w')
				for line in lines:
					if not path in line:
						fp.write(line)
				fp.close()
		Logutil.log("End checkScrapStart" , util.LOG_LEVEL_INFO)
				
				
	def checkAutoExec(self):
		Logutil.log("Begin checkAutoExec" , util.LOG_LEVEL_INFO)
		
		autoexec = util.getAutoexecPath()		
		Logutil.log("Checking path: " + autoexec, util.LOG_LEVEL_INFO)
		if (os.path.isfile(autoexec)):	
			lines = ""
			try:
				fh = fh = open(autoexec, "r")
				lines = fh.readlines()
				fh.close()
			except Exception, (exc):
				Logutil.log("Cannot access autoexec.py: " + str(exc), util.LOG_LEVEL_ERROR)
				return
				
			if(len(lines) > 0):
				firstLine = lines[0]
				#check if it is our autoexec
				if(firstLine.startswith('#Rom Collection Browser autoexec')):
					try:
						os.remove(autoexec)
					except Exception, (exc):
						Logutil.log("Cannot remove autoexec.py: " + str(exc), util.LOG_LEVEL_ERROR)
						return
				else:
					return
		else:
			Logutil.log("No autoexec.py found at given path.", util.LOG_LEVEL_INFO)
		
		rcbSetting = helper.getRCBSetting(self.gdb)
		if (rcbSetting == None):
			print "RCB_WARNING: rcbSetting == None in checkAutoExec"
			return
					
		#check if we have to restore autoexec backup 
		autoExecBackupPath = rcbSetting[util.RCBSETTING_autoexecBackupPath]
		if (autoExecBackupPath == None):
			return
			
		if (os.path.isfile(autoExecBackupPath)):
			try:
				os.rename(autoExecBackupPath, autoexec)
				os.remove(autoExecBackupPath)
			except Exception, (exc):
				Logutil.log("Cannot rename autoexec.py: " + str(exc), util.LOG_LEVEL_ERROR)
				return
			
		RCBSetting(self.gdb).update(('autoexecBackupPath',), (None,), rcbSetting[0])
		self.gdb.commit()
		
		Logutil.log("End checkAutoExec" , util.LOG_LEVEL_INFO)		
		
		
	def backupConfigXml(self):
		#backup config.xml for later use (will be overwritten in case of an addon update)
		configXml = util.getConfigXmlPath()
		configXmlBackup = os.path.join(util.getAddonDataPath(), 'config.xml.backup')
		
		if os.path.isfile(configXmlBackup):
			try:
				os.remove(configXmlBackup)
			except Exception, (exc):
				Logutil.log("Cannot remove config.xml backup: " +str(exc), util.LOG_LEVEL_ERROR)
				return
		
		try:
			shutil.copy(configXml, configXmlBackup)
		except Exception, (exc):
			Logutil.log("Cannot backup config.xml: " +str(exc), util.LOG_LEVEL_ERROR)
			return
		
		
	def saveViewState(self, isOnExit):
		
		Logutil.log("Begin saveViewState" , util.LOG_LEVEL_INFO)
		
		if(self.getListSize() == 0):
			Logutil.log("ListSize == 0 in saveViewState", util.LOG_LEVEL_WARNING)
			return
		
		selectedGameIndex = self.getCurrentListPosition()
		if(selectedGameIndex == -1):
			selectedGameIndex = 0
		if(selectedGameIndex == None):
			Logutil.log("selectedGameIndex == None in saveViewState", util.LOG_LEVEL_WARNING)
			return
		
		self.saveViewMode()
		
		helper.saveViewState(self.gdb, isOnExit, util.VIEW_MAINVIEW, selectedGameIndex, self.selectedConsoleIndex, self.selectedGenreIndex, self.selectedPublisherIndex,
			self.selectedYearIndex, self.selectedCharacterIndex, self.selectedControlId, None, self.Settings)
		
		Logutil.log("End saveViewState" , util.LOG_LEVEL_INFO)


	def saveViewMode(self):
		
		Logutil.log("Begin saveViewMode" , util.LOG_LEVEL_INFO)
		
		view_mode = ""
		for id in range(CONTROL_GAMES_GROUP_START, CONTROL_GAMES_GROUP_END + 1):
			try:			
				if xbmc.getCondVisibility("Control.IsVisible(%i)" % id):
					view_mode = repr(id)					
					break
			except:
				pass
				
		self.Settings.setSetting(util.SETTING_RCB_VIEW_MODE, view_mode)
		
		Logutil.log("End saveViewMode" , util.LOG_LEVEL_INFO)

	
	def loadViewState(self):
		
		Logutil.log("Begin loadViewState" , util.LOG_LEVEL_INFO)
		
		rcbSetting = helper.getRCBSetting(self.gdb)
		if(rcbSetting == None):			
			Logutil.log("rcbSetting == None in loadViewState", util.LOG_LEVEL_WARNING)
			focusControl = self.getControlById(CONTROL_BUTTON_UPDATEDB)
			self.setFocus(focusControl)
			return		
		
		#reset filter selection
		if(rcbSetting[util.RCBSETTING_lastSelectedConsoleIndex] != None):
			self.selectedConsoleId = int(self.setFilterSelection(CONTROL_CONSOLES, rcbSetting[util.RCBSETTING_lastSelectedConsoleIndex]))	
			self.selectedConsoleIndex = rcbSetting[util.RCBSETTING_lastSelectedConsoleIndex]
		if(rcbSetting[util.RCBSETTING_lastSelectedGenreIndex] != None):
			self.selectedGenreId = int(self.setFilterSelection(CONTROL_GENRE, rcbSetting[util.RCBSETTING_lastSelectedGenreIndex]))
			self.selectedGenreIndex = rcbSetting[util.RCBSETTING_lastSelectedGenreIndex]
		if(rcbSetting[util.RCBSETTING_lastSelectedPublisherIndex] != None):
			self.selectedPublisherId = int(self.setFilterSelection(CONTROL_PUBLISHER, rcbSetting[util.RCBSETTING_lastSelectedPublisherIndex]))
			self.selectedPublisherIndex = rcbSetting[util.RCBSETTING_lastSelectedPublisherIndex]
		if(rcbSetting[util.RCBSETTING_lastSelectedYearIndex] != None):
			self.selectedYearId = int(self.setFilterSelection(CONTROL_YEAR, rcbSetting[util.RCBSETTING_lastSelectedYearIndex]))
			self.selectedYearIndex = rcbSetting[util.RCBSETTING_lastSelectedYearIndex]
		if(rcbSetting[util.RCBSETTING_lastSelectedCharacterIndex] != None):
			self.selectedCharacter = self.setFilterSelection(CONTROL_CHARACTER, rcbSetting[util.RCBSETTING_lastSelectedCharacterIndex])
			self.selectedCharacterIndex = rcbSetting[util.RCBSETTING_lastSelectedCharacterIndex]		

		#reset view mode
		id = self.Settings.getSetting(util.SETTING_RCB_VIEW_MODE)
		if(id != None and id != ''):
			xbmc.executebuiltin("Container.SetViewMode(%i)" % int(id))

		#reset game list
		self.showGames()
		self.setFilterSelection(CONTROL_GAMES_GROUP_START, rcbSetting[util.RCBSETTING_lastSelectedGameIndex])
						
		#lastFocusedControl
		if(rcbSetting[util.RCBSETTING_lastFocusedControlMainView] != None):
			focusControl = self.getControlById(rcbSetting[util.RCBSETTING_lastFocusedControlMainView])
			if(focusControl == None):
				Logutil.log("focusControl == None in loadViewState", util.LOG_LEVEL_WARNING)
				return
			self.setFocus(focusControl)			
			if(CONTROL_GAMES_GROUP_START <= rcbSetting[util.RCBSETTING_lastFocusedControlMainView] <= CONTROL_GAMES_GROUP_END):
				self.showGameInfo()
		else:
			focusControl = self.getControlById(CONTROL_CONSOLES)
			if(focusControl == None):
				Logutil.log("focusControl == None (2) in loadViewState", util.LOG_LEVEL_WARNING)
				return
			self.setFocus(focusControl)					
		
		#lastSelectedView
		if(rcbSetting[util.RCBSETTING_lastSelectedView] == util.VIEW_GAMEINFOVIEW):
			self.showGameInfoDialog()
			
		Logutil.log("End loadViewState" , util.LOG_LEVEL_INFO)					

			
	def setFilterSelection(self, controlId, selectedIndex):
		
		Logutil.log("Begin setFilterSelection" , util.LOG_LEVEL_DEBUG)
		
		if(selectedIndex != None):
			control = self.getControlById(controlId)
			if(control == None):
				Logutil.log("control == None in setFilterSelection", util.LOG_LEVEL_WARNING)
				return 0
			
			if(controlId == CONTROL_GAMES_GROUP_START):
				if(self.getListSize() == 0):
					Logutil.log("ListSize == 0 in setFilterSelection", util.LOG_LEVEL_WARNING)
					return 0
				self.setCurrentListPosition(selectedIndex)
				#HACK: selectItem takes some time and we can't read selectedItem immediately
				xbmc.sleep(util.WAITTIME_UPDATECONTROLS)
				selectedItem = self.getListItem(selectedIndex)
				
			else:
				control.selectItem(selectedIndex)
				#HACK: selectItem takes some time and we can't read selectedItem immediately 
				xbmc.sleep(util.WAITTIME_UPDATECONTROLS)
				selectedItem = control.getSelectedItem()
				
			if(selectedItem == None):
				Logutil.log("End setFilterSelection" , util.LOG_LEVEL_DEBUG)
				return 0
			label2 = selectedItem.getLabel2()
			Logutil.log("End setFilterSelection" , util.LOG_LEVEL_DEBUG)
			return label2
		else:
			Logutil.log("End setFilterSelection" , util.LOG_LEVEL_DEBUG)
			return 0								
		
	
	def cacheItems(self):		
		Logutil.log("Begin cacheItems" , util.LOG_LEVEL_INFO)
		
		#cacheAll
		if(self.cachingOption == 0):
			fileRows = File(self.gdb).getAll()
			if(fileRows == None):
				Logutil.log("fileRows == None in cacheItems", util.LOG_LEVEL_WARNING)
				return
			self.fileDict = self.cacheFiles(fileRows)
		
		self.yearDict = self.cacheYears()
		
		self.publisherDict = self.cachePublishers()
		
		self.developerDict = self.cacheDevelopers()
		
		self.reviewerDict = self.cacheReviewers()
		
		#0 = cacheAll: load all game data at once
		if(self.cachingOption == 0):
			self.genreDict = self.cacheGenres()
		else:
			self.genreDict = None
		
		Logutil.log("End cacheItems" , util.LOG_LEVEL_INFO)
		
		
	def clearCache(self):
		Logutil.log("Begin clearCache" , util.LOG_LEVEL_INFO)
				
		self.fileDict = None		
		self.yearDict = None
		self.publisherDict = None
		self.developerDict = None
		self.reviewerDict = None
		self.genreDict = None
		
		Logutil.log("End clearCache" , util.LOG_LEVEL_INFO)
		

	def cacheFiles(self, fileRows):
		
		Logutil.log("Begin cacheFiles" , util.LOG_LEVEL_DEBUG)
		
		fileDict = {}
		for fileRow in fileRows:
			key = '%i;%i' % (fileRow[util.FILE_parentId] , fileRow[util.FILE_fileTypeId])
			item = None
			try:
				item = fileDict[key]
			except:
				pass
			if(item == None):
				fileRowList = []
				fileRowList.append(fileRow)
				fileDict[key] = fileRowList
			else:				
				fileRowList = fileDict[key]
				fileRowList.append(fileRow)
				fileDict[key] = fileRowList
				
		Logutil.log("End cacheFiles" , util.LOG_LEVEL_DEBUG)
		return fileDict
		
		
	def cacheYears(self):
		Logutil.log("Begin cacheYears" , util.LOG_LEVEL_DEBUG)
		yearRows = Year(self.gdb).getAll()
		if(yearRows == None):
			Logutil.log("yearRows == None in cacheYears", util.LOG_LEVEL_WARNING)
			return
		yearDict = {}
		for yearRow in yearRows:
			yearDict[yearRow[util.ROW_ID]] = yearRow
			
		Logutil.log("End cacheYears" , util.LOG_LEVEL_DEBUG)
		return yearDict
		
		
	def cacheReviewers(self):
		Logutil.log("Begin cacheReviewers" , util.LOG_LEVEL_DEBUG)
		reviewerRows = Reviewer(self.gdb).getAll()
		if(reviewerRows == None):
			Logutil.log("reviewerRows == None in cacheReviewers", util.LOG_LEVEL_WARNING)
			return
		reviewerDict = {}
		for reviewerRow in reviewerRows:
			reviewerDict[reviewerRow[util.ROW_ID]] = reviewerRow
			
		Logutil.log("End cacheReviewers" , util.LOG_LEVEL_DEBUG)
		return reviewerDict
		
	
	def cachePublishers(self):
		Logutil.log("Begin cachePublishers" , util.LOG_LEVEL_DEBUG)
		publisherRows = Publisher(self.gdb).getAll()
		if(publisherRows == None):
			Logutil.log("publisherRows == None in cachePublishers", util.LOG_LEVEL_WARNING)
			return
		publisherDict = {}
		for publisherRow in publisherRows:
			publisherDict[publisherRow[util.ROW_ID]] = publisherRow
			
		Logutil.log("End cachePublishers" , util.LOG_LEVEL_DEBUG)
		return publisherDict
		
		
	def cacheDevelopers(self):
		Logutil.log("Begin cacheDevelopers" , util.LOG_LEVEL_DEBUG)
		developerRows = Developer(self.gdb).getAll()
		if(developerRows == None):
			Logutil.log("developerRows == None in cacheDevelopers", util.LOG_LEVEL_WARNING)
			return
		developerDict = {}
		for developerRow in developerRows:
			developerDict[developerRow[util.ROW_ID]] = developerRow
			
		Logutil.log("End cacheDevelopers" , util.LOG_LEVEL_DEBUG)
		return developerDict
		
	
	def cacheGenres(self):
		
		Logutil.log("Begin cacheGenres" , util.LOG_LEVEL_DEBUG)
				
		genreGameRows = GenreGame(self.gdb).getAll()
		if(genreGameRows == None):
			Logutil.log("genreRows == None in cacheGenres", util.LOG_LEVEL_WARNING)
			return
		genreDict = {}
		for genreGameRow in genreGameRows:
			key = genreGameRow[util.GENREGAME_gameId]
			item = None
			try:
				item = genreDict[key]
				continue
			except:
				pass
				
			genreRows = Genre(self.gdb).getGenresByGameId(genreGameRow[util.GENREGAME_gameId])
			for i in range(0, len(genreRows)):
				if(i == 0):
					genres = genreRows[i][util.ROW_NAME]	
					genreDict[key] = genres
				else:				
					genres = genreDict[key]					
					genres = genres + ', ' + genreRows[i][util.ROW_NAME]					
					genreDict[key] = genres
				
		Logutil.log("End cacheGenres" , util.LOG_LEVEL_DEBUG)
		return genreDict
	
	
	def getControlById(self, controlId):
		try:
			control = self.getControl(controlId)
		except Exception, (exc):
			#HACK there seems to be a problem with recognizing the scrollbar controls
			if(controlId not in (CONTROL_SCROLLBARS)):
				Logutil.log("Control with id: %s could not be found. Check WindowXML file. Error: %s" % (str(controlId), str(exc)), util.LOG_LEVEL_ERROR)
				self.writeMsg("Control with id: %s could not be found. Check WindowXML file." % str(controlId))
			return None
		
		return control
	
	
	def writeMsg(self, msg, count=0):
		
		control = self.getControlById(CONTROL_LABEL_MSG)
		if(control == None):
			Logutil.log("RCB_WARNING: control == None in writeMsg", util.LOG_LEVEL_WARNING)
			return
		control.setLabel(msg)					
	
	
	def exit(self):				
		
		Logutil.log("exit" , util.LOG_LEVEL_INFO)
					
		self.saveViewState(True)
		
		if self.memDB:
			Logutil.log("Saving DB to disk", util.LOG_LEVEL_INFO)
			if self.gdb.toDisk():
				Logutil.log("Database saved ok!", util.LOG_LEVEL_INFO)
			else:
				Logutil.log("Failed to save database!", util.LOG_LEVEL_INFO)
				
		self.gdb.close()
		self.close()
		


def main():
	if(util.hasAddons()):
		ui = UIGameDB("script-Rom_Collection_Browser-main.xml", util.getAddonInstallPath(), "Default", "PAL")
		#ui = UIGameDB("script-Rom_Collection_Browser-main.xml", util.getAddonInstallPath(), "Light", "PAL")
	else:
		ui = UIGameDB("script-Rom_Collection_Browser-main.xml", util.getAddonInstallPath(), "Default", 1)
		#ui = UIGameDB("script-Rom_Collection_Browser-main.xml", util.getAddonInstallPath(), "Light", 1)
	ui.doModal()
	del ui

main()
