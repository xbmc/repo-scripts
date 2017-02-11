"""
	###################### xbmcutil.listitem ######################
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

# Import Python System Modules
import os
import time
import xbmcplugin

# Import Custom Modules
from xbmcutil import plugin

class ListItem(plugin.xbmcgui.ListItem):
	"""
		A wrapper for the xbmcgui.ListItem class. The class keeps track
		of any set properties
	"""
	_sortMethods = set((xbmcplugin.SORT_METHOD_TITLE_IGNORE_THE,))
	_sortAdd = _sortMethods.add
	_plugin = plugin
	_strptime = time.strptime
	_strftime = time.strftime
	_handleZero = _plugin.handleZero
	_selfObject = _plugin.xbmcgui.ListItem
	_urlencode = _plugin.urlencode
	_fanartImage = _plugin.getFanart()
	_addonName = _plugin.getAddonInfo("name")
	_imageGlobal = os.path.join(_plugin.getGlobalPath(), u"resources", u"media", u"%s")
	_imageLocal = os.path.join(_plugin.getLocalPath(), u"resources", u"media", u"%s")
	_strRelated = _plugin.getuni(32904) # 32904 = Related Videos
	_folderMenu = [("$LOCALIZE[1045]", "XBMC.RunPlugin(%s?action=system.opensettings)" % _handleZero), # 1045 = Add-on Settings
				   ("$LOCALIZE[184]", "XBMC.Container.Update(%srefresh=true)" % _plugin.handleThree)] # 184 = Refresh
	_videoMenu =  [("$LOCALIZE[20159]", "XBMC.Action(Info)"), # 20159 = Video Information
				   ("$LOCALIZE[13347]", "XBMC.Action(Queue)"), # 13347 = Queue Item
				   ("$LOCALIZE[13350]", "XBMC.ActivateWindow(videoplaylist)"), # 13350 = Now Playing...
				   ("$LOCALIZE[184]", "XBMC.Container.Update(%srefresh=true)" % _plugin.handleThree)] # 184 = Refresh
	
	@classmethod
	def setSortMethod(cls, sortMethod):
		""" Set SortMethod """
		cls._sortAdd(sortMethod)
	
	def __init__(self):
		""" Initialize XBMC ListItem Object """
		
		# Initiate Overriding, in obj Classs Method
		self._selfObject.__init__(self)
		
		# Set class wide variables
		self.infoLabels = {"studio":self._addonName}
		self.urlParams = {}
		self.streamInfo = {}
		self.imagePaths = {"fanart":self._fanartImage}
		self.contextMenu = []
	
	def setLabel(self, label, bold=False):
		""" Sets the listitem's label """
		if bold: label = "[B]%s[/B]" % label
		self.infoLabels["title"] = label
		self._selfObject.setLabel(self, label)
	
	def getLabel(self):
		""" Returns the listitem label as a unicode string """
		return self._selfObject.getLabel(self).decode("utf8")
	
	def setPlot(self, value):
		""" Set plot info : string or unicode """
		self.infoLabels["plot"] = value
	
	def setSize(self, value):
		""" Set size info : string digit or long integer """
		self.infoLabels["size"] = long(value)
		self._sortAdd(xbmcplugin.SORT_METHOD_SIZE)
	
	def setGenre(self, value):
		""" Set genre info : string or unicode """
		self.infoLabels["genre"] = value
		self._sortAdd(xbmcplugin.SORT_METHOD_GENRE)
	
	def setStudio(self, value):
		""" Set studio info : string or unicode """
		self.infoLabels["studio"] = value
		self._sortAdd(xbmcplugin.SORT_METHOD_STUDIO_IGNORE_THE)
	
	def setCount(self, value):
		""" Set count info : string digit or integer """
		self.infoLabels["count"] = int(value)
		self._sortAdd(xbmcplugin.SORT_METHOD_PROGRAM_COUNT)
	
	def setRating(self, value):
		""" Set rating info : string Float or Float """
		self.infoLabels["rating"] = float(value)
		self._sortAdd(xbmcplugin.SORT_METHOD_VIDEO_RATING)
	
	def setEpisode(self, value):
		""" Set episode info : string digit or integer """
		self.infoLabels["episode"] = int(value)
		self._sortAdd(xbmcplugin.SORT_METHOD_EPISODE)
	
	def setDate(self, date, dateFormat):
		""" Sets Date Info Label
			
			date: string - Date of list item
			dateFormat: string - Format of date string for strptime conversion
		"""
		convertedDate = self._strptime(date, dateFormat)
		self.infoLabels["date"] = self._strftime("%d.%m.%Y", convertedDate)
		self.infoLabels["aired"] = self._strftime("%Y-%m-%d", convertedDate)
		self.infoLabels["year"] = self._strftime("%Y", convertedDate)
		self.infoLabels["dateadded"] = self._strftime("%Y-%m-%d %H-%M-%S", convertedDate)
		self._sortAdd(xbmcplugin.SORT_METHOD_DATE)

	def setDuration(self, duration):
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
		self._sortAdd(xbmcplugin.SORT_METHOD_VIDEO_RUNTIME)
	
	def setIcon(self, image):
		""" Set icon : string or unicode - image filename """
		self.imagePaths["icon"] = image
	
	def setFanart(self, image):
		""" Set fanart : string or unicode - image filename """
		self.imagePaths["fanart"] = image
	
	def setPoster(self, image):
		""" Set poster : string or unicode - image filename """
		self.imagePaths["poster"] = image
	
	def setBanner(self, image):
		""" Set banner : string or unicode - image filename """
		self.imagePaths["banner"] = image
	
	def setClearArt(self, image):
		""" Set clearart : string or unicode - image filename """
		self.imagePaths["clearart"] = image
	
	def setClearLogo(self, image):
		""" Set clearlogo : string or unicode - image filename """
		self.imagePaths["clearlogo"] = image
	
	def setLandscape(self, image):
		""" Set landscape : string or unicode - image filename """
		self.imagePaths["landscape"] = image
	
	def setThumb(self, image, local=0):
		""" Set thumbnail : string or unicode - image filename
			
			image: string or unicode - Path to thumbnail image, (local or remote)
			local: integer - (0/1/2) - Changes image path to point to (Remote/Local/Global)
		"""
		if   local is 0: self.imagePaths["thumb"] = image
		elif local is 1: self.imagePaths["thumb"] = self._imageLocal % image
		elif local is 2: self.imagePaths["thumb"] = self._imageGlobal % image
	
	def setInfoDict(self, key=None, value=None, **kwargs):
		""" Sets infolabels key and value """
		if key and value: self.infoLabels[key] = value
		elif kwargs: self.infoLabels.update(kwargs)
	
	def setParamDict(self, key=None, value=None, **kwargs):
		""" Sets urlParam key and value """
		if key and value: self.urlParams[key] = value
		elif kwargs: self.urlParams.update(kwargs)
	
	def setIdentifier(self, identifier):
		""" Sets Unique Identifier for Watched Flags """
		self.urlParams["identifier"] = identifier
	
	def setResumePoint(self, startPoint, totalTime=None):
		""" Set Resume Point for Kodi to start playing video """
		self.setProperty("totaltime", totalTime or str(self.streamInfo.get("duration","1")))
		self.setProperty("resumetime", startPoint)
	
	def setAudioFlags(self, codec="aac", language="en", channels=2):
		""" Set Default Audio Info """
		self.addStreamInfo("audio", {"codec":codec, "language":language, "channels":channels})
	
	def setVideoFlags(self, isHD=None, codec="h264", aspect=None):
		""" Enable Listitem's HD, SD, Codec, aspect Overlay Icons """
		streamInfo = self.streamInfo
		if codec: streamInfo["codec"] = codec
		if aspect: streamInfo["aspect"] = aspect
		
		# Set HD/SD overlay icon
		if isHD is True:
			streamInfo["width"] = 1280
			streamInfo["height"] = 720
			streamInfo["aspect"] = 1.78
		elif isHD is False:
			streamInfo["width"] = 768
			streamInfo["height"] = 576
	
	def addRelatedContext(self, **params):
		""" Adds a context menu item to link to related videos """
		if not "action" in params: params["action"] = "Related"
		if not "updatelisting" in params: params["updatelisting"] = "true"
		command = "XBMC.Container.Update(%s?%s)" % (self._handleZero, self._urlencode(params))
		self.contextMenu.append((self._strRelated, command))
	
	def addContextMenuItem(self, label, command, **params):
		""" Adds context menu item to Kodi
			
			label: string or unicode - Name of contect item
			command: string or unicode - Kodi build in function
			params: dict - Command options
		"""
		if params: command += "(%s?%s)" % (self._handleZero, self._urlencode(params))
		self.contextMenu.append((label, command))
	
	def getListitemTuple(self, isPlayable=False):
		""" Returns a tuple of listitem properties, (path, listitem, isFolder) """
		infoLabels = self.infoLabels
		urlParams = self.urlParams
		
		# Set Kodi InfoLabels
		self.setInfo("video", infoLabels)
		
		if isPlayable is True:
			# Change Kodi Propertys to mark as Playable
			self.setProperty("isplayable","true")
			self.setProperty("video","true")
			
			# Set streamInfo if found
			if self.streamInfo: self.addStreamInfo("video", self.streamInfo)
			
			# Add title to urlParams for the Download title
			urlParams["title"] = infoLabels["title"].encode("ascii","ignore")
			
			# Create path to send to Kodi
			path = "%s?%s" % (self._handleZero, self._urlencode(urlParams))
			
			# Add context menu items
			self.addContextMenuItems(self.contextMenu + self._videoMenu, replaceItems=False)
			
			# Set Kodi icon image
			self.setIconImage(self.imagePaths.pop("icon", "DefaultVideo.png"))
			
			# Apply listitem images if any
			self.setArt(self.imagePaths)
			
			# Return Tuple of url, listitem, isFolder
			VirtualFS._vidCounter += 1
			return (path, self, False)
		
		else:
			# Change Kodi Propertys to mark as Folder
			self.setProperty("isplayable","false")
			self.setProperty("folder","true")
			
			# Add context menu items
			self.addContextMenuItems(self.contextMenu + self._folderMenu, replaceItems=True)
			
			# Set Kodi icon image
			self.setIconImage(self.imagePaths.pop("icon", "DefaultFolder.png"))
			
			# Apply listitem images if any
			self.setArt(self.imagePaths)
			
			# Return Tuple of url, listitem, isFolder
			return ("%s?%s" % (self._handleZero, self._urlencode(urlParams)), self, True)
	
	@classmethod
	def add_item(cls, label, icon=None, thumbnail=None, url={}, info={}, isPlayable=False):
		""" A Listitem constructor for creating a Kodi listitem object
			
			label: string - Title of listitem
			icon: string - Image for listitem icon
			thumbnail: list/tuple - (image/0) Thumbnail Image for listitem / Image location identifier
			url: dict - Dictionary containing url params to control addon
			info: dict - Dictionary containing information about video 
			isPlayable: boolean - (True/False) - Lets Kodi know if listitem is a playable source - Default=False
		"""
		listitem = cls()
		listitem.setLabel("[B]%s[/B]" % label)
		if icon: listitem.imagePaths["icon"] = icon
		if thumbnail: listitem.setThumb(*thumbnail)
		if url: listitem.urlParams.update(url)
		if info: listitem.infoLabels.update(info)
		VirtualFS._extraItems.append(listitem.getListitemTuple(isPlayable))
	
	@classmethod
	def add_next_page(cls, url={}):
		""" A Listitem constructor for Next Page Item
			
			url: dict - Dictionary containing url params to control addon
		"""
		nextCount = int(cls._plugin.get("nextpagecount",1)) + 1
		if not "action" in url and "action" in cls._plugin: url["action"] = cls._plugin["action"]
		url["nextpagecount"] = nextCount
		url["updatelisting"] = "true"
		label = u"[B]%s %i[/B]" % (cls._plugin.getuni(33078), nextCount) # 33078 = Next Page
		listitem = cls()
		listitem.setLabel(label)
		listitem.imagePaths["thumb"] = cls._imageGlobal % u"next.png"
		listitem.urlParams.update(url)
		VirtualFS._extraItems.append(listitem.getListitemTuple(False))
	
	@classmethod
	def add_search(cls, forwarding, url, label=None):
		""" A Listitem constructor to add Saved Search Support to addon
			
			forwarding: string - Addon Action to farward on to
			url: string - Base url to combine with search term
			label: string - Lable of Listitem
		"""
		listitem = cls()
		if label: listitem.setLabel(label, bold=True)
		else: listitem.setLabel(cls._plugin.getuni(137), bold=True) # 137 = Search
		listitem.imagePaths["thumb"] = cls._imageGlobal % u"search.png"
		listitem.urlParams.update({"action":"system.search", "forwarding":forwarding, "url":url})
		VirtualFS._extraItems.append(listitem.getListitemTuple(False))
	
	@classmethod
	def add_recent(cls, action="MostRecent", url=None, label=None):
		""" A Listitem constructor to add Recent Folder to addon
			
			action: string - Action to tell whitch class to exacute
			url: string - Url to pass to Most Recent Class
			label: string - Lable of Listitem
		"""
		listitem = cls()
		if label: listitem.setLabel(u"[B]%s[/B]" % label)
		else: listitem.setLabel(u"[B]%s[/B]" % cls._plugin.getuni(32941)) # 32941 = Most Recent
		if url: listitem.urlParams["url"] = url
		listitem.urlParams["action"] = action
		listitem.imagePaths["thumb"] = cls._imageGlobal % u"recent.png"
		VirtualFS._extraItems.append(listitem.getListitemTuple(False))
	
	@classmethod
	def add_youtube_videos(cls, playlistID=None, channelID=None, channelName=None, label=None, hasPlaylist=True):
		""" A Listitem constructor to add a youtube channel to addon
			
			channelID: string - Youtube channel ID to add
			label: string - Title of listitem - default (-Youtube Channel)
			hasPlaylist: boolean - True/False if channel ID contains any playlists - default (False) - (soon to be obsolete)
		"""
		listitem = cls()
		url = {"action":"system.videohosts.YTPlaylistVideos", "hasplaylists":str(hasPlaylist).lower()}
		if playlistID: url["playlistid"] = playlistID
		elif channelID: url["channelid"] = channelID
		elif channelName: url["channelname"] = channelName
		if label: listitem.setLabel(u"[B]%s[/B]" % label)
		else: listitem.setLabel(u"[B]%s[/B]" % cls._plugin.getuni(32901)) # 32901 = Youtube Channel
		listitem.imagePaths["thumb"] = cls._imageGlobal % u"youtube.png"
		listitem.urlParams.update(url)
		VirtualFS._extraItems.append(listitem.getListitemTuple(False))

