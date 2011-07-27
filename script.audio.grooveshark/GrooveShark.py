import xbmc, xbmcgui, xbmcplugin #, xbmcaddon
import sys
import pickle
import os
import traceback
import threading
import random
import gc
from pprint import pprint

__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__version__ = sys.modules[ "__main__" ].__version__
__settings__ = sys.modules[ "__main__" ].__settings__
__language__ = sys.modules[ "__main__" ].__language__
__scriptid__ = sys.modules[ "__main__" ].__scriptid__
__debugging__ = sys.modules["__main__"].__debugging__
__isXbox__ = sys.modules["__main__"].__isXbox__
__cwd__ = sys.modules["__main__"].__cwd__

sys.path.append(os.path.join(__cwd__.replace(";",""),'resources','lib'))
import uuid

from GrooveAPI import *
from GrooveLib import *
from GroovePlayer import GroovePlayer
from GrooveGUI import *
from operator import itemgetter, attrgetter

pGUI = None

def setPGUI(p):
	global pGUI
	pGUI = p

def lock():
	cnt = pGUI.getControl(7005)
	pGUI.setFocus(cnt)

def unlock():
	pGUI.playlistHasFocus()

#plugin://%s/?playSong=%s&artistId=%s&albumId=%s&image=%s&songName=%s&artistName=%s&albumName=%s&options=%s

#plugin://script.audio.grooveshark/?
#playSong=10779110
#&artistId=401423
#&albumId=1145459
#&image=http%3A%2F%2Fbeta.grooveshark.com%2Fstatic%2Famazonart%2Fm3253484.jpg
#&songName=Yes Sir I Can Boogie
#&artistName=Goldfrapp
#&albumName=Misc
#&options=
class NowPlaying:
	def __init__(self, gui, gsapi, defaultCoverArt = None):
		self.songs = []
		self.gsapi = gsapi
		self.defaultCoverArt = defaultCoverArt
		self.gui = gui
		pass

	def decode(self, s):
		try:
			return urllib.unquote_plus(s)
		except:
			print s
			return "blabla"

	def _list(self, gui, gsapi):
		playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
		n = playlist.size()
		data = []
		songs = []
		for i in range(n):
			song = playlist[i]
			name = song.getfilename()
			name = name.split('?')[1]
			parts = name.split('&')
			songId = parts[0].split('=')[1]
			artistId = parts[1].split('=')[1]
			albumId = parts[2].split('=')[1]
			image = self.decode(parts[3].split('=')[1])
			songName = self.decode(parts[4].split('=')[1])
			artistName = self.decode(parts[5].split('=')[1])
			albumName = self.decode(parts[6].split('=')[1])
			options = parts[7].split('=')[1]
			item = {'SongID': songId,\
					'Name': songName,\
					'AlbumName':albumName,\
					'ArtistName':artistName,\
					'ArtistID':artistId,\
					'AlbumID':albumId,\
					'ArtistID':artistId,\
					'CoverArt':image\
					}
			data.append(item)
		songs = Songs(data, defaultCoverArt = self.defaultCoverArt)
		#pprint(data)
		return songs._list(self.gui, self.gsapi)
			

class Search(GS_Search):
	def __init__(self, gui, defaultCoverArt = None):
		self.gui = gui
		GS_Search.__init__(self,\
					defaultCoverArt = defaultCoverArt,\
					songContainer = Song,\
					songsContainer = Songs,\
					albumContainer = Album,\
					albumsContainer = Albums,\
					artistContainer = Artist,\
					artistsContainer = Artists)

	def newSongContainer(self, item):
		return self.songContainer(item, defaultCoverArt = self.defaultCoverArt)

	def newSongsContainer(self, item, sort = 'Score'):
		return self.songsContainer(item, defaultCoverArt = self.defaultCoverArt)

	def newArtistContainer(self, item):
		return self.artistContainer(item, defaultCoverArt = self.defaultCoverArt)

	def newArtistsContainer(self, item):
		return self.artistsContainer(item, defaultCoverArt = self.defaultCoverArt)

	def newAlbumContainer(self, item):
		return self.albumContainer(item, defaultCoverArt = self.defaultCoverArt)

	def newAlbumsContainer(self, item):
		return self.albumsContainer(item, defaultCoverArt = self.defaultCoverArt)

	def get(self, n):
		if n == 0:
			return self.songs
		if n == 1:
			return self.artists
		if n == 2:
			return self.albums
		if n == 3:
			return self.songs

	def _list(self, gui, gsapi):
		if self.queryText == None:
			return
		self.info = ''
		pathArtist = os.path.join(__cwd__,'resources','skins','DefaultSkin', 'media', 'gs_artist.png')
		pathAlbum = os.path.join(__cwd__,'resources','skins','DefaultSkin', 'media', 'gs_album.png')
		pathSong = os.path.join(__cwd__,'resources','skins','DefaultSkin', 'media', 'gs_song.png')
		pathPlaylist = os.path.join(__cwd__,'resources','skins','DefaultSkin', 'media', 'gs_playlist.png')
		search = self
		listItems = [\
			xbmcgui.ListItem (label=__language__(3023), label2=str(search.countSongs()) + ' ' + __language__(3026), thumbnailImage=pathSong),\
			xbmcgui.ListItem (label=__language__(3024), label2=str(search.countArtists()) + ' ' + __language__(3026), thumbnailImage=pathArtist),\
			xbmcgui.ListItem (label=__language__(3025), label2=str(search.countAlbums()) + ' ' + __language__(3026), thumbnailImage=pathAlbum),\
			#xbmcgui.ListItem (label=__language__(3042), label2=str(0) + ' ' + __language__(3026), thumbnailImage=pathPlaylist),\
		]
		return [self, listItems]
		pass

