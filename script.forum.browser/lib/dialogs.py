import os, sys, re, fnmatch, binascii, xbmc, xbmcgui
import util

DEBUG = None
CACHE_PATH = None

ACTION_MOVE_LEFT      = 1
ACTION_MOVE_RIGHT     = 2
ACTION_MOVE_UP        = 3
ACTION_MOVE_DOWN      = 4
ACTION_PAGE_UP        = 5
ACTION_PAGE_DOWN      = 6
ACTION_SELECT_ITEM    = 7
ACTION_HIGHLIGHT_ITEM = 8
ACTION_PARENT_DIR     = 9
ACTION_PARENT_DIR2	  = 92
ACTION_PREVIOUS_MENU  = 10
ACTION_SHOW_INFO      = 11
ACTION_PAUSE          = 12
ACTION_STOP           = 13
ACTION_NEXT_ITEM      = 14
ACTION_PREV_ITEM      = 15
ACTION_SHOW_GUI       = 18
ACTION_PLAYER_PLAY    = 79
ACTION_MOUSE_LEFT_CLICK = 100
ACTION_CONTEXT_MENU   = 117

def clearDirFiles(filepath):
	if not os.path.exists(filepath): return
	for f in os.listdir(filepath):
		f = os.path.join(filepath,f)
		if os.path.isfile(f): os.remove(f)
				
def doKeyboard(prompt,default='',hidden=False,mod=False):
	if mod: xbmcgui.Window(10000).setProperty('ForumBrowser_modKeyboard','1') #I set the home window, because that's the only way I know to get it to work before the window displays
	keyboard = xbmc.Keyboard(default,prompt)
	keyboard.setHiddenInput(hidden)
	keyboard.doModal()
	xbmcgui.Window(10000).setProperty('ForumBrowser_modKeyboard','0') #I set the home window, because that's the only way I know to get it to work before the window displays
	if not keyboard.isConfirmed(): return None
	return keyboard.getText()

def openWindow(windowClass,xmlFilename,return_window=False,modal=True,theme=None,*args,**kwargs):
	xbmcgui.Window(10000).setProperty('ForumBrowser_hidePNP',util.getSetting('hide_pnp',False) and '1' or '0') #I set the home window, because that's the only way I know to get it to work before the window displays
	theme = theme or sys.modules["__main__"].THEME
	path = util.__addon__.getAddonInfo('path')
	src = os.path.join(path,'resources','skins',theme,'720p',xmlFilename)
	if not os.path.exists(src): theme = 'Default'
	if not util.getSetting('use_skin_mods',True):
		src = os.path.join(path,'resources','skins',theme,'720p',xmlFilename)
		#path = util.util.__addon__.getAddonInfo('profile')
		skin = os.path.join(xbmc.translatePath(path),'resources','skins',theme,'720p')
		#if not os.path.exists(skin): os.makedirs(skin)
		xml = open(src,'r').read()
		xmlFilename = 'script-forumbrowser-current.xml'
		open(os.path.join(skin,xmlFilename),'w').write(xml.replace('ForumBrowser-font','font'))
	w = windowClass(xmlFilename,path,theme,*args,**kwargs)
	if modal:
		w.doModal()
	else:
		w.show()
	if return_window: return w
	del w
	return None

def showMessage(caption,text,text2='',text3='',error=False,success=None,scroll=False):
	if text2: text += '[CR]' + text2
	if text3: text += '[CR]' + text3
	w = MessageDialog('script-forumbrowser-message-dialog.xml' ,xbmc.translatePath(util.__addon__.getAddonInfo('path')),'Default',caption=caption,text=text,error=error,success=success,scroll=scroll)
	if util.getSetting('video_pause_on_dialog',True): sys.modules["__main__"].PLAYER.pauseStack()
	w.doModal()
	del w
	if util.getSetting('video_pause_on_dialog',True): sys.modules["__main__"].PLAYER.resumeStack()

def showMessageSilent(caption,text,text2='',text3='',error=False,success=None,scroll=False): pass

def loadHelp(helpfile,as_list=False):
	lang = xbmc.getLanguage().split(' ',1)[0]
	addonPath = xbmc.translatePath(util.__addon__.getAddonInfo('path'))
	helpfilefull = os.path.join(addonPath,'resources','language',lang,helpfile)
	if not os.path.exists(helpfilefull):
		helpfilefull = os.path.join(addonPath,'resources','language','English',helpfile)
	if not os.path.exists(helpfilefull): return {}
	data = open(helpfilefull,'r').read()
	items = data.split('\n@item:')
	caption = items.pop(0)
	if as_list:
		ret = []
		for i in items:
			if not i: continue
			key, val = i.split('\n',1)
			name = ''
			if '=' in key: key,name = key.split('=')
			ret.append({'id':key,'name':name,'help':val})
		return caption,ret
	else:
		ret = {}
		for i in items:
			if not i: continue
			key, val = i.split('\n',1)
			name = ''
			if '=' in key: key,name = key.split('=')
			ret[key] = val
			if name: ret[key + '.name'] = name
		return ret

