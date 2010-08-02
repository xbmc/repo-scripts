# This class is not pretty. Needs some TLC

import xbmc, xbmcgui
import sys
import pickle
import os
import traceback
sys.path.append(os.path.join(os.getcwd().replace(";",""),'resources/lib'))

def gShowPlaylists(playlists=[], options=[]):
#	popup = popupList(title= 'Playlists', items=playlists, btns=options, width=400)
#	popup.doModal()
#	selected = popup.selected
#	del popup
#	return selected
	
	selected = gSimplePopup(title='Playlists', items=playlists)
	if selected != -1:
		if options != []:
			action = gSimplePopup('Do what?', items=options)
			if action == -1:
				return [-1, -1]
			else:
				return [action, selected]
		else:
			return [-1, -1]
	else:
		if options != []:
			return [-1, selected]
		else:
			return [-1, -1]
	
	
def gSimplePopup(title='', items=[], width=300):
#	popupMenu = popupBtns(title='', btns=items, width=width)
#	rootDir = os.getcwd()
#	print 'RootDir: ' + rootDir
	#popupMenu = popupBtns("button-popup.xml", rootDir, "DefaultSkin")	
#	popupMenu.doModal()
#	selected = popupMenu.selected
#	del popupMenu
#	return selected
	dialog = xbmcgui.Dialog()
	return dialog.select(title, items)

#class popupBtns
#	def __init__(self, title, btns=[], width=100):
#		dialog = xbmcgui.Dialog()
#		self.selected = dialog.select(title, btns)

class popupBtnsXml(xbmcgui.WindowXMLDialog):
	#def __init__(self, title, btns=[], width=100):
	def __init__(self, *args, **kwargs):
		self.w=100
		pass

	def onInit(self):
		pass
			
	def onControl(self, action):
		print 'control: ' + action.getButtonCode()
		pass

	def onClick(self, controlId):
		print 'control, click: ' + controlID
		pass

	def onFocus(self, controlID):
		pass

	def onAction(self, action):
		pass


class popupBtnsOld(xbmcgui.WindowDialog):
	def __init__(self, title, btns=[], width=100):
		self.w = width
		self.selected = -1
		self.btns = btns
		self.btnCnts = [0]
		for i in range(len(btns)-1): # There has to be a better way to do this. zeros doesn't work...
			self.btnCnts.append(0)

	#def onInit(self):
		w = self.w		
		pad = 10
		hCnt = 30
		yo = 5

		h = len(self.btns) * (hCnt + 5) + yo
		mediaDir = os.path.join(os.getcwd().replace(";",""),'resources/skins/DefaultSkin/media')
		rw = self.getWidth()
		rh = self.getHeight()
		x = rw/2 - w/2
		y = rh/2 -h/2
		
		print 'rw: ' + str(rw)
		print 'rh: ' + str(rh)
		print 'Media Dir: ' +os.path.join(mediaDir,'gs-bg-menu.png')

		# Background
		#self.imgBg = xbmcgui.ControlImage(0+x-30,0+y-30,w+60,h+60, os.path.join(mediaDir,'gs-bg-menu.png'))
		self.imgBg = xbmcgui.ControlImage(0,0,w+60,h+60, os.path.join(mediaDir,'gs-bg-menu.png'))
		print self.imgBg
		self.addControl(self.imgBg)
		
		i = 0
		while i < len(btns):
			self.btnCnts[i] = xbmcgui.ControlButton(pad+x, yo+y, w-2*pad, hCnt, str(self.btns[i]), os.path.join(mediaDir,'button_focus.png'), '', font='font12', textColor='0xFFFFFFFF', alignment=2)
			self.addControl(self.btnCnts[i])
			yo += hCnt + 5
			i += 1
			
		self.setFocus(self.btnCnts[0])
			
	def onControl(self, action):
		pass
 
	def onAction(self, action):
		if action == 10:
			self.close()	
		elif (action == 3) or (action == 4) or (action == 7) or (action == 9):
			try:	
				cnt = self.getFocus()
			except:
				self.setFocus(self.btnCnts[0])
				return None

			d = 0
			if action == 3: # Up
				d = -1
			elif action == 4: # Down
				d = 1
			l = len(self.btnCnts)
			for i in range(l):
				if self.btnCnts[i] == cnt:
					if action == 7: # Select
						self.selected = i
						self.close()
					elif action == 9: # Back
						self.close()
					elif i+d > l-1:
						self.setFocus(self.btnCnts[0])
					elif i+d < 0:
						self.setFocus(self.btnCnts[l-1])
					else:
						self.setFocus(self.btnCnts[i+d])
						

