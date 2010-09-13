

import os, sys
from pysqlite2 import dbapi2 as sqlite

import util


class GameDataBase:	
	
	def __init__(self, databaseDir):		
		self.dataBasePath = os.path.join(databaseDir, 'MyGames.db')
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
	
	def executeSQLScript(self, scriptName):
		sqlCreateFile = open(scriptName, 'r')
		sqlCreateString = sqlCreateFile.read()						
		self.connection.executescript(sqlCreateString)		
	
	def createTables(self):
		print "Create Tables"
		self.executeSQLScript(os.path.join(self.sqlDir, 'SQL_CREATE.txt'))
		
	def dropTables(self):
		print "Drop Tables"
		self.executeSQLScript(os.path.join(self.sqlDir, 'SQL_DROP_ALL.txt'))

	
	def checkDBStructure(self):
		
		#returnValues: -1 error, 0=nothing, 1=import Settings and Games
		
		dbVersion = ""
		try:
			rcbSettingRows = RCBSetting(self).getAll()
			if(rcbSettingRows == None or len(rcbSettingRows) != 1):	
				self.self.createTables()
				return 1, ""
			rcbSetting = rcbSettingRows[0]
			dbVersion = rcbSetting[10]
			
		except  Exception, (exc): 
			self.createTables()
			return 1, ""
		
		#Alter Table
		if(dbVersion != util.CURRENT_DB_VERSION):
			alterTableScript = "SQL_ALTER_%(old)s_%(new)s.txt" %{'old': dbVersion, 'new':util.CURRENT_DB_VERSION}
			alterTableScript = str(os.path.join(self.sqlDir, alterTableScript))
			
			if os.path.isfile(alterTableScript):				
				self.executeSQLScript(alterTableScript)				
				return 0, ""
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
		return allObjects
		
		
	def getAllOrdered(self):		
		self.gdb.cursor.execute("SELECT * FROM '%s' ORDER BY name COLLATE NOCASE" % self.tableName)
		allObjects = self.gdb.cursor.fetchall()
		return allObjects
		
		
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


class Game(DataBaseObject):	
	filterQuery = "Select * From Game WHERE \
					(RomCollectionId IN (Select Id From RomCollection Where ConsoleId = ?) OR (0 = ?)) AND \
					(Id IN (Select GameId From GenreGame Where GenreId = ?) OR (0 = ?)) AND \
					(YearId = ? OR (0 = ?)) AND \
					(PublisherId = ? OR (0 = ?)) \
					AND %s \
					ORDER BY name COLLATE NOCASE"
					
	filterByNameAndRomCollectionId = "SELECT * FROM Game WHERE name = ? and romCollectionId = ?"
	
	def __init__(self, gdb):		
		self.gdb = gdb
		self.tableName = "Game"
		
	def getFilteredGames(self, consoleId, genreId, yearId, publisherId, likeStatement):
		args = (consoleId, genreId, yearId, publisherId)
		filterQuery = self.filterQuery %likeStatement		
		games = self.getObjectsByWildcardQuery(filterQuery, args)		
		return games
		
	def getGameByNameAndRomCollectionId(self, name, romCollectionId):
		game = self.getObjectByQuery(self.filterByNameAndRomCollectionId, (name, romCollectionId))
		return game


class Console(DataBaseObject):	
	
	filterByRomCollectionId = "SELECT * FROM Console WHERE Id IN (SELECT consoleId FROM RomCollection WHERE Id = ?)"
	
	def __init__(self, gdb):		
		self.gdb = gdb
		self.tableName = "Console"
		
	def getConsoleByRomCollectionId(self, romCollectionId):
		console = self.getObjectByQuery(self.filterByRomCollectionId, (romCollectionId,))
		return console


class RCBSetting(DataBaseObject):	
	def __init__(self, gdb):		
		self.gdb = gdb
		self.tableName = "RCBSetting"


class RomCollection(DataBaseObject):	
	def __init__(self, gdb):		
		self.gdb = gdb
		self.tableName = "RomCollection"


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


class FileType(DataBaseObject):	
	def __init__(self, gdb):		
		self.gdb = gdb
		self.tableName = "FileType"
		
		
