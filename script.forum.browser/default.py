# -*- coding: utf-8 -*-

import urllib2, re, os, sys, time, urlparse, binascii, math
import xbmc, xbmcgui #@UnresolvedImport
from distutils.version import StrictVersion
from lib import util, signals, asyncconnections
from lib.util import LOG, ERROR, getSetting, setSetting
from lib.xbmcconstants import * # @UnusedWildImport

try:
	from webviewer import webviewer #@UnresolvedImport
	print 'FORUMBROWSER: WEB VIEWER IMPORTED'
except:
	import traceback
	traceback.print_exc()
	print 'FORUMBROWSER: COULD NOT IMPORT WEB VIEWER'

'''
TODO:

Read/Delete PM's in xbmc4xbox.org

'''

__plugin__ = 'Forum Browser'
__author__ = 'ruuk (Rick Phillips)'
__url__ = 'http://code.google.com/p/forumbrowserxbmc/'
__date__ = '1-28-2013'
__version__ = util.__addon__.getAddonInfo('version')
T = util.T

THEME = util.getSavedTheme()


PLAYER = None
SIGNALHUB = None

MEDIA_PATH = xbmc.translatePath(os.path.join(util.__addon__.getAddonInfo('path'),'resources','skins','Default','media'))
FORUMS_STATIC_PATH = xbmc.translatePath(os.path.join(util.__addon__.getAddonInfo('path'),'forums'))
FORUMS_PATH = xbmc.translatePath(os.path.join(util.__addon__.getAddonInfo('profile'),'forums'))
FORUMS_SETTINGS_PATH = xbmc.translatePath(os.path.join(util.__addon__.getAddonInfo('profile'),'forums_settings'))
CACHE_PATH = xbmc.translatePath(os.path.join(util.__addon__.getAddonInfo('profile'),'cache'))
if not os.path.exists(FORUMS_PATH): os.makedirs(FORUMS_PATH)
if not os.path.exists(FORUMS_SETTINGS_PATH): os.makedirs(FORUMS_SETTINGS_PATH)
if not os.path.exists(CACHE_PATH): os.makedirs(CACHE_PATH)


STARTFORUM = None

LOG('Version: ' + __version__)
LOG('Python Version: ' + sys.version)
DEBUG = getSetting('debug') == 'true'
if DEBUG: LOG('DEBUG LOGGING ON')
LOG('Skin: ' + THEME)

CLIPBOARD = None
try:
	import SSClipboard #@UnresolvedImport
	CLIPBOARD = SSClipboard.Clipboard()
	LOG('Clipboard Enabled')
except:
	LOG('Clipboard Disabled: No SSClipboard')
	
FB = None

from lib.forumbrowser import forumbrowser
from lib.forumbrowser import texttransform
from lib.crypto import passmanager
from lib.forumbrowser import tapatalk
from webviewer import video #@UnresolvedImport
from lib import dialogs, windows, mods

signals.DEBUG = DEBUG

dialogs.CACHE_PATH = CACHE_PATH
dialogs.DEBUG = DEBUG

mods.CACHE_PATH = CACHE_PATH
mods.DEBUG = DEBUG

video.LOG = LOG
video.ERROR = ERROR

asyncconnections.LOG = LOG
asyncconnections.setEnabled(not getSetting('disable_async_connections',False))

######################################################################################
#
# Image Dialog
#
######################################################################################
class ImagesDialog(windows.BaseWindowDialog):
	def __init__( self, *args, **kwargs ):
		self.images = kwargs.get('images')
		self.index = 0
		windows.BaseWindowDialog.__init__( self, *args, **kwargs )
	
	def onInit(self):
		windows.BaseWindowDialog.onInit(self)
		self.getControl(200).setEnabled(len(self.images) > 1)
		self.getControl(202).setEnabled(len(self.images) > 1)
		self.showImage()

	def onFocus( self, controlId ):
		self.controlId = controlId
		
	def showImage(self):
		if not self.images: return
		self.getControl(102).setImage(self.images[self.index])
		
	def nextImage(self):
		self.index += 1
		if self.index >= len(self.images): self.index = 0
		self.showImage()
		
	def prevImage(self):
		self.index -= 1
		if self.index < 0: self.index = len(self.images) - 1
		self.showImage()
	
	def onClick( self, controlID ):
		if windows.BaseWindow.onClick(self, controlID): return
		if controlID == 200:
			self.nextImage()
		elif controlID == 202:
			self.prevImage()
	
	def onAction(self,action):
		if action == ACTION_PARENT_DIR or action == ACTION_PARENT_DIR2:
			action = ACTION_PREVIOUS_MENU
		elif action == ACTION_NEXT_ITEM or action == ACTION_MOVE_RIGHT:
			self.nextImage()
			self.setFocusId(202)
		elif action == ACTION_PREV_ITEM or action == ACTION_MOVE_LEFT:
			self.prevImage()
			self.setFocusId(200)
		elif action == ACTION_CONTEXT_MENU:
			self.doMenu()
		windows.BaseWindowDialog.onAction(self,action)
		
	def doMenu(self):
		d = dialogs.ChoiceMenu(T(32051))
		d.addItem('save', T(32129))
		d.addItem('help',T(32244))
		result = d.getResult()
		if not result: return
		if result == 'save':
			self.saveImage()
		elif result == 'help':
			dialogs.showHelp('imageviewer')
			
	def downloadImage(self,url):
		base = xbmc.translatePath(os.path.join(util.__addon__.getAddonInfo('profile'),'slideshow'))
		if not os.path.exists(base): os.makedirs(base)
		clearDirFiles(base)
		return Downloader(message=T(32148)).downloadURLs(base,[url],'.jpg')
		
	def saveImage(self):
		#browse(type, heading, shares[, mask, useThumbs, treatAsFolder, default])
		source = self.images[self.index]
		firstfname = os.path.basename(source)
		if source.startswith('http'):
			result = self.downloadImage(source)
			if not result:
				dialogs.showMessage(T(32257),T(32258),success=False)
				return
			source = result[0]
		filename = dialogs.doKeyboard(T(32259), firstfname)
		if filename == None: return
		default = getSetting('last_download_path') or ''
		result = xbmcgui.Dialog().browse(3,T(32260),'files','',False,True,default)
		setSetting('last_download_path',result)
		if not os.path.exists(source): return
		target = os.path.join(result,filename)
		ct = 1
		original = filename
		while os.path.exists(target):
			fname, ext = os.path.splitext(original)
			filename = fname + '_' + str(ct) + ext
			ct+=1
			if os.path.exists(os.path.join(result,filename)): continue
			yes = dialogs.dialogYesNo(T(32261),T(32262),T(32263),filename + '?',T(32264),T(32265))
			if not yes:
				ct = 0
				filename = dialogs.doKeyboard(T(32259), filename)
				original = filename
				if filename == None: return
			target = os.path.join(result,filename)
		import shutil
		shutil.copy(source, target)
		dialogs.showMessage(T(32266),T(32267),os.path.basename(target),success=True)

######################################################################################
#
# Forum Settings Dialog
#
######################################################################################
class ForumSettingsDialog(windows.BaseWindowDialog):
	def __init__( self, *args, **kwargs ):
		self.colorsDir = os.path.join(CACHE_PATH,'colors')
		self.colorGif = os.path.join(xbmc.translatePath(util.__addon__.getAddonInfo('path')),'resources','media','white1px.gif')
		self.gifReplace = chr(255)*6
		self.items = []
		self.data = {}
		self.help = {}
		self.helpSep = FB.MC.hrReplace
		self.header = ''
		self.headerColor = ''
		self.settingsChanged = False
		self.OK = False
		windows.BaseWindowDialog.__init__( self, *args, **kwargs )
		
	def setHeader(self,header):
		self.header = header
		
	def onInit(self):
		self.getControl(250).setLabel('[B]%s[/B]' % self.header)
		self.fillList()
		self.setFocusId(320)
		
	def setHelp(self,hlp):
		self.help = hlp
		
	def addItem(self,sid,name,value,vtype):
		valueDisplay = str(value)
		if vtype == 'text.password': valueDisplay = len(valueDisplay) * '*'
		elif vtype == 'boolean': valueDisplay = value and 'booleanTrue' or 'booleanFalse'
		elif vtype.startswith('color.'):
			valueDisplay = self.makeColorFile(value.upper())
			self.headerColor = valueDisplay
		item = xbmcgui.ListItem(name,valueDisplay)
		item.setProperty('value_type',vtype.split('.',1)[0])
		item.setProperty('value',str(value))
		item.setProperty('id',sid)
		if vtype == 'text.long':
			item.setProperty('help',self.help.get(sid,'') + '[CR][COLOR FF999999]%s[/COLOR][CR][B]Current:[/B][CR][CR]%s' % (self.helpSep,valueDisplay))
		else:
			item.setProperty('help',self.help.get(sid,''))
		self.items.append(item)
		self.data[sid] = {'name':name, 'value':value, 'type':vtype}
	
	def addSep(self):
		if len(self.items) > 0: self.items[-1].setProperty('separator','separator')
			
	def fillList(self):
		for i in self.items:
			if i.getProperty('id') == 'logo': i.setProperty('header_color', str(self.headerColor))
		self.getControl(320).addItems(self.items)
		
	def onClick(self,controlID):
		if controlID == 320:
			self.editSetting()		
		elif controlID == 100:
			self.OK = True
			self.doClose()
		elif controlID == 101:
			self.cancel()
		
	def onAction(self,action):
		if action == ACTION_PARENT_DIR or action == ACTION_PARENT_DIR2:
			action = ACTION_PREVIOUS_MENU
		if action == ACTION_PREVIOUS_MENU:
			self.cancel()
		
	def cancel(self):
		if self.settingsChanged:
			yes = dialogs.dialogYesNo(T(32268),T(32269),T(32270))
			if not yes: return
		self.doClose()
		
	def editSetting(self):
		item = self.getControl(320).getSelectedItem()
		if not item: return
		dID = item.getProperty('id')
		data = self.data.get(dID)
		value = data['value']
		self.doEditSetting(dID,item,data)
		if value != data['value']: self.settingsChanged = True
		
	def doEditSetting(self,dID,item,data):
		if not data:
			LOG('ERROR GETTING FORUM SETTING FROM LISTITEM')
			return
		if data['type'] == 'boolean':
			data['value'] = not data['value']
			item.setLabel2(data['value'] and 'booleanTrue' or 'booleanFalse')
		elif data['type'].startswith('text'):
			if data['type'] == 'text.long':
				val = dialogs.doKeyboard(T(32271),data['value'],mod=True)
				item.setProperty('help',self.help.get(dID,'') + '[CR][COLOR FF999999]%s[/COLOR][CR][B]Current:[/B][CR][CR]%s' % (self.helpSep,val))
			elif data['type'].startswith('text.url'):
				if data['value']:
					yes = dialogs.dialogYesNo(T(32272),T(32274),T(32273),'',T(32276),T(32275))
					if yes:
						data['value'] = ''
						item.setLabel2('')
						return
				val = browseWebURL(data['type'].split('.',2)[-1])
			else:
				val = dialogs.doKeyboard(T(32271),data['value'],hidden=data['type']=='text.password')
			if val == None: return
			if not self.validate(val,data['type']): return
			data['value'] = val
			item.setLabel2(data['type'] != 'text.password' and val or len(val) * '*')
		elif data['type'].startswith('webimage.'):
			url = data['type'].split('.',1)[-1]
			yes = dialogs.dialogYesNo(T(32272),T(32278),T(32277),'',T(32280),T(32279))
			if yes is None: return
			if yes:
				logo = dialogs.doKeyboard(T(32281),data['value'] or 'http://')
				logo = logo or ''
			else:
				logo = self.getWebImage(url)
				if not logo: return
			data['value'] = logo
			item.setProperty('value',logo)
			self.refreshImage()
		elif data['type'].startswith('color.'):
			forumID = data['type'].split('.',1)[-1]
			color = askColor(forumID,data['value'],logo=(self.data.get('logo') or {}).get('value'))
			if not color: return
			data['value'] = color
			colorFile = self.makeColorFile(color)
			item.setLabel2(colorFile)
			self.headerColor = colorFile
			self.updateHeaderColor()
		elif data['type'] == 'function':
			data['value'][0](*data['value'][1:])
		
	def validate(self,val,vtype):
		if vtype == 'text.integer':
			if not val: return True
			try:
				int(val)
			except:
				dialogs.showMessage(T(32282),T(32283))
				return False
		elif vtype == 'text.time':
			if not val: return True
			if val.startswith('-'): val = val[1:]
			if not ':' in val:
				if val.isdigit() and len(val) < 3: return True
			else:
				left, right = val.split(':',1)
				left = left or '00'
				if left.isdigit() and right.isdigit() and len(right) == 2: return True
			dialogs.showMessage(T(32282),T(32284).format('-mmm:ss'))
			return False
		return True
				
	def updateHeaderColor(self):
		clist = self.getControl(320)
		for idx in range(0,clist.size()):
			i = clist.getListItem(idx)
			if i.getProperty('id') == 'logo':
				i.setProperty('header_color', str(self.headerColor))
				self.refreshImage()
				return
			
	def refreshImage(self):
		cid = self.getFocusId()
		if not cid: return
		#self.setFocusId(100)
		self.setFocusId(cid)
		
	def handleXBMCDialogProgress(self,dialog,pct,msg):
		if pct > -1: dialog.update(pct,msg)
		if dialog.iscanceled(): asyncconnections.StopConnection()
		return not dialog.iscanceled()
	
	def getWebImage(self,url):
		d = xbmcgui.DialogProgress()
		d.create(T(32285))
		try:
			info = forumbrowser.HTMLPageInfo(url,progress_callback=(self.handleXBMCDialogProgress,d))
			if d.iscanceled():
				d.close()
				return ''
			domain = url.split('://',1)[-1].split('/',1)[0]
			logo = chooseLogo(domain,info.images(),keep_colors=True,splash=d)
		except util.StopRequestedException:
			return ''
		finally:
			d.close()
		return logo
	
	def makeColorFile(self,color):
		path = self.colorsDir
		try:
			replace = binascii.unhexlify(color)
		except:
			replace = chr(255)
		replace += replace
		target = os.path.join(path,color + '.gif')
		with open(target,'w') as t:
			with open(self.colorGif,'r') as c:
				t.write(c.read().replace(self.gifReplace,replace))
		return target
		
def editForumSettings(forumID):
	w = dialogs.openWindow(ForumSettingsDialog,'script-forumbrowser-forum-settings.xml',return_window=True,modal=False,theme='Default')
	sett,rules = loadForumSettings(forumID,get_both=True) or {'username':'','password':'','notify':False}
	fdata = forumbrowser.ForumData(forumID,FORUMS_PATH)
	w.setHeader(forumID[3:])
	w.setHelp(dialogs.loadHelp('forumsettings.help') or {})
	w.addItem('username',T(32286),sett.get('username',''),'text')
	w.addItem('password',T(32287),sett.get('password',''),'text.password')
	w.addItem('notify',T(32018),sett.get('notify',''),'boolean')
	w.addItem('extras',T(32288),sett.get('extras',''),'text')
	w.addItem('time_offset_hours',T(32289),sett.get('time_offset_hours',''),'text.time')
	w.addSep()
	w.addItem('description',T(32290),fdata.description,'text.long')
	w.addItem('logo',T(32291),fdata.urls.get('logo',''),'webimage.' + fdata.forumURL())
	w.addItem('header_color',T(32292),fdata.theme.get('header_color',''),'color.' + forumID)
	if forumID.startswith('GB.'):
		w.addSep()
		w.addItem('login_url',T(32293),rules.get('login_url',''),'text.url.' + fdata.forumURL())
		w.addItem('rules',T(32294),(manageParserRules,forumID,rules),'function')
	oldLogo = fdata.urls.get('logo','')
	w.doModal()
	if w.OK:
		rules['login_url'] = w.data.get('login_url') and w.data['login_url']['value'] or None
		saveForumSettings(	forumID,
							username=w.data['username']['value'],
							password=w.data['password']['value'],
							notify=w.data['notify']['value'],
							extras=w.data['extras']['value'],
							time_offset_hours=w.data['time_offset_hours']['value'],
							rules=rules)
		fdata.description = w.data['description']['value']
		fdata.urls['logo'] = w.data['logo']['value']
		fdata.theme['header_color'] = w.data['header_color']['value']
		fdata.writeData()
	del w
	if oldLogo != fdata.urls['logo']:
		getCachedLogo(fdata.urls['logo'],forumID,clear=True)
	