class Songs(GS_Songs):
	def __init__(self, data, defaultCoverArt = None, sort = None):
		GS_Songs.__init__(self, data, defaultCoverArt = defaultCoverArt, sort = sort)

	def setContainers(self):
		self.songContainer = Song

	def _list(self, gui, gsapi):
		try:
			n = self.count()
			self.info = str(n) + ' ' + __language__(3023)
			listItems = []
			for i in range(self.count()):
				song = self.get(i)
				try:
					durMin = int(song.duration/60.0)
					durSec = int(song.duration - durMin*60)
					if durSec < 10:
						durStr = '(' + str(durMin) + ':0' + str(durSec) + ')'
					else:
						durStr = '(' + str(durMin) + ':' + str(durSec) + ')'
				except:
					durStr = ''
				if gui.useCoverArt == True:
					path = song.coverart
					if path == None:
						path = 'Invalid cover path: ' + str(path)
						print path
				else:
					path = os.path.join(__cwd__, 'resources','skins','DefaultSkin','media','default-cover.png')
				l1 = song.name
				l2 = 'By ' + song.artistName + '\n From ' + song.albumName
				if song.year != None:
					try:
						lYear = ' (' + str(int(song.year)) + ')'
					except:
						lYear = ''
				else:
					lYear = ''
				l2 = l2 + lYear
				imageDir = os.path.join(__cwd__, 'resources','skins','DefaultSkin','media')
				path2 = os.path.join(imageDir, 'gs_smile.png')
				item = xbmcgui.ListItem (label=l1,label2=l2, thumbnailImage=path, iconImage = path2)
				listItems.append(item)
			return self, listItems
		except:
			xbmc.log('GrooveShark Exception (listSongs): ' + str(sys.exc_info()[0]))
			traceback.print_exc()
			xbmcgui.unlock()
		return [self, []]

	def queueAll(self, playlist = None, append = False):
		if playlist == None:
			playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)		
		if append == False:
			playlist.clear()
			offset = 0
		else:
			offset = playlist.size()
		for i in range(self.count()):
			song = self.get(i)
			self.queue(song, playlist = playlist, index = i + offset)

	def play(self, selected, gsapi, playlist = None):
		# It's not pretty but it works
		if playlist == None:
			playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)		
		self.queueAll(playlist, append = False)

		song = self.get(selected)
		url = song.getStreamURL(gsapi)
		songName = playlist[selected].getfilename()
		playlist.remove(songName)

		self.queue(song, playlist = playlist, index = selected, url = url)
		xbmc.Player().playselected(selected)
		songName = playlist[selected].getfilename()
		playlist.remove(songName)
		self.queue(song, playlist = playlist, index = selected)
		
	def queue(self, song, playlist = None, index = -1, options = '', url = None):
		if playlist == None:
			playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
		if url == None:
			url = self.defaultUrl(song)
		if index < 0:
			index = playlist.size()
		listItem = self.createListItem(url, song)
		playlist.add(url=url, listitem=listItem, index=index)

	def defaultUrl(self, song, options = ''):
		return 'plugin://%s/?playSong=%s&artistId=%s&albumId=%s&image=%s&songName=%s&artistName=%s&albumName=%s&options=%s' % (__scriptid__, song.id, song.artistID, song.albumID, self.encode(song.coverart), self.encode(song.name), self.encode(song.artistName), self.encode(song.albumName), options) # Adding plugin:// to the url makes xbmc call the script to resolve the real url

	def encode(self, s):
		try:
			return urllib.quote_plus(s.encode('latin1','ignore'))
		except:
			print '########## GS Encode error'
			print s
			return '### encode error ###'

	def createListItem(self, url, song):
		listItem = xbmcgui.ListItem('music', thumbnailImage=song.coverart, iconImage=song.coverart)
		listItem.setProperty( 'Music', "true" )
		listItem.setProperty('mimetype', 'audio/mpeg')
		listItem.setProperty('IsPlayable', 'true') # Tell XBMC that it is playable and not a folder
		listItem.setInfo(type = 'Music', infoLabels = {'title': song.name, 'artist': song.artistName, 'album': song.albumName, 'duration': song.duration, 'path':url})
		return listItem

class Albums(GS_Albums):
	def __init__(self, data, defaultCoverArt = None):
		GS_Albums.__init__(self, data, defaultCoverArt = defaultCoverArt)

	def setContainers(self):
		self.albumContainer = Album

	def _list(self, gui, gsapi):
		n = self.count()
		self.info = str(n) + ' ' + __language__(3025)
		listItems = []
		for i in range(self.count()):
			album = self.get(i)
			item = xbmcgui.ListItem (label=album.name, label2=album.artistName, thumbnailImage=album.coverart, iconImage=album.coverart)
			listItems.append(item)
		return [self, listItems]

class Artists(GS_Artists):
	def __init__(self, data, defaultCoverArt = None):
		GS_Artists.__init__(self, data, defaultCoverArt = defaultCoverArt)

	def setContainers(self):
		self.artistContainer = Artist

	def _list(self, gui, gsapi):
		n = self.count()
		self.info = str(n) + ' ' + __language__(3024)
		path = os.path.join(os.getcwd(),'resources','skins','DefaultSkin', 'media','default-cover.png')
		listItems = []
		for i in range(self.count()):
			artist = self.get(i)
			item = xbmcgui.ListItem (label=artist.name, thumbnailImage=path)
			listItems.append(item)
		return [self, listItems]

class Song(GS_Song):
	def __init__(self, data, defaultCoverArt = None):
		GS_Song.__init__(self, data, defaultCoverArt = defaultCoverArt)

	def _list(self, gui, gsapi):
		return [None, None]

	def setContainers(self):
		self.albumContainer = Album


