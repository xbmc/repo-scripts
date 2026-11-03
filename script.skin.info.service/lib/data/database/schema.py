"""Every table and index in the add-on's database."""
from __future__ import annotations

import sqlite3
import time
from typing import List, Final


SCHEMA_VERSION: Final = 2

_KODI_SIDE: List[str] = [
    '''
    CREATE TABLE IF NOT EXISTS library_item (
        media_type   TEXT    NOT NULL,
        dbid         INTEGER NOT NULL,
        title        TEXT    NOT NULL,
        imdb_id      TEXT,
        tmdb_id      INTEGER,
        tvdb_id      INTEGER,
        mbid         TEXT,
        parent_dbid  INTEGER,
        season       INTEGER,
        episode      INTEGER,
        content_key  TEXT    NOT NULL,
        updated_at   INTEGER NOT NULL,
        PRIMARY KEY (media_type, dbid)
    ) WITHOUT ROWID
    ''',
    'CREATE INDEX IF NOT EXISTS li_tmdb ON library_item(media_type, tmdb_id) '
    'WHERE tmdb_id IS NOT NULL',
    'CREATE INDEX IF NOT EXISTS li_imdb ON library_item(media_type, imdb_id) '
    'WHERE imdb_id IS NOT NULL',
    'CREATE INDEX IF NOT EXISTS li_parent ON library_item(media_type, parent_dbid) '
    'WHERE parent_dbid IS NOT NULL',
    '''
    CREATE TABLE IF NOT EXISTS imdb_sync (
        media_type  TEXT    NOT NULL,
        dbid        INTEGER NOT NULL,
        imdb_id     TEXT    NOT NULL,
        rating      REAL    NOT NULL,
        votes       INTEGER NOT NULL,
        synced_at   INTEGER NOT NULL,
        PRIMARY KEY (media_type, dbid)
    ) WITHOUT ROWID
    ''',
    'CREATE INDEX IF NOT EXISTS imdb_sync_id ON imdb_sync(imdb_id)',
    '''
    CREATE TABLE IF NOT EXISTS slideshow_pool (
        media_type  TEXT    NOT NULL,
        dbid        INTEGER NOT NULL,
        title       TEXT    NOT NULL DEFAULT '',
        fanart      TEXT    NOT NULL,
        plot        TEXT,
        year        INTEGER,
        artist      TEXT,
        clearlogo   TEXT,
        PRIMARY KEY (media_type, dbid)
    ) WITHOUT ROWID
    ''',
    '''
    CREATE TABLE IF NOT EXISTS tvshow_runtime (
        tvshowid  INTEGER NOT NULL,
        season    INTEGER NOT NULL DEFAULT -1,
        total     INTEGER NOT NULL,
        avg       INTEGER NOT NULL DEFAULT 0,
        episodes  INTEGER NOT NULL,
        PRIMARY KEY (tvshowid, season)
    ) WITHOUT ROWID
    ''',
    '''
    CREATE TABLE IF NOT EXISTS imdb_run_progress (
        media_type    TEXT    NOT NULL,
        dataset_date  TEXT    NOT NULL,
        dbid          INTEGER NOT NULL,
        PRIMARY KEY (media_type, dataset_date, dbid)
    ) WITHOUT ROWID
    ''',
]

