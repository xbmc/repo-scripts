"""Mtime and scan time of each gif the poster scan has seen."""
from __future__ import annotations

from typing import Optional, Dict, Set, Union
from lib.data.database._infrastructure import get_db, chunked_in_modify


def get_cached_gif(gif_path: str) -> Optional[Dict[str, Union[float, str]]]:
    """Get `{mtime, scanned_at}` for a cached gif path, or None when not cached."""
    with get_db() as cursor:
        cursor.execute(
            'SELECT mtime, scanned_at FROM gif_cache WHERE path = ?',
            (gif_path,)
        )
        row = cursor.fetchone()
        if row:
            return {
                'mtime': row['mtime'],
                'scanned_at': row['scanned_at']
            }
    return None


def update_gif_cache(gif_path: str, mtime: float, scanned_at: int) -> None:
    """Update a gif's cached mtime and scan time, adding the row if it is new."""
    with get_db() as cursor:
        cursor.execute('''
            INSERT INTO gif_cache (path, mtime, scanned_at)
            VALUES (?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                mtime = excluded.mtime,
                scanned_at = excluded.scanned_at
        ''', (gif_path, mtime, scanned_at))


def get_all_cached_gifs() -> Dict[str, Dict[str, Union[float, str]]]:
    """Get every cached entry as `path -> {mtime, scanned_at}`."""
    cache = {}
    with get_db() as cursor:
        cursor.execute('SELECT path, mtime, scanned_at FROM gif_cache')
        for row in cursor.fetchall():
            cache[row['path']] = {
                'mtime': row['mtime'],
                'scanned_at': row['scanned_at']
            }
    return cache


def cleanup_stale_gifs(accessed_paths: Set[str]) -> int:
    """Clean up entries for gifs this scan did not see, returning how many were removed."""
    with get_db() as cursor:
        if not accessed_paths:
            cursor.execute('DELETE FROM gif_cache')
            return cursor.rowcount

        cursor.execute('SELECT path FROM gif_cache')
        stale = [row['path'] for row in cursor.fetchall() if row['path'] not in accessed_paths]
        if not stale:
            return 0

        return chunked_in_modify(
            cursor, 'DELETE FROM gif_cache WHERE path IN ({placeholders})', [], stale)


def clear_gif_cache() -> int:
    """Clear the whole gif cache, returning how many entries were removed."""
    with get_db() as cursor:
        cursor.execute('DELETE FROM gif_cache')
        return cursor.rowcount
