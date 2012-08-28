import xbmcaddon #@UnresolvedImport
from htmltoxbmc import HTMLConverter
import re, os, sys, time, urllib2, urlparse
import xbmc, xbmcgui #@UnresolvedImport
import mechanize, threading


__plugin__ = 'Web Viewer'
__author__ = 'ruuk (Rick Phillips)'
__url__ = 'http://code.google.com/p/webviewer-xbmc/'
__date__ = '01-19-2011'
__version__ = '0.9.1'
__addon__ = xbmcaddon.Addon(id='script.web.viewer')
__language__ = __addon__.getLocalizedString

THEME = 'Default'

ACTION_MOVE_LEFT = 1
ACTION_MOVE_RIGHT = 2
ACTION_MOVE_UP = 3
ACTION_MOVE_DOWN = 4
ACTION_PAGE_UP = 5
ACTION_PAGE_DOWN = 6
ACTION_SELECT_ITEM = 7
ACTION_HIGHLIGHT_ITEM = 8
ACTION_PARENT_DIR = 9
ACTION_PARENT_DIR2 = 92
ACTION_PREVIOUS_MENU = 10
ACTION_SHOW_INFO = 11
ACTION_PAUSE = 12
ACTION_STOP = 13
ACTION_NEXT_ITEM = 14
ACTION_PREV_ITEM = 15
ACTION_PLAYER_FORWARD = 77
ACTION_PLAYER_REWIND = 78 
ACTION_SHOW_GUI = 18
ACTION_PLAYER_PLAY = 79
ACTION_MOUSE_LEFT_CLICK = 100
ACTION_CONTEXT_MENU = 117

#Actually it's show codec info but I'm using in a threaded callback
ACTION_RUN_IN_MAIN = 27

import locale
loc = locale.getdefaultlocale()
print loc
ENCODING = loc[1] or 'utf-8'

def ENCODE(string):
	return string.encode(ENCODING,'replace')

def ERROR(message):
	errtext = sys.exc_info()[1]
	print 'WEBVIEWER - %s::%s (%d) - %s' % (message, sys.exc_info()[2].tb_frame.f_code.co_name, sys.exc_info()[2].tb_lineno, errtext)
	return str(errtext)
	
def LOG(message):
	print 'WEBVIEWER: %s' % ENCODE(str(message))

LOG('Version: ' + __version__)
LOG('Python Version: ' + sys.version)
ATV2 = xbmc.getCondVisibility('System.Platform.ATV2')
if ATV2: LOG('Running on ATV2')

def clearDirFiles(filepath):
	if not os.path.exists(filepath): return
	for f in os.listdir(filepath):
		f = os.path.join(filepath, f)
		if os.path.isfile(f): os.remove(f)
		
class ResponseData:
	def __init__(self, url='', content='', data='', content_disp=''):
		self.url = url
		self.content = content
		self.contentDisp = content_disp
		self.data = data
		
	def hasText(self):
		return self.content.startswith('text') and self.data
		
class WebReader:
	def __init__(self):
		self.browser = mechanize.Browser()
		self.browser.set_handle_robots(False)
		self.browser.set_handle_redirect(True)
		self.browser.set_handle_refresh(True, honor_time=False)
		self.browser.set_handle_equiv(True)
		self.browser.set_debug_redirects(True)
		self.browser.addheaders = [('User-agent', 'Mozilla/3.0 (compatible)')]
		#self.browser.addheaders = [('User-agent','Mozilla/5.0 (X11; Linux i686; rv:2.0.1) Gecko/20100101 Firefox/4.0.1')]
		
	def setBrowser(self,browser):
		LOG('Using Alternate Browser')
		self.browser = browser
		
	def getWebPage(self, url, callback=None):
		LOG('Getting Page at URL: ' + url)
		if not callback: callback = self.fakeCallback
		resData = ResponseData(url)
		id = ''
		urlsplit = url.split('#', 1)
		if len(urlsplit) > 1: url, id = urlsplit
		try:
			resData = self.readURL(url, callback)
		except:
			err = ERROR('ERROR READING PAGE')
			LOG('URL: %s' % url)
			xbmcgui.Dialog().ok('ERROR', __language__(30100), err)
			return None
		resData = self.checkRedirect(resData, callback)
		if not callback(80, __language__(30101)): return None
		if not resData: return None
		formsProcessed = True
		forms = []
		if resData.hasText():
			try:
				forms = self.browser.forms()
			except:
				formsProcessed = False
			if not formsProcessed:
				try:
					res = self.browser.response()
					res.set_data(self.cleanHTML(res.get_data()))
					self.browser.set_response(res)
					forms = self.browser.forms()
				except:
					ERROR('Could not process forms')
				
		return WebPage(resData, id=id, forms=resData.data and forms or [])
	
	def cleanHTML(self, html):
		return re.sub('<![^>]*?>', '', html)
		
	def checkRedirect(self, resData, callback=None):
		if not callback: callback = self.fakeCallback
		match = re.search('<meta[^>]+?http-equiv="Refresh"[^>]*?URL=(?P<url>[^>"]+?)"[^>]*?/>', resData.data)
		#print html
		if match:
			LOG('REDIRECTING TO %s' % match.group('url'))
			if not callback(3, __language__(30102)): return None
			try:
				url = match.group('url')
				return self.readURL(url, callback)
			except:
				#err = 
				ERROR('ERROR READING PAGE REDIRECT')
				LOG('URL: %s' % url)
				#xbmcgui.Dialog().ok('ERROR','Error loading page.',err)
		return resData
	
	def readURL(self, url, callback):
		if not callback(5, __language__(30103)): return None
		response = None
		try:
			response = self.browser.open(url)
		except Exception, e:
			#If we have a redirect loop, this is a same url cookie issue. Just use the response in the error.
			if 'redirect' in str(e) and 'infinite loop' in str(e):
				response = e
			else:
				raise
		content = response.info().get('content-type', '')
		contentDisp = response.info().get('content-disposition', '')
		#print response.info()
		if not content.startswith('text'): return ResponseData(response.geturl(), content, content_disp=contentDisp) 
		if not callback(30, __language__(30104)): return None
		return ResponseData(response.geturl(), content, response.read())
		
	def submitForm(self, form, submit_control, callback):
		if not callback: callback = self.fakeCallback
		self.browser.form = form
		ct = 0
		if submit_control:
			for c in form.controls:
				if c.type == 'submit':
					if c == submit_control: break
					ct += 1 
		if not callback(5, __language__(30105)): return None
		try:
			res = self.browser.submit(nr=ct)
		except:
			self.browser.back()
			return None
		if not callback(60, __language__(30106)): return None
		html = res.read()
		resData = self.checkRedirect(ResponseData(res.geturl(), data=html), callback=callback) #@UnusedVariable
		if not callback(80, __language__(30101)): return None
		if not resData: return None
		return WebPage(resData, self.browser.geturl(), forms=resData.data and self.browser.forms() or [])
		
	def setFormValue(self,form,key,value):
		self.browser.form = form
		try:
			self.browser[key] = value
			return True
		except:
			return False
		
	def getForm(self, html, action, name=None):
		if not action: return None
		try:
			forms = self.mechanize.ParseString(''.join(re.findall('<form\saction="%s.+?</form>' % re.escape(action), html, re.S)), self._url)
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
		
	def fakeCallback(self, pct, message=''): return True
						
	def doForm(self, url, form_name=None, action_match=None, field_dict={}, controls=None, submit_name=None, submit_value=None, wait='1', callback=None):
		if not callback: callback = self.fakeCallback
		if not self.checkLogin(callback=callback): return False
		res = self.browser.open(url)
		html = res.read()
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
			form = self.getForm(html, action_match, form_name)
			if form:
				self.browser.form = form
			else:
				return False
		try:
			for k in field_dict.keys():
				if field_dict[k]: self.browser[k] = field_dict[k]
			self.setControls(controls)
			wait = int(wait)
			time.sleep(wait) #or this will fail on some forums. I went round and round to find this out.
			res = self.browser.submit(name=submit_name, label=submit_value)
		except:
			ERROR('FORM ERROR')
			return False
			
		return True
		
	def setControls(self, controls):
		if not controls: return
		x = 1
		for control in controls:
			ctype, rest = control.split(':', 1)
			ftype, rest = rest.split('.', 1)
			name, value = rest.split('=')
			control = self.browser.find_control(**{ftype:name})
			if ctype == 'radio':
				control.value = [value]
			elif ctype == 'checkbox':
				control.items[0].selected = value == 'True'
			x += 1