class Album(GS_Album):
	def __init__(self, data, defaultCoverArt = None):
		GS_Album.__init__(self, data, defaultCoverArt = defaultCoverArt)

	def setContainers(self):
		self.songsContainer = Songs

	def _list(self, gui, gsapi):
		songs = self.getSongs(gsapi)
		return songs._list(gui, gsapi)
		
class Artist(GS_Artist):
	def __init__(self, data, defaultCoverArt = None):
		GS_Artist.__init__(self, data, defaultCoverArt = defaultCoverArt)

	def setContainers(self):
		self.songsContainer = Songs
		self.albumsContainer = Albums
		self.artistsContainer = Artists

	def _list(self, gui, gsapi):
		songs = self.getSongs(gsapi)
		return songs._list(gui, gsapi)

class Playlist(Songs):
	def _null(self):
		pass
		
class Popular(GS_PopularSongs):
	def __init__(self, gui, gsapi, type = 'monthly', defaultCoverArt = None):
		self.defaultCoverArt = defaultCoverArt
		self.gui = gui
		self.type = type
		GS_PopularSongs.__init__(self, defaultCoverArt = defaultCoverArt)

	def setContainers(self):
		self.songContainer = Song

	def _list(self, gui, gsapi):
		data = self._getPopular(gsapi)
		return Songs(data, self.defaultCoverArt)._list(gui, gsapi)

class Favorites(GS_FavoriteSongs):
	def __init__(self, gui, gsapi, defaultCoverArt = None):
		self.defaultCoverArt = defaultCoverArt
		self.gui = gui
		self.type = type
		GS_FavoriteSongs.__init__(self, defaultCoverArt = defaultCoverArt)

	def setContainers(self):
		self.songContainer = Song

	def _list(self, gui, gsapi):
		data = self._favorites(gsapi)
		if data == None:
			gui.notification(__language__(3027)) #Wrong username/password
			return None
		return Songs(data, self.defaultCoverArt)._list(gui, gsapi)

class Playlists(GS_Playlists):
	def __init__(self, gui, defaultCoverArt = None):
		self.gui = gui
		GS_Playlists.__init__(self, defaultCoverArt = defaultCoverArt)

	def setContainers(self):
		self.playlistContainer = Playlist

	def _list(self, gui, gsapi):
		if self.getPlaylists(gsapi) == False:
			gui.notification(__language__(3027))
			return [None, None]
		n = self.count()
		self.info = str(n) + ' ' + __language__(3042)
		listItems = []
		for i in range(self.count()):
			playlist = self.get(i)
			if playlist.about == None:
				l2 = ''
			else:
				l2 = playlist.about
			item = xbmcgui.ListItem (label=playlist.name, label2=l2, thumbnailImage=self.defaultCoverArt, iconImage=self.defaultCoverArt)
			listItems.append(item)
		return [self, listItems]

class Playlist(GS_Playlist):
	def setContainers(self):
		self.songsContainer = Songs

	def _list(self, gui, gsapi):
		data = self.getSongs(gsapi)
		return self.songs._list(gui, gsapi)

class RootTree:
	def __init__(self, gui, gsapi, defaultCoverArt = None):
		self.defaultCoverArt = defaultCoverArt
		self.gui = gui
		self._search = Search(gui = gui, defaultCoverArt = self.defaultCoverArt)
		self.tree = [self._search,\
						Popular(gui = gui, gsapi = gsapi, type = 'monthly', defaultCoverArt = self.defaultCoverArt),\
						Favorites(gui = gui, gsapi = gsapi, defaultCoverArt = self.defaultCoverArt),\
						Playlists(gui = gui, defaultCoverArt = self.defaultCoverArt),\
						NowPlaying(gui = gui, gsapi = gsapi, defaultCoverArt = self.defaultCoverArt)]

		pass

	def get(self, n):
		return self.tree[n]

	def setSearch(self):
		pass

	def _list(self, gui, gsapi):
		self.info = ''
		pathSearch = os.path.join(__cwd__,'resources','skins','DefaultSkin', 'media', 'gs_search.png')
		pathPopular = os.path.join(__cwd__,'resources','skins','DefaultSkin', 'media', 'gs_popular.png')
		pathFavorites = os.path.join(__cwd__,'resources','skins','DefaultSkin', 'media', 'gs_favorites.png')
		pathPlaylist = os.path.join(__cwd__,'resources','skins','DefaultSkin', 'media', 'gs_playlist.png')
		pathNowPlaying = os.path.join(__cwd__,'resources','skins','DefaultSkin', 'media', 'gs_song.png')
		try:
			searchLabel = 'Found ' + str(self._search.countResults()) + ' for "' + self._search.queryText + '"'
		except:
			searchLabel = 'Start a new search in the menu'
			traceback.print_exc()

		listItems = [\
			xbmcgui.ListItem (label=__language__(128), label2=searchLabel, thumbnailImage=pathSearch),\
			xbmcgui.ListItem (label=__language__(108), label2=__language__(3041), thumbnailImage=pathPopular),\
			xbmcgui.ListItem (label=__language__(129), label2='Your favorites', thumbnailImage=pathFavorites),\
			xbmcgui.ListItem (label=__language__(117), label2=__language__(3039), thumbnailImage=pathPlaylist),\
			xbmcgui.ListItem (label=__language__(107), label2='Have a look at the tunes you\'re playing', thumbnailImage=pathNowPlaying),\
		]
		self.gui.setStateLabel('')
		return [self, listItems]

