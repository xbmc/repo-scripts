

import os, sys, shutil

from util import *
import util

try:
	from sqlite3 import dbapi2 as sqlite
	Logutil.log("Loading sqlite3 as DB engine", util.LOG_LEVEL_INFO)
except:
	from pysqlite2 import dbapi2 as sqlite
	Logutil.log("Loading pysqlite2 as DB engine", util.LOG_LEVEL_INFO)


class GameDataBase:
	
	def __init__(self, databaseDir):		
		self.dataBasePath = os.path.join(databaseDir, 'MyGames.db')
		sqlite.register_adapter(str, lambda s:s.decode('utf-8'))
		#use scripts home for reading SQL files
		self.sqlDir = os.path.join(util.RCBHOME, 'resources', 'database')		
		
	def connect( self ):
		print self.dataBasePath
		self.connection = sqlite.connect(self.dataBasePath, check_same_thread = False)
		self.cursor = self.connection.cursor()
		
	def commit( self ):		
		try:
			self.connection.commit()
			return True
		except: return False

	def close( self ):
		print "close Connection"
		self.connection.close()
	
	def compact(self):
		self.cursor.execute("VACUUM")
		
	def toMem(self):
		try:
			memDB = sqlite.connect(':memory:', check_same_thread = False)
			dump = os.linesep.join([line for line in self.connection.iterdump()])
			memDB.executescript(dump)
			self.connection.close()
			self.connection = memDB
			self.cursor = memDB.cursor()
			return True
		except Exception, e: 
			util.Logutil.log("ERROR: %s" % str(e), util.LOG_LEVEL_INFO)
			return False	
	
	def toDisk(self):
		try:
			self.connection.commit()
			os.remove(self.dataBasePath)
			diskDB = sqlite.connect(self.dataBasePath)
			dump = os.linesep.join([line for line in self.connection.iterdump()])
			diskDB.executescript(dump)
			self.connection.close()
			self.connection = diskDB
			self.cursor = diskDB.cursor()
			return True
		except Exception, e: 
			util.Logutil.log("ERROR: %s" % str(e), util.LOG_LEVEL_INFO)
			return False
	
	def executeSQLScript(self, scriptName):
		sqlCreateFile = open(scriptName, 'r')
		sqlCreateString = sqlCreateFile.read()						
		self.connection.executescript(sqlCreateString)		
	
	def createTables(self):
		print "Create Tables"		
		self.executeSQLScript(os.path.join(self.sqlDir, 'SQL_CREATE.txt'))
		RCBSetting(self).insert((None, None, None, None, None, None, None, util.CURRENT_DB_VERSION, None, None, None))
		
	def dropTables(self):
		print "Drop Tables"
		self.executeSQLScript(os.path.join(self.sqlDir, 'SQL_DROP_ALL.txt'))

	
	def checkDBStructure(self):
		
		#returnValues: -1 error, 0=nothing, 1=import Games, 2=idLookupFile created
		
		dbVersion = ""
		try:
			rcbSettingRows = RCBSetting(self).getAll()
			if(rcbSettingRows == None or len(rcbSettingRows) != 1):	
				self.createTables()
				self.commit()
				return 1, ""
			rcbSetting = rcbSettingRows[0]
			
			#HACK: reflect changes in RCBSetting
			dbVersion = rcbSetting[util.RCBSETTING_dbVersion]
			if(dbVersion == None):
				dbVersion = rcbSetting[10]
			
		except  Exception, (exc): 
			self.createTables()
			self.commit()
			return 1, ""
		
		#Alter Table
		if(dbVersion != util.CURRENT_DB_VERSION):
			alterTableScript = "SQL_ALTER_%(old)s_%(new)s.txt" %{'old': dbVersion, 'new':util.CURRENT_DB_VERSION}
			alterTableScript = str(os.path.join(self.sqlDir, alterTableScript))
			
			if os.path.isfile(alterTableScript):
				#backup MyGames.db				
				newFileName = self.dataBasePath +'.backup ' +dbVersion 
				
				if os.path.isfile(newFileName):					
					return -1, util.localize(32030)				
				try:
					self.close()
					shutil.copy(str(self.dataBasePath), str(newFileName))
					self.connect()
				except Exception, (exc):					
					return -1, util.localize(32031) +": " +str(exc)
								
				self.executeSQLScript(alterTableScript)
				self.commit()
				return returnCode, message
			else:
				return -1, util.localize(32032) %(dbVersion, util.CURRENT_DB_VERSION)
					
		count = Game(self).getCount()
		if(count == 0):
			return 1, ""
		
		return 0, ""
	

