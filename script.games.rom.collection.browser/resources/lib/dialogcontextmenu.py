
import xbmc, xbmcgui
import util
import dialogeditromcollection, dialogeditscraper, dialogdeleteromcollection
from util import *

ACTION_EXIT_SCRIPT = (10,)
ACTION_CANCEL_DIALOG = ACTION_EXIT_SCRIPT + (9,)


class ContextMenuDialog(xbmcgui.WindowXMLDialog):
	def __init__(self, *args, **kwargs):
		# Don't put GUI sensitive stuff here (as the xml hasn't been read yet)
		Logutil.log('init ContextMenu', util.LOG_LEVEL_INFO)
		
		self.gui = kwargs[ "gui" ]
		
		self.doModal()
	
	def onInit(self):
		Logutil.log('onInit ContextMenu', util.LOG_LEVEL_INFO)		
	
	def onAction(self, action):
		if (action.getId() in ACTION_CANCEL_DIALOG):
			self.close()
	
	def onClick(self, controlID):
		if (controlID == 5101): # Close window button
			self.close()
		elif (controlID == 5110): # Import games
			self.close()
			self.gui.updateDB()		
		elif (controlID == 5111): # add Rom Collection			
			self.close()
			self.gui.addRomCollection()
		elif (controlID == 5112): # edit Rom Collection			
			self.close()
			constructorParam = 1
			if(util.hasAddons()):
				constructorParam = "PAL"
			editRCdialog = dialogeditromcollection.EditRomCollectionDialog("script-RCB-editromcollection.xml", util.getAddonInstallPath(), "Default", constructorParam, gui=self.gui)			
			del editRCdialog
			
			self.config = Config()
			self.config.readXml()
			
		elif (controlID == 5117): # edit scraper			
			self.close()
			constructorParam = 1
			if(util.hasAddons()):
				constructorParam = "PAL"
			editscraperdialog = dialogeditscraper.EditOfflineScraper("script-RCB-editscraper.xml", util.getAddonInstallPath(), "Default", constructorParam, gui=self.gui)			
			del editscraperdialog
			
			self.config = Config()
			self.config.readXml()
		
		elif (controlID == 5113): #Edit Game Command			
			self.close()
			
			pos = self.gui.getCurrentListPosition()
			if(pos == -1):
				xbmcgui.Dialog().ok(util.SCRIPTNAME, 'Edit Game Command Error', "Can't load selected Game")
				return					
				
			selectedGame, gameRow = self.gui.getGameByPosition(self.gui.gdb, pos)
			if(selectedGame == None or gameRow == None):
				xbmcgui.Dialog().ok(util.SCRIPTNAME, 'Edit Game Command Error', "Can't load selected Game")
				return

			command = gameRow[util.GAME_gameCmd]
			
			keyboard = xbmc.Keyboard()
			keyboard.setHeading('Enter Game Command')
			if(command != None):
				keyboard.setDefault(command)
			keyboard.doModal()
			if (keyboard.isConfirmed()):
				command = keyboard.getText()
				
				Logutil.log("Updating game '%s' with command '%s'" %(str(gameRow[util.ROW_NAME]), command), util.LOG_LEVEL_INFO)
				Game(self.gui.gdb).update(('gameCmd',), (command,), gameRow[util.ROW_ID])
				self.gui.gdb.commit()
			
		elif (controlID == 5114): #Delete Rom
			pos = self.gui.getCurrentListPosition()
			if(pos == -1):
				xbmcgui.Dialog().ok(util.SCRIPTNAME, 'Delete Game Error', "Can't delete selected Game")
				return					
			dialog = xbmcgui.Dialog()
			if dialog.yesno("Delete Game", "Are you sure you want to delete this game?"):
				gameID = self.gui.getGameId(self.gui.gdb,pos)
				self.gui.deleteGame(gameID)
				self.gui.showGames()
				if(pos > 0):
					pos = pos - 1
					self.gui.setFilterSelection(self.gui.CONTROL_GAMES_GROUP_START, pos)
				else:
					self.gui.setFilterSelection(self.gui.CONTROL_GAMES_GROUP_START, 0)
		
		elif (controlID == 5115): #Remove Rom Collection			
			self.close()
			
			constructorParam = 1
			if(util.hasAddons()):
				constructorParam = "PAL"
			removeRCDialog = dialogdeleteromcollection.RemoveRCDialog("script-RCB-removeRC.xml", util.getAddonInstallPath(), "Default", constructorParam, gui=self.gui)			
			rDelStat = removeRCDialog.getDeleteStatus()
			if(rDelStat):
				selectedRCId = removeRCDialog.getSelectedRCId()
				rcDelStat = removeRCDialog.getRCDeleteStatus()
				self.gui.deleteRCGames(selectedRCId, rcDelStat, rDelStat)
				del removeRCDialog
				
		elif (controlID == 5116): #Clean DB			
			self.close()
			self.gui.cleanDB()
		
	
	def onFocus(self, controlID):
		pass

