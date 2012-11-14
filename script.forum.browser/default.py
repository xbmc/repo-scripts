import urllib2, re, os, sys, time, urlparse, binascii
import xbmc, xbmcgui, xbmcaddon #@UnresolvedImport
import threading

try:
	from webviewer import webviewer #@UnresolvedImport
	print 'FORUM BROWSER: WEB VIEWER IMPORTED'
except:
	import traceback
	traceback.print_exc()
	print 'FORUM BROWSER: COULD NOT IMPORT WEB VIEWER'

'''
TODO:

Read/Delete PM's in xbmc4xbox.org

'''

__plugin__ = 'Forum Browser'
__author__ = 'ruuk (Rick Phillips)'
__url__ = 'http://code.google.com/p/forumbrowserxbmc/'
__date__ = '03-29-2012'
__version__ = '1.1.0'
__addon__ = xbmcaddon.Addon(id='script.forum.browser')
__language__ = __addon__.getLocalizedString

THEME = 'Default'
SKINS = ['Default','Dark','Default']
if __addon__.getSetting('skin') == '1':
	THEME = 'Dark'

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

#Actually it's show codec info but I'm using in a threaded callback
ACTION_RUN_IN_MAIN = 27

MEDIA_PATH = xbmc.translatePath(os.path.join(__addon__.getAddonInfo('path'),'resources','skins','default','media'))
FORUMS_STATIC_PATH = xbmc.translatePath(os.path.join(__addon__.getAddonInfo('path'),'forums'))
FORUMS_PATH = xbmc.translatePath(os.path.join(__addon__.getAddonInfo('profile'),'forums'))
CACHE_PATH = xbmc.translatePath(os.path.join(__addon__.getAddonInfo('profile'),'cache'))
if not os.path.exists(FORUMS_PATH): os.makedirs(FORUMS_PATH)
if not os.path.exists(CACHE_PATH): os.makedirs(CACHE_PATH)

def ERROR(message,hide_tb=False):
	LOG('ERROR: ' + message)
	short = str(sys.exc_info()[1])
	if hide_tb:
		LOG('ERROR Message: ' + short)
	else:
		import traceback #@Reimport
		traceback.print_exc()
	return short
	
def LOG(message):
	print 'FORUMBROWSER: %s' % message

LOG('Version: ' + __version__)
LOG('Python Version: ' + sys.version)
DEBUG = __addon__.getSetting('debug') == 'true'
if DEBUG: LOG('DEBUG LOGGING ON')
LOG('Skin: ' + THEME)

CLIPBOARD = None
try:
	import SSClipboard #@UnresolvedImport
	CLIPBOARD = SSClipboard.Clipboard()
	LOG('Clipboard Enabled')
except:
	LOG('Clipboard Disabled: No SSClipboard')

def getSetting(key,default=None):
	setting = __addon__.getSetting(key)
	if not setting: return default
	if isinstance(default,bool):
		return setting == 'true'
	elif isinstance(default,int):
		return int(float(setting))
	elif isinstance(default,list):
		if setting: return setting.split(':!,!:')
		else: return default
	
	return setting

def setSetting(key,value):
	if isinstance(value,list):
		value = ':!,!:'.join(value)
	__addon__.setSetting(key,value)
	
FB = None

from forumbrowser import forumbrowser
from forumbrowser import texttransform
from crypto import passmanager
from forumbrowser import tapatalk
from video import WebVideo

	
######################################################################################
# Base Window Classes
######################################################################################
def _async_raise(tid, exctype):
	try:
		LOG('Trying to kill thread...')
		import inspect,ctypes
		'''Raises an exception in the threads with id tid'''
		if not inspect.isclass(exctype):
			raise TypeError("Only types can be raised (not instances)")
		res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid,
													  ctypes.py_object(exctype))
		if res == 0:
			raise ValueError("invalid thread id")
		elif res != 1:
			# "if it returns a number greater than one, you're in trouble,
			# and you should call it again with exc=NULL to revert the effect"
			ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, 0)
			raise SystemError("PyThreadState_SetAsyncExc failed")
	except:
		ERROR('Error killing thread')

class StoppableThread(threading.Thread):
	def __init__(self,group=None, target=None, name=None, args=(), kwargs=None):
		kwargs = kwargs or {}
		self._stop = threading.Event()
		threading.Thread.__init__(self,group=group, target=target, name=name, args=args, kwargs=kwargs)
		
	def stop(self):
		self._stop.set()
		
	def stopped(self):
		return self._stop.isSet()
	
	def _get_my_tid(self):
		"""determines this (self's) thread id

		CAREFUL : this function is executed in the context of the caller
		thread, to get the identity of the thread represented by this
		instance.
		"""
		if not self.isAlive():
			raise threading.ThreadError("the thread is not active")

		# do we have it cached?
		if hasattr(self, "_thread_id"):
			return self._thread_id

		# no, look for it in the _active dict
		for tid, tobj in threading._active.items():
			if tobj is self:
				self._thread_id = tid
				return tid

		# TODO: in python 2.6, there's a simpler way to do : self.ident

		raise AssertionError("could not determine the thread's id")

	def raiseExc(self, exctype):
		"""Raises the given exception type in the context of this thread.

		If the thread is busy in a system call (time.sleep(),
		socket.accept(), ...), the exception is simply ignored.

		If you are sure that your exception should terminate the thread,
		one way to ensure that it works is:

			t = ThreadWithExc( ... )
			...
			t.raiseExc( SomeException )
			while t.isAlive():
				time.sleep( 0.1 )
				t.raiseExc( SomeException )

		If the exception is to be caught by the thread, you need a way to
		check that your thread has caught it.

		CAREFUL : this function is executed in the context of the
		caller thread, to raise an excpetion in the context of the
		thread represented by this instance.
		"""
		_async_raise( self._get_my_tid(), exctype )

		
class ThreadError:
	def __init__(self,message='Unknown'):
		self.message = message
		
	def __nonzero__(self):
		return False
	
class StoppableCallbackThread(StoppableThread):
	def __init__(self,target=None, name='FBUNKOWN'):
		self._target = target
		self._stop = threading.Event()
		self._finishedHelper = None
		self._finishedCallback = None
		self._progressHelper = None
		self._progressCallback = None
		self._errorHelper = None
		self._errorCallback = None
		self._threadName = name
		StoppableThread.__init__(self,name=name)
		
	def setArgs(self,*args,**kwargs):
		self.args = args
		self.kwargs = kwargs
		
	def run(self):
		try:
			self._target(*self.args,**self.kwargs)
		except forumbrowser.Error,e:
			LOG('ERROR IN THREAD: ' + e.message)
			self.errorCallback(ThreadError('%s: %s' % (self._threadName,e.message)))
		except:
			err = ERROR('ERROR IN THREAD: ' + self._threadName)
			self.errorCallback(ThreadError('%s: %s' % (self._threadName,err)))
		
	def setFinishedCallback(self,helper,callback):
		self._finishedHelper = helper
		self._finishedCallback = callback
	
	def setErrorCallback(self,helper,callback):
		self._errorHelper = helper
		self._errorCallback = callback
		
	def setProgressCallback(self,helper,callback):
		self._progressHelper = helper
		self._progressCallback = callback
		
	def stop(self):
		self._stop.set()
		
	def stopped(self):
		return self._stop.isSet()
		
	def progressCallback(self,*args,**kwargs):
		if self.stopped(): return False
		if self._progressCallback: self._progressHelper(self._progressCallback,*args,**kwargs)
		return True
		
	def finishedCallback(self,*args,**kwargs):
		if self.stopped(): return False
		if self._finishedCallback: self._finishedHelper(self._finishedCallback,*args,**kwargs)
		return True
	
	def errorCallback(self,error):
		if self.stopped(): return False
		if self._errorCallback: self._errorHelper(self._errorCallback,error)
		return True

class ThreadWindow:
	def __init__(self):
		self._currentThread = None
		self._stopControl = None
		self._startCommand = None
		self._progressCommand = None
		self._endCommand = None
		self._isMain = False
		self._resetFunction()
			
	def setAsMain(self):
		self._isMain = True
		
	def setStopControl(self,control):
		self._stopControl = control
		control.setVisible(False)
		
	def setProgressCommands(self,start=None,progress=None,end=None):
		self._startCommand = start
		self._progressCommand = progress
		self._endCommand = end
		
	def onAction(self,action):
		if action == ACTION_RUN_IN_MAIN:
			if self._function:
				func,args,kwargs = self.getFunction()
				func(*args,**kwargs)
				return True
		elif action == ACTION_PREVIOUS_MENU:
			if self._currentThread and self._currentThread.isAlive():
				self._currentThread.stop()
				if self._endCommand: self._endCommand()
				if self._stopControl: self._stopControl.setVisible(False)
			if self._isMain and len(threading.enumerate()) > 1:
				d = xbmcgui.DialogProgress()
				d.create(__language__(30220),__language__(30221))
				d.update(0)
				self.stopThreads()
				if d.iscanceled():
					d.close()
					return True
				d.close()
			return False
		return False
	
	def stopThreads(self):
		for t in threading.enumerate():
			if isinstance(t,StoppableThread): t.stop()
		time.sleep(1)
		while len(threading.enumerate()) > 1:
			for t in threading.enumerate():
				#if t != threading.currentThread(): t.join()
				if isinstance(t,StoppableThread): t.raiseExc(Exception)
			time.sleep(1)
		
	def getFunction(self):
		func = self._function
		args = self._functionArgs
		kwargs = self._functionKwargs
		self._resetFunction()
		return func,args,kwargs
	
	def _resetFunction(self):
		self._function = None
		self._functionArgs = []
		self._functionKwargs = {}
		
	def runInMain(self,function,*args,**kwargs):
		self._function = function
		self._functionArgs = args
		self._functionKwargs = kwargs
		xbmc.executebuiltin('Action(codecinfo)')
		
	def endInMain(self,function,*args,**kwargs):
		if self._endCommand: self._endCommand()
		if self._stopControl: self._stopControl.setVisible(False)
		self.runInMain(function,*args,**kwargs)
		
	def getThread(self,function,finishedCallback=None,progressCallback=None,errorCallback=None,name='FBUNKNOWN'):
		if self._currentThread: self._currentThread.stop()
		if not progressCallback: progressCallback = self._progressCommand
		t = StoppableCallbackThread(target=function,name=name)
		t.setFinishedCallback(self.endInMain,finishedCallback)
		t.setErrorCallback(self.endInMain,errorCallback)
		t.setProgressCallback(self.runInMain,progressCallback)
		self._currentThread = t
		if self._stopControl: self._stopControl.setVisible(True)
		if self._startCommand: self._startCommand()
		return t
		
	def stopThread(self):
		if self._stopControl: self._stopControl.setVisible(False)
		if self._currentThread:
			self._currentThread.stop()
			self._currentThread = None
			if self._endCommand: self._endCommand()
		
class BaseWindowFunctions(ThreadWindow):
	def __init__( self, *args, **kwargs ):
		self._progMessageSave = ''
		self.closed = False
		self.headerTextFormat = '%s'
		ThreadWindow.__init__(self)
	
	def onClick( self, controlID ):
		return False
			
	def onAction(self,action):
		if action == ACTION_PARENT_DIR or action == ACTION_PARENT_DIR2:
			action = ACTION_PREVIOUS_MENU
		if ThreadWindow.onAction(self,action): return
		if action == ACTION_PREVIOUS_MENU:
			self.closed = True
			self.close()
		xbmcgui.WindowXML.onAction(self,action)
	
	def startProgress(self):
		self._progMessageSave = self.getControl(104).getLabel()
		#self.getControl(310).setVisible(True)
	
	def setProgress(self,pct,message=''):
		if pct<0:
			self.stopThread()
			showMessage('ERROR',message,error=True)
			return False
		w = int((pct/100.0)*self.getControl(300).getWidth())
		self.getControl(310).setWidth(w)
		self.getControl(104).setLabel(self.headerTextFormat % message)
		return True
		
	def endProgress(self):
		#self.getControl(310).setVisible(False)
		self.getControl(104).setLabel(self._progMessageSave)
		
class BaseWindow(xbmcgui.WindowXML,BaseWindowFunctions):
	def __init__(self, *args, **kwargs):
		BaseWindowFunctions.__init__(self, *args, **kwargs)
		xbmcgui.WindowXML.__init__( self )
		
	def onAction(self,action):
		BaseWindowFunctions.onAction(self,action)
		