######################################################################################
#
# Forums Manager/ Notifications Dialog
#
######################################################################################
class NotificationsDialog(windows.BaseWindowDialog):
	def __init__( self, *args, **kwargs ):
		self.forumsWindow = kwargs.get('forumsWindow')
		self.initialForumID = kwargs.get('forumID')
		self.initialIndex = 0
		self.colorsDir = os.path.join(CACHE_PATH,'colors')
		if not os.path.exists(self.colorsDir): os.makedirs(self.colorsDir)
		self.colorGif = os.path.join(xbmc.translatePath(util.__addon__.getAddonInfo('path')),'resources','media','white1px.gif')
		self.gifReplace = chr(255)*6
		self.items = None
		self.stopTimeout = False
		self.started = False
		self.createItems()
		windows.BaseWindowDialog.__init__( self, *args, **kwargs )
	
	def newPostsCallback(self,signal,data):
		winid = xbmcgui.getCurrentWindowDialogId()
		xbmcgui.Window(winid).setProperty('PulseNotify', '1')
		self.refresh()
		
	def onInit(self):
		if self.started: return
		if SIGNALHUB: SIGNALHUB.registerReceiver('NEW_POSTS', self, self.newPostsCallback)
		self.started = True
		windows.BaseWindowDialog.onInit(self)
		if not self.forumsWindow: self.getControl(250).setLabel(T(32295))
		self.fillList()
		self.startDisplayTimeout()
		if self.items:
			self.setFocusId(220)
		else:
			if self.forumsWindow: self.setFocusId(200)
		
	def onClick( self, controlID ):
		if windows.BaseWindowDialog.onClick(self, controlID): return
		forumID = self.getSelectedForumID()
		if controlID == 220: self.changeForum()
		elif controlID == 200:
			forumID = addForum()
			if forumID: self.refresh(forumID)
		elif controlID == 201:
			forumID = addForumFromOnline(True)
			if forumID: self.refresh(forumID)
		elif controlID == 202:
			if removeForum(forumID): self.refresh()
		elif controlID == 203:
			addFavorite(forumID)
			self.refresh()
		elif controlID == 204:
			removeFavorite(forumID)
			self.refresh()
		elif controlID == 205:
			editForumSettings(forumID)
			item = self.getControl(220).getSelectedItem()
			if not item: return
			ndata = loadForumSettings(forumID) or {}
			item.setProperty('notify',ndata.get('notify') and 'notify' or '')
			
			fdata = forumbrowser.ForumData(forumID,FORUMS_PATH)
			logo = fdata.urls.get('logo','')
			exists, logopath = getCachedLogo(logo,forumID)
			if exists: logo = logopath
			item.setIconImage(logo)
			
			hc = 'FF' + fdata.theme.get('header_color','FFFFFF')
			item.setProperty('bgcolor',hc)
			color = hc.upper()[2:]
			path = self.makeColorFile(color, self.colorsDir)
			item.setProperty('bgfile',path)
			
			self.setFocusId(220)
			
		elif controlID == 207: addCurrentForumToOnlineDatabase(forumID)
		elif controlID == 208: updateThemeODB(forumID)
		elif controlID == 210:
			dialogs.showMessage(str(self.getControl(210).getLabel()),dialogs.loadHelp('options.help').get('help',''))
			
	def onAction(self,action):
		windows.BaseWindowDialog.onAction(self,action)
		self.stopTimeout = True
		if action == ACTION_CONTEXT_MENU:
			focusID = self.getFocusId()
			if focusID == 220:
				self.toggleNotify()
			elif focusID > 199 and focusID < 210:
				helpname = ''
				if focusID  == 200: helpname = 'addforum'
				if focusID  == 201: helpname = 'addonline'
				if focusID  == 202: helpname = 'removeforum'
				if focusID  == 203: helpname = 'addfavorite'
				if focusID  == 204: helpname = 'removefavorite'
				if focusID  == 205: helpname = 'setlogins'
				if focusID  == 206: helpname = 'setcurrentcolor'
				if focusID  == 207: helpname = 'addcurrentonline'
				if focusID  == 208: helpname = 'updatethemeodb'
				if focusID  == 209: helpname = 'parserbrowser'
				dialogs.showMessage(str(self.getControl(focusID).getLabel()),dialogs.loadHelp('options.help').get(helpname,''))

		
	def startDisplayTimeout(self):
		if self.forumsWindow: return
		if getSetting('notify_dialog_close_only_video',True) and not self.isVideoPlaying(): return 
		duration = getSetting('notify_dialog_timout',0)
		if duration:
			xbmc.sleep(1000 * duration)
			if self.stopTimeout and getSetting('notify_dialog_close_activity_stops',True): return
			self.doClose()
	
	def isVideoPlaying(self):
		return xbmc.getCondVisibility('Player.Playing') and xbmc.getCondVisibility('Player.HasVideo')
	
	def toggleNotify(self):
		item = self.getControl(220).getSelectedItem()
		if not item: return
		forumID = item.getProperty('forumID')
		if not forumID: return
		current = toggleNotify(forumID)
		item.setProperty('notify',current and 'notify' or '')
		
	def getSelectedForumID(self):
		item = self.getControl(220).getSelectedItem()
		if not item: return None
		forumID = item.getProperty('forumID')
		return forumID or None
		
	def changeForum(self):
		forumID = self.getSelectedForumID()
		if not forumID: return
		if self.forumsWindow:
			self.forumsWindow.changeForum(forumID)
		else:
			#startForumBrowser(forumID)
			section = ''
			if getSetting('notify_open_subs_pms',True):
				item = self.getControl(220).getSelectedItem()
				if item:
					if getSetting('notify_prefer_subs',False):
						section = item.getProperty('new_subs') and 'SUBSCRIPTIONS' or ''
					if not section: section = item.getProperty('new_PMs') and 'PM' or ''
					if not section: section = item.getProperty('new_subs') and 'SUBSCRIPTIONS' or ''
			furl = util.createForumBrowserURL(forumID,section)
			xbmc.executebuiltin("RunScript(script.forum.browser,%s)" % furl)
		self.doClose()
		
	def createItems(self):
		favs = []
		if not self.forumsWindow and getSetting('notify_dialog_only_enabled'):
			final = getNotifyList()
		else:
			favs = getFavorites()
			flist_tmp = os.listdir(FORUMS_PATH)
			rest = sorted(flist_tmp,key=fidSortFunction)
			if favs:
				for f in favs:
					if f in rest: rest.pop(rest.index(f))
				favs.append('')
			whole = favs + rest
			final = []
			for f in whole:
				if f and not f in final and not f.startswith('.'):
					final.append(f)
		unreadData = self.loadLastData() or {}
		uitems = []
		items = []
		colors = {}
		for f in final:
			flag = False
			path = getForumPath(f,just_path=True)
			unread = unreadData.get(f) or {}
			if not path: continue
			if not os.path.isfile(os.path.join(path,f)): continue
			fdata = forumbrowser.ForumData(f,path)
			ndata = loadForumSettings(f) or {}
			name = fdata.name
			logo = fdata.urls.get('logo','')
			exists, logopath = getCachedLogo(logo,f)
			if exists: logo = logopath
			hc = 'FF' + fdata.theme.get('header_color','FFFFFF')
			item = xbmcgui.ListItem(name,iconImage=logo)
			item.setProperty('bgcolor',hc)
			color = hc.upper()[2:]
			if color in colors:
				path = colors[color]
			else:
				path = self.makeColorFile(color, self.colorsDir)
				colors[color] = path
			if f in favs: item.setProperty('favorite','favorite')
			item.setProperty('bgfile',path)
			item.setProperty('forumID',f)
			item.setProperty('type',f[:2])
			item.setProperty('notify',ndata.get('notify') and 'notify' or '')
			up = unread.get('PM','')
			if up:
				flag = True
				item.setProperty('new_PMs','newpms')
			upms = str(up) or ''
			if 'PM' in unread: del unread['PM']
			uct = unread.values().count(True)
			if uct:
				flag = True
				item.setProperty('new_subs','newsubs')
			usubs = unread and str(uct) or ''
			tsubs = unread and str(len(unread.values())) or ''
			usubs = usubs and '%s/%s' % (usubs,tsubs) or ''
			item.setProperty('unread_subs',usubs)
			item.setProperty('unread_PMs',upms)
			if flag:
				uitems.append(item)
			else:
				items.append(item)
		self.items = uitems + items
		idx = 0
		for item in self.items:
			if item.getProperty('forumID') == self.initialForumID: self.initialIndex = idx
			idx += 1
		
	def fillList(self):
		self.getControl(220).addItems(self.items)
		self.getControl(220).selectItem(self.initialIndex)
		self.initialForumID = None
		self.initialIndex = 0
		
	def refresh(self,forumID=None):
		self.initialForumID = forumID or self.getSelectedForumID()
		self.getControl(220).reset()
		self.createItems()
		self.fillList()
	
	def makeColorFile(self,color,path):
		try:
			replace = binascii.unhexlify(color)
		except:
			replace = chr(255)
		replace += replace
		target = os.path.join(path,color + '.gif')
		open(target,'w').write(open(self.colorGif,'r').read().replace(self.gifReplace,replace))
		return target
	
	def loadLastData(self):
		dataFile = os.path.join(CACHE_PATH,'notifications')
		if not os.path.exists(dataFile): return
		seconds = (getSetting('notify_interval',20) + 5) * 60
		df = open(dataFile,'r')
		lines = df.read()
		df.close()
		try:
			dtime,data = lines.splitlines()
			if time.time() - float(dtime) > seconds: return
			import ast
			return ast.literal_eval(data)
		except:
			ERROR('Failed To Read Data File')

def getNotifyList():
		flist = listForumSettings()
		nlist = []
		for f in flist:
			data = loadForumSettings(f)
			if data:
				if data['notify']: nlist.append(f)
		return nlist
	
######################################################################################
#
# Post Dialog
#
######################################################################################
class PostDialog(windows.BaseWindow):
	failedPM = None
	def __init__( self, *args, **kwargs ):
		self.post = kwargs.get('post')
		self.doNotPost = kwargs.get('donotpost') or False
		self.title = self.post.title
		self.posted = False
		self.moderated = False
		self.display_base = '%s\n \n'
		windows.BaseWindow.__init__( self, *args, **kwargs )
	
	def onInit(self):
		windows.BaseWindow.onInit(self)
		self.getControl(122).setText(' ') #to remove scrollbar
		if self.failedPM:
			if self.failedPM.isPM == self.post.isPM and self.failedPM.tid == self.post.tid and self.failedPM.to == self.post.to:
				yes = dialogs.dialogYesNo(T(32296),T(32297))
				if yes:
					self.post = self.failedPM
					for line in self.post.message.split('\n'): self.addQuote(line)
					self.updatePreview()
					self.setTheme()
					PostDialog.failedPM = None
					return
		if self.post.quote:
			qformat = FB.getQuoteReplace()
			pid = self.post.pid
			if False:
				#This won't work with other formats, need to do this better TODO
				if not pid or self.isPM(): qformat = qformat.replace(';!POSTID!','')
				for line in qformat.replace('!USER!',self.post.quser).replace('!POSTID!',self.post.pid).replace('!QUOTE!',self.post.quote).split('\n'):
					self.addQuote(line)
			else:
				for line in self.post.quote.split('\n'): self.addQuote(line)
		elif self.post.isEdit:
			for line in self.post.message.split('\n'): self.addQuote(line)
				
		self.updatePreview()
		self.setTheme()
		if self.post.moderated:
			self.moderated = True
			dialogs.showMessage(T(32298),T(32299),T(32300))
		if self.isPM() or self.doNotPost: self.setTitle() #We're creating a thread
	
	def setTheme(self):
		self.setProperty('loggedin',FB.isLoggedIn() and 'loggedin' or '')
		if self.isPM():
			self.setProperty('posttype',T(32177))
			self.setProperty('submit_button',T(32178))
		else:
			self.setProperty('posttype',T(32902))
			self.setProperty('submit_button',T(32908))
		self.showTitle(self.post.title)
			
	def showTitle(self,title):
		self.setProperty('title',title or '')
		self.setProperty('toggle_title',title or T(32921))
		
	def onClick( self, controlID ):
		if windows.BaseWindow.onClick(self, controlID): return
		if controlID == 202:
			self.postReply()
		elif controlID == 104:
			self.setTitle()

	def onFocus( self, controlId ):
		self.controlId = controlId
		
	def onAction(self,action):
		if action == ACTION_PREVIOUS_MENU:
			if util.Control.HasFocus(group=196):
				if self.getControl(120).size():
					self.setFocusId(120)
					return
			if not self.confirmExit(): return
		windows.BaseWindow.onAction(self,action)
		
	def confirmExit(self):
		if not self.getOutput() and not self.title: return True
		return dialogs.dialogYesNo(T(32301),T(32302),T(32303))
	
	def isPM(self):
		return str(self.post.pid).startswith('PM') or self.post.to
	
	def getOutput(self): pass
	
	def setTitle(self):
		keyboard = xbmc.Keyboard(self.title,T(32125))
		keyboard.doModal()
		if not keyboard.isConfirmed(): return
		title = keyboard.getText()
		self.showTitle(title)
		self.title = title
	
	def dialogCallback(self,pct,message):
		self.prog.update(pct,message)
		return True
		
	def postReply(self):
		message = self.getOutput()
		self.post.setMessage(self.title,message)
		self.posted = True
		if self.doNotPost:
			self.doClose()
			return
		splash = dialogs.showActivitySplash(T(32126))
		try:
			if self.post.isPM:
				if not FB.doPrivateMessage(self.post,callback=splash.update):
					self.posted = False
					dialogs.showMessage(T(32050),T(32246),' ',self.post.error or '?',success=False)
					return
			else:
				if not FB.post(self.post,callback=splash.update):
					self.posted = False
					dialogs.showMessage(T(32050),T(32227),' ',self.post.error or '?',success=False)
					return
			dialogs.showMessage(T(32304),self.post.isPM and T(32305) or T(32306),' ',str(self.post.successMessage),success=True)
		except:
			self.posted = False
			err = ERROR('Error creating post')
			dialogs.showMessage(T(32050),T(32307),err,error=True)
			PostDialog.failedPM = self.post
		finally:
			splash.close()
		if not self.moderated and self.post.moderated:
			dialogs.showMessage(T(32298),T(32299),T(32300))
		self.doClose()
		
	def parseCodes(self,text):
		return FB.MC.parseCodes(text)
	
	def processQuote(self,m):
		gd = m.groupdict()
		quote = FB.MC.imageFilter.sub(FB.MC.quoteImageReplace,gd.get('quote',''))
		if gd.get('user'):
			ret = FB.MC.quoteReplace % (gd.get('user',''),quote)
		else:
			ret = FB.MC.aQuoteReplace % quote
		return re.sub(FB.getQuoteFormat(),self.processQuote,ret)
	
	def updatePreview(self):
		disp = self.display_base % self.getOutput()
		if FB.browserType == 'ScraperForumBrowser':
			qf = FB.getQuoteFormat()
			if qf: disp = re.sub(qf,self.processQuote,disp)
			disp = self.parseCodes(disp).replace('\n','[CR]')
			disp = re.sub('\[(/?)b\]',r'[\1B]',disp)
			disp = re.sub('\[(/?)i\]',r'[\1I]',disp)
		else:
			disp =  FB.MC.messageToDisplay(disp.replace('\n','[CR]'))
		self.getControl(122).reset()
		self.getControl(122).setText(self.parseCodes(disp).replace('\n','[CR]'))

class LinePostDialog(PostDialog):
	def addQuote(self,quote):
		self.addLine(quote)
		
	def onClick( self, controlID ):
		if controlID == 200:
			self.addLineSingle()
		elif controlID == 201:
			self.addLineMulti()
		elif controlID == 120:
			self.editLine()
		PostDialog.onClick(self, controlID)
			
	def onAction(self,action):
		if action == ACTION_CONTEXT_MENU:
			self.doMenu()
		elif action == ACTION_PARENT_DIR or action == ACTION_PARENT_DIR2:
			action = ACTION_PREVIOUS_MENU
		PostDialog.onAction(self,action)
		
	def doMenu(self):
		d = dialogs.ChoiceMenu(T(32051))
		item = self.getControl(120).getSelectedItem()
		if item:
			d.addItem('addbefore',T(32128))
			d.addItem('delete',T(32122))
			if CLIPBOARD and CLIPBOARD.hasData(('link','image','video')):
				d.addItem('pastebefore',T(32308) + ' %s' % CLIPBOARD.hasData().title())
		if CLIPBOARD and CLIPBOARD.hasData(('link','image','video')):
			d.addItem('paste',T(32309) + ' %s' % CLIPBOARD.hasData().title())
		d.addItem('help',T(32244))
		result = d.getResult()
		if result == 'addbefore': self.addLineSingle(before=True)
		elif result == 'delete': self.deleteLine()
		elif result == 'paste': self.paste()
		elif result == 'pastebefore': self.paste(before=True)
		elif result == 'help': dialogs.showHelp('editor')
		
	def paste(self,before=False):
		share = CLIPBOARD.getClipboard()
		if share.shareType == 'link':
			text = dialogs.doKeyboard(T(32310),mod=True)
			if not text: text = share.page
			paste = '[url=%s]%s[/url]' % (share.page,text)
		elif share.shareType == 'image':
			paste = '[img]%s[/img]' % share.url
		elif share.shareType == 'video':
			source = video.WebVideo().getVideoObject(share.page).sourceName.lower()
			paste = '[video=%s]%s[/video]' % (source,share.page)
			
		if before:
			self.addLineSingle(paste,True,False)
		else:
			self.addLine(paste)
		self.updatePreview()
			
	def getOutput(self):
		llist = self.getControl(120)
		out = ''
		for x in range(0,llist.size()):
			out += llist.getListItem(x).getProperty('text') + '\n'
		return out
		
	def addLine(self,line=''):
		item = xbmcgui.ListItem(label=self.displayLine(line))
		#we set text separately so we can have the display be formatted...
		item.setProperty('text',line)
		self.getControl(120).addItem(item)
		self.getControl(120).selectItem(self.getControl(120).size()-1)
		return True
		
	def displayLine(self,line):
		return line	.replace('\n',' ')\
					.replace('[/B]','[/b]')\
					.replace('[/I]','[/i]')\
					.replace('[/COLOR]','[/color]')
			
	def addLineSingle(self,line=None,before=False,update=True):
		if line == None: line = dialogs.doKeyboard(T(32123),'',mod=True)
		if line == None: return False
		if before:
			clist = self.getControl(120)
			idx = clist.getSelectedPosition()
			lines = []
			for i in range(0,clist.size()):
				if i == idx: lines.append(line)
				lines.append(clist.getListItem(i).getProperty('text'))
			clist.reset()
			for l in lines: self.addLine(l)
			self.updatePreview()
			return True
				
		else:
			self.addLine(line)
			self.updatePreview()
			return True
		
	def addLineMulti(self):
		while self.addLineSingle(): pass
		
	def deleteLine(self):
		llist = self.getControl(120)
		pos = llist.getSelectedPosition()
		lines = []
		for x in range(0,llist.size()):
			if x != pos: lines.append(llist.getListItem(x).getProperty('text'))
		llist.reset()
		for line in lines: self.addLine(line)
		self.updatePreview()
		if pos > llist.size(): pos = llist.size()
		llist.selectItem(pos)
	
	def editLine(self):
		item = self.getControl(120).getSelectedItem()
		if not item: return
		line = dialogs.doKeyboard(T(32124),item.getLabel(),mod=True)
		if line == None: return False
		item.setProperty('text',line)
		item.setLabel(self.displayLine(line))
		self.updatePreview()
		#re.sub(q,'[QUOTE=\g<user>;\g<postid>]\g<quote>[/QUOTE]',FB.MC.lineFilter.sub('',test3))

######################################################################################
#
# Message Window
#
######################################################################################		
class MessageWindow(windows.BaseWindow):
	def __init__( self, *args, **kwargs ):
		self.post = kwargs.get('post')
		self.searchRE = kwargs.get('search_re')
		#self.imageReplace = '[COLOR FFFF0000]I[/COLOR][COLOR FFFF8000]M[/COLOR][COLOR FF00FF00]G[/COLOR][COLOR FF0000FF]#[/COLOR][COLOR FFFF00FF]%s[/COLOR]'
		self.imageReplace = 'IMG #%s'
		self.action = None
		self.started = False
		self.interruptedVideo = None
		self.hasImages = False
		self.hasLinks = False
		self.videoHandler = video.WebVideo()
		windows.BaseWindow.__init__( self, *args, **kwargs )
		
	def onInit(self):
		windows.BaseWindow.onInit(self)
		if self.started: return
		self.started = True
		self.setLoggedIn()
		self.setWindowProperties()
