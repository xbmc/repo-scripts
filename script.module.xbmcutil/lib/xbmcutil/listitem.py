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
import urllib
import functools

# Import Custom Modules
from xbmcutil import plugin

class Playlist(plugin.xbmc.PlayList):
	""" Wrapper for XBMC Playlist """
	def __init__(self, playlistType):
		""" Retrieve a reference from a valid xbmc playlist
		
			0 : xbmc.PLAYLIST_MUSIC
			1 : xbmc.PLAYLIST_VIDEO
		"""
		
		# Initiate Overriding, in obj Classs Method
		super(Playlist, self).__init__()
		self.clear()
		
		# Create Dummy Item to fix XBMC Playlist Bug
		self.add("V V V V V V V V V V V V V")
	
	def add_iter(self, listitems):
		""" Accepts a iterable of (url, listitem, isfolder) """
		for url, listitem, isfolder in listitems:
			if isfolder is False: self.add(url, listitem)

class DialogProgress(plugin.xbmcgui.DialogProgress):
	def __init__(self, heading, line1, line2="", line3=""):
		# Initiate Overriding, in obj Classs Method
		self.subClass = super(DialogProgress, self)
		self.subClass.__init__()
		
		# Create Progress Dialog
		self.lines = [line1,line2,line3]
		self.create(heading, line1, line2, line3)
		self.update(0)
	
	def updateLine1(self, line):
		self.lines[0] = line
	
	def updateLine2(self, line):
		self.lines[1] = line
	
	def updateLine3(self, line):
		self.lines[2] = line
	
	def update(self, percent, line1=None, line2=None, line3=None):
		# Add updated line if available
		if line1 != None: self.lines[0] = line1
		if line2 != None: self.lines[1] = line2
		if line3 != None: self.lines[2] = line3
		
		# Initeate Overriding, in obj Classs Method
		self.subClass.update(int(percent), *self.lines)

