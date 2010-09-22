import xbmc
import sys
import os
import traceback
import threading

#path = os.path.abspath(os.path.join(os.getcwd(), '..', 'script.module.pysqlite', 'lib', 'pysqlite2'))
#sys.path.append(path)
from pysqlite2 import dbapi2 as sqlite

__language__ = sys.modules[ "__main__" ].__language__

class musicdb(object):
	def __init__(self, path):
		self.db = sqlite.connect(path)
		self.db.text_factory = str
		self.cursor = self.db.cursor()
	
	def __del__(self):
		self.db.close()

	def getArtists(self, query):
		sql = 'select artist from artists where artist like "' + query + '%" order by artist'
		self.cursor.execute(sql)
		result = self.cursor.fetchmany(20)
		return self.tupleToList(result)

	def getSongs(self, query):
		sql = 'select song from songs where song like "%' + query + '%" order by song'
		self.cursor.execute(sql)
		result = self.cursor.fetchmany(20)
		return self.tupleToList(result)

	def getAlbums(self, query):
		sql = 'select album from albums where album like "' + query + '%" order by album'
		self.cursor.execute(sql)
		result = self.cursor.fetchmany(20)
		return self.tupleToList(result)

	def tupleToList(self, tuple_):
		list_ = []
		for item in tuple_:
			list_.append(item[0])
		return list_

class getTextThread(threading.Thread):
	def __init__(self, keyboard, cwd, returnResults):
		threading.Thread.__init__(self)
		self.running = 1
		self.keyboard = keyboard
		self.cwd = cwd
		self.returnResults = returnResults
		pass

	def run (self):
		path = os.path.join(self.cwd, 'musicdb.db')
		self.db = musicdb(path)
		oldText = ''
		while self.running == 1:
			newText = self.keyboard.getText()
			if newText != oldText:
				oldText = newText
				if newText != '':
					songs, artists, albums = self.searchDatabase(newText)
					if len(songs) == 0:
						songs = ['<' + __language__(3050) + '>']
					if len(artists) == 0:
						artists = ['<' + __language__(3050) + '>']
					if len(albums) == 0:
						albums = ['<' + __language__(3050) + '>']
					self.returnResults(songs, artists, albums)
				else:
					self.returnResults(['<' + __language__(3050) + '>'], ['<' + __language__(3050) + '>'], ['<' + __language__(3050) + '>']) #FIXME
				#print res
			xbmc.sleep(100)

	def searchDatabase(self, query):
		db = self.db
		songs = db.getSongs(query)
		artists = db.getArtists(query)
		albums = db.getAlbums(query)
		return songs, artists, albums
	
	def closeThread(self):
		self.running = 0
