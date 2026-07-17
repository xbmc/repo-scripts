#!/usr/bin/python
# -*- coding: utf-8 -*-
import zlib
import xbmcvfs
from xbmc import Monitor
from xbmcgui import Window
from jurialmunkey.locker import MutexPropLock
from jurialmunkey.tmdate import set_timestamp
from jurialmunkey.futils import FileUtils
from jurialmunkey.futils import json_loads as data_loads
from json import dumps as data_dumps
import sqlite3


FILEUTILS = FileUtils()


DATABASE_NAME = 'database_v6'
TIME_MINUTES = 60
TIME_HOURS = 60 * TIME_MINUTES
TIME_DAYS = 24 * TIME_HOURS


class SimpleCache(object):
    '''simple stateless caching system for Kodi'''
    _exit = False
    _auto_clean_interval = 4 * TIME_HOURS
    _database = None
    _basefolder = ''
    _fileutils = FILEUTILS
    _db_timeout = 3.0
    _db_read_timeout = 1.0
    _row_factory = False

    def __init__(self, folder=None, filename=None):
        '''Initialize our caching class'''
        folder = folder or DATABASE_NAME
        basefolder = f'{self._basefolder}{folder}'
        filename = filename or 'defaultcache.db'

        self._db_file = self._fileutils.get_file_path(basefolder, filename, join_addon_data=basefolder == folder)
        self._sc_name = f'{folder}_{filename}_simplecache'

        self.check_cleanup()
        self.kodi_log(f"CACHE: Initialized: {self._sc_name} - Thread Safety Level: {sqlite3.threadsafety} - SQLite v{sqlite3.sqlite_version}")

    @property
    def monitor(self):
        try:
            return self._monitor
        except AttributeError:
            self._monitor = Monitor()
            return self._monitor

    def get_window_property(self, name):
        return Window(10000).getProperty(name)

    def set_window_property(self, name, value):
        return Window(10000).setProperty(name, value)

    def del_window_property(self, name):
        return Window(10000).clearProperty(name)

    def exit_requested(self):
        return self._exit or self.monitor.abortRequested()

    @staticmethod
    def kodi_log(msg, level=0):
        from jurialmunkey.logger import Logger
        Logger('[script.module.jurialmunkey]\n').kodi_log(msg, level)

    def close(self):
        '''tell any tasks to stop immediately (as we can be called multithreaded) and cleanup objects'''
        self._exit = True

    def get(self, endpoint, cur_time=None):
        '''
            get object from cache and return the results
            endpoint: the (unique) name of the cache object as reference
        '''
        cur_time = cur_time or set_timestamp(0, True)
        result = None
        # result = result or self._get_mem_cache(endpoint, cur_time)  # Try from memory first
        result = result or self._get_db_cache(endpoint, cur_time)  # Fallback to checking database if not in memory
        return result

    def set(self, endpoint, data, cache_days=30):
        """ set data in cache """
        expires = set_timestamp(cache_days * TIME_DAYS, True)
        data = data_dumps(data, separators=(',', ':'))
        self._set_db_cache(endpoint, expires, data)

    def check_cleanup(self):
        '''check if cleanup is needed - public method, may be called by calling addon'''
        lastexecuted = self.get_window_property(f'{self._sc_name}.clean.lastexecuted')

        if not lastexecuted:
            self._init_database()
            return

        cur_time = set_timestamp(0, True)
        if (int(lastexecuted) + self._auto_clean_interval) < cur_time:
            self._do_cleanup()

    def _get_mem_cache(self, endpoint, cur_time):
        '''
            get cache data from memory cache
            we use window properties because we need to be stateless
        '''
        # Check expiration time
        expr_endpoint = f'{self._sc_name}_expr_{endpoint}'
        expr_propdata = self.get_window_property(expr_endpoint)
        if not expr_propdata or int(expr_propdata) <= cur_time:
            return

        # Retrieve data
        data_endpoint = f'{self._sc_name}_data_{endpoint}'
        data_propdata = self.get_window_property(data_endpoint)
        if not data_propdata:
            return

        return data_loads(data_propdata)

    def _set_mem_cache(self, endpoint, expires, data):
        '''
            window property cache as alternative for memory cache
            usefull for (stateless) plugins
        '''
        expr_endpoint = f'{self._sc_name}_expr_{endpoint}'
        data_endpoint = f'{self._sc_name}_data_{endpoint}'
        self.set_window_property(expr_endpoint, str(expires))
        self.set_window_property(data_endpoint, data)

    def _get_db_cache(self, endpoint, cur_time):
        '''get cache data from sqllite _database'''

        query = "SELECT expires, data, checksum FROM simplecache WHERE id = ? LIMIT 1"
        connection = self._execute_sql(query, (endpoint,), read_only=True)

        if not connection:
            return

        cache_data = connection.fetchone()
        connection.close()

        if not cache_data:
            return

        try:
            expires = int(cache_data[0])  # Check we can convert expiry to int otherwise assume has expired.
            data = cache_data[1]  # Check that we can get data from cache otherwise return None.
        except TypeError:
            return

        if expires <= cur_time:
            return

        try:
            data = str(zlib.decompress(data), 'utf-8')
        except Exception as error:
            self.kodi_log(f'CACHE: _get_db_cache zlib.decompress error: {error}\n{self._sc_name} - {endpoint}', 1)
            return

        try:
            result = data_loads(data)  # Confirm that data is valid JSON
        except Exception as error:
            self.kodi_log(f'CACHE: _get_db_cache data_loads error: {error}\n{self._sc_name} - {endpoint}', 1)
            return

        # Uncomment to set db cache reads to mem
        # self._set_mem_cache(endpoint, cache_data[0], data)

        return result

    def _set_db_cache(self, endpoint, expires, data):
        ''' store cache data in _database '''
        query = "INSERT OR REPLACE INTO simplecache( id, expires, data, checksum) VALUES (?, ?, ?, ?)"
        try:
            data = zlib.compress(bytes(data, 'utf-8'))
        except Exception as error:
            self.kodi_log(f'CACHE: _set_db_cache zlib.compress error: {error}\n{self._sc_name} - {endpoint}', 1)
            return
        connection = self._execute_sql(query, (endpoint, expires, data, 0))
        connection.close() if connection else None

    def _do_delete(self):
        """ Delete all cache entries in simplecache """
        if self.exit_requested():
            return

        self.set_window_property(f'{self._sc_name}.cleanbusy', "busy")
        self.kodi_log(f'CACHE: Deleting {self._sc_name}...')

        query = 'DELETE FROM simplecache'
        connection = self._execute_sql(query)
        connection.close() if connection else None

        connection = self._execute_sql("VACUUM")
        connection.close() if connection else None

        # Washup
        cur_time = set_timestamp(0, True)
        self.set_window_property(f'{self._sc_name}.clean.lastexecuted', str(cur_time))
        self.del_window_property(f'{self._sc_name}.cleanbusy')
        self.kodi_log(f'CACHE: Delete {self._sc_name} done')

    def _do_cleanup(self, force=False):
        """ Delete expired cache objects from simplecache """
        if self.exit_requested():
            return

        if self.get_window_property(f'{self._sc_name}.cleanbusy'):
            return

        self.kodi_log(f"CACHE: Running cleanup...\n{self._sc_name}", 1)
        self.set_window_property(f'{self._sc_name}.cleanbusy', "busy")

        with MutexPropLock(f'{self._db_file}.lockfile', kodi_log=self.kodi_log):
            cur_time = set_timestamp(0, True)
            query = "SELECT id, expires FROM simplecache"

            connection = self._execute_sql(query)
            if not connection:
                return
            fetch_data = connection.fetchall()
            connection.close()

            for cache_data in fetch_data:
                if self.exit_requested():
                    return

                cache_id, cache_expires = cache_data[0], cache_data[1]

                # always cleanup all memory objects on each interval
                self.del_window_property(cache_id)

                # check expiry
                if not force and int(cache_expires) >= cur_time:
                    continue

                # delete
                query = 'DELETE FROM simplecache WHERE id = ?'
                connection = self._execute_sql(query, (cache_id,))
                connection.close() if connection else None

                # logging
                self.kodi_log(f'CACHE: delete from db {cache_id}')

            # compact db
            connection = self._execute_sql("VACUUM")
            connection.close() if connection else None

            # Washup
            self.set_window_property(f'{self._sc_name}.clean.lastexecuted', str(cur_time))
            self.del_window_property(f'{self._sc_name}.cleanbusy')

        # logging
        self.kodi_log(f"CACHE: Cleanup complete...\n{self._sc_name}", 1)

    def _set_pragmas(self, connection):
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def _init_database(self):
        with MutexPropLock(f'{self._db_file}.lockfile', kodi_log=self.kodi_log):
            if xbmcvfs.exists(self._db_file):
                return
            database = self._create_database()
            cur_time = set_timestamp(0, True)
            self.set_window_property(f'{self._sc_name}.clean.lastexecuted', str(cur_time - self._auto_clean_interval + 600))
        return database

    @staticmethod
    def create_database_execute(connection):
        connection.execute("""
            CREATE TABLE IF NOT EXISTS simplecache(
                id TEXT UNIQUE,
                expires INTEGER,
                data TEXT,
                checksum INTEGER
            )""")

    def _create_database(self):
        try:
            self.kodi_log(f'CACHE: Initialising: {self._db_file}...', 1)
            connection = sqlite3.connect(self._db_file, timeout=5.0, isolation_level=None)
            self.create_database_execute(connection)
        except Exception as error:
            self.kodi_log(f'CACHE: Exception while initializing _database: {error}\n{self._sc_name}', 1)
        try:
            connection.execute("CREATE INDEX idx ON simplecache(id)")
        except Exception as error:
            self.kodi_log(f'CACHE: Exception while creating index for _database: {error}\n{self._sc_name}', 1)
        try:
            return self._set_pragmas(connection)
        except Exception as error:
            self.kodi_log(f'CACHE: Exception while setting pragmas for _database: {error}\n{self._sc_name}', 1)

    def _get_database(self, read_only=False, log_level=1):
        timeout = self._db_read_timeout if read_only else self._db_timeout
        try:
            connection = sqlite3.connect(self._db_file, timeout=timeout, isolation_level=None)
            # connection.execute('SELECT * FROM simplecache LIMIT 1')  # Integrity check ?
        except Exception as error:
            self.kodi_log(f'CACHE: ERROR while retrieving _database: {error}\n{self._sc_name}', log_level)
            return
        if self._row_factory:
            connection.row_factory = sqlite3.Row
        return self._set_pragmas(connection)

    def _execute_sql(self, query, data=None, read_only=False):
        '''little wrapper around execute and executemany to just retry a db command if db is locked'''

        def database_execute(database):
            try:
                if not data:
                    return database.execute(query)
                if isinstance(data, list):
                    return database.executemany(query, data)
                return database.execute(query, data)
            except sqlite3.OperationalError as operational_exception:
                self.kodi_log(f'CACHE: database OPERATIONAL ERROR! -- {operational_exception}\n{self._sc_name} -- read_only: {read_only}', 2)
            except Exception as other_exception:
                self.kodi_log(f'CACHE: database OTHER ERROR! -- {other_exception}\n{self._sc_name} -- read_only: {read_only}', 2)

        # always use new db object because we need to be sure that data is available for other simplecache instances
        try:
            with self._get_database(read_only=read_only) as database:
                return database_execute(database)

        except Exception as database_exception:
            self.kodi_log(f'CACHE: database GET DATABASE ERROR! -- {database_exception}\n{self._sc_name} -- read_only: {read_only}', 2)
