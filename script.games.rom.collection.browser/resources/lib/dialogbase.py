import xbmc, xbmcgui

import os

import util, config
from util import *

ACTION_CANCEL_DIALOG = (9,10,51,92,110)
CONTROL_BUTTON_EXIT = 5101


class DialogBaseEdit(xbmcgui.WindowXMLDialog):
	
	
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
		
		
	def getAvailableScrapers(self, localOnly):
		Logutil.log('get available scrapers', util.LOG_LEVEL_INFO)
		
		#Scrapers
		sitesInList = []		
		if(not localOnly):
			sitesInList.append(util.localize(56004))
		#get all scrapers
		
		for siteName in self.scraperSites:
			
			site = self.scraperSites[siteName]
			
			#only add scrapers without http
			if(localOnly):
				#don't use local nfo scraper
				if(site.name == util.localize(40054)):
					 continue
				skipScraper = False
				
				for scraper in site.scrapers:
					source = scraper.source
					if(source.startswith('http')):
						skipScraper = True
						break
				if(skipScraper):
					continue
			
			
			Logutil.log('add scraper name: ' +str(site.name), util.LOG_LEVEL_INFO)
			sitesInList.append(site.name)
				
		if(len(sitesInList) == 0):
			 sitesInList.append(util.localize(56004))
				
		return sitesInList
	
	
	def editTextProperty(self, controlId, name):
		control = self.getControlById(controlId)
		textValue = control.getLabel()
		
		keyboard = xbmc.Keyboard()
		keyboard.setHeading(util.localize(40032) %name)			
		keyboard.setDefault(textValue)
		keyboard.doModal()
		if (keyboard.isConfirmed()):
			textValue = keyboard.getText()
							
		control.setLabel(textValue)
		
		return textValue
	
	
	def editPathWithFileMask(self, controlId, enterString, controlIdFilemask):
		
		dialog = xbmcgui.Dialog()
		
		#get new value
		pathValue = dialog.browse(0, enterString, 'files')
		if(pathValue == ''):
			return ''
		
		control = self.getControlById(controlId)
		control.setLabel(pathValue)
		
		
		control = self.getControlById(controlIdFilemask)
		filemask = control.getLabel()
		pathComplete = os.path.join(pathValue, filemask.strip())
		
		return pathComplete
		
		
	def editFilemask(self, controlId, enterString, pathComplete):
		control = self.getControlById(controlId)
		filemask = control.getLabel()
		
		keyboard = xbmc.Keyboard()
		keyboard.setHeading(util.localize(40032) %enterString)
		keyboard.setDefault(filemask)
		keyboard.doModal()
		if (keyboard.isConfirmed()):
			filemask = keyboard.getText()
		
		control.setLabel(filemask)
												
		pathParts = os.path.split(pathComplete)
		path = pathParts[0]
		pathComplete = os.path.join(path, filemask.strip())
		
		return pathComplete
	
	
	def selectItemInList(self, itemName, controlId):				
		
		Logutil.log('selectItemInList', util.LOG_LEVEL_INFO)		
		
		control = self.getControlById(controlId)
		
		for i in range(0, control.size()):
			item = control.getListItem(i)
			if(item.getLabel() == itemName):
				control.selectItem(i)
				break