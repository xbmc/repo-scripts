#Forum browser common
import sys, os, re, urllib, urllib2, texttransform, binascii, time
from lib import asyncconnections
from lib.util import LOG, ERROR


def durationToShortText(unixtime):
	days = int(unixtime/86400)
	if days: return '%sd' % days
	left = unixtime % 86400
	hours = int(left/3600)
	if hours: return '%sh' % hours
	left = left % 3600
	mins = int(left/60)
	if mins: return '%sm' % mins
	sec = int(left % 60)
	if sec: return '%ss' % sec
	return '0s'

class Error(Exception): pass

class BrokenForumException(Exception): pass

class ForumMovedException(Exception): pass

class ForumNotFoundException(Exception): pass

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
		self.url = 'http://xbmc.2ndmind.com/forumbrowser/forums.php'
		#self.url = 'http://xbmc.2ndmind.tk/forumbrowser/forums.php'
	
	def postData(self,**data):
		enc = urllib.urlencode(data)
		try:
			result = urllib2.urlopen(self.url,enc).read()
			return result
		except:
			err = ERROR('FBTTOnlineDatabase.postData()')
			return 'ERROR: ' + err
			
	def addForum(self,name,url,logo='',desc='',ftype='TT',cat='0',rating_function='0',rating_accuracy='0',header_color='FFFFFF'):
		header_color = header_color or 'FFFFFF'
		return self.postData(do='add',name=name,url=url,desc=desc,cat=cat,logo=logo,type=ftype,rating_function=rating_function,rating_accuracy=rating_accuracy,header_color=header_color)
		
	def setTheme(self,fname,vals_dict):
		return self.postData(do='set_theme',name=fname,**vals_dict)
	
	def setRules(self,forumID,rules):
		return self.postData(do='set_rules',forumid=forumID,rules=rules)
		
	def getForumList(self,cat=None,terms=None):
		if cat:
			flist = self.postData(do='list',cat=cat)
		elif terms:
			flist = self.postData(do='list',terms=terms)
		else:
			flist = self.postData(do='list')
		#print flist.replace('\r',',')
		if not flist: return None
		flist = flist.split('\n')
		final = []
		try:
			for f in flist:
				if f:
					name, rest = f.split(':',1)
					add = {'name':name}
					for f in rest.split('\r'):
						k,v = f.split('=',1)
						add[k] = v
					#print repr(add)
					add['cat'] = int(add.get('cat',0))
					final.append(add)
		except:
			ERROR(str(flist))
		return final
	
	def getForumRules(self,forumID):
		rules = self.postData(do='get_rules',forumid=forumID)
		rlist = rules.split('\n')
		final = {}
		try:
			for r in rlist:
				if r and '=' in r:
					k,v = r.split('=')
					final[k] = v
		except:
			ERROR(str(rlist))
		return final

