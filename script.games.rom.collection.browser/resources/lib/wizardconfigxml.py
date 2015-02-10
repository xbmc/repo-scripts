
import os
import xbmc, xbmcgui, xbmcvfs

from xml.etree.ElementTree import *
import config, helper
from configxmlwriter import *
from emulatorautoconfig.autoconfig import EmulatorAutoconfig


class ConfigXmlWizard:


	def createConfigXml(self, configFile):
				
		id = 1		
		consoleList = sorted(config.consoleDict.keys())
				
		success, romCollections = self.addRomCollections(id, None, consoleList, False)
		if(not success):
			Logutil.log('Action canceled. Config.xml will not be written', util.LOG_LEVEL_INFO)
			return False, util.localize(32172)
				
		configWriter = ConfigXmlWriter(True)
		success, message = configWriter.writeRomCollections(romCollections, False)
			
		return success, message
	
	
	def addRomCollection(self, configObj):
		Logutil.log("Begin addRomCollection" , util.LOG_LEVEL_INFO)
		
		consoleList = sorted(config.consoleDict.keys())
		id = 1
		
		rcIds = configObj.romCollections.keys()
		rcIds.sort()
		#read existing rom collection ids and names
		for rcId in rcIds:				
			
			#remove already configured consoles from the list			
			if(configObj.romCollections[rcId].name in consoleList):
				consoleList.remove(configObj.romCollections[rcId].name)
			#find highest id
			if(int(rcId) > int(id)):
				id = rcId
								
		id = int(id) +1
		
		success, romCollections = self.addRomCollections(id, configObj, consoleList, True)
		if(not success):
			Logutil.log('Action canceled. Config.xml will not be written', util.LOG_LEVEL_INFO)
			return False, util.localize(32172)
				
		configWriter = ConfigXmlWriter(False)
		success, message = configWriter.writeRomCollections(romCollections, False)
		
		Logutil.log("End addRomCollection" , util.LOG_LEVEL_INFO)
		return success, message
	
	
	def addRomCollections(self, id, configObj, consoleList, isUpdate):
		
		romCollections = {}
		dialog = xbmcgui.Dialog()
		
		#scraping scenario
		scenarioIndex = dialog.select(util.localize(32173), [util.localize(32174), util.localize(32175)])
		Logutil.log('scenarioIndex: ' +str(scenarioIndex), util.LOG_LEVEL_INFO)
		if(scenarioIndex == -1):
			del dialog
			Logutil.log('No scenario selected. Action canceled.', util.LOG_LEVEL_INFO)
			return False, romCollections
		
		autoconfig = EmulatorAutoconfig(util.getEmuAutoConfigPath())
		
		while True:
					
			fileTypeList, errorMsg = self.buildMediaTypeList(configObj, isUpdate)
			romCollection = RomCollection()
			
			#console
			platformIndex = dialog.select(util.localize(32176), consoleList)
			Logutil.log('platformIndex: ' +str(platformIndex), util.LOG_LEVEL_INFO)
			if(platformIndex == -1):
				Logutil.log('No Platform selected. Action canceled.', util.LOG_LEVEL_INFO)
				break
			else:
				console = consoleList[platformIndex]
				if(console =='Other'):				
					keyboard = xbmc.Keyboard()
					keyboard.setHeading(util.localize(32177))			
					keyboard.doModal()
					if (keyboard.isConfirmed()):
						console = keyboard.getText()
						Logutil.log('Platform entered manually: ' +console, util.LOG_LEVEL_INFO)
					else:
						Logutil.log('No Platform entered. Action canceled.', util.LOG_LEVEL_INFO)
						break
				else:
					consoleList.remove(console)
					Logutil.log('selected platform: ' +console, util.LOG_LEVEL_INFO)
			
			romCollection.name = console
			romCollection.id = id
			id = id +1
			
			
			#check if we have general RetroPlayer support
			if(helper.isRetroPlayerSupported()):
				supportsRetroPlayer = True
				#if we have full python integration we can also check if specific platform supports RetroPlayer
				if(helper.retroPlayerSupportsPythonIntegration()):
					supportsRetroPlayer = False
					success, installedAddons = helper.readLibretroCores("all", True, romCollection.name)
					if(success and len(installedAddons) > 0):
						supportsRetroPlayer = True
					else:
						success, installedAddons = helper.readLibretroCores("uninstalled", False, romCollection.name)
						if(success and len(installedAddons) > 0):
							supportsRetroPlayer = True
					
				if(supportsRetroPlayer):
					retValue = dialog.yesno(util.localize(32999), util.localize(32198))
					if(retValue == True):
						romCollection.useBuiltinEmulator = True
			
			#only ask for emulator and params if we don't use builtin emulator
			if(not romCollection.useBuiltinEmulator):
				
				#maybe there is autoconfig support
				preconfiguredEmulator = None
				
				#emulator
				#xbox games on xbox will be launched directly
				if (os.environ.get( "OS", "xbox" ) == "xbox" and romCollection.name == 'Xbox'):
					romCollection.emulatorCmd = '%ROM%'
					Logutil.log('emuCmd set to "%ROM%" on Xbox.', util.LOG_LEVEL_INFO)
				#check for standalone games
				elif (romCollection.name == 'Linux' or romCollection.name == 'Macintosh' or romCollection.name == 'Windows'):
					romCollection.emulatorCmd = '"%ROM%"'
					Logutil.log('emuCmd set to "%ROM%" for standalone games.', util.LOG_LEVEL_INFO)
				else:
					#TODO: Windows and Linux support
					#xbmc.getCondVisibility('System.Platform.Windows')
					#xbmc.getCondVisibility('System.Platform.Linux')
					if(xbmc.getCondVisibility('System.Platform.Android')):
						Logutil.log('Running on Android. Trying to find emulator per autoconfig.', util.LOG_LEVEL_INFO)
						emulators = autoconfig.findEmulators('Android', romCollection.name, True)
						emulist = []
						for emulator in emulators:
							if(emulator.isInstalled):
								emulist.append(util.localize(32202) %emulator.name)
							else:
								emulist.append(emulator.name)
						if(len(emulist) > 0):
							emuIndex = dialog.select(util.localize(32203), emulist)
							Logutil.log('emuIndex: ' +str(emuIndex), util.LOG_LEVEL_INFO)
							if(emuIndex == -1):
								Logutil.log('No Emulator selected.', util.LOG_LEVEL_INFO)
							else:
								preconfiguredEmulator = emulators[emuIndex]
							
					if(preconfiguredEmulator):
						romCollection.emulatorCmd = preconfiguredEmulator.emuCmd
					else:
						consolePath = dialog.browse(1, util.localize(32178) %console, 'files')
						Logutil.log('consolePath: ' +str(consolePath), util.LOG_LEVEL_INFO)
						if(consolePath == ''):
							Logutil.log('No consolePath selected. Action canceled.', util.LOG_LEVEL_INFO)
							break
						romCollection.emulatorCmd = consolePath
				
				#params
				#on xbox we will create .cut files without params
				if (os.environ.get( "OS", "xbox" ) == "xbox"):
					romCollection.emulatorParams = ''
					Logutil.log('emuParams set to "" on Xbox.', util.LOG_LEVEL_INFO)
				elif (romCollection.name == 'Linux' or romCollection.name == 'Macintosh' or romCollection.name == 'Windows'):
					romCollection.emulatorParams = ''
					Logutil.log('emuParams set to "" for standalone games.', util.LOG_LEVEL_INFO)
				else:
					defaultParams = '"%ROM%"'
					if(preconfiguredEmulator):
						defaultParams = preconfiguredEmulator.emuParams
											
					keyboard = xbmc.Keyboard()
					keyboard.setDefault(defaultParams)
					keyboard.setHeading(util.localize(32179))			
					keyboard.doModal()
					if (keyboard.isConfirmed()):
						emuParams = keyboard.getText()
						Logutil.log('emuParams: ' +str(emuParams), util.LOG_LEVEL_INFO)
					else:
						Logutil.log('No emuParams selected. Action canceled.', util.LOG_LEVEL_INFO)
						break
					romCollection.emulatorParams = emuParams
			
			#roms
			romPath = dialog.browse(0, util.localize(32180) %console, 'files')
			if(romPath == ''):
				Logutil.log('No romPath selected. Action canceled.', util.LOG_LEVEL_INFO)
				break
									
			#TODO: find out how to deal with non-ascii characters
			try:
				unicode(romPath)
			except:
				Logutil.log("RCB can't acces your Rom Path. Make sure it does not contain any non-ascii characters.", util.LOG_LEVEL_INFO)
				xbmcgui.Dialog().ok(util.SCRIPTNAME, util.localize(32041), errorMsg)
				break
					
			#filemask
			
			#xbox games always use default.xbe as executable
			if (os.environ.get( "OS", "xbox" ) == "xbox" and romCollection.name == 'Xbox'):
				Logutil.log('filemask "default.xbe" for Xbox games on Xbox.', util.LOG_LEVEL_INFO)
				romPathComplete = util.joinPath(romPath, 'default.xbe')					
				romCollection.romPaths = []
				romCollection.romPaths.append(romPathComplete)
			else:
				keyboard = xbmc.Keyboard()
				keyboard.setHeading(util.localize(32181))			
				keyboard.doModal()
				if (keyboard.isConfirmed()):					
					fileMaskInput = keyboard.getText()
					Logutil.log('fileMask: ' +str(fileMaskInput), util.LOG_LEVEL_INFO)
					fileMasks = fileMaskInput.split(',')
					romCollection.romPaths = []
					for fileMask in fileMasks:
						romPathComplete = util.joinPath(romPath, fileMask.strip())					
						romCollection.romPaths.append(romPathComplete)
				else:
					Logutil.log('No fileMask selected. Action canceled.', util.LOG_LEVEL_INFO)
					break
	
			if (os.environ.get( "OS", "xbox" ) == "xbox"):
				romCollection.xboxCreateShortcut = True
				romCollection.xboxCreateShortcutAddRomfile = True
				romCollection.xboxCreateShortcutUseShortGamename = False
				
				#TODO use flags for complete platform list (not only xbox)
				if(romCollection.name == 'Xbox'):
					romCollection.useFoldernameAsGamename = True
					romCollection.searchGameByCRC = False
					romCollection.maxFolderDepth = 1
			
			
			if(scenarioIndex == 0):
				artworkPath = dialog.browse(0, util.localize(32193) %console, 'files', '', False, False, romPath)
				Logutil.log('artworkPath: ' +str(artworkPath), util.LOG_LEVEL_INFO)				
				#TODO: find out how to deal with non-ascii characters
				try:
					unicode(artworkPath)
				except:
					Logutil.log("RCB can't acces your artwork path. Make sure it does not contain any non-ascii characters.", util.LOG_LEVEL_INFO)
					xbmcgui.Dialog().ok(util.SCRIPTNAME, util.localize(32042), errorMsg)
					break
				
				if(artworkPath == ''):
					Logutil.log('No artworkPath selected. Action canceled.', util.LOG_LEVEL_INFO)
					break
				
				romCollection.descFilePerGame= True
				
				#mediaPaths
				romCollection.mediaPaths = []
				
				if(romCollection.name == 'MAME'):
					romCollection.mediaPaths.append(self.createMediaPath('boxfront', artworkPath, scenarioIndex))
					romCollection.mediaPaths.append(self.createMediaPath('action', artworkPath, scenarioIndex))
					romCollection.mediaPaths.append(self.createMediaPath('title', artworkPath, scenarioIndex))
					romCollection.mediaPaths.append(self.createMediaPath('cabinet', artworkPath, scenarioIndex))
					romCollection.mediaPaths.append(self.createMediaPath('marquee', artworkPath, scenarioIndex))					
				else:
					romCollection.mediaPaths.append(self.createMediaPath('boxfront', artworkPath, scenarioIndex))
					romCollection.mediaPaths.append(self.createMediaPath('boxback', artworkPath, scenarioIndex))
					romCollection.mediaPaths.append(self.createMediaPath('cartridge', artworkPath, scenarioIndex))
					romCollection.mediaPaths.append(self.createMediaPath('screenshot', artworkPath, scenarioIndex))
					romCollection.mediaPaths.append(self.createMediaPath('fanart', artworkPath, scenarioIndex))
				
				#other MAME specific properties
				if(romCollection.name == 'MAME'):
					romCollection.imagePlacingMain = ImagePlacing()
					romCollection.imagePlacingMain.name = 'gameinfomamecabinet'
					
					#MAME zip files contain several files but they must be passed to the emu as zip file
					romCollection.doNotExtractZipFiles = True
					
					#create MAWS scraper
					site = Site()
					site.name = 'maws.mameworld.info'
					scrapers = []
					scraper = Scraper()
					scraper.parseInstruction = '06 - maws.xml'
					scraper.source = 'http://maws.mameworld.info/maws/romset/%GAME%'
					scrapers.append(scraper)
					site.scrapers = scrapers
					romCollection.scraperSites = []
					romCollection.scraperSites.append(site)
			else:
				
				if(romCollection.name == 'MAME'):
					romCollection.imagePlacingMain = ImagePlacing()
					romCollection.imagePlacingMain.name = 'gameinfomamecabinet'
					#MAME zip files contain several files but they must be passed to the emu as zip file
					romCollection.doNotExtractZipFiles = True
				
				
				romCollection.mediaPaths = []
				
				lastArtworkPath = ''
				while True:
					
					fileTypeIndex = dialog.select(util.localize(32183), fileTypeList)
					Logutil.log('fileTypeIndex: ' +str(fileTypeIndex), util.LOG_LEVEL_INFO)					
					if(fileTypeIndex == -1):
						Logutil.log('No fileTypeIndex selected.', util.LOG_LEVEL_INFO)
						break
					
					fileType = fileTypeList[fileTypeIndex]
					fileTypeList.remove(fileType)
					
					if(lastArtworkPath == ''):					
						artworkPath = dialog.browse(0, util.localize(32182) %(console, fileType), 'files', '', False, False, romPath)
					else:
						artworkPath = dialog.browse(0, util.localize(32182) %(console, fileType), 'files', '', False, False, lastArtworkPath)
					
					try:
						unicode(artworkPath)
					except:				
						Logutil.log("RCB can't acces your artwork path. Make sure it does not contain any non-ascii characters.", util.LOG_LEVEL_INFO)
						xbmcgui.Dialog().ok(util.SCRIPTNAME, util.localize(32042), errorMsg)
						break
					
					lastArtworkPath = artworkPath
					Logutil.log('artworkPath: ' +str(artworkPath), util.LOG_LEVEL_INFO)
					if(artworkPath == ''):
						Logutil.log('No artworkPath selected.', util.LOG_LEVEL_INFO)
						break
					
					romCollection.mediaPaths.append(self.createMediaPath(fileType, artworkPath, scenarioIndex))
					
					retValue = dialog.yesno(util.localize(32999), util.localize(32184))
					if(retValue == False):
						break
				
				descIndex = dialog.select(util.localize(32185), [util.localize(32186), util.localize(32187), util.localize(32188)])
				Logutil.log('descIndex: ' +str(descIndex), util.LOG_LEVEL_INFO)
				if(descIndex == -1):
					Logutil.log('No descIndex selected. Action canceled.', util.LOG_LEVEL_INFO)
					break
				
				romCollection.descFilePerGame = (descIndex != 1)
				
				if(descIndex == 2):
					#leave scraperSites empty - they will be filled in configwriter
					pass
				
				else:
					descPath = ''
					
					if(romCollection.descFilePerGame):
						#get path
						pathValue = dialog.browse(0, util.localize(32189) %console, 'files')
						if(pathValue == ''):
							break
						
						#get file mask
						keyboard = xbmc.Keyboard()
						keyboard.setHeading(util.localize(32190))
						keyboard.setDefault('%GAME%.txt')
						keyboard.doModal()
						if (keyboard.isConfirmed()):
							filemask = keyboard.getText()
							
						descPath = util.joinPath(pathValue, filemask.strip())
					else:
						descPath = dialog.browse(1, util.localize(32189) %console, 'files', '', False, False, lastArtworkPath)
					
					Logutil.log('descPath: ' +str(descPath), util.LOG_LEVEL_INFO)
					if(descPath == ''):
						Logutil.log('No descPath selected. Action canceled.', util.LOG_LEVEL_INFO)
						break
					
					parserPath = dialog.browse(1, util.localize(32191) %console, 'files', '', False, False, descPath)
					Logutil.log('parserPath: ' +str(parserPath), util.LOG_LEVEL_INFO)
					if(parserPath == ''):
						Logutil.log('No parserPath selected. Action canceled.', util.LOG_LEVEL_INFO)
						break
					
					#create scraper
					site = Site()
					site.name = console
					site.descFilePerGame = (descIndex == 0)
					site.searchGameByCRC = True
					scrapers = []
					scraper = Scraper()
					scraper.parseInstruction = parserPath
					scraper.source = descPath
					scraper.encoding = 'iso-8859-1'
					scrapers.append(scraper)
					site.scrapers = scrapers
					romCollection.scraperSites = []
					romCollection.scraperSites.append(site)
			
			romCollections[romCollection.id] = romCollection						
			
			retValue = dialog.yesno(util.localize(32999), util.localize(32192))
			if(retValue == False):
				break
		
		del dialog
		
		return True, romCollections
	
	
	
	def buildMediaTypeList(self, configObj, isUpdate):
		#build fileTypeList
		fileTypeList = []
		
		if(isUpdate):
			fileTypes = configObj.tree.findall('FileTypes/FileType')
		else:
			#build fileTypeList
			configFile = util.joinPath(util.getAddonInstallPath(), 'resources', 'database', 'config_template.xml')
	
			if(not xbmcvfs.exists(configFile)):
				Logutil.log('File config_template.xml does not exist. Place a valid config file here: ' +str(configFile), util.LOG_LEVEL_ERROR)
				return None, util.localize(32040)
			
			tree = ElementTree().parse(configFile)			
			fileTypes = tree.findall('FileTypes/FileType')			
			
		for fileType in fileTypes:
			name = fileType.attrib.get('name')
			if(name != None):
				type = fileType.find('type')				
				if(type != None and type.text == 'video'):
					name = name +' (video)'
				fileTypeList.append(name)
				
		return fileTypeList, ''
	
	
	def createMediaPath(self, type, path, scenarioIndex):
		
		if(type == 'gameplay (video)'):
			type = 'gameplay'
			
		fileMask = '%GAME%.*'
		if(type == 'romcollection'):
			fileMask = '%ROMCOLLECTION%.*'
		if(type == 'developer'):
			fileMask = '%DEVELOPER%.*'
		if(type == 'publisher'):
			fileMask = '%PUBLISHER%.*'
		
		fileType = FileType()
		fileType.name = type
		
		mediaPath = MediaPath()
		mediaPath.fileType = fileType
		if(scenarioIndex == 0):
			mediaPath.path = util.joinPath(path, type, fileMask)
		else:
			mediaPath.path = util.joinPath(path, fileMask)
				
		return mediaPath
	
	