################################################################################
# Web Page
################################################################################
class WebPage:
	def __init__(self, resData, id='', forms=[]):
		self.url = resData.url
		end = ''
		#if not '<a ' in resData.data and not '<img ' in resData.data and not '<form ' in resData.data: 
		#	end = '<a href="#END">END OF PAGE</a><a name="#END"></a>'
		self.html = resData.data
		self.content = resData.content
		self.contentDisp = resData.contentDisp
		self.id = id
		self.title = ''
		self.forms = []
		self.imageURLDict = {}
		self._imageCount = -1
		self._labels = None
		self._headers = None
		self._displayWithIDs = ''
		self._display = ''
		self.idFilter = re.compile('\[\{(.+?)\}\]', re.S)
		self.linkCTag = '[COLOR %s]' % HC.linkColor
		self.formCTag = '[COLOR %s]' % HC.formColorB
		self.imageTag = '[COLOR %s]' % HC.imageColor
		self.frameCTag = '[COLOR %s]' % HC.frameColor
		self._links = []
		self._images = []
		self._frames = []
		self._cleanHTML = ''
		self.elements = []
		ct = 0
		for f in forms:
			self.forms.append(Form(f, ct))
			ct += 1
		if self.html: self.processPage()
		#Fix for pages without elements
		if not self.elements:
			element = Link(HC.linkFilter.search('<a href="#END">NO LINKS ON PAGE</a>'), self.url, 0)
			element.elementIndex = 0
			element.displayPageIndex = len(self._display)
			element.lineNumber = len(self.forDisplay().split('[CR]'))-1
			self._links.append(element)
			self.elements.append(element)
			self._display += HC.linkFilter.sub(HC.linkConvert,'[CR]<a href="#END"> </a>')
			self._displayWithIDs += HC.linkFilter.sub(HC.linkConvert,'[CR]<a href="#END"> </a>')
		
	def getFileName(self):
		fn_m = re.search('filename="([^"]*)"', self.contentDisp)
		if not fn_m: return ''
		return fn_m.group(1)
	
	def isDisplayable(self):
		return bool(self.html)
	
	def processPage(self):
		disp = self.forDisplay()
		#import codecs
		#codecs.open('/home/ruuk/test.txt','w',encoding='utf-8').write(disp)
		alltags = '(%s|%s|%s|%s)' % (re.escape(self.linkCTag), re.escape(self.imageTag), re.escape(self.formCTag), re.escape(self.frameCTag))
		types = {self.linkCTag:PE_LINK, self.imageTag:PE_IMAGE, self.formCTag:PE_FORM, self.frameCTag:PE_FRAME}
		pre = None
		stack = ''
		ct = 0
		fct = 0
		lct = 0
		ict = 0
		frct = 0
		self.links()
		self.images()
		self.frames()
		self.elements = []
		for part in re.split(alltags, disp):
			if pre != None:
				stack += pre
				index = len(stack)
				lines = stack.count('[CR]')
				stack += part
				pre = None
				type = types[part]
				if type == PE_LINK:
					element = self._links[lct]
					lct += 1
				elif type == PE_IMAGE:
					element = self._images[ict]
					ict += 1
				elif type == PE_FORM:
					element = self.forms[fct]
					fct += 1
				elif type == PE_FRAME:
					element = self._frames[frct]
					frct += 1
				element.elementIndex = ct
				element.displayPageIndex = index
				element.lineNumber = lines
				self.elements.append(element)
				ct += 1
			else:
				pre = part
		
	def getNextElementAfterPageIndex(self, index):
		for e in self.elements:
			if e.displayPageIndex >= index:
				return e
			
	def getElementByTypeIndex(self, type, index):
		for e in self.elements:
			if e.type == type and e.typeIndex == index:
				return e
	
	def forDisplay(self):
		if self._display: return self._display
		self.forDisplayWithIDs()
		return self._display
	
	def forDisplayWithIDs(self):
		if self._displayWithIDs: return self._displayWithIDs, self.title
		self._displayWithIDs, self.title = HC.htmlToDisplayWithIDs(self.html)
		self._display = self.idFilter.sub('', self._displayWithIDs)
		return self._displayWithIDs, self.title
		
	def imageCount(self):
		if self._imageCount >= 0: return self._imageCount
		self.imageUrls()
		return self._imageCount()
	
	def cleanHTML(self):
		if self._cleanHTML: return self._cleanHTML
		self._cleanHTML = HC.cleanHTML(self.html)
		return self._cleanHTML

	def images(self):
		if self._images: return self._images
		self.getImageURLDict()
		ct = 0
		for url in HC.imageFilter.findall(HC.linkFilter.sub('', self.cleanHTML()), re.S):
			shortIndex = self.imageURLDict.get(url)
			self._images.append(Image(url, ct, shortIndex, base_url=self.url))
			ct += 1
		return self._images
			
	def imageURLs(self):
		urls = []
		ct = 0
		for url in HC.imageFilter.findall(HC.linkFilter.sub('', self.cleanHTML()), re.S):
			for u in urls:
				if u == url: break
			else:
				urls.append(url)
			ct += 1
		self._imageCount = ct
		return urls
		
	def getImageURLDict(self):
		if self.imageURLDict: return self.imageURLDict
		urls = []
		ct = 0
		for url in HC.imageFilter.findall(HC.linkFilter.sub('', self.cleanHTML()), re.S):
			urls.append(url)
			if not url in self.imageURLDict:
				self.imageURLDict[url] = ct
				ct += 1
		return self.imageURLDict
		
	def linkImageURLs(self):
		#TODO: UNUSED - Remove
		return re.findall('<a.+?href="(http://.+?\.(?:jpg|png|gif|bmp))".+?</a>', self.cleanHTML(), re.S)
		
	def linkURLs(self):
		html = unicode(self.cleanHTML(), 'utf8', 'replace')
		return HC.linkFilter.finditer(html)
		
	def links(self):
		if self._links: return self._links
		ct = 0
		for m in self.linkURLs():
			self._links.append(Link(m, self.url, ct))
			ct += 1
		return self._links
	
	def frameMatches(self):
		html = unicode(self.cleanHTML(), 'utf8', 'replace')
		return HC.frameFilter.finditer(html)
	
	def frames(self):
		if self._frames: return self._frames
		ct = 0
		for m in self.frameMatches():
			self._frames.append(Frame(m, self.url, ct))
			ct += 1
		return self._frames
	
	def labels(self):
		if self._labels: return self._labels, self._headers
		self._labels = {}
		self._headers = {}
		for m in HC.labelFilter.finditer(self.html, re.S):
			self._labels[m.group('inputid')] = HC.convertHTMLCodes(HC.tagFilter.sub('', m.group('label')))
		for m in HC.altLabelFilter.finditer(HC.lineFilter.sub('', self.html)):
			if not m.group('inputid') in self._labels:
				self._labels[m.group('inputid')] = HC.convertHTMLCodes(m.group('label'))
				header = m.group('header')
				if header: header = header.strip()
				if header: self._headers[m.group('inputid')] = HC.convertHTMLCodes(header)
		for k in self._labels.keys():
			if self._labels[k].endswith(':'):
				self._labels[k] = self._labels[k][:-1]
		return self._labels, self._headers
	
	def getForm(self, url=None, name=None, action=None, index=None):
		if url:
			if not re.match(url, self.url): return None
			LOG('URL MATCH: %s' % self.url)
		if name:
			idx = 0
			for f in self.forms:
				if name == f.form.name or name == f.form.attrs.get('id'):
					if index != None:
						if index != idx: continue
					return f
				idx += 1
		if action:
			idx = 0
			for f in self.forms:
				if action in f.form.action:
					LOG('ACTION MATCH: %s' % action)
					if index != None:
						if index != idx:
							LOG('WRONG INDEX: %s instead of %s' % (idx, index))
							idx += 1
							continue
					return f
				idx += 1
		if index:
			ct = 0
			for f in self.forms:
				if ct == index: return f
		return None
	
	def matches(self, url_regex=None, html_regex=None):
		if not url_regex and not html_regex: return False
		if url_regex and not re.match(url_regex, self.url):
			LOG('AUTOCLOSE: NO URL MATCH')
			return False
		if html_regex and not re.match(html_regex, self.html):
			LOG('AUTOCLOSE: NO HTML MATCH')
			return False
		return True
	
	def getTitle(self):
		return self.title or self.url
		
PE_LINK = 'LINK'
PE_IMAGE = 'IMAGE'
PE_FORM = 'FORM'
PE_FRAME = 'FRAME'

class PageElement:
	def __init__(self, type=0, type_index= -1):
		self.typeIndex = type_index
		self.elementIndex = -1
		self.displayPageIndex = -1
		self.lineNumber = -1
		
		self.type = type

class Image(PageElement):
	def __init__(self, url='', image_index= -1, short_index= -1, base_url=''):
		PageElement.__init__(self, PE_IMAGE, image_index)
		self.baseUrl = base_url
		self.url = url
		self.shortIndex = short_index
		
	def fullURL(self):
		return fullURL(self.baseUrl, self.url)
		
class Form(PageElement):
	def __init__(self, form=None, form_index= -1):
		PageElement.__init__(self, PE_FORM, form_index)
		self.form = form

class LinkBase:
	def cannotBeFollowed(self):
		if 'javascript:' in self.url: return 'Javascript'
		if 'mailto:' in self.url: return 'Email'
		prot_m = re.match('\w+://', self.url)
		if prot_m:
			if not re.match('(?:http|https|ftp)://', self.url): return prot_m.group(0)
		return None
	
	def fullURL(self):
		return fullURL(self.baseUrl, self.url)
	
	def isImage(self): return False
	
class Frame(PageElement, LinkBase):
	def __init__(self, match=None, url='', frame_index= -1):
		PageElement.__init__(self, PE_FRAME, frame_index)
		self.baseUrl = url
		self.url = ''
		if match: self.url = match.group('url')