class HTMLPageInfo:
	def __init__(self,url,html='',progress_callback=None):
		self.url = url
		self.progressCallback = progress_callback
		self.currMaxProgress = 0
		self.currentProgress = 0
		self.lastProgTime = 0
		self.progWait = 1
		self.lastProgMessage = ''
		
		self.base = url
		if not self.base.endswith('/'): self.base += '/'
		
		base2 = 'http://' + url.rsplit('://',1)[-1].split('/',1)[0]
		self.base2 = base2
		self.base2 += '/'
		
		self.html = ''
		self.html2 = ''
		
		self.isValid = True
		if html:
			self.html = html
			self.html2 = html
		else:
			self._getHTML()
		
	def updateProgress(self,pct,msg=''):
		if not self.progressCallback: return True
		msg = msg or self.lastProgMessage
		self.lastProgMessage = msg
		if pct < 0:
			now = time.time()
			if self.currentProgress < self.currMaxProgress and now - self.lastProgTime >= self.progWait:
				self.lastProgTime = now
				self.progWait += 0.1
				self.currentProgress += abs(pct)
		else:
			self.currentProgress = pct
			
		callback, arg = self.progressCallback
		return callback(arg,self.currentProgress,msg)
		
	def updateProgressMax(self,maxp):
		self.currMaxProgress = maxp
		self.progWait = 1
		
	def _getHTML(self):
		self.updateProgressMax(50)
		if not self.updateProgress(0, 'Searching Forum Page'):
			self.isValid = False
			return
		try:
			self.html = self.getHTML(self.url)
		except:
			self.isValid = False
			ERROR('HTMLPageInfo 1: FAILED',hide_tb=True)
			
		if self.url == self.base2: return
		self.updateProgressMax(100)
		if not self.updateProgress(50, 'Searching Main Page'):
			self.isValid = False
			return
		try:
			self.html2 = self.getHTML(self.base2)
			self.isValid = True
		except:
			ERROR('HTMLPageInfo 2: FAILED',hide_tb=True)
		
	def getHTML(self,url):
		opener = urllib2.build_opener(asyncconnections.createHandlerWithCallback(self.updateProgress))
		try:
			o = opener.open(urllib2.Request(url,None,{'User-Agent':'Mozilla/5.0'}))
		except urllib2.HTTPError,e:
			if e.code == 403:
				o = opener.open(urllib2.Request(url,None,{'User-Agent':'Wget/1.12'}))
			else:
				raise
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
		if not self.isValid: return default
		try:
			desc = re.search('<meta[^>]*?name="description"[^>]*?content="([^"]*?)"',self.html).group(1)
			if desc: return desc
		except: pass
		try: return re.search('<meta[^>]*?name="description"[^>]*?content="([^"]*?)"',self.html2).group(1)
		except: pass
		return default
		
	def images(self):
		if not self.isValid: return [self.base2 + 'favicon.ico']
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
		#<link rel="Shortcut Icon" href="favicon.ico" type="image/x-icon" />
		final = []
		for u in urlList + urlList2:
			u = self.fullURL(u, base)
			if u in final: continue
			if u:
				final.append(u)
		return final

	def getStyleImages(self,html,base):
		urls = []
		for url in re.findall('<link[^>]*?href="(?P<url>[^"]*?)"[^>]*?"text/css"[^>]*?>',html) + re.findall('<link[^>]*?"text/css"[^>]*?href="(?P<url>[^"]*?)"[^>]*?>',html):
			#print url
			url = self.fullURL(url, base)
			sbase = url.rsplit('/',1)[0] + '/'
			try:
				style = self.getHTML(url)
				for url in re.findall("background(?:-image)?:[^\(]*?url\(['\"]?(?P<url>[^\"']+?)['\"]?\)",style):
					urls.append(self.fullURL(url, sbase))
			except:
				LOG('Failed to get stylesheet')
		
		#print urls
		return urls
	
	def fullURL(self,u,base): return fullURL(u,base,self.base2)
	
urlParentDirFilter = re.compile('(?<!/)/\w[^/]*?/\.\./')
def fullURL(u,base,base2=None):
	if not base2: base2 = 'http://' + base.rsplit('://',1)[-1].split('/',1)[0] + '/'
	u = u.strip()
	if u.startswith('http'):
		pass
	elif u.startswith('./') or u.startswith('../'):
		u = base + u[2:]
	elif u.startswith('.'):
		u = base + u[1:]
	elif u.startswith('/'):
		u = base2 + u[1:]
	else:
		u = base + u
	pdfFilter = urlParentDirFilter
	while pdfFilter.search(u):
		#TODO: Limit
		u = pdfFilter.sub('/',u)
		u = u.replace('/../','/')
	u = u.replace('&amp;','&')
	return u
	
