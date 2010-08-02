
import os, sys

import string, glob, xbmc, xbmcgui, xbmcaddon
import getpass, ntpath, re, time
from xml.dom.minidom import Document, parseString
from pysqlite2 import dbapi2 as sqlite
import shutil

import dbupdate, importsettings
from gamedatabase import *
import helper, util


#__language__ = xbmc.Language( os.getcwd() ).getLocalizedString

#Action Codes
# See guilib/Key.h
ACTION_EXIT_SCRIPT = ( 10, )
ACTION_CANCEL_DIALOG = ACTION_EXIT_SCRIPT + ( 9, )
ACTION_MOVEMENT_LEFT = ( 1, )
ACTION_MOVEMENT_RIGHT = ( 2, )
ACTION_MOVEMENT_UP = ( 3, )
ACTION_MOVEMENT_DOWN = ( 4, )
ACTION_MOVEMENT = ( 1, 2, 3, 4, )
ACTION_INFO = ( 11, )


#ControlIds
CONTROL_CONSOLES = 500
CONTROL_GENRE = 600
CONTROL_YEAR = 700
CONTROL_PUBLISHER = 800
FILTER_CONTROLS = (500, 600, 700, 800,)
GAME_LISTS = (50, 51, 52, 53,)
CONROL_SCROLLBARS = (2200, 2201,)

CONTROL_IMG_BACK = 75

CONTROL_GAMES_GROUP = 200
CONTROL_GAMES_GROUP_START = 50
CONTROL_GAMES_GROUP_END = 59
CONTROL_THUMBS_VIEW = 51
CONTROL_CONSOLE_IMG = 2000
CONTROL_CONSOLE_DESC = 2100
CONTROL_BUTTON_SETTINGS = 3000
CONTROL_BUTTON_UPDATEDB = 3100
CONTROL_BUTTON_CHANGE_VIEW = 2

CONTROL_LABEL_MSG = 4000

RCBHOME = os.getcwd()


class MyPlayer(xbmc.Player):
	
	gui = None	
	
	def onPlayBackStarted(self):		
		self.gui.saveViewState(True)
	
	def onPlayBackEnded(self):
		xbmc.sleep(1000)
		
		self.gui.loadViewState()



class ProgressDialogGUI:		
	
	def __init__(self):
		self.itemCount = 0
		self.dialog = xbmcgui.DialogProgress()		
			
	def writeMsg(self, message, count=0):
		if ( not count ):
			self.dialog.create(message)
		elif ( count > 0 ):
			percent = int( count * ( float( 100 ) / self.itemCount))
			__line1__ = "%s" % (message, )
			self.dialog.update( percent, __line1__ )
			if ( self.dialog.iscanceled() ): 
				return False
			else: 
				return True
		else:
			self.dialog.close()