#		if getSetting('use_forum_colors') == 'true':
#			if (FB.theme.get('mode') == 'dark' or getSetting('color_mode') == '1') and getSetting('color_mode') != '2':
#				text = '[COLOR FFFFFFFF]%s[/COLOR][CR] [CR]' % (self.post.translated or self.post.messageAsDisplay())
#			else:
#				text = '[COLOR FF000000]%s[/COLOR][CR] [CR]' % (self.post.translated or self.post.messageAsDisplay())
#		else:
#			text = '%s[CR] [CR]' % (self.post.translated or self.post.messageAsDisplay())
		s = dialogs.showActivitySplash()
		try:
			text = '%s[CR] [CR]' % self.post.messageAsDisplay(raw=True)
		finally:
			s.close()
			
		if self.searchRE: text = self.highlightTerms(FB,text)
		try:
			self.getControl(122).setLabel(text)
		except:
			self.getControl(122).setText(text)
		self.getControl(102).setImage(self.post.avatarFinal)
		self.setTheme()
		self.getImages()
		self.getLinks()
		self.setWindowProperties()
		
	def setTheme(self):
		self.getControl(103).setLabel('[B]%s[/B]' % self.post.cleanUserName() or '')
		title = []
		if self.post.postNumber: title.append('#' + str(self.post.postNumber))
		if self.post.title: title.append(self.post.title)
		title = ' '.join(title)
		self.getControl(104).setLabel('[B]%s[/B]' % title)
		self.getControl(105).setLabel(self.post.date or '')
		
	def getLinks(self):
		ulist = self.getControl(148)
		links = self.post.links()
		checkVideo = False
		for link in links:
			checkVideo = self.videoHandler.mightBeVideo(link.url)
			if checkVideo: break
			checkVideo = self.videoHandler.mightBeVideo(link.text)
			if checkVideo: break
		s = None
		if checkVideo: s = dialogs.showActivitySplash(T(32311))
		if links: self.hasLinks = True
		try:
			for link in links:
				item = xbmcgui.ListItem(link.text or link.url,link.urlShow())
				video = None
				if checkVideo:
					try:
						video = self.videoHandler.getVideoObject(link.url)
						if not video: video = self.videoHandler.getVideoObject(link.text)
					except:
						LOG('Error getting video info')
				if video:
					item.setIconImage(video.thumbnail)
					if video.title: item.setLabel(video.title)
					item.setLabel2('%s: %s' % (video.sourceName,video.ID))
				elif link.textIsImage():
					item.setIconImage(link.text)
				elif link.isImage():
					item.setIconImage(link.url)
				elif link.isPost():
					item.setIconImage(os.path.join(MEDIA_PATH,'forum-browser-post.png'))
				elif link.isThread():
					item.setIconImage(os.path.join(MEDIA_PATH,'forum-browser-thread.png'))
				else:
					item.setIconImage(os.path.join(MEDIA_PATH,'forum-browser-link.png'))
				ulist.addItem(item)
		finally:
			if s: s.close()

	def getImages(self):
		i=0
		urlParentDirFilter = re.compile('(?<!/)/\w[^/]*?/\.\./')
		urls = self.post.imageURLs()
		if urls: self.hasImages = True
		for url in urls:
			i+=1
			while urlParentDirFilter.search(url):
				#TODO: Limit
				url = urlParentDirFilter.sub('/',url)
			url = url.replace('/../','/')
			item = xbmcgui.ListItem(self.imageReplace % i,iconImage=url)
			item.setProperty('url',url)
			self.getControl(150).addItem(item)
			
		#targetdir = os.path.join(util.__addon__.getAddonInfo('profile'),'messageimages')
		#TD.startDownload(targetdir,self.post.imageURLs(),ext='.jpg',callback=self.getImagesCallback)
		
	def getImagesCallback(self,file_dict):
		for fname,idx in zip(file_dict.values(),range(0,self.getControl(150).size())):
			fname = xbmc.translatePath(fname)
			self.getControl(150).getListItem(idx).setIconImage(fname)
		
	def setWindowProperties(self):
		extras = showUserExtras(self.post,just_return=True)
		self.setProperty('extras',extras)
		self.setProperty('avatar',self.post.avatarFinal)
		if self.hasLinks: self.setProperty('haslinks','1')
		if self.hasImages: self.setProperty('hasimages','1')
		if self.post.online: self.setProperty('online','1')
	
	def onFocus( self, controlId ):
		self.controlId = controlId
		
	def onClick( self, controlID ):
		if windows.BaseWindow.onClick(self, controlID): return
		if controlID == 148:
			self.linkSelected()
		elif controlID == 150:
			self.showImage(self.getControl(150).getSelectedItem().getProperty('url'))
	
	def showVideo(self,source):
		if video.isPlaying() and getSetting('video_ask_interrupt',True):
			line2 = getSetting('video_return_interrupt',True) and T(32254) or ''
			if not dialogs.dialogYesNo(T(32255),T(32256),line2):
				return
		PLAYER.start(source)
		#video.play(source)
		
	def getSelectedLink(self):
		idx = self.getControl(148).getSelectedPosition()
		if idx < 0: return None
		links = self.post.links()
		if idx >= len(links): return None
		return links[idx]
		
	def linkSelected(self):
		link = self.getSelectedLink()
		if not link: return
		if self.videoHandler.mightBeVideo(link.url) or self.videoHandler.mightBeVideo(link.text):
			s = dialogs.showActivitySplash()
			try:
				video = self.videoHandler.getVideoObject(link.url)
				if not video: video = self.videoHandler.getVideoObject(link.text)
				if video and video.isVideo:
					self.showVideo(video.getPlayableURL())
					return
			finally:
				s.close()
		
		if link.isImage() and not link.textIsImage():
			self.showImage(link.url)
		elif link.isPost() or link.isThread():
			self.action = forumbrowser.PostMessage(tid=link.tid,pid=link.pid)
			self.doClose()
		else:
			try:
				webviewer.getWebResult(link.url,dialog=True,browser=FB.browser)
			except:
				raise
		
	def showImage(self,url):
		image_files = self.post.imageURLs()
		for l in self.post.links():
			if l.isImage() and not l.textIsImage(): image_files.append(l.url)
		if url in image_files:
			image_files.pop(image_files.index(url))
			image_files.insert(0,url)
		w = ImagesDialog("script-forumbrowser-imageviewer.xml" ,util.__addon__.getAddonInfo('path'),THEME,images=image_files,parent=self)
		w.doModal()
		del w
			
	def onAction(self,action):
		if action == ACTION_CONTEXT_MENU:
			if self.getFocusId() == 148:
				self.doLinkMenu()
			elif self.getFocusId() == 150:
				self.doImageMenu()
			else:
				self.doMenu()
			return
		elif action == ACTION_PARENT_DIR or action == ACTION_PARENT_DIR2 or action == ACTION_PREVIOUS_MENU:
			if self.getFocusId() == 148 or self.getFocusId() == 150:
				self.setFocusId(127)
				return
		windows.BaseWindow.onAction(self,action)
		
	def doLinkMenu(self):
		link = self.getSelectedLink()
		if not link: return
		d = dialogs.ChoiceMenu(T(32312))
		if CLIPBOARD:
			d.addItem('copy',T(32313))
			if link.isImage():
				d.addItem('copyimage',T(32314))
			video = self.videoHandler.getVideoObject(link.url)
			if not video: video = self.videoHandler.getVideoObject(link.text)
			if video and video.isVideo: d.addItem('copyvideo',T(32315))
				
		if d.isEmpty(): return
		result = d.getResult()
		if result == 'copy':
			share = CLIPBOARD.getShare('script.forum.browser','link')
			share.page = link.url
			CLIPBOARD.setClipboard(share)
		elif result == 'copyimage':
			share = CLIPBOARD.getShare('script.forum.browser','image')
			share.url = link.url
			CLIPBOARD.setClipboard(share)
		elif result == 'copyvideo':
			share = CLIPBOARD.getShare('script.forum.browser','video')
			video = self.videoHandler.getVideoObject(link.url)
			if video:
				share.page = link.url
			else:
				share.page = link.text
			CLIPBOARD.setClipboard(share)
				
	def doImageMenu(self):
		img = self.getControl(150).getSelectedItem().getProperty('url')
		d = dialogs.ChoiceMenu(T(32316))
		if CLIPBOARD:
			d.addItem('copy',T(32314))
		if d.isEmpty(): return
		result = d.getResult()
		if result == 'copy':
			share = CLIPBOARD.getShare('script.evernote','image')
			share.url = img
			CLIPBOARD.setClipboard(share)
	
	def doMenu(self):
		d = dialogs.ChoiceMenu(T(32051))
		if FB.canPost(): d.addItem('quote',self.post.isPM and T(32249) or T(32134))
		if FB.canDelete(self.post.cleanUserName(),self.post.messageType()): d.addItem('delete',T(32141))
		if FB.canEditPost(self.post.cleanUserName()): d.addItem('edit',T(32232))
		if self.post.extras: d.addItem('extras',T(32317))
		d.addItem('help',T(32244))
		result = d.getResult()
		if result == 'quote': self.openPostDialog(quote=True)
		elif result == 'delete': self.deletePost()
		elif result == 'edit':
			splash = dialogs.showActivitySplash(T(32318))
			try:
				pm = FB.getPostForEdit(self.post)
			finally:
				splash.close()
			pm.tid = self.post.tid
			if openPostDialog(editPM=pm):
				self.action = forumbrowser.Action('REFRESH-REOPEN')
				self.action.pid = pm.pid
				self.doClose()
		elif result == 'extras':
			showUserExtras(self.post)
		elif result == 'help':
			dialogs.showHelp('message')
			
	def deletePost(self):
		result = deletePost(self.post,is_pm=self.post.isPM)
		self.action = forumbrowser.Action('REFRESH')
		if result: self.doClose()
		
	def openPostDialog(self,quote=False):
		pm = openPostDialog(quote and self.post or None,pid=self.post.postId,tid=self.post.tid,fid=self.post.fid)
		if pm:
			self.action = forumbrowser.PostMessage(pid=pm.pid)
			self.action.action = 'GOTOPOST'
			self.doClose()
		
	def setLoggedIn(self):
		if FB.isLoggedIn():
			self.getControl(111).setColorDiffuse('FF00FF00')
		else:
			self.getControl(111).setColorDiffuse('FF555555')
		self.getControl(160).setLabel(FB.loginError)

def openPostDialog(post=None,pid='',tid='',fid='',editPM=None,donotpost=False,no_quote=False,to=''):
	if editPM:
		pm = editPM
	else:
		pm = forumbrowser.PostMessage(pid,tid,fid,is_pm=(tid == 'private_messages'))
		if post and not no_quote:
			s = dialogs.showActivitySplash()
			try:
				pm.setQuote(post.userName,post.messageAsQuote())
				pm.title = post.title
			finally:
				s.close()
		if tid == 'private_messages':
			default = to
			if post: default = post.userName
			to = dialogs.doKeyboard(T(32319),default=default)
			if not to: return
			pm.to = to
	w = dialogs.openWindow(LinePostDialog,"script-forumbrowser-post.xml" ,post=pm,return_window=True,donotpost=donotpost)
	posted = w.posted
	del w
	if posted: return pm
	return None

def deletePost(post,is_pm=False):
	pm = forumbrowser.PostMessage().fromPost(post)
	if not pm.pid: return
	yes = dialogs.dialogYesNo(T(32320),T(32321))
	if not yes: return
	splash = dialogs.showActivitySplash(T(32322))
	try:
		if is_pm or post.isPM:
			pm.isPM = True
			result = FB.deletePrivateMessage(pm)
		else:
			result = FB.deletePost(pm)
		if not result:
			dialogs.showMessage(T(32323),T(32324),pm.error or T(32325),success=False)
		else:
			dialogs.showMessage(T(32304),pm.isPM and T(32326) or T(32327),success=True)
	except:
		err = ERROR('Delete post error.')
		LOG('Error deleting post/pm: ' + err)
		dialogs.showMessage(T(32050),T(32328),'[CR]',err,error=True)
		return None
	finally:
		splash.close()
	return result

def showUserExtras(post,ignore=None,just_return=False):
	out = ''
	color = 'FF550000'
	if just_return: color = 'FFBBBBBB'
	for k,v in post.getExtras(ignore=ignore).items():
		out += '[B]{0}:[/B] [COLOR {1}]{2}[/COLOR]\n'.format(k.title(),color,texttransform.convertHTMLCodes(str(v)))
	if just_return: return out
	dialogs.showMessage(T(32329),out,scroll=True)

