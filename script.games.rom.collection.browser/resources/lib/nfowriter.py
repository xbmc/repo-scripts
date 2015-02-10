
import os

import xbmc, xbmcgui, xbmcvfs

import dialogprogress
import util, helper
from util import *
from config import *
from gamedatabase import *
from xml.etree.ElementTree import *


class NfoWriter:
	
	Settings = util.getSettings()
	
	def __init__(self):
		pass
	
	
	def exportLibrary(self, gui):
		Logutil.log("Begin exportLibrary", util.LOG_LEVEL_INFO)
		
		gdb = gui.gdb
		romCollections = gui.config.romCollections
		
		progressDialog = dialogprogress.ProgressDialogGUI()
		progressDialog.writeMsg(util.localize(32169), "", "")
		continueExport = True
		rccount = 1
		
		for romCollection in gui.config.romCollections.values():
			
			progDialogRCHeader = util.localize(32170) +" (%i / %i): %s" %(rccount, len(romCollections), romCollection.name)
			rccount = rccount + 1			
			
			Logutil.log("export Rom Collection: " +romCollection.name, util.LOG_LEVEL_INFO)
			gameCount = 1
			
			#get all games for this Rom Collection
			games = Game(gdb).getFilteredGames(romCollection.id, 0, 0, 0, False, '0 = 0')
			progressDialog.itemCount = len(games) +1
			
			for gameRow in games:
				
				gamename = self.getGameProperty(gameRow[util.ROW_NAME])
				
				continueExport = progressDialog.writeMsg(progDialogRCHeader, util.localize(32171) +": " +str(gamename), "", gameCount)
				if(not continueExport):				
					Logutil.log('Game export canceled by user', util.LOG_LEVEL_INFO)
					break
				
				gameCount = gameCount +1
				
				plot = self.getGameProperty(gameRow[util.GAME_description])
								
				publisher = self.getGamePropertyFromCache(gameRow, gui.publisherDict, util.GAME_publisherId, util.ROW_NAME)
				developer = self.getGamePropertyFromCache(gameRow, gui.developerDict, util.GAME_developerId, util.ROW_NAME)
				year = self.getGamePropertyFromCache(gameRow, gui.yearDict, util.GAME_yearId, util.ROW_NAME)
				
				genreList = []
				try:
					cachingOptionStr = self.Settings.getSetting(util.SETTING_RCB_CACHINGOPTION)
					if(cachingOptionStr == 'CACHEALL'):
						genre = gui.genreDict[gameRow[util.ROW_ID]]
					else:				
						genres = Genre(gdb).getGenresByGameId(gameRow[util.ROW_ID])
						if (genres != None):
							for i in range(0, len(genres)):
								genreRow = genres[i]
								genreList.append(genreRow[util.ROW_NAME])
				except:				
					pass
				
				players = self.getGameProperty(gameRow[util.GAME_maxPlayers])
				rating = self.getGameProperty(gameRow[util.GAME_rating])
				votes = self.getGameProperty(gameRow[util.GAME_numVotes])
				url = self.getGameProperty(gameRow[util.GAME_url])
				region = self.getGameProperty(gameRow[util.GAME_region])
				media = self.getGameProperty(gameRow[util.GAME_media])
				perspective = self.getGameProperty(gameRow[util.GAME_perspective])
				controller = self.getGameProperty(gameRow[util.GAME_controllerType])
				originalTitle = self.getGameProperty(gameRow[util.GAME_originalTitle])
				alternateTitle = self.getGameProperty(gameRow[util.GAME_alternateTitle])
				version = self.getGameProperty(gameRow[util.GAME_version])
				
				#user settings
				isFavorite = self.getGameProperty(gameRow[util.GAME_isFavorite])
				launchCount = self.getGameProperty(gameRow[util.GAME_launchCount])
																
				romFiles = File(gdb).getRomsByGameId(gameRow[util.ROW_ID])
				romFile = ''
				if(romFiles != None and len(romFiles) > 0):
					romFile = romFiles[0][0]
				gamenameFromFile = helper.getGamenameFromFilename(romFile, romCollection)
				artworkfiles = {}
				artworkurls = []
				
				self.createNfoFromDesc(gamename, plot, romCollection.name, publisher, developer, year, 
									players, rating, votes, url, region, media, perspective, controller, originalTitle, alternateTitle, version, genreList, isFavorite, launchCount, romFile, gamenameFromFile, artworkfiles, artworkurls)
		
		progressDialog.writeMsg("", "", "", -1)
		del progressDialog
		
		
	def createNfoFromDesc(self, gamename, plot, romCollectionName, publisher, developer, year, players, rating, votes, 
						url, region, media, perspective, controller, originalTitle, alternateTitle, version, genreList, isFavorite, launchCount, romFile, gameNameFromFile, artworkfiles, artworkurls):
		
		Logutil.log("Begin createNfoFromDesc", util.LOG_LEVEL_INFO)
		
		root = Element('game')
		SubElement(root, 'title').text = gamename		
		SubElement(root, 'originalTitle').text = originalTitle
		SubElement(root, 'alternateTitle').text = alternateTitle
		SubElement(root, 'platform').text = romCollectionName
		SubElement(root, 'plot').text = plot
		SubElement(root, 'publisher').text = publisher
		SubElement(root, 'developer').text = developer
		SubElement(root, 'year').text = year
		
		for genre in genreList:
			SubElement(root, 'genre').text = str(genre)
		
		SubElement(root, 'detailUrl').text = url
		SubElement(root, 'maxPlayer').text = players
		SubElement(root, 'region').text = region
		SubElement(root, 'media').text = media
		SubElement(root, 'perspective').text = perspective
		SubElement(root, 'controller').text = controller
		SubElement(root, 'version').text = version
		SubElement(root, 'rating').text = rating
		SubElement(root, 'votes').text = votes
		
		SubElement(root, 'isFavorite').text = isFavorite
		SubElement(root, 'launchCount').text = launchCount
		
		for artworktype in artworkfiles.keys():
			
			local = ''
			online = ''
			try:
				local = artworkfiles[artworktype][0]
				online = str(artworkurls[artworktype.name])
			except:
				pass
			
			try:
				SubElement(root, 'thumb', {'type' : artworktype.name, 'local' : local}).text = online
			except Exception, (exc):
				Logutil.log('Error writing artwork url: ' +str(exc), util.LOG_LEVEL_WARNING)				
				pass
		
		#write file		
		try:
			util.indentXml(root)
			tree = ElementTree(root)
			
			nfoFile = self.getNfoFilePath(romCollectionName, romFile, gameNameFromFile)
						
			if(nfoFile != ''):
				if(nfoFile.startswith('smb://')):
					localFile = util.joinPath(util.getTempDir(), os.path.basename(nfoFile))					
					tree.write(localFile)
					xbmcvfs.copy(localFile, nfoFile)
					xbmcvfs.delete(localFile)
				else:
					tree.write(nfoFile)
			
		except Exception, (exc):
			Logutil.log("Error: Cannot write file game.nfo: " +str(exc), util.LOG_LEVEL_WARNING)
			
			
			
	def getNfoFilePath(self, romCollectionName, romFile, gameNameFromFile):
		nfoFile = ''
		
		useNfoFolder = self.Settings.getSetting(util.SETTING_RCB_USENFOFOLDER)
		if(useNfoFolder == 'true'):
			nfoFolder = self.Settings.getSetting(util.SETTING_RCB_NFOFOLDER)
		else:
			nfoFolder = ''
		if(nfoFolder != '' and nfoFolder != None):
			if(not os.path.exists(nfoFolder)):
				Logutil.log("Path to nfoFolder does not exist: " +nfoFolder, util.LOG_LEVEL_WARNING)
			else:
				nfoFolder = os.path.join(nfoFolder, romCollectionName)
				if(not os.path.exists(nfoFolder)):
					os.mkdir(nfoFolder)
					
				nfoFile = os.path.join(nfoFolder, gameNameFromFile +'.nfo')
						
		if(nfoFile == ''):
			romDir = os.path.dirname(romFile)
			Logutil.log('Romdir: ' +str(romDir), util.LOG_LEVEL_INFO)
			nfoFile = os.path.join(romDir, gameNameFromFile +'.nfo')
		
		if (not os.path.isfile(nfoFile)):
			Logutil.log('Writing NfoFile: ' +str(nfoFile), util.LOG_LEVEL_INFO)
		else:
			Logutil.log('NfoFile already exists. Wont overwrite file: ' +str(nfoFile), util.LOG_LEVEL_INFO)
			nfoFile = ''
		
		return nfoFile
	
	
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
	