def showText(caption,text,text_is_file=False):
	if text_is_file:
		lang = xbmc.getLanguage().split(' ',1)[0]
		addonPath = xbmc.translatePath(util.__addon__.getAddonInfo('path'))
		textfilefull = os.path.join(addonPath,'resources','language',lang,text)
		if not os.path.exists(textfilefull):
			textfilefull = os.path.join(addonPath,'resources','language','English',text)
		if not os.path.exists(textfilefull): return None
		f = open(textfilefull,'r')
		text = f.read()
		f.close()
	openWindow(TextDialog,'script-forumbrowser-text-dialog.xml',theme='Default',caption=caption,text=text)
	
def showHelp(helptype):
	helptype += '.help'
	caption, helplist = loadHelp(helptype,True)
	dialog = OptionsChoiceMenu(caption)
	for h in helplist:
		if h['id'] == 'sep':
			dialog.addSep()
		else:
			dialog.addItem(h['id'],h['name'],'forum-browser-info.png',h['help'])
	result = dialog.getResult()
	if result == 'changelog':
		addonPath = xbmc.translatePath(util.__addon__.getAddonInfo('path'))
		changelogPath = os.path.join(addonPath,'changelog.txt')
		showText('Changelog',open(changelogPath,'r').read())

def showInfo(infotype):
	infotype += '.info'
	lang = xbmc.getLanguage().split(' ',1)[0]
	addonPath = xbmc.translatePath(util.__addon__.getAddonInfo('path'))
	infofilefull = os.path.join(addonPath,'resources','language',lang,infotype)
	if not os.path.exists(infofilefull):
		infofilefull = os.path.join(addonPath,'resources','language','English',infotype)
	if not os.path.exists(infofilefull): return None
	showText('Info',open(infofilefull,'r').read())
	
class MessageDialog(xbmcgui.WindowXMLDialog):
	def __init__( self, *args, **kwargs ):
		self.text = kwargs.get('text') or ''
		self.caption = kwargs.get('caption') or ''
		self.error = kwargs.get('error')
		self.success = kwargs.get('success')
		self.scroll = kwargs.get('scroll')
		self.started = False
		xbmcgui.WindowXMLDialog.__init__( self )
	
	def onInit(self):
		if self.started: return
		self.started = True
		self.getControl(104).setLabel(self.caption)
		textbox = self.getControl(122)
		textbox.reset()
		textbox.setText(self.text)
		if self.error:
			self.getControl(250).setColorDiffuse('FFFF0000')
		elif self.success is not None:
			if self.success:
				self.getControl(250).setColorDiffuse('FF009900')
			else:
				self.getControl(250).setColorDiffuse('FF999900')
		if self.scroll and not util.getSetting('message_dialog_always_show_ok',False):
			self.getControl(112).setVisible(False)
			self.setFocusId(123)
		else:
			self.setFocusId(111)
		
	def onAction(self,action):
		if action == 92 or action == 10:
			self.close()
		
	def onFocus( self, controlId ): self.controlId = controlId

class TextDialog(xbmcgui.WindowXMLDialog):
	def __init__( self, *args, **kwargs ):
		self.text = kwargs.get('text') or ''
		self.caption = kwargs.get('caption') or ''
		xbmcgui.WindowXMLDialog.__init__( self )
	
	def onInit(self):
		self.getControl(104).setLabel(self.caption)
		textbox = self.getControl(122)
		textbox.reset()
		textbox.setText(self.text)
		
	def onAction(self,action):
		if action == 92 or action == 10:
			self.close()
		
	def onFocus( self, controlId ): self.controlId = controlId
	