class BaseWindowDialog(xbmcgui.WindowXMLDialog,BaseWindowFunctions):
	def __init__(self, *args, **kwargs):
		BaseWindowFunctions.__init__(self, *args, **kwargs)
		xbmcgui.WindowXMLDialog.__init__( self )
	
	def onAction(self,action):
		BaseWindowFunctions.onAction(self,action)

class PageWindow(BaseWindow):
	def __init__( self, *args, **kwargs ):
		self.next = ''
		self.prev = ''
		self.pageData = FB.getPageData(total_items=kwargs.get('total_items',0))
		self.firstRun = True
		self._firstPage = __language__(30110)
		self._lastPage = __language__(30111)
		self._newestPage = None
		BaseWindow.__init__( self, *args, **kwargs )
		
	def onFocus( self, controlId ):
		self.controlId = controlId

	def onClick( self, controlID ):
		if controlID == 200:
			if self.pageData.prev: self.gotoPage(self.pageData.getPrevPage())
		elif controlID == 202:
			if self.pageData.next: self.gotoPage(self.pageData.getNextPage())
		elif controlID == 105:
			self.pageMenu()
		BaseWindow.onClick(self,controlID)
	
	def onAction(self,action):
		BaseWindow.onAction(self,action)
		if action == ACTION_NEXT_ITEM:
			if self.pageData.next: self.gotoPage(self.pageData.getNextPage())
		elif action == ACTION_PREV_ITEM:
			if self.pageData.prev: self.gotoPage(self.pageData.getPrevPage())
		
	def pageMenu(self):
		dialog = xbmcgui.Dialog()
		options = [self._firstPage,self._lastPage]
		if self._newestPage: options.append(self._newestPage)
		options.append(__language__(30115))
		idx = dialog.select(__language__(30114),options)
		if idx < 0: return
		if options[idx] == self._firstPage: self.gotoPage(self.pageData.getPageNumber(1))
		elif options[idx] == self._lastPage: self.gotoPage(self.pageData.getPageNumber(-1))
		elif options[idx] == self._newestPage:
			self.firstRun = True #For replies window
			self.gotoPage(self.pageData.getPageNumber(-1))
		else: self.askPageNumber()
		
	def askPageNumber(self):
		page = xbmcgui.Dialog().numeric(0,__language__(30116))
		try: int(page)
		except: return
		self.gotoPage(self.pageData.getPageNumber(page))
		
	def setupPage(self,pageData):
		if pageData:
			self.pageData = pageData
		else:
			from forumbrowser.forumbrowser import PageData
			pageData = PageData(None)
		self.getControl(200).setVisible(pageData.prev)
		self.getControl(202).setVisible(pageData.next)
		self.getControl(105).setLabel(pageData.getPageDisplay())
		
	def gotoPage(self,page): pass

######################################################################################
# Image Dialog
######################################################################################
class ImagesDialog(BaseWindowDialog):
	def __init__( self, *args, **kwargs ):
		self.images = kwargs.get('images')
		self.index = 0
		BaseWindowDialog.__init__( self, *args, **kwargs )
	
	def onInit(self):
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
		if BaseWindow.onClick(self, controlID): return
		if controlID == 200:
			self.nextImage()
		elif controlID == 202:
			self.prevImage()
	
	def onAction(self,action):
		if action == ACTION_PARENT_DIR or action == ACTION_PARENT_DIR2:
			action = ACTION_PREVIOUS_MENU
		elif action == ACTION_NEXT_ITEM:
			self.nextImage()
		elif action == ACTION_PREV_ITEM:
			self.prevImage()
		elif action == ACTION_CONTEXT_MENU:
			self.doMenu()
		BaseWindowDialog.onAction(self,action)
		
	def doMenu(self):
		d = ChoiceMenu('Options')
		d.addItem('save', 'Save Image')
		d.addItem('help','Help')
		result = d.getResult()
		if not result: return
		if result == 'save':
			self.saveImage()
		elif result == 'help':
			showHelp('imageviewer')
			
	def downloadImage(self,url):
		base = xbmc.translatePath(os.path.join(__addon__.getAddonInfo('profile'),'slideshow'))
		if not os.path.exists(base): os.makedirs(base)
		clearDirFiles(base)
		return Downloader(message=__language__(30148)).downloadURLs(base,[url],'.jpg')
		
	def saveImage(self):
		#browse(type, heading, shares[, mask, useThumbs, treatAsFolder, default])
		source = self.images[self.index]
		firstfname = os.path.basename(source)
		if source.startswith('http'):
			result = self.downloadImage(source)
			if not result:
				showMessage('Failed','Failed to download file.',success=False)
				return
			source = result[0]
		filename = doKeyboard('Enter Filename', firstfname)
		if filename == None: return
		default = __addon__.getSetting('last_download_path') or ''
		result = xbmcgui.Dialog().browse(3,'Select Directory','files','',False,True,default)
		__addon__.setSetting('last_download_path',result)
		if not os.path.exists(source): return
		target = os.path.join(result,filename)
		ct = 1
		original = filename
		while os.path.exists(target):
			fname, ext = os.path.splitext(original)
			filename = fname + '_' + str(ct) + ext
			ct+=1
			if os.path.exists(os.path.join(result,filename)): continue
			yes = xbmcgui.Dialog().yesno('File Exists','File exists!','Save as:',filename + '?','Enter New','Yes')
			if not yes:
				ct = 0
				filename = doKeyboard('Enter Filename', filename)
				original = filename
				if filename == None: return
			target = os.path.join(result,filename)
		import shutil
		shutil.copy(source, target)
		showMessage('Finished','File Saved Successfully: ',os.path.basename(target),success=True)
		
######################################################################################
# Post Dialog
######################################################################################
class PostDialog(BaseWindowDialog):
	failedPM = None
	def __init__( self, *args, **kwargs ):
		self.post = kwargs.get('post')
		self.doNotPost = kwargs.get('donotpost') or False
		self.title = self.post.title
		self.posted = False
		self.moderated = False
		self.display_base = '%s\n \n'
		BaseWindowDialog.__init__( self, *args, **kwargs )
	
	def onInit(self):
		self.getControl(122).setText(' ') #to remove scrollbar
		if self.failedPM:
			if self.failedPM.isPM == self.post.isPM and self.failedPM.tid == self.post.tid and self.failedPM.to == self.post.to:
				yes = xbmcgui.Dialog().yesno('Failed post found','Re-use previous failed post?')
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
			showMessage('Note','Posting appears to be moderated.','Your message may not appear right away.')
		if self.isPM() or self.doNotPost: self.setTitle() #We're creating a thread
	
	def setTheme(self):
		if self.isPM():
			self.getControl(103).setLabel('[B]%s[/B]' % __language__(30177))
			self.getControl(202).setLabel(__language__(30178))
		else:
			self.getControl(103).setLabel('[B]Post Reply[/B]')
		if self.post.title:
			self.getControl(104).setLabel(self.post.title)
		else:
			self.getControl(104).setLabel(__language__(30120))
		
	def onClick( self, controlID ):
		if BaseWindow.onClick(self, controlID): return
		if controlID == 202:
			self.postReply()
		elif controlID == 104:
			self.setTitle()

	def onFocus( self, controlId ):
		self.controlId = controlId
		
	def onAction(self,action):
		if action == ACTION_PREVIOUS_MENU:
			if not self.confirmExit(): return
		BaseWindowDialog.onAction(self,action)
		
	def confirmExit(self):
		if not self.getOutput() and not self.title: return True
		return xbmcgui.Dialog().yesno('Are You Sure?','Really close?','Changes will be lost.')
	
	def isPM(self):
		return str(self.post.pid).startswith('PM') or self.post.to
	
	def getOutput(self): pass
	
	def setTitle(self):
		keyboard = xbmc.Keyboard(self.title,__language__(30125))
		keyboard.doModal()
		if not keyboard.isConfirmed(): return
		title = keyboard.getText()
		self.getControl(104).setLabel(title)
		self.title = title
	
	def dialogCallback(self,pct,message):
		self.prog.update(pct,message)
		return True
		
	def postReply(self):
		message = self.getOutput()
		self.post.setMessage(self.title,message)
		self.posted = True
		if self.doNotPost:
			self.close()
			return
		splash = showActivitySplash('Posting')
		try:
			if self.post.isPM:
				if not FB.doPrivateMessage(self.post,callback=splash.update):
					self.posted = False
					showMessage(__language__(30050),__language__(30246),' ',self.post.error or '?',success=False)
					return
			else:
				if not FB.post(self.post,callback=splash.update):
					self.posted = False
					showMessage(__language__(30050),__language__(30227),' ',self.post.error or '?',success=False)
					return
			showMessage('Success',self.post.isPM and 'Message sent.' or 'Message posted.',' ',str(self.post.successMessage),success=True)
		except:
			self.posted = False
			err = ERROR('Error creating post')
			showMessage('ERROR','Error creating post:',err,error=True)
			PostDialog.failedPM = self.post
		finally:
			splash.close()
		if not self.moderated and self.post.moderated:
			showMessage('Note','Posting appears to be moderated.','Your message may not appear right away.')
		self.close()
		
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
		d = ChoiceMenu(__language__(30051))
		item = self.getControl(120).getSelectedItem()
		if item:
			d.addItem('addbefore',__language__(30128))
			d.addItem('delete',__language__(30122))
			if CLIPBOARD and CLIPBOARD.hasData(('link','image','video')):
				d.addItem('pastebefore','Paste From Clipboard Before: ' + CLIPBOARD.hasData().title())
		if CLIPBOARD and CLIPBOARD.hasData(('link','image','video')):
			d.addItem('paste','Paste From Clipboard: ' + CLIPBOARD.hasData().title())
		d.addItem('help',__language__(30244))
		result = d.getResult()
		if result == 'addbefore': self.addLineSingle(before=True)
		elif result == 'delete': self.deleteLine()
		elif result == 'paste': self.paste()
		elif result == 'pastebefore': self.paste(before=True)
		elif result == 'help': showHelp('editor')
		
	def paste(self,before=False):
		share = CLIPBOARD.getClipboard()
		if share.shareType == 'link':
			text = doKeyboard('Enter Link Text')
			if not text: text = share.page
			paste = '[url=%s]%s[/url]' % (share.page,text)
		elif share.shareType == 'image':
			paste = '[img]%s[/img]' % share.url
		elif share.shareType == 'video':
			source = WebVideo().getVideoObject(share.page).sourceName.lower()
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
	
	def doKeyboard(self,caption,text):
		return doModKeyboard(caption,text)
			
	def addLineSingle(self,line=None,before=False,update=True):
		if line == None: line = self.doKeyboard(__language__(30123),'')
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
		line = self.doKeyboard(__language__(30124),item.getLabel())
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
class MessageWindow(BaseWindow):
	def __init__( self, *args, **kwargs ):
		self.post = kwargs.get('post')
		#self.imageReplace = '[COLOR FFFF0000]I[/COLOR][COLOR FFFF8000]M[/COLOR][COLOR FF00FF00]G[/COLOR][COLOR FF0000FF]#[/COLOR][COLOR FFFF00FF]%s[/COLOR]'
		self.imageReplace = 'IMG #%s'
		self.action = None
		self.started = False
		self.videoHandler = WebVideo()
		BaseWindow.__init__( self, *args, **kwargs )
		
	def onInit(self):
		if self.started: return
		self.started = True
		self.setLoggedIn()
