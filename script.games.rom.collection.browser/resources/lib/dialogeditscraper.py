import xbmc, xbmcgui

import os

import util, config, dialogbase
from util import *
from configxmlwriter import *

ACTION_CANCEL_DIALOG = (9,10,51,92,110)

CONTROL_BUTTON_EXIT = 5101
CONTROL_BUTTON_SAVE = 6000
CONTROL_BUTTON_CANCEL = 6010


#Scrapers
CONTROL_LIST_SCRAPERS = 5600
CONTROL_BUTTON_SCRAPERS_DOWN = 5601
CONTROL_BUTTON_SCRAPERS_UP = 5602
CONTROL_BUTTON_GAMEDESCPATH = 5520
CONTROL_BUTTON_GAMEDESCMASK = 5530
CONTROL_BUTTON_PARSEINSTRUCTION = 5540
CONTROL_BUTTON_DESCPERGAME = 5550
CONTROL_BUTTON_SEARCHBYCRC = 5560
CONTROL_BUTTON_USEFOLDERASCRC = 5580
CONTROL_BUTTON_USEFILEASCRC = 5590
CONTROL_BUTTON_REMOVESCRAPER = 5610
CONTROL_BUTTON_ADDSCRAPER = 5620


class EditOfflineScraper(dialogbase.DialogBaseEdit):
	
	selectedControlId = 0
	
	selectedOfflineScraper = None
	scraperSites = None
	
	
	def __init__(self, *args, **kwargs):
		Logutil.log('init Edit Offline Scraper', util.LOG_LEVEL_INFO)
		
		self.gui = kwargs[ "gui" ]
		self.scraperSites = self.gui.config.scraperSites
		self.doModal()
		
		
	def onInit(self):
		Logutil.log('onInit Edit Offline Scraper', util.LOG_LEVEL_INFO)
				
		Logutil.log('build scrapers list', util.LOG_LEVEL_INFO)
		scrapers = self.getAvailableScrapers(True)
		self.addItemsToList(CONTROL_LIST_SCRAPERS, scrapers)
		
		self.updateOfflineScraperControls()
		
	
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
				
			#store selectedOfflineScraper
			if(self.selectedOfflineScraper != None):
				self.updateSelectedOfflineScraper()				
				self.scraperSites[self.selectedOfflineScraper.name] = self.selectedOfflineScraper
						
			configWriter = ConfigXmlWriter(False)
			success, message = configWriter.writeScrapers(self.scraperSites)
			
			self.close()
		#Cancel
		elif (controlID == CONTROL_BUTTON_CANCEL):
			self.close()
			
		#Offline Scraper
		elif(self.selectedControlId in (CONTROL_BUTTON_SCRAPERS_UP, CONTROL_BUTTON_SCRAPERS_DOWN)):
			
			if(self.selectedOfflineScraper != None):
				#save current values to selected ScraperSite
				self.updateSelectedOfflineScraper()
				
				#store previous selectedOfflineScrapers state
				self.scraperSites[self.selectedOfflineScraper.name] = self.selectedOfflineScraper
			
			#HACK: add a little wait time as XBMC needs some ms to execute the MoveUp/MoveDown actions from the skin
			xbmc.sleep(util.WAITTIME_UPDATECONTROLS)
			self.updateOfflineScraperControls()
			
		elif (controlID == CONTROL_BUTTON_GAMEDESCPATH):
			
			#check value of descfilepergame
			control = self.getControlById(CONTROL_BUTTON_DESCPERGAME)
			if(control.isSelected()):
				gamedescPathComplete = self.editPathWithFileMask(CONTROL_BUTTON_GAMEDESCPATH, '%s ' %self.selectedOfflineScraper.name +util.localize(32703), CONTROL_BUTTON_GAMEDESCMASK)
				if(gamedescPathComplete != ''):
					#HACK: only use source and parser from 1st scraper
					if(len(self.selectedOfflineScraper.scrapers) >= 1):			
						self.selectedOfflineScraper.scrapers[0].source = gamedescPathComplete
			else:
				dialog = xbmcgui.Dialog()
				gamedescPath = dialog.browse(1, '%s ' %self.selectedOfflineScraper.name +util.localize(32703), 'files', '', False, False, self.selectedOfflineScraper.scrapers[0].source)
				if(gamedescPath == ''):
					return
				
				if(len(self.selectedOfflineScraper.scrapers) >= 1):
					self.selectedOfflineScraper.scrapers[0].source = gamedescPath

				control = self.getControlById(CONTROL_BUTTON_GAMEDESCPATH)
				control.setLabel(gamedescPath)
		
		elif (controlID == CONTROL_BUTTON_GAMEDESCMASK):
			
			if(len(self.selectedOfflineScraper.scrapers) >= 1):
				self.selectedOfflineScraper.scrapers[0].source = self.editFilemask(CONTROL_BUTTON_GAMEDESCMASK, util.localize(32704), self.selectedOfflineScraper.scrapers[0].source)
			
		elif (controlID == CONTROL_BUTTON_DESCPERGAME):
			#set value of gamedesc path and mask
			self.toggleGameDescPath()
		
		elif (controlID == CONTROL_BUTTON_PARSEINSTRUCTION):
			
			dialog = xbmcgui.Dialog()
			
			parseInstruction = dialog.browse(1, '%s ' %self.selectedOfflineScraper.name +util.localize(32705), 'files')
			if(parseInstruction == ''):
				return
			
			control = self.getControlById(CONTROL_BUTTON_PARSEINSTRUCTION)
			control.setLabel(parseInstruction)		
			
			if(len(self.selectedOfflineScraper.scrapers) >= 1):
				self.selectedOfflineScraper.scrapers[0].parseInstruction = parseInstruction
				
		elif (controlID == CONTROL_BUTTON_ADDSCRAPER):
			
			#get list of all rc names that are not in use
			names = []
			for romCollection in self.gui.config.romCollections.values():
				scraperInUse = False
				for scraper in self.gui.config.scraperSites:
					if(romCollection.name == scraper):
						scraperInUse = True
						break
				
				if not scraperInUse:
					names.append(romCollection.name)
			
			dialog = xbmcgui.Dialog()
			
			if(len(names) == 0):
				dialog.ok(util.SCRIPTNAME, util.localize(32144), util.localize(32145))
				return
						
			#select name
			scraperIndex = dialog.select(util.localize(32146), names)
			if(scraperIndex == -1):
				return						
			
			name = names[scraperIndex]
			if(name == ''):
				return
			
			site = Site()
			site.name = name
			site.scrapers = []
			scraper = Scraper()
			scraper.encoding = 'iso-8859-1'			
						
			#select game desc
			gamedescPath = dialog.browse(1, '%s ' %name +util.localize(32703), 'files')
			if(gamedescPath == ''):
				return
			
			scraper.source = gamedescPath
			
			#select parse instruction
			parseInstruction = dialog.browse(1, '%s ' %self.selectedOfflineScraper.name +util.localize(32705), 'files')
			if(parseInstruction == ''):
				return
			
			scraper.parseInstruction = parseInstruction
			
			
			site.scrapers.append(scraper)
			self.scraperSites[name] = site				
			
			#add scraper to list
			control = self.getControlById(CONTROL_LIST_SCRAPERS)
			item = xbmcgui.ListItem(name, '', '', '')
			control.addItem(item)
						
			self.selectItemInList(name, CONTROL_LIST_SCRAPERS)
			
			if(self.selectedOfflineScraper != None):
				#save current values to selected ScraperSite
				self.updateSelectedOfflineScraper()
				
				#store previous selectedOfflineScrapers state
				self.scraperSites[self.selectedOfflineScraper.name] = self.selectedOfflineScraper
			
			#HACK: add a little wait time as XBMC needs some ms to execute the MoveUp/MoveDown actions from the skin
			xbmc.sleep(util.WAITTIME_UPDATECONTROLS)
			self.updateOfflineScraperControls()
			
		elif (controlID == CONTROL_BUTTON_REMOVESCRAPER):
			
			scraperSites = self.getAvailableScrapers(True)
			
			scraperIndex = xbmcgui.Dialog().select(util.localize(32147), scraperSites)
			if(scraperIndex == -1):
				return
			
			scraperSite = scraperSites[scraperIndex]
			
			#check if scraper is in use
			for romCollection in self.gui.config.romCollections.values():				
				for scraper in romCollection.scraperSites:
					if(scraper.name == scraperSite):
						xbmcgui.Dialog().ok(util.localize(32019), util.localize(32148) %scraper.name)
						return

																	
			scraperSites.remove(scraperSite)
			del self.scraperSites[scraperSite]
			
			if(len(scraperSites) == 0):
				scraperSites.append(util.localize(32854))
				site = Site()
				site.name = util.localize(32854)
				site.scrapers = []
				self.scraperSites[util.localize(32854)] = site
				
			control = self.getControlById(CONTROL_LIST_SCRAPERS)
			control.reset()
			self.addItemsToList(CONTROL_LIST_SCRAPERS, scraperSites)
				
			self.updateOfflineScraperControls()
			
	
	def onFocus(self, controlId):
		self.selectedControlId = controlId
	
	
	def updateOfflineScraperControls(self):
		
		Logutil.log('updateOfflineScraperControls', util.LOG_LEVEL_INFO)
		
		control = self.getControlById(CONTROL_LIST_SCRAPERS)
		selectedScraperName = str(control.getSelectedItem().getLabel())
		
		selectedSite = None
		try:
			selectedSite = self.scraperSites[selectedScraperName]
		except:
			#should not happen
			return
		
		self.selectedOfflineScraper = selectedSite
		
		#HACK: only use source and parser from 1st scraper
		firstScraper = None
		if(len(selectedSite.scrapers) >= 1):			
			firstScraper = selectedSite.scrapers[0]
		if(firstScraper == None):
			firstScraper = Scraper()
		
		
		"""
		pathParts = os.path.split(firstScraper.source)
		scraperSource = pathParts[0]
		scraperFileMask = pathParts[1]
		
		control = self.getControlById(CONTROL_BUTTON_GAMEDESCPATH)
		control.setLabel(scraperSource)
		
		control = self.getControlById(CONTROL_BUTTON_GAMEDESCMASK)
		if(selectedSite.descFilePerGame):
			control.setLabel(scraperFileMask)
		else:
			control.setLabel('')
		"""
		
		control = self.getControlById(CONTROL_BUTTON_PARSEINSTRUCTION)
		control.setLabel(firstScraper.parseInstruction)
		
		control = self.getControlById(CONTROL_BUTTON_DESCPERGAME)
		control.setSelected(selectedSite.descFilePerGame)
		#set skin setting for game desc file mask control
		if(selectedSite.descFilePerGame):
			xbmc.executebuiltin('Skin.SetBool(%s)' %util.SETTING_RCB_EDITSCRAPER_DESCFILEPERGAME)
		else:
			xbmc.executebuiltin('Skin.Reset(%s)' %util.SETTING_RCB_EDITSCRAPER_DESCFILEPERGAME)
			
		#set value of game desc path and mask
		self.toggleGameDescPath()
		
		control = self.getControlById(CONTROL_BUTTON_SEARCHBYCRC)
		control.setSelected(selectedSite.searchGameByCRC)
		
		control = self.getControlById(CONTROL_BUTTON_USEFILEASCRC)
		control.setSelected(selectedSite.useFilenameAsCRC)
		
		control = self.getControlById(CONTROL_BUTTON_USEFOLDERASCRC)
		control.setSelected(selectedSite.useFoldernameAsCRC)
		
	
	def updateSelectedOfflineScraper(self):
		Logutil.log('updateSelectedOfflineScraper', util.LOG_LEVEL_INFO)
		
		#desc file per game
		control = self.getControlById(CONTROL_BUTTON_DESCPERGAME)
		self.selectedOfflineScraper.descFilePerGame = bool(control.isSelected())
		
		#search game by crc
		control = self.getControlById(CONTROL_BUTTON_SEARCHBYCRC)
		self.selectedOfflineScraper.searchGameByCRC = bool(control.isSelected())
		
		#use foldername as crc
		control = self.getControlById(CONTROL_BUTTON_USEFOLDERASCRC)
		self.selectedOfflineScraper.useFoldernameAsCRC = bool(control.isSelected())
		
		#use filename as crc
		control = self.getControlById(CONTROL_BUTTON_USEFILEASCRC)
		self.selectedOfflineScraper.useFilenameAsCRC = bool(control.isSelected())
		
		
	def toggleGameDescPath(self):
		
		if(len(self.selectedOfflineScraper.scrapers) >= 1):
			pathComplete = self.selectedOfflineScraper.scrapers[0].source
			pathParts = os.path.split(pathComplete)
	
			controlPath = self.getControlById(CONTROL_BUTTON_GAMEDESCPATH)
			controlMask = self.getControlById(CONTROL_BUTTON_GAMEDESCMASK)
			
			#check value of descfilepergame
			controlDescPerGame = self.getControlById(CONTROL_BUTTON_DESCPERGAME)
			if(controlDescPerGame.isSelected()):				
				controlPath.setLabel(pathParts[0])
				controlMask.setLabel(pathParts[1])
			else:
				controlPath.setLabel(pathComplete)
				controlMask.setLabel('')
		
		