class ListItem(plugin.xbmcgui.ListItem):
	"""
		A wrapper for the xbmcgui.ListItem class. The class keeps track
		of any set properties
	"""
	_plugin = plugin
	_strptime = time.strptime
	_strftime = time.strftime
	_handleZero = _plugin.handleZero
	_handelThree = _plugin.handleThree
	_selfObject = _plugin.xbmcgui.ListItem
	_urlencode = _plugin.urlencode
	_addonName = _plugin.getName()
	_fanartImage = _plugin.getFanartImage()
	_imageGlobal = _plugin.getImageLocation(local=False)
	_imageLocal = _plugin.getImageLocation(local=True)
	_stringDownload = _plugin.getstr(33003)
	_strRelated = _plugin.getstr(32966)
	_staticMenu = ([(_plugin.getstr(20159), "XBMC.Action(Info)"),
					(_plugin.getstr(1045), "XBMC.RunPlugin(%s?action=system.opensettings)" % _handleZero),
					(_plugin.getstr(13347), "XBMC.Action(Queue)"),
					(_plugin.getstr(32962), "XBMC.ActivateWindow(videoplaylist)"),
					(_plugin.getstr(22083), "XBMC.RunPlugin(%splayall=true)" % _handelThree),
					(_plugin.getstr(184), "XBMC.Container.Update(%srefresh=true)" % _handelThree)],
				   [(_plugin.getstr(1045), "XBMC.RunPlugin(%s?action=system.opensettings)" % _handleZero),
					(_plugin.getstr(184), "XBMC.Container.Update(%srefresh=true)" % _handelThree)])
	
	def __init__(self):
		""" Initialize XBMC ListItem Object """
		
		# Initiate Overriding, in obj Classs Method
		self._selfObject.__init__(self)
		
		# Set class wide variables
		self.infoLabels = {"studio":self._addonName}
		self.contextMenu = []
		self.urlParams = {}
		self.streamInfo = {}
		self.isFolder = True
		self.isIconSet = False
		self.isFanartSet = False
		self.isPlayableSet = False
	
	def setLabel(self, label):
		""" Sets the listitem's label
			
			label: string or unicode - text string
		"""
		self.urlParams["title"] = label.encode("ascii", "ignore")
		self.infoLabels["title"] = label
		self._selfObject.setLabel(self, label)
	
	def setIconImage(self, icon=None):
		""" Sets ListItem's Icon Image
			
			icon: string - (DefaultFolder.png/DefaultVideo.png/DefaultVideoPlaylists.png)
		"""
		if icon is None: icon = ("DefaultVideo.png","DefaultFolder.png")[self.isFolder]
		self._selfObject.setIconImage(self, icon)
		self.isIconSet = True
	
	def setThumbnailImage(self, image, local=0):
		""" Sets ListItem's Thumbnail Image
			
			image: string - Path to thumbnail image, (local or remote)
			local: integer - (0/1/2) - Changes image path to point to (Remote/Local/Global) Filesystem
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
	
	def getInfoItem(self, key, fbObject=None):
		""" Return specifiyed Key form infolabels """
		if key in self.infoLabels: return self.infoLabels[key]
		else: return fbObject
	
	def getParamItem(self, key, fbObject=None):
		""" Return specifiyed key from urlparams """
		if key in self.urlParams: return self.urlParams[key]
		else: return fbObject
	
	def getStreamItem(self, key, fbObject=None):
		""" Return specifiyed key from streamInfo """
		if key in self.streamInfo: return self.streamInfo[key]
		else: return fbObject
	
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
	
	def setResumePoint(self, startPoint, totalTime=None):
		""" Set Resume Pont for xbmc to start playing video """
		self.setProperty("TotalTime", totalTime or str(self.streamInfo.get("duration","1")))
		self.setProperty("ResumeTime", startPoint)
	
	def setDateInfo(self, date, dateFormat):
		""" Sets Date Info Label
			
			date: string - Date of list item
			dateFormat: string - Format of date string for strptime conversion
		"""
		convertedDate = self._strptime(date, dateFormat)
		self.infoLabels["date"] = self._strftime("%d.%m.%Y", convertedDate)
		self.infoLabels["aired"] = self._strftime("%Y-%m-%d", convertedDate)
		self.infoLabels["year"] = self._strftime("%Y", convertedDate)
	
	def setFanartImage(self, fanart=None):
		""" Sets ListItem's Fanart Image
			
			fanart: string - Path to fanart image, if not set defaults to fanart of addon
		"""
		if fanart is None: fanart = self._fanartImage
		self.setProperty("Fanart_Image", fanart)
		self.isFanartSet = True
	
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
	
	def setAudioInfo(self, codec="aac", language="en", channels=2):
		""" Set Default Audio Info """
		self.addStreamInfo("audio", {"codec":codec, "language":language, "channels":channels})
	
	def addRelatedContext(self, **params):
		""" Adds a context menu item to link to related videos """
		if not "action" in params: params["action"] = "Related"
		command = "XBMC.Container.Update(%s?%s)" % (self._handleZero, self._urlencode(params))
		self.contextMenu.append((self._strRelated, command))
	
	def addContextMenuItem(self, label, command, **params):
		""" Adds context menu item to XBMC
			
			label: string - Name of contect item
			command: string - XBMC build in function
			params: dict - Command options
		"""
		if params: command += "(%s?%s)" % (self._handleZero, self._urlencode(params))
		self.contextMenu.append((label, command))
	
	def setIsPlayable(self, isPlayable=False):
		""" Sets the listitem's playable flag """
		self.isPlayableSet = True
		self.isFolder = not isPlayable
		self.setProperty("IsPlayable", str(isPlayable).lower())
		self.setProperty(("Folder","Video")[isPlayable], "true")
	
	def setIdentifier(self, identifier):
		""" Sets Unique Identifier for Watched Flags """
		self.urlParams["identifier"] = identifier
	
	def getPath(self):
		""" Returns urlParams as a string """
		return self._handleZero + "?" + self._urlencode(self.urlParams)
	
	def finalize(function):
		""" Wrapper for get Listitem to finalize creation of listitem for XBMC
			
			isPlayable: boolean - (True/False) - Lets XBMC know if listitem is a playable source - Default=False
			infoType: string - (video/music/pictures) - Lets XBMC know the type of content been listed - Default="video"
		"""
		def wrapped(self, isPlayable=False, infoType="video"):
			# If markers are not set, set sections
			if not self.isPlayableSet: self.setIsPlayable(isPlayable)
			if not self.isFanartSet: self.setFanartImage()
			if not self.isIconSet: self.setIconImage()
			# Set info, steam into and path where available
			if self.infoLabels: self.setInfo(infoType, self.infoLabels)
			if self.streamInfo: self.addStreamInfo(infoType, self.streamInfo)
			self.path = self.getPath()
			# Add context menu items
			if not self.isFolder and not "live" in self.urlParams: self.addContextMenuItem(self._stringDownload, "XBMC.RunPlugin(%s&download=true)" % (self.path))
			self.addContextMenuItems(self.contextMenu + self._staticMenu[self.isFolder], replaceItems=True)
			# Call Decorated Function ad return it response
			return function(self)
		return wrapped
	
	@finalize
	def getListitemTuple(self):
		""" Returns a tuple of listitem properties, (path, _listitem, isFolder) """
		return self.path, self, self.isFolder
	
	@finalize
	def getListitem(self):
		""" Returns the wrapped xbmcgui.ListItem """
		return self
	
	@classmethod
	def add_item(cls, label=None, label2=None, icon=None, thumbnail=None, url={}, info={}, isPlayable=False, infoType="video"):
		""" A Listitem constructor for creating a XBMC listitem object
			
			label: string - Title of listitem
			label2: string - Secondary lable of listitem
			icon: string - Image for listitem icon
			thumbnail: list/tuple - (image/0) Thumbnail Image for listitem / Image location identifier
			url: dict - Dictionary containing url params to control addon
			info: dict - Dictionary containing information about video 
			isPlayable: boolean - (True/False) - Lets XBMC know if listitem is a playable source - Default=False
			infoType: string - (video/music/pictures) - Lets XBMC know the type of content been listed - Default="video"
		"""
		listitem = cls()
		if label: listitem.setLabel(label)
		if label2: listitem.setLabel2(label2)
		if icon: listitem.setIconImage(icon)
		if thumbnail: listitem.setThumbnailImage(*thumbnail)
		if url: listitem.urlParams.update(url)
		if info: listitem.infoLabels.update(info)
		return listitem.getListitemTuple(isPlayable, infoType)
	
	@classmethod
	def add_next_page(cls, url={}, infoType="video"):
		""" A Listitem constructor for Next Page Item
			
			url: dict - Dictionary containing url params to control addon
			infoType: string - (video/music/pictures) - Lets XBMC know the type of content been listed - Default="video"
		"""
		nextCount = int(cls._plugin.get("NextPageCount",1)) + 1
		if not "action" in url and "action" in cls._plugin: url["action"] = cls._plugin["action"]
		url["NextPageCount"] = nextCount
		url["updatelisting"] = "true"
		label = u"%s %i" % (cls._plugin.getuni(33078), nextCount)
		return cls.add_item(label, thumbnail=(u"next.png", 2), url=url, infoType=infoType)
	
	@classmethod
	def add_search(cls, forwarding, url, label=u"-Search"):
		""" A Listitem constructor to add Saved Search Support to addon
			
			forwarding: string - Addon Action to farward on to
			url: string - Base url to combine with search term
			label: string - Lable of Listitem
		"""
		return cls.add_item(label, thumbnail=(u"search.png", 2), url={"action":"system.search", "forwarding":forwarding, "url":url})
	
	@classmethod
	def add_youtube_channel(cls, channelID, label=None, hasPlaylist=False):
		""" A Listitem constructor to add a youtube channel to addon
			
			channelID: string - Youtube channel ID to add
			label: string - Title of listitem - default (-Youtube Channel)
			hasPlaylist: boolean - True/False if channel ID contains any playlists - default (False) - (soon to be obsolete)
		"""
		if label is None: label = u"-" + cls._plugin.getuni(32963)
		return cls.add_item(label, thumbnail=(u"youtube.png", 2), url={"action":"system.videohosts.YTChannelUploads", "url":channelID, "hasPlaylists":unicode(hasPlaylist).lower()})
	
	@classmethod
	def add_youtube_playlist(cls, playlistID, label=None):
		""" A Listitem constructor to add a youtube playlist to addon 
			
			playlistID: string - Youtube playlist ID to add
			label: string - Title of listitem - default (-Youtube Playlist)
		"""
		if label is None: label = u"-" + cls._plugin.getuni(32964)
		return cls.add_item(label, icon="DefaultVideoPlaylists.png", thumbnail=(u"youtubeplaylist.png", 2), url={"action":"system.videohosts.YTPlaylistVideos", "url":playlistID})
	
	@classmethod
	def add_youtube_playlists(cls, channelID, label=None):
		""" A Listitem constructor to add a youtube playlist to addon 
			
			channelID: string - Youtube channel ID to list playlists from
			label: string - Title of listitem - default (-Youtube Playlist)
		"""
		if label is None: label = u"-" + cls._plugin.getuni(32965)
		return cls.add_item(label, icon="DefaultVideoPlaylists.png", thumbnail=(u"youtubeplaylist.png", 2), url={"action":"system.videohosts.YTChannelPlaylists", "url":channelID})
	
	@classmethod
	def add_vimeo_user(cls, channelID, label=None):
		""" A Listitem constructor to add a youtube channel to addon
			
			channelID: string - Youtube channel ID to add
			label: string - Title of listitem - default (-Youtube Channel)
			hasPlaylist: boolean - True/False if channel ID contains any playlists - default (False) - (soon to be obsolete)
		"""
		if label is None: label = u"-" + cls._plugin.getuni(32967)
		return cls.add_item(label, thumbnail=(u"vimeo.png", 2), url={"action":"system.videohosts.VUserVideos", "url":channelID})

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
		self.add_item = self.item_add(self._listitem.add_item)
		self.add_next_page = self.item_add(self._listitem.add_next_page)
		self.add_search = self.item_add(self._listitem.add_search)
		self.add_youtube_channel = self.item_add(self._listitem.add_youtube_channel)
		self.add_youtube_playlist = self.item_add(self._listitem.add_youtube_playlist)
		self.add_youtube_playlists = self.item_add(self._listitem.add_youtube_playlists)
		self.add_vimeo_user = self.item_add(self._listitem.add_vimeo_user)
		
		# If a directory listings exists then add to XBMC and Finalize
		#start = time.time()
		listitems = self.scraper()
		#self._plugin.log("Elapsed Time: %s" % (time.time() - start))
		if listitems and listitems is not True: self.add_dir_items(listitems)
		self.finalize(bool(listitems), self.updateListing, self.cacheToDisc)
	
	def item_add(self, function):
		# Wrap Listitem classmethods to redirect the output to add_dir_item
		@functools.wraps(function)
		def wrapped(*args, **kwargs): self.add_dir_item(function(*args, **kwargs))
		return wrapped
	
	def add_dir_item(self, listitem):
		""" Add Directory List Item to XBMC """
		self._plugin.xbmcplugin.addDirectoryItem(self._handleOne, *listitem)
	
	def add_dir_items(self, listitems):
		""" Add Directory List Items to XBMC """
		if "playall" in self._plugin:
			# Create a Playlist of all Items
			playlist = Playlist(1)
			playlist.add_iter(listitems)
			self._plugin.xbmc.Player().play(playlist)
		
		# Else List all Items
		else: self._plugin.xbmcplugin.addDirectoryItems(self._handleOne, listitems, len(listitems))
	
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
		if succeeded and self.viewID: self._plugin.setviewMode(self.viewID)
		self._plugin.xbmcplugin.setPluginFanart(self._handleOne, self._listitem._fanartImage)
		self._plugin.xbmcplugin.endOfDirectory(self._handleOne, succeeded, updateListing, cacheToDisc)

