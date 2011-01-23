import urllib2, re, os, sys, time, urlparse, htmlentitydefs
import xbmc, xbmcgui, xbmcaddon #@UnresolvedImport
from googletranslate import googleTranslateAPI
import threading
from webviewer import webviewer #@UnresolvedImport

'''
TODO:

Read/Delete PM's in xbmc4xbox.org

'''

__plugin__ = 'Forum Browser'
__author__ = 'ruuk (Rick Phillips)'
__url__ = 'http://code.google.com/p/forumbrowserxbmc/'
__date__ = '01-22-2011'
__version__ = '0.8.2'
__addon__ = xbmcaddon.Addon(id='script.forum.browser')
__language__ = __addon__.getLocalizedString

THEME = 'Default'

ACTION_MOVE_LEFT      = 1
ACTION_MOVE_RIGHT     = 2
ACTION_MOVE_UP        = 3
ACTION_MOVE_DOWN      = 4
ACTION_PAGE_UP        = 5
ACTION_PAGE_DOWN      = 6
ACTION_SELECT_ITEM    = 7
ACTION_HIGHLIGHT_ITEM = 8
ACTION_PARENT_DIR     = 9
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

TITLE_FORMAT = '[COLOR %s][B]%s[/B][/COLOR]'


def ERROR(message):
	errtext = sys.exc_info()[1]
	print 'FORUMBROWSER - %s::%s (%d) - %s' % (message,sys.exc_info()[2].tb_frame.f_code.co_name, sys.exc_info()[2].tb_lineno, errtext)
	return str(errtext)
	
def LOG(message):
	print 'FORUMBROWSER: %s' % message

######################################################################################
# Forum Browser Classes
######################################################################################
class PMLink:
	def __init__(self,match=None):
		self.url = ''
		self.text = ''
		self.pid = ''
		self.tid = ''
		self.fid = ''
		self._isImage = False
		
		if match:
			self.url = match.group('url')
			text = match.group('text')
			self.text = MC.tagFilter.sub('',text).strip()
		self.processURL()
			
	def processURL(self):
		if not self.url: return
		self._isImage = re.search('http://.+?\.(?:jpg|png|gif|bmp)',self.url) and True or False
		if self._isImage: return
		pm = re.search(FB.filters.get('post_link','@`%#@>-'),self.url)
		tm = re.search(FB.filters.get('thread_link','@`%#@>-'),self.url)
		if pm:
			d = pm.groupdict()
			self.pid = d.get('postid','')
			self.tid = d.get('threadid','')
		elif tm:
			d = tm.groupdict()
			self.tid = d.get('threadid','')
			
	def urlShow(self):
		if self.isPost(): return 'Post ID: %s' % self.pid
		elif self.isThread(): return 'Thread ID: %s' % self.tid
		return self.url
		
	def isImage(self):
		return self._isImage
		
	def isPost(self):
		return self.pid and True or False
		
	def isThread(self):
		return self.tid and not self.pid
		
################################################################################
# ForumPost
################################################################################
class ForumPost:
	def __init__(self,pmatch=None,pdict=None):
		self.isPM = False
		if pmatch:
			pdict = pmatch.groupdict()
			self.setVals(pdict)
		elif pdict:
			self.setVals(pdict)
		else:
			self.postId,self.date,self.userId,self.userName,self.avatar,self.status,self.title,self.message,self.signature = ('','','','ERROR','','','ERROR','','')
			self.pid = ''
		self.translated = ''
		self.avatarFinal = ''
		self.tid = ''
		self.fid = ''
			
	def setVals(self,pdict):
		self.setPostID(pdict.get('postid',''))
		self.date = pdict.get('date','')
		self.userId = pdict.get('userid','')
		self.userName = pdict.get('user') or pdict.get('guest') or 'UERROR'
		self.avatar = pdict.get('avatar','')
		self.status = pdict.get('status','')
		self.title = pdict.get('title','')
		self.message = pdict.get('message','')
		self.signature = pdict.get('signature','') or ''
		self.isPM = self.postId.startswith('PM')
			
	def setPostID(self,pid):
		self.postId = pid
		self.pid = pid
		self.isPM = pid.startswith('PM')
	
	def getID(self):
		if self.pid.sartswith('PM'): return self.pid[2:]
		return self.pid
		
	def cleanUserName(self):
		return MC.tagFilter.sub('',self.userName)
		
	def getMessage(self):
		return self.message + self.signature
	
	def messageAsText(self):
		return messageToText(self.getMessage())
		
	def messageAsDisplay(self):
		if self.isPM:
			return MC.parseCodes(self.getMessage())
		else:
			return MC.messageToDisplay(self.getMessage())
		
	def messageAsQuote(self):
		return MC.messageAsQuote(self.message)
		
	def imageURLs(self):
		return MC.imageFilter.findall(self.getMessage(),re.S)
		
	def linkImageURLs(self):
		return re.findall('<a.+?href="(http://.+?\.(?:jpg|png|gif|bmp))".+?</a>',self.message,re.S)
		
	def linkURLs(self):
		return MC.linkFilter.finditer(self.getMessage(),re.S)
		
	def links(self):
		links = []
		for m in self.linkURLs(): links.append(PMLink(m))
		return links
		
	def makeAvatarURL(self):
		base = FB.urls.get('avatar')
		if base and not self.avatar:
			self.avatar = base.replace('!USERID!',self.userId)
		return self.avatar
	
			
################################################################################
# PageData
################################################################################
class PageData:
	def __init__(self,page_match=None,next_match=None,prev_match=None,page_type=''):
		self.next = False
		self.prev = False
		self.page = '1'
		self.totalPages = '1'
		self.pageDisplay = ''
		self.urlMode = 'PAGE'
		self.nextStart = '0'
		self.prevStart = '0'
		self.topic = ''
		self.tid = ''
		self.pageType = page_type
		
		if page_match:
			pdict = page_match.groupdict()
			self.page = pdict.get('page','1')
			self.totalPages = pdict.get('total','1')
			self.pageDisplay = pdict.get('display','')
		if next_match:
			ndict = next_match.groupdict()
			page = ndict.get('page')
			start = ndict.get('start')
			if page:
				self.next = True
				self.urlMode = 'PAGE'
			elif start:
				self.next = True
				self.nextStart = start
				self.urlMode = 'START'
		if prev_match:
			pdict = prev_match.groupdict()
			page = pdict.get('page')
			start = pdict.get('start')
			if page:
				self.prev = True
				self.urlMode = 'PAGE'
			elif start:
				self.prev = True
				self.prevStart = start
				self.urlMode = 'START'
	
	def getPageNumber(self,page):
		if self.urlMode != 'PAGE':
			per_page = FB.formats.get('%s_per_page' % self.pageType)
			if per_page:
				try:
					if int(page) < 0: page = 9999
					page = str((int(page) - 1) * int(per_page))
				except:
					ERROR('CALCULATE START PAGE ERROR - PAGE: %s' % page)
		return page
		
	def setThreadData(self,topic,threadid):
		self.topic = topic
		self.tid = threadid
				
	def getNextPage(self):
		if self.urlMode == 'PAGE':
			try:
				return str(int(self.page) + 1)
			except:
				return '1'
		else:
			return self.nextStart
			
	def getPrevPage(self):
		if self.urlMode == 'PAGE':
			try:
				return str(int(self.page) - 1)
			except:
				return '1'
		else:
			return self.prevStart
				
	def getPageDisplay(self):
		if self.pageDisplay: return self.pageDisplay
		if self.page and self.totalPages:
			return 'Page %s of %s' % (self.page,self.totalPages)

################################################################################
# Action
################################################################################
class Action:
	def __init__(self,action=''):
		self.action = action
		
################################################################################
# PostMessage
################################################################################
class PostMessage(Action):
	def __init__(self,pid='',tid='',fid='',title='',message='',is_pm=False):
		Action.__init__(self,'CHANGE')
		self.pid = pid
		self.tid = tid
		self.fid = fid
		self.title = title
		self.message = message
		self.quote = ''
		self.quser = ''
		self.to = ''
		self.isPM = is_pm
		
	def setQuote(self,user,quote):
		self.quser = MC.tagFilter.sub('',user)
		self.quote = quote
		
	def setMessage(self,title,message):
		self.title = title
		self.message = message
				
