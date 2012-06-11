import sys, re, time, os, urllib2
import forumbrowser, texttransform
from forumbrowser import FBData

import locale
loc = locale.getdefaultlocale()
print loc
ENCODING = loc[1] or 'utf-8'

DEBUG = sys.modules["__main__"].DEBUG
LOG = sys.modules["__main__"].LOG
ERROR = sys.modules["__main__"].ERROR
__addon__ = sys.modules["__main__"].__addon__
__language__ = sys.modules["__main__"].__language__
FORUMS_STATIC_PATH = sys.modules["__main__"].FORUMS_STATIC_PATH

######################################################################################
# Forum Browser Classes
######################################################################################
		
################################################################################
# ForumPost
################################################################################
class ForumPost(forumbrowser.ForumPost):
	def __init__(self,fb,pmatch=None,pdict=None):
		if pmatch:
			pdict = pmatch.groupdict()
		forumbrowser.ForumPost.__init__(self, fb, pdict)
			
	def setVals(self,pdict):
		self.setPostID(pdict.get('postid',pdict.get('pmid','')))
		self.date = pdict.get('date','')
		self.userId = pdict.get('userid','')
		self.userName = pdict.get('user') or pdict.get('guest') or 'UERROR'
		self.avatar = pdict.get('avatar','')
		self.status = pdict.get('status','')
		self.title = pdict.get('title','')
		self.message = pdict.get('message','') or ''
		self.signature = pdict.get('signature','') or ''
		self.online = pdict.get('online')
		self.postNumber = pdict.get('postnumber') or None
		self.postCount = pdict.get('postcount') or None
		self.joinDate = pdict.get('joindate') or ''
		self.extras = pdict.get('extras') or self.extras
	
	def messageToText(self,html):
		html = self.MC.lineFilter.sub('',html)
		html = re.sub('<br[^>]*?>','\n',html)
		html = html.replace('</table>','\n\n')
		html = html.replace('</div></div>','\n') #to get rid of excessive new lines
		html = html.replace('</div>','\n')
		html = re.sub('<[^>]*?>','',html)
		return texttransform.convertHTMLCodes(html).strip()
	
	def setPostID(self,pid):
		pid = str(pid) or repr(time.time())
		self.postId = pid
		self.pid = pid
		self.isPM = pid.startswith('PM')
	
	def getID(self):
		if self.pid.sartswith('PM'): return self.pid[2:]
		return self.pid
		
	def cleanUserName(self):
		return self.MC.tagFilter.sub('',self.userName)
	
	def getMessage(self):
		sig = ''
		if self.signature: sig = '\n__________\n' + self.signature
		return self.message + sig
	
	def messageAsText(self):
		return self.messageToText(self.getMessage())
		
	def messageAsDisplay(self,short=False,raw=False):
		if self.isPM:
			message =  self.MC.parseCodes(self.getMessage())
		else:
			message = self.MC.messageToDisplay(self.getMessage())
		message = re.sub('\[(/?)b\]',r'[\1B]',message)
		message = re.sub('\[(/?)i\]',r'[\1I]',message)
		return message
		
	def messageAsQuote(self):
		return self.MC.messageAsQuote(self.message)
		
	def imageURLs(self):
		return self.MC.imageFilter.findall(self.getMessage())
		
	def linkImageURLs(self):
		return re.findall('<a.+?href="(https?://.+?\.(?:jpg|jpeg|png|gif|bmp))".+?</a>',self.message)
		
	def linkURLs(self):
		return self.MC.linkFilter.finditer(self.getMessage())
		
	def links(self):
		links = []
		for m in self.linkURLs(): links.append(self.FB.getPMLink(m))
		return links
		
	def makeAvatarURL(self):
		base = self.FB.urls.get('avatar')
		if base and not self.avatar:
			self.avatar = base.replace('!USERID!',self.userId)
		return self.avatar
	
			