######################################################################################
#
# Replies Window
#
######################################################################################
class RepliesWindow(windows.PageWindow):
	info_display = {'postcount':'posts','joindate':'joined'}
	def __init__( self, *args, **kwargs ):
		windows.PageWindow.__init__( self,total_items=int(kwargs.get('reply_count',0)),*args, **kwargs )
		self.setPageData(FB)
		self.pageData.isReplies = True
		self.threadItem = item = kwargs.get('item')
		self.dontOpenPD = False
		self.forumElements = kwargs.get('forumElements')
		if item:
			self.tid = item.getProperty('id')
			self.lastid = item.getProperty('lastid')
			self.topic = item.getProperty('title')
			self.reply_count = item.getProperty('reply_count')
			self.isAnnouncement = bool(item.getProperty('announcement'))
			self.search = item.getProperty('search_terms')
		else:
			self.tid = kwargs.get('tid')
			self.lastid = ''
			self.topic = kwargs.get('topic')
			self.reply_count = ''
			self.isAnnouncement = False
			self.search = kwargs.get('search_terms')
			
		self.searchRE = kwargs.get('search_re')
		if not self.searchRE: self.setupSearch()
				
		self.fid = kwargs.get('fid','')
		self.pid = kwargs.get('pid','')
		self.uid = kwargs.get('uid','')
		self.search_uname = kwargs.get('search_name','')
		self.parent = kwargs.get('parent')
		#self._firstPage = T(32113)
		self._newestPage = T(32112)
		self.me = FB.user
		self.posts = {}
		self.empty = True
		self.desc_base = u'[CR]%s[CR] [CR]'
		self.ignoreSelect = False
		self.firstRun = True
		self.started = False
		self.currentPMBox = {}
		self.timeOffset = 0
		timeOffset = getForumSetting(FB.getForumID(),'time_offset_hours','').replace(':','')
		if timeOffset:
			negative = timeOffset.startswith('-') and -1 or 1
			timeOffset = timeOffset.strip('-')
			seconds = timeOffset[-2:] or 0
			minutes = timeOffset[:-2] or 0
			try:
				self.timeOffset = negative * ((int(minutes) * 60) + int(seconds)) 
			except:
				pass 
	
	def onInit(self):
		windows.BaseWindow.onInit(self)
		self.setLoggedIn()
		if self.started: return
		self.started = True
		self.setupPage(None)
		self.setStopControl(self.getControl(106))
		self.setProgressCommands(self.startProgress,self.setProgress,self.endProgress)
		self.postSelected()
		self.setPMBox()
		self.setTheme()
		self.setPostButton()
		self.showThread()
		#self.setFocusId(120)
				
	def setPostButton(self):
		if self.isPM():
			self.getControl(201).setEnabled(FB.canPrivateMessage())
			self.getControl(201).setLabel(T(32177))
		elif self.search:
			self.getControl(201).setEnabled(True)
			self.getControl(201).setLabel(T(32914))
		else:
			self.getControl(201).setEnabled(FB.canPost())
			self.getControl(201).setLabel(T(32902))
			
	def setPMBox(self,boxid=None):
		if not self.isPM(): return
		boxes = FB.getPMBoxes(update=False)
		self.currentPMBox = {}
		if not boxes: return
		if not boxid:
			for b in boxes:
				if b.get('default'):
					self.currentPMBox = b
					return
		else:
			for b in boxes:
				if b.get('id') == boxid:
					self.currentPMBox = b
					return
		
	def setTheme(self):
		mtype = self.isPM() and self.currentPMBox.get('name','Inbox') or T(32130)
		#if self.isPM(): self.getControl(201).setLabel(T(32177))
		self.getControl(103).setLabel('[B]%s[/B]' % mtype)
		self.getControl(104).setLabel('[B]%s[/B]' % self.topic)
		
	def showThread(self,nopage=False):
		if nopage:
			page = ''
		else:
			page = '1'
			if getSetting('open_thread_to_newest') == 'true':
				if not self.search: page = '-1'
		self.fillRepliesList(FB.getPageData(is_replies=True).getPageNumber(page))
		
	def isPM(self):
		return self.tid == 'private_messages'
	
	def errorCallback(self,error):
		dialogs.showMessage(T(32050),T(32131),error.message,error=True)
		self.endProgress()
	
	def fillRepliesList(self,page='',pid=None):
		#page = int(page)
		#if page < 0: raise Exception()
		self.getControl(106).setVisible(True)
		self.setFocusId(106)
		if self.tid == 'private_messages':
			t = self.getThread(FB.getPrivateMessages,finishedCallback=self.doFillRepliesList,errorCallback=self.errorCallback,name='PRIVATE MESSAGES')
			t.setArgs(callback=t.progressCallback,donecallback=t.finishedCallback,boxid=self.currentPMBox.get('id'))
		elif self.isAnnouncement:
			t = self.getThread(FB.getAnnouncement,finishedCallback=self.doFillRepliesList,errorCallback=self.errorCallback,name='ANNOUNCEMENT')
			t.setArgs(self.tid,callback=t.progressCallback,donecallback=t.finishedCallback)
		elif self.search:
			if self.search == '@!RECENT!@':
				t = self.getThread(FB.getUserPosts,finishedCallback=self.doFillRepliesList,errorCallback=self.errorCallback,name='USER-RECENT-POSTS')
				t.setArgs(uname=self.search_uname,page=page or 0,uid=self.uid,callback=t.progressCallback,donecallback=t.finishedCallback,page_data=self.pageData)
			elif self.uid:
				t = self.getThread(FB.searchAdvanced,finishedCallback=self.doFillRepliesList,errorCallback=self.errorCallback,name='UID-SEARCHPOSTS')
				t.setArgs(self.search,page,sid=self.lastid,callback=t.progressCallback,donecallback=t.finishedCallback,page_data=self.pageData,uid=self.uid)
			elif self.search_uname:
				t = self.getThread(FB.searchAdvanced,finishedCallback=self.doFillRepliesList,errorCallback=self.errorCallback,name='UNAME-SEARCHPOSTS')
				t.setArgs(self.search,page,sid=self.lastid,callback=t.progressCallback,donecallback=t.finishedCallback,page_data=self.pageData,uname=self.search_uname)
			elif self.tid:
				t = self.getThread(FB.searchAdvanced,finishedCallback=self.doFillRepliesList,errorCallback=self.errorCallback,name='TID-SEARCHPOSTS')
				t.setArgs(self.search,page,sid=self.lastid,callback=t.progressCallback,donecallback=t.finishedCallback,page_data=self.pageData,tid=self.tid)
			else:
				t = self.getThread(FB.searchReplies,finishedCallback=self.doFillRepliesList,errorCallback=self.errorCallback,name='SEARCHPOSTS')
				t.setArgs(self.search,page,sid=self.lastid,callback=t.progressCallback,donecallback=t.finishedCallback,page_data=self.pageData)
		else:
			t = self.getThread(FB.getReplies,finishedCallback=self.doFillRepliesList,errorCallback=self.errorCallback,name='POSTS')
			t.setArgs(self.tid,self.fid,page,lastid=self.lastid,pid=self.pid or pid,callback=t.progressCallback,donecallback=t.finishedCallback,page_data=self.pageData)
		t.start()
		
	def setMessageProperty(self,post,item,short=False):
		title = (self.search and post.topic or post.title) or ''
		item.setProperty('title',title)
		message = post.messageAsDisplay(short)
		if self.searchRE: message = self.highlightTerms(FB,message)
		item.setProperty('message',message)
	
	def updateItem(self,item,post):
		alt = self.getUserInfoAttributes()
		defAvatar = xbmc.translatePath(os.path.join(util.__addon__.getAddonInfo('path'),'resources','skins','Default','media','forum-browser-avatar-none.png'))
		webvid = video.WebVideo()
		showIndicators = getSetting('show_media_indicators',True)
		countLinkImages = getSetting('smi_count_link_images',False)
		item.setProperty('alternate1','')
		item.setProperty('alternate2','')
		item.setProperty('alternate3','')
		
		self._updateItem(item,post,defAvatar,showIndicators,countLinkImages,webvid,alt)
		self.setFocusId(120)
		
	def fixAvatar(self,url):
		if not 'http%3A%2F%2F' in url: return url
		return url + '&time=%s' % str(time.time())
		
	def _updateItem(self,item,post,defAvatar,showIndicators,countLinkImages,webvid,alt):
		url = defAvatar
		if post.avatar: url = FB.makeURL(post.avatar)
		post.avatarFinal = url
		self.setMessageProperty(post,item,True)
		item.setProperty('post',str(post.postId))
		item.setProperty('avatar',self.fixAvatar(url))
		#item.setProperty('status',texttransform.convertHTMLCodes(post.status))
		item.setProperty('date',post.getDate(self.timeOffset))
		item.setProperty('online',post.online and 'online' or '')
		item.setProperty('postnumber',post.postNumber and unicode(post.postNumber) or '')
		if post.online:
			item.setProperty('activity',post.getActivity(self.timeOffset))
		else:
			item.setProperty('last_seen',post.getActivity(self.timeOffset))
		if showIndicators:
			hasimages,hasvideo = post.hasMedia(webvid,countLinkImages)
			item.setProperty('hasimages',hasimages and 'hasimages' or 'noimages')
			item.setProperty('hasvideo',hasvideo and 'hasvideo' or 'novideo')
		altused = []
		extras = post.getExtras()
		for a in alt:
			val = extras.get(a)
			if val != None and unicode(val):
				edisp = val and '%s: %s' % (self.info_display.get(a,a).title(),texttransform.convertHTMLCodes(unicode(val))) or ''
				del extras[a]
				altused.append(a)
				if item.getProperty('alternate1'):
					if item.getProperty('alternate2'):
						item.setProperty('alternate3',edisp)
						break
					else:
						item.setProperty('alternate2',edisp)
				else:
					item.setProperty('alternate1',edisp)
		
		if extras:
			item.setProperty('extras','extras')
			item.setProperty('usedExtras',','.join(altused))
			
	def shouldReverse(self):
		if self.isPM(): return False
		if self.search: return getSetting('reverse_sort_search',False)
		return getSetting('reverse_sort',False)
	
	def shouldDropToBottom(self):
		if self.isPM(): return False
		if self.search: return getSetting('reverse_sort_search',False)
		return not getSetting('reverse_sort',False)
			
	def doFillRepliesList(self,data):
		if 'newthreadid' in data: self.tid = data['newthreadid']
		if not data:
			self.setFocusId(201)
			if data.error == 'CANCEL': return
			LOG('GET REPLIES ERROR')
			dialogs.showMessage(T(32050),self.isPM() and T(32135) or T(32131),T(32053),'[CR]' + data.error,success=False)
			return
		elif not data.data:
			if data.data == None:
				self.setFocusId(201)
				LOG('NO REPLIES')
				dialogs.showMessage(T(32050),self.isPM() and T(32135) or T(32131),T(32053),success=False)
			else:
				self.setFocusId(201)
				self.getControl(104).setLabel(self.isPM() and T(32251) or T(32250))
				LOG('No messages/posts - clearing list')
				self.getControl(120).reset()
				self.getControl(120).addItems([])
			return
		
		self.empty = False
		defAvatar = xbmc.translatePath(os.path.join(util.__addon__.getAddonInfo('path'),'resources','skins','Default','media','forum-browser-avatar-none.png'))
		#xbmcgui.lock()
		try:
			self.getControl(120).reset()
			if not self.topic: self.topic = data.pageData.topic
			if not self.tid: self.tid = data.pageData.tid
			self.setupPage(data.pageData)
			if self.shouldReverse():
				data.data.reverse()
			alt = self.getUserInfoAttributes()
			self.posts = {}
			select = -1
			webvid = video.WebVideo()
			showIndicators = getSetting('show_media_indicators',True)
			countLinkImages = getSetting('smi_count_link_images',False)
			items = []
			for post,idx in zip(data.data,range(0,len(data.data))):
				if self.pid and post.postId == self.pid: select = idx
				self.posts[post.postId] = post
				user = re.sub('<.*?>','',post.userName)
				item = xbmcgui.ListItem(label=post.isSent and 'To: ' + user or user)
				if user == self.me: item.setInfo('video',{"Director":'me'})
				self._updateItem(item,post,defAvatar,showIndicators,countLinkImages,webvid,alt)
				items.append(item)
			self.getControl(120).addItems(items)
			self.setFocusId(120)
			if select > -1:
				self.getControl(120).selectItem(int(select))
			elif self.firstRun and getSetting('open_thread_to_newest',False) and FB.canOpenLatest() and self.shouldDropToBottom():
				self.getControl(120).selectItem(self.getControl(120).size() - 1)
			self.firstRun = False
		except:
			self.setFocusId(201)
			#xbmcgui.unlock()
			ERROR('FILL REPLIES ERROR')
			dialogs.showMessage(T(32050),T(32133),error=True)
			raise
		#xbmcgui.unlock()
		if select > -1 and not self.dontOpenPD:
			self.dontOpenPD = False
			self.postSelected(itemindex=select)
		
		self.getControl(104).setLabel('[B]%s[/B]' % self.topic)
		self.pid = ''
		self.setLoggedIn()
		self.openElements()
		
	def openElements(self):
		if not self.forumElements: return
		if self.forumElements.get('post'):
			item = util.selectListItemByProperty(self.getControl(120),'post',self.forumElements.get('post'))
			if item: self.onClick(120)
		self.forumElements = None
			
	def getUserInfoAttributes(self):
		data = loadForumSettings(FB.getForumID())
		try:
			if 'extras' in data and data['extras']: return data['extras'].split(',')
			return getSetting('post_user_info','status,postcount,reputation,joindate,location').split(',')
		except:
			ERROR('getUserInfoAttributes(): Bad settings data')
			return ['postcount','reputation','joindate','location']
		
	def makeLinksArray(self,miter):
		if not miter: return []
		urls = []
		for m in miter:
			urls.append(m)
		return urls
		
	def postSelected(self,itemindex=-1):
		if itemindex > -1:
			item = self.getControl(120).getListItem(itemindex)
		else:
			item = self.getControl(120).getSelectedItem()
		if not item: return
		post = self.posts.get(item.getProperty('post'))
		if self.search and getSetting('search_open_thread',False):
			return self.openPostThread(post)
		post.tid = self.tid
		post.fid = self.fid
		w = dialogs.openWindow(MessageWindow,"script-forumbrowser-message.xml" ,return_window=True,post=post,search_re=self.searchRE,parent=self)
		self.setMessageProperty(post,item)
		self.setFocusId(120)
		if w.action:
			if w.action.action == 'CHANGE':
				self.topic = ''
				self.pid = w.action.pid
				self.tid = w.action.tid
				self.search = ''
				self.searchRE = None
				self.firstRun = True
				self.setPostButton()
				if w.action.pid: self.showThread(nopage=True)
				else: self.showThread()
			elif w.action.action == 'REFRESH':
				self.fillRepliesList(self.pageData.getPageNumber())
			elif w.action.action == 'REFRESH-REOPEN':
				self.pid = w.action.pid
				self.fillRepliesList(self.pageData.getPageNumber())
			elif w.action.action == 'GOTOPOST':
				self.firstRun = True
				self.fillRepliesList(self.pageData.getPageNumber(),pid=w.action.pid)
		del w
		
	def onClick(self,controlID):
		if controlID == 201:
			self.stopThread()
			if self.search:
				self.newSearch()
			else:
				self.openPostDialog()
		elif controlID == 120:
			if not self.empty: self.stopThread()
			self.postSelected()
		elif controlID == 106:
			self.stopThread()
			return
		if self.empty: self.fillRepliesList()
		windows.PageWindow.onClick(self,controlID)
		
	def onAction(self,action):
		if action == ACTION_CONTEXT_MENU:
			self.doMenu()
		elif action == ACTION_PARENT_DIR or action == ACTION_PARENT_DIR2 or action == ACTION_PREVIOUS_MENU:
			if util.Control.HasFocus(group=196):
					if self.getControl(120).size():
						self.setFocusId(120)
						return
		windows.PageWindow.onAction(self,action)
	
	def newSearch(self):
		terms = dialogs.doKeyboard(T(32330),self.search or '')
		if not terms: return
		self.search = terms
		self.setupSearch()
		self.fillRepliesList()
	
	def selectNewPMBox(self):
		boxes = FB.getPMBoxes(update=False)
		if not boxes: return #TODO: Show message
		d = dialogs.ChoiceMenu(T(32331))
		for b in boxes:
			d.addItem(b,b.get('name','?'))
		box = d.getResult()
		if not box: return
		self.currentPMBox = box
		self.setTheme()
		self.fillRepliesList()
		
	def doMenu(self):
		item = self.getControl(120).getSelectedItem()
		d = dialogs.ChoiceMenu(T(32051),with_splash=True)
		post = None
		try:
			if self.isPM():
				boxes = FB.getPMBoxes(update=False)
				if boxes and len(boxes) > 1:
					d.addItem('changebox',T(32332))
			if item:
				post = self.posts.get(item.getProperty('post'))
				if FB.canPost() and not self.search:
					d.addItem('quote',self.isPM() and T(32249) or T(32134))
				if FB.canDelete(item.getLabel(),post.messageType()):
					d.addItem('delete',T(32141))
				if not self.isPM():
					if FB.canEditPost(item.getLabel()):
						d.addItem('edit',T(32232))
						
			if self.threadItem:
				if FB.isThreadSubscribed(self.tid,self.threadItem.getProperty('subscribed')):
					if FB.canUnSubscribeThread(self.tid): d.addItem('unsubscribe',T(32240) + ': ' + self.threadItem.getProperty('title')[:25])
				else:
					if FB.canSubscribeThread(self.tid): d.addItem('subscribe',T(32236) + ': ' + self.threadItem.getProperty('title')[:25])
			if post and item.getProperty('extras'):
				d.addItem('extras',T(32317))
			if item and FB.canPrivateMessage() and not self.isPM():
				d.addItem('pm',T(32253).format(item.getLabel()))
			if post and post.canLike():
				d.addItem('like',T(32333))
			if post and post.canUnlike():
				d.addItem('unlike',T(32334))
			if self.searchRE and not getSetting('search_open_thread',False):
				d.addItem('open_thread',T(32335))
			d.addItem('refresh',T(32054))
			d.addItem('help',T(32244))
		finally:
			d.cancel()
		
		result = d.getResult()
		if not result: return
		if result == 'changebox':
			self.selectNewPMBox()
			return
		elif result == 'quote':
			self.stopThread()
			self.openPostDialog(post)
		elif result == 'refresh':
			self.stopThread()
			self.fillRepliesList(self.pageData.getPageNumber())
		elif result == 'edit':
			splash = dialogs.showActivitySplash(T(32318))
			try:
				pm = FB.getPostForEdit(post)
			finally:
				splash.close()
			pm.tid = self.tid
			if openPostDialog(editPM=pm):
				self.pid = pm.pid
				self.dontOpenPD = True
				self.fillRepliesList(self.pageData.getPageNumber())
		elif result == 'delete':
			self.stopThread()
			self.deletePost()
		elif result == 'subscribe':
			if subscribeThread(self.tid): self.threadItem.setProperty('subscribed','subscribed')
		elif result == 'unsubscribe':
			if unSubscribeThread(self.tid): self.threadItem.setProperty('subscribed','')
		elif result == 'extras':
			showUserExtras(post,ignore=(item.getProperty('usedExtras') or '').split(','))
		elif result == 'pm':
			quote = dialogs.dialogYesNo(T(32336),T(32337))
			self.openPostDialog(post,force_pm=True,no_quote=not quote)
		elif result == 'like':
			splash = dialogs.showActivitySplash(T(32338))
			try:
				post.like()
				self.updateItem(item, post)
			finally:
				splash.close()
		elif result == 'unlike':
			splash = dialogs.showActivitySplash(T(32339))
			try:
				post.unLike()
				self.updateItem(item, post)
			finally:
				splash.close()
		elif result == 'open_thread':
			self.openPostThread(post)
		elif result == 'help':
			if self.isPM():
				dialogs.showHelp('pm')
			else:
				dialogs.showHelp('posts')
		if self.empty: self.fillRepliesList()
			
	def deletePost(self):
		item = self.getControl(120).getSelectedItem()
		pid = item.getProperty('post')
		if not pid: return
		post = self.posts.get(pid)
		if deletePost(post,is_pm=self.isPM()):
			self.fillRepliesList(self.pageData.getPageNumber())
		
	def openPostThread(self,post):
		if not post: return
		dialogs.openWindow(RepliesWindow,"script-forumbrowser-replies.xml" ,fid=post.fid,tid=post.tid,pid=post.postId,topic=post.topic,search_re=self.searchRE,parent=self)
	
	def openPostDialog(self,post=None,force_pm=False,no_quote=False):
		tid = self.tid
		if force_pm:
			tid = 'private_messages'
			
		if post:
			item = self.getControl(120).getSelectedItem()
		else:
			if self.isPM():
				item = None
			else:
				if not self.getControl(120).size(): return
				item = self.getControl(120).getListItem(0)
		#if not item.getProperty('post'): item = self.getControl(120).getListItem(1)
		if item:
			pid = item.getProperty('post')
		else:
			pid = 0
		pm = openPostDialog(post,pid,tid,self.fid,no_quote=no_quote)
		if pm and not force_pm:
			self.firstRun = True
			self.fillRepliesList(self.pageData.getPageNumber('-1'),pid=pm.pid)
	
	def gotoPage(self,page):
		self.stopThread()
		self.fillRepliesList(page)
		
	def setLoggedIn(self):
		if FB.isLoggedIn():
			self.getControl(111).setColorDiffuse('FF00FF00')
		else:
			if FB.loginError:
				self.getControl(111).setColorDiffuse('FFFF0000')
			else:
				self.getControl(111).setColorDiffuse('FF555555')
		#self.getControl(160).setLabel(FB.loginError)

def subscribeThread(tid):
	splash = dialogs.showActivitySplash()
	try:
		result = FB.subscribeThread(tid)
		if result == True:
			dialogs.showMessage(T(32304),T(32340),success=True)
		else:
			dialogs.showMessage(T(32323),T(32341),str(result),success=False)
		return result
	finally:
		splash.close()
		
def unSubscribeThread(tid):
	splash = dialogs.showActivitySplash()
	try:
		result = FB.unSubscribeThread(tid)
		if result == True:
			dialogs.showMessage(T(32304),T(32342),success=True)
		else:
			dialogs.showMessage(T(32323),T(32343),str(result),success=False)
		return result
	finally:
		splash.close()

def subscribeForum(fid):
	splash = dialogs.showActivitySplash()
	try:
		result = FB.subscribeForum(fid)
		if result == True:
			dialogs.showMessage(T(32304),T(32344),success=True)
		else:
			dialogs.showMessage(T(32323),T(32345),str(result),success=False)
		return result
	finally:
		splash.close()

def unSubscribeForum(fid):
	splash = dialogs.showActivitySplash()
	try:
		result = FB.unSubscribeForum(fid)
		if result == True:
			dialogs.showMessage(T(32304),T(32346),success=True)
		else:
			dialogs.showMessage(T(32323),T(32347),str(result),success=False)
		return result
	finally:
		splash.close()
	
