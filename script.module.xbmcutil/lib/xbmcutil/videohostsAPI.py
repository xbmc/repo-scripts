"""
	###################### xbmcutil.videohostsAPI ######################
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
import listitem, urlhandler
from xbmcutil import plugin, storageDB
from fastjson import load
from base64 import b64decode

# Key
APIKEY = b64decode("Rh1UiBVOpd1RwYWR3RzMDlEbwdXclR3d1xGVjJlY0I1Q5NVY6lUQ"[::-1])

class YTPlaylistVideos(listitem.VirtualFS):
	@plugin.error_handler
	def scraper(self):
		_plugin = plugin
		# Initialize Youtube API
		Gdata = YoutubeAPI()
		
		# Fetch Playlist ID from parse args
		if "playlistid" in _plugin:
			# Fetch Playlist if from plugin args
			playlistID = _plugin["playlistid"]
			
			# Set sortMethods
			if playlistID.lower().startswith("pl"): self.set_sort_methods(17, 10, 15, 20, 3, 29, 31)
		
		# Fetch Playlist ID using Channel ID
		elif "channelid" in _plugin:
			channelID = _plugin.pop("channelid")
			playlistID = _plugin.getSetting(channelID)
			if not playlistID:
				playlistID = Gdata.Channels(id=channelID)[1]
				_plugin.setSetting(channelID, playlistID)
		
		# Fetch Playlist ID using Channel Name
		elif "channelname" in _plugin:
			channelName = _plugin.pop("channelname")
			channelID = _plugin.getSetting(channelName)
			if not channelID: 
				channelID, playlistID = Gdata.Channels(forUsername=channelName)
				_plugin.setSetting(channelName,channelID)
				_plugin.setSetting(channelID,playlistID)
			else:
				playlistID = _plugin.getSetting(channelID)
				if not playlistID:
					playlistID = Gdata.Channels(id=channelID)[1]
					_plugin.setSetting(channelID,playlistID)
		
		# Return List of Videos
		return Gdata.PlaylistItems(playlistID)

class YTChannelPlaylists(listitem.VirtualFS):
	@plugin.error_handler
	def scraper(self):
		# Initialize Gdata API and return playlist Listitems
		Gdata = YoutubeAPI()
		return Gdata.Playlists(plugin["url"], loop=True)

class YTRelatedVideos(listitem.VirtualFS):
	@plugin.error_handler
	def scraper(self):
		_plugin = plugin
		# Create 
		kargs = {"relatedToVideoId":_plugin["videoid"]}
		#if "channelid" in _plugin: kargs["channelId"] = _plugin["channelid"] # Not Working
		
		# Initialize Gdata API and return Video Listitems
		Gdata = YoutubeAPI()
		return Gdata.Search(kargs)

class YoutubeAPI:
	def Channels(self, **kargs):
		# Set Defautl parameters
		queries = self.set_default_queries(kargs)
		queries["fields"] = u"items(id,contentDetails/relatedPlaylists/uploads)"
		queries["part"] = u"contentDetails"
		
		# Fetch List of Entries
		url = "https://www.googleapis.com/youtube/v3/channels?%s" % plugin.urlencode(queries)
		with urlhandler.urlopen(url, -1) as sourceObj:
			feed = load(sourceObj)[u"items"][0]
			return (feed[u"id"], feed[u"contentDetails"][u"relatedPlaylists"][u"uploads"])
	
	def Search(self, kargs):
		# Set Defautl parameters
		queries = self.set_default_queries(kargs)
		queries["fields"] = u"nextPageToken,items/id/videoId"
		queries["type"] = u"video"
		queries["part"] = u"snippet"
		queries["safeSearch"] = u"none"
		
		# Add pageToken if needed
		if "pagetoken" in plugin: queries["pageToken"] = plugin["pagetoken"]
		
		# Return list of videos
		return self._videoItems(queries, self.Process_Search)
	
	def Process_Search(self, queries):
		# Fetch List of Entries
		url = "https://www.googleapis.com/youtube/v3/search?%s" % plugin.urlencode(queries)
		with urlhandler.urlopen(url, 14400) as sourceObj: feed = load(sourceObj)
		
		# Fetch list of video ID from feed
		return (video[u"id"][u"videoId"] for video in feed["items"])
	
	def PlaylistItems(self, playlistID, loop=False, **kargs):
		# Set Default parameters
		queries = self.set_default_queries(kargs)
		queries["fields"] = u"nextPageToken,items/contentDetails/videoId"
		queries["part"] = u"contentDetails"
		queries["playlistId"] = playlistID
		
		# Add pageToken if needed
		if "pagetoken" in plugin: queries["pageToken"] = plugin["pagetoken"]
		
		# Return list of videos
		return self._videoItems(queries, self.Process_PlaylistItems, loop)
	
	def Process_PlaylistItems(self, queries):
		# Fetch List of Entries
		url = "https://www.googleapis.com/youtube/v3/playlistItems?%s" % plugin.urlencode(queries)
		with urlhandler.urlopen(url, 14400) as sourceObj: feed = load(sourceObj)
		
		# Fetch next Page Token if exists
		if u"nextPageToken" in feed: queries["pageToken"] = feed[u"nextPageToken"]
		elif "pageToken" in queries: del queries["pageToken"]
		
		# Fetch list of video ID from feed
		return (video[u"contentDetails"][u"videoId"] for video in feed["items"])
	
	def Playlists(self, channelID, loop=False, **kargs):
		# Set Default parameters
		queries = self.set_default_queries(kargs)
		queries["fields"] = u"nextPageToken,items(id,contentDetails/itemCount,snippet(publishedAt,title,description,thumbnails/medium/url))"
		queries["part"] = u"snippet,contentDetails"
		queries["channelId"] = channelID
		
		# Add pageToken if needed
		if "pagetoken" in plugin: queries["pageToken"] = plugin["pagetoken"]
		localListItem = listitem.ListItem
		
		while True:
			# Fetch List of Entries
			url = "https://www.googleapis.com/youtube/v3/playlists?%s" % plugin.urlencode(queries)
			with urlhandler.urlopen(url, 14400) as sourceObj: feed = load(sourceObj)
			
			# Loop Entries
			for playlist in feed[u"items"]:
				# Create listitem object
				item = localListItem()
				item.setParamDict("action", "system.videohosts.YTPlaylistVideos")
				
				# Fetch Video ID
				item.setParamDict("playlistid", playlist[u"id"])
				
				# Fetch video snippet
				snippet = playlist[u"snippet"]
				
				# Fetch Title and Video Cound for combining Title
				item.setLabel(u"%s (%s)" % (snippet[u"title"], playlist[u"contentDetails"][u"itemCount"]))
				
				# Fetch Image Url
				item.setThumb(snippet[u"thumbnails"][u"medium"][u"url"])
				
				# Fetch Possible Plot and Check if Available
				item.setPlot(snippet[u"description"])
				
				# Fetch Possible Date and Check if Available
				date = snippet[u"publishedAt"]
				item.setDate(date[:date.find("T")], "%Y-%m-%d")
				
				# Add InfoLabels and Data to Processed List
				yield item.getListitemTuple(False)
			
			# Fetch next Page Token if available
			if u"nextPageToken" in feed:
				if loop is True:
					queries["pageToken"] = feed[u"nextPageToken"]
					continue
				else:
					self.display_next_page(feed[u"nextPageToken"])
					break
			else:
				break
	
	def _videoItems(self, queries, processObj, loop=False):
		# Setup Optimizations
		localListItem = listitem.ListItem
		reFind = __import__("re").findall
		_plugin = plugin
		localInt = int
		
		# Check if Displaying related Videos
		isRelated = u"YTRelatedVideos" in _plugin["action"]
		_youTubeStr = _plugin.getuni(19103)
		
		# Fetch Youtube Video Quality Setting
		try: isHD = not _plugin.getAddonSetting("plugin.video.youtube", "hd_videos") == "1"
		except: isHD = True
		
		# Fetch categorys ID Maps
		self.categorysMap = categorysMap = CategoryFile()
		self.videoData = videoData = VideoFile("%s.json" % queries["playlistId"] if "playlistId" in queries else "video-data.json")
		self.unmapedCats = []
		channelIDs = []
		
		# Set Default parameters for second request
		newQueries = self.set_default_queries({})
		newQueries["fields"] = u"items(id,snippet(publishedAt,channelId,title,description,thumbnails/medium/url,channelTitle,categoryId),contentDetails(duration,definition),statistics/viewCount)"
		newQueries["part"] = u"contentDetails,statistics,snippet"
		
		while True:
			# Fetch video Ids
			selectedVids = []
			selectedVidsAppend = selectedVids.append
			fetchVids = []
			fetchVidsAppend = fetchVids.append
			for videoId in processObj(queries):
				if videoId in videoData: selectedVidsAppend(videoData[videoId])
				else: fetchVidsAppend(videoId)
			
			if fetchVids:
				# Fetch video Information
				newQueries["id"] = u",".join(fetchVids)
				url = u"https://www.googleapis.com/youtube/v3/videos?%s" % _plugin.urlencode(newQueries)
				with urlhandler.urlopen(url, -1) as sourceObj:
					for video in load(sourceObj)[u"items"]:
						selectedVidsAppend(video)
						videoData[video[u"id"]] = video
				
				# Sync videoData to file
				videoData.sync()
			
			# Loop Entries
			for video in selectedVids:
				# Create listitem object
				item = localListItem()
				item.setParamDict("action", "system.source.youtube_com")
				
				# Fetch Video ID
				item.setParamDict("url", video[u"id"])
				
				# Fetch video snippet & contentDetails
				snippet = video[u"snippet"]
				contentDetails = video[u"contentDetails"]
				
				# Fetch Channel ID
				channelID = snippet[u"channelId"]
				if not channelID in channelIDs: channelIDs.append(channelID)
				
				# Fetch video Image url
				item.setThumb(snippet[u"thumbnails"][u"medium"][u"url"])
				
				# Fetch Title
				item.setLabel(snippet[u"title"])
				
				# Fetch Studio
				item.setStudio(snippet[u"channelTitle"])
				
				# Fetch Description
				item.setPlot(snippet[u"description"])
				
				# Fetch Possible Date
				date = snippet[u"publishedAt"]
				item.setDate(date[:date.find("T")], "%Y-%m-%d")
				
				# Fetch Viewcount
				item.setCount(video[u"statistics"][u"viewCount"])
				
				# Fetch Category
				category = snippet[u"categoryId"]
				if category in categorysMap: item.setGenre(categorysMap[category])
				elif not category in self.unmapedCats: self.unmapedCats.append(category)
				
				# Set Quality and Audio Overlays
				if isHD and contentDetails[u"definition"] == u"hd": item.setVideoFlags(True, "h264")
				else: item.setVideoFlags(False, "h264")
				item.setAudioFlags("aac", "en", 2)
				
				# Fetch Duration
				durationStr = contentDetails[u"duration"]
				durationStr = reFind("(\d+)(\w)", durationStr)
				if durationStr:
					duration = 0
					for time, timeType in durationStr:
						if   timeType == "H": duration += (localInt(time) * 3600)
						elif timeType == "M": duration += (localInt(time) * 60)
						elif timeType == "S": duration += (localInt(time))
					
					# Set duration
					item.setDuration(duration)
				
				# Add Context item to link to related videos
				item.addRelatedContext(action="system.videohosts.YTRelatedVideos", videoid=video[u"id"], channelid=channelID)
				if isRelated: item.addContextMenuItem(_youTubeStr, "XBMC.Container.Update", action="system.videohosts.YTPlaylistVideos", channelid=channelID)
				
				# Add InfoLabels and Data to Processed List
				yield item.getListitemTuple(True)
			
			# Break from loop if needed
			if not (loop is True and "pageToken" in queries): break
		
		# Add Next Page, Playlists and fetch categorys if needed
		if "pageToken" in queries: self.display_next_page(queries["pageToken"])
		if len(channelIDs) == 1 and not "pagetoken" in _plugin and _plugin.get("hasplaylists",u"false") == u"true" : self.display_Playlists(channelIDs[0])
		setattr(listitem.VirtualFS, "finalize", self.finalize)
	
	def set_default_queries(self, kargs={}):
		# Set querie parameters
		if not "key" in kargs: kargs["key"] = APIKEY
		if not "maxResults" in kargs: kargs["maxResults"] = u"50"
		if not "prettyPrint" in kargs: kargs["prettyPrint"] = u"false"
		return kargs
	
	def display_next_page(self, pageToken):
		actions = plugin.copy()
		actions["pagetoken"] = pageToken
		listitem.ListItem.add_next_page(actions)
	
	def display_Playlists(self, channelID):
		icon = "DefaultVideoPlaylists.png"
		thumbnail = (u"youtubeplaylist.png", 2)
		url = {"action":"system.videohosts.YTChannelPlaylists", "url":channelID}
		listitem.ListItem.add_item(plugin.getuni(136), icon, thumbnail, url)
	
	def category_api(self):
		# Create new Queries
		newQueries = self.set_default_queries({})
		newQueries["fields"] = u"items(id,snippet/title)"
		newQueries["part"] = u"snippet"
		newQueries["id"] = u",".join(self.unmapedCats)
		
		# Fetch video Information
		url = u"https://www.googleapis.com/youtube/v3/videoCategories?%s" % plugin.urlencode(newQueries)
		with urlhandler.urlopen(url, -1) as sourceObj: items = load(sourceObj)[u"items"]
		for node in items: self.categorysMap[node[u"id"]] = node[u"snippet"][u"title"]
		self.categorysMap.close(sync=True)
	
	def finalize(self):
		# Fetch category refferences if needed
		if self.unmapedCats: self.category_api()
		else: self.categorysMap.close()
		
		# Fetch Youtube Cache Value
		try: cacheLimit = int(plugin.getAddonSetting("plugin.video.youtube", "kodion.cache.size")) * 1048576
		except: cacheLimit = 5242880
		
		# Fetch Size of video Data file
		videoData = self.videoData
		fileSize = videoData.getsize()
		if fileSize > cacheLimit:
			dataLenght = len(videoData)/2
			for count, data in enumerate(sorted(((videoID, data[u"snippet"][u"publishedAt"]) for videoID, data in videoData.iteritems()), key=lambda data: data[1])):
				if count <= dataLenght: del videoData[data[0]]
				else: break
			videoData.close(sync=True)
		else: videoData.close()

class CategoryFile(storageDB.dictStorage):
	def __init__(self, filename="ytcategorys.json"):
		# Create and set saved searches data path
		_plugin = plugin
		_osPath = _plugin.os.path
		systemCats = _osPath.join(_plugin.getGlobalPath(), u"resources", filename)
		userCats = _osPath.join(plugin.getGlobalProfile(), filename)
		if _osPath.isfile(systemCats) and not _osPath.isfile(userCats):
			__import__("shutil").move(systemCats, userCats)
			super(CategoryFile, self).__init__(userCats)
		else:
			super(CategoryFile, self).__init__(userCats)

class VideoFile(storageDB.dictStorage):
	def __init__(self, filename):
		# Create and set saved searches data path
		filePath = plugin.os.path.join(plugin.getProfile(), filename)
		super(VideoFile, self).__init__(filePath)