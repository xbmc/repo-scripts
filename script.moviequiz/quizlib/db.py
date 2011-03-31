from elementtree import ElementTree
from pysqlite2 import dbapi2 as sqlite3
import os
import xbmc
import mysql.connector

__author__ = 'twinther'

class Database(object):
    """Base class for the various databases"""
    def __init__(self):
        self.conn = None

    def __del__(self):
        self.close()

    def close(self):
        self.conn.close()
        xbmc.log("Database closed")

    def fetchall(self, sql, parameters = tuple()):
        if not isinstance(parameters, tuple):
            parameters = [parameters]

        parameters = self._prepareParameters(parameters)
        sql = self._prepareSql(sql)

        xbmc.log("Executing fetchall SQL [%s]" % sql)

        c = self._createCursor()
        c.execute(sql, parameters)
        result = c.fetchall()

        if result is None:
            raise DbException(sql)

        return result

    def fetchone(self, sql, parameters = tuple()):
        if not isinstance(parameters, tuple):
            parameters = [parameters]

        parameters = self._prepareParameters(parameters)
        sql = self._prepareSql(sql)

        xbmc.log("Executing fetchone SQL [%s]" % sql)

        c = self._createCursor()
        c.execute(sql, parameters)
        result = c.fetchone()

        if result is None:
            raise DbException(sql)

        return result

    def execute(self, sql, parameters = tuple()):
        if not isinstance(parameters, tuple):
            parameters = [parameters]

        parameters = self._prepareParameters(parameters)
        sql = self._prepareSql(sql)

        c = self._createCursor()
        c.execute(sql, parameters)
        self.conn.commit()
        c.close()

    def _prepareParameters(self, parameters):
        return parameters

    def _prepareSql(self, sql):
        return sql

    def _createCursor(self):
        return self.conn.cursor()

    def hasMovies(self):
        row = self.fetchone("SELECT COUNT(*) AS cnt FROM movieview")
        return int(row['cnt']) > 0

    def hasTVShows(self):
        row = self.fetchone("SELECT COUNT(*) AS cnt FROM tvshowview")
        return int(row['cnt']) > 0

#
# MySQL
#

class MySQLDatabase(Database):
    def __init__(self, settings):
        Database.__init__(self)

        self.conn = mysql.connector.connect(
            host = settings['host'],
            user = settings['user'],
            passwd = settings['pass'],
            db = settings['name']
            )

        xbmc.log("MySQLDatabase opened")

    def hasMovies(self):
        row = self.fetchone("SELECT COUNT(table_name) AS cnt FROM information_schema.tables WHERE table_name='movieview'")
        if int(row['cnt']) > 0:
            return Database.hasMovies(self)
        else:
            return False

    def hasTVShows(self):
        row = self.fetchone("SELECT COUNT(table_name) AS cnt FROM information_schema.tables WHERE table_name='tvshowview'")
        if int(row['cnt']) > 0:
            return Database.hasTVShows(self)
        else:
            return False

    def _createCursor(self):
        return self.conn.cursor(cursor_class = MySQLCursorDict)

    def _prepareParameters(self, parameters):
        return map(str, parameters)

    def _prepareSql(self, sql):
        sql = sql.replace('%', '%%')
        sql = sql.replace('?', '%s')
        sql = sql.replace('random()', 'rand()')
        return sql

class MySQLCursorDict(mysql.connector.cursor.MySQLCursor):
    def fetchone(self):
        row = self._fetch_row()
        if row:
            return dict(zip(self.column_names, self._row_to_python(row)))
        return None

    def fetchall(self):
        if self._have_result is False:
            raise DbException("No result set to fetch from.")
        res = []
        (rows, eof) = self.db().protocol.get_rows()
        self.rowcount = len(rows)
        for i in xrange(0,self.rowcount):
            res.append(dict(zip(self.column_names, self._row_to_python(rows[i]))))
        self._handle_eof(eof)
        return res

#
# SQLite
#

class SQLiteDatabase(Database):
    def __init__(self, settings):
        Database.__init__(self)
        found = True
        db_file = None

        candidates = [
            'MyVideos48.db', # Eden
            'MyVideos34.db'  # Dharma
        ]
        if settings.has_key('name') and settings['name'] is not None:
            candidates.insert(0, settings['name'] + '.db') # defined in settings

        for candidate in candidates:
            db_file = os.path.join(settings['host'], candidate)
            if os.path.exists(db_file):
                found = True
                break

        if not found:
            xbmc.log("Unable to find any known SQLiteDatabase files!")
            return

        xbmc.log("Connecting to SQLite database file: %s" % db_file)
        self.conn = sqlite3.connect(db_file)
        self.conn.row_factory = self._sqlite_dict_factory
        xbmc.log("SQLiteDatabase opened")

    def hasMovies(self):
        row = self.fetchone("SELECT COUNT(*) AS cnt FROM sqlite_master WHERE name='movieview'")
        if int(row['cnt']) > 0:
            return Database.hasMovies(self)
        else:
            return False

    def hasTVShows(self):
        row = self.fetchone("SELECT COUNT(*) AS cnt FROM sqlite_master WHERE name='tvshowview'")
        if int(row['cnt']) > 0:
            return Database.hasTVShows(self)
        else:
            return False

    def _sqlite_dict_factory(self, cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            dot = col[0].find('.') + 1
            if dot != -1:
                d[col[0][dot:]] = row[idx]
            else:
                d[col[0]] = row[idx]
        return d

class DbException(Exception):
    def __init__(self, sql):
        Exception.__init__(self, sql)


def connect():
    settings = _loadSettings()
    xbmc.log("Loaded DB settings: %s" % settings)

    if settings.has_key('type') and settings['type'] is not None and settings['type'].lower() == 'mysql':
        return MySQLDatabase(settings)
    else:
        return SQLiteDatabase(settings)

        
def _loadSettings():
    settings = {
        'type' : 'sqlite3',
        'host' : xbmc.translatePath('special://database/')
    }

    advancedSettings = xbmc.translatePath('special://userdata/advancedsettings.xml')
    if os.path.exists(advancedSettings):
        f = open(advancedSettings)
        doc = ElementTree.fromstring(f.read())
        f.close()

        if doc.findtext('videodatabase/type') is not None:
            settings['type'] = doc.findtext('videodatabase/type')
        if doc.findtext('videodatabase/host') is not None:
            settings['host'] = doc.findtext('videodatabase/host')
        if doc.findtext('videodatabase/name') is not None:
            settings['name'] = doc.findtext('videodatabase/name')
        if doc.findtext('videodatabase/user') is not None:
            settings['user'] = doc.findtext('videodatabase/user')
        if doc.findtext('videodatabase/pass') is not None:
            settings['pass'] = doc.findtext('videodatabase/pass')

    return settings
    