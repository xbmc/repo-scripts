import threading, xbmc, xbmcgui, time, re, signals, asyncconnections, dialogs
from xbmcconstants import *  # @UnusedWildImport
from lib.forumbrowser import forumbrowser
from util import LOG, ERROR, T, StoppableThread

SIGNALHUB = None

######################################################################################
# Base Window Classes
######################################################################################
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
		if xbmc.abortRequested:
			self.stop()
			return False
		if self.stopped(): return False
		if self._progressCallback: self._progressHelper(self._progressCallback,*args,**kwargs)
		return True
		
	def finishedCallback(self,*args,**kwargs):
		if xbmc.abortRequested:
			self.stop()
			return False
		if self.stopped(): return False
		if self._finishedCallback: self._finishedHelper(self._finishedCallback,*args,**kwargs)
		return True
	
	def errorCallback(self,error):
		if xbmc.abortRequested:
			self.stop()
			return False
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
		self._funcID = 0
		if SIGNALHUB: SIGNALHUB.registerSelfReceiver('RUN_IN_MAIN', self, self.runInMainCallback)
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
		
	def runInMainCallback(self,signal,data):
		if self._functionStack:
			func,args,kwargs = self.getNextFunction(data)
			if not func: return
			func(*args,**kwargs)
	
	def onAction(self,action):
		if action == ACTION_RUN_IN_MAIN:
			#print 'yy %s' % repr(self._functionStack)
			if self._functionStack:
				self.runInMainCallback(None, None)
				return True
			else:
				signals.sendSignal('RUN_IN_MAIN')
		elif action == ACTION_PREVIOUS_MENU:
			asyncconnections.StopConnection()
			if self._currentThread and self._currentThread.isAlive():
				self._currentThread.stop()
				if self._endCommand: self._endCommand()
				if self._stopControl: self._stopControl.setVisible(False)
			if self._isMain and len(threading.enumerate()) > 1:
				d = xbmcgui.DialogProgress()
				d.create(T(32220),T(32221))
				d.update(0)
				self.stopThreads()
				if d.iscanceled():
					d.close()
					return True
				d.close()
			return False
		return False
	
	def onClose(self):
		if SIGNALHUB: SIGNALHUB.unRegister(None, self)
		
	def stopThreads(self):
		for t in threading.enumerate():
			if isinstance(t,StoppableThread): t.stop()
		time.sleep(1)
		while len(threading.enumerate()) > 1:
			for t in threading.enumerate():
				#if t != threading.currentThread(): t.join()
				if isinstance(t,StoppableThread) and t.isAlive(): t.raiseExc(Exception)
			time.sleep(1)
	
	def _resetFunction(self):
		self._functionStack = []
	
	def getNextFunction(self,funcID):
		if self._functionStack:
			for i in range(0,len(self._functionStack)):
				if funcID == self._functionStack[i][3]: return self._functionStack.pop(i)[:-1]
		return (None,None,None)
		
	def addFunction(self,function,args,kwargs,funcID):
		self._functionStack.append((function,args,kwargs,funcID))
		
	def runInMain(self,function,*args,**kwargs):
		#print 'xx %s' % repr(function)
		funcID = function.__name__ + ':' + str(self._funcID)
		self.addFunction(function, args, kwargs,funcID)
		signals.sendSelfSignal(self,'RUN_IN_MAIN',funcID)
		self._funcID+=1
		if self._funcID > 9999: self._funcID = 0
		#xbmc.executebuiltin('Action(codecinfo)')
		
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
		asyncconnections.StopConnection()
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
		self._externalWindow = None
		self._progressWidth = 1
		ThreadWindow.__init__(self)
		
	def externalWindow(self):
		if not self._externalWindow: self._externalWindow = self._getExternalWindow()
		return self._externalWindow
		
	def _getExternalWindow(self): pass
	
	def onClick( self, controlID ):
		return False
			
	def onAction(self,action):
		if action == ACTION_PARENT_DIR or action == ACTION_PARENT_DIR2:
			action = ACTION_PREVIOUS_MENU
		if ThreadWindow.onAction(self,action): return
		if action == ACTION_PREVIOUS_MENU:
			self.doClose()
		#xbmcgui.WindowXML.onAction(self,action)
	
	def doClose(self):
		self.closed = True
		self.close()
		self.onClose()
	
	def startProgress(self):
		self._progMessageSave = self.getControl(104).getLabel()
		self._progressWidth = self.getControl(300).getWidth()
		#self.getControl(310).setVisible(True)
	
	def setProgress(self,pct,message=''):
		if pct<0:
			self.stopThread()
			dialogs.showMessage('ERROR',message,error=True)
			return False
		w = int((pct/100.0)*self._progressWidth)
		self.getControl(310).setWidth(w)
		self.getControl(104).setLabel(self.headerTextFormat % message)
		return True
		
	def endProgress(self):
		#self.getControl(310).setVisible(False)
		self.getControl(104).setLabel(self._progMessageSave)
		
	def highlightTerms(self,FB,message):
		message = self.searchRE[0].sub(self.searchReplace,message)
		for sRE in self.searchRE[1:]: message = sRE.sub(self.searchWordReplace,message)
		message = message.replace('\r','')
		message = FB.MC.removeNested(message,'\[/?B\]','[B]')
		return message
	
	def searchReplace(self,m):
		return '[COLOR FFFF0000][B]%s[/B][/COLOR]' % '\r'.join(list(m.group(0)))
	
	def searchWordReplace(self,m):
		return '[COLOR FFAAAA00][B]%s[/B][/COLOR]' % m.group(0)
	
	def setupSearch(self):
		self.searchRE = None
		if self.search and not self.search.startswith('@!RECENT'):
			self.searchRE = [re.compile(re.sub('[\'"]','',self.search),re.I)]
			words = self.getSearchWords(self.search)
			if len(words) > 1:
				for w in words: self.searchRE.append(re.compile(w,re.I))
	
	def getSearchWords(self,text):
		words = []
		quoted = re.findall('(?P<quote>["\'])(.+?)(?P=quote)',text)
		for q in quoted: words.append(q[1])
		words += re.sub('(?P<quote>["\'])(.+?)(?P=quote)','',text).split()
		return words
	