class VirtualFS(object):
	""" Wrapper for Kodi Virtual Directory Listings """
	_plugin = plugin
	contentType = None
	cacheToDisc = False
	updateListing = False
	_handleOne = _plugin.handleOne
	_vidCounter = 0
	_extraItems = []
	_sortMethods = None
	
	# Set Reference methods
	add_item = ListItem.add_item
	add_search = ListItem.add_search
	add_recent = ListItem.add_recent
	add_next_page = ListItem.add_next_page
	add_youtube_videos = ListItem.add_youtube_videos
	
	def __del__(self):
		""" Fix memory leak by Manually deleting references """
		
		# Remove Reference to _extraItems to prevent memory leak
		del VirtualFS._extraItems
		
		# Remove stale cache object to save disk space
		currentTime = time.time()
		try: lastTime = float(plugin.getSetting("lastcleanup")) + 2419200
		except ValueError: lastTime = 0
		if lastTime < currentTime:
			plugin.debug("Initiating Cache Cleanup")
			import urlhandler
			try: urlhandler.CachedResponse.cleanup(604800)
			except: plugin.error("Cache Cleanup Failed")
			else: plugin.setSetting("lastcleanup", str(currentTime))
		
		# Call plugin destroyer to prevent Memory leak from xbmcaddon objects
		plugin.destroyer()
	
	def __init__(self):
		""" Initialize Virtual File System Object """
		for sortMethod, value in self._plugin.xbmcplugin.__dict__.iteritems():
			if sortMethod.startswith("SORT_METHOD"):
				setattr(self, sortMethod.lower(), value)
		
		# Set UpdateListing Flag for Content Refresh
		if "refresh" in self._plugin:
			self.updateListing = True
		elif "updatelisting" in self._plugin:
			self.updateListing = True
		elif "cachetodisc" in self._plugin:
			self.cacheToDisc = True
		
		# Add Listitems to Kodi
		listitems = self.scraper()
		extraItems = self._extraItems
		if hasattr(listitems, "__iter__"): extraItems.extend(listitems)
		if extraItems: self.add_dir_items(extraItems)
		
		# Finalize the script
		self.end_dir(bool(listitems), self.updateListing, self.cacheToDisc)
		
		# Call Finalize Method if Exists
		if hasattr(self, "finalize"): self.finalize()
	
	def add_dir_item(self, listitem):
		""" Add Directory List Item to Kodi """
		self._extraItems.append(listitem)
	
	def add_dir_items(self, listitems):
		""" Add Directory List Items to Kodi """
		self._plugin.xbmcplugin.addDirectoryItems(self._handleOne, listitems, len(listitems))
	
	def set_sort_methods(self, *sortMethods):
		""" Set Kodi Sort Methods """
		self._sortMethods = sortMethods
	
	def set_content(self, content):
		""" Sets the plugins content """
		self.contentType = content
	
	def end_dir(self, succeeded=True, updateListing=False, cacheToDisc=False):
		""" Make the end of directory listings """
		if succeeded:
			# Set Kodi Sort Methods
			handle = self._handleOne
			callingObj = self._plugin.xbmcplugin.addSortMethod
			sortMethods = self._sortMethods if self._sortMethods else sorted(ListItem._sortMethods)
			for sortMethod in sortMethods: callingObj(handle, sortMethod)
			self._plugin.debug(sortMethods)
			
			# Guess Content Type and set View Mode
			isFolder = self._vidCounter < (len(self._extraItems) / 2)
			self._plugin.setViewMode("folder" if isFolder else "video")
			
			# Fetch and Set Content Type
			if self.contentType: self._plugin.xbmcplugin.setContent(handle, self.contentType)
			else: self._plugin.xbmcplugin.setContent(handle, "files" if isFolder else "episodes")
		
		# End Directory Listings
		self._plugin.xbmcplugin.endOfDirectory(self._handleOne, succeeded, updateListing, cacheToDisc)

