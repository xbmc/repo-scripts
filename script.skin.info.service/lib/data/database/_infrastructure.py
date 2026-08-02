"""Database infrastructure for connections, migrations, and schema.

Core infrastructure shared across all database modules.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
import zlib
import xbmc
import xbmcvfs
from contextlib import contextmanager
from typing import Any, Generator
from lib.kodi.client import log

DB_VERSION = 4


def compress_data(data: Any) -> bytes:
    """Compress a JSON-serializable value to a zlib blob."""
    json_str = json.dumps(data, separators=(',', ':'))
    return zlib.compress(json_str.encode('utf-8'), level=6)


def decompress_data(blob: bytes) -> Any:
    """Inverse of `compress_data`."""
    return json.loads(zlib.decompress(blob).decode('utf-8'))


# Kodi bundled SQLite has a parameter limit of 999; 900 leaves headroom
SQL_PARAM_CHUNK_SIZE = 900


def sql_placeholders(count: int) -> str:
    """Build a comma-separated placeholder string for SQL IN-lists, e.g. `'?,?,?'`.

    Raises for lists too long to bind in one statement, rather than leaving it to fail on a
    user's library; feed caller-sized lists through `chunked_in_query`/`chunked_in_modify`.
    """
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
    """Execute an IN-list query in chunks, yielding rows.

    `sql_template` must contain `{placeholders}`.

    Use for SELECT/DELETE patterns where the IN-list size could exceed SQLite's parameter limit.
    `fixed_params` come before the chunk; the chunk values are appended for each batch.
    """
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
    """Execute a chunked DELETE/UPDATE with an IN list. Returns total `rowcount` across chunks."""
    total = 0
    for start in range(0, len(values), chunk_size):
        chunk = values[start:start + chunk_size]
        sql = sql_template.format(placeholders=sql_placeholders(len(chunk)))
        cursor.execute(sql, fixed_params + list(chunk))
        total += cursor.rowcount
    return total
_DB_BASE = 'special://profile/addon_data/script.skin.info.service/skininfo'
DB_PATH = xbmcvfs.translatePath(f'{_DB_BASE}_v{DB_VERSION}.db')

_OLD_DB_PATHS = [
    xbmcvfs.translatePath(f'{_DB_BASE}_v{v}.db')
    for v in range(1, DB_VERSION)
]


def generate_guid() -> str:
    return uuid.uuid4().hex


def _ensure_addon_data_folder() -> None:
    folder = xbmcvfs.translatePath('special://profile/addon_data/script.skin.info.service/')
    if not xbmcvfs.exists(folder):
        xbmcvfs.mkdirs(folder)


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Open a SQLite connection with Row factory and per-connection pragmas."""
    _ensure_addon_data_folder()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA busy_timeout = 5000')
    conn.execute('PRAGMA synchronous = NORMAL')
    return conn


@contextmanager
def get_db(db_path: str = DB_PATH) -> Generator[sqlite3.Cursor, None, None]:
    """Context manager yielding a cursor; auto-commits on success, rolls back on exception."""
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


