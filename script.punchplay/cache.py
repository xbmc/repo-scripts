"""
cache.py — SQLite-backed persistence for PunchPlay Scrobble.

Two tables:
  identifier_cache   — maps file paths / Kodi item keys to resolved metadata
                        so repeated identification on every play event is avoided.
  pending_scrobbles  — offline queue; events written here when the network is
                        down, replayed on the next successful connection.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from typing import Any

import xbmc
import xbmcaddon
import xbmcvfs

_ADDON = xbmcaddon.Addon()
_DATA_DIR: str = xbmcvfs.translatePath(_ADDON.getAddonInfo("profile"))

# How long to keep identifier cache entries (7 days).
_CACHE_TTL = 7 * 24 * 3600


class Cache:
    def __init__(self) -> None:
        os.makedirs(_DATA_DIR, exist_ok=True)
        self._db_path = os.path.join(_DATA_DIR, "punchplay.db")
        self._init_db()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path, timeout=10)

    def _init_db(self) -> None:
        with self._connect() as conn:
            # Enable WAL mode once — it persists across connections.
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS identifier_cache (
                    key        TEXT    PRIMARY KEY,
                    data       TEXT    NOT NULL,
                    created_at INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS pending_scrobbles (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    endpoint   TEXT    NOT NULL,
                    payload    TEXT    NOT NULL,
                    created_at INTEGER NOT NULL
                );
                """
            )

    # ------------------------------------------------------------------
    # Identifier cache
    # ------------------------------------------------------------------

    def get_identifier(self, key: str) -> dict[str, Any] | None:
        """Return cached metadata for *key*, or None if missing/stale."""
        cutoff = int(time.time()) - _CACHE_TTL
        with self._connect() as conn:
            row = conn.execute(
                "SELECT data FROM identifier_cache WHERE key = ? AND created_at >= ?",
                (key, cutoff),
            ).fetchone()
        if row:
            try:
                return json.loads(row[0])
            except Exception:
                return None
        return None

    def set_identifier(self, key: str, data: dict[str, Any]) -> None:
        """Cache *data* under *key*, overwriting any previous entry."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO identifier_cache (key, data, created_at)
                VALUES (?, ?, ?)
                """,
                (key, json.dumps(data), int(time.time())),
            )

    def prune_identifier_cache(self) -> None:
        """Delete stale cache entries older than TTL."""
        cutoff = int(time.time()) - _CACHE_TTL
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM identifier_cache WHERE created_at < ?", (cutoff,)
            )

    # ------------------------------------------------------------------
    # Offline scrobble queue
    # ------------------------------------------------------------------

    # Maximum events held in the offline queue — oldest dropped when full.
    _MAX_QUEUE = 200

    def enqueue_scrobble(self, endpoint: str, payload: dict[str, Any]) -> None:
        """Persist a failed scrobble event for later replay."""
        with self._connect() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM pending_scrobbles"
            ).fetchone()[0]
            if count >= self._MAX_QUEUE:
                conn.execute(
                    "DELETE FROM pending_scrobbles WHERE id = "
                    "(SELECT id FROM pending_scrobbles ORDER BY id LIMIT 1)"
                )
            conn.execute(
                """
                INSERT INTO pending_scrobbles (endpoint, payload, created_at)
                VALUES (?, ?, ?)
                """,
                (endpoint, json.dumps(payload), int(time.time())),
            )
        xbmc.log(
            f"[PunchPlay] Queued offline scrobble → {endpoint}", xbmc.LOGDEBUG
        )

    def get_pending_scrobbles(self) -> list[tuple[int, str, dict[str, Any]]]:
        """Return all pending scrobbles ordered by insertion time."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, endpoint, payload FROM pending_scrobbles ORDER BY id"
            ).fetchall()
        return [(row[0], row[1], json.loads(row[2])) for row in rows]

    def delete_pending_scrobble(self, scrobble_id: int) -> None:
        """Remove a successfully replayed scrobble from the queue."""
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM pending_scrobbles WHERE id = ?", (scrobble_id,)
            )