#		if __addon__.getSetting('use_forum_colors') == 'true':
#			if (FB.theme.get('mode') == 'dark' or __addon__.getSetting('color_mode') == '1') and __addon__.getSetting('color_mode') != '2':
#				text = '[COLOR FFFFFFFF]%s[/COLOR][CR] [CR]' % (self.post.translated or self.post.messageAsDisplay())
#			else:
#				text = '[COLOR FF000000]%s[/COLOR][CR] [CR]' % (self.post.translated or self.post.messageAsDisplay())
#		else:
#			text = '%s[CR] [CR]' % (self.post.translated or self.post.messageAsDisplay())
		s = showActivitySplash()
		try:
			text = '%s[CR] [CR]' % self.post.messageAsDisplay(raw=True)
		finally:
			s.close()
		self.getControl(122).setText(text)
		self.getControl(102).setImage(self.post.avatarFinal)
		self.setTheme()
		self.getImages()
		self.getLinks()

	def setTheme(self):
		self.getControl(103).setLabel('[B]%s[/B]' % self.post.cleanUserName() or '')
		title = ''
		if self.post.postNumber: title = '#' + str(self.post.postNumber) + ' '
		title += self.post.title or ''
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
		if checkVideo: s = showActivitySplash('Getting Video Info...')
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
		for url in self.post.imageURLs():
			i+=1
			while urlParentDirFilter.search(url):
				#TODO: Limit
				url = urlParentDirFilter.sub('/',url)
			url = url.replace('/../','/')
			item = xbmcgui.ListItem(self.imageReplace % i,iconImage=url)
			item.setProperty('url',url)
			self.getControl(150).addItem(item)
		#targetdir = os.path.join(__addon__.getAddonInfo('profile'),'messageimages')
		#TD.startDownload(targetdir,self.post.imageURLs(),ext='.jpg',callback=self.getImagesCallback)
		
	def getImagesCallback(self,file_dict):
		for fname,idx in zip(file_dict.values(),range(0,self.getControl(150).size())):
			fname = xbmc.translatePath(fname)
			self.getControl(150).getListItem(idx).setIconImage(fname)
			
	def onFocus( self, controlId ):
		self.controlId = controlId
		
	def onClick( self, controlID ):
		if BaseWindow.onClick(self, controlID): return
		if controlID == 148:
			self.linkSelected()
		elif controlID == 150:
			self.showImage(self.getControl(150).getSelectedItem().getProperty('url'))
	
	def showVideo(self,source):
		xbmc.executebuiltin('PlayMedia(%s)' % source)
		
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
			s = showActivitySplash()
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
			self.close()
		else:
			try:
				webviewer.getWebResult(link.url,dialog=True,browser=FB.browser)
			except:
				raise
				#We're in Boxee
				wvPath = xbmc.translatePath(os.path.join(__addon__.getAddonInfo('path'),'webviewer'))
				webviewer.getWebResult(link.url,dialog=True,runFromSubDir=wvPath)
				#xbmc.executebuiltin('XBMC.RunScript(special://home/apps/script.web.viewer/default.py,%s)' % link.url)
			
#			base = xbmcgui.Dialog().browse(3,__language__(30144),'files')
#			if not base: return
#			fname,ftype = Downloader(message=__language__(30145)).downloadURL(base,link.url)
#			if not fname: return
#			showMessage(__language__(30052),__language__(30146),fname,__language__(30147) % ftype)
		
	def showImage(self,url):
		#base = xbmc.translatePath(os.path.join(__addon__.getAddonInfo('profile'),'slideshow'))
		#if not os.path.exists(base): os.makedirs(base)
		#clearDirFiles(base)
		#image_files = Downloader(message=__language__(30148)).downloadURLs(base,[url],'.jpg')
		#if not image_files: return
		image_files = self.post.imageURLs()
		for l in self.post.links():
			if l.isImage() and not l.textIsImage(): image_files.append(l.url)
		if url in image_files:
			image_files.pop(image_files.index(url))
			image_files.insert(0,url)
		w = ImagesDialog("script-forumbrowser-imageviewer.xml" ,__addon__.getAddonInfo('path'),THEME,images=image_files,parent=self)
		w.doModal()
		del w
			
	def onAction(self,action):
		BaseWindow.onAction(self,action)
		if action == ACTION_CONTEXT_MENU:
			if self.getFocusId() == 148:
				self.doLinkMenu()
			elif self.getFocusId() == 150:
				self.doImageMenu()
			else:
				self.doMenu()
		
	def doLinkMenu(self):
		link = self.getSelectedLink()
		if not link: return
		d = ChoiceMenu('Link Options')
		if CLIPBOARD:
			d.addItem('copy','Copy Link To Clipboard')
			if link.isImage():
				d.addItem('copyimage','Copy Image URL To Clipboard')
			video = self.videoHandler.getVideoObject(link.url)
			if not video: video = self.videoHandler.getVideoObject(link.text)
			if video and video.isVideo: d.addItem('copyvideo','Copy Video URL To Clipboard')
				
		if d.isEmpty(): return
		result = d.getResult()
		if result == 'copy':
			share = CLIPBOARD.getShare('script.evernote','link')
			share.page = link.url
			CLIPBOARD.setClipboard(share)
		elif result == 'copyimage':
			share = CLIPBOARD.getShare('script.evernote','image')
			share.url = link.url
			CLIPBOARD.setClipboard(share)
		elif result == 'copyvideo':
			share = CLIPBOARD.getShare('script.evernote','video')
			video = self.videoHandler.getVideoObject(link.url)
			if video:
				share.page = link.url
			else:
				share.page = link.text
			CLIPBOARD.setClipboard(share)
				
	def doImageMenu(self):
		img = self.getControl(150).getSelectedItem().getProperty('url')
		d = ChoiceMenu('Image Options')
		if CLIPBOARD:
			d.addItem('copy','Copy Image URL To Clipboard')
		if d.isEmpty(): return
		result = d.getResult()
		if result == 'copy':
			share = CLIPBOARD.getShare('script.evernote','image')
			share.url = img
			CLIPBOARD.setClipboard(share)
	
	def doMenu(self):
		d = ChoiceMenu(__language__(30051))
		if FB.canPost(): d.addItem('quote',self.post.isPM and __language__(30249) or __language__(30134))
		if FB.canDelete(self.post.cleanUserName(),self.post.messageType()): d.addItem('delete',__language__(30141))
		if FB.canEditPost(self.post.cleanUserName()): d.addItem('edit',__language__(30232))
		if self.post.extras: d.addItem('extras','User Extra Info')
		d.addItem('help',__language__(30244))
		result = d.getResult()
		if result == 'quote': self.openPostDialog(quote=True)
		elif result == 'delete': self.deletePost()
		elif result == 'edit':
			splash = showActivitySplash('Getting post for edit...')
			try:
				pm = FB.getPostForEdit(self.post)
			finally:
				splash.close()
			pm.tid = self.post.tid
			if openPostDialog(editPM=pm):
				self.action = forumbrowser.Action('REFRESH-REOPEN')
				self.action.pid = pm.pid
				self.close()
		elif result == 'extras':
			showUserExtras(self.post.extras)
		elif result == 'help':
			showHelp('message')
			
	def deletePost(self):
		result = deletePost(self.post,is_pm=self.post.isPM)
		self.action = forumbrowser.Action('REFRESH')
		if result: self.close()
		
	def openPostDialog(self,quote=False):
		pm = openPostDialog(quote and self.post or None,pid=self.post.postId,tid=self.post.tid,fid=self.post.fid)
		if pm:
			self.action = forumbrowser.PostMessage(pid=pm.pid)
			self.action.action = 'GOTOPOST'
			self.close()
		
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
			s = showActivitySplash()
			try:
				pm.setQuote(post.userName,post.messageAsQuote())
				pm.title = post.title
			finally:
				s.close()
		if tid == 'private_messages':
			default = to
			if post: default = post.userName
			to = doKeyboard('Enter Recipient(s)',default=default)
			if not to: return
			pm.to = to
	w = openWindow(LinePostDialog,"script-forumbrowser-post.xml" ,post=pm,return_window=True,donotpost=donotpost)
	posted = w.posted
	del w
	if posted: return pm
	return None

def deletePost(post,is_pm=False):
	pm = forumbrowser.PostMessage().fromPost(post)
	if not pm.pid: return
	yes = xbmcgui.Dialog().yesno('Really Delete?','Are you sure you want to delete this message?')
	if not yes: return
	splash = showActivitySplash('Deleting')
	try:
		if is_pm or post.isPM:
			pm.isPM = True
			result = FB.deletePrivateMessage(pm)
		else:
			result = FB.deletePost(pm)
		if not result:
			showMessage('Failed','Failed to delete: ',pm.error or 'Reason unknown.',success=False)
		else:
			showMessage('Success',pm.isPM and 'Message deleted.' or 'Post deleted.',success=True)
	except:
		err = ERROR('Delete post error.')
		LOG('Error deleting post/pm: ' + err)
		showMessage('ERROR','Error while deleting post: [CR]',err,error=True)
		return None
	finally:
		splash.close()
	return result

def showUserExtras(extras):
	out = ''
	for k,v in extras.items():
		out += '[B]' + k.title() + ':[/B] [COLOR FF550000]' + v + '[/COLOR]\n'
	showMessage('User Info',out,scroll=True)

