# -*- coding: utf-8 -*-

"""HTTP File cache and helpers"""

__author__ = "fraser"

import logging
import sqlite3
import time
from datetime import datetime, timedelta, tzinfo
from os import path

import xbmc
import xbmcaddon
import xbmcvfs

try:
    import _pickle as cpickle
except ImportError:
    import cPickle as cpickle

logger = logging.getLogger(__name__)

HTTP_DATE_FORMAT = "%a, %d %b %Y %H:%M:%S %Z"
ADDON = xbmcaddon.Addon()
ADDON_PROFILE = ADDON.getAddonInfo("profile").encode("utf-8").decode("utf-8")
CACHE_URI = xbmc.translatePath(path.join(ADDON_PROFILE, "cache.sqlite"))


def httpdate_to_datetime(input_date):
    # type: (str) -> Optional[datetime]
    """Converts http date string to datetime"""
    if input_date is None:
        return None
    try:
        return datetime.strptime(input_date, HTTP_DATE_FORMAT)
    except TypeError:
        return datetime(*(time.strptime(input_date, HTTP_DATE_FORMAT)[0:6]))
    except ValueError as e:
        logger.debug(e)
        return None


def datetime_to_httpdate(input_date):
    # type: (datetime) -> Optional[str]
    """Converts datetime to http date string"""
    if input_date is None:
        return None
    try:
        return input_date.strftime(HTTP_DATE_FORMAT)
    except (ValueError, TypeError) as e:
        logger.debug(e)
        return None


def conditional_headers(row):
    # type: (sqlite3.Row) -> dict
    """Creates conditional request header dict based on etag and last_modified"""
    headers = {}
    if row["etag"] is not None:
        headers["If-None-Match"] = row["etag"]
    if row["last_modified"] is not None:
        headers["If-Modified-Since"] = datetime_to_httpdate(row["last_modified"])
    return headers


class Store(object):
    """
    Generic unique string storage helper
    Saves unique strings in a set that can
    be retrieved, appended to, removed from or cleared entirely
    """

    def __init__(self, key, db=None):
        # type: (str, str) -> None
        """
        Creates a new Store object
        key is the identifier that the set of strings are stored under
        db is the path to a sqlite3 database (defaults to Cache default)
        """
        self.db = db
        self.key = key

    def retrieve(self):
        # type: () -> set
        """Gets set of stored strings"""
        with Cache(self.db) as c:
            data = c.get(self.key)
            return data["blob"] if data else set()

    def _save(self, data):
        # type: (set) -> None
        """Saves set of strings"""
        with Cache(self.db) as c:
            if isinstance(data, set):
                c.set(self.key, data)

    def append(self, item):
        # type: (str) -> None
        """Add string to the store"""
        current = self.retrieve()
        current.add(item)
        self._save(current)

    def remove(self, item):
        # type: (str) -> None
        """Remove string from the store"""
        current = self.retrieve()
        current.remove(item)
        self._save(current)

    def clear(self):
        # type: () -> None
        """Clears the store of all data"""
        with Cache(self.db) as c:
            c.delete(self.key)


