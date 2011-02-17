import traceback
from operator import itemgetter, attrgetter
from pprint import pprint
################### Classes for songs

def debug(msg):
	try:
		if __debugging__ == True:
			print 'GrooveLib: ' + str(msg)
	except:
		pass

class GS_Song:
	"""class: Represents a Grooveshark song"""
	def __init__(self, data, defaultCoverArt = None):
		"""function: Initiates the Song class"""
		self.setContainers()
		self.id = -1
		self.name = ''
		self.artistName = ''
		self.artistID = -1
		self.albumName = ''
		self.albumID = -1
		self.verified = False
		self.duration = 0
		self.defaultCoverArt = defaultCoverArt
		self._parseData(data)

	def _parseData(self, data):
		"""function: Parses raw track data from Grooveshark"""
		try:	
			self.id = data["SongID"]
			self.name = data["Name"]
			self.artistName = data["ArtistName"]
			self.artistID = data["ArtistID"]
   			self.albumName = data["AlbumName"]
   			self.albumID = data["AlbumID"]
   			self.verified = False
		except: # Otherwise assume only songID was supplied in data
			self.id = data

		self.year = None
		try:
			self.year = data['Year']
		except:
			self.year = None
		try:
			if (data['CoverArtFilename'] != None) and (data['CoverArtFilename'] != ''):
				self.coverart = 'http://beta.grooveshark.com/static/amazonart/m' + data['CoverArtFilename']
			else:
				self.coverart = self.defaultCoverArt
		except:
			pass
		try:
			if (data['CoverArt']) != '':
				self.coverart = data['CoverArt']
		except:
			pass

		try:
			self.duration = int(data['EstimateDuration'])
		except:
			self.duration = 0

		try:
			if data["IsVerified"] == "1":
				self.verified = True
		except:
			pass
		self.artistVerified = False
		self.albumVerified = False
		try:
			if data["ArtistVerified"] == "1":
				self.artistVerified = True
		except:
			pass
		try:
			if data["AlbumVerified"] == "1":
				self.albumVerified = True
		except:
			pass
		try:
			self.trackNum = int(data["TrackNum"])
		except:
			self.trackNum = None

		self.popularity = 0
		try:
			self.popularity = int(data["Popularity"])
		except:
			pass

	def markDownloaded(self):
		"""function: Tells Grooveshark you have downloaded a song"""
		parameters = {
			"streamKey": self._lastStreamKey,
			"streamServerID": self._lastStreamServerID,
			"songID": self.id}
		self._gsapi.request(parameters, "markSongDownloaded").send()

	def mark30Seconds(self):
		"""function: Tells Grooveshark song has played over 30 seconds"""
		parameters = {
			"streamKey": self._lastStreamKey,
			"streamServerID": self._lastStreamServerID,
			"songID": self.id,
			"songQueueSongID": 0,
			"songQueueID": 0}
		self._gsapi.request(parameters, "markStreamKeyOver30Seconds",
				"service").send()

	def getStreamURL(self, gsapi):
		return gsapi.getStreamURL(self.id)

	def getSongsOnAlbum(self, gsapi):
		album = albumContainer(self.albumID, defaultCoverArt = self.defaultCoverArt)
		return album.getSongs(gsapi)

	def setContainers(self):
		self.albumContainer = GS_Album

class GS_Songs:
	def __init__(self, data, defaultCoverArt = None, container = GS_Song, sort = None):
		rev = False
		if sort == 'Score': #Sort by relevance
			rev = True
		if 'Sort' == 'Popularity': #Sort by popularity on Grooveshark
			rev = True
		try:
			data = sorted(data, key=itemgetter('Score'), reversed=rev)
		except:
			print 'GS_Songs: Couldn\'t sort'
			pass

		self.songs = []
		self.setContainers()
		self.defaultCoverArt = defaultCoverArt
		for item in data:
			song = self.songContainer(item, defaultCoverArt = self.defaultCoverArt)
			self.songs.append(song)

	def newContainer(self, song):
		return self.container(song, defaultCoverArt = self.defaultCoverArt)

	def addSong(self, song):
		self.songs.append(song)

	def get(self, n):
		return self.songs[n]

	def count(self):
		return len(self.songs)

	def queueAll(self):
		pass

	def setContainers(self):
		self.songContainer = GS_Song

	def addSong(self, song):
		self.songs.append(song)