######################################################################################
# Forum Browser API
######################################################################################
class ForumBrowser:
	def __init__(self,forum,always_login=False):
		self.forum = forum
		self._url = ''
		self.browser = None
		self.mechanize = None
		self.needsLogin = True
		self.alwaysLogin = always_login
		self.lastHTML = ''
		
		self.reloadForumData(forum)
		
	def resetBrowser(self):
		self.browser = None
		
	def reloadForumData(self,forum):
		self.urls = {}
		self.filters = {}
		self.theme = {}
		self.forms = {}
		self.formats = {}
		self.smilies = {}
		
		self.loadForumData(forum)
		
	def loadForumData(self,forum):
		self.needsLogin = True
		fname = xbmc.translatePath('special://home/addons/script.forum.browser/forums/%s' % forum)
		if not os.path.exists(fname): return False
		f = open(fname,'r')
		data = f.read()
		f.close()
		for line in data.splitlines():
			line = line.strip()
			if not line: continue
			if line.startswith('#'): continue
			dtype , rest = line.split(':',1)
			if dtype == 'import':
				self.loadForumData(rest)
			elif dtype == 'url':
				key,url = rest.split('=',1)
				if url.startswith('=='):
					dup = url.split('=')[-1]
					url = self.urls[dup]
				self.urls[key] = url
			elif dtype == 'filter':
				key,regex = rest.split('=',1)
				if regex.startswith('=='):
					dup = regex.split('=')[-1]
					regex = self.filters[dup]
				self.filters[key] = regex
			elif dtype == 'theme':
				key,color = rest.split('=',1)
				if color.startswith('=='):
					dup = color.split('=')[-1]
					color = self.theme[dup]
				self.theme[key] = color
			elif dtype == 'form':
				key,data = rest.split('=',1)
				if data.startswith('=='):
					dup = data.split('=')[-1]
					data = self.forms[dup]
				self.forms[key] = data
			elif dtype == 'format':
				key,data = rest.split('=',1)
				if data.startswith('=='):
					dup = data.split('=')[-1]
					data = self.formats[dup]
				self.formats[key] = data
			elif dtype == 'smilies':
				key,data = rest.split('=',1)
				if data.startswith('=='):
					dup = data.split('=')[-1]
					data = self.smilies[dup]
				self.smilies[key] = data
				
		self._url = self.urls.get('base','')
		self.forum = forum
		return True
			
		
	def setLogin(self,user,password,always=False):
		self.user = user
		self.password = password
		self.alwaysLogin = always
			
	def login(self):
		LOG('LOGGING IN')
		if not self.mechanize:
			from webviewer import mechanize #@UnresolvedImport
			self.mechanize = mechanize
		if not self.browser: self.browser = self.mechanize.Browser()
		response = self.browser.open(self.getURL('login'))
		html = response.read()
		try:
			self.browser.select_form(predicate=self.predicateLogin)
		except:
			ERROR('LOGIN FORM SELECT ERROR')
			LOG('TRYING ALTERNATE METHOD')
			form = self.getForm(html,self.forms.get('login_action'))
			if form:
				self.browser.form = form
			else:
				LOG('FAILED')
				return False
		self.browser[self.forms['login_user']] = self.user
		self.browser[self.forms['login_pass']] = self.password
		response = self.browser.submit()
		html = response.read()
		if not self.forms.get('login_action','@%+#') in html: return True
		LOG('FAILED TO LOGIN')
		return False
		
	def checkLogin(self,callback=None):
		if not callback: callback = self.fakeCallback
		if not self.browser or self.needsLogin:
			self.needsLogin = False
			if not callback(5,__language__(30100)): return False
			if not self.login():
				return False
		return True
		
	def browserReadURL(self,url,callback):
		if not callback(30,__language__(30101)): return ''
		response = self.browser.open(url)
		if not callback(60,__language__(30102)): return ''
		return response.read()
		
	def readURL(self,url,callback=None,force_login=False,is_html=True):
		if not url:
			LOG('ERROR - EMPTY URL IN readURL()')
			return ''
		if not callback: callback = self.fakeCallback
		if self.formats.get('login_required') or force_login or (self.alwaysLogin and self.password):
			if not self.checkLogin(callback=callback): return ''
			data = self.browserReadURL(url,callback)
			if self.forms.get('login_action','@%+#') in data:
				self.login()
				data = self.browserReadURL(url,callback)
		else:
			if not callback(5,__language__(30101)): return ''
			req = urllib2.urlopen(url)
			if not callback(50,__language__(30102)): return ''
			data = req.read()
			req.close()
		if is_html: self.lastHTML = data
		return data
		
	def makeURL(self,phppart):
		if not phppart: return ''
		if phppart.startswith('http://'):
			url = phppart
		else:
			url = self._url + phppart
		return url.replace('&amp;','&').replace('/./','/')
		
	def getPMCounts(self,html=''):
		if not html: html = MC.lineFilter.sub('',self.lastHTML)
		pm_counts = None
		ct = 0
		while not pm_counts:
			ct += 1
			if self.filters.get('pm_counts%s' % ct):
				pm_counts = re.search(self.filters.get('pm_counts%s' % ct),html)
			else:
				break
		#print html
		if pm_counts: return pm_counts.groupdict()
		return None
		
	def getForums(self,callback=None,donecallback=None):
		if not callback: callback = self.fakeCallback
		html = self.readURL(self.getURL('forums'),callback=callback)
		#open('/home/ruuk/test3.html','w').write(html)
		if not html or not callback(80,__language__(30103)):
			if donecallback: donecallback(None,None,None)
			return (None,None,None)
		html = MC.lineFilter.sub('',html)
		forums = re.finditer(self.filters['forums'],html)
		logo = ''
		if self.filters.get('logo'): logo = re.findall(self.filters['logo'],html)[0]
		pm_counts = self.getPMCounts(html)
		if logo: logo = self.makeURL(logo)
		callback(100,__language__(30052))
		if donecallback: donecallback(forums,logo,pm_counts)
		else: return forums, logo, pm_counts
		
	def getThreads(self,forumid,page='',callback=None,donecallback=None):
		if not callback: callback = self.fakeCallback
		url = self.getPageUrl(page,'threads',fid=forumid)
		html = self.readURL(url,callback=callback)
		if not html or not callback(80,__language__(30103)):
			if donecallback: donecallback(None,None)
			return (None,None)
		if self.filters.get('threads_start_after'): html = html.split(self.filters.get('threads_start_after'),1)[-1]
		threads = re.finditer(self.filters['threads'],MC.lineFilter.sub('',html))
		callback(100,__language__(30052))
		pd = self.getPageData(html,page,page_type='threads')
		if donecallback: donecallback(threads,pd)
		else: return threads,pd
		
	def getReplies(self,threadid,forumid,page='',lastid='',pid='',callback=None,donecallback=None):
		if not callback: callback = self.fakeCallback
		url = self.getPageUrl(page,'replies',tid=threadid,fid=forumid,lastid=lastid,pid=pid)
		html = self.readURL(url,callback=callback)
		if not html or not callback(80,__language__(30103)):
			if donecallback:
				donecallback(None,None)
				return
			else:
				return (None,None)
		html = MC.lineFilter.sub('',html)
		replies = re.findall(self.filters['replies'],html)
		topic = re.search(self.filters.get('thread_topic','%#@+%#@'),html)
		if not threadid:
			threadid = re.search(self.filters.get('thread_id','%#@+%#@'),html)
			threadid = threadid and threadid.group(1) or ''
		topic = topic and topic.group(1) or ''
		sreplies = []
		for r in replies:
			try:
				post = ForumPost(re.search(self.filters['post'],MC.lineFilter.sub('',r)))
				sreplies.append(post)
			except:
				post = ForumPost()
				sreplies.append(post)
		pd = self.getPageData(html,page,page_type='replies')
		pd.setThreadData(topic,threadid)
		callback(100,__language__(30052))
		
		if donecallback: donecallback(sreplies, pd)
		else: return sreplies, pd
		
	def hasPM(self):
		return bool(self.urls.get('private_messages_xml') or self.urls.get('private_messages_csv'))
	
	def getPrivateMessages(self,callback=None,donecallback=None):
		if not callback: callback = self.fakeCallback
		#if not self.checkLogin(callback=callback): return None, None
		pms = None
		if self.urls.get('private_messages_xml'):
			xml = self.readURL(self.getURL('private_messages_xml'),callback=callback,force_login=True,is_html=False)
			if not xml or not callback(80,__language__(30103)):
				if donecallback:
					donecallback(None,None)
					return
				else:
					return (None,None)
			folders = re.search(self.filters.get('pm_xml_folders'),xml,re.S)
			if not folders:
				if donecallback:
					donecallback([],None)
					return
				else:
					return (None,None)
			messages = re.finditer(self.filters.get('pm_xml_messages'),folders.group('inbox'),re.S)
			pms = []
			for m in messages:
				p = ForumPost(m)
				p.setPostID('PM%s' % len(pms))
				p.message = re.sub('[\t\r]','',p.message)
				p.makeAvatarURL()
				pms.append(p)
		elif self.urls.get('private_messages_csv'):
			csvstring = self.readURL(self.getURL('private_messages_csv'),callback=callback,force_login=True,is_html=False)
			if not csvstring or not callback(80,__language__(30103)):
				if donecallback:
					donecallback(None,None)
					return
				else:
					return (None,None)
			columns = self.formats.get('pm_csv_columns').split(',')
			import csv
			cdata = csv.DictReader(csvstring.splitlines()[1:],fieldnames=columns)
			pms = []
			folder = self.formats.get('pm_csv_folder')
			for d in cdata:
				if folder and folder == d.get('folder'):
					p = ForumPost(pdict=d)
					p.setPostID('PM%s' % len(pms))
					pms.append(p)
		callback(100,__language__(30052))
		
		if donecallback: donecallback(pms,None)
		else: return pms, None
	
	def hasSubscriptions(self):
		return bool(self.urls.get('subscriptions'))
	
	def getSubscriptions(self,page='',callback=None,donecallback=None):
		if not callback: callback = self.fakeCallback
		#if not self.checkLogin(callback=callback): return None
		url = self.getPageUrl(page,'subscriptions')
		html = self.readURL(url,callback=callback,force_login=True)
		if not html or not callback(80,__language__(30103)):
			if donecallback:
				donecallback(None,None)
				return
			else:
				return (None,None)
		threads = re.finditer(self.filters['subscriptions'],MC.lineFilter.sub('',html))
		callback(100,__language__(30052))
		pd = self.getPageData(html,page,page_type='threads')
		if donecallback: donecallback(threads,pd)
		else: return threads,pd
		
	def getPageData(self,html,page,page_type=''):
		next_page = re.search(self.filters['next'],html,re.S)
		prev_page= None
		if page != '1':
			prev_page = re.search(self.filters['prev'],html,re.S)
		page_disp = re.search(self.filters['page'],html)
		return PageData(page_disp,next_page,prev_page,page_type=page_type)
		
	def getPageUrl(self,page,sub,pid='',tid='',fid='',lastid=''):
		if sub == 'replies' and page and int(page) < 0:
			gnp = self.urls.get('gotonewpost','')
			page = self.URLSubs(gnp,pid=lastid)
		else:
			if page:
				try:
					if int(page) < 0: page = '9999'
				except:
					ERROR('CALCULATE START PAGE ERROR - PAGE: %s' % page)
				page = '&%s=%s' % (self.urls.get('page_arg',''),page)
		sub = self.URLSubs(self.urls[sub],pid=pid,tid=tid,fid=fid)
		return self._url + sub + page
		
	def getURL(self,name):
		return self._url + self.urls.get(name,'')
		
	def predicateLogin(self,formobj):
		return self.forms.get('login_action','@%+#') in formobj.action
		
	def getForm(self,html,action,name=None):
		if not action: return None
		try:
			forms = self.mechanize.ParseString(''.join(re.findall('<form\saction="%s.+?</form>' % re.escape(action),html,re.S)),self._url)
			if name:
				for f in forms:
					if f.name == name:
						return f
			for f in forms:
				if action in f.action:
					return f
			LOG('NO FORM 2')
		except:
			ERROR('PARSE ERROR')
			
	def URLSubs(self,url,pid='',tid='',fid='',post=None):
		if post:
			url = url.replace('!POSTID!',post.pid).replace('!THREADID!',post.tid).replace('!FORUMID!',post.fid)
		else:
			url = url.replace('!POSTID!',pid).replace('!THREADID!',tid).replace('!FORUMID!',fid)
		#removes empty vars
		return re.sub('(?:\w+=&)|(?:\w+=$)','',url)
		
	def postURL(self,post):
		return self.URLSubs(self.getURL('newpost'),post=post)
	
	def predicatePost(self,formobj):
		return self.forms.get('post_action','@%+#') in formobj.action
		
	def fakeCallback(self,pct,message=''): return True
	
	def post(self,post,callback=None):
		if not callback: callback = self.fakeCallback
		if not self.checkLogin(callback=callback): return False
		url = self.postURL(post)
		res = self.browser.open(url)
		html = res.read()
		if self.forms.get('login_action','@%+#') in html:
			callback(5,__language__(30100))
			if not self.login(): return False
			res = self.browser.open(url)
			html = res.read()
		callback(40,__language__(30105))
		selected = False
		try:
			if self.forms.get('post_name'):
				self.browser.select_form(self.forms.get('post_name'))
				LOG('FORM SELECTED BY NAME')
			else:
				self.browser.select_form(predicate=self.predicatePost)
				LOG('FORM SELECTED BY ACTION')
			selected = True
		except:
			ERROR('NO FORM 1')
			
		if not selected:
			form = self.getForm(html,self.forms.get('post_action',''),self.forms.get('post_name',''))
			if form:
				self.browser.form = form
			else:
				return False
		try:
			if post.title: self.browser[self.forms['post_title']] = post.title
			self.browser[self.forms['post_message']] = post.message
			self.setControls('post_controls%s')
			#print self.browser.form
			wait = int(self.forms.get('post_submit_wait',0))
			if wait: callback(60,__language__(30107) % wait)
			time.sleep(wait) #or this will fail on some forums. I went round and round to find this out.
			callback(80,__language__(30106))
			res = self.browser.submit(name=self.forms.get('post_submit_name'),label=self.forms.get('post_submit_value'))
			callback(100,__language__(30052))
		except:
			ERROR('FORM ERROR')
			return False
			
		return True
		
	def doPrivateMessage(self,to,title,message,callback=None):
		self.doForm(	self.urls.get('pm_new_message'),
						self.forms.get('pm_name'),
						self.forms.get('pm_action'),
						{self.forms.get('pm_recipient'):to,self.forms.get('pm_title'):title,self.forms.get('pm_message'):message},
						callback=callback)
			
	def deletePrivateMessageViaIndex(self,pmidx,callback=None):
		html = self.readURL(self.urls.get('private_messages_inbox'),callback=callback,force_login=True)
		if not html: return
		pmid_list = re.findall(self.filters.get('pm_pmid_list'),html,re.S)
		try:
			pmid_list.reverse()
			pmid = pmid_list[int(pmidx)]
		except:
			ERROR('DELETE PM VIA INDEX ERROR')
			return
			
		self.doForm(	self.urls.get('private_messages_delete').replace('!PMID!',pmid),
						self.forms.get('pm_delete_name'),
						self.forms.get('pm_delete_action'),
						controls='pm_delete_control%s',
						callback=callback)
						
	def doForm(self,url,form_name=None,action_match=None,field_dict={},controls=None,submit_name=None,submit_value=None,wait='1',callback=None):
		if not callback: callback = self.fakeCallback
		if not self.checkLogin(callback=callback): return False
		res = self.browser.open(url)
		html = res.read()
		if self.forms.get('login_action','@%+#') in html:
			callback(5,__language__(30100))
			if not self.login(): return False
			res = self.browser.open(url)
			html = res.read()
		callback(40,__language__(30105))
		selected = False
		try:
			if form_name:
				self.browser.select_form(form_name)
				LOG('FORM SELECTED BY NAME')
			else:
				predicate = lambda formobj: action_match in formobj.action
				self.browser.select_form(predicate=predicate)
				LOG('FORM SELECTED BY ACTION')
			selected = True
		except:
			ERROR('NO FORM 1')
			
		if not selected:
			form = self.getForm(html,action_match,form_name)
			if form:
				self.browser.form = form
			else:
				return False
		try:
			for k in field_dict.keys():
				if field_dict[k]: self.browser[k] = field_dict[k]
			self.setControls(controls)
			wait = int(wait)
			if wait: callback(60,__language__(30107) % wait)
			time.sleep(wait) #or this will fail on some forums. I went round and round to find this out.
			callback(80,__language__(30106))
			res = self.browser.submit(name=submit_name,label=submit_value)
			callback(100,__language__(30052))
		except:
			ERROR('FORM ERROR')
			return False
			
		return True
		
	def predicateDeletePost(self,formobj):
		if self.forms.get('delete_action','@%+#') in formobj.action: return True
		return False
		
	def deletePost(self,post):
		if not self.checkLogin(): return False
		res = self.browser.open(self.URLSubs(self.getURL('deletepost'),post=post))
		html = res.read()
		
		if self.forms.get('login_action','@%+#') in html:
			if not self.login(): return False
			res = self.browser.open(self.URLSubs(self.getURL('deletepost'),post=post))
			html = res.read()
			
		selected = False
		#print html
		try:
			self.browser.select_form(predicate=self.predicateDeletePost)
			selected = True
		except:
			ERROR('DELETE NO FORM 1')
			
		if not selected:
			form = self.getForm(html,self.forms.get('delete_action',''),self.forms.get('delete_name',''))
			if form:
				self.browser.form = form
			else:
				LOG('DELETE NO FORM 2')
				return False
		
		try:
			#self.browser.find_control(name="deletepost").value = ["delete"]
			self.setControls('delete_control%s')
			#self.browser["reason"] = reason[:50]
			self.browser.submit()
		except:
			ERROR('DELETE NO CONTROL')
			return False
			
		return True
		#<a href="editpost.php?do=editpost&amp;p=631488" name="vB::QuickEdit::631488">
	
	def setControls(self,control_string):
		if not control_string: return
		x=1
		#limit to 50 because while loops scare me :)
		while x<50:
			control = self.forms.get(control_string % x)
			if not control: return
			ctype,rest = control.split(':',1)
			ftype,rest = rest.split('.',1)
			name,value = rest.split('=')
			control = self.browser.find_control(**{ftype:name})
			if ctype == 'radio':
				control.value = [value]
			elif ctype == 'checkbox':
				control.items[0].selected = value == 'True'
			x+=1
			
	def canDelete(self,user):
		return self.user == user and self.urls.get('deletepost')

