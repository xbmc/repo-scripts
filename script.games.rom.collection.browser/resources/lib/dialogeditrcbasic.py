import xbmc, xbmcgui

import os

import util, config
from util import *
from configxmlwriter import *

ACTION_EXIT_SCRIPT = (10,)
ACTION_CANCEL_DIALOG = ACTION_EXIT_SCRIPT + (9,)

CONTROL_BUTTON_EXIT = 5101
CONTROL_BUTTON_SAVE = 6000
CONTROL_BUTTON_CANCEL = 6010

CONTROL_BUTTON_EMUCMD = 5220
CONTROL_BUTTON_PARAMS = 5230
CONTROL_BUTTON_ROMPATH = 5240
CONTROL_BUTTON_FILEMASK = 5250
CONTROL_BUTTON_MEDIAPATH = 5270
CONTROL_BUTTON_MEDIAFILEMASK = 5280

CONTROL_BUTTON_IGNOREONSCAN = 5330

CONTROL_LIST_ROMCOLLECTIONS = 5210
CONTROL_BUTTON_RC_DOWN = 5211
CONTROL_BUTTON_RC_UP = 5212

CONTROL_BUTTON_MEDIA_DOWN = 5261
CONTROL_BUTTON_MEDIA_UP = 5262

CONTROL_LIST_MEDIATYPES = 5260
CONTROL_LIST_SCRAPER1 = 5290
CONTROL_LIST_SCRAPER2 = 5300
CONTROL_LIST_SCRAPER3 = 5310
CONTROL_LIST_IMAGEPLACING = 5320