class FileTypeForControl(DataBaseObject):
	filterQueryByKey = "Select * from FileTypeForControl \
					where romCollectionId = ? AND \
					fileTypeId = (select id from filetype where name = ?) AND \
					control = ? AND \
					priority = ?"
					
	filterQueryByKeyNoPrio = "Select * from FileTypeForControl \
					where romCollectionId = ? AND \
					control = ? \
					ORDER BY priority"							
	
	def __init__(self, gdb):		
		self.gdb = gdb
		self.tableName = "FileTypeForControl"
		
	def getFileTypeForControlByKey(self, romCollectionId, fileType, control, priority):
		fileType = self.getObjectByQuery(self.filterQueryByKey, (romCollectionId, fileType, control, priority))
		return fileType
		
	def getFileTypesForControlByKey(self, romCollectionId, control):
		fileTypes = self.getObjectsByQuery(self.filterQueryByKeyNoPrio, (romCollectionId, control))
		return fileTypes			


class File(DataBaseObject):	
	filterQueryByGameIdAndFileType = "Select name from File \
					where parentId = ? AND \
					filetypeid = (select id from filetype where name = ?)"
					
	filterQueryByNameAndType = "Select * from File \
					where name = ? AND \
					filetypeid = (select id from filetype where name = ?)"
					
	filterQueryByNameAndTypeAndParent = "Select * from File \
					where name = ? AND \
					filetypeid = (select id from filetype where name = ?) AND \
					parentId = ?"
					
	filterQueryByGameIdAndTypeId = "Select * from File \
					where parentId = ? AND \
					filetypeid = ?"
					
	filterFilesForGameList = "Select * from File Where FileTypeId in (Select distinct filetypeid from filetypeforcontrol \
					where control = 'gamelist' OR control = 'gamelistselected' OR control = 'mainviewvideofullscreen')"
					
	filterQueryByParentIds = "Select * from File \
					where parentId in (?, ?, ?, ?, ?)"
	
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
		files = self.getObjectsByQuery(self.filterQueryByGameIdAndFileType, (gameId, 'rcb_rom'))
		return files
		
	def getFilesForGamelist(self):
		files = self.getObjectsByQueryNoArgs(self.filterFilesForGameList)
		return files
		
	def getFilesByParentIds(self, gameId, romCollectionId, consoleId, publisherId, developerId):
		files = self.getObjectsByQuery(self.filterQueryByParentIds, (gameId, romCollectionId, consoleId, publisherId, developerId))
		return files
		

class Path(DataBaseObject):	
	filterQueryByRomCollectionId = "SELECT * FROM Path \
					WHERE romCollectionId = ? \
					AND filetypeId NOT IN (SELECT id FROM filetype WHERE name LIKE 'rcb_%')"
	
	filterQueryByRomCollectionIdAndFileType = "Select name from Path \
					where romCollectionId = ? AND \
					filetypeid = (select id from filetype where name = ?)"
					
	filterQueryByNameAndType = "Select name from Path \
					where name = ? AND \
					filetypeid = (select id from filetype where name = ?)"
					
	filterQueryByNameAndTypeAndRomCollection = "Select name from Path \
					where name = ? AND \
					filetypeid = (select id from filetype where name = ?) AND \
					romCollectionId = ?"
	
	def __init__(self, gdb):		
		self.gdb = gdb
		self.tableName = "Path"
		
	def getPathByNameAndType(self, name, type):
		file = self.getObjectByQuery(self.filterQueryByNameAndType, (name, type))
		return file
		
	def getPathByNameAndTypeAndRomCollectionId(self, name, type, romCollectionId):
		file = self.getObjectByQuery(self.filterQueryByNameAndTypeAndRomCollection, (name, type, romCollectionId))
		return file
		
	def getPathsByRomCollectionId(self, romCollectionId):
		paths = self.getObjectsByQuery(self.filterQueryByRomCollectionId, (romCollectionId,))
		return paths
		
	def getRomPathsByRomCollectionId(self, romCollectionId):
		path = self.getObjectsByQuery(self.filterQueryByRomCollectionIdAndFileType, (romCollectionId, 'rcb_rom'))
		return path
		
	def getDescriptionPathByRomCollectionId(self, romCollectionId):
		path = self.getObjectByQuery(self.filterQueryByRomCollectionIdAndFileType, (romCollectionId, 'rcb_description'))
		if path == None:
			return ""	
		return path[0]
		
		
	def getManualPathsByRomCollectionId(self, romCollectionId):
		path = self.getObjectsByQuery(self.filterQueryByRomCollectionIdAndFileType, (romCollectionId, 'manual'))
		return path
	
	def getConfigurationPathsByRomCollectionId(self, romCollectionId):
		path = self.getObjectsByQuery(self.filterQueryByRomCollectionIdAndFileType, (romCollectionId, 'configuration'))
		return path