################################################################################
# PageData
################################################################################
class PageData:
	def __init__(self,fb,page_match=None,next_match=None,prev_match=None,page_type='',total_items='',page_urls=None):
		self.FB = fb
		self.MC = fb.MC
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
		self.isReplies = False
		self.current = '0'
		self.useURLs = False
		self.pageType = page_type
		self.totalitems = total_items
		self.pageURLs = page_urls
		self.first = True
		self.doInit(page_match, next_match, prev_match, page_type, total_items, page_urls)
		self.first = False
		
	def doInit(self,page_match=None,next_match=None,prev_match=None,page_type='',total_items='',page_urls=None):
		self.pageType = page_type or self.pageType
		self.totalitems = total_items or self.totalitems
		self.pageURLs = page_urls or self.pageURLs
		
		self.endPage = self.FB.formats.get('no_9999') == 'True' and 1 or 9999
		page_set = False
		if page_match:
			pdict = page_match.groupdict()
			if pdict.get('page'):
				self.page = pdict.get('page')
				page_set = True
			self.totalPages = pdict.get('total','1')
			self.pageDisplay = self.MC.tagFilter.sub('',pdict.get('display',''))
		if next_match:
			#check for less greedy match by looking in the whole match for a smaller match
			alld = next_match.group(0)
			pre = re.compile(self.FB.filters.get('next'))
			while alld:
				alld = alld[1:]
				test = pre.search(alld)
				if not test: break
				next_match = test
			ndict = next_match.groupdict()
			page = ndict.get('page')
			start = ndict.get('start','0')
			if page:
				self.next = True
				self.urlMode = 'PAGE'
				if not page_set and page.isdigit(): self.page = str(int(page) - 1)
			elif start:
				self.next = True
				self.nextStart = start
				self.urlMode = 'START'
		else:
			try:
				if not page_match and self.pageURLs: raise Exception('NO_PAGE_MATCH')
				self.next = int(self.page) < int(self.totalPages)
			except:
				self.useURLs = True
		if prev_match:
			self.useURLs = False
			#check for less greedy match by looking in the whole match for a smaller match
			alld = prev_match.group(0)
			pre = re.compile(self.FB.filters.get('prev'))
			while alld:
				alld = alld[1:]
				test = pre.search(alld)
				if not test: break
				prev_match = test
			pdict = prev_match.groupdict()
			page = pdict.get('page')
			start = pdict.get('start','0')
			if page:
				self.prev = True
				self.urlMode = 'PAGE'
				if not page_set and page.isdigit(): self.page = str(int(page) + 1)
			elif start:
				self.prev = True
				self.prevStart = start
				self.urlMode = 'START'
		else:
			try:
				if not page_match and self.pageURLs: raise Exception('NO_PAGE_MATCH')
				self.prev = int(self.page) > 1
			except:
				if not next_match: self.useURLs = True
			
		if not self.FB.urls.get('page_arg'): self.useURLs = True
			
		if self.useURLs:
			if self.pageURLs:
				totalPages = self.totalPages
				for p in self.pageURLs:
					if int(p) > int(totalPages): totalPages = p
				self.totalPages = totalPages
				if '1' in self.pageURLs and not page_match:
					self.page = self.getCurrentFromMissing()
					if int(self.page) > int(self.totalPages): self.totalPages = self.page
				self.prev = bool(self.getPrevPageURL())
				self.next = bool(self.getNextPageURL())
				
		if int(self.totalPages) < int(self.page): self.totalPages = self.page
		
	def update(self,page_match=None,next_match=None,prev_match=None,page_type='',total_items='',page_urls=None):
		self.doInit(page_match, next_match, prev_match, page_type, total_items, page_urls)
		return self
		
	def getCurrentFromMissing(self):
		if not self.first: return self.page
		missing = []
		for x in range(1,int(self.totalPages) + 1):
			if not str(x) in self.pageURLs:
				missing.append(x)
		if '1' in missing: return '1'
		if not missing: return str(int(self.totalPages) + 1) 
		for m in missing:
			under = m - 1
			over = m + 1
			if not under in missing and not over in missing: return str(m)
		else:
			return str(missing[-1] + 1)
			
	
	def getPageNumber(self,page=None):
		if page == None: page = self.page
		if self.useURLs:
			if int(page) < 0:
				if self.pageURLs and str(self.totalPages) in self.pageURLs:
					self.page = self.totalPages
					return self.pageURLs[str(self.totalPages)]
			else:
				if self.pageURLs and str(page) in self.pageURLs:
					self.page = page
					return self.pageURLs[str(page)]
			return page
		elif self.urlMode != 'PAGE':
			per_page = self.FB.formats.get('%s_per_page' % self.pageType)
			if not per_page:
				nextp = int(self.nextStart)
				prev = int(self.prevStart)
				if nextp == 0:
					if int(page) < 0: return self.current
				elif prev == 0 and int(self.page) == 1:
					per_page = nextp
				else:
					per_page = int((nextp - prev) / 2)
			try:
				if int(page) < 0: page = self.totalPages > 1 and self.totalPages or self.endPage
				page = str((int(page) - 1) * int(per_page))
				self.current = page
			except:
				ERROR('CALCULATE START PAGE ERROR - PAGE: %s' % page)
		else:
			try:
				if int(page) < 0: page = int(self.totalPages) > 1 and self.totalPages or self.endPage
			except:
				ERROR('CALCULATE START PAGE ERROR - PAGE: %s' % page)
		return page
		
	def setThreadData(self,topic,threadid):
		self.topic = topic
		self.tid = threadid
				
	def getNextPage(self):
		if self.useURLs: return self.getNextPageURL(set_page=True)
		if self.urlMode == 'PAGE':
			try:
				return str(int(self.page) + 1)
			except:
				return '1'
		else:
			return self.nextStart
			
	def getPrevPage(self):
		if self.useURLs: return self.getPrevPageURL(set_page=True)
		if self.urlMode == 'PAGE':
			try:
				return str(int(self.page) - 1)
			except:
				return '1'
		else:
			return self.prevStart
		
	def getNextPageURL(self,set_page=False):
		if not self.pageURLs: return ''
		try:
			current = int(self.page)
			for p in self.pageURLs:
				if int(p) - current == 1:
					if set_page: self.page = p
					return self.pageURLs[p]
		except:
			ERROR('getNextPageURL()')
			return ''
	
	def getPrevPageURL(self,set_page=False):
		if not self.pageURLs: return ''
		try:
			current = int(self.page)
			for p in self.pageURLs:
				if current - int(p) == 1:
					if set_page: self.page = p
					return self.pageURLs[p]
		except:
			ERROR('getNextPageURL()')
			return ''
			
	def getPageDisplay(self):
		if self.pageDisplay: return self.pageDisplay
		totalPages = self.totalPages
		if self.useURLs and self.pageURLs:
			for p in self.pageURLs:
				if int(p) > int(totalPages): totalPages = p
			self.totalPages = totalPages
			totalPages = str(totalPages) + '?'
		if self.page and self.totalPages:
			return 'Page %s of %s' % (self.page,totalPages)
		
