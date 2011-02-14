
import os, sys, re
import getpass, string, glob
import codecs
import zipfile
import zlib
import time
from pysqlite2 import dbapi2 as sqlite

from config import *
from gamedatabase import *
from descriptionparserfactory import *
import util
from util import *
from pyscraper import *



class DBUpdate:		
	
	def __init__(self):
		pass
	
	Settings = util.getSettings()
	
	def updateDB(self, gdb, gui, updateOption, romCollections):
		self.gdb = gdb
			
		#self.scrapeResultsFile = self.openFile(os.path.join(util.getAddonDataPath(), 'scrapeResults.txt'))
		self.missingDescFile = self.openFile(os.path.join(util.getAddonDataPath(), 'scrapeResult_missingDesc.txt'))
		self.missingArtworkFile = self.openFile(os.path.join(util.getAddonDataPath(), 'scrapeResult_missingArtwork.txt'))
		self.possibleMismatchFile = self.openFile(os.path.join(util.getAddonDataPath(), 'scrapeResult_possibleMismatches.txt'))		
		
		Logutil.log("Start Update DB", util.LOG_LEVEL_INFO)
		
		Logutil.log("Iterating Rom Collections", util.LOG_LEVEL_INFO)
		rccount = 1
		
		continueUpdate = True
		
		for romCollection in romCollections.values():
			
			#timestamp1 = time.clock()
			
			#check if import was canceled
			if(not continueUpdate):
				Logutil.log('Game import canceled', util.LOG_LEVEL_INFO)
				break
				
			
			#prepare Header for ProgressDialog
			progDialogRCHeader = "Importing Rom Collection (%i / %i): %s" %(rccount, len(romCollections), romCollection.name)
			rccount = rccount + 1
			
			Logutil.log("current Rom Collection: " +romCollection.name, util.LOG_LEVEL_INFO)
			
			#self.scrapeResultsFile.write('~~~~~~~~~~~~~~~~~~~~~~~~\n' +romCollection.name +'\n' +'~~~~~~~~~~~~~~~~~~~~~~~~\n')
			self.missingDescFile.write('~~~~~~~~~~~~~~~~~~~~~~~~\n' +romCollection.name +'\n' +'~~~~~~~~~~~~~~~~~~~~~~~~\n')
			self.missingArtworkFile.write('~~~~~~~~~~~~~~~~~~~~~~~~\n' +romCollection.name +'\n' +'~~~~~~~~~~~~~~~~~~~~~~~~\n')
			self.possibleMismatchFile.write('~~~~~~~~~~~~~~~~~~~~~~~~\n' +romCollection.name +'\n' +'~~~~~~~~~~~~~~~~~~~~~~~~\n')
			self.possibleMismatchFile.write('gamename, filename\n')

			#Read settings for current Rom Collection
			Logutil.log("ignoreOnScan: " +str(romCollection.ignoreOnScan), util.LOG_LEVEL_INFO)
			if(romCollection.ignoreOnScan):
				Logutil.log("current Rom Collection will be ignored.", util.LOG_LEVEL_INFO)
				#self.scrapeResultsFile.write('Rom Collection will be ignored.\n')
				continue
									
			Logutil.log("using one description file per game: " +str(romCollection.descFilePerGame), util.LOG_LEVEL_INFO)						
			Logutil.log("update is allowed for current rom collection: " +str(romCollection.allowUpdate), util.LOG_LEVEL_INFO)			
			Logutil.log("search game by CRC: " +str(romCollection.searchGameByCRC), util.LOG_LEVEL_INFO)			
			Logutil.log("ignore rom filename when searching game by CRC: " +str(romCollection.searchGameByCRCIgnoreRomName), util.LOG_LEVEL_INFO)
						
			Logutil.log("use foldername as CRC: " +str(romCollection.useFoldernameAsCRC), util.LOG_LEVEL_INFO)			
			Logutil.log("use filename as CRC: " +str(romCollection.useFilenameAsCRC), util.LOG_LEVEL_INFO)
																
			Logutil.log("max folder depth: " +str(romCollection.maxFolderDepth), util.LOG_LEVEL_INFO)
			
			#check if we can find any roms with this configuration
			if(romCollection.searchGameByCRCIgnoreRomName and not romCollection.searchGameByCRC and not romCollection.descFilePerGame):
				Logutil.log("Configuration error: descFilePerGame = false, searchGameByCRCIgnoreRomName = true, searchGameByCRC = false." \
				"You won't find any description with this configuration!", util.LOG_LEVEL_ERROR)
				continue			
			
					
			files = self.getRomFilesByRomCollection(romCollection.romPaths, romCollection.maxFolderDepth)				
								
			lastgamenameFromFile = ""
			lastgamename = ""
			foldername = ''
			
			filecrcDict = {}
			fileGamenameDict = {}
			fileFoldernameDict = {}
			
			#always remember the crc of the first rom of multi rom games
			crcOfFirstGame = {}
			
			#itemCount is used for percentage in ProgressDialogGUI
			gui.itemCount = len(files) +1
			fileCount = 1
			
			Logutil.log("Start building file crcs", util.LOG_LEVEL_INFO)
			for filename in files:				
				gui.writeMsg(progDialogRCHeader, "Building file list...", "", fileCount)
				fileCount = fileCount +1
				
				gamename = self.getGamenameFromFilename(filename, romCollection)
				
				#check if we are handling one of the additional disks of a multi rom game
				isMultiRomGame = self.checkRomfileIsMultirom(gamename, lastgamename)
				
				#lastgamename may be overwritten by parsed gamename				
				lastgamename = gamename				
				
				gamename = gamename.strip()
				gamename = gamename.lower()
				
				#build dictionaries (key=gamename, filecrc or foldername; value=filenames) for later game search
				fileGamenameDict = self.buildFilenameDict(fileGamenameDict, isMultiRomGame, filename, gamename, fileGamenameDict, gamename, True)
					
				if(romCollection.searchGameByCRC):
					filecrc = self.getFileCRC(filename)
					#use crc of first rom if it is a multirom game
					if(not isMultiRomGame):
						try:
							crcOfFirstGame[gamename] = filecrc
							Logutil.log('Adding crc to crcOfFirstGame-dict: %s:%s' %(gamename, filecrc), util.LOG_LEVEL_DEBUG)
						except:							
							pass
					else:
						try:
							filecrc = crcOfFirstGame[gamename]
							Logutil.log('Read crc from crcOfFirstGame-dict: %s:%s' %(gamename, filecrc), util.LOG_LEVEL_DEBUG)
						except Exception, (exc):							
							pass
						
					filecrcDict = self.buildFilenameDict(filecrcDict, isMultiRomGame, filename, filecrc, fileGamenameDict, gamename, False)
				
				#Folder name of game may be used as crc value in description files					
				if(romCollection.useFoldernameAsCRC):
					foldername = self.getCRCFromFolder(filename)
					foldername = foldername.strip()
					foldername = foldername.lower()
					fileFoldernameDict = self.buildFilenameDict(fileFoldernameDict, isMultiRomGame, filename, foldername, fileGamenameDict, gamename, False)

			Logutil.log("Building file crcs done", util.LOG_LEVEL_INFO)
			
			#self.scrapeResultsFile.write('%s games total' %(str(len(fileGamenameDict))))
			
			#get fuzzyFactor before scraping
			matchingRatioIndex = self.Settings.getSetting(util.SETTING_RCB_FUZZYFACTOR)
			if (matchingRatioIndex == ''):
				matchingRatioIndex = 2
			fuzzyFactor = util.FUZZY_FACTOR_ENUM[int(matchingRatioIndex)]
			
			"""			
			#HACK: only use local nfo scraper if chosen in option dialog
			if(updateOption == util.SCRAPING_OPTION_LOCALNFO):				
				site = Site()
				site.name = 'local nfo'
				scrapers = []
				scraper = Scraper()				
				scraper.parseInstruction = os.path.join(util.RCBHOME, 'resources', 'scraper', '00 - local nfo.xml') 
				scraper.source = 'nfo'
				#TODO: check correct encoding
				#scraper.encoding = 'iso-8859-15'
				scrapers.append(scraper)
				site.scrapers = scrapers 				
				sites = []
				sites.append(site)
				
				romCollection.scraperSites = sites
			"""
				
			
			if(not romCollection.descFilePerGame and len(romCollection.scraperSites) > 0):
				Logutil.log("Searching for game in parsed results:", util.LOG_LEVEL_INFO)
				
				try:						
					fileCount = 1
					
					#first scraper must be the one for multiple games					
					if(len(romCollection.scraperSites[0].scrapers) == 0):
						Logutil.log('Configuration error: Configured scraper site does not contain any scrapers', util.LOG_LEVEL_ERROR)
						continue
						
					scraper = romCollection.scraperSites[0].scrapers[0]
					Logutil.log("start parsing with multi game scraper: " +str(romCollection.scraperSites[0].name), util.LOG_LEVEL_INFO)
					Logutil.log("using parser file: " +scraper.parseInstruction, util.LOG_LEVEL_INFO)
					Logutil.log("using game description: " +scraper.source, util.LOG_LEVEL_INFO)
											
					parser = DescriptionParserFactory.getParser(str(scraper.parseInstruction)) 										
					
					#parse description
					for result in parser.scanDescription(scraper.source, str(scraper.parseInstruction), scraper.encoding):
						
						isUpdate = False
						gameId = None
						filenamelist, foldername, filecrc = self.findFilesByGameDescription(result, romCollection, filecrcDict, fileFoldernameDict, fileGamenameDict)						
	
						if(filenamelist != None and len(filenamelist) > 0):
											
							gamenameFromFile = self.getGamenameFromFilename(filenamelist[0], romCollection)
							gamenameFromDesc = result['Game'][0]
							
							continueUpdate = gui.writeMsg(progDialogRCHeader, "Import game: " +str(gamenameFromDesc), "", fileCount)
							if(not continueUpdate):				
								Logutil.log('Game import canceled', util.LOG_LEVEL_INFO)
								break
							
							fileCount = fileCount +1
							
							Logutil.log('Start scraping info for game: ' +str(gamenameFromFile), LOG_LEVEL_INFO)
														
							#check if this file already exists in DB
							romFile = File(self.gdb).getFileByNameAndType(filenamelist[0], 0)
							if(romFile != None):
								isUpdate = True
								gameId = romFile[3]
								Logutil.log('File "%s" already exists in database.' %filenamelist[0], util.LOG_LEVEL_INFO)
								enableFullReimport = self.Settings.getSetting(util.SETTING_RCB_ENABLEFULLREIMPORT).upper() == 'TRUE'
								Logutil.log('Always rescan imported games = ' +str(enableFullReimport), util.LOG_LEVEL_INFO)
								if(enableFullReimport == False):
									Logutil.log('Won\'t scrape this game again. Set "Always rescan imported games" to True to force scraping.', util.LOG_LEVEL_INFO)
									continue
							
							#use additional scrapers
							if(len(romCollection.scraperSites) > 1):
								for i in range(1, len(romCollection.scraperSites)):
									scraperSite = romCollection.scraperSites[i]
									Logutil.log('using scraper: ' +scraperSite.name, util.LOG_LEVEL_INFO)
									urlsFromPreviousScrapers = []
									doContinue = False
									for scraper in scraperSite.scrapers:
										pyScraper = PyScraper()
										results, urlsFromPreviousScrapers, doContinue = pyScraper.scrapeResults(result, scraper, urlsFromPreviousScrapers, gamenameFromFile, foldername, filecrc, filenamelist[0], fuzzyFactor, updateOption)
									if(doContinue):
										continue										
						else:
							gamename = ''
							gamenameFromFile = ''								
							
						dialogDict = {'dialogHeaderKey':progDialogRCHeader, 'gameNameKey':gamenameFromFile, 'scraperSiteKey':{}, 'fileCountKey':fileCount}
						self.insertGameFromDesc(result, gamenameFromFile, romCollection, filenamelist, foldername, isUpdate, gameId, gui, dialogDict)
							
				except Exception, (exc):
					Logutil.log("an error occured while adding game " +gamename.encode('utf-8'), util.LOG_LEVEL_WARNING)
					Logutil.log("Error: " +str(exc), util.LOG_LEVEL_WARNING)
					continue
			else:	
				fileCount = 1				
				lastgamename = ''
				lastGameId = None
				
				for filename in files:
					
					isUpdate = False
					gameId = None
					
					gamenameFromFile = self.getGamenameFromFilename(filename, romCollection)
					
					#check if we are handling one of the additional disks of a multi rom game
					isMultiRomGame = self.checkRomfileIsMultirom(gamenameFromFile, lastgamename)
					lastgamename = gamenameFromFile
					
					if(isMultiRomGame):
						if(lastGameId == None):
							Logutil.log('Game detected as multi rom game, but lastGameId is None.', util.LOG_LEVEL_ERROR)
							continue
						fileType = FileType()
						fileType.id = 0
						fileType.name = "rcb_rom"
						fileType.parent = "game"
						self.insertFile(filename, lastGameId, fileType, None, None, None)
						continue
					
					Logutil.log('Start scraping info for game: ' +str(gamenameFromFile), LOG_LEVEL_INFO)						
					
					continueUpdate = gui.writeMsg(progDialogRCHeader, "Import game: " +gamenameFromFile, "", fileCount)
					if(not continueUpdate):				
						Logutil.log('Game import canceled', util.LOG_LEVEL_INFO)
						break
						
					
					#check if this file already exists in DB
					romFile = File(self.gdb).getFileByNameAndType(filename, 0)
					if(romFile != None):
						isUpdate = True
						gameId = romFile[3]
						Logutil.log('File "%s" already exists in database.' %filename, util.LOG_LEVEL_INFO)						
						enableFullReimport = self.Settings.getSetting(util.SETTING_RCB_ENABLEFULLREIMPORT).upper() == 'TRUE'
						Logutil.log('Always rescan imported games = ' +str(enableFullReimport), util.LOG_LEVEL_INFO)
						if(enableFullReimport == False):
							Logutil.log('Won\'t scrape this game again. Set "Always rescan imported games" to True to force scraping.', util.LOG_LEVEL_INFO)
							continue										
					
					foldername = os.path.dirname(filename)
					filecrc = self.getFileCRC(filename)																		
					
					results = {}
					artScrapers = {}					
					
					for scraperSite in romCollection.scraperSites:
						#Show Scraper Download Info in Dialog
						Logutil.log('Progress Scraper: ' +scraperSite.name, util.LOG_LEVEL_INFO)
						gui.writeMsg(progDialogRCHeader, "Import game: " +gamenameFromFile, scraperSite.name + " - downloading info", fileCount)
						
						Logutil.log('using scraper: ' +scraperSite.name, util.LOG_LEVEL_INFO)
						urlsFromPreviousScrapers = []						
						for scraper in scraperSite.scrapers:
							pyScraper = PyScraper()							
							results, urlsFromPreviousScrapers, doContinue = pyScraper.scrapeResults(results, scraper, urlsFromPreviousScrapers, gamenameFromFile, foldername, filecrc, filename, fuzzyFactor, updateOption)							
							if(doContinue):
								continue
					
						#Find Filetypes and Scrapers for Art Download					
						if(len(results) > 0):
							for path in romCollection.mediaPaths:
								thumbKey = 'Filetype' + path.fileType.name 
								if(len(self.resolveParseResult(results, thumbKey)) > 0):
									if((thumbKey in artScrapers) == 0):
										artScrapers[thumbKey] = scraperSite.name
					
					#print results
					if(len(results) == 0):
						lastgamename = ""
						gamedescription = None
					else:						
						gamedescription = results
						
					filenamelist = []
					filenamelist.append(filename)
					fileCount = fileCount +1

					#Variables to process Art Download Info
					dialogDict = {'dialogHeaderKey':progDialogRCHeader, 'gameNameKey':gamenameFromFile, 'scraperSiteKey':artScrapers, 'fileCountKey':fileCount}
					#Add 'gui' and 'dialogDict' parameters to function
					lastGameId = self.insertGameFromDesc(gamedescription, gamenameFromFile, romCollection, filenamelist, foldername, isUpdate, gameId, gui, dialogDict)													
			
			#timestamp2 = time.clock()
			#diff = (timestamp2 - timestamp1) * 1000		
			#print "load %i games in %d ms" % (self.getListSize(), diff)
					
		gui.writeMsg("Done.", "", "", gui.itemCount)
		self.exit()
		return True, ''
	
	
	
	def getRomFilesByRomCollection(self, romPaths, maxFolderDepth):
				
		Logutil.log("Rom path: " +str(romPaths), util.LOG_LEVEL_INFO)
				
		Logutil.log("Reading rom files", util.LOG_LEVEL_INFO)
		files = []
		for romPath in romPaths:
			files = self.walkDownPath(files, romPath, maxFolderDepth)
			
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
			allFiles = [f.decode(sys.getfilesystemencoding()).encode('utf-8') for f in glob.glob(newRomPath)]
			Logutil.log( "all files in newRomPath: " +str(allFiles), util.LOG_LEVEL_DEBUG)
		
			#did not find appendall or something like this
			files.extend(allFiles)
		
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
		
		
	def getGamenameFromFilename(self, filename, romCollection):		
					
		Logutil.log("current rom file: " +str(filename), util.LOG_LEVEL_INFO)

		#build friendly romname
		if(not romCollection.useFoldernameAsGamename):
			gamename = os.path.basename(filename)
		else:
			gamename = os.path.basename(os.path.dirname(filename))
			
		Logutil.log("gamename (file): " +gamename, util.LOG_LEVEL_INFO)
						
		dpIndex = gamename.lower().find(romCollection.diskPrefix.lower())
		if dpIndex > -1:
			gamename = gamename[0:dpIndex]			
		else:
			gamename = os.path.splitext(gamename)[0]					
		
		Logutil.log("gamename (friendly): " +gamename, util.LOG_LEVEL_INFO)		
		
		return gamename
		
		
	def checkRomfileIsMultirom(self, gamename, lastgamename):		
	
		#XBOX Hack: rom files will always be named default.xbe: always detected as multi rom without this hack
		if(gamename == lastgamename and lastgamename.lower() != 'default'):		
			Logutil.log("handling multi rom game: " +lastgamename, util.LOG_LEVEL_INFO)			
			return True
		return False
		
		
	def buildFilenameDict(self, dict, isMultiRomGame, filename, key, fileGamenameDict, gamename, appendToGamenameDict):				
		
		try:											
			if(not isMultiRomGame):
				filenamelist = []
				filenamelist.append(filename)
				dict[key] = filenamelist
				Logutil.log('Add filename "%s" with key "%s"' %(filename, key), util.LOG_LEVEL_DEBUG)
			else:
				filenamelist = fileGamenameDict[gamename]
				if(appendToGamenameDict):
					filenamelist.append(filename)
				dict[key] = filenamelist
				Logutil.log('Add filename "%s" to multirom game with key "%s"' %(filename, key), util.LOG_LEVEL_DEBUG)
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
				
		filecrc = filecrc.strip()
		filecrc = filecrc.lower()
		return filecrc
		
		
	def getCRCFromFolder(self, filename):
		crcFromFolder = ''
		dirname = os.path.dirname(filename)		
		if(dirname != None):
			pathTuple = os.path.split(dirname)			
			if(len(pathTuple) == 2):
				crcFromFolder = pathTuple[1]				
				
		return crcFromFolder


	def findFilesByGameDescription(self, result, romCollection, filecrcDict, fileFoldernameDict, fileGamenameDict):
		gamedesc = result['Game'][0]
		Logutil.log("game name in parsed result: " +str(gamedesc), util.LOG_LEVEL_DEBUG)				
		
		foldername = ''
		filecrc = ''
		
		#find by filename
		#there is an option only to search by crc (maybe there are games with the same name but different crcs)
		if(not romCollection.searchGameByCRCIgnoreRomName):
			try:
				gamedesc = gamedesc.lower()
				gamedesc = gamedesc.strip()
				filename = fileGamenameDict[gamedesc]
			except:
				filename = None
				
			if (filename != None):
				Logutil.log("result found by filename: " +gamedesc, util.LOG_LEVEL_INFO)				
				return filename, foldername, filecrc
		
		#find by crc
		if(romCollection.searchGameByCRC or romCollection.useFoldernameAsCRC or romCollection.useFilenameAsCRC):
			try:
				resultFound = False
				resultcrcs = result['crc']
				for resultcrc in resultcrcs:
					Logutil.log("crc in parsed result: " +resultcrc, util.LOG_LEVEL_DEBUG)
					resultcrc = resultcrc.lower()
					resultcrc = resultcrc.strip()
					try:
						filename = filecrcDict[resultcrc]
						filecrc = resultcrc
					except:
						filename = None
					if(filename != None):
						Logutil.log("result found by crc: " +gamedesc, util.LOG_LEVEL_INFO)						
						return filename, foldername, filecrc
						
					#search for folder
					if(romCollection.useFoldernameAsCRC):
						Logutil.log("using foldername as crc value", util.LOG_LEVEL_DEBUG)						
						try:
							filename = fileFoldernameDict[resultcrc]
							foldername = resultcrc
						except:
							filename = None
						if(filename != None):
							Logutil.log("result found by foldername crc: " +gamedesc, util.LOG_LEVEL_INFO)							
							return filename, foldername, filecrc
							
					Logutil.log("using filename as crc value", util.LOG_LEVEL_DEBUG)										
					try:
						filename = fileGamenameDict[resultcrc]
					except:
						filename = None
					if(filename != None):
						Logutil.log("result found by filename crc: " +gamedesc, util.LOG_LEVEL_INFO)						
						return filename, foldername, filecrc
						
			except Exception, (exc):
				Logutil.log("Error while checking crc results: " +str(exc), util.LOG_LEVEL_ERROR)
		
		return None, foldername, filecrc
		
				
	def insertGameFromDesc(self, gamedescription, gamename, romCollection, filenamelist, foldername, isUpdate, gameId, gui, dialogDict=''):								
		if(gamedescription != None):
			game = self.resolveParseResult(gamedescription, 'Game')
		else:
			self.missingDescFile.write('%s\n' %gamename)
			
			ignoreGameWithoutDesc = self.Settings.getSetting(util.SETTING_RCB_IGNOREGAMEWITHOUTDESC).upper() == 'TRUE'
			if(ignoreGameWithoutDesc):
				Logutil.log('No description found for game "%s". Game will not be imported.' %gamename, util.LOG_LEVEL_WARNING)
				return None
			game = ''
						
		if(filenamelist == None or len(filenamelist) == 0):
			Logutil.log("game " +game +" was found in parsed results but not in your rom collection.", util.LOG_LEVEL_WARNING)
			return None	
					
		gameId = self.insertData(gamedescription, gamename, romCollection, filenamelist, foldername, isUpdate, gameId, gui, dialogDict)
		return gameId
	
	
			
	def insertData(self, gamedescription, gamenameFromFile, romCollection, romFiles, foldername, isUpdate, gameId, gui, dialogDict=''):
		Logutil.log("Insert data", util.LOG_LEVEL_INFO)
		
		publisher = self.resolveParseResult(gamedescription, 'Publisher')
		developer = self.resolveParseResult(gamedescription, 'Developer')
		year = self.resolveParseResult(gamedescription, 'ReleaseYear')
		
		yearId = self.insertForeignKeyItem(gamedescription, 'ReleaseYear', Year(self.gdb))
		genreIds = self.insertForeignKeyItemList(gamedescription, 'Genre', Genre(self.gdb))		
		publisherId = self.insertForeignKeyItem(gamedescription, 'Publisher', Publisher(self.gdb))
		developerId = self.insertForeignKeyItem(gamedescription, 'Developer', Developer(self.gdb))
		reviewerId = self.insertForeignKeyItem(gamedescription, 'Reviewer', Reviewer(self.gdb))	
		
		region = self.resolveParseResult(gamedescription, 'Region')		
		media = self.resolveParseResult(gamedescription, 'Media')
		controller = self.resolveParseResult(gamedescription, 'Controller')
		players = self.resolveParseResult(gamedescription, 'Players')		
		rating = self.resolveParseResult(gamedescription, 'Rating')
		votes = self.resolveParseResult(gamedescription, 'Votes')
		url = self.resolveParseResult(gamedescription, 'URL')
		perspective = self.resolveParseResult(gamedescription, 'Perspective')
		originalTitle = self.resolveParseResult(gamedescription, 'OriginalTitle')
		alternateTitle = self.resolveParseResult(gamedescription, 'AlternateTitle')
		translatedBy = self.resolveParseResult(gamedescription, 'TranslatedBy')
		version = self.resolveParseResult(gamedescription, 'Version')								
		plot = self.resolveParseResult(gamedescription, 'Description')
		
		if(gamedescription != None):
			gamename = self.resolveParseResult(gamedescription, 'Game')
			if(gamename != gamenameFromFile):
				self.possibleMismatchFile.write('%s, %s\n' %(gamename, gamenameFromFile))
			
			if(gamename == ""):
				gamename = gamenameFromFile
		else:
			gamename = gamenameFromFile
			
		#create Nfo file with game properties
		createNfoFile = self.Settings.getSetting(util.SETTING_RCB_CREATENFOFILE).upper() == 'TRUE'	
		if(createNfoFile):
			self.createNfoFromDesc(gamename, plot, romCollection.name, publisher, developer, year, 
			players, rating, votes, url, region, media, perspective, controller, originalTitle, alternateTitle, version, gamedescription, romFiles[0], gamenameFromFile)
		
		artWorkFound = False
		artworkfiles = {}
		for path in romCollection.mediaPaths:
						
			Logutil.log("FileType: " +str(path.fileType.name), util.LOG_LEVEL_INFO)			
			
			#TODO replace %ROMCOLLECTION%, %PUBLISHER%, ... 
			fileName = path.path.replace("%GAME%", gamenameFromFile)
						
			self.getThumbFromOnlineSource(gamedescription, path.fileType.name, fileName, gui, dialogDict)
			
			Logutil.log("Additional data path: " +str(path.path), util.LOG_LEVEL_DEBUG)
			files = self.resolvePath((path.path,), gamename, gamenameFromFile, foldername, romCollection.name, publisher, developer)
			if(len(files) > 0):
				imagePath = str(self.resolvePath((path.path,), gamename, gamenameFromFile, foldername, romCollection.name, publisher, developer))
				staticImageCheck = imagePath.find(gamenameFromFile)	
				
				#make sure that it was no default image that was found here
				if(staticImageCheck != -1):
					artWorkFound = True					
			else:
				self.missingArtworkFile.write('%s (filename: %s) (%s)\n' %(gamename, gamenameFromFile, path.fileType.name))
			
			artworkfiles[path.fileType] = files
				
		if(not artWorkFound):
			ignoreGamesWithoutArtwork = self.Settings.getSetting(util.SETTING_RCB_IGNOREGAMEWITHOUTARTWORK).upper() == 'TRUE'
			if(ignoreGamesWithoutArtwork):								
				Logutil.log('No artwork found for game "%s". Game will not be imported.' %gamenameFromFile, util.LOG_LEVEL_WARNING)
				self.missingArtworkFile.write('--> No artwork found for game "%s". Game will not be imported.\n' %gamename)
				return None
						
		gameId = self.insertGame(gamename, plot, romCollection.id, publisherId, developerId, reviewerId, yearId, 
			players, rating, votes, url, region, media, perspective, controller, originalTitle, alternateTitle, translatedBy, version, isUpdate, gameId, romCollection.allowUpdate, )
		
		if(gameId == None):
			return None
						
		for genreId in genreIds:
			genreGame = GenreGame(self.gdb).getGenreGameByGenreIdAndGameId(genreId, gameId)
			if(genreGame == None):
				GenreGame(self.gdb).insert((genreId, gameId))
			
		for romFile in romFiles:
			fileType = FileType()
			fileType.id = 0
			fileType.name = "rcb_rom"
			fileType.parent = "game"
			self.insertFile(romFile, gameId, fileType, None, None, None)				
		
		Logutil.log("Importing files: " +str(artworkfiles), util.LOG_LEVEL_INFO)		
		for fileType in artworkfiles.keys():
			for fileName in artworkfiles[fileType]:
				self.insertFile(fileName, gameId, fileType, romCollection.id, publisherId, developerId)		
				
		self.gdb.commit()
		return gameId
		
		
	def insertGame(self, gameName, description, romCollectionId, publisherId, developerId, reviewerId, yearId, 
				players, rating, votes, url, region, media, perspective, controller, originalTitle, alternateTitle, translatedBy, version, isUpdate, gameId, allowUpdate):		
		
		try:
			if(not isUpdate):
				Logutil.log("Game does not exist in database. Insert game: " +gameName, util.LOG_LEVEL_INFO)
				Game(self.gdb).insert((gameName, description, None, None, romCollectionId, publisherId, developerId, reviewerId, yearId, 
					players, rating, votes, url, region, media, perspective, controller, 0, 0, originalTitle, alternateTitle, translatedBy, version))
				return self.gdb.cursor.lastrowid
			else:	
				if(allowUpdate):
					#TODO
					gameRow = None
					Logutil.log("Game does exist in database. Update game: " +gameName, util.LOG_LEVEL_INFO)
					Game(self.gdb).update(('name', 'description', 'romCollectionId', 'publisherId', 'developerId', 'reviewerId', 'yearId', 'maxPlayers', 'rating', 'numVotes',
						'url', 'region', 'media', 'perspective', 'controllerType', 'originalTitle', 'alternateTitle', 'translatedBy', 'version'),
						(gameName, description, romCollectionId, publisherId, developerId, reviewerId, yearId, players, rating, votes, url, region, media, perspective, controller,
						originalTitle, alternateTitle, translatedBy, version),
						gameId)
				else:
					Logutil.log("Game does exist in database but update is not allowed for current rom collection. game: " +gameName, util.LOG_LEVEL_INFO)
				
				return gameId
		except Exception, (exc):
			Logutil.log("An error occured while adding game '%s'. Error: %s" %(gameName, str(exc)), util.LOG_LEVEL_INFO)
			return None
			
		
	
	def insertForeignKeyItem(self, result, itemName, gdbObject):
		
		item = self.resolveParseResult(result, itemName)
						
		if(item != "" and item != None):
			itemRow = gdbObject.getOneByName(item)
			if(itemRow == None):	
				Logutil.log(itemName +" does not exist in database. Insert: " +item, util.LOG_LEVEL_INFO)
				gdbObject.insert((item,))
				itemId = self.gdb.cursor.lastrowid
			else:
				itemId = itemRow[0]
		else:
			itemId = None
			
		return itemId
		
	
	def insertForeignKeyItemList(self, result, itemName, gdbObject):
		idList = []				
				
		try:
			itemList = result[itemName]
			Logutil.log("Result " +itemName +" = " +str(itemList), util.LOG_LEVEL_INFO)
		except:
			Logutil.log("Error while resolving item: " +itemName, util.LOG_LEVEL_WARNING)
			return idList				
		
		for item in itemList:
			item = self.stripHTMLTags(item)
			
			itemRow = gdbObject.getOneByName(item)
			if(itemRow == None):
				Logutil.log(itemName +" does not exist in database. Insert: " +item, util.LOG_LEVEL_INFO)
				gdbObject.insert((item,))
				idList.append(self.gdb.cursor.lastrowid)
			else:
				idList.append(itemRow[0])
				
		return idList
		
		
	def resolvePath(self, paths, gamename, gamenameFromFile, foldername, romCollectionName, publisher, developer):		
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
			if(path.find("%ROMCOLLECTION%") > -1 and romCollectionName != None and len(files) == 0):
				pathnameFromRomCollection = path.replace("%ROMCOLLECTION%", romCollectionName)
				Logutil.log("resolved path from rom collection name: " +pathnameFromRomCollection, util.LOG_LEVEL_INFO)
				files = self.getFilesByWildcard(pathnameFromRomCollection)				
				
			if(path.find("%PUBLISHER%") > -1 and publisher != None and len(files) == 0):
				pathnameFromPublisher = path.replace("%PUBLISHER%", publisher)
				Logutil.log("resolved path from publisher name: " +pathnameFromPublisher, util.LOG_LEVEL_INFO)
				files = self.getFilesByWildcard(pathnameFromPublisher)				
				
			if(path.find("%DEVELOPER%") > -1 and developer != None and len(files) == 0):
				pathnameFromDeveloper = path.replace("%DEVELOPER%", developer)
				Logutil.log("resolved path from developer name: " +pathnameFromDeveloper, util.LOG_LEVEL_INFO)
				files = self.getFilesByWildcard(pathnameFromDeveloper)													
			
			if(path.find("%GAME%") == -1 & path.find("%ROMCOLLECTION%") == -1 & path.find("%PUBLISHER%") == -1 & path.find("%DEVELOPER%") == -1):
				pathnameFromStaticFile = path
				Logutil.log("using static defined media file from path: " + pathnameFromStaticFile, util.LOG_LEVEL_INFO)
				files = self.getFilesByWildcard(pathnameFromStaticFile)			
				
			if(len(files) == 0):
				Logutil.log('No files found for game "%s" at path "%s". Make sure that file names are matching.' %(gamename, path), util.LOG_LEVEL_WARNING)
			for file in files:
				if(os.path.exists(file)):
					resolvedFiles.append(file)
					
		return resolvedFiles
	
	
	def getFilesByWildcard(self, pathName):
		
		files = []
		
		try:
			# try glob with * wildcard
			files = glob.glob(pathName)
			
			if(len(files) == 0):				
				squares = re.findall('\s\[.*\]',pathName)				
				if(squares != None and len(squares) >= 1):
					Logutil.log('Replacing [...] with *', util.LOG_LEVEL_INFO)
					for square in squares:						
						pathName = pathName.replace(square, '*')
				
					Logutil.log('new pathname: ' +str(pathName), util.LOG_LEVEL_INFO)
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
				Logutil.log('Found path "%s" by search with ignore case.' %pathname, util.LOG_LEVEL_WARNING)
				files.append(file)
				
		return files
		
		
	def resolveParseResult(self, result, itemName):
		
		resultValue = ""
		
		try:			
			resultValue = result[itemName][0]
			
			if(itemName == 'ReleaseYear' and resultValue != None):
				if(type(resultValue) is time.struct_time):
					resultValue = str(resultValue[0])
				elif(len(resultValue) > 4):
					resultValueOrig = resultValue
					resultValue = resultValue[0:4]
					try:
						#year must be numeric
						int(resultValue)
					except:
						resultValue = resultValueOrig[len(resultValueOrig) -4:]
						try:
							int(resultValue)
						except:
							resultValue = ''
							
			#replace and remove HTML tags
			resultValue = self.stripHTMLTags(resultValue)
			resultValue = resultValue.strip()
									
		except Exception, (exc):
			Logutil.log("Error while resolving item: " +itemName +" : " +str(exc), util.LOG_LEVEL_WARNING)
						
		try:
			Logutil.log("Result " +itemName +" = " +resultValue, util.LOG_LEVEL_DEBUG)
		except:
			pass
				
		return resultValue
	
	
	def stripHTMLTags(self, inputString):
				
		inputString = util.html_unescape(inputString)
				
		#remove html tags and double spaces
		intag = [False]
		lastSpace = [False]
		def chk(c):
			if intag[0]:
				intag[0] = (c != '>')
				lastSpace[0] = (c == ' ')
				return False
			elif c == '<':
				intag[0] = True
				lastSpace[0] = (c == ' ')
				return False
			if(c == ' ' and lastSpace[0]):
				lastSpace[0] = (c == ' ')
				return False
			lastSpace[0] = (c == ' ')
			return True
		
		return ''.join(c for c in inputString if chk(c))


	def createNfoFromDesc(self, gamename, plot, romCollectionName, publisher, developer, year, players, rating, votes, 
						url, region, media, perspective, controller, originalTitle, alternateTitle, version, gamedescription, romFile, gameNameFromFile):
		
		root = Element('game')
		SubElement(root, 'title').text = gamename		
		SubElement(root, 'originalTitle').text = originalTitle
		SubElement(root, 'alternateTitle').text = alternateTitle
		SubElement(root, 'platform').text = romCollectionName
		SubElement(root, 'plot').text = plot
		SubElement(root, 'publisher').text = publisher
		SubElement(root, 'developer').text = developer
		SubElement(root, 'year').text = year
				
		try:
			genreList = gamedescription['Genre']			
		except:
			genreList = []
		
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
		
		#write file		
		try:
			util.indentXml(root)
			tree = ElementTree(root)
			
			romDir = os.path.dirname(romFile)
			Logutil.log('Romdir: ' +str(romDir), util.LOG_LEVEL_INFO)
			nfoFile = os.path.join(romDir, gameNameFromFile +'.nfo')
			
			if (not os.path.isfile(nfoFile)):
				Logutil.log('Writing NfoFile: ' +str(nfoFile), util.LOG_LEVEL_INFO)
			else:
				Logutil.log('NfoFile already exists. Wont overwrite file: ' +str(nfoFile), util.LOG_LEVEL_INFO)
				return
												
			tree.write(nfoFile)					
			
		except Exception, (exc):
			print("Error: Cannot write game.nfo: " +str(exc))		
			
		
	def insertFile(self, fileName, gameId, fileType, romCollectionId, publisherId, developerId):
		Logutil.log("Begin Insert file: " +fileName, util.LOG_LEVEL_DEBUG)										
		
		parentId = None
		
		#TODO console and romcollection could be done only once per RomCollection			
		#fileTypeRow[3] = parent
		if(fileType.parent == 'game'):
			Logutil.log("Insert file with parent game", util.LOG_LEVEL_INFO)
			parentId = gameId
		elif(fileType.parent == 'romcollection'):
			Logutil.log("Insert file with parent romcollection", util.LOG_LEVEL_INFO)
			parentId = romCollectionId		
		elif(fileType.parent == 'publisher'):
			Logutil.log("Insert file with parent publisher", util.LOG_LEVEL_INFO)
			parentId = publisherId
		elif(fileType.parent == 'developer'):
			Logutil.log("Insert file with parent developer", util.LOG_LEVEL_INFO)
			parentId = developerId
			
		fileRow = File(self.gdb).getFileByNameAndTypeAndParent(fileName, fileType.id, parentId)
		if(fileRow == None):
			Logutil.log("File does not exist in database. Insert file: " +fileName, util.LOG_LEVEL_INFO)
			File(self.gdb).insert((str(fileName), fileType.id, parentId))
				
	
	def getThumbFromOnlineSource(self, gamedescription, fileType, fileName, gui, dialogDict=''):
		Logutil.log("Get thumb from online source", util.LOG_LEVEL_INFO)
		try:			
			#maybe we got a thumb url from desc parser
			thumbKey = 'Filetype' +fileType
			Logutil.log("using key: " +thumbKey, util.LOG_LEVEL_INFO)
			thumbUrl = self.resolveParseResult(gamedescription, thumbKey)			
			if(thumbUrl == ''):
				return
			
			Logutil.log("Get thumb from url: " +str(thumbUrl), util.LOG_LEVEL_INFO)
			
			rootExtFile = os.path.splitext(fileName)
			rootExtUrl = os.path.splitext(thumbUrl)
			
			if(len(rootExtUrl) == 2 and len(rootExtFile) != 0):
				fileName = rootExtFile[0] + rootExtUrl[1]
				gameName = rootExtFile[0] + ".*"
				files = self.getFilesByWildcard(gameName)
			
			#check if folder exists
			dirname = os.path.dirname(fileName)
			if(not os.path.isdir(dirname)):
				os.mkdir(dirname)
			
			Logutil.log("Download file to: " +str(fileName), util.LOG_LEVEL_INFO)			
			if(len(files) == 0):
				Logutil.log("File does not exist. Starting download.", util.LOG_LEVEL_INFO)
				
				#Dialog Status Art Download
				if(dialogDict != ''):
					progDialogRCHeader = dialogDict["dialogHeaderKey"]
					gamenameFromFile = dialogDict["gameNameKey"]
					scraperSiteName = dialogDict["scraperSiteKey"]
					fileCount = dialogDict["fileCountKey"]
					gui.writeMsg(progDialogRCHeader, "Import game: " +gamenameFromFile, str(scraperSiteName[thumbKey]) + " - downloading art", fileCount)

				# fetch thumbnail and save to filepath
				urllib.urlretrieve( thumbUrl, str(fileName))
				# cleanup any remaining urllib cache
				urllib.urlcleanup()
				Logutil.log("Download finished.", util.LOG_LEVEL_INFO)
			else:
				Logutil.log("File already exists. Won't download again.", util.LOG_LEVEL_INFO)
		except Exception, (exc):
			Logutil.log("Error in getThumbFromOnlineSource: " +str(exc), util.LOG_LEVEL_WARNING)						


	def openFile(self, filename):
		try:			
			filehandle = open(filename,'w')		
		except Exception, (exc):			
			Logutil.log('Cannot write to file "%s". Error: "%s"' %(filename, str(exc)), util.LOG_LEVEL_WARNING)
			return None
		
		return filehandle
		

	def exit(self):
		
		try:
			self.missingArtworkFile.close()
			self.missingDescFile.close()
		except:
			pass
		
		Logutil.log("Update finished", util.LOG_LEVEL_INFO)		