class DataBaseObject:
	
	def __init__(self, gdb, tableName):
		self.gdb = gdb
		self.tableName = tableName
	
	def insert(self, args):		
		paramsString = ( "?, " * len(args))
		paramsString = paramsString[0:len(paramsString)-2]
		insertString = "Insert INTO %(tablename)s VALUES (NULL, %(args)s)" % {'tablename':self.tableName, 'args': paramsString }		
		self.gdb.cursor.execute(insertString, args)
		
		#print("Insert INTO %(tablename)s VALUES (%(args)s)" % {'tablename':self.tableName, 'args': ( "?, " * len(args)) })
		
	
	def update(self, columns, argsOrig, id, updateWithNullValues):
		
		if(len(columns) != len(argsOrig)):
			util.Logutil.log("len columns != len args in gdb.update()", util.LOG_LEVEL_WARNING)			
			return
			
		args = []
		updateString = "Update %s SET " %self.tableName
		for i in range(0, len(columns)):
			#don't update with empty values
			if(not updateWithNullValues and (argsOrig[i] == '' or argsOrig[i] == None)):
				continue
			
			args.append(argsOrig[i])
			updateString += columns[i] +  " = ?"
			if(i < len(columns) -1):
				updateString += ", "
				
		updateString += " WHERE id = " +str(id)
		self.gdb.cursor.execute(updateString, args)
		
	
	def deleteAll(self):
		self.gdb.cursor.execute("DELETE FROM '%s'" % self.tableName)		
	
	
	def deleteObjectByQuery(self, query, args):
		self.gdb.cursor.execute(query, args)
		
	def getCount(self):
		self.gdb.cursor.execute("SELECT count(*) From '%s'" % self.tableName)
		count = self.gdb.cursor.fetchall()
		return count[0][0]
		
	def getAll(self):
		self.gdb.cursor.execute("SELECT * FROM '%s'" % self.tableName)
		allObjects = self.gdb.cursor.fetchall()
		newList = self.encodeUtf8(allObjects)
		return newList
		
		
	def getAllOrdered(self):		
		self.gdb.cursor.execute("SELECT * FROM '%s' ORDER BY name COLLATE NOCASE" % self.tableName)
		allObjects = self.gdb.cursor.fetchall()
		newList = self.encodeUtf8(allObjects)
		return newList		
		
		
	def getOneByName(self, name):			
		self.gdb.cursor.execute("SELECT * FROM '%s' WHERE name = ?" % self.tableName, (name,))
		object = self.gdb.cursor.fetchone()
		return object
		
	def getObjectById(self, id):
		self.gdb.cursor.execute("SELECT * FROM '%s' WHERE id = ?" % self.tableName, (id,))
		object = self.gdb.cursor.fetchone()		
		return object	
	
	def getObjectsByWildcardQuery(self, query, args):		
		#double Args for WildCard-Comparison (0 = 0)
		newArgs = []
		for arg in args:
			newArgs.append(arg)
			newArgs.append(arg)
					
		return self.getObjectsByQuery(query, newArgs)		
		
	def getObjectsByQuery(self, query, args):
		self.gdb.cursor.execute(query, args)
		allObjects = self.gdb.cursor.fetchall()		
		return allObjects
		
	def getObjectsByQueryNoArgs(self, query):
		self.gdb.cursor.execute(query)
		allObjects = self.gdb.cursor.fetchall()		
		return allObjects

	def getObjectByQuery(self, query, args):		
		self.gdb.cursor.execute(query, args)
		object = self.gdb.cursor.fetchone()		
		return object
	
	def getFileAllFilesByRCId(self, id):
		self.gdb.cursor.execute('select File.name from File, Game where Game.romcollectionid=? and File.parentId=Game.id and File.fileTypeId=0', (id,))
		objects = self.gdb.cursor.fetchall()
		results = [r[0] for r in objects]
		return results
	
	def encodeUtf8(self, list):
		newList = []
		for item in list:
			newItem = []
			for param in item:
				if type(param).__name__ == 'str':
					newItem.append(param.encode('utf-8'))
				else:
					newItem.append(param)
			newList.append(newItem)
		return newList


