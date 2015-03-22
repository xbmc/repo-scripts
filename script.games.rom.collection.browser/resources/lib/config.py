import os

import util
import urllib
import helper
from util import *
from xml.etree.ElementTree import *



#friendly name : db column, missing filter statement
gameproperties = {'Title' : ['name', "name = ''"],
				'Description' : ['description', "description = ''"],				
				'Genre' : ['genre', "Id NOT IN (SELECT GameId From GenreGame)"],
				'Developer' : ['developerId', "developerId is NULL"],
				'Publisher' : ['publisherId', "publisherId is NULL"],
				'Reviewer' : ['reviewerId', "reviewerId is NULL"],
				'Release Year' : ['yearId', "yearId is NULL"],
				'Rating' : ['rating', "rating = ''"],
				'Votes' : ['numVotes', "numVotes is NULL"],
				'Region' : ['region', "region = ''"],
				'Media' : ['media', "media = ''"],	
				'Max. Players' : ['maxPlayers', "maxPlayers = ''"],
				'Controller' : ['controllerType', "controllerType = ''"],
				'Perspective' : ['perspective', "perspective = ''"],
				'Original Title' : ['originalTitle', "originalTitle = ''"],
				'Alternate Title' : ['alternateTitle', "alternateTitle = ''"],
				'Translated By' : ['translatedBy', "translatedBy = ''"],
				'Version' : ['version', "version = ''"],
				'Url' : ['url', "url = ''"]
				}


consoleDict = {
			#name, mobygames-id, thegamesdb, archive vg
			'Other' : ['0', '', ''],
			'3DO' : ['35', '3DO', '3do'],
			'Amiga' : ['19', 'Amiga', 'amiga'],
			'Amiga CD32' : ['56', '', 'cd32'],
			'Amstrad CPC' : ['60', 'Amstrad CPC', 'cpc'],
			'Apple II' : ['31', '', 'appleii'],
			'Atari 2600' : ['28', 'Atari 2600', 'atari2600'],
			'Atari 5200' : ['33', 'Atari 5200', 'atari5200'],
			'Atari 7800' : ['34', 'Atari 7800', 'atari7800'],
			'Atari 8-bit' : ['39', '', 'atari8bit'],
			'Atari ST' : ['24', '', 'ast'],
			'BBC Micro' : ['92', '', 'bbc'],
			'BREW' : ['63', '', ''],
			'CD-i' : ['73', '', 'cdi'], 
			'Channel F' : ['76', '', 'channelf'],  
			'ColecoVision' : ['29', 'Colecovision', 'colecovision'],
			'Commodore 128' : ['61', '', ''],
			'Commodore 64' : ['27', 'Commodore 64', 'c64'],
			'Commodore PET/CBM' : ['77', '', 'pet'],  
			'DoJa' : ['72', '', ''],
			'DOS' : ['2', '', ''],
			'Dragon 32/64' : ['79', '', ''],  
			'Dreamcast' : ['8', 'Sega Dreamcast', 'dreamcast'],
			'Electron' : ['93', '', ''],
			'ExEn' : ['70', '', ''],
			'Game Boy' : ['10', 'Nintendo Gameboy', 'gameboy'],
			'Game Boy Advance' : ['12', 'Nintendo Gameboy Advance', 'gba'],  
			'Game Boy Color' : ['11', 'Nintendo Game Boy Color', 'gbc'],
			'GameCube' : ['14', 'Nintendo GameCube', 'gamecube'],
			'Game Gear' : ['25', 'Sega Game Gear', 'gamegear'],
			'Genesis' : ['16', 'Sega Genesis', 'genesis'],
			'Gizmondo' : ['55', '', 'gizmondo'],
			'Intellivision' : ['30', 'Intellivision', 'intellivision'],
			'Jaguar' : ['17', 'Atari Jaguar', 'jaguar'],
			'Linux' : ['1', '', ''],
			'Lynx' : ['18', '', 'lynx'],
			'Macintosh' : ['74', 'Mac OS', ''],
			'MAME' : ['0', 'Arcade', ''],
			'Mophun' : ['71', '', ''],
			'MSX' : ['57', '', 'msx'],
			'Neo Geo' : ['36', 'NeoGeo', 'neo'],
			'Neo Geo CD' : ['54', '', 'neogeocd'],
			'Neo Geo Pocket' : ['52', '', ''],
			'Neo Geo Pocket Color' : ['53', '', 'ngpc'],  
			'NES' : ['22', 'Nintendo Entertainment System (NES)', 'nes'],
			'N-Gage' : ['32', '', 'ngage'],
			'Nintendo 64' : ['9', 'Nintendo 64', 'n64'],  
			'Nintendo DS' : ['44', 'Nintendo DS', ''],
			'Nintendo DSi' : ['87', '', ''],
			'Odyssey' : ['75', '', 'odyssey'],
			'Odyssey 2' : ['78', '', 'odyssey2'],
			'PC-88' : ['94', '', 'pc88'],
			'PC-98' : ['95', '', 'pc98'],
			'PC Booter' : ['4', '', ''],
			'PC-FX' : ['59', '', 'pcfx'],
			'PlayStation' : ['6', 'Sony Playstation', 'ps'],  
			'PlayStation 2' : ['7', 'Sony Playstation 2', 'ps2'],
			'PlayStation 3' : ['81', 'Sony Playstation 3', ''],
			'PSP' : ['46', 'Sony PSP', ''],
			'SEGA 32X' : ['21', 'Sega 32X', 'sega32x'],  
			'SEGA CD' : ['20', 'Sega CD', 'segacd'],
			'SEGA Master System' : ['26', 'Sega Master System', 'sms'],  
			'SEGA Saturn' : ['23', 'Sega Saturn', 'saturn'],
			'SNES' : ['15', 'Super Nintendo (SNES)', 'snes'],
			'Spectravideo' : ['85', '', ''],
			'TI-99/4A' : ['47', '', 'ti99'],
			'TRS-80' : ['58', '', ''],
			'TRS-80 CoCo' : ['62', '', ''],  
			'TurboGrafx-16' : ['40', 'TurboGrafx 16', 'tg16'],
			'TurboGrafx CD' : ['45', '', ''],
			'Vectrex' : ['37', '', 'vectrex'],
			'VIC-20' : ['43', '', 'vic20'],
			'Virtual Boy' : ['38', 'Nintendo Virtual Boy', 'virtualboy'],  
			'V.Smile' : ['42', '', ''],
			'Wii' : ['82', 'Nintendo Wii', ''],
			'Windows' : ['3', 'PC', ''], 
			'Windows 3.x' : ['5', '', ''],
			'WonderSwan' : ['48', '', 'wonderswan'],
			'WonderSwan Color' : ['49', '', ''],  
			'Xbox' : ['13', 'Microsoft Xbox', 'xbox'],
			'Xbox 360' : ['69', 'Microsoft Xbox 360', ''],
			'Zeebo' : ['88', '', ''],
			'Zodiac' : ['68', '', 'zod'],
			'ZX Spectr' : ['41', 'Sinclair ZX Spectrum', '']}