_PROVIDER_SIDE: List[str] = [
    '''
    CREATE TABLE IF NOT EXISTS tmdb_title (
        media_type      TEXT    NOT NULL,
        tmdb_id         INTEGER NOT NULL,
        imdb_id         TEXT,
        tvdb_id         INTEGER,
        title           TEXT,
        status          TEXT,
        release_date    TEXT,
        last_air_date   TEXT,
        next_air_date   TEXT,
        next_complete   INTEGER NOT NULL DEFAULT 0,
        aired_complete  INTEGER NOT NULL DEFAULT 0,
        vote_average    REAL,
        vote_count      INTEGER,
        fetched_at      INTEGER NOT NULL,
        expires_at      INTEGER NOT NULL,
        data            BLOB    NOT NULL,
        UNIQUE (media_type, tmdb_id)
    )
    ''',
    'CREATE INDEX IF NOT EXISTS tmdb_title_imdb ON tmdb_title(imdb_id) WHERE imdb_id IS NOT NULL',
    'CREATE INDEX IF NOT EXISTS tmdb_title_tvdb ON tmdb_title(tvdb_id) WHERE tvdb_id IS NOT NULL',
    'CREATE INDEX IF NOT EXISTS tmdb_title_expires ON tmdb_title(expires_at)',
    'CREATE INDEX IF NOT EXISTS tmdb_title_next ON tmdb_title(next_air_date) '
    'WHERE next_air_date IS NOT NULL',
    '''
    CREATE TABLE IF NOT EXISTS provider_response (
        provider    TEXT    NOT NULL,
        media_type  TEXT    NOT NULL,
        media_id    TEXT    NOT NULL,
        season      INTEGER NOT NULL DEFAULT -1,
        episode     INTEGER NOT NULL DEFAULT -1,
        fetched_at  INTEGER NOT NULL,
        expires_at  INTEGER NOT NULL,
        data        BLOB    NOT NULL,
        UNIQUE (provider, media_type, media_id, season, episode)
    )
    ''',
    'CREATE INDEX IF NOT EXISTS provider_response_expires ON provider_response(expires_at)',
    '''
    CREATE TABLE IF NOT EXISTS online_props (
        media_type  TEXT    NOT NULL,
        item_id     TEXT    NOT NULL,
        scope       TEXT    NOT NULL DEFAULT '',
        fetched_at  INTEGER NOT NULL,
        expires_at  INTEGER NOT NULL,
        data        BLOB    NOT NULL,
        UNIQUE (media_type, item_id, scope)
    )
    ''',
    'CREATE INDEX IF NOT EXISTS online_props_expires ON online_props(expires_at)',
    '''
    CREATE TABLE IF NOT EXISTS tmdb_season (
        tmdb_id     INTEGER NOT NULL,
        season      INTEGER NOT NULL,
        fetched_at  INTEGER NOT NULL,
        expires_at  INTEGER NOT NULL,
        data        BLOB    NOT NULL,
        UNIQUE (tmdb_id, season)
    )
    ''',
    'CREATE INDEX IF NOT EXISTS tmdb_season_expires ON tmdb_season(expires_at)',
    '''
    CREATE TABLE IF NOT EXISTS tmdb_person (
        person_id   INTEGER NOT NULL,
        expires_at  INTEGER NOT NULL,
        data        BLOB    NOT NULL,
        UNIQUE (person_id)
    )
    ''',
    'CREATE INDEX IF NOT EXISTS tmdb_person_expires ON tmdb_person(expires_at)',
    '''
    CREATE TABLE IF NOT EXISTS artwork_cache (
        media_type  TEXT    NOT NULL,
        media_id    TEXT    NOT NULL,
        source      TEXT    NOT NULL,
        art_type    TEXT    NOT NULL,
        expires_at  INTEGER NOT NULL,
        data        BLOB    NOT NULL,
        UNIQUE (media_type, media_id, source, art_type)
    )
    ''',
    'CREATE INDEX IF NOT EXISTS artwork_cache_expires ON artwork_cache(expires_at)',
    'CREATE INDEX IF NOT EXISTS artwork_cache_id ON artwork_cache(media_type, media_id)',
    '''
    CREATE TABLE IF NOT EXISTS blob_cache (
        kind        TEXT    NOT NULL,
        cache_key   TEXT    NOT NULL,
        expires_at  INTEGER NOT NULL,
        miss_count  INTEGER NOT NULL DEFAULT 0,
        data        BLOB    NOT NULL,
        UNIQUE (kind, cache_key)
    )
    ''',
    'CREATE INDEX IF NOT EXISTS blob_cache_expires ON blob_cache(expires_at)',
    '''
    CREATE TABLE IF NOT EXISTS tmdb_find_miss (
        imdb_id     TEXT    NOT NULL,
        media_type  TEXT    NOT NULL,
        checked_at  INTEGER NOT NULL,
        PRIMARY KEY (imdb_id, media_type)
    ) WITHOUT ROWID
    ''',
    '''
    CREATE TABLE IF NOT EXISTS tmdb_episode_miss (
        tmdb_id     INTEGER NOT NULL,
        season      INTEGER NOT NULL,
        episode     INTEGER NOT NULL,
        expires_at  INTEGER NOT NULL,
        PRIMARY KEY (tmdb_id, season, episode)
    ) WITHOUT ROWID
    ''',
    'CREATE INDEX IF NOT EXISTS tmdb_episode_miss_expires '
    'ON tmdb_episode_miss(expires_at)',
    '''
    CREATE TABLE IF NOT EXISTS mb_id_alias (
        old_id        TEXT    NOT NULL,
        canonical_id  TEXT    NOT NULL,
        cached_at     INTEGER NOT NULL,
        PRIMARY KEY (old_id)
    ) WITHOUT ROWID
    ''',
    'CREATE INDEX IF NOT EXISTS mb_id_alias_canonical ON mb_id_alias(canonical_id)',
    '''
    CREATE TABLE IF NOT EXISTS pvr_match (
        title_key   TEXT    NOT NULL,
        year        INTEGER NOT NULL,
        kind        TEXT    NOT NULL,
        media_type  TEXT    NOT NULL,
        tmdb_id     INTEGER NOT NULL,
        checked_at  INTEGER NOT NULL,
        last_seen   INTEGER NOT NULL,
        manual      INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (title_key, year, kind)
    ) WITHOUT ROWID
    ''',
]

