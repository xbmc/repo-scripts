import sys, os
import forumbrowser, scraperbrowser, texttransform
from forumparsers import GeneralForumParser, GeneralThreadParser, GeneralPostParser
from forumbrowser import FBData

LOG = sys.modules["__main__"].LOG
ERROR = sys.modules["__main__"].ERROR
FORUMS_STATIC_PATH = sys.modules["__main__"].FORUMS_STATIC_PATH
__language__ = sys.modules["__main__"].__language__

	
class GenericParserForumBrowser(scraperbrowser.ScraperForumBrowser):
	browserType = 'GenericParserForumBrowser'
	
	def __init__(self,forum,always_login=False,ftype=None,url=''):
		forumbrowser.ForumBrowser.__init__(self, forum, always_login,message_converter=texttransform.BBMessageConverter)
		self.forum = 'general'
		self._url = url
		self.browser = None
		self.mechanize = None
		self.needsLogin = True
		self.alwaysLogin = always_login
		self.lastHTML = ''
		#self.reloadForumData(forum)
		self.forumType = 'u0'
		self.forumParser = GeneralForumParser()
		self.threadParser = GeneralThreadParser()
		self.threadParser.forumParser = self.forumParser
		self.postParser = GeneralPostParser()
		self.postParser.threadParser = self.threadParser
		self.urls = {}
		self.filters = {}
		self.forms = {}
		self.formats = {}
		
		self.urls['base'] = url
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
		self.initialize()
		
	def getForumID(self):
		return 'GB.' + self.getDisplayName()
	
	def getDisplayName(self):
		name = self._url.split('://')[-1].split('/')[0]
		if name.startswith('www.'): name = name[4:]
		return name
	
	def getForumType(self):
		return self.forumType
	
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
		if not html:
			try:
				url = url or self.urls.get('base','')
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
		logo = 'http://%s/favicon.ico' % self.urls.get('base','').split('://')[-1].split('/')[0]
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
		replies = self.postParser.getPosts(html,pagesURL,callback=callback)
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
		
	def subscribeThread(self,tid): return False
		
	def unSubscribeThread(self, tid): return False
		
	def subscribeForum(self, fid): return False
		
	def unSubscribeForum(self, fid): return False
		
	def canSubscribeThread(self, tid): return False
	
	def canSubscribeForum(self, fid): return False
	