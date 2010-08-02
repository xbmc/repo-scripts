
import os, sys, string, re
from pysqlite2 import dbapi2 as sqlite
from xml.dom.minidom import Document, parseString

from gamedatabase import *
import util

#TODO use elementtree instead of minidom
from elementtree.ElementTree import *

class SettingsImporter:
	
	def importSettings(self, gdb, databaseDir, gui):
		
		self.gdb = gdb
		configFile = os.path.join(databaseDir, 'config.xml')
		
		if(os.path.isfile(configFile)):
			try:
				fh=open(configFile,"r")
				xmlDoc = fh.read()
				fh.close()				
			except Exception, (exc):
				util.log('Cannot open file config.xml: ' +str(exc), util.LOG_LEVEL_ERROR)
				return False, 'Error: Cannot open file config.xml'
				
			try:
				xmlDoc = parseString(xmlDoc)
			except Exception, (exc):
				util.log('config.xml is no valid XML File: ' +str(exc), util.LOG_LEVEL_ERROR)
				return False, 'Error: config.xml is no valid XML File'
				
		else:	
			util.log('File config.xml does not exist', util.LOG_LEVEL_ERROR)
			return False, 'Error: File config.xml does not exist'

		#itemCount and stepCount are used to show percentage in ProgressDialog		
		gui.itemCount = 5
		stepCount = 1
		gui.writeMsg("Importing Settings...", stepCount)
				
		#check config.xml
		success, errorCount = self.checkFileStructure(xmlDoc, configFile)
		if(not success):
			return False, 'Error: config.xml has %i error(s)!' %errorCount
		
		#start import
		rcbSettings = xmlDoc.getElementsByTagName('RCBSettings')
				
		for rcbSetting in rcbSettings:
			favoriteConsole = self.getElementValue(rcbSetting, 'favoriteConsole')
			favoriteGenre = self.getElementValue(rcbSetting, 'favoriteGenre')
			showEntryAllConsoles = self.getElementValue(rcbSetting, 'showEntryAllConsoles')
			showEntryAllGenres = self.getElementValue(rcbSetting, 'showEntryAllGenres')
			showEntryAllYears = self.getElementValue(rcbSetting, 'showEntryAllYears')
			showEntryAllPublisher = self.getElementValue(rcbSetting, 'showEntryAllPublisher')
			saveViewStateOnExit = self.getElementValue(rcbSetting, 'saveViewStateOnExit')
			saveViewStateOnLaunchEmu = self.getElementValue(rcbSetting, 'saveViewStateOnLaunchEmu')
			
			self.insertRCBSetting(favoriteConsole, favoriteGenre, showEntryAllConsoles, showEntryAllGenres, showEntryAllYears, showEntryAllPublisher, 
				saveViewStateOnExit, saveViewStateOnLaunchEmu)
			
		stepCount = stepCount +1
		gui.writeMsg("Importing Console Info...", stepCount)
		
		consoles = xmlDoc.getElementsByTagName('Console')
		for console in consoles:			
			consoleName = self.getElementValue(console, 'name')
			consoleDesc = self.getElementValue(console, 'desc')
			consoleImage =  self.getElementValue(console, 'imgFile')
			
			self.insertConsole(consoleName, consoleDesc, consoleImage)
		
		
		stepCount = stepCount +1
		gui.writeMsg("Importing File Types...", stepCount)
		
		#import internal file types
		self.insertFileType('rcb_rom', 'image', 'game')
		self.insertFileType('rcb_manual', 'image', 'game')
		self.insertFileType('rcb_description', 'image', 'game')
		self.insertFileType('rcb_configuration', 'image', 'game')
		
		#import user defined file types
		fileTypes = xmlDoc.getElementsByTagName('FileType')
		for fileType in fileTypes:
			name = self.getElementValue(fileType, 'name')
			type = self.getElementValue(fileType, 'type')
			parent = self.getElementValue(fileType, 'parent')
			
			self.insertFileType(name, type, parent)
		
		
		stepCount = stepCount +1
		gui.writeMsg("Importing Rom Collections...", stepCount)
		
		#fileTypesForControl must be deleted. There is no useful unique key
		FileTypeForControl(self.gdb).deleteAll()
		
		romCollections = xmlDoc.getElementsByTagName('RomCollection')
		for romCollection in romCollections:			
			romCollName = self.getElementValue(romCollection, 'name')			
			consoleName = self.getElementValue(romCollection, 'consoleName')
			emuCmd = self.getElementValue(romCollection, 'emulatorCmd')
			emuSolo = self.getElementValue(romCollection, 'useEmuSolo')
			escapeCmd = self.getElementValue(romCollection, 'escapeCommand')
			relyOnNaming = self.getElementValue(romCollection, 'relyOnNaming')
			startWithDescFile = self.getElementValue(romCollection, 'startWithDescFile')
			descFilePerGame = self.getElementValue(romCollection, 'descFilePerGame')			
			descParserFile = self.getElementValue(romCollection, 'descriptionParserFile')			
			diskPrefix = self.getElementValue(romCollection, 'diskPrefix')
			typeOfManual = self.getElementValue(romCollection, 'typeOfManual')
			allowUpdate = self.getElementValue(romCollection, 'allowUpdate')
			ignoreOnScan = self.getElementValue(romCollection, 'ignoreOnScan')
			searchGameByCRC = self.getElementValue(romCollection, 'searchGameByCRC')
			searchGameByCRCIgnoreRomName = self.getElementValue(romCollection, 'searchGameByCRCIgnoreRomName')
			ignoreGameWithoutDesc = self.getElementValue(romCollection, 'ignoreGameWithoutDesc')
				
			
			romPaths = self.getElementValues(romCollection, 'romPath')
			descFilePaths = self.getElementValues(romCollection, 'descFilePath')
			configFilePaths = self.getElementValues(romCollection, 'configFilePath')
			manualPaths = self.getElementValues(romCollection, 'manualPath')
			
			
			#import romCollection first to obtain the id
			romCollectionId = self.insertRomCollection(consoleName, romCollName, emuCmd, emuSolo, escapeCmd, relyOnNaming, startWithDescFile, 
				descFilePerGame, descParserFile, diskPrefix, typeOfManual, allowUpdate, ignoreOnScan, searchGameByCRC, 
				searchGameByCRCIgnoreRomName, ignoreGameWithoutDesc)
			
			
			self.insertPaths(romCollectionId, romPaths, 'rcb_rom')
			self.insertPaths(romCollectionId, descFilePaths, 'rcb_description')
			self.insertPaths(romCollectionId, configFilePaths, 'rcb_configuration')
			self.insertPaths(romCollectionId, manualPaths, 'rcb_manual')
			
			
			self.handleTypedElements(romCollection, 'mediaPath', romCollectionId)
			
			fileTypesForGameList = self.getElementValues(romCollection, 'fileTypeForGameList')
			fileTypesForGameListSelected = self.getElementValues(romCollection, 'fileTypeForGameListSelected')			
			fileTypesForMainView1 = self.getElementValues(romCollection, 'fileTypeForMainView1')
			fileTypesForMainView2 = self.getElementValues(romCollection, 'fileTypeForMainView2')
			fileTypesForMainView3 = self.getElementValues(romCollection, 'fileTypeForMainView3')						
			fileTypesForMainViewBackground = self.getElementValues(romCollection, 'fileTypeForMainViewBackground')
			fileTypesForMainViewGameInfoBig = self.getElementValues(romCollection, 'fileTypeForMainViewGameInfoBig')
			fileTypesForMainViewGameInfoUpperLeft = self.getElementValues(romCollection, 'fileTypeForMainViewGameInfoUpperLeft')
			fileTypesForMainViewGameInfoUpperRight = self.getElementValues(romCollection, 'fileTypeForMainViewGameInfoUpperRight')
			fileTypesForMainViewGameInfoLowerLeft = self.getElementValues(romCollection, 'fileTypeForMainViewGameInfoLowerLeft')
			fileTypesForMainViewGameInfoLowerRight = self.getElementValues(romCollection, 'fileTypeForMainViewGameInfoLowerRight')
			fileTypesForMainViewVideoWindowBig = self.getElementValues(romCollection, 'fileTypeForMainViewVideoWindowBig')
			fileTypesForMainViewVideoWindowSmall = self.getElementValues(romCollection, 'fileTypeForMainViewVideoWindowSmall')
			
			fileTypesForGameInfoViewBackground = self.getElementValues(romCollection, 'fileTypeForGameInfoViewBackground')
			fileTypesForGameInfoViewGamelist = self.getElementValues(romCollection, 'fileTypeForGameInfoViewGamelist')
			fileTypesForGameInfoView1 = self.getElementValues(romCollection, 'fileTypeForGameInfoView1')
			fileTypesForGameInfoView2 = self.getElementValues(romCollection, 'fileTypeForGameInfoView2')
			fileTypesForGameInfoView3 = self.getElementValues(romCollection, 'fileTypeForGameInfoView3')
			fileTypesForGameInfoView4 = self.getElementValues(romCollection, 'fileTypeForGameInfoView4')
			fileTypesForGameInfoViewVideoWindow = self.getElementValues(romCollection, 'fileTypeForGameInfoViewVideoWindow')


			self.insertFileTypeForControl(romCollectionId, fileTypesForGameList, 'gamelist')
			self.insertFileTypeForControl(romCollectionId, fileTypesForGameListSelected, 'gamelistselected')
			self.insertFileTypeForControl(romCollectionId, fileTypesForMainView1, 'mainview1')
			self.insertFileTypeForControl(romCollectionId, fileTypesForMainView2, 'mainview2')
			self.insertFileTypeForControl(romCollectionId, fileTypesForMainView3, 'mainview3')
			self.insertFileTypeForControl(romCollectionId, fileTypesForMainViewBackground, 'mainviewbackground')
			self.insertFileTypeForControl(romCollectionId, fileTypesForMainViewGameInfoBig, 'mainviewgameinfobig')
			self.insertFileTypeForControl(romCollectionId, fileTypesForMainViewGameInfoUpperLeft, 'mainviewgameinfoupperleft')
			self.insertFileTypeForControl(romCollectionId, fileTypesForMainViewGameInfoUpperRight, 'mainviewgameinfoupperright')
			self.insertFileTypeForControl(romCollectionId, fileTypesForMainViewGameInfoLowerLeft, 'mainviewgameinfolowerleft')
			self.insertFileTypeForControl(romCollectionId, fileTypesForMainViewGameInfoLowerRight, 'mainviewgameinfolowerright')
			self.insertFileTypeForControl(romCollectionId, fileTypesForMainViewVideoWindowBig, 'mainviewvideowindowbig')
			self.insertFileTypeForControl(romCollectionId, fileTypesForMainViewVideoWindowSmall, 'mainviewvideowindowsmall')			
			
			self.insertFileTypeForControl(romCollectionId, fileTypesForGameInfoViewBackground, 'gameinfoviewbackground')
			self.insertFileTypeForControl(romCollectionId, fileTypesForGameInfoViewGamelist, 'gameinfoviewgamelist')
			self.insertFileTypeForControl(romCollectionId, fileTypesForGameInfoView1, 'gameinfoview1')
			self.insertFileTypeForControl(romCollectionId, fileTypesForGameInfoView2, 'gameinfoview2')
			self.insertFileTypeForControl(romCollectionId, fileTypesForGameInfoView3, 'gameinfoview3')
			self.insertFileTypeForControl(romCollectionId, fileTypesForGameInfoView4, 'gameinfoview4')
			self.insertFileTypeForControl(romCollectionId, fileTypesForGameInfoViewVideoWindow, 'gameinfoviewvideowindow')
			
		#TODO Transaction?
		gdb.commit()
		stepCount = stepCount +1
		gui.writeMsg("Done.", stepCount)
		return True, ''				
	
	
	def getElementValue(self, parentNode, elementName):
		nodeList = parentNode.getElementsByTagName(elementName)
		if(nodeList == None or len(nodeList) == 0):
			return ""					
			
		node = nodeList[0]
		if(node == None):
			return ""
		
		firstChild = node.firstChild
		if(firstChild == None):
			return ""
			
		return firstChild.nodeValue
		
	
	def getElementValues(self, parentNode, elementName):
		valueList = []
		nodeList = parentNode.getElementsByTagName(elementName)
		for node in nodeList:
			if(node == None):
				continue
			if(node.firstChild == None):
				continue
			valueList.append(node.firstChild.nodeValue)
			
		return valueList
		
		
	def handleTypedElements(self, parentNode, elementName, romCollectionId):
		
		nodeList = parentNode.getElementsByTagName(elementName)
		for node in nodeList:
			
			fileType = self.getAttribute(node, 'type')
			if(fileType == ''):
				continue
				
			fileTypeRow = FileType(self.gdb).getOneByName(fileType)			
			if(fileTypeRow == None):				
				continue						
			
			self.insertPath(node.firstChild.nodeValue, fileType, fileTypeRow[0], romCollectionId)
			
	
	def getAttribute(self, node, attrName):
		if(node == None):				
			return ''				
		
		if(not node.hasAttributes()):			
			return ''
			
		attr = node.getAttribute(attrName)
		if(attr == None):
			return ''
			
		return attr
	
	
	def insertRCBSetting(self, favoriteConsole, favoriteGenre, showEntryAllConsoles, showEntryAllGenres, showEntryAllYears, showEntryAllPublisher, saveViewStateOnExit, saveViewStateOnLaunchEmu):
		
		rcbSettingRows = RCBSetting(self.gdb).getAll()
		
		if(favoriteConsole == ''):
			favoriteConsole = None
		if(favoriteGenre == ''):
			favoriteGenre = None
		if(showEntryAllConsoles == ''):
			showEntryAllConsoles = 'True'
		if(showEntryAllGenres == ''):
			showEntryAllGenres = 'True'
		if(showEntryAllYears == ''):
			showEntryAllYears = 'True'
		if(showEntryAllPublisher == ''):
			showEntryAllPublisher = 'True'
		if(saveViewStateOnExit == ''):
			saveViewStateOnExit = 'False'
		if(saveViewStateOnLaunchEmu == ''):
			saveViewStateOnLaunchEmu = 'False'
		
		if(rcbSettingRows == None or len(rcbSettingRows) == 0):			
			RCBSetting(self.gdb).insert((None, None, None, None, None, None, favoriteConsole, favoriteGenre, None, CURRENT_SCRIPT_VERSION, 
				showEntryAllConsoles, showEntryAllGenres, showEntryAllYears, showEntryAllPublisher, saveViewStateOnExit, saveViewStateOnLaunchEmu, None, None))
		else:
			rcbSetting = rcbSettingRows[0]
			RCBSetting(self.gdb).update(('dbVersion', 'favoriteConsoleId', 'favoriteGenreId', 'showEntryAllConsoles', 'showEntryAllGenres', 'showEntryAllYears', 'showEntryAllPublisher', 'saveViewStateOnExit', 'saveViewStateOnLaunchEmu'),
				(CURRENT_SCRIPT_VERSION, favoriteConsole, favoriteGenre, showEntryAllConsoles, showEntryAllGenres, showEntryAllYears, showEntryAllPublisher, saveViewStateOnExit, saveViewStateOnLaunchEmu), rcbSetting[0])
	
	
	def insertConsole(self, consoleName, consoleDesc, consoleImage):
		consoleRow = Console(self.gdb).getOneByName(consoleName)		
		if(consoleRow == None):			
			Console(self.gdb).insert((consoleName, consoleDesc, consoleImage))
		else:
			Console(self.gdb).update(('name', 'description', 'imageFileName'), (consoleName, consoleDesc, consoleImage), consoleRow[0])
	
	
	def insertRomCollection(self, consoleName, romCollName, emuCmd, emuSolo, escapeCmd, relyOnNaming, startWithDescFile, 
				descFilePerGame, descParserFile, diskPrefix, typeOfManual, allowUpdate, ignoreOnScan, searchGameByCRC, 
				searchGameByCRCIgnoreRomName, ignoreGameWithoutDesc):		
		
		#set default values
		if(emuSolo == ''):
			emuSolo = 'False'
		if(escapeCmd == ''):
			escapeCmd = 'True'
		if(relyOnNaming == ''):
			relyOnNaming = 'True'
		if(startWithDescFile == ''):
			startWithDescFile = 'False'
		if(descFilePerGame == ''):
			descFilePerGame = 'False'
		if(diskPrefix == ''):
			diskPrefix = '_Disk'
		if(typeOfManual == ''):
			typeOfManual = ''
		if(allowUpdate == ''):
			allowUpdate = 'True'
		if(ignoreOnScan == ''):
			ignoreOnScan = 'False'
		if(searchGameByCRC == ''):
			searchGameByCRC = 'True'
		if(searchGameByCRCIgnoreRomName == ''):
			searchGameByCRCIgnoreRomName = 'False'
		if(ignoreGameWithoutDesc == ''):
			ignoreGameWithoutDesc = 'False'	
		
		consoleRow = Console(self.gdb).getOneByName(consoleName)
		if(consoleRow == None):
			#TODO error handling
			return
		consoleId = consoleRow[0] 
				
		romCollectionRow = RomCollection(self.gdb).getOneByName(romCollName)
		if(romCollectionRow == None):		
			RomCollection(self.gdb).insert((romCollName, consoleId, emuCmd, emuSolo, escapeCmd, descParserFile, relyOnNaming, 
			startWithDescFile, descFilePerGame, diskPrefix, typeOfManual, allowUpdate, ignoreOnScan, searchGameByCRC, searchGameByCRCIgnoreRomName, 
			ignoreGameWithoutDesc))
			romCollectionId = self.gdb.cursor.lastrowid
		else:
			RomCollection(self.gdb).update(('name', 'consoleId', 'emuCommandline', 'useEmuSolo', 'escapeEmuCmd', 'descriptionParserFile', 'relyOnFileNaming', 'startWithDescFile',
								'descFilePerGame', 'diskPrefix', 'typeOfManual', 'allowUpdate', 'ignoreOnScan', 'searchGameByCRC', 'searchGameByCRCIgnoreRomName', 'ignoreGameWithoutDesc'),
								(romCollName, consoleId, emuCmd, emuSolo, escapeCmd, descParserFile, relyOnNaming, startWithDescFile, descFilePerGame, diskPrefix, typeOfManual, allowUpdate, 
								ignoreOnScan, searchGameByCRC, searchGameByCRCIgnoreRomName, ignoreGameWithoutDesc),
								romCollectionRow[0])
			
			romCollectionId = romCollectionRow[0]
			
		return romCollectionId
		
	
	def insertFileType(self, fileTypeName, type, parent):
		fileTypeRow = FileType(self.gdb).getOneByName(fileTypeName)
		if(fileTypeRow == None):				
			FileType(self.gdb).insert((fileTypeName, type, parent))
			return self.gdb.cursor.lastrowid
		return fileTypeRow[0]
		
			

	def insertPaths(self, romCollectionId, paths, fileType):
		fileTypeRow = FileType(self.gdb).getOneByName(fileType)
		if(fileTypeRow == None):
			#TODO error handling
			return
			
		for path in paths:
			self.insertPath(path, fileType, fileTypeRow[0], romCollectionId)
				
	
	def insertPath(self, path, fileTypeName, fileTypeId, romCollectionId):
		
		pathRow = Path(self.gdb).getPathByNameAndTypeAndRomCollectionId(path, fileTypeName, romCollectionId)
		if(pathRow == None):				
			Path(self.gdb).insert((path, fileTypeId, romCollectionId))
				
	
	def insertFileTypeForControl(self, romCollectionId, fileTypes, control):
		for i in range(0, len(fileTypes)):
			fileType = fileTypes[i]
				
			fileTypeRow = FileType(self.gdb).getOneByName(fileType)			
			if(fileTypeRow == None):				
				return						
			
			fileTypeForControlRow = FileTypeForControl(self.gdb).getFileTypeForControlByKey(romCollectionId, fileType, control, str(i))
			if(fileTypeForControlRow == None):
				FileTypeForControl(self.gdb).insert((control, str(i), romCollectionId, fileTypeRow[0]))


	def checkFileStructure(self, xmlDoc, configFile):
		
		#load xmlDoc as elementtree to check with xpaths
		tree = ElementTree().parse(configFile)
		
		errorCount = 0
		
		#RCBSettings
		rcbSettings = xmlDoc.getElementsByTagName('RCBSettings')		
		if(len(rcbSettings) != 1):
			errorCount = errorCount +1
			util.log('Import Settings: Error in config.xml. There must be exactly 1 RCBSettings entry!', util.LOG_LEVEL_ERROR)
			
		#Consoles
		consoles = xmlDoc.getElementsByTagName('Console')
		if(len(consoles) == 0):
			errorCount = errorCount +1
			util.log('Import Settings: Error in config.xml. You must have at least 1 Console entry!', util.LOG_LEVEL_ERROR)
		
		for console in consoles:			
			consoleName = self.getElementValue(console, 'name')
			if(consoleName == ''):
				errorCount = errorCount +1
				util.log('Import Settings: Error in config.xml. Console must have a name!', util.LOG_LEVEL_ERROR)
				
		#FileTypes
		fileTypes = xmlDoc.getElementsByTagName('FileType')
		if(len(fileTypes) == 0):
			errorCount = errorCount +1
			util.log('Import Settings: Error in config.xml. You must have at least 1 FileType entry!', util.LOG_LEVEL_ERROR)
		
		for fileType in fileTypes:
			
			name = self.getElementValue(fileType, 'name')			
			if(name == ''):
				errorCount = errorCount +1
				util.log('Import Settings: Error in config.xml. FileType must have a name!', util.LOG_LEVEL_ERROR)
			
			type = self.getElementValue(fileType, 'type')			
			if(type == ''):
				errorCount = errorCount +1
				util.log('Import Settings: Error in config.xml. FileType must have a type!', util.LOG_LEVEL_ERROR)			
			elif(type not in ('image', 'video')):
				errorCount = errorCount +1
				util.log('Import Settings: Error in config.xml. Allowed values for FileType/@type: image, video!', util.LOG_LEVEL_ERROR)
				
			parent = self.getElementValue(fileType, 'parent')
			if(parent == ''):
				errorCount = errorCount +1
				util.log('Import Settings: Error in config.xml. FileType must have a parent!', util.LOG_LEVEL_ERROR)
			elif(parent not in ('game', 'publisher', 'developer', 'console', 'romcollection')):
				errorCount = errorCount +1
				util.log('Import Settings: Error in config.xml. Allowed values for FileType/@parent: game, publisher, developer, console, romcollection!', util.LOG_LEVEL_ERROR)
				
			
		#RomCollection
		romCollections = xmlDoc.getElementsByTagName('RomCollection')
		if(len(romCollections) == 0):
			errorCount = errorCount +1
			util.log('Import Settings: Error in config.xml. You must have at least 1 RomCollection entry!', util.LOG_LEVEL_ERROR)
			
		for romCollection in romCollections:			
			
			romCollName = self.getElementValue(romCollection, 'name')
			if(romCollName == ''):
				errorCount = errorCount +1
				util.log('Import Settings: Error in config.xml. RomCollection must have a name!', util.LOG_LEVEL_ERROR)
				
			consoleName = self.getElementValue(romCollection, 'consoleName')
			if(consoleName == ''):
				errorCount = errorCount +1
				util.log('Import Settings: Error in config.xml. RomCollection %s must have a consoleName!' %romCollName, util.LOG_LEVEL_ERROR)
			else:
				#check if consoleName is configured in Consoles
				elementFound = self.checkReferencedElement(tree, 'Consoles/Console/name', consoleName)				
				if(elementFound == False):
					errorCount = errorCount +1
					util.log('Import Settings: Error in config.xml. Console %s in Rom Collection %s does not exist in Consoles!' %(consoleName, romCollName), util.LOG_LEVEL_ERROR)
			
			emuCmd = self.getElementValue(romCollection, 'emulatorCmd')
			if(emuCmd == ''):
				errorCount = errorCount +1
				util.log('Import Settings: Error in config.xml. RomCollection %s must have an emulatorCmd!' %romCollName, util.LOG_LEVEL_ERROR)			
				
			romPaths = self.getElementValues(romCollection, 'romPath')
			if(len(romPaths) == 0):
				errorCount = errorCount +1
				util.log('Import Settings: Error in config.xml. RomCollection %s must have a romPath!' %romCollName, util.LOG_LEVEL_ERROR)
				
			for romPath in romPaths:
				dirname = os.path.dirname(romPath)
				if(not os.path.isdir(dirname)):
					errorCount = errorCount +1
					util.log('Import Settings: Error in config.xml. Configured romPath %s in RomCollection %s does not exist!' %(dirname, romCollName), util.LOG_LEVEL_ERROR)
			
			descFilePaths = self.getElementValues(romCollection, 'descFilePath')
			"""
			if(len(descFilePaths) == 0):
				errorCount = errorCount +1
				util.log('Import Settings: Error in config.xml. RomCollection %s must have a descFilePath!' %romCollName, util.LOG_LEVEL_ERROR)
			"""
			if(len(descFilePaths) > 0):
				descParserFile = self.getElementValue(romCollection, 'descriptionParserFile')
				if(descParserFile == ''):
					errorCount = errorCount +1
					util.log('Import Settings: Error in config.xml. RomCollection %s must have a descParserFile (if you have configured a descFilePath)!' %romCollName, util.LOG_LEVEL_ERROR)
				elif(not os.path.isfile(descParserFile)):
					errorCount = errorCount +1
					util.log('Import Settings: Error in config.xml. descParserFile %s in RomCollection %s does not exist!' %(descParserFile, romCollName), util.LOG_LEVEL_ERROR)
			
			for descFilePath in descFilePaths:							
				dirname = os.path.dirname(descFilePath)
				phIndex = dirname.find('%GAME%')
				if(phIndex >= 0):
					dirname = dirname[0:phIndex]				
				if(not os.path.isdir(dirname)):
					errorCount = errorCount +1
					util.log('Import Settings: Error in config.xml. Configured descFilePath %s in RomCollection %s does not exist!' %(dirname, romCollName), util.LOG_LEVEL_ERROR)
			
			mediaPaths = romCollection.getElementsByTagName('mediaPath')
			for mediaPath in mediaPaths:				
				type = self.getAttribute(mediaPath, 'type')
				if(type == ''):
					errorCount = errorCount +1
					util.log('Import Settings: Error in config.xml. MediaPath must have a type!', util.LOG_LEVEL_ERROR)
				else:
					#check if type is configured
					elementFound = self.checkReferencedElement(tree, 'FileTypes/FileType/name', type)
					if(elementFound == False):
						errorCount = errorCount +1
						util.log('Import Settings: Error in config.xml. mediaPath type %s in Rom Collection %s does not exist in FileTypes!' %(type, romCollName), util.LOG_LEVEL_ERROR)
			

			errorCount = self.checkFileTypeForElements('fileTypeForGameList', romCollection, errorCount, tree)
			errorCount = self.checkFileTypeForElements('fileTypeForMainViewGameInfo', romCollection, errorCount, tree)
			errorCount = self.checkFileTypeForElements('fileTypeForGameInfoViewBackground', romCollection, errorCount, tree)
			errorCount = self.checkFileTypeForElements('fileTypeForGameInfoViewGamelist', romCollection, errorCount, tree)
			errorCount = self.checkFileTypeForElements('fileTypeForGameInfoView1', romCollection, errorCount, tree)
			errorCount = self.checkFileTypeForElements('fileTypeForGameInfoView2', romCollection, errorCount, tree)
			errorCount = self.checkFileTypeForElements('fileTypeForGameInfoView3', romCollection, errorCount, tree)
			errorCount = self.checkFileTypeForElements('fileTypeForGameInfoView4', romCollection, errorCount, tree)
			errorCount = self.checkFileTypeForElements('fileTypeForGameInfoViewVideoWindow', romCollection, errorCount, tree)
		
		
		
		if(errorCount != 0):
			return False, errorCount
		else:
			return True, errorCount
	

	def checkReferencedElement(self, tree, xpath, expectedValue):
		elements = tree.findall(xpath)
		elementFound = False
		for element in elements:
			if(element.text == expectedValue):
				elementFound = True
				break				
		
		return elementFound		
		
			
	def checkFileTypeForElements(self, tagName, romCollection, errorCount, tree):
		elements = romCollection.getElementsByTagName(tagName)
		for element in elements:				
			firstChild = element.firstChild
			if(firstChild == None or firstChild.nodeValue == ''):																
				errorCount = errorCount +1
				util.log('Import Settings: Error in config.xml. FileTypeFor... element must have a value!', util.LOG_LEVEL_ERROR)							
			else:
				#check if type is configured
				elementFound = self.checkReferencedElement(tree, 'FileTypes/FileType/name', firstChild.nodeValue)
				if(elementFound == False):
					romCollName = self.getElementValue(romCollection, 'name')					
					errorCount = errorCount +1
					util.log('Import Settings: Error in config.xml. FileTypeFor... value %s in Rom Collection %s does not exist in FileTypes!' %(firstChild.nodeValue, romCollName), util.LOG_LEVEL_ERROR)
				
		return errorCount
	