class ImageChoiceDialog(xbmcgui.WindowXMLDialog):
	def __init__( self, *args, **kwargs ):
		self.result = None
		self.items = kwargs.get('items')
		self.caption = kwargs.get('caption')
		self.select = kwargs.get('select')
		self.menu = kwargs.get('menu')
		self.filtering = kwargs.get('filtering',False)
		self.keepColors = kwargs.get('keep_colors',False)
		self.terms = ''
		self.filter = None
		self.filterType = 'terms'
		self.started = False
		self.gifReplace = chr(255)*6
		self.colorsDir = os.path.join(CACHE_PATH,'colors')
		self.colorGif = os.path.join(xbmc.translatePath(util.__addon__.getAddonInfo('path')),'resources','media','white1px.gif')
		xbmcgui.WindowXMLDialog.__init__( self )
	
	def onInit(self):
		if self.started: return
		self.started = True
		self.showItems()
		
	def showItems(self):
		clist = self.getControl(120)
		clist.reset()
		colors = {}
		if not os.path.exists(self.colorsDir): os.makedirs(self.colorsDir)
		
		for i in self.items:
			if self.filter:
				text = i['disp'] + ' ' + i['disp2']
				if self.filterType == 'terms':
					matched = False
					text = (i['disp'] + ' ' + i['disp2']).lower()
					for f in self.filter:
						if not f.search(text):
							break
					else:
						matched = True
						
					if not matched: continue
				else:
					if not fnmatch.fnmatch(text.lower(), self.filter): continue
					
			item = xbmcgui.ListItem(label=i['disp'],label2=i['disp2'],thumbnailImage=i['icon'])
			if i['sep']: item.setProperty('SEPARATOR','SEPARATOR')
			item.setProperty('bgcolor',i['bgcolor'])
			item.setProperty('disabled',str(bool(i['disabled'])))
			color = i['bgcolor'].upper()[2:]
			if color in colors:
				path = colors[color]
			else:
				path = self.makeColorFile(color, self.colorsDir)
				colors[color] = path
			item.setProperty('bgfile',path)
			for k,v in i.get('extras',{}).items():
				item.setProperty(k,v)
			clist.addItem(item)
		self.getControl(300).setLabel('[B]%s[/B]' % self.caption)
		self.setFocus(clist)
		if self.select:
			idx=0
			for i in self.items:
				if i['id'] == self.select:
					clist.selectItem(idx)
					break
				idx+=1
		
	def doFilter(self):
		self.getControl(199).setVisible(False)
		try:
			terms = doKeyboard(util.T(32517),self.terms)
			self.terms = terms or ''
			if '*' in terms or '?' in terms:
				self.filter = terms.lower()
				self.filterType = 'wild'
			else:
				terms = terms.strip().split()
				self.filter = []
				for t in terms: self.filter.append(re.compile(r'\b%s\b' % t,re.I))
				self.filterType = 'terms'
				
			self.showItems()
		except:
			util.ERROR('Error handling search terms')
		finally:
			self.getControl(199).setVisible(True)
	
	def makeColorFile(self,color,path):
		try:
			replace = binascii.unhexlify(color)
		except:
			replace = chr(255)
		replace += replace
		target = os.path.join(path,color + '.gif')
		open(target,'w').write(open(self.colorGif,'r').read().replace(self.gifReplace,replace))
		return target
		
	def onAction(self,action):
		if action == 92 or action == 10:
			self.doClose()
		elif action == 7:
			self.finish()
		elif action == ACTION_CONTEXT_MENU:
			self.doMenu()
	
	def doClose(self):
		if not self.keepColors: clearDirFiles(self.colorsDir)
		self.close()
		
	def onClick( self, controlID ):
		if controlID == 120:
			self.finish()
		
	def doMenu(self):
		if self.menu.contextCallback:
			pos = self.getControl(120).getSelectedPosition()
			if pos < 0: return
			if self.menu.closeContext: self.close()
			self.menu.contextCallback(self,self.items[pos])
		elif self.filtering:
			self.doFilter()
			
	def finish(self):
		item = self.getControl(120).getSelectedItem()
		if item and item.getProperty('disabled') == 'True': return
		self.result = self.getControl(120).getSelectedPosition()
		self.doClose()
		
	def onFocus( self, controlId ): self.controlId = controlId
		
class ActivitySplashWindow(xbmcgui.WindowXMLDialog):
	def __init__( self, *args, **kwargs ):
		self.caption = kwargs.get('caption')
		self.cancelStopsConnections = kwargs.get('cancel_stops_connections')
		self.modal_callback = kwargs.get('modal_callback')
		self.canceled = False
		xbmcgui.WindowXMLDialog.__init__(self)
		
	def onInit(self):
		self.getControl(100).setLabel(self.caption)
		if self.modal_callback:
			callback, args, kwargs = self.modal_callback
			args = args or []
			kwargs = kwargs = {} 
			callback(self,*args,**kwargs)
		
	def update(self,message):
		self.getControl(100).setLabel(message)
		return not self.canceled
		
	def onAction(self,action):
		print 'TEST'
		if action == ACTION_PARENT_DIR or action == ACTION_PARENT_DIR2: action = ACTION_PREVIOUS_MENU
		if action == ACTION_PREVIOUS_MENU:
			self.cancel()
			
	def cancel(self):
		self.canceled = True
		if self.cancelStopsConnections:
			from lib import asyncconnections
			asyncconnections.StopConnection()
	
	def onClick(self,controlID):
		if controlID == 200:
			self.cancel()
	