######################################################################################
# Base Window Classes
######################################################################################
class StoppableThread(threading.Thread):
	def __init__(self,group=None, target=None, name=None, args=(), kwargs={}):
		self._stop = threading.Event()
		threading.Thread.__init__(self,group=group, target=target, name=name, args=args, kwargs=kwargs)
		
	def stop(self):
		self._stop.set()
		
	def stopped(self):
		return self._stop.isSet()
		
class StoppableCallbackThread(StoppableThread):
	def __init__(self,target=None, name=None):
		self._target = target
		self._stop = threading.Event()
		self._finishedHelper = None
		self._finishedCallback = None
		self._progressHelper = None
		self._progressCallback = None
		StoppableThread.__init__(self,name=name)
		
	def setArgs(self,*args,**kwargs):
		self.args = args
		self.kwargs = kwargs
		
	def run(self):
		self._target(*self.args,**self.kwargs)
		
	def setFinishedCallback(self,helper,callback):
		self._finishedHelper = helper
		self._finishedCallback = callback
	
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
				self._function(*self._functionArgs,**self._functionKwargs)
				self._resetFunction()
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
		for t in threading.enumerate():
			if t != threading.currentThread(): t.join()
			
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
		
	def getThread(self,function,finishedCallback=None,progressCallback=None):
		if self._currentThread: self._currentThread.stop()
		if not progressCallback: progressCallback = self._progressCommand
		t = StoppableCallbackThread(target=function)
		t.setFinishedCallback(self.endInMain,finishedCallback)
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
		
class BaseWindow(xbmcgui.WindowXMLDialog,ThreadWindow):
	def __init__( self, *args, **kwargs ):
		self._progMessageSave = ''
		ThreadWindow.__init__(self)
		xbmcgui.WindowXMLDialog.__init__( self, *args, **kwargs )
	
	def onClick( self, controlID ):
		return False
			
	def onAction(self,action):
		#print action.getId()
		if action == ACTION_PARENT_DIR:
			action = ACTION_PREVIOUS_MENU
		if ThreadWindow.onAction(self,action): return
		if action == ACTION_PREVIOUS_MENU: self.close()
		xbmcgui.WindowXMLDialog.onAction(self,action)
	
	def startProgress(self):
		self._title_fg = FB.theme.get('title_fg','FF000000')
		self._progMessageSave = self.getControl(104).getLabel()
		self.getControl(310).setVisible(True)
	
	def setProgress(self,pct,message=''):
		w = int((pct/100.0)*self.getControl(300).getWidth())
		self.getControl(310).setWidth(w)
		self.getControl(104).setLabel(TITLE_FORMAT % (self._title_fg,message))
		return True
		
	def endProgress(self):
		self.getControl(310).setVisible(False)
		self.getControl(104).setLabel(self._progMessageSave)
	
class PageWindow(BaseWindow):
	def __init__( self, *args, **kwargs ):
		self.next = ''
		self.prev = ''
		self.pageData = PageData()
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
		if options[idx] == self._firstPage: self.gotoPage(1)
		elif options[idx] == self._lastPage: self.gotoPage(9999)
		elif options[idx] == self._newestPage: self.gotoPage(-1)
		else: self.askPageNumber()
		
	def askPageNumber(self):
		page = xbmcgui.Dialog().numeric(0,__language__(30116))
		try: int(page)
		except: return
		self.gotoPage(self.pageData.getPageNumber(page))
		
	def setupPage(self,pageData):
		if pageData: self.pageData = pageData
		self.getControl(200).setVisible(self.pageData.prev)
		self.getControl(202).setVisible(self.pageData.next)
		self.getControl(105).setLabel(TITLE_FORMAT % (FB.theme['title_fg'],self.pageData.getPageDisplay()))
		
	def gotoPage(self,page): pass

######################################################################################
# Image Dialog
######################################################################################
class ImagesDialog(BaseWindow):
	def __init__( self, *args, **kwargs ):
		self.images = kwargs.get('images')
		self.index = 0
		BaseWindow.__init__( self, *args, **kwargs )
	
	def onInit(self):
		self.setTheme()
		self.getControl(200).setEnabled(len(self.images) > 1)
		self.getControl(202).setEnabled(len(self.images) > 1)
		self.showImage()
		
	def setTheme(self):
		xbmcgui.lock()
		try:
			self.getControl(101).setColorDiffuse(FB.theme.get('window_bg','FF222222')) #panel bg
		except:
			xbmcgui.unlock()
			raise
		xbmcgui.unlock()

	def onFocus( self, controlId ):
		self.controlId = controlId
		
	def showImage(self):
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
		if action == ACTION_PARENT_DIR:
			action = ACTION_PREVIOUS_MENU
		elif action == ACTION_NEXT_ITEM:
			self.nextImage()
		elif action == ACTION_PREV_ITEM:
			self.prevImage()
		BaseWindow.onAction(self,action)
		
