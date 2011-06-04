
import xbmc, xbmcgui
import os, sys
import helper, util, dbupdate, launcher
from util import *
from gamedatabase import *


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

RCBHOME = util.getAddonInstallPath()


class UIGameInfoView(xbmcgui.WindowXMLDialog):
	def __init__(self, *args, **kwargs):		
		xbmcgui.WindowXMLDialog.__init__( self, *args, **kwargs )		
		
		Logutil.log("Init GameInfoView", util.LOG_LEVEL_INFO)
		
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
		self.selectedCharacter = kwargs[ "selectedCharacter" ]
		self.selectedCharacterIndex = kwargs[ "selectedCharacterIndex" ]
		self.selectedGameIndex = kwargs[ "selectedGameIndex" ]		
		self.selectedControlIdMainView = kwargs["controlIdMainView"]		
		self.fileDict = kwargs["fileDict"]
		self.config = kwargs["config"]
		self.settings = kwargs["settings"]
		
		self.doModal()
		
		
	def onInit(self):
		
		Logutil.log("Begin OnInit", util.LOG_LEVEL_DEBUG)				
		
		self.showGameList()
		
		control = self.getControlById(CONTROL_GAME_LIST_GROUP)
		if(control == None):
			return
			
		self.setFocus(control)
		self.selectedControlId = CONTROL_GAME_LIST_GROUP
		self.setCurrentListPosition(self.selectedGameIndex)
				
		xbmc.sleep(util.WAITTIME_UPDATECONTROLS)
		self.showGameInfo()	
		
		Logutil.log("End OnInit", util.LOG_LEVEL_DEBUG)
		
		
		
	def onClick( self, controlId ):
		Logutil.log("Begin onClick", util.LOG_LEVEL_DEBUG)
		
		if (controlId == CONTROL_BUTTON_PLAYGAME):			
			self.launchEmu()
			
		Logutil.log("End onClick", util.LOG_LEVEL_DEBUG)
		

	def onFocus( self, controlId ):
		Logutil.log("onFocus", util.LOG_LEVEL_DEBUG)		
		self.selectedControlId = controlId

	def onAction( self, action ):		
		if(action.getId() in ACTION_CANCEL_DIALOG):
			Logutil.log("onAction exit", util.LOG_LEVEL_DEBUG)
			
			#stop Player (if playing)
			if(xbmc.Player().isPlayingVideo()):
				xbmc.Player().stop()
			self.close()
		elif(action.getId() in ACTION_MOVEMENT_LEFT or action.getId() in ACTION_MOVEMENT_RIGHT):
			if(self.selectedControlId == CONTROL_GAME_LIST_GROUP or self.selectedControlId == CONTROL_GAME_LIST):
				
				Logutil.log("onAction Movement left/right", util.LOG_LEVEL_DEBUG)
				
				pos = self.getCurrentListPosition()
				if(pos == -1):
					pos = 0
				selectedGame = self.getListItem(pos)
				if(selectedGame == None):
					Logutil.log("selectedGame == None in showGameInfo", util.LOG_LEVEL_WARNING)
					return
			
				self.selectedGameId = selectedGame.getProperty('gameId')
				self.showGameInfo()
	
	
	def showGameList(self):
		
		Logutil.log("Begin showGameList", util.LOG_LEVEL_DEBUG)
		
		likeStatement = helper.buildLikeStatement(self.selectedCharacter)
		games = Game(self.gdb).getFilteredGames(self.selectedConsoleId, self.selectedGenreId, self.selectedYearId, self.selectedPublisherId, likeStatement)
				
		self.writeMsg("loading games...")
		
		xbmcgui.lock()
		
		self.clearList()
		
		for game in games:
			
			romCollection = None
			try:
				romCollection = self.config.romCollections[str(game[util.GAME_romCollectionId])]
			except:
				Logutil.log('Cannot get rom collection with id: ' +str(game[util.GAME_romCollectionId]), util.LOG_LEVEL_ERROR)
			
			images = helper.getFilesByControl_Cached(self.gdb, romCollection.imagePlacing.fileTypesForGameInfoViewGamelist, game[util.ROW_ID], game[util.GAME_publisherId], game[util.GAME_developerId], game[util.GAME_romCollectionId], self.fileDict)
			if(images != None and len(images) != 0):
				image = images[0]
			else:
				image = ""			
			item = xbmcgui.ListItem(game[util.ROW_NAME], str(game[util.ROW_ID]), image, '')
			item.setProperty('gameId', str(game[util.ROW_ID]))
			self.addItem(item, False)
				
		xbmc.executebuiltin("Container.SortDirection")
		xbmcgui.unlock()
		self.writeMsg("")
		
		Logutil.log("End showGameList", util.LOG_LEVEL_DEBUG)
	
		
	def showGameInfo(self):
		
		Logutil.log("Begin showGameInfo", util.LOG_LEVEL_DEBUG)
		
		#stop video (if playing)
		if(xbmc.Player().isPlayingVideo()):
			xbmc.Player().stop()
			
		pos = self.getCurrentListPosition()		
		if(pos == -1):
			pos = 0	
		
		selectedGame = self.getListItem(pos)

		if(selectedGame == None):
			Logutil.log("selectedGame == None in showGameInfo", util.LOG_LEVEL_WARNING)
			return
		
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
						
		selectedGame.setProperty('year', year)
		selectedGame.setProperty('publisher', publisher)
		selectedGame.setProperty('developer', developer)
		selectedGame.setProperty('reviewer', reviewer)		
		selectedGame.setProperty('genre', genreString)
		selectedGame.setProperty('maxplayers', self.getGameProperty(gameRow[util.GAME_maxPlayers]))				
		selectedGame.setProperty('rating', self.getGameProperty(gameRow[util.GAME_rating]))
		selectedGame.setProperty('votes', self.getGameProperty(gameRow[util.GAME_numVotes]))
		selectedGame.setProperty('url', self.getGameProperty(gameRow[util.GAME_url]))
		selectedGame.setProperty('region', self.getGameProperty(gameRow[util.GAME_region]))
		selectedGame.setProperty('media', self.getGameProperty(gameRow[util.GAME_media]))			
		selectedGame.setProperty('perspective', self.getGameProperty(gameRow[util.GAME_perspective]))
		selectedGame.setProperty('controllertype', self.getGameProperty(gameRow[util.GAME_controllerType]))
		selectedGame.setProperty('isfavorite', self.getGameProperty(gameRow[util.GAME_isFavorite]))
		selectedGame.setProperty('playcount', self.getGameProperty(gameRow[util.GAME_launchCount]))
		selectedGame.setProperty('originaltitle', self.getGameProperty(gameRow[util.GAME_originalTitle]))
		selectedGame.setProperty('alternatetitle', self.getGameProperty(gameRow[util.GAME_alternateTitle]))
		selectedGame.setProperty('translatedby', self.getGameProperty(gameRow[util.GAME_translatedBy]))
		selectedGame.setProperty('version', self.getGameProperty(gameRow[util.GAME_version]))
		
		description = gameRow[util.GAME_description]
		if(description == None):
			description = ""
		selectedGame.setProperty('plot', description)
		
		fileDict = self.getFileDictByGameRow(self.gdb, gameRow)
		
		romCollection = None
		try:
			romCollection = self.config.romCollections[str(gameRow[util.GAME_romCollectionId])]
		except:
			Logutil.log('Cannot get rom collection with id: ' +str(gameRow[util.GAME_romCollectionId]), util.LOG_LEVEL_ERROR)
										
		#gameRow[5] = romCollectionId
		background = os.path.join(RCBHOME, 'resources', 'skins', 'Default', 'media', 'rcb-background-black.png')					
		
		self.setImage(util.IMAGE_CONTROL_GIV_BACKGROUND, romCollection.imagePlacing.fileTypesForGameInfoViewBackground, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], background, selectedGame, fileDict)
		self.setImage(util.IMAGE_CONTROL_GIV_Img1, romCollection.imagePlacing.fileTypesForGameInfoView1, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], '', selectedGame, fileDict)
		self.setImage(util.IMAGE_CONTROL_GIV_Img2, romCollection.imagePlacing.fileTypesForGameInfoView2, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], None, selectedGame, fileDict)
		self.setImage(util.IMAGE_CONTROL_GIV_Img3, romCollection.imagePlacing.fileTypesForGameInfoView3, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], None, selectedGame, fileDict)
		self.setImage(util.IMAGE_CONTROL_GIV_Img4, romCollection.imagePlacing.fileTypesForGameInfoView4, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], None, selectedGame, fileDict)
					
		videos = helper.getFilesByControl_Cached(self.gdb, romCollection.imagePlacing.fileTypesForGameInfoViewVideoWindow, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
					
		if(videos != None and len(videos) != 0):			
			video = videos[0]						
			
			xbmc.Player().play(video, selectedGame, True)
		
		Logutil.log("End showGameInfo", util.LOG_LEVEL_DEBUG)
		
		
	def getItemName(self, object, itemId):
		
		Logutil.log("Begin getItemName", util.LOG_LEVEL_DEBUG)
		
		itemRow = object.getObjectById(itemId)
		if(itemRow == None):
			Logutil.log("End getItemName", util.LOG_LEVEL_DEBUG)
			return ""
		else:
			Logutil.log("End getItemName", util.LOG_LEVEL_DEBUG)
			return itemRow[1]
			
	
	def getGameProperty(self, property):				
		
		if(property == None):
			return ""
		
		try:				
			result = str(property)
		except:
			result = ""		
			
		return result
		
	
	def getFileDictByGameRow(self, gdb, gameRow):				
		
		files = File(gdb).getFilesByParentIds(gameRow[util.ROW_ID], gameRow[util.GAME_romCollectionId], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId])
				
		fileDict = self.cacheFiles(files)
		
		return fileDict
	
	
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
	
	
	def getFileForControl(self, controlName, gameId, publisherId, developerId, romCollectionId, fileDict):
		files = helper.getFilesByControl_Cached(self.gdb, controlName, gameId, publisherId, developerId, romCollectionId, self.fileTypeForControlDict, self.fileTypeDict, fileDict, self.romCollectionDict)		
		if(files != None and len(files) != 0):
			file = files[0]
		else:
			file = ""
			
		return file
	
	
	
	def setImage(self, controlName, fileTypes, gameId, publisherId, developerId, romCollectionId, defaultImage, selectedGame, fileDict):
		
		Logutil.log("Begin setImage", util.LOG_LEVEL_DEBUG)						
				
		images = helper.getFilesByControl_Cached(self.gdb, fileTypes, gameId, publisherId, developerId, romCollectionId, fileDict)
								
		#TODO more than one image?
		image = ''
		if(images != None and len(images) != 0):
			image = images[0]						
			#control.setVisible(1)
		else:
			if(defaultImage == None):
				pass
				#control.setVisible(0)
			else:						
				image = defaultImage
				
		selectedGame.setProperty(controlName, image)
				
		Logutil.log("End setImage", util.LOG_LEVEL_DEBUG)
	
	
	
	def launchEmu(self):
		
		Logutil.log("Begin launchEmu", util.LOG_LEVEL_INFO)				
		
		launcher.launchEmu(self.gdb, self, self.selectedGameId, self.config, self.settings)
		Logutil.log("End launchEmu", util.LOG_LEVEL_INFO)
		
	
	def saveViewState(self, isOnExit):
		
		Logutil.log("Begin saveViewState", util.LOG_LEVEL_INFO)
		
		selectedGameIndex = self.getCurrentListPosition()
		if(selectedGameIndex == -1):
			selectedGameIndex = 0
		if(selectedGameIndex == None):
			Logutil.log("selectedGameIndex == None in saveViewState", util.LOG_LEVEL_WARNING)
			return
		
		helper.saveViewState(self.gdb, isOnExit, 'gameInfoView', selectedGameIndex, self.selectedConsoleIndex, self.selectedGenreIndex, self.selectedPublisherIndex, 
			self.selectedYearIndex, self.selectedCharacterIndex, self.selectedControlIdMainView, self.selectedControlId)
			
		Logutil.log("End saveViewState", util.LOG_LEVEL_INFO)
			
			
	def getControlById(self, controlId):
		try:
			control = self.getControl(controlId)
		except: 
			Logutil.log("Control with id: %s could not be found. Check WindowXML file." %str(controlId), util.LOG_LEVEL_ERROR)
			self.writeMsg("Control with id: %s could not be found. Check WindowXML file." %str(controlId))
			return None
		
		return control


	def writeMsg(self, msg):
		control = self.getControlById(CONTROL_LABEL_MSG)
		if(control == None):
			return
			
		control.setLabel(msg)
		