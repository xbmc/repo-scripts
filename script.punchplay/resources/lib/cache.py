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
    MAX_QUEUE_ATTEMPTS,
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
                    event_created_at INTEGER,
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
                    last_identify_confidence   REAL,
                    last_pull_sync_at          INTEGER,
                    last_pull_sync_summary     TEXT,
                    pull_sync_held_runs        INTEGER,
                    pull_sync_failure_counts   TEXT,
                    pull_sync_context          TEXT
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
            self._migrate_rating_suppression_keys(conn)

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
        if "event_created_at" not in existing_columns:
            # Replay order must follow when each event actually happened, not
            # the order it was written to this table — a later event can be
            # persisted here before an earlier one that was still in flight
            # (e.g. a slow request abandoned at Kodi shutdown). Backfill from
            # created_at for pre-existing rows, which predate this column and
            # have no better timestamp available.
            conn.execute(
                "ALTER TABLE pending_scrobbles "
                "ADD COLUMN event_created_at INTEGER"
            )
            conn.execute(
                "UPDATE pending_scrobbles SET event_created_at = created_at "
                "WHERE event_created_at IS NULL"
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
            ("last_pull_sync_at", "INTEGER"),
            ("last_pull_sync_summary", "TEXT"),
            ("pull_sync_held_runs", "INTEGER"),
            ("pull_sync_failure_counts", "TEXT"),
            ("pull_sync_context", "TEXT"),
        ):
            if column_name not in existing_columns:
                if not column_name.replace("_", "").isalnum():
                    raise ValueError(f"Invalid column name: {column_name}")
                if column_type.upper() not in _VALID_TYPES:
                    raise ValueError(f"Invalid column type: {column_type}")
                conn.execute(
                    f"ALTER TABLE runtime_status ADD COLUMN {column_name} {column_type}"
                )

    def _migrate_rating_suppression_keys(self, conn: sqlite3.Connection) -> None:
        """One-time cleanup for the 1.5.2 show-suppression key format
        change: `show:{id-or-title}:{title}:{year}` -> `show:{title}`.

        The old key varied almost as much per episode as the field it
        replaced (an episode-level id or year, not a show-level one), so
        rows written under it rarely matched reliably in the first place.
        There's no safe way to rewrite an old key into the new format when
        a title itself may contain colons, so old rows are cleared rather
        than migrated — the user re-suppresses if they still want to.

        Gated on PRAGMA user_version so this runs exactly once rather than
        on every launch (a real show:{title} key can itself contain extra
        colons if the title does, and would otherwise match the old
        format's pattern forever).
        """
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        if version >= 1:
            return
        deleted = conn.execute(
            "DELETE FROM rating_suppressions WHERE key GLOB 'show:*:*:*'"
        ).rowcount
        if deleted:
            xbmc.log(
                f"[PunchPlay] Cleared {deleted} rating suppression(s) from "
                "the old show-key format",
                xbmc.LOGINFO,
            )
        conn.execute("PRAGMA user_version = 1")

    def _drop_expired_pending_scrobbles_locked(
        self,
        conn: sqlite3.Connection,
    ) -> int:
        cutoff = int(time.time()) - QUEUE_ENTRY_MAX_AGE_SECS
        cur = conn.execute(
            "DELETE FROM pending_scrobbles WHERE created_at < ?",
            (cutoff,),
        )
        dropped = max(cur.rowcount or 0, 0)
        cur = conn.execute(
            "DELETE FROM pending_scrobbles WHERE attempt_count >= ?",
            (MAX_QUEUE_ATTEMPTS,),
        )
        return dropped + max(cur.rowcount or 0, 0)

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
        self.enqueue_scrobbles([(endpoint, payload)])

    def enqueue_scrobbles(self, items: list[tuple[str, dict[str, Any]]]) -> None:
        """Batched form of enqueue_scrobble — one connection/transaction for
        several events, so draining several unsent posts at once (e.g. Kodi
        shutdown) doesn't reconnect per item."""
        if not items:
            return
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
            for endpoint, payload in items:
                while count >= OFFLINE_QUEUE_MAX_ITEMS:
                    if not self._drop_one_low_value_pending_scrobble_locked(conn):
                        break
                    count -= 1

                event_created_at = payload.get("event_created_at")
                if not isinstance(event_created_at, int):
                    event_created_at = now * 1000

                conn.execute(
                    """
                    INSERT INTO pending_scrobbles (
                        endpoint,
                        payload,
                        created_at,
                        event_created_at,
                        attempt_count,
                        last_attempt_at,
                        last_error
                    )
                    VALUES (?, ?, ?, ?, 0, NULL, NULL)
                    """,
                    (endpoint, json.dumps(payload), now, event_created_at),
                )
                count += 1

        xbmc.log(f"[PunchPlay] Queued {len(items)} offline scrobble(s)", xbmc.LOGDEBUG)

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
                ORDER BY event_created_at, id
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

    def pending_scrobble_exists(self, scrobble_id: int) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM pending_scrobbles WHERE id = ?",
                (scrobble_id,),
            ).fetchone()
        return row is not None

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

    def clear_rating_suppressions(self) -> int:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM rating_suppressions")
        return max(cur.rowcount or 0, 0)

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
                    last_identify_confidence,
                    last_pull_sync_at,
                    last_pull_sync_summary,
                    pull_sync_held_runs
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
            "last_pull_sync_at": row[10],
            "last_pull_sync_summary": row[11],
            "pull_sync_held_runs": row[12] or 0,
        }

    def set_account_username(self, username: str | None) -> None:
        with self._connect() as conn:
            current = conn.execute(
                "SELECT account_username FROM runtime_status WHERE singleton = 1"
            ).fetchone()
            account_changed = (
                username is None
                or current is None
                or current[0] != username
            )
            if account_changed:
                conn.execute(
                    """
                    UPDATE runtime_status
                    SET account_username = ?,
                        last_pull_sync_at = NULL,
                        last_pull_sync_summary = NULL,
                        pull_sync_held_runs = 0,
                        pull_sync_failure_counts = NULL,
                        pull_sync_context = NULL
                    WHERE singleton = 1
                    """,
                    (username,),
                )
                return
            conn.execute(
                "UPDATE runtime_status SET account_username = ? WHERE singleton = 1",
                (username,),
            )

    def ensure_pull_sync_context(self, context: str) -> bool:
        """Reset incremental state when the enabled sync halves change.

        Returns True when *context* already matched, False when a full sync is
        now required.
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT pull_sync_context FROM runtime_status WHERE singleton = 1"
            ).fetchone()
            if row and row[0] == context:
                return True
            conn.execute(
                """
                UPDATE runtime_status
                SET pull_sync_context = ?,
                    last_pull_sync_at = NULL,
                    last_pull_sync_summary = NULL,
                    pull_sync_held_runs = 0,
                    pull_sync_failure_counts = NULL
                WHERE singleton = 1
                """,
                (context,),
            )
        return False

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

    def record_pull_sync(self, summary: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE runtime_status
                SET last_pull_sync_at = ?,
                    last_pull_sync_summary = ?,
                    pull_sync_held_runs = 0,
                    pull_sync_failure_counts = NULL
                WHERE singleton = 1
                """,
                (int(time.time() * 1000), summary[:300]),
            )

    def clear_pull_sync_checkpoint(self) -> None:
        """Force the next automatic pull to run without a `since` filter.

        Failure counters are deliberately preserved: clearing the timestamp
        changes what the next run fetches, while the held-run policy still
        decides when a persistently bad item may stop blocking progress.
        """
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE runtime_status
                SET last_pull_sync_at = NULL
                WHERE singleton = 1
                """
            )

    def record_pull_sync_held(self, failed_items: set[str]) -> int:
        """Record one failed pull run and return its minimum retry count.

        Counts are consecutive per failed-item identity. Items that succeeded
        on this run are removed, while newly failing items start at one, so an
        unrelated failure cannot inherit another item's exhausted allowance.
        `record_pull_sync` clears the state after a clean run or intentional
        checkpoint advance.
        """
        if not failed_items:
            # Defensive fallback for callers that only have an aggregate
            # failure count (primarily old tests or third-party integrations).
            failed_items = {"unknown-apply-failure"}
        with self._connect() as conn:
            row = conn.execute(
                "SELECT pull_sync_failure_counts FROM runtime_status "
                "WHERE singleton = 1"
            ).fetchone()
            previous: dict[str, int] = {}
            if row and row[0]:
                try:
                    decoded = json.loads(row[0])
                    if isinstance(decoded, dict):
                        previous = {
                            str(key): max(0, int(value))
                            for key, value in decoded.items()
                        }
                except (TypeError, ValueError):
                    previous = {}

            current = {
                item: previous.get(item, 0) + 1
                for item in sorted(failed_items)
            }
            held_runs = min(current.values())
            conn.execute(
                """
                UPDATE runtime_status
                SET pull_sync_held_runs = ?,
                    pull_sync_failure_counts = ?
                WHERE singleton = 1
                """,
                (held_runs, json.dumps(current, sort_keys=True)),
            )
        return held_runs

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
