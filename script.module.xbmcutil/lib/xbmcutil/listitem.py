"""
	###################### xbmcutil.listitem ######################
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

# Import Python System Modules
import os
import time
import functools

# Import Custom Modules
from xbmcutil import plugin, cleanup

class ListItem(plugin.xbmcgui.ListItem):
	"""
		A wrapper for the xbmcgui.ListItem class. The class keeps track
		of any set properties
	"""
	_plugin = plugin
	_strptime = time.strptime
	_strftime = time.strftime
	_handleZero = _plugin.handleZero
	_selfObject = _plugin.xbmcgui.ListItem
	_urlencode = _plugin.urlencode
	_addonName = _plugin.getAddonInfo("name")
	_fanartImage = _plugin.translatePath(_plugin.getAddonInfo("fanart"))
	_imageGlobal = os.path.join(_plugin.getGlobalPath(), "resources", "media", "%s")
	_imageLocal = os.path.join(_plugin.getLocalPath(), "resources", "media", "%s")
	_strRelated = _plugin.getuni(32904) # 32904 = Related Videos
	_folderMenu = [("$LOCALIZE[1045]", "XBMC.RunPlugin(%s?action=system.opensettings)" % _handleZero), # 1045 = Add-on Settings
				   ("$LOCALIZE[184]", "XBMC.Container.Update(%srefresh=true)" % _plugin.handleThree)] # 184 = Refresh
	_videoMenu =  [("$LOCALIZE[20159]", "XBMC.Action(Info)"), # 20159 = Video Information
				   ("$LOCALIZE[13347]", "XBMC.Action(Queue)"), # 13347 = Queue Item
				   ("$LOCALIZE[13350]", "XBMC.ActivateWindow(videoplaylist)"), # 13350 = Now Playing...
				   ("$LOCALIZE[184]", "XBMC.Container.Update(%srefresh=true)" % _plugin.handleThree)] # 184 = Refresh
	
	def __init__(self):
		""" Initialize XBMC ListItem Object """
		
		# Initiate Overriding, in obj Classs Method
		self._selfObject.__init__(self)
		
		# Set class wide variables
		self.infoLabels = {"studio":self._addonName}
		self.urlParams = {}
		self.streamInfo = {}
		self.contextMenu = []
		
		# Pre Define Vars
		self.icon = None
		self.fanartImg = None
	
	def setLabel(self, label):
		""" Sets the listitem's label """
		self.infoLabels["title"] = label
		self._selfObject.setLabel(self, label)
	
	def getLabel(self):
		""" Returns the listitem label as a unicode string"""
		return self._selfObject.getLabel(self).decode("utf8")
	
	def setIconImage(self, icon):
		""" Sets ListItem's Icon Image """
		self.icon = icon
	
	def setFanartImage(self, fanart):
		""" Sets ListItem's Fanart Image """
		self.fanartImg = fanart
	
	def setThumbnailImage(self, image, local=0):
		""" Sets ListItem's Thumbnail Image
			
			image: string - Path to thumbnail image, (local or remote)
			local: integer - (0/1/2) - Changes image path to point to (Remote/Local/Global)
		"""
		if   local is 0: self._selfObject.setThumbnailImage(self, image)
		elif local is 1: self._selfObject.setThumbnailImage(self, self._imageLocal % image)
		elif local is 2: self._selfObject.setThumbnailImage(self, self._imageGlobal % image)
	
	def setInfoDict(self, key=None, value=None, **kwargs):
		""" Sets infolabels key and value """
		if key and value: self.infoLabels[key] = value
		if kwargs: self.infoLabels.update(kwargs)
	
	def setParamDict(self, key=None, value=None, **kwargs):
		""" Sets urlParam key and value """
		if key and value: self.urlParams[key] = value
		if kwargs: self.urlParams.update(kwargs)
	
	def setStreamDict(self, key=None, value=None, **kwargs):
		""" Sets SteamInfo key and value """
		if key and value: self.streamInfo[key] = value
		if kwargs: self.streamInfo.update(kwargs)
	
	def setDateInfo(self, date, dateFormat):
		""" Sets Date Info Label
			
			date: string - Date of list item
			dateFormat: string - Format of date string for strptime conversion
		"""
		convertedDate = self._strptime(date, dateFormat)
		self.infoLabels["date"] = self._strftime("%d.%m.%Y", convertedDate)
		self.infoLabels["aired"] = self._strftime("%Y-%m-%d", convertedDate)
		self.infoLabels["year"] = self._strftime("%Y", convertedDate)
		self.infoLabels["dateadded"] = self._strftime("%Y-%m-%d %H-%M-%S", convertedDate)
	
	def setDurationInfo(self, duration):
		""" Sets Date duration Label """
		if isinstance(duration, basestring):
			if u":" in duration:
				# Split Time By Marker and Convert to Integer
				timeParts = duration.split(":")
				timeParts.reverse()
				duration = 0
				counter = 1
				
				# Multiply Each Time Delta Segment by it's Seconds Equivalent
				for part in timeParts: 
					duration += int(part) * counter
					counter *= 60
			else:
				# Convert to Interger
				duration = int(duration)
		
		# Set Duration
		self.streamInfo["duration"] = duration
	
	def setAudioInfo(self, codec="aac", language="en", channels=2):
		""" Set Default Audio Info """
		self.addStreamInfo("audio", {"codec":codec, "language":language, "channels":channels})
	
	def setQualityIcon(self, HD=False):
		""" Enable Listitem's HD|SD Overlay Iron """
		self.streamInfo["codec"] = "h264"
		if HD is True:
			self.streamInfo["width"] = 1280
			self.streamInfo["height"] = 720
			self.streamInfo["aspect"] = 1.78
		elif HD is False:
			self.streamInfo["width"] = 768
			self.streamInfo["height"] = 576
	
	def setResumePoint(self, startPoint, totalTime=None):
		""" Set Resume Pont for xbmc to start playing video """
		self.setProperty("totaltime", totalTime or str(self.streamInfo.get("duration","1")))
		self.setProperty("resumetime", startPoint)
	
	def addRelatedContext(self, **params):
		""" Adds a context menu item to link to related videos """
		if not "action" in params: params["action"] = "Related"
		command = "XBMC.Container.Update(%s?%s)" % (self._handleZero, self._urlencode(params))
		self.contextMenu.append((self._strRelated, command))
	
	def addContextMenuItem(self, label, command, **params):
		""" Adds context menu item to XBMC
			
			label: string or unicode - Name of contect item
			command: string or unicode - XBMC build in function
			params: dict - Command options
		"""
		if params: command += "(%s?%s)" % (self._handleZero, self._urlencode(params))
		self.contextMenu.append((label, command))
	
	def setIdentifier(self, identifier):
		""" Sets Unique Identifier for Watched Flags """
		self.urlParams["identifier"] = identifier
	
	def getListitemTuple(self, isPlayable=False):
		""" Returns a tuple of listitem properties, (path, listitem, isFolder) """
		infoLabels = self.infoLabels
		urlParams = self.urlParams
		
		# Set XBMC InfoLabels and StreamInfo
		self.setInfo("video", infoLabels)
		if self.streamInfo: self.addStreamInfo("video", self.streamInfo)
		
		# Set Listitem Fanart Image
		if self.fanartImg: self.setProperty("fanart_image", self.fanartImg)
		else: self.setProperty("fanart_image", self._fanartImage)
		
		if isPlayable is True:
			# Change XBMC Propertys to mark as Playable
			self.setProperty("isplayable","true")
			self.setProperty("video","true")
			
			# Add title to urlParams for the Download title
			urlParams["title"] = infoLabels["title"].encode("ascii","ignore")
			
			# If not a live video then add Download option in context menu
			path = "%s?%s" % (self._handleZero, self._urlencode(urlParams))
			if not "live" in urlParams: self.contextMenu.append(("$LOCALIZE[33003]", "XBMC.RunPlugin(%s&download=true)" % path))
			
			# Set XBMC icon image
			if self.icon: self._selfObject.setIconImage(self, self.icon)
			else: self._selfObject.setIconImage(self, "DefaultVideo.png")
			
			# Add context menu items
			self.addContextMenuItems(self.contextMenu + self._videoMenu, replaceItems=False)
			
			# Return Tuple of url, listitem, isFolder
			return (path, self, False)
		
		else:
			# Change XBMC Propertys to mark as Folder
			self.setProperty("isplayable","false")
			self.setProperty("video","true")
			
			# Set XBMC icon image
			if self.icon: self._selfObject.setIconImage(self, self.icon)
			else: self._selfObject.setIconImage(self, "DefaultFolder.png")
			
			# Add context menu items
			self.addContextMenuItems(self.contextMenu + self._folderMenu, replaceItems=True)
			
			# Return Tuple of url, listitem, isFolder
			return ("%s?%s" % (self._handleZero, self._urlencode(urlParams)), self, True)
	
	@classmethod
	def add_item(cls, label=None, icon=None, thumbnail=None, url={}, info={}, isPlayable=False):
		""" A Listitem constructor for creating a XBMC listitem object
			
			label: string - Title of listitem
			icon: string - Image for listitem icon
			thumbnail: list/tuple - (image/0) Thumbnail Image for listitem / Image location identifier
			url: dict - Dictionary containing url params to control addon
			info: dict - Dictionary containing information about video 
			isPlayable: boolean - (True/False) - Lets XBMC know if listitem is a playable source - Default=False
		"""
		listitem = cls()
		if label: listitem.setLabel(label)
		if icon: listitem.icon = icon
		if thumbnail: listitem.setThumbnailImage(*thumbnail)
		if url: listitem.urlParams.update(url)
		if info: listitem.infoLabels.update(info)
		return listitem.getListitemTuple(isPlayable)
	
	@classmethod
	def add_next_page(cls, url={}):
		""" A Listitem constructor for Next Page Item
			
			url: dict - Dictionary containing url params to control addon
		"""
		nextCount = int(cls._plugin.get("nextpagecount",1)) + 1
		if not "action" in url and "action" in cls._plugin: url["action"] = cls._plugin["action"]
		url["nextpagecount"] = nextCount
		url["updatelisting"] = "true"
		label = u"%s %i" % (cls._plugin.getuni(33078), nextCount) # 33078 = Next Page
		listitem = cls()
		listitem.setLabel(label)
		listitem.setThumbnailImage(u"next.png", 2)
		listitem.urlParams.update(url)
		return listitem.getListitemTuple(False)
	
	@classmethod
	def add_search(cls, forwarding, url, label=None):
		""" A Listitem constructor to add Saved Search Support to addon
			
			forwarding: string - Addon Action to farward on to
			url: string - Base url to combine with search term
			label: string - Lable of Listitem
		"""
		listitem = cls()
		if label: listitem.setLabel(label)
		else: listitem.setLabel(u"-%s" % cls._plugin.getuni(137)) # 137 = Search
		listitem.setThumbnailImage(u"search.png", 2)
		listitem.urlParams.update({"action":"system.search", "forwarding":forwarding, "url":url})
		return listitem.getListitemTuple(False)
	
	@classmethod
	def add_youtube_channel(cls, channelID, label=None, hasPlaylist=False, hasHD=None):
		""" A Listitem constructor to add a youtube channel to addon
			
			channelID: string - Youtube channel ID to add
			label: string - Title of listitem - default (-Youtube Channel)
			hasPlaylist: boolean - True/False if channel ID contains any playlists - default (False) - (soon to be obsolete)
		"""
		listitem = cls()
		if label: listitem.setLabel(label)
		else: listitem.setLabel(u"-" + cls._plugin.getuni(32901)) # 32901 = Youtube Channel
		listitem.setThumbnailImage(u"youtube.png", 2)
		listitem.urlParams.update({"action":"system.videohosts.YTChannelUploads", "url":channelID, "hasplaylists":str(hasPlaylist).lower(), "hashd":str(hasHD).lower()})
		return listitem.getListitemTuple(False)
	
	@classmethod
	def add_youtube_playlist(cls, playlistID, label=None, hasHD=None):
		""" A Listitem constructor to add a youtube playlist to addon 
			
			playlistID: string - Youtube playlist ID to add
			label: string - Title of listitem - default (-Youtube Playlist)
		"""
		listitem = cls()
		if label: listitem.setLabel(label)
		else: listitem.setLabel(u"-" + cls._plugin.getuni(32902)) # 32902 = Youtube Playlist
		listitem.icon = "DefaultVideoPlaylists.png"
		listitem.setThumbnailImage(u"youtubeplaylist.png", 2)
		listitem.urlParams.update({"action":"system.videohosts.YTPlaylistVideos", "url":playlistID, "hashd":str(hasHD).lower()})
		return listitem.getListitemTuple(False)
	
	@classmethod
	def add_youtube_playlists(cls, channelID, label=None, hasHD=None):
		""" A Listitem constructor to add a youtube playlist to addon 
			
			channelID: string - Youtube channel ID to list playlists from
			label: string - Title of listitem - default (-Youtube Playlist)
		"""
		listitem = cls()
		if label: listitem.setLabel(label)
		else: listitem.setLabel(u"-" + cls._plugin.getuni(32903)) # 32903 = Youtube Playlists
		listitem.icon = "DefaultVideoPlaylists.png"
		listitem.setThumbnailImage(u"youtubeplaylist.png", 2)
		listitem.urlParams.update({"action":"system.videohosts.YTChannelPlaylists", "url":channelID, "hashd":str(hasHD).lower()})
		return listitem.getListitemTuple(False)

