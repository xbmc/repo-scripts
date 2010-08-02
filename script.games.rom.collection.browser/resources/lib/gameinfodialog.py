
import os, sys
import xbmc, xbmcgui
import dbupdate, importsettings
from gamedatabase import *
import helper, util


ACTION_EXIT_SCRIPT = ( 10, )
ACTION_CANCEL_DIALOG = ACTION_EXIT_SCRIPT + ( 9, )
ACTION_MOVEMENT_LEFT = ( 1, )
ACTION_MOVEMENT_RIGHT = ( 2, )
ACTION_MOVEMENT_UP = ( 3, )
ACTION_MOVEMENT_DOWN = ( 4, )
ACTION_MOVEMENT = ( 1, 2, 3, 4, )

CONTROL_BUTTON_PLAYGAME = 3000

CONTROL_GAME_LIST_GROUP = 1000
CONTROL_GAME_LIST = 59
CONTROL_IMG_BACK = 2000

CONTROL_LABEL_MSG = 4000

CONTROL_LABEL_GENRE = 6100
CONTROL_LABEL_YEAR = 6200
CONTROL_LABEL_PUBLISHER = 6300
CONTROL_LABEL_DEVELOPER = 6400
CONTROL_LABEL_REGION = 6500
CONTROL_LABEL_MEDIA = 6600
CONTROL_LABEL_CONTROLLER = 6700
CONTROL_LABEL_RATING = 6800
CONTROL_LABEL_VOTES = 6900
CONTROL_LABEL_PLAYERS = 7000
CONTROL_LABEL_PERSPECTIVE = 7100
CONTROL_LABEL_REVIEWER = 7200
CONTROL_LABEL_URL = 7300
CONTROL_LABEL_LAUNCHCOUNT = 7400
CONTROL_LABEL_TRANSLATED = 7500
CONTROL_LABEL_ORIGTITLE= 7600
CONTROL_LABEL_ALTERNATETITLE = 7700
CONTROL_LABEL_VERSION = 7800

CONTROL_LABEL_DESC = 8000

CONTROL_IMG_GAMEINFO1 = 9000
CONTROL_IMG_GAMEINFO2 = 9100
CONTROL_IMG_GAMEINFO3 = 9200
CONTROL_IMG_GAMEINFO4 = 9300

RCBHOME = os.getcwd()


