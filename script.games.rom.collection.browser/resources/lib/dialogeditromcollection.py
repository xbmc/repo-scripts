import xbmc, xbmcgui

import os

import util, helper, config, dialogbase
from util import *
from configxmlwriter import *
from emulatorautoconfig.autoconfig import EmulatorAutoconfig

ACTION_CANCEL_DIALOG = (9,10,51,92,110)

CONTROL_BUTTON_EXIT = 5101
CONTROL_BUTTON_SAVE = 6000
CONTROL_BUTTON_CANCEL = 6010

CONTROL_LIST_ROMCOLLECTIONS = 5210
CONTROL_BUTTON_RC_DOWN = 5211
CONTROL_BUTTON_RC_UP = 5212

#Import Games
CONTROL_BUTTON_ROMPATH = 5240
CONTROL_BUTTON_FILEMASK = 5250
CONTROL_BUTTON_IGNOREONSCAN = 5330
CONTROL_BUTTON_ALLOWUPDATE = 5400
CONTROL_BUTTON_MAXFOLDERDEPTH = 5410
CONTROL_BUTTON_DISKINDICATOR = 5420
CONTROL_BUTTON_USEFOLDERASGAMENAME = 5430

#Import Game data
CONTROL_LIST_SCRAPER1 = 5290
CONTROL_LIST_SCRAPER2 = 5300
CONTROL_LIST_SCRAPER3 = 5310
CONTROL_LIST_MEDIATYPES = 5260
CONTROL_BUTTON_MEDIA_DOWN = 5261
CONTROL_BUTTON_MEDIA_UP = 5262
CONTROL_BUTTON_MEDIAPATH = 5270
CONTROL_BUTTON_MEDIAFILEMASK = 5280
CONTROL_BUTTON_REMOVEMEDIAPATH = 5490
CONTROL_BUTTON_ADDMEDIAPATH = 5500


#Browse Games
CONTROL_LIST_IMAGEPLACING_MAIN = 5320
CONTROL_LIST_IMAGEPLACING_INFO = 5340
CONTROL_BUTTON_AUTOPLAYVIDEO_MAIN = 5350
CONTROL_BUTTON_AUTOPLAYVIDEO_INFO = 5360


#Launch Games
CONTROL_BUTTON_USERETROPLAYER = 5540
CONTROL_BUTTON_GAMECLIENT = 5550

CONTROL_BUTTON_EMUCMD = 5220
CONTROL_BUTTON_PARAMS = 5230
CONTROL_BUTTON_USEEMUSOLO = 5440
CONTROL_BUTTON_USEPOPEN = 5530
CONTROL_BUTTON_DONTEXTRACTZIP = 5450
CONTROL_BUTTON_SAVESTATEPATH = 5460
CONTROL_BUTTON_SAVESTATEMASK = 5470
CONTROL_BUTTON_SAVESTATEPARAMS = 5480
CONTROL_BUTTON_PRECMD = 5510
CONTROL_BUTTON_POSTCMD = 5520
CONTROL_BUTTON_MAKELOCALCOPY = 5560


