
import os, sys
import getpass, string, glob
import codecs
import zipfile
import zlib
import time
from pysqlite2 import dbapi2 as sqlite

from gamedatabase import *
from pyparsing import *
from descriptionparser import *
import util
from util import *




class DBUpdate:		
	
	def __init__(self):
		pass
	
	def updateDB(self, gdb, gui):
		self.gdb = gdb
		
		Logutil.log("Start Update DB", util.LOG_LEVEL_INFO)
		
		Logutil.log("Reading Rom Collections from database", util.LOG_LEVEL_INFO)
		romCollectionRows = RomCollection(self.gdb).getAll()
		if(romCollectionRows == None):			
			Logutil.log("There are no Rom Collections in database. Make sure to import settings first.", util.LOG_LEVEL_ERROR)
			self.exit()
			return False, "There are no Rom Collections in database. Make sure to import settings first."
		Logutil.log(str(len(romCollectionRows)) +" Rom Collections read", util.LOG_LEVEL_INFO)				
		
		rccount = 1
		for romCollectionRow in romCollectionRows:
			#prepare Header for ProgressDialog
			progDialogRCHeader = "Importing Rom Collection (%i / %i): %s" %(rccount, len(romCollectionRows), romCollectionRow[1])			
			rccount = rccount + 1
			
			Logutil.log("current Rom Collection: " +romCollectionRow[1], util.LOG_LEVEL_INFO)

			#Read settings for current Rom Collection
			
			ignoreOnScan = romCollectionRow[13]
			Logutil.log("ignoreOnScan: " +ignoreOnScan, util.LOG_LEVEL_INFO)
			#TODO: correct handling of boolean values
			if(ignoreOnScan == 'True'):
				Logutil.log("current Rom Collection will be ignored.", util.LOG_LEVEL_INFO)
				continue
			
			descParserFile = romCollectionRow[6]
			Logutil.log("using parser file: " +descParserFile, util.LOG_LEVEL_INFO)
			descFilePerGame = romCollectionRow[9]
			Logutil.log("using one description file per game: " +descFilePerGame, util.LOG_LEVEL_INFO)
			descriptionPath = Path(self.gdb).getDescriptionPathByRomCollectionId(romCollectionRow[0])
			Logutil.log("using game descriptions: " +descriptionPath, util.LOG_LEVEL_INFO)
			allowUpdate = romCollectionRow[12]
			Logutil.log("update is allowed for current rom collection: " +allowUpdate, util.LOG_LEVEL_INFO)
			searchGameByCRC = romCollectionRow[14]
			Logutil.log("search game by CRC: " +searchGameByCRC, util.LOG_LEVEL_INFO)
			searchGameByCRCIgnoreRomName = romCollectionRow[15]			
			Logutil.log("ignore rom filename when searching game by CRC: " +searchGameByCRCIgnoreRomName, util.LOG_LEVEL_INFO)
			
			useFoldernameAsCRC = romCollectionRow[20]
			Logutil.log("use foldername as CRC: " +useFoldernameAsCRC, util.LOG_LEVEL_INFO)
			useFilenameAsCRC = romCollectionRow[21]
			Logutil.log("use filename as CRC: " +useFilenameAsCRC, util.LOG_LEVEL_INFO)
			
			ignoreGameWithoutDesc = romCollectionRow[16]			
			Logutil.log("ignore games without description: " +ignoreGameWithoutDesc, util.LOG_LEVEL_INFO)
			
			maxFolderDepth = romCollectionRow[22]
			Logutil.log("max folder depth: " +str(maxFolderDepth), util.LOG_LEVEL_INFO)
			
			#check if we can find any roms with this configuration
			if(searchGameByCRCIgnoreRomName == 'True' and searchGameByCRC == 'False' and descFilePerGame == 'False'):
				Logutil.log("Configuration error: descFilePerGame = false, searchGameByCRCIgnoreRomName = true, searchGameByCRC = false." \
				"You won't find any description with this configuration!", util.LOG_LEVEL_ERROR)
				continue			
			
			#romCollectionRow[8] = startWithDescFile
			Logutil.log("using start with description file: " +romCollectionRow[8], util.LOG_LEVEL_INFO)
			if(romCollectionRow[8] == 'True'):
				Logutil.log("startWithDescFile == True is not implemented!", util.LOG_LEVEL_WARNING)
				continue
			else:		
				files = self.getRomFilesByRomCollection(romCollectionRow, maxFolderDepth)				
									
				lastgamenameFromFile = ""
				lastgamename = ""
				foldername = ''
				
				filecrcDict = {}
				fileGamenameDict = {}
				fileFoldernameDict = {}								
				
				#itemCount is used for percentage in ProgressDialogGUI
				gui.itemCount = len(files) +1
				fileCount = 1
				
				Logutil.log("Start building file crcs", util.LOG_LEVEL_INFO)
				for filename in files:
					gamename = self.getGamenameFromFilename(filename, romCollectionRow)
					gui.writeMsg(progDialogRCHeader, "Checking file crcs...", "", fileCount)
					fileCount = fileCount +1
					
					#check if we are handling one of the additional disks of a multi rom game
					isMultiRomGame = self.checkRomfileIsMultirom(gamename, lastgamename, lastgamenameFromFile, filename)
					
					#lastgamename may be overwritten by parsed gamename
					lastgamenameFromFile = gamename
					lastgamename = gamename	
					
					gamename = gamename.strip()
					gamename = gamename.lower()
					
					#build dictionaries (key=gamename, filecrc or foldername; value=filenames) for later game search
					fileGamenameDict = self.buildFilenameDict(fileGamenameDict, isMultiRomGame, filename, gamename, fileGamenameDict, gamename, True)
						
					if(searchGameByCRC == 'True'):
						filecrc = self.getFileCRC(filename)
						filecrc = filecrc.strip()
						filecrc = filecrc.lower()
						filecrcDict = self.buildFilenameDict(filecrcDict, isMultiRomGame, filename, filecrc, fileGamenameDict, gamename, False)
					
					#Folder name of game may be used as crc value in description files					
					if(useFoldernameAsCRC == 'True'):
						foldername = self.getCRCFromFolder(filename)
						foldername = foldername.strip()
						foldername = foldername.lower()
						fileFoldernameDict = self.buildFilenameDict(fileFoldernameDict, isMultiRomGame, filename, foldername, fileGamenameDict, gamename, False)

				Logutil.log("Building file crcs done", util.LOG_LEVEL_INFO)								
									
				if(descFilePerGame == 'False' and descParserFile != '' and descriptionPath != ''):
					Logutil.log("Searching for game in parsed results:", util.LOG_LEVEL_INFO)
					
					try:
						#prepare game description parser
						dp = DescriptionParser()
						gameGrammar = dp.getGameGrammar(str(descParserFile), '')
						
						fh = open(str(descriptionPath), 'r')
						fileAsString = fh.read()		
						fileAsString = fileAsString.decode('iso-8859-15')
						
						fileCount = 1
						
						#parse description
						for result,start,end in gameGrammar.scanString(fileAsString):														
							
							filenamelist, foldername = self.findFilesByGameDescription(result, searchGameByCRCIgnoreRomName, searchGameByCRC, 
								filecrcDict, fileFoldernameDict, fileGamenameDict, useFoldernameAsCRC, useFilenameAsCRC)

							if(filenamelist != None and len(filenamelist) > 0):								
								gamenameFromFile = self.getGamenameFromFilename(filenamelist[0], romCollectionRow)
								gamenameFromDesc = result['Game'][0]
								gui.writeMsg(progDialogRCHeader, "Import game: " +str(gamenameFromDesc), "", fileCount)
								fileCount = fileCount +1
							else:
								gamename = ''
								gamenameFromFile = ''
							self.insertGameFromDesc(result, lastgamename, ignoreGameWithoutDesc, gamenameFromFile, romCollectionRow, filenamelist, foldername, allowUpdate)
								
					except Exception, (exc):
						Logutil.log("an error occured while parsing game description: " +descriptionPath, util.LOG_LEVEL_WARNING)
						Logutil.log("Parser complains about: " +str(exc), util.LOG_LEVEL_WARNING)
						return None
				else:	
					fileCount = 1
					for filename in files:
						gamename = self.getGamenameFromFilename(filename, romCollectionRow)						
						
						gui.writeMsg(progDialogRCHeader, "Import game: " +gamename, "", fileCount)
						fileCount = fileCount +1
						
						results = self.parseDescriptionFile(str(descriptionPath), str(descParserFile), gamename)						
						#print results
						if(results == None):
							gamedescription = Empty()
							
							lastgamename = ""							
						else:
							gamedescription = results[0]
							
						filenamelist = []
						filenamelist.append(filename)
							
						self.insertGameFromDesc(gamedescription, lastgamename, ignoreGameWithoutDesc, gamename, romCollectionRow, filenamelist, foldername, allowUpdate)													
					
		gui.writeMsg("Done.", "", "", gui.itemCount)
		self.exit()
		return True, ''
					
		
	
	def getRomFilesByRomCollection(self, romCollectionRow, maxFolderDepth):
		Logutil.log("Reading configured paths from database", util.LOG_LEVEL_INFO)
		romPaths = Path(self.gdb).getRomPathsByRomCollectionId(romCollectionRow[0])
		Logutil.log("Rom path: " +str(romPaths), util.LOG_LEVEL_INFO)
				
		Logutil.log("Reading rom files", util.LOG_LEVEL_INFO)
		files = []
		for romPath in romPaths:
			files = self.walkDownPath(files, romPath[0], maxFolderDepth)
			
		files.sort()
			
		Logutil.log("Files read: " +str(files), util.LOG_LEVEL_INFO)
		
		return files
		
		
	def walkDownPath(self, files, romPath, maxFolderDepth):
		
		Logutil.log("walkDownPath romPath: " +romPath, util.LOG_LEVEL_INFO)						
		
		dirname = os.path.dirname(romPath)
		Logutil.log("dirname: " +dirname, util.LOG_LEVEL_INFO)
		basename = os.path.basename(romPath)
		Logutil.log("basename: " +basename, util.LOG_LEVEL_INFO)						
				
		Logutil.log("checking sub directories", util.LOG_LEVEL_INFO)
		for walkRoot, walkDirs, walkFiles in self.walklevel(dirname.encode('utf-8'), maxFolderDepth):
			Logutil.log( "root: " +str(walkRoot), util.LOG_LEVEL_DEBUG)
			Logutil.log( "walkDirs: " +str(walkDirs), util.LOG_LEVEL_DEBUG)
			Logutil.log( "walkFiles: " +str(walkFiles), util.LOG_LEVEL_DEBUG)
									
			newRomPath = os.path.join(walkRoot, basename)
			Logutil.log( "newRomPath: " +str(newRomPath), util.LOG_LEVEL_DEBUG)
			
			#glob is same as "os.listdir(romPath)" but it can handle wildcards like *.adf
			allFiles = glob.glob(newRomPath)
			Logutil.log( "all files in newRomPath: " +str(allFiles), util.LOG_LEVEL_DEBUG)
		
			#did not find appendall or something like this
			for file in allFiles:
				files.append(file)							
		
		return files
	
	
	def walklevel(self, some_dir, level=1):
	    some_dir = some_dir.rstrip(os.path.sep)
	    assert os.path.isdir(some_dir)
	    num_sep = len([x for x in some_dir if x == os.path.sep])
	    for root, dirs, files in os.walk(some_dir):
	        yield root, dirs, files
	        num_sep_this = len([x for x in root if x == os.path.sep])
	        if num_sep + level <= num_sep_this:
	            del dirs[:]
		
		
	def getGamenameFromFilename(self, filename, romCollectionRow):
		subrom = False
					
		Logutil.log("current rom file: " +str(filename), util.LOG_LEVEL_INFO)

		#build friendly romname
		gamename = os.path.basename(filename)
		Logutil.log("gamename (file): " +gamename, util.LOG_LEVEL_INFO)
		
		#romCollectionRow[10] = DiskPrefix
		dpIndex = gamename.lower().find(romCollectionRow[10].lower())
		if dpIndex > -1:
			gamename = gamename[0:dpIndex]
		else:
			gamename = os.path.splitext(gamename)[0]					
		
		Logutil.log("gamename (friendly): " +gamename, util.LOG_LEVEL_INFO)		
		
		return gamename
		
		
	def checkRomfileIsMultirom(self, gamename, lastgamename, lastgamenameFromFile, filename):		
	
		#XBOX Hack: rom files will always be named default.xbe: always detected as multi rom without this hack
		if(gamename == lastgamenameFromFile and lastgamenameFromFile.lower() != 'default'):		
			Logutil.log("handling multi rom game: " +lastgamename, util.LOG_LEVEL_INFO)			
			return True
		return False
		
		
	def buildFilenameDict(self, dict, isMultiRomGame, filename, key, fileGamenameDict, gamename, isGamenameDict):				
		
		try:											
			if(not isMultiRomGame):
				filenamelist = []
				filenamelist.append(filename)
				dict[key] = filenamelist
				Logutil.log("Add filename %s with key %s" %(filename, key), util.LOG_LEVEL_DEBUG)
			else:
				filenamelist = fileGamenameDict[gamename]
				if(isGamenameDict):
					filenamelist.append(filename)
				dict[key] = filenamelist
				Logutil.log("Add filename %s with key %s" %(filename, key), util.LOG_LEVEL_DEBUG)
		except:
			pass
			
		return dict
		
		
	def getFileCRC(self, filename):
		#get crc value of the rom file - this can take a long time for large files, so it is configurable
		filecrc = ''		
		if (zipfile.is_zipfile(str(filename))):
			try:
				Logutil.log("handling zip file", util.LOG_LEVEL_INFO)
				zip = zipfile.ZipFile(str(filename), 'r')
				zipInfos = zip.infolist()
				if(len(zipInfos) > 1):
					Logutil.log("more than one file in zip archive is not supported! Checking CRC of first entry.", util.LOG_LEVEL_WARNING)
				filecrc = "%0.8X" %(zipInfos[0].CRC & 0xFFFFFFFF)
				Logutil.log("crc in zipped file: " +filecrc, util.LOG_LEVEL_INFO)
			except:
				Logutil.log("Error while creating crc from zip file!", util.LOG_LEVEL_ERROR)
		else:						
			prev = 0
			for eachLine in open(str(filename),"rb"):
			    prev = zlib.crc32(eachLine, prev)					
			filecrc = "%0.8X"%(prev & 0xFFFFFFFF)
			Logutil.log("crc for current file: " +str(filecrc), util.LOG_LEVEL_INFO)
				
		return filecrc
		
		
	def getCRCFromFolder(self, filename):
		crcFromFolder = ''
		dirname = os.path.dirname(filename)		
		if(dirname != None):
			pathTuple = os.path.split(dirname)			
			if(len(pathTuple) == 2):
				crcFromFolder = pathTuple[1]				
				
		return crcFromFolder


	def findFilesByGameDescription(self, result, searchGameByCRCIgnoreRomName, searchGameByCRC, filecrcDict, fileFoldernameDict, fileGamenameDict, 
			useFoldernameAsCRC, useFilenameAsCRC):
		gamedesc = result['Game'][0]
		Logutil.log("game name in parsed result: " +str(gamedesc), util.LOG_LEVEL_DEBUG)				
		
		foldername = ''
		
		#find by filename
		#there is an option only to search by crc (maybe there are games with the same name but different crcs)
		if(searchGameByCRCIgnoreRomName == 'False'):
			try:
				gamedesc = gamedesc.lower()
				gamedesc = gamedesc.strip()
				filename = fileGamenameDict[gamedesc]
			except:
				filename = None
				
			if (filename != None):
				Logutil.log("result found by filename: " +gamedesc, util.LOG_LEVEL_INFO)				
				return filename, foldername
		
		#find by crc
		if(searchGameByCRC == 'True' or useFoldernameAsCRC == 'True' or useFilenameAsCRC == 'true'):
			try:
				resultFound = False
				resultcrcs = result['crc']
				for resultcrc in resultcrcs:
					Logutil.log("crc in parsed result: " +resultcrc, util.LOG_LEVEL_DEBUG)
					resultcrc = resultcrc.lower()
					resultcrc = resultcrc.strip()
					try:
						filename = filecrcDict[resultcrc]
					except:
						filename = None
					if(filename != None):
						Logutil.log("result found by crc: " +gamedesc, util.LOG_LEVEL_INFO)						
						return filename, foldername
						
					#TODO search for folder as option?
					if(useFoldernameAsCRC == 'True'):
						Logutil.log("using foldername as crc value", util.LOG_LEVEL_DEBUG)						
						try:
							filename = fileFoldernameDict[resultcrc]
							foldername = resultcrc
						except:
							filename = None
						if(filename != None):
							Logutil.log("result found by foldername crc: " +gamedesc, util.LOG_LEVEL_INFO)							
							return filename, foldername
							
					Logutil.log("using filename as crc value", util.LOG_LEVEL_DEBUG)										
					try:
						filename = fileGamenameDict[resultcrc]
					except:
						filename = None
					if(filename != None):
						Logutil.log("result found by filename crc: " +gamedesc, util.LOG_LEVEL_INFO)						
						return filename, foldername
						
			except Exception, (exc):
				Logutil.log("Error while checking crc results: " +str(exc), util.LOG_LEVEL_ERROR)
		
		return None, foldername
		
		
	def insertGameFromDesc(self, gamedescription, lastgamename, ignoreGameWithoutDesc, gamename, romCollectionRow, filenamelist, foldername, allowUpdate):
		
		if(gamedescription != Empty()):
			game = self.resolveParseResult(gamedescription.Game, 'Game')
		else:
			game = ''
				
		if(filenamelist == None or len(filenamelist) == 0):
			lastgamename = ""
			if(ignoreGameWithoutDesc == 'True'):
				Logutil.log("game " +game +" could not be found in parsed results. Game will not be imported.", util.LOG_LEVEL_WARNING)
				return
			else:
				#TODO game without description?
				Logutil.log("game " +game +" could not be found in parsed results. Game will not be imported.", util.LOG_LEVEL_WARNING)
				return
		else:
			lastgamename = game
		
		#get Console Name to import images via %CONSOLE%
		consoleId = romCollectionRow[2]									
		consoleRow = Console(self.gdb).getObjectById(consoleId)					
		if(consoleRow == None):						
			consoleName = None						
		else:
			consoleName = consoleRow[1]
		
		self.insertData(gamedescription, gamename, romCollectionRow[0], filenamelist, foldername, allowUpdate, consoleId, consoleName)
	
	
	def parseDescriptionFile(self, descriptionPath, descParserFile, gamename):
		descriptionfile = descriptionPath.replace("%GAME%", gamename)

		if(os.path.exists(descriptionfile)):
			Logutil.log("Parsing game description: " +descriptionfile, util.LOG_LEVEL_INFO)
			dp = DescriptionParser()
			
			try:
				results = dp.parseDescription(descriptionfile, descParserFile, gamename)
			except Exception, (exc):
				Logutil.log("an error occured while parsing game description: " +descriptionfile, util.LOG_LEVEL_WARNING)
				Logutil.log("Parser complains about: " +str(exc), util.LOG_LEVEL_WARNING)
				return None
							
			del dp
			
			return results
			
		else:
			Logutil.log("description file for game " +gamename +" could not be found. "\
				"Check if this path exists: " +descriptionfile, util.LOG_LEVEL_WARNING)
			return None
			
			
	def insertData(self, gamedescription, gamenameFromFile, romCollectionId, romFiles, foldername, allowUpdate, consoleId, consoleName):
		Logutil.log("Insert data", util.LOG_LEVEL_INFO)
				
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
		
			Logutil.log("Result Game (from parser) = " +str(gamedescription.Game), util.LOG_LEVEL_INFO)
			gamename = self.resolveParseResult(gamedescription.Game, 'Game')
			plot = self.resolveParseResult(gamedescription.Description, 'Description')
			
			Logutil.log("Result Game (as string) = " +gamename, util.LOG_LEVEL_INFO)
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
			
		for romFile in romFiles:
			self.insertFile(romFile, gameId, "rcb_rom", None, None, None, None)
		
		
		allPathRows = Path(self.gdb).getPathsByRomCollectionId(romCollectionId)
		for pathRow in allPathRows:
			Logutil.log("Additional data path: " +str(pathRow), util.LOG_LEVEL_INFO)
			files = self.resolvePath((pathRow[1],), gamename, gamenameFromFile, foldername, consoleName, publisher, developer)
			Logutil.log("Importing files: " +str(files), util.LOG_LEVEL_INFO)
			fileTypeRow = FileType(self.gdb).getObjectById(pathRow[2])
			Logutil.log("FileType: " +str(fileTypeRow), util.LOG_LEVEL_INFO)
			if(fileTypeRow == None):
				continue
			self.insertFiles(files, gameId, fileTypeRow[1], consoleId, publisherId, developerId, romCollectionId)
			
		
		"""
		manualPaths = Path(self.gdb).getManualPathsByRomCollectionId(romCollectionId)
		Logutil.log("manual path: " +str(manualPaths), util.LOG_LEVEL_INFO)
		manualFiles = self.resolvePath(manualPaths, gamename, gamenameFromFile, None, None, None)
		Logutil.log("manual files: " +str(manualFiles), util.LOG_LEVEL_INFO)
		self.insertFiles(manualFiles, gameId, "rcb_manual", None, None, None, None)
		
		configurationPaths = Path(self.gdb).getConfigurationPathsByRomCollectionId(romCollectionId)
		Logutil.log("configuration path: " +str(configurationPaths), util.LOG_LEVEL_INFO)
		configurationFiles = self.resolvePath(configurationPaths, gamename, gamenameFromFile, None, None, None)
		Logutil.log("configuration files: " +str(configurationFiles), util.LOG_LEVEL_INFO)
		self.insertFiles(configurationFiles, gameId, "rcb_configuration", None, None, None, None)
		"""		
				
		self.gdb.commit()
		
		
	def insertGame(self, gameName, description, romCollectionId, publisherId, developerId, reviewerId, yearId, 
				players, rating, votes, url, region, media, perspective, controller, originalTitle, alternateTitle, translatedBy, version, allowUpdate):
		# TODO unique by name an RC
		gameRow = Game(self.gdb).getGameByNameAndRomCollectionId(gameName, romCollectionId)
		if(gameRow == None):
			Logutil.log("Game does not exist in database. Insert game: " +gameName.encode('iso-8859-15'), util.LOG_LEVEL_INFO)
			Game(self.gdb).insert((gameName, description, None, None, romCollectionId, publisherId, developerId, reviewerId, yearId, 
				players, rating, votes, url, region, media, perspective, controller, 0, 0, originalTitle, alternateTitle, translatedBy, version))
			return self.gdb.cursor.lastrowid
		else:	
			if(allowUpdate == 'True'):
				Logutil.log("Game does exist in database. Update game: " +gameName, util.LOG_LEVEL_INFO)
				Game(self.gdb).update(('name', 'description', 'romCollectionId', 'publisherId', 'developerId', 'reviewerId', 'yearId', 'maxPlayers', 'rating', 'numVotes',
					'url', 'region', 'media', 'perspective', 'controllerType', 'originalTitle', 'alternateTitle', 'translatedBy', 'version'),
					(gameName, description, romCollectionId, publisherId, developerId, reviewerId, yearId, players, rating, votes, url, region, media, perspective, controller,
					originalTitle, alternateTitle, translatedBy, version),
					gameRow[0])
			else:
				Logutil.log("Game does exist in database but update is not allowed for current rom collection. game: " +gameName.encode('iso-8859-15'), util.LOG_LEVEL_INFO)
			
			return gameRow[0]
		
	
	def insertForeignKeyItem(self, result, itemName, gdbObject):
		Logutil.log("Result " +itemName +" (from Parser) = " +str(result), util.LOG_LEVEL_INFO)
		#if(result != Empty()):
		if(len(result) != 0):
			item = result[0].strip()
			Logutil.log("Result "  +itemName +" (as string) = " +item.encode('iso-8859-15'), util.LOG_LEVEL_INFO)
			itemRow = gdbObject.getOneByName(item)
			if(itemRow == None):	
				Logutil.log(itemName +" does not exist in database. Insert: " +item.encode('iso-8859-15'), util.LOG_LEVEL_INFO)
				gdbObject.insert((item,))
				itemId = self.gdb.cursor.lastrowid
			else:
				itemId = itemRow[0]
		else:
			itemId = None
			
		return itemId
		
	
	def insertForeignKeyItemList(self, resultList, itemName, gdbObject):	
		Logutil.log("Result " +itemName +" (from Parser) = " +str(resultList), util.LOG_LEVEL_INFO)
		idList = []
		
		for resultItem in resultList:			
			item = resultItem.strip()
			Logutil.log("Result " +itemName +" (as string) = " +item.encode('iso-8859-15'), util.LOG_LEVEL_INFO)
			itemRow = gdbObject.getOneByName(item)
			if(itemRow == None):
				Logutil.log(itemName +" does not exist in database. Insert: " +item.encode('iso-8859-15'), util.LOG_LEVEL_INFO)
				gdbObject.insert((item,))
				idList.append(self.gdb.cursor.lastrowid)
			else:
				idList.append(itemRow[0])
				
		return idList
		
		
	def resolvePath(self, paths, gamename, gamenameFromFile, foldername, consoleName, publisher, developer):		
		resolvedFiles = []				
				
		for path in paths:
			files = []
			Logutil.log("resolve path: " +path, util.LOG_LEVEL_INFO)
			
			if(path.find("%GAME%") > -1):
				pathnameFromGameName = path.replace("%GAME%", gamename)
				Logutil.log("resolved path from game name: " +pathnameFromGameName, util.LOG_LEVEL_INFO)				
				files = self.getFilesByWildcard(pathnameFromGameName)
				
				pathnameFromFile = path.replace("%GAME%", gamenameFromFile)
				if(gamename != gamenameFromFile and len(files) == 0):					
					Logutil.log("resolved path from rom file name: " +pathnameFromFile, util.LOG_LEVEL_INFO)					
					files = self.getFilesByWildcard(pathnameFromFile)
					
				pathnameFromFolder = path.replace("%GAME%", foldername)
				if(gamename != foldername and len(files) == 0):					
					Logutil.log("resolved path from rom folder name: " +pathnameFromFolder, util.LOG_LEVEL_INFO)					
					files = self.getFilesByWildcard(pathnameFromFolder)								
				
				#one last try with case insensitive search (on Linux we don't get files with case mismatches)
				if(len(files) == 0):
					files = self.getFilesByGameNameIgnoreCase(pathnameFromGameName)
				if(len(files) == 0):
					files = self.getFilesByGameNameIgnoreCase(pathnameFromFile)
				if(len(files) == 0):
					files = self.getFilesByGameNameIgnoreCase(pathnameFromFolder)
				
				
			#TODO could be done only once per RomCollection			
			if(path.find("%CONSOLE%") > -1 and consoleName != None and len(files) == 0):
				pathnameFromConsole = path.replace("%CONSOLE%", consoleName)
				Logutil.log("resolved path from console name: " +pathnameFromConsole, util.LOG_LEVEL_INFO)
				files = self.getFilesByWildcard(pathnameFromConsole)				
				
			if(path.find("%PUBLISHER%") > -1 and publisher != None and len(files) == 0):
				pathnameFromPublisher = path.replace("%PUBLISHER%", publisher)
				Logutil.log("resolved path from publisher name: " +pathnameFromPublisher, util.LOG_LEVEL_INFO)
				files = self.getFilesByWildcard(pathnameFromPublisher)				
				
			if(path.find("%DEVELOPER%") > -1 and developer != None and len(files) == 0):
				pathnameFromDeveloper = path.replace("%DEVELOPER%", developer)
				Logutil.log("resolved path from developer name: " +pathnameFromDeveloper, util.LOG_LEVEL_INFO)
				files = self.getFilesByWildcard(pathnameFromDeveloper)													
				
			if(len(files) == 0):
				Logutil.log("No files found for game %s at path %s. Make sure that file names are matching." %(gamename, path), util.LOG_LEVEL_WARNING)
			for file in files:
				if(os.path.exists(file)):
					resolvedFiles.append(file)
					
		return resolvedFiles
	
	
	def getFilesByWildcard(self, pathName):
		
		files = []
		
		try:
			# try glob with * wildcard
			files = glob.glob(pathName)
		except Exception, (exc):
			Logutil.log("Error using glob function in resolvePath " +str(exc), util.LOG_LEVEL_WARNING)
		
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
		Logutil.log("resolved files: " +str(files), util.LOG_LEVEL_INFO)
		
		
	def getFilesByGameNameIgnoreCase(self, pathname):
		
		files = []
		
		dirname = os.path.dirname(pathname)
		basename = os.path.basename(pathname)
		
		#search all Files that start with the first character of game name
		newpath = os.path.join(dirname, basename[0].upper() +'*')
		filesUpper = glob.glob(newpath)
		newpath = os.path.join(dirname, basename[0].lower() +'*')
		filesLower = glob.glob(newpath)
		
		allFiles = filesUpper + filesLower
		for file in allFiles:
			if(pathname.lower() == file.lower()):
				Logutil.log("Found path %s by search with ignore case." %pathname, util.LOG_LEVEL_WARNING)
				files.append(file)
				
		return files
		
		
	def resolveParseResult(self, result, itemName):
		Logutil.log("Result " +itemName +" (from Parser) = " +str(result), util.LOG_LEVEL_INFO)
		if(len(result) != 0):
			item = result[0].strip()
		else:
			item = ""
		Logutil.log("Result " +itemName +" (as string) = " +item.encode('iso-8859-15'), util.LOG_LEVEL_INFO)
		return item
	
	
	def insertFiles(self, fileNames, gameId, fileType, consoleId, publisherId, developerId, romCollectionId):
		for fileName in fileNames:
			self.insertFile(fileName, gameId, fileType, consoleId, publisherId, developerId, romCollectionId)
			
		
	def insertFile(self, fileName, gameId, fileType, consoleId, publisherId, developerId, romCollectionId):
		Logutil.log("Begin Insert file: " +fileName, util.LOG_LEVEL_DEBUG)
				
		fileTypeRow = FileType(self.gdb).getOneByName(fileType)
		if(fileTypeRow == None):
			Logutil.log("No filetype found for %s. Please check your config.xml" %fileType, util.LOG_LEVEL_WARNING)
			
		parentId = None
		
		#TODO console and romcollection could be done only once per RomCollection			
		#fileTypeRow[3] = parent
		if(fileTypeRow[3] == 'game'):
			Logutil.log("Insert file with parent game", util.LOG_LEVEL_INFO)
			parentId = gameId
		elif(fileTypeRow[3] == 'console'):
			Logutil.log("Insert file with parent console", util.LOG_LEVEL_INFO)
			parentId = consoleId
		elif(fileTypeRow[3] == 'romcollection'):
			Logutil.log("Insert file with parent rom collection", util.LOG_LEVEL_INFO)
			parentId = romCollectionId
		elif(fileTypeRow[3] == 'publisher'):
			Logutil.log("Insert file with parent publisher", util.LOG_LEVEL_INFO)
			parentId = publisherId
		elif(fileTypeRow[3] == 'developer'):
			Logutil.log("Insert file with parent developer", util.LOG_LEVEL_INFO)
			parentId = developerId
			
		fileRow = File(self.gdb).getFileByNameAndTypeAndParent(fileName, fileType, parentId)
		if(fileRow == None):
			Logutil.log("File does not exist in database. Insert file: " +fileName, util.LOG_LEVEL_INFO)
			File(self.gdb).insert((str(fileName), fileTypeRow[0], parentId))
				
		

	def exit(self):
		Logutil.log("Update finished", util.LOG_LEVEL_INFO)		