######################################################################################
# Forum Browser API
######################################################################################
class ScraperForumBrowser(forumbrowser.ForumBrowser):
	browserType = 'ScraperForumBrowser'
	PageData = PageData
	ForumPost = ForumPost
	def __init__(self,forum,always_login=False):
		forumbrowser.ForumBrowser.__init__(self, forum, always_login, texttransform.MessageConverter)
		self.forum = forum
		self._url = ''
		self.lastURL = ''
		self.browser = None
		self.mechanize = None
		self.needsLogin = True
		self.alwaysLogin = always_login
		self.lastHTML = ''
		self.cookieJar = None
		
		self.reloadForumData(forum)
		self.initialize()
		
	def getForumID(self):
		return self.forum
	
	def isLoggedIn(self):
		#check = self.forms.get('login_action','@%+#').split('?')[0]
		#if check and self.lastHTML:
		#	#open('/home/ruuk/test3.txt','w').write(self.lastHTML)
		#	return not 'action="' + check in self.lastHTML
		if self.lastHTML:
			return bool(re.search('log[\s-]?out(?i)',self.lastHTML)) and not self.needsLogin
		return self._loggedIn
	
	def resetBrowser(self):
		self.browser = None
		
	def reloadForumData(self,forum):
		self.urls = {}
		self.filters = {}
		self.theme = {}
		self.forms = {}
		self.formats = {}
		self.smilies = {}
		
		if not self.loadForumData(forum): raise Exception('Forum Load Failure')
			#self.forum = 'forum.xbmc.org'
			#self.loadForumData(self.forum)
		
	def loadForumData(self,forum):
		self.needsLogin = True
		fname = os.path.join(FORUMS_STATIC_PATH,forum)
		if not os.path.exists(fname): fname = forum
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
			
	def checkBrowser(self):
		if not self.mechanize:
			from webviewer import mechanize #@UnresolvedImport
			import xbmc
			cookiesPath = os.path.join(xbmc.translatePath(__addon__.getAddonInfo('profile')),'cache','cookies')
			LOG('Cookies will be saved to: ' + cookiesPath)
			cookies = mechanize.LWPCookieJar(cookiesPath)
			if os.path.exists(cookiesPath): cookies.load()
			self.cookieJar = cookies
			opener = mechanize.build_opener(mechanize.HTTPCookieProcessor(cookies))
			mechanize.install_opener(opener)
			self.mechanize = mechanize
		if not self.browser:
			self.browser = self.mechanize.Browser()
			self.browser.set_cookiejar(self.cookieJar)
			self.browser.set_handle_robots(False)
			self.browser.addheaders = [('User-Agent','Wget/1.12')]
