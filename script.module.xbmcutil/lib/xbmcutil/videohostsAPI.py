"""
	###################### xbmcutil.videohostsAPI ######################
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
import listitem, urlhandler
from xbmcutil import plugin
from fastjson import load

############################## YoutubeAPI ##############################

class YTChannelUploads(listitem.VirtualFS):
	@plugin.error_handler
	def scraper(self, contentID=None):
		# Create Url Source
		urlString = "http://gdata.youtube.com/feeds/api/users/%s/uploads"
		contentID = plugin.get("url", contentID)
		url = urlString % contentID
		
		# Initialize Gdata API
		Gdata = YoutubeAPI(url, int(plugin.get("processed",0)))
		Gdata.ProcessUrl()
		
		# Fetch Video Results
		videoItems = Gdata.VideoGenerator()
		
		# Add Next Page and/or Playlist
		if plugin.get("hasPlaylists","false") == "true": self.add_youtube_playlists(contentID, label="Playlists")
		
		# Add Next Page
		if Gdata.processed: self.add_next_page({"action":plugin["action"], "url":contentID, "processed":Gdata.processed})
		
		# Set SortMethods and Content
		self.set_sort_methods(self.sort_method_date, self.sort_method_video_runtime, self.sort_method_program_count, self.sort_method_video_rating, self.sort_method_genre, self.sort_method_studio, self.sort_method_video_title)
		self.set_content("episodes")
		
		# Return List of Video Listitems
		return videoItems

class YTChannelPlaylists(listitem.VirtualFS):
	@plugin.error_handler
	def scraper(self, contentID=None):
		# Create Url Source
		urlString = "http://gdata.youtube.com/feeds/api/users/%s/playlists"
		contentID = plugin.get("url", contentID)
		url = urlString % contentID
		
		# Initialize Gdata API
		Gdata = YoutubeAPI(url, int(plugin.get("processed",0)))
		Gdata.ProcessUrl(filterMode="playlists")
		
		# Fetch Video Results
		videoItems = Gdata.PlaylistGenerator(loop=True)
		
		# Add Next Page
		if Gdata.processed: self.add_next_page({"action":plugin["action"], "url":contentID, "processed":Gdata.processed})
		
		# Set SortMethods and Content
		self.set_sort_methods(self.sort_method_video_title, self.sort_method_date)
		self.set_content("episodes")
		
		# Return List of Video Listitems
		return videoItems

class YTPlaylistVideos(listitem.VirtualFS):
	@plugin.error_handler
	def scraper(self, contentID=None):
		# Create Url Source
		urlString = "http://gdata.youtube.com/feeds/api/playlists/%s"
		contentID = plugin.get("url", contentID)
		url = urlString % contentID
		
		# Initialize Gdata API
		Gdata = YoutubeAPI(url, int(plugin.get("processed",0)))
		Gdata.ProcessUrl()
		
		# Fetch Video Results
		videoItems = Gdata.VideoGenerator()
		
		# Add Next Page
		if Gdata.processed: self.add_next_page({"action":plugin["action"], "url":contentID, "processed":Gdata.processed})

		# Set Content Properties
		self.set_sort_methods(self.sort_method_date, self.sort_method_video_runtime, self.sort_method_program_count, self.sort_method_video_rating, self.sort_method_genre, self.sort_method_studio, self.sort_method_video_title)
		self.set_content("episodes")
		
		# Return List of Video Listitems
		return videoItems

class YTRelatedVideos(listitem.VirtualFS):
	@plugin.error_handler
	def scraper(self, contentID=None):
		# Create Url Source
		urlString = "http://gdata.youtube.com/feeds/api/videos/%s/related"
		contentID = plugin.get("url", contentID)
		url = urlString % contentID
		
		# Initialize Gdata API
		Gdata = YoutubeAPI(url)
		Gdata.ProcessUrl()
		
		# Set Content Properties
		self.set_sort_methods(self.sort_method_date, self.sort_method_video_runtime, self.sort_method_program_count, self.sort_method_video_rating, self.sort_method_genre, self.sort_method_studio, self.sort_method_video_title)
		self.set_content("episodes")
		
		# Return List of Video Listitems
		return Gdata.VideoGenerator()

class YoutubeAPI:
	def __init__(self, baseUrl, processed=0, maxResults=50):
		# Set Global Vars
		self.baseUrl = baseUrl
		self.processed = processed
		self.maxResults = maxResults
	
	def ProcessUrl(self, filterMode="video"):
		# Fetch Filter String Based of Filter Mode
		filterString = {"video":"openSearch:totalResults,entry(yt:statistics,gd:rating,media:group(yt:videoid,media:title,yt:duration,media:credit,media:category,media:description,yt:uploaded))", "playlists":"openSearch:totalResults,entry(yt:playlistId,yt:countHint,title,summary,published,media:group(media:thumbnail))"}[filterMode]
		
		# Fetch SourceCode
		sourceObj = urlhandler.urlopen("%s?v=2&max-results=%i&start-index=%i&alt=json&fields=%s" % (self.baseUrl, self.maxResults, self.processed+1, filterString), 28800)
		
		# Fetch List of Entries
		feed = load(sourceObj)["feed"]
		self.entries = feed["entry"]
		sourceObj.close()
		
		# Fetch Total Video Count
		try: videoCount = int(feed["openSearch$totalResults"]["$t"])
		except: videoCount = 0
		
		# Increment Processed Videos
		self.processed += self.maxResults
		if self.processed > videoCount: self.processed = 0
	
	def VideoGenerator(self, loop=False):
		# Setup Converter and Optimizations
		results = []
		localInt = int
		localFloat = float
		imagePath = "http://img.youtube.com/vi/%s/0.jpg"
		localListItem = listitem.ListItem
		addItem = results.append
		strRelated = plugin.getstr(30966)
		
		while 1:
			# Loop Entries
			for node in self.entries:
				# Create listitem object
				item = localListItem()
				item.setParamDict(action="system.source", sourcetype="youtube_com")
				
				# Fetch media group Section
				mediaGroup = node["media$group"]
				
				# Fetch Video ID and Set
				videoID = mediaGroup["yt$videoid"]["$t"]
				item.setThumbnailImage(imagePath % videoID)
				item.setParamDict("url", videoID)
				#item.setIdentifier(videoID)
				
				# Fetch Title
				item.setLabel(mediaGroup["media$title"]["$t"].encode('utf-8'))
				
				# Fetch Studio & Category
				item.setInfoDict(studio=mediaGroup["media$credit"][0]["$t"].title().encode('utf-8'), genre=mediaGroup["media$category"][0]["label"].encode('utf-8'))
				
				# Fetch Duration
				if "yt$duration" in node: item.setDurationInfo(mediaGroup["yt$duration"]["seconds"])
				
				# Fetch View Count
				if "yt$statistics" in node: item.setInfoDict("count", localInt(node["yt$statistics"]["viewCount"]))
				
				# Fetch Possible Plot and Check if Available
				if "media$description" in mediaGroup: item.setInfoDict("plot", mediaGroup["media$description"]["$t"].encode('utf-8'))
				
				# Fetch Possible Rating and Check if Available
				if "gd$rating" in node: item.setInfoDict("rating", localFloat(node["gd$rating"].get("average","0")))
				
				# Fetch Possible Date and Check if Available
				if "yt$uploaded" in mediaGroup: item.setDateInfo(mediaGroup["yt$uploaded"]["$t"].split("T")[0], "%Y-%m-%d")
				
				# Add Context item to link to related videos
				item.addContextMenuItem(strRelated, "XBMC.Container.Update", action="system.videohosts.YTRelatedVideos", url=videoID)
				
				# Add InfoLabels and Data to Processed List
				addItem(item.getListitemTuple(isPlayable=True))
			
			# Fetch Next Set of Pages if Available
			if (loop == True) and (self.processed): self.ProcessUrl()
			else: break
		
		# Return List of Listitems
		return results
	
	def PlaylistGenerator(self, loop=False):
		results = []
		addItem = results.append
		while True:
			# Loop Entries
			for node in self.entries:
				# Create listitem object
				item = listitem.ListItem()
				item.setParamDict("action", "system.videohosts.YTPlaylistVideos")
				
				# Fetch Video ID
				item.setParamDict("url", node["yt$playlistId"]["$t"].encode('utf-8'))
				
				# Fetch Title and Video Cound for combining Title
				item.setLabel("%s (%s)" % (node["title"]["$t"].encode('utf-8'), node["yt$countHint"]["$t"]))
				
				# Fetch Image
				if "media$thumbnail" in node["media$group"]: item.setThumbnailImage(node["media$group"]["media$thumbnail"][0]["url"])
				
				# Fetch Possible Plot and Check if Available
				if "summary" in node: item.setInfoDict("plot", node["summary"]["$t"].encode('utf-8'))
				
				# Fetch Possible Date and Check if Available
				if "published" in node: item.setDateInfo(node["published"]["$t"].split("T")[0], "%Y-%m-%d")
				
				# Add InfoLabels and Data to Processed List
				addItem(item.getListitemTuple())
			
			# Fetch Next Set of Pages if Available
			if (loop == True) and (self.processed): self.ProcessUrl()
			else: break
		
		# Return List of Listitems
		return results

############################## VimeoAPI ##############################

class VUserVideos(listitem.VirtualFS):
	@plugin.error_handler
	def scraper(self, contentID=None):
		# Create Url Source
		urlString = "http://vimeo.com/api/v2/%s/videos.json"
		contentID = plugin.get("url", contentID)
		url = urlString % contentID
		
		# Fetch User Info
		pagelimit = int(plugin.get("pagelimit", 0))
		if pagelimit == 0:
			info = VimeoAPI.user_info(contentID)
			pagelimit = (info["total_videos_uploaded"] -1) / 20 + 1
		
		# Initialize Vimeo API
		Vimeo = VimeoAPI(url, int(plugin.get("currentpage",1)), pagelimit)
		Vimeo.ProcessUrl()
		
		# Fetch Video Results
		videoItems = Vimeo.VideoGenerator()
		
		# Add Next Page
		#if Vimeo.currentPage: self.add_next_page({"url":contentID, "pagelimit":Vimeo.pageLimit, "currentpage":Vimeo.currentPage})
		
		# Set Content Properties
		self.set_sort_methods(self.sort_method_date, self.sort_method_video_runtime, self.sort_method_genre, self.sort_method_video_title)
		self.set_content("episodes")
		
		# Return List of Video Listitems
		return videoItems

class VimeoAPI:
	@classmethod
	def user_info(self, userID):
		# Create Url String
		url = "http://vimeo.com/api/v2/%s/info.json" % userID
		sourceObj = urlhandler.urlopen(url, 604800)
		
		# Fetch User Info
		info = load(sourceObj)
		sourceObj.close()
		return info
	
	def __init__(self, baseUrl, currentPage=1, pageLimit=3):
		# Set Global Vars
		self.baseUrl = baseUrl
		self.currentPage = currentPage
		
		# Restrict Page Limit to 3, Only 3 Pages allowed for Simple API
		if pageLimit > 3: self.pageLimit = 3
		else: self.pageLimit = pageLimit
	
	def ProcessUrl(self):
		# Fetch SourceCode
		sourceObj = urlhandler.urlopen("%s?page=%s" % (self.baseUrl, self.currentPage), 28800)
		
		# Fetch List of Entries
		self.entries = load(sourceObj)
		sourceObj.close()
		print self.entries
		
		# Increment Page Counter
		if self.currentPage >= self.pageLimit: self.currentPage = 0
		else: self.currentPage += 1
	
	def VideoGenerator(self, loop=False):
		# Setup Converter and Optimizations
		results = []
		localListItem = listitem.ListItem
		addItem = results.append
		
		while 1:
			# Loop Entries
			for node in self.entries:
				# Create listitem object
				item = localListItem()
				
				# Fetch Title
				item.setLabel(node["title"].encode('utf-8'))
				
				# Fetch Video ID and Set Actions
				item.setParamDict(action="system.source", sourcetype="vimeo_com", url=node["id"])
				
				# Fetch Plot Description
				item.setInfoDict(plot=node["description"].encode('utf-8'), genre=node["tags"].replace('"','').split(",")[0].encode('utf-8'))
				
				# Fetch Duration and Convert to String
				item.setDurationInfo(node["duration"])
				
				# Fetch Date of Video
				item.setDateInfo(node["upload_date"].split(" ")[0], "%Y-%m-%d")
				
				# Add Thumbnail Image
				item.setThumbnailImage(node["thumbnail_large"])
				
				# Add Quality Overlay
				item.setStreamDict(codec="h264", width=node["width"], height=node["height"])
				
				# Add InfoLabels and Data to Processed List
				addItem(item.getListitemTuple(isPlayable=True))
			
			# Fetch Next Set of Pages if Available
			if (loop == True) and (self.currentPage): self.ProcessUrl()
			else: break
		
		# Return List of Listitems
		return results