class Link(PageElement, LinkBase):
	def __init__(self, match=None, url='', link_index= -1):
		PageElement.__init__(self, PE_LINK, link_index)
		self.baseUrl = url
		self.url = ''
		self.text = ''
		self.image = ''
		self._isImage = False
		
		if match:
			self.url = match.group('url')
			text = match.group('text')
			image_m = HC.imageFilter.search(text)
			if image_m:
				self.image = fullURL(self.baseUrl,image_m.group('url'))
				alt_m = re.search('alt="([^"]+?)"', image_m.group(0))
				if alt_m: text = alt_m.group(1)
			text = HC.tagFilter.sub('', text).strip()
			self.text = HC.convertHTMLCodes(text)
		self.processURL()
			
	def processURL(self):
		if not self.url: return
		self.url = self.url.replace('&amp;', '&')
		self._isImage = bool(re.search('http://.+?\.(?:jpg|png|gif|bmp)$', self.url))
		if self._isImage: return
			
	def urlShow(self):
		return self.fullURL()
		
	def isImage(self):
		return self._isImage

def fullURL(baseUrl, url):
	if url.startswith('ftp://') or url.startswith('http://') or url.startswith('https://') or url.startswith('file:/'): return url
	if not (baseUrl.startswith('file://') or baseUrl.startswith('file:///')) and baseUrl.startswith('file:/'): baseUrl = baseUrl.replace('file:/','file:///')
	pre = baseUrl.split('://', 1)[0] + '://'
	if not url.startswith(pre):
		base = baseUrl.split('://', 1)[-1]
		base = base.rsplit('/', 1)[0]
		domain = base.split('/', 1)[0]
		if url.startswith('/'):
			if url.startswith('//'):
				url =  pre.split('/', 1)[0] + url
			else:
				url =  pre + domain + url
		elif url.startswith('.'):
			if not base.endswith('/'): base += '/'
			url =  pre + base + url
		else:
			url =  pre + domain + '/' + url
	return url

class URLHistory:
	def __init__(self, first):
		self.index = 0
		self.history = [first]
		
	def addURL(self, old, new):
		self.history[self.index].copy(old) 
		self.history = self.history[0:self.index + 1]
		self.history.append(new)
		self.index = len(self.history) - 1
		
	def gotoIndex(self, index):
		if index < 0 or index >= self.size(): return None
		self.index = index
		return self.history[self.index]
		
	def goBack(self, line):
		self.history[self.index].line = line
		self.index -= 1
		if self.index < 0: self.index = 0
		return self.history[self.index]
	
	def goForward(self, line):
		self.history[self.index].line = line
		self.index += 1
		if self.index >= self.size(): self.index = self.size() - 1
		return self.history[self.index]
		
	def canGoBack(self):
		return self.index > 0
	
	def canGoForward(self):
		return self.index < self.size() - 1
	
	def updateCurrent(self, url, title=None):
		self.history[self.index].url = url
		if title: self.history[self.index].title = title
		
	def size(self):
		return len(self.history)
	
class HistoryLocation:
	def __init__(self, url='', line=0, title=''):
		self.url = url
		self.line = line
		self.title = title
		
	def getTitle(self):
		return self.title or self.url
	
	def copy(self, other):
		if other.url: self.url = other.url
		if other.title: self.title = other.title
		self.line = other.line
		
######################################################################################
# Base Window Classes
######################################################################################
class StoppableThread(threading.Thread):
	def __init__(self, group=None, target=None, name=None, args=(), kwargs={}):
		self._stop = threading.Event()
		threading.Thread.__init__(self, group=group, target=target, name=name, args=args, kwargs=kwargs)
		
	def stop(self):
		self._stop.set()
		
	def stopped(self):
		return self._stop.isSet()
		
class StoppableCallbackThread(StoppableThread):
	def __init__(self, target=None, name=None):
		self._target = target
		self._stop = threading.Event()
		self._finishedHelper = None
		self._finishedCallback = None
		self._progressHelper = None
		self._progressCallback = None
		StoppableThread.__init__(self, name=name)
		
	def setArgs(self, *args, **kwargs):
		self.args = args
		self.kwargs = kwargs
		
	def run(self):
		self._target(*self.args, **self.kwargs)
		
	def setFinishedCallback(self, helper, callback):
		self._finishedHelper = helper
		self._finishedCallback = callback
	
	def setProgressCallback(self, helper, callback):
		self._progressHelper = helper
		self._progressCallback = callback
		
	def stop(self):
		self._stop.set()
		
	def stopped(self):
		return self._stop.isSet()
		
	def progressCallback(self, *args, **kwargs):
		if self.stopped(): return False
		if self._progressCallback: self._progressHelper(self._progressCallback, *args, **kwargs)
		return True
		
	def finishedCallback(self, *args, **kwargs):
		if self.stopped(): return False
		if self._finishedCallback: self._finishedHelper(self._finishedCallback, *args, **kwargs)
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
		
	def setStopControl(self, control):
		self._stopControl = control
		control.setVisible(False)
		
	def setProgressCommands(self, start=None, progress=None, end=None):
		self._startCommand = start
		self._progressCommand = progress
		self._endCommand = end
		
	def onClick(self, controlID):
		if controlID == self._stopControl.getId():
			self.stopThread()
			return True
		return False
	
	def onAction(self, action):
		if action == ACTION_RUN_IN_MAIN:
			if self._function:
				self._function(*self._functionArgs, **self._functionKwargs)
				self._resetFunction()
				return True
		elif action == ACTION_PREVIOUS_MENU:
			if self._currentThread and self._currentThread.isAlive():
				self._currentThread.stop()
				if self._endCommand: self._endCommand()
				if self._stopControl: self._stopControl.setVisible(False)
			if self._isMain and len(threading.enumerate()) > 1:
				d = xbmcgui.DialogProgress()
				d.create(__language__(30107), __language__(30108))
				d.update(0)
				self.stopThreads()
				if d.iscanceled():
					d.close()
					return True
				d.close()
			return False
		elif action == ACTION_STOP:
			self.stopThread()
			return True
		return False
	
	def stopThreads(self):
		for t in threading.enumerate():
			if isinstance(t, StoppableThread): t.stop()
		for t in threading.enumerate():
			if t != threading.currentThread(): t.join()
			
	def _resetFunction(self):
		self._function = None
		self._functionArgs = []
		self._functionKwargs = {}
		
	def runInMain(self, function, *args, **kwargs):
		self._function = function
		self._functionArgs = args
		self._functionKwargs = kwargs
		xbmc.executebuiltin('Action(codecinfo)')
		
	def endInMain(self, function, *args, **kwargs):
		if self._endCommand: self._endCommand()
		if self._stopControl: self._stopControl.setVisible(False)
		self.runInMain(function, *args, **kwargs)
		
	def getThread(self, function, finishedCallback=None, progressCallback=None):
		if self._currentThread: self._currentThread.stop()
		if not progressCallback: progressCallback = self._progressCommand
		t = StoppableCallbackThread(target=function)
		t.setFinishedCallback(self.endInMain, finishedCallback)
		t.setProgressCallback(self.runInMain, progressCallback)
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
		
class BaseWindow(ThreadWindow):
	def __init__(self, *args, **kwargs):
		self._progMessageSave = ''
		ThreadWindow.__init__(self)
		xbmcgui.WindowXMLDialog.__init__(self)
	
	def onClick(self, controlID):
		return ThreadWindow.onClick(self, controlID)
			
	def onAction(self, action):
		if action == ACTION_PARENT_DIR or action == ACTION_PARENT_DIR2:
			action = ACTION_PREVIOUS_MENU
		if ThreadWindow.onAction(self, action): return
		xbmcgui.WindowXMLDialog.onAction(self, action)
	
	def startProgress(self):
		self._progMessageSave = self.getControl(104).getLabel()
		self.getControl(310).setWidth(1)
		self.getControl(310).setVisible(True)
	
	def setProgress(self, pct, message=''):
		w = int((pct / 100.0) * self.getControl(300).getWidth())
		self.getControl(310).setWidth(w)
		self.getControl(104).setLabel(message)
		return True
		
	def endProgress(self):
		self.getControl(310).setVisible(False)
		self.getControl(104).setLabel(self._progMessageSave)

######################################################################################
# Image Dialog
######################################################################################
class ImageDialog(BaseWindow, xbmcgui.WindowXMLDialog):
	def __init__(self, *args, **kwargs):
		self.image = kwargs.get('image')
		xbmcgui.WindowXML.__init__(self)
	
	def onInit(self):
		self.showImage()

	def onFocus(self, controlId):
		pass
		
	def showImage(self):
		self.getControl(102).setImage(self.image)
	
	def onClick(self, controlID):
		pass
	
	def onAction(self, action):
		if action == ACTION_PARENT_DIR or action == ACTION_PARENT_DIR2:
			action = ACTION_PREVIOUS_MENU
		xbmcgui.WindowXMLDialog.onAction(self, action)
		