######################################################################################
# Post Dialog
######################################################################################
class PostDialog(BaseWindow):
	def __init__( self, *args, **kwargs ):
		self.post = kwargs.get('post')
		self.title = self.post.title
		self.posted = False
		self.display_base = '[COLOR '+FB.theme.get('desc_fg',FB.theme.get('title_fg','FF000000'))+']%s[/COLOR]\n \n'
		BaseWindow.__init__( self, *args, **kwargs )
	
	def onInit(self):
		self.getControl(122).setText(' ') #to remove scrollbar
		if self.post.quote:
			format = FB.formats.get('quote')
			xbmcgui.lock()
			try:
				pid = self.post.pid
				#This won't work with other formats, need to do this better TODO
				if not pid or pid.startswith('PM'): format = format.replace(';!POSTID!','')
				for line in format.replace('!USER!',self.post.quser).replace('!POSTID!',self.post.pid).replace('!QUOTE!',self.post.quote).split('\n'):
					self.addQuote(line)
				self.updatePreview()
			except:
				xbmcgui.unlock()
			else:
				xbmcgui.unlock()
		self.setTheme()
	
	def setTheme(self):
		xbmcgui.lock()
		try:
			title_bg = FB.theme.get('title_bg','FFFFFFFF')
			title_fg = FB.theme.get('title_fg','FF000000')
			self.getControl(251).setColorDiffuse(title_bg) #title bg
			self.getControl(300).setColorDiffuse(title_bg) #sep
			self.getControl(301).setColorDiffuse(title_bg) #sep
			self.getControl(302).setColorDiffuse(title_bg) #sep
			self.getControl(101).setColorDiffuse(FB.theme.get('window_bg','FF222222')) #panel bg
			self.getControl(351).setColorDiffuse(FB.theme.get('desc_bg',title_bg)) #desc bg
			self.getControl(103).setLabel(TITLE_FORMAT % (title_fg,'Post Reply'))
			self.getControl(104).setLabel(TITLE_FORMAT % (title_fg,__language__(30120)))
		except:
			xbmcgui.unlock()
			raise
		xbmcgui.unlock()
		
	def onClick( self, controlID ):
		if BaseWindow.onClick(self, controlID): return
		if controlID == 202:
			self.postReply()
		elif controlID == 104:
			self.setTitle()

	def onFocus( self, controlId ):
		self.controlId = controlId
		
	def onAction(self,action):
		BaseWindow.onAction(self,action)
		
	
	def setTitle(self):
		keyboard = xbmc.Keyboard(self.title,__language__(30125))
		keyboard.doModal()
		if not keyboard.isConfirmed(): return
		title = keyboard.getText()
		title_fg = FB.theme.get('title_fg','FF000000')
		self.getControl(104).setLabel(TITLE_FORMAT % (title_fg,title))
		self.title = title
	
	def dialogCallback(self,pct,message):
		self.prog.update(pct,message)
		return True
		
	def postReply(self):
		message = self.getOutput()
		self.prog = xbmcgui.DialogProgress()
		self.prog.create(__language__(30126),__language__(30127))
		self.prog.update(0)
		self.post.setMessage(self.title,message)
		try:
			if not self.post.isPM:
				FB.post(self.post,callback=self.dialogCallback)
			else:
				FB.doPrivateMessage(self.post.to,self.title,message,callback=self.dialogCallback)
		except:
			self.prog.close()
			raise
		self.prog.close()
		self.posted = True
		self.close()
		
	def parseCodes(self,text):
		return MC.parseCodes(text)
	
	def updatePreview(self):
		disp = self.display_base % self.getOutput()
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
		elif action == ACTION_PARENT_DIR:
			action = ACTION_PREVIOUS_MENU
		PostDialog.onAction(self,action)
		
	def doMenu(self):
		dialog = xbmcgui.Dialog()
		idx = dialog.select(__language__(30051),[__language__(30128),__language__(30122)])
		if idx == 0: self.addLineSingle(before=True)
		elif idx == 1: self.deleteLine()
		
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
					.replace('[/B]','[/B ]')\
					.replace('[/I]','[/I ]')\
					.replace('[/B]','[/B ]')\
					.replace('[/COLOR]','[/COLOR ]')
		
	def addLineSingle(self,before=False,update=True):
		keyboard = xbmc.Keyboard('',__language__(30123))
		keyboard.doModal()
		if not keyboard.isConfirmed(): return False
		line = keyboard.getText()
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
	
	def editLine(self):
		item = self.getControl(120).getSelectedItem()
		if not item: return
		keyboard = xbmc.Keyboard(item.getProperty('text'),__language__(30124))
		keyboard.doModal()
		if not keyboard.isConfirmed(): return
		line = keyboard.getText()
		item.setProperty('text',line)
		item.setLabel(self.displayLine(line))
		self.updatePreview()
		#re.sub(q,'[QUOTE=\g<user>;\g<postid>]\g<quote>[/QUOTE]',MC.lineFilter.sub('',test3))

class TextPostDialog(PostDialog):
	def __init__( self, *args, **kwargs ):
		PostDialog.__init__( self, *args, **kwargs )
		self.buffer = ''
		self.cursor = '[COLOR red]|[/COLOR]'
		#self.cursor = '|'
		self.cursorPos = 0
		self.charsPerLine = 100
		self.linesPerPage = 12
		self.lastViewStart = 0
		self.posHint = -1
		self.editButton = None
		import string
		self.transTable = string.maketrans("`1234567890-=abcdefghijklmnopqrstuvwxyz[]\\;',./", "~!@#$%^&*()_+ABCDEFGHIJKLMNOPQRSTUVWXYZ{}|:\"<>?")
	
	def onInit(self):
		PostDialog.onInit(self)
		self.editButton = self.getControl(200)
		self.cursorPos = len(self.buffer)
		self.showBuffer()
	
	def addQuote(self,quote):
		self.buffer += quote + '\n'
		
	def getOutput(self):
		return self.buffer
	
	def onClick(self,controlID):
		PostDialog.onClick(self,controlID)
		
	def onAction(self,action):
		if self.checkKeys(action): return
		if action == ACTION_CONTEXT_MENU:
			self.doMenu()
			return
		PostDialog.onAction(self,action)
		
	def doMenu(self):
		dialog = xbmcgui.Dialog()
		idx = dialog.select(__language__(30051),[__language__(30120),__language__(3008)])
		if idx == 0: self.setTitle()
		elif idx == 1: self.postReply()
		
	def checkKeys(self,action):
		#if not self.editButton.isSelected(): return False
		aid = action.getId()
		bc = action.getButtonCode()
		#print aid,bc
		try:
			shift = False
			if bc & 0x00020000:
				#de-shift
				bc = bc ^ 0x00020000
				shift = True
			if not bc: bc = aid
			char = None
			if aid == ACTION_PARENT_DIR:
				self.backspace()
				return True
			#elif aid == 18:
			#	print 'test'
			#	char = '\\'
			#	xbmc.executebuiltin('Action(fullscreen)')
			elif aid == 122:
				if bc == 61517:
					char = 'm'
				else:
					xbmc.executebuiltin('Action(previousmenu)')
					char = 's'
			#elif aid == 88:
			elif bc == 61627:
				char = '='
			#	else:
			#		char = '+'
			elif bc > 61476 and bc < 61481:
				self.moveCursor(bc)
				return True
			elif bc == 61453:
				char = '\n'
			elif bc == 61472:
				char = ' '
			elif bc == 61475:
				self.moveToEnd()
			elif bc == 61476:
				self.moveToStart()
			elif bc > 61504 and bc < 61531:
				#a-z
				char = chr(bc-61408)
			elif bc > 61535 and bc < 61546:
				#0-9
				char = chr(bc-61488)
			elif bc == 61626:
				char = ';'
			elif bc == 61632:
				char = '`'
			elif bc == 61678:
				char = "'"
			elif bc > 61626 and bc < 61678:
				char = chr(bc-61584)
			elif bc > 61726 and bc < 61823:
				char = chr(bc-61696)
			elif bc == 61473:
				#pgup
				self.pageUp()
			elif bc == 61474:
				#pgdn
				self.pageDown()
			elif bc == 127009:
				#ctrl-pgup
				xbmc.executebuiltin('PageUp(123)')
			elif bc == 127010:
				#ctrl-pgdn
				xbmc.executebuiltin('PageDown(123)')
			elif bc == 127138:
				char = '\\'
			
			if char:
				if shift: char = char.translate(self.transTable)
				self.addChar(char)
				self.posHint = -1
				return True
		except:
			raise
			return False
			
		return False
		
	def pageUp(self):
		for x in range(0,self.linesPerPage-1): #@UnusedVariable
			self.lastViewStart -= 1
			if self.lastViewStart < 0:
				self.lastViewStart = 0
				break
			self.moveCursor(61478)
		
	def pageDown(self):
		cmax = len(self.getWrapped()) - self.linesPerPage
		for x in range(0,self.linesPerPage-1): #@UnusedVariable
			self.lastViewStart += 1
			if self.lastViewStart > cmax:
				self.lastViewStart = cmax
				break
			self.moveCursor(61480)
	
	def moveCursor(self,bc):
		if bc == 61477:
			#left
			self.posHint = -1
			self.cursorPos -= 1
			if self.cursorPos < 0: self.cursorPos = 0
		elif bc == 61478:
			#up
			oldPos = self.cursorPos
			idx,pos,clen = self.getLinePos() #@UnusedVariable
			relPos = pos % self.charsPerLine
			if self.posHint < 0: self.posHint = relPos
			posOff = self.posHint - relPos
			if pos > self.charsPerLine-1:
				self.cursorPos -= (self.charsPerLine - posOff)
				if self.cursorPos < 0: self.cursorPos = 0
			else:
				line = self.getPreviousLine()
				llen = len(line)
				tail = llen % self.charsPerLine
				self.cursorPos -= (pos + 1)
				if tail > self.posHint: self.cursorPos -= (tail - self.posHint)
			#if self.cursorPos == -1 and line: self.cursorPos = 0
			if self.cursorPos < 0: self.cursorPos = oldPos
		elif bc == 61479:
			#right
			self.posHint = -1
			self.cursorPos += 1
			if self.cursorPos > len(self.buffer): self.cursorPos = len(self.buffer)
		elif bc == 61480:
			#down
			eol = self.buffer.find('\n',self.cursorPos)
			sol = self.buffer.rfind('\n',0,self.cursorPos)
			#if sol < 0: sol = 0
			if eol < 0:
				eol = len(self.buffer)
				if eol - sol < self.charsPerLine: return
			lpos = self.cursorPos - sol
			relPos = lpos % self.charsPerLine
			if self.posHint < 0: self.posHint = relPos - 1
			posOff = (self.posHint - relPos) + 1
			llen = eol - sol
			#print '%s %s %s' % (sol,lpos,eol)
			if lpos + self.charsPerLine < llen:
				#print 'one'
				self.cursorPos += self.charsPerLine + posOff
			elif lpos != eol and llen > self.charsPerLine and llen % self.charsPerLine and lpos + self.charsPerLine < llen + (self.charsPerLine - (llen % self.charsPerLine)):
				#print 'two'
				self.cursorPos = eol
			else:
				next_eol = self.buffer.find('\n',eol+1)
				if next_eol < 0: next_eol = len(self.buffer)
				off = (lpos % self.charsPerLine)
				newPos = eol + off + posOff
				#print '%s %s' % (newPos,next_eol)
				#if llen > self.charsPerLine: newPos += 1
				if newPos > next_eol:
					if newPos >= len(self.buffer): return
					self.cursorPos = next_eol
				else:
					self.cursorPos = newPos
			if self.cursorPos > len(self.buffer): self.cursorPos = oldPos
		self.showBuffer(upPrev=False)
	
	def moveToEnd(self):
		self.posHint = -1
		eol = self.buffer.find('\n',self.cursorPos)
		if eol < 0:
			self.cursorPos = len(self.buffer)
		else:
			self.cursorPos = eol
		self.showBuffer()
		
	def moveToStart(self):
		self.posHint = -1
		sol = self.buffer.rfind('\n',0,self.cursorPos) + 1
		if sol:
			self.cursorPos = sol
		else:
			self.cursorPos = 0
		self.showBuffer()
		
	def getPreviousLine(self):
		lines = self.buffer.split('\n')
		ct=0
		lastline = ''
		for line in lines:
			ct += len(line) + 1
			if self.cursorPos < ct:
				return lastline
			lastline = line
			
	def getLinePos(self):
		lines = self.buffer.split('\n')
		ct=0
		lastct=0
		idx=0
		for line in lines:
			ct += len(line) + 1
			if self.cursorPos < ct:
				return (idx,self.cursorPos - lastct,len(line))
			lastct = ct
			idx += 1
		return (idx-1,len(line),len(line))
	
	def backspace(self):
		self.buffer = self.buffer[0:self.cursorPos-1] + self.buffer[self.cursorPos:]
		self.cursorPos -= 1
		self.showBuffer()
		
	def addChar(self,char):
		self.buffer = self.buffer[0:self.cursorPos] + char + self.buffer[self.cursorPos:]
		self.cursorPos += 1
		self.showBuffer()
				
	def showBuffer(self,upPrev=True):
		wrapped = self.getWrapped()
		cursor_idx = 0
		for w in wrapped:
			if '\r' in w: break
			cursor_idx += 1
		if cursor_idx < self.lastViewStart:
			self.lastViewStart = cursor_idx
		elif cursor_idx >= self.lastViewStart + self.linesPerPage:
			self.lastViewStart = (cursor_idx - self.linesPerPage) + 1
		show = wrapped[self.lastViewStart:self.lastViewStart + self.linesPerPage]
		self.getControl(120).setText('\n'.join(show).replace('\r',self.cursor))
		if upPrev: self.updatePreview()
		
	def getWrapped(self):
		buffer = self.buffer[0:self.cursorPos]+'\r'+self.buffer[self.cursorPos:]
		lines = buffer.split('\n')
		wrapped = []
		for line in lines:
			wrapped += self.splitLine(line)
		return wrapped
		
	def splitLine(self,line):
		llen = len(line)
		if llen <= self.charsPerLine: return [line]
		ct = 0
		lastct = 0
		out = []
		while ct < llen:
			ct += self.charsPerLine
			sub = line[lastct:ct]
			#Don't count cursor in line length
			if '\r' in sub:
				ct += 1
				sub = line[lastct:ct]
			out.append(sub)
			lastct = ct
		return out