class Navigation:
	tree = []
	def __init__(self, gui, gsapi, optionsCallBack = None, displayCallBack = None, optionsShowCallback = None):
		self.gsapi = gsapi
		self.gui = gui
		self.optionsCallBack = optionsCallBack
		self.displayCallBack = displayCallBack
		self.optionsShowCallBack = optionsShowCallback
		pass

	def showOptions(self, item):
		self.debug('showOptions called in navi')
		if self.optionsShowCallBack != None:
			return self.optionsShowCallBack(item)

	def setOptions(self, item):
		if self.optionsCallBack != None:
			return self.optionsCallBack(item)

	def displayItems(self, item, selected = 0):
		if self.displayCallBack != None:
			return self.displayCallBack(item, selected = selected)

	def locationLabel(self):
		return
		location = ''
		for i in range(len(self.tree)):
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
		

	def reset(self):
		self.tree = []

	def navigate(self, p):
		n = len(self.tree)
		print 'Navigate: n = ' + str(n) + ', p = ' + str(p) 
		if n > 1:
			if p == 0:
				self.up()
			else:
				try:
					item = self.getBranchObject().get(p-1)
					print 'navigate()::get(): Type: ' + str(item)
					self.down(item, selected = p)
				except:
					traceback.print_exc()
					print 'navigate()::get() failed p-1'
		else:
			try:
				item = self.getBranchObject().get(p)
				print 'Type: ' + str(item)
				self.down(item, selected = p)
			except:
				traceback.print_exc()
				print 'navigate()::get() failed p'

	def up(self):
		n = len(self.tree)
		if n > 1:
			self.tree.pop(n-1)
			self._list()
		pass

	def addBack(self):
		try:
			n = len(self.tree)
			if n > 1:
				path = os.path.join(__cwd__,'resources','skins','DefaultSkin', 'media', 'gs_back.png')
				item = xbmcgui.ListItem (label='', label2='', thumbnailImage=path, iconImage=self.gui.defaultCoverArt)
				self.gui.addItem(item)
		except:
			traceback.print_exc()


	def hasBack(self):
		n = len(self.tree)
		if n > 1:
			return True
		return False

	def updateList(self, branch, subBranch, selected = 0):
		while len(self.tree) > (branch + 1):
			self.tree.pop(len(self.tree)-1)
		_branch = self.tree[branch]
		listItems = _branch['branchObject']._list(gui = self.gui, gsapi = self.gsapi)[1]
		_branch['listItems'] = listItems
		subBranchObj = _branch['branchObject'].get(subBranch)
		self.down(subBranchObj, preSelected = selected)
		
		
	def down(self, item, selected = 0, withList = True, preSelected = 0):
		if item == None:
			return
		lock()
		try:
			res = item._list(self.gui, self.gsapi)
			branchObject = res[0]
			listItems = res[1]
		except:
			unlock()
			traceback.print_exc()
			return
		try:
			n = len(self.tree)
			if n > 0:
				self.tree[n-1]['selected'] = selected
			if branchObject != None:
				self.addBranch(listItems, branchObject, selected = preSelected)
				if withList == True:
					self._list()
			else:
				self.showOptions(self.getBranchObject())
		except:
			unlock()
			traceback.print_exc()
			print 'Could not descend a level'

	def addBranch(self, listItems, branchObject, selected = 0):
		n = len(listItems)
		print 'sel: ' + str(selected) + ' n: ' + str(n)
		if selected > n:
			selected = n
		self.tree.append({'listItems': listItems, 'branchObject': branchObject, 'selected': selected})

	def setSelected(self, selected):
		n = len(self.tree)
		self.tree[n-1]['selected'] = selected

	def getListItems(self, n = -1):
		if n == -1:
			n = len(self.tree)
		return self.tree[n-1]['listItems']

	def getBranchObject(self, n = -1):
		if n == -1:
			n = len(self.tree)
		return self.tree[n-1]['branchObject']

	def _list(self):
		obj = self.getBranchObject()
		try:
			info = obj.info
		except:
			info = ''
		self.gui.setInfoLabel(info)
		self.gui.clearList()
		self.addBack()
		listItems = self.getListItems()
		n = len(self.tree)
		self.displayItems(listItems, selected = self.tree[n-1]['selected'])
		self.setOptions(obj)
	
	def debug(self, msg):
		print msg

class searchThread(threading.Thread):
	def __init__(self, item, query, searchLimit):
		threading.Thread.__init__(self)
		self.item = item
		self.query = query
		self.searchLimit = searchLimit

	def run (self):
		try:
			function = self.item['function']
			if self.query == None:
				self.item['result'] = function(self.searchLimit)
			else:
				self.item['result'] = function(self.query, self.searchLimit)
		except:
			self.item['result'] = None
			print "GrooveShark: Search thread failed"
			traceback.print_exc()

class Options:
	def __init__(self, cntList, cntLabel, cntImage, gui):
		self.cntLabel = cntLabel
		self.cntList = cntList
		self.cntImage = cntImage
		self.reset()

	def reset(self):
		self.items = []
		self.lastUpdatedItems = []
		self.label = ''
		self.image = ''

	def addOption(self, name, callback):
		self.items.append({'name': name, 'callback': callback})

	def addOptions(self, items):
		self.lastUpdatedItems = []
		for item in items:
			self.items.append(item)

	def setLabel(self, s):
		self.label = s

	def setImage(self, path):
		self.cntImage.setImage(path)

	def countEnabled(self, withBack = True):
		if withBack == True:
			return len(self.items)
		n = 0
		for item in self.items:
			if item['enabledOnBack'] == True:
				n += 1
		return n

	def execute(self):
		n = self.cntList.getSelectedPosition()
		try:
			f = self.lastUpdatedItems[n]['callback']
			f(obj = self.obj, selected = self.selected, item = self.lastUpdatedItems[n])
		except:
			print 'execute(): Error when using callback. Obj: ' + str(self.obj.__class__) + ', callback: ' + str(type(f)) + ', n: ' + str(n)
			traceback.print_exc()

	def update(self, selected = 0, back = False, obj = None):
		self.obj = obj
		self.selected = selected
		self.cntLabel.setLabel(self.label)
		self.cntList.reset()
		n = self.countEnabled(withBack = (not back))
		for item in self.items:
			icon = ''
			try:
				icon = item['icon']
			except:
				pass
			listItem = xbmcgui.ListItem (label=item['name'], label2='', thumbnailImage=icon, iconImage='')
			if back == True:
				if item['enabledOnBack'] == True:
					self.cntList.addItem(listItem)
					self.lastUpdatedItems.append(item)
			else:
				self.cntList.addItem(listItem)
				self.lastUpdatedItems.append(item)