class GS_PopularSongs(GS_Songs):
	def __init__(self, defaultCoverArt = None):
		self.songs = []
		self.setContainers()
		self.defaultCoverArt = defaultCoverArt

	def _getPopular(self, gsapi, type = 'monthly'):
		parameters = {"type":type}
		response = gsapi.request(parameters, "popularGetSongs").send()
		return response['result']['Songs']

	def getPopular(self, gsapi, type = 'monthly'):
		data = self._getPopular(gsapi, type = type) 
		for item in data:
			song = self.songContainer(item, defaultCoverArt = self.defaultCoverArt)
			self.songs.append(song)

class GS_FavoriteSongs(GS_Songs):
	def __init__(self, defaultCoverArt = None):
		self.songs = []
		self.setContainers()
		self.defaultCoverArt = defaultCoverArt

	def _favorites(self, gsapi, ofWhat = 'Songs'):
		if gsapi.authenticate():
			parameters = {"ofWhat":ofWhat, "userID":gsapi._authenticatedUserId}
			response = gsapi.request(parameters, "getFavorites").send()
			return response['result']
		else:
			debug('Could not auth in favorites')
			return None

	def getFavorites(self, gsapi, ofWhat = 'Songs'):
		data = self._favorites(gsapi, ofWhat = ofWhat) 
		for item in data:
			song = self.songContainer(item, defaultCoverArt = self.defaultCoverArt)
			self.songs.append(song)


class GS_Playlists:
	def __init__(self, defaultCoverArt = None):
		self.playlists = []
		self.setContainers()
		self.defaultCoverArt = defaultCoverArt

	def newContainer(self, song):
		return self.container(song, defaultCoverArt = self.defaultCoverArt)

	def getPlaylists(self, gsapi):
		self.playlists = []
		if gsapi.authenticate():
			parameters = {"userID":gsapi._authenticatedUserId}
			response = gsapi.request(parameters, "userGetPlaylists").send()
			#print response
			data = response['result']['Playlists']
			data = sorted(data, key=itemgetter('Name'))
			for item in data:
				playlist = self.playlistContainer(item, defaultCoverArt = self.defaultCoverArt)
				self.playlists.append(playlist)
			return True
		else:
			debug('Could not auth in playlists')
			return False

	def get(self, n):
		return self.playlists[n]

	def count(self):
		return len(self.playlists)

	def setContainers(self):
		self.playlistContainer = GS_Playlist

class GS_Playlist:
	def __init__(self, data, defaultCoverArt = None, songs = None):
		self.setContainers()
		self.songs = songs
		self.saved = True
		try:
			self.id = data['PlaylistID']
			self.name = data['Name']
			self.about = data['About']
			self.defaultCoverArt = defaultCoverArt
		except:
			self.id = data
			self.name = ''
			self.about = ''
			self.defaultCoverArt = None

	def getSongs(self, gsapi):
		if gsapi.authenticate():
			parameters = {"playlistID":self.id}
			response = gsapi.request(parameters, "playlistGetSongs").send()
			self.songs = []
			try:
				data = response['result']['Songs']
				data = sorted(data, key=itemgetter('Sort')) # Sort according to groovesharks sort key. Keeps original sorting when the playlist is saved
				self.songs = self.songsContainer(data, self.defaultCoverArt)
				return True
			except:
				return False
		else:
			return False
			print 'playlist, could not auth'

	def addSong(self, song):
		try:
			self.songs.addSong(song)
			self.saved = False
			return True
		except:
			traceback.print_exc()
			return False

	def rename(self, gsapi, name):
		if gsapi.authenticate():
			parameters = {"playlistID":self.id, 'playlistName':name}
			response = gsapi.request(parameters, "renamePlaylist").send()
			#print response
			try:
				result = response['result']
				if result == True:
					return True
				else:
					return False
			except:
				return False
		else:
			debug('Could not auth in rename playlist')
			return False

	def save(self, gsapi):
		songIds = []
		for i in range(self.songs.count()):
			song = self.songs.get(i)
			songIds.append(song.id)
		if gsapi.authenticate():
			parameters = {"playlistID":self.id, 'songIDs':songIds}
			response = gsapi.request(parameters, "overwritePlaylist").send()
			try:
				if response['result'] == True:
					self.saved = True
					return True
			except:
				return False
		else:
			debug('Could not auth in save')
			return False

	def saveAs(self, gsapi):
		songIds = []
		for i in range(self.songs.count()):
			song = self.songs.get(i)
			songIds.append(song.id)
		if gsapi.authenticate():
			parameters = {"playlistAbout":self.about, "playlistName":self.name, 'songIDs':songIds}
			response = gsapi.request(parameters, "createPlaylist").send()
			try:
				return response['result']
			except:
				return -1
		else:
			debug('Could not auth in playlist save as')
			return -1

	def delete(self, gsapi):
		if gsapi.authenticate():
			parameters = {"name":self.name, "playlistID":self.id}
			response = gsapi.request(parameters, "deletePlaylist").send()
			try:
				result = response['result']
				if result == 1:
					return True
			except:
				return False
		else:
			debug('Could not auth in delete playlist')
			return False

	def setContainers(self):
		self.songsContainer = GS_Songs
