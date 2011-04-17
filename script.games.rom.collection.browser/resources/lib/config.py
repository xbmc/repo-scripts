import os

import util
from util import *
from elementtree.ElementTree import *


consoleDict = {
			#name, mobygames-id
			'Other' : '0',
			'3DO' : '35',
			'Amiga' : '19',
			'Amiga CD32' : '56',
			'Amstrad CPC' : '60',
			'Apple II' : '31',
			'Atari 2600' : '28',
			'Atari 5200' : '33',
			'Atari 7800' : '34',
			'Atari 8-bit' : '39',
			'Atari ST' : '24',			
			'BBC Micro' : '92',
			'BREW' : '63',
			'CD-i' : '73',  
			'Channel F' : '76',  
			'ColecoVision' : '29',  
			'Commodore 128' : '61',  
			'Commodore 64' : '27',  
			'Commodore PET/CBM' : '77',  
			'DoJa' : '72',  
			'DOS' : '2',  
			'Dragon 32/64' : '79',  
			'Dreamcast' : '8',  
			'Electron' : '93',  
			'ExEn' : '70',  
			'Game Boy' : '10',  
			'Game Boy Advance' : '12',  
			'Game Boy Color' : '11',
			'GameCube' : '14',  
			'Game Gear' : '25',  
			'Genesis' : '16',  
			'Gizmondo' : '55',  
			'Intellivision' : '30',
			'Jaguar' : '17',  
			'Linux' : '1',  
			'Lynx' : '18',  
			'Macintosh' : '74',
			'MAME' : '0',  
			'Mophun' : '71',  
			'MSX' : '57',  
			'Neo Geo' : '36',  
			'Neo Geo CD' : '54',  
			'Neo Geo Pocket' : '52',  
			'Neo Geo Pocket Color' : '53',  
			'NES' : '22',  
			'N-Gage' : '32',
			'Nintendo 64' : '9',  
			'Nintendo DS' : '44',  
			'Nintendo DSi' : '87',  
			'Odyssey' : '75',  
			'Odyssey 2' : '78',
			'PC-88' : '94',  
			'PC-98' : '95',  
			'PC Booter' : '4',  
			'PC-FX' : '59',  
			'PlayStation' : '6',  
			'PlayStation 2' : '7',  
			'PlayStation 3' : '81',  
			'PSP' : '46',  
			'SEGA 32X' : '21',  
			'SEGA CD' : '20',  
			'SEGA Master System' : '26',  
			'SEGA Saturn' : '23',  
			'SNES' : '15',  
			'Spectravideo' : '85',
			'TI-99/4A' : '47',  
			'TRS-80' : '58',  
			'TRS-80 CoCo' : '62',  
			'TurboGrafx-16' : '40',  
			'TurboGrafx CD' : '45',  
			'Vectrex' : '37',  
			'VIC-20' : '43',  
			'Virtual Boy' : '38',  
			'V.Smile' : '42',  
			'Wii' : '82',  
			'Windows' : '3',  
			'Windows 3.x' : '5',
			'WonderSwan' : '48',  
			'WonderSwan Color' : '49',  
			'Xbox' : '13',  
			'Xbox 360' : '69',  
			'Zeebo' : '88',  
			'Zodiac' : '68',  
			'ZX Spectr' : '41'}
			
			


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
	
	fileTypesForGameInfoViewBackground = None
	fileTypesForGameInfoViewGamelist = None
	fileTypesForGameInfoView1 = None
	fileTypesForGameInfoView2 = None
	fileTypesForGameInfoView3 = None
	fileTypesForGameInfoView4 = None
	fileTypesForGameInfoViewVideoWindow = None
	
class MediaPath:
	path = ''
	fileType = None
	
class Scraper:
	parseInstruction = ''
	source = ''
	encoding = 'utf-8'
	returnUrl = False
	replaceKeyString = ''
	replaceValueString = ''
	platformId = 0
	
class Site:
	name = ''
	scrapers = None

class RomCollection:
	id = -1
	name = ''
	
	emulatorCmd = ''
	emulatorParams = ''
	romPaths = None
	mediaPaths = None
	scraperSites = None
	imagePlacing = None
	ignoreOnScan = False
	allowUpdate = True	
	searchGameByCRC = True
	searchGameByCRCIgnoreRomName = False
	useFoldernameAsCRC = False
	useFilenameAsCRC = False
	useFoldernameAsGamename = False
	maxFolderDepth = 99
	descFilePerGame = False
	doNotExtractZipFiles = False
	diskPrefix = '_Disk'
	xboxCreateShortcut = False
	xboxCreateShortcutAddRomfile = False
	xboxCreateShortcutUseShortGamename = False