def _create_base_schema(cursor: sqlite3.Cursor) -> None:
    """Create all tables and indexes for the unified database."""
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS art_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            media_type TEXT NOT NULL,
            dbid INTEGER NOT NULL,
            title TEXT,
            year TEXT,
            status TEXT DEFAULT 'pending',
            priority INTEGER DEFAULT 5,
            date_added TEXT DEFAULT CURRENT_TIMESTAMP,
            date_processed TEXT,
            scope TEXT DEFAULT '',
            scan_session_id INTEGER,
            guid TEXT,
            FOREIGN KEY(scan_session_id) REFERENCES scan_sessions(id) ON DELETE SET NULL,
            UNIQUE(media_type, dbid)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS art_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            queue_id INTEGER NOT NULL,
            art_type TEXT NOT NULL,
            selected_url TEXT,
            auto_applied INTEGER DEFAULT 0,
            review_mode TEXT DEFAULT 'missing',
            requires_manual INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            scan_session_id INTEGER,
            date_processed TEXT,
            FOREIGN KEY(queue_id) REFERENCES art_queue(id) ON DELETE CASCADE,
            UNIQUE(queue_id, art_type)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scan_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_type TEXT,
            status TEXT DEFAULT 'in_progress',
            started TEXT DEFAULT CURRENT_TIMESTAMP,
            last_activity TEXT,
            completed TEXT,
            stats TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS session_media_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            media_type TEXT NOT NULL,
            FOREIGN KEY(session_id) REFERENCES scan_sessions(id) ON DELETE CASCADE,
            UNIQUE(session_id, media_type)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS session_art_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            art_type TEXT NOT NULL,
            FOREIGN KEY(session_id) REFERENCES scan_sessions(id) ON DELETE CASCADE,
            UNIQUE(session_id, art_type)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS artwork_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            media_type TEXT NOT NULL,
            media_id TEXT NOT NULL,
            source TEXT NOT NULL,
            art_type TEXT NOT NULL,
            data TEXT NOT NULL,
            release_date TEXT,
            cached_at TEXT DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT NOT NULL,
            UNIQUE(media_type, media_id, source, art_type)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS metadata_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            media_type TEXT NOT NULL,
            tmdb_id TEXT NOT NULL,
            data BLOB NOT NULL,
            release_date TEXT,
            cached_at TEXT DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT NOT NULL,
            UNIQUE(media_type, tmdb_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS person_cache (
            person_id INTEGER PRIMARY KEY,
            data BLOB NOT NULL,
            cached_at INTEGER NOT NULL,
            expires_at INTEGER NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS season_metadata_cache (
            tmdb_id TEXT NOT NULL,
            season_number INTEGER NOT NULL,
            data BLOB NOT NULL,
            cached_at TEXT DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT NOT NULL,
            PRIMARY KEY (tmdb_id, season_number)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tmdb_genre_cache (
            tmdb_type TEXT PRIMARY KEY,
            data BLOB NOT NULL,
            cached_at TEXT DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS operation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            stats TEXT NOT NULL,
            completed INTEGER DEFAULT 1,
            scope TEXT
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_queue_status ON art_queue(status, priority)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_queue_media_type ON art_queue(media_type)')
    cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_queue_guid ON art_queue(guid)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_queue_scope ON art_queue(scope)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_queue_session ON art_queue(scan_session_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_art_items_queue ON art_items(queue_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_art_items_status ON art_items(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_art_items_review_mode ON art_items(review_mode)')
    cursor.execute(
        'CREATE INDEX IF NOT EXISTS idx_art_items_queue_status_review '
        'ON art_items(queue_id, status, review_mode)'
    )
    cursor.execute(
        'CREATE INDEX IF NOT EXISTS idx_person_cache_expires ON person_cache(expires_at)'
    )
    cursor.execute(
        'CREATE INDEX IF NOT EXISTS idx_sessions_scan_type_activity '
        'ON scan_sessions(scan_type, last_activity DESC)'
    )
    cursor.execute(
        'CREATE INDEX IF NOT EXISTS idx_session_media_types_session '
        'ON session_media_types(session_id)'
    )
    cursor.execute(
        'CREATE INDEX IF NOT EXISTS idx_session_media_types_lookup '
        'ON session_media_types(session_id, media_type)'
    )
    cursor.execute(
        'CREATE INDEX IF NOT EXISTS idx_session_art_types_session '
        'ON session_art_types(session_id)'
    )
    cursor.execute(
        'CREATE INDEX IF NOT EXISTS idx_session_art_types_lookup '
        'ON session_art_types(session_id, art_type)'
    )
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cache_expires ON artwork_cache(expires_at)')
    cursor.execute(
        'CREATE INDEX IF NOT EXISTS idx_season_metadata_cache_expires '
        'ON season_metadata_cache(expires_at)'
    )
    cursor.execute(
        'CREATE INDEX IF NOT EXISTS idx_tmdb_genre_cache_expires ON tmdb_genre_cache(expires_at)'
    )
    cursor.execute(
        'CREATE INDEX IF NOT EXISTS idx_operation_history_lookup '
        'ON operation_history(operation, timestamp DESC)'
    )

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS provider_cache (
            provider TEXT NOT NULL,
            media_id TEXT NOT NULL,
            data BLOB NOT NULL,
            release_date TEXT,
            cached_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (provider, media_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS id_corrections (
            imdb_id TEXT PRIMARY KEY,
            tmdb_id INTEGER NOT NULL,
            media_type TEXT NOT NULL,
            cached_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS id_mappings (
            tmdb_id TEXT NOT NULL,
            media_type TEXT NOT NULL,
            imdb_id TEXT,
            tvdb_id TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (tmdb_id, media_type)
        )
    ''')

    cursor.execute(
        'CREATE INDEX IF NOT EXISTS idx_id_mappings_imdb '
        'ON id_mappings(imdb_id) WHERE imdb_id IS NOT NULL'
    )
    cursor.execute(
        'CREATE INDEX IF NOT EXISTS idx_id_mappings_tvdb '
        'ON id_mappings(tvdb_id) WHERE tvdb_id IS NOT NULL'
    )

    cursor.execute(
        'CREATE INDEX IF NOT EXISTS idx_provider_cache_expires ON provider_cache(cached_at)'
    )

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS slideshow_pool (
            dbid INTEGER NOT NULL,
            media_type TEXT NOT NULL,
            title TEXT,
            fanart TEXT NOT NULL,
            description TEXT,
            year INTEGER,
            season INTEGER,
            episode INTEGER,
            last_synced INTEGER,
            PRIMARY KEY (media_type, dbid)
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_slideshow_media ON slideshow_pool(media_type)')
    cursor.execute(
        'CREATE INDEX IF NOT EXISTS idx_slideshow_fanart '
        'ON slideshow_pool(fanart) WHERE fanart IS NOT NULL'
    )

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gif_cache (
            path TEXT PRIMARY KEY,
            mtime REAL NOT NULL,
            scanned_at TEXT NOT NULL
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_gif_cache_scanned ON gif_cache(scanned_at)')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS imdb_ratings (
            imdb_id TEXT PRIMARY KEY,
            rating REAL NOT NULL,
            votes INTEGER NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS imdb_episodes (
            parent_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            episode INTEGER NOT NULL,
            episode_id TEXT NOT NULL,
            PRIMARY KEY (parent_id, season, episode)
        )
    ''')

    cursor.execute(
        'CREATE INDEX IF NOT EXISTS idx_imdb_episodes_parent ON imdb_episodes(parent_id)'
    )

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS imdb_meta (
            dataset TEXT PRIMARY KEY,
            last_modified TEXT,
            downloaded_at TEXT,
            entry_count INTEGER DEFAULT 0,
            library_episode_count INTEGER DEFAULT 0
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS imdb_update_progress (
            media_type TEXT PRIMARY KEY,
            dataset_date TEXT NOT NULL,
            processed_ids TEXT NOT NULL,
            total_items INTEGER NOT NULL,
            started_at TEXT NOT NULL,
            last_updated TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ratings_synced (
            media_type TEXT NOT NULL,
            dbid INTEGER NOT NULL,
            source TEXT NOT NULL,
            external_id TEXT,
            rating REAL NOT NULL,
            votes INTEGER NOT NULL,
            synced_at TEXT NOT NULL,
            PRIMARY KEY (media_type, dbid, source)
        )
    ''')
    cursor.execute(
        'CREATE INDEX IF NOT EXISTS idx_ratings_synced_lookup ON ratings_synced(media_type, dbid)'
    )
    cursor.execute(
        'CREATE INDEX IF NOT EXISTS idx_ratings_synced_external '
        'ON ratings_synced(source, external_id)'
    )

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS online_properties_cache (
            item_key TEXT PRIMARY KEY,
            data BLOB NOT NULL,
            cached_at TEXT DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT NOT NULL
        )
    ''')
    cursor.execute(
        'CREATE INDEX IF NOT EXISTS idx_online_cache_expires ON online_properties_cache(expires_at)'
    )

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mb_id_mappings (
            old_id TEXT PRIMARY KEY,
            canonical_id TEXT NOT NULL,
            cached_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_mb_id_canonical ON mb_id_mappings(canonical_id)')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tv_schedule (
            tmdb_id TEXT NOT NULL,
            tvshowid INTEGER NOT NULL,
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT '',
            next_episode_air_date TEXT,
            next_episode_title TEXT,
            next_episode_season INTEGER,
            next_episode_number INTEGER,
            last_episode_air_date TEXT,
            last_episode_title TEXT,
            last_episode_season INTEGER,
            last_episode_number INTEGER,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (tmdb_id)
        )
    ''')
    cursor.execute(
        'CREATE INDEX IF NOT EXISTS idx_tv_schedule_air_date ON tv_schedule(next_episode_air_date)'
    )
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tv_schedule_status ON tv_schedule(status)')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dbid_registry (
            media_type TEXT NOT NULL,
            dbid INTEGER NOT NULL,
            title TEXT NOT NULL,
            content_id TEXT,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (media_type, dbid)
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_dbid_registry_type ON dbid_registry(media_type)')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tvshow_runtime_cache (
            tvshowid INTEGER NOT NULL,
            season INTEGER NOT NULL DEFAULT 0,
            total_runtime INTEGER NOT NULL,
            avg_episode_runtime INTEGER NOT NULL DEFAULT 0,
            episode_count INTEGER NOT NULL,
            synced_at TEXT NOT NULL,
            PRIMARY KEY (tvshowid, season)
        )
    ''')

    # These lookup indexes duplicate the table's UNIQUE / PRIMARY KEY auto-index; drop the
    # redundant copies so existing DBs stop paying the extra write on every cache insert.
    cursor.execute('DROP INDEX IF EXISTS idx_cache_lookup')
    cursor.execute('DROP INDEX IF EXISTS idx_metadata_cache_lookup')
    cursor.execute('DROP INDEX IF EXISTS idx_provider_cache_lookup')


def _cleanup_old_databases() -> None:
    """Delete old database versions if they exist."""
    for path in _OLD_DB_PATHS:
        if xbmcvfs.exists(path):
            try:
                xbmcvfs.delete(path)
                log("Database", f"Deleted old database: {path}", xbmc.LOGINFO)
            except Exception as e:
                log("Database", f"Failed to delete old database: {e}", xbmc.LOGWARNING)


def init_database() -> None:
    """Create all tables at DB_PATH; deletes any older-version DB files first."""
    _cleanup_old_databases()

    conn = get_connection(DB_PATH)
    cursor = conn.cursor()

    try:
        # WAL is persistent at the DB level; apply once during init.
        cursor.execute('PRAGMA journal_mode = WAL')
        _create_base_schema(cursor)
        conn.commit()

    except Exception as e:
        conn.rollback()
        log("Database", f"Initialization failed: {str(e)}", xbmc.LOGERROR)
        raise
    finally:
        conn.close()

