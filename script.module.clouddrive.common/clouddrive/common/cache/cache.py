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

import datetime
import sqlite3
import time

from clouddrive.common.db import execute, from_text, to_text
from clouddrive.common.ui.logger import Logger
from clouddrive.common.ui.utils import KodiUtils


class Cache(object):
    _addonid = None
    _name = None
    _expiration_delta = None
    _monitor = None
    _abort = False

    def __init__(self, addonid, name, expiration):
        self._addonid = addonid
        self._name = name
        self._expiration_delta = expiration
        self._monitor = KodiUtils.get_system_monitor()

    def __del__(self):
        self._abort = True
        del self._monitor

    def _get_connection(self):
        profile_path = KodiUtils.get_addon_info("profile", self._addonid)
        if not KodiUtils.file_exists(profile_path):
            KodiUtils.mkdirs(profile_path)
        db = KodiUtils.translate_path("%s/cache_%s.db" % (profile_path, self._name,))
        con = sqlite3.connect(db, timeout=30, isolation_level=None)
        # Setup statements can meet a lock too: same retries as the queries.
        name = 'cache_' + self._name
        execute(name, con, self._monitor, lambda: self._abort, 'pragma journal_mode=wal')
        execute(name, con, self._monitor, lambda: self._abort, "create table if not exists cache(key text unique, value text, expiration integer)")
        return con

    def _get_datetime(self, ts):
        return int(time.mktime(ts.timetuple()))

    def _now(self):
        return self._get_datetime(datetime.datetime.now())

    def _expiration(self):
        # Whole seconds, rounded up: an entry never expires before its time.
        ts = datetime.datetime.now() + self._expiration_delta
        return self._get_datetime(ts) + (1 if ts.microsecond else 0)

    def get(self, key):
        row = self._execute_sql("select value, expiration from cache where key = ?", (key,))
        if row and row[1] > self._now():
            return from_text(row[0])
        return

    def set(self, key, value):
        expiration = self._expiration()
        self._execute_sql("insert or replace into cache(key, value, expiration) values(?,?,?)", (key, to_text(value), expiration,), purge=True)

    def setmany(self, key_value_list):
        expiration = self._expiration()
        rows = [(key, to_text(value), expiration) for key, value in key_value_list]
        self._execute_sql("insert or replace into cache(key, value, expiration) values(?,?,?)", rows, purge=True)

    def remove(self, key):
        self._execute_sql("delete from cache where key = ?", (key,))

    def clear(self):
        self._execute_sql("delete from cache")
        Logger.debug("Cache '%s' cleared" % self._name)
        self.checkpoint()

    def checkpoint(self):
        row = self._execute_sql("PRAGMA wal_checkpoint(TRUNCATE)")
        if row:
            Logger.debug("Db '%s' checkpoint: %s, %s, %s" % (self._name, row[0], row[1], row[2],))

    def _execute_sql(self, query, data=None, purge=False):
        con = self._get_connection()
        try:
            with con:
                # Expired rows are skipped when read, and deleted when something new is written.
                if purge:
                    execute('cache_' + self._name, con, self._monitor, lambda: self._abort, "delete from cache where expiration <= ?", (self._now(),))
                return execute('cache_' + self._name, con, self._monitor, lambda: self._abort, query, data)
        finally:
            con.close()