class popupList(xbmcgui.WindowDialog):
	def __init__(self, title, btns=[], items=[], width=100):
		w = width
		pad = 5
		hCnt = 30
		yo = 30
		self.selected = [-1, -1]
		h = 420
		self.btns = btns
		mediaDir = os.path.join(os.getcwd().replace(";",""),'resources/skins/DefaultSkin/media')
		rw = self.getWidth()
		rh = self.getHeight()
		x = rw/2 - w/2
		y = rh/2 -h/2
		
		# Background
		#self.imgBg = xbmcgui.ControlImage(5+x,5+y,w,h, os.path.join(mediaDir,'popup-bg-shadow.png'))
		#self.addControl(self.imgBg)
		self.imgBg = xbmcgui.ControlImage(0+x-30,0+y-30,w+60,h+60, os.path.join(mediaDir,'gs-bg-menu.png'))
		self.addControl(self.imgBg)
		self.imgBg = xbmcgui.ControlImage(0+x+pad,yo+y,w-2*pad,h-yo-2*pad, os.path.join(mediaDir,'list-bg2.png'))
		self.addControl(self.imgBg)
		
		# Title
		self.labelTitle = xbmcgui.ControlLabel(0+x, 0+y, w, hCnt, title, 'font14', '0xFFFFFFFF', alignment=2)
		self.addControl(self.labelTitle)
		
		self.cntList = xbmcgui.ControlList(2*pad+x, yo+y+pad, w-4*pad, h-4*pad, buttonFocusTexture = os.path.join(mediaDir,'button_focus.png'), font='font12', textColor='0xFFFFFFFF', space=0)
		self.addControl(self.cntList)
		for item in items:
			self.cntList.addItem(str(item))
		self.setFocus(self.cntList)
		
	def onAction(self, action):
		if action == 10:
			self.selected = [-1, -1]
			self.close()
		elif action == 9: # Back
			self.selected = [-1, -1]
			self.close()	
		elif (action == 3) or (action == 4):
			try:	
				cnt = self.getFocus()
			except:
				self.setFocus(self.cntList)
				return None
		elif action == 7:
			if len(self.btns) != 0:
				popupMenu = popupBtns(title='', btns=self.btns, width=150)
				popupMenu.doModal()
				if popupMenu.selected != -1:
					self.selected = [popupMenu.selected, self.cntList.getSelectedPosition()]
					del popupMenu
					self.close()
				else:
					del popupMenu
			else:
				self.selected = [-1, self.cntList.getSelectedPosition()]
				self.close()
		else:
			pass
			
	def onControl(self, controlID):
		pass

