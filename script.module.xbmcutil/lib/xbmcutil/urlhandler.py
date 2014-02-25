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
import urllib2, StringIO, urlparse, httplib, codecs, socket, os, re
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
	return data.decode("utf-8")

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
	if u"#" in url: url = url[:url.find(u"#")]
	if u"?" in url: url = url[url.find(u"?")+1:]
	return dict(part.split(u"=",1) for part in url.split(u"&"))

def strip_tags(html):
	# Strips out html code and return plan text
	sub_start = html.find(u"<")
	sub_end = html.find(u">")
	while sub_start < sub_end and sub_start > -1:
		html = html.replace(html[sub_start:sub_end + 1], u"").strip()
		sub_start = html.find(u"<")
		sub_end = html.find(u">")
	return html

def search(urlString=u""):
	# Open KeyBoard Dialog
	ret = plugin.keyBoard("", plugin.getstr(16017), False)
	
	# Check if User Entered Any Data
	if ret and urlString: return urlString % ret
	elif ret: return ret
	else: raise plugin.URLError(0, "User Cannceled The Search KeyBoard Dialog")

def redirect(url, data=None, headers={}):
	# Convert url to ascii if needed
	if isinstance(url, unicode): url = url.encode("ascii")
	
	# Log for Debuging
	plugin.log(url + " - Redirected To:", 0)
	
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
	except: raise plugin.URLError(32910, "Failed to Make Request for Redirected Url")
	
	# Fetch Headers from Server
	try:
		resp = conn.getresponse()
		plugin.log("%s - %s" % (resp.status, resp.reason), 0)
		headers = dict(resp.getheaders())
		conn.close()
	except: raise plugin.URLError(32910, "Failed to Read Server Response")
	
	# Fetch Redirect Location
	if "location" in headers: url = headers["location"]
	elif "uri" in headers: url = headers["uri"]
	else: url = ""
	plugin.log(url, 0)
	return url.decode("ascii")

#################################################################

class HttpHandler:
	def __init__(self):
		self.handleList = [ErrorHandler]
	
	#def add_dns_handler(self, dnsAddr=None):
	#	if dnsAddr: DNSConnection.dns_address = dnsAddr
	#	self.handleList.append(DNSHandler)
	
	def add_response_handler(self, userAgent=1, compressed=True, stripEntity=False):
		''' Adds Response Handler to Urllib to Handle Compression and unescaping '''
		self.handleList.append(ResponseHandler(userAgent, compressed, stripEntity))
	
	def add_cache_handler(self, maxAge=0, cacheLocal=u"urlcache", asUrl=None):
		''' Adds Cache Handler to Urllib to Handle Caching of Source '''
		self.handleList.append(CacheHandler(maxAge, cacheLocal, asUrl))
	
	def add_authorization(self, username, password):
		''' Adds Basic Authentication to Requst '''
		self.handleList.append(Authorization(username, password))
	
	def add_cookie_handler(self, cookieName=u"cookies.lwp", loginData={}):
		''' Adds Cookie Support ''' 
		self.handleList.append(HTTPCookieProcessor(cookieName, loginData))
	
	def open(self, url, data=None, headers={}, timeout=10):
		# Create Request Object
		if isinstance(url, unicode): url = url.encode("ascii")
		request = urllib2.Request(url, data, headers)
		
		# Make Url Connection, Save Cookie If Set and Return Response
		opener = urllib2.build_opener(*self.handleList)
		try: return opener.open(request, timeout=timeout)
		except socket.timeout: raise plugin.URLError(32904, "Server Request Timed Out")
		except urllib2.URLError: raise plugin.URLError(32909, "An Unexpected UrlError Occurred")

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

#class DNSConnection(httplib.HTTPConnection):
#	# Set Default DNS Address
#	dns_address = "8.8.8.8" # Google DNS
#	
#	def connect(self):
#		from dns.resolver import Resolver
#		resolver = Resolver()
#		resolver.nameservers = [self.dns_address]
#		answer = resolver.query(self.host,"A")
#		self.host = answer.rrset.items[0].address
#		self.sock = socket.create_connection ((self.host, self.port), self.timeout)

#class DNSHandler(urllib2.HTTPHandler):
#	def http_open(self, req):
#		return self.do_open(DNSConnection, req)
#	
#	# Redirect HTTPS Requests to HTTP
#	https_open = http_open

