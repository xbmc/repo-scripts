import forumbrowser, json, urllib2, urllib, sys, os,re, time
from forumbrowser import FBData
from texttransform import BBMessageConverter
from lib.util import LOG, ERROR

DEBUG = sys.modules["__main__"].DEBUG

def testForum(forum):
	url3 = None
	url2 = None
	if forum.startswith('http://'):
		url = forum
		if not forum.endswith('/'): forum += '/'
		if not forum.endswith('.php/'): url2 = forum + 'forumrunner/request.php'
	else:
		if forum.startswith('/'): forum = forum[1:]
		if forum.endswith('/'): forum = forum[:-1]
		url = 'http://%s/forumrunner/request.php' % forum
		url2 = None
		if '/' in forum: url3 = 'http://%s/forumrunner/request.php' % forum.split('/',1)[0]
	
	for u in (url,url2,url3):
		if not u: continue
		try:
			client = ForumrunnerClient(u)
			result = client.version()
			if result.get('version'): return u
		except:
			continue
	return None

class FRCFail:
	def __init__(self,result=None):
		self.result = result or {}
		self.message = result.get('message','') or ''
		
	def __nonzero__(self):
		return False
	
class ForumrunnerClient():
	def __init__(self,url):
		self.url = url
		if not self.url.endswith('/'): self.url += '/'
		self.cache = {}
		self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor)
		#urllib2.install_opener(self.opener)
		
	def __getattr__(self, method):
		if method.startswith('_'): return object.__getattr__(self,method)
		if method in self.cache:
			return self.cache[method]
				
		def handler(**args):
			try:
				return self._callMethod(method,**args)
			except:
				LOG('Failed: ForumrunnerClient.%s()' % method)
				raise
	
		handler.method = method
		
		self.cache[method] = handler
		return handler
	
	def _callMethod(self,method,**args):
		url = self.url #+ 'request.php?cmd=' + method
		if url.endswith('/'): url = url[:-1]
		args['cmd'] = method
		#url = '&'.join((url,urllib.urlencode(args)))
		encArgs = urllib.urlencode(args)
		try:
			obj = self.opener.open(url,encArgs)
		except urllib2.HTTPError,e:
			if e.code == 404: raise forumbrowser.ForumNotFoundException('Forumrunner')
			data = e.read()
			return FRCFail({'message':e.msg + '\n\n' + data})
			
		if DEBUG: LOG('Response Headers: ' + str(obj.info()))
		encoding = obj.info().get('content-type').split('charset=')[-1]
		if '/' in encoding: encoding = 'utf8'
		data = unicode(obj.read(),encoding)
		pyobj = None
		try:
			pyobj = json.loads(data)
		except:
			pass
		#open('/home/ruuk/test.html','w').write(data.encode('ascii','replace'))
		if not pyobj: pyobj = json.loads(re.sub(r'\\u[\d\w]+','?',data),strict=False)
		if DEBUG: LOG('JSON: ' + str(pyobj))
		if pyobj.get('success'):
			return pyobj.get('data')
		else:
			return FRCFail(pyobj)
		
