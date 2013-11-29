"""
	###################### xbmcutil.urlhandler ######################
	Copyright: (c) 2013 William Forde (willforde+xbmc@gmail.com)
	License: GPLv3, see LICENSE for more details
	
	This file is part of xbmcutil
	
	xbmcutil is free software: you can redistribute it and/or modify
	it under the terms of the GNU General Public License as published by
	the Free Software Foundation, either version 3 of the License, or
	(at your option) any later version.
	
	xbmcutil is distributed in the hope that it will be useful,
	but WITHOUT ANY WARRANTY; without even the implied warranty of
	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
	GNU General Public License for more details.
	
	You should have received a copy of the GNU General Public License
	along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# Call Necessary Imports
import urllib2, StringIO, urlparse, httplib, socket, os, re
htmlentitydefs = time = zlib = None

# Call Custom xbmcutil Module
from xbmcutil import plugin
from hashlib import md5

#################################################################

def urlopen(url, maxAge=None, data=None, headers={}, userAgent=1):
	''' Makes Request and Return Response Object '''
	handle = HttpHandler()
	handle.add_response_handler(userAgent)
	if maxAge is not None: handle.add_cache_handler(maxAge)
	return handle.open(url, data, headers)

def urlread(url, maxAge=None, data=None, headers={}, userAgent=1):
	''' Makes Request and Return Response Data '''
	handle = HttpHandler()
	handle.add_response_handler(userAgent, stripEntity=True)
	if maxAge is not None: handle.add_cache_handler(maxAge)
	resp = handle.open(url, data, headers)
	data = resp.read()
	resp.close()
	return data

def urllogin(url, data=None, headers={}):
	handle = HttpHandler()
	handle.add_cookie_handler()
	return handle.open(url, data, headers)

def urlretrieve(url, filename):
	handle = HttpHandler()
	handle.add_response_handler()
	resp = handle.open(url)
	opened = open(filename, "wb")
	opened.write(resp.read())
	opened.close()
	return filename

#################################################################

def parse_qs(url):
	# Strip url down to Query String
	if "#" in url: url = url[:url.find("#")]
	if "?" in url: url = url[url.find("?")+1:]
	return dict(part.split("=",1) for part in url.split("&"))

def strip_tags(html):
	# Strips out html code and return plan text
	sub_start = html.find("<")
	sub_end = html.find(">")
	while sub_start < sub_end and sub_start > -1:
		html = html.replace(html[sub_start:sub_end + 1], "").strip()
		sub_start = html.find("<")
		sub_end = html.find(">")
	
	return html

def search(urlString=""):
	# Open KeyBoard Dialog
	ret = plugin.keyBoard("", plugin.getstr(16017), False)
	
	# Check if User Entered Any Data
	if ret and urlString: return urlString % ret
	elif ret: return ret
	else: raise plugin.URLError(0, "User Cannceled The Search KeyBoard Dialog")

def redirect(url, data=None, headers={}):
	# Print out Debug
	print url,
	print "Redirected To:",
	# Split url into Components
	splitUrl = urlparse.urlsplit(url)
	
	# Create Connection Object, HTTP or HTTPS
	if splitUrl[0] == "http": conn = httplib.HTTPConnection(splitUrl[1])
	elif splitUrl[0] == "https": conn = httplib.HTTPSConnection(splitUrl[1])
	
	# Set Request Mothods
	if data is not None:
		method = "POST"
		headers["Content-Type"] = "application/x-www-form-urlencoded"
		headers["Content-Length"] = "%d" % len(data)
	else:
		method = "HEAD"
	
	# Make Request to Server
	try: conn.request(method, urlparse.urlunsplit(splitUrl), data, headers)
	except: raise plugin.URLError(30910, "Failed to Make Request for Redirected Url")
	
	# Fetch Headers from Server
	try:
		resp = conn.getresponse()
		print resp.status, resp.reason
		headers = dict(resp.getheaders())
		conn.close()
	except: raise plugin.URLError(30910, "Failed to Read Server Response")
	
	# Fetch Redirect Location
	if "location" in headers: url = headers["location"]
	elif "uri" in headers: url = headers["uri"]
	else: url = ""
	print url
	return url

#################################################################

class HttpHandler:
	def __init__(self):
		# Create OpenerDirector Object
		self.opener = urllib2.build_opener(ErrorHandler())
	
	def add_response_handler(self, userAgent=1, compressed=True, stripEntity=False):
		''' Adds Response Handler to Urllib to Handle Compression and unescaping '''
		self.opener.add_handler(ResponseHandler(userAgent, compressed, stripEntity))
	
	def add_cache_handler(self, maxAge=0, cacheLocal="urlcache", asUrl=None):
		''' Adds Cache Handler to Urllib to Handle Caching of Source '''
		self.opener.add_handler(CacheHandler(maxAge, cacheLocal, asUrl))
	
	def add_authorization(self, username, password):
		''' Adds Basic Authentication to Requst '''
		self.opener.add_handler(Authorization(username, password))
	
	def add_cookie_handler(self, cookieName="cookies.lwp", loginData={}):
		''' Adds Cookie Support ''' 
		self.opener.add_handler(HTTPCookieProcessor(cookieName, loginData))
	
	def open(self, url, data=None, headers={}, timeout=10):
		# Create Request Object
		request = urllib2.Request(url, data, headers)
		
		# Make Url Connection, Save Cookie If Set and Return Response
		try: return self.opener.open(request, timeout=timeout)
		except socket.timeout: raise plugin.URLError(30904, "Server Request Timed Out")
		except urllib2.URLError: raise plugin.URLError(30909, "An Unexpected UrlError Occurred")

class ErrorHandler(urllib2.HTTPDefaultErrorHandler):
	''' Default Error Handler for Reporting The Error Code to XBMC '''
	def http_error_default(self, req, fp, code, msg, hdrs):
		raise plugin.URLError(msg, "HTTPError %s:%s" % (code, msg))

class Authorization(urllib2.BaseHandler):
	def __init__(self, username, password):
		import base64
		self.AuthString = base64.encodestring("%s:%s" % (username, password))[:-1]
	
	def http_request(self, request):
		''' Adds Authorization Header to Request '''
		if self.AuthString: request.add_header("Authorization", "Basic %s" % self.AuthString)
		return request
	
	# Redirect HTTPS Requests to HTTP
	https_request = http_request

class HTTPCookieProcessor(urllib2.BaseHandler):
	def __init__(self, cookieName="cookies.lwp", loginData={}):
		import cookielib
		# Create Cookie With FileName and Load Existing Cookie If Available
		cookieFile = os.path.join(plugin.getProfile(), cookieName)
		self.cookiejar = cookielib.LWPCookieJar(cookieFile)
		self.loginPage = loginData.pop("login", None)
		self.loginData = loginData
		self.logonAtempted = False
	
	def http_request(self, request):
		self.load_cookies()
		self.cookiejar.add_cookie_header(request)
		return request
	
	def http_response(self, request, response):
		headers = response.info()
		loginPage = self.loginPage
		if loginPage and (headers.get("location") == loginPage or headers.get("uri") == loginPage):
			# Check if Logon has already happend within current session
			if self.logonAtempted is True: raise plugin.URLError(30914, "Logon Already Atempted, Stopping infinite loop")
			else: self.logonAtempted = True
			
			# Login to site and create session cookie
			print "Sending Login Data"
			urllogin(**self.loginData)
			
			# Resend Request for Data with new session cookie
			request = self.http_request(request)
			return self.parent.open(request)
		else:
			self.cookiejar.extract_cookies(response, request)
			self.save_cookies()
			return response
	
	def load_cookies(self):
		try: self.cookiejar.load()
		except IOError: pass
	
	def save_cookies(self):
		try: self.cookiejar.save()
		except IOError: pass
	
	# Redirect HTTPS Requests to use HTTP
	https_request = http_request
	https_response = http_response

class ResponseHandler(urllib2.BaseHandler):
	''' Class to Handle Commpressed HTTP Responses '''
	def __init__(self, userAgent=1, compressed=True, stripEntity=False):
		# Set Global Vars
		global zlib, htmlentitydefs
		import zlib, htmlentitydefs
		self.compressed = compressed
		self.stripEntity = stripEntity
		
		# Set UserAgent
		if userAgent == 1: self.userAgent = "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:24.0) Gecko/20100101 Firefox/24.0"
		elif userAgent == 2: self.userAgent = "Mozilla/5.0 (iPhone; U; CPU iPhone OS 3_0 like Mac OS X; en-us) AppleWebKit/528.18 (KHTML, like Gecko) Version/4.0 Mobile/7A341 Safari/528.16"
		elif type(userAgent) is str: self.userAgent = userAgent
		else: self.userAgent = None
	
	def http_request(self, request):
		''' Add Accept-Encoding & User-Agent Headers '''
		if self.userAgent and not request.has_header("User-Agent"): request.add_header("User-Agent", self.userAgent)
		if self.compressed: request.add_header("Accept-Encoding", "gzip, deflate")
		print request.get_full_url(),
		return request
	
	def handle_response(self, response):
		# Check if Response need to be decoded, else return raw response
		data = None
		headers = response.info()
		encoding = headers.get("Content-Encoding")
		if encoding or (self.stripEntity and "Content-Type" in headers):
			try:
				# Check if Response needs to be Decompressed
				if encoding and "gzip" in encoding: data = zlib.decompress(response.read(), 16+zlib.MAX_WBITS)
				elif encoding and "deflate" in encoding: data = zlib.decompress(response.read())
			except:
				raise plugin.URLError(30912, "Failed to Decompress Response Body")
			
			# If Content-Type is text/html, Unescape the Content
			if self.stripEntity and "Content-Type" in headers:
				# Process Content Type
				url = response.url
				contentType = [i.strip() for i in headers["Content-Type"].lower().split(";")]
				if "text/html" in contentType and not url[-5:] == ".json" or not url[-4:] == ".xml":
					# Fetch Charset
					charset = [part[part.find("=")+1:] for part in contentType if part.startswith("charset")]
					
					# If No Charset Header Exist Then Attempt to read the Document to determine Charset Type
					if data is None: data = response.read(); response.close()
					if charset: data = self.unescape(data, charset[0])
					else:
						# Atempt to Fetch Charset form Body
						charset = re.findall('<meta http-equiv="Content-Type" content=".*?charset=(.+?)" />', data)
						if charset: data = self.unescape(data, charset[0])
						else: data = self.unescape(data)
		
		# Return Data Wraped in an addinfourl Object
		if data is None: return response
		else:
			addInfo = urllib2.addinfourl(StringIO.StringIO(data), headers, response.url, response.code)
			addInfo.msg = response.msg
			response.close()
			return addInfo
	
	def unescape(self, text, encoding="utf-8"):
		# Add None Valid HTML Entities
		htmlentitydefs.name2codepoint['apos'] = 0x0027
		
		def fixup(m):
			# Fetch Text from Group
			text = m.group(0)
			# Check if Character is A Character Reference or Named Entity
			if text[:2] == "&#": # Character Reference
				try:
					if text[:3] == "&#x": return unichr(int(text[3:-1], 16))
					else: return unichr(int(text[2:-1]))
				except ValueError: return text
			else: # Named Entity
				try: return unichr(htmlentitydefs.name2codepoint[text[1:-1]])
				except KeyError: return text
		
		# Return Clean string using accepted encoding
		try: return re.sub("&#?\w+;", fixup, unicode(text, encoding)).encode("utf-8")
		except: pass
		
		# Return Clean String using Latin1 as encoding
		try: return re.sub("&#?\w+;", fixup, unicode(text, "latin-1")).encode("utf-8")
		except: pass
		
		# Unable to Decode Body Raising Exception
		raise plugin.URLError(30913, "HTML Entity Decoding Failed")
	
	def http_response(self, request, response):
		''' Returns a Decompress Version of the response '''
		print response.code, response.msg
		if response.code is not 200 or response.info().get("X-Cache") == "HIT": return response
		else: return self.handle_response(response)
	
	# Redirect HTTPS Requests and Responses to HTTP
	https_request = http_request
	https_response = http_response

class CacheHandler(urllib2.BaseHandler):
	'''Stores responses in a persistant on-disk cache'''
	def __init__(self, maxAge=0, cacheLocal="urlcache", asUrl=None):
		global time
		import time
		self.cacheLocal = cacheLocal
		self.maxAge = maxAge
		self.redirect = False
		self.url = asUrl
	
	def default_open(self, request):
		'''
		Returns Cached Response if Cache is not stale
		
		If Cache Exists but is Stale, the If-Modified-Since header
		and If-None-Match header is set.
		'''
		
		# Create Url Hash
		if self.redirect is False:
			if self.url: url = self.url
			else:
				url = request.get_full_url()
				if request.has_data(): url += request.get_data()
				if request.has_header("Referer"): url += request.get_header("Referer")
			
			# Create Cache Path
			urlHash = md5(url).hexdigest()
			self.CachePath = os.path.join(plugin.getProfile(), self.cacheLocal, urlHash + ".%s")
		
		# Check Status of Cache
		if CachedResponse.exists(self.CachePath):
			# If Refresh Param Exists Then Reset 
			if "refresh" in plugin: CachedResponse.reset(self.CachePath, (0,0))
			
			# Check if Cache is Valid
			if self.maxAge == -1 or CachedResponse.isValid(self.CachePath, self.maxAge):
				print "Cached",
				# Return Cached Response
				return CachedResponse(self.CachePath)
			else:
				print "Cache Not Valid",
				# Set If-Modified-Since & If-None-Match Headers
				cacheHeaders = CachedResponse.loadHeaders(self.CachePath)
				if "Last-Modified" in cacheHeaders:
					# Add If-Modified-Since Date to Request Headers
					request.add_header("If-Modified-Since", cacheHeaders["Last-Modified"])
				if "ETag" in cacheHeaders:
					# Add If-None-Match Etag to Request Headers
					request.add_header("If-None-Match", cacheHeaders["ETag"])
	
	def http_response(self, request, response):
		''' Store Server Response into Cache '''
		# Save response to cache and return it if status is 200 else return response untouched
		self.redirect = False
		if response.code is 200 and not response.info().get("X-Cache") == "HIT":
			CachedResponse.store_in_cache(self.CachePath, response)
			return CachedResponse(self.CachePath)
		elif response.code in (301,302,303,307):
			self.redirect = True
			return response
		else:
			return response
	
	def http_error_304(self, req, fp, code, msg, hdrs):
		'''
		Server Content Not Modified Since Last Access.
		Cache Access Times will be Reset and the Cache
		Response will be Returned
		'''
		
		# Reset Cache and Return Cached Response
		CachedResponse.reset(self.CachePath)
		return CachedResponse(self.CachePath)
	
	# Redirect HTTPS Responses to HTTP
	https_response = http_response

class CachedResponse(StringIO.StringIO):
	'''
	An urllib2.response-like object for cached responses.
	 
	To determine wheter a response is cached or coming directly from
	the network, check the x-cache header rather than the object type.
	'''
	
	@staticmethod
	def exists(cachePath):
		''' Returns True if Cache Exists, Else Return False '''
		return os.path.isfile(cachePath % "body") and os.path.isfile(cachePath % "headers")
	
	@staticmethod
	def isValid(cachePath, maxAge):
		''' Returns True if Cache is Valid, Else Return False '''
		return maxAge and time.time() - os.stat(cachePath % "body").st_mtime < maxAge and time.time() - os.stat(cachePath % "headers").st_mtime < maxAge
	
	@staticmethod
	def loadHeaders(cachePath):
		''' Returns Only the headers to chack If-Modified-Since & If-None-Match '''
		try: return httplib.HTTPMessage(StringIO.StringIO(file(cachePath % "headers").read()))
		except: raise plugin.CacheError(30911, "Loading of Cache Headers Failed")
	
	@staticmethod
	def reset(cachePath, times=None):
		''' Reset the access and modified times of the cache '''
		os.utime(cachePath % "headers", times)
		os.utime(cachePath % "body", times)
	
	@staticmethod
	def remove(cachePath):
		''' Remove Cache Items '''
		# Remove Headers
		try: os.remove(cachePath % "headers")
		except: pass
		# Remove Body
		try: os.remove(cachePath % "body")
		except: pass
	
	@staticmethod
	def store_in_cache(cachePath, response):
		''' Saves Response and Headers to Cache '''
		# Check if Cache Location is Valid
		cacheLocal = os.path.dirname(cachePath)
		if not os.path.exists(cacheLocal): os.makedirs(cacheLocal)
		
		# Save Headers to Cache
		outputFile = open(cachePath % "headers", "w")
		headers = response.info()
		headers["X-Cache"] = "HIT"
		headers["X-Location"] = response.url
		try: outputFile.write(str(headers))
		except: raise plugin.CacheError(30911, "Failed to Save Headers to Cache")
		finally: outputFile.close()
		
		# Save Response to Cache
		outputFile = open(cachePath % "body", "w")
		try: outputFile.write(response.read())
		except: raise plugin.CacheError(30911, "Failed to Save Body to Cache")
		finally: outputFile.close()
		
		# Close Response Connection
		response.close()
	
	def __init__(self, cachePath):
		# Read in Both Body and Header Responses
		try: StringIO.StringIO.__init__(self, file(cachePath % "body").read())
		except: raise plugin.CacheError(30911, "Loading of Cache Body Failed")
		self.headers = self.loadHeaders(cachePath)
		
		# Set Response Codes
		self.url = self.headers["X-Location"]
		self.msg = "OK"
		self.code = 200
	
	def info(self):
		''' Returns headers '''
		return self.headers
	
	def geturl(self):
		''' Returns original Url '''
		return self.url