class VirtualFS(object):
	""" Wrapper for XBMC Virtual Directory Listings """
	_plugin = plugin
	viewID = None
	cacheToDisc = False
	updateListing = False
	_listitem = ListItem
	_handleOne = _plugin.handleOne
	def __init__(self):
		""" Initialize Virtual File System Object """
		for sortMethod, value in self._plugin.xbmcplugin.__dict__.iteritems():
			if sortMethod.startswith("SORT_METHOD"):
				setattr(self, sortMethod.lower(), value)
		
		# Set UpdateListing Flag for Content Refresh
		if "refresh" in self._plugin:
			self.updateListing = True
			self.cacheToDisc = True
		if "updatelisting" in self._plugin:
			self.updateListing = True
		if "cachetodisc" in self._plugin:
			self.cacheToDisc = True
		
		# Start Scraper Script
		self.extraItems = []
		self.add_item = self.item_add(self._listitem.add_item)
		self.add_next_page = self.item_add(self._listitem.add_next_page)
		self.add_search = self.item_add(self._listitem.add_search)
		self.add_youtube_channel = self.item_add(self._listitem.add_youtube_channel)
		self.add_youtube_playlist = self.item_add(self._listitem.add_youtube_playlist)
		self.add_youtube_playlists = self.item_add(self._listitem.add_youtube_playlists)
		
		# Add Listitems to xbmc
		listitems = self.scraper()
		extraItems = self.extraItems
		if isinstance(listitems, list): extraItems.extend(listitems)
		if extraItems: self.add_dir_items(extraItems)
		
		# Finalize the script
		self.finalize(bool(listitems), self.updateListing, self.cacheToDisc)
		self.cleanup()
	
	def item_add(self, function):
		# Wrap Listitem classmethods to redirect the output to add_dir_item
		@functools.wraps(function)
		def wrapped(*args, **kwargs): self.extraItems.append(function(*args, **kwargs))
		return wrapped
	
	def add_dir_item(self, listitem):
		""" Add Directory List Item to XBMC """
		self.extraItems.append(listitem)
	
	def add_dir_items(self, listitems):
		""" Add Directory List Items to XBMC """
		self._plugin.xbmcplugin.addDirectoryItems(self._handleOne, listitems, len(listitems))
	
	def set_sort_methods(self, *sortMethods):
		""" Set XBMC Sort Methods """
		for sortMethod in sortMethods:
			self._plugin.xbmcplugin.addSortMethod(self._handleOne, sortMethod)
	
	def set_content(self, content="files"):
		""" Sets the plugins content """
		self._plugin.xbmcplugin.setContent(self._handleOne, content)
		if not self.viewID: self.viewID = self._plugin.getSelectedViewID(content)
	
	def finalize(self, succeeded=True, updateListing=False, cacheToDisc=False):
		""" Make the end of directory listings """
		if succeeded and self.viewID: self._plugin.executebuiltin("Container.SetViewMode(%d)" % self.viewID)
		self._plugin.xbmcplugin.setPluginFanart(self._handleOne, self._listitem._fanartImage)
		self._plugin.xbmcplugin.endOfDirectory(self._handleOne, succeeded, updateListing, cacheToDisc)
	
	def scraper_speed_check(self):
		try:
			start = time.time()
			return self.scraper()
		finally:
			self._plugin.info("Elapsed Time: %s" % (time.time() - start))
	
	def cleanup(self):
		currentTime = time.time()
		try: lastTime = float(plugin.getSetting("lastcleanup")) + 2419200
		except ValueError: lastTime = 0
		if lastTime < currentTime:
			plugin.debug("Initiating Cache Cleanup")
			import urlhandler
			try: urlhandler.CachedResponse.cleanup(604800)
			except: plugin.error("Cache Cleanup Failed")
			else: plugin.setSetting("lastcleanup", str(currentTime))