################################################################################
# ForumPost
################################################################################
class ForumPost(forumbrowser.ForumPost):
	imageFilter = re.compile('<img[^>]+src="(?P<url>https?://[^"]+)"[^>]*/>')
	linkFilter = re.compile('<a.+?href="(?P<url>.+?)".*?>(?P<text>.+?)</a>')
	quotFilter = re.compile('<div class="quotedRoot">(.*?)</div>(?s)')
	def __init__(self,fb,pdict):
		forumbrowser.ForumPost.__init__(self, fb, pdict)
		
	def setVals(self,pdict):
		self.postId = pdict.get('post_id',pdict.get('id',''))
		self.tid = pdict.get('thread_id','')
		self.userName = pdict.get('username',pdict.get('post_username',''))
		self.userId = pdict.get('userid',pdict.get('post_userid',''))
		self.title = pdict.get('title','')
		self.message = pdict.get('edittext',self.filterMessage(pdict.get('text',pdict.get('message',pdict.get('thread_preview','')))))
		self.date = pdict.get('post_timestamp',pdict.get('pm_timestamp',''))
		self.images = pdict.get('images',[])
		self.thumbs = pdict.get('image_thumbs',[])
		self.quotable = pdict.get('quotable','')
		self.avatar = pdict.get('avatarurl','')
		self.postCount = pdict.get('numposts',pdict.get('posts',0))
		self.joinDate = pdict.get('joindate',0)
		self.status = pdict.get('usertitle','')
		#print self.images
		#print self.thumbs
	
	def update(self,pdict):
		self.setVals(pdict)
		
	def imageURLs(self):
		return self.MC.imageFilter.findall(self.getMessage())
		
	def linkImageURLs(self):
		return re.findall('<a.+?href="(http://.+?\.(?:jpg|png|gif|bmp))".+?</a>',self.message)
	
	def linkURLs(self):
		return self.MC.linkFilter.finditer(self.getMessage())
	
	def link2URLs(self):
		if not self.MC.linkFilter2: return []
		return self.MC.linkFilter2.finditer(self.getMessage())
	
	def messageAsQuote(self):
		qr = self.FB.getQuoteReplace()
		return qr.replace('!USER!',self.userName).replace('!POSTID!',self.postId).replace('!USERID!',self.userId).replace('!DATE!',str(int(time.time()))).replace('!QUOTE!',self.quotable)
	
	def getMessage(self,skip=False,raw=False):
		if raw and self.isShort:
			self.FB.updatePost(self)
		if self.hideSignature: return self.message
		return self.message + self.signature
	
	def messageToDisplay(self,message):
		return self.MC.messageToDisplay(message)
	
	def filterMessage(self,message):
		message = message.replace('<br/>','\n').replace('</color>','')#'[/COLOR]')
		message = message.replace('<b>','[b]').replace('</b>','[/b]').replace('<i>','[i]').replace('</i>','[/i]')
		message = re.sub('<color color="#(\w+)">','',message) #r'[COLOR FF\1]',message)
		message = re.sub('\[\*\]',self.MC.bullet,message)
		message = self.quotFilter.sub(r'[quote]\1[/quote]',message)
		message = self.linkFilter.sub(r'[url=\g<url>]\g<text>[/url]',message)
		message = self.imageFilter.sub(r'[img]\g<url>[/img]',message)
		return message
		
	
	
class ForumrunnerForumBrowser(forumbrowser.ForumBrowser):
	browserType = 'forumrunner'
	prefix = 'FR.'
	ForumPost = ForumPost
	
	def __init__(self,forum,always_login=False):
		forumbrowser.ForumBrowser.__init__(self, forum, always_login,BBMessageConverter)
		self.forum = forum[3:]
		self.T = sys.modules["__main__"].T
		self.online = {}
		self.lastOnlineCheck = 0
		self.version = {}
		self.pmBoxes = []
		self.loadForumFile()
		self.setupClient()
		self.setFilters()
		self.initialize()
	
	def setupClient(self):
		self.needsLogin = True
		if not self._url:
			self._url = 'http://%s/forumrunner/request.php' % self.forum
