# This class is not pretty. Needs some TLC

import xbmc, xbmcgui
import sys
import pickle
import os
import traceback
import threading

sys.path.append(os.path.join(os.getcwd().replace(";",""),'resources','lib'))
__language__ = sys.modules[ "__main__" ].__language__
__isXbox__ = sys.modules[ "__main__" ].__isXbox__

if __isXbox__ == False: # MusicSuggestions is not supported fox XBOX yet
	from MusicSuggestions import getTextThread

def gShowPlaylists(playlists=[], options=[]):
	popup = popupList(title= 'Playlists', items=playlists, btns=options, width=0.5)
	popup.doModal()
	selected = popup.selected
	del popup
	return selected	
	
def gSimplePopup(title='', items=[], width=300, returnAll = False):
	popupMenu = popupBtns(title='', btns=items, width=width)
	popupMenu.doModal()
	n = popupMenu.selected
	del popupMenu
	if returnAll == False:
		return n
	else:
		if n == -1:
			return [n, '']
		else:
			return [n, items[n]]

class popupBtnsXml(xbmcgui.WindowXMLDialog):
	#def __init__(self, title, btns=[], width=100):
	def __init__(self, *args, **kwargs):
		self.w=100
		pass

	def onInit(self):
		print "################## INIT"
		#h = len(self.btns) * (hCnt + 5) + yo
		mediaDir = os.path.join(os.getcwd().replace(";",""),'resources','skins','DefaultSkin','media')
		#rw = self.getWidth()
		#rh = self.getHeight()
		#x = rw/2 - w/2
		#y = rh/2 -h/2
		
		#print 'rw: ' + str(rw)
		#print 'rh: ' + str(rh)
		#print 'Media Dir: ' +os.path.join(mediaDir,'gs-bg-menu.png')
		w = 100
		h = 100
		# Background
		#self.imgBg = xbmcgui.ControlImage(0+x-30,0+y-30,w+60,h+60, os.path.join(mediaDir,'gs-bg-menu.png'))
		self.imgBg = xbmcgui.ControlImage(0,0,w+60,h+60, os.path.join(mediaDir,'gs-bg-menu.png'))
		print self.imgBg
		self.addControl(self.imgBg)
		pass
			
	def onAction(self, action):
		#self.close()
		aId = action.getId()
		print '###### aId: ' + str(aId)
		if aId == 10:
			self.close()
		else:

			#aId = 10
			pWin = xbmcgui.Window(10500)
			#xbmc.sendclick(10500, aId)
			xbmc.executebuiltin('XBMC.Action(10500,' + str(aId) + ')')
			pWin.onAction(action)
			#pWin.close()
		#pass

	def onClick(self, controlId):
		print 'control, click: ' + controlID
		aId = controlId.getId()
		if aId == 10:
			self.close()
		pass

	def onFocus(self, controlID):
		pass

def busy():
	t = busyThread()
	w = t.getWindow()
	t.start()
	return w