class GrooveClass(xbmcgui.WindowXML):
	def setStateLabel(self, msg):
		self.getControl(3000).setLabel(msg)

	def setInfoLabel(self, msg):
		cnt = self.getControl(300011)
		cnt.setLabel(msg)
		cnt.setVisible(True)

	def notification(self, message):
		cnt = self.getControl(7001)
		label = self.getControl(7003)
		label.setLabel(message)
		self.setFocus(cnt)
		xbmc.sleep(100)
		self.playlistHasFocus()

	def displayItems(self, items, selected = 0):
		xbmcgui.lock()
		try:
			for item in items:
				self.addItem(item)
			self.setCurrentListPosition(selected)
			self.playlistHasFocus()
			xbmcgui.unlock()
		except:
			xbmcgui.unlock()
			self.debug('displayItems(): Could not add items')

	def setOptionsPlaylists(self, song):
		playlists = Playlists(self, defaultCoverArt = self.defaultCoverArt)
		playlists.getPlaylists(self.gs)
		self.options = self.optionsPlaylists
		print 'setOptionsPlaylists() called'
		cnt = self.getControl(500)
		cnt.setEnabled(True)
		items = []
		for i in range(playlists.count()):
			playlist = playlists.get(i)
			item = {'name': playlist.name, 'callback': self.addSongToPlaylistExec, 'enabledOnBack': True, 'song': song, 'playlist': playlist}
			items.append(item)

		self.options.reset()
		self.options.setLabel('Which?')
		self.options.setImage(os.path.join(self.imageDir, 'gs_addsong.png'))
		self.options.addOptions(items)
		self.options.update()

	def setOptionsMenu(self):
		self.options = self.optionsMenu
		self.debug('setOptionsMenu() called')
		cnt = self.getControl(500)
		cnt.setEnabled(True)
		items = []
		items = [{'name': __language__(106), 'callback': self.newSearch, 'enabledOnBack': True, 'icon': 'gs_search.png'},\
					{'name': __language__(117), 'callback': self.showPlaylists, 'enabledOnBack': True, 'icon': 'gs_playlist.png'},\
					{'name': __language__(107), 'callback': self.showNowPlaying, 'enabledOnBack': True, 'icon': 'gs_song.png'},\
					{'name': __language__(109), 'callback': self.settings, 'enabledOnBack': True, 'icon': 'gs_wrench.png'},\
					{'name': __language__(121), 'callback': self.exit, 'enabledOnBack': True, 'icon': 'gs_exit.png'}]

		self.options.reset()
		self.options.setLabel('')
		self.options.setImage(os.path.join(self.imageDir, 'gs_home.png'))
		self.options.addOptions(items)
		self.options.update()

	def setOptionsRight(self, obj):
		self.options = self.optionsRight
		print 'setOptionsRight() called'
		cnt = self.getControl(500)
		cnt.setEnabled(True)
		if isinstance(obj, Song):
			pass
		if isinstance(obj, Songs):
			items = [{'name': __language__(102), 'callback': self.play, 'enabledOnBack': False, 'icon':'gs_play_item.png'},\
						{'name': __language__(101), 'callback': self.queueSong, 'enabledOnBack': False, 'icon':'gs_enqueue.png'},\
						{'name': __language__(103), 'callback': self.queueAllSongs, 'enabledOnBack': True, 'icon':'gs_enqueue.png'},\
						{'name': __language__(104), 'callback': self.addSongToPlaylist, 'enabledOnBack': False, 'icon':'gs_addsong.png'},\
						{'name':  __language__(119), 'callback': self.findSimilarFromSong, 'enabledOnBack': False, 'icon':'gs_similar.png'},\
						{'name':  __language__(120), 'callback': self.songsOnAlbum, 'enabledOnBack': False, 'icon':'gs_album.png'}]
			self.options.reset()
			self.options.setLabel('')
			self.options.setImage(os.path.join(self.imageDir, 'gs_song.png'))
			self.options.addOptions(items)
			self.options.update()
		if isinstance(obj, Albums):
			items = [{'name': __language__(125), 'callback': self.playAlbum, 'enabledOnBack': False, 'icon': 'gs_play_item.png'},\
						{'name': __language__(126), 'callback': self.queueAlbum, 'enabledOnBack': False, 'icon': 'gs_enqueue.png'},\
						{'name': __language__(127), 'callback': self.saveAlbumAsPlaylist, 'enabledOnBack': False, 'icon': 'gs_savealbum.png'},\
						{'name':  __language__(119), 'callback': self.findSimilarFromAlbum, 'enabledOnBack': False, 'icon': 'gs_similar.png'}]
			self.options.reset()
			self.options.setLabel('')
			self.options.setImage(os.path.join(self.imageDir, 'gs_album.png'))
			self.options.addOptions(items)
			self.options.update()
		if isinstance(obj, Playlists):
			items = [{'name': __language__(111), 'callback': self.renamePlaylist, 'enabledOnBack': False, 'icon': 'gs_rename.png'},\
						{'name': __language__(112), 'callback': self.deletePlaylist, 'enabledOnBack': False, 'icon': 'gs_delete2.png'}]
			self.options.reset()
			self.options.setLabel('')
			self.options.setImage(os.path.join(self.imageDir, 'gs_playlist.png'))
			self.options.addOptions(items)
			self.options.update()
		if isinstance(obj, Artists):
			items = [{'name': 'Play songs', 'callback': self.playSongsByArtist, 'enabledOnBack': False, 'icon': 'gs_play_item.png'},\
						{'name':  __language__(119), 'callback': self.findSimilarFromArtist, 'enabledOnBack': False, 'icon': 'gs_similar.png'}]
			self.options.reset()
			self.options.setLabel('')
			self.options.setImage(os.path.join(self.imageDir, 'gs_artist.png'))
			self.options.addOptions(items)
			self.options.update()
		if isinstance(obj, Search):	
			cnt = self.getControl(500)
			cnt.setEnabled(False)
			self.options.reset()
			self.options.setLabel('')
			self.options.update()
		if isinstance(obj, RootTree):	
			cnt = self.getControl(500)
			cnt.setEnabled(False)
			self.options.reset()
			self.options.setLabel('')
			self.options.update()

	def insertOptions(self, items):
		cnt = self.getControl(500)
		cnt.addItems(items)

	def setOptionsLabel(self, msg):
		self.getControl(4100).setLabel(msg)

	def showOptionsRight(self, obj):
		self.setOptionsRight(obj)
		self.optionsHasFocus()

	def saveAlbumAsPlaylist(self, selected = 0, obj = None, item = None):
		album = obj.get(selected)
		name = album.artistName + ' - ' + album.name
		name = self.getInput('Name for playlist', default=name)
		if name == None:
			return
		if name != '':
			lock()
			try:
				songs = album.getSongs(self.gs)
				info = {'Name': name, 'PlaylistID': -1, 'About': ''}
				Playlist(info, songs = songs).saveAs(self.gs)
				unlock()
				self.notification('Saved')
			except:
				unlock()
				self.notification('Sorry')
		else:
			unlock()
			self.notification('Type a name')

	def addSongToPlaylist(self, selected = 0, obj = None, item = None):
		lock()
		try:
			songs = obj
			self.setOptionsPlaylists(songs.get(selected))		
			unlock()
			cnt = self.getControl(500)
			self.setFocus(cnt)
		except:
			unlock()
			self.notification('Sorry')			
			traceback.print_exc()
		pass

	def addSongToPlaylistExec(self, selected = 0, obj = None, item = None):
		lock()
		song = item['song']
		playlist = item['playlist']
		playlist.getSongs(self.gs)
		playlist.addSong(song)
		playlist.save(self.gs)
		unlock()
		self.notification('Added')

	def exit(self, selected = 0, obj = None, item = None):
		self.close()

	def settings(self, selected = 0, obj = None, item = None):
		try:
			username = __settings__.getSetting('username')
			password = __settings__.getSetting('password')
			core = __settings__.getSetting('player_core')
			debug = __settings__.getSetting('debug')
			__settings__.openSettings()
			#try:
			#	self.searchLimit = int(__settings__.getSetting('search_limit'))
			#except:
			#	self.searchLimit = 100
			#self.gs.setRemoveDuplicates(__settings__.getSetting('remove_duplicates'))
			#self.useCoverArt = self.convertToBool(__settings__.getSetting('covers_in_script'))
			#self.useCoverArtNowPlaying = self.convertToBool(__settings__.getSetting('cover_now_playing'))
			# Check to see if things have changed:
			if __settings__.getSetting('username') != username or __settings__.getSetting('password') != password:
				self.gs.startSession(__settings__.getSetting('username'), __settings__.getSetting('password'))
			if __settings__.getSetting('player_core') != core:
				self.initPlayer()
			if __settings__.getSetting('debug') != debug:
				debug = __settings__.getSetting('debug')
				if debug == 'false':
					__debugging__ = False
				else:
					__debugging__ = True
				self.gs._enableDebug(__debugging__)
		except:
			traceback.print_exc()

	def newSearch(self, selected = 0, obj = None, item = None):
		self.playlistHasFocus()
		search = SearchGUI()
		#text = self.getInput(__language__(1000), "") 
		result = search.getResult()
		if result != None:
			lock()
			try:
				text = result['query']
				self.rootTree.tree[0].search(query= text, gsapi = self.gs)
				self.navi.updateList(0, 0)
				self.navi._list()
				unlock()
			except:
				unlock()
				self.notification('Sorry')

	def deletePlaylist(self, selected = 0, obj = None, item = None):
		lock()
		try:
			playlist = obj.get(selected)
			playlist.delete(self.gs)
			self.navi.updateList(0, 3, selected = selected) #Reload playlists
			unlock()
			self.notification('Deleted')
		except:
			unlock()
			self.notification('Sorry')

	def renamePlaylist(self, selected = 0, obj = None, item = None):
		playlist = obj.get(selected)
		name = self.getInput(__language__(111), default=playlist.name)
		if name != '' and name != None:
			lock()
			try:
				playlist.rename(self.gs, name)
				self.navi.updateList(0, 3, selected = selected) #Reload playlists
				unlock()
				self.notification('Renamed')
			except:
				unlock()
				self.notification('Sorry')

	def play(self, selected = 0, obj = None, item = None):
		lock()
		try:
			obj.play(selected = selected, gsapi = self.gs, playlist = self.xbmcPlaylist)
			unlock()
		except:
			unlock()
			self.notification('Sorry')
			traceback.print_exc()

	def queueSong(self, selected = 0, obj = None, item = None):
		lock()
		try:
			song = obj.get(selected)
			obj.queue(song, playlist = self.xbmcPlaylist)
			unlock()
			self.notification('Queued')
		except:
			unlock()
			self.notification('Sorry')

	def queueAllSongs(self, selected = 0, obj = None, item = None):
		lock()
		try:
			obj.queueAll(playlist = self.xbmcPlaylist, append = True)
			unlock()
			self.notification('Queued')
		except:
			unlock()
			self.notification('Sorry')

	def playAlbum(self, selected = 0, obj = None, item = None):
		lock()
		try:
			album = obj.get(selected)
			songs = album.getSongs(self.gs)
			songs.play(selected = 0, gsapi = self.gs, playlist = self.xbmcPlaylist)
			unlock()
		except:
			unlock()
			self.notification('Sorry')

	def queueAlbum(self, selected = 0, obj = None, item = None):
		lock()
		try:
			album = obj.get(selected)
			songs = album.getSongs(self.gs)
			songs.queueAll(playlist = self.xbmcPlaylist, append = True)
			unlock()
			self.notification('Queued')
		except:
			unlock()
			self.notification('Sorry')

	def playSongsByArtist(self, selected = 0, obj = None, item = None):
		lock()
		try:
			artist = obj.get(selected)
			songs = artist.getSongs(self.gs)
			songs.play(selected = 0, gsapi = self.gs, playlist = self.xbmcPlaylist)
			unlock()
		except:
			unlock()
			self.notification('Sorry')

	def showPlaylists(self, selected = 0, obj = None, item = None):
		self.navi.updateList(0, 3)
		self.navi._list()

	def showNowPlaying(self, selected = 0, obj = None, item = None):
		self.navi.updateList(0, 4)
		self.navi._list()
		return
		#Disable the old way for now
		wId = xbmcgui.getCurrentWindowId()
		gWin = xbmcgui.Window(wId)
		pWin = xbmcgui.Window(10500)
		selected = self.getCurrentListPosition()
		self.navi.setSelected(selected)
		pWin.show()
		while xbmcgui.getCurrentWindowId() == 10500: #Music playlist
			xbmc.sleep(100)
			pass
		while xbmcgui.getCurrentWindowId() == 12006:#Visualization
			xbmc.sleep(100)
		if xbmcgui.getCurrentWindowId() != wId:
			gWin.show()
		self.navi._list()

	def findSimilarFromSong(self, selected = 0, obj = None, item = None):
		lock()
		try:
			song = obj.get(selected)
			artist = Artist(song.artistID)
			artists = artist.similar(gsapi = self.gs)
			self.navi.down(artists, selected+1)
			unlock()
		except:
			unlock()
			self.notification('Sorry')

	def findSimilarFromAlbum(self, selected = 0, obj = None, item = None):
		lock()
		try:
			album = obj.get(selected)
			artist = Artist(album.artistID)
			artists = artist.similar(gsapi = self.gs)
			self.navi.down(artists, selected+1)
			unlock()
		except:
			unlock()
			self.notification('Sorry')

	def findSimilarFromArtist(self, selected = 0, obj = None, item = None):
		lock()
		try:
			artist = obj.get(selected)
			artists = artist.similar(gsapi = self.gs)
			self.navi.down(artists, selected+1)
			unlock()
		except:
			unlock()
			self.notification('Sorry')

	def songsOnAlbum(self, selected = 0, obj = None, item = None):
		lock()
		try:
			song = obj.get(selected)
			albumId = song.albumID
			songs = Album(albumId, defaultCoverArt = self.defaultCoverArt).getSongs(gsapi = self.gs)
			self.navi.down(songs, selected+1)
			unlock()
		except:
			unlock()
			self.notification('Sorry')

	def message(self, message, title = ''):
		dialog = xbmcgui.Dialog()
		dialog.ok(title, message)

	def onInit(self):
		setPGUI(self)
		try:
			if self.initialized == True:
				self.navi._list()
				pass
		except:
			self.initVars()
			self.loadState()
			try:
				self.gs = GrooveAPI(enableDebug = __debugging__, cwd = self.confDir ,clientUuid = None, clientVersion = None)
				username = __settings__.getSetting("username")
				password = __settings__.getSetting("password")
				self.gs.startSession(username, password)
				self.gs.setRemoveDuplicates(__settings__.getSetting('remove_duplicates'))
			except:
				self.message(__language__(3046), __language__(3011)) #Unable to get new session ID
				xbmc.log('GrooveShark Exception (onInit): ' + str(sys.exc_info()[0]))
				traceback.print_exc()
				self.close()
				return
			self.initialized = True
			self.initPlayer()
			self.optionsRight = Options(self.getControl(500), self.getControl(4100), self.getControl(410), self)
			self.optionsPlaylists = Options(self.getControl(500), self.getControl(4100), self.getControl(410), self)
			self.optionsMenu = Options(self.getControl(500), self.getControl(4100), self.getControl(410), self)
			self.navi = Navigation(self, self.gs, displayCallBack = self.displayItems, optionsCallBack = self.setOptionsRight, optionsShowCallback = self.showOptionsRight)
			self.rootTree = RootTree(self, self.gs, defaultCoverArt = os.path.join(self.imageDir, 'default-cover.png'))
			self.navi.down(self.rootTree)

	def __del__(self):
		print 'GrooveShark: __del__() called'
		self.saveState()

	def initPlayer(self):
		try:
			core = __settings__.getSetting('player_core')
			if core == 'MPlayer':
				self.player = GroovePlayer(xbmc.PLAYER_CORE_MPLAYER)
			elif core == 'DVDPlayer':
				self.player = GroovePlayer(xbmc.PLAYER_CORE_DVDPLAYER)
			elif core == 'PAPlayer':
				self.player = GroovePlayer(xbmc.PLAYER_CORE_PAPLAYER)
			else:
				self.player = GroovePlayer()
			print 'GrooveShark: Player core: ' + core
			self.player.setCallBackFunc(self.playerChanged)
		except:
			xbmc.log('GrooveShark Exception (initPlayer): ' + str(sys.exc_info()[0]))
			traceback.print_exc()
		
	def onFocus(self, controlID):
		self.debug('onFocus(): id = ' + str(controlID)					)
		pass

	def onAction(self, action):
		aId = action.getId()
		if aId == 10:
			if self.getFocusId() == 500:
				self.playlistHasFocus()
			else:
				self.setOptionsMenu()
				self.optionsHasFocus()
		elif aId == 1:
			cid = self.getFocusId()
			if cid != 500:
				self.setOptionsMenu()
				self.optionsHasFocus()
			else:
				self.playlistHasFocus()

		elif aId == 2:
			cid = self.getFocusId()
			if cid != 500:
				self.setOptionsRight(self.navi.getBranchObject())
				self.optionsHasFocus()
			else:
				self.playlistHasFocus()

		elif aId == 9:
			self.navi.up()
		else:
			pass
 
	def onClick(self, control):
		self.debug('onClick: ' + str(control))
		if control == 500:
			self.options.execute()
			if self.options == self.optionsRight:
				pass #FIXME

		elif control == 50:
			self.setOptionsRight(self.navi.getBranchObject())
			self.navi.navigate(self.getCurrentListPosition())
		else:
			pass
	
	def debug(self, msg):
		if __debugging__ == True:
			print 'GrooveShark: ' + str(msg)

	def convertToBool(self, s):
		if s == 'true' or s == 'True' or s == True:
			return True
		else:
			return False

	def initVars(self):
		self.nowPlayingList = []
		self.searchText = ""
		self.rootDir = __cwd__
		self.xbmcPlaylist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
		self.defaultCoverArt = os.path.join(__cwd__,'resources','skins','DefaultSkin', 'media','default-cover.png')
		#try:
		#	self.searchLimit = int(__settings__.getSetting('search_limit'))
		#except:
		#	self.searchLimit = 100
		#self.useCoverArt = self.convertToBool(__settings__.getSetting('covers_in_script'))
		self.useCoverArt = True
		#self.useCoverArtNowPlaying = self.convertToBool(__settings__.getSetting('cover_now_playing'))
		if __isXbox__ == True:
			self.dataDir = 'script_data'
			dataRoot = os.path.join('special://profile/', self.dataDir)
			if os.path.exists(dataRoot) == False:
				os.mkdir(dataRoot)
		else:
			self.dataDir = 'addon_data'

		self.imageDir = os.path.join(__cwd__,'resources','skins','DefaultSkin', 'media')
		self.confDir = os.path.join('special://profile/', self.dataDir, __scriptid__)
		self.defaultArtTinyUrl = 'http://beta.grooveshark.com/webincludes/img/defaultart/album/tdefault.png'
		self.defaultArtSmallUrl = 'http://beta.grooveshark.com/webincludes/img/defaultart/album/sdefault.png'
		self.defaultArtMediumUrl = 'http://beta.grooveshark.com/webincludes/img/defaultart/album/mdefault.png'

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
			self.playlistId,\
			self.playlistName,\
			self.searchText,\
			self.rootDir,\
			self.location,\
			self.nowPlayingList = pickle.load(f)
			f.close()
			return True
		except:
			self.debug(str(sys.exc_info()[0]))
			return False
			pass		

	def getState(self):
		# Use this instead of __getstate__() for pickling
		return (self.playlistId,\
		self.playlistName,\
		self.searchText,\
		self.rootDir,\
		self.location,\
		self.nowPlayingList)

	def truncateText(self, text, n):
		if len(text) > n:
			return text[0:n-3] + '...'
		else:
			return text

	def isRadioOn(self):
		protocol = 'plugin://' + __scriptid__ + '/?playSong'
		songList = []
		try:
			url = self.xbmcPlaylist[0].getfilename()
		except:
			return False
		parts = url.split('=')
		try:
			if parts[0] == protocol:
				parts = url.split('&')
				print parts[2]
				if parts[2] == 'options=radio':
					return True
			else:
				return False
		except:
			return False

	def replaceCharacters(self, text, items):
		newText = text
		for item in items:
			newText = newText.replace(item['searchFor'], item['replaceWith'])
		return newText

	def playlistHasFocus(self):
		self.setFocus(self.getControl(205))

	def optionsHasFocus(self):
		if self.navi.hasBack() == True:
			n = self.getCurrentListPosition()
			if n == 0:
				#self.getControl(500).setVisible(False)
				print 'Updating options, back = True'
				self.options.update(n-1, back = True)
			else:
				print 'Updating options, back = False'
				obj = self.navi.getBranchObject()
				self.options.update(n-1, back = False, obj = obj)
		self.setFocusId(500)

	def playerChanged(self, event, windowId = None):
		if event == 0: # Stopped
			pass
			
		elif event == 1: # Ended
			if __isXbox__ == True:
				self.playNextSong()
				if windowId != None:
					if windowId == 12006: #Visualization
						xbmcgui.Window(windowId).show()
			
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
			if __isXbox__ == True:
				self.playNextSong()
				if windowId != None:
					if windowId == 12006: #Visualization
						xbmcgui.Window(windowId).show()
			pass
													
	def getInput(self, title, default="", hidden=False):
		keyboard = xbmc.Keyboard(default, title)
		keyboard.setHiddenInput(hidden)
		keyboard.doModal()
		if keyboard.isConfirmed():
			return keyboard.getText()
		else:
			return None
				
	def savePlaylist(self, playlistId = 0, name = '', about = '', songList = []):
		try:
			if self.gs.loggedInStatus() != 1:
				result = self.login()
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