######################################################################################
# Message Window
######################################################################################
class MessageWindow(BaseWindow):
	def __init__( self, *args, **kwargs ):
		self.post = kwargs.get('post')
		#self.imageReplace = '[COLOR FFFF0000]I[/COLOR][COLOR FFFF8000]M[/COLOR][COLOR FF00FF00]G[/COLOR][COLOR FF0000FF]#[/COLOR][COLOR FFFF00FF]%s[/COLOR]'
		self.imageReplace = 'IMG #%s'
		self.action = None
		BaseWindow.__init__( self, *args, **kwargs )
		
	def onInit(self):
		if (FB.theme.get('mode') == 'dark' or __addon__.getSetting('color_mode') == '1') and __addon__.getSetting('color_mode') != '2':
			text = '[COLOR FFFFFFFF]%s[/COLOR][CR] [CR]' % (self.post.translated or self.post.messageAsDisplay())
		else:
			text = '[COLOR FF000000]%s[/COLOR][CR] [CR]' % (self.post.translated or self.post.messageAsDisplay())
		self.getControl(122).setText(text)
		self.getControl(102).setImage(self.post.avatarFinal)
		self.setTheme()
		self.getImages()
		self.getLinks()

	def setTheme(self):
		xbmcgui.lock()
		try:
			title_bg = FB.theme.get('title_bg','FFFFFFFF')
			title_fg = FB.theme.get('title_fg','FF000000')
			self.getControl(251).setColorDiffuse(title_bg) #title bg
			self.getControl(300).setColorDiffuse(title_bg) #sep
			self.getControl(101).setColorDiffuse(FB.theme.get('window_bg','FF222222')) #panel bg
			#self.getControl(351).setColorDiffuse(FB.theme.get('desc_bg',title_bg)) #desc bg
			self.getControl(103).setLabel(TITLE_FORMAT % (title_fg,self.post.cleanUserName() or ''))
			self.getControl(104).setLabel(TITLE_FORMAT % (title_fg,self.post.title or ''))
			self.getControl(105).setLabel(TITLE_FORMAT % (title_fg,self.post.date or ''))
			if (FB.theme.get('mode') == 'dark' or __addon__.getSetting('color_mode') == '1') and __addon__.getSetting('color_mode') != '2':
				self.getControl(351).setColorDiffuse('FF000000')
			else:
				self.getControl(351).setColorDiffuse('FFFFFFFF')
			self.listItemBG = title_bg
		except:
			xbmcgui.unlock()
			raise
		xbmcgui.unlock()
		
	def getLinks(self):
		ulist = self.getControl(148)
		for link in self.post.links():
			item = xbmcgui.ListItem(link.text or link.url,link.urlShow())
			if link.isImage():
				item.setIconImage(link.url)
			elif link.isPost():
				item.setIconImage('post.png')
			elif link.isThread():
				item.setIconImage('thread.png')
			else:
				item.setIconImage('link.png')
			ulist.addItem(item)

	def getImages(self):
		i=0
		for url in self.post.imageURLs():
			i+=1
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
	
	def linkSelected(self):
		idx = self.getControl(148).getSelectedPosition()
		if idx < 0: return
		links = self.post.links()
		if idx >= len(links): return
		link = links[idx]
		
		if link.isImage():
			self.showImage(link.url)
		elif link.isPost() or link.isThread():
			self.action = PostMessage(tid=link.tid,pid=link.pid)
			self.close()
		else:
			webviewer.getWebResult(link.url,dialog=True)
			return
			base = xbmcgui.Dialog().browse(3,__language__(30144),'files')
			if not base: return
			fname,ftype = Downloader(message=__language__(30145)).downloadURL(base,link.url)
			if not fname: return
			xbmcgui.Dialog().ok(__language__(30052),__language__(30146),fname,__language__(30147) % ftype)
		
	def showImage(self,url):
		base = os.path.join(__addon__.getAddonInfo('profile'),'slideshow')
		if not os.path.exists(base): os.makedirs(base)
		clearDirFiles(base)
		image_files = Downloader(message=__language__(30148)).downloadURLs(base,[url],'.jpg')
		if not image_files: return
		w = ImagesDialog("script-forumbrowser-imageviewer.xml" ,__addon__.getAddonInfo('path'),THEME,images=image_files,parent=self)
		w.doModal()
		del w
			
	def onAction(self,action):
		BaseWindow.onAction(self,action)
		if action == ACTION_CONTEXT_MENU:
			self.doMenu()
		
	def doMenu(self):
		options = [__language__(30134),__language__(30135)]
		delete = None
		if FB.canDelete(self.post.cleanUserName()):
			delete = len(options)
			options.append(__language__(30141))
		idx = xbmcgui.Dialog().select(__language__(30051),options)
		if idx == 0: self.openPostDialog(quote=self.post.messageAsQuote())
		elif idx == 1: self.translateMessage()
		elif idx == delete: self.deletePost()
		
	def translateMessage(self):
		message = translateDisplay(self.post.messageAsDisplay())
		desc_base = '[COLOR FF000000]%s[/COLOR][CR] [CR]'
		self.getControl(122).setText(desc_base % message)
		self.post.translated = message
			
	def deletePost(self):
		post = PostMessage(self.post.pid,self.post.tid,self.post.fid)
		if not self.post.pid: return
		prog = xbmcgui.DialogProgress()
		prog.create(__language__(30149),__language__(30150))
		prog.update(0)
		try:
			FB.deletePost(post)
		except:
			prog.close()
			raise
		prog.close()
		self.action = Action('REFRESH')
		self.close()
		
	def openPostDialog(self,quote=''):
		if quote:
			user = self.post.userName
		else:
			user=''
		pm = PostMessage(self.post.pid,self.post.tid,self.post.fid)
		if quote: pm.setQuote(user,quote)
		w = PostDialog("script-forumbrowser-post.xml" ,__addon__.getAddonInfo('path'),THEME,post=pm,parent=self)
		w.doModal()
		#posted = w.posted
		del w
	
