
import os, sys
import getpass, string, glob
import codecs
import zipfile
import zlib
from pysqlite2 import dbapi2 as sqlite

from gamedatabase import *
from pyparsing import *
from descriptionparser import *
import util


DEBUG = True

class DBUpdate:		
	
	def __init__(self):
		pass
	
	def updateDB(self, gdb, gui):
		self.gdb = gdb
		
		self.log("Start Update DB", util.LOG_LEVEL_INFO)
		
		self.log("Reading Rom Collections from database", util.LOG_LEVEL_INFO)
		romCollectionRows = RomCollection(self.gdb).getAll()
		if(romCollectionRows == None):
			#gui.writeMsg("There are no Rom Collections in database. Make sure to import settings first.")
			self.log("There are no Rom Collections in database. Make sure to import settings first.", util.LOG_LEVEL_ERROR)
			self.exit()
			return False, "There are no Rom Collections in database. Make sure to import settings first."
		self.log(str(len(romCollectionRows)) +" Rom Collections read", util.LOG_LEVEL_INFO)		
		
		#itemCount is used fpr percenatge in ProgressDialogGUI
		gui.itemCount = len(romCollectionRows) +1
		
		rccount = 1
		for romCollectionRow in romCollectionRows:			
			gui.writeMsg("Importing Rom Collection: " +romCollectionRow[1], rccount)
			rccount = rccount + 1
			
			self.log("current Rom Collection: " +romCollectionRow[1], util.LOG_LEVEL_INFO)
						
			ignoreOnScan = romCollectionRow[13]
			self.log("ignoreOnScan: " +ignoreOnScan, util.LOG_LEVEL_INFO)
			#TODO: correct handling of boolean values
			if(ignoreOnScan == 'True'):
				self.log("current Rom Collection will be ignored.", util.LOG_LEVEL_INFO)
				continue
			
			descParserFile = romCollectionRow[6]
			self.log("using parser file: " +descParserFile, util.LOG_LEVEL_INFO)
			descFilePerGame = romCollectionRow[9]
			self.log("using one description file per game: " +descFilePerGame, util.LOG_LEVEL_INFO)
			descriptionPath = Path(self.gdb).getDescriptionPathByRomCollectionId(romCollectionRow[0])
			self.log("using game descriptions: " +descriptionPath, util.LOG_LEVEL_INFO)
			allowUpdate = romCollectionRow[12]
			self.log("update is allowed for current rom collection: " +allowUpdate, util.LOG_LEVEL_INFO)
			searchGameByCRC = romCollectionRow[14]
			self.log("search game by CRC: " +searchGameByCRC, util.LOG_LEVEL_INFO)
			searchGameByCRCIgnoreRomName = romCollectionRow[15]
			self.log("ignore rom filename when searching game by CRC: " +searchGameByCRCIgnoreRomName, util.LOG_LEVEL_INFO)
			ignoreGameWithoutDesc = romCollectionRow[16]
			self.log("ignore games without description: " +ignoreGameWithoutDesc, util.LOG_LEVEL_INFO)
			
			#check if we can find any roms with this configuration
			if(searchGameByCRCIgnoreRomName == 'True' and searchGameByCRC == 'False' and descFilePerGame == 'False'):
				self.log("Configuration error: descFilePerGame = false, searchGameByCRCIgnoreRomName = true, searchGameByCRC = false." \
				"You won't find any description with this configuration!", util.LOG_LEVEL_ERROR)
				continue
				
			if(descFilePerGame == 'False'):
				self.log("Start parsing description file", util.LOG_LEVEL_INFO)
				results = self.parseDescriptionFile(str(descriptionPath), str(descParserFile), '')
				if(results == None):					
					self.log("There was an error parsing the description file. Please see log file for more information.", util.LOG_LEVEL_ERROR)					
				
				if(results != None and util.CURRENT_LOG_LEVEL == util.LOG_LEVEL_DEBUG):
					for result in results:
						self.log(str(result.asDict()), util.LOG_LEVEL_DEBUG)
			
			#romCollectionRow[8] = startWithDescFile
			self.log("using start with description file: " +romCollectionRow[8], util.LOG_LEVEL_INFO)
			if(romCollectionRow[8] == 'True'):
				self.log("startWithDescFile is not implemented!", util.LOG_LEVEL_WARNING)
				continue
			else:		
				self.log("Reading configured paths from database", util.LOG_LEVEL_INFO)
				romPaths = Path(self.gdb).getRomPathsByRomCollectionId(romCollectionRow[0])
				self.log("Rom path: " +str(romPaths), util.LOG_LEVEL_INFO)
						
				self.log("Reading rom files", util.LOG_LEVEL_INFO)
				files = []
				for romPath in romPaths:
					files = self.walkDownPath(files, romPath[0])
					
				files.sort()
					
				self.log("Files read: " +str(files), util.LOG_LEVEL_INFO)
					
				lastgamenameFromFile = ""
				lastgamename = ""
					
				for filename in files:
					subrom = False
					
					self.log("current rom file: " +str(filename), util.LOG_LEVEL_INFO)
			
					#build friendly romname
					gamename = os.path.basename(filename)
					self.log("gamename (file): " +gamename, util.LOG_LEVEL_INFO)
					
					#romCollectionRow[10] = DiskPrefix
					dpIndex = gamename.lower().find(romCollectionRow[10].lower())
					if dpIndex > -1:
						gamename = gamename[0:dpIndex]
					else:
						gamename = os.path.splitext(gamename)[0]					
					
					self.log("gamename (friendly): " +gamename, util.LOG_LEVEL_INFO)
					gui.writeMsg("Importing Game: " +gamename, rccount)
					
					
					#check if we are handling one of the additional disks of a multi rom game
					if(gamename == lastgamenameFromFile):
						self.log("handling multi rom game: " +lastgamename, util.LOG_LEVEL_INFO)
						gameRow = Game(self.gdb).getOneByName(lastgamename)
						if(gameRow == None):
							self.log("multi rom game could not be read from database. "\
								"This usually happens if game name in description file differs from game name in rom file name.", util.LOG_LEVEL_WARNING)
							continue
						self.insertFile(str(filename), gameRow[0], "rcb_rom", None, None, None, None)
						self.gdb.commit()
						continue
						
					#lastgamename may be overwritten by parsed gamename
					lastgamenameFromFile = gamename
					lastgamename = gamename
					

					gamedescription = Empty()
					
					#get crc value of the rom file - this can take a long time for large files, so it is configurable
					if(searchGameByCRC == 'True'):
						filecrc = ''
						if (zipfile.is_zipfile(str(filename))):
							try:
								self.log("handling zip file", util.LOG_LEVEL_INFO)
								zip = zipfile.ZipFile(str(filename), 'r')
								zipInfos = zip.infolist()
								if(len(zipInfos) > 1):
									self.log("more than one file in zip archive is not supported! Checking CRC of first entry.", util.LOG_LEVEL_WARNING)
								filecrc = "%X" %(zipInfos[0].CRC & 0xFFFFFFFF)
								self.log("crc in zipped file: " +filecrc, util.LOG_LEVEL_INFO)
							except:
								self.log("Error while creating crc from zip file!", util.LOG_LEVEL_ERROR)
						else:						
							prev = 0
							for eachLine in open(str(filename),"rb"):
							    prev = zlib.crc32(eachLine, prev)					
							filecrc = "%X"%(prev & 0xFFFFFFFF)
							self.log("crc for current file: " +str(filecrc), util.LOG_LEVEL_INFO)

					#romCollectionRow[9] = descFilePerGame
					if(romCollectionRow[9] == 'False'):						
						self.log("Searching for game in parsed results:", util.LOG_LEVEL_INFO)
						if(results != None):
							for result in results:
								gamedesc = result['Game'][0]
								self.log("game name in parsed result: " +str(gamedesc), util.LOG_LEVEL_DEBUG)
								
								#find by filename
								#there is an option only to search by crc (maybe there are games with the same name but different crcs)
								if(searchGameByCRCIgnoreRomName == 'False'):
									if (gamedesc.strip() == gamename.strip()):
										self.log("result found by filename: " +gamedesc, util.LOG_LEVEL_INFO)
										gamedescription = result
										break
								
								#find by crc
								if(searchGameByCRC == 'True'):
									try:
										resultFound = False
										resultcrcs = result['crc']
										for resultcrc in resultcrcs:
											self.log("crc in parsed result: " +resultcrc, util.LOG_LEVEL_DEBUG)
											if(resultcrc.lower() == filecrc.lower()):
												self.log("result found by crc: " +gamedesc, util.LOG_LEVEL_INFO)
												gamedescription = result
												resultFound = True
												break
										if(resultFound):
											break
												
									except Exception, (exc):
										self.log("Error while checking crc results: " +str(exc), util.LOG_LEVEL_ERROR)
										
					else:						
						results = self.parseDescriptionFile(str(descriptionPath), str(descParserFile), gamename)
						if(results == None):
							gamedescription = Empty()
							
							lastgamename = ""							
						else:
							gamedescription = results[0]
							
					if(gamedescription == Empty()):
						lastgamename = ""
						if(ignoreGameWithoutDesc == 'True'):
							self.log("game " +gamename +" could not be found in parsed results. Game will not be imported.", util.LOG_LEVEL_WARNING)
							continue
						else:
							self.log("game " +gamename +" could not be found in parsed results. Importing game without description.", util.LOG_LEVEL_WARNING)
					else:
						lastgamename = self.resolveParseResult(gamedescription.Game, 'Game')
					
					#get Console Name to import images via %CONSOLE%
					consoleId = romCollectionRow[2]									
					consoleRow = Console(self.gdb).getObjectById(consoleId)					
					if(consoleRow == None):						
						consoleName = None						
					else:
						consoleName = consoleRow[1]
					
					self.insertData(gamedescription, gamename, romCollectionRow[0], filename, allowUpdate, consoleId, consoleName)
					
		gui.writeMsg("Done.", rccount)
		self.exit()
		return True, ''
		
	
	def walkDownPath(self, files, romPath):
		
		self.log("walkDownPath romPath: " +romPath, util.LOG_LEVEL_INFO)
		
		#TODO add configuration option
		walkDownRomPath = True
		
		dirname = os.path.dirname(romPath)
		self.log("dirname: " +dirname, util.LOG_LEVEL_INFO)
		basename = os.path.basename(romPath)
		self.log("basename: " +basename, util.LOG_LEVEL_INFO)
		
		if(walkDownRomPath):
			self.log("walkDownRomPath is true: checking sub directories", util.LOG_LEVEL_INFO)
			for walkRoot, walkDirs, walkFiles in os.walk(dirname):
				self.log( "root: " +str(walkRoot), util.LOG_LEVEL_DEBUG)	
				
				newRomPath = os.path.join(walkRoot, basename)
				self.log( "newRomPath: " +str(newRomPath), util.LOG_LEVEL_DEBUG)
				
				#glob is same as "os.listdir(romPath)" but it can handle wildcards like *.adf
				allFiles = glob.glob(newRomPath)
				self.log( "all files in newRomPath: " +str(allFiles), util.LOG_LEVEL_DEBUG)
			
				#did not find appendall or something like this
				for file in allFiles:
					files.append(file)
					
		else:		
			if os.path.isdir(dirname):
			
				#glob is same as "os.listdir(romPath)" but it can handle wildcards like *.adf
				allFiles = glob.glob(romPath)
			
				#did not find appendall or something like this
				for file in allFiles:
					files.append(file)
		
		return files
	
	
	def parseDescriptionFile(self, descriptionPath, descParserFile, gamename):
		descriptionfile = descriptionPath.replace("%GAME%", gamename)

		if(os.path.exists(descriptionfile)):
			self.log("Parsing game description: " +descriptionfile, util.LOG_LEVEL_INFO)
			dp = DescriptionParser()
			
			try:
				results = dp.parseDescription(descriptionfile, descParserFile, gamename)
			except Exception, (exc):
				self.log("an error occured while parsing game description: " +descriptionfile, util.LOG_LEVEL_WARNING)
				self.log("Parser complains about: " +str(exc), util.LOG_LEVEL_WARNING)
				return None
							
			del dp
			
			return results
			
		else:
			self.log("description file for game " +gamename +" could not be found. "\
				"Check if this path exists: " +descriptionfile, util.LOG_LEVEL_WARNING)
			return None
			
			
	def insertData(self, gamedescription, gamenameFromFile, romCollectionId, romFile, allowUpdate, consoleId, consoleName):
		self.log("Insert data", util.LOG_LEVEL_INFO)
				
		publisherId = None
		developerId = None
		publisher = None
		developer = None
				
		if(gamedescription != Empty()):
			
			publisher = self.resolveParseResult(gamedescription.Publisher, 'Publisher')
			developer = self.resolveParseResult(gamedescription.Developer, 'Developer')
			
			yearId = self.insertForeignKeyItem(gamedescription.ReleaseYear, 'Year', Year(self.gdb))
			genreIds = self.insertForeignKeyItemList(gamedescription.Genre, 'Genre', Genre(self.gdb))		
			publisherId = self.insertForeignKeyItem(gamedescription.Publisher, 'Publisher', Publisher(self.gdb))
			developerId = self.insertForeignKeyItem(gamedescription.Developer, 'Developer', Developer(self.gdb))
			reviewerId = self.insertForeignKeyItem(gamedescription.Reviewer, 'Reviewer', Reviewer(self.gdb))	
			
			region = self.resolveParseResult(gamedescription.Region, 'Region')		
			media = self.resolveParseResult(gamedescription.Media, 'Media')
			controller = self.resolveParseResult(gamedescription.Controller, 'Controller')
			players = self.resolveParseResult(gamedescription.Players, 'Players')		
			rating = self.resolveParseResult(gamedescription.Rating, 'Rating')
			votes = self.resolveParseResult(gamedescription.Votes, 'Votes')
			url = self.resolveParseResult(gamedescription.URL, 'URL')
			perspective = self.resolveParseResult(gamedescription.Perspective, 'Perspective')
			originalTitle = self.resolveParseResult(gamedescription.OriginalTitle, 'OriginalTitle')
			alternateTitle = self.resolveParseResult(gamedescription.AlternateTitle, 'AlternateTitle')
			translatedBy = self.resolveParseResult(gamedescription.TranslatedBy, 'TranslatedBy')
			version = self.resolveParseResult(gamedescription.Version, 'Version')
		
			self.log("Result Game (from parser) = " +str(gamedescription.Game), util.LOG_LEVEL_INFO)
			gamename = self.resolveParseResult(gamedescription.Game, 'Game')
			plot = self.resolveParseResult(gamedescription.Description, 'Description')
			
			self.log("Result Game (as string) = " +gamename, util.LOG_LEVEL_INFO)
			gameId = self.insertGame(gamename, plot, romCollectionId, publisherId, developerId, reviewerId, yearId, 
				players, rating, votes, url, region, media, perspective, controller, originalTitle, alternateTitle, translatedBy, version, allowUpdate, )
				
			for genreId in genreIds:
				genreGame = GenreGame(self.gdb).getGenreGameByGenreIdAndGameId(genreId, gameId)
				if(genreGame == None):
					GenreGame(self.gdb).insert((genreId, gameId))
		else:
			gamename = gamenameFromFile
			gameId = self.insertGame(gamename, None, romCollectionId, None, None, None, None, 
					None, None, None, None, None, None, None, None, None, None, None, None, allowUpdate)			
			
		
		self.insertFile(romFile, gameId, "rcb_rom", None, None, None, None)
		
		
		allPathRows = Path(self.gdb).getPathsByRomCollectionId(romCollectionId)
		for pathRow in allPathRows:
			self.log("Additional data path: " +str(pathRow), util.LOG_LEVEL_INFO)
			files = self.resolvePath((pathRow[1],), gamename, gamenameFromFile, consoleName, publisher, developer)
			self.log("Importing files: " +str(files), util.LOG_LEVEL_INFO)
			fileTypeRow = FileType(self.gdb).getObjectById(pathRow[2])
			self.log("FileType: " +str(fileTypeRow), util.LOG_LEVEL_INFO)
			if(fileTypeRow == None):
				continue
			self.insertFiles(files, gameId, fileTypeRow[1], consoleId, publisherId, developerId, romCollectionId)							
				
		self.gdb.commit()
		
		
	def insertGame(self, gameName, description, romCollectionId, publisherId, developerId, reviewerId, yearId, 
				players, rating, votes, url, region, media, perspective, controller, originalTitle, alternateTitle, translatedBy, version, allowUpdate):
		# TODO unique by name an RC
		gameRow = Game(self.gdb).getGameByNameAndRomCollectionId(gameName, romCollectionId)
		if(gameRow == None):
			self.log("Game does not exist in database. Insert game: " +gameName.encode('iso-8859-15'), util.LOG_LEVEL_INFO)
			Game(self.gdb).insert((gameName, description, None, None, romCollectionId, publisherId, developerId, reviewerId, yearId, 
				players, rating, votes, url, region, media, perspective, controller, 0, 0, originalTitle, alternateTitle, translatedBy, version))
			return self.gdb.cursor.lastrowid
		else:	
			if(allowUpdate == 'True'):
				self.log("Game does exist in database. Update game: " +gameName, util.LOG_LEVEL_INFO)
				Game(self.gdb).update(('name', 'description', 'romCollectionId', 'publisherId', 'developerId', 'reviewerId', 'yearId', 'maxPlayers', 'rating', 'numVotes',
					'url', 'region', 'media', 'perspective', 'controllerType', 'originalTitle', 'alternateTitle', 'translatedBy', 'version'),
					(gameName, description, romCollectionId, publisherId, developerId, reviewerId, yearId, players, rating, votes, url, region, media, perspective, controller,
					originalTitle, alternateTitle, translatedBy, version),
					gameRow[0])
			else:
				self.log("Game does exist in database but update is not allowed for current rom collection. game: " +gameName.encode('iso-8859-15'), util.LOG_LEVEL_INFO)
			
			return gameRow[0]
		
	
	def insertForeignKeyItem(self, result, itemName, gdbObject):
		self.log("Result " +itemName +" (from Parser) = " +str(result), util.LOG_LEVEL_INFO)
		#if(result != Empty()):
		if(len(result) != 0):
			item = result[0].strip()
			self.log("Result "  +itemName +" (as string) = " +item.encode('iso-8859-15'), util.LOG_LEVEL_INFO)
			itemRow = gdbObject.getOneByName(item)
			if(itemRow == None):	
				self.log(itemName +" does not exist in database. Insert: " +item.encode('iso-8859-15'), util.LOG_LEVEL_INFO)
				gdbObject.insert((item,))
				itemId = self.gdb.cursor.lastrowid
			else:
				itemId = itemRow[0]
		else:
			itemId = None
			
		return itemId
		
	
	def insertForeignKeyItemList(self, resultList, itemName, gdbObject):	
		self.log("Result " +itemName +" (from Parser) = " +str(resultList), util.LOG_LEVEL_INFO)
		idList = []
		
		for resultItem in resultList:			
			item = resultItem.strip()
			self.log("Result " +itemName +" (as string) = " +item.encode('iso-8859-15'), util.LOG_LEVEL_INFO)
			itemRow = gdbObject.getOneByName(item)
			if(itemRow == None):
				self.log(itemName +" does not exist in database. Insert: " +item.encode('iso-8859-15'), util.LOG_LEVEL_INFO)
				gdbObject.insert((item,))
				idList.append(self.gdb.cursor.lastrowid)
			else:
				idList.append(itemRow[0])
				
		return idList
		
		
	def resolvePath(self, paths, gamename, gamenameFromFile, consoleName, publisher, developer):		
		resolvedFiles = []				
				
		for path in paths:
			files = []
			self.log("resolve path: " +path, util.LOG_LEVEL_INFO)
			pathnameFromGameName = path.replace("%GAME%", gamename)
			self.log("resolved path from game name: " +pathnameFromGameName, util.LOG_LEVEL_INFO)
			files = self.getFilesByWildcard(pathnameFromGameName)			
			
			if(gamename != gamenameFromFile and len(files) == 0):
				pathnameFromFile = path.replace("%GAME%", gamenameFromFile)
				self.log("resolved path from rom file name: " +pathnameFromFile, util.LOG_LEVEL_INFO)
				files = glob.glob(pathnameFromFile)
				self.log("resolved files: " +str(files), util.LOG_LEVEL_INFO)
				
			#TODO could be done only once per RomCollection
			if(consoleName != None and len(files) == 0):
				pathnameFromConsole = path.replace("%CONSOLE%", consoleName)
				self.log("resolved path from console name: " +pathnameFromConsole, util.LOG_LEVEL_INFO)
				files = self.getFilesByWildcard(pathnameFromConsole)				
				
			if(publisher != None and len(files) == 0):
				pathnameFromPublisher = path.replace("%PUBLISHER%", publisher)
				self.log("resolved path from publisher name: " +pathnameFromPublisher, util.LOG_LEVEL_INFO)
				files = self.getFilesByWildcard(pathnameFromPublisher)				
				
			if(developer != None and len(files) == 0):
				pathnameFromDeveloper = path.replace("%DEVELOPER%", developer)
				self.log("resolved path from developer name: " +pathnameFromDeveloper, util.LOG_LEVEL_INFO)
				files = self.getFilesByWildcard(pathnameFromDeveloper)				
						
			if(len(files) == 0):
				self.log("No files found for game %s. Make sure that file names are matching." %gamename, util.LOG_LEVEL_WARNING)
			for file in files:
				if(os.path.exists(file)):
					resolvedFiles.append(file)		
		return resolvedFiles
		
	
	def getFilesByWildcard(self, pathName):
		# try glob with * wildcard
		files = glob.glob(pathName)
		
		# glob can't handle []-characters - try it with listdir
		if(len(files)  == 0):
			try:				
				if(os.path.isfile(pathName)):
					files.append(pathName)
				else:
					files = os.listdir(pathName)					
			except:
				pass
		return files
		self.log("resolved files: " +str(files), util.LOG_LEVEL_INFO)
		
		
	def resolveParseResult(self, result, itemName):
		self.log("Result " +itemName +" (from Parser) = " +str(result), util.LOG_LEVEL_INFO)
		if(len(result) != 0):
			item = result[0].strip()
		else:
			item = ""
		self.log("Result " +itemName +" (as string) = " +item.encode('iso-8859-15'), util.LOG_LEVEL_INFO)
		return item
	
	
	def insertFiles(self, fileNames, gameId, fileType, consoleId, publisherId, developerId, romCollectionId):
		for fileName in fileNames:
			self.insertFile(fileName, gameId, fileType, consoleId, publisherId, developerId, romCollectionId)
			
		
	def insertFile(self, fileName, gameId, fileType, consoleId, publisherId, developerId, romCollectionId):
		self.log("Begin Insert file: " +fileName, util.LOG_LEVEL_DEBUG)
				
		fileTypeRow = FileType(self.gdb).getOneByName(fileType)
		if(fileTypeRow == None):
			self.log("No filetype found for %s. Please check your config.xml" %fileType, util.LOG_LEVEL_WARNING)
			
		parentId = None
		
		#TODO console and romcollection could be done only once per RomCollection			
		#fileTypeRow[3] = parent
		if(fileTypeRow[3] == 'game'):
			self.log("Insert file with parent game", util.LOG_LEVEL_INFO)
			parentId = gameId
		elif(fileTypeRow[3] == 'console'):
			self.log("Insert file with parent console", util.LOG_LEVEL_INFO)
			parentId = consoleId
		elif(fileTypeRow[3] == 'romcollection'):
			self.log("Insert file with parent rom collection", util.LOG_LEVEL_INFO)
			parentId = romCollectionId
		elif(fileTypeRow[3] == 'publisher'):
			self.log("Insert file with parent publisher", util.LOG_LEVEL_INFO)
			parentId = publisherId
		elif(fileTypeRow[3] == 'developer'):
			self.log("Insert file with parent developer", util.LOG_LEVEL_INFO)
			parentId = developerId
			
		fileRow = File(self.gdb).getFileByNameAndTypeAndParent(fileName, fileType, parentId)
		if(fileRow == None):
			self.log("File does not exist in database. Insert file: " +fileName, util.LOG_LEVEL_INFO)
			File(self.gdb).insert((str(fileName), fileTypeRow[0], parentId))
			

	def log(self, message, logLevel):				
			
		if(logLevel > util.CURRENT_LOG_LEVEL):
			return
			
		prefix = ''
		if(logLevel == util.LOG_LEVEL_DEBUG):
			prefix = 'RCB_DEBUG: '
		elif(logLevel == util.LOG_LEVEL_INFO):
			prefix = 'RCB_INFO: '
		elif(logLevel == util.LOG_LEVEL_WARNING):
			prefix = 'RCB_WARNING: '
		elif(logLevel == util.LOG_LEVEL_ERROR):
			prefix = 'RCB_ERROR: '

		print(prefix + message+"\n")			
				
		
	def exit(self):
		self.log("Update finished", util.LOG_LEVEL_INFO)		