class PlayMedia(object):
	""" Class to handle the resolving and playing of video urls """
	_plugin = plugin
	
	def __del__(self):
		# Call plugin destroyer to prevent 
		# Memory leak from xbmcaddon objects
		plugin.destroyer()
	
	def __init__(self):
		# Resolve Video Url using Plugin Resolver
		resolved = self.resolve()
		if resolved is None or resolved is False: return None
		elif isinstance(resolved, basestring):
			self.simple_processor(resolved)
		elif isinstance(resolved, dict):
			self._plugin.update(resolved)
			self.complex_processor()
		elif isinstance(resolved, list):
			self.complex_processor(resolved)
		else:
			plugin.sendNotification(32854, "Invalid media response from resolver", icon="error")
		
		# Call Finalize Method if Exists
		if hasattr(self, "finalize"): self.finalize()
	
	def add_header_pips(self, url, useragent, referer):
		# Create Pipe list
		pipe = []
		
		# Add Useragent to pipe
		if useragent and isinstance(useragent, unicode): pipe.append("User-Agent=%s" % self._quotePlus(useragent.encode("ascii")))
		elif referer and isinstance(referer, unicode): pipe.append("Referer=%s" % self._quotePlus(referer.encode("ascii")))
		elif useragent: pipe.append("User-Agent=%s" % self._quotePlus(useragent))
		elif referer: pipe.append("Referer=%s" % self._quotePlus(useragent))
		
		# Combine header into Pips to create new url
		return "%s|%s" (url, "&".join(pipe))
	
	def set_resolved_url(self, listitem):
		""" Send the Resolved Url to Kodi """
		self._plugin.xbmcplugin.setResolvedUrl(self._plugin.handleOne, True, listitem)
	
	def simple_processor(self, url):
		# Fetch Video Url and create Listitem
		if isinstance(url, unicode): url = url.encode("ascii")
		
		# Add Url Headers if needed
		_plugin = self._plugin
		if "useragent" in _plugin or "referer" in _plugin:
			self._quotePlus = _plugin.urllib.quote_plus
			url = self.add_header_pips(url, _plugin.get("useragent"), _plugin.get("referer"))
		
		# Create Listitem Object for kodi
		if "item" in _plugin: listitem = _plugin["item"]
		else: listitem = _plugin.xbmcgui.ListItem()
		listitem.setPath(url)
		
		# If Mime Type is found then setMimeType in listitem
		if "type" in _plugin:listitem.setMimeType(_plugin["type"])
		
		# Send Resolved url Listitem to kodi
		self.set_resolved_url(listitem)
	
	def complex_processor(self, videoUrl=None):
		# Fetch Video Url/List
		_plugin = self._plugin
		listitemObj = _plugin.xbmcgui.ListItem
		
		# Fetch Video Url
		if videoUrl is None: videoUrl = plugin["url"]
		
		# Add Each url to a Playlist
		isIterable = hasattr(videoUrl, "__iter__")
		if isIterable and len(videoUrl) > 1:
			# Fetch title of listitem
			videoTitle = _plugin["title"].encode("utf8") + " Part %i"
			
			# Create Playlist
			playlist = _plugin.xbmc.PlayList(1)
			playlist.clear()
			
			# Check if Url Pipes need to be added
			addPipes = "useragent" in _plugin or "referer" in _plugin
			self._quotePlus = _plugin.urllib.quote_plus
			
			# Loop each item to create playlist
			for count, url in enumerate(videoUrl, 1):
				# If url is dict then work with that
				if isinstance(url, dict):
					if "item" in url: listitem = url["item"]
					else:
						# Create Listitem
						listitem = listitemObj()
						listitem.setLabel(videoTitle % count)
					
					# Fetch Url from dict
					url = url["url"]
				
				# Create Listitem
				elif isinstance(url, basestring):
					# Create Listitem
					listitem = listitemObj()
					listitem.setLabel(videoTitle % count)
				
				# Else just skip to next item
				else: continue
				
				# Add Content Type and Url Headers if needed
				if "type" in _plugin: listitem.setMimeType(_plugin["type"])
				if isinstance(url, unicode): url = url.encode("ascii")
				if addPipes: listitem.setPath(self.add_header_pips(url, _plugin.get("useragent"), _plugin.get("referer")))
				else: listitem.setPath(url)
				
				# Populate Playlis
				playlist.add(url, listitem)
			
			# Resolve to first element of playlist
			self.set_resolved_url(playlist[0])
		
		# Add Single Video to Kodi
		elif isIterable: self.simple_processor(videoUrl[0])
		else: self.simple_processor(videoUrl)