_IMDB_SIDE: List[str] = [
    '''
    CREATE TABLE IF NOT EXISTS imdb_rating (
        imdb_id  TEXT    NOT NULL,
        rating   REAL    NOT NULL,
        votes    INTEGER NOT NULL,
        PRIMARY KEY (imdb_id)
    ) WITHOUT ROWID
    ''',
    '''
    CREATE TABLE IF NOT EXISTS imdb_episode (
        parent_id   TEXT    NOT NULL,
        season      INTEGER NOT NULL,
        episode     INTEGER NOT NULL,
        episode_id  TEXT    NOT NULL,
        PRIMARY KEY (parent_id, season, episode)
    ) WITHOUT ROWID
    ''',
    '''
    CREATE TABLE IF NOT EXISTS imdb_dataset (
        dataset        TEXT    NOT NULL,
        last_modified  TEXT,
        downloaded_at  INTEGER,
        entry_count    INTEGER NOT NULL DEFAULT 0,
        library_count  INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (dataset)
    ) WITHOUT ROWID
    ''',
]

_WORKFLOW_SIDE: List[str] = [
    '''
    CREATE TABLE IF NOT EXISTS scan_session (
        id          INTEGER PRIMARY KEY,
        scan_type   TEXT    NOT NULL,
        status      TEXT    NOT NULL DEFAULT 'in_progress',
        started     INTEGER NOT NULL,
        completed   INTEGER,
        media_types TEXT    NOT NULL DEFAULT '',
        art_types   TEXT    NOT NULL DEFAULT '',
        stats       TEXT
    )
    ''',
    '''
    CREATE TABLE IF NOT EXISTS art_queue (
        media_type      TEXT    NOT NULL,
        dbid            INTEGER NOT NULL,
        title           TEXT    NOT NULL DEFAULT '',
        year            TEXT    NOT NULL DEFAULT '',
        status          TEXT    NOT NULL DEFAULT 'pending',
        date_added      INTEGER NOT NULL,
        date_processed  INTEGER,
        PRIMARY KEY (media_type, dbid)
    ) WITHOUT ROWID
    ''',
    'CREATE INDEX IF NOT EXISTS art_queue_status ON art_queue(status)',
    '''
    CREATE TABLE IF NOT EXISTS art_item (
        media_type   TEXT    NOT NULL,
        dbid         INTEGER NOT NULL,
        art_type     TEXT    NOT NULL,
        selected_url TEXT,
        review_mode  TEXT    NOT NULL DEFAULT 'missing',
        status       TEXT    NOT NULL DEFAULT 'pending',
        PRIMARY KEY (media_type, dbid, art_type),
        FOREIGN KEY (media_type, dbid) REFERENCES art_queue(media_type, dbid) ON DELETE CASCADE
    ) WITHOUT ROWID
    ''',
    'CREATE INDEX IF NOT EXISTS art_item_review ON art_item(status, review_mode)',
    '''
    CREATE TABLE IF NOT EXISTS operation_history (
        operation  TEXT    NOT NULL,
        timestamp  INTEGER NOT NULL,
        completed  INTEGER NOT NULL DEFAULT 1,
        scope      TEXT,
        stats      TEXT    NOT NULL,
        PRIMARY KEY (operation)
    ) WITHOUT ROWID
    ''',
    '''
    CREATE TABLE IF NOT EXISTS gif_cache (
        path        TEXT    NOT NULL,
        mtime       REAL    NOT NULL,
        scanned_at  INTEGER NOT NULL,
        PRIMARY KEY (path)
    ) WITHOUT ROWID
    ''',
    '''
    CREATE TABLE IF NOT EXISTS fanarttv_feed (
        feed        TEXT    NOT NULL,
        checked_at  INTEGER NOT NULL,
        PRIMARY KEY (feed)
    ) WITHOUT ROWID
    ''',
    '''
    CREATE TABLE IF NOT EXISTS fanarttv_recheck (
        feed           TEXT    NOT NULL,
        item_id        TEXT    NOT NULL,
        recheck_after  INTEGER NOT NULL,
        PRIMARY KEY (feed, item_id)
    ) WITHOUT ROWID
    ''',
    '''
    CREATE TABLE IF NOT EXISTS cache_reset (
        name        TEXT    PRIMARY KEY,
        applied_at  INTEGER NOT NULL
    ) WITHOUT ROWID
    ''',
]

