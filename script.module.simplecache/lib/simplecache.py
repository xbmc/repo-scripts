#!/usr/bin/python
# -*- coding: utf-8 -*-

'''provides a simple stateless caching system for Kodi addons and plugins'''

import xbmcvfs
import xbmcgui
import xbmc
import xbmcaddon
import datetime
import time
import sqlite3
from functools import reduce

ADDON_ID = "script.module.simplecache"


class SimpleCache(object):
    '''simple stateless caching system for Kodi'''
    exit = False
    auto_clean_interval = datetime.timedelta(hours=4)
    enable_mem_cache = True
    win = None
    busy_tasks = []
    multithreaded = False
    database = None

    def __init__(self):
        '''Initialize our caching class'''
        self.win = xbmcgui.Window(10000)
        self.monitor = xbmc.Monitor()
        self.check_cleanup()
        self.log_msg("Initialized")

    def close(self):
        '''tell any tasks to stop immediately (as we can be called multithreaded) and cleanup objects'''
        self.exit = True
        # wait for all tasks to complete
        while self.busy_tasks:
            xbmc.sleep(25)
        self.win = None
        self.monitor = None
        del self.win
        del self.monitor
        self.log_msg("Closed")

    def __del__(self):
        '''make sure close is called'''
        if not self.exit:
            self.close()

    def get(self, endpoint, checksum=""):
        '''
            get object from cache and return the results
            endpoint: the (unique) name of the cache object as reference
            checkum: optional argument to check if the checksum in the cacheobject matches the checkum provided
        '''
        checksum = self.get_checksum(checksum)
        cur_time = self.get_timestamp(datetime.datetime.now())

        # 1: try memory cache first
        if self.enable_mem_cache:
            result = self.get_mem_cache(endpoint, checksum, cur_time)

        # 2: fallback to database cache
        if result is None:
            result = self.get_db_cache(endpoint, checksum, cur_time)

        return result

    def set(self, endpoint, data, checksum="", expiration=datetime.timedelta(days=30)):
        '''
            set data in cache
        '''
        task_name = "set.%s" % endpoint
        self.busy_tasks.append(task_name)
        checksum = self.get_checksum(checksum)
        expires = self.get_timestamp(datetime.datetime.now() + expiration)

        # memory cache: write to window property
        if self.enable_mem_cache and not self.exit:
            self.set_mem_cache(endpoint, checksum, expires, data)

        # db cache
        if not self.exit:
            self.set_db_cache(endpoint, checksum, expires, data)

        # remove this task from list
        self.busy_tasks.remove(task_name)

    def get_mem_cache(self, endpoint, checksum, cur_time):
        '''
            get cache data from memory cache
            we use window properties because we need to be stateless
        '''
        result = None
        cachedata = self.win.getProperty(endpoint.encode("utf-8"))
        if cachedata:
            cachedata = eval(cachedata)
            if cachedata[0] > cur_time:
                if not checksum or checksum == cachedata[2]:
                    result = cachedata[1]
        return result

    def set_mem_cache(self, endpoint, checksum, expires, data):
        '''
            window property cache as alternative for memory cache
            usefull for (stateless) plugins
        '''
        cachedata = (expires, data, checksum)
        cachedata_str = repr(cachedata).encode("utf-8")
        self.win.setProperty(endpoint.encode("utf-8"), cachedata_str)

    def get_db_cache(self, endpoint, checksum, cur_time):
        '''get cache data from sqllite database'''
        result = None
        query = "SELECT expires, data, checksum FROM simplecache WHERE id = ?"
        cache_data = self.execute_sql(query, (endpoint,))
        if cache_data:
            cache_data = cache_data.fetchone()
            if cache_data and cache_data[0] > cur_time:
                if not checksum or cache_data[2] == checksum:
                    result = eval(cache_data[1])
                    # also set result in memory cache for further access
                    if self.enable_mem_cache:
                        self.set_mem_cache(endpoint, checksum, cache_data[0], result)
        return result

    def set_db_cache(self, endpoint, checksum, expires, data):
        ''' store cache data in database '''
        query = "INSERT OR REPLACE INTO simplecache( id, expires, data, checksum) VALUES (?, ?, ?, ?)"
        data = repr(data)
        self.execute_sql(query, (endpoint, expires, data, checksum))

    def check_cleanup(self):
        '''check if cleanup is needed'''
        cur_time = datetime.datetime.now()
        lastexecuted = self.win.getProperty("simplecache.clean.lastexecuted")
        if not lastexecuted:
            self.win.setProperty("simplecache.clean.lastexecuted", repr(cur_time))
        elif (eval(lastexecuted) + self.auto_clean_interval) < cur_time:
            # cleanup needed...
            self.do_cleanup()

    def do_cleanup(self):
        '''perform cleanup task'''
        if self.exit or self.monitor.abortRequested():
            return
        self.busy_tasks.append(__name__)
        cur_time = datetime.datetime.now()
        cur_timestamp = self.get_timestamp(cur_time)
        self.log_msg("Running cleanup...")
        if self.win.getProperty("simplecachecleanbusy"):
            return
        self.win.setProperty("simplecachecleanbusy", "busy")

        query = "SELECT id, expires FROM simplecache"
        for cache_data in self.execute_sql(query).fetchall():
            if self.exit or self.monitor.abortRequested():
                return
            # always cleanup all memory objects on each interval
            self.win.clearProperty(cache_data[0].encode("utf-8"))
            # clean up db cache object only if expired
            if cache_data[1] < cur_timestamp:
                query = 'DELETE FROM simplecache WHERE id = ?'
                self.execute_sql(query, (cache_data[0],))
                self.log_msg("delete from db %s" % cache_data[0])

        # compact db
        self.execute_sql("VACUUM")

        # remove task from list
        self.busy_tasks.remove(__name__)
        self.win.setProperty("simplecache.clean.lastexecuted", repr(cur_time))
        self.win.clearProperty("simplecachecleanbusy")
        self.log_msg("Auto cleanup done")

    def get_database(self):
        '''get reference to our sqllite database - performs basic integrity check'''
        addon = xbmcaddon.Addon(ADDON_ID)
        dbpath = addon.getAddonInfo('profile')
        dbfile = xbmc.translatePath("%s/simplecache.db" % dbpath).decode('utf-8')
        del addon
        try:
            connection = sqlite3.connect(dbfile, timeout=30, isolation_level=None)
            connection.execute('SELECT * FROM simplecache LIMIT 1')
            return connection
        except Exception as error:
            # our database is corrupt or doesn't exist yet, we simply try to recreate it
            if xbmcvfs.exists(dbfile):
                xbmcvfs.delete(dbfile)
            if not xbmcvfs.exists(dbpath):
                xbmcvfs.mkdir(dbpath)
            try:
                connection = sqlite3.connect(dbfile, timeout=30, isolation_level=None)
                connection.execute(
                    """CREATE TABLE IF NOT EXISTS simplecache(
                    id TEXT UNIQUE, expires INTEGER, data TEXT, checksum INTEGER)""")
                return connection
            except Exception as error:
                self.log_msg("Exception while initializing database: %s" % str(error), xbmc.LOGWARNING)
                self.close()
                return None

    def execute_sql(self, query, data=None):
        '''little wrapper around execute and executemany to just retry a db command if db is locked'''
        retries = 0
        result = None
        error = None
        # always use new db object because we need to be sure that data is available for other simplecache instances
        with self.get_database() as database:
            while not retries == 10:
                if self.exit:
                    return None
                try:
                    if isinstance(data, list):
                        result = database.executemany(query, data)
                    elif data:
                        result = database.execute(query, data)
                    else:
                        result = database.execute(query)
                    return result
                except sqlite3.OperationalError as error:
                    if "database is locked" in error:
                        self.log_msg("retrying DB commit...")
                        retries += 1
                        self.monitor.waitForAbort(0.5)
                    else:
                        break
                except Exception as error:
                    break
            self.log_msg("Database ERROR ! -- %s" % str(error), xbmc.LOGWARNING)
        return None

    @staticmethod
    def log_msg(msg, loglevel=xbmc.LOGDEBUG):
        '''helper to send a message to the kodi log'''
        if isinstance(msg, unicode):
            msg = msg.encode('utf-8')
        xbmc.log("Skin Helper Simplecache --> %s" % msg, level=loglevel)

    @staticmethod
    def get_timestamp(date_time):
        '''Converts a datetime object to unix timestamp'''
        return int(time.mktime(date_time.timetuple()))

    @staticmethod
    def get_checksum(stringinput):
        '''get int checksum from string'''
        if not stringinput:
            return 0
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