class PlayMedia(object):
	""" Class to handle the resolving and playing of video url """
	_plugin = plugin
	_quotePlus = _plugin.urllib.quote_plus
	def __init__(self):
		# Fetch Common Vars
		downloadRequested = self._plugin.get("download") == u"true"
		vaildFilename = self.validate_filename(self._plugin["title"])
		downloadPath = self._plugin.getSetting("downloadpath")
		
		# Check if Video has already been downlaoded
		if downloadRequested is False: downloads = self.check_downloads(downloadPath, vaildFilename)
		else: downloads = None
		
		# Select witch Video Resolver to use
		if downloads: self._plugin["url"] = downloads
		elif self.video_resolver() is not True: return None
		self.process_video(downloadRequested, downloadPath, vaildFilename)
		
		# Call Finalize Method if Exists
		if hasattr(self, "finalize"): self.finalize()
	
	def validate_filename(self, title):
		""" Creates a valid filename for downloader """
		import unicodedata, re
		title = unicodedata.normalize("NFKD", title)
		title = re.sub("[^\w\s-]", "", title).strip()
		return re.sub("[-\s]+", "-", title)
	
	def check_downloads(self, downloadPath, filename):
		""" Check if video has already been downloaded """
		if downloadPath and self._plugin.xbmcvfs.exists(downloadPath):
			files = []
			appendfiles = files.append
			filenameLength = len(filename)
			pathStr = os.path.join(downloadPath, u"%s")
			for file in self._plugin.xbmcvfs.listdir(downloadPath)[1]:
				file = file.decode("utf8")
				if file[:filenameLength] == filename:
					appendfiles(pathStr % file)
			
			return files
	
	def video_resolver(self):
		# Fetch Subaction to deside on action
		try: subaction = self._plugin.actions[1]
		except:
			# Resolve Video Url using Plugin Resolver
			resolvedData = self.resolve()
			if resolvedData and isinstance(resolvedData, dict):
				self._plugin.update(resolvedData)
				return True
			elif resolvedData:
				self._plugin["url"] = resolvedData
				return True
		else:
			# Resolve Video Url using Video Hosts sources
			if subaction == u"direct":
				return True
			elif subaction == u"source":
				resolvedData = self._plugin.error_handler(self.sources)()
				if resolvedData and isinstance(resolvedData, dict):
					self._plugin.update(resolvedData)
					return True
				elif resolvedData:
					self._plugin["url"] = resolvedData
					return True
	
	def sources(self, url=None, urls=None, sourcetype=None):
		# Import Video Resolver
		import videoResolver
		if url is None: url = self._plugin["url"]
		
		# Call Specified Source Decoder if Set
		sourcetype = self._plugin.get("sourcetype", sourcetype)
		if sourcetype and hasattr(videoResolver, sourcetype.lower()):
			# Fetch Specified Class
			classObject = getattr(videoResolver, sourcetype.lower())()
			return classObject.decode(url)
		elif sourcetype:
			# Use urlresolver to fetch video url 
			import urlresolver
			return {"url": urlresolver.HostedMediaFile(url, sourcetype.replace(u"_",u".").lower()).resolve()}
		else:
			# Parse WebPage and Find Video Sources
			sources = videoResolver.VideoParser()
			if urls: sources.setUrls(urls)
			else: sources.parse(url)
			
			# Loop Available Sources and Play
			for sourceInfo in sources.get(sort=True):
				# Decode Video ID and Return Video Url
				try: return sourceInfo["function"](sourceInfo["vodepid"])
				except self._plugin.videoResolver: pass
				except self._plugin.URLError: pass
			
			# Failed to find a playable video using my own parser, Not trying urlResolver
			try: import urlresolver
			except ImportError: pass
			else:
				for url in sources.sourceUrls:
					urlObj = urlresolver.HostedMediaFile(url)
					if urlObj:
						mediaUrl = urlObj.resolve()
						if mediaUrl: return {"url":mediaUrl}
			
			# Unable to Resolve Video Source
			raise self._plugin.videoResolver(self._plugin.getstr(33077), "Was unable to Find Video Url for: %s" % repr(sources.get()))
	
	def process_video(self, downloadRequested, downloadPath, vaildFilename):
		# Fetch Video Url / List and Create Listitem
		listitemObj = self._plugin.xbmcgui.ListItem
		videoTitle = self._plugin["title"].encode("utf8")
		vaildFilename = vaildFilename.encode("utf8")
		videoUrl = self._plugin["url"]
		
		# Add Each url to a Playlist
		isIterable = hasattr(videoUrl, "__iter__")
		if isIterable and len(videoUrl) > 1:
			prepList = []
			prepappend = prepList.append
			videoTitle = videoTitle + " Part %i"
			cleanTitle = vaildFilename + "-Part-%i"
			for count, url in enumerate(videoUrl, 1):
				# Check type of url
				listitem = None
				if isinstance(url, dict):
					if "item" in url: listitem = url["item"]
					url = url["url"]
				
				# Check if download is Requested
				if isinstance(url, unicode): url = url.encode("ascii")
				if downloadRequested: prepappend((url, cleanTitle % count, videoTitle % count))
				else:
					if listitem is None:
						listitem = listitemObj()
						listitem.setLabel(videoTitle % count)
					
					# Add Content Type and urlpath to listitem
					if "type" in self._plugin: listitem.setMimeType(self._plugin["type"])
					url = self.add_header_pips(url, self._plugin.get("useragent"), self._plugin.get("referer"))
					listitem.setPath(url)
					prepappend((url, listitem, False))
			
			if downloadRequested:
				downloader = DownloadMGR(downloadPath)
				downloader.add_batch_job(prepList)
			else:
				# Create Playlist and add items
				playlist = self._plugin.xbmc.PlayList(1)
				playlist.clear()
				for url, listitem, isfolder in prepList:
					if isfolder is False: playlist.add(url, listitem)
				
				# Resolve to first element of playlist
				self.set_resolved_url(prepList[0][1])
		
		# Add Single Video to XBMC
		else:
			# Check if video is url is contained within a list
			if isIterable: videoUrl = videoUrl[0]
			if isinstance(videoUrl, unicode): videoUrl = videoUrl.encode("ascii")
			
			# Check if Download is Requested
			if downloadRequested:
				downloader = DownloadMGR(downloadPath)
				downloader.add_job(videoUrl, vaildFilename, videoTitle)
			else:
				# Add Content Type and Header Pips if any
				if "item" in self._plugin: listitem = self._plugin["item"]
				else: listitem = listitemObj()
				
				if "type" in self._plugin: listitem.setMimeType(self._plugin["type"])
				listitem.setPath(self.add_header_pips(videoUrl, self._plugin.get("useragent"), self._plugin.get("referer")))
				self.set_resolved_url(listitem)
	
	def add_header_pips(self, url, useragent, referer):
		if useragent or referer:
			# Convert Unicode to UTF-8 if needed
			if isinstance(useragent, unicode): useragent = useragent.encode("ascii")
			if isinstance(referer, unicode): referer = referer.encode("ascii")
			
			# Create Pip list
			pipe = []
			
			# Create Pip headers to combine with url
			if useragent: pipe.append("User-Agent=%s" % self._quotePlus(useragent))
			if referer: pipe.append("Referer=%s" % self._quotePlus(referer))
			
			# Combine header Pips to create new url and return that
			return url + "|%s" % "&".join(pipe)
		else:
			# Just return url untochted
			return url
	
	def set_resolved_url(self, listitem):
		""" Send the Resolved Url to XBMC """
		self._plugin.xbmcplugin.setResolvedUrl(self._plugin.handleOne, True, listitem)