######################################################################################
# Replies Window
######################################################################################
class RepliesWindow(PageWindow):
	def __init__( self, *args, **kwargs ):
		PageWindow.__init__( self, *args, **kwargs )
		self.tid = kwargs.get('tid','')
		self.fid = kwargs.get('fid','')
		self.pid = ''
		self.topic = kwargs.get('topic','')
		self.lastid = kwargs.get('lastid','')
		self.parent = kwargs.get('parent')
		#self._firstPage = __language__(30113)
		self._newestPage = __language__(30112)
		self.me = self.parent.parent.getUsername()
		self.posts = {}
		self.empty = True
		self.desc_base = '[CR][COLOR FF000000]%s[/COLOR][CR] [CR]'
		
	
	def onInit(self):
		self.setStopControl(self.getControl(106))
		self.setProgressCommands(self.startProgress,self.setProgress,self.endProgress)
		self.postSelected()
		self.setTheme()
		self.getControl(201).setEnabled(self.parent.parent.hasLogin())
		self.showThread()
		self.setFocus(self.getControl(120))
	
	def setTheme(self):
		xbmcgui.lock()
		try:
			title_bg = FB.theme.get('title_bg','FFFFFFFF')
			title_fg = FB.theme.get('title_fg','FF000000')
			self.getControl(251).setColorDiffuse(title_bg) #title bg
			self.getControl(300).setColorDiffuse(title_bg) #sep
			self.getControl(301).setColorDiffuse(title_bg) #sep
			self.getControl(302).setColorDiffuse(title_bg) #sep
			self.getControl(101).setColorDiffuse(FB.theme.get('window_bg','FF222222')) #panel bg
			#self.getControl(351).setColorDiffuse(FB.theme.get('desc_bg',title_bg)) #desc bg
			mtype = self.tid == "private_messages" and __language__(30151) or __language__(30130)
			self.getControl(103).setLabel(TITLE_FORMAT % (title_fg,mtype))
			self.getControl(104).setLabel(TITLE_FORMAT % (title_fg,self.topic))
			if (FB.theme.get('mode') == 'dark' or __addon__.getSetting('color_mode') == '1') and __addon__.getSetting('color_mode') != '2':
				self.mode = 'dark'
				self.desc_base = '[CR][COLOR FFFFFFFF]%s[/COLOR][CR] [CR]'
			else:
				self.mode = 'light'
				self.desc_base = '[CR][COLOR FF000000]%s[/COLOR][CR] [CR]'
			if self.tid == 'private_messages': self.getControl(201).setLabel('Send Message')
		except:
			xbmcgui.unlock()
			raise
		xbmcgui.unlock()
		
	def showThread(self,nopage=False):
		if nopage:
			page = ''
		else:
			page = '1'
			if __addon__.getSetting('open_thread_to_newest') == 'true': page = '-1'
		
		self.fillRepliesList(page)
		
	def fillRepliesList(self,page=''):
		if self.tid == 'private_messages':
			t = self.getThread(FB.getPrivateMessages,finishedCallback=self.doFillRepliesList)
			t.setArgs(callback=t.progressCallback,donecallback=t.finishedCallback)
		else:
			t = self.getThread(FB.getReplies,finishedCallback=self.doFillRepliesList)
			t.setArgs(self.tid,self.fid,page,lastid=self.lastid,pid=self.pid,callback=t.progressCallback,donecallback=t.finishedCallback)
		t.start()
		
	def doFillRepliesList(self,replies,pageData):
		if not replies:
			if replies == None:
				LOG('GET REPLIES ERROR')
				xbmcgui.Dialog().ok(__language__(30050),__language__(30131),__language__(30132))
			return
		self.empty = False
		defAvatar = os.path.join(__addon__.getAddonInfo('path'),'resources','skins',THEME,'media','avatar-none.png')
		xbmcgui.lock()
		try:
			self.getControl(120).reset()
			if not self.topic: self.topic = pageData.topic
			if not self.tid: self.tid = pageData.tid
			self.setupPage(pageData)
			if __addon__.getSetting('reverse_sort') != 'true' or self.tid == 'private_messages': replies.reverse()
			self.posts = {}
			select = -1
			for post,idx in zip(replies,range(0,len(replies))):
				#print post.postId + ' ' + self.pid
				if self.pid and post.postId == self.pid: select = idx
				self.posts[post.postId] = post
				title = post.title or ''
				if title: title = '[B]%s[/B][CR][CR]' % title
				url = defAvatar
				if post.avatar: url = FB.makeURL(post.avatar)
				post.avatarFinal = url
				user = re.sub('<.*?>','',post.userName)
				item = xbmcgui.ListItem(label=user,label2=post.date + ': ' + title)
				if user == self.me: item.setInfo('video',{"Director":'me'})
				item.setProperty('message',self.desc_base % (title + post.messageAsDisplay()))
				item.setProperty('post',post.postId)
				item.setProperty('avatar',url)
				item.setProperty('status',post.status)
				item.setProperty('date',post.date)
				item.setInfo('video',{'Genre':self.mode})
				self.getControl(120).addItem(item)
			if select > -1: self.getControl(120).selectItem(int(select))
		except:
			xbmcgui.unlock()
			ERROR('FILL REPLIES ERROR')
			xbmcgui.Dialog().ok(__language__(30050),__language__(30133))
			raise
		xbmcgui.unlock()
		if select > -1: self.postSelected(itemindex=select)
		title_fg = FB.theme.get('title_fg','FF000000')
		self.getControl(104).setLabel(TITLE_FORMAT % (title_fg,self.topic))
		self.pid = ''
		self.getAvatars()
		
	def getAvatars(self):
		urls = {}
		for post in self.posts.values():
			url = FB.makeURL(post.avatar)
			if url: urls[url] = 1
		targetdir = os.path.join(__addon__.getAddonInfo('profile'),'avatars')
		TD.startDownload(targetdir,urls.keys(),ext='.jpg',callback=self.getAvatarsCallback)
		
	def getAvatarsCallback(self,file_dict):
		self.runInMain(self.updateAvatars,file_dict)
		
	def updateAvatars(self,file_dict):
		clist = self.getControl(120)
		for idx in range(0,clist.size()):
			item = clist.getListItem(idx)
			post = self.posts[item.getProperty('post')]
			fname = file_dict.get(FB.makeURL(post.avatar))
			if fname:
				fname = xbmc.translatePath(fname)
				item.setProperty('avatar',fname)
				post.avatarFinal = fname
		focus = self.getFocusId()
		xbmcgui.lock()
		if focus == 120:
			self.setFocusId(105)
		else:
			self.setFocusId(120)
		self.setFocusId(focus)
		xbmcgui.unlock()
			
	def makeLinksArray(self,miter):
		if not miter: return []
		urls = []
		for m in miter:
			urls.append(m)
		return urls
		
	def postSelected(self,itemindex=-1):
		if itemindex >= 0:
			item = self.getControl(120).getListItem(itemindex)
		else:
			item = self.getControl(120).getSelectedItem()
		if not item: return
		post = self.posts.get(item.getProperty('post'))
		post.tid = self.tid
		post.fid = self.fid
		w = MessageWindow("script-forumbrowser-message.xml" ,__addon__.getAddonInfo('path'),THEME,post=post,parent=self)
		w.doModal()
		if w.action:
			if w.action.action == 'CHANGE':
				self.topic = ''
				self.pid = w.action.pid
				self.tid = w.action.tid
				if w.action.pid: self.showThread(nopage=True)
				else: self.showThread()
			elif w.action.action == 'REFRESH':
				self.fillRepliesList(self.pageData.page)
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
	
	def doMenu(self):
		options = [__language__(30134),__language__(30135),__language__(30054)]
		delete = None
		item = self.getControl(120).getSelectedItem()
		post = self.posts.get(item.getProperty('post'))
		if FB.canDelete(item.getLabel()):
			delete = len(options)
			options.append(__language__(30141))
		idx = xbmcgui.Dialog().select(__language__(30051),options)
		if idx == 0:
			self.stopThread()
			self.openPostDialog(quote=post.messageAsQuote())
		elif idx == 1:
			self.stopThread()
			self.translateMessage()
		elif idx == 2:
			self.stopThread()
			self.fillRepliesList(self.pageData.page)
		elif idx == delete:
			self.stopThread()
			self.deletePost()
		if self.empty: self.fillRepliesList()
		
	def translateMessage(self):
		item = self.getControl(120).getSelectedItem()
		post =  self.posts.get(item.getProperty('post'))
		message = translateDisplay(post.messageAsDisplay())
		item.setProperty('message',self.desc_base % message)
		post.translated = message
		self.setFocusId(105)
		self.setFocusId(120)
		item.select(True)
			
	def deletePost(self):
		item = self.getControl(120).getSelectedItem()
		pid = item.getProperty('post')
		if not pid: return
		prog = xbmcgui.DialogProgress()
		prog.create(__language__(30149),__language__(30150))
		prog.update(0)
		try:
			if self.tid == 'private_messages':
				FB.deletePrivateMessageViaIndex(pid[2:])
			else:
				post = PostMessage(pid,self.tid,self.fid)
				FB.deletePost(post)
		except:
			prog.close()
			raise
		prog.close()
		self.fillRepliesList(self.pageData.page)
		
	def openPostDialog(self,quote=''):
		if quote:
			item = self.getControl(120).getSelectedItem()
			user = item.getLabel()
		else:
			if self.tid == 'private_messages':
				item = None
			else:
				if not self.getControl(120).size(): return
				item = self.getControl(120).getListItem(0)
			user=''
		#if not item.getProperty('post'): item = self.getControl(120).getListItem(1)
		if item:
			pid = item.getProperty('post')
		else:
			pid = 0
		pm = PostMessage(pid,self.tid,self.fid,is_pm=(self.tid == 'private_messages'))
		if quote: pm.setQuote(user,quote)
		if self.tid == 'private_messages':
			to = doKeyboard('Enter Receipient(s)')
			if not to: return
			pm.to = to
		if __addon__.getSetting('use_text_editor') == 'true':
			w = TextPostDialog(	"script-forumbrowser-post-text.xml" ,__addon__.getAddonInfo('path'),THEME,post=pm,parent=self)
		else:
			w = LinePostDialog(	"script-forumbrowser-post.xml" ,__addon__.getAddonInfo('path'),THEME,post=pm,parent=self)
		w.doModal()
		posted = w.posted
		del w
		if posted:
			self.fillRepliesList('-1')
	
	def gotoPage(self,page):
		self.stopThread()
		self.fillRepliesList(page)

######################################################################################
# Threads Window
######################################################################################
class ThreadsWindow(PageWindow):
	def __init__( self, *args, **kwargs ):
		self.fid = kwargs.get('fid','')
		self.topic = kwargs.get('topic','')
		self.parent = kwargs.get('parent')
		self.me = self.parent.getUsername()
		self.empty = True
		self.textBase = '%s'
		PageWindow.__init__( self, *args, **kwargs )
		
	def onInit(self):
		self.setStopControl(self.getControl(106))
		self.setProgressCommands(self.startProgress,self.setProgress,self.endProgress)
		self.setTheme()
		self.fillThreadList()
		self.setFocus(self.getControl(120))
		
	def setTheme(self):
		try:
			xbmcgui.lock()
			title_bg = FB.theme.get('title_bg','FFFFFFFF')
			title_fg = FB.theme.get('title_fg','FF000000')
			self.getControl(251).setColorDiffuse(title_bg) #title bg
			self.getControl(300).setColorDiffuse(title_bg) #sep
			self.getControl(301).setColorDiffuse(title_bg) #sep
			self.getControl(101).setColorDiffuse(FB.theme.get('window_bg','FF222222')) #panel bg
			#self.getControl(121).setColorDiffuse(title_bg) #scroll bar doesn't work
			self.getControl(351).setColorDiffuse(FB.theme.get('desc_bg',title_bg)) #desc bg
			self.getControl(103).setLabel(TITLE_FORMAT % (title_fg,__language__(30160)))
			self.getControl(104).setLabel(TITLE_FORMAT % (title_fg,self.topic))
			if (FB.theme.get('mode') == 'dark' or __addon__.getSetting('color_mode') == '1') and __addon__.getSetting('color_mode') != '2':
				self.textBase = '[COLOR FFFFFFFF]%s[/COLOR]'
				self.highBase = '[COLOR FF00DD00]%s[/COLOR]'
				self.getControl(115).setColorDiffuse('BB000000')
			else:
				self.textBase = '[COLOR FF000000]%s[/COLOR]'
				self.highBase = '[COLOR FF006600]%s[/COLOR]'
				self.getControl(115).setColorDiffuse('99FFFFFF')
		except:
			xbmcgui.unlock()
			raise
		xbmcgui.unlock()
		
	def fillThreadList(self,page=''):
		if self.fid == 'subscriptions':
			t = self.getThread(FB.getSubscriptions,finishedCallback=self.doFillThreadList)
			t.setArgs(page,callback=t.progressCallback,donecallback=t.finishedCallback)
		else:
			t = self.getThread(FB.getThreads,finishedCallback=self.doFillThreadList)
			t.setArgs(self.fid,page,callback=t.progressCallback,donecallback=t.finishedCallback)
		t.start()
		
	def doFillThreadList(self,threads,pageData):
		if not threads:
			LOG('GET THREADS ERROR')
			xbmcgui.Dialog().ok(__language__(30050),__language__(30161),__language__(30053))
			return
		self.empty = False
		xbmcgui.lock()
		try:
			self.getControl(120).reset()
			self.setupPage(pageData)
			desc_base = unicode.encode('[COLOR '+FB.theme.get('desc_fg',FB.theme.get('title_fg','FF000000'))+']'+__language__(30162)+' %s[/COLOR]','utf8')
			desc_bold = unicode.encode('[COLOR '+FB.theme.get('desc_fg',FB.theme.get('title_fg','FF000000'))+'][B]'+__language__(30162)+' %s[/B][/COLOR]','utf8')
			
			for t in threads:
				tdict = t.groupdict()
				starter = tdict.get('starter','Unknown')
				title = tdict.get('title','')
				title = convertHTMLCodes(MC.tagFilter.sub('',title))
				last = tdict.get('lastposter','?')
				tid = tdict.get('threadid','')
				fid = tdict.get('forumid','')
				sticky = tdict.get('sticky') and 'sticky' or ''
				if starter == self.me: starterbase = self.highBase
				else: starterbase = self.textBase
				
				item = xbmcgui.ListItem(label=starterbase % starter,label2=self.textBase % title)
				item.setInfo('video',{"Genre":sticky})
				item.setProperty("id",tid)
				item.setProperty("fid",fid)
				if last == self.me:
					item.setProperty("last",desc_bold % last)
				else:
					item.setProperty("last",desc_base % last)
				item.setProperty("lastid",tdict.get('lastid',''))
				item.setProperty('title',title)
				self.getControl(120).addItem(item)
		except:
			xbmcgui.unlock()
			ERROR('FILL THREAD ERROR')
			xbmcgui.Dialog().ok(__language__(30050),__language__(30163))
		xbmcgui.unlock()
						
	def openRepliesWindow(self):
		item = self.getControl(120).getSelectedItem()
		tid = item.getProperty('id')
		fid = item.getProperty('fid') or self.fid
		lastid = item.getProperty('lastid')
		topic = item.getProperty('title')
		w = RepliesWindow("script-forumbrowser-replies.xml" , __addon__.getAddonInfo('path'),THEME,tid=tid,fid=fid,lastid=lastid,topic=topic,parent=self)
		w.doModal()
		del w

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
			pass
		PageWindow.onAction(self,action)
		
	def gotoPage(self,page):
		self.stopThread()
		self.fillThreadList(page)

