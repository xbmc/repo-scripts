import sys, os
import forumbrowser, scraperbrowser, texttransform
from forumparsers import GeneralForumParser, GeneralThreadParser, GeneralPostParser
from forumbrowser import FBData

LOG = sys.modules["__main__"].LOG
ERROR = sys.modules["__main__"].ERROR
FORUMS_STATIC_PATH = sys.modules["__main__"].FORUMS_STATIC_PATH
__language__ = sys.modules["__main__"].__language__
getSetting = sys.modules["__main__"].getSetting

def testForum(url,user=None,password=None):
	if not url.startswith('http'):
		if url.startswith('/'): url = url[1:]
		url = 'http://' + url
	if not url.endswith('/'): url += '/'
	#p = GeneralForumParser()
	pb = GenericParserForumBrowser(url,url=url)
	pb.user = user
	pb.password = password
	info = forumbrowser.HTMLPageInfo(url)
	#p.getForums(info.html)
	pb.getForums()
	if pb.forumParser.isValid: return url,info,pb.forumParser
	return None,None,None

class GenericParserForumBrowser(scraperbrowser.ScraperForumBrowser):
	browserType = 'GenericParserForumBrowser'
	prefix = 'GB.' 
	
	def __init__(self,forum,always_login=False,ftype=None,url=''):
		forumbrowser.ForumBrowser.__init__(self, forum, always_login,message_converter=texttransform.BBMessageConverter)
		self.forum = forum[3:]
		self._url = url
		self.browser = None
		self.mechanize = None
		self.needsLogin = True
		self.alwaysLogin = always_login
		self.lastHTML = ''
		self.loadForumFile()
		self.forumType = 'u0'
		self.forumParser = GeneralForumParser()
		self.threadParser = GeneralThreadParser()
		self.threadParser.forumParser = self.forumParser
		self.postParser = GeneralPostParser()
		self.postParser.threadParser = self.threadParser
		
		#self.urls['base'] = url
		self.initialize()
		
	def loadForumFile(self):
		self.filters.update({	'quote':'\[QUOTE\](?P<quote>.*)\[/QUOTE\](?is)',
								'code':'\[CODE\](?P<code>.+?)\[/CODE\](?is)',
								'php':'\[PHP\](?P<php>.+?)\[/PHP\](?is)',
								'html':'\[HTML\](?P<html>.+?)\[/HTML\](?is)',
								'image':'\[img\](?P<url>[^\[]+)\[/img\](?is)',
								'link':'\[url="?(?P<url>[^\]]+?)"?\](?P<text>.*?)\[/url\](?is)',
								'link2':'\[url\](?P<text>(?P<url>.+?))\[/url\](?is)',
								'post_link':'(?:showpost.php|showthread.php)\?[^<>"]*?tid=(?P<threadid>\d+)[^<>"]*?pid=(?P<postid>\d+)',
								'thread_link':'showthread.php\?[^<>"]*?tid=(?P<threadid>\d+)',
								'color_start':'\[color=?#?(?P<color>\w+)\]'
								})
				
		forum = self.getForumID()
		fname = os.path.join(sys.modules["__main__"].FORUMS_PATH,forum)
		if not os.path.exists(fname):
			fname = os.path.join(sys.modules["__main__"].FORUMS_STATIC_PATH,forum)
			if not os.path.exists(fname): return False
		self.loadForumData(fname)
		self._url = self.urls.get('server',self._url)
		self.formats['quote'] = ''
		
	def getForumID(self):
		return 'GB.' + self.getDisplayName()
	
	def getDisplayName(self):
		return self.forum
		#name = self._url.split('://')[-1].split('/')[0]
		#if name.startswith('www.'): name = name[4:]
		#return name
	
	def getForumType(self):
		return self.forumType
	
	def getForumInfo(self):
		return [	('name',self.getDisplayName()),
					('interface','Parser Browser'),
					('forum_type',self.forumParser.getForumTypeName()),
					('login_set',self.canLogin()),
					('can_post',self.canPost()),
					('can_edit_posts',self.canEditPost(self.user)),
					('can_delete_posts',self.canDelete(self.user)),
					('can_view_private_messages',self.hasPM()),
					('can_view_subscriptions',self.hasSubscriptions()),
					('can_subscribe',self.canSubscribeForum(None)),
					('can_send_private_messages',self.canPrivateMessage()),
					('can_delete_private_messages',self.canDelete(self.user,target='PM')),
				]
	
	def loadForumData(self,forum):
		self.needsLogin = True
		fname = os.path.join(FORUMS_STATIC_PATH,forum)
		if not os.path.exists(fname): fname = forum
		if not os.path.exists(fname): return False
		return forumbrowser.ForumBrowser.parseForumData(self, fname)
	
	def isLoggedIn(self):
		if self.forms.get('login_action'):
			return scraperbrowser.ScraperForumBrowser.isLoggedIn(self)
		else:
			return False
	
	def getQuoteStartFormat(self):
		forumType = self.getForumType()
		if forumType:
			return self.quoteStartFormats.get(forumType,'(?i)\[QUOTE[^\]]*?\]')
		else:
			return scraperbrowser.ScraperForumBrowser.getQuoteStartFormat(self)
	
	def doLoadForumData(self):
		path = os.path.join(FORUMS_STATIC_PATH,'general',self.forumParser.getForumType())
		self.loadForumData(path)
			
	def getForums(self,callback=None,donecallback=None,url='',html='',subs=False):
		if not callback: callback = self.fakeCallback
		#if html: self.lastHTML = html #TODO: Maybe put this back
		if not html:
			try:
				url = url or self._url
				LOG('Forums List URL: ' + url)
				html = self.readURL(url,callback=callback,force_browser=True)
			except:
				em = ERROR('ERROR GETTING FORUMS')
				callback(-1,'%s' % em)
				return self.finish(FBData(error=em or 'ERROR'),donecallback)
		
		if not html or not callback(80,__language__(30103)):
			return self.finish(FBData(error=html and 'CANCEL' or 'EMPTY HTML'),donecallback)
		
		forums = self.forumParser.getForums(html)
		LOG('Detected Forum Type: ' + self.forumParser.forumType)
		self.forumType = self.forumParser.forumType
		self.MC.resetRegex()
		self.doLoadForumData()
		self.checkLogin(callback)
		if not forums and self.isLoggedIn():
			try:
				html = self.readURL(url,callback=callback,force_browser=True)
			except:
				em = ERROR('ERROR GETTING FORUMS')
				callback(-1,'%s' % em)
				return self.finish(FBData(error=em or 'ERROR'),donecallback)
			forums = self.forumParser.getForums(html)
		for f in forums:
			f['subscribed'] = subs
			f['is_forum'] = True
		
		#logo = self.getLogo(html)
		logo = self.urls.get('logo') or 'http://%s/favicon.ico' % self.domain()
		#pm_counts = self.getPMCounts(html)
		pm_counts = None
		callback(100,__language__(30052))
		
		return self.finish(FBData(forums,extra={'logo':logo,'pm_counts':pm_counts}),donecallback)
	
	def getThreads(self,forumid,page='',callback=None,donecallback=None,url=None,subs=False,page_data=None):
		if not callback: callback = self.fakeCallback
		pagesURL = url
		if self.forumParser.isGeneric:
			for f in self.forumParser.forums:
				if forumid == f.get('forumid'):
					url = f.get('url')
					if not url: break
					if not url.startswith('http'):
						if url.startswith('/'): url = url[1:]
						url = self._url + url
					break
			pagesURL = url
			if page and not str(page).isdigit(): url = self._url + page
		if not url: url = self.getPageUrl(page,'threads',fid=forumid)
		LOG('Forum URL: ' + url)
		html = self.readURL(url,callback=callback,force_browser=True)
		if not html or not callback(80,__language__(30103)):
			return self.finish(FBData(error=html and 'CANCEL' or 'EMPTY HTML'),donecallback)
		threads = self.threadParser.getThreads(html,pagesURL)
		LOG('Detected Threads Type: ' + self.threadParser.forumType)
		#forums = self.forumParser.getList(html,in_threads=True)
		try:
			newfid = self.forumParser.linkRE.search(self.lastURL.rsplit('/',1)[-1]).groupdict().get('id')
			extra = newfid and {'newforumid':newfid} or None
		except:
			extra = None
		#if forums: extra = {'forums':forums}
		if subs:
			for t in threads: t['subscribed'] = True
		callback(100,__language__(30052))
		pd = self.getPageInfo(html,page,page_type='threads',page_urls=self.threadParser.pages,page_data=page_data)
		if self.threadParser.getForumType() == 'u0': pd.useURLs = True
		return self.finish(FBData(threads,pd,extra=extra),donecallback)
	
	def getSubscriptionSub(self):
		urls = self.urls.get('subscriptions','').split('|')
		for u in urls:
			#print u
			if u in self.lastHTML: return u
		return None

	def getSubscriptions(self,page='',callback=None,donecallback=None,page_data=None):
		if self.forumParser.isGeneric:
			#import codecs
			#codecs.open('/home/ruuk/test.txt','w','utf8').write(self.lastHTML.decode('utf8'))
			sub = self.getSubscriptionSub()
			if sub:
				url = self.getPageUrl(page,'subscriptions',suburl=sub)
			else:
				return self.finish(FBData(error='Generic Browser: Could not find subscriptions :('),donecallback)
		else:
			url = self.getPageUrl(page,'subscriptions')
		url2 = self.getPageUrl(page,'forum_subscriptions')
		data = self.getThreads(None, page,url=url,subs=True)
		if url2:
			html = ''
			if url2 == url: html = self.lastHTML
			forums = self.getForums(url=url2,html=html,subs=True)
			data.extra['forums'] = forums.data
		return self.finish(data, donecallback)
	
	def getReplies(self,threadid,forumid,page='',lastid='',pid='',callback=None,donecallback=None,page_data=None):
		if not callback: callback = self.fakeCallback
		url = None
		pagesURL = url
		self.postParser.ignoreForumImages = getSetting('ignore_forum_images',True)
		self.postParser.setDomain(self._url)
		if self.threadParser.isGeneric:
			for f in self.threadParser.threads:
				if threadid == f.get('threadid'):
					url = f.get('url')
					if not url: break
					if not url.startswith('http'):
						if url.startswith('/'): url = url[1:]
						url = self._url + url
					break
			pagesURL = url
			if page and not str(page).replace('-','').isdigit(): url = self._url + page
		if not url: url = self.getPageUrl(page,'replies',tid=threadid,fid=forumid,lastid=lastid,pid=pid)
		LOG('Thread URL: ' + url)
		html = self.readURL(url,callback=callback,force_browser=True)
		if not html or not callback(80,__language__(30103)):
			return self.finish(FBData(error=html and 'CANCEL' or 'EMPTY HTML'),donecallback)
		replies = self.postParser.getPosts(html,pagesURL,callback=callback,filters=self.filters,page_url=url)
		LOG('Detected Posts Type: ' + self.postParser.forumType)
		#topic = re.search(self.filters.get('thread_topic','%#@+%#@'),html)
		#if not threadid:
		#	threadid = re.search(self.filters.get('thread_id','%#@+%#@'),html)
		#	threadid = threadid and threadid.group(1) or ''
		#topic = topic and topic.group(1) or ''
		sreplies = []
		for r in replies:
			try:
				post = self.getForumPost(r)
				post.tid = threadid
				post.fid = forumid
				#print post.message.encode('ascii','replace')
				sreplies.append(post)
			except:
				ERROR('ERROR CREATING POST - Using blank post')
				post = self.getForumPost()
				sreplies.append(post)
		pd = self.getPageInfo(html,page,page_type='replies',page_urls=self.postParser.pages)
		if pd: pd.setThreadData('',threadid)
		
		try:
			newtid = self.threadParser.linkRE.search(self.lastURL.rsplit('/',1)[-1]).groupdict().get('id')
			extra = newtid and {'newthreadid':newtid} or None
		except:
			extra = None
			
		callback(100,__language__(30052))
		
		return self.finish(FBData(sreplies,pd,extra=extra),donecallback)
	
	def hasSubscriptions(self):
		if self.forumParser.isGeneric:
			return bool(self.getSubscriptionSub() and scraperbrowser.ScraperForumBrowser.hasSubscriptions(self))
		else:
			return scraperbrowser.ScraperForumBrowser.hasSubscriptions(self)
		
	def subscribeThread(self,tid):
		url = self.urls.get('subscribe_thread').replace('!THREADID!',tid)
		try:
			if self.doForm(url,action_match=self.forms.get('subscribe_thread_action','subs'),controls='subscribe_notification_control%s'):
				return True
			else:
				return 'Reason Unknown'
			#TODO: check for success = perhaps look for exec_refresh()
		except:
			return ERROR('Failed to subscribe to thread: ' + tid)
		
	def unSubscribeThread(self, tid):
		url = self.urls.get('unsubscribe_thread').replace('!THREADID!',tid)
		try:
			self.readURL(url, force_login=True,is_html=False) #is_html=False because otherwise breaks login status
			#TODO: check for success = perhaps look for exec_refresh()
			return True
		except:
			return ERROR('Failed to unsubscribe from thread: ' + tid)
		
	def subscribeForum(self, fid):
		url = self.urls.get('subscribe_forum').replace('!FORUMID!',fid)
		try:
			
			if self.doForm(url,action_match=self.forms.get('subscribe_forum_action','subs'),controls='subscribe_forum_notification_control%s'):
				return True
			else:
				return 'Reason Unknown'
			#TODO: check for success = perhaps look for exec_refresh()
		except:
			return ERROR('Failed to subscribe to forum: ' + fid)
		
	def unSubscribeForum(self, fid):
		url = self.urls.get('unsubscribe_forum').replace('!FORUMID!',fid)
		try:
			self.readURL(url, force_login=True,is_html=False) #is_html=False because otherwise breaks login status
			#TODO: check for success = perhaps look for exec_refresh()
			return True
		except:
			return ERROR('Failed to unsubscribe from forum: ' + fid)
		
	def canSubscribeThread(self, tid): return bool(self.urls.get('subscribe_thread') and self.isLoggedIn())
	
	def canSubscribeForum(self, fid): return bool(self.urls.get('subscribe_forum') and self.isLoggedIn())
	
	def canUnSubscribeThread(self,tid): return bool(self.urls.get('unsubscribe_thread') and self.isLoggedIn())
	
	def canUnSubscribeForum(self,fid): return bool(self.urls.get('unsubscribe_forum') and self.isLoggedIn())
		
	def isThreadSubscribed(self,tid,default=False):
		if not self.canSubscribeThread(tid): return default
		if default: return True
		url = self.getPageUrl('','subscriptions')
		data = self.getThreads(None, '',url=url,subs=True)
		for d in data.data:
			if d.get('threadid') == tid: return True
		return False
	
	def isForumSubscribed(self,fid,default=False):
		if not self.canSubscribeForum(fid): return default
		if default: return True
		url2 = self.getPageUrl('','forum_subscriptions')
		if not url2: return default
		data = self.getForums(url=url2,subs=True)
		for d in data.data:
			if d.get('forumid') == fid: return True
		return False
	

	