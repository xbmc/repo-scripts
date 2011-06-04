

import os, sys, shutil

from util import *
import util
from gamedatabase import *
from elementtree.ElementTree import *
from config import ImagePlacing


class ConfigxmlUpdater:
	
	tree = None
	configFile = util.getConfigXmlPath()
	
	def updateConfig(self, gui):
		
		if(not os.path.isfile(self.configFile)):
			return False, 'File config.xml does not exist'
		
		
		tree = ElementTree().parse(self.configFile)
		if(tree == None):
			Logutil.log('Could not read config.xml', util.LOG_LEVEL_ERROR)
			return False, 'Could not read config.xml.'
		
		self.tree = tree
	
		configVersion = tree.attrib.get('version')
		Logutil.log('Reading config version from config.xml: ' +str(configVersion), util.LOG_LEVEL_INFO)
		if(configVersion == None):
			#set to previous version
			configVersion = '0.7.4'
		
		#nothing to do
		if(configVersion == util.CURRENT_CONFIG_VERSION):
			Logutil.log('Config file is up to date', util.LOG_LEVEL_INFO)
			return True, ''
		
		Logutil.log('Config file is out of date. Start update', util.LOG_LEVEL_INFO)
		
		#backup config.xml
		newFileName = self.configFile +'.backup ' +configVersion
		if not os.path.isfile(newFileName):
			try:
				shutil.copy(str(self.configFile), str(newFileName))
			except Exception, (exc):
				return -1, "Error: Cannot backup config.xml: " +str(exc)
		
		#write current version to config
		self.tree.attrib['version'] = util.CURRENT_CONFIG_VERSION
		
		if(configVersion == '0.7.4'):
			success, message = self.update_074_to_086()
			if(not success):
				return False, message
		
		#write file
		success, message = self.writeFile()	
				
		return success, message
	
	
	def update_074_to_086(self):
		
		#update scrapers
		scraperSitesXml = self.tree.findall('Scrapers/Site')
		for scraperSiteXml in scraperSitesXml:
			siteName = scraperSiteXml.attrib.get('name')
			
			#handle online scrapers
			if(siteName == 'local nfo'):
				scraperSiteXml.attrib['descFilePerGame'] = 'True'
				scraperSiteXml.attrib['searchGameByCRC'] = 'False'
			elif(siteName == 'thevideogamedb.com'):
				scraperSiteXml.attrib['descFilePerGame'] = 'True'
				scraperSiteXml.attrib['searchGameByCRC'] = 'True'
			elif(siteName == 'thegamesdb.net'):
				scraperSiteXml.attrib['descFilePerGame'] = 'True'
				scraperSiteXml.attrib['searchGameByCRC'] = 'False'
			elif(siteName == 'giantbomb.com'):
				scraperSiteXml.attrib['descFilePerGame'] = 'True'
				scraperSiteXml.attrib['searchGameByCRC'] = 'False'
			elif(siteName == 'mobygames.com'):
				scraperSiteXml.attrib['descFilePerGame'] = 'True'
				scraperSiteXml.attrib['searchGameByCRC'] = 'False'
			elif(siteName == 'maws.mameworld.info'):
				scraperSiteXml.attrib['descFilePerGame'] = 'True'
				scraperSiteXml.attrib['searchGameByCRC'] = 'False'
				
			#handle offline scrapers
			else:
				#search for rom collection that uses current scraper
				romCollectionsXml = self.tree.findall('RomCollections/RomCollection')
				for romCollectionXml in romCollectionsXml:
					scraperXml = romCollectionXml.find('scraper')
					scraperName = scraperXml.attrib.get('name')
					
					if(scraperName != siteName):
						continue
					
					descFilePerGame = self.readTextElement(romCollectionXml, 'descFilePerGame')
					if(descFilePerGame != ''):
						scraperSiteXml.attrib['descFilePerGame'] = descFilePerGame						
					
					searchGameByCRC = self.readTextElement(romCollectionXml, 'searchGameByCRC')
					if(searchGameByCRC != ''):
						scraperSiteXml.attrib['searchGameByCRC'] = searchGameByCRC						
						
					useFoldernameAsCRC = self.readTextElement(romCollectionXml, 'useFoldernameAsCRC')
					if(useFoldernameAsCRC != ''):
						scraperSiteXml.attrib['useFoldernameAsCRC'] = useFoldernameAsCRC						
						
					useFilenameAsCRC = self.readTextElement(romCollectionXml, 'useFilenameAsCRC')
					if(useFilenameAsCRC != ''):
						scraperSiteXml.attrib['useFilenameAsCRC'] = useFilenameAsCRC						
				
			#remove obsolete entries from rom collections
			romCollectionsXml = self.tree.findall('RomCollections/RomCollection')
			for romCollectionXml in romCollectionsXml:
				self.removeElement(romCollectionXml, 'descFilePerGame')
				self.removeElement(romCollectionXml, 'searchGameByCRC')
				self.removeElement(romCollectionXml, 'useFoldernameAsCRC')
				self.removeElement(romCollectionXml, 'useFilenameAsCRC')
				self.removeElement(romCollectionXml, 'searchGameByCRCIgnoreRomName')
		
		return True, ''
	
	
	#TODO use same as in config
	def readTextElement(self, parent, elementName):
		element = parent.find(elementName)
		if(element != None and element.text != None):
			Logutil.log('%s: %s' %(elementName, element.text), util.LOG_LEVEL_INFO)
			return element.text
		else:
			return ''
		
		
	def removeElement(self, parent, elementName):
		element = parent.find(elementName)
		if(element != None):
			parent.remove(element)
	
	
	#TODO use configxmlwriter
	def writeFile(self):
		#write file		
		try:
			util.indentXml(self.tree)
			treeToWrite = ElementTree(self.tree)			
			treeToWrite.write(self.configFile)
			
			return True, ""
			
		except Exception, (exc):
			print("Error: Cannot write config.xml: " +str(exc))
			return False, "Error: Cannot write config.xml: " +str(exc)