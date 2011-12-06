'''
   Simple Downloader plugin for XBMC
   Copyright (C) 2010-2011 Tobias Ussing And Henrik Mosgaard Jensen

   This program is free software: you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation, either version 3 of the License, or
   (at your option) any later version.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.
   
   You should have received a copy of the GNU General Public License
   along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import sys, urllib2, os, xbmcaddon, time
import DialogDownloadProgress

class SimpleDownloader():
	dialog = ""
	def __init__(self):
		self.version = "0.9.0"
		self.plugin = "SimpleDownloader-" + self.version

		self.INVALID_CHARS = "\\/:*?\"<>|"

		if sys.modules[ "__main__" ].common:
			self.common = sys.modules[ "__main__" ].common
		else:
			import CommonFunctions
			common = CommonFunctions.CommonFunctions()
			common.plugin = self.plugin

		try:
			import StorageServer
		except:
			import storageserverdummy as StorageServer

		self.cache = StorageServer.StorageServer()
		self.cache.table_name = "Downloader"

                if sys.modules[ "__main__" ].xbmc:
                        self.xbmc = sys.modules["__main__"].xbmc
                else:
                        import xbmc
                        self.xbmc = xbmc

                if sys.modules[ "__main__" ].xbmcvfs:
                        self.xbmcvfs = sys.modules["__main__"].xbmcvfs
                else:
			try:
				import xbmcvfs
			except ImportError:
				import xbmcvfsdummy as xbmcvfs				
                        self.xbmcvfs = xbmcvfs

		if sys.modules[ "__main__" ].dbglevel:
                        self.dbglevel = sys.modules[ "__main__" ].dbglevel
		else:
                        self.dbglevel = 3

		if sys.modules[ "__main__" ].dbg:
			self.dbg = sys.modules[ "__main__" ].dbg
		else:
			self.dbg = True

		self.settings = sys.modules[ "__main__" ].settings

		self.language = self.settings.getLocalizedString
		self.download_path = self.settings.getSetting( "downloadPath" )
		self.hide_during_playback = self.settings.getSetting( "hideDuringPlayback" ) == "true"
		self.notification_length = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10][int(self.settings.getSetting( 'notification_length' ))]
		
		if hasattr(sys.modules[ "__main__" ], "settings"):
			inherited_settings = sys.modules[ "__main__" ].settings
			if inherited_settings.getSetting( "downloadPath" ):
				self.download_path = inherited_settings.getSetting( "downloadPath" )
			if inherited_settings.getSetting( "hideDuringPlayback" ):
				self.hide_during_playback = inherited_settings.getSetting( "hideDuringPlayback" ) == "true"
			if inherited_settings.getSetting( "notification_length" ):
				self.notification_length = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10][int(inherited_settings.getSetting( 'notification_length' ))]

		if sys.modules[ "__main__" ].plugin:
			self.plugin = sys.modules[ "__main__" ].plugin
	
	def downloadVideo(self, params = {}):
		self.common.log("")
		get = params.get
		
		if (not self.download_path):
			self.showMessage(self.language(30600), self.language(30611))
			self.settings.openSettings()
			self.dbg = self.settings.getSetting("debug") == "true"
			self.download_path = self.settings.getSetting( "downloadPath" )

		if self.cache.lock("SimpleDownloaderLock"):
			self.common.log("Downloader not active, initializing downloader.")
			
			self.addVideoToDownloadQueue(params)
			self.processQueue(params)
			self.cache.unlock("SimpleDownloaderLock")
		else:
			self.common.log("Downloader is active, Queueing video.")
			self.addVideoToDownloadQueue(params)

	def processQueue(self, params = {}):
		self.common.log("")
		video = self.getNextVideoFromDownloadQueue()
		
		if video:
			if not self.dialog:
				self.dialog = DialogDownloadProgress.DownloadProgress()
				self.dialog.create(self.language(30605), "")

			while video:
				params["videoid"] = video['videoid']
				if not video.has_key("video_url") and video.has_key("callback_for_url"):
					( video, status ) = video['callback_for_url'](params)

				if not video.has_key("video_url"):
					if video.has_key("apierror"):
						self.showMessage(self.language(30625), video["apierror"])
					else:
						self.showMessage(self.language(30625), "ERROR")
					self.removeVideoFromDownloadQueue(video['videoid'])
					video = self.getNextVideoFromDownloadQueue()
					continue

				if video.has_key("stream_map"):
					self.showMessage(self.language(30607), self.language(30619))
					self.removeVideoFromDownloadQueue(video['videoid'])
					video = self.getNextVideoFromDownloadQueue()
					continue

				if video["video_url"].find("swfurl") > 0 or video["video_url"].find("rtmp") > -1:
					self.common.log("Found RTMP stream")
					( dvideo, status ) = self.downloadVideoRTMP(video, params)
					if status != 200:
						self.showMessage(self.language( 30625 ), self.language(30619))
				else:
					( dvideo, status ) = self.downloadVideoURL(video)
				self.removeVideoFromDownloadQueue(video['videoid'])
				video = self.getNextVideoFromDownloadQueue()

			self.common.log("Finished download queue.")
			if self.dialog:
				self.dialog.close()
				self.common.log("Closed dialog")
			self.dialog = ""

	def downloadVideoRTMP(self, video, params = {}):
		get = params.get
		self.common.log(video['Title'])

		if video.has_key("player_url"):
			player_url = video["player_url"]
		else:
			player_url = None


		video["downloadPath"] = self.download_path
		filename = "%s-[%s].mp4" % ( ''.join(c for c in video['Title'].decode("utf-8") if c not in self.INVALID_CHARS), video["videoid"] )
		filename_incomplete = os.path.join(self.xbmc.translatePath( "special://temp" ).decode("utf-8"), filename )
		filename_complete = os.path.join(self.download_path.decode("utf-8"), filename)

		if self.xbmcvfs.exists(filename_complete):
			self.xbmcvfs.delete(filename_complete)

		try:
			import subprocess
			probe_args = ['rtmpdump', '-B', '1'] + [[], ['-v']][get("live", "false") == "true"] + [[], ['-W', player_url]][player_url is not None] + ['-r', video["video_url"], '-o', filename_incomplete]
			p = subprocess.Popen(probe_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			output = p.communicate()[1]
			if output.find("filesize") > -1:
				total_size = int(float(output[output.find("filesize") + len("filesize"):output.find("\n", output.find("filesize"))]))
			else:
				total_size = 0

		except (OSError, IOError):
			self.self.showMessage(self.language(30600), self.language(30619))
			return ( {}, 500 )

		basic_args = ['rtmpdump', '-V'] + [[], ['-v']][get("live", "false") == "true"] + [[], ['-W', player_url]][player_url is not None] + ['-r', video["video_url"], '-o', filename_incomplete]

		p = subprocess.Popen(basic_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		bytes_so_far = 0
		opercent = -1
		retval = 1
		if total_size == 0:
			total_size = int(get("max_size", "10000000"))

		self.common.log('total_size ')
		for chunk in p.stderr:
			bytes_so_far = os.path.getsize(filename_incomplete)
			self.common.log('bytes_so_far : ' + str(bytes_so_far))
			if total_size > 0:
				percent = float(bytes_so_far) / float(total_size) * 100
			else:
				percent = opercent + 1 
				if percent == 100:
					percent = 0.1

			if percent != opercent:
				opercent = percent
				queue = self.cache.get("SimpleDownloaderQueue")

				if queue:
					try:
						videos = eval(queue)
					except:
						videos = {}
				else:
					videos = {}
				
				heading = "[%s] %s - %s%%" % ( str(len(videos)), self.language(30624), str(int(percent)))

			       	self.common.log("Updating %s - %s" % ( heading, self.common.makeAscii(video["Title"])), 2)
				if self.xbmc.Player().isPlaying() and self.xbmc.getCondVisibility("VideoPlayer.IsFullscreen"):
					if self.dialog:
						self.dialog.close()
						self.dialog = ""
				else:
					if not self.dialog:
						self.dialog = DialogDownloadProgress.DownloadProgress()
						self.dialog.create(self.language(30605), "")
					self.dialog.update(percent=percent, heading = heading, label=video["Title"])

			self.common.log('total_size : ' + str(total_size))
			if bytes_so_far >= total_size and total_size != 0:
				self.common.log("Download complete")
				retval = 0
				break
			# Some rtmp streams seem abort after ~ 99.8%. Don't complain for those
			if total_size * 0.998 < bytes_so_far:
				self.common.log("Download complete. Size disrepancy: " + str( total_size - bytes_so_far))
				retval = 0
				break

		if retval == 0:
			if self.xbmcvfs.exists(filename_incomplete):
				self.common.log("Found incomplete file: " + filename_incomplete)
				self.xbmcvfs.rename(filename_incomplete, filename_complete)
			else:
				self.common.log("Download complete but couldn't find file: " + filename_incomplete)

			if not self.dialog:
				self.dialog = DialogDownloadProgress.DownloadProgress()
			self.dialog.update(heading = self.language(30604), label=video["Title"])

			self.common.log("done")
			return ( video, 200 )
		else:
			self.common.log("Download failed")
			return ( {}, 500 )
			
	def downloadVideoURL(self, video, params = {}):
		self.common.log(video['Title'])
		
		video["downloadPath"] = self.download_path

		url = urllib2.Request(video['video_url'])
		url.add_header('User-Agent', self.common.USERAGENT);
		filename = "%s-[%s].mp4" % ( ''.join(c for c in video['Title'].decode("utf-8") if c not in self.INVALID_CHARS), video["videoid"] )
		filename_incomplete = os.path.join(self.xbmc.translatePath( "special://temp" ).decode("utf-8"), filename )
		filename_complete = os.path.join(self.download_path.decode("utf-8"), filename)

		if self.xbmcvfs.exists(filename_complete):
			self.xbmcvfs.delete(filename_complete)

		file = self.common.openFile(filename_incomplete, "wb")
		con = urllib2.urlopen(url);

		total_size = 8192 * 25
		chunk_size = 8192

		if con.info().getheader('Content-Length').strip():			
			total_size = int(con.info().getheader('Content-Length').strip())	
			chunk_size = int(total_size / 200) # We only want 200 updates of the status bar.
			if chunk_size <= 0:
				chunk_size = 5
			elif chunk_size > 3000000:
				chunk_size = 3000000
		try:
			bytes_so_far = 0
			
			videos = {}
			while 1:
				chunk = con.read(chunk_size)
				bytes_so_far += len(chunk)
				percent = float(bytes_so_far) / float(total_size) * 100
				file.write(chunk)
				
				queue = self.cache.get("SimpleDownloaderQueue")

				if queue:
					try:
						videos = eval(queue)
					except:
						videos = {}
				else:
					videos = {}
				
				heading = "[%s] %s - %s%%" % ( str(len(videos)), self.language(30624), str(int(percent)))

				self.common.log("Updating %s - %s" % ( heading, self.common.makeAscii(video["Title"])), 2)
				if self.xbmc.Player().isPlaying() and self.xbmc.getCondVisibility("VideoPlayer.IsFullscreen"):
					if self.dialog:
						self.dialog.close()
						self.dialog = ""
				else:
					if not self.dialog:
						self.dialog = DialogDownloadProgress.DownloadProgress()
						self.dialog.create(self.language(30605), "")
					self.dialog.update(percent=percent, heading = heading, label=video["Title"])

				if not chunk:
					break
			
			con.close()
			file.close()
		except:
			self.common.log("Download failed.")
			try:
				con.close()
				file.close()
			except:
				self.common.log("Failed to close download stream and file handle")
			self.showMessage(self.language(30625), "ERROR")
			return ( {}, 500 )
		
		if self.xbmcvfs.exists(filename_incomplete):
			self.common.log("Found incomplete file: " + filename_incomplete)
			self.xbmcvfs.rename(filename_incomplete, filename_complete)
			self.common.log("Moved file")
		else:
			self.common.log("Download complete but couldn't find file: " + filename_incomplete)


		if not self.dialog:
			self.dialog = DialogDownloadProgress.DownloadProgress()
		self.dialog.update(heading = self.language(30604), label=video["Title"])

		self.common.log("done")
		return ( video, 200 )
		
	#============================= Download Queue =================================
	def getNextVideoFromDownloadQueue(self):
		if self.cache.lock("SimpleDownloaderQueueLock"):
			videos = []
			
			queue = self.cache.get("SimpleDownloaderQueue")
			self.common.log("queue loaded : " + repr(queue))

			if queue:
				try:
					videos = eval(queue)
				except: 
					videos = []
		
			video = {}
			if len(videos) > 0:
				video = videos[0]
				self.common.log("getNextVideoFromDownloadQueue released. returning : " + video["videoid"])

			self.cache.unlock("SimpleDownloaderQueueLock")
			return video
		else:
			self.common.log("getNextVideoFromDownloadQueue Couldn't aquire lock")

	def addVideoToDownloadQueue(self, params = {}):
		if self.cache.lock("SimpleDownloaderQueueLock"):
			get = params.get

			videos = []
			if get("videoid"):
				queue = self.cache.get("SimpleDownloaderQueue")
				self.common.log("queue loaded : " + repr(queue))

				if queue:
					try:
						videos = eval(queue)
					except:
						videos = []
		
				append = True
				for index, video in enumerate(videos):
					if video["videoid"] == get("videoid"):
						print "FOUND ID"
						append = False
						del videos[index]
						break;
				if append:					
					videos.append(params)
					self.common.log("Moved " + get("videoid") + " to front of queue. - " + str(len(videos)))
				else:
					videos.insert(1, params)
					self.common.log("Added: " + get("videoid") + " to queue - " + str(len(videos)))

				self.cache.set("SimpleDownloaderQueue", repr(videos))

			self.cache.unlock("SimpleDownloaderQueueLock")
			self.common.log("addVideoToDownloadQueue released")
		else:
			self.common.log("addVideoToDownloadQueue Couldn't lock")
		
	def removeVideoFromDownloadQueue(self, videoid):
		if self.cache.lock("SimpleDownloaderQueueLock"):
			videos = []
			
			queue = self.cache.get("SimpleDownloaderQueue")
			self.common.log("queue loaded : " + repr(queue))
			if queue:
				try:
					videos = eval(queue)
				except:
					videos = []

			for index, video in enumerate(videos):
				if video["videoid"] == videoid:
					del videos[index]
					self.cache.set("SimpleDownloaderQueue", repr(videos))
					self.common.log("Removed: " + video["videoid"] + " from queue")

			self.cache.unlock("SimpleDownloaderQueueLock")
			self.common.log("removeVideoFromDownloadQueue released")
		else:
			self.common.log("removeVideoFromDownloadQueue Exception")

	# Shows a more user-friendly notification
        def showMessage(self, heading, message):
                self.xbmc.executebuiltin('XBMC.Notification("%s", "%s", %s)' % ( heading, message, self.notification_length) )