class Game(DataBaseObject):	
	filterQuery = "Select * From Game WHERE \
					(romCollectionId = ? OR (0 = ?)) AND \
					(Id IN (Select GameId From GenreGame Where GenreId = ?) OR (0 = ?)) AND \
					(YearId = ? OR (0 = ?)) AND \
					(PublisherId = ? OR (0 = ?)) AND \
					(isFavorite = ? OR (0 = ?)) \
					AND %s \
					ORDER BY name COLLATE NOCASE \
					%s"
					
	filterByNameAndRomCollectionId = "SELECT * FROM Game WHERE name = ? and romCollectionId = ?"
	
	filterMostPlayedGames = "Select * From Game Where launchCount > 0 Order by launchCount desc Limit "
	
	deleteQuery = "DELETE FROM Game WHERE id = ?"
	
	def __init__(self, gdb):
		self.gdb = gdb
		self.tableName = "Game"
		
	def getFilteredGames(self, romCollectionId, genreId, yearId, publisherId, isFavorite, likeStatement, maxNumGames=0):
		args = (romCollectionId, genreId, yearId, publisherId, isFavorite)
		limit = ""
		if(int(maxNumGames) > 0):
			limit = "LIMIT %s" %str(maxNumGames)
		filterQuery = self.filterQuery %(likeStatement, limit)
		util.Logutil.log('searching games with query: ' +filterQuery, util.LOG_LEVEL_DEBUG)
		util.Logutil.log('searching games with args: romCollectionId = %s, genreId = %s, yearId = %s, publisherId = %s, isFavorite = %s, likeStatement = %s, limit = %s' %(str(romCollectionId), str(genreId), str(yearId), str(publisherId), str(isFavorite), likeStatement, limit), util.LOG_LEVEL_DEBUG)
		games = self.getObjectsByWildcardQuery(filterQuery, args)
		newList = self.encodeUtf8(games)
		return newList
		
	def getGameByNameAndRomCollectionId(self, name, romCollectionId):
		game = self.getObjectByQuery(self.filterByNameAndRomCollectionId, (name, romCollectionId))
		return game
		
	def getMostPlayedGames(self, count):
		if(str.isdigit(str(count))):
			filter = self.filterMostPlayedGames +str(count)
		else:
			filter = self.filterMostPlayedGames +str(10)
		games = self.getObjectsByQuery(filter, [])
		return games
		
	def delete(self, gameId):
		self.deleteObjectByQuery(self.deleteQuery, (gameId,))

class RCBSetting(DataBaseObject):	
	def __init__(self, gdb):		
		self.gdb = gdb
		self.tableName = "RCBSetting"