class UIGameInfoView(xbmcgui.WindowXMLDialog):
	def __init__(self, *args, **kwargs):		
		xbmcgui.WindowXMLDialog.__init__( self, *args, **kwargs )		
		
		util.log("Init GameInfoView", util.LOG_LEVEL_INFO)
		
		self.gdb = kwargs[ "gdb" ]
		self.selectedGameId = kwargs[ "gameId" ]		
		self.selectedConsoleId = kwargs[ "consoleId" ]		
		self.selectedGenreId = kwargs[ "genreId" ]				
		self.selectedYearId = kwargs[ "yearId" ]		
		self.selectedPublisherId = kwargs[ "publisherId" ]
		self.selectedConsoleIndex = kwargs[ "consoleIndex" ]
		self.selectedGenreIndex = kwargs[ "genreIndex" ]		
		self.selectedYearIndex = kwargs[ "yearIndex" ]		
		self.selectedPublisherIndex = kwargs[ "publisherIndex" ]
		self.selectedGameIndex = kwargs[ "selectedGameIndex" ]		
		self.selectedControlIdMainView = kwargs["controlIdMainView"]
		self.fileTypeForControlDict = kwargs["fileTypeForControlDict"]
		self.fileTypeDict = kwargs["fileTypeDict"]
		self.fileDict = kwargs["fileDict"]
		self.romCollectionDict = kwargs["romCollectionDict"]
		
		self.doModal()
		
		
	def onInit(self):
		
		util.log("Begin OnInit", util.LOG_LEVEL_DEBUG)
		
		self.showGameList()
		self.showGameInfo()
		
		control = self.getControlById(CONTROL_GAME_LIST_GROUP)
		if(control == None):
			return
			
		self.setFocus(control)
		self.selectedControlId = CONTROL_GAME_LIST_GROUP
		self.setCurrentListPosition(self.selectedGameIndex)	
		
		util.log("End OnInit", util.LOG_LEVEL_DEBUG)
		
		
		
	def onClick( self, controlId ):
		util.log("Begin onClick", util.LOG_LEVEL_DEBUG)
		
		if (controlId == CONTROL_BUTTON_PLAYGAME):			
			self.launchEmu()
			
		util.log("End onClick", util.LOG_LEVEL_DEBUG)
		

	def onFocus( self, controlId ):
		util.log("onFocus", util.LOG_LEVEL_DEBUG)		
		self.selectedControlId = controlId

	def onAction( self, action ):		
		if(action.getId() in ACTION_CANCEL_DIALOG):
			util.log("onAction exit", util.LOG_LEVEL_DEBUG)
			
			#stop Player (if playing)
			if(xbmc.Player().isPlayingVideo()):
				xbmc.Player().stop()
			self.close()
		elif(action.getId() in ACTION_MOVEMENT_LEFT or action.getId() in ACTION_MOVEMENT_RIGHT):
			if(self.selectedControlId == CONTROL_GAME_LIST_GROUP):
				
				util.log("onAction Movement up/down", util.LOG_LEVEL_DEBUG)
				
				pos = self.getCurrentListPosition()
				if(pos == -1):
					pos = 0
				selectedGame = self.getListItem(pos)
				if(selectedGame == None):
					util.log("selectedGame == None in showGameInfo", util.LOG_LEVEL_WARNING)
					return
			
				self.selectedGameId = selectedGame.getLabel2()
				self.showGameInfo()
	
	
	def showGameList(self):
		
		util.log("Begin showGameList", util.LOG_LEVEL_DEBUG)
		
		games = Game(self.gdb).getFilteredGames(self.selectedConsoleId, self.selectedGenreId, self.selectedYearId, self.selectedPublisherId)
				
		self.writeMsg("loading games...")
		
		xbmcgui.lock()
		
		self.clearList()
		
		for game in games:
			images = helper.getFilesByControl_Cached(self.gdb, 'gameinfoviewgamelist', game[util.ROW_ID], game[util.GAME_publisherId], game[util.GAME_developerId], game[util.GAME_romCollectionId],
				self.fileTypeForControlDict, self.fileTypeDict, self.fileDict, self.romCollectionDict)
			if(images != None and len(images) != 0):
				image = images[0]
			else:
				image = ""
			item = xbmcgui.ListItem(str(game[util.ROW_NAME]), str(game[util.ROW_ID]), image, '')
			self.addItem(item, False)
				
		xbmcgui.unlock()
		self.writeMsg("")
		
		util.log("End showGameList", util.LOG_LEVEL_DEBUG)
	
		
	def showGameInfo(self):
		
		util.log("Begin showGameInfo", util.LOG_LEVEL_DEBUG)
		
		#stop video (if playing)
		if(xbmc.Player().isPlayingVideo()):
			xbmc.Player().stop()
		
		gameRow = Game(self.gdb).getObjectById(self.selectedGameId)
		if(gameRow == None):
			self.writeMsg('Selected game could not be read from database.')
			return
		
		genreString = ""
		genres = Genre(self.gdb).getGenresByGameId(gameRow[0])
		if (genres != None):
			for i in range(0, len(genres)):
				genre = genres[i]
				genreString += genre[util.ROW_NAME]
				if(i < len(genres) -1):
					genreString += ", "
				
		year = self.getItemName(Year(self.gdb), gameRow[util.GAME_yearId])
		publisher = self.getItemName(Publisher(self.gdb), gameRow[util.GAME_publisherId])
		developer = self.getItemName(Developer(self.gdb), gameRow[util.GAME_developerId])
		reviewer = self.getItemName(Reviewer(self.gdb), gameRow[util.GAME_reviewerId])
				
		self.setLabel(CONTROL_LABEL_GENRE, genreString)
		self.setLabel(CONTROL_LABEL_YEAR, year)
		self.setLabel(CONTROL_LABEL_PUBLISHER, publisher)
		self.setLabel(CONTROL_LABEL_DEVELOPER, developer)
		self.setLabel(CONTROL_LABEL_REGION, gameRow[util.GAME_region])
		self.setLabel(CONTROL_LABEL_MEDIA, gameRow[util.GAME_media])
		self.setLabel(CONTROL_LABEL_CONTROLLER, gameRow[util.GAME_controllerType])
		self.setLabel(CONTROL_LABEL_RATING, gameRow[util.GAME_rating])
		self.setLabel(CONTROL_LABEL_VOTES, gameRow[util.GAME_numVotes])
		self.setLabel(CONTROL_LABEL_PLAYERS, gameRow[util.GAME_maxPlayers])
		self.setLabel(CONTROL_LABEL_PERSPECTIVE, gameRow[util.GAME_perspective])
		self.setLabel(CONTROL_LABEL_REVIEWER, reviewer)
		self.setLabel(CONTROL_LABEL_URL, gameRow[util.GAME_url])		
		self.setLabel(CONTROL_LABEL_LAUNCHCOUNT, gameRow[util.GAME_launchCount])
		self.setLabel(CONTROL_LABEL_ORIGTITLE, gameRow[util.GAME_originalTitle])
		self.setLabel(CONTROL_LABEL_ALTERNATETITLE, gameRow[util.GAME_alternateTitle])
		self.setLabel(CONTROL_LABEL_TRANSLATED, gameRow[util.GAME_translatedBy])
		self.setLabel(CONTROL_LABEL_VERSION, gameRow[util.GAME_version])
		
		description = gameRow[util.GAME_description]
		if(description == None):
			description = ""		
		
		controlDesc = self.getControlById(CONTROL_LABEL_DESC)
		if(controlDesc != None):			
			controlDesc.setText(description)
				
		#gameRow[5] = romCollectionId
		background = os.path.join(RCBHOME, 'resources', 'skins', 'Default', 'media', 'rcb-background-black.png')	
		self.setImage(CONTROL_IMG_BACK, util.IMAGE_CONTROL_GIV_BACKGROUND, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], background)
		self.setImage(CONTROL_IMG_GAMEINFO1, util.IMAGE_CONTROL_GIV_Img1, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], '')
		self.setImage(CONTROL_IMG_GAMEINFO2, util.IMAGE_CONTROL_GIV_Img2, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], None)
		self.setImage(CONTROL_IMG_GAMEINFO3, util.IMAGE_CONTROL_GIV_Img3, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], None)
		self.setImage(CONTROL_IMG_GAMEINFO4, util.IMAGE_CONTROL_GIV_Img4, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], None)
			
		
		videos = helper.getFilesByControl_Cached(self.gdb, util.IMAGE_CONTROL_GIV_VideoWindow, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId],
			self.fileTypeForControlDict, self.fileTypeDict, self.fileDict, self.romCollectionDict)
		#ingameVideos = File(self.gdb).getIngameVideosByGameId(self.selectedGameId)
		if(videos != None and len(videos) != 0):			
			video = videos[0]			
						
			playlist = xbmc.PlayList( xbmc.PLAYLIST_VIDEO)
			playlist.clear()			
			xbmc.Player().play(video, xbmcgui.ListItem('Dummy'), True)
		
		util.log("End showGameInfo", util.LOG_LEVEL_DEBUG)
		
		
	def getItemName(self, object, itemId):
		
		util.log("Begin getItemName", util.LOG_LEVEL_DEBUG)
		
		itemRow = object.getObjectById(itemId)
		if(itemRow == None):
			util.log("End getItemName", util.LOG_LEVEL_DEBUG)
			return ""
		else:
			util.log("End getItemName", util.LOG_LEVEL_DEBUG)
			return itemRow[1]
			
	
	def setLabel(self, controlId, value):
		
		util.log("Begin setLabel", util.LOG_LEVEL_DEBUG)
		
		if(value == None):
			value = ""	
		
		control = self.getControlById(controlId)
		if(control == None):
			return
		control.setLabel(str(value))
		util.log("End setLabel", util.LOG_LEVEL_DEBUG)
		
		
	def setImage(self, controlId, controlName, gameId, publisherId, developerId, romCollectionId, defaultImage):
		
		util.log("Begin setImage", util.LOG_LEVEL_DEBUG)
				
		images = helper.getFilesByControl_Cached(self.gdb, controlName, gameId, publisherId, developerId, romCollectionId, self.fileTypeForControlDict, self.fileTypeDict, self.fileDict, self.romCollectionDict)
		
		control = self.getControlById(controlId)
		if(control == None):
			return
				
		#TODO more than one image?
		if(images != None and len(images) != 0):
			image = images[0]			
			control.setImage(image)
			control.setVisible(1)
		else:
			if(defaultImage == None):
				control.setVisible(0)
			else:						
				control.setImage(defaultImage)
				
		util.log("End setImage", util.LOG_LEVEL_DEBUG)
	
	
	def launchEmu(self):
		
		util.log("Begin launchEmu", util.LOG_LEVEL_INFO)
		
		pos = self.getCurrentListPosition()
		if(pos == -1):
			pos = 0
		selectedGame = self.getListItem(pos)
		
		if(selectedGame == None):
			util.log("selectedGame == None in launchEmu", util.LOG_LEVEL_WARNING)
			return
			
		gameId = selectedGame.getLabel2()
		
		helper.launchEmu(self.gdb, self, gameId)
		util.log("End launchEmu", util.LOG_LEVEL_INFO)
		
	
	def saveViewState(self, isOnExit):
		
		util.log("Begin saveViewState", util.LOG_LEVEL_INFO)
		
		selectedGameIndex = self.getCurrentListPosition()
		if(selectedGameIndex == -1):
			selectedGameIndex = 0
		if(selectedGameIndex == None):
			util.log("selectedGameIndex == None in saveViewState", util.LOG_LEVEL_WARNING)
			return
		
		helper.saveViewState(self.gdb, isOnExit, 'gameInfoView', selectedGameIndex, self.selectedConsoleIndex, self.selectedGenreIndex, self.selectedPublisherIndex, 
			self.selectedYearIndex, self.selectedControlIdMainView, self.selectedControlId)
			
		util.log("End saveViewState", util.LOG_LEVEL_INFO)
			
			
	def getControlById(self, controlId):
		try:
			control = self.getControl(controlId)
		except: 
			util.log("Control with id: %s could not be found. Check WindowXML file." %str(controlId), util.LOG_LEVEL_ERROR)
			self.writeMsg("Control with id: %s could not be found. Check WindowXML file." %str(controlId))
			return None
		
		return control


	def writeMsg(self, msg):
		control = self.getControlById(CONTROL_LABEL_MSG)
		if(control == None):
			return
			
		control.setLabel(msg)
		