######################################################################################
#
# Threads Window
#
######################################################################################
class ThreadsWindow(windows.PageWindow):
	def __init__( self, *args, **kwargs ):
		self.fid = kwargs.get('fid','')
		self.topic = kwargs.get('topic','')
		self.parent = kwargs.get('parent')
		self.forumItem = kwargs.get('item')
		self.me = self.parent.getUsername() or '?'
		self.search = kwargs.get('search_terms')
		self.search_uname = kwargs.get('search_name','')
		self.forumElements = kwargs.get('forumElements','')
		
		self.setupSearch()
		
		self.empty = True
		self.textBase = '%s'
		self.newBase = '[B]%s[/B]'
		self.highBase = '%s'
		self.forum_desc_base = '[I]%s [/I]'
		self.started = False
		windows.PageWindow.__init__( self, *args, **kwargs )
		self.setPageData(FB)
		
	def onInit(self):
		windows.BaseWindow.onInit(self)
		self.setLoggedIn()
		if self.started: return
		self.started = True
		self.setupPage(None)
		self.setStopControl(self.getControl(106))
		self.setProgressCommands(self.startProgress,self.setProgress,self.endProgress)
		self.setTheme()
		self.fillThreadList()
		#self.setFocus(self.getControl(120))
			
	def setTheme(self):
		self.desc_base = unicode.encode(T(32162)+' %s','utf8')
		if self.fid == 'subscriptions':
			self.getControl(103).setLabel('[B]%s[/B]' % T(32175))
			self.getControl(104).setLabel('')
		else:
			self.getControl(103).setLabel('[B]%s[/B]' % T(32160))
			self.getControl(104).setLabel('[B]%s[/B]' % self.topic)
	
	def errorCallback(self,error):
		dialogs.showMessage(T(32050),T(32161),error.message,error=True)
		self.endProgress()
		
	def fillThreadList(self,page=''):
		self.getControl(106).setVisible(True)
		self.setFocusId(106)
		if self.fid == 'subscriptions':
			t = self.getThread(FB.getSubscriptions,finishedCallback=self.doFillThreadList,errorCallback=self.errorCallback,name='SUBSCRIPTIONS')
			t.setArgs(page,callback=t.progressCallback,donecallback=t.finishedCallback,page_data=self.pageData)
		elif self.search:
			if self.search == '@!RECENTTHREADS!@':
				t = self.getThread(FB.getUserThreads,finishedCallback=self.doFillThreadList,errorCallback=self.errorCallback,name='USERRECENTTHREADS')
				t.setArgs(uname=self.search_uname,page=page or 0,callback=t.progressCallback,donecallback=t.finishedCallback,page_data=self.pageData)
			elif self.fid:
				t = self.getThread(FB.searchAdvanced,finishedCallback=self.doFillThreadList,errorCallback=self.errorCallback,name='SEARCHTHREADS')
				t.setArgs(self.search,page or 0,callback=t.progressCallback,donecallback=t.finishedCallback,page_data=self.pageData,fid=self.fid)
			else:
				t = self.getThread(FB.searchThreads,finishedCallback=self.doFillThreadList,errorCallback=self.errorCallback,name='SEARCHTHREADS')
				t.setArgs(self.search,page or 0,callback=t.progressCallback,donecallback=t.finishedCallback,page_data=self.pageData)
		else:
			t = self.getThread(FB.getThreads,finishedCallback=self.doFillThreadList,errorCallback=self.errorCallback,name='THREADS')
			t.setArgs(self.fid,page,callback=t.progressCallback,donecallback=t.finishedCallback,page_data=self.pageData)
		t.start()
		
	def doFillThreadList(self,data):
		self.endProgress()
		if 'newforumid' in data: self.fid = data['newforumid']
		if not data:
			if data.error == 'CANCEL': return
			LOG('GET THREADS ERROR')
			dialogs.showMessage(T(32050),T(32161),T(32053),data.error,success=False)
			return
		
		self.empty = False
		try:
			self.getControl(120).reset()
			self.setupPage(data.pageData)
			if not (self.addForums(data['forums']) + self.addThreads(data.data)):
				LOG('Empty Forum')
				dialogs.showMessage(T(32229),T(32230),success=False)
			self.setFocusId(120)
		except:
			ERROR('FILL THREAD ERROR')
			dialogs.showMessage(T(32050),T(32163),error=True)
		self.setLoggedIn()
		self.openElements()
		
	def openElements(self):
		if not self.forumElements: return
		if self.forumElements.get('section') == 'SUBSCRIPTIONS' and self.forumElements.get('forum'):
			item = util.selectListItemByProperty(self.getControl(120),'id',self.forumElements.get('forum'))
			if item:
				self.onClick(120)
			else:
				self.openRepliesWindow(self.forumElements)
				self.forumElements = None
		elif self.forumElements.get('thread'):
			item = util.selectListItemByProperty(self.getControl(120),'id',self.forumElements.get('thread'))
			if item:
				self.onClick(120)
			else:
				self.openRepliesWindow(self.forumElements)
				self.forumElements = None
			
	def addThreads(self,threads):
		if not threads: return False
		for t in threads:
			if hasattr(t,'groupdict'):
				tdict = t.groupdict()
			else:
				tdict = t
			tid = tdict.get('threadid','')
			starter = tdict.get('starter',T(32348))
			title = tdict.get('title','')
			title = texttransform.convertHTMLCodes(FB.MC.tagFilter.sub('',title))
			last = tdict.get('lastposter','')
			fid = tdict.get('forumid','')
			sticky = tdict.get('sticky') and 'sticky' or ''
			reply_count = unicode(tdict.get('reply_number','0') or '0')
			if starter == self.me: starterbase = self.highBase
			else: starterbase = self.textBase
			#title = (tdict.get('new_post') and self.newBase or self.textBase) % title
			titleDisplay = title
			if self.searchRE: titleDisplay = self.highlightTerms(FB,titleDisplay)
			item = xbmcgui.ListItem(label=starterbase % starter,label2=titleDisplay)
			if tdict.get('new_post'): item.setProperty('unread','unread')
			item.setInfo('video',{"Genre":sticky})
			item.setInfo('video',{"Director":starter == self.me and 'me' or ''})
			item.setInfo('video',{"Studio":last == self.me and 'me' or ''})
			item.setProperty("id",unicode(tid))
			item.setProperty("fid",unicode(fid))
			item.setProperty("lastposter",last)
			preview = tdict.get('short_content','')
			if preview: preview = re.sub('<[^>]+?>','',texttransform.convertHTMLCodes(preview))
			
			if last:
				last = self.desc_base % last
				if preview: last += '[CR]' + preview
			else:
				last = preview
			if self.searchRE: last = self.highlightTerms(FB,last)
			item.setProperty("preview",preview)
			item.setProperty("last",last)
			item.setProperty("starter",starter)
			item.setProperty("lastid",tdict.get('lastid',''))
			item.setProperty('title',title)
			item.setProperty('announcement',unicode(tdict.get('announcement','')))
			item.setProperty('reply_count',reply_count)
			item.setProperty('subscribed',tdict.get('subscribed') and 'subscribed' or '')
			self.getControl(120).addItem(item)
		return True
			
	def addForums(self,forums):
		if not forums: return False
		for f in forums:
			if hasattr(f,'groupdict'):
				fdict = f.groupdict()
			else:
				fdict = f
			fid = fdict.get('forumid','')
			title = fdict.get('title',T(32050))
			desc = fdict.get('description') or T(32172)
			text = self.textBase
			title = texttransform.convertHTMLCodes(re.sub('<[^<>]+?>','',title) or '?')
			item = xbmcgui.ListItem(label=self.textBase % T(32164),label2=text % title)
			item.setInfo('video',{"Genre":'is_forum'})
			item.setProperty("last",self.forum_desc_base % texttransform.convertHTMLCodes(FB.MC.tagFilter.sub('',FB.MC.brFilter.sub(' ',desc))))
			item.setProperty("title",title)
			item.setProperty("topic",title)
			item.setProperty("id",fid)
			item.setProperty("fid",fid)
			item.setProperty("is_forum",'True')
			if fdict.get('new_post'): item.setProperty('unread','unread')
			item.setProperty('subscribed',fdict.get('subscribed') and 'subscribed' or '')
			self.getControl(120).addItem(item)
		return True
				
	def openRepliesWindow(self,forumElements=None):
		forumElements = forumElements or self.forumElements
		self.forumElements = None
		if forumElements and forumElements.get('section') == 'SUBSCRIPTIONS' and forumElements.get('forum'):
			item = util.getListItemByProperty(self.getControl(120),'id',forumElements.get('forum'))
			if not item:
				item = xbmcgui.ListItem()
				item.setProperty('fid',forumElements.get('forum'))
				item.setProperty('id',forumElements.get('forum'))
				item.setProperty('is_forum','True')
		elif forumElements and forumElements.get('thread'):
			item = util.getListItemByProperty(self.getControl(120),'id',forumElements.get('thread'))
			if not item:
				item = xbmcgui.ListItem()
				item.setProperty('fid',forumElements.get('forum'))
				item.setProperty('id',forumElements.get('thread'))
		else:
			item = self.getControl(120).getSelectedItem()
		
		item.setProperty('unread','')
		fid = item.getProperty('fid') or self.fid
		topic = item.getProperty('title')
		if item.getProperty('is_forum') == 'True':
			dialogs.openWindow(ThreadsWindow,"script-forumbrowser-threads.xml",fid=fid,topic=topic,parent=self.parent,item=item)
			#self.fid = fid
			#self.topic = topic
			#self.setTheme()
			#self.fillThreadList()
		else:
			dialogs.openWindow(RepliesWindow,"script-forumbrowser-replies.xml" ,fid=fid,topic=topic,item=item,search_re=self.searchRE,parent=self,forumElements=forumElements)

	def onFocus( self, controlId ):
		self.controlId = controlId
	
	def onClick( self, controlID ):
		if controlID == 120:
			if not self.empty: self.stopThread()
			self.openRepliesWindow()
		elif controlID == 106:
			self.stopThread()
			return
		if self.empty: self.fillThreadList()
		windows.PageWindow.onClick(self,controlID)
	
	def onAction(self,action):
		if action == ACTION_CONTEXT_MENU:
			self.doMenu()
		elif action == ACTION_PARENT_DIR or action == ACTION_PARENT_DIR2 or action == ACTION_PREVIOUS_MENU:
			if util.Control.HasFocus(group=196):
				if self.getControl(120).size():
					self.setFocusId(120)
					return
		windows.PageWindow.onAction(self,action)
		
	def doMenu(self):
		item = self.getControl(120).getSelectedItem()
		d = dialogs.ChoiceMenu('Options',with_splash=True)
		try:
			if item:
				if item.getProperty("is_forum") == 'True':
					if FB.isForumSubscribed(item.getProperty('id'),item.getProperty('subscribed')):
						if FB.canUnSubscribeForum(item.getProperty('id')): d.addItem('unsubscribeforum', T(32242))
					else:
						if FB.canSubscribeForum(item.getProperty('id')): d.addItem('subscribeforum', T(32243))
				else:
					if FB.isThreadSubscribed(item.getProperty('id'),item.getProperty('subscribed')):
						if FB.canUnSubscribeThread(item.getProperty('id')): d.addItem('unsubscribe', T(32240))
					else:
						if FB.canSubscribeThread(item.getProperty('id')): d.addItem('subscribe', T(32236))
				if self.fid != 'subscriptions':
					if self.forumItem:
						if FB.isForumSubscribed(self.forumItem.getProperty('id'),self.forumItem.getProperty('subscribed')):
							if FB.canUnSubscribeForum(self.forumItem.getProperty('id')): d.addItem('unsubscribecurrentforum', T(32242) + ': ' + self.forumItem.getProperty('topic')[:25])
						else:
							if FB.canSubscribeForum(self.forumItem.getProperty('id')): d.addItem('subscribecurrentforum', T(32243) + ': ' + self.forumItem.getProperty('topic')[:25])
					if FB.canCreateThread(item.getProperty('id')):
						d.addItem('createthread',T(32252))
				if FB.canSearchAdvanced('TID'):
					d.addItem('search','%s [B][I]%s[/I][/B]' % (T(32371),item.getProperty('title')[:30]))
			d.addItem('help',T(32244))
		finally:
			d.cancel()
		result = d.getResult()
		if not result: return
		if result == 'subscribe':
			if subscribeThread(item.getProperty('id')): item.setProperty('subscribed','subscribed')
		elif result == 'subscribeforum':
			if subscribeForum(item.getProperty('id')): item.setProperty('subscribed','subscribed')
		elif result == 'unsubscribe':
			if unSubscribeThread(item.getProperty('id')):
				item.setProperty('subscribed','')
				self.removeItem(item)
		elif result == 'unsubscribeforum':
			if unSubscribeForum(item.getProperty('id')):
				item.setProperty('subscribed','')
				self.removeItem(item)
		elif result == 'subscribecurrentforum':
			if subscribeForum(self.fid): self.forumItem.setProperty('subscribed','subscribed')
		elif result == 'unsubscribecurrentforum':
			if unSubscribeForum(self.fid): self.forumItem.setProperty('subscribed','')
		elif result == 'search':
			if not item.getProperty("is_forum") == 'True':
				searchPosts(self,item.getProperty('id'))
			else:
				searchThreads(self.parent,item.getProperty('id'))
		elif result == 'createthread':
			self.createThread()
		elif result == 'help':
			if self.fid == 'subscriptions':
				dialogs.showHelp('subscriptions')
			else:
				dialogs.showHelp('threads')
	
	def createThread(self):
		pm = openPostDialog(fid=self.fid,donotpost=True)
		if pm:
			splash = dialogs.showActivitySplash(T(32349))
			try:
				result = FB.createThread(self.fid,pm.title,pm.message)
				if result == True:
					dialogs.showMessage(T(32304),T(32350),'\n',pm.title,success=True)
					self.fillThreadList()
				else:
					dialogs.showMessage(T(32323),T(32351),'\n',str(result),success=False)
			finally:
				splash.close()
			
	
	def removeItem(self,item):
		clist = self.getControl(120)
		#items = []
		storageList = xbmcgui.ControlList(-100,-100,80,80)
		for idx in range(0,clist.size()):
			i = clist.getListItem(idx)
			#print str(item.getProperty('id')) + ' : ' + str(i.getProperty('id'))
			if item.getProperty('id') != i.getProperty('id'): storageList.addItem(i)
		clist.reset()
		clist.addItems(self.getListItems(storageList))
		del storageList
	
	def getListItems(self,alist):
		items = []
		for x in range(0,alist.size()):
			items.append(alist.getListItem(x))
		return items
	
	def gotoPage(self,page):
		self.stopThread()
		self.fillThreadList(page)
		
	def setLoggedIn(self):
		if FB.isLoggedIn():
			self.getControl(111).setColorDiffuse('FF00FF00')
		else:
			if FB.loginError:
				self.getControl(111).setColorDiffuse('FFFF0000')
			else:
				self.getControl(111).setColorDiffuse('FF555555')
		#self.getControl(160).setLabel(FB.loginError)

######################################################################################
#
# Forums Window
#
######################################################################################
class ForumsWindow(windows.BaseWindow):
	def __init__( self, *args, **kwargs ):
		windows.BaseWindow.__init__( self, *args, **kwargs )
		#FB.setLogin(self.getUsername(),self.getPassword(),always=getSetting('always_login') == 'true')
		self.parent = self
		self.empty = True
		self.setAsMain()
		self.started = False
		self.headerIsDark = False
		self.forumElements = None
		self.headerTextFormat = '[B]%s[/B]'
		self.forumsManagerWindowIsOpen = False
		self.lastFB = None
	
	def newPostsCallback(self,signal,data):
		self.openForumsManager(external=True)
		
	def getUsername(self):
		data = loadForumSettings(FB.getForumID())
		if data and data['username']: return data['username']
		return ''
		
	def getPassword(self):
		data = loadForumSettings(FB.getForumID())
		if data and data['password']: return data['password']
		return ''
		
	def getNotify(self):
		data = loadForumSettings(FB.getForumID())
		if data: return data['notify']
		return False
	
	def hasLogin(self):
		return self.getUsername() != '' and self.getPassword() != ''
		
	def onInit(self):
		windows.BaseWindow.onInit(self)
		self.setLoggedIn() #So every time we return to the window we check
		self.getControl(112).setVisible(False)
		try:
			if self.started: return
			SIGNALHUB.registerReceiver('NEW_POSTS', self, self.newPostsCallback)
			xbmcgui.Window(xbmcgui.getCurrentWindowId()).setProperty('ForumBrowserMAIN','MAIN')
			self.setVersion()
			self.setStopControl(self.getControl(105))
			self.setProgressCommands(self.startProgress,self.setProgress,self.endProgress)
			self.started = True
			self.getControl(105).setVisible(True)
			self.setFocusId(105)
			self.startGetForumBrowser()
		except:
			self.setStopControl(self.getControl(105)) #In case the error happens before we do this
			self.setProgressCommands(self.startProgress,self.setProgress,self.endProgress)
			self.getControl(105).setVisible(False)
			self.endProgress() #resets the status message to the forum name
			self.setFocusId(202)
			raise
		
	def startGetForumBrowser(self,forum=None,url=None):
		self.getControl(201).setEnabled(False)
		self.getControl(203).setEnabled(False)
		self.getControl(204).setEnabled(False)
		t = self.getThread(getForumBrowser,finishedCallback=self.endGetForumBrowser,errorCallback=self.errorCallback,name='GETFORUMBROWSER')
		t.setArgs(forum=forum,url=url,donecallback=t.finishedCallback)
		t.start()
		
	def endGetForumBrowser(self,fb,forumElements):
		global FB
		FB = fb
		#self.setTheme()
		self.getControl(112).setVisible(False)
		self.resetForum(no_theme=True)
		self.fillForumList(True)
		setSetting('last_forum',FB.getForumID())
		self.forumElements = forumElements
		
	def openElements(self):
		if not self.forumElements: return
		forumElements = self.forumElements
		if forumElements.get('section'):
			if forumElements.get('section') == 'SUBSCRIPTIONS':
				self.openSubscriptionsWindow(forumElements)
				self.forumElements = None
			elif forumElements.get('section') == 'PM':
				self.openPMWindow(forumElements)
				self.forumElements = None
		elif forumElements.get('forum'):
			fid = forumElements.get('forum')
			item = util.selectListItemByProperty(self.getControl(120),'id',fid)
			if item:
				self.onClick(120)
			else:
				self.openThreadsWindow(forumElements)
				self.forumElements = None
		elif forumElements.get('thread'):
			#tid = forumElements.get('thread')
			self.forumElements = None
		elif forumElements.get('post'):
			#pid = forumElements.get('post')
			self.forumElements = None
		
	def setVersion(self):
		self.getControl(109).setLabel('v' + __version__)
		
	def setTheme(self):
		hc = FB.theme.get('header_color')
		self.headerTextFormat = '[B]%s[/B]'
		if hc and hc.upper() != 'FFFFFF':
			self.headerIsDark = self.hexColorIsDark(hc)
			if self.headerIsDark: self.headerTextFormat = '[COLOR FFFFFFFF][B]%s[/B][/COLOR]'
			hc = 'FF' + hc.upper()
			self.getControl(100).setColorDiffuse(hc)
			self.getControl(251).setVisible(False)
		else:
			self.getControl(100).setColorDiffuse('FF888888')
			self.getControl(251).setVisible(True)
		self.setLabels()
		
	def hexColorIsDark(self,h):
		r,g,b = self.hexToRGB(h)
		if r > 140 or g > 140 or b > 200: return False
		return True
		
	def hexToRGB(self,h):
		try:
			r = h[:2]
			g = h[2:4]
			b = h[4:]
			#print h
			#print r,g,b
			return (int(r,16),int(g,16),int(b,16))
		except:
			ERROR('hexToRGB()')
			return (255,255,255)

	def setLabels(self):
		self.getControl(103).setLabel(self.headerTextFormat % T(32170))
		self.getControl(104).setLabel(self.headerTextFormat % FB.getDisplayName())
		
	def errorCallback(self,error):
		self.failedToGetForum()
		dialogs.showMessage(T(32050),T(32171),error.message,error=True)
		self.setFocusId(202)
		self.endProgress()
	
	def failedToGetForum(self):
		global FB
		FB = self.lastFB
		if FB: setSetting('last_forum',FB.getForumID())
	
	def stopThread(self):
		self.failedToGetForum()
		windows.ThreadWindow.stopThread(self)
		
	def fillForumList(self,first=False):
		if not FB: return
		self.setLabels()
		if not FB.guestOK() and not self.hasLogin():
			yes = dialogs.dialogYesNo(T(32352),T(32353),T(32354),T(32355))
			if yes:
				setLogins()
				if not self.hasLogin():
					self.setFocusId(202)
					return
				self.resetForum()
			else:
				self.setFocusId(202)
				return
		self.setFocusId(105)
		if first and getSetting('auto_thread_subscriptions_window') == 'true':
			if self.hasLogin() and FB.hasSubscriptions():
				FB.getForums(callback=self.setProgress,donecallback=self.doFillForumList)
				self.openSubscriptionsWindow()
				return
		t = self.getThread(FB.getForums,finishedCallback=self.doFillForumList,errorCallback=self.errorCallback,name='FORUMS')
		t.setArgs(callback=t.progressCallback,donecallback=t.finishedCallback)
		t.start()
		
	def doFillForumList(self,data):
		self.endProgress()
		self.lastFB = FB
		self.setLogo(data.getExtra('logo'))
		if not data:
			self.setFocusId(202)
			if data.error == 'CANCEL': return
			dialogs.showMessage(T(32050),T(32171),T(32053),'[CR]'+data.error,success=False)
			return
		self.empty = True
		
		try:
			#xbmcgui.lock()
			self.getControl(120).reset()
			self.setPMCounts(data.getExtra('pm_counts'))
			
			for f in data.data:
				self.empty = False
				if hasattr(f,'groupdict'):
					fdict = f.groupdict()
				else:
					fdict = f
				fid = fdict.get('forumid','')
				title = fdict.get('title',T(32050))
				desc = fdict.get('description') or T(32172)
				sub = fdict.get('subforum')
				if sub: desc = T(32173)
				title = texttransform.convertHTMLCodes(re.sub('<[^<>]+?>','',title) or '?')
				item = xbmcgui.ListItem(label=title)
				item.setInfo('video',{"Genre":sub and 'sub' or ''})
				item.setProperty("description",texttransform.convertHTMLCodes(FB.MC.tagFilter.sub('',FB.MC.brFilter.sub(' ',desc))))
				item.setProperty("topic",title)
				item.setProperty("id",unicode(fid))
				item.setProperty("link",fdict.get('link',''))
				if fdict.get('new_post'): item.setProperty('unread','unread')
				item.setProperty('subscribed',fdict.get('subscribed') and 'subscribed' or '')
				self.getControl(120).addItem(item)
				self.setFocusId(120)
		except:
			#xbmcgui.unlock()
			ERROR('FILL FORUMS ERROR')
			dialogs.showMessage(T(32050),T(32174),error=True)
			self.setFocusId(202)
		if self.empty: self.setFocusId(202)
		#xbmcgui.unlock()
		self.setLoggedIn()
		self.resetForum()
		if not FB.guestOK() and not FB.isLoggedIn():
			yes = dialogs.dialogYesNo(T(32352),T(32353),T(32354),T(32355))
			if yes:
				setLogins()
				self.resetForum()
				self.fillForumList()
		self.openElements()
		
	def setLogoFromFile(self):
		logopath = getCurrentLogo()
		if not logopath:
			LOG('NO LOGO WHEN SETTING LOGO')
			return
		return self.getControl(250).setImage(logopath)
			
	def setLogo(self,logo):
		if not logo: return
		if getSetting('save_logos',False):
			exists, logopath = getCachedLogo(logo,FB.getForumID())
			if exists:
				logo = logopath
			else:
				
				try:
					open(logopath,'wb').write(urllib2.urlopen(logo).read())
					logo = logopath
				except:
					LOG('ERROR: Could not save logo for: ' + FB.getForumID())
		if logo: self.getControl(250).setImage(logo)
		if 'ForumBrowser' in FB.browserType:
			image = 'forum-browser-logo-128.png'
		else:
			image = 'forum-browser-%s.png' % FB.browserType or ''
		image = os.path.join(xbmc.translatePath(util.__addon__.getAddonInfo('path')),'resources','skins','Default','media',image)
		self.getControl(249).setImage(image)
			
	def setPMCounts(self,pm_counts=False):
		if not FB: return
		if pm_counts == False: return
		disp = ''
		if not pm_counts: pm_counts = FB.getPMCounts()
		if pm_counts: disp = ' (%s/%s)' % (pm_counts.get('unread','?'),pm_counts.get('total','?'))
		self.getControl(203).setLabel(T(32909) + disp)
		self.setLoggedIn()
		
	def openPMWindow(self,forumElements=None):
		dialogs.openWindow(RepliesWindow,"script-forumbrowser-replies.xml" ,tid='private_messages',topic=T(32176),parent=self,forumElements=forumElements)
		self.setPMCounts(FB.getPMCounts())
	
	def openThreadsWindow(self,forumElements=None):
		forumElements = forumElements or self.forumElements
		self.forumElements = None
		fid = None
		topic = ''
		item = None
		if forumElements and forumElements.get('forum'):
			fid = forumElements.get('forum')
			item = util.getListItemByProperty(self.getControl(120),'id',fid)
		else:
			item = self.getControl(120).getSelectedItem()
			
		if item:
			link = item.getProperty('link')
			if link:
				return self.openLink(link)
			if not fid: fid = item.getProperty('id')
			topic = item.getProperty('topic')
			
		dialogs.openWindow(ThreadsWindow,"script-forumbrowser-threads.xml",fid=fid,topic=topic,parent=self,item=item,forumElements=forumElements)
		self.setPMCounts(FB.getPMCounts())
		return True
		
	def openLink(self,link):
		LOG('Forum is a link. Opening URL: ' + link)
		webviewer.getWebResult(link,dialog=True,browser=hasattr(FB,'browser') and FB.browser)
	
	def openSubscriptionsWindow(self,forumElements=None):
		fid = 'subscriptions'
		topic = T(32175)
		dialogs.openWindow(ThreadsWindow,"script-forumbrowser-threads.xml",fid=fid,topic=topic,parent=self,forumElements=forumElements)
		self.setPMCounts(FB.getPMCounts())
	
	def showOnlineUsers(self):
		s = dialogs.showActivitySplash(T(32356))
		try:
			users = FB.getOnlineUsers()
		finally:
			s.close()
		if isinstance(users,str):
			dialogs.showMessage(T(32357),users,success=False)
			return
		users.sort(key=lambda u: u['user'].lower())
		d = dialogs.OptionsChoiceMenu(T(32358))
		d.setContextCallback(self.showOnlineContext)
		for u in users:
			d.addItem(u.get('userid'),u.get('user'),u.get('avatar') or '',u.get('status'))
		d.getResult(close_on_context=False)
		
	def showOnlineContext(self,menu,item):
		d = dialogs.ChoiceMenu(T(32051))
		if FB.canPrivateMessage(): d.addItem('pm',T(32253) % item.get('disp'))
		if FB.canSearchAdvanced('UID'): d.addItem('search',T(32359).format(item.get('disp')))
		if FB.canGetUserInfo(): d.addItem('info',T(32360))
		result = d.getResult()
		if not result: return
		if result == 'pm':
			menu.close()
			openPostDialog(tid='private_messages',to=item.get('disp'))
		elif result == 'search':
			menu.close()
			searchUser(self,item.get('id'))
		elif result == 'info':
			self.showUserInfo(item.get('id'),item.get('disp'))

	def showUserInfo(self,uid,uname):
		s = dialogs.showActivitySplash(T(32361))
		try:
			user = FB.getUserInfo(uid,uname)
			if not user: return
			out = '[B]%s:[/B] [COLOR FF550000]%s[/COLOR]\n' % (T(32362),user.name)
			out += '[B]%s:[/B] [COLOR FF550000]%s[/COLOR]\n' % (T(32363),user.status)
			out += '[B]%s:[/B] [COLOR FF550000]%s[/COLOR]\n' % (T(32364),user.postCount)
			out += '[B]%s:[/B] [COLOR FF550000]%s[/COLOR]\n' % (T(32365),user.joinDate)
			if user.activity: out += '[B]%s:[/B] [COLOR FF550000]%s[/COLOR]\n' % (T(32366),user.activity)
			if user.lastActivityDate: out += '[B]%s:[/B] [COLOR FF550000]%s[/COLOR]\n' % (T(32367),user.lastActivityDate)
			for k,v in user.extras.items():
				out += '[B]' + k.title() + ':[/B] [COLOR FF550000]' + v + '[/COLOR]\n'
			dialogs.showMessage(T(32368),out,scroll=True)
		finally:
			s.close()
		
	def changeForum(self,forum=None):
		if not self.closeSubWindows(): return
		if not forum: forum = askForum()
		if not forum: return False
		url = None
		self.stopThread()
		fid = 'Unknown'
		if FB: fid = FB.getForumID()
		LOG('------------------ CHANGING FORUM FROM: %s TO: %s' % (fid,forum))
		self.startGetForumBrowser(forum,url=url)
		return True

	def closeSubWindows(self):
		for x in range(0,10):  # @UnusedVariable
			winid = xbmcgui.getCurrentWindowId()
			if winid > 0:
				window = xbmcgui.Window(winid)
				if window.getProperty('ForumBrowserMAIN'): return True
				#print winid
				xbmc.executebuiltin('Action(PreviousMenu)')
				xbmc.sleep(100)
			else:
				print winid
			
		return False
		
	def onFocus( self, controlId ):
		self.controlId = controlId
		
	def onClick( self, controlID ):
		if controlID == 200:
			self.stopThread()
			self.openSettings()
		elif controlID == 201:
			self.stopThread()
			self.openSubscriptionsWindow()
		elif controlID == 203:
			self.stopThread()
			self.openPMWindow()
		elif controlID == 202:
			return self.openForumsManager()
		elif controlID == 205:
			searchPosts(self)
		elif controlID == 206:
			searchThreads(self)
		elif controlID == 207:
			searchUser(self)
		elif controlID == 120:
			if not self.empty: self.stopThread()
			self.openThreadsWindow()
		elif controlID == 105:
			self.stopThread()
			self.setFocusId(202)
			return
		if windows.BaseWindow.onClick(self, controlID): return
		if self.empty: self.fillForumList()
	
	def onAction(self,action):
		if action == ACTION_CONTEXT_MENU:
			self.doMenu()
		elif action == ACTION_PARENT_DIR or action == ACTION_PARENT_DIR2:
			action = ACTION_PREVIOUS_MENU
		if action == ACTION_PREVIOUS_MENU:
			if util.Control.HasFocus(group=198):
				self.setFocusId(204)
				return
			elif util.Control.HasFocus(group=196):
				if self.getControl(120).size():
					self.setFocusId(120)
					return
			if not self.preClose(): return
		windows.BaseWindow.onAction(self,action)
	
	def openForumsManager(self,external=False):
		if self.forumsManagerWindowIsOpen: return
		self.forumsManagerWindowIsOpen = True
		size = 'manage'
		if external:
			methods = ('manage','small','full')
			if video.isPlaying():
				size = methods[getSetting('notify_method_video',0)]
			else:
				size = methods[getSetting('notify_method',0)]
			
		forumsManager(self,size=size,forumID=FB and FB.getForumID() or None)
		self.forumsManagerWindowIsOpen = False
		if not FB: return
		forumID = FB.getForumID()
		fdata = forumbrowser.ForumData(forumID,FORUMS_PATH)
		logo = fdata.urls.get('logo','')
		self.setLogo(logo)
		FB.theme = fdata.theme
		self.setTheme()
		
	def doMenu(self):
		item = self.getControl(120).getSelectedItem()
		d = dialogs.ChoiceMenu('Options',with_splash=True)
		try:
			if FB:
				if item:
					fid = item.getProperty('id')
					if FB.isForumSubscribed(fid,item.getProperty('subscribed')):
						if FB.canUnSubscribeForum(fid): d.addItem('unsubscribecurrentforum', T(32242))
					else:
						if FB.canSubscribeForum(fid): d.addItem('subscribecurrentforum', T(32243))
					if FB.canSearchAdvanced('FID'):
						d.addItem('search','%s [B][I]%s[/I][/B]' % (T(32371),item.getProperty('topic')[:30]))
				if FB.canGetOnlineUsers():
					d.addItem('online',T(32369))
				d.addItem('foruminfo',T(32370))
			d.addItem('refresh',T(32054))
			d.addItem('help',T(32244))
		finally:
			d.cancel()
		result = d.getResult()
		if result == 'subscribecurrentforum':
			if subscribeForum(fid): pass #item.setProperty('subscribed','subscribed') #commented out because can't change if we unsubscribe from subs view
		elif result == 'unsubscribecurrentforum':
			if unSubscribeForum(fid): item.setProperty('subscribed','')
		elif result == 'search':
			searchThreads(self,item.getProperty('id'))
		elif result == 'foruminfo':
			self.showForumInfo()			
		elif result == 'refresh':
			if FB:
				self.fillForumList()
			else:
				self.startGetForumBrowser()
		elif result == 'online':
			self.showOnlineUsers()
		elif result == 'help':
			dialogs.showHelp('forums')
		
	def showForumInfo(self):
		out = ''
		for k,v in FB.getForumInfo():
			out += u'[B]%s[/B]: [COLOR FF550000]%s[/COLOR][CR]' % (k.replace('_',' ').title(),v)
		dialogs.showMessage(T(32372),out,scroll=True)
				
	def preClose(self):
		if not getSetting('ask_close_on_exit') == 'true': return True
		if self.closed: return True
		return dialogs.dialogYesNo(T(32373),T(32373))
		
	def resetForum(self,hidelogo=True,no_theme=False):
		if not FB: return
		FB.setLogin(self.getUsername(),self.getPassword(),always=getSetting('always_login') == 'true',rules=loadForumSettings(FB.getForumID(),get_rules=True))
		self.setButtons()
		setSetting('last_forum',FB.getForumID())
		if no_theme: return
		if hidelogo: self.getControl(250).setImage('')
		self.setTheme()
		self.setLogoFromFile()
		
	def setLoggedIn(self):
		if not FB: return
		if FB.isLoggedIn():
			self.getControl(111).setColorDiffuse('FF00FF00')
		else:
			if FB.loginError:
				self.getControl(111).setColorDiffuse('FFFF0000')
			else:
				self.getControl(111).setColorDiffuse('FF555555')
		self.getControl(160).setLabel(FB.loginError)
		self.getControl(112).setVisible(FB.SSL)
		self.setButtons()
	
	def setButtons(self):
		loggedIn = FB.isLoggedIn()
		self.getControl(201).setEnabled(loggedIn and FB.hasSubscriptions())
		self.getControl(203).setEnabled(loggedIn and FB.hasPM())
		self.getControl(204).setEnabled(FB.canSearch())
		self.getControl(205).setEnabled(FB.canSearchPosts())
		self.getControl(206).setEnabled(FB.canSearchThreads())
		self.getControl(207).setEnabled(FB.canSearchAdvanced('UNAME'))
		
	def openSettings(self):
		#if not FB: return
		oldLogin = FB and self.getUsername() + self.getPassword() or ''
		doSettings(self)
		newLogin = FB and self.getUsername() + self.getPassword() or ''
		if not oldLogin == newLogin:
			self.resetForum(False)
			self.setPMCounts()
		self.setLoggedIn()
		self.resetForum(False)
		skin = util.getSavedTheme(current=THEME)
		if skin != THEME:
			dialogs.showMessage(T(32374),T(32375))
		forumbrowser.ForumPost.hideSignature = getSetting('hide_signatures',False)
		