######################################################################################
# Source Dialog
######################################################################################
class SourceDialog(BaseWindow, xbmcgui.WindowXMLDialog):
	def __init__(self, *args, **kwargs):
		self.source = kwargs.get('source')
	
	def onInit(self):
		self.showSource()

	def onFocus(self, controlId):
		pass
		
	def showSource(self):
		self.getControl(120).setText(self.source)
	
	def onClick(self, controlID):
		pass
	
	def onAction(self, action):
		if action == ACTION_PARENT_DIR or action == ACTION_PARENT_DIR2:
			action = ACTION_PREVIOUS_MENU
		elif action == ACTION_PAGE_UP or action == 104:
			action = ACTION_MOVE_UP
		elif action == ACTION_PAGE_DOWN  or action == 105:
			action = ACTION_MOVE_DOWN
		xbmcgui.WindowXMLDialog.onAction(self, action)
	
class LineItem:
	def __init__(self, text='', ids='', index=''):
		self.text = text
		self.IDs = ids
		self.index = index
		self.displayLen = len(HC.displayTagFilter.sub('', self.text.split('[CR]', 1)[0]))
		
class LineView:
	def __init__(self, view, scrollbar=None):
		self.view = view
		self.scrollBar = scrollbar
		if scrollbar:
			self.scrollY = scrollbar.getPosition()[1]
			self.scrollX = scrollbar.getPosition()[0]
			self.scrollSpan = view.getHeight() - scrollbar.getHeight()
		self.items = []
		self.pos = 0
		
	def setScroll(self):
		if not self.scrollBar: return
		y = self.scrollY + int((self.pos / float(self.size())) * self.scrollSpan)
		self.scrollBar.setPosition(self.scrollX, y)
		
	def reset(self):
		self.pos = 0
		self.items = []
		
	def setDisplay(self, text=None):
		if not text: self.currentText()
		self.display = text
		self.view.setText('[CR]' + text)
		self.view.scroll(0)
		self.setScroll()
		
	def currentText(self):
		if not self.items:
			LOG('LineView currentText() - No Items')
			return ''
		return self.items[self.pos].text
		
	def addItem(self, lineItem):
		self.items.append(lineItem)
		
	def currentItem(self):
		return self.items[self.pos]
	
	def getLineItem(self, pos):
		return self.items[pos]
	
	def setCurrentPos(self, pos):
		if pos < 0 or pos >= len(self.items): return
		self.pos = pos
		#self.setScroll()
		
	def update(self):
		self.setDisplay(self.currentText())
		
	def getSelectedPosition(self):
		return self.pos
	
	def moveUp(self):
		self.pos -= 1
		if self.pos < 0: self.pos = 0
		#self.setScroll()
		return self.pos
	
	def moveDown(self):
		self.pos += 1
		if self.pos >= self.size(): self.pos = self.size() - 1
		#self.setScroll()
		return self.pos
	
	def size(self):
		return len(self.items)
	
	def selectItem(self, pos): return self.setCurrentPos(pos)
	def getListItem(self, pos): return self.getLineItem(pos)
			