SCHEMA: List[str] = _KODI_SIDE + _PROVIDER_SIDE + _IMDB_SIDE + _WORKFLOW_SIDE


# tables built only from the Kodi library, with the newest column each must have
_LIBRARY_BUILT: Final = {'slideshow_pool': 'clearlogo'}


def _drop_outdated_library_tables(cursor: sqlite3.Cursor) -> None:
    """Drop a library-built table missing its newest column, for the schema to recreate empty."""
    for table, column in _LIBRARY_BUILT.items():
        columns = {row[1] for row in cursor.execute(f'PRAGMA table_info({table})')}
        if columns and column not in columns:
            cursor.execute(f'DROP TABLE {table}')


def create_schema(cursor: sqlite3.Cursor) -> None:
    """Create every table and index on an open cursor, replacing outdated library-built ones."""
    _drop_outdated_library_tables(cursor)
    for statement in SCHEMA:
        cursor.execute(statement)
    cursor.execute(f'PRAGMA user_version = {SCHEMA_VERSION}')


# each runs once per database, keyed by name; an edited entry needs a new name
CACHE_RESETS: Final = (
    ('tvshow-online-tmdb-only',
     "UPDATE online_props SET expires_at = 0 WHERE media_type = 'tvshow' AND scope = ''"),
)


def apply_cache_resets(conn: sqlite3.Connection) -> None:
    """Apply each cache reset the database has not had yet, under one write lock."""
    conn.execute('BEGIN IMMEDIATE')
    try:
        done = {row[0] for row in conn.execute('SELECT name FROM cache_reset')}
        for name, sql in CACHE_RESETS:
            if name not in done:
                conn.execute(sql)
                conn.execute('INSERT INTO cache_reset (name, applied_at) VALUES (?, ?)',
                             (name, int(time.time())))
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
