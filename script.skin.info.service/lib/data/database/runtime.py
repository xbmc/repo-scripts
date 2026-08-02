"""TV show / season runtime cache (storage CRUD)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Tuple

from lib.data.database._infrastructure import get_db


def get_show_runtime(tvshowid: int) -> Optional[Tuple[int, int]]:
    """Return (total_runtime_seconds, avg_episode_runtime_seconds) or None if not cached."""
    with get_db() as cursor:
        cursor.execute(
            "SELECT total_runtime, avg_episode_runtime FROM tvshow_runtime_cache "
            "WHERE tvshowid = ? AND season = 0",
            (tvshowid,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return row["total_runtime"], row["avg_episode_runtime"]


def get_season_runtime(tvshowid: int, season: int) -> Optional[int]:
    """Return total_runtime_seconds for a season, or None if not cached."""
    with get_db() as cursor:
        cursor.execute(
            "SELECT total_runtime FROM tvshow_runtime_cache "
            "WHERE tvshowid = ? AND season = ?",
            (tvshowid, season),
        )
        row = cursor.fetchone()
        return row["total_runtime"] if row else None


def save_show_runtime(tvshowid: int, total: int, avg: int, episode_count: int) -> None:
    with get_db() as cursor:
        cursor.execute(
            "INSERT OR REPLACE INTO tvshow_runtime_cache "
            "(tvshowid, season, total_runtime, avg_episode_runtime, episode_count, synced_at) "
            "VALUES (?, 0, ?, ?, ?, ?)",
            (tvshowid, total, avg, episode_count, datetime.now().isoformat()),
        )


def save_season_runtime(tvshowid: int, season: int, total: int, episode_count: int) -> None:
    with get_db() as cursor:
        cursor.execute(
            "INSERT OR REPLACE INTO tvshow_runtime_cache "
            "(tvshowid, season, total_runtime, avg_episode_runtime, episode_count, synced_at) "
            "VALUES (?, ?, ?, 0, ?, ?)",
            (tvshowid, season, total, episode_count, datetime.now().isoformat()),
        )


def invalidate_show_runtime(tvshowid: int) -> None:
    """Drop all cached runtime entries for a show (whole + every season)."""
    with get_db() as cursor:
        cursor.execute("DELETE FROM tvshow_runtime_cache WHERE tvshowid = ?", (tvshowid,))


def clear_all_runtime_cache() -> None:
    """Drop every cached runtime entry."""
    with get_db() as cursor:
        cursor.execute("DELETE FROM tvshow_runtime_cache")