class Config:
		
	romCollections = None
	fileTypeIdsForGamelist = None
	
	tree = None
		
	
	def readXml(self):
		
		Logutil.log('Begin readXml', util.LOG_LEVEL_INFO)
		
		configFile = util.getConfigXmlPath()		
		
		if(not os.path.isfile(configFile)):			
			Logutil.log('File config.xml does not exist. Place a valid config file here: ' +str(configFile), util.LOG_LEVEL_ERROR)
			return False, 'Error: File config.xml does not exist'
		
		tree = ElementTree().parse(configFile)
		self.tree = tree
		if(tree == None):
			Logutil.log('Could not read config.xml', util.LOG_LEVEL_ERROR)
			return False, 'Could not read config.xml.'
		
		romCollections, errorMsg = self.readRomCollections(tree)
		if(romCollections == None):
			return False, errorMsg
		
		self.romCollections = romCollections
				
		self.fileTypeIdsForGamelist = self.getFileTypeIdsForGameList(romCollections)
		
		return True, ''	

	
		
	def readRomCollections(self, tree):
		
		Logutil.log('Begin readRomCollections', util.LOG_LEVEL_INFO)
		
		romCollections = {}
		
		romCollectionRows = tree.findall('RomCollections/RomCollection')
				
		"""	
		#TODO Find out how to check result of findall. None, len() and list() don't work
		if (len(list(romCollections)) == 0):
			Logutil.log('Configuration error. config.xml does not contain any RomCollections', util.LOG_LEVEL_ERROR)
			return None, 'Configuration error. See xbmc.log for details'
		"""
			
		for romCollectionRow in romCollectionRows:
			
			romCollection = RomCollection()
			romCollection.name = romCollectionRow.attrib.get('name')
			if(romCollection.name == None):
				Logutil.log('Configuration error. RomCollection must have an attribute name', util.LOG_LEVEL_ERROR)
				return None, 'Configuration error. See xbmc.log for details'
			
			Logutil.log('current Rom Collection: ' +str(romCollection.name), util.LOG_LEVEL_INFO)
			
			id = romCollectionRow.attrib.get('id')
			if(id == ''):
				Logutil.log('Configuration error. RomCollection %s must have an id' %romCollection.name, util.LOG_LEVEL_ERROR)
				return None, 'Configuration error. See xbmc.log for details'
			try:
				rc = romCollections[id]
				Logutil.log('Error while adding RomCollection. Make sure that the id is unique.', util.LOG_LEVEL_ERROR)
				return None, 'Rom Collection ids are not unique'
			except:
				pass
			romCollection.id = id
			
			#romPath
			romCollection.romPaths = []
			romPathRows = romCollectionRow.findall('romPath')			
			for romPathRow in romPathRows:
				Logutil.log('Rom path: ' +str(romPathRow.text), util.LOG_LEVEL_INFO)
				romCollection.romPaths.append(romPathRow.text)
				
			#mediaPath
			romCollection.mediaPaths = []
			mediaPathRows = romCollectionRow.findall('mediaPath')
			for mediaPathRow in mediaPathRows:
				mediaPath = MediaPath()
				mediaPath.path = mediaPathRow.text
				Logutil.log('Media path: ' +str(mediaPathRow.text), util.LOG_LEVEL_INFO)
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
					return None, 'Configuration error. See xbmc.log for details'
				
				#read additional scraper properties
				platform = scraperRow.attrib.get('platform')
				if(platform == None):
					platform = ''
				replaceKeyString = scraperRow.attrib.get('replaceKeyString')
				if(replaceKeyString == None):
					replaceKeyString = ''
				replaceValueString = scraperRow.attrib.get('replaceValueString')
				if(replaceValueString == None):
					replaceValueString = ''
				
				
				scraper, errorMsg = self.readScraper(siteName, platform, replaceKeyString, replaceValueString, tree)
				if(scraper == None):
					return None, errorMsg
				romCollection.scraperSites.append(scraper)
				
			#imagePlacing
			romCollection.imagePlacing = []
			imagePlacingRow = romCollectionRow.find('imagePlacing')			
			if(imagePlacingRow != None):
				Logutil.log('Image Placing name: ' +str(imagePlacingRow.text), util.LOG_LEVEL_INFO)
				fileTypeFor, errorMsg = self.readImagePlacing(imagePlacingRow.text, tree)
				if(fileTypeFor == None):
					return None, errorMsg
				
				romCollection.imagePlacing = fileTypeFor
			
			#all simple RomCollection properties
			emulatorCmd = romCollectionRow.find('emulatorCmd')
			if(emulatorCmd != None):
				Logutil.log('Emulator cmd: ' +str(emulatorCmd.text), util.LOG_LEVEL_INFO)
				romCollection.emulatorCmd = emulatorCmd.text
			
			emulatorParams = romCollectionRow.find('emulatorParams')
			if(emulatorParams != None):
				Logutil.log('Emulator params: ' +str(emulatorParams.text), util.LOG_LEVEL_INFO)
				romCollection.emulatorParams = emulatorParams.text
			
			ignoreOnScan = romCollectionRow.find('ignoreOnScan')
			if(ignoreOnScan != None):
				romCollection.ignoreOnScan = ignoreOnScan.text.upper() == 'TRUE'
				
			allowUpdate = romCollectionRow.find('allowUpdate')
			if(allowUpdate != None):
				romCollection.allowUpdate = allowUpdate.text.upper() == 'TRUE'
				
			searchGameByCRC = romCollectionRow.find('searchGameByCRC')
			if(searchGameByCRC != None):
				romCollection.searchGameByCRC = searchGameByCRC.text.upper() == 'TRUE'
				
			searchGameByCRCIgnoreRomName = romCollectionRow.find('searchGameByCRCIgnoreRomName')
			if(searchGameByCRCIgnoreRomName != None):
				romCollection.searchGameByCRCIgnoreRomName = searchGameByCRCIgnoreRomName.text.upper() == 'TRUE'
				
			useFoldernameAsCRC = romCollectionRow.find('useFoldernameAsCRC')
			if(useFoldernameAsCRC != None):
				romCollection.useFoldernameAsCRC = useFoldernameAsCRC.text.upper() == 'TRUE'
				
			useFilenameAsCRC = romCollectionRow.find('useFilenameAsCRC')
			if(useFilenameAsCRC != None):
				romCollection.useFilenameAsCRC = useFilenameAsCRC.text.upper() == 'TRUE'
			
			useFoldernameAsGamename = romCollectionRow.find('useFoldernameAsGamename')
			if(useFoldernameAsGamename != None):
				romCollection.useFoldernameAsGamename = useFoldernameAsGamename.text.upper() == 'TRUE'	
			
			maxFolderDepth = romCollectionRow.find('maxFolderDepth')
			if(maxFolderDepth != None):
				romCollection.maxFolderDepth = int(maxFolderDepth.text)
				
			descFilePerGame = romCollectionRow.find('descFilePerGame')
			if(descFilePerGame != None):
				romCollection.descFilePerGame = descFilePerGame.text.upper() == 'TRUE'
				
			doNotExtractZipFiles = romCollectionRow.find('doNotExtractZipFiles')
			if(doNotExtractZipFiles != None):
				romCollection.doNotExtractZipFiles = doNotExtractZipFiles.text.upper() == 'TRUE'		
				
			diskPrefix = romCollectionRow.find('diskPrefix')
			if(diskPrefix != None):
				romCollection.diskPrefix = diskPrefix.text							
				
			xboxCreateShortcut = romCollectionRow.find('xboxCreateShortcut')
			if(xboxCreateShortcut != None):
				romCollection.xboxCreateShortcut = xboxCreateShortcut.text.upper() == 'TRUE'
				
			xboxCreateShortcutAddRomfile = romCollectionRow.find('xboxCreateShortcutAddRomfile')
			if(xboxCreateShortcutAddRomfile != None):
				romCollection.xboxCreateShortcutAddRomfile = xboxCreateShortcutAddRomfile.text.upper() == 'TRUE'
				
			xboxCreateShortcutUseShortGamename = romCollectionRow.find('xboxCreateShortcutUseShortGamename')
			if(xboxCreateShortcutUseShortGamename != None):
				romCollection.xboxCreateShortcutUseShortGamename = xboxCreateShortcutUseShortGamename.text.upper() == 'TRUE'
									
			romCollections[id] = romCollection
			
		return romCollections, ''
		
			
	def readScraper(self, siteName, platform, inReplaceKeyString, inReplaceValueString, tree):
		
		#elementtree version 1.2.7 does not support xpath like this: Scrapers/Site[@name="%s"] 
		siteRow = None
		siteRows = tree.findall('Scrapers/Site')
		for element in siteRows:
			if(element.attrib.get('name') == siteName):
				siteRow = element
				break
		
		if(siteRow == None):
			Logutil.log('Configuration error. Site %s does not exist in config.xml' %siteName, util.LOG_LEVEL_ERROR)
			return None, 'Configuration error. See xbmc.log for details'
		
		site = Site()
		site.name = siteName
		site.platformId = platform
		
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
					return None, 'Configuration error. See xbmc.log for details'
				
				scraper.parseInstruction = parseInstruction
				
			source = scraperRow.attrib.get('source')
			if(source != None and source != ''):				
				scraper.source = source.replace('%PLATFORM%', platform)
			
			encoding = scraperRow.attrib.get('encoding')
			if(encoding != None and encoding != 'utf-8'):
				scraper.encoding = encoding
			
			returnUrl = scraperRow.attrib.get('returnUrl')
			if(returnUrl != None and returnUrl != ''):
				scraper.returnUrl = returnUrl.upper() == 'TRUE'
				
			replaceKeyString = scraperRow.attrib.get('replaceKeyString')
			if(replaceKeyString != None and replaceKeyString != ''):
				scraper.replaceKeyString = replaceKeyString.replace('%REPLACEKEYS%', inReplaceKeyString)
				
			replaceValueString = scraperRow.attrib.get('replaceValueString')
			if(replaceValueString != None and replaceValueString != ''):
				scraper.replaceValueString = replaceValueString.replace('%REPLACEVALUES%', inReplaceValueString)
			
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
			return None, 'Configuration error. See xbmc.log for details'
			
		fileType = FileType()
		fileType.name = name
		
		id = fileTypeRow.attrib.get('id')
		if(id == ''):
			Logutil.log('Configuration error. FileType %s must have an id' %name, util.LOG_LEVEL_ERROR)
			return None, 'Configuration error. See xbmc.log for details'
			
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
			Logutil.log('Configuration error. ImagePlacing/fileTypeFor %s does not exist in config.xml' %imagePlacingName, util.LOG_LEVEL_ERROR)
			return None, 'Configuration error. See xbmc.log for details'
		
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
		
		imagePlacing.fileTypesForGameInfoViewBackground, errorMsg = self.readFileTypeForElement(fileTypeForRow, 'fileTypeForGameInfoViewBackground', tree)
		imagePlacing.fileTypesForGameInfoViewGamelist, errorMsg = self.readFileTypeForElement(fileTypeForRow, 'fileTypeForGameInfoViewGamelist', tree)
		imagePlacing.fileTypesForGameInfoView1, errorMsg = self.readFileTypeForElement(fileTypeForRow, 'fileTypeForGameInfoView1', tree)
		imagePlacing.fileTypesForGameInfoView2, errorMsg = self.readFileTypeForElement(fileTypeForRow, 'fileTypeForGameInfoView2', tree)
		imagePlacing.fileTypesForGameInfoView3, errorMsg = self.readFileTypeForElement(fileTypeForRow, 'fileTypeForGameInfoView3', tree)
		imagePlacing.fileTypesForGameInfoView4, errorMsg = self.readFileTypeForElement(fileTypeForRow, 'fileTypeForGameInfoView4', tree)
		imagePlacing.fileTypesForGameInfoViewVideoWindow, errorMsg = self.readFileTypeForElement(fileTypeForRow, 'fileTypeForGameInfoViewVideoWindow', tree)		
			
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
		
	
	def getFileTypeIdsForGameList(self, romCollections):
		
		fileTypeIds = []
		for romCollection in romCollections.values():
			for fileType in romCollection.imagePlacing.fileTypesForGameList:				
				if(fileTypeIds.count(fileType.id) == 0):
					fileTypeIds.append(fileType.id)
			for fileType in romCollection.imagePlacing.fileTypesForGameListSelected:
				if(fileTypeIds.count(fileType.id) == 0):
					fileTypeIds.append(fileType.id)
			for fileType in romCollection.imagePlacing.fileTypesForMainViewVideoFullscreen:
				if(fileTypeIds.count(fileType.id) == 0):
					fileTypeIds.append(fileType.id)

		return fileTypeIds
			