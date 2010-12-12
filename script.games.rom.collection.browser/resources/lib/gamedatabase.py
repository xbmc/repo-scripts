

import os, sys, shutil
from pysqlite2 import dbapi2 as sqlite

import util
from configxmlupdater import *


class GameDataBase:	
	
	def __init__(self, databaseDir):		
		self.dataBasePath = os.path.join(databaseDir, 'MyGames.db')
		#use scripts home for reading SQL files
		self.sqlDir = os.path.join(util.RCBHOME, 'resources', 'database')		
		
	def connect( self ):
		print self.dataBasePath
		sqlite.register_adapter(str, lambda s:s.decode('utf-8'))
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
				self.self.createTables()
				return 1, ""
			rcbSetting = rcbSettingRows[0]
			
			#HACK: reflect changes in RCBSetting
			dbVersion = rcbSetting[util.RCBSETTING_dbVersion]
			if(dbVersion == None):
				dbVersion = rcbSetting[10]				
			
		except  Exception, (exc): 
			self.createTables()
			return 1, ""
		
		#Alter Table
		if(dbVersion != util.CURRENT_DB_VERSION):
			alterTableScript = "SQL_ALTER_%(old)s_%(new)s.txt" %{'old': dbVersion, 'new':util.CURRENT_DB_VERSION}
			alterTableScript = str(os.path.join(self.sqlDir, alterTableScript))
			
			if os.path.isfile(alterTableScript):
								
				returnCode, message = ConfigxmlUpdater().createConfig(self, dbVersion)
								
				#backup MyGames.db							
				newFileName = self.dataBasePath +'.backup ' +dbVersion 
				
				if os.path.isfile(newFileName):					
					return -1, "Error: Cannot backup MyGames.db: Backup File exists."				
				try:
					self.close()
					shutil.copy(str(self.dataBasePath), str(newFileName))
					self.connect()
				except Exception, (exc):					
					return -1, "Error: Cannot backup MyGames.db: " +str(exc)
								
				self.executeSQLScript(alterTableScript)
				return returnCode, message
			else:
				return -1, "Error: No Update from version %s to %s." %(dbVersion, util.CURRENT_DB_VERSION)
			
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
		
	
	def update(self, columns, args, id):
		
		if(len(columns) != len(args)):
			#TODO raise Exception?			
			return
			
		updateString = "Update %s SET " %self.tableName
		for i in range(0, len(columns)):
			updateString += columns[i] +  " = ?"
			if(i < len(columns) -1):
				updateString += ", "
				
		updateString += " WHERE id = " +str(id)		
		self.gdb.cursor.execute(updateString, args)
		
	
	def deleteAll(self):
		self.gdb.cursor.execute("DELETE FROM '%s'" % self.tableName)		
	
	
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
					(PublisherId = ? OR (0 = ?)) \
					AND %s \
					ORDER BY name COLLATE NOCASE"
					
	filterByNameAndRomCollectionId = "SELECT * FROM Game WHERE name = ? and romCollectionId = ?"
	
	def __init__(self, gdb):		
		self.gdb = gdb
		self.tableName = "Game"
		
	def getFilteredGames(self, romCollectionId, genreId, yearId, publisherId, likeStatement):
		args = (romCollectionId, genreId, yearId, publisherId)
		filterQuery = self.filterQuery %likeStatement			
		games = self.getObjectsByWildcardQuery(filterQuery, args)
		newList = self.encodeUtf8(games)
		return newList
		
	def getGameByNameAndRomCollectionId(self, name, romCollectionId):
		game = self.getObjectByQuery(self.filterByNameAndRomCollectionId, (name, romCollectionId))
		return game


class RCBSetting(DataBaseObject):	
	def __init__(self, gdb):		
		self.gdb = gdb
		self.tableName = "RCBSetting"


class Genre(DataBaseObject):
	
	filteGenreByGameId = "SELECT * FROM Genre WHERE Id IN (Select GenreId From GenreGame Where GameId = ?)"
	
	def __init__(self, gdb):		
		self.gdb = gdb
		self.tableName = "Genre"
		
	def getGenresByGameId(self, gameId):
		genres = self.getObjectsByQuery(self.filteGenreByGameId, (gameId,))
		return genres


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
	
	def __init__(self, gdb):		
		self.gdb = gdb
		self.tableName = "Year"


class Publisher(DataBaseObject):	
	def __init__(self, gdb):		
		self.gdb = gdb
		self.tableName = "Publisher"
		

class Developer(DataBaseObject):
	def __init__(self, gdb):		
		self.gdb = gdb
		self.tableName = "Developer"
		
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
	