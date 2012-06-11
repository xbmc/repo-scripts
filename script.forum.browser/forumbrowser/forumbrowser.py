#Forum browser common
import sys, re, urllib, urllib2, texttransform

def LOG(message):
	print 'FORUMBROWSER: %s' % message

def ERROR(message):
	LOG('ERROR: ' + message)
	import traceback #@Reimport
	traceback.print_exc()
	return str(sys.exc_info()[1])

class Error(Exception): pass

class FBData():
	def __init__(self,data=None,pagedata=None,extra=None,error=None):
		self.data = data
		self.pageData = pagedata
		self.extra = extra or {}
		self.error = error
	
	def __getitem__(self,key):
		return self.extra.get(key)
	
	def __setitem__(self,key,value):
		self.extra[key] = value
	
	def __contains__(self,key):
		return key in self.extra
	
	def getExtra(self,key,default=None):
		return self.extra.get(key,default)
	
	def setExtra(self,key,value):
		self.extra[key] = value
			
	def setError(self,message):
		self.error = message
		
	def __nonzero__(self):
		return not self.error
	
class FBOnlineDatabase():
	def __init__(self):
		self.url = 'http://xbmc.2ndmind.net/forumbrowser/tapatalk.php'
	
	def postData(self,**data):
		enc = urllib.urlencode(data)
		try:
			result = urllib2.urlopen(self.url,enc).read()
			return result
		except:
			err = ERROR('FBTTOnlineDatabase.postData()')
			return 'ERROR: ' + err
			
	def addForum(self,name,url,logo='',desc='',ftype='TT'):
		return self.postData(do='add',name=name,url=url,desc=desc,logo=logo,type=ftype)
		
	def getForumList(self):
		flist = self.postData(do='list')
		if not flist: return None
		flist = flist.split('\n')
		final = []
		for f in flist:
			if f:
				name, rest = f.split('=',1)
				url,desc,logo,ftype = rest.split('\r',3)
				final.append({'name':name,'url':url,'desc':desc,'logo':logo,'type':ftype})
		return final

class HTMLPageInfo:
	def __init__(self,url,html=''):
		self.url = url
		
		self.base = url
		if not self.base.endswith('/'): self.base += '/'
		
		base2 = 'http://' + url.rsplit('://',1)[-1].split('/',1)[0]
		self.base2 = base2
		self.base2 += '/'
		
		self.isValid = True
		if html:
			self.html = html
			self.html2 = html
		else:
			self._getHTML()
		
	def _getHTML(self):
		try:
			self.html = self.getHTML(self.url)
		except:
			self.isValid = False
			LOG('HTMLPageInfo 1: FAILED')
			
		if self.url == self.base2: return
		
		try:
			self.html2 = self.getHTML(self.base2)
			self.isValid = True
		except:
			LOG('HTMLPageInfo 2: FAILED')
		
	def getHTML(self,url):
		opener = urllib2.build_opener()
		o = opener.open(urllib2.Request(url,None,{'User-Agent':'Wget/1.12'}))
		html = o.read()
		o.close()
		return html
			
	def title(self,default=''):
		try: return re.search('<title>(.*?)</title>',self.html).group(1) or ''
		except: pass
		try: return re.search('<title>(.*?)</title>',self.html2).group(1) or ''
		except: pass
		return ''
		
		
	def description(self,default=''):
		try: return re.search('<meta[^>]*?name="description"[^>]*?content="([^"]*?)"',self.html).group(1)
		except: pass
		try: return re.search('<meta[^>]*?name="description"[^>]*?content="([^"]*?)"',self.html2).group(1)
		except: pass
		return default
		
	def images(self):
		images = self._images(self.html, self.base)
		images2 = self._images(self.html2, self.base2)
		images3 = self.getStyleImages(self.html, self.base)
		images4 = self.getStyleImages(self.html2, self.base2)
		for i in images2 + images3 + images4:
			if not i in images: images.append(i)
		return images
	
	def pageImages(self):
		return self._images(self.html, self.base)
			
	def baseImages(self):
		return self._images(self.html2, self.base2)
		
	def _images(self,html,base):
		urlList = re.findall('<img[^>]*?src="([^"]+?)"[^>]*?>',html) #Image tags
		urlList2 = re.findall('<meta[^>]*?property="[^"]*image"[^>]*?content="([^"]*?)"',html) #Meta tag images
		final = []
		for u in urlList + urlList2:
			u = self.fullURL(u, base)
			if u in final: continue
			if u:
				final.append(u)
		return final

	def getStyleImages(self,html,base):
		styles = ''
		for url in re.findall('<link[^>]*?href="(?P<url>[^"]*?)"[^>]*?"text/css"[^>]*?>',html) + re.findall('<link[^>]*?"text/css"[^>]*?href="(?P<url>[^"]*?)"[^>]*?>',html):
			#print url
			url = self.fullURL(url, base)
			try:
				styles += self.getHTML(url)
			except:
				LOG('Failed to get stylesheet')
		urls = []
		for url in re.findall("background(?:-image)?:[^\(]+?url\(['\"](?P<url>[^\"']+?)['\"]\)",styles):
			urls.append(self.fullURL(url, base))
		#print urls
		return urls
	
	def fullURL(self,u,base):
		u = u.strip()
		if u.startswith('http'):
			pass
		elif u.startswith('./') or u.startswith('../'):
			u = base + u[2:]
		elif u.startswith('.'):
			u = base + u[1:]
		elif u.startswith('/'):
			u = self.base2 + u[1:]
		else:
			u = base + u
		return u
	