######################################################################################
#
# PlayerMonitor
#
######################################################################################
class PlayerMonitor(xbmc.Player):
	def __init__(self,core=None):
		self.init()
		xbmc.Player.__init__(core)
		
	def init(self):
		self.interrupted = None
		self.isSelfPlaying = False
		self.stack = 0
		self.currentTime = None
		self.FBisRunning = True
		
	def start(self,path):
		interrupted = None
		if getSetting('video_return_interrupt',True):
			interrupted = video.current()
			self.getCurrentTime()
		self.interrupted = interrupted
		self.doPlay(path)
		
	def finish(self):
		self.FBisRunning = False
		if getSetting('video_stop_on_exit',True):
			self.doStop()
			if self.interrupted: self.wait()
		else:
			if getSetting('video_return_interrupt_after_exit',False) and self.interrupted:
				self.waitLong()
		LOG('PLAYER: Exiting')
		
	def doPlay(self,path):
		self.played = path
		self.isSelfPlaying = True
		if getSetting('video_start_preview',True):
			video.play(path, preview=True)
		else:
			self.play(path)
		
	def doStop(self):
		if not self.isSelfPlaying: return
		LOG('PLAYER: Stopping forum video')
		self.stop()
		
	def wait(self):
		LOG('PLAYER: Waiting for video to stop...')
		ct = 0
		while self.interrupted and not xbmc.abortRequested:
			xbmc.sleep(1000)
			ct+=1
			if ct > 19: break #Don't know if this is necessary, but it's here just in case.
			
	def waitLong(self):
		LOG('PLAYER: Waiting after FB close to resume interrupted video...')
		while self.interrupted and not xbmc.abortRequested:
			xbmc.sleep(1000)
		
	def playInterrupted(self):
		if not self.isSelfPlaying: return
		self.isSelfPlaying = False
		if self.interrupted:
			LOG('PLAYER: Playing interrupted video')
			if getSetting('video_bypass_resume_dialog',True) and self.currentTime:
				try:
					xbmc.sleep(1000)
					video.playAt(self.interrupted, *self.currentTime)
				except:
					ERROR('PLAYER: Failed manually resume video - sending to XBMC')
					xbmc.sleep(1000)
					video.play(self.interrupted)
			else:
				xbmc.sleep(1000)
				video.play(self.interrupted,getSetting('video_resume_as_preview',False))
		self.interrupted = None
		self.currentTime = None
	
	def onPlayBackStarted(self):
		if self.FBisRunning and getSetting('video_resume_as_preview',False) and not self.isSelfPlaying:
			xbmc.sleep(1000)
			xbmc.executebuiltin('Action(FullScreen)')
		
	def onPlayBackEnded(self):
		self.playInterrupted()
		
	def onPlayBackStopped(self):
		self.playInterrupted()
		
	def pauseStack(self):
		if not self.stack: video.pause()
		self.stack += 1
		
	def resumeStack(self):
		self.stack -= 1
		if self.stack < 1:
			self.stack = 0
			video.resume()
		
	def getCurrentTime(self):
		if not video.isPlaying(): return None
		offset = getSetting('video_resume_offset',0)
		val = self.getTime() - offset
		if val < 0: val = 0
		(ms,tsec) = math.modf(val)
		m, s = divmod(int(tsec), 60)
		h, m = divmod(m, 60)
		self.currentTime = (h,m,s,int(ms*1000))

# Functions -------------------------------------------------------------------------------------------------------------------------------------------
def appendSettingList(key,value,limit=0):
	slist = getSetting(key,[])
	if value in slist: slist.remove(value)
	slist.append(value)
	if limit: slist = slist[-limit:]
	setSetting(key,slist)
	
def getSearchDefault(setting,default='',with_global=True,heading=T(32376),new=T(32377),extra=None):
	if getSetting('show_search_history',True): 
		slist = getSetting(setting,[])
		slistDisplay = slist[:]
		if with_global:
			glist = getSetting('last_search',[])
			glist.reverse()
			for g in glist:
				if not g in slist:
					slistDisplay.insert(0,'[COLOR FFAAAA00]%s[/COLOR]' % g)
					slist.insert(0,g)
	else:
		slist = []
		slistDisplay = []
		
	if slist or extra:
		slist.reverse()
		slistDisplay.reverse()
		if extra:
			for eid,edisplay in extra:
				slistDisplay.insert(0,'[[COLOR FF009999][B]%s[/B][/COLOR]]' % edisplay)
				slist.insert(0,eid)
		slistDisplay.insert(0,'[[COLOR FF00AA00][B]%s[/B][/COLOR]]' % new)
		slist.insert(0,'')
		idx = xbmcgui.Dialog().select(heading,slistDisplay)
		if idx < 0: return None
		elif idx > 0: default = slist[idx]
	return default
		
def searchPosts(parent,tid=None):
	default = getSearchDefault('last_post_search')
	if default == None: return
	terms = dialogs.doKeyboard(T(32330),default)
	if not terms: return
	appendSettingList('last_post_search',terms,10)
	appendSettingList('last_search',terms,10)
	dialogs.openWindow(RepliesWindow,"script-forumbrowser-replies.xml" ,search_terms=terms,topic=T(32378),tid=tid,parent=parent)
	
def searchThreads(parent,fid=None):
	default = getSearchDefault('last_thread_search')
	if default == None: return
	terms = dialogs.doKeyboard(T(32330),default)
	if not terms: return
	appendSettingList('last_thread_search',terms,10)
	appendSettingList('last_search',terms,10)
	dialogs.openWindow(ThreadsWindow,"script-forumbrowser-threads.xml",search_terms=terms,topic=T(32379),fid=fid,parent=parent)

def searchUser(parent,uid=None):
	uname = None
	if not uid:
		default = getSearchDefault('last_search_user',with_global=False,heading=T(32380),new=T(32381))
		if default == None: return
		if default:
			uname = default
		else:
			uname = dialogs.doKeyboard(T(32382),default)
		if not uname: return
		appendSettingList('last_search_user',uname,10)
	extra = None
	ct = FB.canGetUserThreads()
	if ct:
		if not extra: extra = []
		extra.append(('@!RECENTTHREADS!@',T(32383)))
	ct = FB.canGetUserPosts()
	if ct:
		if not extra: extra = []
		extra.append(('@!RECENT!@',T(32384)))
		
	default = getSearchDefault('last_user_search',extra=extra)
	if default == None: return
	topic = T(32385)
	if default == '@!RECENT!@':
		terms = default
		topic = T(32384)
	elif default == '@!RECENTTHREADS!@':
		terms = default
		dialogs.openWindow(ThreadsWindow,"script-forumbrowser-threads.xml",search_terms=terms,search_name=uname,topic=T(32383),parent=parent)
		return 
	else:
		terms = dialogs.doKeyboard(T(32330),default)
		if not terms: return
		appendSettingList('last_user_search',terms,10)
		appendSettingList('last_search',terms,10)
	dialogs.openWindow(RepliesWindow,"script-forumbrowser-replies.xml" ,search_terms=terms,topic=topic,uid=uid,search_name=uname,parent=parent)

def getCachedLogo(logo,forumID,clear=False):
	root, ext = os.path.splitext(logo) #@UnusedVariable
	logopath = os.path.join(CACHE_PATH,forumID + ext or '.jpg')
	if not ext:
		if not os.path.exists(logopath): logopath = os.path.join(CACHE_PATH,forumID + '.png')
		if not os.path.exists(logopath): logopath = os.path.join(CACHE_PATH,forumID + '.gif')
	if os.path.exists(logopath):
		if clear: os.remove(logopath)
		return True, logopath
	return False, logopath

def getForumSetting(forumID,key,default=None):
	data = loadForumSettings(forumID)
	return util._processSetting(data.get(key),default)

def loadForumSettings(forumID,get_rules=False,get_both=False):
	fsPath = os.path.join(FORUMS_SETTINGS_PATH,forumID)
	if not os.path.exists(fsPath):
		if get_both:
			return {},{}
		else:
			return {}
	fsFile = open(fsPath,'r')
	lines = fsFile.read()
	fsFile.close()
	try:
		ret = {}
		rules = {}
		mode = 'settings'
		for l in lines.splitlines():
			if l.startswith('[rules]'):
				if not get_rules and not get_both: break
				mode = 'rules'
			else:
				k,v = l.split('=',1)
				if mode == 'rules':
					rules[k] = v.strip()
				else:
					ret[k] = v.strip()
	except:
		ERROR('Failed to get settings for forum: %s' % forumID)
		if get_both:
			return {},{}
		else:
			return {}
		
	if get_rules:
		return rules
	
	ret['username'] = ret.get('username','')
	ret['password'] = passmanager.decryptPassword(ret['username'] or '?', ret.get('password',''))
	ret['notify'] = ret.get('notify') == 'True'
		
	if get_both:
		return ret,rules
	else:
		return ret

def saveForumSettings(forumID,**kwargs):
	username=kwargs.pop('username',None)
	password=kwargs.pop('password',None)
	notify=kwargs.pop('notify',None)
	rules=kwargs.pop('rules',None)
	
	data, rules_data = loadForumSettings(forumID,get_both=True) or ({},{})
	#data.update(kwargs)
	if rules: rules_data.update(rules)
	if data: data.update(kwargs)
	
	if notify == None: data['notify'] = data.get('notify')  or False
	else: data['notify'] = notify
	
	if username == None: data['username'] = data.get('username') or ''
	else: data['username'] = username
	
	if password == None: data['password'] = data.get('password') or ''
	else: data['password'] = password
	
	try:
		password = passmanager.encryptPassword(data['username'] or '?', data['password'])
		data['password'] = password
		out = []
		for k,v in data.items():
			out.append('%s=%s' % (k,v))
		if rules_data:
			out.append('[rules]')
			for k,v in rules_data.items():
				if v != None: out.append('%s=%s' % (k,v))
		fsFile = open(os.path.join(FORUMS_SETTINGS_PATH,forumID),'w')
		#fsFile.write('username=%s\npassword=%s\nnotify=%s' % (data['username'],password,data['notify']))
		fsFile.write('\n'.join(out))
		fsFile.close()
		return True
	except:
		ERROR('Failed to save forum settings for: %s' % forumID)
		return False

def addParserRule(forumID,key,value):
	if key.startswith('extra.'):
		saveForumSettings(rules={key:value})
	else:
		rules = loadForumSettings(get_rules=True)
		if key == 'head':
			vallist = rules.get('head') and rules['head'].split(';&;') or []
		elif key == 'tail':
			vallist = rules.get('tail') and rules['tail'].split(';&;') or []
		if not value in vallist: vallist.append(value)
		saveForumSettings(rules={key:';&;'.join(vallist)})