class EditRomCollectionDialog(dialogbase.DialogBaseEdit):
		
	selectedControlId = 0
	selectedRomCollection = None	
	romCollections = None
	scraperSites = None
	
	def __init__(self, *args, **kwargs):
		Logutil.log('init Edit Rom Collection', util.LOG_LEVEL_INFO)
		
		self.gui = kwargs[ "gui" ]
		self.romCollections = self.gui.config.romCollections
		self.scraperSites = self.gui.config.scraperSites
		
		self.doModal()
	
	
	def onInit(self):
		Logutil.log('onInit Edit Rom Collection', util.LOG_LEVEL_INFO)
		
		#Rom Collections
		Logutil.log('build rom collection list', util.LOG_LEVEL_INFO)
		romCollectionList = []
		for rcId in self.romCollections.keys():
			romCollection = self.romCollections[rcId]
			romCollectionList.append(romCollection.name)
		self.addItemsToList(CONTROL_LIST_ROMCOLLECTIONS, romCollectionList)
		
		Logutil.log('build scraper lists', util.LOG_LEVEL_INFO)
		self.availableScrapers = self.getAvailableScrapers(False)
		self.addItemsToList(CONTROL_LIST_SCRAPER1, self.availableScrapers)
		self.addItemsToList(CONTROL_LIST_SCRAPER2, self.availableScrapers)
		self.addItemsToList(CONTROL_LIST_SCRAPER3, self.availableScrapers)

		Logutil.log('build imagePlacing list', util.LOG_LEVEL_INFO)		
		self.imagePlacingList = []
		imagePlacingRows = self.gui.config.tree.findall('ImagePlacing/fileTypeFor')
		for imagePlacing in imagePlacingRows:
			Logutil.log('add image placing: ' +str(imagePlacing.attrib.get('name')), util.LOG_LEVEL_INFO)
			option = imagePlacing.attrib.get('name')
			#HACK: remove all video options from config
			if(option.upper().find('VIDEO') >= 0):
				continue
			try:
				option = config.imagePlacingDict[option]
			except:
				pass
			self.imagePlacingList.append(option)
		self.addItemsToList(CONTROL_LIST_IMAGEPLACING_MAIN, self.imagePlacingList)
		self.addItemsToList(CONTROL_LIST_IMAGEPLACING_INFO, self.imagePlacingList)
		
		if(not helper.isRetroPlayerSupported()):
			control = self.getControlById(CONTROL_BUTTON_USERETROPLAYER)
			if(control):
				control.setEnabled(False)
				control.setVisible(False)
			control = self.getControlById(CONTROL_BUTTON_GAMECLIENT)
			if(control):
				control.setEnabled(False)
				control.setVisible(False)
		elif(not helper.retroPlayerSupportsPythonIntegration()):
			control = self.getControlById(CONTROL_BUTTON_GAMECLIENT)
			if(control):
				control.setEnabled(False)
				control.setVisible(False)
		
		self.updateRomCollectionControls()
		
		
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
			
			if not success:
				xbmcgui.Dialog().ok(util.localize(32021), message)
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
			self.updateRomCollectionControls()
		
		#Media Path
		elif(self.selectedControlId in (CONTROL_BUTTON_MEDIA_DOWN, CONTROL_BUTTON_MEDIA_UP)):
			#HACK: add a little wait time as XBMC needs some ms to execute the MoveUp/MoveDown actions from the skin
			xbmc.sleep(util.WAITTIME_UPDATECONTROLS)
			self.updateMediaPathControls()
			
			
		elif (controlID == CONTROL_BUTTON_GAMECLIENT):
			success, gameclient = helper.selectlibretrocore(self.selectedRomCollection.name)
			if success:
				self.selectedRomCollection.gameclient = gameclient
						
			control = self.getControlById(CONTROL_BUTTON_GAMECLIENT)
			if(gameclient == ""):			
				control.setLabel("None")
			else:
				control.setLabel(gameclient)
			
		elif (controlID == CONTROL_BUTTON_EMUCMD):
			
			#maybe there is autoconfig support
			preconfiguredEmulator = None
			emulatorPath = ''
			dialog = xbmcgui.Dialog()
			
			if (self.selectedRomCollection.name == 'Linux' or self.selectedRomCollection.name == 'Macintosh' or self.selectedRomCollection.name == 'Windows'):
				emulatorPath = self.editTextProperty(CONTROL_BUTTON_EMUCMD, util.localize(32624))
			else:
				if(xbmc.getCondVisibility('System.Platform.Android')):
					
					autoconfig = EmulatorAutoconfig(util.getEmuAutoConfigPath())
					
					Logutil.log('Running on Android. Trying to find emulator per autoconfig.', util.LOG_LEVEL_INFO)
					emulators = autoconfig.findEmulators('Android', self.selectedRomCollection.name, True)
					emulist = []
					if(emulators):
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
					emulatorPath = preconfiguredEmulator.emuCmd					
					self.selectedRomCollection.emulatorParams = preconfiguredEmulator.emuParams
					control = self.getControlById(CONTROL_BUTTON_PARAMS)
					control.setLabel(self.selectedRomCollection.emulatorParams)
				else:										
					emulatorPath = dialog.browse(1, '%s ' %self.selectedRomCollection.name +util.localize(32139), 'files')
					if(emulatorPath == ''):
						return
							
			self.selectedRomCollection.emulatorCmd = emulatorPath
			control = self.getControlById(CONTROL_BUTTON_EMUCMD)
			control.setLabel(emulatorPath)
			
		elif (controlID == CONTROL_BUTTON_PARAMS):
			emulatorParams = self.editTextProperty(CONTROL_BUTTON_PARAMS, util.localize(32625))
			self.selectedRomCollection.emulatorParams = emulatorParams
			
		elif (controlID == CONTROL_BUTTON_ROMPATH):
			self.editRomPath()
			
		elif (controlID == CONTROL_BUTTON_FILEMASK):
			self.editRomFileMask()
			
		elif (controlID == CONTROL_BUTTON_MEDIAPATH):
			self.editMediaPath()
		
		elif (controlID == CONTROL_BUTTON_MEDIAFILEMASK):
			self.editMediaFileMask()
		
		elif (controlID == CONTROL_BUTTON_ADDMEDIAPATH):
			self.addMediaPath()
			
		elif (controlID == CONTROL_BUTTON_REMOVEMEDIAPATH):
			self.removeMediaPath()
			
		elif (controlID == CONTROL_BUTTON_MAXFOLDERDEPTH):
			maxFolderDepth = self.editTextProperty(CONTROL_BUTTON_MAXFOLDERDEPTH, util.localize(32610))
			self.selectedRomCollection.maxFolderDepth = maxFolderDepth
			
		elif (controlID == CONTROL_BUTTON_DISKINDICATOR):
			diskIndicator = self.editTextProperty(CONTROL_BUTTON_DISKINDICATOR, util.localize(32611))
			self.selectedRomCollection.diskPrefix = diskIndicator
						
		elif (controlID == CONTROL_BUTTON_SAVESTATEPATH):
			saveStatePathComplete = self.editPathWithFileMask(CONTROL_BUTTON_SAVESTATEPATH, '%s ' %self.selectedRomCollection.name +util.localize(32629), CONTROL_BUTTON_SAVESTATEMASK)
			if(saveStatePathComplete != ''):
				self.selectedRomCollection.saveStatePath = saveStatePathComplete
				
		elif (controlID == CONTROL_BUTTON_SAVESTATEMASK):
			self.selectedRomCollection.saveStatePath = self.editFilemask(CONTROL_BUTTON_SAVESTATEMASK, util.localize(32630), self.selectedRomCollection.saveStatePath)
			
		elif (controlID == CONTROL_BUTTON_SAVESTATEPARAMS):
			saveStateParams = self.editTextProperty(CONTROL_BUTTON_SAVESTATEPARAMS, util.localize(32631))
			self.selectedRomCollection.saveStateParams = saveStateParams
		
		elif (controlID == CONTROL_BUTTON_PRECMD):
			preCmd = self.editTextProperty(CONTROL_BUTTON_PRECMD, util.localize(32632))
			self.selectedRomCollection.preCmd = preCmd
			Logutil.log('OnClick: precmd = ' +self.selectedRomCollection.preCmd, util.LOG_LEVEL_INFO)
			
			
		elif (controlID == CONTROL_BUTTON_POSTCMD):
			postCmd = self.editTextProperty(CONTROL_BUTTON_POSTCMD, util.localize(32633))
			self.selectedRomCollection.postCmd = postCmd
				
	
	def onFocus(self, controlId):
		self.selectedControlId = controlId
	
	
	def updateRomCollectionControls(self):
		
		Logutil.log('updateRomCollectionControls', util.LOG_LEVEL_INFO)
		
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
				
		#Import Games
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
		util.setLabel(firstRomPath, control)
		
		control = self.getControlById(CONTROL_BUTTON_FILEMASK)
		util.setLabel(fileMask, control)		
		
		control = self.getControlById(CONTROL_BUTTON_IGNOREONSCAN)		
		control.setSelected(self.selectedRomCollection.ignoreOnScan)
		
		control = self.getControlById(CONTROL_BUTTON_ALLOWUPDATE)
		control.setSelected(self.selectedRomCollection.allowUpdate)
		
		control = self.getControlById(CONTROL_BUTTON_DISKINDICATOR)
		util.setLabel(self.selectedRomCollection.diskPrefix, control)
		
		control = self.getControlById(CONTROL_BUTTON_MAXFOLDERDEPTH)
		util.setLabel(self.selectedRomCollection.maxFolderDepth, control)
		
		control = self.getControlById(CONTROL_BUTTON_USEFOLDERASGAMENAME)
		control.setSelected(self.selectedRomCollection.useFoldernameAsGamename)
		
		#Import Game Data
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
		util.setLabel(firstMediaPath, control)
		
		control = self.getControlById(CONTROL_BUTTON_MEDIAFILEMASK)
		util.setLabel(firstMediaFileMask, control)		
						
		self.selectScrapersInList(self.selectedRomCollection.scraperSites, self.availableScrapers)
		
		#Browse Games
		optionMain = self.selectedRomCollection.imagePlacingMain.name
		try:
			optionMain = config.imagePlacingDict[optionMain]
		except:
			pass
		self.selectItemInList(optionMain, CONTROL_LIST_IMAGEPLACING_MAIN)
		
		optionInfo = self.selectedRomCollection.imagePlacingInfo.name
		try:
			optionInfo = config.imagePlacingDict[optionInfo]
		except:			
			pass		
		self.selectItemInList(optionInfo, CONTROL_LIST_IMAGEPLACING_INFO)
		
		control = self.getControlById(CONTROL_BUTTON_AUTOPLAYVIDEO_MAIN)
		if(control != None):
			control.setSelected(self.selectedRomCollection.autoplayVideoMain)
		
		control = self.getControlById(CONTROL_BUTTON_AUTOPLAYVIDEO_INFO)
		if(control != None):
			control.setSelected(self.selectedRomCollection.autoplayVideoInfo)
		
		#Launch Games
		control = self.getControlById(CONTROL_BUTTON_USERETROPLAYER)
		if(control):
			control.setSelected(self.selectedRomCollection.useBuiltinEmulator)
		
		control = self.getControlById(CONTROL_BUTTON_GAMECLIENT)
		if(control):
			util.setLabel(self.selectedRomCollection.gameclient, control)		
			
		control = self.getControlById(CONTROL_BUTTON_EMUCMD)
		util.setLabel(self.selectedRomCollection.emulatorCmd, control)		
		
		control = self.getControlById(CONTROL_BUTTON_PARAMS)
		util.setLabel(self.selectedRomCollection.emulatorParams, control)		
		
		control = self.getControlById(CONTROL_BUTTON_USEEMUSOLO)
		control.setSelected(self.selectedRomCollection.useEmuSolo)
		
		control = self.getControlById(CONTROL_BUTTON_USEPOPEN)
		control.setSelected(self.selectedRomCollection.usePopen)
		
		pathParts = os.path.split(self.selectedRomCollection.saveStatePath)
		saveStatePath = pathParts[0]
		saveStateFileMask = pathParts[1]
		
		control = self.getControlById(CONTROL_BUTTON_SAVESTATEPATH)
		util.setLabel(saveStatePath, control)
		
		control = self.getControlById(CONTROL_BUTTON_SAVESTATEMASK)
		util.setLabel(saveStateFileMask, control)
		
		control = self.getControlById(CONTROL_BUTTON_SAVESTATEPARAMS)		
		util.setLabel(self.selectedRomCollection.saveStateParams, control)
		
		control = self.getControlById(CONTROL_BUTTON_DONTEXTRACTZIP)
		control.setSelected(self.selectedRomCollection.doNotExtractZipFiles)
		
		control = self.getControlById(CONTROL_BUTTON_MAKELOCALCOPY)
		control.setSelected(self.selectedRomCollection.makeLocalCopy)
		
		control = self.getControlById(CONTROL_BUTTON_PRECMD)
		util.setLabel(self.selectedRomCollection.preCmd, control)		
		
		control = self.getControlById(CONTROL_BUTTON_POSTCMD)
		util.setLabel(self.selectedRomCollection.postCmd, control)
	
	
	def updateMediaPathControls(self):
		
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
		
		control = self.getControlById(CONTROL_BUTTON_IGNOREONSCAN)
		self.selectedRomCollection.ignoreOnScan = bool(control.isSelected())
		control = self.getControlById(CONTROL_BUTTON_ALLOWUPDATE)
		self.selectedRomCollection.allowUpdate = bool(control.isSelected())
		control = self.getControlById(CONTROL_BUTTON_USEFOLDERASGAMENAME)
		self.selectedRomCollection.useFoldernameAsGamename = bool(control.isSelected())
		
		sites = []
		sites = self.addScraperToSiteList(CONTROL_LIST_SCRAPER1, sites, self.selectedRomCollection)
		sites = self.addScraperToSiteList(CONTROL_LIST_SCRAPER2, sites, self.selectedRomCollection)
		sites = self.addScraperToSiteList(CONTROL_LIST_SCRAPER3, sites, self.selectedRomCollection)
			
		self.selectedRomCollection.scraperSites = sites		
		
		#Image Placing Main
		control = self.getControlById(CONTROL_LIST_IMAGEPLACING_MAIN)
		imgPlacingItem = control.getSelectedItem()
		imgPlacingName = imgPlacingItem.getLabel()
		#HACK search key by value
		for item in config.imagePlacingDict.items():
			if(item[1] == imgPlacingName):
				imgPlacingName = item[0]
		imgPlacing, errorMsg = self.gui.config.readImagePlacing(imgPlacingName, self.gui.config.tree)
		self.selectedRomCollection.imagePlacingMain = imgPlacing
		
		#Image Placing Info
		control = self.getControlById(CONTROL_LIST_IMAGEPLACING_INFO)
		imgPlacingItem = control.getSelectedItem()
		imgPlacingName = imgPlacingItem.getLabel()
		#HACK search key by value
		for item in config.imagePlacingDict.items():
			if(item[1] == imgPlacingName):
				imgPlacingName = item[0]
		imgPlacing, errorMsg = self.gui.config.readImagePlacing(imgPlacingName, self.gui.config.tree)
		self.selectedRomCollection.imagePlacingInfo = imgPlacing
		
		control = self.getControlById(CONTROL_BUTTON_AUTOPLAYVIDEO_MAIN)
		if(control != None):
			self.selectedRomCollection.autoplayVideoMain = bool(control.isSelected())
		control = self.getControlById(CONTROL_BUTTON_AUTOPLAYVIDEO_INFO)
		if(control != None):
			self.selectedRomCollection.autoplayVideoInfo = bool(control.isSelected())
		
		control = self.getControlById(CONTROL_BUTTON_USERETROPLAYER)
		if(control):
			self.selectedRomCollection.useBuiltinEmulator = bool(control.isSelected())
			
		control = self.getControlById(CONTROL_BUTTON_USEEMUSOLO)
		self.selectedRomCollection.useEmuSolo = bool(control.isSelected())
		control = self.getControlById(CONTROL_BUTTON_USEPOPEN)
		self.selectedRomCollection.usePopen = bool(control.isSelected())
		control = self.getControlById(CONTROL_BUTTON_DONTEXTRACTZIP)
		self.selectedRomCollection.doNotExtractZipFiles = bool(control.isSelected())
		control = self.getControlById(CONTROL_BUTTON_MAKELOCALCOPY)
		self.selectedRomCollection.makeLocalCopy = bool(control.isSelected())
	
	
	def editRomPath(self):
		
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
		
		
	def editRomFileMask(self):
		
		control = self.getControlById(CONTROL_BUTTON_FILEMASK)
		romFileMask = control.getLabel()
		
		keyboard = xbmc.Keyboard()
		keyboard.setHeading(util.localize(32140))
		keyboard.setDefault(romFileMask)			
		keyboard.doModal()
		if (keyboard.isConfirmed()):
			romFileMask = keyboard.getText()
			if(romFileMask == ''):
				romFileMask = ' '
								
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
		
		
	def editMediaPath(self):
		
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
		
		mediaPathComplete = self.editPathWithFileMask(CONTROL_BUTTON_MEDIAPATH, '%s ' %currentMediaPath.fileType.name +util.localize(32141), CONTROL_BUTTON_MEDIAFILEMASK)
		
		if(mediaPathComplete != ''):
			currentMediaPath.path = mediaPathComplete
			self.selectedRomCollection.mediaPaths[currentMediaPathIndex] = currentMediaPath
	
	
	def editMediaFileMask(self):
		
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
			
		mediaPathComplete = self.editFilemask(CONTROL_BUTTON_MEDIAFILEMASK, util.localize(32618), currentMediaPath.path)
					
		currentMediaPath.path = mediaPathComplete
		self.selectedRomCollection.mediaPaths[currentMediaPathIndex] = currentMediaPath
		
		
	def addMediaPath(self):
		
		mediaTypes = self.gui.config.tree.findall('FileTypes/FileType')
			
		mediaTypeList = []
		
		for mediaType in mediaTypes:
			name = mediaType.attrib.get('name')
			if(name != None):
				type = mediaType.find('type')
				if(type != None and type.text == 'video'):
					name = name +' (video)'
				
				#check if media type is already in use for selected RC
				isMediaTypeInUse = False
				for mediaPath in self.selectedRomCollection.mediaPaths:
					if(mediaPath.fileType.name == name):
						isMediaTypeInUse = True
				
				if(not isMediaTypeInUse):
					mediaTypeList.append(name)
		
		mediaTypeIndex = xbmcgui.Dialog().select(util.localize(32142), mediaTypeList)
		if(mediaTypeIndex == -1):
			return
		
		mediaType = mediaTypeList[mediaTypeIndex]
		mediaType = mediaType.replace(' (video)', '')
				
		mediaPathComplete = self.editPathWithFileMask(CONTROL_BUTTON_MEDIAPATH, '%s ' %mediaType +util.localize(32141), CONTROL_BUTTON_MEDIAFILEMASK)
		#TODO: use default value in editFilemask
		control = self.getControlById(CONTROL_BUTTON_MEDIAFILEMASK)
		control.setLabel('%GAME%.*')
		mediaPathComplete = self.editFilemask(CONTROL_BUTTON_MEDIAFILEMASK, util.localize(32618), mediaPathComplete)
		
		mediaPath = MediaPath()
		fileType = FileType()
		fileType.name = mediaType
		mediaPath.fileType = fileType
		mediaPath.path = mediaPathComplete
		self.selectedRomCollection.mediaPaths.append(mediaPath)			
		
		control = self.getControlById(CONTROL_LIST_MEDIATYPES)
		item = xbmcgui.ListItem(mediaType, '', '', '')
		control.addItem(item)
		
		self.selectItemInList(mediaType, CONTROL_LIST_MEDIATYPES)
		
		xbmc.sleep(util.WAITTIME_UPDATECONTROLS)
		self.updateMediaPathControls()
		
		
	def removeMediaPath(self):
		
		mediaTypeList = []
		for mediaPath in self.selectedRomCollection.mediaPaths:
			mediaTypeList.append(mediaPath.fileType.name)
		
		mediaTypeIndex = xbmcgui.Dialog().select(util.localize(32143), mediaTypeList)
		if(mediaTypeIndex == -1):
			return
					
		mediaType = mediaTypeList[mediaTypeIndex]
		for mediaPath in self.selectedRomCollection.mediaPaths:
			if(mediaPath.fileType.name == mediaType):
				self.selectedRomCollection.mediaPaths.remove(mediaPath)
				break
			
		if(self.selectedRomCollection != None):
			#save current values to selected Rom Collection
			self.updateSelectedRomCollection()
			#store previous selectedRomCollections state
			self.romCollections[self.selectedRomCollection.id] = self.selectedRomCollection
			
		self.updateRomCollectionControls()
	
	
	def selectScrapersInList(self, sitesInRomCollection, sitesInList):
		
		Logutil.log('selectScrapersInList', util.LOG_LEVEL_INFO)
		
		if(len(sitesInRomCollection) >= 1):
			self.selectItemInList(sitesInRomCollection[0].name, CONTROL_LIST_SCRAPER1)			
		else:
			self.selectItemInList(util.localize(32854), CONTROL_LIST_SCRAPER1)
		if(len(sitesInRomCollection) >= 2):
			self.selectItemInList(sitesInRomCollection[1].name, CONTROL_LIST_SCRAPER2)
		else:
			self.selectItemInList(util.localize(32854), CONTROL_LIST_SCRAPER2)
		if(len(sitesInRomCollection) >= 3):
			self.selectItemInList(sitesInRomCollection[2].name, CONTROL_LIST_SCRAPER3)
		else:
			self.selectItemInList(util.localize(32854), CONTROL_LIST_SCRAPER3)
			
			
	def addScraperToSiteList(self, controlId, sites, romCollection):				

		Logutil.log('addScraperToSiteList', util.LOG_LEVEL_INFO)
		
		control = self.getControlById(controlId)
		scraperItem = control.getSelectedItem()
		scraper = scraperItem.getLabel()
		
		if(scraper == util.localize(32854)):
			return sites
		
		#check if this site is already available for current RC
		for site in romCollection.scraperSites:
			if(site.name == scraper):
				sites.append(site)
				return sites
		
		siteRow = None
		siteRows = self.gui.config.tree.findall('Scrapers/Site')
		for element in siteRows:
			if(element.attrib.get('name') == scraper):
				siteRow = element
				break
		
		if(siteRow == None):
			xbmcgui.Dialog().ok(util.localize(32021), util.localize(32022) %scraper)
			return None
		
		site, errorMsg = self.gui.config.readScraper(siteRow, romCollection.name, '', '', True, self.gui.config.tree)
		if(site != None):
			sites.append(site)
			
		return sites