class ActivitySplash():
	def __init__(self,caption='',cancel_stops_connections=False,modal_callback=None):
		self.splash = openWindow(ActivitySplashWindow,'script-forumbrowser-loading-splash.xml',return_window=True,modal=bool(modal_callback),theme='Default',caption=caption,cancel_stops_connections=cancel_stops_connections,modal_callback=modal_callback)
		self.splash.show()
		
	def update(self,pct,message):
		self.splash.update(message)

	def close(self):
		if not self.splash: return
		self.splash.close()
		del self.splash
		self.splash = None

class FakeActivitySplash():
	def __init__(self,caption=''):
		pass
		
	def update(self,pct,message):
		pass

	def close(self):
		pass
		
def showActivitySplash(caption=util.T(32248),cancel_stops_connections=False,modal_callback=None):
	if util.getSetting('hide_activity_splash',False):
		s = FakeActivitySplash(caption)
	else:
		s = ActivitySplash(caption,cancel_stops_connections=cancel_stops_connections,modal_callback=modal_callback)
	s.update(0,caption)
	return s
	
class ChoiceMenu():
	def __init__(self,caption,with_splash=False):
		self.caption = caption
		self.items = []
		self.splash = None
		self.contextCallback = None
		self.closeContext = True
		if with_splash: self.showSplash()
		
	def setContextCallback(self,callback):
		self.contextCallback = callback
		
	def isEmpty(self):
		return not self.items
	
	def showSplash(self):
		self.splash = showActivitySplash()
		
	def hideSplash(self):
		if not self.splash: return
		self.splash.close()
		
	def cancel(self):
		self.hideSplash()
		
	def addItem(self,ID,display,icon='',display2='',sep=False,disabled=False,bgcolor='FFFFFFFF',**kwargs):
		if not ID: return self.addSep()
		if disabled:
			display = "[COLOR FF444444]%s[/COLOR]" % display
			display2 = "[B]DISABLED[/B][CR][CR][COLOR FF444444]%s[/COLOR]" % display2
		self.items.append({'id':ID,'disp':display,'disp2':display2,'icon':icon,'sep':sep,'disabled':disabled,'bgcolor':bgcolor,'extras':kwargs})
		
	def addSep(self):
		if self.items: self.items[-1]['sep'] = True
	
	def getChoiceIndex(self):
		options = []
		for i in self.items: options.append(i.get('disp'))
		return xbmcgui.Dialog().select(self.caption,options)
	
	def getResult(self,close_on_context=True):
		self.closeContext = close_on_context
		self.hideSplash()
		if util.getSetting('video_pause_on_dialog',True): sys.modules["__main__"].PLAYER.pauseStack()
		idx = self.getChoiceIndex()
		if util.getSetting('video_pause_on_dialog',True): sys.modules["__main__"].PLAYER.resumeStack()
		if idx < 0: return None
		if self.items[idx]['disabled']: return None
		return self.items[idx]['id']

def dialogSelect(heading,ilist,autoclose=0):
	if util.getSetting('video_pause_on_dialog',True): sys.modules["__main__"].PLAYER.pauseStack()
	result =  xbmcgui.Dialog().select(heading,ilist,autoclose)
	if util.getSetting('video_pause_on_dialog',True): sys.modules["__main__"].PLAYER.resumeStack()
	return result
	
class OptionsChoiceMenu(ChoiceMenu):
	def getResult(self,windowFile='script-forumbrowser-options-dialog.xml',select=None,close_on_context=True):
		self.closeContext = close_on_context
		if util.getSetting('video_pause_on_dialog',True): sys.modules["__main__"].PLAYER.pauseStack()
		w = openWindow(ImageChoiceDialog,windowFile,return_window=True,theme='Default',menu=self,items=self.items,caption=self.caption,select=select)
		if util.getSetting('video_pause_on_dialog',True): sys.modules["__main__"].PLAYER.resumeStack()
		result = w.result
		del w
		if result == None: return None
		if self.items[result]['disabled']: return None
		return self.items[result]['id']
		
