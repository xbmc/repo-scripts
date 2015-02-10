import os, sys, time, xbmc, xbmcaddon
from lib import signals
from lib.util import AbortRequestedException

from lib import util
util.LOG_PREFIX = 'FORUMBROWSER-SERVICE'

DEBUG = False
def ERROR(txt):
	if isinstance (txt,str):
		txt = txt.decode("utf-8")
	message = u'FORUMBROWSER-SERVICE: ERROR: %s' % txt
	xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGNOTICE)
	short = str(sys.exc_info()[1])
	import traceback #@Reimport
	traceback.print_exc()
	return short
	
def LOG(txt): pass

FB = None
import default
from default import FORUMS_PATH, FORUMS_STATIC_PATH, CACHE_PATH #@UnusedImport
from default import getForumBrowser, listForumSettings, loadForumSettings, forumsManager, getNotifyList #@UnusedImport
from webviewer import video #@UnresolvedImport

default.LOG = LOG
default.tapatalk.LOG = LOG

ADDONID = util.__addon__.getAddonInfo('id')

def getSetting(key,default=None):
	setting = xbmcaddon.Addon('script.forum.browser').getSetting(key)
	if not setting: return default
	if isinstance(default,bool):
		return setting == 'true'
	elif isinstance(default,int):
		return int(float(setting or '0'))
	elif isinstance(default,list):
		if setting: return setting.split(':!,!:')
		else: return default
	
	return setting

