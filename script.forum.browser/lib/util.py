import os, sys, xbmc, xbmcaddon, filelock

__addon__ = xbmcaddon.Addon(id='script.forum.browser')
T = __addon__.getLocalizedString

SETTINGS_PATH = os.path.join(xbmc.translatePath(__addon__.getAddonInfo('profile')),'settings.xml')

class AbortRequestedException(Exception): pass
class StopRequestedException(Exception): pass

LOG_PREFIX = 'FORUMBROWSER' 

def ERROR(message,hide_tb=False):
	if sys.exc_info()[0] == AbortRequestedException:
		import threading
		LOG('Abort Requested (%s): Exiting....' % str(threading.currentThread().getName()))
		import thread
		thread.interrupt_main()
		return 'AbortRequested'
	elif sys.exc_info()[0] == StopRequestedException:
		LOG('Stop exception handled')
		return
	
	LOG('ERROR: ' + message)
	short = str(sys.exc_info()[1])
	if hide_tb:
		LOG('ERROR Message: ' + short)
	else:
		import traceback #@Reimport
		traceback.print_exc()
		if getSetting('debug_show_traceback_dialog',False):
			import dialogs #import dialogs here so we can import this module into dialogs
			dialogs.showText('Traceback', traceback.format_exc())
	return short
	
def LOG(message):
	print '%s: %s' % (LOG_PREFIX,message)

def getSetting(key,default=None):
	lock = filelock.FileLock(SETTINGS_PATH, timeout=5, delay=0.1)
	lock.acquire()
	setting = __addon__.getSetting(key)
	lock.release()
	del lock
	return _processSetting(setting,default)

def _processSetting(setting,default):
	if not setting: return default
	if isinstance(default,bool):
		return setting == 'true'
	elif isinstance(default,int):
		return int(float(setting or 0))
	elif isinstance(default,list):
		if setting: return setting.split(':!,!:')
		else: return default
	
	return setting

def setSetting(key,value):
	value = _processSettingForWrite(value)
	lock = filelock.FileLock(SETTINGS_PATH, timeout=5, delay=0.1)
	lock.acquire()
	__addon__.setSetting(key,value)
	lock.release()
	del lock
	
def _processSettingForWrite(value):
	if isinstance(value,list):
		value = ':!,!:'.join(value)
	elif isinstance(value,bool):
		value = value and 'true' or 'false'
	return value
		
def getSettingExternal(key,default=None):
	lock = filelock.FileLock(SETTINGS_PATH, timeout=5, delay=0.1)
	lock.acquire()
	setting = xbmcaddon.Addon(id='script.forum.browser').getSetting(key)
	lock.release()
	del lock
	return _processSetting(setting,default)

def setSettingExternal(key,value):
	value = _processSettingForWrite(value)
	lock = filelock.FileLock(SETTINGS_PATH, timeout=5, delay=0.1)
	lock.acquire()
	xbmcaddon.Addon(id='script.forum.browser').setSetting(key,value)
	lock.release()
	del lock
	
def parseForumBrowserURL(url):
	if not url.startswith('forumbrowser://'):
		return {'forumID':url}
	parts = url.split('://',1)[-1].split('/',4)
	elements = {}
	elements['forumID'] = parts[0]
	if len(parts) > 1: elements['section'] = parts[1]
	if len(parts) > 2: elements['forum'] = parts[2]
	if len(parts) > 3: elements['thread'] = parts[3]
	if len(parts) > 4: elements['post'] = parts[4]
	return elements

def createForumBrowserURL(forumID,section='',forum='',thread='',post=''):
	ret = 'forumbrowser://%s/%s/%s/%s/%s' % (forumID,section,forum,thread,post)
	return ret.strip('/')
	
def getListItemByProperty(clist,prop,value):
	for idx in range(0,clist.size()):
		item = clist.getListItem(idx)
		if item.getProperty(prop) == value: return item
	return None
	
def selectListItemByProperty(clist,prop,value):
	for idx in range(0,clist.size()):
		item = clist.getListItem(idx)
		if item.getProperty(prop) == value:
			clist.selectItem(idx)
			return item
	return None

class XBMCControlConditionalVisiblity:
	def __init__(self):
		self.cache = {}
		
	def __getattr__(self,attr):
		if attr in self.cache: return self.cache[attr]
		def method(control=0,group=None):
			if group:
				return bool(xbmc.getCondVisibility('ControlGroup(%s).%s(%s)' % (group,attr,control)))
			else:
				return bool(xbmc.getCondVisibility('Control.%s(%s)' % (attr,control)))
										
		self.cache[attr] = method
		return method		
		
Control = XBMCControlConditionalVisiblity()

		