missingFilterOptions = {util.localize(32157) : util.localize(32158),
					util.localize(32159) : util.localize(32160),
					util.localize(32161) : util.localize(32162)}



def getPlatformByRomCollection(source, romCollectionName):
	platform = ''
	if(source.find('mobygames.com') != -1):
		try:
			platform = consoleDict[romCollectionName][0]
		except:
			Logutil.log('Could not find platform name for Rom Collection %s' %romCollectionName, util.LOG_LEVEL_WARNING)
	elif(source.find('thegamesdb.net') != -1):
		try:
			platform = consoleDict[romCollectionName][1]
		except:
			Logutil.log('Could not find platform name for Rom Collection %s' %romCollectionName, util.LOG_LEVEL_WARNING)
	elif(source.find('archive.vg') != -1):
		try:
			platform = consoleDict[romCollectionName][2]
		except:
			Logutil.log('Could not find platform name for Rom Collection %s' %romCollectionName, util.LOG_LEVEL_WARNING)
	
	return platform

			
imagePlacingDict = {'gameinfobig' : 'one big',
					'gameinfobigVideo' : 'one big or video',
					'gameinfosmall' : 'four small',
					'gameinfosmallVideo' : 'three small + video',
					'gameinfomamemarquee' : 'MAME: marquee in list',
					'gameinfomamecabinet' : 'MAME: cabinet in list'}			


class FileType:
	name = ''
	id = -1
	type = ''
	parent = ''
	
