import simplejson
import urllib2
import md5
import os

import xbmc

import db

try:
    # Used by Eden/external python
    from sqlite3 import dbapi2 as sqlite3
except ImportError:
    # Used by Dharma/internal python
    from pysqlite2 import dbapi2 as sqlite3

class HighscoreDatabase(object):
    def getHighscores(self, game):
        """
        @type game: quizlib.game.Game
        @param game: game instance
        """
        raise

    def getHighscoresNear(self, game, highscoreId):
        """
        @type game: quizlib.game.Game
        @param game: game instance
        @type highscoreId: int
        @param highscoreId: the highscoreId to get highscores near
        """
        raise

class GlobalHighscoreDatabase(HighscoreDatabase):
    STATUS_OK = 'OK'
    SERVICE_URL = 'http://moviequiz.xbmc.info/service.json.php'

    def __init__(self, addonVersion):
        self.addonVersion = addonVersion

    def addHighscore(self, nickname, game):
        if game.getPoints() <= 0:
            return -1

        req = {
            'action' : 'submit',
            'entry' : {
                'type' : game.getType(),
                'gameType' : game.getGameType(),
                'gameSubType' : game.getGameSubType(),
                'nickname' : nickname,
                'score' : game.getPoints(),
                'correctAnswers' : game.getCorrectAnswers(),
                'numberOfQuestions' : game.getTotalAnswers(),
                'addonVersion' : self.addonVersion,
                'xbmcVersion' : xbmc.getInfoLabel('System.BuildVersion')
            }
        }

        resp = self._request(req)

        if resp['status'] == self.STATUS_OK:
            return int(resp['newHighscoreId'])
        else:
            return -1


    def getHighscores(self, game):
        req = {
            'action' : 'highscores',
            'type' : game.getType(),
            'gameType' : game.getGameType(),
            'gameSubType' : game.getGameSubType()
        }

        resp = self._request(req)
        if resp['status'] == 'OK':
            return resp['highscores']
        else:
            return []

    def getHighscoresNear(self, game, highscoreId):
        return self.getHighscores(game)


    def _request(self, data):
        jsonData = simplejson.dumps(data)

        req = urllib2.Request(self.SERVICE_URL, jsonData)
        req.add_header('X-MovieQuiz-Checksum', md5.new(jsonData).hexdigest())
        req.add_header('Content-Type', 'text/json')

        try:
            u = urllib2.urlopen(req)
            resp = u.read()
            u.close()
            return simplejson.loads(resp)
        except urllib2.URLError:
            return {'status' : 'error'}


class LocalHighscoreDatabase(HighscoreDatabase):
    HIGHSCORE_DB = 'highscore.db'
    def __init__(self, path):
        highscoreDbPath = os.path.join(path, LocalHighscoreDatabase.HIGHSCORE_DB)

        self.conn = sqlite3.connect(highscoreDbPath, check_same_thread = False)
        self.conn.row_factory = db._sqlite_dict_factory
        xbmc.log("HighscoreDatabase opened: " + highscoreDbPath)

        self._createTables()

    def close(self):
        if hasattr(self, 'conn') and self.conn is not None:
            self.conn.close()
            print "LocalHighscoreDatabase closed"
        
    def addHighscore(self, game):
        if game.getPoints() <= 0:
            return -1

        c = self.conn.cursor()
        c.execute("INSERT INTO highscore(user_id, type, gameType, gameSubType, score, correctAnswers, numberOfQuestions, timestamp)"
            + " VALUES(?, ?, ?, ?, ?, ?, ?, datetime('now'))",
            [game.getUserId(), game.getType(), game.getGameType(), game.getGameSubType(), game.getPoints(), game.getCorrectAnswers(), game.getTotalAnswers()])
        self.conn.commit()
        rowid = c.lastrowid

        # reposition highscore
        highscores = self.getHighscores(game)
        for idx, highscore in enumerate(highscores):
            c.execute("UPDATE highscore SET position=? WHERE id=?", [idx + 1, highscore['id']])
        self.conn.commit()
        c.close()

        return rowid

    def getHighscores(self, game):
        c = self.conn.cursor()
        c.execute('SELECT h.*, u.nickname FROM highscore h, user u WHERE h.user_id=u.id AND h.type=? AND h.gameType=? and h.gameSubType=? ORDER BY h.score DESC, h.timestamp ASC',
            [game.getType(), game.getGameType(), game.getGameSubType()])
        return c.fetchall()

    def getHighscoresNear(self, game, highscoreId):
        c = self.conn.cursor()
        c.execute('SELECT position FROM highscore WHERE id=?', [highscoreId])
        r = c.fetchone()
        position = r['position']

        c.execute("SELECT h.*, u.nickname FROM highscore h, user u WHERE h.user_id=u.id AND h.type=? AND h.gameType=? and h.gameSubType=? AND h.position > ? AND h.position < ? ORDER BY h.position",
            [game.getType(), game.getGameType(), game.getGameSubType(), position - 5, position + 5])
        return c.fetchall()

    def createUser(self, nickname):
        c = self.conn.cursor()
        c.execute("INSERT INTO user(nickname, last_used) VALUES(?, datetime('now'))", [nickname])
        self.conn.commit()
        rowid = c.lastrowid
        c.close()

        return rowid

    def getUsers(self):
        c = self.conn.cursor()
        c.execute('SELECT * FROM user ORDER BY last_used DESC, nickname')
        users = c.fetchall()
        c.close()

        return users

    def deleteUser(self, id):
        c = self.conn.cursor()
        c.execute('DELETE FROM user WHERE id = ?', [id])
        c.execute('DELETE FROM highscore WHERE user_id = ?', [id])
        self.conn.commit()

    def getNickname(self, userId):
        c = self.conn.cursor()
        c.execute("UPDATE user SET last_used = datetime('now') WHERE id = ?", [userId])
        self.conn.commit()
        c.execute('SELECT nickname FROM user WHERE id = ?', [userId])
        nickname = c.fetchone()['nickname']
        c.close()
        return nickname

    def _createTables(self):
        xbmc.log('Migrating Highscore Database')

        c = self.conn.cursor()

        try:
            c.execute('SELECT major, minor, patch FROM version')
            version = c.fetchone().values()
        except sqlite3.OperationalError:
            version = [0,0,0]

        xbmc.log("Highscore Database version: " + str(version))

        if version < [0,4,1]:
            xbmc.log("Migrating Highscore Database to v0.4.1")

            c.execute('CREATE TABLE IF NOT EXISTS highscore ('
                + 'id INTEGER PRIMARY KEY,'
                + 'user_id INTEGER,'
                + 'type TEXT,'
                + 'gameType TEXT,'
                + 'gameSubType TEXT,'
                + 'position INTEGER,'
                + 'score REAL,'
                + 'correctAnswers INTEGER,'
                + 'numberOfQuestions INTEGER,'
                + 'timestamp INTEGER,'
                + 'FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE )'
            )

            c.execute('CREATE TABLE IF NOT EXISTS user ('
                + 'id INTEGER PRIMARY KEY,'
                + 'nickname TEXT )')


        if version < [0,4,2]:
            xbmc.log("Migrating Highscore Database to v0.4.2")

            c.execute('CREATE TABLE IF NOT EXISTS version (major INTEGER, minor INTEGER, patch INTEGER)')
            c.execute('INSERT INTO version VALUES(0, 4, 2)')

            c.execute('ALTER TABLE user ADD COLUMN last_used INTEGER')
            
        self.conn.commit()
        c.close()

        xbmc.log('Highscore Database is up-to-date')