class ForumData:
	def __init__(self,forumID,forumsPath):
		self.forumID = forumID
		self.forumsPath = forumsPath
		self.filePath = os.path.join(self.forumsPath,self.forumID)
		self.name = ''
		self.description = ''
		self.readData()
		
	def forumURL(self):
		return self.urls.get('tapatalk_server',self.urls.get('forumrunner_server',self.urls.get('server','')))
	
	def readData(self):
		self.urls = {}
		self.theme = {}
		self.formats = {}
		if not os.path.exists(self.filePath): return
		f = open(self.filePath,'r')
		data = f.read()
		f.close()
		data = data.splitlines()
		self.name = data.pop(0)[1:]
		self.description = data.pop(0)[1:]
		for line in data:
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
			elif dtype == 'theme':
				key,color = rest.split('=',1)
				if color.startswith('=='):
					dup = color.split('=')[-1]
					color = self.theme[dup]
				self.theme[key] = color
			elif dtype == 'format':
				key,data = rest.split('=',1)
				if data.startswith('=='):
					dup = data.split('=')[-1]
					data = self.formats[dup]
				self.formats[key] = data
				
	def writeData(self):
		out = '#%s\n#%s\n' % (self.name,self.description)
		for k,v in self.urls.items():
			out += 'url:' + k + '=' + v + '\n'
		for k,v in self.theme.items():
			out += 'theme:' + k + '=' + v + '\n'
		for k,v in self.formats.items():
			out += 'format:' + k + '=' + v + '\n'
		f = open(self.filePath,'w')
		f.write(out)
		f.close()
		

################################################################################
# Action
################################################################################
class Action:
	def __init__(self,action=''):
		self.action = action

class PMLink:
	linkImageFilter = re.compile('https?://.+?\.(?:jpg|jpeg|png|gif|bmp)$')
	#urlParentDirFilter = re.compile('(?<!/)/\w[^/]*?/\.\./')
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
		self.url = self.url.replace('&amp;','&')
		self._isImage = self.linkImageFilter.search(self.url) and True or False
		if self._isImage: return
		pm = tm = None
		for plre in self.FB.getPostLinkRE():
			pm = re.search(plre,self.url)
			if pm: break
		for tlre in self.FB.getThreadLinkRE():
			tm = re.search(tlre.replace('{{FORUM}}',self.FB.forum),self.url)
			if tm: break
		if pm:
			d = pm.groupdict()
			self.pid = d.get('pid','')
			self.tid = d.get('tid','')
		elif tm:
			d = tm.groupdict()
			self.tid = d.get('tid','')
			
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
		self.successMessage = ''
		self.boxid = ''
		self.moderated = False
		
	def setQuote(self,user,quote):
		tagFilter = re.compile('<[^<>]+?>',re.S)
		self.quser = tagFilter.sub('',user)
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
		self.boxid = post.boxid
		return self
	
	def toString(self):
		return dictToString(self.__dict__)
	
	def fromString(self,data):
		self.__dict__.update(dictFromString(data))
		return self

def valToString(val):
	if hasattr(val,'encode'):
		try:
			return val.encode('utf-8')
		except:
			LOG('valToString() encode error')
			return val
	return str(val).encode('utf-8')

def dictToString(data_dict):
	if not data_dict: return ''
	ret = []
	try:
		for key,val in data_dict.items():
			if val == None:
				continue
			elif isinstance(val,dict):
				val = dictToString(val)
				key = 'dict___' + key
			elif isinstance(val,list):
				val = ','.join(val)
				key = 'list___' + key
			ret.append('%s=%s' % (key,binascii.hexlify(valToString(val))))
	except:
		raise
	return ','.join(ret)