class UIGameDB(xbmcgui.WindowXML):	

	databaseDir = util.getAddonDataPath()
	gdb = GameDataBase(databaseDir)
	
	selectedControlId = 0
	selectedConsoleId = 0
	selectedGenreId = 0
	selectedYearId = 0
	selectedPublisherId = 0
	
	selectedConsoleIndex = 0
	selectedGenreIndex = 0
	selectedYearIndex = 0
	selectedPublisherIndex = 0	
	
	currentView = ''
	
	currentlyPlayingItem = None
	currentlyPlayingVideo = None
	
	#dummy to be compatible with ProgressDialogGUI
	itemCount = 0
	
	def __init__(self,strXMLname, strFallbackPath, strDefaultName, forceFallback):
		# Changing the three varibles passed won't change, anything
		# Doing strXMLname = "bah.xml" will not change anything.
		# don't put GUI sensitive stuff here (as the xml hasn't been read yet
		# Idea to initialize your variables here
		
		util.log("Init Rom Collection Browser: " +RCBHOME, util.LOG_LEVEL_INFO)
		
		if not os.path.exists(self.databaseDir):
			try:
				os.makedirs(self.databaseDir)
			except:
				xbmcgui.Dialog().ok(util.SCRIPTNAME, 'Cannot write to ' +self.databaseDir, 'RCB Error')
				self.quit = True
				return
		
		self.isInit = True
				
		self.Settings = xbmcaddon.Addon(id='script.games.rom.collection.browser')
		#self.Settings = xbmc.Settings(RCBHOME)
		
		self.gdb.connect()
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
			
			self.cacheItems()
			
			self.player = MyPlayer()
			self.player.gui = self
		
		
	def onInit(self):
		
		util.log("Begin onInit", util.LOG_LEVEL_INFO)
		
		if(self.quit):			
			self.close()
			return
		
		#init only once
		if(not self.isInit):
			return
			
		self.isInit = False
		
		self.updateControls()
		self.loadViewState()
		self.checkAutoExec()

		util.log("End onInit", util.LOG_LEVEL_INFO)			

	
	def onAction(self, action):		
		if(action.getId() in ACTION_CANCEL_DIALOG):
			util.log("onAction: ACTION_CANCEL_DIALOG", util.LOG_LEVEL_DEBUG)
						
			if(self.player.isPlayingVideo()):
				self.player.stop()
			
			self.exit()
		elif(action.getId() in ACTION_MOVEMENT_UP or action.getId() in ACTION_MOVEMENT_DOWN):
			
			util.log("onAction: ACTION_MOVEMENT_UP / ACTION_MOVEMENT_DOWN", util.LOG_LEVEL_DEBUG)
			
			control = self.getControlById(self.selectedControlId)
			if(control == None):
				util.log("control == None in onAction", util.LOG_LEVEL_WARNING)
				return
				
			if(CONTROL_GAMES_GROUP_START <= self.selectedControlId <= CONTROL_GAMES_GROUP_END):				
				self.showGameInfo()
			
			elif(self.selectedControlId in FILTER_CONTROLS):								
				
				label = str(control.getSelectedItem().getLabel())
				label2 = str(control.getSelectedItem().getLabel2())
					
				filterChanged = False
				
				if (self.selectedControlId == CONTROL_CONSOLES):
					if(self.selectedConsoleIndex != control.getSelectedPosition()):
						self.selectedConsoleId = int(label2)
						self.selectedConsoleIndex = control.getSelectedPosition()
						filterChanged = True
					
					"""
					#consoleId 0 = Entry "All"					
					if (self.selectedConsoleId == 0):
						pass
						#self.getControl(CONTROL_CONSOLE_IMG).setVisible(0)
						#self.getControl(CONTROL_CONSOLE_DESC).setVisible(0)
					else:
						self.showConsoleInfo()
					"""
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
				if(filterChanged):					
					self.showGames()								
				
		elif(action.getId() in ACTION_MOVEMENT_LEFT or action.getId() in ACTION_MOVEMENT_RIGHT):
			util.log("onAction: ACTION_MOVEMENT_LEFT / ACTION_MOVEMENT_RIGHT", util.LOG_LEVEL_DEBUG)
			
			control = self.getControlById(self.selectedControlId)
			if(control == None):
				util.log("control == None in onAction", util.LOG_LEVEL_WARNING)
				return
				
			if(CONTROL_GAMES_GROUP_START <= self.selectedControlId <= CONTROL_GAMES_GROUP_END):
				self.showGameInfo()
		elif(action.getId() in ACTION_INFO):
			util.log("onAction: ACTION_INFO", util.LOG_LEVEL_DEBUG)
			
			control = self.getControlById(self.selectedControlId)
			if(control == None):
				util.log("control == None in onAction", util.LOG_LEVEL_WARNING)
				return
			if(CONTROL_GAMES_GROUP_START <= self.selectedControlId <= CONTROL_GAMES_GROUP_END):
				self.showGameInfoDialog()



	def onClick(self, controlId):
		
		util.log("onClick: " +str(controlId), util.LOG_LEVEL_DEBUG)
		
		if (controlId == CONTROL_BUTTON_SETTINGS):
			util.log("onClick: Import Settings", util.LOG_LEVEL_DEBUG)
			self.importSettings()
		elif (controlId == CONTROL_BUTTON_UPDATEDB):
			util.log("onClick: Update DB", util.LOG_LEVEL_DEBUG)
			self.updateDB()		
		elif (controlId in FILTER_CONTROLS):
			util.log("onClick: Show Game Info", util.LOG_LEVEL_DEBUG)
			self.setFocus(self.getControl(CONTROL_GAMES_GROUP_START))
			self.showGameInfo()
		elif (controlId in GAME_LISTS):
			util.log("onClick: Launch Emu", util.LOG_LEVEL_DEBUG)
			self.launchEmu()		


	def onFocus(self, controlId):
		util.log("onFocus: " +str(controlId), util.LOG_LEVEL_DEBUG)
		self.selectedControlId = controlId
		
		
	def updateControls(self):
		
		util.log("Begin updateControls", util.LOG_LEVEL_DEBUG)
		
		#prepare FilterControls	
		self.showConsoles()		
		self.showGenre()		
		self.showYear()
		self.showPublisher()		
		
		util.log("End updateControls", util.LOG_LEVEL_DEBUG)
		
		
	def showConsoles(self):
		util.log("Begin showConsoles" , util.LOG_LEVEL_DEBUG)
		rcbSetting = helper.getRCBSetting(self.gdb)
		if(rcbSetting == None):
			showEntryAllItems = 'True'
		else:
			showEntryAllItems = rcbSetting[util.RCBSETTING_showEntryAllConsoles]
		self.selectedConsoleId = self.showFilterControl(Console(self.gdb), CONTROL_CONSOLES, showEntryAllItems)
		
		util.log("End showConsoles" , util.LOG_LEVEL_DEBUG)


	def showGenre(self):
		util.log("Begin showGenre" , util.LOG_LEVEL_DEBUG)
		rcbSetting = helper.getRCBSetting(self.gdb)
		if(rcbSetting == None):
			showEntryAllItems = 'True'
		else:
			showEntryAllItems = rcbSetting[util.RCBSETTING_showEntryAllGenres]
		self.selectedGenreId = self.showFilterControl(Genre(self.gdb), CONTROL_GENRE, showEntryAllItems)
		
		util.log("End showGenre" , util.LOG_LEVEL_DEBUG)
		
	
	def showYear(self):
		util.log("Begin showYear" , util.LOG_LEVEL_DEBUG)
		rcbSetting = helper.getRCBSetting(self.gdb)
		if(rcbSetting == None):
			showEntryAllItems = 'True'
		else:
			showEntryAllItems = rcbSetting[util.RCBSETTING_showEntryAllYears]
		self.selectedYearId = self.showFilterControl(Year(self.gdb), CONTROL_YEAR, showEntryAllItems)
		util.log("End showYear" , util.LOG_LEVEL_DEBUG)
		
		
	def showPublisher(self):
		util.log("Begin showPublisher" , util.LOG_LEVEL_DEBUG)
		rcbSetting = helper.getRCBSetting(self.gdb)
		if(rcbSetting == None):
			showEntryAllItems = 'True'
		else:
			showEntryAllItems = rcbSetting[util.RCBSETTING_showEntryAllPublisher]
		self.selectedPublisherId = self.showFilterControl(Publisher(self.gdb), CONTROL_PUBLISHER, showEntryAllItems)
		
		util.log("End showPublisher" , util.LOG_LEVEL_DEBUG)


	def showFilterControl(self, dbo, controlId, showEntryAllItems):
		
		util.log("begin showFilterControl: " +str(controlId), util.LOG_LEVEL_DEBUG)
		
		#xbmcgui.lock()
		rows = dbo.getAllOrdered()
		
		control = self.getControlById(controlId)
		if(control == None):
			util.log("control == None in showFilterControl", util.LOG_LEVEL_WARNING)
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
		#xbmcgui.unlock
		
		util.log("End showFilterControl", util.LOG_LEVEL_DEBUG)
		

	def showGames(self):
		util.log("Begin showGames" , util.LOG_LEVEL_INFO)
		
		games = Game(self.gdb).getFilteredGames(self.selectedConsoleId, self.selectedGenreId, self.selectedYearId, self.selectedPublisherId)		
		
		self.writeMsg("loading games...")
		
		#timestamp1 = time.clock()
		xbmcgui.lock()				
		
		self.clearList()			
		
		for game in games:			
			
			images = helper.getFilesByControl_Cached(self.gdb, util.IMAGE_CONTROL_MV_GAMELIST, game[util.ROW_ID], game[util.GAME_publisherId], game[util.GAME_developerId], game[util.GAME_romCollectionId],
				self.fileTypeForControlDict, self.fileTypeDict, self.fileDict, self.romCollectionDict)
			if(images != None and len(images) != 0):
				image = images[0]
			else:
				image = ""
			
			
			selectedImages = helper.getFilesByControl_Cached(self.gdb, util.IMAGE_CONTROL_MV_GAMELISTSELECTED, game[util.ROW_ID], game[util.GAME_publisherId], game[util.GAME_developerId], game[util.GAME_romCollectionId],
				self.fileTypeForControlDict, self.fileTypeDict, self.fileDict, self.romCollectionDict)
			if(selectedImages != None and len(selectedImages) != 0):
				selectedImage = selectedImages[0]
			else:
				selectedImage = ""			
			
			item = xbmcgui.ListItem(str(game[util.ROW_NAME]), str(game[util.ROW_ID]), image, selectedImage)
			
			#set additional properties
			try:
				romCollectionRow = self.romCollectionDict[game[util.GAME_romCollectionId]]
				consoleRow = self.consoleDict[romCollectionRow[util.ROMCOLLECTION_consoleId]]
				item.setProperty(util.GAMEPROPERTY_Console, consoleRow[util.ROW_NAME])
			except:
				pass
			
			self.addItem(item, False)
			
		xbmcgui.unlock()				
		
		self.writeMsg("")
		
		#timestamp2 = time.clock()
		#diff = (timestamp2 - timestamp1) * 1000		
		#print "load games in %d ms" %diff
		
		
		util.log("End showGames" , util.LOG_LEVEL_INFO)	
	

	"""
	#TODO no console info atm
	def showConsoleInfo(self):	
		util.log("Begin showConsoleInfo" , util.LOG_LEVEL_DEBUG)
		
		if(self.getListSize() == 0):
			util.log("ListSize == 0 in showGameInfo", util.LOG_LEVEL_WARNING)
			return
		
		pos = self.getCurrentListPosition()
		if(pos == -1):
			pos = 0
		selectedGame = self.getListItem(pos)
		if(selectedGame == None):
			util.log("selectedGame == None in showGameInfo", util.LOG_LEVEL_WARNING)
			return
		
		consoleRow = Console(self.gdb).getObjectById(self.selectedConsoleId)
		
		if(consoleRow == None):
			util.log("consoleRow == None in showConsoleInfo", util.LOG_LEVEL_WARNING)
			return
					
		image = consoleRow[3]		
		description = consoleRow[2]		
				
		selectedGame.setProperty('mainviewgameinfo', image)
		selectedGame.setProperty('gamedesc', description)		
		
		util.log("End showConsoleInfo" , util.LOG_LEVEL_DEBUG)
	"""
		
	
	def showGameInfo(self):
		util.log("Begin showGameInfo" , util.LOG_LEVEL_DEBUG)
		
		if(self.getListSize() == 0):
			util.log("ListSize == 0 in showGameInfo", util.LOG_LEVEL_WARNING)
			return
			
		#stop video (if playing)
		if(self.player.isPlayingVideo()):
			self.player.stop()
					
		pos = self.getCurrentListPosition()
		if(pos == -1):
			pos = 0
		selectedGame = self.getListItem(pos)
		if(selectedGame == None):
			util.log("selectedGame == None in showGameInfo", util.LOG_LEVEL_WARNING)
			return
			
		gameId = selectedGame.getLabel2()				
		gameRow = Game(self.gdb).getObjectById(gameId)
		
		if(gameRow == None):
			util.log("gameId = %s" %gameId, util.LOG_LEVEL_DEBUG)
			util.log("gameRow == None in showGameInfo", util.LOG_LEVEL_WARNING)
			return
			
		bgimages = helper.getFilesByControl_Cached(self.gdb, util.IMAGE_CONTROL_MV_BACKGROUND, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId],
			self.fileTypeForControlDict, self.fileTypeDict, self.fileDict, self.romCollectionDict)
		if(bgimages != None and len(bgimages) != 0):
			bgimage = bgimages[0]
		else:
			bgimage = os.path.join(RCBHOME, 'resources', 'skins', 'Default', 'media', 'rcb-background-black.png')		
		controlBg = self.getControlById(CONTROL_IMG_BACK)
		controlBg.setImage(bgimage)

		imageGameInfoBig = self.getFileForControl(util.IMAGE_CONTROL_MV_GAMEINFO_BIG, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId])
		imageGameInfoUpperLeft = self.getFileForControl(util.IMAGE_CONTROL_MV_GAMEINFO_UPPERLEFT, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId])
		imageGameInfoUpperRight = self.getFileForControl(util.IMAGE_CONTROL_MV_GAMEINFO_UPPERRIGHT, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId])
		imageGameInfoLowerLeft = self.getFileForControl(util.IMAGE_CONTROL_MV_GAMEINFO_LOWERLEFT, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId])
		imageGameInfoLowerRight = self.getFileForControl(util.IMAGE_CONTROL_MV_GAMEINFO_LOWERRIGHT, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId])
		imageMainView1 = self.getFileForControl(util.IMAGE_CONTROL_MV_1, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId])
		imageMainView2 = self.getFileForControl(util.IMAGE_CONTROL_MV_2, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId])
		imageMainView3 = self.getFileForControl(util.IMAGE_CONTROL_MV_3, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId])
		
		selectedGame.setProperty(util.IMAGE_CONTROL_MV_GAMEINFO_BIG, imageGameInfoBig)
		selectedGame.setProperty(util.IMAGE_CONTROL_MV_GAMEINFO_UPPERLEFT, imageGameInfoUpperLeft)
		selectedGame.setProperty(util.IMAGE_CONTROL_MV_GAMEINFO_UPPERRIGHT, imageGameInfoUpperRight)
		selectedGame.setProperty(util.IMAGE_CONTROL_MV_GAMEINFO_LOWERLEFT, imageGameInfoLowerLeft)
		selectedGame.setProperty(util.IMAGE_CONTROL_MV_GAMEINFO_LOWERRIGHT, imageGameInfoLowerRight)
		selectedGame.setProperty(util.IMAGE_CONTROL_MV_1, imageMainView1)		
		selectedGame.setProperty(util.IMAGE_CONTROL_MV_2, imageMainView2)
		selectedGame.setProperty(util.IMAGE_CONTROL_MV_3, imageMainView3)
		
		description = gameRow[util.GAME_description]
		if(description == None):
			description = ""
		
		selectedGame.setProperty(util.TEXT_CONTROL_MV_GAMEDESC, description)
				
		#no video in thumbs view
		if (not xbmc.getCondVisibility( "Control.IsVisible(%i)" % CONTROL_THUMBS_VIEW )):
		
			videosBig = helper.getFilesByControl_Cached(self.gdb, util.VIDEO_CONTROL_MV_VideoWindowBig, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId],
				self.fileTypeForControlDict, self.fileTypeDict, self.fileDict, self.romCollectionDict)
			
			if(videosBig != None and len(videosBig) != 0):
				video = videosBig[0]
				
				selectedGame.setProperty('mainviewvideosizebig', 'big')								
				
				self.player.play(video, selectedGame, True)
			else:
				videosSmall = helper.getFilesByControl_Cached(self.gdb, util.VIDEO_CONTROL_MV_VideoWindowSmall, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId],
					self.fileTypeForControlDict, self.fileTypeDict, self.fileDict, self.romCollectionDict)
				if(videosSmall != None and len(videosSmall) != 0):
					video = videosSmall[0]
					
					selectedGame.setProperty('mainviewvideosizesmall', 'small')										
					
					self.player.play(video, selectedGame, True)
		
		util.log("End showGameInfo" , util.LOG_LEVEL_DEBUG)
		
		
	def getFileForControl(self, controlName, gameId, publisherId, developerId, romCollectionId):
		files = helper.getFilesByControl_Cached(self.gdb, controlName, gameId, publisherId, developerId, romCollectionId, self.fileTypeForControlDict, self.fileTypeDict, self.fileDict, self.romCollectionDict)
		if(files != None and len(files) != 0):
			file = files[0]
		else:
			file = ""
			
		return file


	def launchEmu(self):

		util.log("Begin launchEmu" , util.LOG_LEVEL_INFO)

		if(self.getListSize() == 0):
			util.log("ListSize == 0 in launchEmu", util.LOG_LEVEL_WARNING)
			return

		pos = self.getCurrentListPosition()
		if(pos == -1):
			pos = 0
		selectedGame = self.getListItem(pos)
		
		if(selectedGame == None):
			util.log("selectedGame == None in launchEmu", util.LOG_LEVEL_WARNING)
			return
			
		gameId = selectedGame.getLabel2()
		util.log("launching game with id: " +str(gameId), util.LOG_LEVEL_INFO)
		
		helper.launchEmu(self.gdb, self, gameId)
		util.log("End launchEmu" , util.LOG_LEVEL_INFO)
		
		
	def updateDB(self):
		util.log("Begin updateDB" , util.LOG_LEVEL_INFO)
		
		dbupdate.DBUpdate().updateDB(self.gdb, self)
		self.updateControls()
		util.log("End updateDB" , util.LOG_LEVEL_INFO)
		
	
	def importSettings(self):
		util.log("Begin importSettings" , util.LOG_LEVEL_INFO)
		
		databaseDir = os.path.join(RCBHOME, 'resources', 'database')
		importSuccessful, errorMsg = importsettings.SettingsImporter().importSettings(self.gdb, databaseDir, self)
		if(not importSuccessful):
			self.writeMsg(errorMsg +' See xbmc.log for details.')
		else:
			self.cacheItems()
			self.updateControls()
			
			self.backupConfigXml(databaseDir)
			
		util.log("End importSettings" , util.LOG_LEVEL_INFO)
		
		
	def showGameInfoDialog(self):

		util.log("Begin showGameInfoDialog", util.LOG_LEVEL_INFO)
		
		if(self.getListSize() == 0):
			util.log("ListSize == 0 in saveViewState", util.LOG_LEVEL_WARNING)
			return
		
		selectedGameIndex = self.getCurrentListPosition()		
		if(selectedGameIndex == -1):
			selectedGameIndex = 0
		selectedGame = self.getListItem(selectedGameIndex)		
		if(selectedGame == None):
			util.log("selectedGame == None in showGameInfoDialog", util.LOG_LEVEL_WARNING)
			return
		gameId = selectedGame.getLabel2()
		
		self.saveViewMode()
		
		import gameinfodialog
		gid = gameinfodialog.UIGameInfoView("script-Rom_Collection_Browser-gameinfo.xml", os.getcwd(), "Default", 1, gdb=self.gdb, gameId=gameId, 
			consoleId=self.selectedConsoleId, genreId=self.selectedGenreId, yearId=self.selectedYearId, publisherId=self.selectedPublisherId, selectedGameIndex=selectedGameIndex,
			consoleIndex=self.selectedConsoleIndex, genreIndex=self.selectedGenreIndex, yearIndex=self.selectedYearIndex, publisherIndex=self.selectedPublisherIndex, 
			controlIdMainView=self.selectedControlId, fileTypeForControlDict=self.fileTypeForControlDict, fileTypeDict=self.fileTypeDict, fileDict=self.fileDict, romCollectionDict=self.romCollectionDict)
		del gid
				
		
		self.setFocus(self.getControl(CONTROL_GAMES_GROUP_START))
		self.showGames()
		self.setCurrentListPosition(selectedGameIndex)
		self.showGameInfo()
		
		util.log("End showGameInfoDialog", util.LOG_LEVEL_INFO)
	
	
	def checkImport(self, doImport):
		#doImport: 0=nothing, 1=import Settings and Games, 2=import Settings only
		if(doImport in (1,2)):
			dialog = xbmcgui.Dialog()
			retSettings = dialog.yesno('Rom Collection Browser', 'Database is empty.', 'Do you want to import Settings now?')
			del dialog
			if(retSettings == True):
				progressDialog = ProgressDialogGUI()
				progressDialog.writeMsg("Import settings...")
				importSuccessful, errorMsg = importsettings.SettingsImporter().importSettings(self.gdb, os.path.join(RCBHOME, 'resources', 'database'), progressDialog)
				# XBMC crashes on my Linux system without this line:
				print('RCB INFO: Import done')
				progressDialog.writeMsg("", -1)
				del progressDialog
				
				#TODO 2nd chance
				if (not importSuccessful):
					xbmcgui.Dialog().ok(util.SCRIPTNAME, errorMsg, 'See xbmc.log for details.')

				self.backupConfigXml(os.path.join(RCBHOME, 'resources', 'database'))
				
				if(importSuccessful and doImport == 1):
					dialog = xbmcgui.Dialog()
					retGames = dialog.yesno('Rom Collection Browser', 'Import Settings successful', 'Do you want to import Games now?')
					if(retGames == True):
						progressDialog = ProgressDialogGUI()
						progressDialog.writeMsg("Import games...")
						dbupdate.DBUpdate().updateDB(self.gdb, progressDialog)
						progressDialog.writeMsg("", -1)
						del progressDialog
						
	
	
	def backupConfigXml(self, databaseDir):
		#backup config.xml for later use (will be overwritten in case of an addon update)
		configXml = os.path.join(databaseDir, 'config.xml')
		configXmlBackup = os.path.join(util.getAddonDataPath(), 'config.xml.backup')
		
		if os.path.isfile(configXmlBackup):
			try:
				os.remove(configXmlBackup)
			except Exception, (exc):
				util.log("Cannot remove config.xml backup: " +str(exc), util.LOG_LEVEL_ERROR)
				return
		
		try:
			shutil.copy(configXml, configXmlBackup)
		except Exception, (exc):
			util.log("Cannot backup config.xml: " +str(exc), util.LOG_LEVEL_ERROR)
			return

			
	def checkAutoExec(self):
		util.log("Begin checkAutoExec" , util.LOG_LEVEL_INFO)
				
		autoexec = util.getAutoexecPath()
		if (os.path.isfile(autoexec)):	
			lines = ""
			try:
				fh = fh=open(autoexec,"r")
				lines = fh.readlines()
				fh.close()
			except Exception, (exc):
				util.log("Cannot access autoexec.py: " +str(exc), util.LOG_LEVEL_ERROR)
				return
				
			if(len(lines) > 0):
				firstLine = lines[0]
				#check if it is our autoexec
				if(firstLine.startswith('#Rom Collection Browser autoexec')):
					try:
						os.remove(autoexec)
					except Exception, (exc):
						util.log("Cannot remove autoexec.py: " +str(exc), util.LOG_LEVEL_ERROR)
						return
				else:
					return
		
		rcbSetting = helper.getRCBSetting(self.gdb)
		if (rcbSetting == None):
			print "RCB_WARNING: rcbSetting == None in checkAutoExec"
			return
					
		autoExecBackupPath = rcbSetting[9]
		if (autoExecBackupPath == None):
			return
			
		if (os.path.isfile(autoExecBackupPath)):
			try:
				os.rename(autoExecBackupPath, autoexec)
				os.remove(autoExecBackupPath)
			except Exception, (exc):
				util.log("Cannot rename autoexec.py: " +str(exc), util.LOG_LEVEL_ERROR)
				return
			
		RCBSetting(self.gdb).update(('autoexecBackupPath',), (None,), rcbSetting[0])
		self.gdb.commit()
		
		util.log("End checkAutoExec" , util.LOG_LEVEL_INFO)		
		
		
	def saveViewState(self, isOnExit):
		
		util.log("Begin saveViewState" , util.LOG_LEVEL_INFO)
		
		if(self.getListSize() == 0):
			util.log("ListSize == 0 in saveViewState", util.LOG_LEVEL_WARNING)
			return
		
		selectedGameIndex = self.getCurrentListPosition()
		if(selectedGameIndex == -1):
			selectedGameIndex = 0
		if(selectedGameIndex == None):
			util.log("selectedGameIndex == None in saveViewState", util.LOG_LEVEL_WARNING)
			return
		
		self.saveViewMode()
		
		helper.saveViewState(self.gdb, isOnExit, util.VIEW_MAINVIEW, selectedGameIndex, self.selectedConsoleIndex, self.selectedGenreIndex, self.selectedPublisherIndex, 
			self.selectedYearIndex, self.selectedControlId, None)
		
		util.log("End saveViewState" , util.LOG_LEVEL_INFO)


	def saveViewMode(self):
		
		util.log("Begin saveViewMode" , util.LOG_LEVEL_INFO)
		
		view_mode = ""
		for id in range( CONTROL_GAMES_GROUP_START, CONTROL_GAMES_GROUP_END + 1 ):
			try:			
				if xbmc.getCondVisibility( "Control.IsVisible(%i)" % id ):
					view_mode = repr( id )					
					break
			except:
				pass
				
		self.Settings.setSetting( util.SETTING_RCB_VIEW_MODE, view_mode)
		
		util.log("End saveViewMode" , util.LOG_LEVEL_INFO)

	
	def loadViewState(self):
		
		util.log("Begin loadViewState" , util.LOG_LEVEL_INFO)
		
		rcbSetting = helper.getRCBSetting(self.gdb)
		if(rcbSetting == None):			
			util.log("rcbSetting == None in loadViewState", util.LOG_LEVEL_WARNING)
			focusControl = self.getControlById(CONTROL_BUTTON_SETTINGS)
			self.setFocus(focusControl)
			return		
		
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

		self.showGames()
		self.setFilterSelection(CONTROL_GAMES_GROUP_START, rcbSetting[util.RCBSETTING_lastSelectedGameIndex])
						
		#lastFocusedControl
		if(rcbSetting[util.RCBSETTING_lastFocusedControlMainView] != None):
			focusControl = self.getControlById(rcbSetting[util.RCBSETTING_lastFocusedControlMainView])
			if(focusControl == None):
				util.log("focusControl == None in loadViewState", util.LOG_LEVEL_WARNING)
				return
			self.setFocus(focusControl)
			"""
			if(rcbSetting[util.RCBSETTING_lastFocusedControlMainView] == CONTROL_CONSOLES):
				self.showConsoleInfo()
			"""
			if(CONTROL_GAMES_GROUP_START <= rcbSetting[util.RCBSETTING_lastFocusedControlMainView] <= CONTROL_GAMES_GROUP_END):
				self.showGameInfo()
		else:
			focusControl = self.getControlById(CONTROL_CONSOLES)
			if(focusControl == None):
				util.log("focusControl == None (2) in loadViewState", util.LOG_LEVEL_WARNING)
				return
			self.setFocus(focusControl)		
		
		id = self.Settings.getSetting( util.SETTING_RCB_VIEW_MODE)
		xbmc.executebuiltin( "Container.SetViewMode(%i)" % int(id) )		
		
		#lastSelectedView
		if(rcbSetting[util.RCBSETTING_lastSelectedView] == util.VIEW_GAMEINFOVIEW):
			self.showGameInfoDialog()
			
		util.log("End loadViewState" , util.LOG_LEVEL_INFO)
			
			
			
	def setFilterSelection(self, controlId, selectedIndex):
		
		util.log("Begin setFilterSelection" , util.LOG_LEVEL_DEBUG)
		
		if(selectedIndex != None):
			control = self.getControlById(controlId)
			if(control == None):
				util.log("control == None in setFilterSelection", util.LOG_LEVEL_WARNING)
				return
			
			if(controlId == CONTROL_GAMES_GROUP_START):
				self.setCurrentListPosition(selectedIndex)
				selectedItem = self.getListItem(selectedIndex)
				
			else:
				control.selectItem(selectedIndex)
				selectedItem = control.getSelectedItem()
				
			if(selectedItem == None):
				util.log("End setFilterSelection" , util.LOG_LEVEL_DEBUG)
				return 0
			label2 = selectedItem.getLabel2()
			util.log("End setFilterSelection" , util.LOG_LEVEL_DEBUG)
			return label2
		else:
			util.log("End setFilterSelection" , util.LOG_LEVEL_DEBUG)
			return 0					
	
	
	def cacheItems(self):
		
		util.log("Begin cacheItems" , util.LOG_LEVEL_DEBUG)
		
		self. fileTypeForControlDict = self.cacheFileTypesForControl()
				
		self. fileTypeDict = self.cacheFileTypes()
				
		self.fileDict = self.cacheFiles()
		
		self.consoleDict = self.cacheConsoles()
		
		self.romCollectionDict = self.cacheRomCollections()
		
		util.log("End cacheItems" , util.LOG_LEVEL_DEBUG)
	
	
	def cacheFileTypesForControl(self):
		
		util.log("Begin cacheFileTypesForControl" , util.LOG_LEVEL_DEBUG)
		
		fileTypeForControlRows = FileTypeForControl(self.gdb).getAll()		
		if(fileTypeForControlRows == None):
			util.log("fileTypeForControlRows == None", util.LOG_LEVEL_WARNING)
			return None
		
		fileTypeForControlDict = {}
		for fileTypeForControlRow in fileTypeForControlRows:
			key = '%i;%s' %(fileTypeForControlRow[util.FILETYPEFORCONTROL_romCollectionId] , fileTypeForControlRow[util.FILETYPEFORCONTROL_control])
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
		
		util.log("End cacheFileTypesForControl" , util.LOG_LEVEL_DEBUG)
		return fileTypeForControlDict
		
		
	def cacheFileTypes(self):
		util.log("Begin cacheFileTypes" , util.LOG_LEVEL_DEBUG)
		fileTypeRows = FileType(self.gdb).getAll()
		if(fileTypeRows == None):
			util.log("fileTypeRows == None in getFilesByControl", util.LOG_LEVEL_WARNING)
			return
		fileTypeDict = {}
		for fileTypeRow in fileTypeRows:
			fileTypeDict[fileTypeRow[util.ROW_ID]] = fileTypeRow
			
		util.log("End cacheFileTypes" , util.LOG_LEVEL_DEBUG)
		return fileTypeDict
		
		
	def cacheFiles(self):
		
		util.log("Begin cacheFiles" , util.LOG_LEVEL_DEBUG)
		
		#TODO ignore non-media files
		fileRows = File(self.gdb).getAll()
		if(fileRows == None):
			util.log("fileRows == None in cacheFiles", util.LOG_LEVEL_WARNING)
			return
		fileDict = {}
		for fileRow in fileRows:
			key = '%i;%i' %(fileRow[util.FILE_parentId] , fileRow[util.FILE_fileTypeId])			
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
				
		util.log("End cacheFiles" , util.LOG_LEVEL_DEBUG)
		return fileDict
		
	
	def cacheRomCollections(self):
		util.log("Begin cacheRomCollections" , util.LOG_LEVEL_DEBUG)
		
		romCollectionRows = RomCollection(self.gdb).getAll()
		if(romCollectionRows == None):
			util.log("romCollectionRows == None in cacheRomCollections", util.LOG_LEVEL_WARNING)
			return
		romCollectionDict = {}
		for romCollectionRow in romCollectionRows:
			romCollectionDict[romCollectionRow[util.ROW_ID]] = romCollectionRow
			
		util.log("End cacheRomCollections" , util.LOG_LEVEL_DEBUG)
		return romCollectionDict
	
		
	def cacheConsoles(self):
		util.log("Begin cacheConsoles" , util.LOG_LEVEL_DEBUG)
		
		consoleRows = Console(self.gdb).getAll()
		if(consoleRows == None):
			util.log("consoleRows == None in cacheConsoles", util.LOG_LEVEL_WARNING)
			return
		consoleDict = {}
		for consoleRow in consoleRows:
			consoleDict[consoleRow[util.ROW_ID]] = consoleRow
			
		util.log("End cacheConsoles" , util.LOG_LEVEL_DEBUG)
		return consoleDict
	
	
	def getControlById(self, controlId):
		try:
			control = self.getControl(controlId)
		except: 
			#HACK there seems to be a problem with recognizing the scrollbar controls
			if(controlId not in (CONROL_SCROLLBARS)):
				util.log("Control with id: %s could not be found. Check WindowXML file." %str(controlId), util.LOG_LEVEL_ERROR)
				self.writeMsg("Control with id: %s could not be found. Check WindowXML file." %str(controlId))
			return None
		
		return control
	
	
	def writeMsg(self, msg, count=0):
		control = self.getControlById(CONTROL_LABEL_MSG)
		if(control == None):
			util.log("RCB_WARNING: control == None in writeMsg", util.LOG_LEVEL_WARNING)
			return
		control.setLabel(msg)
	
	
	def exit(self):				
		
		util.log("exit" , util.LOG_LEVEL_INFO)
		
		self.saveViewState(True)
		
		self.gdb.close()
		self.close()
		


def main():    
    ui = UIGameDB("script-Rom_Collection_Browser-main.xml", os.getcwd(), "Default", 1)    
    ui.doModal()
    del ui

main()