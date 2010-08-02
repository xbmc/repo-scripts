import xbmc, xbmcgui, xbmcaddon
import sys
import pickle
import os
import traceback
import thread
sys.path.append(os.path.join(os.getcwd().replace(";",""),'resources','lib'))

from GrooveAPI import *
from GroovePlayer import GroovePlayer
from GrooveGUI import *
from operator import itemgetter, attrgetter

#_ = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__version__ = sys.modules[ "__main__" ].__version__
__settings__ = sys.modules[ "__main__" ].__settings__
__language__ = sys.modules[ "__main__" ].__language__
__scriptid__ = sys.modules[ "__main__" ].__scriptid__

class GrooveClass(xbmcgui.WindowXMLDialog):

	STATE_LIST_EMPTY = 0
	STATE_LIST_SEARCH = 1
	STATE_LIST_SONGS = 2
	STATE_LIST_ARTISTS = 3
	STATE_LIST_ALBUMS = 4
	STATE_LIST_ALBUMS_BY_ARTIST = 5
	STATE_LIST_SONGS_ON_ALBUM = 6
	STATE_LIST_SONGS_ON_ALBUM_FROM_SEARCH = 7
	STATE_LIST_PLAYLIST = 8

	SEARCH_LIMIT = 20

	def onInit(self):
		try:
			if self.initialized == True:
				self.listMenu()
		except:
			self.initVars()
			try:
				self.gs = GrooveAPI(enableDebug = __settings__.getSetting("debug"))
				pass
			except:
				self.message('Unable to get a new session ID. Wait a few minutes and try again', 'Error')
				xbmc.log('GrooveShark Exception (onInit): ' + str(sys.exc_info()[0]))
				traceback.print_exc()
				self.close()
			self.initialized = True
			self.showPlayButton()
			self.initPlayer()
			#print str(thread.start_new_thread(self.threadPlayer, ()))
			self.login()
			self.getPopularSongs()

	def initPlayer(self):
		try:
			self.player = GroovePlayer(xbmc.PLAYER_CORE_MPLAYER)
			self.player.setCallBackFunc(self.playerChanged)
		except:
			xbmc.log('GrooveShark Exception (initPlayer): ' + str(sys.exc_info()[0]))
			traceback.print_exc()
			

	def initVars(self):
		self.setStateLabel('')
		self.stateList = GrooveClass.STATE_LIST_EMPTY
		self.searchResultSongs = []
		self.searchResultAlbums = []
		self.searchResultArtists = []
		self.songs = []
		self.artists = []
		self.albums = []
		self.playlist = []
		self.playlistId = 0
		self.playlistName = 'Unsaved'
		self.searchText = ""
		self.settings = []
		self.rootDir = os.getcwd()
		
		#self.cacheDir = os.path.join(self.rootDir, 'cache')
		self.cacheDir = os.path.join('special://profile/', 'addon_data', __scriptid__)
		if os.path.exists(self.cacheDir) == False:
			os.mkdir(self.cacheDir)		
		self.cacheDir = os.path.join('special://profile/', 'addon_data', __scriptid__, 'cache')
		if os.path.exists(self.cacheDir) == False:
			os.mkdir(self.cacheDir)
		self.nowPlaying = -1
		self.defaultArtTinyUrl = 'http://beta.grooveshark.com/webincludes/img/defaultart/album/tdefault.png'
		self.defaultArtSmallUrl = 'http://beta.grooveshark.com/webincludes/img/defaultart/album/sdefault.png'
		self.defaultArtMediumUrl = 'http://beta.grooveshark.com/webincludes/img/defaultart/album/mdefault.png'
		self.itemsPrPage = 10
		self.listPos = [0]
		for i in range(GrooveClass.STATE_LIST_PLAYLIST):
			self.listPos.append(0)
		#self.settings = self.getSavedSettings()
		
		
	def onFocus(self, controlID):
		pass

	def onAction(self, action):
		aId = action.getId()
		if aId == 10:
			dialog = xbmcgui.Dialog()
			c = dialog.yesno(__language__(1003), __language__(1004))
			if c == True:
				self.close()
		elif aId == 117: # Play
			self.player.play()
		elif aId == 14: # Skip
			self.playNextSong()
		elif aId == 15: # Replay
			self.playPrevSong()
		else:
			pass
 
	def onClick(self, control):
		# The state machine should be rewritten at some point
		if control == 1002:
			text = self.getInput(__language__(1000), "")
			if text != "":
				self.searchAll(text)
				self.stateList = GrooveClass.STATE_LIST_SEARCH
				self.listMenu()
		elif control == 1001:
			self.stateList = GrooveClass.STATE_LIST_PLAYLIST
			self.listMenu()
		elif control == 1003:
			self.showPlaylists()
		elif control == 1004:
			self.getPopular()
			self.stateList = GrooveClass.STATE_LIST_SEARCH
			self.listMenu()
		elif control == 1005:
			__settings__.openSettings()
			#self.showSettings()
		elif control == 2001: #Prev
			self.playPrevSong()
		elif control == 2002: #Stop
			self.playStop()
		elif control == 2003: #Play
			self.playPause()
		elif control == 2004: #Next
			self.playNextSong()
		elif control == 2005: #Pause
			self.playPause()
		elif control == 50:
			n = self.getCurrentListPosition()
			item = self.getListItem(n)
			if self.stateList == GrooveClass.STATE_LIST_EMPTY:
				pass
			elif self.stateList == GrooveClass.STATE_LIST_PLAYLIST:
				if n == 0:
					self.setStateListUp(GrooveClass.STATE_LIST_SEARCH)
				else:
					self.showOptionsPlaylist()
					pass
			elif self.stateList == GrooveClass.STATE_LIST_SEARCH:
				if n == 0:
					self.setStateListDown(GrooveClass.STATE_LIST_SONGS)
				elif n == 1:
					self.setStateListDown(GrooveClass.STATE_LIST_ARTISTS)
				elif n == 2:
					self.setStateListDown(GrooveClass.STATE_LIST_ALBUMS)
				else:
					pass
			elif self.stateList == GrooveClass.STATE_LIST_SONGS:
				if n == 0:
					self.setStateListUp(GrooveClass.STATE_LIST_SEARCH)
				else:
					self.showOptionsSearch(self.searchResultSongs)
			elif self.stateList == GrooveClass.STATE_LIST_ARTISTS:
				if n == 0:
					self.setStateListUp(GrooveClass.STATE_LIST_SEARCH)
				else:
					#if self.settings[2] == True: # Get verified albums. Disabled in API so skip it for now
						#self.albums = self.gs.artistGetVerifiedAlbums(self.searchResultArtists[n-1][1],GrooveClass.SEARCH_LIMIT)
					#	self.albums = self.gs.artistGetAlbums(self.searchResultArtists[n-1][1],GrooveClass.SEARCH_LIMIT)
					#else: # Get all albums
					self.albums = self.gs.artistGetAlbums(self.searchResultArtists[n-1][1],GrooveClass.SEARCH_LIMIT)
					self.setStateListDown(GrooveClass.STATE_LIST_ALBUMS_BY_ARTIST)
			elif self.stateList == GrooveClass.STATE_LIST_ALBUMS:
				if n == 0:
					self.setStateListUp(GrooveClass.STATE_LIST_SEARCH)
				else:
					self.songs = self.gs.albumGetSongs(self.searchResultAlbums[n-1][3],GrooveClass.SEARCH_LIMIT)
					self.setStateListDown(GrooveClass.STATE_LIST_SONGS_ON_ALBUM_FROM_SEARCH)
			elif self.stateList == GrooveClass.STATE_LIST_SONGS_ON_ALBUM_FROM_SEARCH:
				if n == 0:
					self.setStateListUp(GrooveClass.STATE_LIST_ALBUMS)
				else:
					self.showOptionsSearch(self.songs)
			elif self.stateList == GrooveClass.STATE_LIST_ALBUMS_BY_ARTIST:
				if n == 0:
					self.setStateListUp(GrooveClass.STATE_LIST_ARTISTS)
				else:
					print 'l180, n:' + str(n)
					self.songs = self.gs.albumGetSongs(self.albums[n-1][3],GrooveClass.SEARCH_LIMIT)
					self.setStateListDown(GrooveClass.STATE_LIST_SONGS_ON_ALBUM)
			elif self.stateList == GrooveClass.STATE_LIST_SONGS_ON_ALBUM:
				if n == 0:
					self.setStateListUp(GrooveClass.STATE_LIST_ALBUMS_BY_ARTIST)
				else:
					self.showOptionsSearch(self.songs)
		else:
			pass

	def listMenu(self):
		n = self.getCurrentListPosition()
		if self.stateList == GrooveClass.STATE_LIST_EMPTY:
			pass #listpopular

		elif self.stateList == GrooveClass.STATE_LIST_PLAYLIST:
			self.listSongs(self.playlist,  __language__(3007) + ': ' + self.playlistName)
		
		elif self.stateList == GrooveClass.STATE_LIST_SEARCH:
			self.listSearchResults(self.searchResultSongs, self.searchResultArtists, self.searchResultAlbums, p=self.listPos[self.stateList])	

		elif self.stateList == GrooveClass.STATE_LIST_SONGS:
			self.listSongs(self.searchResultSongs, __language__(3003) + '"' + self.searchText + '"', p=self.listPos[self.stateList])

		elif self.stateList == GrooveClass.STATE_LIST_ARTISTS:
			self.listArtists(self.searchResultArtists, __language__(3004) + '"' + self.searchText + '"', p=self.listPos[self.stateList])
				
		elif self.stateList == GrooveClass.STATE_LIST_ALBUMS:
			self.listAlbums(self.searchResultAlbums, __language__(3005) + '"' + self.searchText + '"', withArtist=1, p=self.listPos[self.stateList])

		elif self.stateList == GrooveClass.STATE_LIST_SONGS_ON_ALBUM_FROM_SEARCH:
			self.listSongs(self.songs, self.searchResultAlbums[n-1][2] + ' ' + __language__(3006) + ' ' + self.searchResultAlbums[n-1][0], p=self.listPos[self.stateList])

		elif self.stateList == GrooveClass.STATE_LIST_ALBUMS_BY_ARTIST:
			self.listAlbums(self.albums, p=self.listPos[self.stateList])

		elif self.stateList == GrooveClass.STATE_LIST_SONGS_ON_ALBUM:
			self.listSongs(self.songs, self.albums[n-1][2] + ' ' + __language__(3006) + ' ' + self.albums[n-1][0], p=self.listPos[self.stateList])
		else:
			pass
		self.playlistHasFocus()
		
	def threadPlayer(self):
		i = 0
		while i < 10:
			self.setStateLabel(str(i))
			xbmc.sleep(1000)
			i += 1

	def setStateListDown(self, state):
		#print 'Down, stateList: ' + str(self.stateList)
		#print 'Down, New state: ' + str(state)
		self.listPos[self.stateList] = self.getCurrentListPosition()
		self.stateList = state
		self.listMenu()

	def setStateListUp(self, state):
		#print 'Up, stateList: ' + str(self.stateList)
		#print 'Up, New state: ' + str(state)
		self.listPos[self.stateList] = 0
		self.stateList = state
		self.listMenu()

	def showOptionsSearch(self, songs):
		items = [__language__(101),__language__(102),__language__(103),__language__(104)]
		result = gSimplePopup(title='', items=items, width=200)

		if result == 0:
			n = self.getCurrentListPosition()
			self.playlist.append(songs[n-1])
		elif result == 1:
			n = self.getCurrentListPosition()
			self.playlist = songs
			self.playSong(n, offset=-1)
		elif result == 2:
			l = len(songs)
			for n in range(0, l):
				self.playlist.append(songs[n])
		elif result == 3:
			items = []
			playlists = self.gs.userGetPlaylists(limit=150)
			i = 0
			while (i < len(playlists)):
				items.append(playlists[i][0])
				i += 1
			result = gShowPlaylists(playlists=items,options=[])
			action = result[0]
			selected = result[1]
			if selected != -1:
				pId = playlists[selected][1]
				n = self.getCurrentListPosition()
				songId = songs[n-1][1]
				self.gs.playlistAddSong(pId, songId, 0)
		else:
			pass

	def showOptionsPlaylist(self):
		items = [__language__(102),__language__(113),__language__(114),__language__(115),__language__(116)]
		result = gSimplePopup(title='', items=items, width=200)
		if result == 0:
			self.nowPlaying = self.getCurrentListPosition()-1
			self.playSong(self.nowPlaying, offset=0)
		elif result == 1:
			self.removeSongFromList(self.playlist)
			self.listSongs(self.playlist, __language__(3007) + ' (' + self.playlistName + ')')
		elif result == 2: # Save
			if self.playlistId != 0:
				if self.savePlaylist(self.playlistId, self.playlistName) == 0:
					self.message(__language__(3008))
			else:
				self.message('Unsaved playlist. Use \'Save Playlist As\' instead','Problem saving')
		elif result == 3: # Save As
			name = self.getInput(__language__(3009))
			if name != '':
				pId = self.savePlaylist(0, name, '')
				if pId == 0:
					self.message(__language__(3008))
				else:
					self.playlistId = pId
					self.playlistName = name
					self.setStateLabel(__language__(3007) + ' (' + self.playlistName + ')')
			else:
				self.message(__language__(3010), __language__(3011))
		elif result == 4: #Close playlist
			self.closePlaylist()
		else:
			pass

	def removeSongFromList(self, sList, n = -1):
		if n == -1:
			nn = self.getCurrentListPosition()-1
		else:
			nn = n
		sList.pop(nn)

	def getSongIdFromList(self, songs, n = -1):
		if n == -1:
			nn = self.getCurrentListPosition()
		else:
			nn = n
		return songs[nn-1][1]

	def getSongInfoFromListAsListItem(self, songs, n = -1):
		if n == -1:
			nn = self.getCurrentListPosition()
		else:
			nn = n
		listItem = xbmcgui.ListItem('some music')
		listItem.setInfo( type = 'music', infoLabels = { 'title': songs[nn-1][0], 'artist': songs[nn-1][6] } )
		return listItem
	
	def setPlayerLabel(self, msg):
		self.getControl(3001).reset(msg)
		self.getControl(3001).addLabel(msg)

	def message(self, message, title = ''):
		dialog = xbmcgui.Dialog()
		dialog.ok(title, message)
	
	def setStateLabel(self, msg):
		self.getControl(3000).setLabel(msg)

	def playlistHasFocus(self):
		self.setFocus(self.getControl(205))

	def getPopularSongs(self):
		try:
			self.searchResultSongs = self.gs.popularGetSongs(10)
			self.stateList = GrooveClass.STATE_LIST_SONGS
			self.listMenu()
		except:
			self.message(__language__(3012))
			traceback.print_exc()
			pass

	def getPopular(self):
		self.searchText = 'Popular'
		dialog = xbmcgui.DialogProgress()
		dialog.create(__language__(3013), __language__(3014))
		dialog.update(0)
		try:
			self.searchResultSongs = self.gs.popularGetSongs(GrooveClass.SEARCH_LIMIT)
			dialog.update(33, __language__(3015))
			self.searchResultArtists = self.gs.popularGetArtists(GrooveClass.SEARCH_LIMIT)
			dialog.update(66, __language__(3016))
			self.searchResultAlbums = self.gs.popularGetAlbums(GrooveClass.SEARCH_LIMIT)
			dialog.update(100, __language__(3017))
			dialog.close()
			self.playlistHasFocus()
		except:
			dialog.close()
			self.message(__language__(3012))
			traceback.print_exc()
	
	def searchAll(self, text):
		self.searchText = text
		dialog = xbmcgui.DialogProgress()
		dialog.create(__language__(3013), __language__(3018))
		dialog.update(0)
		i = 0
		while i < len(self.listPos):
			self.listPos[i] = 0
			i += 1
		try:
			self.searchResultSongs = self.gs.searchSongs(text, GrooveClass.SEARCH_LIMIT)
			dialog.update(33, __language__(3019))
			self.searchResultArtists = self.gs.searchArtists(text, GrooveClass.SEARCH_LIMIT)
			dialog.update(66, __language__(3020))
			self.searchResultAlbums = self.gs.searchAlbums(text, GrooveClass.SEARCH_LIMIT)
			dialog.update(100, __language__(3021))
			dialog.close()
			self.playlistHasFocus()
		except:
			dialog.close()
			self.message(__language__(3022))
			traceback.print_exc()
	
	def listSearchResults(self, songs, artists, albums, p=0):
		xbmcgui.lock()
		path = os.path.join(os.getcwd(),'resources','skins','DefaultSkin', 'media', 'default-cover.png')
		self.clearList()
		self.setStateLabel('Search results for "' + self.searchText + '"')
		item = xbmcgui.ListItem (label=__language__(3023), label2=str(len(songs)) + ' ' + __language__(3026), thumbnailImage=path)			
		self.addItem(item)
		item = xbmcgui.ListItem (label=__language__(3024), label2=str(len(artists)) + ' ' + __language__(3026), thumbnailImage=path)			
		self.addItem(item)
		item = xbmcgui.ListItem (label=__language__(3025), label2=str(len(albums)) + ' ' + __language__(3026), thumbnailImage=path)			
		self.addItem(item)
		self.setCurrentListPosition(p)
		xbmcgui.unlock()

	def listSongs(self, songs, text='',p=0):
		try:
			#xbmcgui.lock()
			i = 0
			self.clearList()
			self.addItem('..')
			self.setStateLabel(text)
			items = []
			while(i < len(songs)):
				items.append([songs[i][4], songs[i][8]])
				i += 1

			self.getThumbs(items)
			i = 0
			while(i < len(songs)):
				if songs[i][2] == -1:
					durStr = ''
				else:
					durMin = int(songs[i][2]/60.0)
					durSec = int(songs[i][2] - durMin*60)
					if durSec < 10:
						durStr = '(' + str(durMin) + ':0' + str(durSec) + ')'
					else:
						durStr = '(' + str(durMin) + ':' + str(durSec) + ')'
				songId = str(songs[i][1])
				#path = '/home/solver/.xbmc/scripts/My Scripts/grooveshark-for-xbmc/cache/default-cover.png'
				#print songs[i]
				path = self.getThumbPath(items[i])
				l1 = songs[i][0]
				l2 = songs[i][6] + '\n' + songs[i][3]
				item = xbmcgui.ListItem (label=l1,label2=l2, thumbnailImage=path)			
				#item = xbmcgui.ListItem (label=songs[i][6] + ' - "' + songs[i][0] + '" (' + songs[i][3] + ')',label2=durStr, thumbnailImage=path)			
				self.addItem(item)
				i += 1
			self.setCurrentListPosition(p)
		except:
			xbmc.log('GrooveShark Exception (listSongs): ' + str(sys.exc_info()[0]))
			traceback.print_exc()

	def listArtists(self, artists, text='',p=0):
		xbmcgui.lock()
		i = 0
		self.clearList()
		self.addItem('..')
		self.setStateLabel(text)
		path = os.path.join(os.getcwd(),'resources','skins','DefaultSkin', 'media','default-cover.png')
		while(i < len(artists)):
			item = xbmcgui.ListItem (label=artists[i][0], thumbnailImage=path)
			self.addItem(item)
			i += 1
		self.setCurrentListPosition(p)
		xbmcgui.unlock()
		
	def listAlbums(self, albums, text='', withArtist=0, p=0):
		if len(albums) == 0:
			return
		i = 0
		self.clearList()
		self.addItem('..')
		if text == '':
			self.setStateLabel(__language__(3025) + ' ' + __language__(3006) + ' "' + albums[0][0] + '"')
		else:
			self.setStateLabel(text)

		items = []
		while(i < len(albums)):
			items.append([albums[i][3], albums[i][4]])
			i += 1

		self.getThumbs(items)
		i = 0
		while(i < len(albums)):
			path = self.getThumbPath(items[i])
			if withArtist == 0:
				item = xbmcgui.ListItem (label=albums[i][2], thumbnailImage=path)
			else:
				item = xbmcgui.ListItem (label=albums[i][2], label2=albums[i][0], thumbnailImage=path)
			self.addItem(item)
			i += 1
		self.setCurrentListPosition(p)

	def playerChanged(self, event):
		if event == 0: # Stopped
			print 'Player stopped'
			self.showPlayButton()
			
		elif event == 1: # Ended
			self.playNextSong()		
			
		elif event == 2: # Started
			pass
			
		elif event == 3: # Playback paused
			self.showPlayButton()
			
		elif event == 4: # Playback resumed
			self.showPauseButton()

		elif event == 5: # Play next
			pass
			
	def showPlayButton(self):
		return None
		playBtn = self.getControl(2003)
		pauseBtn = self.getControl(2005)
		stopBtn = self.getControl(2002)
		nextBtn = self.getControl(2004)
		pauseBtn.setVisible(False) # Pause button
		playBtn.setVisible(True) # Play button
		playBtn.controlLeft(stopBtn)
		playBtn.controlRight(nextBtn)
		stopBtn.controlRight(playBtn)
		nextBtn.controlLeft(playBtn)

	def showPauseButton(self):
		return None
		playBtn = self.getControl(2003)
		pauseBtn = self.getControl(2005)
		stopBtn = self.getControl(2002)
		nextBtn = self.getControl(2004)
		playBtn.setVisible(False) # Play button
		pauseBtn.setVisible(True) # Pause button
		pauseBtn.controlLeft(stopBtn)
		pauseBtn.controlRight(nextBtn)
		stopBtn.controlRight(pauseBtn)
		nextBtn.controlLeft(pauseBtn)
		pauseBtn.setVisible(True) # Pause button

	def playSong(self, n, offset=0):
		# Missing some sort of fallback mechanism if playback fails. 'playbackStarted' from callback func. from player might come in handy for this
		p = n+offset
		songId = self.playlist[p][1]
		title = self.playlist[p][0]
		albumId = self.playlist[p][4]
		artist = self.playlist[p][6]
		imgUrl = self.playlist[p][9] # Medium image
		self.nowPlaying = p
		listItem = xbmcgui.ListItem('some music')
		#listItem.setInfo( type = 'music', infoLabels = {'title': title, 'artist': artist})
		try:
			item = [albumId, imgUrl]
			items = []
			items.append(item)
			path = self.getThumbPath(item, prefix='m')
			listItem.setInfo( type = 'music', infoLabels = {'title': title, 'artist': artist, 'thumbnailImage': path, 'icon': path})
			self.getThumbs(items, prefix='m')
			url = self.gs.getStreamURL(str(songId))
			if url != "":
				self.setPlayerLabel('Buffering...')

				res = self.player.play(str(url), listItem)
				self.setPlayingNow(self.playlist[p])
				self.setPlayingNext(self.playlist[self.getNextSongNumber()])
				print 'Player says: ' + str(res)
				#self.setPlayerLabel('Now Playing: ' + artist + ' - ' + title)
				self.showPauseButton()
				return 1
			else:
				print 'Didn\'t receive an URL for: ' + str(self.playlist[p])
				return 0
		except:
			xbmc.log('GrooveShark Exception (playSong): ' + str(sys.exc_info()[0]))
			traceback.print_exc()
			self.setPlayerLabel('Playback failed')
			print 'Playback failed'
			self.showPlayButton()
			return 0
			
	def setPlaying(self, song, labelId=0, imgId=0, title=''):
		songId = song[1]
		albumId = song[4]
		title = song[0]
		artist = song[6]
		url = song[9] # Medium image
	
		self.getControl(labelId).reset()
		self.getControl(labelId).addLabel(artist + ' - ' + title)
		item = [albumId, url]
		items = []
		items.append(item)
		#self.getThumbs(items, prefix='m')
		path = self.getThumbPath(item, prefix='m')
		self.getControl(imgId).setImage(path)

	def setPlayingNow(self, song):
		self.setPlaying(song, labelId=3001, imgId=9001, title='Playing Now')
		
	def setPlayingNext(self, song):
		self.setPlaying(song, labelId=4001, imgId=9002, title='Playing Next')
	
	def playNextSong(self):
		# Try to play the next song on the current playlist
		if self.nowPlaying != -1:
			n = self.getNextSongNumber()
			#self.nowPlaying = n
			self.playSong(n, offset=0)
		else:
			self.setPlayerLabel('')

	def getNextSongNumber(self):
		n = len(self.playlist)-1
		if n > 0:
			if (self.nowPlaying + 1) > n:
				return 0
			else:
				return self.nowPlaying + 1
		else:
			return -1

	def playPrevSong(self):
		# Try to play the previous song on the current playlist
		if self.nowPlaying != -1:
			n = len(self.playlist)
			if n > 0:
				if (self.nowPlaying - 1) < 0:
					self.nowPlaying = n-1 #Wrap around
				else:
					self.nowPlaying -= 1
				self.playSong(self.playlist[self.nowPlaying])
			else:
				pass
		else:
			self.setPlayerLabel('')

	def playStop(self):
		# Stop playback
		if self.player.isPlayingAudio():
			self.player.stop()
			self.setPlayerLabel('')
		self.showPlayButton()
					
	def playPause(self):
		if self.player.isPlayingAudio():
			self.player.pause()
			self.showPlayButton()
		else:
			self.player.play()
			self.showPauseButton()
						
	def getInput(self, title, default="", hidden=False):
		ret = ""
	
		keyboard = xbmc.Keyboard(default, title)
		keyboard.setHiddenInput(hidden)
		keyboard.doModal()

		if keyboard.isConfirmed():
			ret = keyboard.getText()

		return ret
	def loginBasic(self):
		self.login(1)

	def login(self, basic = 0):
		#return 0
		username = __settings__.getSetting("username")
		password = __settings__.getSetting("password")
		if self.gs.loggedInStatus() == 1:
			self.gs.logout()
		if (username != "") and (password != ""):
			pDialog = xbmcgui.DialogProgress()
			pDialog.update(0)
			pDialog.create(__language__(3037), __language__(3013))
			try:
				if basic == 1:
					self.userId = self.gs.loginBasic(username, password)
				else:
					self.userId = self.gs.login(username, password)

				if self.userId != 0:
					pDialog.update(0, 'Success')
					xbmc.sleep(500)
					pDialog.close()
				else:
					pDialog.close()
					self.message(__language__(3027))

			except LoginTokensExceededError:
				pDialog.close()
				dialog = xbmcgui.Dialog()
				result = dialog.yesno('Failed to login', 'Exceeded number of allowed authentication tokens.','Try plain text authentication?')
				if result == True:
					self.loginBasic()
				else:
					pass
			except:
				pDialog.close()
				self.message(__language__(3027))
				
		else:
			print 'No login details provided in settings'

	def showPlaylists(self):
		if self.gs.loggedInStatus() != 1:
			self.message(__language__(3028),__language__(3029))
			return None
		dialog = xbmcgui.DialogProgress()
		dialog.update(0)
		dialog.create(__language__(3038), '')		
		try:
			items = []
			playlists = self.gs.userGetPlaylists(limit=150)
			i = 0
			while (i < len(playlists)):
				items.append(playlists[i][0])
				i += 1
			dialog.close()
			result = gShowPlaylists(playlists=items,options=[__language__(110),__language__(111),__language__(112)]) #xbmcgui.Dialog().select("Playlists", items)
			action = result[0]
			n = result[1]
			if action == 0: #Load
				self.playlistId = playlists[n][1]
				self.playlistName = playlists[n][0]
				self.playlist = self.gs.playlistGetSongs(self.playlistId, limit=100)
				self.stateList = GrooveClass.STATE_LIST_PLAYLIST
				self.listMenu()
				self.playlistHasFocus()
			elif action == 1: #Rename
				name = self.getInput(__language__(3030), default=playlists[n][0])
				if name != '':
					if self.gs.playlistRename(playlists[n][1], name) == 0:
						self.message(__language__(3031))
				self.showPlaylists()
			elif action == 2: #Delete
				dialog = xbmcgui.Dialog()
				result = dialog.yesno(__language__(3033),__language__(3032)+':',playlists[n][0])
				if result == True:
					self.gs.playlistDelete(playlists[n][1])
					if self.playlistId == playlists[n][1]:
						self.closePlaylist()
				else:
					pass
				self.showPlaylists()
			
		except:
			dialog.close()
			xbmc.log('GrooveShark Exception (getPlaylists): ' + str(sys.exc_info()[0]))
			traceback.print_exc()
			self.message('Could not get your playlists', 'Error')
			
	def closePlaylist(self):
		self.playlistId = 0
		self.playlistName = 'Unsaved'
		self.playlist = []
		self.nowPlaying = -1
		self.stateList = GrooveClass.STATE_LIST_PLAYLIST
		self.listMenu()
	
	def savePlaylist(self, playlistId, name = '', about = ''):
		pDialog = xbmcgui.DialogProgress()
		pDialog.update(0)
		pDialog.create(__language__(3034), __language__(3013) + '...')
		if playlistId == 0:
			if name != '':
				pId = self.gs.playlistCreate(name, about)
				if pId == 0:
					return 0
		else:
			pId = playlistId
		
		i = 0
		n = len(self.playlist)
		songIds = []
		while i < n:
			songIds.append(self.getSongIdFromList(self.playlist, i))
			i += 1
		try:
			if self.gs.playlistReplace(pId, songIds) == 0:
				pDialog.update(0, __language__(3008))
				xbmc.sleep(1000)
				pDialog.close()
			else:
				pDialog.update(0, __language__(3035))
				xbmc.sleep(1000)
				pDialog.close()
			return pId
		except:
			pDialog.update(0, __language__(3008))
			xbmc.sleep(1000)
			pDialog.close()
			return 0
		
	def listCacheDir(self):
		fileNames = []
		dList = os.listdir(self.cacheDir)
		for entry in dList:
			fileNames.append(entry.split('.')[0])
		return fileNames
		
	def getThumbs(self, items, prefix=''):
		#print 'Songs: ' + str(songs)
		data=None 
		headers={}
		timeout=30		
		fileNames = self.listCacheDir()
		
		n = len(items)
		pDialog = xbmcgui.DialogProgress()
		pDialog.update(1)
		pDialog.create(__language__(3036), __language__(3013))
		try:
			i = 0
			while i < len(items):
				item = items[i]
				#print song
				pDialog.update(int((i*100)/n), __language__(3013))
				i += 1
				songId = prefix + str(item[0])
				if songId in fileNames:
					pass
				else:
					url = item[1]
					if (url != self.defaultArtTinyUrl) and (url != self.defaultArtSmallUrl) and (url != self.defaultArtMediumUrl):
						ext = url.split('/')
						ext = ext[len(ext)-1].split('.')[1]
						thumb = self.downloadFile(url, timeout)
						fileName = songId + '.' + ext
						filePath = os.path.join(self.cacheDir, fileName)
						fp = open(filePath, 'wb')				
						fp.write(thumb)
						fp.close()
						fileNames = self.listCacheDir()
						#print 'url: ' + url
						#print 'Path: ' + filePath
						#print 'ext: ' + ext 
		except:
			pDialog.close()
			traceback.print_exc()
			print 'Could not get all thumbs. Stopped at: ' + str(item)
			
	def downloadFile(self, url, timeout=30):
		req = urllib2.Request(url)
		#req.add_header('Host', 'api.grooveshark.com')
		#req.add_header('Content-type', 'text/json')
		#req.add_header('Content-length', str(len(data)))
		#req.add_data(data)
		response = urllib2.urlopen(req)
		result = response.read()
		response.close()
		return result
	
	def getThumbPath(self, item, prefix=''):
		url = item[1]
		#print 'Img url: ' + url
		songId = prefix + str(item[0])
		ext = url.split('/')
		ext = ext[len(ext)-1].split('.')[1]
		fileName = songId + '.' + ext
		filePath = os.path.join(self.cacheDir, fileName)		
		if os.path.exists(filePath):
			return filePath
		else:
			return os.path.join(os.getcwd(),'resources','skins','DefaultSkin' ,'media', 'default-cover.png')
		

			
#rootDir = os.getcwd()
#print 'RootDir: ' + rootDir

