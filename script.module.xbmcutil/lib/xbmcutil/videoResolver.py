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
		if u"src" in attrs:# and attrs[u"src"][:4] == u"http":
			self.sourceUrls.add(attrs[u"src"])
	
	def handle_param(self, attrs):
		if u"name" in attrs and u"value" in attrs and attrs[u"name"] == u"movie":# and attrs[u"value"][:4] == u"http":
			self.sourceUrls.add(attrs[u"value"])
	
	def handle_embed(self, attrs):
		if u"src" in attrs:# and attrs[u"src"][:4] == u"http":
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
		if u"src" in attrs:# and attrs[u"src"][:4] == u"http":
			self.sourceUrls.add(attrs[u"src"])
	
	def handle_param(self, attrs):
		if u"name" in attrs and u"value" in attrs and attrs[u"name"] == u"movie":# and attrs[u"value"][:4] == u"http":
			self.sourceUrls.add(attrs[u"value"])
	
	def handle_embed(self, attrs):
		if u"src" in attrs:# and attrs[u"src"][:4] == u"http":
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
	
	def parse(self, arg, maxAge=57600):
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
		sourceUrls = list(self.htmlparser(htmlSource))
		if not sourceUrls: raise plugin.ParserError(plugin.getstr(32827), "No Video Sources ware found")
		else: self.setUrls(sourceUrls)
	
	def setUrls(self, sourceUrls):
		# Process Available Sources
		plugin.debug("Source url's: " + str(sourceUrls))
		self.parsedUrls = self.processUrls(sourceUrls)
	
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
		except: plugin.debug("HTML Parser Failed: Falling Back to Regex")
		
		try:
			# Try Parse HTML Using Regex
			customParser = RegexParser()
			customParser.parse(htmlSource)
			return customParser.sourceUrls
		except: plugin.debug("Regex Parser Failed: Falling Beautiful Soup")
		
		try:
			# Try Parse HTML Using Beautiful Soup
			customParser = SoupParser()
			customParser.parse(htmlSource)
			return customParser.sourceUrls
		except: plugin.debug("Beautiful Soup Parser Failed: All Out Total Failure")
		
		# Raise ParserError when all three parsers have failded
		raise plugin.ParserError(plugin.getstr(32826), "HTML Parsing Failed")
	
	def processUrls(self, sourceUrls):
		'''
		Take in a list of Embeded Source Urls and Create a list Containing
		information about the Sources found and the required Decoder.
		''' 
		blockList = ("platform.twitter.com", "google.com", "megavideo.com", "myspace.com")
		
		# Filter Video Sources
		parsedUrls = []
		self.sourceUrls = []
		appendUrl = self.sourceUrls.append
		for url in sourceUrls:
			urlParts = urlparse.urlsplit(url)
			if urlParts[1] in blockList:
				plugin.debug("Ignoring domain %s" % urlParts[1])
				continue
			else:
				appendUrl(url)
				filtered = self.process(urlParts)
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
		plugin.debug(u"Video Source UnSupported\nDomain = %s\nurl    = %s" % (urlObject[1], urlObject.geturl()))
	
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
			if not arg: raise plugin.videoResolver(plugin.getstr(32821), u"Unable to Strip out videoID ==> %s ==> %s" % (pluginName, oarg))
			else:
				# Call Function and return response
				plugin.debug("VideoResolver, Select Source ==> %s ==> %s" % (pluginName, arg))
				return function(self, arg)
		return wrapper
	return decorator

#######################################################################################