######################################################################################
# Viewer Window
######################################################################################
class ViewerWindow(BaseWindow):
	IS_DIALOG = False
	def __init__(self, *args, **kwargs):
		LOG('STARTED')
		self.url = kwargs.get('url')
		self.autoForms = kwargs.get('autoForms', [])
		self.autoClose = kwargs.get('autoClose')
		
		self.first = True
		
		self.isBoxee = self._isBoxee()
		if ATV2:
			if not __addon__.getSetting('simple_controls'):
				LOG('ATV2: Setting unset simple_controls to: true')
				__addon__.setSetting('simple_controls','true')
		self.simpleControls = __addon__.getSetting('simple_controls') == 'true'			
		self.imageReplace = 'IMG #%s: %s'
		self.page = None
		self.history = URLHistory(HistoryLocation(self.url))
		self.line = 0
		self.idFilter = re.compile('\[\{(.+?)\}\]', re.S)
		self.linkCTag = '[COLOR %s]' % HC.linkColor
		self.formCTag = '[COLOR %s]' % HC.formColorB
		self.imageTag = '[COLOR %s]' % HC.imageColor
		self.frameCTag = '[COLOR %s]' % HC.frameColor
		self.cTags = {PE_FORM:self.formCTag, PE_LINK:self.linkCTag, PE_IMAGE:self.imageTag, PE_FRAME:self.frameCTag}
		self.selectedCTag = '[COLOR %s]' % 'FFFE1203'
		self.selected = None
		self.lastPos = 0
		self.linkLastPos = 0
		self.baseDisplay = ''
		self.form = None
		self.currentElementIndex = 0
		self.formFocused = False
		self.lastPageSearch = ''
		self.bmManger = BookmarksManager(os.path.join(xbmc.translatePath(__addon__.getAddonInfo('profile')), 'bookmarks'))
		self.standalone = True
		BaseWindow.__init__(self, *args, **kwargs)
		
	def onInit(self):
		if not self.first: return
		self.first = False
		#self.pageList = self.getControl(122)
		self.pageList = LineView(self.getControl(123), self.getControl(124))
		self.controlList = self.getControl(120)
		self.linkList = self.getControl(148)
		self.imageList = self.getControl(150)
		self.setStopControl(self.getControl(106))
		self.setProgressCommands(self.startProgress, self.setProgress, self.endProgress)
		self.setHistoryControls()
		self.refresh()
		
	def endProgress(self):
		self.getControl(310).setVisible(False)
		
	def back(self):
		if not self.history.canGoBack(): return False
		hloc = self.history.goBack(self.pageList.getSelectedPosition())
		self.gotoHistory(hloc)
		return True

	def forward(self):
		if not self.history.canGoForward(): return
		hloc = self.history.goForward(self.pageList.getSelectedPosition())
		self.gotoHistory(hloc)
		
	def gotoHistory(self, hloc):
		self.url = hloc.url
		self.line = hloc.line
		self.setHistoryControls()
		self.refresh()
		
	def gotoURL(self, url=None):
		if not url:
			default = ''
			if __addon__.getSetting('goto_pre_filled') == 'true': default = self.page.url
			url = doKeyboard(__language__(30111), default=default)
			if not url: return
			if not url.startswith('http://'): url = 'http://' + url
		old = HistoryLocation(self.page and self.page.url or self.url, self.pageList.getSelectedPosition())
		new = HistoryLocation(url)
		self.history.addURL(old, new)
		self.url = url
		self.line = 0
		self.setHistoryControls()
		self.refresh()
		
	def setHistoryControls(self):
		self.getControl(200).setVisible(self.history.canGoBack())
		self.getControl(202).setVisible(self.history.canGoForward())
	
	def _isBoxee(self):
		try:
			import mc #@UnresolvedImport @UnusedImport
			return True
		except:
			return False
		
	def viewHistory(self):
		options = []
		if self.isBoxee and not self.simpleControls:
			options.append(__language__(30133))
			options.append('-                         -')
		ct = 0
		for h in self.history.history:
			t = h.getTitle()
			if ct == self.history.index: t = '[ %s ]' % t
			else: t = '  ' + t 
			options.append(t)
			ct += 1
		dialog = xbmcgui.Dialog()
		idx = dialog.select(__language__(30112), options)
		if self.isBoxee:
			if idx == 0:
				self.openSettings()
				return
			elif idx == 1:
				return
			idx -= 2
		if idx < 0: return
		if idx == self.history.index: return
		hloc = self.history.gotoIndex(idx)
		if not hloc: return
		self.gotoHistory(hloc)
		
		
	def refresh(self):
		t = self.getThread(self.getRefreshData, finishedCallback=self.refreshDo)
		t.setArgs(callback=t.progressCallback, donecallback=t.finishedCallback)
		t.start()
		
	def getRefreshData(self, callback=None, donecallback=None):
		page = WR.getWebPage(self.url, callback=callback)
		if not page or not page.isDisplayable():
			callback(100, __language__(30109))
		donecallback(page)
		
	def refreshDo(self, page):
		if not page or not page.isDisplayable():
			if page and not page.isDisplayable():
				if page.content.startswith('video'):
					self.playMedia(page.url)
				elif page.content.startswith('audio'):
					self.playMedia(page.url, mtype='music')
				elif xbmcgui.Dialog().yesno(__language__(30113), __language__(30114), page.getFileName(), __language__(30115) % page.content):
					self.downloadLink(page.url, page.getFileName())
			self.endProgress()
			if self.page: self.getControl(104).setLabel(self.page.title or self.page.url)
			return
		self.selected = None
		self.lastPos = 0
		self.page = page
		#xbmcgui.lock()
		#try:
		self.hideLists()
		self.getImages()
		self.getLinks()
		#finally:
			#xbmcgui.unlock()
		self.displayPage() 
		#self.endProgress()
	
	LINE_COUNT = 28
	CHAR_PER_LINE = 80
	def pageUp(self):
		pos = self.pageList.getSelectedPosition()
		ct = 0
		i = -1
		for i in range(pos * -1, 1):
			i = abs(i)
			item = self.pageList.getListItem(i)
			if item.displayLen < self.CHAR_PER_LINE:
				ct += 1
			else:
				ct += (item.displayLen / self.CHAR_PER_LINE) + 1
			if ct >= self.LINE_COUNT: break
		if i: i += 1
		if i > pos: i = pos
		self.pageList.selectItem(i)
		self.refreshFocus()
	
	def pageDown(self):
		pos = self.pageList.getSelectedPosition()
		max = self.pageList.size()
		ct = 0
		for i in range(pos, max):
			item = self.pageList.getListItem(i)
			if item.displayLen < self.CHAR_PER_LINE:
				ct += 1
			else:
				ct += (item.displayLen / self.CHAR_PER_LINE) + 1
			if ct >= self.LINE_COUNT: break
		else:
			return
		i -= 1
		if i < 0: i = 0
		if i > max: return
		self.pageList.selectItem(i)
		self.refreshFocus()
		
	def calculateLines(self, pos, max):
		ct = 0
		toppos = -1
		for i in range(max * -1, (pos * -1) + 1):
			i = abs(i)
			item = self.pageList.getListItem(i)
			if item.displayLen < self.CHAR_PER_LINE:
				ct += 1
			else:
				ct += (item.displayLen / self.CHAR_PER_LINE) + 1
			if ct < self.LINE_COUNT:
				toppos = i
		if toppos < -1: toppos = -1
		return ct, toppos
	
	def refreshFocus(self):
		xbmc.executebuiltin('ACTION(highlight)')
	
	def prevElement(self):
		self.currentElementIndex -= 1
		if self.currentElementIndex < 0: self.currentElementIndex = len(self.page.elements) - 1
		self.selectElement()
		
	def nextElement(self):
		self.currentElementIndex += 1
		if self.currentElementIndex >= len(self.page.elements): self.currentElementIndex = 0
		self.selectElement()
		
	def selectElement(self, element=None):
		if element: self.currentElementIndex = element.elementIndex
		#xbmcgui.lock()
		try:
			element = self.currentElement()
			if not element:
				#xbmcgui.unlock()
				return
			itemIndex = self.pageList.getSelectedPosition()
			item = self.pageList.getListItem(element.lineNumber)
			curr = self.pageList.currentItem()
			offset = element.displayPageIndex - curr.index
			lines, top = self.calculateLines(itemIndex, element.lineNumber)
			#print 'test %s %s' % (lines,top)
			if offset >= 0 and lines < self.LINE_COUNT:
				item = curr				
			else:
				linenum = element.lineNumber
				if top > -1: linenum = top
				if itemIndex != linenum:
					#index = self.currentElementIndex
					self.lastPos = linenum
					self.pageList.selectItem(linenum)
					item = self.pageList.currentItem()
					#self.currentElementIndex = index
			
			disp = item.text
			index = element.displayPageIndex - item.index
			#print self.currentElementIndex
			#print '%s %s %s' % (index,element.displayPageIndex,item.index)
			one = disp[0:index]
			two = disp[index:].replace(self.cTags[element.type], self.selectedCTag, 1)
			# two[:100]
			self.pageList.setDisplay(one + two)
			#item.setProperty('selected',element.type)
			self.elementChanged()
		except:
			raise
			#xbmcgui.unlock()
	
	def currentElement(self):
		if not self.page: return None
		if self.currentElementIndex < 0 or self.currentElementIndex >= len(self.page.elements): return None
		return self.page.elements[self.currentElementIndex]
	
	def elementChanged(self):
		element = self.currentElement()
		if not element: return
		try:
			#xbmcgui.lock()
			if element.type == PE_LINK:
				if self.linkList.getSelectedPosition() != element.typeIndex: self.linkList.selectItem(element.typeIndex)
				self.controlList.setVisible(False)
				self.imageList.setVisible(False)
				self.linkList.setVisible(True)
			elif element.type == PE_IMAGE:
				self.imageList.selectItem(element.shortIndex)
				self.linkList.setVisible(False)
				self.controlList.setVisible(False)
				self.imageList.setVisible(True)
			elif element.type == PE_FRAME:
				self.linkList.setVisible(False)
				self.controlList.setVisible(False)
				self.imageList.setVisible(False)
			else:
				self.showForm(element.form)
				self.linkList.setVisible(False)
				self.imageList.setVisible(False)
				self.controlList.setVisible(True)
		except:
			raise
			#xbmcgui.unlock()
	
	def hideLists(self):
		self.linkList.setVisible(False)
		self.imageList.setVisible(False)
		self.controlList.setVisible(False)
		
	def addLabel(self, text):
		item = xbmcgui.ListItem(label=text)
		item.setInfo('video', {'Genre':'label'})
		item.setProperty('index', '-1')
		self.controlList.addItem(item)
		
	def showForm(self, form):
		self.form = form
		self.controlList.reset()
		labels, headers = self.page.labels()
		idx = 0
		trail = False
		notrail = True
		hasSubmit = False
		hasControl = False
		for c in form.controls:
			if c.type != 'hidden':
				label = labels.get(c.id) or labels.get(c.name) or c.name or c.type.title()
				header = headers.get(c.id) or headers.get(c.name)
				if header and not c.type == 'submit': self.addLabel(header)
				if trail and notrail:
					notrail = False
				elif trail:
					trail = False
				notrail = True
				if c.type == 'checkbox' or c.type == 'radio':
					multiple = len(c.items) > 1
					if multiple and not trail and not header: self.controlList.addItem(xbmcgui.ListItem())
					cidx = 0
					for i in c.items:
						if multiple:
							label = i.name or labels.get(i.id) or labels.get(i.name) or i.id
						else:
							label = labels.get(i.id) or labels.get(i.name) or i.id
						value = i.selected
						item = xbmcgui.ListItem(label=label)
						item.setInfo('video', {'Genre':'checkbox'})
						item.setInfo('video', {'Director':value and 'checked' or 'unchecked'})
						item.setProperty('index', str(idx))
						item.setProperty('cindex', str(cidx))
						self.controlList.addItem(item)
						cidx += 1
					if len(c.items) > 1:
						trail = True
						self.controlList.addItem(xbmcgui.ListItem())
					hasControl = True
				elif c.type == 'submit' or c.type == 'image':
					hasSubmit = True
					a = c.attrs
					#value = a.get('title','')
					item = xbmcgui.ListItem(label=a.get('alt') or c.value or label)
					item.setInfo('video', {'Genre':'submit'})
					item.setProperty('index', str(idx))
					self.controlList.addItem(item)
					hasControl = True
				elif c.type == 'text' or c.type == 'password' or c.type == 'textarea':
					a = c.attrs
					label = labels.get(c.id) or labels.get(c.name) or a.get('title') or a.get('value') or a.get('type') or ''
					if c.type == 'password':
						value = '*' * len(c.value or '')
					else:
						value = c.value or ''
					#label = label + ': ' + value
					item = xbmcgui.ListItem(label=label, label2=value)
					item.setInfo('video', {'Genre':'text'})
					item.setProperty('index', str(idx))
					self.controlList.addItem(item)
					hasControl = True
				elif c.type == 'select':
					pre = labels.get(c.id, labels.get(c.name, ''))
					if pre: self.addLabel(pre)
					if c.value:
						value = c.value[0]
						citem = c.get(value)
						label = citem.attrs.get('label', value)
					else:
						label = __language__(30116)
					item = xbmcgui.ListItem(label=label)
					item.setInfo('video', {'Genre':'select'})
					item.setProperty('index', str(idx))
					self.controlList.addItem(item)
					hasControl = True
				elif c.type == 'file':
					if label: self.addLabel(label)
					label = ''
					if c._upload_data:
						try:
							label = c._upload_data[0][0].name
						except:
							ERROR('Error setting file control label')
							pass
					item = xbmcgui.ListItem(label=label)
					item.setInfo('video', {'Genre':'file'})
					item.setProperty('index', str(idx))
					self.controlList.addItem(item)
					hasControl = True
			idx += 1
		if not hasControl:
			self.addLabel('Empty Form')
		if not hasSubmit and hasControl and __addon__.getSetting('add_missing_submit') == 'true':
			item = xbmcgui.ListItem(label=__language__(30147))
			item.setInfo('video', {'Genre':'submit'})
			item.setProperty('index', str(idx))
			self.controlList.addItem(item)
	
	def getFormControl(self, item):
		idx = item.getProperty('index')
		try:
			idx = int(idx)
		except:
			LOG('error', idx)
			return None
		if idx < 0: return None
		if idx >= len(self.form.controls):
			class fake(object):
				type = 'missing_submit'
			return fake
		return self.form.controls[idx]
			
	def doControl(self):
		item = self.controlList.getSelectedItem()
		control = self.getFormControl(item)
		if not control: return
		ctype = control.type
		if ctype == 'text' or ctype == 'password' or ctype == 'textarea':
			text = doKeyboard(item.getLabel(), item.getLabel2(), hidden=bool(ctype == 'password'))
			if text == None: return
			control.value = text
			if ctype == 'password':
				text = '*' * len(text)
			item.setLabel2(text)
		elif ctype == 'checkbox' or ctype == 'radio':
			cidx = int(item.getProperty('cindex'))
			value = control.items[cidx].selected
			value = not value
			control.items[cidx].selected = value
			if type == 'checkbox':
				item.setInfo('video', {'Director':value and 'checked' or 'unchecked'})
			else:
				pos = self.controlList.getSelectedPosition() - cidx
				for i, ci in zip(range(0, len(control.items)), control.items):
					value = ci.selected
					it = self.controlList.getListItem(pos + i)
					it.setInfo('video', {'Director':value and 'checked' or 'unchecked'})
		elif ctype == 'select':
			if control.multiple:
				while self.doSelect(control, item): pass
			else:
				self.doSelect(control, item)
		elif ctype == 'submit' or ctype == 'image':
			self.submitForm(control)
			return
		elif ctype == 'missing_submit':
			self.submitForm(None)
			return
		elif ctype == 'file':
			fname = xbmcgui.Dialog().browse(1, __language__(30117), 'files')
			control.add_file(open(fname, 'r'), filename=os.path.basename(fname))
			item.setLabel(fname)
			
	
	def doSelect(self, control, item):
		options = []
		for i in control.items:
			if i.disabled:
				cb = ''
			else:
				cb = i.selected and unichr(0x2611) or unichr(0x2610)
			options.append(cb + ' ' + unicode(i.attrs.get('label', i.name) or i.name, 'utf8', 'replace'))
			#options.append(i.attrs.get('label',i.name) or i.name)
		dialog = xbmcgui.Dialog()
		idx = dialog.select(__language__(30118), options)
		if idx < 0: return False
		i = control.items[idx]
		if not i.disabled:
			i.selected = not i.selected
		if control.multiple:
			ct = 0
			for i in control.items:
				if i.selected: ct += 1
			if ct:
				label = __language__(30119) % ct
			else:
				label = __language__(30116)
		else:
			value = control.value[0]
			citem = control.get(value)
			label = citem.attrs.get('label', value)
		item.setLabel(label)
		return True
		
	def displayPage(self):
		LOG('displayPage() - START')
		disp, title = self.page.forDisplayWithIDs()
		self.baseDisplay = disp
		#xbmcgui.lock()
		self.hideLists()
		self.history.updateCurrent(self.page.url, title)
		try:
			#import codecs
			#codecs.open('/home/ruuk/test.txt','w',encoding='utf-8').write(disp)
			self.getControl(104).setLabel(title or self.url)
			self.getControl(108).setLabel(self.page.url)
			favicon = 'http://' + urlparse.urlparse(self.page.url)[1] + '/favicon.ico'
			#print favicon
			self.getControl(102).setImage(favicon)
			plist = self.pageList
			plist.reset()
			index = 0
			while disp:
				ids = ','.join(self.idFilter.findall(disp))
				label = '[CR]'.join(self.idFilter.sub('', disp).split('[CR]')[:35])
				item = LineItem(label, ids, index)
				plist.addItem(item)
				if not '[CR]' in disp: break
				old, disp = disp.split('[CR]', 1)
				index += len(self.idFilter.sub('', old)) + 4
			plist.update()
		except:
			raise
			#xbmcgui.unlock()
		self.currentElementIndex = 0
		if self.line:
			self.pageList.selectItem(self.line)
		elif self.page.id:
			self.gotoID(self.page.id)
		
		self.selectionChanged(self.pageList.getSelectedPosition(), -1)
		for fd in self.autoForms:
			f = self.page.getForm(url=fd.get('url'), name=fd.get('name'), action=fd.get('action'), index=fd.get('index'))
			if f:
				submit = fd.get('autosubmit') == 'true'
				for fill in fd.get('autofill','').split(','):
					if not '=' in fill: break
					key,value = fill.split('=',1)
					if not WR.setFormValue(f.form, key, value): submit = False
				self.selectElement(f)
				self.setFocusId(122)
				xbmc.sleep(500)
				xbmc.executebuiltin('ACTION(select)')
				#self.showForm(f.form)
				if submit:
					self.autoForms = []
					self.form = f.form
					LOG('displayPage() - END - FORM SUBMIT')
					self.submitForm(None)
					return
				break
		if self.autoClose:
			if self.page.matches(self.autoClose.get('url'), self.autoClose.get('html')):
				self.doAutoClose(self.autoClose.get('heading'), self.autoClose.get('message'))
		LOG('displayPage() - END')
				
	def doAutoClose(self, heading, message):
		if xbmcgui.Dialog().yesno(heading, message, __language__(30148)): self.close()
		
	def getLinks(self):
		ulist = self.getControl(148)
		ulist.reset()
		for link in self.page.links():
			item = xbmcgui.ListItem(link.text or link.url, link.urlShow())
			if link.isImage():
				#LOG(link.fullURL())
				item.setIconImage(link.fullURL())
			elif link.image:
				#LOG(link.image)
				item.setIconImage(link.image)
			else:
				item.setIconImage('webviewer-link.png')
			ulist.addItem(item)

	def getImages(self):
		self.getControl(150).reset()
		i = 0
		for url in self.page.imageURLs():
			#Replace file:// so images display properly in xbmc
			url = fullURL(self.url, url).replace('file://','')
			i += 1
			item = xbmcgui.ListItem(self.imageReplace % (i, url), iconImage=url)
			item.setProperty('url', url)
			self.getControl(150).addItem(item)
			
	def onFocus(self, controlId):
		self.controlId = controlId
		
	def onClick(self, controlID):
		if BaseWindow.onClick(self, controlID): return
		if controlID == 122:
			self.itemSelected()
		elif controlID == 120:
			self.doControl()
		elif controlID == 105:
			self.refresh()
		elif controlID == 200:
			self.back()
		elif controlID == 202:
			self.forward()
		elif controlID == 148:
			self.linkSelected()
		elif controlID == 150:
			self.showImage(self.getControl(150).getSelectedItem().getProperty('url'))
		elif controlID == 109:
			self.gotoURL()
		elif controlID == 112:
			self.googleSearch()
			
	def doHelp(self):
		if self.simpleControls:
			w = xbmcgui.WindowXMLDialog("script-webviewer-control-simple-help.xml" , __addon__.getAddonInfo('path'), THEME)
		else:
			w = xbmcgui.WindowXMLDialog("script-webviewer-control-help.xml" , __addon__.getAddonInfo('path'), THEME)
		w.doModal()
		del w
	
	def gotoID(self, id):
		id = id.replace('#', '')
		plist = self.pageList
		bottom = plist.size() - 1
		for i in range((bottom) * -1, 1):
			i = abs(i)
			item = plist.getListItem(i)
			ids = item.IDs
			#print id,ids
			if id in ids:
				plist.selectItem(i)
				return
			
	def itemSelected(self):
		element = self.currentElement()
		if not element:
			LOG('elementSelected() - No Element')
			return
		if element.type == PE_LINK:
			self.linkSelected(element)
		elif element.type == PE_IMAGE:
			self.showImage(element.fullURL())
		elif element.type == PE_FRAME:
			self.linkSelected(element)
		else:
			self.formFocused = True
			self.setFocusId(120)
			#self.doForm(form=item)
		
	def focusElementList(self):
		element = self.currentElement()
		if not element:
			LOG('focusElementList() - No Element')
			return
		if element.type == PE_LINK:
			self.formFocused = True
			self.setFocusId(148)
		elif element.type == PE_IMAGE:
			self.formFocused = True
			self.setFocusId(150)
		elif element.type == PE_FRAME:
			pass
		else:
			self.formFocused = True
			self.setFocusId(120)
		
	def linkSelected(self, link=None):
		if not link:
			link = self.currentElement()
		if not link.type == PE_LINK and not link.type == PE_FRAME: return
		if link.cannotBeFollowed():
			xbmcgui.Dialog().ok(__language__(30151), __language__(30152), '', link.cannotBeFollowed())
			return
		if link.url.startswith('#'):
			self.gotoID(link.url)
			return
		url = link.fullURL()
		if link.isImage():
			self.showImage(url)
		else:
			self.gotoURL(url)
			#base = xbmcgui.Dialog().browse(3,__language__(30144),'files')
			#if not base: return
			#fname,ftype = Downloader(message=__language__(30145)).downloadURL(base,link.url)
			#if not fname: return
			#xbmcgui.Dialog().ok(__language__(30052),__language__(30146),fname,__language__(30147) % ftype)
		
	def showImage(self, url):
		LOG('SHOWING IMAGE: ' + url)
		base = os.path.join(xbmc.translatePath(__addon__.getAddonInfo('profile')), 'imageviewer')
		if not os.path.exists(base): os.makedirs(base)
		clearDirFiles(base)
		image_files = Downloader().downloadURLs(base, [url], '.jpg', opener=WR.browser.open_novisit)
		if not image_files: return
		if self.IS_DIALOG:
			w = ImageDialog("script-webviewer-imageviewer.xml" , __addon__.getAddonInfo('path'), THEME, image=image_files[0], parent=self)
			w.doModal()
			del w
		else:
			xbmc.executebuiltin('SlideShow(%s)' % base)
			
	def playMedia(self, url, mtype='video'):
		if self.IS_DIALOG:
			pass
		else:
			xbmc.executebuiltin('PlayMedia(%s)' % url)
			xbmc.executebuiltin('ActivateWindow(%sosd)' % mtype)
	
	def selectLinkByIndex(self, idx):
		element = self.page.getElementByTypeIndex(PE_LINK, idx)
		if not element: return
		self.currentElementIndex = element.elementIndex
		self.selectElement()
	
	def linkSelectionChanged(self, pos, last_pos):
		if pos < 0: return
		self.selectLinkByIndex(pos)
	
	def selectionChanged(self, pos, last_pos):
		#print '%s %s' % (pos,last_pos)
		if pos > -1 and pos < self.pageList.size():
			item = self.pageList.getListItem(pos)
			index = item.index
			element = self.page.getNextElementAfterPageIndex(index)
			if not element: return
			self.currentElementIndex = element.elementIndex
			self.selectItemFirstElement(item)
			
	def selectItemFirstElement(self, item):
		disp = item.text
		element = self.currentElement()
		index = element.displayPageIndex - item.index
		disp = disp[0:index] + disp[index:].replace(self.cTags[element.type], self.selectedCTag, 1)
		#try:
			#xbmcgui.lock()
		self.pageList.setDisplay(disp)
		self.elementChanged()
		#finally:
			#xbmcgui.unlock()
	
	def bookmarks(self):
		options = [__language__(30120), __language__(30121), '-                         -']
		for bm in self.bmManger.bookmarks: options.append(bm.title)
		dialog = xbmcgui.Dialog()
		idx = dialog.select(__language__(30122), options)
		if idx < 0: return
		if idx == 0:
			title = doKeyboard(__language__(30123), default=self.page.title)
			if title == None: title = self.page.title
			self.bmManger.addBookmark(Bookmark(title, self.page.url))
		elif idx == 1: self.manageBookmarks()
		elif idx == 2: pass
		else:
			idx -= 3
			bm = self.bmManger.getBookmark(idx)
			self.gotoURL(bm.url)
	
	def manageBookmarks(self):
		while 1:
			options = []
			for bm in self.bmManger.bookmarks: options.append(bm.title)
			dialog = xbmcgui.Dialog()
			idx = dialog.select(__language__(30124), options)
			if idx < 0: return
			if xbmcgui.Dialog().yesno(__language__(30125), __language__(30126), __language__(30127) % self.bmManger.getBookmark(idx).title):
				self.bmManger.removeBookmark(idx)
	
	def onAction(self, action):
		#print action.getId()
		#check for exit so errors won't prevent it
		if self.simpleControls:
			if action == ACTION_PAUSE or action == ACTION_PLAYER_PLAY:
				action = ACTION_CONTEXT_MENU
		if action == ACTION_PREVIOUS_MENU:
			if action.getButtonCode() or self.getFocusId() == 111:
				#Escape was pressed
				BaseWindow.onAction(self, action)
				return
			else:
				#This was a mouse right click on a button
				action = ACTION_CONTEXT_MENU
					
		#if self.getFocusId() == 122:	
		if self.getFocusId() == 148:
			pos = self.linkList.getSelectedPosition()
			if pos != self.linkLastPos:
				self.linkSelectionChanged(pos, self.linkLastPos)
				self.linkLastPos = pos
			elif action == ACTION_CONTEXT_MENU:
				self.doMenu(PE_LINK)
		elif self.getFocusId() == 150:
			if action == ACTION_CONTEXT_MENU:
				self.doMenu(PE_IMAGE)
		elif self.getFocusId() == 120:
			if action == ACTION_CONTEXT_MENU:
				self.doMenu(PE_FORM)
		else:
			pos = self.pageList.getSelectedPosition()
			if pos != self.lastPos:
				self.selectionChanged(pos, self.lastPos)
				self.lastPos = pos
			if action == ACTION_MOVE_RIGHT:
				if not self.formFocused: self.nextElement()
				self.formFocused = False
				#self.nextLink()
				return
			elif action == ACTION_MOVE_LEFT:
				if not self.formFocused:  self.prevElement()
				self.formFocused = False
				return
			if action == ACTION_MOVE_UP or action == 104:
				pos = self.pageList.moveUp()
				self.selectionChanged(pos, self.lastPos)
				self.lastPos = pos
				return
			elif action == ACTION_MOVE_DOWN  or action == 105:
				pos = self.pageList.moveDown()
				self.selectionChanged(pos, self.lastPos)
				self.lastPos = pos
				return
			elif action == ACTION_PAGE_UP or action == ACTION_PREV_ITEM:
				self.pageUp()
				return
			elif action == ACTION_PAGE_DOWN or action == ACTION_NEXT_ITEM:
				self.pageDown()
				return
			elif action == ACTION_CONTEXT_MENU:
				self.doMenu()
				return
			
		if action == ACTION_PARENT_DIR or action == ACTION_PARENT_DIR2 or action == ACTION_PLAYER_REWIND:
			if not self.back() and (not self.standalone or self.simpleControls):
				action == ACTION_PREVIOUS_MENU
			else:
				return
		elif action == ACTION_PLAYER_FORWARD:
			self.forward()
			return
		elif action == ACTION_PAUSE:
			self.viewHistory()
			return
		elif action == ACTION_SHOW_INFO:
				self.focusElementList()
				return
		elif action == ACTION_PLAYER_PLAY:
				self.refresh()
				return
		
		BaseWindow.onAction(self, action)
		
	def downloadLink(self, url, fname=None):
		base = xbmcgui.Dialog().browse(3, __language__(30128), 'files')
		if not base: return
		fname, ftype = Downloader(message=__language__(30129)).downloadURL(base, url, fname, opener=WR.browser.open)
		if not fname: return
		xbmcgui.Dialog().ok(__language__(30109), __language__(30130), fname, __language__(30115) % ftype)
		
	def doMenu(self, etype=None):
		element = self.currentElement()
		if element and not etype: etype = element.type
		
		#populate options
		options = [	__language__(30131),
					__language__(30132),
					__language__(30110),
					__language__(30146),
					__language__(30149),
					__language__(30153)]
		
		if self.simpleControls:
			options += [__language__(30158), __language__(30159), __language__(30160), __language__(30112),__language__(30161)]
		
		idx_base = len(options) - 1
		if etype == PE_LINK:
			options += [__language__(30134), __language__(30135)]
			if element.image: options.append(__language__(30136))
			if element.isImage(): options.append(__language__(30137))
		elif etype == PE_IMAGE: options += [__language__(30138), __language__(30139)]
		elif etype == PE_FORM: options.append(__language__(30140))
		
		#do dialog/handle common
		dialog = xbmcgui.Dialog()
		idx = dialog.select(__language__(30110), options)
		if idx < 0: return
		elif idx == 0: self.gotoURL()
		elif idx == 1: self.bookmarks()
		elif idx == 2: self.settings()
		elif idx == 3: self.doHelp()
		elif idx == 4: self.googleSearch()
		elif idx == 5: self.searchPage()
		
		if self.simpleControls:
			if idx == 6: self.back()
			elif idx == 7: self.forward()
			elif idx == 8: self.refresh()
			elif idx == 9: self.viewHistory()
			elif idx == 10: self.close()
			
		#handle contextual options
		if etype == PE_LINK:
			if idx == idx_base + 1: self.linkSelected()
			elif idx == idx_base + 2: self.downloadLink(element.fullURL())
			elif options[idx] == __language__(30136): self.showImage(fullURL(self.url, element.image))
			elif options[idx] == __language__(30137): self.showImage(element.fullURL())
		elif etype == PE_IMAGE:
			if idx == idx_base + 1: self.showImage(element.fullURL())
			elif idx == idx_base + 2: self.downloadLink(element.fullURL())
		elif etype == PE_FORM:
			if idx == idx_base + 1: self.submitForm(None)
		
	def settings(self):
		dialog = xbmcgui.Dialog()
		idx = dialog.select(__language__(30110), [__language__(30133), __language__(30142), __language__(30157), __language__(30162)])
		if idx < 0: return
		
		if idx == 0:
			self.openSettings()
		elif idx == 1:
			setHome(self.page.url)
			xbmcgui.Dialog().ok(__language__(30109), __language__(30143), self.page.getTitle())
		elif idx == 2:
			self.viewPageSource()
		elif idx == 3:
			self.viewReadMode()
	
	def openSettings(self):
		__addon__.openSettings()
		self.simpleControls = __addon__.getSetting('simple_controls') == 'true'
		
	def viewPageSource(self):
		source = '\n' + self.page.html.replace('\t', '    ')
		source = re.sub('\r', '', source)
		#source = HC.commentFilter.sub('[COLOR FF666677]\g<0>[/COLOR]',source)
		source = HC.tagFilter.sub(self.tagConvert, source)
		#import codecs
		#codecs.open('/home/ruuk/test.txt','w',encoding='utf-8').write(source)
		w = SourceDialog("script-webviewer-source.xml" , __addon__.getAddonInfo('path'), THEME, source=source)
		w.doModal()
		del w
		
	def viewReadMode(self):
		w = SourceDialog("script-webviewer-source.xml" , __addon__.getAddonInfo('path'), THEME, source=self.page.forDisplay())
		w.doModal()
		del w
		
	def tagConvert(self, m):
		ret = re.sub('[\n\r]', '', m.group(0))
		#ret = re.sub('[\'"][^"]*?[\'"]','[COLOR FF007700]\g<0>[/COLOR]',ret)
		return '[B][COLOR FF007700]%s[/COLOR][/B]' % ret
	
	def submitForm(self, control):
		self.startProgress()
		page = WR.submitForm(self.form, control, callback=self.setProgress)
		if not page:
			LOG('submitForm() Failure')
			return
		old = HistoryLocation(self.page and self.page.url or self.url, self.pageList.getSelectedPosition())
		new = HistoryLocation(page.url)
		self.history.addURL(old, new)
		self.refreshDo(page)
		self.endProgress()
		self.setFocusId(122)
				
	def googleSearch(self):
		terms = doKeyboard(__language__(30150))
		if terms == None: return
		import urllib
		terms = urllib.quote_plus(terms)
		url = 'http://www.google.com/search?q=%s' % terms
		self.gotoURL(url)
		
	def searchPage(self, term=None, start=None):
		if not term:
			term = doKeyboard(__language__(30150), default=self.lastPageSearch)
			if term == None: return
		self.lastPageSearch = term
		term = term.lower()
		plist = self.pageList
		bottom = plist.size() - 1
		top = start
		if start == None: top = (plist.getSelectedPosition()* -1) - 1
		match = -1
		for i in range((bottom) * -1, top):
			i = abs(i)
			item = plist.getListItem(i)
			if term in item.text.split('[CR]', 1)[0].lower():
				match = i
		if match >= 0:
			self.pageList.selectItem(match)
			self.refreshFocus()
		else:
			if start != None:
				xbmcgui.Dialog().ok(__language__(30154), '%s:' % __language__(30155), '', term)
			else:
				if xbmcgui.Dialog().yesno(__language__(30154), __language__(30155), '', __language__(30156)):
					self.searchPage(term, 0)
		

