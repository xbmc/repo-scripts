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

from __builtin__ import True
import sqlite3

from clouddrive.common.ui.logger import Logger
from clouddrive.common.ui.utils import KodiUtils
from clouddrive.common.utils import Utils


class SimpleKeyValueDb(object):
    _base_path = None
    _name = None
    _monitor = None
    _abort = False

    def __init__(self, _base_path, name):
        self._base_path = _base_path
        self._name = name
        self._monitor = KodiUtils.get_system_monitor()
    
    def __del__(self):
        self._abort = True
        del self._monitor
    
    def _get_connection(self):
        if not KodiUtils.file_exists(self._base_path):
            KodiUtils.mkdirs(self._base_path)
        db = KodiUtils.translate_path("%s/%s.db" % (self._base_path, self._name,))
        con = sqlite3.connect(db, timeout=30, isolation_level=None)
        con.execute("pragma journal_mode=wal")
        rs = con.execute("select name from sqlite_master where type='table' AND name='store'")
        if not rs.fetchone():
            try:
                con.execute("create table store(key text unique, value text)")
            except Exception as ex:
                Logger.debug("error in db [%s] - %s" % (self._name, Utils.str(ex),))
        return con

    def get(self, key):
        row = self._read(key)
        if row:
            return eval(row[0])
        return
    
    def getall(self):
        d = {}
        rows = self._readall()
        for row in rows:
            d[row[0]] = eval(row[1])
        return d

    def set(self, key, value):
        self._insert(key, value)
    
    def setmany(self, key_value_list):
        for kv in key_value_list:
            kv[1] = repr(kv[1])
        self._execute_sql("insert or replace into store(key, value) values(?,?)", key_value_list)
        
    def remove(self, key):
        self._execute_sql("delete from store where key = ?", (key,))
    
    def checkpoint(self):
        row = self._execute_sql("PRAGMA wal_checkpoint(TRUNCATE)")
        Logger.debug("Db '%s' checkpoint: #d, #d, #d" % (self._name, row[0], row[1], row[2],))
        
    def _readall(self):
        return self._execute_sql("select key, value from store", fetchall=True)
    
    def _read(self, key):
        return self._execute_sql("select value from store where key = ?", (key,))
    
    def _insert(self, key, value):
        self._execute_sql("insert or replace into store(key, value) values(?,?)", (key, repr(value)))
        
    def _execute_sql(self, query, data=None, fetchall=False):
        result = None
        con = self._get_connection()
        with con:
            retries = 0
            error = None
            while retries < 15 and not self._abort:
                try:
                    if isinstance(data, list):
                        cur = con.executemany(query, data)
                    elif data:
                        cur = con.execute(query, data)
                    else:
                        cur = con.execute(query)
                    
                    if fetchall:
                        result = cur.fetchall()
                    else:
                        result = cur.fetchone()
                    break
                except sqlite3.OperationalError as error:
                    if "_database is locked" in error:
                        retries += 1
                        Logger.debug("db [%s] - query retry #d: [%s]: %s" % (self._name, retries, query, str(data),))
                        self._monitor.waitForAbort(0.3)
                    else:
                        break
                except Exception as error:
                    break
            if error:
                Logger.debug("db [%s] - Error executing query [%s]: %s" % (self._name, query, str(error),))
        con.close()
        return result

