from elementtree import ElementTree
from xml.parsers.expat import ExpatError

import os
import xbmc
import mysql.connector
import glob

try:
    # Used by Eden/external python
    from sqlite3 import dbapi2 as sqlite3
except ImportError:
    # Used by Dharma/internal python
    from pysqlite2 import dbapi2 as sqlite3

class Database(object):
    """Base class for the various databases"""
    FUNC_RANDOM = None
    PARAM_REPL = None

    def __init__(self, allowedRatings, onlyWatched):
        """
        @param allowedRatings: limit movies based on ratings
        @type allowedRatings: list
        @param onlyWatched: only include watches movies or not
        @type onlyWatched: bool
        """
        self.conn = None

        self.defaultMovieViewClause = ''
        self.defaultTVShowViewClause = ''
        if allowedRatings:
            self.defaultMovieViewClause += " AND ("
            self.defaultTVShowViewClause += " AND ("
            for allowedRating in allowedRatings:
                self.defaultMovieViewClause += " TRIM(c12) LIKE '%s%%%%' OR" % allowedRating
                self.defaultTVShowViewClause += " TRIM(tv.c13) LIKE '%s%%%%' OR" % allowedRating
            self.defaultMovieViewClause = self.defaultMovieViewClause[0:-3] + ")"
            self.defaultTVShowViewClause = self.defaultTVShowViewClause[0:-3] + ")"
        if onlyWatched:
            self.defaultMovieViewClause += " AND mv.playCount IS NOT NULL"
            self.defaultTVShowViewClause += " AND ev.playCount IS NOT NULL"

    def postInit(self):
        self._fixMissingTVShowView()

    @staticmethod
    def connect(allowedRatings = None, onlyWatched = None):
        """
        @param allowedRatings: limit movies based on ratings
        @type allowedRatings: list
        @param onlyWatched: only include watches movies or not
        @type onlyWatched: bool
        """
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

        xbmc.log("Loaded DB settings: %s" % settings)

        if settings.has_key('type') and settings['type'] is not None and settings['type'].lower() == 'mysql':
            return MySQLDatabase(allowedRatings, onlyWatched, settings)
        else:
            return SQLiteDatabase(allowedRatings, onlyWatched, settings)


    def _fixMissingTVShowView(self):
        c = self.cursor()
        try:
            c.execute('SELECT * FROM tvshowview LIMIT 1')
            c.fetchall()
        except Exception:
            xbmc.log('The tvshowview is missing in the database, creating...')
            c.execute("""
            CREATE VIEW tvshowview AS
                SELECT tvshow.*, path.strPath AS strPath, NULLIF(COUNT(episode.c12), 0) AS totalCount, COUNT(files.playCount) AS watchedcount, NULLIF(COUNT(DISTINCT(episode.c12)), 0) AS totalSeasons
                FROM tvshow
                    LEFT JOIN tvshowlinkpath ON tvshowlinkpath.idShow=tvshow.idShow
                    LEFT JOIN path ON path.idPath=tvshowlinkpath.idPath
                    LEFT JOIN tvshowlinkepisode ON tvshowlinkepisode.idShow=tvshow.idShow
                    LEFT JOIN episode ON episode.idEpisode=tvshowlinkepisode.idEpisode
                    LEFT JOIN files ON files.idFile=episode.idFile
                GROUP BY tvshow.idShow
            """)
            self.conn.commit()
        c.close()

    def close(self):
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()
            print "Database closed"

    def fetchall(self, sql, parameters = tuple()):
        if isinstance(parameters, list):
            parameters = tuple(parameters)
        elif not isinstance(parameters, tuple):
            parameters = [parameters]

        xbmc.log("Fetch all SQL [%s] with params %s" % (sql, str(parameters)))
        c = self.cursor()
        c.execute(sql, parameters)
        result = c.fetchall()

        if result is None:
            raise DbException(sql)

        return result

    def fetchone(self, sql, parameters = tuple()):
        if isinstance(parameters, list):
            parameters = tuple(parameters)
        if not isinstance(parameters, tuple):
            parameters = [parameters]

        xbmc.log("Fetch one SQL [%s] with params %s" % (sql, str(parameters)))
        c = self.cursor()
        c.execute(sql, parameters)
        result = c.fetchone()

        if result is None:
            raise DbException(sql)

        return result

    def execute(self, sql, parameters = tuple()):
        if isinstance(parameters, list):
            parameters = tuple(parameters)
        if not isinstance(parameters, tuple):
            parameters = [parameters]

        xbmc.log("Execute SQL [%s] with params %s" % (sql, str(parameters)))
        c = self.cursor()
        c.execute(sql, parameters)
        self.conn.commit()
        c.close()

    def cursor(self):
        return self.conn.cursor()

    def hasMovies(self):
        try:
            row = self.fetchone("SELECT COUNT(*) AS cnt FROM movieview")
            return int(row['cnt']) > 0
        except DbException:
            return False

    def hasTVShows(self):
        try:
            row = self.fetchone("SELECT COUNT(*) AS cnt FROM tvshowview")
            return int(row['cnt']) > 0
        except DbException:
            return False

    def isAnyVideosWatched(self):
        """
        Checks if any movie or episode videos has been played. 
        """
        try:
            row = self.fetchone("SELECT COUNT(*) AS cnt FROM files f, movie m WHERE f.idFile=m.idFile AND f.playCount IS NOT NULL")
            movieCount = row['cnt']

            row = self.fetchone("SELECT COUNT(*) AS cnt FROM files f, episode e WHERE f.idFile=e.idFile AND f.playCount IS NOT NULL")
            episodeCount = row['cnt']

            return movieCount > 0 < episodeCount
        except DbException:
            return False

    def isAnyMPAARatingsAvailable(self):
        try:
            row = self.fetchone("SELECT COUNT(*) AS cnt FROM movie WHERE c12 != ''")
            return int(row['cnt']) > 0
        except DbException:
            return False

    def isAnyContentRatingsAvailable(self):
        try:
            row = self.fetchone("SELECT COUNT(*) AS cnt FROM tvshow WHERE c13 != ''")
            return int(row['cnt']) > 0
        except DbException:
            return False

    def getVideoBookmark(self, idFile):
        """
        Get bookmark details, so we can restore after playback

        @param idFile: the id of the file currently playing
        @type idFile: int
        @return: dict with bookmark information
        """
        try:
            bookmark = self.fetchone("SELECT idBookmark, timeInSeconds FROM bookmark WHERE idFile = " + self.PARAM_REPL, idFile)
        except DbException:
            bookmark = {'idFile' : idFile}

        return bookmark

    def resetVideoBookmark(self, bookmark):
        """
        Resets the bookmark to what it was and deletes it if necessary.

        @param bookmark: The dict as returned by getVideoBookmark(..)
        @type bookmark: dict
        """
        if bookmark.has_key('idFile'):
            try:
                self.execute("DELETE FROM bookmark WHERE idFile = " + self.PARAM_REPL, bookmark['idFile'])
            except DbException:
                pass
        else:
            try:
                self.execute("UPDATE bookmark SET timeInSeconds = " + self.PARAM_REPL + " WHERE idBookmark = " + self.PARAM_REPL
                    , (bookmark['timeInSeconds'], bookmark['idBookmark']))
            except DbException:
                pass


    def getMovies(self, maxResults, setId = None, genres = None, excludeMovieIds = None, actorIdInMovie = None, actorIdNotInMovie = None,
                        directorId = None, excludeDirectorId = None, studioId = None, minYear = None, maxYear = None, mustHaveTagline = False,
                        minActorCount = None, mustHaveRuntime = False, maxRuntime = None):
        """
        Retrieves random movies from XBMC's video library.
        For each movie the following information is returned:
        * idMovie
        * idFile
        * title
        * tagline
        * year
        * runtime
        * genre
        * strPath
        * strFileName
        * idSet

        @type maxResults: int
        @param maxResults: Retrieves this number of movies at most (actual number may be less than this)
        @type setId: int
        @param setId: Only retrieve movies included in this set
        @type genres: str
        @param genres: Only retrieve movies in this/these genres
        @type excludeMovieIds: array of int
        @param excludeMovieIds: Exclude the provided movie Ids from the list of movie candidiates
        @type actorIdInMovie: int
        @param actorIdInMovie: Only retrieve movies with this actor
        @type actorIdNotInMovie: int
        @param actorIdNotInMovie: Exclude movies with this actor from the list of movie candidiates
        @type directorId: int
        @param directorId: Only retrieve movies with this director
        @type excludeDirectorId: int
        @param excludeDirectorId: Exclude movies with this director from the list of movie candidates
        @type studioId: int
        @param studioId: Only retrieve movies with this studio
        @type minYear: int
        @param minYear: Exclude movies with year less than this from the list of movie candidates
        @type maxYear: int
        @param maxYear: Exclude movies with year more than this from the list of movie candidates
        @type mustHaveTagline: bool
        @param mustHaveTagline: Exclude movies without a tagline from the list of movie candidates
        @type minActorCount: int
        @param minActorCount: Only retrieve movies with this or more actors
        @type mustHaveRuntime: bool
        @param mustHaveRuntime: Exclude movies without a runtime from the list of movie candidates
        @type maxRuntime: int
        @param maxRuntime: Only retrieve movies with less than this runtime
        """
        params = list()
        query = """
            SELECT mv.idMovie, mv.idFile, mv.c00 AS title, mv.c03 AS tagline, mv.c07 AS year, mv.c11 AS runtime, mv.c14 AS genre, mv.strPath, mv.strFileName, slm.idSet
            FROM movieview mv LEFT JOIN setlinkmovie slm ON mv.idMovie = slm.idMovie
            WHERE mv.strFileName NOT LIKE '%%.nfo'
            """ + self.defaultMovieViewClause

        if setId:
            query += " AND slm.idSet = " + self.PARAM_REPL
            params.append(int(setId))

        if genres:
            query += " AND mv.c14 = " + self.PARAM_REPL
            params.append(genres)

        if excludeMovieIds:
            if isinstance(excludeMovieIds, list):
                excludeMovieString = ','.join(map(str, excludeMovieIds))
            else:
                excludeMovieString = excludeMovieIds
            query += " AND mv.idMovie NOT IN (%s)" % excludeMovieString
            # different title
            query += " AND mv.c00 NOT IN (SELECT c00 FROM movieview WHERE idMovie IN (%s))" % excludeMovieString

        if actorIdNotInMovie:
            query += " AND mv.idMovie NOT IN (SELECT alm.idMovie FROM actorlinkmovie alm WHERE alm.idActor = " + self.PARAM_REPL + ")"
            params.append(int(actorIdNotInMovie))

        if actorIdInMovie:
            query += " AND mv.idMovie IN (SELECT alm.idMovie FROM actorlinkmovie alm WHERE alm.idActor = " + self.PARAM_REPL + ")"
            params.append(int(actorIdInMovie))

        if mustHaveTagline:
            query += " AND TRIM(mv.c03) != ''"

        if mustHaveRuntime:
            query += " AND TRIM(mv.c11) != ''"

        if maxRuntime:
            if isinstance(self, SQLiteDatabase):
                query += " AND CAST(mv.c11 AS INTEGER) < " + self.PARAM_REPL
            elif isinstance(self, MySQLDatabase):
                query += " AND CAST(mv.c11 AS SIGNED INTEGER) < " + self.PARAM_REPL
            params.append(int(maxRuntime))

        if minYear:
            query += " AND mv.c07 > " + self.PARAM_REPL
            params.append(int(minYear))

        if maxYear:
            query += " AND mv.c07 < " + self.PARAM_REPL
            params.append(int(maxYear))

        if directorId:
            query += " AND mv.idMovie IN (SELECT dlm.idMovie FROM directorlinkmovie dlm WHERE dlm.idDirector = " + self.PARAM_REPL + ")"
            params.append(int(directorId))

        if excludeDirectorId:
            query += " AND mv.idMovie NOT IN (SELECT dlm.idMovie FROM directorlinkmovie dlm WHERE dlm.idDirector = " + self.PARAM_REPL + ")"
            params.append(int(excludeDirectorId))

        if studioId:
            query += " AND mv.idMovie IN (SELECT slm.idMovie FROM studiolinkmovie slm WHERE slm.idStudio = " + self.PARAM_REPL + ")"
            params.append(int(studioId))

        if minActorCount:
            query += " AND (SELECT COUNT(DISTINCT alm.idActor) FROM actorlinkmovie alm WHERE alm.idMovie = mv.idMovie) >= " + self.PARAM_REPL
            params.append(int(minActorCount))

        query += " ORDER BY " + self.FUNC_RANDOM
        if maxResults:
            query += " LIMIT " + str(maxResults)

        return self.fetchall(query, params)


    def getMovieActors(self, maxResults = None, minMovieCount = None, excludeActorId = None, selectDistinct = None,
                        movieId = None, appendDefaultClause = True, mustHaveRole = False, excludeMovieIds = None):
        """
        Retrieves random movie actors from XBMC's video library.
        For each actor the following information is returned:
        * idActor
        * strActor
        * strRole

        @type maxResults: int
        @param maxResults: Retrieves this number of movies at most (actual number may be less than this)
        """
        params = []
        if selectDistinct:
            query = "SELECT DISTINCT "
        else:
            query = "SELECT "

        query += """
            a.idActor, a.strActor, alm.strRole
            FROM movieview mv, actorlinkmovie alm, actors a
            WHERE mv.idMovie = alm.idMovie AND alm.idActor = a.idActor AND mv.strFileName NOT LIKE '%%.nfo'
            """
        if appendDefaultClause:
            query += self.defaultMovieViewClause

        if excludeActorId:
            query += " AND alm.idActor != " + self.PARAM_REPL
            params.append(int(excludeActorId))

        if mustHaveRole:
            query += " AND alm.strRole != ''"

        if movieId:
            query += " AND mv.idMovie = " + self.PARAM_REPL
            params.append(int(movieId))
    
        if excludeMovieIds:
            if isinstance(excludeMovieIds, list):
                excludeMovieString = ','.join(map(str, excludeMovieIds))
            else:
                excludeMovieString = excludeMovieIds
            query += " AND mv.idMovie NOT IN (%s)" % excludeMovieString
            # different title
            query += " AND mv.c00 NOT IN (SELECT c00 FROM movieview WHERE idMovie IN (%s))" % excludeMovieString

        if minMovieCount:
            query += " GROUP BY alm.idActor HAVING count(mv.idMovie) >= " + self.PARAM_REPL
            params.append(int(minMovieCount))

        query += " ORDER BY " + self.FUNC_RANDOM
        if maxResults:
            query += " LIMIT " + str(maxResults)

        return self.fetchall(query, params)


    def getMovieDirectors(self, maxResults = None, minMovieCount = None, excludeDirectorId = None):
        params = []
        query = """
            SELECT a.idActor, a.strActor
            FROM movieview mv, directorlinkmovie dlm, actors a
            WHERE mv.idMovie = dlm.idMovie AND dlm.idDirector = a.idActor AND mv.strFileName NOT LIKE '%%.nfo'
            """ + self.defaultMovieViewClause

        if excludeDirectorId:
            query += " AND dlm.idDirector != " + self.PARAM_REPL
            params.append(int(excludeDirectorId))

        if minMovieCount:
            query += " GROUP BY dlm.idDirector HAVING count(mv.idMovie) >= " + self.PARAM_REPL
            params.append(int(minMovieCount))

        query += " ORDER BY " + self.FUNC_RANDOM
        if maxResults:
            query += " LIMIT " + str(maxResults)

        return self.fetchall(query, params)


    def getStudios(self, maxResults = None, excludeStudioId = None):
        params = []
        query = """
            SELECT s.idStudio, s.strStudio
            FROM movieview mv, studiolinkmovie slm, studio s
            WHERE mv.idMovie = slm.idMovie AND slm.idStudio = s.idStudio AND mv.strFileName NOT LIKE '%%.nfo'
            """ + self.defaultMovieViewClause

        if excludeStudioId:
            query += " AND slm.idStudio != " + self.PARAM_REPL
            params.append(int(excludeStudioId))

        query += " ORDER BY " + self.FUNC_RANDOM
        if maxResults:
            query += " LIMIT " + str(maxResults)

        return self.fetchall(query, params)


    def getTVShows(self, maxResults = None, excludeTVShowId = None, excludeSpecials = False, episode = None, mustHaveFirstAired = False, onlySelectTVShow = False):
        params = []
        if onlySelectTVShow:
            query = """
                SELECT tv.idShow, tv.c00 AS title, tv.strPath AS tvShowPath
                FROM tvshowview tv
                WHERE tv.idShow IN (SELECT idShow FROM tvshowlinkepisode)
                """
        else:
            query = """
                SELECT ev.idFile, tv.c00 AS title, ev.c05 AS firstAired, ev.c12 AS season, ev.c13 AS episode, ev.idShow, ev.strPath, ev.strFileName, tv.strPath AS tvShowPath
                FROM episodeview ev, tvshowview tv
                WHERE ev.idShow=tv.idShow AND ev.strFileName NOT LIKE '%%.nfo'
                """ + self.defaultTVShowViewClause

        if excludeTVShowId:
            query += " AND tv.idShow != " + self.PARAM_REPL
            params.append(int(excludeTVShowId))

        if excludeSpecials:
            query += " AND ev.c12 != 0"

        if episode:
            query += " AND ev.c13 = " + self.PARAM_REPL
            params.append(int(episode))

        if mustHaveFirstAired:
            query += " AND ev.c05 != ''"

        query += " ORDER BY " + self.FUNC_RANDOM
        if maxResults:
            query += " LIMIT " + str(maxResults)

        return self.fetchall(query, params)


    def getTVShowSeasons(self, maxResults = None, minSeasonCount = None, showId = None, excludeSeason = None, onlySelectSeason = False):
        params = []
        if onlySelectSeason:
            query = "SELECT DISTINCT ev.c12 AS season"
        else:
            query = """
                SELECT ev.idFile, ev.c12 AS season, tv.c00 AS title, ev.idShow, ev.strPath, ev.strFileName, tv.strPath AS tvShowPath, s.seasons
                """

        query += """
            FROM episodeview ev, tvshowview tv, (SELECT idShow, COUNT(DISTINCT c12) AS seasons FROM episodeview GROUP BY idShow) s
            WHERE ev.idShow=tv.idShow AND ev.idShow=s.idShow AND ev.strFileName NOT LIKE '%%.nfo'
            """

        if minSeasonCount:
            query += " AND s.seasons >= " + self.PARAM_REPL
            params.append(int(minSeasonCount))

        if showId:
            query += " AND ev.idShow = " + self.PARAM_REPL
            params.append(int(showId))

        if excludeSeason:
            query += " AND ev.c12 != " + self.PARAM_REPL
            params.append(int(excludeSeason))

        query += " ORDER BY " + self.FUNC_RANDOM
        if maxResults:
            query += " LIMIT " + str(maxResults)

        return self.fetchall(query, params)

    def getTVShowEpisodes(self, maxResults = None, minEpisodeCount = None, idShow = None, season = None, excludeEpisode = None):
        params = []
        query = """
            SELECT ev.idFile, ev.c00 AS episodeTitle, ev.c12 AS season, ev.c13 AS episode, tv.c00 AS title, ev.idShow, ev.strPath, ev.strFileName, ep.episodes
            FROM episodeview ev, tvshowview tv, (SELECT idShow, COUNT(DISTINCT c13) AS episodes FROM episodeview GROUP BY idShow) ep
            WHERE ev.idShow=tv.idShow AND ev.idShow=ep.idShow AND ev.strFileName NOT LIKE '%%.nfo'
            """

        if minEpisodeCount:
            query += " AND ep.episodes >= " + self.PARAM_REPL
            params.append(int(minEpisodeCount))

        if idShow:
            query += " AND ev.idShow = " + self.PARAM_REPL
            params.append(int(idShow))

        if season:
            query += " AND ev.c12 = " + self.PARAM_REPL
            params.append(int(season))

        if excludeEpisode:
            query += " AND ev.c13 != " + self.PARAM_REPL
            params.append(int(excludeEpisode))


        query += " ORDER BY " + self.FUNC_RANDOM
        if maxResults:
            query += " LIMIT " + str(maxResults)

        return self.fetchall(query, params)


    def getTVShowActors(self, maxResults = None, excludeActorId = None, selectDistinct = None, showId = None,
                        mustHaveRole = False, onlySelectActor = False):
        params = []
        if selectDistinct:
            query = "SELECT DISTINCT "
        else:
            query = "SELECT "

        if onlySelectActor:
            query += """
                alt.idActor, a.strActor, alt.strRole
                FROM actorlinktvshow alt, actors a
                WHERE alt.idActor=a.idActor
                """
        else:
            query += """
                alt.idActor, a.strActor, alt.strRole, tv.idShow, tv.c00 AS title, tv.strPath, tv.c08 AS genre
                FROM tvshowview tv, actorlinktvshow alt, actors a, episodeview ev
                WHERE tv.idShow = alt.idShow AND alt.idActor=a.idActor AND tv.idShow=ev.idShow AND ev.strFileName NOT LIKE '%%.nfo'
                """ + self.defaultTVShowViewClause

        if excludeActorId:
            query += " AND alt.idActor != " + self.PARAM_REPL
            params.append(int(excludeActorId))

        if mustHaveRole:
            query += " AND alt.strRole != ''"

        if showId:
            query += " AND alt.idShow = " + self.PARAM_REPL
            params.append(int(showId))

        query += " ORDER BY " + self.FUNC_RANDOM
        if maxResults:
            query += " LIMIT " + str(maxResults)

        return self.fetchall(query, params)


#
# SQLite
#

class SQLiteDatabase(Database):
    FUNC_RANDOM = "random()"
    PARAM_REPL = '?'
    
    def __init__(self, maxRating, onlyWatched, settings):
        super(SQLiteDatabase, self).__init__(maxRating, onlyWatched)
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

def _sqlite_dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        dot = col[0].find('.') + 1
        if dot != -1:
            d[col[0][dot:]] = row[idx]
        else:
            d[col[0]] = row[idx]
    return d


#
# MySQL
#

class MySQLDatabase(Database):
    FUNC_RANDOM = "rand()"
    PARAM_REPL = '%s'

    def __init__(self, maxRating, onlyUsedWatched, settings):
        super(MySQLDatabase, self).__init__(maxRating, onlyUsedWatched)
        xbmc.log("Connecting to MySQL database...")
        self.conn = mysql.connector.connect(
            host = settings['host'],
            user = settings['user'],
            passwd = settings['pass'],
            db = settings['name']
            )

        xbmc.log("MySQLDatabase opened")
        super(MySQLDatabase, self).postInit()

    def cursor(self):
        return self.conn.cursor(cursor_class = MySQLCursorDict)


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


class DbException(Exception):
    def __init__(self, sql):
        Exception.__init__(self, sql)




