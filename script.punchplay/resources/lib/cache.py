"""
SQLite-backed persistence for PunchPlay.

Tables:
  identifier_cache  — resolved metadata cache for local identification.
  pending_scrobbles — offline queue for retriable scrobble events.
  runtime_status    — lightweight health/debug state for settings dialogs.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from typing import Any

import xbmc

from constants import (
    IDENTIFIER_CACHE_TTL_SECS,
    OFFLINE_QUEUE_MAX_ITEMS,
    QUEUE_ENTRY_MAX_AGE_SECS,
    SCROBBLE_PROGRESS_ENDPOINT,
    SCROBBLE_STOP_ENDPOINT,
    get_profile_dir,
)


class Cache:
    def __init__(self) -> None:
        data_dir = get_profile_dir()
        os.makedirs(data_dir, exist_ok=True)
        self._db_path = os.path.join(data_dir, "punchplay.db")
        self._init_db()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path, timeout=10)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS identifier_cache (
                    key        TEXT    PRIMARY KEY,
                    data       TEXT    NOT NULL,
                    created_at INTEGER NOT NULL,
                    expires_at INTEGER
                );

                CREATE TABLE IF NOT EXISTS pending_scrobbles (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    endpoint        TEXT    NOT NULL,
                    payload         TEXT    NOT NULL,
                    created_at      INTEGER NOT NULL,
                    attempt_count   INTEGER NOT NULL DEFAULT 0,
                    last_attempt_at INTEGER,
                    last_error      TEXT
                );

                CREATE TABLE IF NOT EXISTS runtime_status (
                    singleton                  INTEGER PRIMARY KEY CHECK (singleton = 1),
                    account_username           TEXT,
                    last_successful_event_at   INTEGER,
                    last_successful_event_type TEXT,
                    last_successful_title      TEXT,
                    last_error_at              INTEGER,
                    last_error                 TEXT,
                    last_identify_at           INTEGER,
                    last_identify_status       TEXT,
                    last_identify_title        TEXT,
                    last_identify_confidence   REAL
                );

                CREATE TABLE IF NOT EXISTS rating_suppressions (
                    key        TEXT PRIMARY KEY,
                    scope      TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                );
                """
            )
            conn.execute(
                "INSERT OR IGNORE INTO runtime_status (singleton) VALUES (1)"
            )
            self._migrate_identifier_cache(conn)
            self._migrate_pending_scrobbles(conn)
            self._migrate_runtime_status(conn)

    def _migrate_identifier_cache(self, conn: sqlite3.Connection) -> None:
        existing_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(identifier_cache)")
        }
        if "expires_at" not in existing_columns:
            conn.execute(
                "ALTER TABLE identifier_cache "
                "ADD COLUMN expires_at INTEGER"
            )
            conn.execute(
                "UPDATE identifier_cache SET expires_at = created_at + ?",
                (IDENTIFIER_CACHE_TTL_SECS,),
            )

    def _migrate_pending_scrobbles(self, conn: sqlite3.Connection) -> None:
        existing_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(pending_scrobbles)")
        }
        if "attempt_count" not in existing_columns:
            conn.execute(
                "ALTER TABLE pending_scrobbles "
                "ADD COLUMN attempt_count INTEGER NOT NULL DEFAULT 0"
            )
        if "last_attempt_at" not in existing_columns:
            conn.execute(
                "ALTER TABLE pending_scrobbles "
                "ADD COLUMN last_attempt_at INTEGER"
            )
        if "last_error" not in existing_columns:
            conn.execute(
                "ALTER TABLE pending_scrobbles "
                "ADD COLUMN last_error TEXT"
            )

    def _migrate_runtime_status(self, conn: sqlite3.Connection) -> None:
        existing_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(runtime_status)")
        }
        _VALID_TYPES = {"TEXT", "INTEGER", "REAL", "BLOB"}
        for column_name, column_type in (
            ("last_identify_at", "INTEGER"),
            ("last_identify_status", "TEXT"),
            ("last_identify_title", "TEXT"),
            ("last_identify_confidence", "REAL"),
        ):
            if column_name not in existing_columns:
                if not column_name.replace("_", "").isalnum():
                    raise ValueError(f"Invalid column name: {column_name}")
                if column_type.upper() not in _VALID_TYPES:
                    raise ValueError(f"Invalid column type: {column_type}")
                conn.execute(
                    f"ALTER TABLE runtime_status ADD COLUMN {column_name} {column_type}"
                )

    def _drop_expired_pending_scrobbles_locked(
        self,
        conn: sqlite3.Connection,
    ) -> int:
        cutoff = int(time.time()) - QUEUE_ENTRY_MAX_AGE_SECS
        cur = conn.execute(
            "DELETE FROM pending_scrobbles WHERE created_at < ?",
            (cutoff,),
        )
        return max(cur.rowcount or 0, 0)

    def _drop_one_low_value_pending_scrobble_locked(
        self,
        conn: sqlite3.Connection,
    ) -> bool:
        for sql, params in (
            (
                "DELETE FROM pending_scrobbles WHERE id = ("
                "SELECT id FROM pending_scrobbles "
                "WHERE endpoint = ? ORDER BY id LIMIT 1"
                ")",
                (SCROBBLE_PROGRESS_ENDPOINT,),
            ),
            (
                "DELETE FROM pending_scrobbles WHERE id = ("
                "SELECT id FROM pending_scrobbles "
                "WHERE endpoint != ? ORDER BY id LIMIT 1"
                ")",
                (SCROBBLE_STOP_ENDPOINT,),
            ),
            (
                "DELETE FROM pending_scrobbles WHERE id = ("
                "SELECT id FROM pending_scrobbles ORDER BY id LIMIT 1"
                ")",
                (),
            ),
        ):
            cur = conn.execute(sql, params)
            if (cur.rowcount or 0) > 0:
                return True
        return False

    # ------------------------------------------------------------------
    # Identifier cache
    # ------------------------------------------------------------------

    def get_identifier(self, key: str) -> dict[str, Any] | None:
        now = int(time.time())
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT data
                FROM identifier_cache
                WHERE key = ?
                  AND COALESCE(expires_at, created_at + ?) >= ?
                """,
                (key, IDENTIFIER_CACHE_TTL_SECS, now),
            ).fetchone()
        if not row:
            return None
        try:
            return json.loads(row[0])
        except Exception:
            return None

    def set_identifier(
        self,
        key: str,
        data: dict[str, Any],
        ttl_secs: int = IDENTIFIER_CACHE_TTL_SECS,
    ) -> None:
        now = int(time.time())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO identifier_cache (key, data, created_at, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (key, json.dumps(data), now, now + max(1, int(ttl_secs))),
            )

    def prune_identifier_cache(self) -> None:
        now = int(time.time())
        with self._connect() as conn:
            conn.execute(
                """
                DELETE FROM identifier_cache
                WHERE COALESCE(expires_at, created_at + ?) < ?
                """,
                (IDENTIFIER_CACHE_TTL_SECS, now),
            )

    def get_identifier_cache_size(self) -> int:
        now = int(time.time())
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*)
                FROM identifier_cache
                WHERE COALESCE(expires_at, created_at + ?) >= ?
                """,
                (IDENTIFIER_CACHE_TTL_SECS, now),
            ).fetchone()
        return int(row[0] or 0)

    # ------------------------------------------------------------------
    # Offline queue
    # ------------------------------------------------------------------

    def enqueue_scrobble(self, endpoint: str, payload: dict[str, Any]) -> None:
        now = int(time.time())
        with self._connect() as conn:
            expired = self._drop_expired_pending_scrobbles_locked(conn)
            if expired:
                xbmc.log(
                    f"[PunchPlay] Dropped {expired} expired queued scrobble(s)",
                    xbmc.LOGINFO,
                )

            count = int(
                conn.execute(
                    "SELECT COUNT(*) FROM pending_scrobbles"
                ).fetchone()[0]
            )
            while count >= OFFLINE_QUEUE_MAX_ITEMS:
                if not self._drop_one_low_value_pending_scrobble_locked(conn):
                    break
                count -= 1

            conn.execute(
                """
                INSERT INTO pending_scrobbles (
                    endpoint,
                    payload,
                    created_at,
                    attempt_count,
                    last_attempt_at,
                    last_error
                )
                VALUES (?, ?, ?, 0, NULL, NULL)
                """,
                (endpoint, json.dumps(payload), now),
            )

        xbmc.log(f"[PunchPlay] Queued offline scrobble → {endpoint}", xbmc.LOGDEBUG)

    def get_pending_scrobbles(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    id,
                    endpoint,
                    payload,
                    created_at,
                    attempt_count,
                    last_attempt_at,
                    last_error
                FROM pending_scrobbles
                ORDER BY id
                """
            ).fetchall()

        pending: list[dict[str, Any]] = []
        for row in rows:
            try:
                payload = json.loads(row[2])
            except Exception:
                payload = {}
            pending.append(
                {
                    "id": int(row[0]),
                    "endpoint": row[1],
                    "payload": payload,
                    "created_at": int(row[3]),
                    "attempt_count": int(row[4] or 0),
                    "last_attempt_at": row[5],
                    "last_error": row[6],
                }
            )
        return pending

    def delete_pending_scrobble(self, scrobble_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM pending_scrobbles WHERE id = ?",
                (scrobble_id,),
            )

    def mark_pending_scrobble_attempt(self, scrobble_id: int, error: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE pending_scrobbles
                SET attempt_count = attempt_count + 1,
                    last_attempt_at = ?,
                    last_error = ?
                WHERE id = ?
                """,
                (int(time.time()), error[:500], scrobble_id),
            )

    def delete_pending_scrobbles_for_session(self, playback_session_id: str) -> None:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, payload FROM pending_scrobbles ORDER BY id"
            ).fetchall()
            ids: list[int] = []
            for row in rows:
                try:
                    payload = json.loads(row[1])
                except Exception:
                    continue
                if payload.get("playback_session_id") == playback_session_id:
                    ids.append(int(row[0]))
            if ids:
                conn.executemany(
                    "DELETE FROM pending_scrobbles WHERE id = ?",
                    [(scrobble_id,) for scrobble_id in ids],
                )
                xbmc.log(
                    f"[PunchPlay] Cleared {len(ids)} queued event(s) for completed session",
                    xbmc.LOGDEBUG,
                )

    def clear_pending_scrobbles(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM pending_scrobbles")

    def drop_expired_pending_scrobbles(self) -> int:
        with self._connect() as conn:
            dropped = self._drop_expired_pending_scrobbles_locked(conn)
        return dropped

    def get_queue_summary(self) -> dict[str, int | None]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*), MIN(created_at) FROM pending_scrobbles"
            ).fetchone()
        count = int(row[0] or 0)
        oldest_created_at = int(row[1]) if row[1] is not None else None
        oldest_age_secs = None
        if oldest_created_at is not None:
            oldest_age_secs = max(0, int(time.time()) - oldest_created_at)
        return {"count": count, "oldest_age_secs": oldest_age_secs}

    def get_queue_endpoint_summary(self) -> dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT endpoint, COUNT(*)
                FROM pending_scrobbles
                GROUP BY endpoint
                ORDER BY endpoint
                """
            ).fetchall()
        return {str(endpoint): int(count or 0) for endpoint, count in rows}

    # ------------------------------------------------------------------
    # Rating suppression
    # ------------------------------------------------------------------

    def set_rating_suppression(self, key: str, scope: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO rating_suppressions (key, scope, created_at)
                VALUES (?, ?, ?)
                """,
                (key, scope[:50], int(time.time())),
            )

    def has_rating_suppression(self, key: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM rating_suppressions WHERE key = ?",
                (key,),
            ).fetchone()
        return bool(row)

    # ------------------------------------------------------------------
    # Runtime status
    # ------------------------------------------------------------------

    def get_runtime_status(self) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    account_username,
                    last_successful_event_at,
                    last_successful_event_type,
                    last_successful_title,
                    last_error_at,
                    last_error,
                    last_identify_at,
                    last_identify_status,
                    last_identify_title,
                    last_identify_confidence
                FROM runtime_status
                WHERE singleton = 1
                """
            ).fetchone()
        if not row:
            return {}
        return {
            "account_username": row[0],
            "last_successful_event_at": row[1],
            "last_successful_event_type": row[2],
            "last_successful_title": row[3],
            "last_error_at": row[4],
            "last_error": row[5],
            "last_identify_at": row[6],
            "last_identify_status": row[7],
            "last_identify_title": row[8],
            "last_identify_confidence": row[9],
        }

    def set_account_username(self, username: str | None) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE runtime_status SET account_username = ? WHERE singleton = 1",
                (username,),
            )

    def record_success(self, endpoint: str, title: str = "") -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE runtime_status
                SET last_successful_event_at = ?,
                    last_successful_event_type = ?,
                    last_successful_title = ?
                WHERE singleton = 1
                """,
                (int(time.time() * 1000), endpoint, title[:300]),
            )

    def record_error(self, error: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE runtime_status
                SET last_error_at = ?,
                    last_error = ?
                WHERE singleton = 1
                """,
                (int(time.time() * 1000), error[:500]),
            )

    def record_identify_result(
        self,
        *,
        status: str,
        title: str = "",
        confidence: float | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE runtime_status
                SET last_identify_at = ?,
                    last_identify_status = ?,
                    last_identify_title = ?,
                    last_identify_confidence = ?
                WHERE singleton = 1
                """,
                (
                    int(time.time() * 1000),
                    status[:50],
                    title[:300],
                    confidence,
                ),
            )