class youtube_com(object):
	'''
	Takes a full youtube url or video ID and returns the url to the actual
	video resource. Raises video Resolver Error if no resource is found.
	
	>>> youtube_com.decode('http://www.youtube.com/v/c64Aia4XE1Y')
	'http://o-o.preferred.dub06s01.v22.lscache8.c.youtube.com/videoplayback?sparams=id%2Cexpi...'
	
	>>> youtube_com.decode('c64Aia4XE1Y')
	'http://o-o.preferred.dub06s01.v22.lscache8.c.youtube.com/videoplayback?sparams=id%2Cexpi...'
	'''
	__metaclass__ = Plugin
	def __init__(self, priority=100):
		import videohostsAPI
		self.api = videohostsAPI
		self.priority = priority
	
	def strip(self, scheme, netloc, path, query, fragment, returnID=False):
		if path.lower().startswith(u"/embed/videoseries"):
			playlistID = plugin.parse_qs(query)["list"]
			if returnID: return playlistID
			else: return {"domain":netloc, "vodepid":playlistID, "function":self.decode_playlist, "priority":self.priority-1}
		elif path.lower().startswith("/playlist"):
			playlistID = plugin.parse_qs(query)["list"]
			if returnID: return playlistID
			else: return {"domain":netloc, "vodepid":playlistID, "function":self.decode_playlist, "priority":self.priority-1}
		elif path.lower().startswith(u"/embed/") and "list" in query:
			playlistID = plugin.parse_qs(query)["list"]
			if returnID: return playlistID
			else: return {"domain":netloc, "vodepid":playlistID, "function":self.decode_playlist, "priority":self.priority-1}
		elif path.lower().startswith(u"/embed/") or path.lower().startswith(u"/v/"):
			videoID = path[path.rfind(u"/")+1:].split("&")[0]
			if returnID: return videoID
			else: return {"domain":netloc, "vodepid":videoID, "function":self.decode, "priority":self.priority}
		elif path.lower().startswith(u"/watch"):
			videoID = plugin.parse_qs(query)["v"]
			if returnID: return videoID
			else: return {"domain":netloc, "vodepid":videoID, "function":self.decode, "priority":self.priority}
		else: 
			plugin.notice("Unable to Strip out video id from youtube.com source url")
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

class youtu_be(youtube_com): pass

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
		if "video/" in path.lower():
			videoID = path[path.rfind(u"/")+1:].split(u"_",1)[0]
			if returnID: return videoID
			else: return {"domain":netloc, "vodepid":videoID, "function":self.decode, "priority":self.priority}
		else:
			plugin.notice("Unable to Strip out video id from dailymotion.com source url")
			return None
	
	@check_arg(u"DailyMotion")
	def decode(self, arg):
		# Fetch Redirected Url
		url = u"http://www.dailymotion.com/embed/video/%s" % arg
		handle = urlhandler.HttpHandler()
		handle.add_response_handler()
		with handle.open(url) as resp:
			sourceCode = resp.read().decode("utf-8")
		
		# Fetch list of Urls
		sourceCode = re.findall('var info = (\{.+?\}),', sourceCode)[0]
		Sources = dict([[part for part in match if part] for match in re.findall('"(stream_h264_url)":"(\S+?)",|"(stream_h264_ld_url)":"(\S+?)",|"(stream_h264_hq_url)":"(\S+?)",|"(stream_h264_hd_url)":"(\S+?)",|"(stream_h264_hd1080_url)":"(\S+?)",', sourceCode)])
		if not Sources: raise plugin.videoResolver(plugin.getstr(33077), "Unable to Find Video Url")
		
		# Fetch Video Quality
		Quality = plugin.getSetting("quality")
		if  Quality == u"1080p": Quality = 5
		elif Quality == u"720p": Quality = 4
		else: Quality = 3
		
		# Return Available Format
		for res in (u"stream_h264_hd1080_url", u"stream_h264_hd_url", u"stream_h264_hq_url", u"stream_h264_ld_url", u"stream_h264_url")[-(Quality):]:
			if res in Sources: return {"url":Sources[res].replace(u"\\/", u"/")}
			else: continue
		
		# Fallback to any quality if unable to find format
		return {"url":Sources[Sources.keys()[0]]}

#######################################################################################

