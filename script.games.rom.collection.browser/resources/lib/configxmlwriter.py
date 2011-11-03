import os

import util
from util import *
import config
from config import *
from elementtree.ElementTree import *


class ConfigXmlWriter:
	
	def __init__(self, createNew):
		
		Logutil.log('init ConfigXmlWriter', util.LOG_LEVEL_INFO)
		
		self.createNew = createNew
		
		if(createNew):
			configFile = os.path.join(util.getAddonInstallPath(), 'resources', 'database', 'config_template.xml')
		else:
			configFile = util.getConfigXmlPath()
		
		if(not os.path.isfile(configFile)):
			Logutil.log('File config.xml does not exist. Place a valid config file here: ' +str(configFile), util.LOG_LEVEL_ERROR)
			return False, 'Error: File config.xml does not exist'
		
		self.tree = ElementTree().parse(configFile)
	
	
	def writeRomCollections(self, romCollections, isEdit):
				
		Logutil.log('write Rom Collections', util.LOG_LEVEL_INFO)
				
		romCollectionsXml = self.tree.find('RomCollections')
		
		#HACK: remove all Rom Collections and create new
		if(isEdit):
			for romCollectionXml in romCollectionsXml.findall('RomCollection'):				
				romCollectionsXml.remove(romCollectionXml)
				
		
		for romCollection in romCollections.values():
			
			Logutil.log('write Rom Collection: ' +str(romCollection.name), util.LOG_LEVEL_INFO)
			
			romCollectionXml = SubElement(romCollectionsXml, 'RomCollection', {'id' : str(romCollection.id), 'name' : romCollection.name})
			SubElement(romCollectionXml, 'emulatorCmd').text = romCollection.emulatorCmd
			SubElement(romCollectionXml, 'emulatorParams').text = romCollection.emulatorParams
			
			for romPath in romCollection.romPaths:
				SubElement(romCollectionXml, 'romPath').text = str(romPath)
				
			SubElement(romCollectionXml, 'saveStatePath').text = romCollection.saveStatePath
			SubElement(romCollectionXml, 'saveStateParams').text = romCollection.saveStateParams
				
			for mediaPath in romCollection.mediaPaths:
				
				success, message = self.searchConfigObjects('FileTypes/FileType', mediaPath.fileType.name, 'FileType')
				if(not success):
					return False, message								
												
				SubElement(romCollectionXml, 'mediaPath', {'type' : mediaPath.fileType.name}).text = mediaPath.path
				
			SubElement(romCollectionXml, 'useEmuSolo').text = str(romCollection.useEmuSolo)
			SubElement(romCollectionXml, 'ignoreOnScan').text = str(romCollection.ignoreOnScan)
			SubElement(romCollectionXml, 'allowUpdate').text = str(romCollection.allowUpdate)
			SubElement(romCollectionXml, 'useFoldernameAsGamename').text = str(romCollection.useFoldernameAsGamename)
			SubElement(romCollectionXml, 'maxFolderDepth').text = str(romCollection.maxFolderDepth)
			SubElement(romCollectionXml, 'doNotExtractZipFiles').text = str(romCollection.doNotExtractZipFiles)
			SubElement(romCollectionXml, 'diskPrefix').text = str(romCollection.diskPrefix)
			
			if (os.environ.get( "OS", "xbox" ) == "xbox"):
				SubElement(romCollectionXml, 'xboxCreateShortcut').text = str(romCollection.xboxCreateShortcut)
				SubElement(romCollectionXml, 'xboxCreateShortcutAddRomfile').text = str(romCollection.xboxCreateShortcutAddRomfile)
				SubElement(romCollectionXml, 'xboxCreateShortcutUseShortGamename').text = str(romCollection.xboxCreateShortcutUseShortGamename)
				
			#image placing
			if(romCollection.imagePlacingMain != None and romCollection.imagePlacingMain.name != ''):
				success, message = self.searchConfigObjects('ImagePlacing/fileTypeFor', romCollection.imagePlacingMain.name, 'ImagePlacing')
				if(not success):
					return False, message
				SubElement(romCollectionXml, 'imagePlacingMain').text = romCollection.imagePlacingMain.name 
			else:
				SubElement(romCollectionXml, 'imagePlacingMain').text = 'gameinfobig'
				
			if(romCollection.imagePlacingInfo != None and romCollection.imagePlacingInfo.name != ''):
				success, message = self.searchConfigObjects('ImagePlacing/fileTypeFor', romCollection.imagePlacingInfo.name, 'ImagePlacing')
				if(not success):
					return False, message
				SubElement(romCollectionXml, 'imagePlacingInfo').text = romCollection.imagePlacingInfo.name 
			else:
				SubElement(romCollectionXml, 'imagePlacingInfo').text = 'gameinfobig'
			
			if(romCollection.scraperSites == None or len(romCollection.scraperSites) == 0):
				#TODO: enable again when site is more complete and responses are faster
				#SubElement(romCollectionXml, 'scraper', {'name' : 'thevideogamedb.com'})
				SubElement(romCollectionXml, 'scraper', {'name' : 'thegamesdb.net', 'replaceKeyString' : '', 'replaceValueString' : ''})
				SubElement(romCollectionXml, 'scraper', {'name' : 'giantbomb.com', 'replaceKeyString' : '', 'replaceValueString' : ''})
				SubElement(romCollectionXml, 'scraper', {'name' : 'mobygames.com', 'replaceKeyString' : '', 'replaceValueString' : ''})
			else:
				for scraperSite in romCollection.scraperSites:
				
					if(scraperSite == None):
						continue
						
					#HACK: use replaceKey and -Value only from first scraper
					firstScraper = scraperSite.scrapers[0]
					SubElement(romCollectionXml, 'scraper', {'name' : scraperSite.name, 'replaceKeyString' : firstScraper.replaceKeyString, 'replaceValueString' : firstScraper.replaceValueString})
					
					#create Scraper element
					scrapersXml = self.tree.find('Scrapers')
					
					#check if the current scraper already exists
					siteExists = False
					sitesXml = scrapersXml.findall('Site')
					for site in sitesXml:
						name = site.attrib.get('name')
						if name == scraperSite.name:
							siteExists = True
							break
						
					if not siteExists:
						#HACK: this only covers the first scraper (for offline scrapers)
						site = SubElement(scrapersXml, 'Site', 
							{ 
							'name' : scraperSite.name,
							'descFilePerGame' : str(scraperSite.descFilePerGame),
							'searchGameByCRC' : str(scraperSite.searchGameByCRC),
							'useFoldernameAsCRC' : str(scraperSite.useFoldernameAsCRC),
							'useFilenameAsCRC' : str(scraperSite.useFilenameAsCRC)
							})
																		
						scraper = scraperSite.scrapers[0]
						SubElement(site, 'Scraper', 
							{ 
							'parseInstruction' : scraper.parseInstruction,
							'source' : scraper.source,
							'encoding' : scraper.encoding
							})
			
			if(not self.createNew):	
				#in case of an update we have to create new options
				if(romCollection.name == 'MAME' and not self.createNew):					
					self.addFileTypesForMame()
					self.addImagePlacingForMame()
				
		success, message = self.writeFile()
		return success, message
	
	
	def writeScrapers(self, scrapers):
		
		Logutil.log('write scraper sites', util.LOG_LEVEL_INFO)
				
		scraperSitesXml = self.tree.find('Scrapers')
				
		#HACK: remove all scrapers and create new
		for scraperSiteXml in scraperSitesXml.findall('Site'):				
			scraperSitesXml.remove(scraperSiteXml)
			
		for scraperSite in scrapers.values():
			
			Logutil.log('write scraper site: ' +str(scraperSite.name), util.LOG_LEVEL_INFO)
			
			#Don't write None-Scraper
			if(scraperSite.name == 'None'):
				Logutil.log('None scraper will be skipped', util.LOG_LEVEL_INFO)
				continue
			
			scraperSiteXml = SubElement(scraperSitesXml, 'Site', 
					{ 
					'name' : scraperSite.name,
					'descFilePerGame' : str(scraperSite.descFilePerGame),
					'searchGameByCRC' : str(scraperSite.searchGameByCRC),
					'useFoldernameAsCRC' : str(scraperSite.useFoldernameAsCRC),
					'useFilenameAsCRC' : str(scraperSite.useFilenameAsCRC)
					})
			
			for scraper in scraperSite.scrapers:
				
				#check if we can use a relative path to parseInstructions
				rcbScraperPath = os.path.join(util.RCBHOME, 'resources', 'scraper')
				pathParts = os.path.split(scraper.parseInstruction)
				if(pathParts[0].upper() == rcbScraperPath.upper()):
					scraper.parseInstruction = pathParts[1]
				
				scraperXml = SubElement(scraperSiteXml, 'Scraper', 
					{ 
					'parseInstruction' : scraper.parseInstruction,
					'source' : scraper.source,
					'encoding' : scraper.encoding,
					'returnUrl' : str(scraper.returnUrl)
					})
		
		success, message = self.writeFile()
		return success, message
	
	
	def searchConfigObjects(self, xPath, nameToCompare, objectType):		
		objects = self.tree.findall(xPath)
		objectFound = False
		for obj in objects:
			objectName = obj.attrib.get('name')
			if(objectName == nameToCompare):
				objectFound = True
				break
		
		if(not objectFound):
			return False, '%s %s could not be found in config.xml' %(objectType, nameToCompare)
		
		return True, ''
	
		
	def removeRomCollection(self, RCName):
		configFile = util.getConfigXmlPath()
		self.tree = ElementTree().parse(configFile)
		romCollectionsXml = self.tree.find('RomCollections')
		for romCollectionXml in romCollectionsXml.findall('RomCollection'):
			name = romCollectionXml.attrib.get('name')
			if(name == RCName):
				romCollectionsXml.remove(romCollectionXml)	
				
		success, message = self.writeFile()
		return success, message
		
	def addFileTypesForMame(self):
		
		fileTypesXml = self.tree.find('FileTypes')
				
		#check if the MAME FileTypes already exist
		cabinetExists = False
		marqueeExists = False
		actionExists = False
		titleExists = False
		highestId = 0
		fileTypeXml = fileTypesXml.findall('FileType')
		for fileType in fileTypeXml:
			name = fileType.attrib.get('name')
			if name == 'cabinet':
				cabinetExists = True
			elif name == 'marquee':
				marqueeExists = True
			elif name == 'action':
				actionExists = True
			elif name == 'marquee':
				titleExists = True
			
			id = fileType.attrib.get('id')
			if int(id) > highestId:
				highestId = int(id)
		
		if not cabinetExists:
			self.createFileType(fileTypesXml, str(highestId +1), 'cabinet', 'image', 'game')
		if not marqueeExists:
			self.createFileType(fileTypesXml, str(highestId +2), 'marquee', 'image', 'game')			
		if not actionExists:
			self.createFileType(fileTypesXml, str(highestId +3), 'action', 'image', 'game')
		if not titleExists:
			self.createFileType(fileTypesXml, str(highestId +4), 'title', 'image', 'game')			
			
		
	def createFileType(self, fileTypesXml, id, name, type, parent):
		fileType = SubElement(fileTypesXml, 'FileType', {'id' : str(id), 'name' : name})
		SubElement(fileType, 'type').text = type
		SubElement(fileType, 'parent').text = parent
		
		
	def addImagePlacingForMame(self):
		
		imagePlacingXml = self.tree.find('ImagePlacing')
		
		#check if the MAME ImagePlacing options already exist
		cabinetExists = False
		marqueeExists = False		
		fileTypeForXml = imagePlacingXml.findall('fileTypeFor')
		for fileTypeFor in fileTypeForXml:
			name = fileTypeFor.attrib.get('name')
			if name == 'gameinfomamecabinet':
				cabinetExists = True
			elif name == 'gameinfomamemarquee':
				marqueeExists = True
				
		if not cabinetExists:
			fileTypeFor = SubElement(imagePlacingXml, 'fileTypeFor', {'name' : 'gameinfomamecabinet'})
			SubElement(fileTypeFor, 'fileTypeForGameList').text = 'cabinet'
			SubElement(fileTypeFor, 'fileTypeForGameList').text = 'boxfront'
			SubElement(fileTypeFor, 'fileTypeForGameList').text = 'title'
			SubElement(fileTypeFor, 'fileTypeForGameListSelected').text = 'cabinet'
			SubElement(fileTypeFor, 'fileTypeForGameListSelected').text = 'boxfront'
			SubElement(fileTypeFor, 'fileTypeForGameListSelected').text = 'title'			
			SubElement(fileTypeFor, 'fileTypeForMainViewBackground').text = 'boxfront'
			SubElement(fileTypeFor, 'fileTypeForMainViewBackground').text = 'title'
			SubElement(fileTypeFor, 'fileTypeForMainViewBackground').text = 'action'
			SubElement(fileTypeFor, 'fileTypeForMainViewGameInfoUpperLeft').text = 'title'
			SubElement(fileTypeFor, 'fileTypeForMainViewGameInfoUpperRight').text = 'action'
			SubElement(fileTypeFor, 'fileTypeForMainViewGameInfoLower').text = 'marquee'
			
		if not marqueeExists:
			fileTypeFor = SubElement(imagePlacingXml, 'fileTypeFor', {'name' : 'gameinfomamemarquee'})
			SubElement(fileTypeFor, 'fileTypeForGameList').text = 'marquee'
			SubElement(fileTypeFor, 'fileTypeForGameList').text = 'boxfront'
			SubElement(fileTypeFor, 'fileTypeForGameList').text = 'title'
			SubElement(fileTypeFor, 'fileTypeForGameListSelected').text = 'marquee'
			SubElement(fileTypeFor, 'fileTypeForGameListSelected').text = 'boxfront'
			SubElement(fileTypeFor, 'fileTypeForGameListSelected').text = 'title'			
			SubElement(fileTypeFor, 'fileTypeForMainViewBackground').text = 'boxfront'
			SubElement(fileTypeFor, 'fileTypeForMainViewBackground').text = 'title'
			SubElement(fileTypeFor, 'fileTypeForMainViewBackground').text = 'action'
			SubElement(fileTypeFor, 'fileTypeForMainViewGameInfoLeft').text = 'cabinet'
			SubElement(fileTypeFor, 'fileTypeForMainViewGameInfoUpperRight').text = 'action'
			SubElement(fileTypeFor, 'fileTypeForMainViewGameInfoLowerRight').text = 'title'
		
						
	def writeFile(self):
		#write file		
		try:
			configFile = util.getConfigXmlPath()
			
			util.indentXml(self.tree)
			treeToWrite = ElementTree(self.tree)			
			treeToWrite.write(configFile)
			
			return True, ""
			
		except Exception, (exc):
			print("Error: Cannot write config.xml: " +str(exc))
			return False, "Error: Cannot write config.xml: " +str(exc)