class settingsUI(xbmcgui.WindowDialog):
	def __init__(self, settings=[]):
		x = 100
		y = 100
		h = 350
		w = 400
		hCnt = 30
		self.settings = settings
		self.saved = False
		mediaDir = os.path.join(os.getcwd().replace(";",""),'resources/skins/DefaultSkin/media')
		rw = self.getWidth()
		rh = self.getHeight()
		x = rw/2 - w/2
		y = rh/2 -h/2
		
		#y = 0
		#x = 0
		
		# Background
		self.imgBg = xbmcgui.ControlImage(0+x-30,0+y-30,w+60,h+60, os.path.join(mediaDir,'gs-bg-menu.png'))
		self.addControl(self.imgBg)

		# Settings
		self.labelSettings = xbmcgui.ControlLabel(0+x, 0+y, w, hCnt, 'Settings', 'font14', '0xFFFFFFFF', alignment=2)
		self.addControl(self.labelSettings)
		
		# Search
		self.labelSearch = xbmcgui.ControlLabel(5+x, 40+y, w-5, hCnt, 'Search:', 'font13', '0xFFFFFFFF', alignment=0)
		self.addControl(self.labelSearch)
		self.radioAlbums = xbmcgui.ControlRadioButton(20+x, 70+y, w-40, hCnt, 'Only verified albums (disabled in API)', 'button_focus.png', '', font='font12', textColor='0xFFFFFFFF')
		self.addControl(self.radioAlbums)
		self.radioSongs = xbmcgui.ControlRadioButton(20+x, 100+y, w-40, hCnt, 'Exact match for songs (unimplemented)', 'button_focus.png', '', font='font12', textColor='0xFFFFFFFF')
		self.addControl(self.radioSongs)
		
		# Login
		self.labelLogin = xbmcgui.ControlLabel(5+x, 140+y, w, hCnt, 'Login:', 'font13', '0xFFFFFFFF', alignment=0)
		self.addControl(self.labelLogin)
		self.btnUsername = xbmcgui.ControlButton(20+x, 170+y, w-40, hCnt, '', 'button_focus.png', '', font='font12', textColor='0xFFFFFFFF')
		self.addControl(self.btnUsername)
		self.btnPassword = xbmcgui.ControlButton(20+x, 200+y, w-40, hCnt, '', 'button_focus.png', '', font='font12', textColor='0xFFFFFFFF')
		self.addControl(self.btnPassword)
		
		# Debug
		self.labelDebug = xbmcgui.ControlLabel(5+x, 240+y, w-5, hCnt, 'Debug:', 'font13', '0xFFFFFFFF', alignment=0)
		self.addControl(self.labelDebug)
		self.radioDebug = xbmcgui.ControlRadioButton(20+x, 270+y, w-40, hCnt, 'Turn on debugging (restart script)', 'button_focus.png', '', font='font12', textColor='0xFFFFFFFF')
		self.addControl(self.radioDebug)
		
		# Buttons
		self.btnSave = xbmcgui.ControlButton(150+x, 310+y, 100, hCnt, 'Save', 'button_focus.png', '', font='font12', textColor='0xFFFFFFFF', alignment=2)
		self.addControl(self.btnSave)
		
		self.setControls(self.settings)

		self.setFocus(self.radioAlbums)
		
	def setControls(self, settings):
		if settings[0] != '':
			self.btnUsername.setLabel('Username: ' + settings[0])
		else:
			self.btnUsername.setLabel('Username: (unset)')
		
		if settings[1] != '':
			password = ''
			for l in settings[1]:
				password = password + '*'
			self.btnPassword.setLabel('Password: ' + password)
		else:
			self.btnPassword.setLabel('Password: (unset)')
		
		self.radioAlbums.setSelected(settings[2])
		self.radioSongs.setSelected(settings[3])
		self.radioDebug.setSelected(settings[4])
		
	def getControls(self):
		settings = self.settings
		settings[2] = self.radioAlbums.isSelected()
		settings[3] = self.radioSongs.isSelected()
		settings[4] = self.radioDebug.isSelected()
		return settings
		
	def onControl(self, action):
		pass
 
	def onAction(self, action):
		try:	
			cnt = self.getFocus()
		except:
			self.setFocus(self.radioAlbums)
			return None
		if action == 10:
			self.close()
		elif action == 9: # Back
			self.close()
		elif cnt == self.radioAlbums:
			if action == 3: # Up
				self.setFocus(self.btnSave)
			elif action == 4: # Down
				self.setFocus(self.radioSongs)
			else:
				pass
		elif cnt == self.radioSongs:
			if action == 3: # Up
				self.setFocus(self.radioAlbums)
			elif action == 4: # Down
				self.setFocus(self.btnUsername)
			else:
				pass
		elif cnt == self.btnUsername:
			if action == 3: # Up
				self.setFocus(self.radioSongs)
			elif action == 4: # Down
				self.setFocus(self.btnPassword)
			elif action == 7: # Select
				username = self.getInput('Username', default=self.settings[0])
				if username != '':
					self.settings[0] = username
					self.setControls(self.settings)
			else:
				pass
		elif cnt == self.btnPassword:
			if action == 3: # Up
				self.setFocus(self.btnUsername)
			elif action == 4: # Down
				self.setFocus(self.radioDebug)
			elif action == 7: # Select
				password = self.getInput('Password')
				if password != '':
					self.settings[1] = password
					self.setControls(self.settings)
			else:
				pass
		elif cnt == self.radioDebug:
			if action == 3: # Up
				self.setFocus(self.btnPassword)
			elif action == 4: # Down
				self.setFocus(self.btnSave)
			else:
				pass
		elif cnt == self.btnSave:
			if action == 3: # Up
				self.setFocus(self.radioDebug)
			elif action == 4: # Down
				self.setFocus(self.radioAlbums)
			elif action == 7: # Select
				self.saved = True
				self.settings = self.getControls()
				self.close()
			else:
				pass
				
	def settingsSaved(self):
		return self.saved
		
	def getSettings(self):
		return self.settings
				
	def getInput(self, title, default="", hidden=False):
		ret = ""
	
		keyboard = xbmc.Keyboard(default, title)
		keyboard.setHiddenInput(hidden)
		keyboard.doModal()

		if keyboard.isConfirmed():
			ret = keyboard.getText()

		return ret

