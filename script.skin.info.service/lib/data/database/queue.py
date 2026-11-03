"""Artwork review queue: library items awaiting art and the art types each one lacks."""
from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from typing import Any, Optional, Sequence, Dict, List, Tuple, Final

from lib.data.database._infrastructure import (
    get_db, DB_PATH, chunked_in_query,
    sql_placeholders as _build_placeholders)
from lib.kodi.client import log

ARTITEM_REVIEW_MISSING: Final = 'missing'

STATUS_PENDING: Final = 'pending'
STATUS_COMPLETED: Final = 'completed'
STATUS_SKIPPED: Final = 'skipped'
STATUS_ERROR: Final = 'error'

ItemKey = Tuple[str, int]


@dataclass(frozen=True)
class ArtItemEntry:
    """Single art item queued for review or processing."""

    media_type: str
    dbid: int
    art_type: str
    selected_url: Optional[str]
    review_mode: str
    status: str


@dataclass(frozen=True)
class QueueEntry:
    """Top-level queue record representing a library item awaiting review."""

    media_type: str
    dbid: int
    title: str
    year: str
    status: str


def _row_to_queue_entry(row: sqlite3.Row) -> QueueEntry:
    """Convert database row to QueueEntry dataclass."""
    return QueueEntry(
        media_type=row['media_type'],
        dbid=row['dbid'],
        title=row['title'] or '',
        year=row['year'] or '',
        status=row['status'] or STATUS_PENDING,
    )


def _row_to_art_item(row: sqlite3.Row) -> ArtItemEntry:
    """Convert database row to ArtItemEntry dataclass."""
    return ArtItemEntry(
        media_type=row['media_type'],
        dbid=row['dbid'],
        art_type=row['art_type'],
        selected_url=row['selected_url'],
        review_mode=row['review_mode'] or ARTITEM_REVIEW_MISSING,
        status=row['status'] or STATUS_PENDING,
    )


def clear_queue_and_sessions() -> None:
    """Clear all queue data, including scan sessions."""
    with get_db(DB_PATH) as cursor:
        cursor.execute('DELETE FROM art_item')
        cursor.execute('DELETE FROM art_queue')
        cursor.execute('DELETE FROM scan_session')


def clear_queue_for_media(media_types: Sequence[str]) -> None:
    """Clear queue entries for specific media types."""
    if not media_types:
        return
    placeholders = _build_placeholders(len(media_types))
    with get_db(DB_PATH) as cursor:
        cursor.execute(f'DELETE FROM art_queue WHERE media_type IN ({placeholders})',
                       tuple(media_types))


def add_to_queue_batch(items: List[dict]) -> None:
    """Add `{media_type, dbid, title, year?}` queue rows; existing ones reset to pending."""
    if not items:
        return
    now = int(time.time())
    with get_db(DB_PATH) as cursor:
        cursor.executemany(
            'INSERT INTO art_queue '
            '(media_type, dbid, title, year, status, date_added) '
            f"VALUES (?, ?, ?, ?, '{STATUS_PENDING}', ?) "
            'ON CONFLICT (media_type, dbid) DO UPDATE SET '
            f"status = '{STATUS_PENDING}', date_processed = NULL, "
            'date_added = excluded.date_added, title = excluded.title, '
            'year = excluded.year',
            [(item['media_type'], item['dbid'], item.get('title', ''), item.get('year', ''),
              now) for item in items])


def add_art_items_batch(art_items: List[dict]) -> None:
    """Add `{media_type, dbid, art_type}` art rows; existing ones reset to pending."""
    if not art_items:
        return
    with get_db(DB_PATH) as cursor:
        cursor.executemany(
            'INSERT INTO art_item (media_type, dbid, art_type, review_mode, status) '
            f"VALUES (?, ?, ?, '{ARTITEM_REVIEW_MISSING}', '{STATUS_PENDING}') "
            'ON CONFLICT (media_type, dbid, art_type) DO UPDATE SET '
            f"review_mode = '{ARTITEM_REVIEW_MISSING}', status = '{STATUS_PENDING}'",
            [(item['media_type'], item['dbid'], item['art_type']) for item in art_items])


def get_next_batch(batch_size: int = 100, status: str = STATUS_PENDING,
                   media_types: Optional[Sequence[str]] = None) -> List[QueueEntry]:
    """Get the oldest queue entries with one status, optionally limited to some media types."""
    with get_db(DB_PATH) as cursor:
        query = 'SELECT * FROM art_queue WHERE status = ?'
        params: List[Any] = [status]

        if media_types:
            placeholders = _build_placeholders(len(media_types))
            query += f' AND media_type IN ({placeholders})'
            params.extend(media_types)

        query += ' ORDER BY date_added ASC, media_type ASC, dbid ASC LIMIT ?'
        params.append(batch_size)

        cursor.execute(query, params)
        return [_row_to_queue_entry(row) for row in cursor.fetchall()]


def get_art_items_for_queue(media_type: str, dbid: int) -> List[ArtItemEntry]:
    """Get all art items for a queue entry."""
    with get_db(DB_PATH) as cursor:
        cursor.execute('SELECT * FROM art_item WHERE media_type = ? AND dbid = ?',
                       (media_type, dbid))
        return [_row_to_art_item(row) for row in cursor.fetchall()]