def removeParserRule(forumID,key,value=None):
	if key.startswith('extra.'):
		saveForumSettings(rules={key:None})
	else:
		rules = loadForumSettings(get_rules=True)
		if key == 'head':
			vallist = rules.get('head') and rules['head'].split(';&;') or []
		elif key == 'tail':
			vallist = rules.get('tail') and rules['tail'].split(';&;') or []
		if value in vallist: vallist.pop(vallist.index(value))
		saveForumSettings(rules={key:';&;'.join(vallist)})
		
def listForumSettings():
	return os.listdir(FORUMS_SETTINGS_PATH)

def getForumPath(forumID,just_path=False):
	path = os.path.join(FORUMS_PATH,forumID)
	if os.path.exists(path):
		if just_path: return FORUMS_PATH
		return path
	path = os.path.join(FORUMS_STATIC_PATH,forumID)
	if os.path.exists(path):
		if just_path: return FORUMS_STATIC_PATH
		return path
	return None
	
def fidSortFunction(fid):
	if fid[:3] in ['TT.','FR.','GB.']: return fid[3:]
	return fid

def askForum(just_added=False,just_favs=False,caption=T(32386),forumID=None,hide_extra=False):
	favs = getFavorites()
	flist_tmp = os.listdir(FORUMS_PATH)
	rest = sorted(flist_tmp,key=fidSortFunction)
	if favs:
		for f in favs:
			if f in rest: rest.pop(rest.index(f))
		favs.append('')
	if just_favs:
		if not favs: return None
		whole = favs[:-1]
	elif just_added:
		whole = flist_tmp
	else:
		whole = favs + rest
	menu = dialogs.ImageChoiceMenu(caption)
	final = []
	for f in whole:
		if not f in final: final.append(f)
	for f in final:
		if not f.startswith('.'):
			if not f:
				menu.addSep()
				continue
			path = getForumPath(f,just_path=True)
			if not path: continue
			if not os.path.isfile(os.path.join(path,f)): continue
			fdata = forumbrowser.ForumData(f,path)
			name = fdata.name
			desc = fdata.description
			logo = fdata.urls.get('logo','')
			exists, logopath = getCachedLogo(logo,f)
			if exists: logo = logopath
			hc = 'FF' + fdata.theme.get('header_color','FFFFFF')
			desc = '[B]%s[/B]: [COLOR FFFF9999]%s[/COLOR]' % ( T(32290) , (desc or 'None') )
			interface = ''
			if f.startswith('TT.'):
				#desc += '\n\n[B]Forum Interface[/B]: [COLOR FFFF9999]Tapatalk[/COLOR]'
				interface = 'TT'
			elif f.startswith('FR.'):
				#desc += '\n\n[B]Forum Interface[/B]: [COLOR FFFF9999]Forumrunner[/COLOR]'
				interface = 'FR'
			elif f.startswith('GB.'):
				#desc += '\n\n[B]Forum Interface[/B]: [COLOR FFFF9999]Parser Browser[/COLOR]'
				interface = 'GBalt'
			menu.addItem(f, name,logo,desc,bgcolor=hc,interface=interface)

	#if getSetting('experimental',False) and not just_added and not just_favs and not forumID and not hide_extra:
	#	menu.addItem('experimental.general','Experimental General Browser','forum-browser-logo-128.png','')
	forum = menu.getResult('script-forumbrowser-forum-select.xml',select=forumID)
	return forum

def setLogins(force_ask=False,forumID=None):
	if not forumID:
		if FB: forumID = FB.getForumID()
	if not forumID or force_ask: forumID = askForum(forumID=forumID)
	if not forumID: return
	data = loadForumSettings(forumID)
	user = ''
	if data: user = data.get('username','')
	user = dialogs.doKeyboard(T(32201),user)
	if user is None: return
	password = ''
	if data: password = data.get('password','')
	password = dialogs.doKeyboard(T(32202),password,True)
	if password is None: return
	if not user and not password:
		dialogs.showMessage(T(32387),T(32388))
	else:
		saveForumSettings(forumID,username=user,password=password)
		dialogs.showMessage(T(32389),T(32390))
		
def setLoginPage(forumID=None):
	if not forumID:
		if FB: forumID = FB.getForumID()
	if not forumID: return
	
	fdata = forumbrowser.ForumData(forumID,FORUMS_PATH)
	url = fdata.forumURL()
	if not url: return
	LOG('Open Forum Main Page - URL: ' + url)
	url = browseWebURL(url)
	if url == None: return
	saveForumSettings(forumID,rules={'login_url':url})
	
def browseWebURL(url):
	(url,html) = webviewer.getWebResult(url,dialog=True) #@UnusedVariable
	if not url: return None
	yes = dialogs.dialogYesNo(T(32391),str(url),'',T(32392))
	if not yes: return None
	return url
	
###########################################################################################
## - Version Conversion
###########################################################################################

def updateOldVersion():
	lastVersion = getSetting('last_version') or '0.0.0'
	if StrictVersion(__version__) <= StrictVersion(lastVersion): return False
	setSetting('last_version',__version__)
	LOG('NEW VERSION (OLD: %s): Converting any old formats...' % lastVersion)
	if StrictVersion(lastVersion) < StrictVersion('1.1.4'):
		convertForumSettings_1_1_4()
	if StrictVersion(lastVersion) < StrictVersion('1.3.5') and not lastVersion == '0.0.0':
		if getSetting('use_skin_mods',False):
			dialogs.showMessage(T(32393),T(32394))
			mods.installSkinMods(update=True)
	if lastVersion == '0.0.0': doFirstRun()
	return True

def doFirstRun():
	LOG('EXECUTING FIRST RUN FUNCTIONS')
	xbmc_org = os.path.join(FORUMS_PATH,'TT.xbmc.org')
	if not os.path.exists(xbmc_org):
		local = os.path.join(FORUMS_STATIC_PATH,'TT.xbmc.org')
		if os.path.exists(local): open(xbmc_org,'w').write(open(local,'r').read())

def convertForumSettings_1_1_4():
	forums = os.listdir(FORUMS_PATH) + os.listdir(FORUMS_STATIC_PATH)
	for f in forums:
		username = getSetting('login_user_' + f.replace('.','_'))
		key = 'login_pass_' + f.replace('.','_')
		password = passmanager.getPassword(key, username)
		if username or password:
			LOG('CONVERTING FORUM SETTINGS: %s' % f)
			saveForumSettings(f,username=username,password=password)
			setSetting('login_user_' + f.replace('.','_'),'')
			setSetting('login_pass_' + f.replace('.','_'),'')

## - Version Conversion End ###############################################################

def toggleNotify(forumID=None):
	notify = True
	if not forumID and FB: forumID = FB.getForumID()
	if not forumID: return None
	data = loadForumSettings(forumID)
	if data: notify = not data['notify']
	saveForumSettings(forumID,notify=notify)
	return notify
		
def doSettings(window=None):
	w = dialogs.openWindow(xbmcgui.WindowXMLDialog,'script-forumbrowser-overlay.xml',return_window=True,modal=False,theme='Default')
	try:
		util.__addon__.openSettings()
	finally:
		w.close()
		del w
	global DEBUG
	DEBUG = getSetting('debug',False)
	signals.DEBUG = DEBUG
	tapatalk.DEBUG = DEBUG
	if FB: FB.MC.resetRegex()
	if mods.checkForSkinMods():
		setSetting('refresh_skin',True)
	forumbrowser.ForumPost.hideSignature = getSetting('hide_signatures',False)

def forumsManager(window=None,size='full',forumID=None):
	if size == 'small':
		xmlFile = 'script-forumbrowser-notifications-small.xml'
	elif size == 'manage':
		xmlFile = 'script-forumbrowser-manage-forums.xml'
	else:
		xmlFile = 'script-forumbrowser-notifications.xml'
		
	if FB and window and forumID: canLogin = FB.canLogin()
	
	dialogs.openWindow(NotificationsDialog,xmlFile,theme='Default',forumsWindow=window,forumID=forumID)
	
	if FB and window and forumID:
		if forumID == FB.getForumID() and not canLogin:
			window.resetForum()
			if FB.canLogin():
				window.fillForumList()
	
def manageParserRules(forumID=None,rules=None):
	if not forumID:
		if FB: forumID = FB.getForumID()
	if not forumID: return
	returnRules = False
	if rules != None:
		returnRules = True
	else:
		rules = loadForumSettings(forumID,get_rules=True)
	choice = True
	while choice:
		menu = dialogs.OptionsChoiceMenu(T(32395))
		keys = rules.keys()
		keys.sort()
		for k in keys:
			v = rules[k]
			if k.startswith('extra.'):
				if v: menu.addItem(k,'[%s] ' % T(32396) + k.split('.')[-1],display2=v)
			elif k == 'login_url':
				if v: menu.addItem(k,T(32398),display2=texttransform.textwrap.fill(v,30))
			else:
				if v:
					for i in v.split(';&;'):
						if i: menu.addItem(k + '.' + i,'[%s %s] ' % (k.upper(),T(32397)) + i)
		menu.addItem('add','[COLOR FFFFFF00]+ %s[/COLOR]' % T(32399))
		menu.addItem('share','[COLOR FF00FFFF]%s->[/COLOR]' % T(32400),display2='Share rules to the Forum Browser online database')
		menu.addItem('save',returnRules and '[COLOR FF00FF00]%s[/COLOR]' % T(32052) or '[COLOR FF00FF00]<- %s[/COLOR]' % T(32401))
		choice = menu.getResult()
		if not choice: return
		if choice == 'save':
			for k in rules.keys():
				if not rules[k]: rules[k] = None
			if returnRules: return rules
			saveForumSettings(forumID,rules=rules)
			continue
		elif choice == 'share':
			shareForumRules(forumID,rules)
			continue
		elif choice == 'add':
			menu = dialogs.ChoiceMenu(T(32402))
			menu.addItem('extra',T(32317))
			menu.addItem('head',T(32403))
			menu.addItem('tail',T(32404))
			rtype = menu.getResult()
			if not rtype: continue
			if rtype == 'extra':
				name = dialogs.doKeyboard(T(32405))
				if not name: continue
				default = ''
				if 'extra.' + name in rules: default = rules['extra.' + name]
				val = dialogs.doKeyboard(T(32406),default)
				if not val: continue
				rules['extra.' + name] = val
			else:
				val = dialogs.doKeyboard(T(32407))
				if not val: continue
				vallist = rules.get(rtype) and rules[rtype].split(';&;') or []
				if not val in vallist:
					vallist.append(val)
					rules[rtype] = ';&;'.join(vallist)
			continue
		menu = dialogs.ChoiceMenu(T(32408))
		if not choice == 'login_url': menu.addItem('edit',T(32232))
		menu.addItem('remove',T(32409))
		choice2 = menu.getResult()
		if not choice2: continue
		if choice2 == 'remove':
			if choice.startswith('extra.') or choice == 'login_url':
				rules[choice] = None
			else:
				rtype, val = choice.split('.')
				vallist = rules.get(rtype) and rules[rtype].split(';&;') or []
				if val in vallist:
					vallist.pop(vallist.index(val))
					rules[rtype] = ';&;'.join(vallist)
		else:
			if choice.startswith('extra.') or choice == 'login_url':
				val = rules[choice]
#				if choice == 'login_url':
#					edit = dialogs.doKeyboard('Edit',val)
#				else:
				edit = dialogs.doKeyboard(T(32232),val)
				if edit == None: continue
				rules[choice] = edit
			else:
				rtype, val = choice.split('.')
				edit = dialogs.doKeyboard(T(32232),val)
				if edit == None: continue
				vallist = rules.get(rtype) and rules[rtype].split(';&;') or []
				if val in vallist:
					vallist.pop(vallist.index(val))
					vallist.append(edit)
					rules[rtype] = ';&;'.join(vallist)

def shareForumRules(forumID,rules):
	odb = forumbrowser.FBOnlineDatabase()
	odbrules = odb.getForumRules(forumID)
	if odbrules:
		out = []
		for k,v in odbrules.items():
			if k.startswith('extra.'):
				out.append('[%s] ' % T(32396) + k.split('.',1)[-1] + ' = ' + v)
			elif k == 'head':
				out.append('[%s] = ' % T(32410) + ', '.join(v.split(';&;')))
			elif k == 'tail':
				out.append('[%s] = ' % T(32411) + ', '.join(v.split(';&;')))
		dialogs.showMessage(T(32412),'%s\n\n%s' % (T(32413),'[CR]'.join(out)),scroll=True)
		yes = dialogs.dialogYesNo(T(32414),T(32415))
		if not yes: return
	setRulesODB(forumID, rules)
	
def registerForum():
	url = FB.getRegURL()
	LOG('Registering - URL: ' + url)
	webviewer.getWebResult(url,dialog=True)

def addFavorite(forum=None):
	if not forum:
		if not FB: return
		forum = FB.getForumID()
	favs = getFavorites()
	if forum in favs: return
	favs.append(forum)
	setSetting('favorites','*:*'.join(favs))
	dialogs.showMessage(T(32416),T(32418))
	
def removeFavorite(forum=None):
	if not forum: forum = askForum(just_favs=True)
	if not forum: return
	favs = getFavorites()
	if not forum in favs: return
	favs.pop(favs.index(forum))
	setSetting('favorites','*:*'.join(favs))
	dialogs.showMessage(T(32417),T(32419))
	
def getFavorites():
	favs = getSetting('favorites')
	if favs:
		favs = favs.split('*:*')
	else:
		favs = []
	return favs
	
def selectForumCategory(with_all=False):
	d = dialogs.ChoiceMenu(T(32420))
	if with_all:
		d.addItem('search',T(32421))
		d.addItem('all',T(32422))
	for x in range(0,17):
		d.addItem(str(x), str(T(32500 + x)))
	return d.getResult()

def addForum(current=False):
	dialog = xbmcgui.DialogProgress()
	dialog.create(T(32423))
	dialog.update(0,T(32424))
	info = None
	user = None
	password=None
	try:
		if current:
			if not FB: return
			ftype = FB.prefix[:2]
			forum = FB.forum
			url = orig = FB._url
			url = tapatalk.testForum(url)
			if url: pageURL = url.split('/mobiquo/',1)[0]
			if not url:
				from lib.forumbrowser import forumrunner
				url = forumrunner.testForum(orig)
			if url: pageURL = url.split('/forumrunner/',1)[0]
			if not url:
				dialogs.showMessage(T(32257),T(32425),success=False)
				return
		else:
			forum = dialogs.doKeyboard(T(32426))
			if forum == None: return
			forum = forum.lower()
			dialog.update(10,'%s: Tapatalk' % T(32427))
			url = tapatalk.testForum(forum)
			ftype = ''
			label = ''
			if url:
				ftype = 'TT'
				label = 'Tapatalk'
				pageURL = url.split('/mobiquo/',1)[0]
			else:
				dialog.update(13,'%s: Forumrunner' % T(32427))
				from lib.forumbrowser import forumrunner #@Reimport
				url = forumrunner.testForum(forum)
				if url:
					ftype = 'FR'
					label = 'Forumrunner'
					pageURL = url.split('/forumrunner/',1)[0]
					
			if not url:
				dialog.update(16,'%s: Parser Browser' % T(32427))
				yes = dialogs.dialogYesNo(T(32428),T(32429),'',T(32430))
				if yes:
					user = dialogs.doKeyboard(T(32201))
					if user: password = dialogs.doKeyboard(T(32202),hidden=True)
				from lib.forumbrowser import genericparserbrowser
				url,info,parser = genericparserbrowser.testForum(forum,user,password)
				if url:
					ftype = 'GB'
					label = 'Parser Browser (%s)' % parser.getForumTypeName()
					if url.startswith('http'):
						pre,post = url.split('://',1)
					else:
						pre = 'http'
						post = url
					post = post.split('/',1)[0]
					pageURL = pre + '://' + post
			
			if not url:
				dialogs.showMessage(T(32257),T(32431),success=False)
				return
		
			dialogs.showMessage(T(32432),T(32433).format(forum),'[CR]%s: %s' % (T(32402),label),'[CR]'+ url,success=True)
			if ftype == 'GB':
				if parser.getForumTypeName().lower() == 'generic':
					dialogs.showInfo('parserbrowser-generic')
				else:
					dialogs.showInfo('parserbrowser-normal')
			forum = url.split('http://',1)[-1].split('/',1)[0]
			
		dialog.update(20,T(32434))
		if not info: info = forumbrowser.HTMLPageInfo(pageURL)
		tmp_desc = info.description(info.title(''))
		tmp_desc = texttransform.convertHTMLCodes(tmp_desc).strip()
		images = info.images()
		dialog.update(30,T(32435))
		desc = dialogs.doKeyboard(T(32435),default=tmp_desc,mod=True)
		if not desc: desc = tmp_desc
		dialog.update(40,T(32436))
		logo = chooseLogo(forum,images)
		LOG('Adding Forum: %s at URL: %s' % (forum,url))
		name = forum
		if name.startswith('www.'): name = name[4:]
		if name.startswith('forum.'): name = name[6:]
		if name.startswith('forums.'): name = name[7:]
		forumID = ftype + '.' + name
		saveForum(ftype,forumID,name,desc,url,logo)
		if user and password: saveForumSettings(forumID,username=user,password=password)
		dialog.update(60,T(32437))
		if not (not current and ftype == 'GB'): addForumToOnlineDatabase(name,url,desc,logo,ftype,dialog=dialog)
		return forumID
	finally:
		dialog.close()
	
def saveForum(ftype,forumID,name,desc,url,logo,header_color="FFFFFF"): #TODO: Do these all the same. What... was I crazy?
	if ftype == 'TT':
		open(os.path.join(FORUMS_PATH,forumID),'w').write('#%s\n#%s\nurl:tapatalk_server=%s\nurl:logo=%s\ntheme:header_color=%s' % (name,desc,url,logo,header_color))
	elif ftype == 'FR':
		open(os.path.join(FORUMS_PATH,forumID),'w').write('#%s\n#%s\nurl:forumrunner_server=%s\nurl:logo=%s\ntheme:header_color=%s' % (name,desc,url,logo,header_color))
	else:
		open(os.path.join(FORUMS_PATH,forumID),'w').write('#%s\n#%s\nurl:server=%s\nurl:logo=%s\ntheme:header_color=%s' % (name,desc,url,logo,header_color))
	
def addForumFromOnline(stay_open_on_select=False):
	odb = forumbrowser.FBOnlineDatabase()
	res = True
	added = None
	while res:
		res = selectForumCategory(with_all=True)
		if not res: return added
		cat = res
		terms = None
		if cat == 'all': cat = None
		if cat == 'search':
			terms = dialogs.doKeyboard(T(32330))
			if not terms: continue
			cat = None
		splash = dialogs.showActivitySplash(T(32438))
		try:
			flist = odb.getForumList(cat,terms)
		finally:
			splash.close()
		if not flist:
			dialogs.showMessage(T(32439),T(32440))
			continue
		if cat and cat.isdigit():
			caption = '[COLOR FF9999FF]'+str(T(32500 + int(cat)))+'[/COLOR]'
		else:
			caption = '[COLOR FF9999FF]All[/COLOR]'
		menu = dialogs.ImageChoiceMenu(caption)
		for f in flist:
			interface = f.get('type')
			rf=ra=''
			if interface == 'GB':
				rf = {'1':'FFFF0000','2':'FFFFFF00','3':'FF00FF00'}.get(f.get('rating_function'),'')
				ra = {'1':'FFFF0000','2':'FFFFFF00','3':'FF00FF00'}.get(f.get('rating_accuracy'),'')
			desc = f.get('desc','None') or 'None'
			desc = '[B]{0}[/B]: [COLOR FFFF9999]{1}[/COLOR][CR][CR][B]{2}[/B]: [COLOR FFFF9999]{3}[/COLOR]'.format(T(32441),str(T(32500 + f.get('cat',0))),T(32290),desc)
			bgcolor = formatHexColorToARGB(f.get('header_color','FFFFFF'))
			menu.addItem(f, f.get('name'), f.get('logo'), desc,bgcolor=bgcolor,interface=interface,function=rf,accuracy=ra)
		f = True
		while f:
			f = menu.getResult('script-forumbrowser-forum-select.xml',filtering=True)
			if f:
				forumID = doAddForumFromOnline(f,odb)
				added = forumID
				if not stay_open_on_select: return added
	return added
	