class busyThread(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.w = popupBusyXml("popup-busy.xml", os.getcwd(), "DefaultSkin")
		pass
	def run (self):
		self.w.doModal()
	def getWindow(self):
		return self.w

class popupBusyXml(xbmcgui.WindowXMLDialog):
#	def __init__(self, *args, **kwargs):
#		pass

	def onInit(self):
		pass
			
	def onAction(self, action):
		#self.close()
		aId = action.getId()
		if aId == 10:
			self.close()

	def onClick(self, controlId):
		aId = controlId.getId()
		if aId == 10:
			self.close()
		pass

	def onFocus(self, controlID):
		pass

	def place(self):
		rw = 1280
		rh = 720
		group = self.getControl(210)
		icon = self.getControl(220)
		h = icon.getHeight()
		w = icon.getWidth()
		x = rw/2 - w/2
		y = rh/2 - h/2
		#print 'x: ' + str(x) + ', y: ' + str(y) + ', h: ' + str(h) + ', w: ' + str(w) + ', rh: ' + str(rh) + ', rw: ' + str(rw)
		group.setPosition(x, y)

	def setLabel(self, text):
		self.getControl(310).setLabel(text)

	def setProgress(self, n):
		self.getControl(230).setVisible(True)
		if n < 0:
			i = 0
		elif n > 100:
			i = 100
		else:
			i = n
		self.getControl(300).setLabel(str(i) + '%')

class popupBtns(xbmcgui.WindowDialog):
	def __init__(self, title='', btns=[], width=1):
		self.w = width
		self.selected = -1
		self.btns = btns
		self.btnCnts = [0]
		for i in range(len(btns)-1): # There has to be a better way to do this. zeros doesn't work...
			self.btnCnts.append(0)

#	def onInit(self):
		w = self.w		
		w = int(self.getWidth()*width)
		pad = self.getHeight()/100
		hCnt = 5*pad
		yo = pad

		h = len(self.btns) * (hCnt + 5) + yo
		mediaDir = os.path.join(os.getcwd().replace(";",""),'resources','skins','DefaultSkin','media')
		rw = self.getWidth()
		rh = self.getHeight()
		x = rw/2 - w/2
		y = rh/2 - h/2

		# Background
		self.imgBg = xbmcgui.ControlImage(0+x-4*pad,0+y-4*pad,w+8*pad,h+8*pad, os.path.join(mediaDir,'gs-bg-menu.png'))
		self.addControl(self.imgBg)
		
		i = 0
		while i < len(self.btns):
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
		w = int(self.getWidth()*width)
		pad = int(self.getHeight()/100)
		hCnt = 30
		yo = 30
		self.selected = [-1, -1]
		h = self.getHeight()-30*pad
		self.btns = btns
		mediaDir = os.path.join(os.getcwd(),'resources','skins','DefaultSkin','media')
		rw = self.getWidth()
		rh = self.getHeight()
		x = rw/2 - w/2
		y = rh/2 -h/2
		
		# Background
		#self.imgBg = xbmcgui.ControlImage(5+x,5+y,w,h, os.path.join(mediaDir,'popup-bg-shadow.png'))
		#self.addControl(self.imgBg)
		self.imgBg = xbmcgui.ControlImage(0+x-30,0+y-30,w+60,h+60, os.path.join(mediaDir,'gs-bg-menu.png'))
		self.addControl(self.imgBg)
		self.imgBg = xbmcgui.ControlImage(0+x+pad,5*pad+y,w-2*pad,h-5*pad, os.path.join(mediaDir,'list-bg2.png'))
		self.addControl(self.imgBg)
		
		# Title
		self.labelTitle = xbmcgui.ControlLabel(0+x, 0+y, w, hCnt, title, 'font14', '0xFFFFFFFF', alignment=2)
		self.addControl(self.labelTitle)
		
		self.cntList = xbmcgui.ControlList(2*pad+x, yo+y+3*pad, w-4*pad, h-10*pad, buttonFocusTexture = os.path.join(mediaDir,'button_focus.png'), font='font12', textColor='0xFFFFFFFF', space=0, itemHeight=7*pad)
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
				popupMenu = popupBtns(title='', btns=self.btns, width=0.2)
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

class SearchXml(xbmcgui.WindowXMLDialog):
	def onInit(self):
		self.query = ''
		self.result = None
		self.showKeyboard()
		pass
			
	def onAction(self, action):
		aId = action.getId()
		if aId == 10:
			self.close()
		elif aId == 2: #Right		
			if self.getFocusId() == 502:
				self.showKeyboard()
			elif self.getFocusId() == 501:
				self.setFocus(self.getControl(502))
			elif self.getFocusId() == 500:
				self.setFocus(self.getControl(501))
			else:
				pass
		if aId == 1: #Left
			if self.getFocusId() == 500:
				self.showKeyboard()
			elif self.getFocusId() == 501:
				self.setFocus(self.getControl(500))
			elif self.getFocusId() == 502:
				self.setFocus(self.getControl(501))
			else:
				pass
		else:
			pass

	def onClick(self, controlId):
		print 'control, click: ' + str(controlId)
		if controlId == 500: #Songs
			self.result = {'type': 'song', 'query': self.getControl(500).getSelectedItem().getLabel()}
			self.close()
		elif controlId == 501: #Artists
			self.result = {'type': 'artist', 'query': self.getControl(501).getSelectedItem().getLabel()}
			self.close()
		elif controlId == 502: #Albums
			self.result = {'type': 'album', 'query': self.getControl(502).getSelectedItem().getLabel()}
			self.close()
		else:
			pass

	def onFocus(self, controlId):
		print 'onFocus: ' + str(controlId)
		pass

	def showKeyboard(self):
		keyboard = xbmc.Keyboard(self.query, __language__(1000))
		path = os.path.join(os.getcwd(), 'resources', 'lib')
		g = getTextThread(keyboard, path, self.showResults)
		g.start()
		keyboard.doModal()
		g.closeThread()
		if keyboard.isConfirmed():
			ret = keyboard.getText()
			self.result = {'type': 'all', 'query': ret}
			self.close()
		else:
			self.query = keyboard.getText()
			if self.query != '':
				self.getControl(1000).setLabel(__language__(3051) + ' "' + self.query + '"')
			else:
				self.close()
	
	def getResult(self):
		return self.result

	def showResults(self, songs, artists, albums):
		self.getControl(500).reset()
		self.getControl(500).addItems(songs)

		self.getControl(501).reset()
		self.getControl(501).addItems(artists)

		self.getControl(502).reset()
		self.getControl(502).addItems(albums)

class Search(object):
	def __init__(self):
		if __isXbox__ == False:
			w = SearchXml("search.xml", os.getcwd(), "DefaultSkin")
			w.doModal()
			self.result = w.getResult()
			del w
		else:
			keyboard = xbmc.Keyboard('',__language__(1000))
			keyboard.doModal()
			if keyboard.isConfirmed():
				ret = keyboard.getText()
				self.result = {'type': 'all', 'query': ret}
			else:
				self.result = None
	
	def getResult(self):
		return self.result