######################################################################################
#
# Replies Window
#
######################################################################################
class RepliesWindow(PageWindow):
	def __init__( self, *args, **kwargs ):
		PageWindow.__init__( self,total_items=int(kwargs.get('reply_count',0)),*args, **kwargs )
		self.pageData.isReplies = True
		self.threadItem = item = kwargs.get('item')
		self.dontOpenPD = False
		if item:
			self.tid = item.getProperty('id')
			self.lastid = item.getProperty('lastid')
			self.topic = item.getProperty('title')
			self.reply_count = item.getProperty('reply_count')
			self.isAnnouncement = bool(item.getProperty('announcement'))
		else:
			self.tid = kwargs.get('tid')
			self.lastid = ''
			self.topic = kwargs.get('topic')
			self.reply_count = ''
			self.isAnnouncement = False
			
		self.fid = kwargs.get('fid','')
		self.pid = ''
		self.parent = kwargs.get('parent')
		#self._firstPage = __language__(30113)
		self._newestPage = __language__(30112)
		self.me = self.parent.parent.getUsername()
		self.posts = {}
		self.empty = True
		self.desc_base = u'[CR]%s[CR] [CR]'
		self.ignoreSelect = False
		self.firstRun = True
		self.started = False
		self.currentPMBox = {}
	
	def onInit(self):
		if self.started: return
		self.started = True
		self.setLoggedIn()
		self.setupPage(None)
		self.setStopControl(self.getControl(106))
		self.setProgressCommands(self.startProgress,self.setProgress,self.endProgress)
		self.postSelected()
		self.setPMBox()
		self.setTheme()
		if self.isPM():
			self.getControl(201).setEnabled(FB.canPrivateMessage())
		else:
			self.getControl(201).setEnabled(FB.canPost())
		self.showThread()
		#self.setFocusId(120)
	
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
		mtype = self.isPM() and self.currentPMBox.get('name','Inbox') or __language__(30130)
		if self.isPM(): self.getControl(201).setLabel(__language__(30177))
		self.getControl(103).setLabel('[B]%s[/B]' % mtype)
		self.getControl(104).setLabel('[B]%s[/B]' % self.topic)
		
	def showThread(self,nopage=False):
		if nopage:
			page = ''
		else:
			page = '1'
			if __addon__.getSetting('open_thread_to_newest') == 'true': page = '-1'
		self.fillRepliesList(FB.getPageData(is_replies=True).getPageNumber(page))
		
	def isPM(self):
		return self.tid == 'private_messages'
	
	def errorCallback(self,error):
		showMessage(__language__(30050),__language__(30131),error.message,error=True)
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
		else:
			t = self.getThread(FB.getReplies,finishedCallback=self.doFillRepliesList,errorCallback=self.errorCallback,name='POSTS')
			t.setArgs(self.tid,self.fid,page,lastid=self.lastid,pid=self.pid or pid,callback=t.progressCallback,donecallback=t.finishedCallback,page_data=self.pageData)
		t.start()
		
	def setMessageProperty(self,post,item,short=False):
		title = post.title or ''
		item.setProperty('title',title)
		item.setProperty('message',post.messageAsDisplay(short))
		
	def doFillRepliesList(self,data):
		if 'newthreadid' in data: self.tid = data['newthreadid']
		if not data:
			self.setFocusId(201)
			if data.error == 'CANCEL': return
			LOG('GET REPLIES ERROR')
			showMessage(__language__(30050),self.isPM() and __language__(30135) or __language__(30131),__language__(30053),'[CR]' + data.error,success=False)
			return
		elif not data.data:
			if data.data == None:
				self.setFocusId(201)
				LOG('NO REPLIES')
				showMessage(__language__(30050),self.isPM() and __language__(30135) or __language__(30131),__language__(30053),success=False)
			else:
				self.setFocusId(201)
				self.getControl(104).setLabel(self.isPM() and __language__(30251) or __language__(30250))
				LOG('No messages/posts - clearing list')
				self.getControl(120).reset()
				self.getControl(120).addItems([])
			return
		
		self.empty = False
		defAvatar = xbmc.translatePath(os.path.join(__addon__.getAddonInfo('path'),'resources','skins',THEME,'media','forum-browser-avatar-none.png'))
		#xbmcgui.lock()
		try:
			self.getControl(120).reset()
			if not self.topic: self.topic = data.pageData.topic
			if not self.tid: self.tid = data.pageData.tid
			self.setupPage(data.pageData)
			if getSetting('reverse_sort',False) and not self.isPM():
				data.data.reverse()
			self.posts = {}
			select = -1
			for post,idx in zip(data.data,range(0,len(data.data))):
				if self.pid and post.postId == self.pid: select = idx
				self.posts[post.postId] = post
				url = defAvatar
				if post.avatar: url = FB.makeURL(post.avatar)
				post.avatarFinal = url
				user = re.sub('<.*?>','',post.userName)
				item = xbmcgui.ListItem(label=post.isSent and 'To: ' + user or user)
				if user == self.me: item.setInfo('video',{"Director":'me'})
				self.setMessageProperty(post,item,True)
				item.setProperty('post',post.postId)
				item.setProperty('avatar',url)
				item.setProperty('status',texttransform.convertHTMLCodes(post.status))
				item.setProperty('date',post.date)
				item.setProperty('online',post.online and 'online' or '')
				item.setProperty('postcount',post.postCount and unicode(post.postCount) or '')
				item.setProperty('activity',post.getActivity())
				item.setProperty('postnumber',post.postNumber and unicode(post.postNumber) or '')
				item.setProperty('joindate',unicode(post.joinDate))
				if post.extras: item.setProperty('extras','extras')
				self.getControl(120).addItem(item)
				self.setFocusId(120)
			if select > -1:
				self.getControl(120).selectItem(int(select))
			elif self.firstRun and getSetting('open_thread_to_newest',False) and not self.isPM() and not getSetting('reverse_sort',False):
				self.getControl(120).selectItem(self.getControl(120).size() - 1)
			self.firstRun = False
		except:
			self.setFocusId(201)
			#xbmcgui.unlock()
			ERROR('FILL REPLIES ERROR')
			showMessage(__language__(30050),__language__(30133),error=True)
			raise
		#xbmcgui.unlock()
		if select > -1 and not self.dontOpenPD:
			self.dontOpenPD = False
			self.postSelected(itemindex=select)
		
		self.getControl(104).setLabel('[B]%s[/B]' % self.topic)
		self.pid = ''
		self.setLoggedIn()
			
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
		post.tid = self.tid
		post.fid = self.fid
		w = openWindow(MessageWindow,"script-forumbrowser-message.xml" ,return_window=True,post=post,parent=self)
		self.setMessageProperty(post,item)
		self.setFocusId(120)
		if w.action:
			if w.action.action == 'CHANGE':
				self.topic = ''
				self.pid = w.action.pid
				self.tid = w.action.tid
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
			self.openPostDialog()
		elif controlID == 120:
			if not self.empty: self.stopThread()
			self.postSelected()
		elif controlID == 106:
			self.stopThread()
			return
		if self.empty: self.fillRepliesList()
		PageWindow.onClick(self,controlID)
		
	def onAction(self,action):
		if action == ACTION_CONTEXT_MENU:
			self.doMenu()
		PageWindow.onAction(self,action)
	
	def selectNewPMBox(self):
		boxes = FB.getPMBoxes(update=False)
		if not boxes: return #TODO: Show message
		d = ChoiceMenu('Select Box')
		for b in boxes:
			d.addItem(b,b.get('name','?'))
		box = d.getResult()
		if not box: return
		self.currentPMBox = box
		self.setTheme()
		self.fillRepliesList()
		
	def doMenu(self):
		item = self.getControl(120).getSelectedItem()
		d = ChoiceMenu(__language__(30051),with_splash=True)
		post = None
		try:
			if self.isPM():
				boxes = FB.getPMBoxes(update=False)
				if boxes and len(boxes) > 1:
					d.addItem('changebox','Change PM Box')
			if item:
				post = self.posts.get(item.getProperty('post'))
				if FB.canPost():
					d.addItem('quote',self.isPM() and __language__(30249) or __language__(30134))
				if FB.canDelete(item.getLabel(),post.messageType()):
					d.addItem('delete',__language__(30141))
				if not self.isPM():
					if FB.canEditPost(item.getLabel()):
						d.addItem('edit',__language__(30232))
						
			if self.threadItem:
				if FB.isThreadSubscribed(self.tid,self.threadItem.getProperty('subscribed')):
					if FB.canUnSubscribeThread(self.tid): d.addItem('unsubscribe',__language__(30240) + ': ' + self.threadItem.getLabel2()[:25])
				else:
					if FB.canSubscribeThread(self.tid): d.addItem('subscribe',__language__(30236) + ': ' + self.threadItem.getLabel2()[:25])
			if post and post.extras:
				d.addItem('extras','User Extra Info')
			if item and FB.canPrivateMessage() and not self.isPM():
				d.addItem('pm',__language__(30253) % item.getLabel())
			d.addItem('refresh',__language__(30054))
			d.addItem('help',__language__(30244))
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
			splash = showActivitySplash('Getting post for edit...')
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
			showUserExtras(post.extras)
		elif result == 'pm':
			quote = xbmcgui.Dialog().yesno('Quote?','Quote the message?')
			self.openPostDialog(post,force_pm=True,no_quote=not quote)
		elif result == 'help':
			if self.isPM():
				showHelp('pm')
			else:
				showHelp('posts')
		if self.empty: self.fillRepliesList()
			
	def deletePost(self):
		item = self.getControl(120).getSelectedItem()
		pid = item.getProperty('post')
		if not pid: return
		post = self.posts.get(pid)
		if deletePost(post,is_pm=self.isPM()):
			self.fillRepliesList(self.pageData.getPageNumber())
		
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
	splash = showActivitySplash()
	try:
		result = FB.subscribeThread(tid)
		if result == True:
			showMessage('Success','Subscribed to thread.',success=True)
		else:
			showMessage('Failed','Failed to subscribed to thread:',str(result),success=False)
		return result
	finally:
		splash.close()
		
def unSubscribeThread(tid):
	splash = showActivitySplash()
	try:
		result = FB.unSubscribeThread(tid)
		if result == True:
			showMessage('Success','Unsubscribed from thread.',success=True)
		else:
			showMessage('Failed','Failed to unsubscribed from thread:',str(result),success=False)
		return result
	finally:
		splash.close()

def subscribeForum(fid):
	splash = showActivitySplash()
	try:
		result = FB.subscribeForum(fid)
		if result == True:
			showMessage('Success','Subscribed to forum.',success=True)
		else:
			showMessage('Failed','Failed to subscribed to forum:',str(result),success=False)
		return result
	finally:
		splash.close()

def unSubscribeForum(fid):
	splash = showActivitySplash()
	try:
		result = FB.unSubscribeForum(fid)
		if result == True:
			showMessage('Success','Unsubscribed from forum.',success=True)
		else:
			showMessage('Failed','Failed to unsubscribed from forum:',str(result),success=False)
		return result
	finally:
		splash.close()
	
