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
import json
import os
from functools import reduce


class SimpleCache(object):
    '''simple stateless caching system for Kodi'''
    enable_mem_cache = True
    data_is_json = False
    global_checksum = None
    _exit = False
    _auto_clean_interval = datetime.timedelta(hours=4)
    _win = None
    _busy_tasks = []
    _database = None
    _db_path = None
    _log_prefix = "SimpleCache Internal -->"
    _mem_cache_prefix = "simplecache."
    _external_logger = None


    def __init__(self, db_path=None, log_prefix=None, mem_cache_prefix=None, external_logger=None):
        '''Initialize our caching class'''
        self._db_path = db_path
        if log_prefix:
            self._log_prefix = log_prefix
        if mem_cache_prefix:
            self._mem_cache_prefix = mem_cache_prefix if mem_cache_prefix.endswith('.') else mem_cache_prefix + "."
        self._external_logger = external_logger

        try:
            self._win = xbmcgui.Window(10000)
            self._monitor = xbmc.Monitor()
            
            try:
                test_key = "simplecache.init.test"
                test_val = "ok"
                self._win.setProperty(test_key, test_val)
                if self._win.getProperty(test_key) != test_val:
                    self._log_msg("Window(10000) property test failed — disabling memcache", xbmc.LOGWARNING)
                    self.enable_mem_cache = False
                else:
                    self._win.clearProperty(test_key)
            except Exception as e:
                self._log_msg(f"Window(10000) property access error: {e} — disabling memcache", xbmc.LOGERROR)
                self.enable_mem_cache = False
            
            if self._win is None or self._monitor is None:
                raise RuntimeError("Failed to get Window or Monitor")
            self.check_cleanup()
            self._log_msg("Initialized")
        except Exception as init_e:
            self._log_msg(f"CRITICAL Error during SimpleCache low-level init: {init_e}", xbmc.LOGFATAL)
            self._win = None
            self._monitor = None


    def _get_prop_key(self, suffix):
        return f"{self._mem_cache_prefix}{suffix}"


    def _log_msg(self, msg, loglevel=xbmc.LOGINFO):
        '''Helper to send a message to the kodi log via external or fallback logger.'''
        prefix_tag = getattr(self, '_log_prefix', None)
        if prefix_tag:
            formatted_msg = f"{prefix_tag} {str(msg)}"
        else:
            formatted_msg = str(msg)

        if self._external_logger:
            try:
                self._external_logger(formatted_msg, level=loglevel)
            except Exception as ext_log_err:
                fallback_prefix = getattr(self, '_log_prefix', 'SimpleCache Internal -->')
                try:
                    xbmc.log(f"{fallback_prefix} [External Logger Error: {ext_log_err}] {str(msg)}", level=xbmc.LOGERROR)
                except: pass
        else:
            fallback_prefix = getattr(self, '_log_prefix', 'SimpleCache Fallback -->')
            try:
                xbmc.log(f"{fallback_prefix} {str(msg)}", level=loglevel)
            except: pass


    def close(self):
        '''tell any tasks to stop immediately (as we can be called multithreaded) and cleanup objects'''
        self._exit = True
        monitor_exists = hasattr(self, '_monitor') and self._monitor is not None
        win_exists = hasattr(self, '_win') and self._win is not None
        while self._busy_tasks and (not monitor_exists or not self._monitor.abortRequested()):
            xbmc.sleep(25)
        if win_exists:
            try: del self._win
            except: pass
            self._win = None
        if monitor_exists:
            try: del self._monitor
            except: pass
            self._monitor = None
        self._log_msg("Closed")


    def __del__(self):
        '''make sure close is called'''
        if not self._exit:
            self.close()


    def get(self, endpoint, checksum="", json_data=True):
        '''
            get object from cache and return the results
            endpoint: the (unique) name of the cache object as reference
            checkum: optional argument to check if the checksum in the cacheobject matches the checkum provided
        '''
        self._log_msg(f"get(): endpoint={endpoint}", xbmc.LOGINFO)

        if not hasattr(self, '_win') or self._win is None:
            self._log_msg("Cache not properly initialized (Window missing). Cannot get.", xbmc.LOGERROR)
            return None

        checksum = self._get_checksum(checksum)
        cur_time = self._get_timestamp(datetime.datetime.now())
        result = None

        if self.enable_mem_cache and self._win is not None:
            result = self._get_mem_cache(endpoint, checksum, cur_time, json_data)
        else:
            if self.enable_mem_cache:
                self._log_msg("Memcache skipped: no current window dialog available.", xbmc.LOGINFO)

        if result is None:
            self._log_msg(f"Memcache miss or disabled for endpoint '{endpoint}', falling back to DB cache", xbmc.LOGINFO)
            result = self._get_db_cache(endpoint, checksum, cur_time, json_data)

        return result


    def set(self, endpoint, data, checksum="", expiration=datetime.timedelta(days=14), json_data=True):
        '''
            set data in cache
        '''
        self._log_msg(f"set(): endpoint={endpoint}", xbmc.LOGINFO)
        
        if not hasattr(self, '_win') or self._win is None:
            self._log_msg("Cache not properly initialized (Window missing). Cannot set.", xbmc.LOGERROR)
            return

        task_name = f"set.{endpoint}"
        self._busy_tasks.append(task_name)
        try:
            checksum_val = self._get_checksum(checksum)
            expires = self._get_timestamp(datetime.datetime.now() + expiration)

            if self.enable_mem_cache and not self._exit and self._win is not None:
                self._set_mem_cache(endpoint, checksum_val, expires, data, json_data)

            if self._db_path is not None and not self._exit:
                self._set_db_cache(endpoint, checksum_val, expires, data, json_data)
        finally:
            if task_name in self._busy_tasks:
                self._busy_tasks.remove(task_name)


    def delete(self, endpoint):
        '''
        Deletes a specific item from cache (memory and DB).
        '''
        if not hasattr(self, '_win') or self._win is None:
            self._log_msg("Cache not properly initialized (Window missing). Cannot delete.", xbmc.LOGERROR)
            return

        endpoint_str = str(endpoint)
        self._log_msg(f"Deleting cache for endpoint: '{endpoint_str}'", xbmc.LOGINFO)
        delete_task_name = f"delete.{endpoint_str}"
        self._busy_tasks.append(delete_task_name)

        try:
            if self.enable_mem_cache and hasattr(self, '_win') and self._win is not None:
                prop_key = self._get_prop_key(endpoint_str)
                try:
                    self._win.clearProperty(prop_key)
                    self._log_msg(f"Deleted '{prop_key}' from memory cache.", xbmc.LOGINFO)
                except Exception as e:
                    self._log_msg(f"Error deleting '{prop_key}' from memory cache: {e}", xbmc.LOGWARNING)

            if self._db_path is not None:
                query = 'DELETE FROM simplecache WHERE id = ?'
                try:
                    self._execute_sql(query, (endpoint_str,))
                    self._log_msg(f"Executed DB delete for '{endpoint_str}'.", xbmc.LOGINFO)
                except Exception as e:
                    self._log_msg(f"Error deleting '{endpoint_str}' from database cache: {e}", xbmc.LOGERROR)
        finally:
            if delete_task_name in self._busy_tasks:
                self._busy_tasks.remove(delete_task_name)


    def check_cleanup(self):
        '''check if cleanup is needed - public method, may be called by calling addon'''
        if not hasattr(self, '_win') or self._win is None:
            return

        prop_lastexec = self._get_prop_key("internal.clean.lastexecuted")
        try:
            cur_time = datetime.datetime.now()
            lastexecuted_repr = self._win.getProperty(prop_lastexec)
            needs_cleanup = False
            if not lastexecuted_repr:
                self._win.setProperty(prop_lastexec, repr(cur_time))
                needs_cleanup = True
            else:
                try:
                    if (eval(lastexecuted_repr) + self._auto_clean_interval) < cur_time:
                        needs_cleanup = True
                except Exception as e:
                    self._log_msg(f"Error evaluating last cleanup time '{lastexecuted_repr}': {e}. Resetting time.", xbmc.LOGWARNING)
                    self._win.setProperty(prop_lastexec, repr(cur_time))
                    needs_cleanup = True

            if needs_cleanup:
                self._do_cleanup()
        except Exception as e:
            self._log_msg(f"Error during cleanup check: {e}", xbmc.LOGERROR)


    def _get_mem_cache(self, endpoint, checksum, cur_time, json_data):
        '''
            get cache data from memory cache
            we use window properties because we need to be stateless
        '''
        result = None
        prop_key = self._get_prop_key(endpoint)
        cachedata_str = ""
        try:
            cachedata_str = self._win.getProperty(prop_key)
            if cachedata_str:
                try:
                    if json_data or self.data_is_json:
                        try:
                            cachedata = json.loads(cachedata_str)
                        except Exception as json_err:
                            self._log_msg(f"Corrupted JSON in memcache: {prop_key}, error: {json_err}. Clearing.", xbmc.LOGWARNING)
                            self._win.clearProperty(prop_key)
                            return None
                    else:
                        #cachedata = eval(cachedata_str)
                        self._log_msg("Non-JSON cache is disabled for safety. Skipping.", xbmc.LOGERROR)
                        return None

                    if isinstance(cachedata, (list, tuple)) and len(cachedata) >= 3:
                        if cachedata[0] > cur_time:
                            if not checksum or checksum == cachedata[2]:
                                result = cachedata[1]
                    else:
                        self._log_msg(f"Invalid structure in memcache: {prop_key}", xbmc.LOGWARNING)
                        self._win.clearProperty(prop_key)
                except Exception as e:
                    self._log_msg(f"Error parsing memcache for {prop_key}: {e}", xbmc.LOGWARNING)
                    try: self._win.clearProperty(prop_key)
                    except: pass
                    result = None
        except Exception as get_prop_e:
            self._log_msg(f"Error getting property {prop_key}: {get_prop_e}", xbmc.LOGERROR)
            result = None
        return result


    def _set_mem_cache(self, endpoint, checksum, expires, data, json_data):
        '''
            window property cache as alternative for memory cache
            usefull for (stateless) plugins
        '''
        prop_key = self._get_prop_key(endpoint)
        cachedata = (expires, data, checksum)
        try:
            if json_data or self.data_is_json:
                cachedata_str = json.dumps(cachedata)
            else:
                cachedata_str = repr(cachedata)
            self._win.setProperty(prop_key, cachedata_str)
        except Exception as e:
            self._log_msg(f"Error setting memcache for {prop_key}: {e}", xbmc.LOGWARNING)


    def _get_db_cache(self, endpoint, checksum, cur_time, json_data):
        '''get cache data from sqllite _database'''
        if self._db_path is None: return None
        result = None
        query = "SELECT expires, data, checksum FROM simplecache WHERE id = ?"
        try:
            cache_data_cursor = self._execute_sql(query, (endpoint,))
            if cache_data_cursor:
                cache_data = cache_data_cursor.fetchone()
                cache_data_cursor.close() 
                if cache_data and cache_data[0] > cur_time:
                    if not checksum or cache_data[2] == checksum:
                        try:
                            if json_data or self.data_is_json:
                                result = json.loads(cache_data[1])
                            else:
                                #result = eval(cache_data[1])
                                self._log_msg("Unsafe DB cache format (non-JSON) is disabled. Skipping.", xbmc.LOGWARNING)
                                return None

                            if self.enable_mem_cache and hasattr(self, '_win') and self._win is not None:
                                self._set_mem_cache(endpoint, cache_data[2], cache_data[0], result, json_data)
                        except Exception as e:
                            self._log_msg(f"Error parsing DB cache for {endpoint}: {e}. Deleting entry.", xbmc.LOGWARNING)
                            self.delete(endpoint)
                            result = None
        except Exception as e:
            self._log_msg(f"Error executing DB query in _get_db_cache for {endpoint}: {e}", xbmc.LOGWARNING)
            result = None
        return result


    def _set_db_cache(self, endpoint, checksum, expires, data, json_data):
        ''' store cache data in _database '''
        if self._db_path is None: return
        query = "INSERT OR REPLACE INTO simplecache( id, expires, data, checksum) VALUES (?, ?, ?, ?)"
        try:
            if json_data or self.data_is_json:
                data_str = json.dumps(data)
            else:
                data_str = repr(data)
            self._execute_sql(query, (endpoint, expires, data_str, checksum))
        except Exception as e:
            self._log_msg(f"Error setting DB cache for {endpoint}: {e}", xbmc.LOGERROR)


    def _do_cleanup(self):
        '''perform cleanup task'''
        if not hasattr(self, '_monitor') or self._monitor is None or \
           not hasattr(self, '_win') or self._win is None:
            return

        if self._exit or self._monitor.abortRequested():
            return

        db_available = self._db_path is not None
        prop_busy = self._get_prop_key("internal.clean.busy")
        prop_lastexec = self._get_prop_key("internal.clean.lastexecuted")
        cleanup_task_name = f"cleanup.{self._mem_cache_prefix}"

        try:
            if self._win.getProperty(prop_busy):
                self._log_msg("Cleanup already running (busy flag set).", xbmc.LOGINFO)
                return
        except Exception:
            pass

        self._busy_tasks.append(cleanup_task_name)
        self._log_msg("Running cleanup...")
        try:
            try:
                self._win.setProperty(prop_busy, "busy")
            except Exception as set_busy_e:
                self._log_msg(f"Error setting busy flag: {set_busy_e}", xbmc.LOGWARNING)

            cur_time = datetime.datetime.now()
            cur_timestamp = self._get_timestamp(cur_time)
            ids_found_in_db = []

            if db_available:
                query = "SELECT id, expires FROM simplecache"
                cursor = None
                try:
                    cursor = self._execute_sql(query)
                    if cursor:
                        db_results = cursor.fetchall()
                        cursor.close()
                        for cache_id, cache_expires in db_results:
                            ids_found_in_db.append(cache_id)
                            if self._exit or self._monitor.abortRequested():
                                return

                            if cache_expires < cur_timestamp:
                                delete_query = 'DELETE FROM simplecache WHERE id = ?'
                                try:
                                    self._execute_sql(delete_query, (cache_id,))
                                    self._log_msg(f"Deleted expired DB entry: {cache_id}", xbmc.LOGINFO)
                                except Exception as del_e:
                                    self._log_msg(f"Error deleting expired DB entry {cache_id}: {del_e}", xbmc.LOGWARNING)

                        try:
                            self._execute_sql("VACUUM")
                            self._log_msg("DB VACUUM executed.", xbmc.LOGINFO)
                        except Exception as vac_e:
                            self._log_msg(f"Error during DB VACUUM: {vac_e}", xbmc.LOGWARNING)
                except Exception as e:
                    self._log_msg(f"Error during DB cleanup phase: {e}", xbmc.LOGERROR)

            for cache_id in ids_found_in_db:
                if self._exit or self._monitor.abortRequested():
                    break
                mem_key = self._get_prop_key(cache_id)
                try:
                    self._win.clearProperty(mem_key)
                except:
                    pass

            try:
                self._win.setProperty(prop_lastexec, repr(cur_time))
            except Exception as set_last_e:
                self._log_msg(f"Error setting last executed flag: {set_last_e}", xbmc.LOGWARNING)

            self._log_msg("Auto cleanup done")

        finally:
            if cleanup_task_name in self._busy_tasks:
                self._busy_tasks.remove(cleanup_task_name)
            try:
                self._win.clearProperty(prop_busy)
            except:
                pass


    def _get_database(self):
        '''get reference to our sqllite _database - performs basic integrity check'''
        if self._db_path is None:
            return None

        dbfile = os.path.join(self._db_path, "simplecache.db")
        dir_path = os.path.dirname(dbfile)

        if not xbmcvfs.exists(dir_path):
            try:
                if not xbmcvfs.mkdirs(dir_path):
                    self._log_msg(f"Failed to create DB directory (mkdirs returned False): {dir_path}", xbmc.LOGERROR)
                    return None
            except Exception as mkdir_e:
                self._log_msg(f"Exception while creating DB directory '{dir_path}': {mkdir_e}", xbmc.LOGERROR)
                return None

        connection = None
        try:
            connection = sqlite3.connect(dbfile, timeout=30, isolation_level=None)
            connection.execute('SELECT id FROM simplecache LIMIT 1')
            return connection
        except Exception as error:
            self._log_msg(f"DB Check/Connection Error: {error}. Trying to recreate.", xbmc.LOGWARNING)
            if connection:
                try:
                    connection.close()
                    self._log_msg("Closed DB connection before delete/recreate.", xbmc.LOGINFO)
                except Exception as close_e:
                    self._log_msg(f"Error closing DB connection: {close_e}", xbmc.LOGWARNING)

            if xbmcvfs.exists(dbfile):
                try:
                    if not xbmcvfs.delete(dbfile):
                        self._log_msg(f"Failed to delete existing DB file (after closing connection): {dbfile}", xbmc.LOGERROR)
                    else:
                        self._log_msg(f"Deleted existing DB file: {dbfile}")
                except Exception as del_err:
                    self._log_msg(f"Error deleting DB file {dbfile}: {del_err}", xbmc.LOGERROR)

            new_connection = None
            try:
                new_connection = sqlite3.connect(dbfile, timeout=30, isolation_level=None)
                new_connection.execute(
                    """CREATE TABLE IF NOT EXISTS simplecache(
                    id TEXT UNIQUE, expires INTEGER, data TEXT, checksum INTEGER)""")
                self._log_msg("DB table recreated.")
                return new_connection
            except Exception as error_recreate:
                self._log_msg(f"Exception while recreating database: {error_recreate}", xbmc.LOGERROR)
                if new_connection:
                    try: new_connection.close()
                    except: pass
                return None


    def _execute_sql(self, query, data=None):
        '''little wrapper around execute and executemany to just retry a db command if db is locked'''
        if not hasattr(self, '_monitor') or self._monitor is None:
            return None
        if self._db_path is None:
            return None

        retries = 0
        max_retries = 10
        retry_delay = 0.1
        result = None
        error = None
        db_conn = None

        try:
            db_conn = self._get_database()
            if db_conn is None:
                return None

            with db_conn as _database:
                while retries < max_retries:
                    if self._exit or self._monitor.abortRequested():
                        return None
                    try:
                        if isinstance(data, list):
                            result = _database.executemany(query, data)
                        elif data is not None:
                            result = _database.execute(query, data)
                        else:
                            result = _database.execute(query)
                        return result
                    except sqlite3.OperationalError as op_error:
                        if "database is locked" in str(op_error).lower():
                            self._log_msg("retrying DB commit...", xbmc.LOGINFO)
                            retries += 1
                            if hasattr(self, '_monitor') and self._monitor is not None:
                                self._monitor.waitForAbort(retry_delay)
                            else:
                                time.sleep(retry_delay)
                        else:
                            self._log_msg(f"DB OperationalError: {op_error}", xbmc.LOGWARNING)
                            return None
                    except Exception as other_error:
                        self._log_msg(f"DB Exception: {other_error}", xbmc.LOGWARNING)
                        return None

            if retries == max_retries:
                self._log_msg(f"_database ERROR ! -- Max retries ({max_retries}) exceeded.", xbmc.LOGWARNING)

        except Exception as outer_error:
            self._log_msg(f"Outer DB Exception in _execute_sql: {outer_error}", xbmc.LOGERROR)
            return None

        return None


    @staticmethod
    def _get_timestamp(date_time):
        '''Converts a datetime object to unix timestamp'''
        try:
            return int(time.mktime(date_time.timetuple()))
        except (OverflowError, ValueError, TypeError):
            return int(time.time())


    def _get_checksum(self, stringinput):
        '''get int checksum from string'''
        if not stringinput and not self.global_checksum:
            return 0
        try:
            if self.global_checksum:
                calc_input = f"{self.global_checksum}-{stringinput}"
            else:
                calc_input = str(stringinput)

            if not calc_input: return 0

            return reduce(lambda x, y: x + y, map(ord, calc_input))
        except TypeError:
            self._log_msg(f"Checksum TypeError for input: {stringinput}", xbmc.LOGWARNING)
            return 0


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
            cache_instance = getattr(method_class, 'cache', None)
            if cache_instance is None:
                return func(*args, **kwargs)

            method_class_name = method_class.__class__.__name__
            cache_str = f"{method_class_name}.{func.__name__}"
            for item in args[1:]:
                try:
                    cache_str += f".{item}"
                except:
                    cache_str += f".{repr(item)}"
            cache_str = cache_str.lower()

            ignore_cache_flag = kwargs.get("ignore_cache", False)
            global_cache_ignore = getattr(method_class, 'ignore_cache', False)

            cachedata = None
            if not ignore_cache_flag and not global_cache_ignore:
                try:
                    cachedata = cache_instance.get(cache_str)
                except Exception:
                    cachedata = None

            if cachedata is not None:
                return cachedata
            else:
                result = func(*args, **kwargs)
                try:
                    cache_instance.set(cache_str, result, expiration=datetime.timedelta(days=cache_days))
                except Exception:
                    pass
                return result
        return decorated
    return decorator
