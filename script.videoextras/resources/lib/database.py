# -*- coding: utf-8 -*-
import xbmc
import xbmcaddon
import xbmcvfs
import sqlite3
import xbmcgui

__addon__ = xbmcaddon.Addon(id='script.videoextras')

# Import the common settings
from settings import log
from settings import os_path_join


#################################
# Class to handle database access
#################################
class ExtrasDB():
    def __init__(self):
        # Start by getting the database location
        self.configPath = xbmc.translatePath(__addon__.getAddonInfo('profile'))
        self.databasefile = os_path_join(self.configPath, "extras_database.db")
        log("ExtrasDB: Database file location = %s" % self.databasefile)
        # Make sure that the database exists if this is the first time
        self.createDatabase()

    def cleanDatabase(self):
        isYes = xbmcgui.Dialog().yesno(__addon__.getLocalizedString(32102), __addon__.getLocalizedString(32024) + "?")
        if isYes:
            # If the database file exists, delete it
            if xbmcvfs.exists(self.databasefile):
                xbmcvfs.delete(self.databasefile)
                log("ExtrasDB: Removed database: %s" % self.databasefile)
            else:
                log("ExtrasDB: No database exists: %s" % self.databasefile)

    def createDatabase(self):
        # Make sure the database does not already exist
        if not xbmcvfs.exists(self.databasefile):
            # Get a connection to the database, this will create the file
            conn = sqlite3.connect(self.databasefile)
            conn.text_factory = str
            c = conn.cursor()

            # Create the version number table, this is a simple table
            # that just holds the version details of what created it
            # It should make upgrade later easier
            c.execute('''CREATE TABLE version (version text primary key)''')

            # Insert a row for the version
            versionNum = "1"

            # Run the statement passing in an array with one value
            c.execute("INSERT INTO version VALUES (?)", (versionNum,))

            # Create a table that will be used to store each extras file
            # The "id" will be auto-generated as the primary key
            c.execute('''CREATE TABLE ExtrasFile (id integer primary key, filename text unique, resumePoint integer, duration integer, watched integer)''')

            # Save (commit) the changes
            conn.commit()

            # We can also close the connection if we are done with it.
            # Just be sure any changes have been committed or they will be lost.
            conn.close()
        else:
            # Check if this is an upgrade
            conn = sqlite3.connect(self.databasefile)
            c = conn.cursor()
            c.execute('SELECT * FROM version')
            log("Current version number in DB is: %s" % c.fetchone()[0])
            conn.close()

    # Get a connection to the current database
    def getConnection(self):
        conn = sqlite3.connect(self.databasefile)
        conn.text_factory = str
        return conn

    # Insert or replace an entry in the database
    def insertOrUpdate(self, filename, resumePoint, totalDuration, watched):
        log("ExtrasDB: insertOrUpdate( %s )" % filename)

        # Get a connection to the DB
        conn = self.getConnection()
        c = conn.cursor()

        insertData = (filename, resumePoint, totalDuration, watched)
        c.execute('''INSERT OR REPLACE INTO ExtrasFile(filename, resumePoint, duration, watched) VALUES (?,?,?,?)''', insertData)

        rowId = c.lastrowid
        conn.commit()
        conn.close()

        return rowId

    def select(self, filename):
        log("ExtrasDB: select for %s" % filename)

        # Get a connection to the DB
        conn = self.getConnection()
        c = conn.cursor()
        # Select any existing data from the database
        c.execute('SELECT * FROM ExtrasFile where filename = ?', (filename,))
        row = c.fetchone()

        if row is None:
            log("ExtrasDB: No entry found in the database for %s" % filename)
            return None

        log("ExtrasDB: Database info: %s" % str(row))

        # Return will contain
        # row[0] - Unique Index in the DB
        # row[1] - Name of the file
        # row[2] - Current point played to (or -1 is not saved)
        # row[3] - Total Duration of the video
        # row[4] - 0 if not watched 1 if watched
        returnData = {}
        returnData['resumePoint'] = row[2]
        returnData['totalDuration'] = row[3]
        returnData['watched'] = row[4]

        conn.close()
        return returnData

    def delete(self, filename):
        log("ExtrasDB: delete for %s" % filename)

        # Get a connection to the DB
        conn = self.getConnection()
        c = conn.cursor()
        # Select any existing data from the database
        c.execute('delete FROM ExtrasFile where filename = ?', (filename,))
        conn.commit()

        log("ExtrasDB: delete for %s removed %d rows" % (filename, conn.total_changes))

        conn.close()
