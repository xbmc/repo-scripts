import xbmc, xbmcgui, xbmcplugin #, xbmcaddon
import sys
import pickle
import os
import traceback
import threading

sys.path.append(os.path.join(os.getcwd().replace(";",""),'resources','lib'))

from GrooveAPI import *
from GroovePlayer import GroovePlayer
from GrooveGUI import *
from operator import itemgetter, attrgetter

__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__version__ = sys.modules[ "__main__" ].__version__
__settings__ = sys.modules[ "__main__" ].__settings__
__language__ = sys.modules[ "__main__" ].__language__
__scriptid__ = sys.modules[ "__main__" ].__scriptid__
__debugging__ = sys.modules["__main__"].__debugging__
__isXbox__ = sys.modules["__main__"].__isXbox__

class GrooveClass(xbmcgui.WindowXML):

	STATE_LIST_EMPTY = 0
	STATE_LIST_SEARCH = 1
	STATE_LIST_SONGS = 2
	STATE_LIST_ARTISTS = 3
	STATE_LIST_ALBUMS = 4
	STATE_LIST_ALBUMS_BY_ARTIST = 5
	STATE_LIST_SONGS_ON_ALBUM = 6
	STATE_LIST_SONGS_ON_ALBUM_FROM_SEARCH = 7
	STATE_LIST_PLAYLIST = 8
	STATE_LIST_SEARCH_PLAYLIST = 9
	STATE_LIST_SONGS_ON_PLAYLIST_FROM_SEARCH = 10
	STATE_LIST_SIMILAR_SONGS = 11
	STATE_LIST_SIMILAR_ARTISTS = 12
	STATE_LIST_SIMILAR = 13
	STATE_LIST_BROWSE_ALBUM_FOR_SONG = 14
	if __isXbox__ == True:
		SEARCH_LIMIT = 25 # To high a number and getting thumbnails takes forever
	else:
		SEARCH_LIMIT = 0

	RADIO_PLAYLIST_LENGTH = 5

	def onInit(self):
		try:
			if self.initialized == True:
				self.listMenu()
		except:
			self.initVars()
			self.loadState()
			try:
				self.gs = GrooveAPI(enableDebug = __debugging__, isXbox = __isXbox__)
			except:
				self.message(__language__(3046), __language__(3011)) #Unable to get new session ID
				xbmc.log('GrooveShark Exception (onInit): ' + str(sys.exc_info()[0]))
				traceback.print_exc()
				self.close()
				return
			self.initialized = True
			self.initPlayer()
			if self.loadState() == False:
				self.getPopularSongs()
			else:
				self.listMenu()

	def __del__(self):
		print 'GooveShark: __del__() called'
		self.saveState()

	def initPlayer(self):
		try:
			self.player = GroovePlayer()
			self.player.setCallBackFunc(self.playerChanged)
		except:
			xbmc.log('GrooveShark Exception (initPlayer): ' + str(sys.exc_info()[0]))
			traceback.print_exc()
		
	def onFocus(self, controlID):
		pass

	def onAction(self, action):
		aId = action.getId()
		if aId == 10:
			#dialog = xbmcgui.Dialog()
			#c = dialog.yesno(__language__(1003), __language__(1004)) #Close grooveshark
			#if c == True:
			if self.getFocusId() != 50:
				self.playlistHasFocus()
			else:
				self.saveState()
				self.close()
		elif aId == 117: # Play
			self.player.play()
		elif aId == 14: # Skip
			self.playNextSong()
		elif aId == 15: # Replay
			self.playPrevSong()
		elif aId == 9:
			self.navigate('back')
		else:
			pass
 
	def onClick(self, control):
		if control == 1006: # Save queue
			protocol = 'plugin://' + __scriptid__ + '/?playSong'
			songList = []
			n = self.xbmcPlaylist.size()
			for i in range(n):
				url = self.xbmcPlaylist[i].getfilename()
				parts = url.split('=')
				if len(parts) == 2:
					if parts[0] == protocol:
						if parts[1] != '':
							songList.append(parts[1])
			if len(songList) > 0:
				self.savePlaylist(songList = songList)
			else:
				self.message(__language__(3045),__language__(3011)) #Didn't find any GrooveShark material in the queue

		if control == 1002:
			self.playlistHasFocus()
			search = Search()
			#text = self.getInput(__language__(1000), "") 
			result = search.getResult()
			if result != None:
				text = result['query']
				self.searchText = text
				self.searchAll(text)
				self.setStateListDown(GrooveClass.STATE_LIST_SEARCH, reset = True, query = text)
		elif control == 1001:
			if __isXbox__ == True:
				pass
			else:
				wId = xbmcgui.getCurrentWindowId()
				print 'wId: ' + str(wId) + ', self: ' + str(self)
				gWin = xbmcgui.Window(wId)
				pWin = xbmcgui.Window(10500)
				self.location[len(self.location)-1]['itemFocused'] = self.getCurrentListPosition() # Make sure we end up at the index when the playlist is close and the __init__ is run again for the class
				pWin.show()
				while xbmcgui.getCurrentWindowId() == 10500: #Music playlist
					xbmc.sleep(100)
					pass
				while xbmcgui.getCurrentWindowId() == 12006:#Visualization
					xbmc.sleep(100)
				if xbmcgui.getCurrentWindowId() != wId:
					gWin.show()

		elif control == 1003:
			self.showPlaylists()
		elif control == 1004:
			self.getPopular()
		elif control == 1005:
			__settings__.openSettings()
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
			self.navigate('select')
		else:
			pass

	def navigate(self, click):
		if click == 'select':
			n = self.getCurrentListPosition()
		elif click == 'back':
			if len(self.location) <= 1:
				return # We're already at top level
			else:
				n = 0
		else:
			print 'navigate() got an unrecognized click'
			return
		item = self.getListItem(n)
		if self.stateList == GrooveClass.STATE_LIST_EMPTY:
			pass
		elif self.stateList == GrooveClass.STATE_LIST_PLAYLIST:
			if n == 0:
				self.setStateListDown(GrooveClass.STATE_LIST_SEARCH, reset = True, query = self.searchText)
			else:
				self.showOptionsPlaylist()
				pass
		elif self.stateList == GrooveClass.STATE_LIST_SEARCH or self.stateList == GrooveClass.STATE_LIST_SIMILAR:
			if n == 0:
				self.setStateListDown(GrooveClass.STATE_LIST_SONGS)
			elif n == 1:
				self.setStateListDown(GrooveClass.STATE_LIST_ARTISTS)
			elif n == 2:
				self.setStateListDown(GrooveClass.STATE_LIST_ALBUMS)
			elif n == 3:
				self.setStateListDown(GrooveClass.STATE_LIST_SEARCH_PLAYLIST)
			else:
				pass
		elif self.stateList == GrooveClass.STATE_LIST_SONGS:
			if n == 0:
				self.setStateListUp(GrooveClass.STATE_LIST_SEARCH)
			else:
				self.showOptionsSearch(self.searchResultSongs, withBrowse = True)
		elif self.stateList == GrooveClass.STATE_LIST_ARTISTS:
			if n == 0:
				self.setStateListUp(GrooveClass.STATE_LIST_SEARCH)
			else:
				#if self.settings[2] == True: # Get verified albums. Disabled in API so skip it for now
					#self.albums = self.gs.artistGetVerifiedAlbums(self.searchResultArtists[n-1][1],GrooveClass.SEARCH_LIMIT)
				#	self.albums = self.gs.artistGetAlbums(self.searchResultArtists[n-1][1],GrooveClass.SEARCH_LIMIT)
				#else: # Get all albums
				b = busy()
				self.albums = self.gs.artistGetAlbums(self.searchResultArtists[n-1][1],GrooveClass.SEARCH_LIMIT)
				self.setStateListDown(GrooveClass.STATE_LIST_ALBUMS_BY_ARTIST)
				b.close()
				del b
		elif self.stateList == GrooveClass.STATE_LIST_ALBUMS:
			if n == 0:
				self.setStateListUp(GrooveClass.STATE_LIST_SEARCH)
			else:
				b = busy()
				self.songs = self.gs.albumGetSongs(self.searchResultAlbums[n-1][3],GrooveClass.SEARCH_LIMIT)
				self.setStateListDown(GrooveClass.STATE_LIST_SONGS_ON_ALBUM_FROM_SEARCH)
				b.close()
				del b
		elif self.stateList == GrooveClass.STATE_LIST_SEARCH_PLAYLIST:
			if n == 0:
				self.setStateListUp(GrooveClass.STATE_LIST_SEARCH)
			else:
				pass
				b = busy()
				self.songs = self.gs.playlistGetSongs(self.searchResultPlaylists[n-1][0])
				self.setStateListDown(GrooveClass.STATE_LIST_SONGS_ON_PLAYLIST_FROM_SEARCH)
				b.close()
				del b
		elif self.stateList == GrooveClass.STATE_LIST_SONGS_ON_ALBUM_FROM_SEARCH:
			if n == 0:
				self.setStateListUp(GrooveClass.STATE_LIST_ALBUMS)
			else:
				self.showOptionsSearch(self.songs)
		elif self.stateList == GrooveClass.STATE_LIST_ALBUMS_BY_ARTIST:
			if n == 0:
				self.setStateListUp(GrooveClass.STATE_LIST_ARTISTS)
			else:
				b = busy()
				self.songs = self.gs.albumGetSongs(self.albums[n-1][3],GrooveClass.SEARCH_LIMIT)
				self.setStateListDown(GrooveClass.STATE_LIST_SONGS_ON_ALBUM)
				b.close()
				del b
		elif self.stateList == GrooveClass.STATE_LIST_SONGS_ON_ALBUM:
			if n == 0:
				self.setStateListUp(GrooveClass.STATE_LIST_ALBUMS_BY_ARTIST)
			else:
				self.showOptionsSearch(self.songs)
		elif self.stateList == GrooveClass.STATE_LIST_SONGS_ON_PLAYLIST_FROM_SEARCH:
			if n == 0:
				self.setStateListUp(GrooveClass.STATE_LIST_SEARCH_PLAYLIST)
			else:
				self.showOptionsSearch(self.songs)