def formatHexColorToARGB(hexcolor):
	try:
		binascii.unhexlify(hexcolor)
		return 'FF' + hexcolor
	except:
		return "FFFFFFFF"
		
def doAddForumFromOnline(f,odb):
	if not isinstance(f,dict): return
	forumID = f['type']+'.'+f['name']
	saveForum(f['type'],forumID,f['name'],f.get('desc',''),f['url'],f.get('logo',''),f.get('header_color',''))
	rules = isinstance(f,dict) and odb.getForumRules(f['type']+'.'+f['name']) or {}
	old_rules = loadForumSettings(forumID,get_rules=True)
	if rules and not old_rules: saveForumSettings(forumID,rules=rules)
	dialogs.showMessage(T(32416),'{0}: {1}'.format(T(32442),f['name']))
	return forumID
	
def setRulesODB(forumID,rules):
	odb = forumbrowser.FBOnlineDatabase()
	out = []
	for k,v in rules.items():
		if k and v:
			out.append(k + '=' + v)
	result = str(odb.setRules(forumID,'\n'.join(out)))
	LOG('Updating ODB Rules: ' + result)
	if result == '1':
		dialogs.showMessage(T(32052),T(32443),success=True)
	else:
		dialogs.showMessage(T(32257),T(32444),error=True)
	
def addCurrentForumToOnlineDatabase(forumID=None):
	if not forumID:
		if FB: forumID = FB.getForumID()
	if not forumID: return
	fdata = forumbrowser.ForumData(forumID,FORUMS_PATH)
	url = fdata.urls.get('tapatalk_server',fdata.urls.get('forumrunner_server',fdata.urls.get('server',FB and FB._url or '')))
	if not url: raise Exception('No URL')
	addForumToOnlineDatabase(fdata.name,url,fdata.description,fdata.urls.get('logo'),forumID[:2],header_color=fdata.theme.get('header_color','FFFFFF'))
	
def addForumToOnlineDatabase(name,url,desc,logo,ftype,header_color='FFFFFF',dialog=None):
	if not dialogs.dialogYesNo(T(32445),T(32446)): return
	LOG('Adding Forum To Online Database: %s at URL: %s' % (name,url))
	frating = arating = '0'
	if ftype == 'GB':
		frating,arating = askForumRating()
		if not frating:
			dialogs.showMessage(T(32257),T(32447),success=False)
			return
		
	cat = selectForumCategory() or '0'
	splash = None
	if dialog:
		dialog.update(80,T(32448))
	else:
		splash = dialogs.showActivitySplash(T(32448))
		
	try:
		odb = forumbrowser.FBOnlineDatabase()
	finally:
		if splash: splash.close()
		
	msg = odb.addForum(name, url, logo, desc, ftype, cat, rating_function=frating, rating_accuracy=arating, header_color=header_color)
	if msg == 'OK':
		dialogs.showMessage(T(32416),T(32451),success=True)
	elif msg =='EXISTS':
		dialogs.showMessage(T(32449),T(32452),success=True)
	else:
		dialogs.showMessage(T(32450),T(32453) + ':',str(msg),success=False)
		LOG('Forum Not Added: ' + str(msg))
	
def askForumRating():
	d = dialogs.ChoiceMenu(T(32454))
	d.addItem('3',T(32455))
	d.addItem('2',T(32456))
	d.addItem('1',T(32457))
	frating = d.getResult()
	if not frating: return None,None
	d = dialogs.ChoiceMenu(T(32458))
	d.addItem('3',T(32459))
	d.addItem('2',T(32460))
	d.addItem('1',T(32461))
	arating = d.getResult()
	if not arating: return None,None
	return frating,arating
	
def chooseLogo(forum,image_urls,keep_colors=False,splash=None):
	#if not image_urls: return
	base = '.'.join(forum.split('.')[-2:])
	top = []
	middle = []
	bottom = []
	for u in image_urls:
		if 'logo' in u.lower() and base in u:
			top.append(u)
		elif base in u:
			middle.append(u)
		else:
			bottom.append(u)
	image_urls = ['http://%s/favicon.ico' % forum] + top + middle + bottom
	menu = dialogs.ImageChoiceMenu(T(32436))
	for url in image_urls: menu.addItem(url, url, url)
	if splash: splash.close()
	url = menu.getResult(keep_colors=keep_colors)
	return url or ''
		
def getCurrentLogo(forumID=None,logo=None):
	if not logo:
		if FB: logo = FB.urls.get('logo')
	if not logo: return
	if not forumID: forumID = FB.getForumID()
	if not forumID: return
	root, ext = os.path.splitext(logo) #@UnusedVariable
	logopath = os.path.join(CACHE_PATH,forumID + (ext or '.jpg'))
	if os.path.exists(logopath): return logopath
	logopath = os.path.join(CACHE_PATH,forumID + '.png')
	if os.path.exists(logopath): return logopath
	logopath = os.path.join(CACHE_PATH,forumID + '.gif')
	if os.path.exists(logopath): return logopath
	logopath = os.path.join(CACHE_PATH,forumID + '.ico')
	if os.path.exists(logopath): return logopath
	return logo

def askColor(forumID=None,color=None,logo=None):
	#fffaec
	if not forumID:
		if FB: forumID = FB.getForumID()
	if not forumID: return
	fdata = forumbrowser.ForumData(forumID,FORUMS_PATH)
	color = color or fdata.theme.get('header_color')
	logo = logo or getCurrentLogo(forumID,fdata.urls.get('logo'))
	w = dialogs.openWindow(dialogs.ColorDialog,'script-forumbrowser-color-dialog.xml',return_window=True,image=logo,hexcolor=color,theme='Default')
	hexc = w.hexValue()
	del w
	return hexc
	
def setForumColor(color,forumID=None):
	if not color: return False
	if forumID:
		fid = forumID
	else:
		fid = FB.getForumID()
	fdata = forumbrowser.ForumData(fid,FORUMS_PATH)
	fdata.theme['header_color'] = color
	if FB and FB.getForumID() == forumID: FB.theme['header_color'] = color
	fdata.writeData()
	dialogs.showMessage(T(32052),T(32462))
	return True

def updateThemeODB(forumID=None):
	if not forumID:
		forumID = FB.getForumID()
	odb = forumbrowser.FBOnlineDatabase()
	fdata = forumbrowser.ForumData(forumID,FORUMS_PATH)
	splash = dialogs.showActivitySplash(T(32448))
	try:
		result = str(odb.setTheme(forumID[3:],fdata.theme))
	finally:
		splash.close()
	LOG('Updating ODB Theme: ' + result)
	if result == '1':
		dialogs.showMessage(T(32052),T(32463))
	else:
		dialogs.showMessage(T(32257),T(32464))
	
def removeForum(forum=None):
	if forum: return doRemoveForum(forum)
	forum = True
	while forum:
		forum = askForum(caption=T(32465),hide_extra=True)
		if not forum: return
		doRemoveForum(forum)
		
def doRemoveForum(forum):
	yes = dialogs.dialogYesNo(T(32466),T(32467),'',forum[3:])
	if not yes: return False
	path = os.path.join(FORUMS_PATH,forum)
	if not os.path.exists(path): return
	os.remove(path)
	dialogs.showMessage(T(32417),T(32468))
	return True
	
def clearDirFiles(filepath):
	if not os.path.exists(filepath): return
	for f in os.listdir(filepath):
		f = os.path.join(filepath,f)
		if os.path.isfile(f): os.remove(f)
		
def getFile(url,target=None):
	if not target: return #do something else eventually if we need to
	req = urllib2.urlopen(url)
	open(target,'w').write(req.read())
	req.close()

def getLanguage():
		langs = ['Afrikaans', 'Albanian', 'Amharic', 'Arabic', 'Armenian', 'Azerbaijani', 'Basque', 'Belarusian', 'Bengali', 'Bihari', 'Breton', 'Bulgarian', 'Burmese', 'Catalan', 'Cherokee', 'Chinese', 'Chinese_Simplified', 'Chinese_Traditional', 'Corsican', 'Croatian', 'Czech', 'Danish', 'Dhivehi', 'Dutch', 'English', 'Esperanto', 'Estonian', 'Faroese', 'Filipino', 'Finnish', 'French', 'Frisian', 'Galician', 'Georgian', 'German', 'Greek', 'Gujarati', 'Haitian_Creole', 'Hebrew', 'Hindi', 'Hungarian', 'Icelandic', 'Indonesian', 'Inuktitut', 'Irish', 'Italian', 'Japanese', 'Javanese', 'Kannada', 'Kazakh', 'Khmer', 'Korean', 'Kurdish', 'Kyrgyz', 'Lao', 'Latin', 'Latvian', 'Lithuanian', 'Luxembourgish', 'Macedonian', 'Malay', 'Malayalam', 'Maltese', 'Maori', 'Marathi', 'Mongolian', 'Nepali', 'Norwegian', 'Occitan', 'Oriya', 'Pashto', 'Persian', 'Polish', 'Portuguese', 'Portuguese_Portugal', 'Punjabi', 'Quechua', 'Romanian', 'Russian', 'Sanskrit', 'Scots_Gaelic', 'Serbian', 'Sindhi', 'Sinhalese', 'Slovak', 'Slovenian', 'Spanish', 'Sundanese', 'Swahili', 'Swedish', 'Syriac', 'Tajik', 'Tamil', 'Tatar', 'Telugu', 'Thai', 'Tibetan', 'Tonga', 'Turkish', 'Uighur', 'Ukrainian', 'Urdu', 'Uzbek', 'Vietnamese', 'Welsh', 'Yiddish', 'Yoruba', 'Unknown']
		try:
			idx = int(getSetting('language'))
		except:
			return ''
		return langs[idx]
		
class ThreadDownloader:
	def __init__(self):
		self.thread = None
		
	def startDownload(self,targetdir,urllist,ext='',callback=None):
		old_thread = None
		if self.thread and self.thread.isAlive():
			self.thread.stop()
			old_thread = self.thread
		self.thread = DownloadThread(targetdir,urllist,ext,callback,old_thread)
	
	def stop(self):
		self.thread.stop()
		
class DownloadThread(util.StoppableThread):
	def __init__(self,targetdir,urllist,ext='',callback=None,old_thread=None,nothread=False):
		util.StoppableThread.__init__(self,name='Downloader')
		if not os.path.exists(targetdir): os.makedirs(targetdir)
		self.callback = callback
		self.targetdir = targetdir
		self.urllist = urllist
		self.ext = ext
		self.old_thread = old_thread
		if nothread:
			self.run()
		else:
			self.start()
		
	def run(self):
		#Wait until old downloader is stopped
		if self.old_thread: self.old_thread.join()
		clearDirFiles(self.targetdir)
		file_list = {}
		total = len(self.urllist)
		fnbase = 'file_' + str(int(time.time())) + '%s' + self.ext
		try:
			for url,i in zip(self.urllist,range(0,total)):
				fname = os.path.join(self.targetdir,fnbase % i)
				file_list[url] = fname
				if self.stopped(): return None
				self.getUrlFile(url,fname)
			if self.stopped(): return None
		except:
			ERROR('THREADED DOWNLOAD URLS ERROR')
			return None
		self.callback(file_list)
		
	def getUrlFile(self,url,target):
		urlObj = urllib2.urlopen(url)
		outfile = open(target, 'wb')
		outfile.write(urlObj.read())
		outfile.close()
		urlObj.close()
		return target
		
		
class Downloader:
	def __init__(self,header=T(32205),message=''):
		self.message = message
		self.prog = xbmcgui.DialogProgress()
		self.prog.create(header,message)
		self.current = 0
		self.display = ''
		self.file_pct = 0
		
	def progCallback(self,read,total):
		if self.prog.iscanceled(): return False
		pct = int(((float(read)/total) * (self.file_pct)) + (self.file_pct * self.current))
		self.prog.update(pct)
		return True
		
	def downloadURLs(self,targetdir,urllist,ext=''):
		file_list = []
		self.total = len(urllist)
		self.file_pct = (100.0/self.total)
		try:
			for url,i in zip(urllist,range(0,self.total)):
				self.current = i
				if self.prog.iscanceled(): break
				self.display = T(32469).format(i+1,self.total)
				self.prog.update(int((i/float(self.total))*100),self.message,self.display)
				fname = os.path.join(targetdir,str(i) + ext)
				fname, ftype = self.getUrlFile(url,fname,callback=self.progCallback) #@UnusedVariable
				file_list.append(fname)
		except:
			ERROR('DOWNLOAD URLS ERROR')
			self.prog.close()
			return None
		self.prog.close()
		return file_list
	
	def downloadURL(self,targetdir,url,fname=None):
		if not fname:
			fname = os.path.basename(urlparse.urlsplit(url)[2])
			if not fname: fname = 'file'
		f,e = os.path.splitext(fname)
		fn = f
		ct=0
		while ct < 1000:
			ct += 1
			path = os.path.join(targetdir,fn + e)
			if not os.path.exists(path): break
			fn = f + str(ct)
		else:
			raise Exception
		
		try:
			self.current = 0
			self.display = T(32206).format(os.path.basename(path))
			self.prog.update(0,self.message,self.display)
			t,ftype = self.getUrlFile(url,path,callback=self.progCallback) #@UnusedVariable
		except:
			ERROR('DOWNLOAD URL ERROR')
			self.prog.close()
			return (None,'')
		self.prog.close()
		return (os.path.basename(path),ftype)
		
		
			
	def fakeCallback(self,read,total): return True

	def getUrlFile(self,url,target=None,callback=None):
		if not target: return #do something else eventually if we need to
		if not callback: callback = self.fakeCallback
		urlObj = urllib2.urlopen(url)
		size = int(urlObj.info().get("content-length",-1))
		ftype = urlObj.info().get("content-type",'')
		ext = None
		if '/' in ftype: ext = '.' + ftype.split('/')[-1].replace('jpeg','jpg')
		if ext:
			fname, x = os.path.splitext(target) #@UnusedVariable
			target = fname + ext
		#print urlObj.info()
		#Content-Disposition: attachment; filename=FILENAME
		outfile = open(target, 'wb')
		read = 0
		bs = 1024 * 8
		while 1:
			block = urlObj.read(bs)
			if block == "": break
			read += len(block)
			outfile.write(block)
			if not callback(read, size): raise Exception('Download Canceled')
		outfile.close()
		urlObj.close()
		return (target,ftype)

def getForumList():
	ft2 = os.listdir(FORUMS_PATH)
	flist = []
	for f in ft2:
		if not f.startswith('.') and not f == 'general':
			if not f in flist: flist.append(f)
	return flist

def checkForInterface(url):
	url = url.split('/forumrunner')[0].split('/mobiquo')[0]
	LOG('Checking for forum type at URL: ' + url)
	try:
		html = urllib2.urlopen(url).read()
		if 'tapatalkdetect.js' in html:
			return 'TT'
		elif '/detect.js' in html:
			return 'FR'
		return None
	except:
		return None
		
def getForumBrowser(forum=None,url=None,donecallback=None,silent=False,no_default=False,log_function=None):
	showError = dialogs.showMessage
	if silent: showError = dialogs.showMessageSilent
	global STARTFORUM
	forumElements = None
	if not forum and STARTFORUM:
			forumElements = util.parseForumBrowserURL(STARTFORUM)
			forum = forumElements.get('forumID')
			STARTFORUM = None
			
	if not forum:
		if no_default: return False
		forum = getSetting('last_forum') or 'TT.xbmc.org'
	#global FB
	#if forum.startswith('GB.') and not url:
	#	url = getSetting('exp_general_forums_last_url')
	#	if not url: forum = 'TT.xbmc.org'
		
	if not getForumPath(forum):
		if no_default: return False
		forum = 'TT.xbmc.org'
	err = ''
	try:
		if forum.startswith('GB.'):
			err = 'getForumBrowser(): General'
			from lib.forumbrowser import genericparserbrowser
			if log_function: genericparserbrowser.LOG = log_function
			FB = genericparserbrowser.GenericParserForumBrowser(forum,always_login=getSetting('always_login',False))
		elif forum.startswith('TT.'):
			err = 'getForumBrowser(): Tapatalk'
			FB = tapatalk.TapatalkForumBrowser(forum,always_login=getSetting('always_login',False))
		elif forum.startswith('FR.'):
			err = 'getForumBrowser(): Forumrunner'
			from lib.forumbrowser import forumrunner
			if log_function: forumrunner.LOG = log_function
			FB = forumrunner.ForumrunnerForumBrowser(forum,always_login=getSetting('always_login',False))
		#else:
		#	err = 'getForumBrowser(): Boxee'
		#	from forumbrowser import parserbrowser
		#	FB = parserbrowser.ParserForumBrowser(forum,always_login=getSetting('always_login') == 'true')
	except forumbrowser.ForumMovedException,e:
		showError(T(32050),T(32470),'\n' + e.message,error=True)
		return False
	except forumbrowser.ForumNotFoundException,e:
		showError(T(32050),T(32471).format(e.message),error=True)
		return False
	except forumbrowser.BrokenForumException,e:
		url = e.message
		ftype = checkForInterface(url)
		currentType = forum[:2]
		if ftype and ftype != currentType:
			LOG('Forum type changed to: ' + ftype)
			if ftype == 'TT':
				fromType = 'Forumrunner'
				toType = 'Tapatalk'
			else:
				toType = 'Forumrunner'
				fromType = 'Tapatalk'
			showError(T(32050),T(32472).format(fromType,toType),error=True)
		else:
			showError(T(32050),T(32473),error=True)
		return False
	except:
		err = ERROR(err)
		showError(T(32050),T(32171),err,error=True)
		return False
	
	if donecallback: donecallback(FB,forumElements)
	return FB

def startForumBrowser(forumID=None):
	global PLAYER, SIGNALHUB, STARTFORUM
	PLAYER = PlayerMonitor()
	SIGNALHUB = signals.SignalHub()
	windows.SIGNALHUB = SIGNALHUB
	updateOldVersion()
	forumbrowser.ForumPost.hideSignature = getSetting('hide_signatures',False)
	try:
		if mods.checkForSkinMods() or getSetting('refresh_skin',False):
			LOG('Skin Mods Changed: Reloading Skin')
			xbmc.executebuiltin('ReloadSkin()')
			setSetting('refresh_skin',False)
	except:
		ERROR('Error Installing Skin Mods')

	#TD = ThreadDownloader()
	if forumID:
		STARTFORUM = forumID
	elif sys.argv[-1].startswith('forum='):
		STARTFORUM = sys.argv[-1].split('=',1)[-1]
	elif sys.argv[-1].startswith('forumbrowser://'):
		STARTFORUM = sys.argv[-1]
	dialogs.openWindow(ForumsWindow,"script-forumbrowser-forums.xml")
	#sys.modules.clear()
	PLAYER.finish()
	del PLAYER
	del SIGNALHUB
	
######################################################################################
# Startup
######################################################################################
if __name__ == '__main__':
	if sys.argv[-1] == 'settings':
		doSettings()
	elif sys.argv[-1].startswith('settingshelp_'):
		dialogs.showHelp('settings-' + sys.argv[-1].split('_')[-1])
	else:
		try:
			setSetting('FBIsRunning',True)
			setSetting('manageForums',False)
			startForumBrowser()
		except KeyboardInterrupt:
			LOG('XBMC - abort requested: Shutting down...')
		finally:
			setSetting('FBIsRunning',False)
		