class DownloadMGR(object):
	_plugin = plugin
	def __init__(self, downloadPath):
		# Create instance variables
		self.downloader = __import__("SimpleDownloader").SimpleDownloader()
		self.mimeguess = __import__("mimetypes").guess_extension
		self.params = {}
		
		# Create Default Download Params
		if "useragent" in self._plugin and isinstance(self._plugin["useragent"], unicode): self.params["useragent"] = self._plugin["useragent"].encode("ascii")
		elif "useragent" in self._plugin: self.params["useragent"] = self._plugin["useragent"]
		if "duration" in self._plugin: self.params["duration"] = int(self._plugin["duration"])
		if "live" in self._plugin: self.params["live"] = self._plugin["live"] == u"true"
		
		# Check for Download Path
		if not downloadPath: downloadPath = self.get_download_path()
		if downloadPath and not self._plugin.xbmcvfs.exists(downloadPath): self._plugin.xbmcvfs.mkdirs(downloadPath)
		if isinstance(downloadPath, unicode): downloadPath = downloadPath.encode("utf8")
		self.params["download_path"] = downloadPath
	
	def get_download_path(self):
		""" Asks for Download Path """
		downloadPath = self._plugin.browseSingle(3, self._plugin.getuni(33010), u"video", u"", False, False, "") # 33010 = Set Download Directory
		if downloadPath: self._plugin.setSetting("downloadpath", downloadPath)
		return downloadPath
	
	def guess_extension(self, url):
		# Guess File Extension
		urlExt = os.path.splitext(url)[1]
		if not urlExt and "type" in self._plugin: urlExt = self.mimeguess(self._plugin["type"], False)
		if not urlExt: urlExt = ".mp4"
		return urlExt
	
	def add_job(self, url, filename, title=None):
		# Check if url is a Plugin instead of a video Url
		if url.startswith("plugin:"): return self._plugin.executebuiltin("XBMC.RunPlugin(%s)" % url)
		elif not self.params["download_path"]: return None
		else:
			# Guess Full Filename
			filename = filename + self.guess_extension(url)
			if title: self.params["Title"] = title
			self.params["url"] = url
			
			# Start Downloader
			self.downloader.download(filename, self.params)
	
	def add_batch_job(self, batchList):
		# Loop each item it list and create download job
		if not self.params["download_path"]: return None
		else:
			for url, filename, title in batchList:
				self.add_job(url, filename, title)
				self._plugin.xbmc.sleep(1000)