class Genre(DataBaseObject):
	
	#obsolete: atm genres are only filtered by console
	filterQuery = "SELECT * FROM Genre WHERE Id IN (Select GenreId From GenreGame Where GameId IN ( \
    					Select Id From Game WHERE \
						(romCollectionId = ? OR (0 = ?)) AND \
						(YearId = ? OR (0 = ?)) AND \
						(PublisherId = ? OR (0 = ?)) \
						AND %s)) \
						ORDER BY name COLLATE NOCASE"
						
	filterGenreByConsole = "SELECT * FROM Genre WHERE Id IN (Select GenreId From GenreGame Where GameId IN ( \
    					Select Id From Game WHERE \
						(romCollectionId = ? OR (0 = ?)))) \
						ORDER BY name COLLATE NOCASE"
	
	filteGenreByGameId = "SELECT * FROM Genre WHERE Id IN (Select GenreId From GenreGame Where GameId = ?)"
	
	filteGenreIdByGameId = "SELECT GenreId From GenreGame Where GameId = ?"
	
	genreIdCountQuery = "SELECT g.genreid, count(*) 'genreIdCount' \
					from genregame g \
					inner join genregame g2 \
					on g.genreid=g2.genreid \
					where g.gameid = ? \
					group by g.genreid"
	
	genreDeleteQuery = "DELETE FROM Genre WHERE id = ?"
	
	genreGameDeleteQuery = "DELETE FROM GenreGame WHERE gameId = ?"
	
	def __init__(self, gdb):		
		self.gdb = gdb
		self.tableName = "Genre"
		
	def getFilteredGenres(self, romCollectionId, yearId, publisherId, likeStatement):
		args = (romCollectionId, yearId, publisherId)
		filterQuery = self.filterQuery %likeStatement
		util.Logutil.log('searching genres with query: ' +filterQuery, util.LOG_LEVEL_DEBUG)
		genres = self.getObjectsByWildcardQuery(filterQuery, args)
		return genres
	
	def getFilteredGenresByConsole(self, romCollectionId):
		genres = self.getObjectsByWildcardQuery(self.filterGenreByConsole, (romCollectionId,))
		return genres
		
	def getGenresByGameId(self, gameId):
		genres = self.getObjectsByQuery(self.filteGenreByGameId, (gameId,))
		return genres

	def getGenreIdByGameId(self, gameId):
		genreId = self.getObjectsByQuery(self.filteGenreIdByGameId, (gameId,))
		return genreId
		
	def delete(self, gameId):
		#genreId = self.getGenreIdByGameId(gameId)
		self.gdb.cursor.execute(self.genreIdCountQuery, (gameId,))	
		object = self.gdb.cursor.fetchall()
		if(object != None):
			for items in object:	
				if (items[1] < 2):
					util.Logutil.log("Delete Genre with id %s" % str(items[0]), util.LOG_LEVEL_INFO)
					self.deleteObjectByQuery(self.genreDeleteQuery, (items[0],))
		util.Logutil.log("Delete GenreGame with gameId %s" % str(gameId), util.LOG_LEVEL_INFO)
		self.deleteObjectByQuery(self.genreGameDeleteQuery, (gameId,))

class GenreGame(DataBaseObject):
					
	filterQueryByGenreIdAndGameId = "Select * from GenreGame \
					where genreId = ? AND \
					gameId = ?"
	
	def __init__(self, gdb):		
		self.gdb = gdb
		self.tableName = "GenreGame"
		
	def getGenreGameByGenreIdAndGameId(self, genreId, gameId):
		genreGame = self.getObjectByQuery(self.filterQueryByGenreIdAndGameId, (genreId, gameId))
		return genreGame