class ViewerWindowDialog(ViewerWindow, xbmcgui.WindowXMLDialog): IS_DIALOG = True
class ViewerWindowNormal(ViewerWindow, xbmcgui.WindowXML): pass

class BookmarksManager:
	def __init__(self, file=''):
		self.file = file
		self.bookmarks = []
		self.load()
		
	def addBookmark(self, bookmark):
		self.bookmarks.append(bookmark)
		self.save()
		
	def removeBookmark(self, index):
		del self.bookmarks[index]
		self.save()
		
	def getBookmark(self, index):
		return self.bookmarks[index]
	
	def save(self):
		out = ''
		for bm in self.bookmarks:
			out += bm.toString() + '\n'
		bf = open(self.file, 'w')
		bf.write(out)
		bf.close()
			
		
	def load(self):
		if not os.path.exists(self.file): return
		bf = open(self.file, 'r')
		lines = bf.read().splitlines()
		bf.close()
		self.bookmarks = []
		for line in lines:
			self.addBookmark(Bookmark().fromString(line))
		
class Bookmark:
	def __init__(self, title='', url=''):
		self.title = title
		self.url = url
		
	def toString(self):
		return '%s:=:%s' % (self.title, self.url)
	
	def fromString(self, string):
		if ':=:' in string: self.title, self.url = string.split(':=:', 1)
		return self
	
