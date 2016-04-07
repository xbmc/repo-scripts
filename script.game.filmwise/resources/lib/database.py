# -*- coding: utf-8 -*-
import xbmc
import xbmcaddon
import xbmcvfs
import sqlite3

# Import the common settings
from settings import log
from settings import os_path_join

ADDON = xbmcaddon.Addon(id='script.game.filmwise')


#################################
# Class to handle database access
#################################
class FilmWiseDB():
    def __init__(self):
        # Start by getting the database location
        self.configPath = xbmc.translatePath(ADDON.getAddonInfo('profile'))
        self.databasefile = os_path_join(self.configPath, "filmwise_database.db")
        log("FilmWiseDB: Database file location = %s" % self.databasefile)
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

            # Create the table that will be used to store the data for each quiz
            # The "id" will be auto-generated as the primary key
            # Note: Index will automatically be created for "unique" values, so no
            # need to manually create them
            c.execute('''CREATE TABLE answers (id integer primary key, quiz_number integer, question_id text, user_answer text, is_correct integer)''')

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

    def getAnswers(self, quizNumber):
        log("FilmWiseDB: Get answers for %d" % quizNumber)

        # Get a connection to the DB
        conn = self.getConnection()
        c = conn.cursor()
        # Select any existing data from the database
        c.execute('SELECT * FROM answers where quiz_number = ?', (quizNumber,))
        rows = c.fetchall()

        log("FilmWiseDB: Number of rows selected is %d" % len(rows))

        answers = {}

        for row in rows:
            log("FilmWiseDB: Database info: %s" % str(row))

            # Return will contain
            # row[0] - Id - Primary Key
            # row[1] - Quiz Number
            # row[2] - Question Id
            # row[3] - User Answer
            # row[4] - Is Correct
            isCorrect = False
            if row[4] == 1:
                isCorrect = True
            answerId = row[2]
            answers[answerId] = {'user_answer': row[3], 'isCorrect': isCorrect}

        conn.close()
        return answers

    def addAnswer(self, quizNumber, questionId, answer, correct=False):
        log("FilmWiseDB: Adding quiz: %d, question: %s, answer=%s" % (quizNumber, questionId, answer))

        # Get a connection to the DB
        conn = self.getConnection()
        c = conn.cursor()

        correctId = 0
        if correct:
            correctId = 1

        insertData = (quizNumber, questionId, answer, correctId)
        cmd = 'INSERT OR REPLACE INTO answers (quiz_number, question_id, user_answer, is_correct) VALUES (?,?,?,?)'
        c.execute(cmd, insertData)

        rowId = c.lastrowid
        conn.commit()
        conn.close()

        return rowId

    # Delete an entry from the database
    def deleteAnswer(self, quizNumber, questionId):
        log("FilmWiseDB: delete for quiz: %d, question: %s" % (quizNumber, questionId))

        # Get a connection to the DB
        conn = self.getConnection()
        c = conn.cursor()
        # Delete any existing data from the database
        cmd = 'DELETE FROM answers where quiz_number = ? and question_id = ?'
        c.execute(cmd, (quizNumber, questionId))
        conn.commit()

        log("FilmWiseDB: delete for %s, %s removed %d rows" % (quizNumber, questionId, conn.total_changes))

        conn.close()