class PlayMedia(object):
	""" Class to handle the resolving and playing of video url """
	_plugin = plugin
	_videoData = _plugin._Params
	_quotePlus = urllib.quote_plus
	def __init__(self):
		# Fetch Common Vars
		downloadRequested = self._videoData.get("download") == u"true"
		vaildFilename = self.validate_filename(self._videoData["title"])
		downloadPath = self._plugin.getSetting("downloadpath")
		
		# Check if Video has already been downlaoded
		if downloadRequested is False: downloads = self.check_downloads(downloadPath, vaildFilename)
		else: downloads = None
		
		# Select witch Video Resolver to use
		if downloads: self._videoData["url"] = downloads
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
			if resolvedData and "url" in resolvedData:
				self._videoData.update(resolvedData)
				return True
		else:
			# Resolve Video Url using Video Hosts sources
			if subaction == u"direct":
				return True
			elif subaction == u"source":
				resolvedData = self._plugin.error_handler(self.sources)()
				if resolvedData and "url" in resolvedData:
					self._videoData.update(resolvedData)
					return True
	
	def sources(self, url=None, urls=None):
		# Import Video Resolver
		import videoResolver
		if url is None: url = self._videoData["url"]
		
		# Call Specified Source Decoder if Set
		if "sourcetype" in self._videoData:
			# Fetch Specified Class
			classObject = getattr(videoResolver, self._videoData["sourcetype"].lower())()
			return classObject.decode(url)
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
			
			# Unable to Resolve Video Source
			raise self._plugin.videoResolver(33077, "Was unable to Find Video Url for: %s" % repr(sources.get()))
	
	def process_video(self, downloadRequested, downloadPath, vaildFilename):
		# Fetch Video Url / List and Create Listitem
		listitemObj = self._plugin.xbmcgui.ListItem
		videoTitle = self._videoData["title"].encode("utf8")
		vaildFilename = vaildFilename.encode("utf8")
		videoUrl = self._videoData["url"]
		
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
					prepappend((url, listitem))
			
			if downloadRequested:
				downloader = DownloadMGR(downloadPath)
				downloader.add_batch_job(prepList)
			else:
				playlist = Playlist(1)
				for url, listitem in prepList:
					# Add Content Type and listitem to Playlist
					if "type" in self._videoData: listitem.setMimeType(self._videoData["type"])
					playlist.add(self.add_header_pips(url, self._videoData.get("useragent"), self._videoData.get("referer")), listitem)
		
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
				if "item" in self._videoData: listitem = self._videoData["item"]
				else: listitem = listitemObj()
				
				if "type" in self._videoData: listitem.setMimeType(self._videoData["type"])
				listitem.setPath(self.add_header_pips(videoUrl, self._videoData.get("useragent"), self._videoData.get("referer")))
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
		downloadPath = self._plugin.browseSingle(3, self._plugin.getuni(32933), u"video", u"", False, False, "")
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
		if url.startswith("plugin:"): return self._plugin.executePlugin(url)
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