######################################################################################
#
# Threads Window
#
######################################################################################
class ThreadsWindow(PageWindow):
	def __init__( self, *args, **kwargs ):
		self.fid = kwargs.get('fid','')
		self.topic = kwargs.get('topic','')
		self.parent = kwargs.get('parent')
		self.forumItem = kwargs.get('item')
		self.me = self.parent.getUsername() or '?'
		self.empty = True
		self.textBase = '%s'
		self.newBase = '[B]%s[/B]'
		self.highBase = '%s'
		self.forum_desc_base = '[I]%s [/I]'
		self.started = False
		PageWindow.__init__( self, *args, **kwargs )
		
	def onInit(self):
		if self.started: return
		self.started = True
		self.setLoggedIn()
		self.setupPage(None)
		self.setStopControl(self.getControl(106))
		self.setProgressCommands(self.startProgress,self.setProgress,self.endProgress)
		self.setTheme()
		self.fillThreadList()
		#self.setFocus(self.getControl(120))
		
	def setTheme(self):
		self.desc_base = unicode.encode(__language__(30162)+' %s','utf8')
		self.getControl(103).setLabel('[B]%s[/B]' % (self.fid != 'subscriptions' and __language__(30160) or ''))
		self.getControl(104).setLabel('[B]%s[/B]' % self.topic)
	
	def errorCallback(self,error):
		showMessage(__language__(30050),__language__(30161),error.message,error=True)
		self.endProgress()
		
	def fillThreadList(self,page=''):
		self.getControl(106).setVisible(True)
		self.setFocusId(106)
		if self.fid == 'subscriptions':
			t = self.getThread(FB.getSubscriptions,finishedCallback=self.doFillThreadList,errorCallback=self.errorCallback,name='SUBSCRIPTIONS')
			t.setArgs(page,callback=t.progressCallback,donecallback=t.finishedCallback,page_data=self.pageData)
		else:
			t = self.getThread(FB.getThreads,finishedCallback=self.doFillThreadList,errorCallback=self.errorCallback,name='THREADS')
			t.setArgs(self.fid,page,callback=t.progressCallback,donecallback=t.finishedCallback,page_data=self.pageData)
		t.start()
		
	def doFillThreadList(self,data):
		if 'newforumid' in data: self.fid = data['newforumid']
		if not data:
			if data.error == 'CANCEL': return
			LOG('GET THREADS ERROR')
			showMessage(__language__(30050),__language__(30161),__language__(30053),data.error,success=False)
			return
		
		self.empty = False
		try:
			self.getControl(120).reset()
			self.setupPage(data.pageData)
			if not (self.addForums(data['forums']) + self.addThreads(data.data)):
				LOG('Empty Forum')
				showMessage(__language__(30229),__language__(30230),success=False)
			self.setFocusId(120)
		except:
			ERROR('FILL THREAD ERROR')
			showMessage(__language__(30050),__language__(30163),error=True)
		self.setLoggedIn()
			
	def addThreads(self,threads):
		if not threads: return False
		for t in threads:
			if hasattr(t,'groupdict'):
				tdict = t.groupdict()
			else:
				tdict = t
			tid = tdict.get('threadid','')
			starter = tdict.get('starter','Unknown')
			title = tdict.get('title','')
			title = texttransform.convertHTMLCodes(FB.MC.tagFilter.sub('',title))
			last = tdict.get('lastposter','')
			fid = tdict.get('forumid','')
			sticky = tdict.get('sticky') and 'sticky' or ''
			reply_count = unicode(tdict.get('reply_number','0') or '0')
			if starter == self.me: starterbase = self.highBase
			else: starterbase = self.textBase
			#title = (tdict.get('new_post') and self.newBase or self.textBase) % title
			item = xbmcgui.ListItem(label=starterbase % starter,label2=title)
			if tdict.get('new_post'): item.setProperty('unread','unread')
			item.setInfo('video',{"Genre":sticky})
			item.setInfo('video',{"Director":starter == self.me and 'me' or ''})
			item.setInfo('video',{"Studio":last == self.me and 'me' or ''})
			item.setProperty("id",unicode(tid))
			item.setProperty("fid",unicode(fid))
			if last:
				last = self.desc_base % last
				short = tdict.get('short_content','')
				if short: last += '[CR]' + re.sub('<[^>]+?>','',texttransform.convertHTMLCodes(short))[:100]
			else:
				last = re.sub('<[^>]+?>','',texttransform.convertHTMLCodes(tdict.get('short_content','')))
			item.setProperty("last",last)
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
			title = fdict.get('title',__language__(30050))
			desc = fdict.get('description') or __language__(30172)
			text = self.textBase
			title = texttransform.convertHTMLCodes(re.sub('<[^<>]+?>','',title) or '?')
			item = xbmcgui.ListItem(label=self.textBase % __language__(30164),label2=text % title)
			item.setInfo('video',{"Genre":'is_forum'})
			item.setProperty("last",self.forum_desc_base % texttransform.convertHTMLCodes(FB.MC.tagFilter.sub('',FB.MC.brFilter.sub(' ',desc))))
			item.setProperty("title",title)
			item.setProperty("id",fid)
			item.setProperty("fid",fid)
			item.setProperty("is_forum",'True')
			if fdict.get('new_post'): item.setProperty('unread','unread')
			item.setProperty('subscribed',fdict.get('subscribed') and 'subscribed' or '')
			self.getControl(120).addItem(item)
		return True
				
	def openRepliesWindow(self):
		item = self.getControl(120).getSelectedItem()
		item.setProperty('unread','')
		fid = item.getProperty('fid') or self.fid
		topic = item.getProperty('title')
		if item.getProperty('is_forum') == 'True':
			openWindow(ThreadsWindow,"script-forumbrowser-threads.xml",fid=fid,topic=topic,parent=self.parent,item=item)
			#self.fid = fid
			#self.topic = topic
			#self.setTheme()
			#self.fillThreadList()
		else:
			openWindow(RepliesWindow,"script-forumbrowser-replies.xml" ,fid=fid,topic=topic,item=item,parent=self)

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
		PageWindow.onClick(self,controlID)
	
	def onAction(self,action):
		if action == ACTION_CONTEXT_MENU:
			self.doMenu()
		PageWindow.onAction(self,action)
		
	def doMenu(self):
		item = self.getControl(120).getSelectedItem()
		d = ChoiceMenu('Options',with_splash=True)
		try:
			if item:
				if item.getProperty("is_forum") == 'True':
					if FB.isForumSubscribed(item.getProperty('id'),item.getProperty('subscribed')):
						if FB.canUnSubscribeForum(item.getProperty('id')): d.addItem('unsubscribeforum', __language__(30242))
					else:
						if FB.canSubscribeForum(item.getProperty('id')): d.addItem('subscribeforum', __language__(30243))
				else:
					if FB.isThreadSubscribed(item.getProperty('id'),item.getProperty('subscribed')):
						if FB.canUnSubscribeThread(item.getProperty('id')): d.addItem('unsubscribe', __language__(30240))
					else:
						if FB.canSubscribeThread(item.getProperty('id')): d.addItem('subscribe', __language__(30236))
				if self.fid != 'subscriptions':
					if self.forumItem:
						if FB.isForumSubscribed(self.forumItem.getProperty('id'),self.forumItem.getProperty('subscribed')):
							if FB.canUnSubscribeForum(self.forumItem.getProperty('id')): d.addItem('unsubscribecurrentforum', __language__(30242) + ': ' + self.forumItem.getLabel()[:25])
						else:
							if FB.canSubscribeForum(self.forumItem.getProperty('id')): d.addItem('subscribecurrentforum', __language__(30243) + ': ' + self.forumItem.getLabel()[:25])
					if FB.canCreateThread(item.getProperty('id')):
						d.addItem('createthread',__language__(30252))
			d.addItem('help',__language__(30244))
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
		elif result == 'createthread':
			self.createThread()
		elif result == 'help':
			if self.fid == 'subscriptions':
				showHelp('subscriptions')
			else:
				showHelp('threads')
	
	def createThread(self):
		pm = openPostDialog(fid=self.fid,donotpost=True)
		if pm:
			splash = showActivitySplash('Creating Thread...')
			try:
				result = FB.createThread(self.fid,pm.title,pm.message)
				if result == True:
					showMessage('Success','Thread created: ','\n',pm.title,success=True)
					self.fillThreadList()
				else:
					showMessage('Failed','Failed create thread:','\n',str(result),success=False)
			finally:
				splash.close()
			
	
	def removeItem(self,item):
		clist = self.getControl(120)
		items = []
		for idx in range(0,clist.size()):
			i = clist.getListItem(idx)
			if item != i: items.append(i)
		clist.reset()
		clist.addItems(items)
		
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
class ForumsWindow(BaseWindow):
	def __init__( self, *args, **kwargs ):
		BaseWindow.__init__( self, *args, **kwargs )
		#FB.setLogin(self.getUsername(),self.getPassword(),always=__addon__.getSetting('always_login') == 'true')
		self.parent = self
		self.empty = True
		self.setAsMain()
		self.started = False
		self.headerIsDark = False
	
	def getUsername(self):
		return __addon__.getSetting('login_user_' + FB.getForumID().replace('.','_'))
		
	def getPassword(self):
		key = 'login_pass_' + FB.getForumID().replace('.','_')
		return passmanager.getPassword(key, self.getUsername())
		#return __addon__.getSetting('login_pass_' + FB.getForumID().replace('.','_'))
		
	def hasLogin(self):
		return self.getUsername() != '' and self.getPassword() != ''
		
	def onInit(self):
		try:
			self.setLoggedIn() #So every time we return to the window we check
			if self.started: return
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
		t = self.getThread(getForumBrowser,finishedCallback=self.endGetForumBrowser,errorCallback=self.errorCallback,name='GETFORUMBROWSER')
		t.setArgs(forum=forum,url=url,donecallback=t.finishedCallback)
		t.start()
		
	def endGetForumBrowser(self,fb):
		global FB
		FB = fb
		self.setTheme()
		self.getControl(112).setVisible(False)
		self.resetForum()
		self.fillForumList(True)
		__addon__.setSetting('last_forum',FB.getForumID())
		
	def setVersion(self):
		self.getControl(109).setLabel('v' + __version__)
		
	def setTheme(self):
		hc = FB.theme.get('header_color')
		if hc and hc.upper() != 'FFFFFF':
			self.headerIsDark = self.hexColorIsDark(hc)
			self.headerTextFormat = '[B]%s[/B]'
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
		self.getControl(103).setLabel(self.headerTextFormat % __language__(30170))
		self.getControl(104).setLabel(self.headerTextFormat % FB.getDisplayName())
		
	def errorCallback(self,error):
		showMessage(__language__(30050),__language__(30171),error.message,error=True)
		self.setFocusId(202)
		self.endProgress()
	
	def fillForumList(self,first=False):
		if not FB: return
		self.setLabels()
		if not FB.guestOK() and not self.hasLogin():
			yes = xbmcgui.Dialog().yesno('Login Required','This forum does not allow guest access.','Login required.','Set login info now?')
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
		if first and __addon__.getSetting('auto_thread_subscriptions_window') == 'true':
			if self.hasLogin() and FB.hasSubscriptions():
				FB.getForums(callback=self.setProgress,donecallback=self.doFillForumList)
				self.openSubscriptionsWindow()
				return
		t = self.getThread(FB.getForums,finishedCallback=self.doFillForumList,errorCallback=self.errorCallback,name='FORUMS')
		t.setArgs(callback=t.progressCallback,donecallback=t.finishedCallback)
		t.start()
		
	def doFillForumList(self,data):
		self.endProgress()
		self.setLogo(data.getExtra('logo'))
		if not data:
			self.setFocusId(202)
			if data.error == 'CANCEL': return
			showMessage(__language__(30050),__language__(30171),__language__(30053),'[CR]'+data.error,success=False)
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
				title = fdict.get('title',__language__(30050))
				desc = fdict.get('description') or __language__(30172)
				sub = fdict.get('subforum')
				if sub: desc = __language__(30173)
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
			showMessage(__language__(30050),__language__(30174),error=True)
			self.setFocusId(202)
		if self.empty: self.setFocusId(202)
		#xbmcgui.unlock()
		self.setLoggedIn()
		if not FB.guestOK() and not FB.isLoggedIn():
			yes = xbmcgui.Dialog().yesno('Login Required','This forum does not allow guest access.','Login required.','Set login info now?')
			if yes:
				setLogins()
				self.resetForum()
				self.fillForumList()
		
	def setLogoFromFile(self):
		logopath = getCurrentLogo()
		return self.getControl(250).setImage(logopath)
			
	def setLogo(self,logo):
		if not logo: return
		if getSetting('save_logos',False):
			root, ext = os.path.splitext(logo) #@UnusedVariable
			logopath = os.path.join(CACHE_PATH,FB.getForumID() + ext or '.jpg')
			if not ext:
				if not os.path.exists(logopath): logopath = os.path.join(CACHE_PATH,FB.getForumID() + '.png')
				if not os.path.exists(logopath): logopath = os.path.join(CACHE_PATH,FB.getForumID() + '.gif')
			if os.path.exists(logopath):
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
		self.getControl(249).setImage(image)
			
	def setPMCounts(self,pm_counts=None):
		if not FB: return
		disp = ''
		if not pm_counts: pm_counts = FB.getPMCounts()
		if pm_counts: disp = ' (%s/%s)' % (pm_counts.get('unread','?'),pm_counts.get('total','?'))
		self.getControl(203).setLabel(__language__(3009) + disp)
		self.setLoggedIn()
		
	def openPMWindow(self):
		openWindow(RepliesWindow,"script-forumbrowser-replies.xml" ,tid='private_messages',topic=__language__(30176),parent=self)
		self.setPMCounts(FB.getPMCounts())
		
	def openThreadsWindow(self):
		item = self.getControl(120).getSelectedItem()
		if not item: return False
		link = item.getProperty('link')
		if link:
			return self.openLink(link)
		fid = item.getProperty('id')
		topic = item.getProperty('topic')
		openWindow(ThreadsWindow,"script-forumbrowser-threads.xml",fid=fid,topic=topic,parent=self,item=item)
		self.setPMCounts(FB.getPMCounts())
		return True
		
	def openLink(self,link):
		LOG('Forum is a link. Opening URL: ' + link)
		webviewer.getWebResult(link,dialog=True,browser=hasattr(FB,'browser') and FB.browser)
	
	def openSubscriptionsWindow(self):
		fid = 'subscriptions'
		topic = __language__(30175)
		openWindow(ThreadsWindow,"script-forumbrowser-threads.xml",fid=fid,topic=topic,parent=self)
		self.setPMCounts(FB.getPMCounts())
	
	def showOnlineUsers(self):
		s = showActivitySplash('Getting List')
		try:
			users = FB.getOnlineUsers()
		finally:
			s.close()
		if isinstance(users,str):
			showMessage('Not Available',users,success=False)
			return
		users.sort(key=lambda u: u['user'].lower())
		d = OptionsChoiceMenu('Online Users')
		d.setContextCallback(self.showOnlineContext)
		for u in users:
			d.addItem(u.get('userid'),u.get('user'),u.get('avatar') or 'forum-browser-avatar-none.png',u.get('status'))
		d.getResult(close_on_context=False)
		
	def showOnlineContext(self,menu,item):
		d = ChoiceMenu('Options')
		if FB.canPrivateMessage(): d.addItem('pm',__language__(30253) % item.get('disp'))
		if FB.canGetUserInfo(): d.addItem('info','View User Info')
		result = d.getResult()
		if not result: return
		if result == 'pm':
			menu.close()
			openPostDialog(tid='private_messages',to=item.get('disp'))
		elif result == 'info':
			self.showUserInfo(item.get('id'),item.get('disp'))

	def showUserInfo(self,uid,uname):
		s = showActivitySplash('Getting Info')
		try:
			user = FB.getUserInfo(uid,uname)
			if not user: return
			out = '[B]Name:[/B] [COLOR FF550000]' + user.name + '[/COLOR]\n'
			out += '[B]Status:[/B] [COLOR FF550000]' + user.status + '[/COLOR]\n'
			out += '[B]Post Count:[/B] [COLOR FF550000]' + str(user.postCount) + '[/COLOR]\n'
			out += '[B]Join Date:[/B] [COLOR FF550000]' + user.joinDate + '[/COLOR]\n'
			if user.activity: out += '[B]Current Activity:[/B] [COLOR FF550000]' + user.activity + '[/COLOR]\n'
			if user.lastActivityDate: out += '[B]Last Activity Date:[/B] [COLOR FF550000]' + user.lastActivityDate + '[/COLOR]\n'
			for k,v in user.extras.items():
				out += '[B]' + k.title() + ':[/B] [COLOR FF550000]' + v + '[/COLOR]\n'
			showMessage('Info',out,scroll=True)
		finally:
			s.close()
		
#	def getGeneralForumURL(self):
#		forums = getSetting('exp_general_forums',[])
#		url = None
#		if forums:
#			d = ChoiceMenu('Choose forum')
#			for f in forums: d.addItem(f,f)
#			d.addItem('new','[COLOR FF00FF00]+Add New Forum[/COLOR]')
#			d.addItem('remove','[COLOR FFFF0000]-Remove A Forum[/COLOR]')
#			d.addItem('setlogin','Set Current Forum User/Pass')
#			url = d.getResult()
#			if not url: return
#			if url == 'remove': return self.removeGeneralURL()
#			if url == 'setlogin': return setLogins()
#		if not url or url == 'new':
#			url = doKeyboard('Enter full forum url')
#			if not url: return
#			self.addGeneralURL(url)
#		if not url.endswith('/'): url += '/'
#		if not url.startswith('http'): url = 'http://' + url
#		return url	
#	
#	def addGeneralURL(self,url):
#		forum = url.split('://')[-1]
#		if forum.endswith('/'): forum = forum[:-1]
#		forums = getSetting('exp_general_forums',[])
#		if forum in forums: return
#		forums.append(forum)
#		setSetting('exp_general_forums',forums)
#		
#	def removeGeneralURL(self):
#		forums = getSetting('exp_general_forums',[])
#		d = ChoiceMenu('Choose forum')
#		for f in forums: d.addItem(f,f)
#		forum = d.getResult()
#		if not forum: return
#		if forum in forums: forums.pop(forums.index(forum))
#		setSetting('exp_general_forums',forums)
		
	def changeForum(self,forum=None):
		if not forum: forum = askForum()
		if not forum: return False
		url = None