class Year(DataBaseObject):
	
	yearIdByGameIdQuery = "SELECT yearId From Game Where Id = ?"
	
	#obsolete: atm years are only filtered by console
	filterQuery = "SELECT * FROM Year WHERE Id IN (Select YearId From Game WHERE \
					    (romCollectionId = ? OR (0 = ?)) AND \
					    (PublisherId = ? OR (0 = ?)) \
					    AND id IN \
					    (SELECT GameId From GenreGame Where GenreId = ? OR (0 = ?)) \
					    AND %s) \
					    ORDER BY name COLLATE NOCASE"
					    
	filterYearByConsole = "SELECT * FROM Year WHERE Id IN (Select YearId From Game WHERE \
					    (romCollectionId = ? OR (0 = ?))) \
					    ORDER BY name COLLATE NOCASE"
	
	yearIdCountQuery = "SELECT count(yearId) 'yearIdCount' \
					from Game \
					where yearId = ? \
					group by yearId"
	
	yearDeleteQuery = "DELETE FROM Year WHERE id = ?"


	def __init__(self, gdb):		
		self.gdb = gdb
		self.tableName = "Year"
		
	def getYearIdByGameId(self, gameId):
		yearId = self.getObjectByQuery(self.yearIdByGameIdQuery, (gameId,))
		if(yearId == None):
			return None
		else:
			return yearId[0]
	
	def getFilteredYears(self, romCollectionId, genreId, publisherId, likeStatement):
		args = (romCollectionId, publisherId, genreId)
		filterQuery = self.filterQuery %likeStatement
		util.Logutil.log('searching years with query: ' +filterQuery, util.LOG_LEVEL_DEBUG)		
		years = self.getObjectsByWildcardQuery(filterQuery, args)
		return years
	
	def getFilteredYearsByConsole(self, romCollectionId):
		years = self.getObjectsByWildcardQuery(self.filterYearByConsole, (romCollectionId,))
		return years
	
	def delete(self, gameId):
		yearId = self.getYearIdByGameId(gameId)	
		if(yearId != None):	
			object = self.getObjectByQuery(self.yearIdCountQuery, (yearId,))
			if (object[0] < 2):
				util.Logutil.log("Delete Year with id %s" % str(yearId), util.LOG_LEVEL_INFO)
				self.deleteObjectByQuery(self.yearDeleteQuery, (yearId,))


class Publisher(DataBaseObject):	

	publisherIdByGameIdQuery = "SELECT publisherId From Game Where Id = ?"
	
	filterQuery = "SELECT * FROM Publisher WHERE Id IN (Select PublisherId From Game WHERE \
					    (romCollectionId = ? OR (0 = ?)) AND \
					    (YearId = ? OR (0 = ?)) \
					    AND id IN \
					    (SELECT GameId From GenreGame Where GenreId = ? OR (0 = ?)) \
					    AND %s) \
					    ORDER BY name COLLATE NOCASE"
					    
	filterPublishersByConsole = "SELECT * FROM Publisher WHERE Id IN (Select PublisherId From Game WHERE \
					    (romCollectionId = ? OR (0 = ?))) \
					    ORDER BY name COLLATE NOCASE"
	
	publisherIdCountQuery = "SELECT count(publisherId) 'publisherIdCount' \
					from Game \
					where publisherId = ? \
					group by publisherId"
	
	publisherDeleteQuery = "DELETE FROM Publisher WHERE id = ?"


	def __init__(self, gdb):		
		self.gdb = gdb
		self.tableName = "Publisher"
		
	def getPublisherIdByGameId(self, gameId):
		publisherId = self.getObjectByQuery(self.publisherIdByGameIdQuery, (gameId,))
		if(publisherId == None):
			return None
		else:
			return publisherId[0]
		
	def getFilteredPublishers(self, romCollectionId, genreId, yearId, likeStatement):
		args = (romCollectionId, yearId, genreId)
		filterQuery = self.filterQuery %likeStatement
		util.Logutil.log('searching publishers with query: ' +filterQuery, util.LOG_LEVEL_DEBUG)		
		publishers = self.getObjectsByWildcardQuery(filterQuery, args)
		return publishers
	
	def getFilteredPublishersByConsole(self, romCollectionId):
		publishers = self.getObjectsByWildcardQuery(self.filterPublishersByConsole, (romCollectionId,))
		return publishers
	
	def delete(self, gameId):
		publisherId = self.getPublisherIdByGameId(gameId)
		if(publisherId != None):
			object = self.getObjectByQuery(self.publisherIdCountQuery, (publisherId,))
			if (object[0] < 2):
				util.Logutil.log("Delete Publisher with id %s" % str(publisherId), util.LOG_LEVEL_INFO)
				self.deleteObjectByQuery(self.publisherDeleteQuery, (publisherId,))