######################################################################################
# Forums Window
######################################################################################
class ForumsWindow(BaseWindow):
	def __init__( self, *args, **kwargs ):
		BaseWindow.__init__( self, *args, **kwargs )
		#FB.setLogin(self.getUsername(),self.getPassword(),always=__addon__.getSetting('always_login') == 'true')
		self.parent = self
		self.empty = True
		self.textBase = '%s'
		self.subTextBase = '%s'
		self.setAsMain()
	
	def getUsername(self):
		return __addon__.getSetting('login_user_' + FB.forum.replace('.','_'))
		
	def getPassword(self):
		return __addon__.getSetting('login_pass_' + FB.forum.replace('.','_'))
		
	def hasLogin(self):
		return self.getUsername() != '' and self.getPassword() != ''
		
	def onInit(self):
		self.setStopControl(self.getControl(105))
		self.setProgressCommands(self.startProgress,self.setProgress,self.endProgress)
		self.resetForum()
		self.fillForumList()
		self.setFocus(self.getControl(120))
		
	def setTheme(self):
		try:
			xbmcgui.lock()
			title_bg = FB.theme.get('title_bg','FFFFFFFF')
			title_fg = FB.theme.get('title_fg','FF000000')
			self.getControl(251).setColorDiffuse(title_bg) #title bg
			self.getControl(300).setColorDiffuse(title_bg) #sep
			self.getControl(301).setColorDiffuse(title_bg) #sep
			self.getControl(302).setColorDiffuse(title_bg) #sep
			self.getControl(101).setColorDiffuse(FB.theme.get('window_bg','FF222222')) #panel bg
			self.getControl(351).setColorDiffuse(FB.theme.get('desc_bg',title_bg)) #desc bg
			self.getControl(103).setLabel(TITLE_FORMAT % (title_fg,__language__(30170)))
			self.getControl(104).setLabel(TITLE_FORMAT % (title_fg,FB.forum))
			if (FB.theme.get('mode') == 'dark' or __addon__.getSetting('color_mode') == '1') and __addon__.getSetting('color_mode') != '2':
				self.subTextBase = '[I][COLOR FFBBBBBB]%s[/COLOR][/I] '
				self.textBase = '[B][COLOR FFFFFFFF]%s[/COLOR][/B]'
				self.getControl(115).setColorDiffuse('BB000000')
			else:
				self.subTextBase = '[I][COLOR FF333333]%s[/COLOR][/I] '
				self.textBase = '[B][COLOR FF000000]%s[/COLOR][/B]'
				self.getControl(115).setColorDiffuse('99FFFFFF')
		except:
			xbmcgui.unlock()
			raise
		xbmcgui.unlock()
		
	def fillForumList(self):
		self.setTheme()
		t = self.getThread(FB.getForums,finishedCallback=self.doFillForumList)
		t.setArgs(callback=t.progressCallback,donecallback=t.finishedCallback)
		t.start()
		
	#def fillForumListFromThread(self,forums,logo,pm_counts):
		#if threading.currentThread().stopped():
		#	LOG('INORING STOPPED THREAD')
		#	return
		#	
		#self.runInMain(self.doFillForumList,forums,logo,pm_counts)
		
	def doFillForumList(self,forums,logo,pm_counts):
		self.endProgress()
		if not forums:
			xbmcgui.Dialog().ok(__language__(30050),__language__(30171),__language__(30053),'Bad Page Data')
			return
		self.empty = False
		#reason = ERROR('GET FORUMS ERROR')
		#xbmcgui.Dialog().ok(__language__(30050),__language__(30171),__language__(30053),reason)
		#self.endProgress()
		#return
		
		try:
			xbmcgui.lock()
			self.getControl(120).reset()
			self.getControl(250).setImage(logo)
			self.setPMCounts(pm_counts)
			#print forums
			desc_base = '[COLOR '+FB.theme.get('desc_fg',FB.theme.get('title_fg','FF000000'))+']%s[/COLOR]'
			for f in forums:
				#print f.group(0)
				fdict = f.groupdict()
				fid = fdict.get('forumid','')
				title = fdict.get('title',__language__(30050))
				desc = fdict.get('description') or __language__(30172)
				sub = fdict.get('subforum')
				if sub:
					text = self.subTextBase
					desc = __language__(30173)
				else:
					text = self.textBase
				title = convertHTMLCodes(re.sub('<[^<>]+?>','',title) or '?')
				item = xbmcgui.ListItem(label=text % title)
				item.setProperty("description",desc_base % convertHTMLCodes(MC.tagFilter.sub('',MC.brFilter.sub(' ',desc))))
				item.setProperty("topic",title)
				item.setProperty("id",fid)
				self.getControl(120).addItem(item)
		except:
			xbmcgui.unlock()
			ERROR('FILL FORUMS ERROR')
			xbmcgui.Dialog().ok(__language__(30050),__language__(30174))
		xbmcgui.unlock()
			
	def setPMCounts(self,pm_counts=None):
		disp = ''
		if pm_counts: disp = ' (%s/%s)' % (pm_counts.get('unread','?'),pm_counts.get('total','?'))
		self.getControl(203).setLabel(__language__(3009) + disp)
		
	def openPMWindow(self):
		w = RepliesWindow("script-forumbrowser-replies.xml" , __addon__.getAddonInfo('path'),THEME,tid='private_messages',topic=__language__(30176),parent=self)
		w.doModal()
		del w
		self.setPMCounts(FB.getPMCounts())
		
	def openThreadsWindow(self):
		item = self.getControl(120).getSelectedItem()
		if not item: return False
		fid = item.getProperty('id')
		topic = item.getProperty('topic')
		w = ThreadsWindow("script-forumbrowser-threads.xml" , __addon__.getAddonInfo('path'), THEME,fid=fid,topic=topic,parent=self)
		w.doModal()
		del w
		self.setPMCounts(FB.getPMCounts())
		return True
		
	def openSubscriptionsWindow(self):
		fid = 'subscriptions'
		topic = __language__(30175)
		w = ThreadsWindow("script-forumbrowser-threads.xml" , __addon__.getAddonInfo('path'), THEME,fid=fid,topic=topic,parent=self)
		w.doModal()
		del w
		self.setPMCounts(FB.getPMCounts())
		
	def changeForum(self):
		fpath = xbmc.translatePath('special://home/addons/script.forum.browser/forums/')
		flist = os.listdir(fpath)
		dialog = xbmcgui.Dialog()
		idx = dialog.select(__language__(30170),flist)
		if idx < 0: return False
		self.stopThread()
		FB.resetBrowser()
		FB.reloadForumData(flist[idx])
		MC.resetRegex()
		self.resetForum()
		self.fillForumList()
		__addon__.setSetting('last_forum',FB.forum)
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
		#print "ACTION: " + str(action.getId()) + " FOCUS: " + str(self.getFocusId()) + " BC: " + str(action.getButtonCode())
		if action == ACTION_CONTEXT_MENU:
			pass
		elif action == ACTION_PARENT_DIR:
			action = ACTION_PREVIOUS_MENU
		BaseWindow.onAction(self,action)
		
	def resetForum(self,hidelogo=True):
		FB.setLogin(self.getUsername(),self.getPassword(),always=__addon__.getSetting('always_login') == 'true')
		self.getControl(201).setEnabled(self.hasLogin() and FB.hasSubscriptions())
		self.getControl(203).setEnabled(FB.hasPM())
		if hidelogo: self.getControl(250).setImage('')
		
	def openSettings(self):
		mode = __addon__.getSetting('color_mode')
		doSettings()
		self.resetForum(False)
		if mode !=  __addon__.getSetting('color_mode'): self.fillForumList()