################### Classes for albums

class GS_Album:
	"""class: Respresent a Grooveshark album"""

	def __init__(self, data, defaultCoverArt = None):
		"""function: Initiates the Album class"""
		self.setContainers()
		id = None
		self.name = ""
		self.artistId = None
		self.artistName = ""
		self.artistVerified = False
		self.coverArt = None
		self.verified = False
		self.hasMore = False
		self.defaultCoverArt = defaultCoverArt
		try:
			self._parseData(data)
		except:
			self.id = data

	def _parseData(self, data):
		"""function: Parse information from json data"""
		try:
			self.id = data["AlbumID"]
			self.name = data["AlbumName"]
			self.artistName = data["ArtistName"]
			self.artistID = data["ArtistID"]
		except:
			self.id = data
			pass

		if (data['CoverArtFilename'] != None) and (data['CoverArtFilename'] != ''):
			self.coverart = 'http://beta.grooveshark.com/static/amazonart/m' + data['CoverArtFilename']
		else:
			self.coverart = self.defaultCoverArt
		
	def getSongs(self, gsapi):
		parameters = {"albumID":self.id, "isVerified":self.verified, "offset":0}
		response = gsapi.request(parameters, "albumGetSongs").send()
		return self.songsContainer(response['result']['songs'], defaultCoverArt = self.defaultCoverArt)

	def setContainers(self):
		self.songsContainer = GS_Songs

class GS_Albums:
	def __init__(self, data, defaultCoverArt = None, container = GS_Album):
		self.albums = []
		self.defaultCoverArt = defaultCoverArt
		self.setContainers()
		for entry in data:
			album = self.albumContainer(entry, defaultCoverArt = self.defaultCoverArt)
			duplicate = False
			for a in self.albums:
				if a.id == album.id:
					duplicate = True
			if duplicate == False:
				self.albums.append(album)

	def setContainers(self):
		self.albumContainer = GS_Album

	def count(self):
		return len(self.albums)

	def get(self, n):
		return self.albums[n]

	def newContainer(self, album):
		return self.container(album, defaultCoverArt = self.defaultCoverArt)


################### Classes for artists

class GS_Artist:
	"""class: Respresent a Grooveshark artist"""

	def __init__(self, data, defaultCoverArt = None):
		"""function: Initiates the Artist class"""
		self.setContainers()
		try:
			self.id = None
			self.name = ""
			self.verified = False
			self.hasMore = False
			self.defaultCoverArt = defaultCoverArt
			self._parseData(data)
		except:
			self.id = data

	def _parseData(self, data):
		"""function: Parse information from json data"""
		try:
			self.id = data["ArtistID"]
			self.name = data["ArtistName"]
		except:
			try: #Returned by similar artists
				self.id = data["ArtistID"]
				self.name = data["Name"]
			except:
				self.id = data
		try:
			if None == self.verified and "1" == data["ArtistVerified"]:
				self.verified = True
		except:
			pass
	
	def similar(self, gsapi):
		parameters = {
			"artistID": self.id}

		response = gsapi.request(parameters, "artistGetSimilarArtists").send()
		return self.artistsContainer(response['result']['SimilarArtists'], defaultCoverArt = self.defaultCoverArt)

	def _getSongs(self, gsapi):
		parameters = {"artistID":self.id, "isVerified":self.verified, "offset":0}
		return gsapi.request(parameters, "artistGetSongs").send()

	def getSongs(self, gsapi):
		res = self._getSongs(gsapi)
		return self.songsContainer(res['result']['songs'], defaultCoverArt = self.defaultCoverArt)

	def getAlbums(self, gsapi):
		res = self._getSongs(gsapi)
		return self.albumsContainer(res['result']['songs'], defaultCoverArt = self.defaultCoverArt)

	def setContainers(self):
		self.songsContainer = GS_Songs
		self.albumsContainer = GS_Albums
		self.artistsContainer = GS_Artists

