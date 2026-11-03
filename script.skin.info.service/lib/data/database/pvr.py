"""Live TV programmes matched to TMDB titles, an automatic one kept a month after last shown."""
from __future__ import annotations

import time
from typing import NamedTuple, Optional, Final

from lib.data.database._infrastructure import chunked_in_query, get_db

PVR_SCOPE: Final = "pvr"
KEEP_DAYS: Final = 30
RECHECK_DAYS: Final = 30
_DAY: Final = 86400


class PvrMatchKey(NamedTuple):
    """Identity of a programme match: the cleaned title, the EPG year and the movie or TV hint."""
    title_key: str
    year: int
    kind: str


class PvrMatch(NamedTuple):
    """A programme's TMDB title, with when it was last searched and shown; an id of 0 is none."""
    media_type: str
    tmdb_id: int
    checked_at: int
    last_seen: int
    manual: bool


def get_pvr_match(key: PvrMatchKey) -> Optional[PvrMatch]:
    """Get a programme's saved TMDB title, or None when none is saved."""
    with get_db() as cursor:
        cursor.execute(
            "SELECT media_type, tmdb_id, checked_at, last_seen, manual FROM pvr_match "
            "WHERE title_key = ? AND year = ? AND kind = ?", tuple(key))
        row = cursor.fetchone()
    if not row:
        return None
    return PvrMatch(row["media_type"], row["tmdb_id"], row["checked_at"], row["last_seen"],
                    bool(row["manual"]))


def save_pvr_match(key: PvrMatchKey, media_type: str, tmdb_id: int, manual: bool = False) -> None:
    """Save a programme's TMDB title, stamped as searched and shown now; a user's pick is manual."""
    now = int(time.time())
    with get_db() as cursor:
        cursor.execute(
            "INSERT INTO pvr_match "
            "(title_key, year, kind, media_type, tmdb_id, checked_at, last_seen, manual) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT (title_key, year, kind) DO UPDATE SET "
            "media_type = excluded.media_type, tmdb_id = excluded.tmdb_id, "
            "checked_at = excluded.checked_at, last_seen = excluded.last_seen, "
            "manual = excluded.manual",
            (*key, media_type, tmdb_id, now, now, int(manual)))


def touch_pvr_match(key: PvrMatchKey) -> None:
    """Touch a programme's match, stamping it as shown now."""
    with get_db() as cursor:
        cursor.execute(
            "UPDATE pvr_match SET last_seen = ? WHERE title_key = ? AND year = ? AND kind = ?",
            (int(time.time()), *key))


def needs_recheck(match: PvrMatch) -> bool:
    """True when an automatic match was last searched long enough ago to search again."""
    return not match.manual and time.time() - match.checked_at > RECHECK_DAYS * _DAY


def needs_touch(match: PvrMatch) -> bool:
    """True when the match was last stamped as shown over a day ago."""
    return time.time() - match.last_seen > _DAY


def prune_pvr_matches() -> int:
    """Prune automatic matches unshown for a month, with the props and payloads only they kept."""
    cutoff = int(time.time()) - KEEP_DAYS * _DAY
    with get_db() as cursor:
        cursor.execute(
            "SELECT DISTINCT media_type, tmdb_id FROM pvr_match "
            "WHERE last_seen < ? AND manual = 0", (cutoff,))
        dropped = {(row["media_type"], row["tmdb_id"]) for row in cursor.fetchall()}
        if not dropped:
            return 0
        cursor.execute("DELETE FROM pvr_match WHERE last_seen < ? AND manual = 0", (cutoff,))
        removed = cursor.rowcount
        cursor.execute("SELECT DISTINCT media_type, tmdb_id FROM pvr_match")
        orphaned = dropped - {(row["media_type"], row["tmdb_id"]) for row in cursor.fetchall()}
        cursor.executemany(
            "DELETE FROM online_props WHERE media_type = ? AND item_id = ? AND scope = ?",
            [(media_type, str(tmdb_id), PVR_SCOPE) for media_type, tmdb_id in orphaned])
        for media_type in {m for m, _ in orphaned}:
            ids = sorted(i for m, i in orphaned if m == media_type)
            in_library = {
                row["tmdb_id"] for row in chunked_in_query(
                    cursor,
                    "SELECT t.tmdb_id FROM tmdb_title t JOIN library_item li "
                    "ON li.media_type = t.media_type AND (li.tmdb_id = t.tmdb_id "
                    "OR li.imdb_id = t.imdb_id OR li.tvdb_id = t.tvdb_id) "
                    "WHERE t.media_type = ? AND t.tmdb_id IN ({placeholders})",
                    [media_type], ids)
            }
            cursor.executemany(
                "UPDATE tmdb_title SET data = X'' "
                "WHERE media_type = ? AND tmdb_id = ? AND LENGTH(data) > 0",
                [(media_type, i) for i in ids if i not in in_library])
    return removed
