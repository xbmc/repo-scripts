import os

import util
from util import *
import config
from config import *
from elementtree.ElementTree import *


class ConfigXmlWriter:
	
	def __init__(self, createNew):
		
		self.createNew = createNew
		
		if(createNew):
			configFile = os.path.join(util.getAddonInstallPath(), 'resources', 'database', 'config_template.xml')
		else:
			configFile = util.getConfigXmlPath()
		
		if(not os.path.isfile(configFile)):
			Logutil.log('File config.xml does not exist. Place a valid config file here: ' +str(configFile), util.LOG_LEVEL_ERROR)
			return False, 'Error: File config.xml does not exist'
		
		self.tree = ElementTree().parse(configFile)
	
	
	def writeRomCollections(self, romCollections):
				
		romCollectionsXml = self.tree.find('RomCollections')
		
		for romCollection in romCollections.values():
			romCollectionXml = SubElement(romCollectionsXml, 'RomCollection', {'id' : str(romCollection.id), 'name' : romCollection.name})
			SubElement(romCollectionXml, 'emulatorCmd').text = romCollection.emulatorCmd
			SubElement(romCollectionXml, 'emulatorParams').text = romCollection.emulatorParams
			
			for romPath in romCollection.romPaths:
				SubElement(romCollectionXml, 'romPath').text = str(romPath)
				
			for mediaPath in romCollection.mediaPaths:								
				SubElement(romCollectionXml, 'mediaPath', {'type' : mediaPath.type.name}).text = mediaPath.path
				
			#some default values
			SubElement(romCollectionXml, 'ignoreOnScan').text = str(romCollection.ignoreOnScan)
			SubElement(romCollectionXml, 'descFilePerGame').text = str(romCollection.descFilePerGame)
			SubElement(romCollectionXml, 'useFoldernameAsGamename').text = str(romCollection.useFoldernameAsGamename)
			SubElement(romCollectionXml, 'searchGameByCRC').text = str(romCollection.searchGameByCRC)
			SubElement(romCollectionXml, 'maxFolderDepth').text = str(romCollection.maxFolderDepth)
			SubElement(romCollectionXml, 'doNotExtractZipFiles').text = str(romCollection.doNotExtractZipFiles)
			
			if (os.environ.get( "OS", "xbox" ) == "xbox"):
				SubElement(romCollectionXml, 'xboxCreateShortcut').text = str(romCollection.xboxCreateShortcut)
				SubElement(romCollectionXml, 'xboxCreateShortcutAddRomfile').text = str(romCollection.xboxCreateShortcutAddRomfile)
				SubElement(romCollectionXml, 'xboxCreateShortcutUseShortGamename').text = str(romCollection.xboxCreateShortcutUseShortGamename)
				
			#image placing
			if(romCollection.imagePlacing != None and romCollection.imagePlacing.name != ''):
				SubElement(romCollectionXml, 'imagePlacing').text = romCollection.imagePlacing.name 
			else:
				SubElement(romCollectionXml, 'imagePlacing').text = 'gameinfobig'
			
			mobyConsoleId = '0'
			try:
				mobyConsoleId = config.consoleDict[romCollection.name]
			except:
				pass
			
			if(romCollection.scraperSites == None or len(romCollection.scraperSites) == 0):
				#TODO: enable again when site is more complete and responses are faster
				#SubElement(romCollectionXml, 'scraper', {'name' : 'thevideogamedb.com'})
				SubElement(romCollectionXml, 'scraper', {'name' : 'thegamesdb.net', 'replaceKeyString' : '', 'replaceValueString' : ''})
				SubElement(romCollectionXml, 'scraper', {'name' : 'giantbomb.com', 'replaceKeyString' : '', 'replaceValueString' : ''})
				SubElement(romCollectionXml, 'scraper', {'name' : 'mobygames.com', 'replaceKeyString' : '', 'replaceValueString' : '', 'platform' : mobyConsoleId})
			else:
				SubElement(romCollectionXml, 'scraper', {'name' : romCollection.scraperSites[0].name})
				
				#create Scraper element
				scrapersXml = self.tree.find('Scrapers')
				
				#check if the current scraper already exists
				siteExists = False
				sitesXml = scrapersXml.findall('Site')
				for site in sitesXml:
					name = site.attrib.get('name')
					if name == romCollection.scraperSites[0].name:
						siteExists = True
						break
					
				if not siteExists:
					site = SubElement(scrapersXml, 'Site', {'name' : romCollection.scraperSites[0].name})
					SubElement(site, 'Scraper', {'parseInstruction' : romCollection.scraperSites[0].scrapers[0].parseInstruction, 'source' : romCollection.scraperSites[0].scrapers[0].source})
				
				#in case of an update we have to create some new options
				if(romCollection.name == 'MAME' and not self.createNew):					
					self.addFileTypesForMame()
					self.addImagePlacingForMame()
				
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
			SubElement(fileTypeFor, 'fileTypeForGameInfoViewBackground').text = 'boxfront'
			SubElement(fileTypeFor, 'fileTypeForGameInfoViewBackground').text = 'title'			
			SubElement(fileTypeFor, 'fileTypeForGameInfoViewBackground').text = 'action'			
			SubElement(fileTypeFor, 'fileTypeForGameInfoViewGamelist').text = 'boxfront'
			SubElement(fileTypeFor, 'fileTypeForGameInfoView1').text = 'title'
			SubElement(fileTypeFor, 'fileTypeForGameInfoView2').text = 'action'
			SubElement(fileTypeFor, 'fileTypeForGameInfoView3').text = 'cabinet'
			SubElement(fileTypeFor, 'fileTypeForGameInfoView4').text = 'marquee'
			
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
			SubElement(fileTypeFor, 'fileTypeForGameInfoViewBackground').text = 'boxfront'
			SubElement(fileTypeFor, 'fileTypeForGameInfoViewBackground').text = 'title'			
			SubElement(fileTypeFor, 'fileTypeForGameInfoViewBackground').text = 'action'			
			SubElement(fileTypeFor, 'fileTypeForGameInfoViewGamelist').text = 'boxfront'
			SubElement(fileTypeFor, 'fileTypeForGameInfoView1').text = 'title'
			SubElement(fileTypeFor, 'fileTypeForGameInfoView2').text = 'action'
			SubElement(fileTypeFor, 'fileTypeForGameInfoView3').text = 'cabinet'
			SubElement(fileTypeFor, 'fileTypeForGameInfoView4').text = 'marquee'
		
						
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