class PlayDirect(PlayMedia):
	def resolve(self):
		return plugin["url"]

class PlaySource(PlayMedia):
	def __init__(self):
		# import videoResolver and call pairent init
		import videoResolver
		self.videoResolver = videoResolver
		super(PlaySource, self).__init__()
	
	@plugin.error_handler
	def resolve(self):
		_plugin = self._plugin
		if len(_plugin.actions) >= 3: return self.sourceType(_plugin["url"], _plugin.actions[2].lower())
		elif "sourcetype" in _plugin: return self.sourceType(_plugin["url"], _plugin["sourcetype"].lower())
		else: return self.sourceParse(_plugin["url"])
	
	def sourceParse(self, url):
		# Parse WebPage and Find Video Sources
		sources = self.videoResolver.VideoParser()
		sources.parse(url)
		return self.sourcesResolve(sources)
	
	def sourceUrls(self, urls):
		# Parse WebPage and Find Video Sources
		sources = self.videoResolver.VideoParser()
		sources.setUrls(urls)
		return self.sourcesResolve(sources)
	
	def sourceType(self, url, type):
		# Resolve url using specified type
		if type == "urlchecker":
			return self.sourceUrls((url,))
		elif hasattr(self.videoResolver, type):
			# Fetch Specified Class
			classObject = getattr(self.videoResolver, type)()
			return classObject.decode(url)
		else:
			return self.urlResolver(url, type.replace(u"_",u"."))
	
	def sourcesResolve(self, sources):
		resolved = self.intResolver(sources.get_processed(sort=True))
		if resolved: return resolved
		else:
			# Atempt to use urlResolver if available
			resolved = self.urlResolver(sources.get_sources())
			if resolved: return resolved
			else:
				# Unable to Resolve Video Source
				raise self._plugin.videoResolver(self._plugin.getstr(33077), "Was unable to Find Video Url for: %s" % repr(sources))
	
	def intResolver(self, sources):
		# Loop Available Sources and Play
		for sourceInfo in sources:
			# Decode Video ID and Return Video Url
			try: return sourceInfo["function"](sourceInfo["vodepid"])
			except (self._plugin.videoResolver, self._plugin.URLError): pass
	
	def urlResolver(self, sources, host=""):
		# Atempt to use urlResolver if available
		try: import urlresolver
		except ImportError:
			plugin.debug("Optional Urlresolver Module not Found")
			return None
		else:
			# urlResolver Module found, Atempt to Resolve sources
			for url in sources:
				urlObj = urlresolver.HostedMediaFile(url, host)
				if urlObj:
					mediaUrl = urlObj.resolve()
					if mediaUrl: return mediaUrl