class ImageChoiceMenu(ChoiceMenu):
	def getResult(self,windowFile='script-forumbrowser-image-dialog.xml',select=None,filtering=False,keep_colors=False):
		if util.getSetting('video_pause_on_dialog',True): sys.modules["__main__"].PLAYER.pauseStack()
		w = openWindow(ImageChoiceDialog,windowFile ,return_window=True,theme='Default',menu=self,items=self.items,caption=self.caption,select=select,filtering=filtering,keep_colors=keep_colors)
		if util.getSetting('video_pause_on_dialog',True): sys.modules["__main__"].PLAYER.resumeStack()
		result = w.result
		del w
		if result == None: return None
		return self.items[result]['id']

def getHexColor(hexc=None):
	hexc = doKeyboard(util.T(32475),default=hexc)
	if not hexc: return None
	while len(hexc) != 6 or re.search('[^1234567890abcdef](?i)',hexc):
		showMessage(util.T(32050),util.T(32474))
		hexc = doKeyboard(util.T(32475),default=hexc)
		if not hexc: return None
	return hexc

class ColorDialog(xbmcgui.WindowXMLDialog):
	def __init__( self, *args, **kwargs ):
		self.image = kwargs.get('image')
		self.hexc = kwargs.get('hexcolor','FFFFFF') or 'FFFFFF'
		self.r = 127
		self.g = 127
		self.b = 127
		self.closed = False
		xbmcgui.WindowXMLDialog.__init__( self )
		
	def onInit(self):
		if self.image: self.getControl(300).setImage(self.image)
		self.setHexColor(self.hexc)
		self.showColor()
		
	def onClick(self,controlID):
		if   controlID == 150: self.changeR(-1)
		elif controlID == 151: self.changeR(1)
		elif controlID == 152: self.changeG(-1)
		elif controlID == 153: self.changeG(1)
		elif controlID == 154: self.changeB(-1)
		elif controlID == 155: self.changeB(1)
		elif controlID == 156: self.changeAll(-1)
		elif controlID == 157: self.changeAll(1)
		elif controlID == 158: self.setHexColor()
		elif controlID == 170: self.setHexColor('FFFFFF')
		elif controlID == 171: self.setHexColor('000000')
		elif controlID == 172: self.setHexColor('7E7E7E')
		elif controlID == 173: self.setHexColor('FF0000')
		elif controlID == 174: self.setHexColor('00FF00')
		elif controlID == 175: self.setHexColor('0000FF')
		elif controlID == 111: return self.close()
		
		#print str(self.r) + ' ' +str(self.g) + ' ' +str(self.b)
		self.showColor()
		
	def showColor(self):
		hexR = binascii.hexlify(chr(self.r)).upper()
		hexG = binascii.hexlify(chr(self.g)).upper()
		hexB = binascii.hexlify(chr(self.b)).upper()
		hexc = hexR+hexG+hexB
		self.getControl(160).setColorDiffuse('FF' + hexc)
		self.getControl(200).setLabel(str(self.r))
		self.getControl(201).setLabel(hexR)
		self.getControl(202).setLabel(str(self.g))
		self.getControl(203).setLabel(hexG)
		self.getControl(204).setLabel(str(self.b))
		self.getControl(205).setLabel(hexB)
		self.getControl(158).setLabel('#'+hexc)
		
	def changeR(self,mod):
		self.r += mod
		if self.r < 0: self.r = 255
		elif self.r > 255: self.r = 0
		
	def changeG(self,mod):
		self.g += mod
		if self.g < 0: self.g = 255
		elif self.g > 255: self.g = 0
		
	def changeB(self,mod):
		self.b += mod
		if self.b < 0: self.b = 255
		elif self.b > 255: self.b = 0
		
	def changeAll(self,mod):
		self.r += mod
		if self.r < 0: self.r = 0
		elif self.r > 255: self.r = 255
		self.g += mod
		if self.g < 0: self.g = 0
		elif self.g > 255: self.g = 255
		self.b += mod
		if self.b < 0: self.b = 0
		elif self.b > 255: self.b = 255
		
	def setHexColor(self,hexc=None):
		if not hexc: hexc = getHexColor(self.hexValue())
		if not hexc: return
		self.r = int(hexc[:2],16)
		self.g = int(hexc[2:4],16)
		self.b = int(hexc[4:],16)
		self.showColor()
		
	def hexValue(self):
		if self.closed: return None
		hexR = binascii.hexlify(chr(self.r)).upper()
		hexG = binascii.hexlify(chr(self.g)).upper()
		hexB = binascii.hexlify(chr(self.b)).upper()
		hexc = hexR+hexG+hexB
		return hexc
		
	def onAction(self,action):
		if action == 92 or action == 10:
			self.closed = True
			self.close()