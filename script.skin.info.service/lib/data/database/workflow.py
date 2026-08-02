"""Workflow tracking for sessions and operations.

Manages scan_sessions table for artwork review workflows and operation_history
table for art tool runs (texture cache, GIF scanner).
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Optional, Sequence, List, Dict, Set

from lib.data.database._infrastructure import (
    get_db, DB_PATH, sql_placeholders)


def _insert_session_values(cursor: sqlite3.Cursor, junction_table: str, value_column: str,
                           session_id: int, values: List[str]) -> None:
    if not values:
        return
    cursor.executemany(
        f"INSERT INTO {junction_table} (session_id, {value_column}) VALUES (?, ?)",
        [(session_id, v) for v in values],
    )


def _get_session_values(cursor: sqlite3.Cursor, junction_table: str, value_column: str,
                        session_id: int) -> List[str]:
    cursor.execute(
        f"SELECT {value_column} FROM {junction_table} WHERE session_id = ? ORDER BY {value_column}",
        (session_id,),
    )
    return [row[0] for row in cursor.fetchall()]


def _insert_session_media_types(cursor: sqlite3.Cursor, session_id: int,
                                media_types: List[str]) -> None:
    """Insert media types for a session into junction table."""
    _insert_session_values(cursor, 'session_media_types', 'media_type', session_id, media_types)


def _insert_session_art_types(cursor: sqlite3.Cursor, session_id: int,
                              art_types: List[str]) -> None:
    """Insert art types for a session into junction table."""
    _insert_session_values(cursor, 'session_art_types', 'art_type', session_id, art_types)


def _get_session_media_types(cursor: sqlite3.Cursor, session_id: int) -> List[str]:
    """Retrieve media types for a session from junction table."""
    return _get_session_values(cursor, 'session_media_types', 'media_type', session_id)


def _get_session_art_types(cursor: sqlite3.Cursor, session_id: int) -> List[str]:
    """Retrieve art types for a session from junction table."""
    return _get_session_values(cursor, 'session_art_types', 'art_type', session_id)


def get_session_media_types(session_id: int) -> List[str]:
    """Public wrapper to retrieve media types for a session."""
    with get_db(DB_PATH) as cursor:
        return _get_session_media_types(cursor, session_id)


def get_session_art_types(session_id: int) -> List[str]:
    """Public wrapper to retrieve art types for a session."""
    with get_db(DB_PATH) as cursor:
        return _get_session_art_types(cursor, session_id)


def create_scan_session(scan_type: str, media_types: List[str], art_types: List[str]) -> int:
    """Create a scan session, populate its media/art-type junction tables, return session ID."""
    with get_db(DB_PATH) as cursor:
        cursor.execute('''
            INSERT INTO scan_sessions (scan_type, last_activity)
            VALUES (?, ?)
        ''', (
            scan_type,
            datetime.now().isoformat()
        ))

        session_id = cursor.lastrowid
        assert session_id is not None, "Failed to create scan session"

        _insert_session_media_types(cursor, session_id, media_types)
        _insert_session_art_types(cursor, session_id, art_types)

        return session_id


def update_session_stats(session_id: int, stats: dict) -> None:
    """Store JSON-encoded `stats` against a session and bump its last_activity."""
    with get_db(DB_PATH) as cursor:
        cursor.execute('''
            UPDATE scan_sessions
            SET stats = ?, last_activity = ?
            WHERE id = ?
        ''', (json.dumps(stats), datetime.now().isoformat(), session_id))


def _update_session(session_id: int, status: str, **extra) -> None:
    """Update a scan_session row, touching `last_activity`; `extra` supplies other columns."""
    columns = ['status = ?', 'last_activity = ?']
    params: list = [status, datetime.now().isoformat()]
    for col, val in extra.items():
        columns.append(f'{col} = ?')
        params.append(val)
    params.append(session_id)
    with get_db(DB_PATH) as cursor:
        cursor.execute(
            f"UPDATE scan_sessions SET {', '.join(columns)} WHERE id = ?",
            params,
        )


def complete_session(session_id: int) -> None:
    """Mark session as completed."""
    _update_session(session_id, 'completed', completed=datetime.now().isoformat())


def cancel_session(session_id: int) -> None:
    """Mark session as cancelled and timestamp completion."""
    _update_session(session_id, 'cancelled')


def get_session(session_id: int) -> Optional[sqlite3.Row]:
    """Return a scan session row by ID, or None."""
    with get_db(DB_PATH) as cursor:
        cursor.execute('''
            SELECT *
            FROM scan_sessions
            WHERE id = ?
            LIMIT 1
        ''', (session_id,))

        return cursor.fetchone()


def get_last_manual_review_session(
    media_types: Optional[Sequence[str]] = None,
) -> Optional[sqlite3.Row]:
    """Return most recent `manual_review` session; if `media_types` given, match its exact set."""
    with get_db(DB_PATH) as cursor:
        if not media_types:
            cursor.execute('''
                SELECT *
                FROM scan_sessions
                WHERE scan_type = 'manual_review'
                ORDER BY last_activity DESC
                LIMIT 1
            ''')
            return cursor.fetchone()

        media_types_set = set(media_types)
        media_count = len(media_types_set)

        # Safe: .format() only inserts '?' placeholders (media_count controls count, no user input)
        cursor.execute('''
            SELECT s.*
            FROM scan_sessions s
            LEFT JOIN session_media_types smt ON s.id = smt.session_id
            WHERE s.scan_type = 'manual_review'
            GROUP BY s.id
            HAVING (
                (? = 0 AND COUNT(smt.media_type) = 0) OR
                (? > 0 AND
                 COUNT(smt.media_type) = ? AND
                 SUM(CASE WHEN smt.media_type IN ({}) THEN 1 ELSE 0 END) = ?)
            )
            ORDER BY s.last_activity DESC
            LIMIT 1
        '''.format(sql_placeholders(media_count)),
        (media_count, media_count, media_count, *media_types_set, media_count))

        return cursor.fetchone()


def save_operation_stats(operation: str, stats: dict, scope: Optional[str] = None) -> None:
    """Append an operation_history row.

    `stats['cancelled']` flips the completed flag off. `operation` is e.g.
    `texture_precache`, `texture_cleanup`, `gif_scan`.
    """
    timestamp = datetime.now().isoformat()
    stats_json = json.dumps(stats)
    completed = 0 if stats.get('cancelled') else 1

    with get_db(DB_PATH) as cursor:
        cursor.execute('''
            INSERT INTO operation_history (operation, timestamp, stats, completed, scope)
            VALUES (?, ?, ?, ?, ?)
        ''', (operation, timestamp, stats_json, completed, scope))


def get_last_operation_stats(operation: str) -> Optional[dict]:
    """Return the most recent operation_history row as a dict, or None.

    Row fields: `operation, timestamp, stats, completed, scope`. `stats` is JSON-decoded.
    """
    with get_db(DB_PATH) as cursor:
        cursor.execute('''
            SELECT operation, timestamp, stats, completed, scope
            FROM operation_history
            WHERE operation = ?
            ORDER BY timestamp DESC
            LIMIT 1
        ''', (operation,))

        row = cursor.fetchone()
        if not row:
            return None

        return {
            'operation': row['operation'],
            'timestamp': row['timestamp'],
            'stats': json.loads(row['stats']),
            'completed': bool(row['completed']),
            'scope': row['scope']
        }


def get_imdb_update_progress(media_type: str) -> Optional[Dict]:
    """Return saved IMDb update progress, or None.

    Shape: `{dataset_date, processed_ids (set), total_items, started_at}`.
    """
    with get_db(DB_PATH) as cursor:
        cursor.execute('''
            SELECT dataset_date, processed_ids, total_items, started_at
            FROM imdb_update_progress
            WHERE media_type = ?
        ''', (media_type,))

        row = cursor.fetchone()
        if not row:
            return None

        return {
            'dataset_date': row['dataset_date'],
            'processed_ids': set(json.loads(row['processed_ids'])),
            'total_items': row['total_items'],
            'started_at': row['started_at']
        }


def save_imdb_update_progress(media_type: str, dataset_date: str,
                              processed_ids: Set[int], total_items: int) -> None:
    """Save resumable IMDb update progress, preserving `started_at` across upserts."""
    now = datetime.now().isoformat()

    with get_db(DB_PATH) as cursor:
        cursor.execute('''
            SELECT started_at FROM imdb_update_progress WHERE media_type = ?
        ''', (media_type,))
        row = cursor.fetchone()
        started_at = row['started_at'] if row else now

        cursor.execute('''
            INSERT OR REPLACE INTO imdb_update_progress
            (media_type, dataset_date, processed_ids, total_items, started_at, last_updated)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            media_type,
            dataset_date,
            json.dumps(list(processed_ids)),
            total_items,
            started_at,
            now
        ))


def clear_imdb_update_progress(media_type: str) -> None:
    """Clear saved IMDb update progress for a media type (called when the update completes)."""
    with get_db(DB_PATH) as cursor:
        cursor.execute('''
            DELETE FROM imdb_update_progress WHERE media_type = ?
        ''', (media_type,))


def update_synced_ratings(media_type: str, dbid: int,
                          ratings: Dict[str, Dict[str, float]],
                          external_ids: Optional[Dict[str, str]] = None) -> None:
    """Record ratings written to Kodi; skips sources whose key starts with `_`."""
    if not ratings:
        return

    external_ids = external_ids or {}
    now = datetime.now().isoformat()
    with get_db(DB_PATH) as cursor:
        for source, data in ratings.items():
            if source.startswith('_'):
                continue
            rating = data.get('rating')
            votes = data.get('votes', 0)
            if rating is None:
                continue
            ext_id = external_ids.get(source)
            cursor.execute('''
                INSERT OR REPLACE INTO ratings_synced
                (media_type, dbid, source, external_id, rating, votes, synced_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (media_type, dbid, source, ext_id, rating, int(votes), now))


def update_synced_ratings_batch(items: List[tuple]) -> None:
    """Bulk-upsert sync rows, one per `(media_type, dbid, source, external_id, rating, votes)`."""
    if not items:
        return

    now = datetime.now().isoformat()
    with get_db(DB_PATH) as cursor:
        cursor.executemany('''
            INSERT OR REPLACE INTO ratings_synced
            (media_type, dbid, source, external_id, rating, votes, synced_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', [(mt, dbid, src, ext_id, rating, votes, now)
              for mt, dbid, src, ext_id, rating, votes in items])


def get_imdb_changed_items(media_type: Optional[str] = None) -> List[Dict]:
    """Return previously-synced items whose IMDb rating/votes have drifted since.

    Match criteria: rating diff >= 0.05 (half an IMDb step; ratings are 1-decimal), OR
    votes crossed zero, OR votes changed by any amount (<100 votes), >10% (100-1000),
    or >5% (1000+). Joins `ratings_synced` to `imdb_ratings` in a single query.
    Row fields: `media_type, dbid, imdb_id, new_rating, new_votes, old_rating, old_votes`.
    """
    query = '''
        SELECT s.media_type, s.dbid, s.external_id AS imdb_id,
               r.rating AS new_rating, r.votes AS new_votes,
               s.rating AS old_rating, s.votes AS old_votes
        FROM ratings_synced s
        JOIN imdb_ratings r ON s.external_id = r.imdb_id
        WHERE s.source = 'imdb'
          AND (
              ABS(s.rating - r.rating) >= 0.05
              OR (s.votes = 0 AND r.votes > 0)
              OR (s.votes > 0 AND s.votes < 100 AND r.votes != s.votes)
              OR (s.votes >= 100 AND s.votes < 1000
                  AND ABS(r.votes - s.votes) * 1.0 / s.votes > 0.1)
              OR (s.votes >= 1000 AND ABS(r.votes - s.votes) * 1.0 / s.votes > 0.05)
          )
    '''
    with get_db(DB_PATH) as cursor:
        if media_type:
            cursor.execute(query + '  AND s.media_type = ?', (media_type,))
        else:
            cursor.execute(query)

        return [dict(row) for row in cursor.fetchall()]


def get_synced_items_count(media_type: Optional[str] = None) -> int:
    """Count distinct `(media_type, dbid)` pairs in `ratings_synced`, optionally by media type."""
    with get_db(DB_PATH) as cursor:
        if media_type:
            cursor.execute('''
                SELECT COUNT(DISTINCT dbid) as cnt
                FROM ratings_synced
                WHERE media_type = ?
            ''', (media_type,))
        else:
            cursor.execute('''
                SELECT COUNT(*) as cnt FROM (
                    SELECT DISTINCT media_type, dbid FROM ratings_synced
                )
            ''')
        row = cursor.fetchone()
        return row['cnt'] if row else 0


def get_synced_dbids(media_type: str) -> Set[int]:
    """Return the set of DBIDs that have an IMDb sync entry for the given media type."""
    with get_db(DB_PATH) as cursor:
        cursor.execute('''
            SELECT DISTINCT dbid FROM ratings_synced
            WHERE media_type = ? AND source = 'imdb'
        ''', (media_type,))
        return {row['dbid'] for row in cursor.fetchall()}


def clear_synced_ratings(media_type: Optional[str] = None, dbid: Optional[int] = None) -> None:
    """Clear sync tracking. With no args, clears all; `dbid` requires `media_type`."""
    with get_db(DB_PATH) as cursor:
        if media_type and dbid:
            cursor.execute(
                'DELETE FROM ratings_synced WHERE media_type = ? AND dbid = ?',
                (media_type, dbid)
            )
        elif media_type:
            cursor.execute(
                'DELETE FROM ratings_synced WHERE media_type = ?',
                (media_type,)
            )
        else:
            cursor.execute('DELETE FROM ratings_synced')