class blip_tv(object):
	'''
	Takes a video id from a BlipTV video page url, or takes a complete url 
	to a BlipTV swf and returns the url to the actual video resource.
	Raises videoResolver Error if no match is found.
	
	>>> blip_tv.decode('http://blip.tv/play/AYKvk2QC.html')
	'http://blip.tv/file/get/8bitredcat-....m4v'
	
	>>> blip_tv.decode('AYKvk2QC'|'4966784')
	'http://blip.tv/file/get/8bitredcat-....m4v'
	'''
	__metaclass__ = Plugin
	def __init__(self, priority=95):
		self.priority = priority
	
	def strip(self, scheme, netloc, path, query, fragment, returnID=False):
		if "api.swf" in path.lower(): videoID = fragment
		elif "play/" in path.lower(): videoID = path[path.rfind(u"/")+1:].split(u".")[0]
		elif str.isdigit(path.rsplit("-", 1)[-1]): videoID = path.rsplit("-", 1)[-1]
		else: 
			plugin.notice("Unable to Strip out video id from blip.tv source url")
			return None
		
		# Return Ether Video id or dict of objects
		if returnID: return videoID
		else: return {"domain":netloc, "vodepid":videoID, "function":self.decode, "priority":self.priority}
	
	@check_arg(u"BlipTV")
	def decode(self, arg):
		# Check if arg is the embeded ID or VideoID
		if arg.isdigit(): url = "http://blip.tv/rss/flash/%s" % arg
		else:
			# Fetch Redirected Url with the numeric id
			url = u"http://blip.tv/play/%s" % arg
			reUrl = urlhandler.redirect(url)
			
			# Filter out VideoCode
			try: url = plugin.parse_qs(reUrl[reUrl.find("?")+1:])["file"]
			except (ValueError, KeyError) as e: raise plugin.videoResolver(plugin.getstr(33077), str(e))
		
		# Fetch XMLSource
		handle = urlhandler.HttpHandler()
		handle.add_response_handler()
		sourceObj = handle.open(url)
		import xml.etree.ElementTree as ElementTree
		media = u"http://search.yahoo.com/mrss/"
		tree = ElementTree.parse(sourceObj)
		sourceObj.close()
		
		# Fetch list of Media Content Found
		filtered = ((int(node.get(u"height",0)), node.attrib) for node in tree.getiterator(u"{%s}content" % media) if not node.get(u"type") == u"text/plain")
		filtered = sorted(filtered, key=lambda x: x[0], reverse=True)
		filtered = sorted(filtered, key=lambda x: x[1]["isDefault"] == "true", reverse=True)
		
		# Fetch Video Quality and return video
		try: quality = int(plugin.getSetting("quality").replace(u"p",u""))
		except ValueError: quality = 720
		
		for res, content in filtered:
			if res <= quality:
				return {"url":content[u"url"], "type":content[u"type"]}
		
		# Fallback to hightest available quality
		videoInfo = filtered[0][1]
		return {"url":videoInfo[u"url"], "type":videoInfo[u"type"]}

#######################################################################################

