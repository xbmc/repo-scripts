
import os, sys, shutil
import xbmc, xbmcgui
import string, glob, time, array
import getpass, ntpath, re
from pysqlite2 import dbapi2 as sqlite

import dbupdate, importsettings
from gamedatabase import *
import helper, util
from util import *

from threading import *
from email.Message import Message


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


#ControlIds
CONTROL_CONSOLES = 500
CONTROL_GENRE = 600
CONTROL_YEAR = 700
CONTROL_PUBLISHER = 800
CONTROL_CHARACTER = 900
FILTER_CONTROLS = (500, 600, 700, 800, 900,)
GAME_LISTS = (50, 51, 52, 53, 54, 55, 56, 57, 58)
CONROL_SCROLLBARS = (2200, 2201,)

CONTROL_GAMES_GROUP_START = 50
CONTROL_GAMES_GROUP_END = 59
CONTROL_VIEW_NO_VIDEOS = (55, 56, 57, 58)

CONTROL_BUTTON_SETTINGS = 3000
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
			
	#cachingOption will be overwritten by db-config. Don't change it here.
	cachingOption = 3
	
	
	def __init__(self, strXMLname, strFallbackPath, strDefaultName, forceFallback):
		# Changing the three varibles passed won't change, anything
		# Doing strXMLname = "bah.xml" will not change anything.
		# don't put GUI sensitive stuff here (as the xml hasn't been read yet
		# Idea to initialize your variables here
		
		Logutil.log("Init Rom Collection Browser: " + util.RCBHOME, util.LOG_LEVEL_INFO)				
		
		self.Settings = util.getSettings()				
		
		
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
		
		self.quit = False
		if(doImport == -1):
			xbmcgui.Dialog().ok(util.SCRIPTNAME, errorMsg, 'Please start with a clean database.')			
			self.quit = True
		else:
			self.gdb.commit()
			self.checkImport(doImport)
			
			rcbSetting = helper.getRCBSetting(self.gdb)			
			if(rcbSetting != None):				
				self.cachingOption = rcbSetting[util.RCBSETTING_cachingOption]				
			
			self.cacheItems()
			
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
		self.checkAutoExec()		

		Logutil.log("End onInit", util.LOG_LEVEL_INFO)

	
	def onAction(self, action):
		
		#Hack: prevent being invoked twice
		onActionCurrentRun = time.clock()
		
		Logutil.log("onActionCurrentRun: %d ms" % (onActionCurrentRun * 1000), util.LOG_LEVEL_DEBUG)
		Logutil.log("onActionLastRun: %d ms" % (self.onActionLastRun * 1000), util.LOG_LEVEL_DEBUG)
		
		diff = (onActionCurrentRun - self.onActionLastRun) * 1000
		Logutil.log("diff: %d ms" % (diff), util.LOG_LEVEL_DEBUG)
		
		waitTime = util.WAITTIME_ONACTION
		if (os.environ.get("OS", "xbox") == "xbox"):
			waitTime = util.WAITTIME_ONACTION_XBOX
		
		if(int(diff) <= waitTime):
			Logutil.log("Last run still active. Do nothing.", util.LOG_LEVEL_DEBUG)
			self.onActionLastRun = time.clock()
			return
		
		self.onActionLastRun = time.clock()
							
		try:
			#print "action: " +str(action.getId())
			if(action.getId() in ACTION_CANCEL_DIALOG):
				Logutil.log("onAction: ACTION_CANCEL_DIALOG", util.LOG_LEVEL_DEBUG)
							
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
				
				if(action.getId() in ACTION_MOVEMENT_UP or action.getId() in ACTION_MOVEMENT_DOWN):	
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
		except Exception, (exc):
			print "RCB_ERROR: unhandled Error in onAction: " +str(exc)
			self.onActionLastRun = time.clock()
		
		self.onActionLastRun = time.clock()
			

	def onClick(self, controlId):
		
		Logutil.log("onClick: " + str(controlId), util.LOG_LEVEL_DEBUG)
		
		if (controlId == CONTROL_BUTTON_SETTINGS):
			Logutil.log("onClick: Import Settings", util.LOG_LEVEL_DEBUG)
			self.importSettings()
		elif (controlId == CONTROL_BUTTON_UPDATEDB):
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
		
		
	def updateControls(self):
		
		Logutil.log("Begin updateControls", util.LOG_LEVEL_DEBUG)
		
		#prepare FilterControls	
		self.showConsoles()		
		self.showGenre()		
		self.showYear()
		self.showPublisher()		
		self.showCharacterFilter()
		
		Logutil.log("End updateControls", util.LOG_LEVEL_DEBUG)
		
		
	def showConsoles(self):
		Logutil.log("Begin showConsoles" , util.LOG_LEVEL_DEBUG)
		rcbSetting = helper.getRCBSetting(self.gdb)
		if(rcbSetting == None):
			showEntryAllItems = 'True'
		else:
			showEntryAllItems = rcbSetting[util.RCBSETTING_showEntryAllConsoles]
		self.selectedConsoleId = self.showFilterControl(Console(self.gdb), CONTROL_CONSOLES, showEntryAllItems)
		
		Logutil.log("End showConsoles" , util.LOG_LEVEL_DEBUG)


	def showGenre(self):
		Logutil.log("Begin showGenre" , util.LOG_LEVEL_DEBUG)
		rcbSetting = helper.getRCBSetting(self.gdb)
		if(rcbSetting == None):
			showEntryAllItems = 'True'
		else:
			showEntryAllItems = rcbSetting[util.RCBSETTING_showEntryAllGenres]
		self.selectedGenreId = self.showFilterControl(Genre(self.gdb), CONTROL_GENRE, showEntryAllItems)
		
		Logutil.log("End showGenre" , util.LOG_LEVEL_DEBUG)
		
	
	def showYear(self):
		Logutil.log("Begin showYear" , util.LOG_LEVEL_DEBUG)
		rcbSetting = helper.getRCBSetting(self.gdb)
		if(rcbSetting == None):
			showEntryAllItems = 'True'
		else:
			showEntryAllItems = rcbSetting[util.RCBSETTING_showEntryAllYears]
		self.selectedYearId = self.showFilterControl(Year(self.gdb), CONTROL_YEAR, showEntryAllItems)
		Logutil.log("End showYear" , util.LOG_LEVEL_DEBUG)
		
		
	def showPublisher(self):
		Logutil.log("Begin showPublisher" , util.LOG_LEVEL_DEBUG)
		rcbSetting = helper.getRCBSetting(self.gdb)
		if(rcbSetting == None):
			showEntryAllItems = 'True'
		else:
			showEntryAllItems = rcbSetting[util.RCBSETTING_showEntryAllPublisher]
		self.selectedPublisherId = self.showFilterControl(Publisher(self.gdb), CONTROL_PUBLISHER, showEntryAllItems)
		
		Logutil.log("End showPublisher" , util.LOG_LEVEL_DEBUG)


	def showFilterControl(self, dbo, controlId, showEntryAllItems):
		
		Logutil.log("begin showFilterControl: " + str(controlId), util.LOG_LEVEL_DEBUG)
				
		rows = dbo.getAllOrdered()
		
		control = self.getControlById(controlId)
		if(control == None):
			Logutil.log("control == None in showFilterControl", util.LOG_LEVEL_WARNING)
			return
		
		control.setVisible(1)
		control.reset()
		
		items = []
		if(showEntryAllItems == 'True'):
			items.append(xbmcgui.ListItem("All", "0", "", ""))
		
		for row in rows:
			items.append(xbmcgui.ListItem(str(row[util.ROW_NAME]), str(row[util.ROW_ID]), "", ""))
			
		control.addItems(items)
			
		label2 = str(control.getSelectedItem().getLabel2())
		return int(label2)		
		
		Logutil.log("End showFilterControl", util.LOG_LEVEL_DEBUG)
			
	
	def showCharacterFilter(self):
		Logutil.log("Begin showCharacterFilter" , util.LOG_LEVEL_DEBUG)
		
		control = self.getControlById(CONTROL_CHARACTER)
		
		if(control == None):
			Logutil.log("control == None in showFilterControl", util.LOG_LEVEL_WARNING)
			return
			
		control.reset()
		
		rcbSetting = helper.getRCBSetting(self.gdb)
		if(rcbSetting == None):
			showEntryAllItems = 'True'
		else:
			showEntryAllItems = rcbSetting[util.RCBSETTING_showEntryAllChars]
		
		items = []		
		if(showEntryAllItems == 'True'):
			items.append(xbmcgui.ListItem("All", "All", "", ""))
		items.append(xbmcgui.ListItem("0-9", "0-9", "", ""))
		
		for i in range(0, 26):
			char = chr(ord('A') + i)
			items.append(xbmcgui.ListItem(char, char, "", ""))
			
		control.addItems(items)
		Logutil.log("End showCharacterFilter" , util.LOG_LEVEL_DEBUG)
		

	def showGames(self):
		Logutil.log("Begin showGames" , util.LOG_LEVEL_INFO)
		
		rcbSetting = helper.getRCBSetting(self.gdb)
		if(rcbSetting == None):
			preventUnfilteredSearch = 'False'
		else:
			preventUnfilteredSearch = rcbSetting[util.RCBSETTING_preventUnfilteredSearch]
		
		if(preventUnfilteredSearch == 'True'):			
			if(self.selectedCharacter == 'All' and self.selectedConsoleId == 0 and self.selectedGenreId == 0 and self.selectedYearId == 0 and self.selectedPublisherId == 0):
				Logutil.log("preventing unfiltered search", util.LOG_LEVEL_WARNING)
				return				
		
		# build statement for character search (where name LIKE 'A%')
		likeStatement = helper.buildLikeStatement(self.selectedCharacter)
		games = Game(self.gdb).getFilteredGames(self.selectedConsoleId, self.selectedGenreId, self.selectedYearId, self.selectedPublisherId, likeStatement)
		
		if(games == None):
			Logutil.log("games == None in showGames", util.LOG_LEVEL_WARNING)
			return		
		
		fileDict = self.getFileDictForGamelist()

		self.writeMsg("loading games...")
		
		#timestamp1 = time.clock()
		xbmcgui.lock()
		
		self.clearList()
		self.rcb_playList.clear()		
		
		count = 0
		for gameRow in games:			
		
			#images for gamelist
			imageGameList = self.getFileForControl(util.IMAGE_CONTROL_MV_GAMELIST, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
			imageGameListSelected = self.getFileForControl(util.IMAGE_CONTROL_MV_GAMELISTSELECTED, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)												
			
			#create ListItem
			item = xbmcgui.ListItem(str(gameRow[util.ROW_NAME]), str(gameRow[util.ROW_ID]), imageGameList, imageGameListSelected)			
			item.setProperty('gameId', str(gameRow[util.ROW_ID]))
						
			#0 = cacheAll: load all game data at once
			if(self.cachingOption == 0):
				self.setAllItemData(item, gameRow, self.fileDict)							
			
			self.addItem(item, False)
			
			# add video to playlist for fullscreen support
			self.addFullscreenVideoToPlaylist(gameRow, imageGameList, imageGameListSelected, count, fileDict)
				
			count = count + 1
				
			
		xbmc.executebuiltin("Container.SortDirection")
		xbmcgui.unlock()				
		
		self.writeMsg("")
		
		#timestamp2 = time.clock()
		#diff = (timestamp2 - timestamp1) * 1000		
		#print "load %i games in %d ms" % (self.getListSize(), diff)		
		
		Logutil.log("End showGames" , util.LOG_LEVEL_INFO)		
	
	
	def showGameInfo(self):
		Logutil.log("Begin showGameInfo" , util.LOG_LEVEL_INFO)		
		
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
			
		self.loadVideoFiles(self.gdb, gameRow, selectedGame)
		
		#gameinfos are already loaded with cachingOption 0 (cacheAll)
		if(self.cachingOption > 0):
			self.loadGameInfos(self.gdb, gameRow, selectedGame, pos)
				
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
		
		helper.launchEmu(self.gdb, self, gameId)
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
		
	
	def importSettings(self):
		Logutil.log("Begin importSettings" , util.LOG_LEVEL_INFO)				
		
		self.clearList()
		self.clearCache()
		self.checkImport(2)
		self.cacheItems()
		self.updateControls()			
		
		Logutil.log("End importSettings" , util.LOG_LEVEL_INFO)
		
		
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
		if(util.isPostCamelot()):
			constructorParam = "PAL"		
		
		import gameinfodialog
		gid = gameinfodialog.UIGameInfoView("script-Rom_Collection_Browser-gameinfo.xml", os.getcwd(), "Default", constructorParam, gdb=self.gdb, gameId=gameId,
			consoleId=self.selectedConsoleId, genreId=self.selectedGenreId, yearId=self.selectedYearId, publisherId=self.selectedPublisherId, selectedGameIndex=selectedGameIndex,
			consoleIndex=self.selectedConsoleIndex, genreIndex=self.selectedGenreIndex, yearIndex=self.selectedYearIndex, publisherIndex=self.selectedPublisherIndex,
			selectedCharacter=self.selectedCharacter, selectedCharacterIndex=self.selectedCharacterIndex, controlIdMainView=self.selectedControlId, fileTypeForControlDict=self.fileTypeForControlDict, fileTypeDict=self.fileTypeDict,
			fileDict=fileDict, romCollectionDict=self.romCollectionDict)
		del gid
		
		self.gameinfoDialogOpen = False
				
		
		self.setFocus(self.getControl(CONTROL_GAMES_GROUP_START))
		self.showGames()
		self.setCurrentListPosition(selectedGameIndex)
		xbmc.sleep(util.WAITTIME_UPDATECONTROLS)
		self.showGameInfo()
		
		Logutil.log("End showGameInfoDialog", util.LOG_LEVEL_INFO)
		
		
		
		
	"""
	******************
	* HELPER METHODS *
	******************
	"""
	
	
	def getFileDictForGamelist(self):
		# 0 = cacheAll
		if(self.cachingOption == 0):
			fileDict = self.fileDict
		else:
			fileRows = File(self.gdb).getFilesForGamelist()
			if(fileRows == None):
				Logutil.log("fileRows == None in showGames", util.LOG_LEVEL_WARNING)
				return
					
			fileDict = self.cacheFiles(fileRows)
		
		return fileDict
		
		
	def getFileForControl(self, controlName, gameId, publisherId, developerId, romCollectionId, fileDict):
		files = helper.getFilesByControl_Cached(self.gdb, controlName, gameId, publisherId, developerId, romCollectionId, self.fileTypeForControlDict, self.fileTypeDict, fileDict, self.romCollectionDict)		
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
	
		
	def addFullscreenVideoToPlaylist(self, gameRow, imageGameList, imageGameListSelected, count, fileDict):
		#create dummy ListItem for playlist
		dummyItem = xbmcgui.ListItem(str(gameRow[util.ROW_NAME]), str(gameRow[util.ROW_ID]), imageGameList, imageGameListSelected)
		
		videosFullscreen = helper.getFilesByControl_Cached(self.gdb, util.VIDEO_CONTROL_MV_VideoFullscreen, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId],
			self.fileTypeForControlDict, self.fileTypeDict, fileDict, self.romCollectionDict)
		
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
		Logutil.log("size = %i" % self.getListSize(), util.LOG_LEVEL_INFO)
		Logutil.log("pos = %s" % pos, util.LOG_LEVEL_INFO)
		
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


	def loadVideoFiles(self, gdb, gameRow, selectedGame):				
		
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
			videosFullscreen = helper.getFilesByControl_Cached(self.gdb, util.VIDEO_CONTROL_MV_VideoFullscreen, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId],
				self.fileTypeForControlDict, self.fileTypeDict, fileDict, self.romCollectionDict)				
			if(videosFullscreen != None and len(videosFullscreen) != 0):				
				selectedGame.setProperty('mainviewvideofullscreen', 'fullscreen')
				
		
			video = ""			
			
			videosBig = helper.getFilesByControl_Cached(self.gdb, util.VIDEO_CONTROL_MV_VideoWindowBig, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId],
				self.fileTypeForControlDict, self.fileTypeDict, fileDict, self.romCollectionDict)			
			
			if(videosBig != None and len(videosBig) != 0):
				video = videosBig[0]				
				selectedGame.setProperty('mainviewvideosizebig', 'big')				
				
			else:
				videosSmall = helper.getFilesByControl_Cached(self.gdb, util.VIDEO_CONTROL_MV_VideoWindowSmall, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId],
					self.fileTypeForControlDict, self.fileTypeDict, fileDict, self.romCollectionDict)				
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
		
		
	def loadGameInfos(self, gdb, gameRow, selectedGame, pos):
		Logutil.log("begin loadGameInfos", util.LOG_LEVEL_DEBUG)
		Logutil.log("gameRow = " +str(gameRow), util.LOG_LEVEL_DEBUG)
		
		if(self.getListSize() == 0):
			Logutil.log("ListSize == 0 in loadGameInfos", util.LOG_LEVEL_WARNING)
			return
		
		# > 1: cacheItem, cacheItemAndNext 
		if(self.cachingOption > 1):				
			fileDict = self.getFileDictByGameRow(gdb, gameRow)
			self.setAllItemData(selectedGame, gameRow, fileDict)

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
			self.setAllItemData(selectedGame, gameRow, fileDict)
			
			posAfter = pos + 1
			if(posAfter >= self.getListSize()):
				posAfter = 0
							
			selectedGame, gameRow = self.getGameByPosition(gdb, posAfter)
			if(selectedGame == None or gameRow == None):
				return
			fileDict = self.getFileDictByGameRow(gdb, gameRow)
			self.setAllItemData(selectedGame, gameRow, fileDict)
			
		Logutil.log("end loadGameInfos", util.LOG_LEVEL_DEBUG)

	
	def getFileDictByGameRow(self, gdb, gameRow):
		romCollectionRow = self.romCollectionDict[gameRow[util.GAME_romCollectionId]]
		if(romCollectionRow == None):
			Logutil.log("romCollectionRow == None in getFilesByControl", util.LOG_LEVEL_DEBUG)
			return
		consoleId = romCollectionRow[2]
		
		files = File(gdb).getFilesByParentIds(gameRow[util.ROW_ID], gameRow[util.GAME_romCollectionId], consoleId, gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId])
				
		fileDict = self.cacheFiles(files)
		
		return fileDict
		
		
	def setAllItemData(self, item, gameRow, fileDict):				
				
		# all other images in mainwindow
		imagemainViewBackground = self.getFileForControl(util.IMAGE_CONTROL_MV_BACKGROUND, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
		imageGameInfoBig = self.getFileForControl(util.IMAGE_CONTROL_MV_GAMEINFO_BIG, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
		imageGameInfoUpperLeft = self.getFileForControl(util.IMAGE_CONTROL_MV_GAMEINFO_UPPERLEFT, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
		imageGameInfoUpperRight = self.getFileForControl(util.IMAGE_CONTROL_MV_GAMEINFO_UPPERRIGHT, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
		imageGameInfoLowerLeft = self.getFileForControl(util.IMAGE_CONTROL_MV_GAMEINFO_LOWERLEFT, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
		imageGameInfoLowerRight = self.getFileForControl(util.IMAGE_CONTROL_MV_GAMEINFO_LOWERRIGHT, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
		imageMainView1 = self.getFileForControl(util.IMAGE_CONTROL_MV_1, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
		imageMainView2 = self.getFileForControl(util.IMAGE_CONTROL_MV_2, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
		imageMainView3 = self.getFileForControl(util.IMAGE_CONTROL_MV_3, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)		
		
		#set images as properties for use in the skin
		item.setProperty(util.IMAGE_CONTROL_MV_BACKGROUND, imagemainViewBackground)
		item.setProperty(util.IMAGE_CONTROL_MV_GAMEINFO_BIG, imageGameInfoBig)
		item.setProperty(util.IMAGE_CONTROL_MV_GAMEINFO_UPPERLEFT, imageGameInfoUpperLeft)
		item.setProperty(util.IMAGE_CONTROL_MV_GAMEINFO_UPPERRIGHT, imageGameInfoUpperRight)
		item.setProperty(util.IMAGE_CONTROL_MV_GAMEINFO_LOWERLEFT, imageGameInfoLowerLeft)
		item.setProperty(util.IMAGE_CONTROL_MV_GAMEINFO_LOWERRIGHT, imageGameInfoLowerRight)
		item.setProperty(util.IMAGE_CONTROL_MV_1, imageMainView1)
		item.setProperty(util.IMAGE_CONTROL_MV_2, imageMainView2)
		item.setProperty(util.IMAGE_CONTROL_MV_3, imageMainView3)
		
		
		#set additional properties
		description = gameRow[util.GAME_description]
		if(description == None):
			description = ""			
		item.setProperty(util.TEXT_CONTROL_MV_GAMEDESC, description)
		
		try:
			romCollectionRow = self.romCollectionDict[gameRow[util.GAME_romCollectionId]]
			item.setProperty('romcollection', romCollectionRow[util.ROW_NAME])
			consoleRow = self.consoleDict[romCollectionRow[util.ROMCOLLECTION_consoleId]]
			item.setProperty(util.GAMEPROPERTY_Console, consoleRow[util.ROW_NAME])
			
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
	
	
	def checkImport(self, doImport):				
		
		if(doImport == 0):
			#check file modification time of config.xml			
			modifyTime = util.getConfigXmlModifyTime()
			rcbSetting = helper.getRCBSetting(self.gdb)
			if (rcbSetting == None):
				print "RCB_WARNING: rcbSetting == None in checkImport"
				return
			lastConfigChange = rcbSetting[24]
			Logutil.log("lastConfigChange from DB (as int): " +str(lastConfigChange), util.LOG_LEVEL_INFO)
			Logutil.log("lastConfigChange from DB (as time): " +str(time.ctime(lastConfigChange)), util.LOG_LEVEL_INFO)
			if (modifyTime != lastConfigChange):
				importSuccessful = self.doImportSettings('config.xml has changed since last import.')
				if(not importSuccessful):
					return
		
		#doImport: 0=nothing, 1=import Settings and Games, 2=import Settings only, 3=import games only
		elif(doImport in (1, 2)):			
			if(doImport == 1):
				importSuccessful = self.doImportSettings('Database is empty.')
			else:
				importSuccessful = self.doImportSettings('')								

			if(importSuccessful and doImport == 1):
				dialog = xbmcgui.Dialog()
				retGames = dialog.yesno('Rom Collection Browser', 'Import Settings successful', 'Do you want to import Games now?')
				if(retGames == True):
					progressDialog = ProgressDialogGUI()
					progressDialog.writeMsg("Import games...", "", "")
					dbupdate.DBUpdate().updateDB(self.gdb, progressDialog)
					progressDialog.writeMsg("", "", "", -1)
					del progressDialog
						
		elif(doImport == 3):
			dialog = xbmcgui.Dialog()
			retGames = dialog.yesno('Rom Collection Browser', 'Import Games', 'Do you want to import Games now?')
			if(retGames == True):
				progressDialog = ProgressDialogGUI()
				progressDialog.writeMsg("Import games...", "", "")
				dbupdate.DBUpdate().updateDB(self.gdb, progressDialog)
				progressDialog.writeMsg("", "", "", -1)
				del progressDialog
				
				
	def doImportSettings(self, message):
		dialog = xbmcgui.Dialog()
		retSettings = dialog.yesno('Rom Collection Browser', message, 'Do you want to import Settings now?')
		if(retSettings == True):
			progressDialog = ProgressDialogGUI()
			progressDialog.writeMsg("Import settings...", "", "")				
			importSuccessful, errorMsg = importsettings.SettingsImporter().importSettings(self.gdb, progressDialog)
			# XBMC crashes on my Linux system without this line:
			print('RCB INFO: Import done')
			progressDialog.writeMsg("", "", "", -1)
			del progressDialog
			
			if (not importSuccessful):
				xbmcgui.Dialog().ok(util.SCRIPTNAME, errorMsg, 'See xbmc.log for details.')
				return False
			self.backupConfigXml()
			
			#reset log level
			Logutil.currentLogLevel = None
			return True

			
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
		autoExecBackupPath = rcbSetting[9]
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
			self.selectedYearIndex, self.selectedCharacterIndex, self.selectedControlId, None)
		
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
			focusControl = self.getControlById(CONTROL_BUTTON_SETTINGS)
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
		
		self. fileTypeForControlDict = self.cacheFileTypesForControl()
				
		self. fileTypeDict = self.cacheFileTypes()
		
		#cacheAll
		if(self.cachingOption == 0):
			fileRows = File(self.gdb).getAll()
			if(fileRows == None):
				Logutil.log("fileRows == None in cacheItems", util.LOG_LEVEL_WARNING)
				return
			self.fileDict = self.cacheFiles(fileRows)
		
		self.consoleDict = self.cacheConsoles()
		
		self.romCollectionDict = self.cacheRomCollections()
		
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
		
		self. fileTypeForControlDict = None				
		self. fileTypeDict = None				
		self.fileDict = None		
		self.consoleDict = None		
		self.romCollectionDict = None		
		self.yearDict = None		
		self.publisherDict = None		
		self.developerDict = None		
		self.reviewerDict = None		
		self.genreDict = None
		
		Logutil.log("End clearCache" , util.LOG_LEVEL_INFO)
	
	
	def cacheFileTypesForControl(self):
		
		Logutil.log("Begin cacheFileTypesForControl" , util.LOG_LEVEL_DEBUG)
		
		fileTypeForControlRows = FileTypeForControl(self.gdb).getAll()		
		if(fileTypeForControlRows == None):
			Logutil.log("fileTypeForControlRows == None in cacheFileTypesForControl", util.LOG_LEVEL_WARNING)
			return None
		
		fileTypeForControlDict = {}
		for fileTypeForControlRow in fileTypeForControlRows:
			key = '%i;%s' % (fileTypeForControlRow[util.FILETYPEFORCONTROL_romCollectionId], fileTypeForControlRow[util.FILETYPEFORCONTROL_control])
			item = None
			try:
				item = fileTypeForControlDict[key]
			except:
				pass			
			if(item == None):				
				fileTypeForControlRowList = []
				fileTypeForControlRowList.append(fileTypeForControlRow)
				fileTypeForControlDict[key] = fileTypeForControlRowList
			else:				
				fileTypeForControlRowList = fileTypeForControlDict[key]
				fileTypeForControlRowList.append(fileTypeForControlRow)
				fileTypeForControlDict[key] = fileTypeForControlRowList
		
		Logutil.log("End cacheFileTypesForControl" , util.LOG_LEVEL_DEBUG)
		return fileTypeForControlDict
		
		
	def cacheFileTypes(self):
		Logutil.log("Begin cacheFileTypes" , util.LOG_LEVEL_DEBUG)
		fileTypeRows = FileType(self.gdb).getAll()
		if(fileTypeRows == None):
			Logutil.log("fileTypeRows == None in cacheFileTypes", util.LOG_LEVEL_WARNING)
			return
		fileTypeDict = {}
		for fileTypeRow in fileTypeRows:
			fileTypeDict[fileTypeRow[util.ROW_ID]] = fileTypeRow
			
		Logutil.log("End cacheFileTypes" , util.LOG_LEVEL_DEBUG)
		return fileTypeDict
		

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
		
	
	def cacheRomCollections(self):
		Logutil.log("Begin cacheRomCollections" , util.LOG_LEVEL_DEBUG)
		
		romCollectionRows = RomCollection(self.gdb).getAll()
		if(romCollectionRows == None):
			Logutil.log("romCollectionRows == None in cacheRomCollections", util.LOG_LEVEL_WARNING)
			return
		romCollectionDict = {}
		for romCollectionRow in romCollectionRows:
			romCollectionDict[romCollectionRow[util.ROW_ID]] = romCollectionRow
			
		Logutil.log("End cacheRomCollections" , util.LOG_LEVEL_DEBUG)
		return romCollectionDict
	
		
	def cacheConsoles(self):
		Logutil.log("Begin cacheConsoles" , util.LOG_LEVEL_DEBUG)
		
		consoleRows = Console(self.gdb).getAll()
		if(consoleRows == None):
			Logutil.log("consoleRows == None in cacheConsoles", util.LOG_LEVEL_WARNING)
			return
		consoleDict = {}
		for consoleRow in consoleRows:
			consoleDict[consoleRow[util.ROW_ID]] = consoleRow
			
		Logutil.log("End cacheConsoles" , util.LOG_LEVEL_DEBUG)
		return consoleDict
		
		
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
		except: 
			#HACK there seems to be a problem with recognizing the scrollbar controls
			if(controlId not in (CONROL_SCROLLBARS)):
				Logutil.log("Control with id: %s could not be found. Check WindowXML file." % str(controlId), util.LOG_LEVEL_ERROR)
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
		
		self.gdb.close()
		self.close()
		


def main():
	if(util.isPostCamelot()):
		ui = UIGameDB("script-Rom_Collection_Browser-main.xml", os.getcwd(), "Default", "PAL")
	else:
		ui = UIGameDB("script-Rom_Collection_Browser-main.xml", os.getcwd(), "Default", 1)
	ui.doModal()
	del ui

main()
