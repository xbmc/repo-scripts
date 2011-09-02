from elementtree import ElementTree
from xml.parsers.expat import ExpatError

import os
import xbmc
import glob

try:
    # Used by Eden/external python
    from sqlite3 import dbapi2 as sqlite3
except ImportError:
    # Used by Dharma/internal python
    from pysqlite2 import dbapi2 as sqlite3

__author__ = 'twinther'

class Database(object):
    """Base class for the various databases"""
    def __init__(self):
        self.conn = None

    def __del__(self):
        self.close()

    def postInit(self):
        self._fixMissingTVShowView()

    def _fixMissingTVShowView(self):
        self.conn.execute("""
        CREATE VIEW IF NOT EXISTS tvshowview AS
            SELECT tvshow.*, path.strPath AS strPath, NULLIF(COUNT(episode.c12), 0) AS totalCount, COUNT(files.playCount) AS watchedcount, NULLIF(COUNT(DISTINCT(episode.c12)), 0) AS totalSeasons
            FROM tvshow
                LEFT JOIN tvshowlinkpath ON tvshowlinkpath.idShow=tvshow.idShow
                LEFT JOIN path ON path.idPath=tvshowlinkpath.idPath
                LEFT JOIN tvshowlinkepisode ON tvshowlinkepisode.idShow=tvshow.idShow
                LEFT JOIN episode ON episode.idEpisode=tvshowlinkepisode.idEpisode
                LEFT JOIN files ON files.idFile=episode.idFile
            GROUP BY tvshow.idShow;
        """)

    def close(self):
        self.conn.close()
        print "Database closed"

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
# SQLite
#

class SQLiteDatabase(Database):
    def __init__(self, settings):
        super(SQLiteDatabase, self).__init__()
        found = True
        db_file = None

        # Find newest MyVideos.db and use that
        candidates = glob.glob(settings['host'] + '/MyVideos*.db')
        list.sort(candidates, reverse=True)
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
        self.conn = sqlite3.connect(db_file, check_same_thread = False)
        self.conn.row_factory = _sqlite_dict_factory
        xbmc.log("SQLiteDatabase opened")

        super(SQLiteDatabase, self).postInit()

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

def _sqlite_dict_factory(cursor, row):
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
        raise DbException('MySQL database is not supported')
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
        xml = f.read()
        f.close()
        try:
            doc = ElementTree.fromstring(xml)

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
        except ExpatError:
           xbmc.log("Unable to parse advancedsettings.xml")

    return settings



