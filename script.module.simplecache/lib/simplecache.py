#!/usr/bin/python
# -*- coding: utf-8 -*-

'''provides a simple stateless caching system for Kodi addons and plugins'''

import sys
import xbmcvfs
import xbmcgui
import xbmc
import xbmcaddon
import datetime
import time
import sqlite3
from functools import reduce

ADDON_ID = "script.module.simplecache"
PYTHON3 = True if sys.version_info.major == 3 else False

class SimpleCache(object):
    '''simple stateless caching system for Kodi'''
    enable_mem_cache = True
    global_checksum = None
    _exit = False
    _auto_clean_interval = datetime.timedelta(hours=4)
    _win = None
    _busy_tasks = []
    _database = None

    def __init__(self):
        '''Initialize our caching class'''
        self._win = xbmcgui.Window(10000)
        self._monitor = xbmc.Monitor()
        self.check_cleanup()
        self._log_msg("Initialized")

    def close(self):
        '''tell any tasks to stop immediately (as we can be called multithreaded) and cleanup objects'''
        self._exit = True
        # wait for all tasks to complete
        while self._busy_tasks and not self._monitor.abortRequested():
            xbmc.sleep(25)
        del self._win
        del self._monitor
        self._log_msg("Closed")

    def __del__(self):
        '''make sure close is called'''
        if not self._exit:
            self.close()

    def get(self, endpoint, checksum=""):
        '''
            get object from cache and return the results
            endpoint: the (unique) name of the cache object as reference
            checkum: optional argument to check if the checksum in the cacheobject matches the checkum provided
        '''
        checksum = self._get_checksum(checksum)
        cur_time = self._get_timestamp(datetime.datetime.now())
        result = None
        # 1: try memory cache first
        if self.enable_mem_cache:
            result = self._get_mem_cache(endpoint, checksum, cur_time)

        # 2: fallback to _database cache
        if result is None:
            result = self._get_db_cache(endpoint, checksum, cur_time)

        return result

    def set(self, endpoint, data, checksum="", expiration=datetime.timedelta(days=30)):
        '''
            set data in cache
        '''
        task_name = "set.%s" % endpoint
        self._busy_tasks.append(task_name)
        checksum = self._get_checksum(checksum)
        expires = self._get_timestamp(datetime.datetime.now() + expiration)

        # memory cache: write to window property
        if self.enable_mem_cache and not self._exit:
            self._set_mem_cache(endpoint, checksum, expires, data)

        # db cache
        if not self._exit:
            self._set_db_cache(endpoint, checksum, expires, data)

        # remove this task from list
        self._busy_tasks.remove(task_name)

    def check_cleanup(self):
        '''check if cleanup is needed - public method, may be called by calling addon'''
        cur_time = datetime.datetime.now()
        lastexecuted = self._win.getProperty("simplecache.clean.lastexecuted")
        if not lastexecuted:
            self._win.setProperty("simplecache.clean.lastexecuted", repr(cur_time))
        elif (eval(lastexecuted) + self._auto_clean_interval) < cur_time:
            # cleanup needed...
            self._do_cleanup()

    def _get_mem_cache(self, endpoint, checksum, cur_time):
        '''
            get cache data from memory cache
            we use window properties because we need to be stateless
        '''
        result = None

        if not PYTHON3:
            cachedata = self._win.getProperty(endpoint.encode("utf-8"))
        else:
            cachedata = self._win.getProperty(endpoint)

        if cachedata:
            cachedata = eval(cachedata)
            if cachedata[0] > cur_time:
                if not checksum or checksum == cachedata[2]:
                    result = cachedata[1]
        return result

    def _set_mem_cache(self, endpoint, checksum, expires, data):
        '''
            window property cache as alternative for memory cache
            usefull for (stateless) plugins
        '''
        cachedata = (expires, data, checksum)

        if not PYTHON3:
            cachedata_str = repr(cachedata).encode("utf-8")
            self._win.setProperty(endpoint.encode("utf-8"), cachedata_str)
        else:
            cachedata_str = repr(cachedata)
            self._win.setProperty(endpoint, cachedata_str)


    def _get_db_cache(self, endpoint, checksum, cur_time):
        '''get cache data from sqllite _database'''
        result = None
        query = "SELECT expires, data, checksum FROM simplecache WHERE id = ?"
        cache_data = self._execute_sql(query, (endpoint,))
        if cache_data:
            cache_data = cache_data.fetchone()
            if cache_data and cache_data[0] > cur_time:
                if not checksum or cache_data[2] == checksum:
                    result = eval(cache_data[1])
                    # also set result in memory cache for further access
                    if self.enable_mem_cache:
                        self._set_mem_cache(endpoint, checksum, cache_data[0], result)
        return result

    def _set_db_cache(self, endpoint, checksum, expires, data):
        ''' store cache data in _database '''
        query = "INSERT OR REPLACE INTO simplecache( id, expires, data, checksum) VALUES (?, ?, ?, ?)"
        data = repr(data)
        self._execute_sql(query, (endpoint, expires, data, checksum))

    def _do_cleanup(self):
        '''perform cleanup task'''
        if self._exit or self._monitor.abortRequested():
            return
        self._busy_tasks.append(__name__)
        cur_time = datetime.datetime.now()
        cur_timestamp = self._get_timestamp(cur_time)
        self._log_msg("Running cleanup...")
        if self._win.getProperty("simplecachecleanbusy"):
            return
        self._win.setProperty("simplecachecleanbusy", "busy")

        query = "SELECT id, expires FROM simplecache"
        for cache_data in self._execute_sql(query).fetchall():
            cache_id = cache_data[0]
            cache_expires = cache_data[1]
            if self._exit or self._monitor.abortRequested():
                return
            # always cleanup all memory objects on each interval
            if not PYTHON3:
                self._win.clearProperty(cache_id.encode("utf-8"))
            else:
                self._win.clearProperty(cache_id)
            # clean up db cache object only if expired
            if cache_expires < cur_timestamp:
                query = 'DELETE FROM simplecache WHERE id = ?'
                self._execute_sql(query, (cache_id,))
                self._log_msg("delete from db %s" % cache_id)

        # compact db
        self._execute_sql("VACUUM")

        # remove task from list
        self._busy_tasks.remove(__name__)
        self._win.setProperty("simplecache.clean.lastexecuted", repr(cur_time))
        self._win.clearProperty("simplecachecleanbusy")
        self._log_msg("Auto cleanup done")

    def _get_database(self):
        '''get reference to our sqllite _database - performs basic integrity check'''
        addon = xbmcaddon.Addon(ADDON_ID)
        dbpath = addon.getAddonInfo('profile')

        if not PYTHON3:
            dbfile = xbmc.translatePath("%s/simplecache.db" % dbpath).decode('utf-8')
        else:
            dbfile = xbmc.translatePath("%s/simplecache.db" % dbpath)

        if not xbmcvfs.exists(dbpath):
            xbmcvfs.mkdirs(dbpath)
        del addon
        try:
            connection = sqlite3.connect(dbfile, timeout=30, isolation_level=None)
            connection.execute('SELECT * FROM simplecache LIMIT 1')
            return connection
        except Exception as error:
            # our _database is corrupt or doesn't exist yet, we simply try to recreate it
            if xbmcvfs.exists(dbfile):
                xbmcvfs.delete(dbfile)
            try:
                connection = sqlite3.connect(dbfile, timeout=30, isolation_level=None)
                connection.execute(
                    """CREATE TABLE IF NOT EXISTS simplecache(
                    id TEXT UNIQUE, expires INTEGER, data TEXT, checksum INTEGER)""")
                return connection
            except Exception as error:
                self._log_msg("Exception while initializing _database: %s" % str(error), xbmc.LOGWARNING)
                self.close()
                return None

    def _execute_sql(self, query, data=None):
        '''little wrapper around execute and executemany to just retry a db command if db is locked'''
        retries = 0
        result = None
        error = None
        # always use new db object because we need to be sure that data is available for other simplecache instances
        with self._get_database() as _database:
            while not retries == 10 and not self._monitor.abortRequested():
                if self._exit:
                    return None
                try:
                    if isinstance(data, list):
                        result = _database.executemany(query, data)
                    elif data:
                        result = _database.execute(query, data)
                    else:
                        result = _database.execute(query)
                    return result
                except sqlite3.OperationalError as error:
                    if "_database is locked" in error:
                        self._log_msg("retrying DB commit...")
                        retries += 1
                        self._monitor.waitForAbort(0.5)
                    else:
                        break
                except Exception as error:
                    break
            self._log_msg("_database ERROR ! -- %s" % str(error), xbmc.LOGWARNING)
        return None

    @staticmethod
    def _log_msg(msg, loglevel=xbmc.LOGDEBUG):
        '''helper to send a message to the kodi log'''
        if not PYTHON3 and isinstance(msg, unicode):
            msg = msg.encode('utf-8')

        xbmc.log("Skin Helper Simplecache --> %s" % msg, level=loglevel)

    @staticmethod
    def _get_timestamp(date_time):
        '''Converts a datetime object to unix timestamp'''
        return int(time.mktime(date_time.timetuple()))

    def _get_checksum(self, stringinput):
        '''get int checksum from string'''
        if not stringinput and not self.global_checksum:
            return 0
        if self.global_checksum:
            stringinput = "%s-%s" %(self.global_checksum, stringinput)
        else:
            stringinput = str(stringinput)
        return reduce(lambda x, y: x + y, map(ord, stringinput))


def use_cache(cache_days=14):
    '''
        wrapper around our simple cache to use as decorator
        Usage: define an instance of SimpleCache with name "cache" (self.cache) in your class
        Any method that needs caching just add @use_cache as decorator
        NOTE: use unnamed arguments for calling the method and named arguments for optional settings
    '''
    def decorator(func):
        '''our decorator'''
        def decorated(*args, **kwargs):
            '''process the original method and apply caching of the results'''
            method_class = args[0]
            method_class_name = method_class.__class__.__name__
            cache_str = "%s.%s" % (method_class_name, func.__name__)
            # cache identifier is based on positional args only
            # named args are considered optional and ignored
            for item in args[1:]:
                cache_str += u".%s" % item
            cache_str = cache_str.lower()
            cachedata = method_class.cache.get(cache_str)
            global_cache_ignore = False
            try:
                global_cache_ignore = method_class.ignore_cache
            except Exception:
                pass
            if cachedata is not None and not kwargs.get("ignore_cache", False) and not global_cache_ignore:
                return cachedata
            else:
                result = func(*args, **kwargs)
                method_class.cache.set(cache_str, result, expiration=datetime.timedelta(days=cache_days))
                return result
        return decorated
    return decorator