class Downloader:
	def __init__(self, header=__language__(30129), message=''):
		self.message = message
		self.prog = xbmcgui.DialogProgress()
		self.prog.create(header, message)
		self.current = 0
		self.display = ''
		self.file_pct = 0
		
	def progCallback(self, read, total):
		if self.prog.iscanceled(): return False
		pct = ((float(read) / total) * (self.file_pct)) + (self.file_pct * self.current)
		self.prog.update(int(pct))
		return True
		
	def downloadURLs(self, targetdir, urllist, ext='', opener=urllib2.urlopen):
		file_list = []
		self.total = len(urllist)
		self.file_pct = (100.0 / self.total)
		try:
			for url, i in zip(urllist, range(0, self.total)):
				self.current = i
				if self.prog.iscanceled(): break
				self.display = __language__(30144) % (i + 1, self.total)
				self.prog.update(int((i / float(self.total)) * 100), self.message, self.display)
				fname = os.path.join(targetdir, str(i) + ext)
				file_list.append(fname)
				self.getUrlFile(url, fname, callback=self.progCallback, opener=opener)
		except:
			ERROR('DOWNLOAD URLS ERROR: %s' % url)
			self.prog.close()
			return None
		self.prog.close()
		return file_list
	
	def downloadURL(self, targetdir, url, fname=None, opener=urllib2.urlopen):
		if not fname:
			fname = os.path.basename(urlparse.urlsplit(url)[2])
			if not fname: fname = 'file'
		f, e = os.path.splitext(fname)
		fn = f
		ct = 1
		while ct < 1000:
			ct += 1
			path = os.path.join(targetdir, fn + e)
			if not os.path.exists(path): break
			fn = f + '(%s)' % str(ct)
		else:
			raise Exception
		
		try:
			self.current = 0
			self.display = __language__(30145) % os.path.basename(path)
			self.prog.update(0, self.message, self.display)
			t, ftype = self.getUrlFile(url, path, callback=self.progCallback, opener=opener) #@UnusedVariable
		except:
			ERROR('DOWNLOAD URL ERROR: %s' % url)
			self.prog.close()
			return (None, '')
		self.prog.close()
		return (os.path.basename(path), ftype)
		
		
			
	def fakeCallback(self, read, total): return True

	def getUrlFile(self, url, target=None, callback=None, opener=urllib2.urlopen):
		if not target: return #do something else eventually if we need to
		if not callback: callback = self.fakeCallback
		urlObj = opener(url)
		try:
			size = int(urlObj.info().get("content-length", -1))
		except:
			size = 1
		ftype = urlObj.info().get("content-type", '')
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
		return (target, ftype)

