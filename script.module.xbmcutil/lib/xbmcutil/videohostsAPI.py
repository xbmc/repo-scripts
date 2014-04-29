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
		urlString = u"http://gdata.youtube.com/feeds/api/users/%s/uploads"
		contentID = plugin.get("url", contentID)
		url = urlString % contentID
		
		# Initialize Gdata API
		Gdata = YoutubeAPI(url, int(plugin.get("processed",0)))
		Gdata.ProcessUrl()
		
		# Fetch Video Results
		videoItems = Gdata.VideoGenerator()
		
		# Add Next Page and/or Playlist
		if plugin.get("hasPlaylists",u"false") == u"true": self.add_youtube_playlists(contentID, label=u"Playlists")
		
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
		urlString = u"http://gdata.youtube.com/feeds/api/users/%s/playlists"
		contentID = plugin.get("url", contentID)
		url = urlString % contentID
		
		# Initialize Gdata API
		Gdata = YoutubeAPI(url, int(plugin.get("processed",0)), filterMode="playlists")
		Gdata.ProcessUrl()
		
		# Fetch Video Results
		videoItems = Gdata.PlaylistGenerator(loop=True)
		
		# Add Next Page
		if Gdata.processed: self.add_next_page({"action":plugin["action"], "url":contentID, "processed":Gdata.processed})
		
		# Set SortMethods and Content
		self.set_sort_methods(self.sort_method_video_title, self.sort_method_date)
		self.set_content("files")
		
		# Return List of Video Listitems
		return videoItems

