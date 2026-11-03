"""Connection handling and database creation, shared by every database module."""
from __future__ import annotations

import json
import sqlite3
import threading
import zlib
import xbmc
import xbmcvfs
from contextlib import contextmanager
from typing import Any, Generator, Final
from lib.data.database.schema import apply_cache_resets, create_schema
from lib.kodi.client import log

DB_VERSION: Final = 5


def compress_data(data: Any) -> bytes:
    """Compress a JSON-serializable value to a zlib blob."""
    json_str = json.dumps(data, separators=(',', ':'))
    return zlib.compress(json_str.encode('utf-8'), level=6)


def decompress_data(blob: bytes) -> Any:
    """Inverse of `compress_data`."""
    return json.loads(zlib.decompress(blob).decode('utf-8'))


def as_int(value: Any) -> Any:
    """Value as an int for an INTEGER key column, or None when a scraper handed us junk."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# Kodi bundled SQLite has a parameter limit of 999; 900 leaves headroom
SQL_PARAM_CHUNK_SIZE: Final = 900


def sql_placeholders(count: int) -> str:
    """Build a `?,?,?` placeholder list for an IN clause; raises past the chunk size."""
    if count > SQL_PARAM_CHUNK_SIZE:
        raise ValueError(
            f"{count} placeholders exceeds the {SQL_PARAM_CHUNK_SIZE} parameter budget - "
            "use chunked_in_query/chunked_in_modify for lists sized by the caller")
    return ','.join('?' * count)


def chunked_in_query(
    cursor: sqlite3.Cursor,
    sql_template: str,
    fixed_params: list,
    values: list,
    chunk_size: int = SQL_PARAM_CHUNK_SIZE,
):
    """Execute an IN-list query in {placeholders} chunks under SQLite's parameter limit."""
    for start in range(0, len(values), chunk_size):
        chunk = values[start:start + chunk_size]
        sql = sql_template.format(placeholders=sql_placeholders(len(chunk)))
        cursor.execute(sql, fixed_params + list(chunk))
        for row in cursor.fetchall():
            yield row


def chunked_in_modify(
    cursor: sqlite3.Cursor,
    sql_template: str,
    fixed_params: list,
    values: list,
    chunk_size: int = SQL_PARAM_CHUNK_SIZE,
) -> int:
    """Execute an IN-list DELETE or UPDATE in {placeholders} chunks; returns the total rowcount."""
    total = 0
    for start in range(0, len(values), chunk_size):
        chunk = values[start:start + chunk_size]
        sql = sql_template.format(placeholders=sql_placeholders(len(chunk)))
        cursor.execute(sql, fixed_params + list(chunk))
        total += cursor.rowcount
    return total


_DB_BASE: Final = 'special://profile/addon_data/script.skin.info.service/skininfo'
DB_PATH = xbmcvfs.translatePath(f'{_DB_BASE}_v{DB_VERSION}.db')

# leftover pre-v5 music cache
_MUSIC_DB_PATH = xbmcvfs.translatePath(
    'special://profile/addon_data/script.skin.info.service/music_metadata.db')

_OLD_DB_PATHS = [
    xbmcvfs.translatePath(f'{_DB_BASE}_v{v}.db')
    for v in range(1, DB_VERSION)
]


def _ensure_addon_data_folder() -> None:
    """Create the addon data folder if it is missing."""
    folder = xbmcvfs.translatePath('special://profile/addon_data/script.skin.info.service/')
    if not xbmcvfs.exists(folder):
        xbmcvfs.mkdirs(folder)


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Open a SQLite connection with Row factory and per-connection pragmas."""
    _ensure_addon_data_folder()
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA busy_timeout = 5000')
    conn.execute('PRAGMA synchronous = NORMAL')
    conn.execute('PRAGMA cache_size = -16000')
    conn.execute('PRAGMA journal_size_limit = 16777216')
    return conn


_shared: dict = {}
_shared_lock = threading.Lock()
_reentry = threading.local()


@contextmanager
def _own_db(db_path: str) -> Generator[sqlite3.Cursor, None, None]:
    """Cursor on a private connection, closed on exit."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception as rollback_err:
            log("Database", f"Rollback failed: {rollback_err}", xbmc.LOGWARNING)
        raise
    finally:
        conn.close()


@contextmanager
def get_bulk_db(db_path: str = DB_PATH) -> Generator[sqlite3.Cursor, None, None]:
    """Cursor on a private connection, so a long scan never sits in front of a poll tick."""
    with _own_db(db_path) as cursor:
        yield cursor


@contextmanager
def get_db(db_path: str = DB_PATH) -> Generator[sqlite3.Cursor, None, None]:
    """Cursor on the process-wide connection; commits on success, rolls back on exception."""
    if getattr(_reentry, 'held', False):
        # re-entry would deadlock on the shared connection
        log("Database", "Nested get_db; using a private connection", xbmc.LOGERROR)
        with _own_db(db_path) as cursor:
            yield cursor
        return

    with _shared_lock:
        conn = _shared.get(db_path)
        if conn is None:
            conn = get_connection(db_path)
            _shared[db_path] = conn
        cursor = conn.cursor()
        _reentry.held = True
        try:
            yield cursor
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception as rollback_err:
                log("Database", f"Rollback failed: {rollback_err}", xbmc.LOGWARNING)
            raise
        finally:
            _reentry.held = False
            cursor.close()


def close_connections() -> None:
    """Close the shared connections; call once as the service stops."""
    with _shared_lock:
        for path, conn in list(_shared.items()):
            try:
                conn.close()
            except Exception as e:
                log("Database", f"Failed to close {path}: {e}", xbmc.LOGWARNING)
            _shared.pop(path, None)


def _cleanup_old_databases() -> None:
    """Delete old database versions and the pre-v5 music cache, with their WAL files."""
    for base in _OLD_DB_PATHS + [_MUSIC_DB_PATH]:
        for path in (base, base + '-wal', base + '-shm'):
            if not xbmcvfs.exists(path):
                continue
            try:
                xbmcvfs.delete(path)
                log("Database", f"Deleted old database: {path}", xbmc.LOGINFO)
            except Exception as e:
                log("Database", f"Failed to delete old database: {e}", xbmc.LOGWARNING)


def init_database() -> None:
    """Create every table and apply pending cache resets; a version bump replaces the old file."""
    _cleanup_old_databases()

    conn = get_connection(DB_PATH)
    cursor = conn.cursor()

    try:
        # WAL mode persists in the database file
        cursor.execute('PRAGMA journal_mode = WAL')
        create_schema(cursor)
        conn.commit()
        try:
            apply_cache_resets(conn)
        except sqlite3.Error as e:
            log("Database", f"Cache resets deferred: {e}", xbmc.LOGWARNING)

    except Exception as e:
        conn.rollback()
        log("Database", f"Initialization failed: {str(e)}", xbmc.LOGERROR)
        raise
    finally:
        conn.close()
