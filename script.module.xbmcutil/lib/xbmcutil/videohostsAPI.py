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
	def scraper(self):
		# Create Url Source
		urlString = u"http://gdata.youtube.com/feeds/api/users/%s/uploads"
		contentID = plugin["url"]
		url = urlString % contentID
		
		# Initialize Gdata API
		Gdata = YoutubeAPI(url, int(plugin.get("processed",0)))
		Gdata.ProcessUrl()
		
		# Fetch Video Results
		videoItems = Gdata.VideoGenerator()
		
		# Add Next Page and/or Playlist
		if plugin.get("hasplaylists",u"false") == u"true": self.add_youtube_playlists(contentID, label=plugin.getuni(136), hasHD=plugin.get("hashd","none"))
		
		# Add Next Page
		if Gdata.processed: self.add_next_page({"action":plugin["action"], "url":contentID, "processed":Gdata.processed, "hashd":plugin.get("hashd","none")})
		
		# Set SortMethods and Content
		self.set_sort_methods(self.sort_method_date, self.sort_method_video_runtime, self.sort_method_program_count, self.sort_method_video_rating, self.sort_method_genre, self.sort_method_studio, self.sort_method_video_title)
		self.set_content("episodes")
		
		# Return List of Video Listitems
		return videoItems

class YTChannelPlaylists(listitem.VirtualFS):
	@plugin.error_handler
	def scraper(self):
		# Create Url Source
		urlString = u"http://gdata.youtube.com/feeds/api/users/%s/playlists"
		contentID = plugin["url"]
		url = urlString % contentID
		
		# Initialize Gdata API
		Gdata = YoutubeAPI(url, int(plugin.get("processed",0)), filterMode="playlists")
		Gdata.ProcessUrl()
		
		# Fetch Video Results
		videoItems = Gdata.PlaylistGenerator(loop=True)
		
		# Add Next Page
		if Gdata.processed: self.add_next_page({"action":plugin["action"], "url":contentID, "processed":Gdata.processed, "hashd":plugin.get("hashd","none")})
		
		# Set SortMethods and Content
		self.set_sort_methods(self.sort_method_video_title, self.sort_method_date)
		self.set_content("files")
		
		# Return List of Video Listitems
		return videoItems

class YTPlaylistVideos(listitem.VirtualFS):
	@plugin.error_handler
	def scraper(self):
		# Create Url Source
		urlString = u"http://gdata.youtube.com/feeds/api/playlists/%s"
		contentID = plugin["url"]
		url = urlString % contentID
		
		# Initialize Gdata API
		Gdata = YoutubeAPI(url, int(plugin.get("processed",0)))
		Gdata.ProcessUrl()
		
		# Fetch Video Results
		videoItems = Gdata.VideoGenerator()
		
		# Add Next Page
		if Gdata.processed: self.add_next_page({"action":plugin["action"], "url":contentID, "processed":Gdata.processed, "hashd":plugin.get("hashd","none")})
		
		# Set Content Properties
		self.set_sort_methods(self.sort_method_date, self.sort_method_video_runtime, self.sort_method_program_count, self.sort_method_video_rating, self.sort_method_genre, self.sort_method_studio, self.sort_method_video_title)
		self.set_content("episodes")
		
		# Return List of Video Listitems
		return videoItems

class YTRelatedVideos(listitem.VirtualFS):
	@plugin.error_handler
	def scraper(self):
		# Create Url Source
		urlString = u"http://gdata.youtube.com/feeds/api/videos/%s/related"
		contentID = plugin["url"]
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
		
		# Fetch Youtube Video Quality Setting
		try: setting = int(plugin.getAddonSetting("plugin.video.youtube", "hd_videos"))
		except: self.isHD = None
		else:
			# Set HD Flag based of Youtube Setting
			hashd = plugin.get("hashd", "none")
			if setting == 1 or hashd == "false": self.isHD = False
			elif (setting == 0 or setting >= 2) and hashd == u"true": self.isHD = True
			else: self.isHD = None
	
	def ProcessUrl(self):
		# Fetch SourceCode
		url = u"%s?v=2&max-results=%i&start-index=%i&alt=json&fields=%s" % (self.baseUrl, self.maxResults, self.processed+1, self.filterString)
		sourceObj = urlhandler.urlopen(url, 14400) # TTL = 4 Hours
		
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
		isHD = self.isHD
		localFloat = float
		imagePath = u"http://img.youtube.com/vi/%s/0.jpg"
		localListItem = listitem.ListItem
		addItem = results.append
		hashd = plugin.get("hashd","none")
		
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
				item.addRelatedContext(action="system.videohosts.YTRelatedVideos", url=videoID, hashd=hashd)
				
				# Set Quality and Audio Overlays
				item.setQualityIcon(isHD)
				item.setAudioInfo()
				
				# Add InfoLabels and Data to Processed List
				addItem(item.getListitemTuple(True))
			
			# Fetch Next Set of Pages if Available
			if (loop == True) and (self.processed): self.ProcessUrl()
			else: break
		
		# Return List of Listitems
		return results
	
	def PlaylistGenerator(self, loop=False):
		results = []
		addItem = results.append
		hashd = plugin.get("hashd", "none")
		while True:
			# Loop Entries
			for node in self.entries:
				# Create listitem object
				item = listitem.ListItem()
				item.setParamDict("action", "system.videohosts.YTPlaylistVideos")
				
				# Fetch Video ID
				item.setParamDict("url", node[u"yt$playlistId"][u"$t"])
				item.setParamDict("hashd", hashd)
				
				# Fetch Title and Video Cound for combining Title
				item.setLabel(u"%s (%s)" % (node[u"title"][u"$t"], node[u"yt$countHint"][u"$t"]))
				
				# Fetch Image
				if u"media$thumbnail" in node[u"media$group"]: item.setThumbnailImage(sorted(node[u"media$group"][u"media$thumbnail"], key=lambda x: x[u"width"])[-1][u"url"])
				
				# Fetch Possible Plot and Check if Available
				if u"summary" in node: item.setInfoDict("plot", node[u"summary"][u"$t"])
				
				# Fetch Possible Date and Check if Available
				if u"published" in node: item.setDateInfo(node[u"published"][u"$t"].split(u"T")[0], "%Y-%m-%d")
				
				# Add InfoLabels and Data to Processed List
				addItem(item.getListitemTuple(False))
			
			# Fetch Next Set of Pages if Available
			if (loop == True) and (self.processed): self.ProcessUrl()
			else: break
		
		# Return List of Listitems
		return results