################################################################################
# Action
################################################################################
class Action:
	def __init__(self,action=''):
		self.action = action

class PMLink:
	linkImageFilter = re.compile('https?://.+?\.(?:jpg|png|gif|bmp)$')
	def __init__(self,fb,match=None):
		self.FB = fb
		self.MC = fb.MC
		self.url = ''
		self.text = ''
		self.pid = ''
		self.tid = ''
		self.fid = ''
		self._isImage = False
		self._textIsImage = False
		
		if match:
			self.url = match.group('url').strip()
			text = match.group('text')
			self.text = self.MC.tagFilter.sub('',text).strip()
		self.processURL()
		self.processText()
			
	def processURL(self):
		if not self.url: return
		self._isImage = self.linkImageFilter.search(self.url) and True or False
		if self._isImage: return
		pm = re.search(self.FB.filters.get('post_link','@`%#@>-'),self.url)
		tm = re.search(self.FB.filters.get('thread_link','@`%#@>-'),self.url)
		if pm:
			d = pm.groupdict()
			self.pid = d.get('postid','')
			self.tid = d.get('threadid','')
		elif tm:
			d = tm.groupdict()
			self.tid = d.get('threadid','')
			
	def processText(self):
		m = self.MC.imageFilter.search(self.text)
		if m:
			self._textIsImage = True
			self.text = m.groupdict().get('url',self.text)
			
	def urlShow(self):
		if self.isPost(): return 'Post ID: %s' % self.pid
		elif self.isThread(): return 'Thread ID: %s' % self.tid
		return self.url
		
	def isImage(self):
		return self._isImage
	
	def textIsImage(self):
		return self._textIsImage
		
	def isPost(self):
		return self.pid and True or False
		
	def isThread(self):
		return self.tid and not self.pid
		
################################################################################
# PostMessage
################################################################################
class PostMessage(Action):
	def __init__(self,pid='',tid='',fid='',title='',message='',is_pm=False,isEdit=False):
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
		self.isEdit = isEdit
		self.error = ''
		self.tagFilter = re.compile('<[^<>]+?>',re.S)
		
	def setQuote(self,user,quote):
		self.quser = self.tagFilter.sub('',user)
		self.quote = quote
		
	def setMessage(self,title,message):
		self.title = title
		self.message = message
		
	def fromPost(self,post):
		self.pid = post.postId
		self.tid = post.tid
		self.fid = post.fid
		self.message = post.message
		self.title = post.title
		return self