def dictFromString(data,val_is_hex=True):
	if not data: return {}
	theDict = {}
	for keyval in data.split(','):
		key,val = keyval.split('=',1)
		if key.startswith('dict___'):
			key = key[7:]
			val = dictFromString(binascii.unhexlify(val),val_is_hex)
			theDict[key] = val
		elif key.startswith('list___'):
			key = key[7:]
			val = binascii.unhexlify(val).split(',')
			theDict[key] = val
		else:
			if val_is_hex:
				theDict[key] = binascii.unhexlify(val)
			else:
				theDict[key] = val.decode('utf-8')
	return theDict

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
		self.searchID = None
	
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
	hideSignature = False
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
		self.topic = ''
		self.boxid = ''
		self.status = ''
		self.activity = ''
		self.activityUnix = None
		self.lastSeen = None
		self.online = False
		self.postCount = 0
		self.postNumber = 0
		self.joinDate = ''
		self.userInfo = {}
		self.extras = {}
		self.isSent = False
		self.unixtime = 0
		if pdict: self.setVals(pdict)
		self.attrs_index = dir(self)
		self.attrs_lower = [x.lower() for x in self.attrs_index]
			
	def setVals(self,pdict): pass
	
	def canLike(self): return False
	
	def canUnlike(self): return False
	
	def like(self): return False
	
	def unlike(self): return False
	
	def messageType(self):
		return self.isPM and 'PM' or 'POST'
		
	def setUserInfo(self,info): pass
		
	def getDate(self,offset=0): return self.date
	
	def getActivity(self,time_offset=0): return self.activity
	
	def getUserData(self,name):
		name = name.lower()
		if hasattr(self,name): return getattr(self,name)
		if name in self.extras: return self.extras[name]
		if name in self.attrs_lower:
			return getattr(self, self.attrs_index[self.attrs_lower.index(name)])
			
	def getExtras(self,ignore=None):
		extras = self.extras.copy()
		if self.status: extras['status'] = self.status
		if self.postCount: extras['postcount'] = self.postCount
		if self.joinDate: extras['joindate'] = self.joinDate
		if not ignore: return extras
		for i in ignore:
			if i in extras: del extras[i]
		return extras
	
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
		if self.hideSignature: return self.message
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
		
	def hasMedia(self,webvid=None,count_link_images=False):
		if not webvid:
			from webviewer import video #@UnresolvedImport
			webvid = video.WebVideo()
		images = False
		video = False
		for l in self.links():
			if l.isImage(): images = True
			if count_link_images and l.textIsImage(): images = True
			elif webvid.mightBeVideo(l.url) or webvid.mightBeVideo(l.text): video = True
		if not images: images = bool(self.imageURLs())
		return images,video
			
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
# ForumUser
######################################################################################
class ForumUser:
	def __init__(self,ID,name):
		self.name = name
		self.ID = ID
		self.postCount = ''
		self.joinDate = ''
		self.activity = ''
		self.online = False
		self.lastActivityDate = ''
		self.avatar = ''
		self.status = ''
		self.extras = {}
			