class HTTPCookieProcessor(urllib2.BaseHandler):
	def __init__(self, cookieName=u"cookies.lwp", loginData={}):
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
			if self.logonAtempted is True: raise plugin.URLError(32914, "Logon Already Atempted, Stopping infinite loop")
			else: self.logonAtempted = True
			
			# Login to site and create session cookie
			plugin.log("Sending Login Data")
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
		elif isinstance(userAgent, unicode): self.userAgent = userAgent.encode("utf-8")
		elif isinstance(userAgent, str): self.userAgent = userAgent
		else: self.userAgent = None
	
	def http_request(self, request):
		''' Add Accept-Encoding & User-Agent Headers '''
		if self.userAgent and not request.has_header("User-Agent"): request.add_header("User-Agent", self.userAgent)
		if self.compressed: request.add_header("Accept-Encoding", "gzip, deflate")
		request.add_header("Accept-Language", "en-gb,en-us,en")
		plugin.log(request.get_full_url())
		return request
	
	def handle_response(self, response):
		# Check if Response need to be decoded, else return raw response
		headers = response.info()
		contentCharset = headers.getparam("charset") or headers.getparam("encoding")
		contentEncoding = headers.get("Content-Encoding")
		contentType = headers.gettype()
		
		# If content is compressed then decompress and decode into unicode
		try:
			if contentEncoding and "gzip" in contentEncoding: data = zlib.decompress(response.read(), 16+zlib.MAX_WBITS)
			elif contentEncoding and "deflate" in contentEncoding: data = zlib.decompress(response.read())
			else: data = response.read()
		
		except zlib.error:
			raise plugin.URLError(32912, "Failed to Decompress Response Body")
		
		else:
			# Convert content to unicode and back to utf-8 to fix any issues
			if contentType == "text/html":
				# if no charset was specified in the headers then attempt to fetch from content itself
				if contentCharset is None:
					charset = re.findall('<meta\s+http-equiv="Content-Type"\s+content=".*?charset=(\S+?)"\s+/>', data)
					if charset: contentCharset = charset[0]
			
				# Attempt to decode Response to unicode
				if not contentCharset: contentCharset = "utf-8"; plugin.log("Response encoding not specified, defaulting to UTF-8", 0)
				try: data = unicode(data, contentCharset.lower())
				except:
					# Attempt to decode using iso-8859-1 (latin-1)
					plugin.log("Specified encoding failed, reverting to iso-8859-1 (latin-1)", 0)
					try: data = unicode(data, "iso-8859-1")
					except: raise plugin.URLError(32913, "Unable to Decode response to unicode")
				
				# Unescape the content if requested
				if self.stripEntity: data = self.unescape(data).encode("utf-8")
				else: data = data.encode("utf-8")
		
		finally:
			# Close Http Resource Request
			response.close()
		
		# Return Data Wraped in an addinfourl Object
		addInfo = urllib2.addinfourl(StringIO.StringIO(data), headers, response.url, response.code)
		addInfo.msg = response.msg
		return addInfo
	
	def unescape(self, text):
		# Add None Valid HTML Entities
		htmlentitydefs.name2codepoint["apos"] = 0x0027
		
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
		try: return re.sub("&#?\w+;", fixup, text)
		except: raise plugin.URLError(32913, "HTML Entity Decoding Failed")
	
	def http_response(self, request, response):
		''' Returns a Decompress Version of the response '''
		plugin.log("%s - %s" % (response.code, response.msg), 0)
		if response.code is not 200 or response.info().get("X-Cache") == "HIT": return response
		else: return self.handle_response(response)
	
	# Redirect HTTPS Requests and Responses to HTTP
	https_request = http_request
	https_response = http_response

class CacheHandler(urllib2.BaseHandler):
	'''Stores responses in a persistant on-disk cache'''
	def __init__(self, maxAge=0, cacheLocal=u"urlcache", asUrl=None):
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
			plugin.log("UrlHash = " + urlHash, 0)
			self.CachePath = os.path.join(plugin.getProfile(), self.cacheLocal, urlHash + u".%s")
		
		# Check Status of Cache
		if CachedResponse.exists(self.CachePath):
			# If Refresh Param Exists Then Reset 
			if "refresh" in plugin: CachedResponse.reset(self.CachePath, (0,0))
			
			# Check if Cache is Valid
			if self.maxAge == -1 or CachedResponse.isValid(self.CachePath, self.maxAge):
				plugin.log("Cached")
				# Return Cached Response
				return CachedResponse(self.CachePath)
			else:
				plugin.log("Cache Not Valid")
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
		return os.path.isfile(cachePath % u"body") and os.path.isfile(cachePath % u"headers")
	
	@staticmethod
	def isValid(cachePath, maxAge):
		''' Returns True if Cache is Valid, Else Return False '''
		return maxAge and time.time() - os.stat(cachePath % u"body").st_mtime < maxAge and time.time() - os.stat(cachePath % u"headers").st_mtime < maxAge
	
	@staticmethod
	def loadHeaders(cachePath):
		''' Returns Only the headers to chack If-Modified-Since & If-None-Match '''
		try: return httplib.HTTPMessage(StringIO.StringIO(CachedResponse.readFile(cachePath % u"headers")))
		except: raise plugin.CacheError(32911, "Loading of Cache Headers Failed")
	
	@staticmethod
	def readFile(filename):
		''' Return content of file and auto close file '''
		with open(filename, "rb") as fileObject:
			return fileObject.read()
	
	@staticmethod
	def reset(cachePath, times=None):
		''' Reset the access and modified times of the cache '''
		os.utime(cachePath % u"headers", times)
		os.utime(cachePath % u"body", times)
	
	@staticmethod
	def remove(cachePath):
		''' Remove Cache Items '''
		# Remove Headers
		try: os.remove(cachePath % u"headers")
		except: pass
		# Remove Body
		try: os.remove(cachePath % u"body")
		except: pass
	
	@staticmethod
	def store_in_cache(cachePath, response):
		''' Saves Response and Headers to Cache '''
		# Check if Cache Location is Valid
		cacheLocal = os.path.dirname(cachePath)
		if not os.path.exists(cacheLocal): os.makedirs(cacheLocal)
		
		# Save Headers to Cache
		outputFile = open(cachePath % u"headers", "wb")
		headers = response.info()
		headers["X-Cache"] = "HIT"
		headers["X-Location"] = response.url
		try: outputFile.write(str(headers))
		except: raise plugin.CacheError(32911, "Failed to Save Headers to Cache")
		finally: outputFile.close()
		
		# Save Response to Cache
		outputFile = open(cachePath % u"body", "wb")
		try: outputFile.write(response.read())
		except: raise plugin.CacheError(32911, "Failed to Save Body to Cache")
		finally: outputFile.close()
		
		# Close Response Connection
		response.close()
	
	def __init__(self, cachePath):
		# Read in Both Body and Header Responses
		try: StringIO.StringIO.__init__(self, self.readFile(cachePath % u"body"))
		except: raise plugin.CacheError(32911, "Loading of Cache Body Failed")
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