#			class SanitizeHandler(mechanize.BaseHandler):
#				def http_response(self, request, response):
#					if not hasattr(response, "seek"):
#						response = mechanize.response_seek_wrapper(response)
#			
#					if response.info().dict.has_key('content-type') and ('html' in response.info().dict['content-type']):
#						data = response.get_data()
#						response.set_data(re.sub('<!(?!-)[^>]*?>','',data))
#					return response
#
#			self.browser.add_handler(SanitizeHandler())

	def setSecurityControl(self,c,url,html):
		images = forumbrowser.HTMLPageInfo(url,html).baseImages()
		for i in images:
			if '.php?' in i:
				sec = self.doCaptcha(i)
				if sec: c.value = sec
			
	def doCaptcha(self,url):
		cachePath = sys.modules["__main__"].CACHE_PATH
		captchaPath = os.path.join(cachePath,'captcha')
		open(captchaPath,'w').write(self.browser.open_novisit(url).read())
		url = captchaPath
		import xbmcgui, xbmc
		class CaptchaWindow(xbmcgui.WindowXMLDialog):
			def __init__(self,*args,**kwargs):
				self.url = kwargs.get('url')
				
			def init(self):
				LOG('Showing Captch: ' + self.url)
				self.getControl(100).setImage(self.url)
				
			def update(self,url):
				self.getControl(100).setImage(url)
				
		w = CaptchaWindow('script-forumbrowser-captcha.xml',xbmc.translatePath(__addon__.getAddonInfo('path')),'Default','720p',url=url)
		w.show()
		w.update(url)
		try:
			return sys.modules["__main__"].doModKeyboard('Enter security code')
		finally:
			w.close()
			del w
			
	def login(self,url=''):
		if not self.canLogin():
			self._loggedIn = False
			return False
		if self.isLoggedIn():
			self._loggedIn = True
			return True
		LOG('LOGGING IN')
		self.checkBrowser()
		response = self.browser.open(url or self.getURL('login'))
		html = response.read()
		#open('/home/ruuk/test.txt','w').write(html)
		try:
			self.browser.select_form(predicate=self.predicateLogin)
			self.browser[self.forms['login_user']] = self.user
			self.browser[self.forms['login_pass']] = self.password
		except:
			ERROR('LOGIN FORM SELECT ERROR',hide_tb=True)
			LOG('TRYING ALTERNATE METHOD 1')
			try:
				form = self.getForm(html,self.forms.get('login_action'))
				if not form: raise Exception('NO FORM')
				self.browser.form = form
				self.browser[self.forms['login_user']] = self.user
				self.browser[self.forms['login_pass']] = self.password
			except:
				ERROR('LOGIN FORM SELECT ERROR',hide_tb=True)
				LOG('TRYING ALTERNATE METHOD 2')
				try:
					ct=0
					userset = False
					passset = False
					while True:
						self.browser.select_form(nr=ct) #Will error out after last form
						ct+=1
						try:
							for c in self.browser.form.controls:
								if not userset and self.forms['login_user'] in str(c.name):
									userset = True
									c.value = self.user
								elif not passset and self.forms['login_pass'] in str(c.name):
									passset = True
									c.value = self.password
								elif userset and ('sec' in str(c.name).lower() or 'captcha' in str(c.name).lower()) and not c.readonly:
									LOG('Found Security Control')
									self.setSecurityControl(c,response.geturl(),html)
								#self.browser[self.forms['login_user']] = self.user
								#self.browser[self.forms['login_pass']] = self.password
							if not userset and not passset: raise Exception('No User/Pass Controls')
							break
						except:
							LOG('WRONG FORM: %s' % ct)
					if not userset or not passset:
						if userset:
							response = self.browser.submit()
							html = response.read()
							#import codecs
							#codecs.open('/home/ruuk/test.txt','w','utf8').write(html.decode('utf8'))
							ct=0
							while True:
								self.browser.select_form(nr=ct) #Will error out after last form
								ct+=1
								try:
									for c in self.browser.form.controls:
										if not passset and self.forms['login_pass'] in str(c.name):
											passset = True
											c.value = self.password
										elif passset and 'sec' in str(c.name).lower() and not c.readonly:
											LOG('Found Security Control')
											self.setSecurityControl(c,response.geturl(),html)
									if not passset: raise Exception('No Pass Control')
									break
								except:
									ERROR('WRONG FORM (Password): %s' % ct,hide_tb=True)
										
					if not userset or not passset:
						LOG('FAILED TO FIND USER AND/OR PASSWORD CONTROLS')
						return False
				except:
					LOG('FAILED')
					return False
		response = self.browser.submit()
		html = response.read()
		#import codecs
		#codecs.open('/home/ruuk/test.txt','w','utf8').write(html.decode('utf8'))
		self.lastHTML = html + 'logout'
		#if not 'action="%s' % self.forms.get('login_action','@%+#') in html:
		if self.cookieJar is not None:
			self.cookieJar.save()
			
		self._loggedIn = True
		if self.isLoggedIn():
			LOG('LOGGED IN')
			return True
		LOG('FAILED TO LOGIN')
		return False
		
	def checkLogin(self,callback=None):
		#raise Exception('TEST')
		loginURL = ''
		if 'login.php?' in self.lastURL:
			loginURL = self.lastURL
		if self.isLoggedIn(): return True
		if not callback: callback = self.fakeCallback
		if not self.canLogin():
			self._loggedIn = False
			return False
		if not self.browser or self.needsLogin or not self.isLoggedIn():
			self.needsLogin = False
			if not callback(5,__language__(30100)): return False
			if not self.login(loginURL):
				self._loggedIn = False
			else:
				self._loggedIn = True
		
		return self._loggedIn
		
	def browserReadURL(self,url,callback):
		if not callback(30,__language__(30101)): return ''
		response = self.browser.open(url)
		self.lastURL = response.geturl()
		if not callback(60,__language__(30102)): return ''
		return response.read()
		
	def canLogin(self):
		return self.user and self.password
	
	def readURL(self,url,callback=None,force_login=False,is_html=True,force_browser=False):
		if not url:
			LOG('ERROR - EMPTY URL IN readURL()')
			return ''
		if not callback: callback = self.fakeCallback
		
		if force_browser:
			self.checkBrowser()
			data = self.browserReadURL(url,callback)
		elif self.canLogin() and (self.isLoggedIn() or self.formats.get('login_required') == 'True' or force_login or self.alwaysLogin):
			if not self.checkLogin(callback=callback): return ''
			data = self.browserReadURL(url,callback)
			if self.forms.get('login_action','@%+#') in data:
				self.login()
				data = self.browserReadURL(url,callback)
		else:
			if not callback(5,__language__(30101)): return ''
			req = urllib2.urlopen(url)
			self.lastURL = req.geturl()
			encoding = req.info().get('content-type').split('charset=')[-1]
			if not callback(50,__language__(30102)): return ''
			data = unicode(req.read(),encoding).encode(ENCODING)
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
		if not html: html = self.MC.lineFilter.sub('',self.lastHTML)
		if not html: return None
		pm_counts = None
		ct = 0
		while not pm_counts:
			ct += 1
			if self.filters.get('pm_counts%s' % ct):
				pm_counts = re.search(self.filters.get('pm_counts%s' % ct),html)
			else:
				break
		if pm_counts: return pm_counts.groupdict()
		return None
		
	def getLogo(self,html):
		logo = self.urls.get('logo')
		if logo: return logo
		try:
			if self.filters.get('logo'): logo = re.findall(self.filters['logo'],html)[0]
		except:
			ERROR("ERROR GETTING LOGO IMAGE")
		if logo: return self.makeURL(logo)
		return  'http://%s/favicon.ico' % self.forum
		
	def getForums(self,callback=None,donecallback=None):
		if not callback: callback = self.fakeCallback
		try:
			html = self.readURL(self.getURL('forums'),callback=callback)
		except:
			em = ERROR('ERROR GETTING FORUMS')
			callback(-1,'%s' % em)
			return self.finish(FBData(error=em),donecallback)
		
		if not html or not callback(80,__language__(30103)):
			return self.finish(FBData(error=html and 'CANCEL' or 'EMPTY HTML'),donecallback)
		
		html = self.MC.lineFilter.sub('',html)
		forums = re.finditer(self.filters['forums'],html)
		logo = self.getLogo(html)
		pm_counts = self.getPMCounts(html)
		callback(100,__language__(30052))
		
		return self.finish(FBData(forums,extra={'logo':logo,'pm_counts':pm_counts}),donecallback)
		
	def getThreads(self,forumid,page='',callback=None,donecallback=None,page_data=None):
		if not callback: callback = self.fakeCallback
		url = self.getPageUrl(page,'threads',fid=forumid)
		html = self.readURL(url,callback=callback)
		if not html or not callback(80,__language__(30103)):
			return self.finish(FBData(error=html and 'CANCEL' or 'EMPTY HTML'),donecallback)
		if self.filters.get('threads_start_after'): html = html.split(self.filters.get('threads_start_after'),1)[-1]
		threads = re.finditer(self.filters['threads'],self.MC.lineFilter.sub('',html))
		if self.formats.get('forums_in_threads','False') == 'True':
			forums = re.finditer(self.filters['forums'],html)
			threads = (forums,threads)
		callback(100,__language__(30052))
		pd = self.getPageInfo(html,page,page_type='threads')
		return self.finish(FBData(threads,pd),donecallback)
		
	def getReplies(self,threadid,forumid,page='',lastid='',pid='',callback=None,donecallback=None,page_data=None):
		if not callback: callback = self.fakeCallback
		url = self.getPageUrl(page,'replies',tid=threadid,fid=forumid,lastid=lastid,pid=pid)
		html = self.readURL(url,callback=callback)
		if not html or not callback(80,__language__(30103)):
			return self.finish(FBData(error=html and 'CANCEL' or 'EMPTY HTML'),donecallback)
		html = self.MC.lineFilter.sub('',html)
		replies = re.findall(self.filters['replies'],html)
		topic = re.search(self.filters.get('thread_topic','%#@+%#@'),html)
		if not threadid:
			threadid = re.search(self.filters.get('thread_id','%#@+%#@'),html)
			threadid = threadid and threadid.group(1) or ''
		topic = topic and topic.group(1) or ''
		sreplies = []
		for r in replies:
			try:
				post = ForumPost(re.search(self.filters['post'],self.MC.lineFilter.sub('',r)))
				sreplies.append(post)
			except:
				post = ForumPost()
				sreplies.append(post)
		pd = self.getPageInfo(html,page,page_type='replies')
		pd.setThreadData(topic,threadid)
		callback(100,__language__(30052))
		
		return self.finish(FBData(sreplies,pd),donecallback)
		
	def hasPM(self):
		return bool(self.urls.get('private_messages_xml') or self.urls.get('private_messages_csv'))
	
	def getPrivateMessages(self,callback=None,donecallback=None):
		if not callback: callback = self.fakeCallback
		#if not self.checkLogin(callback=callback): return None, None
		pms = None
		if self.urls.get('private_messages_xml'):
			xml = self.readURL(self.getURL('private_messages_xml'),callback=callback,force_login=True,is_html=False)
			if not xml or not callback(80,__language__(30103)):
				return self.finish(FBData(error=xml and 'CANCEL' or 'NO MESSAGES'),donecallback)
			folders = re.search(self.filters.get('pm_xml_folders'),xml,re.S)
			if not folders:
				#return self.finish(FBData(error='Unable to get folders'),donecallback)
				return self.finish(FBData([]),donecallback)
			messages = re.finditer(self.filters.get('pm_xml_messages'),folders.group('inbox'),re.S)
			pms = []
			for m in messages:
				p = self.getForumPost(m.groupdict())
				p.setPostID(len(pms))
				p.isPM = True
				p.message = re.sub('[\t\r]','',p.message)
				p.makeAvatarURL()
				pms.append(p)
				
		elif self.urls.get('private_messages_csv'):
			csvstring = self.readURL(self.getURL('private_messages_csv'),callback=callback,force_login=True,is_html=False)
			if not csvstring or not callback(80,__language__(30103)):
				return self.finish(FBData(error=csvstring and 'CANCEL' or 'NO MESSAGES'),donecallback)
			columns = self.formats.get('pm_csv_columns').split(',')
			import csv
			cdata = csv.DictReader(csvstring.splitlines()[1:],fieldnames=columns)
			pms = []
			folder = self.formats.get('pm_csv_folder')
			for d in cdata:
				if folder and folder == d.get('folder'):
					p = self.getForumPost(pdict=d)
					p.isPM = True
					p.setPostID(len(pms))
					pms.append(p)
		callback(100,__language__(30052))
		pms.reverse()
		return self.finish(FBData(pms),donecallback)
			
	def hasSubscriptions(self):
		return bool(self.urls.get('subscriptions'))
	
	def getSubscriptions(self,page='',callback=None,donecallback=None,page_data=None):
		if not callback: callback = self.fakeCallback
		#if not self.checkLogin(callback=callback): return None
		url = self.getPageUrl(page,'subscriptions')
		html = self.readURL(url,callback=callback,force_login=True)
		if not html or not callback(80,__language__(30103)):
			return self.finish(FBData(error=html and 'CANCEL' or 'EMPTY HTML'),donecallback)
		threads = re.finditer(self.filters['subscriptions'],self.MC.lineFilter.sub('',html))
		callback(100,__language__(30052))
		pd = self.getPageInfo(html,page,page_type='threads')
		return self.finish(FBData(threads,pd),donecallback)
		
	def getPageInfo(self,html,page,page_type='',page_urls=None,page_data=None):
		if not self.filters.get('page') and not self.filters.get('next'): return None
		next_page = self.filters.get('next') and re.search(self.filters['next'],html) or None
		prev_page= None
		if page != '1':
			prev_page = self.filters.get('prev') and re.search(self.filters['prev'],html) or None
		page_disp = re.search(self.filters['page'],html)
		if page_data:
			return page_data.update(page_disp,next_page,prev_page,page_type=page_type,page_urls=page_urls)
		else:
			return self.getPageData(page_disp,next_page,prev_page,page_type=page_type,page_urls=page_urls)
		
	def getPageUrl(self,page,sub,pid='',tid='',fid='',lastid='',suburl=''):
		suburl = suburl or self.urls.get(sub,'')
		if not suburl: return None
		if page and not str(page).isdigit(): return self.makeURL(page)
		if sub == 'replies' and page and int(page) < 0:
			gnp = self.urls.get('gotonewpost','')
			page = self.URLSubs(gnp,pid=lastid)
		else:
			if page:
				try:
					if int(page) < 0: page = '9999'
				except:
					ERROR('CALCULATE START PAGE ERROR - PAGE: %s' % page)
				page = str(page)
				page = self.urls.get('page_arg','').replace('!PAGE!',page) or page
		sub = self.URLSubs(suburl,pid=pid,tid=tid,fid=fid,page=page)
		return self._url + sub
		
	def getURL(self,name):
		return self._url + self.urls.get(name,'')
		
	def predicateLogin(self,formobj):
		return self.forms.get('login_action','@%+#') in formobj.action
		
	def getForm(self,html,action,name=None):
		if not action: return None
		try:
			forms = self.mechanize.ParseString(''.join(re.findall('<form.*?action="%s[^>]*?>.+?</form>(?s)' % re.escape(action),html)),self._url)
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
			
	def URLSubs(self,url,pid='',tid='',fid='',page='',post=None):
		if post:
			url = url.replace('!POSTID!',str(post.pid)).replace('!THREADID!',str(post.tid)).replace('!FORUMID!',str(post.fid)).replace('!PAGE!',str(page))
		else:
			url = url.replace('!POSTID!',str(pid)).replace('!THREADID!',str(tid)).replace('!FORUMID!',str(fid)).replace('!PAGE!',str(page))
		#removes empty vars
		return re.sub('(?:\w+=&)|(?:\w+=$)','',url)
		
	def postURL(self,post):
		return self.URLSubs(self.getURL('newpost'),post=post)
	
	def editURL(self,post):
		return self.URLSubs(self.getURL('editpost'),post=post)
	
	def predicatePost(self,formobj):
		return self.forms.get('post_action','@%+#') in formobj.action
	
	def predicateEditPost(self,formobj):
		return self.forms.get('edit_post_action','@%+#') in formobj.action
		
	def fakeCallback(self,pct,message=''): return True
	
	def post(self,post,callback=None,edit=False):
		if not callback: callback = self.fakeCallback
		if not self.checkLogin(callback=callback):
			post.error = 'Could not log in'
			return False
		pre = ''
		if edit or post.isEdit:
			pre = 'edit_'
			url = self.editURL(post)
		else:
			url = self.postURL(post)
			
		res = self.browser.open(url)
		#print res.info()
		html = res.read()
		#open('/home/ruuk/test.txt','w').write(html)
		if self.forms.get('login_action','@%+#') in html:
			callback(5,__language__(30100))
			if not self.login():
				post.error = 'Could not log in'
				return False
			res = self.browser.open(url)
			html = res.read()
		callback(40,__language__(30105))
		selected = False
		try:
			if self.forms.get(pre + 'post_name'):
				self.browser.select_form(self.forms.get(pre + 'post_name'))
				LOG('FORM SELECTED BY NAME')
			else:
				if edit or post.isEdit:
					self.browser.select_form(predicate=self.predicateEditPost)
				else:
					self.browser.select_form(predicate=self.predicatePost)
				LOG('FORM SELECTED BY ACTION')
			selected = True
		except:
			ERROR('NO FORM 1')
			
		if not selected:
			form = self.getForm(html,self.forms.get(pre + 'post_action',''),self.forms.get(pre + 'post_name',''))
			if form:
				self.browser.form = form
			else:
				post.error = 'Could not find form.'
				return False
		try:
			if post.title: self.browser[self.forms[pre + 'post_title']] = post.title
			self.browser[self.forms[pre + 'post_message']] = post.message
			self.setControls(pre + 'post_controls%s')
			wait = int(self.forms.get(pre + 'post_submit_wait',0))
			if wait: callback(60,__language__(30107) % wait)
			time.sleep(wait) #or this will fail on some forums. I went round and round to find this out.
			callback(80,__language__(30106))
			res = self.browser.submit(name=self.forms.get(pre + 'post_submit_name'),label=self.forms.get(pre + 'post_submit_value'))
			html = res.read()
			#open('/home/ruuk/test.txt','w').write(html)
			err = self.checkForError(html)
			if err:
				post.error = err
				return False
			callback(100,__language__(30052))
		except:
			post.error = ERROR('FORM ERROR')
			return False
			
		return True
		
	def checkForError(self,html):
		errm = re.search('(<div[^>]*?class="[^"]*?error[^"]*?[^>]*?>)(.*?)</div>(?is)',html)
		if errm:
			if 'hidden' in errm.group(1):
				return None
			error = re.sub('[\n\t\r]','',errm.group(2))
			error = re.sub('<[^>]*?>','\n',error).replace('\n\n','\n').replace('\n','[CR]')
			return error
		return None
	
	def doPrivateMessage(self,post,callback=None):
		return self.doForm(	self.urls.get('pm_new_message'),
							self.forms.get('pm_name'),
							self.forms.get('pm_action'),
							{self.forms.get('pm_recipient'):post.to,self.forms.get('pm_title'):post.title,self.forms.get('pm_message'):post.message},
							callback=callback)
		
	def deletePrivateMessage(self,post,callback=None):
		return self.deletePrivateMessageViaIndex(post, callback)
		
	def deletePrivateMessageViaIndex(self,post,callback=None):
		html = self.readURL(self.urls.get('private_messages_inbox'),callback=callback,force_login=True)
		if not html: return False
		pmid_list = re.findall(self.filters.get('pm_pmid_list'),html,re.S)
		try:
			pmid_list.reverse()
			pmid = pmid_list[int(post.pid)]
		except:
			err = ERROR('DELETE PM VIA INDEX ERROR')
			post.error = err
			return False
			
		return self.doForm(	self.urls.get('private_messages_delete').replace('!PMID!',pmid),
							self.forms.get('pm_delete_name'),
							self.forms.get('pm_delete_action'),
							controls='pm_delete_control%s',
							callback=callback)
						
	def doForm(self,url,form_name=None,action_match=None,field_dict=None,controls=None,submit_name=None,submit_value=None,wait='1',callback=None):
		field_dict = field_dict or {}
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
		post.error = 'Failed'
		if not self.checkLogin(): return post
		res = self.browser.open(self.URLSubs(self.getURL('deletepost'),post=post))
		html = res.read()
		
		if self.forms.get('login_action','@%+#') in html:
			if not self.login():
				post.error = 'Could not log in.'
				return False
			try:
				res = self.browser.open(self.URLSubs(self.getURL('deletepost'),post=post))
				html = res.read()
			except:
				post.error = ERROR('Error deleting post')
			
		selected = False
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
				post.error = 'Could not find form'
				return False
		
		try:
			#self.browser.find_control(name="deletepost").value = ["delete"]
			self.setControls('delete_control%s')
			#self.browser["reason"] = reason[:50]
			self.browser.submit()
		except:
			ERROR('DELETE NO CONTROL')
			post.error = 'Could not find form controls'
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
		
	def canPost(self): return self.isLoggedIn()
	
	def canDelete(self,user,target='POST'):
		if target == 'POST':
			return self.user == user and self.urls.get('deletepost') and self.isLoggedIn()
		else:
			return bool(self.urls.get('private_messages_delete')) and self.isLoggedIn()
	
	def getQuoteFormat(self):
		return None
	
	def getPostForEdit(self,post):
		pm =  forumbrowser.PostMessage().fromPost(post)
		pm.isEdit = True
		return pm
		
	def editPost(self,pm,callback=None):
		return self.post(pm,callback,edit=True)
	
	def canEditPost(self,user): return user == self.user and self.isLoggedIn() and self.canPost()
	
	def getQuoteStartFormat(self):
		return self.filters.get('quote_start','[QUOTE]')
	