"""Queue CRUD operations for artwork review workflow.

Manages art_queue and art_items tables. Handles adding items to queue,
retrieving batches, updating status, and cleanup.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional, Sequence, Dict, List

from lib.data.database._infrastructure import (
    get_db, DB_PATH, generate_guid, chunked_in_query,
    sql_placeholders as _build_placeholders)
from lib.kodi.utilities import validate_media_type, validate_dbid
from lib.kodi.client import log

ARTITEM_REVIEW_MISSING = 'missing'

STATUS_PENDING = 'pending'
STATUS_COMPLETED = 'completed'
STATUS_SKIPPED = 'skipped'
STATUS_ERROR = 'error'
STATUS_CANCELLED = 'cancelled'


@dataclass(frozen=True)
class ArtItemEntry:
    """Single art item queued for review or processing."""

    id: int
    queue_id: int
    art_type: str
    selected_url: Optional[str]
    review_mode: str
    requires_manual: bool
    status: str


@dataclass(frozen=True)
class QueueEntry:
    """Top-level queue record representing a library item awaiting review."""

    id: int
    guid: str
    media_type: str
    dbid: int
    title: str
    year: str
    status: str
    scope: str
    scan_session_id: Optional[int]


def _row_to_queue_entry(row: sqlite3.Row) -> QueueEntry:
    """Convert database row to QueueEntry dataclass."""
    return QueueEntry(
        id=row['id'],
        guid=row['guid'] or '',
        media_type=row['media_type'],
        dbid=row['dbid'],
        title=row['title'] or '',
        year=row['year'] or '',
        status=row['status'] or STATUS_PENDING,
        scope=row['scope'] or '',
        scan_session_id=row['scan_session_id'],
    )


def _row_to_art_item(row: sqlite3.Row) -> ArtItemEntry:
    """Convert database row to ArtItemEntry dataclass."""
    return ArtItemEntry(
        id=row['id'],
        queue_id=row['queue_id'],
        art_type=row['art_type'],
        selected_url=row['selected_url'],
        review_mode=row['review_mode'] or ARTITEM_REVIEW_MISSING,
        requires_manual=bool(row['requires_manual']),
        status=row['status'] or STATUS_PENDING,
    )


def clear_queue_and_sessions() -> None:
    """Clear all queue data, including scan sessions."""
    with get_db(DB_PATH) as cursor:
        cursor.execute('DELETE FROM art_items')
        cursor.execute('DELETE FROM art_queue')
        cursor.execute('DELETE FROM scan_sessions')


def clear_queue_for_media(media_types: Sequence[str]) -> None:
    """Clear queue entries for specific media types."""
    if not media_types:
        return

    placeholders = _build_placeholders(len(media_types))

    with get_db(DB_PATH) as cursor:
        cursor.execute(f'''
            DELETE FROM art_queue
            WHERE media_type IN ({placeholders})
        ''', tuple(media_types))


def add_to_queue(
    media_type: str,
    dbid: int,
    title: str,
    year: str = '',
    priority: int = 5,
    scope: str = '',
    scan_session_id: Optional[int] = None,
    guid: Optional[str] = None,
) -> int:
    """Add a single item to the queue. Existing `(media_type, dbid)` gets re-set to pending.

    Thin wrapper over `add_to_queue_batch`; returns the queue ID.
    """
    if not validate_media_type(media_type):
        raise ValueError(f"Invalid media_type: {media_type}")
    if not validate_dbid(dbid):
        raise ValueError(f"Invalid dbid: {dbid} (must be positive integer)")

    items = [{
        'media_type': media_type,
        'dbid': dbid,
        'title': title,
        'year': year,
        'priority': priority,
        'scope': scope,
        'scan_session_id': scan_session_id,
        'guid': guid
    }]

    queue_ids = add_to_queue_batch(items)
    return queue_ids[0]


def add_art_item(
    queue_id: int,
    art_type: str,
    requires_manual: bool = False,
    scan_session_id: Optional[int] = None,
) -> None:
    """Add art item to queue or update if exists (UPSERT operation).

    Thin wrapper over `add_art_items_batch`.
    """
    add_art_items_batch([{
        'queue_id': queue_id,
        'art_type': art_type,
        'requires_manual': requires_manual,
        'scan_session_id': scan_session_id,
    }])


def add_to_queue_batch(items: List[dict]) -> List[int]:
    """Upsert multiple items. Returns queue IDs in input order.

    Each item: `{media_type, dbid, title, year?, priority?, scope?, scan_session_id?, guid?}`.
    """
    if not items:
        return []

    with get_db(DB_PATH) as cursor:
        prepared_items = []
        for item in items:
            media_type = item['media_type']
            dbid = item['dbid']
            title = item.get('title', '')
            year = item.get('year', '')
            priority = item.get('priority', 5)
            scope = item.get('scope', '')
            scan_session_id = item.get('scan_session_id')
            guid = item.get('guid') or generate_guid()

            prepared_items.append((
                media_type, dbid, title, year, priority,
                scope or '', scan_session_id, guid
            ))

        cursor.executemany(f'''
            INSERT INTO art_queue (media_type, dbid, title, year, priority, scope, scan_session_id, guid)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(media_type, dbid) DO UPDATE SET
                status = '{STATUS_PENDING}',
                date_processed = NULL,
                scope = COALESCE(NULLIF(excluded.scope, ''), art_queue.scope),
                scan_session_id = COALESCE(excluded.scan_session_id, art_queue.scan_session_id),
                guid = COALESCE(NULLIF(art_queue.guid, ''), excluded.guid)
        ''', prepared_items)  # noqa: E501

        dbids_by_media_type: Dict[str, List[int]] = {}
        for item in items:
            dbids_by_media_type.setdefault(item['media_type'], []).append(item['dbid'])

        id_map = {}
        for media_type, dbids in dbids_by_media_type.items():
            rows = chunked_in_query(cursor, '''
                SELECT id, media_type, dbid
                FROM art_queue
                WHERE media_type = ? AND dbid IN ({placeholders})
            ''', [media_type], dbids)
            for row in rows:
                id_map[(row['media_type'], row['dbid'])] = row['id']

        result = []
        for item in items:
            key = (item['media_type'], item['dbid'])
            queue_id = id_map.get(key)
            if queue_id is None:
                raise RuntimeError(
                    f"UPSERT succeeded but SELECT failed for {key} - database corruption?")
            result.append(queue_id)
        return result


def add_art_items_batch(art_items: List[dict]) -> None:
    """Upsert multiple art items in one transaction.

    Each item: `{queue_id, art_type, requires_manual?, scan_session_id?}`.
    """
    if not art_items:
        return

    with get_db(DB_PATH) as cursor:
        cursor.executemany('''
            INSERT INTO art_items (queue_id, art_type, review_mode, requires_manual, status, scan_session_id)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(queue_id, art_type) DO UPDATE SET
                review_mode = excluded.review_mode,
                requires_manual = excluded.requires_manual,
                status = excluded.status,
                scan_session_id = excluded.scan_session_id
        ''', [(  # noqa: E501
            item['queue_id'],
            item['art_type'],
            ARTITEM_REVIEW_MISSING,
            1 if item.get('requires_manual') else 0,
            STATUS_PENDING,
            item.get('scan_session_id'),
        ) for item in art_items])


def get_next_batch(batch_size: int = 100, status: str = STATUS_PENDING,
                   media_types: Optional[Sequence[str]] = None) -> List[QueueEntry]:
    """Fetch up to `batch_size` queue entries filtered by status (and optionally media types)."""
    with get_db(DB_PATH) as cursor:
        query = '''
            SELECT * FROM art_queue
            WHERE status = ?
        '''
        params: List[Any] = [status]

        if media_types:
            placeholders = _build_placeholders(len(media_types))
            query += f' AND media_type IN ({placeholders})'
            params.extend(media_types)

        query += ' ORDER BY priority ASC, id ASC LIMIT ?'
        params.append(batch_size)

        cursor.execute(query, params)

        return [_row_to_queue_entry(row) for row in cursor.fetchall()]


def get_art_items_for_queue(queue_id: int) -> List[ArtItemEntry]:
    """Get all art items for a queue entry."""
    with get_db(DB_PATH) as cursor:
        cursor.execute('''
            SELECT * FROM art_items
            WHERE queue_id = ?
        ''', (queue_id,))

        return [_row_to_art_item(row) for row in cursor.fetchall()]


def get_art_items_for_queue_batch(queue_ids: List[int]) -> Dict[int, List[ArtItemEntry]]:
    """Return `queue_id -> [ArtItemEntry]` for multiple queue entries in one query."""
    if not queue_ids:
        return {}

    with get_db(DB_PATH) as cursor:
        rows = list(chunked_in_query(cursor, '''
            SELECT * FROM art_items
            WHERE queue_id IN ({placeholders})
        ''', [], queue_ids))

        result: Dict[int, List[ArtItemEntry]] = {qid: [] for qid in queue_ids}
        for row in rows:
            queue_id = row['queue_id']
            if queue_id in result:
                result[queue_id].append(_row_to_art_item(row))

        return result


def update_queue_status(queue_id: int, status: str) -> None:
    """Update queue item status."""
    with get_db(DB_PATH) as cursor:
        now = datetime.now().isoformat()
        cursor.execute('''
            UPDATE art_queue
            SET status = ?, date_processed = ?
            WHERE id = ?
        ''', (status, now, queue_id))


def update_art_item(art_item_id: int, selected_url: str, auto_applied: bool = False) -> None:
    """Update art item with selected URL."""
    with get_db(DB_PATH) as cursor:
        now = datetime.now().isoformat()
        cursor.execute('''
            UPDATE art_items
            SET selected_url = ?, auto_applied = ?, status = ?, requires_manual = 0, date_processed = ?
            WHERE id = ?
        ''', (selected_url, int(auto_applied), STATUS_COMPLETED, now, art_item_id))  # noqa: E501


def update_art_item_status(art_item_id: int, status: str) -> None:
    """Update art item status without changing selected URL."""
    with get_db(DB_PATH) as cursor:
        now = datetime.now().isoformat()
        cursor.execute('''
            UPDATE art_items
            SET status = ?, date_processed = COALESCE(date_processed, ?)
            WHERE id = ?
        ''', (status, now, art_item_id))


def get_queue_stats(media_types: Optional[Sequence[str]] = None) -> Dict[str, int]:
    """Return `status -> count` across the queue (optionally filtered by media types)."""
    with get_db(DB_PATH) as cursor:
        stats = {}

        query = '''
            SELECT status, COUNT(*) as count
            FROM art_queue
        '''
        params: List[Any] = []

        if media_types:
            placeholders = _build_placeholders(len(media_types))
            query += f' WHERE media_type IN ({placeholders})'
            params.extend(media_types)

        query += ' GROUP BY status'

        cursor.execute(query, params)
        for row in cursor.fetchall():
            stats[row['status']] = row['count']

    return stats


def count_pending_missing_art(media_types: Optional[Sequence[str]] = None) -> int:
    """Count pending `art_items` with `review_mode='missing'` whose queue row is also pending."""
    with get_db(DB_PATH) as cursor:
        query = '''
            SELECT COUNT(*) AS count
            FROM art_items AS ai
            JOIN art_queue AS q ON ai.queue_id = q.id
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
    """Delete completed/skipped/error queue items processed more than `days_old` days ago."""
    with get_db(DB_PATH) as cursor:
        cutoff = datetime.now() - timedelta(days=days_old)
        cutoff_str = cutoff.isoformat()

        cursor.execute('''
            DELETE FROM art_queue
            WHERE status IN (?, ?, ?)
            AND date_processed IS NOT NULL
            AND date_processed < ?
        ''', (STATUS_COMPLETED, STATUS_SKIPPED, STATUS_ERROR, cutoff_str))

        deleted = cursor.rowcount

    if deleted > 0:
        log("Database", f"Cleaned up {deleted} old queue items")

    return deleted