################################################################################
# PageData
################################################################################
class PageData:
	def __init__(self,fb,page=1,current=0,per_page=20,total_items=0,current_total=0,is_replies=False):
		self.current = current
		
		self.totalitems = total_items
		self.totalPages = int(self.totalitems / per_page)
		self.totalPages += (self.totalitems % per_page) and 1 or 0 
		
		if current > 0:
			self.pageMode= False
			self.page = int((current + 1) / per_page) + 1
			self.nextStart = current + current_total
			ps = current - per_page
			if ps < 0: ps = 0
			self.prevStart = ps
			self.prev = current > 0
		else:
			self.pageMode = True
			if page < 0: page = self.totalPages
			if page == 0: page = 1
			self.page = page
			current = (page - 1) * per_page
			self.nextStart = page + 1
			ps = page -1
			if ps < 1: ps = 1
			self.prevStart = ps
			self.prev = page > 1
			
		self.next = current + per_page < self.totalitems
			
		self.perPage = per_page
		self.prev = current > 0 or page > 1
		self.next = current + per_page < self.totalitems
		self.pageDisplay = ''
		self.topic = ''
		self.tid = ''
		self.isReplies = is_replies
	
	def getPageNumber(self,page=None):
		if page == None: page = self.page
		try:
			page = int(page)
		except:
			page = 0
		if page <= 0:
			if self.isReplies:
				#ret = self.totalitems - self.perPage
				#if ret < 0: ret = 0
				#return ret
				page = self.totalPages
			else:
				return self.totalPages or 0
		if page > self.totalPages: page = self.totalPages
		if self.pageMode: return page
		return int((page - 1) * self.perPage)
						
	def getNextPage(self):
		return self.nextStart
			
	def getPrevPage(self):
		return self.prevStart
				
	def getPageDisplay(self):
		if self.pageDisplay: return self.pageDisplay
		if self.page is not None and self.totalPages is not None:
			total  = self.totalPages or 1
			return 'Page %s of %s' % (self.page,total)

################################################################################
# ForumPost
################################################################################
class ForumPost:
	def __init__(self,fb,pdict=None):
		self.FB = fb
		self.MC = fb.MC
		self.to = ''
		self.isShort = False
		self.isRaw = False
		self.isPM = False
		self.postId = ''
		self.date = ''
		self.userId = ''
		self.userName = ''
		self.avatar = ''
		self.status = ''
		self.title = ''
		self.message = ''
		self.signature = ''
		self.pid = ''
		self.translated = ''
		self.avatarFinal = ''
		self.tid = ''
		self.fid = ''
		self.boxid = ''
		self.status = ''
		self.activity = ''
		self.online = False
		self.postCount = 0
		self.postNumber = 0
		self.joinDate = ''
		self.userInfo = {}
		self.extras = {}
		if pdict: self.setVals(pdict)
			
	def setVals(self,pdict): pass
		
	def messageType(self):
		return self.isPM and 'PM' or 'POST'
		
	def setUserInfo(self,info): pass
		
	def setPostID(self,pid):
		self.postId = pid
		self.pid = pid
		self.isPM = pid.startswith('PM')
	
	def getID(self):
		if self.pid.startswith('PM'): return self.pid[2:]
		return self.pid
		
	def getShortMessage(self):
		return self.getMessage(True)
	
	def getMessage(self,skip=False,raw=False):
		return self.message + self.signature
	
	def messageAsText(self):
		return sys.modules["__main__"].messageToText(self.getMessage())
		
	def messageAsDisplay(self,short=False,raw=False):
		if short:
			message = self.getShortMessage()
		else:
			message = self.getMessage(raw=raw)
		message = message.replace('\n','[CR]')
		message = re.sub('\[(/?)b\]',r'[\1B]',message)
		message = re.sub('\[(/?)i\]',r'[\1I]',message)
		return self.messageToDisplay(message)
		
	def messageToDisplay(self,message): return message
	
	def messageAsQuote(self): return ''
		
	def imageURLs(self): return []
		
	def linkImageURLs(self): return []
		
	def linkURLs(self): return []
	
	def link2URLs(self): return []
		
	def links(self):
		links = []
		for m in self.linkURLs(): links.append(self.FB.getPMLink(m))
		for m in self.link2URLs(): links.append(self.FB.getPMLink(m))
		return links
		
	def makeAvatarURL(self): return self.avatar
	
	def cleanUserName(self): return self.userName
			