#		url = self._url
#		self.client = None
#		result = None
#		if __addon__.getSetting('enable_ssl') == 'true' and not getSetting('forumrunner_disable_ssl') == 'true':
#			LOG('Enabling SSL')
#			url = url.replace('http://','https://')
#			self.client = ForumrunnerClient(url)
#			try:
#				result = self.client.version()
#				self.SSL = True
#			except urllib2.URLError:
#				self.client = None
#				LOG('Falling back to normal http')
#		
#		if not self.client:
		self.client = ForumrunnerClient(self._url)
		try:
			result = self.client.version()
		except forumbrowser.ForumNotFoundException:
			raise
		except:
			ERROR('Error getting version info')
			raise forumbrowser.BrokenForumException(self._url)
		if not result:
			LOG(result.message)
			raise Exception(result.message)
			return False
		
		self.SSL = False
			
		self.platform = result.get('platform')
		self.charset = result.get('charset')
		self.version = result
		
		LOG('Forum Type: ' + self.platform)
		LOG('Plugin Version: ' + result.get('version'))
		return True
		
	def setFilters(self):
		self.filters['quote'] = self.getQuoteFormat()
	
	def getForumType(self):
		text = re.sub('\d','',self.platform)
		if text == 'vb': return 'vb'
		elif text == 'phpbb': return 'pb' #don't know if this is right
		elif text == 'xen': return 'xf'
		elif text == 'mybb': return 'mb'
		elif text == 'ipb': return 'ip' #don't know if this is right
		return text
	
	def getForumVersion(self):
		m = re.search('(\d+)',self.platform)
		if not m: return ''
		return m.group(1)
		
	def getForumTypeName(self):
		return self.forumTypeNames.get(self.getForumType(),'Unknown')
	
	def getForumInfo(self):
		return [	('name',self.getDisplayName()),
					('interface','Forumrunner'),
					('forumrunner_plugin_version',self.version.get('version')),
					('forum_type',self.getForumTypeName() + ' (' + self.getForumVersion()) + ')',
					('login_set',self.canLogin())
				]
		
	def loadForumFile(self):
		forum = self.getForumID()
		fname = os.path.join(sys.modules["__main__"].FORUMS_PATH,forum)
		if not os.path.exists(fname):
			fname = os.path.join(sys.modules["__main__"].FORUMS_STATIC_PATH,forum)
			if not os.path.exists(fname): return False
		self.loadForumData(fname)
		self._url = self.urls.get('forumrunner_server','')
		self.formats['quote'] = ''
			
	def createForumDict(self,data,sub=False):
		data['forumid'] = data.get('id')
		data['title'] = unicode(data.get('name'))
		data['description'] = unicode(data.get('desc'))
		data['subforum'] = sub
		return data
	
	def isLoggedIn(self): return self._loggedIn
	
	def login(self):
		LOG('LOGGING IN')
		result = self.client.login(username=self.user,password=self.password)
		if not result:
			LOG('Failed to login: ' + result.message)
			self.loginError = result.message
			return False
		if not result.get('authenticated'):
			error = str(result.get('requires_authentication',''))
			LOG('LOGIN FAILED: ' + error)
			self.loginError = error
			self._loggedIn = False
		else:
			if DEBUG:
				LOG('LOGGED IN: ' + str(result.get('requires_authentication','')))
			else:
				LOG ('LOGGED IN')
			self.loginError = ''
			self._loggedIn = True
			return True
		return False
		
	def checkLogin(self,callback=None,callback_percent=5):
		if self.loginError: return False
		if not self.user or not self.password: return False
		if not callback: callback = self.fakeCallback
		if self.needsLogin or not self.isLoggedIn():
			self.needsLogin = False
			if not callback(callback_percent,self.T(32100)): return False
			if not self.login():
				return False
		return True
	
	def getForums(self,callback=None,donecallback=None):
		if not callback: callback = self.fakeCallback
		logo = None
		while True:
			if not callback(20,self.T(32102)): break
			try:
				data = self.client.get_forum()
				base = data.get('forums')
				flist = []
				for forum in base:
					if forum.get('link'):
						flist.append((forum,False))
						continue
					sub = False
					data = self.client.get_forum(forumid=forum.get('id'))
					f = data.get('forums')
					t = data.get('threads')
					if t: flist.append((forum,False))
					for ff in f:
						flist.append((ff,sub))
			except:
				em = ERROR('ERROR GETTING FORUMS')
				callback(-1,'%s' % em)
				if donecallback: donecallback(FBData(error=em))
				return FBData(error=em)
			if not callback(40,self.T(32103)): break
			forums = []
			for forum,sub in flist:
				forums.append(self.createForumDict(forum,sub))
			if not callback(80,self.T(32231)): break
			logo = self.urls.get('logo') or 'http://%s/favicon.ico' % self.domain()
			try:
				pm_counts = self.getPMCounts(80)
			except:
				ERROR('Failed to get PM Counts')
				pm_counts = None
			callback(100,self.T(32052))
			
			result = FBData(forums,extra={'logo':logo,'pmcounts':pm_counts})
			if donecallback: donecallback(result)
			return result
			
		if donecallback: donecallback(FBData(extra={'logo':logo},error='CANCEL'))
		return FBData(extra={'logo':logo},error='CANCEL')

	def createThreadDict(self,data,sticky=False):
		if data.get('announcement'): sticky = True
		data['threadid'] = data.get('thread_id','')
		data['starter'] = data.get('post_username',self.user)
		data['title'] = data.get('thread_title','')
		data['short_content'] = re.sub('[\t\r\n]','',data.get('thread_preview',''))
		data['forumid'] = data.get('forum_id','')
		data['sticky'] = sticky
		return data
	
	def _getThreads(self,forumid,page,callback):
		if not callback: callback = self.fakeCallback
		while True:
			threads = []
			if not callback(20,self.T(32102)): break
			data = self.client.get_forum(forumid=forumid,page=page,perpage=20)
			if not callback(40,self.T(32103)): break
			for s in data.get('threads_sticky'): threads.append(self.createThreadDict(s,True))
			if not callback(60,self.T(32102)): break
			for t in data.get('threads'): threads.append(self.createThreadDict(t))
			if not callback(80,self.T(32103)): break
			total = int(data.get('total_threads',1))
			current = len(data.get('threads',[]))
			pd = self.getPageData(page=page,total_items=total,current_total=current)
			return threads, pd
		return None,None
	
	def hasSubscriptions(self): return True
	
	def getSubscriptions(self,page='',callback=None,donecallback=None,page_data=None):
		if not self.checkLogin(callback=callback): self.finish(FBData(error='LOGIN FAILED'),donecallback)
		return self.getThreads(None, page, callback, donecallback)
	
	def _getSubscriptions(self,page,callback,perpage=20):
		callback(20,self.T(32102))
		sub = self.client.get_subscriptions(page=page,perpage=perpage)
		total = int(sub.get('total_threads',1))
		current = len(sub.get('threads',[]))
		pd = self.getPageData(page=page,total_items=total,current_total=current)
		normal = sub.get('threads',[])
		if not callback(70,self.T(32103)): return None,None
		for n in normal:
			self.createThreadDict(n)
			n['subscribed'] = True
		return normal, pd
	
	def isThreadSubscribed(self,tid,default=False):
		if default: return True
		if not self.isLoggedIn(): return False
		normal,pd = self._getSubscriptions(1,self.fakeCallback,perpage=50) #@UnusedVariable
		for n in normal:
			if n.get('thread_id') == tid: return True
		return False
	
	def getThreads(self,forumid,page=1,callback=None,donecallback=None,page_data=None):
		if not callback: callback = self.fakeCallback
		try:
			if forumid:
				threads,pd = self._getThreads(forumid,page or 1,callback)
			else:
				threads,pd = self._getSubscriptions(page or 1,callback)
		except:
			em = ERROR('ERROR GETTING THREADS')
			callback(-1,'%s' % em)
			return self.finish(FBData(error=em),donecallback)
		
		callback(100,self.T(32052))
		return self.finish(FBData(threads,pd),donecallback)
		
	def canGetOnlineUsers(self): return True
	
	def getOnlineUsers(self,for_replies=False):
		#lets not hammer the server. Only get online user list every five minutes
		now = time.time()
		ret = []
		err = None
		if now - self.lastOnlineCheck > 300 or not for_replies:
			self.lastOnlineCheck = now
			try:
				oDict = {}
				online = self.client.online()
				if not online:
					LOG('Could not get online users: ' + online.message)
					if for_replies:
						return self.online
					else:
						return online.message
				for o in online.get('users',online.get('online_users',[])): #online_users is the documented key but not found in practice
					oDict[o.get('username','?')] = o.get('userid','?')
					ret.append({'user':unicode(o.get('username','')),'userid':o.get('userid',''),'avatar':o.get('avatarurl',''),'status':'Online'})
				self.online = oDict
				#print self.online
			except:
				err = ERROR('Error getting online users')
				
		if for_replies:
			return self.online
		else:
			if err:
				return err
			else:
				return ret
	
	def updatePost(self,post):
		result = self.client.get_post(postid=post.postId)
		if result: post.update(result)
	
	def canGetUserThreads(self): return self.isLoggedIn() and -1 or None
	
	def getUserThreads(self,uname=None,page=0,uid=None,callback=None,donecallback=None,page_data=None):
		return self.searchThreads(None, page, callback=callback, donecallback=donecallback, page_data=page_data, uname=uname, starter=True)		
	
	def canGetUserPosts(self): return self.isLoggedIn() and -1 or None
	
	def getUserPosts(self,uname=None,page=0,uid=None,callback=None,donecallback=None,page_data=None):			
		return self.searchReplies(None, page, callback=callback, donecallback=donecallback, page_data=page_data, uname=uname, starter=True)
	
	def canSearchPosts(self): return True
	def canSearchThreads(self): return True
	def canSearchAdvanced(self,stype=None):
		if stype == 'UNAME' or stype == 'FID' or stype == 'TID': return True
		return False
	
	def searchAdvanced(self,terms,page=0,sid='',callback=None,donecallback=None,page_data=None,fid=None,tid=None,uid=None,uname=None):
		if uname:
			return self.searchReplies(terms, page, sid, callback, donecallback, page_data, uname=uname)
		elif fid:
			return self.searchThreads(terms, page, sid, callback, donecallback, page_data, fid)
		elif tid:
			return self.searchReplies(terms, page, sid, callback, donecallback, page_data, tid=tid)
		
	def searchThreads(self,terms,page=0,sid='',callback=None,donecallback=None,page_data=None,fid=None,uname=None,starter=False):
		if page_data and page_data.searchID:
			result = self.client.search_searchid(searchid=page_data.searchID,page=page,perpage=20)
		else:
			if fid:
				result = self.client.search(query=terms,forumid=fid,page=page,perpage=20)
			elif starter:
				result = self.client.search(starteronly=1,searchuser=uname,page=page,perpage=20)
			else:
				result = self.client.search(query=terms,page=page,perpage=20)
		if not result.get('threads'): return self.finish(FBData(error='NO THREADS'),donecallback)
		if result['threads'][0] and 'error' in result['threads'][0]:
			return self.finish(FBData(error=result['threads'][0]['error']),donecallback)
			
		threads = []
		for t in result.get('threads'): threads.append(self.createThreadDict(t))
		total = int(result.get('total_threads',1))
		current = len(result.get('threads',[]))
		pd = self.getPageData(page=page,total_items=total,current_total=current)
		pd.searchID = result.get('searchid')
		return self.finish(FBData(threads,pd),donecallback)
		
	def searchReplies(self,terms,page=0,sid='',callback=None,donecallback=None,page_data=None,uname=None,tid=None,starter=False):
		if page_data and page_data.searchID:
			result = self.client.search_searchid(searchid=page_data.searchID,page=page,perpage=20)
		else:
			if starter:
				result = self.client.search(starteronly=1,searchuser=uname,showposts=1,page=page,perpage=20)
			elif uname:
				result = self.client.search(query=terms,searchuser=uname,showposts=1,page=page,perpage=20)
			elif tid:
				result = self.client.search(query=terms,searchthreadid=tid,showposts=1,page=page,perpage=20)
			else:
				result = self.client.search(query=terms,showposts=1,page=page,perpage=20)
		if not result.get('threads'): return self.finish(FBData(error='NO THREADS'),donecallback)
		if result['threads'][0] and 'error' in result['threads'][0]:
			return self.finish(FBData(error=result['threads'][0]['error']),donecallback)
		total = int(result.get('total_threads',1))
		current = len(result.get('threads',[]))
		pd = self.getPageData(page=page,total_items=total,current_total=current)
		pd.searchID = result.get('searchid')
		posts = []
		ct = pd.current + 1
		oDict = self.getOnlineUsers()
		profiles = {}
		for p in result.get('threads'):
			if self.isLoggedIn():
				if p.get('post_userid') in profiles:
					profile = profiles[p.get('post_userid')]
				else:
					profile = self.client.get_profile(userid=p.get('post_userid'))
					
				profiles[p.get('post_userid')] = profile
				if isinstance(profile,dict):
					profile.update(p)
					p = profile
			fp = self.getForumPost(p)
			fp.isShort = True
			fp.postNumber = ct
			fp.online = fp.userName in self.online
			for o in oDict:
				if fp.userId == o.get('userid'):
					fp.avatar = fp.avatar or o.get('avatar')
			posts.append(fp)
			ct+=1
		
		return self.finish(FBData(posts,pd),donecallback)
		
	def getReplies(self,threadid,forumid,page=1,lastid='',pid='',callback=None,donecallback=None,announcement=False,page_data=None):
		if not callback: callback = self.fakeCallback
		while True:
			try: page = int(page)
			except: page = 1
			
			if not callback(20,self.T(32102)): break
			oDict = self.getOnlineUsers(for_replies=True)
			if not callback(40,self.T(32102)): break
			try:
				sreplies = []
				if announcement:
					thread = self.client.get_announcement(forumid=threadid)
				else:
					thread = self.client.get_thread(threadid=threadid,page=page,perpage=20)
				if not thread:
					LOG('Failed to get posts (%s): %s' % (threadid,thread.message))
					callback(-1,thread.message)
					break
				posts = thread.get('posts')
				if not posts:
					callback(-1,'NO POSTS')
					return self.finish(FBData(error='NO POSTS'),donecallback)
				total = int(thread.get('total_posts',1))
				current = len(thread.get('posts',[]))
				pd = self.getPageData(page,current_total=current,total_items=total,per_page=20,is_replies=True)
				if pid:
					page = pd.getPageNumber(-1)
					thread2 = self.client.get_thread(threadid=threadid,page=page,perpage=20)
					if thread2:
						posts2 = thread2.get('posts')
						if posts2:
							posts = posts2
						else:
							LOG('Failed to get last page')
				if not callback(60,self.T(32103)): break
				ct = pd.current + 1
				for p in posts:
					fp = self.getForumPost(p)
					fp.postNumber = ct
					fp.online = fp.userName in oDict
					sreplies.append(fp)
					ct+=1
			except:
				em = ERROR('ERROR GETTING POSTS')
				callback(-1,'%s' % em)
				return self.finish(FBData(error=em),donecallback)
			
			if not callback(80,self.T(32103)): break
			
			pd.tid = threadid
			callback(100,self.T(32052))
			
			return self.finish(FBData(sreplies,pd),donecallback)
			
		return self.finish(FBData(error='CANCEL'),donecallback)
	
	def getAnnouncement(self,aid,callback=None,donecallback=None):
		return self.getReplies(aid, None, callback=callback, donecallback=donecallback,announcement=True)
	
	def getPMBoxes(self,update=True,callback_percent=5):
		if not update and self.pmBoxes: return self.pmBoxes
		if not self.hasPM(): return None
		if not self.checkLogin(callback_percent=callback_percent): return None
		result = self.client.get_pm_folders()
		if not result or result.get('folders') == None:
			LOG('Failed to get PM boxes')
			return None
		self.pmBoxes = []
		defaultSet = False
		boxes = result.get('folders')
		if not boxes: return None
		if isinstance(boxes,list): #Not sure if this is necessary because I've only gotten empty lists
			temp = boxes
			boxes = {}
			for b in temp:
				boxes[b] = b
			
		for boxid,name in boxes.items():
			box = {	'id':boxid,
					'name':name,
					'count':0,
					'unread':0,
					'type':name.upper()
			}
			if box.get('id') == 0 or box.get('type') == 'INBOX' and not defaultSet:
				box['default'] = True
				defaultSet = True
			self.pmBoxes.append(box)
		if not defaultSet and self.pmBoxes: self.pmBoxes[0]['default'] = True
		return self.pmBoxes
		
	def getPMCounts(self,callback_percent=5):
		if not self.hasPM(): return None
		if not self.checkLogin(callback_percent=callback_percent): return None
		#folders = self.client.get_pm_folders()
		#print folders
		#return None
		pms = self.client.get_pms(page=1,perpage=50)
		if not pms:
			ERROR('Failed to get PM counts')
			return None
		return {'unread':int(pms.get('unread_pms',0)),'total':int(pms.get('total_pms',0)),'boxid':'0'}
	
	def hasPM(self): return True
		
	def getPrivateMessages(self,callback=None,donecallback=None,boxid=None):
		if not callback: callback = self.fakeCallback
		
		while True:
			oDict = self.getOnlineUsers(for_replies=True)
			if not callback(30,self.T(32102)): break
			try:
				if boxid:
					messages = self.client.get_pms(folderid=boxid,page=1,perpage=50)
				else:
					messages = self.client.get_pms(page=1,perpage=50)
			except:
				em = ERROR('ERROR GETTING PRIVATE MESSAGES')
				callback(-1,'%s' % em)
				return self.finish(FBData(error=em),donecallback)
			pms = []
			if not callback(80,self.T(32103)): break
			for p in messages.get('pms',[]):
				fp = self.getForumPost(p)
				fp.isPM = True
				fp.online = fp.userName in oDict
				pms.append(fp)
			
			callback(100,self.T(32052))
			return self.finish(FBData(pms),donecallback)
		
		return self.finish(FBData(error='CANCEL'),donecallback)

	def post(self,post,callback=None):
		if post.isEdit:
			return self.editPost(post)
		LOG('Posting reply')
		if not callback: callback = self.fakeCallback
		if not self.checkLogin(callback=callback): return False
		callback(40,self.T(32106))
		result = self.client.post_reply(threadid=post.tid,message=post.message,title=post.title)
		callback(100,self.T(32052))
		if not result:
			LOG('Failed To Post: ' + result.message)
			post.error = result.message
		return bool(result)
	
	def getPostForEdit(self,post):
		pid = post.postId
		result = self.client.get_post(postid=pid)
		if not result:
			LOG('Could not get raw post for editing')
			return None
		pm = forumbrowser.PostMessage(pid,isEdit=True)
		pm.setMessage(title=result.get('title',''), message=result.get('edittext',''))
		return pm
	
	def editPost(self,pm):
		LOG('Saving edited post')
		result = self.client.post_edit(postid=pm.pid,message=pm.message,title=pm.title)
		if not result:
			LOG('Failed to edit post: ' + result.message)
			pm.error = result.message
		return bool(result)
	
	def canSubscribeThread(self,tid): return self.isLoggedIn()
	def canUnSubscribeThread(self,tid): return self.isLoggedIn()
	
	def subscribeThread(self,tid):
		if not self.checkLogin(): return False
		result = self.client.subscribe_thread(threadid=str(tid))
		if not result:
			LOG('Failed to subscribe to thread: ' + result.message)
			return result.message
		return True
	
	def unSubscribeThread(self,tid):
		if not self.checkLogin(): return False
		result = self.client.unsubscribe_thread(threadid=str(tid))
		if not result:
			LOG('Failed to unsubscribe from thread: ' + result.message)
			return result.message
		return True
		
	def canEditPost(self,user):
		if user == self.user and self.isLoggedIn(): return True
		return False
	
	def doPrivateMessage(self,post,callback=None):
		if not self.checkLogin(): return False
		result = self.client.send_pm(recipients=post.to,title=post.title,message=post.message)
		callback(100,self.T(32052))
		if not result:
			LOG('Failed to send PM: ' + result.message)
			post.error = result.message
			return False
		return True
	
	def canPost(self): return self.isLoggedIn()
	
	def canDelete(self,user,target='POST'):
		if target == 'PM' and self.isLoggedIn(): return True
		return user == self.user and self.isLoggedIn()
	
	def deletePrivateMessage(self,post,callback=None):
		if not self.checkLogin(): return False
		result = self.client.delete_pm(pm=post.pid)
		if not result:
			LOG('Failed to delete PM: ' + result.message)
			post.error = result.message
			return False
		return True
	
	def deletePost(self,post):
		if not self.checkLogin(): return False
		result = self.client.delete_post(postid=post.pid,threadid=post.tid,reason='')
		if not result:
			LOG('Failed to delete post: ' + result.message)
			post.error = result.message
			return False
		return True
	
	def canCreateThread(self,fid): return self.isLoggedIn()
	
	def createThread(self,fid,title,message):
		if not self.checkLogin(): return False
		result = self.client.post_message(forumid=str(fid),subject=title,message=message)
		if not result:
			LOG('Failed to create new thread: ' + result.message)
			return result.message
		return True
	
