# -*- coding: utf-8 -*-
import xbmc
import xbmcaddon
import xbmcvfs
import sqlite3

# Import the common settings
from settings import log
from settings import os_path_join

ADDON = xbmcaddon.Addon(id='script.ebooks')


#################################
# Class to handle database access
#################################
class EbooksDB():
    def __init__(self):
        # Start by getting the database location
        self.configPath = xbmc.translatePath(ADDON.getAddonInfo('profile'))
        self.databasefile = os_path_join(self.configPath, "ebooks_database.db")
        log("EbooksDB: Database file location = %s" % self.databasefile)
        # Check to make sure the DB has been created
        self._createDatabase()

    # Creates the database if the file does not already exist
    def _createDatabase(self):
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

            # Create the table that will be used to store the dat for each book
            # The "id" will be auto-generated as the primary key
            # Note: Index will automatically be created for "unique" values, so no
            # need to manually create them
            c.execute('''CREATE TABLE books (id integer primary key, fullpath text unique, title text, author text, readchapter text, complete integer)''')

            # Save (commit) the changes
            conn.commit()

            # We can also close the connection if we are done with it.
            # Just be sure any changes have been committed or they will be lost.
            conn.close()

    # Get a connection to the current database
    def getConnection(self):
        conn = sqlite3.connect(self.databasefile)
        conn.text_factory = str
        return conn

    def getBookDetails(self, fullpath):
        log("EbooksDB: Get book details for %s" % fullpath)

        # Get a connection to the DB
        conn = self.getConnection()
        c = conn.cursor()
        # Select any existing data from the database
        c.execute('SELECT * FROM books where fullpath = ?', (fullpath,))
        row = c.fetchone()

        if row is None:
            log("EbooksDB: No entry found in the database for %s" % fullpath)
            conn.close()
            return None

        log("EbooksDB: Database info: %s" % str(row))

        # Return will contain
        # row[0] - Unique Index in the DB
        # row[1] - Full Path of the book
        # row[2] - Title
        # row[3] - Author
        # row[4] - Current chapter read until
        # row[5] - 1 if complete, otherwise 0
        completeStatus = False
        if row[5] == 1:
            completeStatus = True
        returnData = {'fullpath': row[1], 'title': row[2], 'author': row[3], 'readchapter': row[4], 'complete': completeStatus}

        conn.close()
        return returnData

    def addBook(self, fullPath, title, author):
        log("EbooksDB: Adding %s" % fullPath)

        # Get a connection to the DB
        conn = self.getConnection()
        c = conn.cursor()

        insertData = (fullPath, title, author)
        cmd = 'INSERT OR REPLACE INTO books (fullpath, title, author, readchapter, complete) VALUES (?,?,?,"",0)'
        c.execute(cmd, insertData)

        rowId = c.lastrowid
        conn.commit()
        conn.close()

        return rowId

    def setReadChapter(self, fullPath, readchapter, complete=False):
        log("EbooksDB: Setting read chapter for book %s to %s" % (fullPath, readchapter))

        # Get a connection to the DB
        conn = self.getConnection()
        c = conn.cursor()

        completeStatus = 0
        if complete:
            completeStatus = 1
        insertData = (readchapter, completeStatus, fullPath)
        cmd = 'UPDATE books SET readchapter = ?, complete = ? WHERE fullpath = ?'

        c.execute(cmd, insertData)

        rowId = c.lastrowid
        conn.commit()
        conn.close()

        return rowId

    # Delete an entry from the database
    def clearBookHistory(self, fullPath):
        log("EbooksDB: delete book history for %s" % fullPath)

        # Get a connection to the DB
        conn = self.getConnection()
        c = conn.cursor()
        # Delete any existing data from the database
        cmd = 'DELETE FROM book where fullPath = ?'
        c.execute(cmd, (fullPath,))
        conn.commit()

        log("EbooksDB: delete for %s removed %d rows" % (fullPath, conn.total_changes))

        conn.close()

    # Select all books from the database
    def getAllBooks(self):
        log("EbooksDB: selecting all books")

        # Get a connection to the DB
        conn = self.getConnection()
        c = conn.cursor()
        # Select any existing data from the database
        cmd = 'SELECT * FROM books'
        c.execute(cmd)
        rows = c.fetchall()

        results = []
        if rows is None:
            # No data
            log("EbooksDB: No entry found in books database")
        else:
            log("EbooksDB: Database info: %s" % str(rows))

            # row[0] - Unique Index in the DB
            # row[1] - Full Path of the book
            # row[2] - Title
            # row[3] - Author
            # row[4] - Current chapter read until
            # row[5] - 1 if complete, otherwise 0
            for row in rows:
                completeStatus = False
                if row[5] == 1:
                    completeStatus = True
                details = {'fullpath': row[1], 'title': row[2], 'author': row[3], 'readchapter': row[4], 'complete': completeStatus}
                results.append(details)

        conn.close()
        return results