class ForumBrowserService:
	def __init__(self):
		self.stop = False
		self.FB = None
		self.seconds = 20
		self.enabled = False
		self.methods = ('normal','small','full')
		self.notifyMethod = 0
		self.notifyMethodVideo = 0
		self.notifyXbmcDuration = 3
		self.notifyStaleTime = 3600
		self.lastData = {}
		self.loadLastData()
		self.loadConfig(True)
		
	def start(self):
		self.log('STARTED :: Enabled: %s - Start Only: %s - Interval: %ss' % (self.enabled,self.onlyOnStart,self.seconds))
		if not self.enabled: return
		while (not xbmc.abortRequested) and (not self.stop):
			if self.enabled:
				try:
					self.checkForums()
				except:
					ERROR('Failed To Check Forums')
				if self.onlyOnStart:
					self.log('STARTUP ONLY - STOPPING SERVICE')
					break
			ct = 0
			for x in range(0,self.seconds): #@UnusedVariable
				if xbmc.abortRequested or self.stop: break
				xbmc.sleep(1000)
				ct+=1
				if ct > 59: #check config every 60 seconds
					ct = 0
					self.loadConfig()
		self.log('STOPPED')
			
	def log(self,txt):
		if isinstance (txt,str):
			txt = txt.decode("utf-8")
		message = u'FORUMBROWSER-SERVICE: %s' % txt
		xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGNOTICE)
		
	def loadConfig(self,first=False):
		self.seconds = getSetting('notify_interval',20) * 60
		self.enabled = getSetting('notify_enabled',False)
		self.onlyOnStart = getSetting('notify_only_on_start',False)
		self.notifyMethod = self.methods[getSetting('notify_method',0)]
		self.notifyMethodVideo = self.methods[getSetting('notify_method_video',0)]
		self.notifyXbmcDuration = getSetting('notify_xbmc_duration',3) * 1000
		self.notifyStaleTime = getSetting('notify_stale_time',1) * 3600
		if not first and self.onlyOnStart:
			self.log('CHANGED: STARTUP ONLY - STOPPING SERVICE')
			self.stop = True
		
	def notify(self,message='',header='Forum Browser',ntype='all'):
		if video.isPlaying():
			method = self.notifyMethodVideo
		else:
			method = self.notifyMethod
			
		if method == 'normal' and ntype == 'single':
			mtime=self.notifyXbmcDuration
			image=util.__addon__.getAddonInfo('icon')
			xbmc.executebuiltin('Notification(%s,%s,%s,%s)' % (header,message,mtime,image))
		elif method != 'normal' and ntype == 'all':
			if getSetting('FBIsRunning',False):
				signals.sendSignal('NEW_POSTS')
				return
			forumsManager(size=method)
		
	def getUsername(self):
		data = loadForumSettings(self.FB.getForumID())
		if data and data['username']: return data['username']
		return ''
		
	def getPassword(self):
		data = loadForumSettings(self.FB.getForumID())
		if data and data['password']: return data['password']
		return ''
		
	def hasLogin(self):
		return self.getUsername() != '' and self.getPassword() != ''
		
	def setForumBrowser(self,forum):
		self.FB = getForumBrowser(forum,silent=True,no_default=True,log_function=LOG)
		return self.FB
		
	def checkLast(self,forum,ID,count=1):
		forumdata = self.lastData.get(forum)
		if not forumdata: return True
		lastCount = forumdata.get(ID,0) or 0
		return count and (lastCount != count)
	
	def setLastData(self,data):
		self.lastData = data
		
		out = []
		out.append(str(time.time()))
		out.append(str(data))
		f = open(os.path.join(CACHE_PATH,'notifications'),'w')
		f.write('\n'.join(out))
	
	def loadLastData(self):
		dataFile = os.path.join(CACHE_PATH,'notifications')
		if not os.path.exists(dataFile): return
		df = open(dataFile,'r')
		lines = df.read()
		df.close()
		try:
			dtime,data = lines.splitlines()
			if time.time() - float(dtime) > self.notifyStaleTime: return
			import ast
			self.lastData = ast.literal_eval(data)
		except:
			ERROR('Failed To Read Data File')
		
	def checkForums(self):
		self.log('CHECKING FORUMS...')
		data = {}
		anyflag = False
		for forum in getNotifyList():
			fdata = {}
			flag = False
			if not self.setForumBrowser(forum): continue
			if not self.hasLogin(): continue
			self.FB.setLogin(self.getUsername(), self.getPassword(), always=True,rules=loadForumSettings(forum,get_rules=True))
			try:
				pmcounts = self.FB.getPMCounts()
				xbmc.sleep(300)
				subs = self.FB.getSubscriptions()
			except AbortRequestedException:
				self.stop = True
				return
			except:
				ERROR('Failed to get data for forum: %s' % forum)
				fdata = self.lastData.get(forum)
				continue
			fdata['PM'] = pmcounts.get('unread',0) or 0
			pmtotal = pmcounts.get('total',0) or 0
			if fdata['PM']:
				if self.checkLast(forum, 'PM', fdata['PM']): flag = True
			
			log = self.FB.getDisplayName() + ': '
			ct = 0
			unread = 0
			if not subs:
				log += 'ERROR: %s' % subs.error
				self.log(log)
				continue
			
			for f in subs['forums'] or []:
				ID = 'F' + f.get('forumid')
				
				fdata[ID] = f.get('new_post')
				if f.get('new_post'):
					unread += 1
					if self.checkLast(forum, ID): flag = True
				ct += 1
			for t in subs.data:
				ID = 'T' + t.get('threadid')
				fdata[ID] = t.get('new_post')
				if t.get('new_post'):
					unread += 1
					if self.checkLast(forum, ID): flag = True
				ct += 1
			data[forum] = fdata
			log += 'Subs: %s/%s PMs: %s/%s' % (unread,ct,fdata['PM'],pmtotal)
			
			if flag:
				self.notify(log,ntype='single')
				self.log(log + ' - SHOWING NOTICE')
				anyflag = True
			else:
				self.log(log)
			
				
		self.setLastData(data)
		
		if anyflag:
			self.log('SHOWING DIALOG')
			self.notify()
		self.log('CHECKING FORUMS: FINISHED')
		
if __name__ == '__main__':
	ForumBrowserService().start()