######################################################################################
# Forum Browser API
######################################################################################
class ForumBrowser:
	browserType = 'ForumBrowser'
	prefix = ''
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
							'ip':'(?i)\[quote(?: name\=\'(?P<user>[^\']+)\')?\]',
							'pb':'\[quote(?:="(?P<user>[^"]+?)")?\](?is)'
						}
	
	quoteReplace = 	{	'mb':"[quote='!USER!' pid='!POSTID!' dateline='!DATE!']!QUOTE![/quote]",
						'xf':'[quote="!USER!, post: !POSTID!, member: !USERID!"]!QUOTE![/quote]',
						'vb':'[QUOTE=!USER!;!POSTID!]!QUOTE![/QUOTE]',
						'pb':'[quote="!USER!"]!QUOTE![/quote]'
					}
	
	#Order is importand because some a substrings of others. Also some include \r so the replacement is not re-replaced. We clean those out at the end
	smiliesDefs = [	(':devil:',u'[COLOR FFAA0000]\u2461[/COLOR]',u'>:\r)'),
					(':evil:',u'[COLOR FFAA0000]\u2461[/COLOR]',u'>:\r)'),
					(':twisted:',u'[COLOR FFAA0000]\u2461[/COLOR]',u'>:\rD'),
					(':angel:',u'\u2460',u'O:\r)'),
					(':;):',u'\u2464',u';\r)'),
					(':-/',u'\u246e',u':-/'),
					(';)',u'\u2464',u';\r)'),
					(':D',u'\u2463',u':\rD'),
					(':P',u'\u2465',u':\rP'),
					(':p',u'\u2465',u':\rP'),
					(':o',u'\u2469',u':\ro'),
					(':~',u'\u246a',u':~'),
					(':grin:',u'\u2463',u':\rD'),
					(':blush:',u'[COLOR FFFF9999]\u246d[/COLOR]',u':")'),
					(':oops:',u'[COLOR FFFF9999]\u246d[/COLOR]',u':")'),
					(':laugh:',u'\u2470',u':\r))'),
					(':angry:',u'\u2466',u'>:\r{'),
					(':rofl:',u'\u2467',u'*ROFL*'),
					(':lol:',u'\u2467',u'*LOL*'),
					(':huh:',u'\u2473',u'*HUH?*'),
					(':sleepy:',u'\u2468',u'*SLEEPY*'),
					(':cool:',u'\u2462',u'B)'),
					('8-)',u'\u2462',u'8-)'),
					(':rolleyes:',u'*ROLLEYES*',u'*ROLLEYES*'),
					(':roll:',u'*ROLLEYES*',u'*ROLLEYES*'),
					(':nod:',u'*NOD*',u'*NOD*'),
					(':sniffle:',u'\u246a',u':\rs'),
					(':confused:',u'%)',u'%)'),
					(':mad:',u'\u2466',u'>:\r{'),
					(':x',u'\u2466',u'>:\r{'),
					(':yawn:',u'*YAWN*',u'*YAWN*'),
					(':struggle:',u'*STRUGGLE*',u'*STRUGGLE*'),
					(':shame:',u'\u246c',u'*SHAME*'),
					(':eek:',u'[COLOR FF00AA00]\u2472[/COLOR]',u'[COLOR FF00AA00]8o[/COLOR]'),
					(':mrgreen:',u'[COLOR FF00AA00]\u2472[/COLOR]',u'[COLOR FF00AA00]:D[/COLOR]'),
					(':rotfl:',u'\u2467',u'*ROFL*'),
					(':bulgy-eyes:',u'\u246f',u'Oo'),
					(':at-wits-end:',u'[COLOR FFAA0000]\u2466[/COLOR]',u'[COLOR FFAA0000]>:{[/COLOR]'),
					(':oo:',u'>oo<',u'>oo<'),
					(':stare:',u'*STARE*',u'*STARE*'),
					(':sad:',u'\u2639',u':\r('),
					(':cry:',u'\u2639',u':\r('),
					(':no:',u'*NO*',u'*NO*'),
					('???',u'\u2473',u'???'),
					(':shocked:',u'\u2469',u'*SHOCKED*'),
					(':shock:',u'\u2469',u'*SHOCKED*'),
					(':love:',u'\u2471',u'[COLOR FFAA0000]<3[/COLOR]'),
					('<3',u'[COLOR FFAA0000]\u2665[/COLOR]',u'[COLOR FFAA0000]<3[/COLOR]'),
					(':shy:',u'*SHY*',u'*SHY*'),
					(':nerd:',u'\u2474',u':-B'),
					(':geek:',u'\u2474',u':-B'),
					(':ugeek:',u'\u2474',u':-B'), #TODO: Make smiley with beard
					#(':!:','',''), #TODO: ! in face
					#(':?:','',''), #TODO: ? in face
					#(':idea:','',''), #TODO: lightbulb 
					#(':arrow:','',''), #TODO: Arrow in face
					(':(',u'\u2639',u':\r('),
					(':)',u'\u263a',u':\r)'),
					(':s',u'\u2463',u':\rs'),
					('\r',u'',u'')
					]