#		if forum == 'experimental.general':
#			url = self.getGeneralForumURL()
#			if not url: return
#			setSetting('exp_general_forums_last_url',url)
		self.stopThread()
		fid = 'Unknown'
		if FB: fid = FB.getForumID()
		LOG('------------------ CHANGING FORUM FROM: %s TO: %s' % (fid,forum))
		self.startGetForumBrowser(forum,url=url)
		return True

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
			if self.changeForum(): return
		elif controlID == 120:
			if not self.empty: self.stopThread()
			self.openThreadsWindow()
		elif controlID == 105:
			self.stopThread()
			return
		if BaseWindow.onClick(self, controlID): return
		if self.empty: self.fillForumList()
	
	def onAction(self,action):
		if action == ACTION_CONTEXT_MENU:
			self.doMenu()
		elif action == ACTION_PARENT_DIR or action == ACTION_PARENT_DIR2:
			action = ACTION_PREVIOUS_MENU
		if action == ACTION_PREVIOUS_MENU:
			if not self.preClose(): return
		BaseWindow.onAction(self,action)
		
	def doMenu(self):
		item = self.getControl(120).getSelectedItem()
		d = ChoiceMenu('Options',with_splash=True)
		try:
			if item:
				fid = item.getProperty('id')
				if FB.isForumSubscribed(fid,item.getProperty('subscribed')):
					if FB.canUnSubscribeForum(fid): d.addItem('unsubscribecurrentforum', __language__(30242))
				else:
					if FB.canSubscribeForum(fid): d.addItem('subscribecurrentforum', __language__(30243))
			if FB.canGetOnlineUsers():
				d.addItem('online','View Online Users')
			d.addItem('foruminfo','View Forum Info')
			d.addItem('refresh',__language__(30054))
			d.addItem('help',__language__(30244))
		finally:
			d.cancel()
		result = d.getResult()
		if result == 'subscribecurrentforum':
			if subscribeForum(fid): pass #item.setProperty('subscribed','subscribed') #commented out because can't change if we unsubscribe from subs view
		elif result == 'unsubscribecurrentforum':
			if unSubscribeForum(fid): item.setProperty('subscribed','')
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
			showHelp('forums')
		
	def showForumInfo(self):
		out = ''
		for k,v in FB.getForumInfo():
			out += u'[B]%s[/B]: [COLOR FF550000]%s[/COLOR][CR]' % (k.replace('_',' ').title(),v)
		showMessage('Forum Info',out,scroll=True)
				
	def preClose(self):
		if not __addon__.getSetting('ask_close_on_exit') == 'true': return True
		if self.closed: return True
		return xbmcgui.Dialog().yesno('Really Exit?','Really exit?')
		
	def resetForum(self,hidelogo=True):
		if not FB: return
		FB.setLogin(self.getUsername(),self.getPassword(),always=__addon__.getSetting('always_login') == 'true')
		self.getControl(201).setEnabled(FB.isLoggedIn() and FB.hasSubscriptions())
		self.getControl(203).setEnabled(FB.isLoggedIn() and FB.hasPM())
		if hidelogo: self.getControl(250).setImage('')
		__addon__.setSetting('last_forum',FB.getForumID())
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
		self.getControl(201).setEnabled(FB.isLoggedIn() and FB.hasSubscriptions())
		self.getControl(203).setEnabled(FB.isLoggedIn() and FB.hasPM())
		
	def openSettings(self):
		if not FB: return
		oldLogin = FB and self.getUsername() + self.getPassword() or ''
		doSettings()
		newLogin = FB and self.getUsername() + self.getPassword() or ''
		if not oldLogin == newLogin:
			self.resetForum(False)
			self.setPMCounts()
		self.setLoggedIn()
		self.resetForum(False)
		skin = SKINS[getSetting('skin',0)]
		if skin != THEME:
			showMessage('Skin Changed','Skin changed. Restart Forum Browser to apply.')
		forumbrowser.ForumPost.hideSignature = getSetting('hide_signatures',False)

# Functions -------------------------------------------------------------------------------------------------------------------------------------------

def openWindow(windowClass,xmlFilename,return_window=False,modal=True,theme=None,*args,**kwargs):
	theme = theme or THEME
	path = __addon__.getAddonInfo('path')
	if not getSetting('use_skin_mods',True):
		src = os.path.join(path,'resources','skins',theme,'720p',xmlFilename)
		#path = __addon__.getAddonInfo('profile')
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


	
def doKeyboard(prompt,default='',hidden=False):
	keyboard = xbmc.Keyboard(default,prompt)
	keyboard.setHiddenInput(hidden)
	keyboard.doModal()
	if not keyboard.isConfirmed(): return None
	return keyboard.getText()

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

def askForum(just_added=False,just_favs=False,caption='Choose Forum',forumID=None,hide_extra=False):
	favs = getFavorites()
	ft = os.listdir(FORUMS_STATIC_PATH)
	hidden = getHiddenForums()
	flist_tmp = []
	for f in ft:
		if not f in hidden: flist_tmp.append(f)
	flist2_tmp = os.listdir(FORUMS_PATH)
	rest = sorted(flist_tmp + flist2_tmp,key=fidSortFunction)
	if favs:
		for f in favs:
			if f in rest: rest.pop(rest.index(f))
		favs.append('')
	if just_favs:
		if not favs: return None
		whole = favs[:-1]
	elif just_added:
		whole = flist2_tmp
	else:
		whole = favs + rest
	menu = ImageChoiceMenu(caption)
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
			hc = 'FF' + fdata.theme.get('header_color','FFFFFF')
			desc = '[B]Description[/B]: [COLOR FFFF9999]' + (desc or 'None') + '[/COLOR]'
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

def setLogins(force_ask=False):
	forumID = None
	if FB: forumID = FB.getForumID()
	if not forumID or force_ask: forumID = askForum(forumID=forumID)
	if not forumID: return
	user = doKeyboard(__language__(30201),__addon__.getSetting('login_user_' + forumID.replace('.','_')))
	if user is None: return
	password = passmanager.getPassword('login_pass_' + forumID.replace('.','_'), __addon__.getSetting('login_user_' + forumID.replace('.','_')))
	password = doKeyboard(__language__(30202),password,True)
	if password is None: return
	saveUserPass(forumID,user,password)
	if not user and not password:
		showMessage('Login Cleared','Username and password cleared.')
	else:
		showMessage('Login Set','Username and password set.')
	
def saveUserPass(forumID,user,password):
	__addon__.setSetting('login_user_' + forumID.replace('.','_'),user)
	key = 'login_pass_' + forumID.replace('.','_')
	if password:
		passmanager.savePassword(key, user, password)
	else:
		__addon__.setSetting(key,'')
		
def doSettings():
	helpdict = loadHelp('options.help')
	dialog = OptionsChoiceMenu(__language__(30051))
	dialog.addItem('addfavorite',__language__(30223),'forum-browser-star.png',helpdict.get('addfavorite',''))
	dialog.addItem('removefavorite',__language__(30225),'forum-browser-star-minus.png',helpdict.get('removefavorite',''))
	dialog.addItem('addforum',__language__(30222),'forum-browser-plus.png',helpdict.get('addforum',''))
	dialog.addItem('removeforum',__language__(30224),'forum-browser-minus.png',helpdict.get('removeforum',''))
	dialog.addItem('addonline',__language__(30226),'forum-browser-arrow-left.png',helpdict.get('addonline',''))
	dialog.addItem('addcurrentonline',__language__(30241),'forum-browser-arrow-right.png',helpdict.get('addcurrentonline','')) #,disabled=FB.prefix == 'GB.')
	dialog.addItem('setcurrentcolor',"Set Current Forum Color",'forum-browser-info.png',helpdict.get('setcurrentcolor',''))
	dialog.addItem('updatethemeodb',"Update Current Theme Online",'forum-browser-info.png',helpdict.get('updatethemeodb',''))
	dialog.addItem('setlogins',__language__(30204),'forum-browser-lock.png',helpdict.get('setlogins',''))
	dialog.addItem('settings',__language__(30203),'forum-browser-wrench.png',helpdict.get('settings',''))
	dialog.addItem('help',__language__(30244),'forum-browser-info.png',helpdict.get('help',''))
	result = dialog.getResult()
	if not result: return
	if result == 'addfavorite': addFavorite()
	elif result == 'removefavorite': removeFavorite()
	elif result == 'addcurrentonline': addCurrentForumToOnlineDatabase() #addForum(current=True)
	elif result == 'addforum': addForum()
	elif result == 'addonline': addForumFromOnline()
	elif result == 'removeforum': removeForum()
	elif result == 'setcurrentcolor': return setForumColor(askColor())
	elif result == 'updatethemeodb': updateThemeODB()
	elif result == 'setlogins': setLogins(True)
#	elif result == 'register': registerForum()
	elif result == 'help': showHelp('forums')
	elif result == 'settings':
		w = openWindow(xbmcgui.WindowXMLDialog,'script-forumbrowser-overlay.xml',return_window=True,modal=False,theme='Default')
		try:
			__addon__.openSettings()
		finally:
			w.close()
			del w
		global DEBUG
		DEBUG = getSetting('debug',False)
		FB.MC.resetRegex()
		checkForSkinMods()

def loadHelp(helpfile,as_list=False):
	lang = xbmc.getLanguage().split(' ',1)[0]
	addonPath = xbmc.translatePath(__addon__.getAddonInfo('path'))
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

def showText(caption,text):
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
		addonPath = xbmc.translatePath(__addon__.getAddonInfo('path'))
		changelogPath = os.path.join(addonPath,'changelog.txt')
		showText('Changelog',open(changelogPath,'r').read())

def showInfo(infotype):
	infotype += '.info'
	lang = xbmc.getLanguage().split(' ',1)[0]
	addonPath = xbmc.translatePath(__addon__.getAddonInfo('path'))
	infofilefull = os.path.join(addonPath,'resources','language',lang,infotype)
	if not os.path.exists(infofilefull):
		infofilefull = os.path.join(addonPath,'resources','language','English',infotype)
	if not os.path.exists(infofilefull): return None
	showText('Info',open(infofilefull,'r').read())
	
def registerForum():
	url = FB.getRegURL()
	LOG('Registering - URL: ' + url)
	webviewer.getWebResult(url,dialog=True)

def addFavorite():
	if not FB: return
	forum = FB.getForumID()
	favs = getFavorites()
	if forum in favs: return
	favs.append(forum)
	__addon__.setSetting('favorites','*:*'.join(favs))
	showMessage('Added','Current forum added to favorites!')
	
def removeFavorite():
	forum = askForum(just_favs=True)
	if not forum: return
	favs = getFavorites()
	if not forum in favs: return
	favs.pop(favs.index(forum))
	__addon__.setSetting('favorites','*:*'.join(favs))
	showMessage('Removed','Forum removed from favorites.')
	
def getFavorites():
	favs = __addon__.getSetting('favorites')
	if favs:
		favs = favs.split('*:*')
	else:
		favs = []
	return favs
	
def selectForumCategory(with_all=False):
	d = ChoiceMenu('Select Category')
	if with_all: d.addItem('all','Show All')
	for x in range(0,17):
		d.addItem(str(x), str(__language__(30500 + x)))
	return d.getResult()

