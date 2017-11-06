#-------------------------------------------------------------------------------
# Copyright (C) 2017 Carlos Guzman (cguZZman) carlosguzmang@protonmail.com
# 
# This file is part of Cloud Drive Common Module for Kodi
# 
# Cloud Drive Common Module for Kodi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# Cloud Drive Common Module for Kodi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# This file incorporates work covered by the following copyright:  
#    Apache License Version 2.0, January 2004. http://www.apache.org/licenses/
#    Author: Marcel van der Veldt (marcelveldt) - https://github.com/marcelveldt/script.module.simplecache
#    Changes:
#      - Memcache removed
#      - Cleanup done in a single query call to avoid performance issue
#      - Adapted for the use of Cloud Drive Common Module for Kodi
#-------------------------------------------------------------------------------
#!/usr/bin/python
# -*- coding: utf-8 -*-
'''provides a simple stateless caching system for Kodi addons and plugins'''

import datetime
from functools import reduce
import sqlite3
import time

from clouddrive.common.ui.utils import KodiUtils
import xbmc
import xbmcvfs


ADDONID = "script.module.clouddrive.common"

class SimpleCache(object):
    '''simple stateless caching system for Kodi'''
    global_checksum = None
    _exit = False
    _auto_clean_interval = datetime.timedelta(minutes=1)
    _win = None
    _busy_tasks = []
    _database = None

    def __init__(self):
        '''Initialize our caching class'''
        self._win = KodiUtils.get_window(10000)
        self._monitor = KodiUtils.get_system_monitor()
        self.check_cleanup()

    def close(self):
        '''tell any tasks to stop immediately (as we can be called multithreaded) and cleanup objects'''
        self._exit = True
        # wait for all tasks to complete
        while self._busy_tasks:
            xbmc.sleep(25)
        del self._win
        del self._monitor

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
        return self._get_db_cache(endpoint, checksum, cur_time)

    def set(self, endpoint, data, checksum="", expiration=datetime.timedelta(days=30)):
        '''
            set data in cache
        '''
        task_name = "set.%s" % endpoint
        self._busy_tasks.append(task_name)
        checksum = self._get_checksum(checksum)
        expires = self._get_timestamp(datetime.datetime.now() + expiration)

        # db cache
        if not self._exit:
            self._set_db_cache(endpoint, checksum, expires, data)

        # remove this task from list
        self._busy_tasks.remove(task_name)

    def check_cleanup(self):
        '''check if cleanup is needed - public method, may be called by calling addon'''
        cur_time = datetime.datetime.now()
        lastexecuted = self._win.getProperty(ADDONID + "simplecache.clean.lastexecuted")
        if not lastexecuted:
            self._win.setProperty(ADDONID + "simplecache.clean.lastexecuted", repr(cur_time))
        elif (eval(lastexecuted) + self._auto_clean_interval) < cur_time:
            # cleanup needed...
            self._do_cleanup()

    def _get_db_cache(self, endpoint, checksum, cur_time):
        '''get cache data from sqllite _database'''
        result = None
        query = "SELECT expires, data, checksum FROM simplecache WHERE id = ?"
        cache_data = self._execute_sql(query, (endpoint,))
        cache_data = cache_data.fetchone() if cache_data else None
        if cache_data:
            if cache_data[0] > cur_time:
                if not checksum or cache_data[2] == checksum:
                    result = eval(cache_data[1])
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
        if self._win.getProperty(ADDONID + "simplecachecleanbusy"):
            return
        self._win.setProperty(ADDONID + "simplecachecleanbusy", "busy")

        query = "delete FROM simplecache where expires < ?"
        self._execute_sql(query, (cur_timestamp,))
        # compact db
        self._execute_sql("VACUUM")

        # remove task from list
        self._busy_tasks.remove(__name__)
        self._win.setProperty(ADDONID + "simplecache.clean.lastexecuted", repr(cur_time))
        self._win.clearProperty(ADDONID + "simplecachecleanbusy")
        self._log_msg("Auto cleanup done")

    def _get_database(self):
        '''get reference to our sqllite _database - performs basic integrity check'''
        dbpath = KodiUtils.get_addon_info('profile', ADDONID)
        dbfile = xbmc.translatePath("%s/simplecache.db" % dbpath).decode('utf-8')
        if not xbmcvfs.exists(dbpath):
            xbmcvfs.mkdirs(dbpath)
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
                self._log_msg("Exception while initializing _database: %s" % str(error), KodiUtils.LOGWARNING)
                self.close()
                return None

    def _execute_sql(self, query, data=None):
        '''little wrapper around execute and executemany to just retry a db command if db is locked'''
        retries = 0
        result = None
        error = None
        # always use new db object because we need to be sure that data is available for other simplecache instances
        with self._get_database() as _database:
            while not retries == 10:
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
            self._log_msg("_database ERROR ! -- %s" % str(error), KodiUtils.LOGWARNING)
        return None

    @staticmethod
    def _log_msg(msg, loglevel=KodiUtils.LOGNOTICE):
        '''helper to send a message to the kodi log'''
        if isinstance(msg, unicode):
            msg = msg.encode('utf-8')
        KodiUtils.log(msg, loglevel)

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