class GS_Artists:
	def __init__(self, data, defaultCoverArt = None):
		self.artists = []
		self.defaultCoverArt = defaultCoverArt
		self.setContainers()
		for entry in data:
			artist = self.artistContainer(entry, defaultCoverArt = self.defaultCoverArt)
			duplicate = False
			for a in self.artists:
				if a.id == artist.id:
					duplicate = True
			if duplicate == False:
				self.artists.append(artist)	

	def get(self, n):
		return self.artists[n]

	def count(self):
		return len(self.artists)

	def newContainer(self, artist):
		return self.container(artist, defaultCoverArt = self.defaultCoverArt)

	def setContainers(self):
		self.artistContainer = GS_Artist

################### Classes for searching
class GS_Search:
	"""class: Represents Grooveshark Search Results"""

	def __init__(self,\
					defaultCoverArt = None,\
					songContainer = GS_Song,\
					songsContainer = GS_Songs,\
					albumContainer = GS_Album,\
					albumsContainer = GS_Albums,\
					artistContainer = GS_Artist,\
					artistsContainer = GS_Artists):

		self.songContainer = songContainer
		self.songsContainer = songsContainer
		self.albumContainer = albumContainer
		self.albumsContainer = albumsContainer
		self.artistContainer = artistContainer
		self.artistsContainer = artistsContainer
		self.defaultCoverArt = defaultCoverArt
		self.queryText = None
		self.resultRaw = ''
		self.songs = []
		self.artists = []
		self.albums = []
		
	def _search(self, gsapi, query, type = 'Songs'):
		self.queryText = query
		parameters = {
			"query": query,
			"type": type}
		self.resultRaw = ''
		self.resultRaw = gsapi.request(parameters, "getSearchResultsEx").send()
		return self.resultRaw

	def search(self, gsapi, query, type = 'Songs'):
		result = self._search(gsapi, query, type = type)
		try:
			self.songs = self.newSongsContainer(result['result']['result'], sort = 'Score')
			self.albums = self.newAlbumsContainer(result['result']['result'])
			self.artists = self.newArtistsContainer(result['result']['result'])
			self.queryText = query
		except:
			self.songs = []
			self.artists = []
			self.albums = []
			self.queryText = None
			traceback.print_exc()
	
	def newSongContainer(self, item, sort = None):
		return self.songContainer(item, defaultCoverArt = self.defaultCoverArt)

	def newSongsContainer(self, item, sort = None):
		return self.songsContainer(item, defaultCoverArt = self.defaultCoverArt, sort = sort)

	def newArtistContainer(self, item):
		return self.artistContainer(item, defaultCoverArt = self.defaultCoverArt)

	def newArtistsContainer(self, item):
		return self.artistsContainer(item, defaultCoverArt = self.defaultCoverArt)

	def newAlbumContainer(self, item):
		return self.albumContainer(item, defaultCoverArt = self.defaultCoverArt)

	def newAlbumsContainer(self, item):
		return self.albumsContainer(item, defaultCoverArt = self.defaultCoverArt)

	def searchPlaylist(self, gsapi):
		pass

	def quickSearch(self, gsapi, query):
		parameters = {"query": query}
		response = gsapi.request(parameters, "getArtistAutocomplete").send()
		return response

	def countResults(self):
		try:
			return self.songs.count()
		except:
			return 0

	def countSongs(self):
		try:
			return self.songs.count()
		except:
			return 0

	def countAlbums(self):
		try:
			return self.albums.count()
		except:
			return 0

	def countArtists(self):
		try:
			return self.artists.count()
		except:
			return 0

	def getSong(self, n):
		try:
			return self.songs.get(n)
		except:
			return 0

	def getAlbum(self, n):
		try:
			return self.albums.get(n)
		except:
			return 0