def addForum(current=False):
	if not FB: return
	dialog = xbmcgui.DialogProgress()
	dialog.create('Add Forum')
	dialog.update(0,'Enter Name/Address')
	info = None
	user = None
	password=None
	try:
		if current:
			ftype = FB.prefix[:2]
			forum = FB.forum
			url = orig = FB._url
			url = tapatalk.testForum(url)
			if url: pageURL = url.split('/mobiquo/',1)[0]
			if not url:
				from forumbrowser import forumrunner
				url = forumrunner.testForum(orig)
			if url: pageURL = url.split('/forumrunner/',1)[0]
			if not url:
				showMessage('Failed','Forum not found or not compatible',success=False)
				return
		else:
			forum = doKeyboard('Enter forum URL')
			if forum == None: return
			dialog.update(10,'Testing Forum: Tapatalk')
			url = tapatalk.testForum(forum)
			ftype = ''
			label = ''
			if url:
				ftype = 'TT'
				label = 'Tapatalk'
				pageURL = url.split('/mobiquo/',1)[0]
			else:
				dialog.update(13,'Testing Forum: Forumrunner')
				from forumbrowser import forumrunner #@Reimport
				url = forumrunner.testForum(forum)
				if url:
					ftype = 'FR'
					label = 'Forumrunner'
					pageURL = url.split('/forumrunner/',1)[0]
					
			if not url:
				dialog.update(16,'Testing Forum: Parser Browser')
				yes = xbmcgui.Dialog().yesno('Question...','Does this forum require a login?','Click "Yes" if you cannot view this forum','without already being a member.')
				if yes:
					user = doKeyboard(__language__(30201))
					if user: password = doKeyboard(__language__(30202),hidden=True)
				from forumbrowser import genericparserbrowser
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
				showMessage('Failed','Forum not found or not compatible',success=False)
				return
		
			showMessage('Found','Forum %s found' % forum,'[CR]Type: ' + label,'[CR]'+ url,success=True)
			if ftype == 'GB':
				if parser.getForumTypeName().lower() == 'generic':
					showInfo('parserbrowser-generic')
				else:
					showInfo('parserbrowser-normal')
			forum = url.split('http://',1)[-1].split('/',1)[0]
			
		dialog.update(20,'Getting Description And Images')
		if not info: info = forumbrowser.HTMLPageInfo(pageURL)
		tmp_desc = info.description(info.title(''))
		tmp_desc = texttransform.convertHTMLCodes(tmp_desc).strip()
		images = info.images()
		dialog.update(30,'Enter Description')
		desc = doKeyboard('Enter Description',default=tmp_desc)
		if not desc: desc = tmp_desc
		dialog.update(40,'Choose Logo')
		logo = chooseLogo(forum,images)
		LOG('Adding Forum: %s at URL: %s' % (forum,url))
		name = forum
		if name.startswith('www.'): name = name[4:]
		if name.startswith('forum.'): name = name[6:]
		if name.startswith('forums.'): name = name[7:]
		forumID = ftype + '.' + name
		saveForum(ftype,forumID,name,desc,url,logo)
		if user and password: saveUserPass(forumID,user,password)
		dialog.update(60,'Add To Online Database')
		if not (not current and ftype == 'GB'): addForumToOnlineDatabase(name,url,desc,logo,ftype,dialog=dialog)
	finally:
		dialog.close()
	
def saveForum(ftype,forumID,name,desc,url,logo,header_color="FFFFFF"): #TODO: Do these all the same. What... was I crazy?
	if ftype == 'TT':
		open(os.path.join(FORUMS_PATH,forumID),'w').write('#%s\n#%s\nurl:tapatalk_server=%s\nurl:logo=%s\ntheme:header_color=%s' % (name,desc,url,logo,header_color))
	elif ftype == 'FR':
		open(os.path.join(FORUMS_PATH,forumID),'w').write('#%s\n#%s\nurl:forumrunner_server=%s\nurl:logo=%s\ntheme:header_color=%s' % (name,desc,url,logo,header_color))
	else:
		open(os.path.join(FORUMS_PATH,forumID),'w').write('#%s\n#%s\nurl:server=%s\nurl:logo=%s\ntheme:header_color=%s' % (name,desc,url,logo,header_color))
	
def addForumFromOnline():
	odb = forumbrowser.FBOnlineDatabase()
	res = True
	while res:
		res = selectForumCategory(with_all=True)
		if not res: return
		cat = res
		if cat == 'all': cat = None
		splash = showActivitySplash('Getting Forums List')
		try:
			flist = odb.getForumList(cat)
		finally:
			splash.close()
		if not flist:
			showMessage('No Forums','No forums in that category.')
			continue
		if cat and cat.isdigit():
			caption = '[COLOR FF9999FF]'+str(__language__(30500 + int(cat)))+'[/COLOR]'
		else:
			caption = '[COLOR FF9999FF]All[/COLOR]'
		menu = ImageChoiceMenu(caption)
		for f in flist:
			interface = f.get('type')
			rf=ra=''
			if interface == 'GB':
				rf = {'1':'FFFF0000','2':'FFFFFF00','3':'FF00FF00'}.get(f.get('rating_function'),'')
				ra = {'1':'FFFF0000','2':'FFFFFF00','3':'FF00FF00'}.get(f.get('rating_accuracy'),'')
			desc = f.get('desc','None') or 'None'
			desc = '[B]Category[/B]: [COLOR FFFF9999]' + str(__language__(30500 + f.get('cat',0))) + '[/COLOR][CR][CR][B]Description[/B]: [COLOR FFFF9999]' + desc + '[/COLOR]'
			menu.addItem(f, f.get('name'), f.get('logo'), desc,bgcolor='FF' + f.get('header_color','FFFFFF'),interface=interface,function=rf,accuracy=ra)
		for f in getHiddenForums():
			path = getForumPath(f,just_path=True)
			if not path: continue
			fdata = forumbrowser.ForumData(f,path)
			name = fdata.name
			desc = fdata.description
			logo = fdata.urls.get('logo','')
			hc = 'FF' + fdata.theme.get('header_color','FFFFFF')
			menu.addItem(f,name,logo,'Hidden (Built-in)[CR]' + desc,bgcolor=hc)
			
		f = menu.getResult('script-forumbrowser-forum-select.xml')
		if f:
			doAddForumFromOnline(f)
			return
	
def doAddForumFromOnline(f):
	if not isinstance(f,dict):
		unHideForum(f)
		return
	saveForum(f['type'],f['type']+'.'+f['name'],f['name'],f.get('desc',''),f['url'],f.get('logo',''),f.get('header_color',''))
	showMessage('Added','Forum added: ' + f['name'])
	
def addCurrentForumToOnlineDatabase():
	fdata = forumbrowser.ForumData(FB.getForumID(),FORUMS_PATH)
	url = fdata.urls.get('tapatalk_server',fdata.urls.get('forumrunner_server',fdata.urls.get('server',FB._url)))
	print url
	if not url: raise Exception('No URL')
	addForumToOnlineDatabase(fdata.name,url,fdata.description,fdata.urls.get('logo'),FB.getForumID()[:2],header_color=FB.theme.get('header_color','FFFFFF'))
	
def addForumToOnlineDatabase(name,url,desc,logo,ftype,header_color='FFFFFF',dialog=None):
	if not xbmcgui.Dialog().yesno('Add To Database?','Share to the Forum Browser','online database?'): return
	LOG('Adding Forum To Online Database: %s at URL: %s' % (name,url))
	frating = arating = '0'
	if ftype == 'GB':
		frating,arating = askForumRating()
		if not frating:
			showMessage('Failed','Forum must be rated in order to be added to the online database.',success=False)
			return
		
	cat = selectForumCategory() or '0'
	if dialog: dialog.update(80,'Saving To Database')
	odb = forumbrowser.FBOnlineDatabase()
	msg = odb.addForum(name, url, logo, desc, ftype, cat, rating_function=frating, rating_accuracy=arating, header_color=header_color)
	if msg == 'OK':
		showMessage('Added','Forum added successfully',success=True)
	elif msg =='EXISTS':
		showMessage('Updated','Forum entry exists. Updated successfully',success=True)
	else:
		showMessage('Not Added','Forum not added:',str(msg),success=False)
		LOG('Forum Not Added: ' + str(msg))
	
def askForumRating():
	d = ChoiceMenu('Function Rating')
	d.addItem('3','Fully Functional')
	d.addItem('2','Partially Functional')
	d.addItem('1','Not Functional')
	frating = d.getResult()
	if not frating: return None,None
	d = ChoiceMenu('Accuracy Rating')
	d.addItem('3','Full Accuracy')
	d.addItem('2','OK Accuracy')
	d.addItem('1','Poor Accuracy')
	arating = d.getResult()
	if not arating: return None,None
	return frating,arating
	
def chooseLogo(forum,image_urls):
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
	menu = ImageChoiceMenu('Choose Logo')
	for url in image_urls: menu.addItem(url, url, url)
	url = menu.getResult()
	return url or ''
	
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
		
def getCurrentLogo():
	logo = FB.urls.get('logo')
	root, ext = os.path.splitext(logo) #@UnusedVariable
	logopath = os.path.join(CACHE_PATH,FB.getForumID() + (ext or '.jpg'))
	if os.path.exists(logopath): return logopath
	logopath = os.path.join(CACHE_PATH,FB.getForumID() + '.png')
	if os.path.exists(logopath): return logopath
	logopath = os.path.join(CACHE_PATH,FB.getForumID() + '.gif')
	if os.path.exists(logopath): return logopath
	logopath = os.path.join(CACHE_PATH,FB.getForumID() + '.ico')
	if os.path.exists(logopath): return logopath
	return logo

def askColor():
	#fffaec
	w = openWindow(ColorDialog,'script-forumbrowser-color-dialog.xml',return_window=True,image=getCurrentLogo(),hexcolor=FB.theme.get('header_color'))
	hexc = w.hexValue()
	del w
	return hexc
	
def getHexColor(hexc=None):
	hexc = doKeyboard('Enter 6-Digit Hex Color',default=hexc)
	if not hexc: return None
	while len(hexc) != 6 or re.search('[^1234567890abcdef](?i)',hexc):
		showMessage('Error','Invalid Hex Color')
		hexc = doKeyboard('Enter 6-Digit Hex Color',default=hexc)
		if not hexc: return None
	return hexc
	
def setForumColor(color):
	if not color: return False
	fid = FB.getForumID()
	fdata = forumbrowser.ForumData(fid,FORUMS_PATH)
	fdata.theme['header_color'] = color
	FB.theme['header_color'] = color
	fdata.writeData()
	showMessage('Done','Color Set!')
	return True

def updateThemeODB():
	odb = forumbrowser.FBOnlineDatabase()
	vals_dict= {'header_color':FB.theme.get('header_color')}
	result = str(odb.setTheme(FB.getForumID()[3:],vals_dict))
	LOG('Updating ODB Theme: ' + result)
	if result == '1':
		showMessage('Done','Online database color updated.')
	else:
		showMessage('Failed','Failed to update the online database.')

def getHiddenForums():
	flist = __addon__.getSetting('hidden_static_forums')
	if flist: flist = flist.split('*:*')
	else: flist = []
	return flist

def unHideForum(forum):
	flist = getHiddenForums()
	if forum in flist: flist.pop(flist.index(forum))
	__addon__.setSetting('hidden_static_forums','*:*'.join(flist))
	
def removeForum():
	forum = askForum(caption='Choose Forum To Remove',hide_extra=True)
	if not forum: return
	path = os.path.join(FORUMS_STATIC_PATH,forum)
	if os.path.exists(path):
		flist = getHiddenForums()
		if not forum in flist: flist.append(forum)
		__addon__.setSetting('hidden_static_forums','*:*'.join(flist))
		return
	path = os.path.join(FORUMS_PATH,forum)
	if not os.path.exists(path): return
	os.remove(path)
	showMessage('Removed','Forum removed.')

def showMessage(caption,text,text2='',text3='',error=False,success=None,scroll=False):
	if text2: text += '[CR]' + text2
	if text3: text += '[CR]' + text3
	w = MessageDialog('script-forumbrowser-message-dialog.xml' ,xbmc.translatePath(__addon__.getAddonInfo('path')),'Default',caption=caption,text=text,error=error,success=success,scroll=scroll)
	w.doModal()
	del w

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
		if self.scroll and not getSetting('message_dialog_always_show_ok',False):
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
		self.colorsDir = os.path.join(CACHE_PATH,'colors')
		self.colorGif = os.path.join(xbmc.translatePath(__addon__.getAddonInfo('path')),'white1px.gif')
		xbmcgui.WindowXMLDialog.__init__( self )
	
	def onInit(self):
		clist = self.getControl(120)
		clist.reset()
		colors = {}
		if not os.path.exists(self.colorsDir): os.makedirs(self.colorsDir)
		
		for i in self.items:
			item = xbmcgui.ListItem(label=i['disp'],label2=i['disp2'],thumbnailImage=i['icon'])
			if i['sep']: item.setProperty('SEPARATOR','SEPARATOR')
			item.setProperty('bgcolor',i['bgcolor'])
			color = i['bgcolor'].upper()[2:]
			if color in colors:
				path = colors[color]
			else:
				path = self.makeColorFile(color, self.colorsDir)
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
		
	def makeColorFile(self,color,path):
		replace = binascii.unhexlify(color)
		replace += replace
		target = os.path.join(path,color + '.gif')
		open(target,'w').write(open(self.colorGif,'r').read().replace(chr(255)*6,replace))
		return target
		
	def onAction(self,action):
		if action == 92 or action == 10:
			self.doClose()
		elif action == 7:
			self.finish()
		elif action == ACTION_CONTEXT_MENU:
			self.doMenu()
	
	def doClose(self):
		clearDirFiles(self.colorsDir)
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
			
	def finish(self):
		self.result = self.getControl(120).getSelectedPosition()
		self.doClose()
		
	def onFocus( self, controlId ): self.controlId = controlId
		