class veehd_com(object):
	'''
	Takes a video id from a veehd video page url, or takes a complete url 
	to a veehd swf and returns the url to the actual video resource.
	Raises videoResolver Error if no match is found.
	
	>>> veehd_com.decode('http://veehd.com/embed?v=4686958&w=720&h=405&t=1&s=0&p=flash')
	'http://v33.veehd.com/dl/92c8e1b53f19f27697e16d186c28f17b/1327678479/5000.4686958.mp4&b=390'
	
	>>> veehd_com.decode('4686958')
	'http://v33.veehd.com/dl/92c8e1b53f19f27697e16d186c28f17b/1327678479/5000.4686958.mp4&b=390'
	'''
	__metaclass__ = Plugin
	def __init__(self, priority=94):
		self.priority = priority
	
	def strip(self, scheme, netloc, path, query, fragment, returnID=False):
		if path.lower().startswith(u"/embed"): videoID = plugin.parse_qs(query)[u"v"]
		elif path.lower().startswith(u"/video/"): videoID = path.strip(u"/video/").split(u"_")[0]
		else: 
			plugin.notice("Unable to Strip out video id from veehd.com source url")
			return None
		
		# Return Ether Video id or dict of objects
		if returnID: return videoID
		else: return {"domain":netloc, "vodepid":videoID, "function":self.decode, "priority":self.priority}
	
	@check_arg(u"Veehd")
	def decode(self, arg):
		# Create Url String and Download HTML Page
		url = u"http://veehd.com/video/%s" % arg
		handle = urlhandler.HttpHandler()
		handle.add_response_handler()
		with handle.open(url) as resp:
			htmlSource = resp.read().decode("utf-8")
		
		# Fetch Video Info Page Url and Download HTML Page
		try: url = [u"http://veehd.com%s" % url for url in re.findall('attr\(\{src\s:\s"(/vpi\S+?)"\}\)',htmlSource) if u"do=d" in url][0]
		except IndexError as e: raise plugin.videoResolver(plugin.getstr(33077), str(e))
		else:
			with handle.open(url) as resp:
				htmlSource = resp.read().decode("utf-8")
		
		# Search for Video Url
		try: return {"url":re.findall('<a\sstyle="color\:#31A0FF;"\shref="(http://.+?)">', htmlSource)[0]}
		except IndexError as e: raise plugin.videoResolver(plugin.getstr(33077), "Was unable to Find Veehd Video Url or Decode It")

#######################################################################################

class vimeo_com(object):
	'''
	Takes a video id from a vimeo video page url, or takes a complete url 
	to a vimeo swf and returns the url to the actual video resource.
	Raises videoResolver Error if no match is found.
	
	>>> vimeo_com.decode('http://player.vimeo.com/video/6368439')
	'http://av.vimeo.com/30750/741/12016117.mp4?token2=1403188386_b1960dae0fb3a6eafedc717134285fbe&aksessionid=5281d14cce9e052f&ns=4'
	
	>>> vimeo_com.decode('6368439')
	'http://av.vimeo.com/30750/741/12016117.mp4?token2=1403188386_b1960dae0fb3a6eafedc717134285fbe&aksessionid=5281d14cce9e052f&ns=4'
	'''
	__metaclass__ = Plugin
	def __init__(self, priority=94):
		self.priority = priority
	
	def strip(self, scheme, netloc, path, query, fragment, returnID=False):
		""" 
			http://www.vimeo.com/moogaloop.swf?clip_id=45517759
			http://player.vimeo.com/video/6368439
			http://vimeo.com/6368439 
		"""
		if "/video/" in path.lower(): videoID = path[path.rfind("/")+1:]
		elif "/moogaloop.swf" in path: videoID = plugin.parse_qs(query)[u"clip_id"]
		elif path[1:].isdigit(): videoID = path[1:]
		else: 
			plugin.notice("Unable to Strip out video id from veehd.com source url")
			return None
		
		# Return Ether Video id or dict of objects
		if returnID: return videoID
		else: return {"domain":netloc, "vodepid":videoID, "function":self.decode, "priority":self.priority}
	
	@check_arg(u"Veehd")
	def decode(self, arg):
		# Create Url String and Download HTML Page
		url = u"http://player.vimeo.com/video/%s" % arg
		handle = urlhandler.HttpHandler()
		handle.add_response_handler()
		with handle.open(url) as resp:
			htmlSource = resp.read()
		
		# Fetch Video Info Page Url and Download HTML Page
		try: jsonData = re.findall('"h264":({.+?}),"hls"', htmlSource)[0]
		except IndexError as e: raise plugin.videoResolver(plugin.getstr(33077), str(e))
		
		# Convert String to json Object
		import fastjson as json
		try: urlData = sorted([(value["height"], value["url"]) for value in json.loads(jsonData).values()], key=lambda x: x[0], reverse=True)
		except (ValueError, KeyError) as e: raise plugin.videoResolver(plugin.getstr(33077), str(e))
		
		# Fetch Video Quality and return video
		try: quality = int(plugin.getSetting("quality").replace(u"p",u""))
		except ValueError: quality = 720
		
		for res, url in urlData:
			if res <= quality:
				return {"url":url}