class ImagePlacing:	
	name = ''	
	fileTypesForGameList = None
	fileTypesForGameListSelected = None			
	fileTypesForMainView1 = None
	fileTypesForMainView2 = None
	fileTypesForMainView3 = None						
	fileTypesForMainViewBackground = None
	fileTypesForMainViewGameInfoBig = None
	fileTypesForMainViewGameInfoUpperLeft = None
	fileTypesForMainViewGameInfoUpperRight = None
	fileTypesForMainViewGameInfoLowerLeft = None
	fileTypesForMainViewGameInfoLowerRight = None	
	fileTypesForMainViewGameInfoUpper = None
	fileTypesForMainViewGameInfoLower = None
	fileTypesForMainViewGameInfoLeft = None
	fileTypesForMainViewGameInfoRight = None
	
	fileTypesForMainViewVideoWindowBig = None
	fileTypesForMainViewVideoWindowSmall = None
	fileTypesForMainViewVideoFullscreen = None
	
class MediaPath:
	path = ''
	fileType = None
	
class Scraper:
	parseInstruction = ''
	source = ''
	sourceAppend = ''
	encoding = 'utf-8'
	returnUrl = False
	replaceKeyString = ''
	replaceValueString = ''
	
class Site:
	name = ''	
	descFilePerGame = False
	searchGameByCRC = True
	searchGameByCRCIgnoreRomName = False
	useFoldernameAsCRC = False
	useFilenameAsCRC = False
	
	scrapers = None
	

class MissingFilter:
	andGroup = []
	orGroup = []

class RomCollection:
	id = -1
	name = ''
	
	useBuiltinEmulator = False
	gameclient = ''
	emulatorCmd = ''
	preCmd = ''
	postCmd = ''
	emulatorParams = ''
	romPaths = None
	saveStatePath = ''
	saveStateParams = ''
	mediaPaths = None
	scraperSites = None
	imagePlacingMain = None
	imagePlacingInfo = None
	autoplayVideoMain = True
	autoplayVideoInfo = True
	ignoreOnScan = False
	allowUpdate = True
	useEmuSolo = False
	usePopen = False
	maxFolderDepth = 99
	useFoldernameAsGamename = False
	doNotExtractZipFiles = False
	makeLocalCopy = False
	diskPrefix = '_Disk.*'
	xboxCreateShortcut = False
	xboxCreateShortcutAddRomfile = False
	xboxCreateShortcutUseShortGamename = False