######################################################################################
# Forum Browser API
######################################################################################
class ForumBrowser:
	browserType = 'ForumBrowser'
	ForumPost = ForumPost
	PMLink = PMLink
	PageData = PageData
	quoteFormats = 	{	'mb':"(?s)\[quote='(?P<user>[^']*?)' pid='(?P<pid>[^']*?)' dateline='(?P<date>[^']*?)'\](?P<quote>.*)\[/quote\]",
						'xf':'(?s)\[quote="(?P<user>[^"]*?), post: (?P<pid>[^"]*?), member: (?P<uid>[^"]*?)"\](?P<quote>.*)\[/quote\]',
						'vb':'\[QUOTE=(?P<user>[^;\]]+)(?:;\d+)*\](?P<quote>.+?)\[/QUOTE\](?is)',
						'pb':'\[quote(?:="(?P<user>[^"]+?)")?\](?P<quote>.+?)\[/quote\](?is)'
					}
	
	quoteStartFormats = {	'mb':"(?i)\[quote(?:\='?(?P<user>[^']*?)'?(?: pid='(?P<pid>[^']*?)')?(?: dateline='(?P<date>[^']*?)')?)?\]",
							'xf':'(?i)\[quote(?:\="(?P<user>[^"]*?), post: (?P<pid>[^"]*?), member: (?P<uid>[^"]*?)")?\]',
							'vb':'(?i)\[quote(?:\=(?P<user>[^;\]]+)(?:;\d+)*)?\]',
							'pb':'\[quote(?:="(?P<user>[^"]+?)")?\](?is)'
						}
	
	quoteReplace = 	{	'mb':"[quote='!USER!' pid='!POSTID!' dateline='!DATE!']!QUOTE![/quote]",
						'xf':'[quote="!USER!, post: !POSTID!, member: !USERID!"]!QUOTE![/quote]',
						'vb':'[QUOTE=!USER!;!POSTID!]!QUOTE![/QUOTE]',
						'pb':'[quote="!USER!"]!QUOTE![/quote]'
					}
	
	#Order is importand because some a substrings of others. Also some include \r so the replacement is not re-replaced. We clean those out at the end
	smiliesDefs = [	(':devil:',u'[COLOR FFAA0000]\u2461[/COLOR]',u'>:\r)'),
					(':angel:',u'\u2460',u'O:\r)'),
					(':;):',u'\u2464',u';\r)'),
					(':-/',u'\u246e',u':-)'),
					(';)',u'\u2464',u';\r)'),
					(':D',u'\u2463',u':\rD'),
					(':P',u'\u2465',u':\rP'),
					(':p',u'\u2465',u':\rP'),
					(':o',u'\u2469',u':\ro'),
					(':~',u'\u246a',u':~'),
					(':grin:',u'\u2463',u':\rD'),
					(':blush:',u'[COLOR FFFF9999]\u246d[/COLOR]',u':")'),
					(':laugh:',u'\u2470',u':\r))'),
					(':angry:',u'\u2466',u'>:\r{'),
					(':rofl:',u'\u2467',u'*ROFL*'),
					(':huh:',u'\u2473',u'*HUH?*'),
					(':sleepy:',u'\u2468',u'*SLEEPY*'),
					(':cool:',u'\u2462',u'B)'),
					(':rolleyes:',u'*ROLLEYES*',u'*ROLLEYES*'),
					(':nod:',u'*NOD*',u'*NOD*'),
					(':sniffle:',u'\u246a',u':\rs'),
					(':confused:',u'%)',u'%)'),
					(':mad:',u'\u2466',u'>:\r{'),
					(':yawn:',u'*YAWN*',u'*YAWN*'),
					(':struggle:',u'*STRUGGLE*',u'*STRUGGLE*'),
					(':shame:',u'\u246c',u'*SHAME*'),
					(':eek:',u'[COLOR FF00AA00]\u2472[/COLOR]',u'8o'),
					(':rotfl:',u'\u2467',u'*ROFL*'),
					(':bulgy-eyes:',u'\u246f',u'Oo'),
					(':at-wits-end:',u'[COLOR FFAA0000]\u2466[/COLOR]',u'[COLOR FFAA0000]>:{[/COLOR]'),
					(':oo:',u'>oo<',u'>oo<'),
					(':stare:',u'*STARE*',u'*STARE*'),
					(':sad:',u'\u2639',u':\r('),
					(':no:',u'*NO*',u'*NO*'),
					('???',u'\u2473',u'???'),
					(':shocked:',u'\u2469',u'*SHOCKED*'),
					(':love:',u'\u2471',u'[COLOR FFAA0000]<3[/COLOR]'),
					('<3',u'[COLOR FFAA0000]\u2665[/COLOR]',u'[COLOR FFAA0000]<3[/COLOR]'),
					(':shy:',u'*SHY*',u'*SHY*'),
					(':nerd:',u'\u2474',u':-B'),
					(':(',u'\u2639',u':\r('),
					(':)',u'\u263a',u':\r)'),
					(':s',u'\u2463',u':\rs'),
					('\r',u'',u'')
					]
	
	def __init__(self,forum,always_login=False,message_converter=None):
		if not message_converter: message_converter = texttransform.MessageConverter
		self.forum = forum
		self.prefix = ''
		self._url = ''
		self.transport = None
		self.server = None
		self.forumConfig = {}
		self.needsLogin = True
		self.alwaysLogin = always_login
		self._loggedIn = False
		self.loginError = ''
		self.SSL = False
		self.urls = {}
		self.filters = {}
		self.theme = {}
		self.forms = {}
		self.formats = {}
		self.altQuoteStartFilter = '\r\r\r\r\r\r'
		self.smilies = {}
		self.MC = None
		self.messageConvertorClass=message_converter
		
	def initialize(self):
		self.MC = self.messageConvertorClass(self)
	
	def finish(self,data,callback=None):
		if callback: callback(data)
		return data
	
	def getForumPost(self,pdict=None):
		return self.ForumPost(self,pdict=pdict)
		
	def getPMLink(self,match=None):
		return self.PMLink(self,match)
	
	def getPageData(self,*args,**kwargs):
		is_replies = kwargs.get('is_replies')
		if 'is_replies' in kwargs: del kwargs['is_replies']
		pd = self.PageData(self,*args,**kwargs)
		if not pd.isReplies: pd.isReplies = is_replies
		return pd
	
	def getForumID(self):
		return self.prefix + self.forum
	
	def getDisplayName(self): return self.forum
	
	def resetBrowser(self): pass
		
	def loadForumData(self,fname):
		self.urls = {}
		self.filters = {'quote':'\[QUOTE\](?P<quote>.*)\[/QUOTE\](?is)',
						'code':'\[CODE\](?P<code>.+?)\[/CODE\](?is)',
						'php':'\[PHP\](?P<php>.+?)\[/PHP\](?is)',
						'html':'\[HTML\](?P<html>.+?)\[/HTML\](?is)',
						'image':'\[img\](?P<url>[^\[]+?)\[/img\](?is)',
						'link':'\[(?:url|video)="?(?P<url>[^\]]+?)\](?P<text>.+?)"?\[/(?:url|video)\](?is)',
						'link2':'\[url\](?P<text>(?P<url>.+?))\[/url\](?is)',
						'post_link':'(?:showpost.php|showthread.php)\?[^<>"]*?tid=(?P<threadid>\d+)[^<>"]*?pid=(?P<postid>\d+)',
						'thread_link':'showthread.php\?[^<>"]*?tid=(?P<threadid>\d+)',
						'color_start':'\[color=?#?(?P<color>\w+)\]'}
		
		self.theme = {}
		self.forms = {}
		self.formats = {}
		
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
	
	def getForumType(self): return ''

	def getQuoteFormat(self):
		forumType = self.getForumType()
		return self.quoteFormats.get(forumType,'\[QUOTE\](?P<quote>.*)\[/QUOTE\](?is)')
	
	def getQuoteStartFormat(self):
		forumType = self.getForumType()
		return self.quoteStartFormats.get(forumType,'\[quote[^\]]*?\](?i)')
	
	def getQuoteReplace(self):
		forumType = self.getForumType()
		return self.quoteReplace.get(forumType,'[QUOTE]!QUOTE![/QUOTE]')
	
	def isLoggedIn(self): return False
	
	def setLogin(self,user,password,always=False):
		self.user = user
		self.password = password
		self.alwaysLogin = always
		self.loginError = ''
		
	def makeURL(self,url): return url
	
	def getPMCounts(self,pct=0): return None
	
	def canSubscribeThread(self,tid): return False
	def canUnSubscribeThread(self,tid): return False
	
	def subscribeThread(self,tid): return False
	def unSubscribeThread(self,tid): return False
	
	def subscribeForum(self,fid): return False
	def unSubscribeForum(self,fid): return False
	
	def canSubscribeForum(self,fid): return False
	def canUnSubscribeForum(self,fid): return False
	
	def isForumSubscribed(self,fid,default=False): return default
	
	def isThreadSubscribed(self,tid,default=False): return default
		
	def hasPM(self): return False
	
	def hasSubscriptions(self): return False
	
	def canPost(self): return False
	
	def canDelete(self,user,target='POST'): return False
			
	def canEditPost(self,user): return False
	
	def fakeCallback(self,pct,message=''): return True
	
	def guestOK(self): return True
	
	def getAnnouncement(self,aid): return None
	
	
		