class Developer(DataBaseObject):

	developerIdByGameIdQuery = "SELECT developerId From Game Where Id = ?"
	
	developerIdCountQuery = "SELECT count(developerId) 'developerIdCount' \
					from Game \
					where developerId = ? \
					group by developerId"
	
	developerDeleteQuery = "DELETE FROM Developer WHERE id = ?"


	def __init__(self, gdb):		
		self.gdb = gdb
		self.tableName = "Developer"

	def getDeveloperIdByGameId(self, gameId):
		developerId = self.getObjectByQuery(self.developerIdByGameIdQuery, (gameId,))
		if(developerId == None):
			return None
		else:
			return developerId[0]
	
	def delete(self, gameId):
		developerId = self.getDeveloperIdByGameId(gameId)
		if(developerId != None):
			object = self.getObjectByQuery(self.developerIdCountQuery, (developerId,))
			if (object[0] < 2):
				util.Logutil.log("Delete Developer with id %s" % str(developerId), util.LOG_LEVEL_INFO)
				self.deleteObjectByQuery(self.developerDeleteQuery, (developerId,))
		
		
class Reviewer(DataBaseObject):
	def __init__(self, gdb):		
		self.gdb = gdb
		self.tableName = "Reviewer"


class File(DataBaseObject):	
	filterQueryByGameIdAndFileType = "Select name from File \
					where parentId = ? AND \
					filetypeid = ?"
					
	filterQueryByNameAndType = "Select * from File \
					where name = ? AND \
					filetypeid = ?"
					
	filterQueryByNameAndTypeAndParent = "Select * from File \
					where name = ? AND \
					filetypeid = ? AND \
					parentId = ?"
					
	filterQueryByGameIdAndTypeId = "Select * from File \
					where parentId = ? AND \
					filetypeid = ?"
					
	filterFilesForGameList = "Select * from File Where FileTypeId in (%s)"
					
	filterQueryByParentIds = "Select * from File \
					where parentId in (?, ?, ?, ?)"
	
	getFileList = "SELECT * FROM File WHERE filetypeid = 0"
	
	deleteQuery = "DELETE FROM File WHERE parentId= ?"
	
	deleteFileQuery = "DELETE FROM File WHERE Id= ?"
	def __init__(self, gdb):		
		self.gdb = gdb
		self.tableName = "File"
			
	def getFileByNameAndType(self, name, type):
		file = self.getObjectByQuery(self.filterQueryByNameAndType, (name, type))
		return file
		
	def getFileByNameAndTypeAndParent(self, name, type, parentId):
		file = self.getObjectByQuery(self.filterQueryByNameAndTypeAndParent, (name, type, parentId))
		return file
		
	def getFilesByNameAndType(self, name, type):
		files = self.getObjectsByQuery(self.filterQueryByNameAndType, (name, type))
		return files
		
	def getFilesByGameIdAndTypeId(self, gameId, fileTypeId):
		files = self.getObjectsByQuery(self.filterQueryByGameIdAndTypeId, (gameId, fileTypeId))
		return files
		
	def getRomsByGameId(self, gameId):
		files = self.getObjectsByQuery(self.filterQueryByGameIdAndFileType, (gameId, 0))
		return files
		
	def getFilesForGamelist(self, fileTypeIds):				
		
		files = self.getObjectsByQueryNoArgs(self.filterFilesForGameList %(','.join(fileTypeIds)))
		return files
		
	def getFilesByParentIds(self, gameId, romCollectionId, publisherId, developerId):
		files = self.getObjectsByQuery(self.filterQueryByParentIds, (gameId, romCollectionId, publisherId, developerId))
		return files
	
	def delete(self, gameId):
		util.Logutil.log("Delete Files with gameId %s" % str(gameId), util.LOG_LEVEL_INFO)
		self.deleteObjectByQuery(self.deleteQuery, (gameId,))
	
	def deleteByFileId(self, fileId):
		util.Logutil.log("Delete File with id %s" % str(fileId), util.LOG_LEVEL_INFO)
		self.deleteObjectByQuery(self.deleteFileQuery, (fileId,))
		
	def getFilesList(self):
		files = self.getObjectsByQueryNoArgs(self.getFileList)
		return files