#From IP Board
#:smile: :thumbsup: :wub: :unsure: >_< :ph34r: (w00t) :drool: :sick: :sorcerer: :sweat: :huggles: :console: :poke: :flowers: :hairy:
#:super: :phone: :santa: :purple: :puppeh: :sheep: :heart: :question: (!) :homestar: :cat: :hyper: <_< :alien: :dry: :hmm: :aww: :afro:
#:sleep: :mellow: :zorro: :whistle: :tongue: :nuke: :ike: :brr: :pirate: :kiss: :cheer: :wacko: :ninja: :turned: :faceless:
#:baby: :ahappy: :bug: :frantics: :ohmy: :shifty: :clover: :bye: :logik: :blink: :yes: :ermm: :twitch: :queen:
					
	forumTypeNames = {	'vb': 'VBulletin',
						'fb': 'FluxBB',
						'mb': 'MyBB',
						'pb': 'PhpBB',
						'ip': 'Invision Power Board',
						'sm': 'Simple Machines Forum',
						'xf': 'XenForo'
					}
	
	threadLinkRE = {		'vb': (	'(?:^|")(?:showthread.php|threads)(?:\?|/)(?:[^"]*?t=)?(?P<tid>\d+)',
									'{{FORUM}}/.+/(?P<tid>\d+)-'),
							'fb': (	'(?:^|")viewtopic.php?[^"]*?(?<!;|p)(?:f|id)=?(?P<tid>\d+)',),
							'mb': (	'(?:^|")thread-(?P<tid>\d+).html',
									'(?:^|")showthread\.php\?[^"\']*?tid=(?P<tid>\d+)'),
							'pb': (	'(?:^|")(?:\W+)?viewtopic.php?[^"\']*?f=(?P<fid>\d+)[^"\']*?t=(?P<tid>\d+)',),
							'ip': (	'/topic/(?P<tid>\d+)-[^"\']*?(?:"|\'|$)',),
							'sm': (	'index\.php\?[^"\']*?topic=(?P<tid>\d+\.0+)',)
						}
	
	postLinkRE = {			'vb': (	'(?:^|")showpost\.php(?:\?|/)(?:[^"\']*?p=)?(?P<pid>\d+)', # threads/70389-Name-Changes?p=1134465&amp;viewfull=1#post1134465
									'(?:^|")(?:showthread\.php\?(?:t=)?|threads/)\d+[^"\']*?p=(?P<pid>\d+)',
									'/(?P<tid>\d+)-.+#post(?P<pid>\d+)$'),
							'fb': (	'(?:^|")viewtopic\.php?[^"\']*?(?<!;)pid=(?P<pid>\d+)',),
							'mb': (	'(?:^|")thread-\d+-post-(?P<pid>\d+)\.html',
									'(?:^|")showthread\.php\?[^"\']*?tid=\d+[^"\']*?pid=(?P<pid>\d+)'),
							'pb': (	'(?:^|")#p(?P<pid>\d+)',),
							'ip': (	'/topic/\d+-[^"\']*?/?#entry(?P<pid>\d+)(?:"|\'|$)',),
							'sm': (	'index\.php\?[^"\']*?topic=\d+\.msg(?P<pid>\d+)#msg\d+',)
						}
	
	def __init__(self,forum,always_login=False,message_converter=None):
		if not message_converter: message_converter = texttransform.MessageConverter
		self.forum = forum
		self._url = ''
		self.user = ''
		self.password = ''
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
		self.pmBoxes = []
		self.lastURL = ''
		self.browser = None
		self.rules = None
		self.messageConvertorClass=message_converter
		
	def initialize(self):
		self.MC = self.messageConvertorClass(self)
	
	def finish(self,data,callback=None):
		if callback: callback(data)
		return data
	
	def domain(self):
		domain = self._url.split('://',1)[-1]
		return domain.split('/')[0]
	
	def getThreadLinkRE(self,others=()):
		ft = self.getForumType()
		if not ft: return others
		return self.threadLinkRE.get(ft,()) + others
	
	def getPostLinkRE(self,others=()):
		ft = self.getForumType()
		if not ft: return others
		return self.postLinkRE.get(ft,()) + others
	
	def getLoginURL(self):
		if self.rules and 'login_url' in self.rules:
			url = self.rules['login_url']
		else:
			url = self.makeURL(self.getURL('login'))
			
		LOG('LOGIN URL: %s' % url)
			
		return url
		
	def canLogin(self):
		return bool(self.user and self.password)
	
	def forumTypeDisplay(self,short):
		return self.forumTypeNames(short,'Unknown')
	
	def getForumInfo(self):
		return [ ('name',self.forum) ]
	
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
		
	def clearForumData(self):
		self.urls = {}
		self.filters = {}
		self.theme = {}
		self.forms = {}
		self.formats = {}
		
	def loadForumData(self,fname):
		self.filters.update({'quote':'\[QUOTE\](?P<quote>.*)\[/QUOTE\](?is)',
						'code':'\[CODE\](?P<code>.+?)\[/CODE\](?is)',
						'php':'\[PHP\](?P<php>.+?)\[/PHP\](?is)',
						'html':'\[HTML\](?P<html>.+?)\[/HTML\](?is)',
						'image':'\[img\](?P<url>[^\[]+?)\[/img\](?is)',
						'link':'\[(?:url|video|ame)="?(?P<url>[^\"\]]+?)"?\](?P<text>.+?)\[/(?:url|video|ame)\](?is)',
						'link2':'\[url\](?P<text>(?P<url>.+?))\[/url\](?is)',
						'post_link':'(?:showpost.php|showthread.php)\?[^<>"]*?tid=(?P<tid>\d+)[^<>"]*?pid=(?P<pid>\d+)',
						'thread_link':'showthread.php\?[^<>"]*?tid=(?P<tid>\d+)',
						'color_start':'\[color=?["\']?#?(?P<color>\w+)["\']?\](?i)'})
		return self.parseForumData(fname)
		
	def parseForumData(self,fname):
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
	
	def sortDictList(self,dlist,key):
		ct = 0
		srt = {}
		for d in dlist:
			srt[str(d.get(key)) + str(ct)] = d
			ct+=1
		keys = srt.keys()
		keys.sort(reverse=True)
		dlist = []
		for k in keys:
			dlist.append(srt[k])
		return dlist
	
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
	
	def setLogin(self,user,password,always=False,rules=None):
		self.user = user
		self.password = password
		self.alwaysLogin = always
		self.loginError = ''
		self.rules = rules
		
	def makeURL(self,url): return url
	
	def getPMCounts(self,pct=0): return None
	
	def canGetUserPosts(self): return False
	def canGetUserThreads(self): return False

	def canSearch(self): return self.canSearchPosts() or self.canSearchThreads() or self.canSearchAdvanced()
	def canSearchPosts(self): return False
	def canSearchThreads(self): return False
	def canSearchAdvanced(self,stype=None): return False
	
	def canSubscribeThread(self,tid): return False
	def canUnSubscribeThread(self,tid): return False
	
	def subscribeThread(self,tid): return False
	def unSubscribeThread(self,tid): return False
	
	def subscribeForum(self,fid): return False
	def unSubscribeForum(self,fid): return False
	
	def canSubscribeForum(self,fid): return False
	def canUnSubscribeForum(self,fid): return False
	
	def canCreateThread(self,fid): return False
	
	def canGetOnlineUsers(self): return False
	
	def isForumSubscribed(self,fid,default=False): return default
	
	def isThreadSubscribed(self,tid,default=False): return default
		
	def hasPM(self): return False
	
	def hasSubscriptions(self): return False
	
	def canPost(self): return False
	
	def canPrivateMessage(self): return self.canPost()
	
	def canDelete(self,user,target='POST'): return False
			
	def canEditPost(self,user): return False
	
	def fakeCallback(self,pct,message=''): return True
	
	def guestOK(self): return True
	
	def getAnnouncement(self,aid): return None
	
	def getPMBoxes(self,update=True): return None
	
	def canGetUserInfo(self): return False
	
	def getUserInfo(self,uid=None,uname=None): return None
	
	def canOpenLatest(self): return True
	
	
		