class YTPlaylistVideos(listitem.VirtualFS):
	@plugin.error_handler
	def scraper(self, contentID=None):
		# Create Url Source
		urlString = u"http://gdata.youtube.com/feeds/api/playlists/%s"
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
		urlString = u"http://gdata.youtube.com/feeds/api/videos/%s/related"
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
	def __init__(self, baseUrl, processed=0, maxResults=50, filterMode="video"):
		# Set Global Vars
		self.baseUrl = baseUrl
		self.processed = processed
		self.maxResults = maxResults
		
		# Fetch Filter String Based of Filter Mode
		if filterMode == "video": self.filterString = u"openSearch:totalResults,entry(yt:statistics,gd:rating,media:group(yt:videoid,media:title,yt:aspectRatio,yt:duration,media:credit,media:category,media:description,yt:uploaded))"
		elif filterMode == "playlists": self.filterString = u"openSearch:totalResults,entry(yt:playlistId,yt:countHint,title,summary,published,media:group(media:thumbnail))"
	
	def ProcessUrl(self):
		# Fetch SourceCode
		url = u"%s?v=2&max-results=%i&start-index=%i&alt=json&fields=%s" % (self.baseUrl, self.maxResults, self.processed+1, self.filterString)
		sourceObj = urlhandler.urlopen(url, 28800)
		
		# Fetch List of Entries
		feed = load(sourceObj)[u"feed"]
		self.entries = feed[u"entry"]
		sourceObj.close()
		
		# Fetch Total Video Count
		videoCount = feed[u"openSearch$totalResults"][u"$t"]
		
		# Increment Processed Videos
		self.processed += self.maxResults
		if self.processed > videoCount: self.processed = 0
	
	def VideoGenerator(self, loop=False):
		# Setup Converter and Optimizations
		results = []
		localInt = int
		localFloat = float
		imagePath = u"http://img.youtube.com/vi/%s/0.jpg"
		localListItem = listitem.ListItem
		addItem = results.append
		
		while 1:
			# Loop Entries
			for node in self.entries:
				# Create listitem object
				item = localListItem()
				item.setParamDict(action="system.source", sourcetype="youtube_com")
				
				# Fetch media group Section
				mediaGroup = node[u"media$group"]
				
				# Fetch Video ID and Set
				videoID = mediaGroup[u"yt$videoid"][u"$t"]
				item.setThumbnailImage(imagePath % videoID)
				item.setParamDict("url", videoID)
				
				# Fetch Title
				item.setLabel(mediaGroup[u"media$title"][u"$t"])
				
				# Fetch Studio & Category
				item.setInfoDict(studio=mediaGroup[u"media$credit"][0][u"yt$display"], genre=mediaGroup[u"media$category"][0][u"label"])
				
				# Fetch Duration
				if u"yt$duration" in node: item.setDurationInfo(mediaGroup[u"yt$duration"][u"seconds"])
				
				# Fetch View Count
				if u"yt$statistics" in node: item.setInfoDict("count", localInt(node[u"yt$statistics"][u"viewCount"]))
				
				# Fetch Possible Plot and Check if Available
				if u"media$description" in mediaGroup: item.setInfoDict("plot", mediaGroup[u"media$description"][u"$t"])
				
				# Fetch Possible Rating and Check if Available
				if u"gd$rating" in node: item.setInfoDict("rating", localFloat(node[u"gd$rating"].get(u"average","0")))
				
				# Fetch Possible Date and Check if Available
				if u"yt$uploaded" in mediaGroup: item.setDateInfo(mediaGroup[u"yt$uploaded"][u"$t"].split(u"T")[0], "%Y-%m-%d")
				
				# Fetch aspectRatio if available
				if u"yt$aspectRatio" in mediaGroup and mediaGroup[u"yt$aspectRatio"][u"$t"] == u"widescreen": item.setStreamDict("aspect", 1.78)
				
				# Add Context item to link to related videos
				item.addRelatedContext(action="system.videohosts.YTRelatedVideos", url=videoID)
				
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
				item.setParamDict("url", node[u"yt$playlistId"][u"$t"])
				
				# Fetch Title and Video Cound for combining Title
				item.setLabel(u"%s (%s)" % (node[u"title"][u"$t"], node[u"yt$countHint"][u"$t"]))
				
				# Fetch Image
				if u"media$thumbnail" in node[u"media$group"]: item.setThumbnailImage(sorted(node[u"media$group"][u"media$thumbnail"], key=lambda x: x[u"width"])[-1][u"url"])
				
				# Fetch Possible Plot and Check if Available
				if u"summary" in node: item.setInfoDict("plot", node[u"summary"][u"$t"])
				
				# Fetch Possible Date and Check if Available
				if u"published" in node: item.setDateInfo(node[u"published"][u"$t"].split(u"T")[0], "%Y-%m-%d")
				
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
		urlString = u"http://vimeo.com/api/v2/%s/videos.json"
		contentID = plugin.get("url", contentID)
		url = urlString % contentID
		
		# Fetch User Info
		pagelimit = int(plugin.get("pagelimit", 0))
		if pagelimit == 0:
			info = VimeoAPI.user_info(contentID)
			pagelimit = (info[u"total_videos_uploaded"] -1) / 20 + 1
		
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
		url = u"http://vimeo.com/api/v2/%s/info.json" % userID
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
		sourceObj = urlhandler.urlopen(u"%s?page=%i" % (self.baseUrl, self.currentPage), 28800)
		
		# Fetch List of Entries
		self.entries = load(sourceObj)
		sourceObj.close()
		
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
				item.setLabel(node[u"title"])
				
				# Fetch Video ID and Set Actions
				item.setParamDict(action="system.source", sourcetype="vimeo_com", url=node[u"id"])
				
				# Fetch Plot Description
				item.setInfoDict(plot=node[u"description"], genre=node[u"tags"].replace(u'"',u'').split(u",")[0])
				
				# Fetch Duration and Convert to String
				item.setDurationInfo(node[u"duration"])
				
				# Fetch Date of Video
				item.setDateInfo(node[u"upload_date"].split(u" ")[0], "%Y-%m-%d")
				
				# Add Thumbnail Image
				item.setThumbnailImage(node[u"thumbnail_large"])
				
				# Add Quality Overlay
				item.setStreamDict(codec="h264", width=node[u"width"], height=node[u"height"])
				
				# Add InfoLabels and Data to Processed List
				addItem(item.getListitemTuple(isPlayable=True))
			
			# Fetch Next Set of Pages if Available
			if (loop == True) and (self.currentPage): self.ProcessUrl()
			else: break
		
		# Return List of Listitems
		return results