class Config:
		
	romCollections = None
	scraperSites = None
	fileTypeIdsForGamelist = None
	
	showHideOption = 'ignore'
	missingFilterInfo = None
	missingFilterArtwork = None
	
	tree = None
	configPath = None
	
	
	def __init__(self, configFile):
		Logutil.log('Config() set path to %s' %configFile, util.LOG_LEVEL_INFO)
		self.configFile = configFile
				
	
	def initXml(self):
		Logutil.log('initXml', util.LOG_LEVEL_INFO)
		
		if(not self.configFile):
			self.configFile = util.getConfigXmlPath()
		
		if(not os.path.isfile(self.configFile)):
			Logutil.log('File config.xml does not exist. Place a valid config file here: %s' %self.configFile, util.LOG_LEVEL_ERROR)
			return None, False, util.localize(32003)
		
		tree = ElementTree().parse(self.configFile)
		if(tree == None):
			Logutil.log('Could not read config.xml', util.LOG_LEVEL_ERROR)
			return None, False, util.localize(32004)
		
		self.tree = tree
		
		return tree, True, ''
	
	
	def checkRomCollectionsAvailable(self):
		Logutil.log('checkRomCollectionsAvailable', util.LOG_LEVEL_INFO)
	
		tree, success, errorMsg = self.initXml()
		if(not success):
			return False, errorMsg
		
		romCollectionRows = tree.findall('RomCollections/RomCollection')
		numRomCollections = len(romCollectionRows) 
		Logutil.log("Number of Rom Collections in config.xml: %i" %numRomCollections, util.LOG_LEVEL_INFO)
				
		return numRomCollections > 0, ''
				
	
	def readXml(self):
		Logutil.log('readXml', util.LOG_LEVEL_INFO)
		
		tree, success, errorMsg = self.initXml()
		if(not success):
			return False, errorMsg	
		
		#Rom Collections
		romCollections, errorMsg = self.readRomCollections(tree)
		if(romCollections == None):
			return False, errorMsg		
		self.romCollections = romCollections
		
		#Scrapers
		scrapers, errorMsg = self.readScrapers(tree)
		if(scrapers == None):
			return False, errorMsg		
		self.scraperSites = scrapers
				
		self.fileTypeIdsForGamelist = self.getFileTypeIdsForGameList(tree, romCollections)
		
		#Missing filter settings
		missingFilter = tree.find('MissingFilter')
		
		if(missingFilter != None):
			showHideOption = self.readTextElement(missingFilter, 'showHideOption')
			if(showHideOption != ''):
				self.showHideOption = showHideOption
			
		self.missingFilterInfo = self.readMissingFilter('missingInfoFilter', missingFilter)
		self.missingFilterArtwork = self.readMissingFilter('missingArtworkFilter', missingFilter)
		
		return True, ''	

	
		
	def readRomCollections(self, tree):
		
		Logutil.log('Begin readRomCollections', util.LOG_LEVEL_INFO)
		
		romCollections = {}
		
		romCollectionRows = tree.findall('RomCollections/RomCollection')
								
		if (len(romCollectionRows) == 0):
			Logutil.log('Configuration error. config.xml does not contain any RomCollections', util.LOG_LEVEL_ERROR)
			return None, 'Configuration error. See xbmc.log for details'
			
		for romCollectionRow in romCollectionRows:
			
			romCollection = RomCollection()
			romCollection.name = romCollectionRow.attrib.get('name')
			if(romCollection.name == None):
				Logutil.log('Configuration error. RomCollection must have an attribute name', util.LOG_LEVEL_ERROR)
				return None, util.localize(32005)
			
			Logutil.log('current Rom Collection: ' +str(romCollection.name), util.LOG_LEVEL_INFO)
			
			id = romCollectionRow.attrib.get('id')
			if(id == ''):
				Logutil.log('Configuration error. RomCollection %s must have an id' %romCollection.name, util.LOG_LEVEL_ERROR)
				return None, util.localize(32005)
			try:
				rc = romCollections[id]
				Logutil.log('Error while adding RomCollection. Make sure that the id is unique.', util.LOG_LEVEL_ERROR)
				return None, util.localize(32006)
			except:
				pass
			
			romCollection.id = id
			
			#romPath
			romCollection.romPaths = []
			romPathRows = romCollectionRow.findall('romPath')
			for romPathRow in romPathRows:
				Logutil.log('Rom path: ' +romPathRow.text, util.LOG_LEVEL_INFO)
				if(romPathRow.text != None):
					romCollection.romPaths.append(romPathRow.text)
				
			#mediaPath
			romCollection.mediaPaths = []
			mediaPathRows = romCollectionRow.findall('mediaPath')
			
			for mediaPathRow in mediaPathRows:
				mediaPath = MediaPath()
				if(mediaPathRow.text != None):					
					mediaPath.path = mediaPathRow.text
				Logutil.log('Media path: ' +mediaPath.path, util.LOG_LEVEL_INFO)
				fileType, errorMsg = self.readFileType(mediaPathRow.attrib.get('type'), tree)
				if(fileType == None):
					return None, errorMsg
				mediaPath.fileType = fileType
				romCollection.mediaPaths.append(mediaPath)
			
			#Scraper
			romCollection.scraperSites = []
			scraperRows = romCollectionRow.findall('scraper')
			for scraperRow in scraperRows:
				siteName = scraperRow.attrib.get('name')
				Logutil.log('Scraper site: ' +str(siteName), util.LOG_LEVEL_INFO)
				if(siteName == None or siteName == ''):
					Logutil.log('Configuration error. RomCollection/scraper must have an attribute name', util.LOG_LEVEL_ERROR)
					return None, util.localize(32005)
				
				#read additional scraper properties
				replaceKeyString = scraperRow.attrib.get('replaceKeyString')
				if(replaceKeyString == None):
					replaceKeyString = ''
				replaceValueString = scraperRow.attrib.get('replaceValueString')
				if(replaceValueString == None):
					replaceValueString = ''
								
				#elementtree version 1.2.7 does not support xpath like this: Scrapers/Site[@name="%s"] 
				siteRow = None
				siteRows = tree.findall('Scrapers/Site')
				for element in siteRows:
					if(element.attrib.get('name') == siteName):
						siteRow = element
						break
				
				if(siteRow == None):
					Logutil.log('Configuration error. Site %s does not exist in config.xml' %siteName, util.LOG_LEVEL_ERROR)
					return None, util.localize(32005)
								
				scraper, errorMsg = self.readScraper(siteRow, romCollection.name, replaceKeyString, replaceValueString, True, tree)
				if(scraper == None):
					return None, errorMsg
				romCollection.scraperSites.append(scraper)
				
			#imagePlacing - Main window
			romCollection.imagePlacingMain = ImagePlacing()
			imagePlacingRow = romCollectionRow.find('imagePlacingMain')			
			if(imagePlacingRow != None):
				Logutil.log('Image Placing name: ' +str(imagePlacingRow.text), util.LOG_LEVEL_INFO)
				fileTypeFor, errorMsg = self.readImagePlacing(imagePlacingRow.text, tree)
				if(fileTypeFor == None):
					return None, errorMsg
				
				romCollection.imagePlacingMain = fileTypeFor
				
			#imagePlacing - Info window
			romCollection.imagePlacingInfo = ImagePlacing()
			imagePlacingRow = romCollectionRow.find('imagePlacingInfo')			
			if(imagePlacingRow != None):
				Logutil.log('Image Placing name: ' +str(imagePlacingRow.text), util.LOG_LEVEL_INFO)
				fileTypeFor, errorMsg = self.readImagePlacing(imagePlacingRow.text, tree)
				if(fileTypeFor == None):
					return None, errorMsg
				
				romCollection.imagePlacingInfo = fileTypeFor
						
			#all simple RomCollection properties
			romCollection.gameclient = self.readTextElement(romCollectionRow, 'gameclient')
			romCollection.emulatorCmd = self.readTextElement(romCollectionRow, 'emulatorCmd')
			romCollection.preCmd = self.readTextElement(romCollectionRow, 'preCmd')
			romCollection.postCmd = self.readTextElement(romCollectionRow, 'postCmd')
			romCollection.emulatorParams = self.readTextElement(romCollectionRow, 'emulatorParams')
			romCollection.saveStatePath = self.readTextElement(romCollectionRow, 'saveStatePath')
			romCollection.saveStateParams = self.readTextElement(romCollectionRow, 'saveStateParams')
						
			useBuiltinEmulator = self.readTextElement(romCollectionRow, 'useBuiltinEmulator')
			if(useBuiltinEmulator != ''):
				romCollection.useBuiltinEmulator = useBuiltinEmulator.upper() == 'TRUE'
				
			ignoreOnScan = self.readTextElement(romCollectionRow, 'ignoreOnScan')
			if(ignoreOnScan != ''):
				romCollection.ignoreOnScan = ignoreOnScan.upper() == 'TRUE'
			
			allowUpdate = self.readTextElement(romCollectionRow, 'allowUpdate') 			
			if(allowUpdate != ''):
				romCollection.allowUpdate = allowUpdate.upper() == 'TRUE'
				
			useEmuSolo = self.readTextElement(romCollectionRow, 'useEmuSolo') 			
			if(useEmuSolo != ''):
				romCollection.useEmuSolo = useEmuSolo.upper() == 'TRUE'
				
			usePopen = self.readTextElement(romCollectionRow, 'usePopen') 			
			if(usePopen != ''):
				romCollection.usePopen = usePopen.upper() == 'TRUE'
				
			autoplayVideoMain = self.readTextElement(romCollectionRow, 'autoplayVideoMain')
			if(autoplayVideoMain != ''):
				romCollection.autoplayVideoMain = autoplayVideoMain.upper() == 'TRUE'
				
			autoplayVideoInfo = self.readTextElement(romCollectionRow, 'autoplayVideoInfo')
			if(autoplayVideoInfo != ''):
				romCollection.autoplayVideoInfo = autoplayVideoInfo.upper() == 'TRUE'
			
			useFoldernameAsGamename = self.readTextElement(romCollectionRow, 'useFoldernameAsGamename')			
			if(useFoldernameAsGamename != ''):
				romCollection.useFoldernameAsGamename = useFoldernameAsGamename.upper() == 'TRUE'	
			
			maxFolderDepth = self.readTextElement(romCollectionRow, 'maxFolderDepth') 
			if(maxFolderDepth != ''):
				romCollection.maxFolderDepth = int(maxFolderDepth)
				
			doNotExtractZipFiles = self.readTextElement(romCollectionRow, 'doNotExtractZipFiles') 			
			if(doNotExtractZipFiles != ''):
				romCollection.doNotExtractZipFiles = doNotExtractZipFiles.upper() == 'TRUE'
				
			makeLocalCopy = self.readTextElement(romCollectionRow, 'makeLocalCopy')
			if(makeLocalCopy != ''):
				romCollection.makeLocalCopy = makeLocalCopy.upper() == 'TRUE'		
				
			romCollection.diskPrefix = self.readTextElement(romCollectionRow, 'diskPrefix')
				
			xboxCreateShortcut = self.readTextElement(romCollectionRow, 'xboxCreateShortcut')			
			if(xboxCreateShortcut != ''):
				romCollection.xboxCreateShortcut = xboxCreateShortcut.upper() == 'TRUE'
				
			xboxCreateShortcutAddRomfile = self.readTextElement(romCollectionRow, 'xboxCreateShortcutAddRomfile') 			
			if(xboxCreateShortcutAddRomfile != ''):
				romCollection.xboxCreateShortcutAddRomfile = xboxCreateShortcutAddRomfile.upper() == 'TRUE'
				
			xboxCreateShortcutUseShortGamename = self.readTextElement(romCollectionRow, 'xboxCreateShortcutUseShortGamename')			
			if(xboxCreateShortcutUseShortGamename != ''):
				romCollection.xboxCreateShortcutUseShortGamename = xboxCreateShortcutUseShortGamename.upper() == 'TRUE'
			
			romCollections[id] = romCollection
			
		return romCollections, ''
		
		
	def readScrapers(self, tree):
		
		sites = {}
				
		siteRows = tree.findall('Scrapers/Site')
		for siteRow in siteRows:
			site, errorMsg = self.readScraper(siteRow, '', '', '', False, tree)
			if(site == None):
				return None, errorMsg
			
			name = siteRow.attrib.get('name')
			sites[name] = site

		return sites, ''
		
			
	def readScraper(self, siteRow, romCollectionName, inReplaceKeyString, inReplaceValueString, replaceValues, tree):
		
		site = Site()
		site.name = siteRow.attrib.get('name')
		Logutil.log('Scraper Site: ' +str(site.name), util.LOG_LEVEL_INFO)
		
		descFilePerGame = siteRow.attrib.get('descFilePerGame')
		if(descFilePerGame != None and descFilePerGame != ''):
			site.descFilePerGame = descFilePerGame.upper() == 'TRUE'
			Logutil.log('Scraper descFilePerGame: ' +str(site.descFilePerGame), util.LOG_LEVEL_INFO)
		
		searchGameByCRC = siteRow.attrib.get('searchGameByCRC')
		if(searchGameByCRC != None and searchGameByCRC != ''):
			site.searchGameByCRC = searchGameByCRC.upper() == 'TRUE'
			
		searchGameByCRCIgnoreRomName = siteRow.attrib.get('searchGameByCRCIgnoreRomName')
		if(searchGameByCRCIgnoreRomName != None and searchGameByCRCIgnoreRomName != ''):
			site.searchGameByCRCIgnoreRomName = searchGameByCRCIgnoreRomName.upper() == 'TRUE'
			
		useFoldernameAsCRC = siteRow.attrib.get('useFoldernameAsCRC')
		if(useFoldernameAsCRC != None and useFoldernameAsCRC != ''):
			site.useFoldernameAsCRC = useFoldernameAsCRC.upper() == 'TRUE'
			
		useFilenameAsCRC = siteRow.attrib.get('useFilenameAsCRC')
		if(useFilenameAsCRC != None and useFilenameAsCRC != ''):
			site.useFilenameAsCRC = useFilenameAsCRC.upper() == 'TRUE'
		
		scrapers = []
		
		scraperRows = siteRow.findall('Scraper')
		for scraperRow in scraperRows:
			scraper = Scraper()
			
			parseInstruction = scraperRow.attrib.get('parseInstruction')
			if(parseInstruction != None and parseInstruction != ''):
				if(not os.path.isabs(parseInstruction)):
					#if it is a relative path, search in RCBs home directory
					parseInstruction = os.path.join(util.RCBHOME, 'resources', 'scraper', parseInstruction)
				
				if(not os.path.isfile(parseInstruction)):
					Logutil.log('Configuration error. parseInstruction file %s does not exist.' %parseInstruction, util.LOG_LEVEL_ERROR)
					return None, util.localize(32005)
				
				scraper.parseInstruction = parseInstruction
				
			source = scraperRow.attrib.get('source')
			if(source != None and source != ''):
				if(replaceValues):
					platform = getPlatformByRomCollection(source, romCollectionName)
					platform = urllib.quote(platform, safe='')
					source = source.replace('%PLATFORM%', platform)
				scraper.source = source
			
			encoding = scraperRow.attrib.get('encoding')
			if(encoding != None and encoding != 'utf-8'):
				scraper.encoding = encoding
			
			returnUrl = scraperRow.attrib.get('returnUrl')
			if(returnUrl != None and returnUrl != ''):
				scraper.returnUrl = returnUrl.upper() == 'TRUE'
				
			sourceAppend = scraperRow.attrib.get('sourceAppend')
			if(sourceAppend != None and sourceAppend != ''):
				scraper.sourceAppend = sourceAppend
				
			scraper.replaceKeyString = inReplaceKeyString
			scraper.replaceValueString = inReplaceValueString
			
			scrapers.append(scraper)
			
		site.scrapers = scrapers
			
		return site, ''
	
	
	def readFileType(self, name, tree):
		
		fileTypeRow = None 
		fileTypeRows = tree.findall('FileTypes/FileType')
		for element in fileTypeRows:
			if(element.attrib.get('name') == name):
				fileTypeRow = element
				break
			
		if(fileTypeRow == None):
			Logutil.log('Configuration error. FileType %s does not exist in config.xml' %name, util.LOG_LEVEL_ERROR)
			return None, util.localize(32005)
			
		fileType = FileType()
		fileType.name = name
		
		id = fileTypeRow.attrib.get('id')
		if(id == ''):
			Logutil.log('Configuration error. FileType %s must have an id' %name, util.LOG_LEVEL_ERROR)
			return None, util.localize(32005)
			
		fileType.id = id
		
		type = fileTypeRow.find('type')
		if(type != None):
			fileType.type = type.text
			
		parent = fileTypeRow.find('parent')
		if(parent != None):
			fileType.parent = parent.text
			
		return fileType, ''
		
		
	def readImagePlacing(self, imagePlacingName, tree):
		
		fileTypeForRow = None 
		fileTypeForRows = tree.findall('ImagePlacing/fileTypeFor')
		for element in fileTypeForRows:
			if(element.attrib.get('name') == imagePlacingName):
				fileTypeForRow = element
				break
		
		if(fileTypeForRow == None):
			Logutil.log('Configuration error. ImagePlacing/fileTypeFor %s does not exist in config.xml' %str(imagePlacingName), util.LOG_LEVEL_ERROR)
			return None, util.localize(32005)
		
		imagePlacing = ImagePlacing()
		
		imagePlacing.name = imagePlacingName
			
		imagePlacing.fileTypesForGameList, errorMsg = self.readFileTypeForElement(fileTypeForRow, 'fileTypeForGameList', tree)		
		imagePlacing.fileTypesForGameListSelected, errorMsg = self.readFileTypeForElement(fileTypeForRow, 'fileTypeForGameListSelected', tree)
		imagePlacing.fileTypesForMainView1, errorMsg = self.readFileTypeForElement(fileTypeForRow, 'fileTypeForMainView1', tree)
		imagePlacing.fileTypesForMainView2, errorMsg = self.readFileTypeForElement(fileTypeForRow, 'fileTypeForMainView2', tree)
		imagePlacing.fileTypesForMainView3, errorMsg = self.readFileTypeForElement(fileTypeForRow, 'fileTypeForMainView3', tree)
		imagePlacing.fileTypesForMainViewBackground, errorMsg = self.readFileTypeForElement(fileTypeForRow, 'fileTypeForMainViewBackground', tree)
		imagePlacing.fileTypesForMainViewGameInfoBig, errorMsg = self.readFileTypeForElement(fileTypeForRow, 'fileTypeForMainViewGameInfoBig', tree)
		imagePlacing.fileTypesForMainViewGameInfoUpperLeft, errorMsg = self.readFileTypeForElement(fileTypeForRow, 'fileTypeForMainViewGameInfoUpperLeft', tree)
		imagePlacing.fileTypesForMainViewGameInfoUpperRight, errorMsg = self.readFileTypeForElement(fileTypeForRow, 'fileTypeForMainViewGameInfoUpperRight', tree)
		imagePlacing.fileTypesForMainViewGameInfoLowerLeft, errorMsg = self.readFileTypeForElement(fileTypeForRow, 'fileTypeForMainViewGameInfoLowerLeft', tree)
		imagePlacing.fileTypesForMainViewGameInfoLowerRight, errorMsg = self.readFileTypeForElement(fileTypeForRow, 'fileTypeForMainViewGameInfoLowerRight', tree)
		
		imagePlacing.fileTypesForMainViewGameInfoLower, errorMsg = self.readFileTypeForElement(fileTypeForRow, 'fileTypeForMainViewGameInfoLower', tree)
		imagePlacing.fileTypesForMainViewGameInfoUpper, errorMsg = self.readFileTypeForElement(fileTypeForRow, 'fileTypeForMainViewGameInfoUpper', tree)
		imagePlacing.fileTypesForMainViewGameInfoRight, errorMsg = self.readFileTypeForElement(fileTypeForRow, 'fileTypeForMainViewGameInfoRight', tree)
		imagePlacing.fileTypesForMainViewGameInfoLeft, errorMsg = self.readFileTypeForElement(fileTypeForRow, 'fileTypeForMainViewGameInfoLeft', tree)
		
		imagePlacing.fileTypesForMainViewVideoWindowBig, errorMsg = self.readFileTypeForElement(fileTypeForRow, 'fileTypeForMainViewVideoWindowBig', tree)
		imagePlacing.fileTypesForMainViewVideoWindowSmall, errorMsg = self.readFileTypeForElement(fileTypeForRow, 'fileTypeForMainViewVideoWindowSmall', tree)
		imagePlacing.fileTypesForMainViewVideoFullscreen, errorMsg = self.readFileTypeForElement(fileTypeForRow, 'fileTypeForMainViewVideoFullscreen', tree)
			
		return imagePlacing, ''
			
	
	def readFileTypeForElement(self, fileTypeForRow, key, tree):
		fileTypeList = []
		fileTypesForControl = fileTypeForRow.findall(key)		
		for fileTypeForControl in fileTypesForControl:						
				
			fileType, errorMsg = self.readFileType(fileTypeForControl.text, tree)
			if(fileType == None):
				return None, errorMsg
						
			fileTypeList.append(fileType)
				
		return fileTypeList, ''
	
	
	def readMissingFilter(self, filterName, tree):
		missingFilter = MissingFilter()
		missingFilter.andGroup = []
		missingFilter.orGroup = []
		if(tree != None):
			missingFilterRow = tree.find(filterName)
			if(missingFilterRow != None):
				missingFilter.andGroup = self.getMissingFilterItems(missingFilterRow, 'andGroup')
				missingFilter.orGroup = self.getMissingFilterItems(missingFilterRow, 'orGroup')
		
		return missingFilter		
	
	def getMissingFilterItems(self, missingFilterRow, groupName):
		items = []
		groupRow = missingFilterRow.find(groupName)
		if(groupRow != None):
			itemRows = groupRow.findall('item')			
			for element in itemRows:
				items.append(element.text)
		return items
	
	
	def getFileTypeIdsForGameList(self, tree, romCollections):
		
		fileTypeIds = []
		for romCollection in romCollections.values():
			for fileType in romCollection.imagePlacingMain.fileTypesForGameList:				
				if(fileTypeIds.count(fileType.id) == 0):
					fileTypeIds.append(fileType.id)
			for fileType in romCollection.imagePlacingMain.fileTypesForGameListSelected:
				if(fileTypeIds.count(fileType.id) == 0):
					fileTypeIds.append(fileType.id)
			
			#fullscreen video
			fileType, errorMsg = self.readFileType('gameplay', tree)
			if(fileType != None):
				fileTypeIds.append(fileType.id)

		return fileTypeIds
	
	
	def readTextElement(self, parent, elementName):
		element = parent.find(elementName)
		if(element != None and element.text != None):
			Logutil.log('%s: %s' %(elementName, element.text), util.LOG_LEVEL_INFO)
			return element.text
		else:
			return ''