class BaseWindow(xbmcgui.WindowXML,BaseWindowFunctions):
	def __init__(self, *args, **kwargs):
		BaseWindowFunctions.__init__(self, *args, **kwargs)
		xbmcgui.WindowXML.__init__( self )
		self.closed
		
	def onInit(self):
		pass
		
	def onAction(self,action):
		BaseWindowFunctions.onAction(self,action)
	
	def setProperty(self,key,value):
		self.externalWindow().setProperty(key,value)
		
	def _getExternalWindow(self):
		return xbmcgui.Window(xbmcgui.getCurrentWindowId())
		
class BaseWindowDialog(xbmcgui.WindowXMLDialog,BaseWindowFunctions):
	def __init__(self, *args, **kwargs):
		BaseWindowFunctions.__init__(self, *args, **kwargs)
		xbmcgui.WindowXMLDialog.__init__( self )
	
	def onInit(self):
		pass
		
	def onAction(self,action):
		BaseWindowFunctions.onAction(self,action)
	
	def setProperty(self,key,value):
		self.externalWindow().setProperty(key,value)
		
	def _getExternalWindow(self):
		return xbmcgui.Window(xbmcgui.getCurrentWindowDialogId())
	
class PageWindow(BaseWindow):
	def __init__( self, *args, **kwargs ):
		self.next = ''
		self.prev = ''
		self.pageData = None
		self._totalItems = kwargs.get('total_items',0)
		self.firstRun = True
		self._firstPage = T(32110)
		self._lastPage = T(32111)
		self._newestPage = None
		BaseWindow.__init__( self, *args, **kwargs )
		
	def setPageData(self,FB):
		self.pageData = FB.getPageData(total_items=self._totalItems)
		
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
		options = [self._firstPage,self._lastPage]
		if self._newestPage: options.append(self._newestPage)
		options.append(T(32115))
		idx = dialogs.dialogSelect(T(32114),options)
		if idx < 0: return
		if options[idx] == self._firstPage: self.gotoPage(self.pageData.getPageNumber(1))
		elif options[idx] == self._lastPage: self.gotoPage(self.pageData.getPageNumber(-1))
		elif options[idx] == self._newestPage:
			self.firstRun = True #For replies window
			self.gotoPage(self.pageData.getPageNumber(-1))
		else: self.askPageNumber()
		
	def askPageNumber(self):
		page = xbmcgui.Dialog().numeric(0,T(32116))
		try: int(page)
		except: return
		self.gotoPage(self.pageData.getPageNumber(page))
		
	def setupPage(self,pageData):
		if pageData:
			self.pageData = pageData
		else:
			from lib.forumbrowser.forumbrowser import PageData
			pageData = PageData(None)
		self.getControl(200).setVisible(pageData.prev)
		self.getControl(202).setVisible(pageData.next)
		self.getControl(105).setLabel(pageData.getPageDisplay())
		
	def gotoPage(self,page): pass