class SavedSearches(VirtualFS):
	@plugin.error_handler
	def scraper(self):
		# Fetch list of current saved searches
		import storageDB
		self.searches = storageDB.SavedSearch()
		
		# Call Search Dialog if Required
		if "remove" in plugin and plugin["remove"] in self.searches:
			self.searches.remove(plugin.pop("remove"))
			self.searches.sync()
		elif "search" in plugin:
			self.search_dialog(plugin["url"])
			del plugin["search"]
		elif not self.searches:
			self.search_dialog(plugin["url"])
		
		# Add Extra Items
		params = plugin._Params.copy()
		params["search"] = "true"
		params["updatelisting"] = "true"
		params["cachetodisc"] = "true"
		self.add_item(label=u"-%s" % plugin.getuni(137), url=params, isPlayable=False) # 137 = Search
		
		# Display list of searches if any
		try:
			if self.searches: return self.list_searches()
			else: return True
		finally:
			self.searches.close()
	
	def search_dialog(self, urlString):
		# Add searchTerm to database
		self.searches.add(plugin.dialogSearch())
		self.searches.sync()
	
	def list_searches(self):
		# Create Speed vars
		results = []
		additem = results.append
		localListitem = ListItem
		
		# Fetch Forwarding url string & action
		baseUrl = plugin["url"]
		baseAction = plugin["forwarding"]
		
		# Create Context Menu item Params
		strRemove = plugin.getuni(1210) # 1210 = Remove
		params = plugin._Params.copy()
		params["updatelisting"] = "true"
		
		# Loop earch Search item
		for searchTerm in self.searches:
			# Create listitem of Data
			item = localListitem()
			item.setLabel(searchTerm.title())
			item.setParamDict(action=baseAction, url=baseUrl % searchTerm)
			
			# Creatre Context Menu item to remove search item
			params["remove"] = searchTerm
			item.addContextMenuItem(strRemove, "XBMC.Container.Update", **params)
			
			# Store Listitem data
			additem(item.getListitemTuple(isPlayable=False))
		
		# Return list of listitems
		return results