class EditRCBasicDialog(xbmcgui.WindowXMLDialog):
		
	selectedControlId = 0
	selectedRomCollection = None
	romCollections = None
	
	def __init__(self, *args, **kwargs):
		Logutil.log('init Edit RC Basic', util.LOG_LEVEL_INFO)
		
		self.gui = kwargs[ "gui" ]
		self.romCollections = self.gui.config.romCollections
		
		self.doModal()
	
	
	def onInit(self):
		Logutil.log('onInit Edit RC Basic', util.LOG_LEVEL_INFO)
		
		#Rom Collections
		Logutil.log('build rom collection list', util.LOG_LEVEL_INFO)
		romCollectionList = []
		for rcId in self.romCollections.keys():
			romCollection = self.romCollections[rcId]
			romCollectionList.append(romCollection.name)
		self.addItemsToList(CONTROL_LIST_ROMCOLLECTIONS, romCollectionList)
		
		Logutil.log('build scraper list', util.LOG_LEVEL_INFO)
		self.availableScrapers = self.getAvailableScrapers()
		self.addItemsToList(CONTROL_LIST_SCRAPER1, self.availableScrapers)
		self.addItemsToList(CONTROL_LIST_SCRAPER2, self.availableScrapers)
		self.addItemsToList(CONTROL_LIST_SCRAPER3, self.availableScrapers)

		Logutil.log('build imagePlacing list', util.LOG_LEVEL_INFO)		
		self.imagePlacingList = []
		imagePlacingRows = self.gui.config.tree.findall('ImagePlacing/fileTypeFor')
		for imagePlacing in imagePlacingRows:
			Logutil.log('add image placing: ' +str(imagePlacing.attrib.get('name')), util.LOG_LEVEL_INFO)
			self.imagePlacingList.append(imagePlacing.attrib.get('name'))
		self.addItemsToList(CONTROL_LIST_IMAGEPLACING, self.imagePlacingList)
		
		self.updateControls()
		
		
	def onAction(self, action):		
		if (action.getId() in ACTION_CANCEL_DIALOG):
			self.close()
		
	
	def onClick(self, controlID):
		
		Logutil.log('onClick', util.LOG_LEVEL_INFO)
		
		if (controlID == CONTROL_BUTTON_EXIT): # Close window button
			Logutil.log('close', util.LOG_LEVEL_INFO)
			self.close()
		#OK
		elif (controlID == CONTROL_BUTTON_SAVE):
			Logutil.log('save', util.LOG_LEVEL_INFO)
			#store selectedRomCollection
			if(self.selectedRomCollection != None):
				
				self.updateSelectedRomCollection()
				
				self.romCollections[self.selectedRomCollection.id] = self.selectedRomCollection
						
			configWriter = ConfigXmlWriter(False)
			success, message = configWriter.writeRomCollections(self.romCollections, True)
			
			self.close()
		#Cancel
		elif (controlID == CONTROL_BUTTON_CANCEL):
			self.close()
		#Rom Collection list
		elif(self.selectedControlId in (CONTROL_BUTTON_RC_DOWN, CONTROL_BUTTON_RC_UP)):						
						
			if(self.selectedRomCollection != None):
				#save current values to selected Rom Collection
				self.updateSelectedRomCollection()
				
				#store previous selectedRomCollections state
				self.romCollections[self.selectedRomCollection.id] = self.selectedRomCollection
			
			#HACK: add a little wait time as XBMC needs some ms to execute the MoveUp/MoveDown actions from the skin
			xbmc.sleep(util.WAITTIME_UPDATECONTROLS)
			self.updateControls()
		
		#Media Path
		elif(self.selectedControlId in (CONTROL_BUTTON_MEDIA_DOWN, CONTROL_BUTTON_MEDIA_UP)):
			#HACK: add a little wait time as XBMC needs some ms to execute the MoveUp/MoveDown actions from the skin
			xbmc.sleep(util.WAITTIME_UPDATECONTROLS)
			self.updateMediaPath()
			
		elif (controlID == CONTROL_BUTTON_EMUCMD):
			
			dialog = xbmcgui.Dialog()
			
			emulatorPath = dialog.browse(1, '%s Emulator' %self.selectedRomCollection.name, 'files')
			if(emulatorPath == ''):
				return
						
			self.selectedRomCollection.emulatorCmd = emulatorPath
			control = self.getControlById(CONTROL_BUTTON_EMUCMD)
			control.setLabel(emulatorPath)
			
		elif (controlID == CONTROL_BUTTON_PARAMS):
			
			control = self.getControlById(CONTROL_BUTTON_PARAMS)
			emulatorParams = control.getLabel()
			
			keyboard = xbmc.Keyboard()
			keyboard.setHeading('Enter Emulator Params')			
			keyboard.setDefault(emulatorParams)
			keyboard.doModal()
			if (keyboard.isConfirmed()):
				emulatorParams = keyboard.getText()
						
			self.selectedRomCollection.emulatorParams = emulatorParams
			control.setLabel(emulatorParams)
			
		elif (controlID == CONTROL_BUTTON_ROMPATH):
			
			dialog = xbmcgui.Dialog()
			
			romPath = dialog.browse(0, '%s Roms' %self.selectedRomCollection.name, 'files')
			if(romPath == ''):
				return
						
			control = self.getControlById(CONTROL_BUTTON_FILEMASK)
			fileMaskInput = control.getLabel()
			fileMasks = fileMaskInput.split(',')
			romPaths = []
			for fileMask in fileMasks:
				romPathComplete = os.path.join(romPath, fileMask.strip())					
				romPaths.append(romPathComplete)
						
			self.selectedRomCollection.romPaths = romPaths
			control = self.getControlById(CONTROL_BUTTON_ROMPATH)
			control.setLabel(romPath)
			
		elif (controlID == CONTROL_BUTTON_FILEMASK):
			
			control = self.getControlById(CONTROL_BUTTON_FILEMASK)
			romFileMask = control.getLabel()
			
			keyboard = xbmc.Keyboard()
			keyboard.setHeading('Enter Rom File Mask')
			keyboard.setDefault(romFileMask)			
			keyboard.doModal()
			if (keyboard.isConfirmed()):
				romFileMask = keyboard.getText()
									
			#HACK: this only handles 1 base rom path
			romPath = self.selectedRomCollection.romPaths[0]
			pathParts = os.path.split(romPath)
			romPath = pathParts[0]
			fileMasks = romFileMask.split(',')
			romPaths = []
			for fileMask in fileMasks:				
				romPathComplete = os.path.join(romPath, fileMask.strip())					
				romPaths.append(romPathComplete)
			
			self.selectedRomCollection.romPaths = romPaths
			control.setLabel(romFileMask)
			
		elif (controlID == CONTROL_BUTTON_MEDIAPATH):
			
			dialog = xbmcgui.Dialog()
			
			#get selected medias type			
			control = self.getControlById(CONTROL_LIST_MEDIATYPES)
			selectedMediaType = str(control.getSelectedItem().getLabel())
			
			#get current media path
			currentMediaPath = None
			currentMediaPathIndex = -1;
			for i in range(0, len(self.selectedRomCollection.mediaPaths)):
				mediaPath = self.selectedRomCollection.mediaPaths[i]
				if(mediaPath.fileType.name == selectedMediaType):
					currentMediaPath = mediaPath
					currentMediaPathIndex = i
					break
			
			#get new value
			mediaPathInput = dialog.browse(0, '%s Path' %currentMediaPath.fileType.name, 'files')
			if(mediaPathInput == ''):
				return
			
			control = self.getControlById(CONTROL_BUTTON_MEDIAPATH)
			control.setLabel(mediaPathInput)
			
			#write new path to selected Rom Collection
			#HACK: only 1 media per type is supported with this implementation
			control = self.getControlById(CONTROL_BUTTON_MEDIAFILEMASK)
			mediaFileMask = control.getLabel()
			mediaPathComplete = os.path.join(mediaPathInput, mediaFileMask.strip())
			currentMediaPath.path = mediaPathComplete
			self.selectedRomCollection.mediaPaths[currentMediaPathIndex] = currentMediaPath
		
		elif (controlID == CONTROL_BUTTON_MEDIAFILEMASK):
			
			dialog = xbmcgui.Dialog()
			
			#get selected medias type			
			control = self.getControlById(CONTROL_LIST_MEDIATYPES)
			selectedMediaType = str(control.getSelectedItem().getLabel())
			
			#get current media path
			currentMediaPath = None
			currentMediaPathIndex = -1;
			for i in range(0, len(self.selectedRomCollection.mediaPaths)):
				mediaPath = self.selectedRomCollection.mediaPaths[i]
				if(mediaPath.fileType.name == selectedMediaType):
					currentMediaPath = mediaPath
					currentMediaPathIndex = i
					break
			
			control = self.getControlById(CONTROL_BUTTON_MEDIAFILEMASK)
			mediaFileMask = control.getLabel()
			
			keyboard = xbmc.Keyboard()
			keyboard.setHeading('Enter Media File Mask')
			keyboard.setDefault(mediaFileMask)			
			keyboard.doModal()
			if (keyboard.isConfirmed()):
				mediaFileMask = keyboard.getText()
							
			control.setLabel(mediaFileMask)
			
			#write new path to selected Rom Collection
			#HACK: only 1 media per type is supported with this implementation
			control = self.getControlById(CONTROL_BUTTON_MEDIAPATH)
			mediaPath = control.getLabel()
			mediaPathComplete = os.path.join(mediaPath, mediaFileMask.strip())
			currentMediaPath.path = mediaPathComplete
			self.selectedRomCollection.mediaPaths[currentMediaPathIndex] = currentMediaPath
						
	
	def onFocus(self, controlId):
		self.selectedControlId = controlId
	
	
	def updateControls(self):
		
		Logutil.log('updateControls', util.LOG_LEVEL_INFO)
		
		control = self.getControlById(CONTROL_LIST_ROMCOLLECTIONS)
		selectedRomCollectionName = str(control.getSelectedItem().getLabel())
				
		Logutil.log('selected rom collection: ' +str(selectedRomCollectionName), util.LOG_LEVEL_INFO)
				
		self.selectedRomCollection = None
		
		for rcId in self.romCollections.keys():
			romCollection = self.romCollections[rcId]
			if romCollection.name == selectedRomCollectionName:
				self.selectedRomCollection = romCollection
				break
			
		if(self.selectedRomCollection == None):
			return
		
		control = self.getControlById(CONTROL_BUTTON_EMUCMD)
		control.setLabel(self.selectedRomCollection.emulatorCmd)
		
		control = self.getControlById(CONTROL_BUTTON_PARAMS)
		control.setLabel(self.selectedRomCollection.emulatorParams)
				
		#HACK: split romPath and fileMask
		firstRomPath = ''
		fileMask = ''
		for romPath in self.selectedRomCollection.romPaths:
			
			pathParts = os.path.split(romPath)			 
			if(firstRomPath == ''):				
				firstRomPath = pathParts[0]
				fileMask = pathParts[1]
			elif(firstRomPath == pathParts[0]):
				fileMask = fileMask +',' +pathParts[1]
								
		control = self.getControlById(CONTROL_BUTTON_ROMPATH)
		control.setLabel(firstRomPath)
		
		control = self.getControlById(CONTROL_BUTTON_FILEMASK)
		control.setLabel(fileMask)
		
		
		#Media Types
		mediaTypeList = []
		firstMediaPath = ''
		firstMediaFileMask = ''
		for mediaPath in self.selectedRomCollection.mediaPaths:
			mediaTypeList.append(mediaPath.fileType.name)
			if(firstMediaPath == ''):
				pathParts = os.path.split(mediaPath.path)
				firstMediaPath = pathParts[0]
				firstMediaFileMask = pathParts[1]
				
		self.addItemsToList(CONTROL_LIST_MEDIATYPES, mediaTypeList)
		
		control = self.getControlById(CONTROL_BUTTON_MEDIAPATH)
		control.setLabel(firstMediaPath)
		
		control = self.getControlById(CONTROL_BUTTON_MEDIAFILEMASK)
		control.setLabel(firstMediaFileMask)
						
		self.selectScrapersInList(self.selectedRomCollection.scraperSites, self.availableScrapers)
		
		self.selectItemInList(self.imagePlacingList, self.selectedRomCollection.imagePlacing.name, CONTROL_LIST_IMAGEPLACING)
		
		control = self.getControlById(CONTROL_BUTTON_IGNOREONSCAN)		
		control.setSelected(self.selectedRomCollection.ignoreOnScan)
	
		print 'ignoreOnScan: ' +str(self.selectedRomCollection.ignoreOnScan)
	
	
	def updateMediaPath(self):
		
		control = self.getControlById(CONTROL_LIST_MEDIATYPES)
		selectedMediaType = str(control.getSelectedItem().getLabel())
		
		for mediaPath in self.selectedRomCollection.mediaPaths:
			if mediaPath.fileType.name == selectedMediaType:
				
				pathParts = os.path.split(mediaPath.path)
				control = self.getControlById(CONTROL_BUTTON_MEDIAPATH)
				control.setLabel(pathParts[0])				
				control = self.getControlById(CONTROL_BUTTON_MEDIAFILEMASK)
				control.setLabel(pathParts[1])
				
				break
	
	
	def updateSelectedRomCollection(self):
		
		Logutil.log('updateSelectedRomCollection', util.LOG_LEVEL_INFO)
		
		#ignore on scan
		control = self.getControlById(CONTROL_BUTTON_IGNOREONSCAN)
		self.selectedRomCollection.ignoreOnScan = bool(control.isSelected())
		
		#Scraper
		try:
			platformId = config.consoleDict[self.selectedRomCollection.name]
		except:
			platformId = '0'
		
		sites = []
		sites = self.addScraperToRomCollection(CONTROL_LIST_SCRAPER1, platformId, sites)
		sites = self.addScraperToRomCollection(CONTROL_LIST_SCRAPER2, platformId, sites)
		sites = self.addScraperToRomCollection(CONTROL_LIST_SCRAPER3, platformId, sites)
			
		self.selectedRomCollection.scraperSites = sites
		
		
		#Image Placing
		control = self.getControlById(CONTROL_LIST_IMAGEPLACING)
		imgPlacingItem = control.getSelectedItem()
		imgPlacingName = imgPlacingItem.getLabel()
		
		imgPlacing, errorMsg = self.gui.config.readImagePlacing(imgPlacingName, self.gui.config.tree)
		self.selectedRomCollection.imagePlacing = imgPlacing

	
	def getControlById(self, controlId):
		try:
			control = self.getControl(controlId)
		except:
			return None
		
		return control
	
	
	def addItemsToList(self, controlId, options):
		Logutil.log('addItemsToList', util.LOG_LEVEL_INFO)
		
		control = self.getControlById(controlId)
		control.setVisible(1)
		control.reset()
				
		items = []
		for option in options:
			items.append(xbmcgui.ListItem(option, '', '', ''))
							
		control.addItems(items)
		
		
	def getAvailableScrapers(self):
		Logutil.log('get available scrapers', util.LOG_LEVEL_INFO)
		
		#Scrapers
		sitesInList = ['None']
		#get all scrapers
		scrapers = self.gui.config.tree.findall('Scrapers/Site')
		for scraper in scrapers:
			name = scraper.attrib.get('name')
			if(name != None):
				Logutil.log('add scraper name: ' +str(name), util.LOG_LEVEL_INFO)
				sitesInList.append(name)
				
		return sitesInList
	
	
	def selectScrapersInList(self, sitesInRomCollection, sitesInList):
		
		Logutil.log('selectScrapersInList', util.LOG_LEVEL_INFO)
		
		if(len(sitesInRomCollection) >= 1):
			self.selectItemInList(sitesInList, sitesInRomCollection[0].name, CONTROL_LIST_SCRAPER1)			
		else:
			self.selectItemInList(sitesInList, 'None', CONTROL_LIST_SCRAPER1)
		if(len(sitesInRomCollection) >= 2):
			self.selectItemInList(sitesInList, sitesInRomCollection[1].name, CONTROL_LIST_SCRAPER2)
		else:
			self.selectItemInList(sitesInList, 'None', CONTROL_LIST_SCRAPER2)
		if(len(sitesInRomCollection) >= 3):
			self.selectItemInList(sitesInList, sitesInRomCollection[2].name, CONTROL_LIST_SCRAPER3)
		else:
			self.selectItemInList(sitesInList, 'None', CONTROL_LIST_SCRAPER3)
				
	
	def selectItemInList(self, options, itemName, controlId):				
		
		Logutil.log('selectItemInList', util.LOG_LEVEL_INFO)		
		
		for i in range(0, len(options)):			
			option = options[i]
			if(itemName == option):
				control = self.getControlById(controlId)
				control.selectItem(i)
				break
			
			
	def addScraperToRomCollection(self, controlId, platformId, sites):				

		Logutil.log('addScraperToRomCollection', util.LOG_LEVEL_INFO)
		
		control = self.getControlById(controlId)
		scraperItem = control.getSelectedItem()
		scraper = scraperItem.getLabel()
		
		if(scraper != 'mobygames.com'):
			platformId = '0'
		
		site, errorMsg = self.gui.config.readScraper(scraper, platformId, '', '', self.gui.config.tree)
		if(site != None):
			sites.append(site)
			
		return sites