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

import ast
import json
import sqlite3

from clouddrive.common.ui.logger import Logger
from clouddrive.common.ui.utils import KodiUtils


# Values are stored as JSON after this prefix. Earlier versions stored Python repr() text, which literal_eval reads
# without running code. The prefix tells them apart without a failing json.loads: in Kodi, json's C decoder can raise
# an exception class left over from an earlier add-on run, which fails with "NameError: ValueError".
_JSON_PREFIX = 'json:'


def to_text(value):
    return _JSON_PREFIX + json.dumps(value)


def from_text(text):
    if text.startswith(_JSON_PREFIX):
        return json.loads(text[len(_JSON_PREFIX):])
    return ast.literal_eval(text)


def execute(name, con, monitor, is_aborted, query, data=None, fetchall=False):
    # Runs a query, retrying while another process holds the lock. Errors are logged (without the data, which can
    # hold tokens) and give None.
    for attempt in range(15):
        try:
            if isinstance(data, list):
                cur = con.executemany(query, data)
            elif data:
                cur = con.execute(query, data)
            else:
                cur = con.execute(query)
            return cur.fetchall() if fetchall else cur.fetchone()
        except sqlite3.OperationalError as ex:
            if 'database is locked' not in str(ex) or is_aborted() or monitor.abortRequested():
                Logger.debug('db [%s] - error executing query [%s]: %s' % (name, query, ex))
                return None
            Logger.debug('db [%s] - database locked, retry %d: [%s]' % (name, attempt + 1, query))
            # Kodi is shutting down: stop retrying.
            if monitor.waitForAbort(0.3):
                return None
        except Exception as ex:
            Logger.debug('db [%s] - error executing query [%s]: %s' % (name, query, ex))
            return None
    Logger.debug('db [%s] - database still locked, giving up: [%s]' % (name, query))
    return None


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
        # Setup statements can meet a lock too: same retries as the queries.
        execute(self._name, con, self._monitor, lambda: self._abort, "pragma journal_mode=wal")
        execute(self._name, con, self._monitor, lambda: self._abort, "create table if not exists store(key text unique, value text)")
        return con

    def get(self, key):
        row = self._execute_sql("select value from store where key = ?", (key,))
        if row:
            return from_text(row[0])
        return

    def getall(self):
        rows = self._execute_sql("select key, value from store", fetchall=True) or []
        return dict((key, from_text(value)) for key, value in rows)

    def set(self, key, value):
        self._execute_sql("insert or replace into store(key, value) values(?,?)", (key, to_text(value)))

    def setmany(self, key_value_list):
        self._execute_sql("insert or replace into store(key, value) values(?,?)", [(key, to_text(value)) for key, value in key_value_list])

    def remove(self, key):
        self._execute_sql("delete from store where key = ?", (key,))

    def checkpoint(self):
        row = self._execute_sql("PRAGMA wal_checkpoint(TRUNCATE)")
        if row:
            Logger.debug("Db '%s' checkpoint: %s, %s, %s" % (self._name, row[0], row[1], row[2],))

    def _execute_sql(self, query, data=None, fetchall=False):
        con = self._get_connection()
        try:
            with con:
                return execute(self._name, con, self._monitor, lambda: self._abort, query, data, fetchall)
        finally:
            con.close()