def doKeyboard(prompt, default='', hidden=False):
	keyboard = xbmc.Keyboard(default, prompt)
	keyboard.setHiddenInput(hidden)
	keyboard.doModal()
	if not keyboard.isConfirmed(): return None
	return keyboard.getText()

################################################################################
# getWebResult
################################################################################
def getWebResult(url, autoForms=[], autoClose=None, dialog=False, runFromSubDir=None,clearCookies=False,browser=None):
	LOG('getWebResult() - STARTED')
	"""Open a url and get the result
	
	url, html = webviewer.getWebResult(url,autoForms=[],autoClose=None,dialog=False)

	This returns the url and html of the page when the browser was closed.
	
	The autoforms parameter is for auto selecting forms and is a list of dicts as follows:
	
	{ 'name': 'exact name of form',
	  'action': 'a substring of the form action',
	  'index': 'index of the form in the html',
	  'autofill': 'comma separated list of input_name=input_value pairs'
	  'autosubmit': 'true|false'}
	
	A match will occur if any of the items in the dict matches,
	except if name or action matches and index is defined, the index must also match.
	
	The autoClose parameter is for matching a page where the window should close.
	If matched it will present a dialog asking to close with the provided heading and message.
	It is a dict as follows:
	
	{ 'url': 'regex to match against page url',
	  'html': 'regex to match against page html',
	  'heading': 'heading for dialog',
	  'message': 'message for dialog' }
	  
	You can specify url, html, or both. A match will only occur if all provided regular expressions match.
	  
	Setting the dialog parameter to true will cause the browser to open as a dialog instead as a normal window.
	
	"""
	if browser: WR.setBrowser(browser)
	if clearCookies: WR.browser._ua_handlers["_cookies"].cookiejar.clear()
	if runFromSubDir: __addon__.setAddonPath(runFromSubDir)
	apath = xbmc.translatePath(__addon__.getAddonInfo('path'))
	if not os.path.exists(os.path.join(apath,'resources','skins','Default','720p','script-webviewer-page.xml')):
		apath = 'Q:\\scripts\\.modules\\script.web.viewer\\' #for XBMC4Xbox when used as a module
	
	if dialog:
		w = ViewerWindowDialog("script-webviewer-page.xml" , apath, THEME, url=url, autoForms=autoForms, autoClose=autoClose)
	else:
		w = ViewerWindowNormal("script-webviewer-page.xml" , apath, THEME, url=url, autoForms=autoForms, autoClose=autoClose)
	w.standalone = False
	w.doModal()
	if w.page:
		url = w.page.url
		html = w.page.html
	else:
		url = None
		html = None
	del w
	LOG('getWebResult() - FINISHED')
	return url, html
	
def setHome(url):
	__addon__.setSetting('home_page', url)
		
def getHome():
	return __addon__.getSetting('home_page')
	
WR = WebReader()
HC = HTMLConverter()

if __name__ == '__main__':
	#start_url = 'http://examples.codecharge.com/ExamplePack/MultiSelectSearch/MultiSelectSearch.php'
	#start_url = 'http://www.tizag.com/phpT/examples/formex.php'
	#start_url = 'http://forum.xbmc.org'
	#start_url='http://www.cs.tut.fi/~jkorpela/forms/file.html'
	start_url = ''
	try: start_url = sys.argv[1]
	except: pass
	
	if not start_url: start_url = getHome() or 'http://wiki.xbmc.org/index.php?title=XBMC_Online_Manual'
	LOG(start_url)
	apath = xbmc.translatePath(__addon__.getAddonInfo('path'))
	if not os.path.exists(os.path.join(apath,'resources','skins','Default','720p','script-webviewer-page.xml')):
		apath = 'Q:\\scripts\\.modules\\script.web.viewer\\' #for XBMC4Xbox when used as a module
	w = ViewerWindowNormal("script-webviewer-page.xml" , apath, THEME, url=start_url)
	w.doModal()
	del w
	sys.modules.clear()
	