def get_art_items_for_queue_batch(keys: Sequence[ItemKey]) -> Dict[ItemKey, List[ArtItemEntry]]:
    """Get `(media_type, dbid) -> [ArtItemEntry]` for multiple queue entries."""
    if not keys:
        return {}

    result: Dict[ItemKey, List[ArtItemEntry]] = {key: [] for key in keys}
    by_media_type: Dict[str, List[int]] = {}
    for media_type, dbid in keys:
        by_media_type.setdefault(media_type, []).append(dbid)

    with get_db(DB_PATH) as cursor:
        for media_type, dbids in by_media_type.items():
            rows = chunked_in_query(
                cursor,
                'SELECT * FROM art_item WHERE media_type = ? AND dbid IN ({placeholders})',
                [media_type], dbids)
            for row in rows:
                key = (row['media_type'], row['dbid'])
                if key in result:
                    result[key].append(_row_to_art_item(row))
    return result


def update_queue_status(media_type: str, dbid: int, status: str) -> None:
    """Update a queue item's status, stamping it processed now."""
    with get_db(DB_PATH) as cursor:
        cursor.execute(
            'UPDATE art_queue SET status = ?, date_processed = ? '
            'WHERE media_type = ? AND dbid = ?',
            (status, int(time.time()), media_type, dbid))


def update_art_item(media_type: str, dbid: int, art_type: str, selected_url: str) -> None:
    """Update an art item's selected URL and mark it completed."""
    with get_db(DB_PATH) as cursor:
        cursor.execute(
            'UPDATE art_item SET selected_url = ?, status = ? '
            'WHERE media_type = ? AND dbid = ? AND art_type = ?',
            (selected_url, STATUS_COMPLETED, media_type, dbid, art_type))


def update_art_item_status(media_type: str, dbid: int, art_type: str, status: str) -> None:
    """Update art item status without changing selected URL."""
    with get_db(DB_PATH) as cursor:
        cursor.execute(
            'UPDATE art_item SET status = ? WHERE media_type = ? AND dbid = ? AND art_type = ?',
            (status, media_type, dbid, art_type))


def get_queue_stats(media_types: Optional[Sequence[str]] = None) -> Dict[str, int]:
    """Get `status -> count` across the queue, optionally limited to some media types."""
    with get_db(DB_PATH) as cursor:
        query = 'SELECT status, COUNT(*) as count FROM art_queue'
        params: List[Any] = []

        if media_types:
            placeholders = _build_placeholders(len(media_types))
            query += f' WHERE media_type IN ({placeholders})'
            params.extend(media_types)

        query += ' GROUP BY status'
        cursor.execute(query, params)
        return {row['status']: row['count'] for row in cursor.fetchall()}


def count_pending_missing_art(media_types: Optional[Sequence[str]] = None) -> int:
    """Count pending `art_item` rows with `review_mode='missing'` whose queue row is pending."""
    with get_db(DB_PATH) as cursor:
        query = '''
            SELECT COUNT(*) AS count
            FROM art_item AS ai
            JOIN art_queue AS q ON ai.media_type = q.media_type AND ai.dbid = q.dbid
            WHERE ai.status = ?
              AND ai.review_mode = ?
              AND q.status = ?
        '''
        params: List[Any] = [STATUS_PENDING, ARTITEM_REVIEW_MISSING, STATUS_PENDING]

        if media_types:
            placeholders = _build_placeholders(len(media_types))
            query += f' AND q.media_type IN ({placeholders})'
            params.extend(media_types)

        cursor.execute(query, params)
        row = cursor.fetchone()
        return int(row['count']) if row else 0


def count_queue_items(status: Optional[str] = None,
                      media_types: Optional[Sequence[str]] = None) -> int:
    """Count queue items matching the optional status and/or media-type filters."""
    with get_db(DB_PATH) as cursor:
        query = 'SELECT COUNT(*) AS count FROM art_queue WHERE 1=1'
        params: List[Any] = []

        if status:
            query += ' AND status = ?'
            params.append(status)

        if media_types:
            placeholders = _build_placeholders(len(media_types))
            query += f' AND media_type IN ({placeholders})'
            params.extend(media_types)

        cursor.execute(query, params)
        row = cursor.fetchone()
        return int(row['count']) if row else 0


def cleanup_old_queue_items(days_old: int = 30) -> int:
    """Clean up queue items processed, or left pending, more than the given days ago."""
    cutoff = int(time.time()) - days_old * 86400
    with get_db(DB_PATH) as cursor:
        cursor.execute(
            'DELETE FROM art_queue WHERE status IN (?, ?, ?) '
            'AND date_processed IS NOT NULL AND date_processed < ?',
            (STATUS_COMPLETED, STATUS_SKIPPED, STATUS_ERROR, cutoff))
        deleted = cursor.rowcount

        cursor.execute('DELETE FROM art_queue WHERE status = ? AND date_added < ?',
                       (STATUS_PENDING, cutoff))
        deleted += cursor.rowcount

    if deleted > 0:
        log("Database", f"Cleaned up {deleted} old queue items")

    return deleted
