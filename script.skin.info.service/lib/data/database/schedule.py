"""TV schedule database operations for airing show tracking."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from lib.data.database._infrastructure import DB_PATH, get_db


def _ep_fields(ep: Optional[dict]) -> tuple:
    """Extract `(air_date, name, season_number, episode_number)` from a TMDB episode dict.

    Text fields fall back to "" (empty); numeric fields fall back to None.
    """
    if not ep:
        return ("", "", None, None)
    return (
        ep.get("air_date") or "",
        ep.get("name") or "",
        ep.get("season_number"),
        ep.get("episode_number"),
    )


def upsert_schedule(
    tmdb_id: str,
    tvshowid: int,
    title: str,
    status: str,
    next_ep: Optional[dict] = None,
    last_ep: Optional[dict] = None,
) -> None:
    """Insert or update a TV show's schedule entry from TMDB data."""
    next_air, next_title, next_season, next_number = _ep_fields(next_ep)
    last_air, last_title, last_season, last_number = _ep_fields(last_ep)
    with get_db(DB_PATH) as cursor:
        cursor.execute('''
            INSERT OR REPLACE INTO tv_schedule (
                tmdb_id, tvshowid, title, status,
                next_episode_air_date, next_episode_title,
                next_episode_season, next_episode_number,
                last_episode_air_date, last_episode_title,
                last_episode_season, last_episode_number,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            tmdb_id, tvshowid, title, status,
            next_air, next_title, next_season, next_number,
            last_air, last_title, last_season, last_number,
            datetime.now().isoformat(),
        ))


def get_all_schedule() -> List[Dict]:
    """Get all schedule entries."""
    with get_db(DB_PATH) as cursor:
        cursor.execute('SELECT * FROM tv_schedule ORDER BY next_episode_air_date ASC')
        return [dict(row) for row in cursor.fetchall()]


def remove_schedule(tmdb_id: str) -> None:
    """Remove a show from the schedule."""
    with get_db(DB_PATH) as cursor:
        cursor.execute('DELETE FROM tv_schedule WHERE tmdb_id = ?', (tmdb_id,))
