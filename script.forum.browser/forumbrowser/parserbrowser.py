import sys, re
import forumbrowser, scraperbrowser, texttransform
from forumparsers import VBForumParser,VBThreadParser, VBPostParser
from forumbrowser import FBData

ERROR = sys.modules["__main__"].ERROR
__language__ = sys.modules["__main__"].__language__

class ForumPost(scraperbrowser.ForumPost):
	def messageAsQuote(self):
		qr = self.FB.getQuoteReplace()
		return qr.replace('!QUOTE!',self.message).replace('!USER!',self.userName).replace('!POSTID!',self.postId)
	
class ParserForumBrowser(scraperbrowser.ScraperForumBrowser):
	ForumPost = ForumPost
	browserType = 'ParserForumBrowser'
	parsers = 	{	'vb':	{	'forums':VBForumParser,
								'threads':VBThreadParser,
								'posts':VBPostParser,
								'pmcountsre':r'class="notifications-number">.{,10}?>(\d+)',
								'filters':{	'quote':'\[QUOTE\](?P<quote>.*)\[/QUOTE\](?is)',
											'code':'\[CODE\](?P<code>.+?)\[/CODE\](?is)',
											'php':'\[PHP\](?P<php>.+?)\[/PHP\](?is)',
											'html':'\[HTML\](?P<html>.+?)\[/HTML\](?is)',
											'image':'\[img\](?P<url>[^\[]+)\[/img\](?is)',
											'link':'\[url="?(?P<url>[^\]]+?)"?\](?P<text>.*?)\[/url\](?is)',
											'link2':'\[url\](?P<text>(?P<url>.+?))\[/url\](?is)',
											'post_link':'(?:showpost.php|showthread.php)\?[^<>"]*?tid=(?P<threadid>\d+)[^<>"]*?pid=(?P<postid>\d+)',
											'thread_link':'showthread.php\?[^<>"]*?tid=(?P<threadid>\d+)',
											'color_start':'\[color=?#?(?P<color>\w+)\]'
											}
							}
				}
	
	def __init__(self,forum,always_login=False,ftype=None):
		forumbrowser.ForumBrowser.__init__(self, forum, always_login, texttransform.BBMessageConverter)
		self.forum = forum
		self._url = ''
		self.browser = None
		self.mechanize = None
		self.needsLogin = True
		self.alwaysLogin = always_login
		self.lastHTML = ''
		self.reloadForumData(forum)
		if not ftype: ftype = self.formats.get('forum_type')
		self.forumType = ftype or ''
		parser = self.parsers.get(ftype,{})
		fp = parser.get('forums')
		self.forumParser = fp and fp() or None
		tp = parser.get('threads')
		self.threadParser = tp and tp() or None
		pp = parser.get('posts')
		self.postParser = pp and pp() or None
		self.pmCountsRE = parser.get('pmcountsre')
		self.filters.update(parser.get('filters',{}))
		self.initialize()
		
	def getForumType(self):
		return self.forumType
	
	def getQuoteStartFormat(self):
		forumType = self.getForumType()
		if forumType:
			return self.quoteStartFormats.get(forumType,'(?i)\[QUOTE[^\]]*?\]')
		else:
			return scraperbrowser.ScraperForumBrowser.getQuoteStartFormat(self)
	
	def getPMCounts(self,html=None):
		if not self.pmCountsRE: return scraperbrowser.ScraperForumBrowser.getPMCounts(self, html)
		self.checkLogin()
		if not html: html = self.lastHTML
		if not html: return None
		m = re.search(self.pmCountsRE,html)
		if not m: return {'unread':'?'}
		return {'unread':m.group(1)}
	
	def getForums(self,callback=None,donecallback=None,url='',subs=False):
		if not self.forumParser: return scraperbrowser.ScraperForumBrowser.getForums(self, callback, donecallback)
		if not callback: callback = self.fakeCallback
		try:
			self.checkLogin()
			html = self.readURL(url or self.getURL('forums'),callback=callback)
		except:
			em = ERROR('ERROR GETTING FORUMS')
			callback(-1,'%s' % em)
			return self.finish(FBData(error=em or 'ERROR'),donecallback)
		
		if not html or not callback(80,__language__(30103)):
			return self.finish(FBData(error=html and 'CANCEL' or 'EMPTY HTML'),donecallback)
		
		forums = self.forumParser.getList(html)
		for f in forums:
			f['subscribed'] = subs
			f['is_forum'] = True
		
		logo = self.getLogo(html)
		pm_counts = self.getPMCounts(html)
		callback(100,__language__(30052))
		
		return self.finish(FBData(forums,extra={'logo':logo,'pm_counts':pm_counts}),donecallback)

	def getThreads(self,forumid,page='',callback=None,donecallback=None,url=None,subs=False):
		if not self.threadParser: return scraperbrowser.ScraperForumBrowser.getThreads(self, forumid, page, callback, donecallback)
		if not callback: callback = self.fakeCallback
		if url:
			forceLogin = True
		else:
			url = self.getPageUrl(page,'threads',fid=forumid)
			forceLogin = False
		html = self.readURL(url,callback=callback,force_login=forceLogin)
		if not html or not callback(80,__language__(30103)):
			return self.finish(FBData(error=html and 'CANCEL' or 'EMPTY HTML'),donecallback)
		if self.filters.get('threads_start_after'): html = html.split(self.filters.get('threads_start_after'),1)[-1]
		threads = self.threadParser.getList(html)
		forums = self.forumParser.getList(html,in_threads=True)
		extra = None
		if forums: extra = {'forums':forums}
		if subs:
			for t in threads: t['subscribed'] = True
		callback(100,__language__(30052))
		pd = self.getPageInfo(html,page,page_type='threads')
		return self.finish(FBData(threads,pd,extra=extra),donecallback)
		
	def getSubscriptions(self,page='',callback=None,donecallback=None):
		url = self.getPageUrl(page,'subscriptions')
		url2 = self.getPageUrl(page,'forum_subscriptions')
		data = self.getThreads(None, page,url=url,subs=True)
		forums = self.getForums(url=url2,subs=True)
		data.extra['forums'] = forums.data
		return self.finish(data, donecallback)
		
		
	def getReplies(self,threadid,forumid,page='',lastid='',pid='',callback=None,donecallback=None):
		if not self.postParser: return scraperbrowser.ScraperForumBrowser.getReplies(self, threadid, forumid, page, lastid, pid, callback, donecallback)
		if not callback: callback = self.fakeCallback
		url = self.getPageUrl(page,'replies',tid=threadid,fid=forumid,lastid=lastid,pid=pid)
		html = self.readURL(url,callback=callback)
		if not html or not callback(80,__language__(30103)):
			return self.finish(FBData(error=html and 'CANCEL' or 'EMPTY HTML'),donecallback)
		replies = self.postParser.getList(html)
		topic = re.search(self.filters.get('thread_topic','%#@+%#@'),html)
		if not threadid:
			threadid = re.search(self.filters.get('thread_id','%#@+%#@'),html)
			threadid = threadid and threadid.group(1) or ''
		topic = topic and topic.group(1) or ''
		sreplies = []
		for r in replies:
			post = self.getForumPost(pdict=r)
			sreplies.append(post)
		pd = self.getPageInfo(html,page,page_type='replies')
		pd.setThreadData(topic,threadid)
		callback(100,__language__(30052))
		
		return self.finish(FBData(sreplies,pd),donecallback)
	
	def subscribeThread(self,tid):
		url = 'http://forums.boxee.tv/subscription.php?do=addsubscription&t=' + tid
		try:
			self.doForm(url,action_match='subscription.php?do=doaddsubscription',controls='subscribe_notification_control%s')
			#TODO: check for success = perhaps look for exec_refresh()
			return True
		except:
			return ERROR('Failed to subscribe to thread: ' + tid)
		
	def unSubscribeThread(self, tid):
		url = 'http://forums.boxee.tv/subscription.php?do=removesubscription&t=' + tid
		try:
			self.readURL(url, force_login=True)
			#TODO: check for success = perhaps look for exec_refresh()
			return True
		except:
			return ERROR('Failed to unsubscribe from thread: ' + tid)
		
	def subscribeForum(self, fid):
		url = 'http://forums.boxee.tv/subscription.php?do=addsubscription&f=' + fid
		try:
			self.doForm(url,action_match='subscription.php?do=doaddsubscription',controls='subscribe_forum_notification_control%s')
			#TODO: check for success = perhaps look for exec_refresh()
			return True
		except:
			return ERROR('Failed to subscribe to forum: ' + fid)
		
	def unSubscribeForum(self, fid):
		url = 'http://forums.boxee.tv/subscription.php?do=removesubscription&f=' + fid
		try:
			self.readURL(url, force_login=True)
			#TODO: check for success = perhaps look for exec_refresh()
			return True
		except:
			return ERROR('Failed to unsubscribe from forum: ' + fid)
		
	def canSubscribeThread(self, tid): return True
	
	def canSubscribeForum(self, fid): return True
	