"""
	###################### xbmcutil.videoResolver ######################
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
import urlhandler, HTMLParser, urlparse, re

# Call Sub Imports
from xbmcutil import plugin
registrar = []

#######################################################################################

class MainParser(HTMLParser.HTMLParser):
	'''
	Take in a HTML Page and Parses the Content Using Python HTMLParser
	Filter Embedded videos and returns Sources Urls
	
	>>>MainParser(HTML)
	["http://www.youtube.com/embed/videoseries?list=PL93A20AE977AA9911&hl=en_US&iv_load_policy=3", "http://video.google.com/googleplayer.swf?docId=7502243539190558658"]
	'''
	
	def parse(self, html):
		self.sourceUrls = set()
		self.feed(html)
		self.close()
	
	def handle_starttag(self, tag, attrs):
		if tag == u"iframe": self.handle_iframe(dict(attrs))
		elif tag == u"param": self.handle_param(dict(attrs))
		elif tag == u"embed": self.handle_embed(dict(attrs))
	
	def handle_iframe(self, attrs):
		if u"src" in attrs and attrs[u"src"][:4] == u"http":
			self.sourceUrls.add(attrs[u"src"])
	
	def handle_param(self, attrs):
		if u"name" in attrs and u"value" in attrs and attrs[u"name"] == u"movie" and attrs[u"value"][:4] == u"http":
			self.sourceUrls.add(attrs[u"value"])
	
	def handle_embed(self, attrs):
		if u"src" in attrs and attrs[u"src"][:4] == u"http":
			self.sourceUrls.add(attrs[u"src"])

class RegexParser:
	'''
	Take in a HTML Page and Parses the Content Using Regex Searches
	Filter Embedded videos and returns Sources Urls
	
	>>>RegexParser(HTML)
	["http://www.youtube.com/embed/videoseries?list=PL93A20AE977AA9911&hl=en_US&iv_load_policy=3", "http://video.google.com/googleplayer.swf?docId=7502243539190558658"]
	'''
	
	def parse(self, html):
		self.sourceUrls = set()
		self.html = html
		self.search()
	
	def dict(self, attrs):
		attrsDict = {}
		for part in attrs.strip().replace(u'"','').replace(u"'","").replace(u'\\','').split(u" "):
			if u"=" in part:
				key, value = part.split(u"=",1)
				attrsDict[key.lower()] = value
		return attrsDict
	
	def search(self):
		for attrs in re.findall('<iframe(.*?)[/]*>', self.html, re.DOTALL | re.IGNORECASE): self.handle_iframe(self.dict(attrs))
		for attrs in re.findall('<param(.*?)[/]*>', self.html, re.DOTALL | re.IGNORECASE): self.handle_param(self.dict(attrs))
		for attrs in re.findall('<embed(.*?)[/]*>', self.html, re.DOTALL | re.IGNORECASE): self.handle_embed(self.dict(attrs))
	
	def handle_iframe(self, attrs):
		if u"src" in attrs and attrs[u"src"][:4] == u"http":
			self.sourceUrls.add(attrs[u"src"])
	
	def handle_param(self, attrs):
		if u"name" in attrs and u"value" in attrs and attrs[u"name"] == u"movie" and attrs[u"value"][:4] == u"http":
			self.sourceUrls.add(attrs[u"value"])
	
	def handle_embed(self, attrs):
		if u"src" in attrs and attrs[u"src"][:4] == u"http":
			self.sourceUrls.add(attrs[u"src"])

class SoupParser:
	'''
	Take in a HTML Page and Parses the Content Using Beautiful Soup
	Filter Embedded videos and returns Sources Urls
	
	>>>SoupParser(HTML)
	["http://www.youtube.com/embed/videoseries?list=PL93A20AE977AA9911&hl=en_US&iv_load_policy=3", "http://video.google.com/googleplayer.swf?docId=7502243539190558658"]
	'''
	
	def parse(self, html):
		from BeautifulSoup import BeautifulSoup
		self.httpCompile = re.compile('^http://')
		self.soup = BeautifulSoup(html)
		self.sourceUrls = set()
		self.search()
	
	def search(self):
		for attrs in self.soup.findAll(u"iframe", {u"src":self.httpCompile}): self.handle_iframe(attrs)
		for attrs in self.soup.findAll(u"param", {u"name":u"movie",u"value":self.httpCompile}): self.handle_param(attrs)
		for attrs in self.soup.findAll(u"embed", {u"src":self.httpCompile}): self.handle_embed(attrs)
	
	def handle_iframe(self, attrs):
		self.sourceUrls.add(attrs[u"src"])
	
	def handle_param(self, attrs):
		self.sourceUrls.add(attrs[u"value"])
	
	def handle_embed(self, attrs):
		self.sourceUrls.add(attrs[u"src"])

#######################################################################################

class VideoParser:
	'''
	Takes in a HTML Page or URL and returns a list of available video sources
	witch can be sorted by priority if required.
	Raises ParserError if failed to parse html.
	
	>>> VideoParser.parse("http://www.justdubs.net/article/Episodes/12391")
	>>> VideoParser.getSources(sort=True)
	[{'domain':'www.youtube.com', 'vodepid':'st40Gps08KI', 'function':youtube_com, 'isplaylist':False, 'priority':99}, {'domain':'video.google.com', 'vodepid':'-369888258105653405', 'function':google_com, 'isplaylist':False, 'priority':95}]
	
	>>> VideoParser.processUrls(["http://www.youtube.com/v/c64Aia4XE1Y","http://videobb.com/e/ZaibwUjYLlxJ"])
	>>> VideoParser.get(sort=False)
	[{'domain':'videobb.com', 'vodepid':'ZaibwUjYLlxJ', 'function':videobb_com, 'isplaylist':False, 'priority':71}, {'domain':'www.youtube.com', 'vodepid':'st40Gps08KI', 'function':youtube_com, 'isplaylist':False, 'priority':100}]
	'''
	
	def parse(self, arg, maxAge=86400):
		'''
		Takes in a url to a online resource or the HTML to that online resource and
		Passes it into the Custom Parsers to Find Embeded Sources
		'''
		# Check if arg is a URL Then Fetch HTML Source
		if arg.startswith(u"http://") or arg.startswith(u"https://"):
			sourceObj = urlhandler.urlopen(arg, maxAge)
			htmlSource = sourceObj.read().decode("utf8")
			sourceObj.close()
		else:
			htmlSource = arg
		
		# Feed the HTML into the HTMLParser and acquire the source urls
		sourceUrls = self.htmlparser(htmlSource)
		if not sourceUrls: raise plugin.ParserError(32973, "No Video Sources ware found")
		else: self.setUrls(sourceUrls)
	
	def setUrls(self, sourceUrls):
		# Process Available Sources
		plugin.log("Source url's: " + str(sourceUrls))
		parsedUrls = self.processUrls(sourceUrls)
		
		# Check for Supported Sources
		if not parsedUrls: raise plugin.ParserError(32970, "No Supported Video Sources ware found")
		else: self.parsedUrls = parsedUrls
	
	def htmlparser(self, htmlSource):
		'''
		Parses the HTML Source into the Custom Parsers that Finds all
		Embeded Urls and Returns the List of Urls
		'''
		
		try:
			# Try Parse HTML Using HTMLParser
			customParser = MainParser()
			customParser.parse(htmlSource)
			return customParser.sourceUrls
		except: plugin.log("HTML Parser Failed: Falling Back to Regex", 0)
		
		try:
			# Try Parse HTML Using Regex
			customParser = RegexParser()
			customParser.parse(htmlSource)
			return customParser.sourceUrls
		except: plugin.log("Regex Parser Failed: Falling Beautiful Soup", 0)
		
		try:
			# Try Parse HTML Using Beautiful Soup
			customParser = SoupParser()
			customParser.parse(htmlSource)
			return customParser.sourceUrls
		except: plugin.log("Beautiful Soup Parser Failed: All Out Total Failure", 0)
		
		# Raise ParserError when all three parsers have failded
		raise plugin.ParserError(32972, "HTML Parsing Failed")
	
	def processUrls(self, sourceUrls):
		'''
		Take in a list of Embeded Source Urls and Create a list Containing
		information about the Sources found and the required Decoder.
		''' 
		
		# Filter Video Sources
		parsedUrls = []
		for url in sourceUrls:
			filtered = self.process(urlparse.urlsplit(url))
			if filtered: parsedUrls.append(filtered)
		
		# Return list of processed Urls
		return parsedUrls
	
	def process(self, urlObject):
		'''
		Takes in urlparsers urlsplit Object and passes it into the avalable Plugins
		that checkes if the url can be decoded. Returns the appropriate Plugin when a Match is found.
		'''
		
		# Loop Available Pluging to find Matching Domain
		for pluginObject, domain in registrar:
			if domain in urlObject[1]:
				return pluginObject().strip(*urlObject)
		
		# Log The UnSupported Video Source for Future Identification
		plugin.log(u"Video Source UnSupported\nDomain = %s\nurl    = %s" % (urlObject[1], urlObject.geturl()), 0)
	
	def get(self, sort=True):
		'''
		Returns the list of Source Info & Decoders and Sorts the list by priority if Requested
		'''
		if sort and len(self.parsedUrls) > 1: return sorted(self.parsedUrls, key=lambda priority: priority["priority"], reverse=True)
		else: return self.parsedUrls

class Plugin(type):
	'''
	Plugin Class Required as a metaclass for each Plugin that needs to Register its Existence
	'''
	def __init__(cls, name, bases, dct):
		super(Plugin, cls).__init__(name, bases, dct)
		registrar.append((cls, name.replace("_",".")))

def check_arg(pluginName):
	def decorator(function):
		def wrapper(self, oarg):
			arg = oarg
			if arg[:4] == u"http": arg = self.strip(*urlparse.urlsplit(arg), returnID=True)
			if not arg: raise plugin.videoResolver(32918, u"Unable to Strip out videoID ==> %s ==> %s" % (pluginName, oarg))
			else:
				# Call Function and return response
				plugin.setDebugMsg("VideoResolver", u"Select Source ==> %s ==> %s" % (pluginName, arg))
				return function(self, arg)
		return wrapper
	return decorator

def parse_qs(query):
	'''
	Takes in a Query Stirng and Converts to a Dictionary with Lower Case Keys
	'''
	qDict = {}
	for key,value in urlparse.parse_qsl(query):
		if key in qDict: qDict[key.lower()].append(value)
		else: qDict[key.lower()] = [value]
	return qDict

def jsUnpack(sJavascript):
	aSplit = sJavascript.split(";',")
	p = str(aSplit[0])
	aSplit = aSplit[1].split(",")
	a = int(aSplit[0])
	c = int(aSplit[1])
	k = aSplit[2].split(".")[0].replace("'", '').split('|')
	e = ''
	d = ''
	sUnpacked = str(__unpack(p, a, c, k, e, d))
	return sUnpacked.replace('\\', '')

def __unpack(p, a, c, k, e, d):
	while (c > 1):
		c = c -1
		if (k[c]):
			p = re.sub('\\b' + str(__itoa(c, a)) +'\\b', k[c], p)
	return p

def __itoa(num, radix):
	result = ""
	while num > 0:
		result = "0123456789abcdefghijklmnopqrstuvwxyz"[num % radix] + result
		num /= radix
	return result

#######################################################################################

class youtube_com(object):
	'''
	Takes a video id from a Youtube video page url, or takes a complete url 
	to a Youtube swf and returns the url to the actual video resource.
	Raises videoResolver Error if no match is found.
	
	>>> youtube_com.decode('http://www.youtube.com/v/c64Aia4XE1Y')
	'http://o-o.preferred.dub06s01.v22.lscache8.c.youtube.com/videoplayback?sparams=id%2Cexpire%2Cip%2Cipbits%2Citag%2Csource%2Calgorithm%2Cburst%2Cfactor%2Ccp&fexp=909513%2C914051%2C910102%2C913601%2C914102%2C902516&algorithm=throttle-factor&itag=34&ip=93.0.0.0&burst=40&sver=3&signature=CB2444C0FE8F08F9C8A5187CD8A7ECB9300F7D08.84A27889772123BA3F53BA5F1D2B6390E9EFF14E&source=youtube&expire=1327129325&key=yt1&ipbits=8&factor=1.25&cp=U0hRTFFNV19HT0NOMV9JR0FEOk5FVGY5blpiSjQx&id=73ae0089ae171356'
	
	>>> youtube_com.decode('c64Aia4XE1Y')
	'http://o-o.preferred.dub06s01.v22.lscache8.c.youtube.com/videoplayback?sparams=id%2Cexpire%2Cip%2Cipbits%2Citag%2Csource%2Calgorithm%2Cburst%2Cfactor%2Ccp&fexp=909513%2C914051%2C910102%2C913601%2C914102%2C902516&algorithm=throttle-factor&itag=34&ip=93.0.0.0&burst=40&sver=3&signature=CB2444C0FE8F08F9C8A5187CD8A7ECB9300F7D08.84A27889772123BA3F53BA5F1D2B6390E9EFF14E&source=youtube&expire=1327129325&key=yt1&ipbits=8&factor=1.25&cp=U0hRTFFNV19HT0NOMV9JR0FEOk5FVGY5blpiSjQx&id=73ae0089ae171356'
	'''
	__metaclass__ = Plugin
	def __init__(self, priority=100):
		import videohostsAPI
		self.api = videohostsAPI
		self.priority = priority
	
	def strip(self, scheme, netloc, path, query, fragment, returnID=False):
		if path.lower() is u"/embed/videoseries":
			playlistID = parse_qs(query)[u"list"][0]
			if returnID: return playlistID
			else: return {"domain":netloc, "vodepid":playlistID, "function":self.decode_playlist, "isplaylist":True, "priority":self.priority-1}
		elif path.lower().startswith(u"/embed/") or path.lower().startswith(u"/v/"):
			videoID = path[path.rfind(u"/")+1:]
			if returnID: return videoID
			else: return {"domain":netloc, "vodepid":videoID, "function":self.decode, "isplaylist":False, "priority":self.priority}
		elif path.lower().startswith(u"/watch"):
			videoID = parse_qs(query)[u"v"][0]
			if returnID: return videoID
			else: return {"domain":netloc, "vodepid":videoID, "function":self.decode, "isplaylist":False, "priority":self.priority}
		else: 
			plugin.log("Unable to Strip out video id from youtube source url")
			return None
	
	@check_arg(u"Youtube")
	def decode(self, arg):
		# Fetch Video Processer Object and Return Decoded Url
		if plugin.get("download",u"false") == u"true": return {"url":u"plugin://plugin.video.youtube/?action=download&videoid=%s" % arg}
		else: return {"url":u"plugin://plugin.video.youtube/?action=play_video&videoid=%s" % arg}
	
	@check_arg(u"Youtube Playlist")
	def decode_playlist(self, arg):
		# Initialize Gdata API
		Gdata = self.api.YoutubeAPI(u"http://gdata.youtube.com/feeds/api/playlists/%s" % arg)
		Gdata.ProcessUrl()
		
		# Fetch list of urls and listiems
		markForDownload = plugin.get("download",u"false") == u"true"
		return [{"url":url + "&download=true", "item":listitem} if markForDownload else {"url":url, "item":listitem} for url, listitem, isfolder in Gdata.VideoGenerator()]
	
	def checker(self, testcard=u"c64Aia4XE1Y"):
		plugin.log("Checking Youtube Decoder", 0)
		try: 
			videoUrl = self.decode(testcard)
			plugin.log("#########################################", 0)
			plugin.log(u"PASS: Successfully Decoded %s" % testcard, 0)
			plugin.log( videoUrl)
			return videoUrl
		except:
			plugin.log("#######################################", 0)
			plugin.log(u"FAILED: Unable to Devode %s" % testcard, 0)

class youtu_be(youtube_com): pass

#######################################################################################

class vimeo_com(object):
	'''
	Takes a video id from a Vimeo video page url, or takes a complete url 
	to a Vimeo swf and returns the url to the actual video resource.
	Raises videoResolver Error if no match is found.
	
	>>> vimeo_com.decode('http://player.vimeo.com/video/34242816?title=0&byline=0&portrait=0')
	'http://av.vimeo.com/68932/441/78039067.mp4?token=1327120954_425c5e7baa06f349386b5479f9cb6d0e'
	
	>>> vimeo_com.decode('34242816')
	'http://av.vimeo.com/68932/441/78039067.mp4?token=1327120954_425c5e7baa06f349386b5479f9cb6d0e'
	'''
	__metaclass__ = Plugin
	def __init__(self, priority=97):
		self.priority = priority
	
	def strip(self, scheme, netloc, path, query, fragment, returnID=False):
		videoID = path[path.rfind(u"/")+1:]
		if returnID: return videoID
		else: return {"domain":netloc, "vodepid":videoID, "function":self.decode, "isplaylist":False, "priority":self.priority}
	
	@check_arg(u"Vimeo")
	def decode(self, arg):
		# Fetch Video Processer Object and Return Decoded Url
		if plugin.get("download",u"false") == u"true": return {"url":u"plugin://plugin.video.vimeo/?action=download&videoid=%s" % arg}
		else: return {"url":u"plugin://plugin.video.vimeo/?action=play_video&videoid=%s" % arg}
	
	def checker(self, testcard=u"34242816"):
		plugin.log("Checking Vimeo Decoder", 0)
		try: 
			videoUrl = self.decode(testcard)
			plugin.log("#########################################", 0)
			plugin.log(u"PASS: Successfully Decoded %s" % testcard, 0)
			plugin.log( videoUrl)
			return videoUrl
		except:
			plugin.log("#######################################", 0)
			plugin.log(u"FAILED: Unable to Devode %s" % testcard, 0)

#######################################################################################

class dailymotion_com(object):
	'''
	Takes a video id from a DailyMotion video page url, or takes a complete url 
	to a DailyMotion swf and returns the url to the actual video resource.
	Raises videoResolver Error if no match is found.
	
	>>> dailymotion_com.decode('http://www.dailymotion.com/video/x162i8b_top-10-video-games-with-great-stories_videogames')
	'http://proxy-13.dailymotion.com/sec(e8b6ec3b1050ca92a370bbda2fc3528e)/frag(3)/video/118/066/70660811_mp4_h264_aac_hq_2.flv'
	
	>>> dailymotion_com.decode('x162i8b')
	'http://proxy-13.dailymotion.com/sec(e8b6ec3b1050ca92a370bbda2fc3528e)/frag(3)/video/118/066/70660811_mp4_h264_aac_hq_2.flv'
	'''
	__metaclass__ = Plugin
	def __init__(self, priority=96):
		self.priority = priority
	
	def strip(self, scheme, netloc, path, query, fragment, returnID=False):
		videoID = path[path.rfind(u"/")+1:].split(u"_",1)[0]
		if returnID: return videoID
		else: return {"domain":netloc, "vodepid":videoID, "function":self.decode, "isplaylist":False, "priority":self.priority}
	
	@check_arg(u"DailyMotion")
	def decode(self, arg):
		# Fetch Redirected Url
		url = u"http://www.dailymotion.com/embed/video/%s" % arg
		sourceCode = urlhandler.urlread(url)
		
		# Fetch list of Urls
		sourceCode = re.findall('var info = (\{.+?\}),', sourceCode)[0]
		Sources = dict([[part for part in match if part] for match in re.findall('"(stream_h264_url)":"(\S+?)",|"(stream_h264_ld_url)":"(\S+?)",|"(stream_h264_hq_url)":"(\S+?)",|"(stream_h264_hd_url)":"(\S+?)",|"(stream_h264_hd1080_url)":"(\S+?)",', sourceCode)])
		if not Sources: raise plugin.videoResolver(33077, "Unable to Find Video Url")
		
		# Fetch Video Quality
		Quality = plugin.getQuality()
		if  Quality == u"1080p": Quality = 5
		elif Quality == u"720p": Quality = 4
		else: Quality = 3
		
		# Return Available Format
		for res in (u"stream_h264_hd1080_url", u"stream_h264_hd_url", u"stream_h264_hq_url", u"stream_h264_ld_url", u"stream_h264_url")[-(Quality):]:
			if res in Sources: return {"url":Sources[res].replace(u"\\/", u"/")}
			else: continue
		
		# Fallback to any quality if unable to find format
		return {"url":Sources[Sources.keys()[0]]}
	
	def checker(self, testcard=u"x162i8b"):
		plugin.log("Checking DailyMotion Decoder", 0)
		try: 
			videoUrl = self.decode(testcard)
			plugin.log("#########################################", 0)
			plugin.log(u"PASS: Successfully Decoded %s" % testcard, 0)
			plugin.log( videoUrl)
			return videoUrl
		except:
			plugin.log("#######################################", 0)
			plugin.log(u"FAILED: Unable to Devode %s" % testcard, 0)

#######################################################################################

class blip_tv(object):
	'''
	Takes a video id from a BlipTV video page url, or takes a complete url 
	to a BlipTV swf and returns the url to the actual video resource.
	Raises videoResolver Error if no match is found.
	
	>>> blip_tv.decode('http://blip.tv/play/AYOW3REC.html')
	'http://blip.tv/file/get/Linuxjournal-GetFirefoxMenuButtonInLinux474.m4v'
	
	>>> blip_tv.decode('AYOW3REC'|'6663725')
	'http://blip.tv/file/get/Linuxjournal-GetFirefoxMenuButtonInLinux474.m4v'
	'''
	__metaclass__ = Plugin
	def __init__(self, priority=95):
		self.priority = priority
	
	def strip(self, scheme, netloc, path, query, fragment, returnID=False):
		videoID = path[path.rfind(u"/")+1:].split(u".")[0]
		if returnID: return videoID
		else: return {"domain":netloc, "vodepid":videoID, "function":self.decode, "isplaylist":False, "priority":self.priority}
	
	@check_arg(u"BlipTV")
	def decode(self, arg):
		# Check if arg is the embeded ID or VideoID
		if arg.isdigit():
			# Fetch Redirected Url
			url = u"http://blip.tv/play/%s" % arg
			reUrl = urlhandler.redirect(url)
			
			# Filter out VideoCode
			try: arg = re.findall('flash%2F(.+?)&', reUrl)[0]
			except: raise plugin.videoResolver(33077, "Unable to filter out Video Code")
		
		# Fetch XMLSource
		url = u"http://blip.tv/rss/flash/%s" % arg
		sourceObj = urlhandler.urlopen(url)
		import xml.etree.ElementTree as ElementTree
		media = u"http://search.yahoo.com/mrss/"
		tree = ElementTree.parse(sourceObj)
		sourceObj.close()
		
		# Fetch list of Media Content Found
		filtered = ((int(node.get(u"height",0)), node.attrib) for node in tree.getiterator(u"{%s}content" % media) if not node.get(u"type") == u"text/plain")
		
		# Fetch Video Quality and return video
		quality = int(plugin.getQuality().replace(u"p",u""))
		qualitySorted = sorted(filtered, key=lambda x: x[0], reverse=True)
		for content in qualitySorted:
			if content[0] <= quality:
				videoInfo = content[1]
				return {"url":videoInfo[u"url"], "type":videoInfo[u"type"]}
		
		# Fallback to hightest available quality
		videoInfo = qualitySorted[0][1]
		return {"url":videoInfo[u"url"], "type":videoInfo[u"type"]}
	
	def checker(self, testcard=u"AYOW3REC"):
		plugin.log("Checking BlipTV Decoder", 0)
		try: 
			videoUrl = self.decode(testcard)
			plugin.log("#########################################", 0)
			plugin.log(u"PASS: Successfully Decoded %s" % testcard, 0)
			plugin.log( videoUrl)
			return videoUrl
		except:
			plugin.log("#######################################", 0)
			plugin.log(u"FAILED: Unable to Devode %s" % testcard, 0)

#######################################################################################

class veehd_com(object):
	'''
	Takes a video id from a veehd video page url, or takes a complete url 
	to a veehd swf and returns the url to the actual video resource.
	Raises videoResolver Error if no match is found.
	
	>>> veehd_com.decode('http://veehd.com/embed?v=4700076&w=720&h=406&t=2&s=6000&p=divx')
	'http://v33.veehd.com/dl/92c8e1b53f19f27697e16d186c28f17b/1327678479/5000.4686958.mp4&b=390'
	
	>>> veehd_com.decode('4700076')
	'http://v33.veehd.com/dl/92c8e1b53f19f27697e16d186c28f17b/1327678479/5000.4686958.mp4&b=390'
	'''
	__metaclass__ = Plugin
	def __init__(self, priority=94):
		self.priority = priority
	
	def strip(self, scheme, netloc, path, query, fragment, returnID=False):
		if path.lower().startswith(u"/embed"): videoID = parse_qs(query)[u"v"][0]
		elif path.lower().startswith(u"/video/"): videoID = path.strip(u"/video/").split(u"_")[0]
		else: 
			plugin.log("Unable to Strip out video id from veehd.com source url")
			return None
		
		if returnID: return videoID
		else: return {"domain":netloc, "vodepid":videoID, "function":self.decode, "isplaylist":False, "priority":self.priority}
	
	@check_arg(u"Veehd")
	def decode(self, arg):
		# Create Url String and Download HTML Page
		url = u"http://veehd.com/video/%s" % arg
		handle = urlhandler.HttpHandler()
		handle.add_response_handler()
		htmlSource = handle.open(url).read().decode("utf8")
		
		# Fetch Video Info Page Url and Download HTML Page
		try: url = u"http://veehd.com" + re.findall('load_stream\(\)\{\s+\$\("#playeriframe"\).attr\(\{src : "(/vpi.+?)"\}\);\s+\}',htmlSource)[0]
		except: raise plugin.videoResolver(33077, "Was unable to Find Veehd Video Info Page Url")
		else: htmlSource = handle.open(url).read().decode("utf8")
		
		# Search for Video Url Using Params Method
		try: return {"url":re.findall('<param\s+name="src"\svalue="(http://\S+?)">',htmlSource)[0]}
		except: plugin.setDebugMsg("VideoResolver", "Video Url Search using params Failed")
		
		# search for Video Url Using Embed Method
		try: return {"url":re.findall('<embed\s+type="video/divx"\s+src="(http://\S+?)"',htmlSource)[0]}
		except: plugin.setDebugMsg("VideoResolver", "Video Url Search using embed Failed")
		
		# Search for Video Url Javascript Method
		import urllib
		try: return {"url":urllib.unquote_plus(re.findall('"url":"(\S+?)"',htmlSource)[0].encode("ascii"))}
		except: raise plugin.videoResolver(33077, "Was unable to Find Veehd Video Url or Decode It")
	
	def checker(self, testcard=u"4700076"):
		plugin.log("Checking Veehd Decoder", 0)
		try: 
			videoUrl = self.decode(testcard)
			plugin.log("#########################################", 0)
			plugin.log(u"PASS: Successfully Decoded %s" % testcard, 0)
			plugin.log( videoUrl)
			return videoUrl
		except:
			plugin.log("#######################################", 0)
			plugin.log(u"FAILED: Unable to Devode %s" % testcard, 0)

#######################################################################################

class www_4shared_com(object):
	'''
	Takes a video id from a 4shared video page url, or takes a complete url 
	to a 4shared swf and returns the url to the actual video resource.
	Raises videoResolver Error if no match is found.
	
	>>> 4shared_com.decode('http://www.4shared.com/embed/488295743/e62f15bd')
	'http://dc171.4shared.com/img/260186666/598f38a8/dlink__2Fdownload_2FsRLkhHko_3Ftsid_3D20120126-030811-665332a8/preview.flv?file=http://dc171.4shared.com/img/260186666/598f38a8/dlink__2Fdownload_2FsRLkhHko_3Ftsid_3D20120126-030811-665332a8/preview.flv&start=0'
	
	>>> 4shared_com.decode('488295743/e62f15bd')
	'http://dc171.4shared.com/img/260186666/598f38a8/dlink__2Fdownload_2FsRLkhHko_3Ftsid_3D20120126-030811-665332a8/preview.flv?file=http://dc171.4shared.com/img/260186666/598f38a8/dlink__2Fdownload_2FsRLkhHko_3Ftsid_3D20120126-030811-665332a8/preview.flv&start=0'
	'''
	__metaclass__ = Plugin
	def __init__(self, priority=72):
		self.priority = priority
	
	def strip(self, scheme, netloc, path, query, fragment, returnID=False):
		videoID = path.strip(u"/embed/")
		if returnID: return videoID
		else: return {"domain":netloc, "vodepid":videoID, "function":self.decode, "isplaylist":False, "priority":self.priority}
	
	@check_arg(u"4Shared")
	def decode(self, arg):
		# Fetch Redirected Url
		url = u"http://www.4shared.com/embed/%s" % arg
		reUrl = urlhandler.redirect(url)
		
		# Parse Url String and Create Dict
		urlDict = parse_qs(urlparse.urlsplit(reUrl)[3])
		
		# Check if the Required Keys Exist
		if u"file" in urlDict and u"streamer" in urlDict: return {"url":u"%s?file=%s&start=0" % (urlDict[u"streamer"][0], urlDict[u"file"][0])}
		else: raise plugin.videoResolver(33077, "Required Key Not Found in Redirected Url")
	
	def checker(self, testcard=u"488295743/e62f15bd"):
		plugin.log("Checking 4Shared Decoder", 0)
		try: 
			videoUrl = self.decode(testcard)
			plugin.log("#########################################", 0)
			plugin.log(u"PASS: Successfully Decoded %s" % testcard, 0)
			plugin.log( videoUrl)
			return videoUrl
		except:
			plugin.log("#######################################", 0)
			plugin.log(u"FAILED: Unable to Devode %s" % testcard, 0)

#######################################################################################

class uploadc_com(object):
	'''
	Takes a video id from a uploadc video page url, or takes a complete url 
	to a uploadc swf and returns the url to the actual video resource.
	Raises videoResolver Error if no match is found.
	
	>>> uploadc_com.decode('http://www.uploadc.com/embed-mcc8uenje34i.html')
	'http://www1.uploadc.com:182/d/rqgabh5gvsulzrqm3ln6pcvoamzh5zsdbpurbtaty6adou55pzhyjqt3/Zegapain+-+Episode+25.mkv'
	
	>>> uploadc_com.decode('mcc8uenje34i')
	'http://www1.uploadc.com:182/d/rqgabh5gvsulzrqm3ln6pcvoamzh5zsdbpurbtaty6adou55pzhyjqt3/Zegapain+-+Episode+25.mkv'
	'''
	__metaclass__ = Plugin
	def __init__(self, priority=71):
		self.priority = priority
	
	def strip(self, scheme, netloc, path, query, fragment, returnID=False):
		videoID = path[path.find(u"embed-")+6:path.rfind(u".")]
		if returnID: return videoID
		else: return {"domain":netloc, "vodepid":videoID, "function":self.decode, "isplaylist":False, "priority":self.priority}
	
	@check_arg(u"UploadC")
	def decode(self, arg):
		# Create Url String and Fetch HTML Page
		url = u"http://www.uploadc.com/embed-%s.html" % arg
		sourceObj = urlhandler.urlopen(url)
		htmlSource = sourceObj.read()
		sourceObj.close()
		
		# Fetch JavaScript Code and Unpack
		try: jsCode = jsUnpack(re.findall("<script type='text/javascript'>eval\((.+?)\)\s+</script>", htmlSource)[0])
		except: raise plugin.videoResolver(33077, "Was unable to Find JavaScript and Unpack It")
		
		# Fetch Video ID From JavaScript Code
		import urllib
		try: return {"url":re.findall('<param name="src"0="(http://\S+?)"/>', jsCode)[0], "referer":url.encode("ascii")}
		except: raise plugin.videoResolver(33077, "Video Url Was Not Found in JavaScript Code")
	
	def checker(self, testcard=u"mcc8uenje34i"):
		plugin.log("Checking Uploadc Decoder", 0)
		try: 
			videoUrl = self.decode(testcard)
			plugin.log("#########################################", 0)
			plugin.log(u"PASS: Successfully Decoded %s" % testcard, 0)
			plugin.log( videoUrl)
			return videoUrl
		except:
			plugin.log("#######################################", 0)
			plugin.log(u"FAILED: Unable to Devode %s" % testcard, 0)

#######################################################################################

class putlocker_com(object):
	'''
	Takes a video id from a PutLocker video page url, or takes a complete url 
	to a PutLocker swf and returns the url to the actual video resource.
	Raises videoResolver Error if no match is found.
	
	>>> putlocker_com.decode('http://www.putlocker.com/embed/21NRHEZN4Z17')
	'http://media-b30.putlocker.com/download/69/imbtcd1_arc_56c02.flv/daac7e476510246bb24ca320e6468969/4f1a63dc'
	
	>>> putlocker_com.decode('21NRHEZN4Z17')
	'http://media-b30.putlocker.com/download/69/imbtcd1_arc_56c02.flv/daac7e476510246bb24ca320e6468969/4f1a63dc'
	'''
	__metaclass__ = Plugin
	def __init__(self, priority=70):
		self.priority = priority
	
	def strip(self, scheme, netloc, path, query, fragment, returnID=False):
		videoID = path[path.rfind(u"/")+1:]
		if returnID: return videoID
		else: return {"domain":netloc, "vodepid":videoID, "function":self.decode, "isplaylist":False, "priority":self.priority}
	
	@check_arg(u"PutLocker")
	def decode(self, arg):
		# Construct Embedded Url and Fetch Server Response
		url = u"http://www.putlocker.com/embed/%s" % arg
		handle = urlhandler.HttpHandler()
		handle.add_response_handler()
		response = handle.open(url).read()
		
		# Fetch Cookie and Hash Values
		try: hash = "fuck_you=%s&confirm=Close+Ad+and+Watch+as+Free+User" % (re.findall('<input type="hidden" value="(\S+?)" name="fuck_you">', response)[0])
		except: raise plugin.videoResolver(33077, "Failed to Read Hash Value used for validating the Cookie")
		
		# Validate Cookie with the Hash Value
		response = handle.open(url, hash, {"Referer":url.encode("ascii")}).read()
		
		# Construct Embedded Url and Fetch Video Info
		try: url = "http://www.putlocker.com/get_file.php?stream=%s" % (re.findall('/get_file.php\?stream=(\S+)', response)[0])
		except: raise plugin.videoResolver(33077, "Failed to Validate Cookie and Fetch Embed Code")
		
		# Connect to Server to Download Video Source Data
		response = handle.open(url)
		
		# Fetch and Return Video Url
		import xml.etree.ElementTree as ElementTree
		media = u"http://search.yahoo.com/mrss/"
		tree = ElementTree.parse(response)
		response.close()
		
		# Loop each media content element and find video url
		for node in tree.getiterator(u"{%s}content" % media):
			url = node.get(u"url")
			type = node.get(u"type")
			if url is not None and type[:5] == u"video":
				return {"url":url, "type":type}
		
		# Raise Error if unable to return any video url
		raise plugin.videoResolver(33077, "Failed to Read Video Url")
	
	def checker(self, testcard=u"21NRHEZN4Z17"):
		plugin.log("Checking PutLocker Decoder", 0)
		try: 
			videoUrl = self.decode(testcard)
			plugin.log("#########################################", 0)
			plugin.log(u"PASS: Successfully Decoded %s" % testcard, 0)
			plugin.log( videoUrl)
			return videoUrl
		except:
			plugin.log("#######################################", 0)
			plugin.log(u"FAILED: Unable to Devode %s" % testcard, 0)

#######################################################################################

class kqed_org(object):
	'''
	Takes a video id from a kqed.org video page url, or takes a complete url 
	to a kqed.org swf and returns the url to the actual video resource.
	Raises videoResolver Error if no match is found.
	
	>>> kqed_org.decode('http://www.kqed.org/quest/television/embed/502')
	'http://www.kqed.org/.stream/anon/quest/116b_exoplanets_e.flv'
	
	>>> kqed_org.decode('502')
	'http://www.kqed.org/.stream/anon/quest/116b_exoplanets_e.flv'
	'''
	__metaclass__ = Plugin
	def __init__(self, priority=51):
		self.priority = priority
	
	def strip(self, scheme, netloc, path, query, fragment, returnID=False):
		videoID = path[path.rfind(u"/")+1:]
		if returnID: return videoID
		else: return {"domain":netloc, "vodepid":videoID, "function":self.decode, "isplaylist":False, "priority":self.priority}
	
	@check_arg(u"kqed.org")
	def decode(self, arg):
		# Create Url String and Fetch HTML Page
		url = u"http://www.kqed.org/quest/television/embed/%s" % arg
		htmlSource = urlhandler.urlread(url)
		
		# Fetch the Video Url And Return It
		try: return {"url":re.findall("source=(http\S+?)&", htmlSource)[0]}
		except: raise plugin.videoResolver(33077, "Was unable to Find kqed.org Video Url")
	
	def checker(self, testcard=u"502"):
		plugin.log("Checking kqed Decoder", 0)
		try: 
			videoUrl = self.decode(testcard)
			plugin.log("#########################################", 0)
			plugin.log(u"PASS: Successfully Decoded %s" % testcard, 0)
			plugin.log( videoUrl)
			return videoUrl
		except:
			plugin.log("#######################################", 0)
			plugin.log(u"FAILED: Unable to Devode %s" % testcard, 0)

#######################################################################################

class stagevu_com(object):
	'''
	WARNING: Very Slow to Start Video Source
	Takes a video id from a StageView video page url, or takes a complete url 
	to a StageView swf and returns the url to the actual video resource.
	Raises videoResolver Error if no match is found.
	
	>>> stagevu_com.decode('http://stagevu.com/embed?width=720&height=405&background=000&uid=srpfmbeqxlwe')
	'http://n47.stagevu.com/v/e848f783c2a9046f44cb93e32ae5d878/43289.avi'
	
	>>> stagevu_com.decode('srpfmbeqxlwe')
	'http://n47.stagevu.com/v/e848f783c2a9046f44cb93e32ae5d878/43289.avi'
	'''
	__metaclass__ = Plugin
	def __init__(self, priority=20):
		self.priority = priority
	
	def strip(self, scheme, netloc, path, query, fragment, returnID=False):
		videoID = parse_qs(query)[u"uid"][0]
		if returnID: return videoID
		else: return {"domain":netloc, "vodepid":videoID, "function":self.decode, "isplaylist":False, "priority":self.priority}
	
	@check_arg(u"StageView")
	def decode(self, arg):
		# Create Url String and Fetch HTML Page
		url = u"http://stagevu.com/embed?uid=%s" % arg
		htmlSource = urlhandler.urlread(url)
		
		# Search for Video Url and Return
		try: return {"url":re.findall("url\[\d+]\ = '(http://\S+?)';", htmlSource)[0]}
		except: raise plugin.videoResolver(33077, "Was unable to Find StageView Video Url")
	
	def checker(self, testcard=u"srpfmbeqxlwe"):
		plugin.log("Checking StageView Decoder", 0)
		try: 
			videoUrl = self.decode(testcard)
			plugin.log("#########################################", 0)
			plugin.log(u"PASS: Successfully Decoded %s" % testcard, 0)
			plugin.log( videoUrl)
			return videoUrl
		except:
			plugin.log("#######################################", 0)
			plugin.log(u"FAILED: Unable to Devode %s" % testcard, 0)

#######################################################################################

class rutube_ru(object):
	'''
	Warning: Video Stream Failes when a 3rd of the way into the Video
	Takes a video id from a rutube.ru video page url, or takes a complete url 
	to a rutube.ru swf and returns the url to the actual video resource.
	Raises videoResolver Error if no match is found.
	
	>>> rutube_ru.decode('http://video.rutube.ru/65110c1ab97f073835033d2b4a9c3bd2')
	'http://bl.rutube.ru/65110c1ab97f073835033d2b4a9c3bd2.m3u8'
	
	>>> rutube_ru.decode('65110c1ab97f073835033d2b4a9c3bd2')
	'http://bl.rutube.ru/65110c1ab97f073835033d2b4a9c3bd2.m3u8'
	'''
	#__metaclass__ = Plugin
	def __init__(self, priority=-1):
		self.priority = priority
	
	def strip(self, scheme, netloc, path, query, fragment, returnID=False):
		videoID = path[path.rfind(u"/")+1:]
		if returnID: return videoID
		else: return {"domain":netloc, "vodepid":videoID, "function":self.decode, "isplaylist":False, "priority":self.priority}
	
	@check_arg(u"rutube.ru")
	def decode(self, arg):
		# Fetch Video Information
		url = u"http://rutube.ru/api/play/options/%s/?format=json" % arg
		sourceObj = urlhandler.urlopen(url)
		
		# Load Json Object
		from fastjson import load
		jsonObject = load(sourceObj)
		sourceObj.close()
		
		# Return Video Url
		return {"url":jsonObject[u"video_balancer"][u"m3u8"]}
	
	def checker(self, testcard=u"65110c1ab97f073835033d2b4a9c3bd2"):
		plugin.log("Checking RuTube.ru Decoder", 0)
		try: 
			videoUrl = self.decode(testcard)
			plugin.log("#########################################", 0)
			plugin.log(u"PASS: Successfully Decoded %s" % testcard, 0)
			plugin.log( videoUrl)
			return videoUrl
		except:
			plugin.log("#######################################", 0)
			plugin.log(u"FAILED: Unable to Devode %s" % testcard, 0)

#######################################################################################

'''
	Dummy Class to Stop Shutdown Sources from Been Identified as UnSupported,
	Google Video has been Shut Down and is no longer available.
	Megavideo has been Shut Down and is no longer available.
	Myspace has Totally Changed and is no longer serving videos
'''

class google_com(object):
	__metaclass__ = Plugin
	def strip(self, *args, **kwargs):
		plugin.log("google.com: Google Video has been Shut Down and is no longer available.")
		return None

class megavideo_com(object):
	__metaclass__ = Plugin
	def strip(self, *args, **kwargs):
		plugin.log("megavideo.com: Megavideo has been Shut Down and is no longer available.")
		return None

class myspace_com(object):
	__metaclass__ = Plugin
	def strip(self, *args, **kwargs):
		plugin.log("myspace.com: Myspace has Totally Changed and is no longer serving videos.")
		return None