class GMT(tzinfo):
    """GMT Time Zone"""

    def utcoffset(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return "GMT"

    def dst(self, dt):
        return timedelta(0)


class Blob(object):
    """Blob serialisation class"""

    def __init__(self, data):
        self.data = data

    def __conform__(self, protocol):
        if protocol is sqlite3.PrepareProtocol:
            return sqlite3.Binary(cpickle.dumps(self.data, -1))

    @staticmethod
    def deserialise(data):
        # type: (bytes) -> Any
        return cpickle.loads(bytes(data))


class Cache(object):
    """
    HTTP control directive based cache
    https://docs.python.org/2/library/sqlite3.html
    https://tools.ietf.org/html/rfc7234
    """

    def __init__(self, db=None):
        # type: (str) -> None
        """
        Creates a new Cache object
        db is the path to a sqlite3 database (defaults to CACHE_URI)
        """
        self.connection = None
        self.db = CACHE_URI if db is None else db
        if not xbmcvfs.exists(self.db):
            xbmcvfs.mkdirs(path.dirname(self.db))
        self._open(self.db)

    def get(self, uri):
        # type: (str) -> Optional[sqlite3.Row]
        """Retrieve a partial entry from the cache"""
        query = """SELECT blob, last_modified, etag, immutable,
                 CASE
                   WHEN max_age THEN max(age, max_age)
                   ELSE CASE
                       WHEN expires THEN expires - http_date
                       ELSE cast((datetime('now') - last_modified) / 10 as int)
                   END
                 END >= strftime('%s', datetime('now')) - strftime('%s', http_date) AS fresh 
                 FROM data WHERE uri=?"""
        result = self._execute(query, (uri,))
        return None if result is None else result.fetchone()

    def set(self, uri, content, headers=None):
        # type: (str, Any, dict) -> None
        """Add or update a complete entry in the cache"""
        if headers is None:
            headers = {
                "date": datetime_to_httpdate(datetime.now(GMT())),
                "cache-control": "immutable, max-age=31556926"  # 1 year
            }
        directives = self._parse_cache_control(headers.get("cache-control"))
        # never store items marked "no-store"
        if "no-store" in directives:
            return
        query = """REPLACE INTO data (uri, blob, http_date, age, etag, expires, last_modified, max_age, immutable)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        values = (
            uri,
            Blob(content),
            httpdate_to_datetime(headers.get("date")),
            headers.get("age", 0),
            headers.get("etag"),
            httpdate_to_datetime(headers.get("expires")),
            httpdate_to_datetime(headers.get("last-modified")),
            directives.get("max-age"),
            directives.get("immutable"))
        self._execute(query, values)

    def touch(self, uri, headers):
        # type: (str, dict) -> None
        """Updates the meta data on an entry in the cache"""
        directives = self._parse_cache_control(headers.get("cache-control"))
        query = "UPDATE data SET http_date=?, age=?, expires=?, last_modified=?, max_age=? WHERE uri=?"
        values = (
            httpdate_to_datetime(headers.get("date")),
            headers.get("age"),
            httpdate_to_datetime(headers.get("expires")),
            httpdate_to_datetime(headers.get("last-modified")),
            directives.get("max-age"),
            uri)
        self._execute(query, values)

    def delete(self, uri):
        # type: (str) -> None
        """Remove an entry from the cache via uri"""
        query = "DELETE FROM data WHERE uri=?"
        self._execute(query, (uri,))

    def domain(self, domain, limit=25):
        # type: (str, int) -> list
        """Get items where uri like %domain%"""
        query = "SELECT * FROM data WHERE uri LIKE ? ORDER BY http_date LIMIT ?"
        cursor = self._execute(query, ('%{}%'.format(domain), limit))
        return [] if cursor is None else cursor.fetchall()

    def clear(self):
        # type: () -> None
        """Truncates the cache data and vacuums"""
        self._execute("DELETE FROM data")
        self._execute("VACUUM")

    @staticmethod
    def _parse_cache_control(header):
        # type: (str) -> dict
        """See https://tools.ietf.org/html/rfc7234#section-5.2"""
        if header is None:
            return {}
        return {
            parts[0].strip():
                [int(parts[1]) if len(parts) > 1 else True][0]
            for directive in header.split(",")
            for parts in [directive.split("=")]
        }

    def _execute(self, query, values=None):
        # type: (str, tuple) -> sqlite3.Cursor
        if values is None:
            values = ()
        try:
            # Automatically commits or rolls back on exception
            with self.connection:
                return self.connection.execute(query, values)
        except (sqlite3.IntegrityError, sqlite3.OperationalError) as e:
            logger.debug(e)

    def _open(self, name):
        # type: (str) -> None
        sqlite3.enable_callback_tracebacks(True)
        sqlite3.register_converter("BLOB", Blob.deserialise)
        try:
            self.connection = sqlite3.connect(name, timeout=1, detect_types=sqlite3.PARSE_DECLTYPES)
        except sqlite3.Error as e:
            logger.debug(e)
            return
        # see: https://docs.python.org/2/library/sqlite3.html#sqlite3.Connection.row_factory
        self.connection.row_factory = sqlite3.Row
        self.connection.text_factory = sqlite3.OptimizedUnicode
        self._create_table()

    def _close(self):
        # type: () -> None
        """Closes any open connection and cursor"""
        # remove module level register_converter 
        # see: https://github.com/jdf76/plugin.video.youtube/issues/640
        del sqlite3.converters["BLOB"]  
        if self.connection:
            self.connection.cursor().close()
            self.connection.close()

    def _create_table(self):
        # type: () -> None
        query = """CREATE TABLE IF NOT EXISTS data (
                uri TEXT PRIMARY KEY NOT NULL,
                blob BLOB NOT NULL,
                http_date TIMESTAMP NOT NULL,
                age INTEGER DEFAULT 0,
                etag TEXT,
                expires TIMESTAMP,
                last_modified TIMESTAMP,
                max_age INTEGER,
                immutable INTEGER DEFAULT 0)"""
        self._execute(query)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._close()
