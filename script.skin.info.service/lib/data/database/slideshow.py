"""Slideshow pool: one row per library item with fanart, for the background rotators."""
from __future__ import annotations

from typing import List, Optional, Final

from lib.data.database._infrastructure import get_db, sql_placeholders

_POOL_INSERT_SQL: Final = '''
    INSERT INTO slideshow_pool (media_type, dbid, title, fanart, plot, year, artist, clearlogo)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT (media_type, dbid) DO UPDATE SET
        title = excluded.title, fanart = excluded.fanart, plot = excluded.plot,
        year = excluded.year, artist = excluded.artist, clearlogo = excluded.clearlogo
'''

_pool_generation = 0


def _bump_generation() -> None:
    """Invalidate cached pool readers by moving the generation on."""
    global _pool_generation
    _pool_generation += 1


def populate_pool(*record_sets: List[tuple]) -> None:
    """Replace the slideshow pool with all given row sets in one transaction."""
    with get_db() as cursor:
        cursor.execute('DELETE FROM slideshow_pool')
        rows = [row for records in record_sets for row in (records or [])]
        if rows:
            cursor.executemany(_POOL_INSERT_SQL, rows)
    _bump_generation()


def upsert_pool_item(media_type: str, dbid: int, title: str, fanart: str,
                     plot: str, year: Optional[int], artist: str = '', clearlogo: str = '') -> None:
    """Upsert one pool row, then bump the generation."""
    with get_db() as cursor:
        cursor.execute(_POOL_INSERT_SQL,
                       (media_type, dbid, title, fanart, plot, year, artist, clearlogo))
    _bump_generation()


def delete_pool_item(media_type: str, dbid: int) -> None:
    """Delete one pool row, bumping the generation only if a row was removed."""
    with get_db() as cursor:
        cursor.execute('DELETE FROM slideshow_pool WHERE media_type = ? AND dbid = ?',
                       (media_type, dbid))
        removed = cursor.rowcount > 0
    if removed:
        _bump_generation()


def get_pool_compare_fields(media_types: tuple) -> dict:
    """Get `(media_type, dbid) -> (title, fanart, plot, year, artist, clearlogo)` to reconcile."""
    if not media_types:
        return {}
    placeholders = sql_placeholders(len(media_types))
    with get_db() as cursor:
        cursor.execute(
            'SELECT media_type, dbid, title, fanart, plot, year, artist, clearlogo '
            f'FROM slideshow_pool WHERE media_type IN ({placeholders})',
            tuple(media_types))
        return {(r[0], r[1]): (r[2], r[3], r[4], r[5], r[6], r[7]) for r in cursor.fetchall()}


def apply_pool_diff(upserts: List[tuple], deletes: List[tuple]) -> None:
    """Apply a reconcile diff of full-row upserts and key deletes in one transaction."""
    if not upserts and not deletes:
        return
    with get_db() as cursor:
        if upserts:
            cursor.executemany(_POOL_INSERT_SQL, upserts)
        for media_type, dbid in deletes:
            cursor.execute('DELETE FROM slideshow_pool WHERE media_type = ? AND dbid = ?',
                           (media_type, dbid))
    _bump_generation()


def pool_generation() -> int:
    """Counter that moves on every pool change, so rotation cursors know to rebuild."""
    return _pool_generation


def get_all_pool_rows() -> list:
    """Get every pool row of every type, for building the rotation cursors."""
    with get_db() as cursor:
        cursor.execute(
            'SELECT media_type, title, fanart, plot, year, artist, clearlogo FROM slideshow_pool')
        return cursor.fetchall()


def get_artist_description(dbid: int) -> str:
    """Get an artist's cached bio, for a song or album background with none of its own."""
    with get_db() as cursor:
        cursor.execute(
            "SELECT plot FROM slideshow_pool WHERE media_type = 'artist' AND dbid = ?",
            (dbid,))
        row = cursor.fetchone()
    return (row[0] or '') if row else ''


def is_pool_populated() -> bool:
    """True if the slideshow pool has any rows."""
    with get_db() as cursor:
        cursor.execute('SELECT 1 FROM slideshow_pool LIMIT 1')
        return cursor.fetchone() is not None