#		elif self.stateList == GrooveClass.STATE_LIST_SIMILAR:
#			if n == 0:
#				self.setStateListUp()
#			elif n == 1:
#				self.setStateListDown(GrooveClass.STATE_LIST_SIMILAR_SONGS)
#			elif n == 2:
#				self.setStateListDown(GrooveClass.STATE_LIST_SIMILAR_ARTISTS)
		elif self.stateList == GrooveClass.STATE_LIST_SIMILAR_SONGS:
			if n == 0:
				self.setStateListUp()
			else:
				self.showOptionsSearch(self.songsSimilar)
		elif self.stateList == GrooveClass.STATE_LIST_SIMILAR_ARTISTS:
			if n == 0:
				self.setStateListUp(GrooveClass.STATE_LIST_SIMILAR)
			else:
				b = busy()
				self.songs = self.gs.artistGetSongs(self.albums[n-1][7],GrooveClass.SEARCH_LIMIT)
				self.setStateListDown(GrooveClass.STATE_LIST_SIMILAR_SONGS)
				b.close()
				del b
		elif self.stateList == GrooveClass.STATE_LIST_BROWSE_ALBUM_FOR_SONG:
			if n == 0:
				self.setStateListUp()
			else:
				self.showOptionsSearch(self.songs)

	def initVars(self):
		self.stateList = GrooveClass.STATE_LIST_EMPTY
		self.searchResultSongs = []
		self.searchResultAlbums = []
		self.searchResultArtists = []
		self.searchResultPlaylists = []
		self.songs = []
		self.artists = []
		self.albums = []
		self.playlist = []
		self.similarSongs = []
		self.similarArtists = []
		self.playlistId = 0
		self.playlistName = 'Unsaved'
		self.searchText = ""
		self.rootDir = os.getcwd()
		self.xbmcPlaylist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
		self.location = []
		if __isXbox__ == True:
			self.dataDir = 'script_data'
		else:
			self.dataDir = 'addon_data'
		self.cacheDir = os.path.join('special://profile/', self.dataDir, __scriptid__)
		if os.path.exists(self.cacheDir) == False:
			os.mkdir(self.cacheDir)		
		self.cacheDir = os.path.join('special://profile/', self.dataDir, __scriptid__, 'cache')
		if os.path.exists(self.cacheDir) == False:
			os.mkdir(self.cacheDir)
		self.confDir = os.path.join('special://profile/', self.dataDir, __scriptid__)
		self.nowPlaying = -1
		self.defaultArtTinyUrl = 'http://beta.grooveshark.com/webincludes/img/defaultart/album/tdefault.png'
		self.defaultArtSmallUrl = 'http://beta.grooveshark.com/webincludes/img/defaultart/album/sdefault.png'
		self.defaultArtMediumUrl = 'http://beta.grooveshark.com/webincludes/img/defaultart/album/mdefault.png'
		self.itemsPrPage = 10
		self.listPos = [0]
		for i in range(GrooveClass.STATE_LIST_BROWSE_ALBUM_FOR_SONG):
			self.listPos.append(0)

	def saveState(self):			
		try:
			print 'GrooveShark: Saving state'
			self.location[len(self.location)-1]['itemFocused'] = self.getCurrentListPosition()
			dir = os.path.join(self.confDir, 'state')
			# Create the 'state' directory if it doesn't exist.
			if not os.path.exists(dir):
				os.mkdir(dir)
			path = os.path.join(dir, 'state.txt')
			f = open(path, 'wb')
			pickle.dump(self.getState(), f, protocol=pickle.HIGHEST_PROTOCOL)
			f.close()
		except IOError, e:
			print 'There was an error while saving the state pickle (%s)' % e
			pass
		except:
			print "An unknown error occured during save state: " + str(sys.exc_info()[0])
			traceback.print_exc()
			pass

	def loadState(self):

		path = os.path.join(self.confDir, 'state', 'state.txt')
		try:
			f = open(path, 'rb')
			self.stateList,\
			self.searchResultSongs,\
			self.searchResultAlbums,\
			self.searchResultArtists,\
			self.searchResultPlaylists,\
			self.songs,\
			self.artists,\
			self.albums,\
			self.playlist,\
			self.similarSongs,\
			self.similarArtists,\
			self.playlistId,\
			self.playlistName,\
			self.searchText,\
			self.rootDir,\
			self.location = pickle.load(f)
			f.close()
			return True
		except:
			print "An unknown error occured reloading state: " + str(sys.exc_info()[0])
			traceback.print_exc()
			return False
			pass		

	def getState(self):
		# Use this instead of __getstate__() for pickling
		return (self.stateList,\
		self.searchResultSongs,\
		self.searchResultAlbums,\
		self.searchResultArtists,\
		self.searchResultPlaylists,\
		self.songs,\
		self.artists,\
		self.albums,\
		self.playlist,\
		self.similarSongs,\
		self.similarArtists,\
		self.playlistId,\
		self.playlistName,\
		self.searchText,\
		self.rootDir,\
		self.location)

	def listMenu(self):
		n = self.getCurrentListPosition()
		if self.stateList == GrooveClass.STATE_LIST_EMPTY:
			pass #listpopular

		elif self.stateList == GrooveClass.STATE_LIST_PLAYLIST:
			self.listSongs(self.playlist)
		
		elif self.stateList == GrooveClass.STATE_LIST_SEARCH or self.stateList == GrooveClass.STATE_LIST_SIMILAR:
			self.listSearchResults(self.searchResultSongs, self.searchResultArtists, self.searchResultAlbums, self.searchResultPlaylists)	

		elif self.stateList == GrooveClass.STATE_LIST_SONGS:
			self.listSongs(self.searchResultSongs)

		elif self.stateList == GrooveClass.STATE_LIST_ARTISTS:
			self.listArtists(self.searchResultArtists)
				
		elif self.stateList == GrooveClass.STATE_LIST_ALBUMS:
			self.listAlbums(self.searchResultAlbums, withArtist=1)

		elif self.stateList == GrooveClass.STATE_LIST_SEARCH_PLAYLIST:
			self.listPlaylists(self.searchResultPlaylists)

		elif self.stateList == GrooveClass.STATE_LIST_SONGS_ON_PLAYLIST_FROM_SEARCH:
			self.listSongs(self.songs)

		elif self.stateList == GrooveClass.STATE_LIST_SONGS_ON_ALBUM_FROM_SEARCH:
			self.listSongs(self.songs)

		elif self.stateList == GrooveClass.STATE_LIST_ALBUMS_BY_ARTIST:
			self.listAlbums(self.albums)

		elif self.stateList == GrooveClass.STATE_LIST_SONGS_ON_ALBUM:
			self.listSongs(self.songs)

		elif self.stateList == GrooveClass.STATE_LIST_SIMILAR_SONGS:
			self.listSongs(self.similarArtists)

		elif self.stateList == GrooveClass.STATE_LIST_SIMILAR_ARTISTS:
			self.listSongs(self.songs)

		elif self.stateList == GrooveClass.STATE_LIST_BROWSE_ALBUM_FOR_SONG:
			self.listSongs(self.songs)

		else:
			pass
		#Construct the location label
		location = ''
		for i in range(len(self.location)):
			if self.location[i]['query'] != '':
				query = '(' + self.truncateText(self.location[i]['query'], 15) + ')'
			else:
				query = ''
			if i == 0:
				location = self.location[0]['folderName'] + ' ' + query
			else:
				if self.location[i]['truncate'] == True:
					folderName = self.truncateText(self.location[i]['folderName'],15)
				else:
					folderName = self.location[i]['folderName']
				location += ' > ' + folderName + ' ' + query
		self.setStateLabel(location)
		self.playlistHasFocus()

	def setStateListDown(self, state, query = '', reset = False, folderName = '', truncate = True):
		print 'Down, stateList: ' + str(self.stateList)
		print 'Down, New state: ' + str(state)
		self.prevState = self.stateList
		self.listPos[self.stateList] = self.getCurrentListPosition()
		self.stateList = state
		if reset == True:
			self.location = []
		if len(self.location) > 0:
			self.location[len(self.location)-1]['itemFocused'] = self.getCurrentListPosition()
		if folderName == '':
			folder = self.getStateName(state)
		else:
			folder = folderName
		self.location.append({'folderId': state, 'folderName':folder, 'itemFocused': 0, 'query':query, 'truncate':truncate})
		self.listMenu()

	def setStateListUp(self, state = -1):
		print 'Up, stateList: ' + str(self.stateList)
		print 'Up, New state: ' + str(state)
		self.listPos[self.stateList] = 0		
		if state == -1:
			self.stateList = self.prevState
		else:
			self.stateList = state
		if len(self.location) > 0:
			self.location.pop(len(self.location)-1)
		self.listMenu()

	def getStateName(self, state):
		n = self.getCurrentListPosition()
		if state == GrooveClass.STATE_LIST_EMPTY:
			name = 'Empty' #Should not enter here
		elif state == GrooveClass.STATE_LIST_SEARCH:
			name = __language__(106) #Search

		elif state == GrooveClass.STATE_LIST_SONGS:
			name = __language__(3023) #Songs

		elif state == GrooveClass.STATE_LIST_ARTISTS:
			name = __language__(3024) #Artists

		elif state == GrooveClass.STATE_LIST_ALBUMS:
			name = __language__(3025) #Albums

		elif state == GrooveClass.STATE_LIST_ALBUMS_BY_ARTIST:
			name = self.searchResultArtists[n-1][0] # Name of the artist

		elif state == GrooveClass.STATE_LIST_SONGS_ON_ALBUM:
			name = self.albums[n-1][2] # Name of the album

		elif state == GrooveClass.STATE_LIST_SONGS_ON_ALBUM_FROM_SEARCH:
			name = self.searchResultAlbums[n-1][2] # Name of the album

		elif state == GrooveClass.STATE_LIST_PLAYLIST:
			name = __language__(3039) + ' > ' + self.playlistName #Your playlists

		elif state == GrooveClass.STATE_LIST_SEARCH_PLAYLIST:
			name = __language__(1001) #Playlists

		elif state == GrooveClass.STATE_LIST_SONGS_ON_PLAYLIST_FROM_SEARCH:
			name = self.searchResultPlaylists[n-1][1] #Playlist name

		elif state == GrooveClass.STATE_LIST_SIMILAR_SONGS:
			name = 'SIMILAR_SONGS' #Not used yet

		elif state == GrooveClass.STATE_LIST_SIMILAR_ARTISTS:
			name = 'SIMILAR_ARTISTS' #Not used yet

		elif state == GrooveClass.STATE_LIST_SIMILAR:
			name = __language__(3040) #Similar

		elif state == GrooveClass.STATE_LIST_BROWSE_ALBUM_FOR_SONG:
			name = self.searchResultSongs[n-1][3] + ' ' + __language__(3006) + ' ' + self.searchResultSongs[n-1][6] #Album by artist

		else:
			name = '*unknown name*'

		return name
		
	def truncateText(self, text, n):
		if len(text) > n:
			return text[0:n-3] + '...'
		else:
			return text

	# Radio is not stable yet
	def showOptionsRadioPlaylist(self, songs):
		items = [__language__(102),'More songs like this','Fewer songs like this', 'Turn off radio'] #FIXME
		result = gSimplePopup(title='Radio', items=items, width=200)

		if result == 0: #Play
			n = self.getCurrentListPosition()
			pass
		elif result == 1: #Rate as good
			pass
		elif result == 2: #Rate as bad
			pass
		elif result == 3: #Turn off radio
			pass
		else:
			pass

	def showOptionsRadioSearch(self, songs):
		items = ['Add song','Add all songs','Add artist','Turn off radio'] #FIXME
		result = gSimplePopup(title='Radio', items=items, width=200)

		if result == 0: #Play
			n = self.getCurrentListPosition()
			pass
		elif result == 1: #Rate as good
			pass
		elif result == 2: #Rate as bad
			pass
		elif result == 3: #Turn off radio
			pass
		else:
			pass

	def showOptionsSearch(self, songs, withBrowse = False):
		items = [__language__(102),__language__(101),__language__(103),__language__(104), __language__(119)]
		if withBrowse == True:
			items.append(__language__(120)) #Browse this songs album
		result = gSimplePopup(title='', items=items, width=200)

		if result == 1: #Queue
			n = self.getCurrentListPosition()-1
			#self.playlist.append(songs[n-1])
			self.queueSong(songs[n])

		elif result == 0: #Play
			n = self.getCurrentListPosition()-1
			#self.playlist = songs
			#self.playSong(n, offset=-1)
			#Playlist.PlayOffset
			self.playSongs(songs, n)

		elif result == 2: #Queue all
			#if __isXbox__ == True:
			#	l = len(songs)
			#	for n in range(0, l):
			#		self.playlist.append(songs[n])
			#else:
			self.queueSongs(songs)
				
		elif result == 3: #Add to playlist
			items = []
			b = busy()
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
			b.close()
			del b
		elif result == 4: #Similar
			b = busy()
			try:
				self.getSimilar(songs)
				b.close()
				del b
			except:
				traceback.print_exc()
				b.close()
				del b
				self.message(__language__(3047), __language__(3011)) #Could not get similar items

		elif result == 5: #Browse
			b = busy()
			n = self.getCurrentListPosition()
			try:
				self.songs = self.gs.albumGetSongs(self.searchResultSongs[n-1][4],GrooveClass.SEARCH_LIMIT)
				self.setStateListDown(GrooveClass.STATE_LIST_BROWSE_ALBUM_FOR_SONG, truncate = False)
				b.close()
				del b
			except:
				traceback.print_exc()
				b.close()
				del b
		else:
			pass

	def showOptionsPlaylist(self):
		items = [__language__(102),__language__(101),__language__(103),__language__(113),__language__(114),__language__(115)]
		if __isXbox__:
			items.append(__language__(116))
		result = gSimplePopup(title='', items=items, width=200)
		n = self.getCurrentListPosition()-1
		if result == 0: #Play
			self.playSongs(self.playlist, n)
			#self.nowPlaying = self.getCurrentListPosition()-1
			#self.playSong(self.nowPlaying, offset=0)

		if result == 1: #Queue
			#self.playlist.append(songs[n-1])
			self.queueSong(self.playlist[n])

		elif result == 2: #Queue all
			#if __isXbox__ == True:
			#	l = len(songs)
			#	for n in range(0, l):
			#		self.playlist.append(songs[n])
			#else:
			self.queueSongs(self.playlist)

		elif result == 3: #Remove
			self.removeSongFromList(self.playlist)
			self.listMenu()

		elif result == 4: # Save
			if self.playlistId != 0:
				self.savePlaylist(playlistId = self.playlistId, name = self.playlistName)
			else:
				self.savePlaylist()

		elif result == 5: # Save As
			self.savePlaylist()

		elif result == 6: #Close playlist
			self.closePlaylist()
		else:
			pass

	def playSongs(self, songs, n):
		self.xbmcPlaylist.clear()
		xbmc.Player().stop()
		self.queueSongs(songs)
		self.playSong(n)

	def queueSong(self, song, i = -1):
		if __isXbox__ == True: #FIXME
			pass
		else:
			if i < 0:
				n = self.xbmcPlaylist.size()
			else:
				n = i
			songId = song[1]
			title = song[0]
			albumId = song[4]
			artist = song[6]
			album = song[3]
			duration = song[2]
			imgUrl = song[9] # Medium image
			url = 'plugin://%s/?playSong=%s' % (__scriptid__, songId) # Adding plugin:// to the url makes xbmc call the script to resolve the real url
			listItem = xbmcgui.ListItem('music', thumbnailImage=imgUrl, iconImage=imgUrl)
			listItem.setProperty( 'Music', "true" )
			listItem.setProperty('mimetype', 'audio/mpeg')
			listItem.setProperty('IsPlayable', 'true') # Tell XBMC that it is playable and not a folder
			listItem.setInfo( type = 'Music', infoLabels = { 'title': title, 'artist': artist, 'album': album, 'duration': duration} )
			self.xbmcPlaylist.add(url, listitem=listItem, index = n)			

	def queueSongs(self, songs, queueFrom = -1):
		if queueFrom < 0:
			n = self.xbmcPlaylist.size()
		else:
			n = queueFrom			
		for i in range(len(songs)):
			self.queueSong(songs[i], i = i + n)

	def getSimilar(self, songs):
		self.searchText = 'Similar'
		n = self.getCurrentListPosition()
		songId = songs[n-1][1]
		artistId = songs[n-1][7]
		artistName = songs[n-1][6]
		b = busy()
		try:
			self.searchResultSongs = self.getSimilarSongs(songId)		
			b.setProgress(25)
			self.searchResultArtists = self.getSimilarArtists(artistId)
			b.setProgress(50)
			self.searchResultAlbums = self.gs.artistGetAlbums(artistId, GrooveClass.SEARCH_LIMIT)
			b.setProgress(75)
			self.searchResultPlaylists = self.gs.searchPlaylists(artistName, GrooveClass.SEARCH_LIMIT)
			b.setProgress(100)
			xbmc.sleep(500)
			self.setStateListDown(GrooveClass.STATE_LIST_SIMILAR, reset = True, query = artistName)
			b.close()
			del b
		except:
			b.close()
			del b #Could not get similar items
			self.message(__language__(3047),__language__(3011))
			traceback.print_exc()

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

	def getSimilarSongs(self, songId):
		try:
			return self.gs.songGetSimilar(songId, GrooveClass.SEARCH_LIMIT)
		except:
			traceback.print_exc()
			pass

	def getSimilarArtists(self, artistId):
		try:
			return self.gs.artistGetSimilar(artistId, GrooveClass.SEARCH_LIMIT)
		except:
			traceback.print_exc()
			pass

	def getPopularSongs(self):
		b = busy()
		try:
			self.searchResultSongs = self.gs.popularGetSongs(200)
			self.setStateListDown(GrooveClass.STATE_LIST_SEARCH, reset = True, folderName = __language__(3041)) # Make sure we have a top folder
			self.setStateListDown(GrooveClass.STATE_LIST_SONGS) # ...and change to popular songs
			b.close()
			del b
		except:
			b.close()
			del b
			self.message(__language__(3012), __language__(3011))
			traceback.print_exc()
			pass

	def getPopular(self):
		b = busy()
		try:
			self.searchResultSongs = self.gs.popularGetSongs(GrooveClass.SEARCH_LIMIT)
			b.setProgress(33)
			self.searchResultArtists = self.gs.popularGetArtists(GrooveClass.SEARCH_LIMIT)
			b.setProgress(66)
			self.searchResultAlbums = self.gs.popularGetAlbums(GrooveClass.SEARCH_LIMIT)
			b.setProgress(100)
			self.setStateListDown(GrooveClass.STATE_LIST_SEARCH, reset = True, folderName = __language__(3041))
			b.close()
			del b
			self.playlistHasFocus()
		except:
			b.close()
			del b
			self.message(__language__(3012))
			traceback.print_exc()
	
	def searchAll(self, text):
		self.searchText = text
		b = busy()
		try:
			self.searchResultSongs = self.gs.searchSongs(text, GrooveClass.SEARCH_LIMIT)
			b.setProgress(25)
			self.searchResultArtists = self.gs.searchArtists(text, GrooveClass.SEARCH_LIMIT)
			b.setProgress(50)
			self.searchResultAlbums = self.gs.searchAlbums(text, GrooveClass.SEARCH_LIMIT)
			b.setProgress(75)
			self.searchResultPlaylists = self.gs.searchPlaylists(text, GrooveClass.SEARCH_LIMIT)
			b.setProgress(100)
			xbmc.sleep(500)
			b.close()
			del b
			self.playlistHasFocus()
		except:
			b.close()
			del b
			self.message(__language__(3022), __language__(3011))
			traceback.print_exc()
	
	def listSearchResults(self, songs, artists, albums, playlists):
		self.getControl(300011).setVisible(False)
		xbmcgui.lock()
		path = os.path.join(os.getcwd(),'resources','skins','DefaultSkin', 'media', 'default-cover.png')
		self.clearList()
		item = xbmcgui.ListItem (label=__language__(3023), label2=str(len(songs)) + ' ' + __language__(3026), thumbnailImage=path)			
		self.addItem(item)
		item = xbmcgui.ListItem (label=__language__(3024), label2=str(len(artists)) + ' ' + __language__(3026), thumbnailImage=path)			
		self.addItem(item)
		item = xbmcgui.ListItem (label=__language__(3025), label2=str(len(albums)) + ' ' + __language__(3026), thumbnailImage=path)			
		self.addItem(item)
		item = xbmcgui.ListItem (label=__language__(3042), label2=str(len(playlists)) + ' ' + __language__(3026), thumbnailImage=path) #FIXME
		self.addItem(item)
		p = self.getPositionForLocation()
		self.setCurrentListPosition(p)
		xbmcgui.unlock()

	def listSimilar(self, songs, artists):
		xbmcgui.lock()
		path = os.path.join(os.getcwd(),'resources','skins','DefaultSkin', 'media', 'default-cover.png')
		self.clearList()
		item = xbmcgui.ListItem (label='..')			
		self.addItem(item)
		item = xbmcgui.ListItem (label=__language__(3023), label2=str(len(songs)) + ' ' + __language__(3026), thumbnailImage=path)			
		self.addItem(item)
		item = xbmcgui.ListItem (label=__language__(3024), label2=str(len(artists)) + ' ' + __language__(3026), thumbnailImage=path)			
		self.addItem(item)
		p = self.getPositionForLocation()
		self.setCurrentListPosition(p)
		xbmcgui.unlock()

	def listSongs(self, songs):
		try:
			self.getControl(300011).setVisible(True)
			i = 0
			self.clearList()
			self.addItem('..')
			items = []
			while(i < len(songs)):
				items.append([songs[i][4], songs[i][8]])
				i += 1

			if __isXbox__ == True:
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
				if __isXbox__ == True:
					path = self.getThumbPath(items[i])
				else:
					path = songs[i][8]
				l1 = songs[i][0]
				l2 = songs[i][6] + '\n' + songs[i][3]
				item = xbmcgui.ListItem (label=l1,label2=l2, thumbnailImage=path, iconImage=path)			
				self.addItem(item)
				i += 1
			p = self.getPositionForLocation()
			self.setCurrentListPosition(p)
		except:
			xbmc.log('GrooveShark Exception (listSongs): ' + str(sys.exc_info()[0]))
			traceback.print_exc()

	def listArtists(self, artists):
		self.getControl(300011).setVisible(False)
		xbmcgui.lock()
		i = 0
		self.clearList()
		self.addItem('..')
		path = os.path.join(os.getcwd(),'resources','skins','DefaultSkin', 'media','default-cover.png')
		while(i < len(artists)):
			item = xbmcgui.ListItem (label=artists[i][0], thumbnailImage=path)
			self.addItem(item)
			i += 1
		p = self.getPositionForLocation()
		self.setCurrentListPosition(p)
		xbmcgui.unlock()
		
	def listAlbums(self, albums, withArtist=0):
		self.clearList()
		self.addItem('..')
		self.getControl(300011).setVisible(False)
		if len(albums) == 0:
			return
		i = 0
		items = []
		while(i < len(albums)):
			items.append([albums[i][3], albums[i][4]])
			i += 1
		if __isXbox__ == True:
			self.getThumbs(items)
		i = 0
		while(i < len(albums)):
			if __isXbox__ == True:
				path = self.getThumbPath(items[i])
			else:
				path = albums[i][4]
			if withArtist == 0:
				item = xbmcgui.ListItem (label=albums[i][2], thumbnailImage=path, iconImage=path)
			else:
				item = xbmcgui.ListItem (label=albums[i][2], label2=albums[i][0], thumbnailImage=path, iconImage=path)
			self.addItem(item)
			i += 1
		p = self.getPositionForLocation()
		self.setCurrentListPosition(p)

	def listPlaylists(self, playlists):
		self.getControl(300011).setVisible(False)
		xbmcgui.lock()
		i = 0
		self.clearList()
		self.addItem('..')
		path = os.path.join(os.getcwd(),'resources','skins','DefaultSkin', 'media','default-cover.png')
		while(i < len(playlists)):
			item = xbmcgui.ListItem (label=playlists[i][1], label2=playlists[i][2], thumbnailImage=path)
			self.addItem(item)
			i += 1
		p = self.getPositionForLocation()
		self.setCurrentListPosition(p)
		xbmcgui.unlock()

	def getPositionForLocation(self):
		if len(self.location) > 0:
			return self.location[len(self.location)-1]['itemFocused']
		else:
			return 0

	def playerChanged(self, event):
		if event == 0: # Stopped
			pass
			
		elif event == 1: # Ended
			self.playNextSong()		
			
		elif event == 2: # Started
			if __isXbox__ == True:
				pass
			else:
				if self.xbmcPlaylist.size() > 1:
					# FIXME: Some code for updating the cover of the next playing
					pass
			pass
			
		elif event == 3: # Playback paused
			if __isXbox__ == True:
				pass
			
		elif event == 4: # Playback resumed
			if __isXbox__ == True:
				pass

		elif event == 5: # Play next
			pass
			
	def newRadioPlaylist(self, createFromNumber = 0):
		if createFromNumber == 0:
			self.playlist = []
			for i in range(GrooveClass.RADIO_PLAYLIST_LENGTH):
				self.playlist.append(self.gs.radioGetNextSong()[0])
		else:
			for i in range(createFromNumber):
				self.playlist.pop(0)
				self.playlist.append(self.gs.radioGetNextSong()[0])

	def playSong(self, n, offset=0):
		# Missing some sort of fallback mechanism if playback fails. 'playbackStarted' from callback func. from player might come in handy for this
		p = n+offset		
		#if self.gs.radioTurnedOn() == 1:
		#	self.newRadioPlaylist(createFromNumber = p)
		#	p = 0
		#	if self.stateList == GrooveClass.STATE_LIST_PLAYLIST:
		#		self.listMenu()
		if __isXbox__ == False:
			# Using xbmc.Player().PlaySelected(n) locks up the script. So use this workaround
			xbmc.Player().stop()
			xbmc.executebuiltin('XBMC.Playlist.PlayOffset(music,' + str(n) + ')')
			return
		songId = self.playlist[p][1]
		title = self.playlist[p][0]
		albumId = self.playlist[p][4]
		artist = self.playlist[p][6]
		imgUrl = self.playlist[p][9] # Medium image
		self.nowPlaying = p
		try:
			path = imgUrl
			listItem = xbmcgui.ListItem('music', thumbnailImage=imgUrl, iconImage=imgUrl)
			listItem.setInfo( type = 'music', infoLabels = { 'title': title, 'artist': artist } )
			url = self.gs.getStreamURL(str(songId))
			if url != "":
				self.setPlayerLabel('Buffering...')
				res = self.player.play(str(url), listItem)
				self.setPlayingNow(self.playlist[p])
				self.setPlayingNext(self.playlist[self.getNextSongNumber()])
				print 'Player says: ' + str(res)
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
		path = url
		self.getControl(imgId).setImage(path)

	def setPlayingNow(self, song):
		self.setPlaying(song, labelId=3001, imgId=9001, title='Playing Now')
		
	def setPlayingNext(self, song):
		self.setPlaying(song, labelId=4001, imgId=9002, title='Playing Next')
	
	def playNextSong(self):
		if __isXbox__ == True:
			# Try to play the next song on the current playlist
			if self.nowPlaying != -1:
				n = self.getNextSongNumber()
				#self.nowPlaying = n
				self.playSong(n, offset=0)
			else:
				self.setPlayerLabel('')
		else:
			pass

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
		if __isXbox__ == True:
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
		else:
			xbmc.Player().playnext()

	def playStop(self):
		# Stop playback
		if self.player.isPlayingAudio():
			self.player.stop()
			#self.setPlayerLabel('')

		#self.showPlayButton()
					
	def playPause(self):
		if self.player.isPlayingAudio():
			self.player.pause()
		else:
			self.player.play()

						
	def getInput(self, title, default="", hidden=False):
		ret = ""
	
		keyboard = xbmc.Keyboard(default, title)
		#keyboard = GrooveKeyboard(default, title)
		keyboard.setHiddenInput(hidden)
		g = getTextThread(keyboard, self.rootDir)
		g.start()
		keyboard.doModal()
		g.closeThread()
		if keyboard.isConfirmed():
			ret = keyboard.getText()

		return ret
	def loginBasic(self):
		return self.login(1)

	def login(self, basic = 0):
		#return 0
		username = __settings__.getSetting("username")
		password = __settings__.getSetting("password")
		if self.gs.loggedInStatus() == 1:
			self.gs.logout()
		if (username != "") and (password != ""):
			b = busy()
			try:
				if basic == 1:
					self.userId = self.gs.loginBasic(username, password)
				else:
					self.userId = self.gs.login(username, password)

				if self.userId != 0:
					b.close()
					del b
					return 1
				else:
					b.close()
					del b
					self.message(__language__(3027), __language__(3011))
					return -1

			except LoginTokensExceededError:
				b.close()
				del b
				dialog = xbmcgui.Dialog()
				result = dialog.yesno('Failed to login', 'Exceeded number of allowed authentication tokens.','Try plain text authentication?')
				traceback.print_exc()
				if result == True:
					self.loginBasic()
				else:
					pass
			except:
				b.close()
				del b
				traceback.print_exc()	
				return -1
				
		else:
			return -2

	def showPlaylists(self):
		if self.gs.loggedInStatus() != 1:
			result = self.loginBasic()
			if result == 1:
				pass
			elif result == -1:
				return None
			elif result == -2:
				self.message(__language__(3028),__language__(3029))
				return None
			else:
				return None
		b = busy()
		try:
			items = []
			playlists = self.gs.userGetPlaylists(limit=1000)
			i = 0
			while (i < len(playlists)):
				items.append(playlists[i][0])
				i += 1
			b.close()
			del b
			result = gShowPlaylists(playlists=items,options=[__language__(110),__language__(111),__language__(112)])
			action = result[0]
			n = result[1]
			if action == 0: #Load
				b = busy()
				try:
					self.playlistId = playlists[n][1]
					self.playlistName = playlists[n][0]
					self.playlist = self.gs.playlistGetSongs(self.playlistId, limit=100)
					self.setStateListDown(GrooveClass.STATE_LIST_PLAYLIST, reset = True)
					self.playlistHasFocus()
					b.close()
					del b
				except:
					b.close()
					del b
					traceback.print_exc()
					self.message(__language__(3043),__language__(3011)) #Could not get the playlist
			elif action == 1: #Rename
				name = self.getInput(__language__(3030), default=playlists[n][0])
				b = busy()
				try:
					if name != '':
						if self.gs.playlistRename(playlists[n][1], name) == 0:
							self.message(__language__(3031), __language__(3011))
					self.showPlaylists()
					b.close()
					del b
				except:
					b.close()
					del b
					traceback.print_exc()
					self.message(__language__(3031), __language__(3011)) #Could not rename the playlist

			elif action == 2: #Delete
				dialog = xbmcgui.Dialog()
				result = dialog.yesno(__language__(3033),__language__(3032)+':',playlists[n][0])
				b = busy()
				try:
					if result == True:
						self.gs.playlistDelete(playlists[n][1])
						if self.playlistId == playlists[n][1]:
							self.closePlaylist()
					else:
						pass
					self.showPlaylists()
					b.close()
					del b
				except:
					b.close()
					del b
					traceback.print_exc()
					self.message(__language__(3044), __language__(3011)) #Could not delete the playlist

			elif action == 3: #Radio
				playlistId = playlists[n][1]
				playlistName = playlists[n][0]
				playlist = self.gs.playlistGetSongs(playlistId, limit=100)
				seedArtists = []
				for i in range(len(playlist)):
					seedArtists.append(playlist[i][7])
				print 'Before radioStart'
				self.gs.radioStart(artists = seedArtists)
				print 'After radioStart'
				self.playlist = []
				for i in range(5):
					self.playlist.append(self.gs.radioGetNextSong()[0])
				self.playSong(0)
			
		except:
			b.close()
			del b
			xbmc.log('GrooveShark Exception (getPlaylists): ' + str(sys.exc_info()[0]))
			traceback.print_exc()
			self.message(__language__(3029), __language__(3011)) #Could not get your playlists
			
	def closePlaylist(self):
		self.playlistId = 0
		self.playlistName = 'Unsaved'
		self.playlist = []
		self.nowPlaying = -1
		self.stateList = GrooveClass.STATE_LIST_SEARCH
		self.listMenu()
	
	def savePlaylist(self, playlistId = 0, name = '', about = '', songList = []):
		try:
			if self.gs.loggedInStatus() != 1:
				result = self.loginBasic()
				if result == 1:
					pass
				elif result == -1:
					return 0
				elif result == -2:
					self.message(__language__(3028),__language__(3029))
					return 0
				else:
					return 0

			if name == '':
				pName = self.getInput(__language__(3009))
			else:
				pName = name
			if pName == '' or pName == None or pName == 0:
				self.message(__language__(3010), __language__(3011))
				return 0
			b = busy()
			if playlistId == 0:
				pId = self.gs.playlistCreate(pName, about)
				if pId == 0:
					b.close()
					del b
					self.message(__language__(3008)+ ' 1')
					return 0			
			else:
				pId = playlistId
			
			if songList != []:
				songIds = songList
			else:	
				n = len(self.playlist)
				songIds = []
				for i in range(n):
					songIds.append(self.getSongIdFromList(self.playlist, i))

			if self.gs.playlistReplace(pId, songIds) == 0:
				b.close()
				del b
				self.message(__language__(3008)+ ' 2')
				return 0
			else:
				if songList == []:
					self.playlistId = pId
					self.playlistName = pName
					self.setStateLabel(__language__(3007) + ' (' + self.playlistName + ')')
				b.close()
				del b
				return pId

		except:
			traceback.print_exc()
			b.close()
			del b
			self.message(__language__(3008)+ ' 3')
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
		pDialog.create(__language__(3036), __language__(3013))
		pDialog.update(1)
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
		songId = prefix + str(item[0])
		ext = url.split('/')
		ext = ext[len(ext)-1].split('.')[1]
		fileName = songId + '.' + ext
		filePath = os.path.join(self.cacheDir, fileName)		
		if os.path.exists(filePath):
			return filePath
		else:
			return os.path.join(os.getcwd(),'resources','skins','DefaultSkin' ,'media', 'default-cover.png')






