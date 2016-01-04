"""
	###################### xbmcutil.urlhandler ######################
	Copyright: (c) 2013 William Forde (willforde+kodi@gmail.com)
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

def urlopen(url, maxAge=None, data=None, headers={}, userAgent=1, stripEntity=False):
	''' Makes Request and Return Response Object '''
	handle = HttpHandler()
	handle.add_response_handler(userAgent, stripEntity=stripEntity)
	if maxAge is not None: handle.add_cache_handler(maxAge)
	return handle.open(url, data, headers)

def urlread(url, maxAge=None, data=None, headers={}, userAgent=1, stripEntity=True):
	''' Makes Request and Return Response Data '''
	handle = HttpHandler()
	handle.add_response_handler(userAgent, stripEntity=stripEntity)
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

def redirect(url, data=None, headers={}):
	# Convert url to ascii if needed
	if isinstance(url, unicode): url = url.encode("ascii")
	
	# Log for Debuging
	plugin.debug(url + " - Redirected To:")
	
	# Split url into Components
	splitUrl = urlparse.urlsplit(url)
	
	# Create Connection Object, HTTP or HTTPS
	if splitUrl[0] == "http": conn = httplib.HTTPConnection(splitUrl[1], timeout=10)
	elif splitUrl[0] == "https": conn = httplib.HTTPSConnection(splitUrl[1], timeout=10)
	
	# Set Request Mothods
	if data is not None:
		method = "POST"
		headers["Content-Type"] = "application/x-www-form-urlencoded"
		headers["Content-Length"] = "%d" % len(data)
	else:
		method = "HEAD"
	
	# Make Request to Server
	try: conn.request(method, urlparse.urlunsplit(splitUrl), data, headers)
	except httplib.HTTPException as e: raise plugin.URLError(str(e), "Failed to Make Request for Redirected Url")
	
	# Fetch Headers from Server
	try:
		resp = conn.getresponse()
		plugin.debug("%s - %s" % (resp.status, resp.reason))
		headers = dict(resp.getheaders())
		conn.close()
	except httplib.HTTPException as e: raise plugin.URLError(str(e), "Failed to Read Redirected Server Response")
	
	# Fetch Redirect Location
	if "location" in headers: url = headers["location"]
	elif "uri" in headers: url = headers["uri"]
	else: url = ""
	plugin.debug(url)
	return url.decode("ascii")

class withaddinfourl(urllib2.addinfourl):
	# Methods to add support for with statement
	def __enter__(self): return self
	def __exit__(self, *exc_info): self.close()

#################################################################

class HttpHandler:
	def __init__(self):
		self.handleList = [ErrorHandler]
		self.userAgent = None
	
	def add_response_handler(self, userAgent=1, compressed=True, stripEntity=False):
		''' Adds Response Handler to Urllib to Handle Compression and unescaping '''
		self.handleList.append(ResponseHandler(compressed, stripEntity))
		
		# Set UserAgent
		if userAgent == 1: self.userAgent = "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:35.0) Gecko/20100101 Firefox/35.0"
		elif userAgent == 2: self.userAgent = "Mozilla/5.0 (iPhone; U; CPU iPhone OS 3_0 like Mac OS X; en-us) AppleWebKit/528.18 (KHTML, like Gecko) Version/4.0 Mobile/7A341 Safari/528.16"
		elif isinstance(userAgent, unicode): self.userAgent = userAgent.encode("utf-8")
		elif isinstance(userAgent, str): self.userAgent = userAgent
	
	def add_cache_handler(self, maxAge=0, asUrl=None):
		''' Adds Cache Handler to Urllib to Handle Caching of Source '''
		self.handleList.append(CacheHandler(maxAge, asUrl))
	
	def add_authorization(self, username, password):
		''' Adds Basic Authentication to Requst '''
		self.handleList.append(Authorization(username, password))
	
	def add_cookie_handler(self, cookieName=u"cookies.lwp", loginData={}):
		''' Adds Cookie Support ''' 
		self.handleList.append(HTTPCookieProcessor(cookieName, loginData))
	
	def open(self, url, data=None, headers={}, timeout=10):
		# Create Request Object
		if self.userAgent and not "User-agent" in headers: headers["User-agent"] = self.userAgent
		request = urllib2.Request(self.clean_url(url), data, headers)
		
		# Make Url Connection, Save Cookie If Set and Return Response
		opener = urllib2.build_opener(*self.handleList)
		try: return opener.open(request, timeout=timeout)
		except socket.timeout as e: raise plugin.URLError(str(e))
		except urllib2.URLError as e: raise plugin.URLError(str(e))
	
	def clean_url(self, url):
		# Try and convert url to ascii
		try: return url.encode("ascii")
		except:
			plugin.debug("Failed to convert url to ASCII, quoting url")
			from urlparse import urlsplit, urlunsplit
			# Ascii conversion failed, Encode to utf8
			if isinstance(url, unicode): url = url.encode("utf8")
			
			# Fetch elements of url and quote the problematic parts
			scheme, netloc, path, query, fragment = urlsplit(url)
			path = plugin.urllib.quote(path)
			
			# Create fixed url and return url
			return urlunsplit((scheme, netloc, path, query, fragment)).encode("ascii")

class ErrorHandler(urllib2.HTTPDefaultErrorHandler):
	''' Default Error Handler for Reporting The Error Code to Kodi '''
	def http_error_default(self, req, fp, code, msg, hdrs):
		raise plugin.URLError("HTTPError %s:%s" % (code, msg))

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
			if self.logonAtempted is True: raise plugin.URLError(plugin.getstr(32806), "Logon Already Atempted, Stopping infinite loop")
			else: self.logonAtempted = True
			
			# Login to site and create session cookie
			plugin.debug("Sending Login Data")
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
	def __init__(self, compressed=True, stripEntity=False):
		# Set Global Vars
		global zlib, htmlentitydefs
		import zlib, htmlentitydefs
		self.compressed = compressed
		self.stripEntity = stripEntity
	
	def http_request(self, request):
		''' Add Accept-Encoding & User-Agent Headers '''
		if self.compressed: request.add_header("Accept-encoding", "gzip, deflate")
		request.add_header("Accept-language", "en-gb,en-us,en")
		plugin.notice(request.get_full_url())
		#plugin.debug(request.header_items())
		return request
	
	def handle_response(self, response):
		# Check if Response need to be decoded, else return raw response
		headers = response.info()
		contentCharset = headers.getparam("charset") or headers.getparam("encoding")
		contentEncoding = headers.get("Content-Encoding")
		contentType = headers.gettype()
		
		# If content is compressed then decompress and decode into unicode
		try:
			if contentEncoding and "gzip" in contentEncoding: rawdata = zlib.decompress(response.read(), 16+zlib.MAX_WBITS)
			elif contentEncoding and "deflate" in contentEncoding: rawdata = zlib.decompress(response.read())
			else: rawdata = response.read()
		
		except zlib.error as e:
			raise plugin.URLError(plugin.getstr(32804), str(e))
		
		else:
			# Convert content to unicode and back to utf-8 to fix any issues
			if contentType == "text/html":
				# if no charset was specified in the headers then attempt to fetch from content itself
				if contentCharset: plugin.debug("Character encoding: %s" % contentCharset)
				else:
					try:
						# Attempting to read charset from html body
						contentCharset = re.findall('<meta\s+http-equiv="Content-Type"\s+content=".*?charset=(\S+?)"\s+/>', rawdata)[0]
						plugin.debug("Character encoding: %s" % contentCharset)
					except:
						# Set Charset to default to UTF-8
						plugin.debug("Response encoding not specified, Defaulting to UTF-8")
						contentCharset = "utf-8"
				
				# Convert html to unicode
				try: unicodeData = unicode(rawdata, contentCharset.lower())
				except:
					# Attempt to decode using iso-8859-1 (latin-1)
					plugin.debug("Specified encoding failed, reverting to iso-8859-1 (latin-1)")
					try: unicodeData = unicode(rawdata, "iso-8859-1")
					except UnicodeDecodeError as e: raise plugin.URLError(plugin.getstr(32805), str(e))
				
				# Unescape the content if requested
				if self.stripEntity: rawdata = self.unescape(unicodeData).encode("utf-8")
				else: rawdata = unicodeData.encode("utf-8")
		
		finally:
			# Close Http Resource Request
			response.close()
		
		# Return Data Wraped in an addinfourl Object
		addInfo = withaddinfourl(StringIO.StringIO(rawdata), headers, response.url, response.code)
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
		return re.sub("&#?\w+;", fixup, text)
	
	def http_response(self, request, response):
		''' Returns a Decompress Version of the response '''
		plugin.debug("%s - %s" % (response.code, response.msg))
		if response.code is not 200 or response.info().get("X-Local-Cache") == "HIT": return response
		else: return self.handle_response(response)
	
	# Redirect HTTPS Requests and Responses to HTTP
	https_request = http_request
	https_response = http_response

class CacheHandler(urllib2.BaseHandler):
	'''Stores responses in a persistant on-disk cache'''
	def __init__(self, maxAge=0, asUrl=None):
		global time
		import time
		self.maxAge = maxAge
		self.redirect = False
		self.url = asUrl
		
		# Fetch Disable-Cache Setting
		self.disableCache = plugin.getSetting("disable-cache") == "true"
	
	def default_open(self, request):
		'''
		Returns Cached Response if Cache is not stale
		
		If Cache Exists but is Stale, the If-Modified-Since header
		and If-None-Match header is set.
		'''
		
		# Create Url Hash
		if self.redirect is False:
			_plugin = plugin
			if self.url: url = self.url
			else:
				url = request.get_full_url()
				if request.has_data(): url += request.get_data()
				if request.has_header("Referer"): url += request.get_header("Referer")
			
			# Create Cache Path
			urlHash = md5(url).hexdigest()
			_plugin.debug("UrlHash = %s" % urlHash)
			self.CachePath = CachePath = os.path.join(_plugin.getProfile(), "urlcache", urlHash + u".%s")
			
			# Check Status of Cache
			if CachedResponse.exists(CachePath):
				# If disable Cache is True then remove old cache and return
				if self.disableCache is True: return CachedResponse.remove(CachePath)
				
				# If Refresh Param Exists Then Reset 
				elif "refresh" in _plugin: CachedResponse.reset(CachePath, (0,0))
				
				# Check if Cache is Valid and return Cached Response if valid
				maxAge = self.maxAge
				if not maxAge == 0:
					if maxAge == -1 or CachedResponse.isValid(CachePath, maxAge):
						_plugin.notice("Cached")
						try: return CachedResponse(CachePath)
						except _plugin.CacheError as e:
							CachedResponse.remove(self.CachePath)
							_plugin.error(e.debugMsg)
							return None
					else:
						_plugin.notice("Cache Not Valid")
				
				# Set If-Modified-Since & If-None-Match Headers
				cacheHeaders = CachedResponse.loadHeaders(CachePath)
				if "Last-Modified" in cacheHeaders:
					# Add If-Modified-Since Date to Request Headers
					request.add_header("If-Modified-Since", cacheHeaders["Last-Modified"])
				if "ETag" in cacheHeaders:
					# Add If-None-Match Etag to Request Headers
					request.add_header("If-None-Match", cacheHeaders["ETag"])
			else:
				_plugin.debug("Cache Not Found")
	
	def http_response(self, request, response):
		''' Store Server Response into Cache '''
		# Save response to cache and return it if status is 200 else return response untouched
		self.redirect = False
		if response.code is 200 and self.disableCache is False and not response.info().get("X-Local-Cache") == "HIT":
			try:
				CachedResponse.store_in_cache(self.CachePath, response)
				return CachedResponse(self.CachePath)
			except plugin.CacheError as e:
				CachedResponse.remove(self.CachePath)
				plugin.error(e.debugMsg)
				return response
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
	the network, check the X-Local-Cache header rather than the object type.
	'''
	@staticmethod
	def cleanup(maxAge):
		# Loop each file within urlcache folder
		cachePath = os.path.join(plugin.getProfile(), "urlcache")
		for urlFile in os.listdir(cachePath):
			# Check if file is a Body file then proceed
			if urlFile.endswith(".body"):
				# Fetch urlHash and check if Cache is Stale, then remove
				fullPath = os.path.join(cachePath, urlFile.replace(".body", ".%s"))
				if not CachedResponse.isValid(fullPath, maxAge):
					# If file is not valid then Remove
					CachedResponse.remove(fullPath)
	
	@staticmethod
	def exists(cachePath):
		''' Returns True if Cache Exists, Else Return False '''
		return os.path.isfile(cachePath % u"body") and os.path.isfile(cachePath % u"headers")
	
	@staticmethod
	def isValid(cachePath, maxAge):
		''' Returns True if Cache is Valid, Else Return False '''
		return time.time() - os.stat(cachePath % u"body").st_mtime < maxAge and time.time() - os.stat(cachePath % u"headers").st_mtime < maxAge
	
	@staticmethod
	def loadHeaders(cachePath):
		''' Returns Only the headers to chack If-Modified-Since & If-None-Match '''
		return httplib.HTTPMessage(StringIO.StringIO(CachedResponse.readFile(cachePath % u"headers")))
	
	@staticmethod
	def readFile(filename):
		''' Return content of file and auto close file '''
		try:
			with open(filename, "rb") as fileObject: return fileObject.read()
		except (IOError, OSError) as e:
			raise plugin.CacheError(plugin.getstr(32803), str(e))
	
	@staticmethod
	def reset(cachePath, times=None):
		''' Reset the access and modified times of the cache '''
		os.utime(cachePath % u"headers", times)
		os.utime(cachePath % u"body", times)
	
	@staticmethod
	def remove(cachePath):
		''' Remove Cache Items '''
		plugin.debug("Removing Cache item: %s" % cachePath[:-3])
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
		if "Content-Encoding" in headers: del headers["Content-Encoding"]
		headers["X-Local-Cache"] = "HIT"
		headers["X-Location"] = response.url
		try: outputFile.write(str(headers))
		except (IOError, OSError) as e: raise plugin.CacheError(plugin.getstr(32803), str(e))
		finally: outputFile.close()
		
		# Save Response to Cache
		outputFile = open(cachePath % u"body", "wb")
		try: outputFile.write(response.read())
		except (IOError, OSError) as e: raise plugin.CacheError(plugin.getstr(32803), str(e))
		finally: outputFile.close()
		
		# Close Response Connection
		response.close()
	
	def __init__(self, cachePath):
		# Read in Both Body and Header Responses
		StringIO.StringIO.__init__(self, self.readFile(cachePath % u"body"))
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
	
	# Methods to add support for with statement
	def __enter__(self): return self
	def __exit__(self, *exc_info): self.close()