class ActivitySplashWindow(xbmcgui.WindowXMLDialog):
	def __init__( self, *args, **kwargs ):
		self.caption = kwargs.get('caption')
		self.canceled = False
		
	def onInit(self):
		self.getControl(100).setLabel(self.caption)
		
	def update(self,message):
		self.getControl(100).setLabel(message)
		return not self.canceled
		
	def onAction(self,action):
		if action == ACTION_PARENT_DIR or action == ACTION_PARENT_DIR2: action = ACTION_PREVIOUS_MENU
		if action == ACTION_PREVIOUS_MENU:
			self.canceled = True
	
	def onClick(self,controlID):
		pass
	
class ActivitySplash():
	def __init__(self,caption=''):
		self.splash = openWindow(ActivitySplashWindow,'script-forumbrowser-loading-splash.xml',return_window=True,modal=False,theme='Default',caption=caption)
		self.splash.show()
		
	def update(self,pct,message):
		self.splash.update(message)

	def close(self):
		if not self.splash: return
		self.splash.close()
		del self.splash
		self.splash = None
		
def showActivitySplash(caption=__language__(30248)):
	s = ActivitySplash(caption)
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
		idx = self.getChoiceIndex()
		if idx < 0: return None
		if self.items[idx]['disabled']: return None
		return self.items[idx]['id']

class OptionsChoiceMenu(ChoiceMenu):
	def getResult(self,windowFile='script-forumbrowser-options-dialog.xml',select=None,close_on_context=True):
		self.closeContext = close_on_context
		w = openWindow(ImageChoiceDialog,windowFile,return_window=True,theme='Default',menu=self,items=self.items,caption=self.caption,select=select)
		result = w.result
		del w
		if result == None: return None
		if self.items[result]['disabled']: return None
		return self.items[result]['id']
		
class ImageChoiceMenu(ChoiceMenu):
	def getResult(self,windowFile='script-forumbrowser-image-dialog.xml',select=None):
		w = openWindow(ImageChoiceDialog,windowFile ,return_window=True,theme='Default',menu=self,items=self.items,caption=self.caption,select=select)
		result = w.result
		del w
		if result == None: return None
		return self.items[result]['id']
	
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
			idx = int(__addon__.getSetting('language'))
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
		
class DownloadThread(StoppableThread):
	def __init__(self,targetdir,urllist,ext='',callback=None,old_thread=None,nothread=False):
		StoppableThread.__init__(self,name='Downloader')
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
	def __init__(self,header=__language__(30205),message=''):
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
				self.display = 'File %s of %s' % (i+1,self.total)
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
			self.display = __language__(30206) % os.path.basename(path)
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
	
def copyKeyboardModImages(skinPath):
	dst = os.path.join(skinPath,'media','forum-browser-keyboard')
	if os.path.exists(dst): return
	os.makedirs(dst)
	src = os.path.join(xbmc.translatePath(__addon__.getAddonInfo('path')),'keyboard','images')
	import shutil
	for f in os.listdir(src):
		s = os.path.join(src,f)
		d = os.path.join(dst,f)
		if not os.path.exists(d) and not f.startswith('.'): shutil.copy(s,d)

def copyFont(sourceFontPath,skinPath):
	dst = os.path.join(skinPath,'fonts','ForumBrowser-DejaVuSans.ttf')
	if os.path.exists(dst): return
	import shutil
	shutil.copy(sourceFontPath,dst)
	
def copyTree(source,target):
	import shutil
	shutil.copytree(source, target)
		
def checkForSkinMods():
	if __addon__.getSetting('use_skin_mods') != 'true': return			
	skinPath = xbmc.translatePath('special://skin')
	font = os.path.join(skinPath,'fonts','ForumBrowser-DejaVuSans.ttf')
	if os.path.exists(font): return
	yes = xbmcgui.Dialog().yesno('Skin Mods','Recommended skin modifications not installed.','(Requires XBMC restart to take effect.)','Install now?')
	if not yes:
		__addon__.setSetting('user_skin_mods','false')	
		return
	LOG('Installing Skin Mods')
	doModKeyboard('',no_keyboard=True)

def doModKeyboard(prompt,default='',hidden=False,no_keyboard=False):
	if __addon__.getSetting('use_skin_mods') != 'true': return doKeyboard(prompt,default,hidden) 
		
	#restart = False
	fbPath = xbmc.translatePath(__addon__.getAddonInfo('path'))
	localAddonsPath = os.path.join(xbmc.translatePath('special://home'),'addons')
	skinPath = xbmc.translatePath('special://skin')
	if skinPath.endswith(os.path.sep): skinPath = skinPath[:-1]
	currentSkin = os.path.basename(skinPath)
	localSkinPath = os.path.join(localAddonsPath,currentSkin)
	
	if not os.path.exists(localSkinPath):
		yesno = xbmcgui.Dialog().yesno('Skin Mod Install',currentSkin + ' skin not installed in user path.','Click Yes to copy,','click No to Abort')
		if not yesno: return
		dialog = xbmcgui.DialogProgress()
		dialog.create('Copying Files','Please wait...')
		try:
			
			copyTree(skinPath,localSkinPath)
		except:
			err = ERROR('Failed to copy skin to user directory')
			showMessage('Error',err,'Failed to copy files, aborting.',error=True)
			return
		finally:
			dialog.close()
		#restart = True
		showMessage('Success','Files copied.','XBMC needs to be restarted','for mod to take effect',success=True)
	skinPath = localSkinPath
	
	sourcePath = os.path.join(fbPath,'keyboard','DialogKeyboard.xml')
	sourceFontXMLPath = os.path.join(fbPath,'keyboard','Font-720p.xml')
	sourceFontPath = os.path.join(fbPath,'keyboard','ForumBrowser-DejaVuSans.ttf')
	
	dialogPath = os.path.join(skinPath,'720p','DialogKeyboard.xml')
	backupPath = os.path.join(skinPath,'720p','DialogKeyboard.xml.FBbackup')
	fontPath = os.path.join(skinPath,'720p','Font.xml')
	fontBackupPath = os.path.join(skinPath,'720p','Font.xml.FBbackup')
	if not os.path.exists(dialogPath):
		dialogPath = dialogPath.replace('720p','1080i')
		backupPath = backupPath.replace('720p','1080i')
		fontPath = fontPath.replace('720p','1080i')
		fontBackupPath = fontBackupPath.replace('720p','1080i')
		sourceFontXMLPath = sourceFontXMLPath.replace('720p','1080i')
	
	if DEBUG:
		LOG('Local Addons Path: %s' % localAddonsPath)
		LOG('Current skin: %s' % currentSkin)
		LOG('Skin path: %s' % skinPath)
		LOG('Target path: %s' % dialogPath)
		LOG('Source path: %s' % sourcePath)
	
	copyKeyboardModImages(skinPath)
	copyFont(sourceFontPath,skinPath)
	
	if not os.path.exists(backupPath):
		if DEBUG: LOG('Creating backup of original skin file: ' + backupPath)
		open(backupPath,'w').write(open(dialogPath,'r').read())
		
	if not os.path.exists(fontBackupPath):
		if DEBUG: LOG('Creating backup and replacing original skin file: ' + fontBackupPath)
		open(fontBackupPath,'w').write(open(fontPath,'r').read())
		original = open(fontPath,'r').read()
		modded = original.replace('<font>',open(sourceFontXMLPath,'r').read() + '<font>',1)
		open(fontPath,'w').write(modded)
	
	if no_keyboard: return
	
	os.remove(dialogPath)
	
	open(dialogPath,'w').write(open(sourcePath,'r').read())
	ret = doKeyboard(prompt,default,hidden)
	
	os.remove(dialogPath)
	open(dialogPath,'w').write(open(backupPath,'r').read())
	#Remove added files
	os.remove(backupPath)
	return ret

def getForumList():
	ft = os.listdir(FORUMS_STATIC_PATH)
	ft2 = os.listdir(FORUMS_PATH)
	flist = []
	for f in ft + ft2:
		if not f.startswith('.') and not f == 'general':
			if not f in flist: flist.append(f)
	return flist

def checkPasswordEncryption():
	if __addon__.getSetting('passwords_encrypted') == 'true': return
	__addon__.setSetting('passwords_encrypted','true')
	flist = getForumList()
	for f in flist:
		key = 'login_pass_' + f.replace('.','_')
		user = __addon__.getSetting('login_user_' + f.replace('.','_'))
		if not user: continue
		password = __addon__.getSetting(key)
		if not password: continue
		LOG('Encrypting password for: ' + f)
		passmanager.savePassword(key, user, password)
	
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
		
def getForumBrowser(forum=None,url=None,donecallback=None):
	if not forum: forum = __addon__.getSetting('last_forum') or 'TT.xbmc.org'
	#global FB
	#if forum.startswith('GB.') and not url:
	#	url = getSetting('exp_general_forums_last_url')
	#	if not url: forum = 'TT.xbmc.org'
		
	if not getForumPath(forum): forum = 'TT.xbmc.org'
	err = ''
	try:
		if forum.startswith('GB.'):
			err = 'getForumBrowser(): General'
			from forumbrowser import genericparserbrowser
			FB = genericparserbrowser.GenericParserForumBrowser(forum,always_login=getSetting('always_login',False))
		elif forum.startswith('TT.'):
			err = 'getForumBrowser(): Tapatalk'
			FB = tapatalk.TapatalkForumBrowser(forum,always_login=__addon__.getSetting('always_login') == 'true')
		elif forum.startswith('FR.'):
			err = 'getForumBrowser(): Forumrunner'
			from forumbrowser import forumrunner
			FB = forumrunner.ForumrunnerForumBrowser(forum,always_login=__addon__.getSetting('always_login') == 'true')
		#else:
		#	err = 'getForumBrowser(): Boxee'
		#	from forumbrowser import parserbrowser
		#	FB = parserbrowser.ParserForumBrowser(forum,always_login=__addon__.getSetting('always_login') == 'true')
	except forumbrowser.ForumMovedException,e:
		showMessage(__language__(30050),'Error accessing forum.\n\nIt apppears the forum may have moved. Check the forum address in a browser and try re-adding it, or if there is a URL listed below, you can try re-adding it with that URL.\n',e.message,error=True)
		return False
	except forumbrowser.ForumNotFoundException,e:
		showMessage(__language__(30050),'Error accessing forum.\n\nIt apppears the forum interface (%s) is no longer installed, is missing or has moved.\n\nVerify the forum\'s URL in a browser and then try re-adding it.\n\nCheck with the forum administrator if the problem persists.' % e.message,error=True)
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
			showMessage(__language__(30050),'Error accessing forum.\n\nForum interface appears to have changed from %s to %s.\n\nTry re-adding it.' % (fromType,toType),error=True)
		else:
			showMessage(__language__(30050),'Error accessing forum.\n\nPlease contact the forum administrator if this problem continues.',error=True)
		return False
	except:
		err = ERROR(err)
		showMessage(__language__(30050),__language__(30171),err,error=True)
		return False
	
	if donecallback: donecallback(FB)
	return True

######################################################################################
# Startup
######################################################################################
if sys.argv[-1] == 'settings':
	doSettings()
elif sys.argv[-1] == 'settingshelp':
	showHelp('settings')
else:
	forumbrowser.ForumPost.hideSignature = getSetting('hide_signatures',False)
	checkForSkinMods()
	checkPasswordEncryption()

	TD = ThreadDownloader()
	
	openWindow(ForumsWindow,"script-forumbrowser-forums.xml")
	#sys.modules.clear()
	