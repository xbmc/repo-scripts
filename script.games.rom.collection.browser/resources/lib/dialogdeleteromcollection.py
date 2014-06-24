import xbmc, xbmcgui

import os

import util, config
from util import *
from configxmlwriter import *

ACTION_CANCEL_DIALOG = (9,10,51,92,110)

CONTROL_BUTTON_EXIT = 5101
CONTROL_BUTTON_SAVE = 6000
CONTROL_BUTTON_CANCEL = 6010

CONTROL_LIST_ROMCOLLECTIONS = 5410
CONTROL_BUTTON_RC_DOWN = 5411
CONTROL_BUTTON_RC_UP = 5412

CONTROL_LIST_DELETEOPTIONS = 5490
CONTROL_BUTTON_DEL_DOWN = 5491
CONTROL_BUTTON_DEL_UP = 5492


class RemoveRCDialog(xbmcgui.WindowXMLDialog):
		
	selectedControlId = 0
	selectedRomCollection = None
	romCollections = None
	romDelete = 'RCollection'
	deleteCollection = False
	rcDeleteCollection = False
	
	def __init__(self, *args, **kwargs):
		Logutil.log('init Edit RC Basic', util.LOG_LEVEL_INFO)
		
		self.gui = kwargs[ "gui" ]
		self.romCollections = self.gui.config.romCollections
		self.doModal()
	
	
	def onInit(self):
		Logutil.log('onInit Remove Rom Collection', util.LOG_LEVEL_INFO)
		
		#Rom Collections
		Logutil.log('build rom collection list', util.LOG_LEVEL_INFO)
		romCollectionList = []
		for rcId in self.romCollections.keys():
			romCollection = self.romCollections[rcId]
			romCollectionList.append(romCollection.name)
		self.addItemsToList(CONTROL_LIST_ROMCOLLECTIONS, romCollectionList)
		
		#Delete Options
		rcDeleteOptions = [util.localize(32137),util.localize(32138)]
		self.addItemsToList(CONTROL_LIST_DELETEOPTIONS, rcDeleteOptions, properties=['RCollection', 'Roms'])
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
				#Code to Remove Roms
				Logutil.log('Removing Roms', util.LOG_LEVEL_INFO)
				self.setDeleteStatus(True)
				#Code to Remove Collection
				if(self.romDelete == 'RCollection'):
					self.setRCDeleteStatus(True)
					Logutil.log('Removing Rom Collection', util.LOG_LEVEL_INFO)
					configWriterRCDel = ConfigXmlWriter(False)
					RCName = str(self.selectedRomCollection.name)
					success, message = configWriterRCDel.removeRomCollection(RCName)
					if(success == False):
						Logutil.log(message, util.LOG_LEVEL_ERROR)
						xbmcgui.Dialog().ok(util.localize(32019), util.localize(32020))
			Logutil.log('Click Close', util.LOG_LEVEL_INFO)
			self.close()
		#Cancel
		elif (controlID == CONTROL_BUTTON_CANCEL):
			self.close()
		#Rom Collection list
		elif(self.selectedControlId in (CONTROL_BUTTON_RC_DOWN, CONTROL_BUTTON_RC_UP)):						
						
			if(self.selectedRomCollection != None):
				
				#store previous selectedRomCollections state
				self.romCollections[self.selectedRomCollection.id] = self.selectedRomCollection
			
			#HACK: add a little wait time as XBMC needs some ms to execute the MoveUp/MoveDown actions from the skin
			xbmc.sleep(util.WAITTIME_UPDATECONTROLS)
			self.updateControls()
		elif(self.selectedControlId in (CONTROL_BUTTON_DEL_DOWN, CONTROL_BUTTON_DEL_UP)):
			#Check for Remove Roms or Roms and Rom Collection
			control = self.getControlById(CONTROL_LIST_DELETEOPTIONS)
			selectedDeleteOption = str(control.getSelectedItem().getLabel2())
			Logutil.log('selectedDeleteOption = ' +selectedDeleteOption, util.LOG_LEVEL_INFO)
			self.romDelete = selectedDeleteOption
		
						
	
	def onFocus(self, controlId):
		self.selectedControlId = controlId
	
	
	def updateControls(self):
		
		Logutil.log('updateControls', util.LOG_LEVEL_INFO)
		
		control = self.getControlById(CONTROL_LIST_ROMCOLLECTIONS)
		selectedRomCollectionName = str(control.getSelectedItem().getLabel())
				
		self.selectedRomCollection = None
		
		for rcId in self.romCollections.keys():
			romCollection = self.romCollections[rcId]
			if romCollection.name == selectedRomCollectionName:
				self.selectedRomCollection = romCollection
				break
			
		if(self.selectedRomCollection == None):
			return
		
	
	def getSelectedRCId(self):
		return self.selectedRomCollection.id
		
	
	def getControlById(self, controlId):
		try:
			control = self.getControl(controlId)
		except:
			return None
		
		return control
	
	
	def addItemsToList(self, controlId, options, properties=None):
		Logutil.log('addItemsToList', util.LOG_LEVEL_INFO)
		
		control = self.getControlById(controlId)
		control.setVisible(1)
		control.reset()
				
		items = []		
		for i in range(0, len(options)):
			option = options[i]
			property = ''
			if(properties):
				property = properties[i]
			items.append(xbmcgui.ListItem(option, property, '', ''))
							
		control.addItems(items)
			
	
	def selectItemInList(self, options, itemName, controlId):				
		
		Logutil.log('selectItemInList', util.LOG_LEVEL_INFO)		
		
		for i in range(0, len(options)):			
			option = options[i]
			if(itemName == option):
				control = self.getControlById(controlId)
				control.selectItem(i)
				break
				
	def getDeleteStatus(self):
		return self.deleteCollection

	def setDeleteStatus(self, status):
		self.deleteCollection = status
		
	def getRCDeleteStatus(self):
		return self.rcDeleteCollection

	def setRCDeleteStatus(self, status):
		self.rcDeleteCollection = status