######################################################################################
# Message Converter
######################################################################################
class MessageConverter:
	def __init__(self):
		self.resetOrdered(False)
		self.resetRegex()
		
		#static replacements
		self.quoteReplace = unicode.encode('[CR]_________________________[CR][B]'+__language__(30180)+'[/B][CR]'+__language__(30181)+' [B]%s[/B][CR][I]%s[/I][CR]_________________________[CR]','utf8')
		self.aQuoteReplace = unicode.encode('[CR]_________________________[CR][B]'+__language__(30180)+'[/B][CR][I]%s[/I][CR]_________________________[CR]','utf8')
		self.quoteImageReplace = '[COLOR FFFF0000]I[/COLOR][COLOR FFFF8000]M[/COLOR][COLOR FF00FF00]A[/COLOR][COLOR FF0000FF]G[/COLOR][COLOR FFFF00FF]E[/COLOR]: \g<url>'
		self.imageReplace = '[COLOR FFFF0000]I[/COLOR][COLOR FFFF8000]M[/COLOR][COLOR FF00FF00]G[/COLOR][COLOR FF0000FF]#[/COLOR][COLOR FFFF00FF]%s[/COLOR]: [I]%s[/I]'
		self.linkReplace = unicode.encode('\g<text> (%s [B]\g<url>[/B])' % __language__(30182),'utf8')
		
		#static filters
		self.imageFilter = re.compile('<img[^<>]+?src="(?P<url>http://.+?)"[^<>]+?/>')
		self.linkFilter = re.compile('<a.+?href="(?P<url>.+?)".*?>(?P<text>.+?)</a>')
		self.ulFilter = re.compile('<ul>(.+?)</ul>')
		#<span style="text-decoration: underline">Underline</span>
		self.olFilter = re.compile('<ol.+?>(.+?)</ol>')
		self.brFilter = re.compile('<br[ /]{0,2}>')
		self.blockQuoteFilter = re.compile('<blockquote>(.+?)</blockquote>',re.S)
		self.colorFilter = re.compile('<font color="(.+?)">(.+?)</font>')
		self.colorFilter2 = re.compile('<span.*?style=".*?color: ?(.+?)".*?>(.+?)</span>')
		self.tagFilter = re.compile('<[^<>]+?>',re.S)
		
	def resetRegex(self):
		self.lineFilter = re.compile('[\n\r\t]')
		f = FB.filters.get('quote')
		self.quoteFilter = f and re.compile(f) or None
		f = FB.filters.get('code')
		self.codeFilter = f and re.compile(f) or None
		f = FB.filters.get('php')
		self.phpFilter = f and re.compile(f) or None
		f = FB.filters.get('html')
		self.htmlFilter = f and re.compile(f) or None
		f = FB.smilies.get('regex')
		self.smileyFilter = f and re.compile(f) or None
		
		#dynamic replacements
		self.codeReplace = unicode.encode('[CR]_________________________[CR][B]'+__language__(30183)+'[/B][CR][COLOR '+FB.theme.get('post_code','FF999999')+']\g<code>[/COLOR][CR]_________________________[CR]','utf8')
		self.phpReplace = unicode.encode('[CR]_________________________[CR][B]'+__language__(30184)+'[/B][CR][COLOR '+FB.theme.get('post_code','FF999999')+']\g<php>[/COLOR][CR]_________________________[CR]','utf8')
		self.htmlReplace = unicode.encode('[CR]_________________________[CR][B]'+__language__(30185)+'[/B][CR][COLOR '+FB.theme.get('post_code','FF999999')+']\g<html>[/COLOR][CR]_________________________[CR]','utf8')
		self.smileyReplace = '[COLOR '+FB.smilies.get('color','FF888888')+']%s[/COLOR]'
		
	def resetOrdered(self,ordered):
		self.ordered = ordered
		self.ordered_count = 0
		
	def messageToDisplay(self,html):
		html = self.lineFilter.sub('',html)
		
		if self.quoteFilter: html = self.quoteFilter.sub(self.quoteConvert,html)
		if self.codeFilter: html = self.codeFilter.sub(self.codeReplace,html)
		if self.phpFilter: html = self.phpFilter.sub(self.phpReplace,html)
		if self.htmlFilter: html = self.htmlFilter.sub(self.htmlReplace,html)
		if self.smileyFilter: html = self.smileyFilter.sub(self.smileyConvert,html)
		
		self.imageCount = 0
		html = self.imageFilter.sub(self.imageConvert,html)
		html = self.linkFilter.sub(self.linkReplace,html)
		html = self.ulFilter.sub(self.processBulletedList,html)
		html = self.olFilter.sub(self.processOrderedList,html)
		html = self.colorFilter.sub(self.convertColor,html)
		html = self.colorFilter2.sub(self.convertColor,html)
		html = self.brFilter.sub('[CR]',html)
		html = self.blockQuoteFilter.sub(self.processIndent,html)
		html = html.replace('<b>','[B]').replace('</b>','[/B]')
		html = html.replace('<i>','[I]').replace('</i>','[/I]')
		html = html.replace('<u>','_').replace('</u>','_')
		html = html.replace('<strong>','[B]').replace('</strong>','[/B]')
		html = html.replace('<em>','[I]').replace('</em>','[/I]')
		html = html.replace('</table>','[CR][CR]')
		html = html.replace('</div></div>','[CR]') #to get rid of excessive new lines
		html = html.replace('</div>','[CR]')
		html = self.tagFilter.sub('',html)
		html = self.removeNested(html,'\[/?B\]','[B]')
		html = self.removeNested(html,'\[/?I\]','[I]')
		html = html.replace('[CR]','\n').strip().replace('\n','[CR]') #TODO Make this unnecessary
		return convertHTMLCodes(html)

	def removeNested(self,html,regex,starttag):
		self.nStart = starttag
		self.nCounter = 0
		return re.sub(regex,self.nestedSub,html)
		
	def nestedSub(self,m):
		tag = m.group(0)
		if tag == self.nStart:
			self.nCounter += 1
			if self.nCounter == 1: return tag
		else:
			self.nCounter -= 1
			if self.nCounter < 0: self.nCounter = 0
			if self.nCounter == 0: return tag
		return ''
		
	def messageAsQuote(self,html):
		html = self.lineFilter.sub('',html)
		if self.quoteFilter: html = self.quoteFilter.sub('',html)
		if self.codeFilter: html = self.codeFilter.sub('[CODE]\g<code>[/CODE]',html)
		if self.phpFilter: html = self.phpFilter.sub('[PHP]\g<php>[/PHP]',html)
		if self.htmlFilter: html = self.htmlFilter.sub('[HTML]\g<html>[/HTML]',html)
		if self.smileyFilter: html = self.smileyFilter.sub(self.smileyConvert,html)
		html = self.linkFilter.sub('[URL="\g<url>"]\g<text>[/URL]',html)
		html = self.imageFilter.sub('[IMG]\g<url>[/IMG]',html)
		html = self.colorFilter.sub(self.convertColor,html)
		html = self.colorFilter2.sub(self.convertColor,html)
		html = html.replace('<b>','[B]').replace('</b>','[/B]')
		html = html.replace('<i>','[I]').replace('</i>','[/I]')
		html = html.replace('<u>','[U]').replace('</u>','[/U]')
		html = html.replace('<strong>','[B]').replace('</strong>','[/B]')
		html = html.replace('<em>','[I]').replace('</em>','[/I]')
		html = re.sub('<br[^<>]*?>','\n',html)
		html = html.replace('</table>','\n\n')
		html = html.replace('</div>','\n')
		html = re.sub('<[^<>]+?>','',html)
		return convertHTMLCodes(html).strip()
		
	def imageConvert(self,m):
		self.imageCount += 1
		return self.imageReplace % (self.imageCount,m.group('url'))
		
	def smileyRawConvert(self,m):
		return FB.smilies.get(m.group('smiley'),'')
		
	def smileyConvert(self,m):
		return self.smileyReplace % FB.smilies.get(m.group('smiley'),'')
		
	def quoteConvert(self,m):
		quote = self.imageFilter.sub(self.quoteImageReplace,m.group('quote'))
		if m.group('user'):
			return self.quoteReplace % (m.group('user'),quote)
		else:
			return self.aQuoteReplace % quote
			
	def processIndent(self,m):
		return '    ' + re.sub('\n','\n    ',m.group(1)) + '\n'
		
	def convertColor(self,m):
		if m.group(1).startswith('#'):
			color = 'FF' + m.group(1)[1:].upper()
		else:
			color = m.group(1).lower()
		return '[COLOR %s]%s[/COLOR]' % (color,m.group(2))

	def processBulletedList(self,m):
		self.resetOrdered(False)
		return self.processList(m.group(1))
		
	def processOrderedList(self,m):
		self.resetOrdered(True)
		return self.processList(m.group(1))
			
	def processList(self,html):
		return re.sub('<li>(.+?)</li>',self.processItem,html) + '\n'

	def processItem(self,m):
		self.ordered_count += 1
		if self.ordered: bullet = str(self.ordered_count) + '.'
		else: bullet = '*'
		return  '%s %s\n' % (bullet,m.group(1))
		
	def parseCodes(self,text):
		text = re.sub('\[QUOTE=(?P<user>\w+)(?:;\d+)*\](?P<quote>.+?)\[/QUOTE\](?is)',MC.quoteConvert,text)
		text = re.sub('\[QUOTE\](?P<quote>.+?)\[(?P<user>)?/QUOTE\](?is)',MC.quoteConvert,text)
		text = re.sub('\[CODE\](?P<code>.+?)\[/CODE\](?is)',MC.codeReplace,text)
		text = re.sub('\[PHP\](?P<php>.+?)\[/PHP\](?is)',MC.phpReplace,text)
		text = re.sub('\[HTML\](?P<html>.+?)\[/HTML\](?is)',MC.htmlReplace,text)
		text = re.sub('\[IMG\](?P<url>.+?)\[/IMG\](?is)',MC.quoteImageReplace,text)
		text = re.sub('\[URL="(?P<url>.+?)"\](?P<text>.+?)\[/URL\](?is)',MC.linkReplace,text)
		text = re.sub('\[URL\](?P<text>(?P<url>.+?))\[/URL\](?is)',MC.linkReplace,text)
		return text
		
######################################################################################
# Functions
######################################################################################

def subTags(m): return '[%s]' % m.group(1).upper()
def translateDisplay(message):
	pre = re.sub('\[(/?(?:(?:COLOR(?: \w+)?)|CR|B|I))\]',r'<\1>',message).replace('> ','><space>').replace(' <','<space><')
	#print pre
	message = TR.translate(pre,FB.formats.get('language','en'),getLanguage(),newline='<CR>',format='html')
	message = convertHTMLCodes(message)
	message = message.replace('> ','>').replace(' <','<').replace('<space>',' ')
	#print unicode.encode(message,'ascii','replace')
	message = re.sub('<(/?COLOR(?: \w+)?)>',r'[\1]',message)
	message = re.sub('<([^<>]+?)>',subTags,message)
	#print unicode.encode(message,'ascii','replace')
	return message
		
def calculatePage(low,high,total):
	low = int(low.replace(',',''))
	high = int(high.replace(',',''))
	total = int(total.replace(',',''))
	if high == total: return -1
	return str(int(round(float(high)/((high-low)+1))))
	
def cUConvert(m): return unichr(int(m.group(1)))
def cTConvert(m): return unichr(htmlentitydefs.name2codepoint.get(m.group(1),32))
def convertHTMLCodes(html):
	try:
		html = re.sub('&#(\d{1,5});',cUConvert,unicode(html,'utf8'))
		html = re.sub('&(\w+?);',cTConvert,html)
	except:
		pass
	return html
				
def messageToText(html):
	html = MC.lineFilter.sub('',html)
	html = re.sub('<br.*?>','\n',html)
	html = html.replace('</table>','\n\n')
	html = html.replace('</div></div>','\n') #to get rid of excessive new lines
	html = html.replace('</div>','\n')
	html = re.sub('<.*?>','',html)
	return convertHTMLCodes(html).strip()
	
def doKeyboard(prompt,default='',hidden=False):
	keyboard = xbmc.Keyboard(default,prompt)
	keyboard.setHiddenInput(hidden)
	keyboard.doModal()
	if not keyboard.isConfirmed(): return ''
	return keyboard.getText()
			
def setLogins():
	fpath = xbmc.translatePath('special://home/addons/script.forum.browser/forums/')
	flist = os.listdir(fpath)
	dialog = xbmcgui.Dialog()
	idx = dialog.select(__language__(30200),flist)
	if idx < 0: return
	forum = flist[idx]
	user = doKeyboard(__language__(30201),__addon__.getSetting('login_user_' + forum.replace('.','_')))
	if not user: return
	password = doKeyboard(__language__(30202),__addon__.getSetting('login_pass_' + forum.replace('.','_')),True)
	if not password: return
	__addon__.setSetting('login_user_' + forum.replace('.','_'),user)
	__addon__.setSetting('login_pass_' + forum.replace('.','_'),password)
	
def doSettings():
	dialog = xbmcgui.Dialog()
	idx = dialog.select(__language__(30203),[__language__(30204),__language__(30203)])
	if idx < 0: return
	if idx == 0: setLogins()
	elif idx == 1: __addon__.openSettings()
	
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
		pct = ((float(read)/total) * (self.file_pct)) + (self.file_pct * self.current)
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
				file_list.append(fname)
				self.getUrlFile(url,fname,callback=self.progCallback)
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
		outfile = open(target, 'wb')
		read = 0
		bs = 1024 * 8
		while 1:
			block = urlObj.read(bs)
			if block == "": break
			read += len(block)
			outfile.write(block)
			if not callback(read, size): raise Exception
		outfile.close()
		urlObj.close()
		return (target,ftype)
	
######################################################################################
# Startup
######################################################################################
if sys.argv[-1] == 'settings':
	doSettings()
else:
	#THEME = 'Fullscreen'
	TD = ThreadDownloader()
	FB = ForumBrowser(__addon__.getSetting('last_forum') or 'forum.xbmc.org',always_login=__addon__.getSetting('always_login') == 'true')
	MC = MessageConverter()
	TR = googleTranslateAPI()
	
	w = ForumsWindow("script-forumbrowser-forums.xml" , __addon__.getAddonInfo('path'), THEME)
	w.doModal()
	del w
	sys.modules.clear()
	