"""Cached runtime totals for TV shows and their seasons."""
from __future__ import annotations

from typing import Optional, Tuple, Final

from lib.data.database._infrastructure import get_db

# season 0 is specials
_WHOLE_SHOW: Final = -1


def get_show_runtime(tvshowid: int,
                     episodes: Optional[int] = None) -> Optional[Tuple[int, int]]:
    """Get a show's total and average episode runtime in seconds; None if uncached or stale."""
    with get_db() as cursor:
        cursor.execute(
            "SELECT total, avg, episodes FROM tvshow_runtime WHERE tvshowid = ? AND season = ?",
            (tvshowid, _WHOLE_SHOW),
        )
        row = cursor.fetchone()
        if not row or (episodes is not None and row["episodes"] != episodes):
            return None
        return row["total"], row["avg"]


def get_season_runtime(tvshowid: int, season: int, episodes: Optional[int] = None) -> Optional[int]:
    """Get a season's total runtime in seconds; None if uncached or stale."""
    with get_db() as cursor:
        cursor.execute(
            "SELECT total, episodes FROM tvshow_runtime WHERE tvshowid = ? AND season = ?",
            (tvshowid, season),
        )
        row = cursor.fetchone()
        if not row or (episodes is not None and row["episodes"] != episodes):
            return None
        return row["total"]


def save_show_runtime(tvshowid: int, total: int, avg: int, episode_count: int) -> None:
    """Save a show's total and average runtime."""
    with get_db() as cursor:
        cursor.execute(
            "INSERT INTO tvshow_runtime (tvshowid, season, total, avg, episodes) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT (tvshowid, season) DO UPDATE SET "
            "total = excluded.total, avg = excluded.avg, episodes = excluded.episodes",
            (tvshowid, _WHOLE_SHOW, total, avg, episode_count),
        )


def save_season_runtime(tvshowid: int, season: int, total: int, episode_count: int) -> None:
    """Save one season's total runtime."""
    with get_db() as cursor:
        cursor.execute(
            "INSERT INTO tvshow_runtime (tvshowid, season, total, avg, episodes) "
            "VALUES (?, ?, ?, 0, ?) "
            "ON CONFLICT (tvshowid, season) DO UPDATE SET "
            "total = excluded.total, episodes = excluded.episodes",
            (tvshowid, season, total, episode_count),
        )


def invalidate_show_runtime(tvshowid: int) -> None:
    """Invalidate a show's cached runtimes, for the whole show and every season."""
    with get_db() as cursor:
        cursor.execute("DELETE FROM tvshow_runtime WHERE tvshowid = ?", (tvshowid,))


def clear_all_runtime_cache() -> None:
    """Clear every cached runtime entry."""
    with get_db() as cursor:
        cursor.execute("DELETE FROM tvshow_runtime")
