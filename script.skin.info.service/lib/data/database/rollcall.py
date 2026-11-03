"""DBID rollcall: tracks valid Kodi library DBIDs and cleans up stale references."""
from __future__ import annotations

import sqlite3
import time
from typing import Dict, Iterable, List, NamedTuple, Optional, Set, Tuple, Final

import xbmc

from lib.data.database._infrastructure import (
    DB_PATH,
    as_int,
    get_db,
    chunked_in_query,
    chunked_in_modify as _chunked_delete,
)
from lib.kodi.client import log


_DEPENDENT_TABLES: Dict[str, Tuple[Optional[str], str]] = {
    "art_queue": ("media_type", "dbid"),
    "slideshow_pool": ("media_type", "dbid"),
    "imdb_sync": ("media_type", "dbid"),
    "tvshow_runtime": (None, "tvshowid"),
}


class _Item(NamedTuple):
    """One library row as Kodi reports it."""
    title: str
    content_key: str
    imdb_id: Optional[str]
    tmdb_id: Optional[int]
    tvdb_id: Optional[int]
    mbid: Optional[str]
    parent_dbid: Optional[int]
    season: Optional[int]
    episode: Optional[int]


def _build_content_key(uniqueid: dict) -> str:
    """Reuse detector: the first id Kodi offers, prefixed by its source."""
    for source in ("imdb", "tmdb", "tvdb"):
        val = uniqueid.get(source)
        if val:
            return f"{source}:{val}"
    for source, val in uniqueid.items():
        if val:
            return f"{source}:{val}"
    return ""


_PAGE_SIZE: Final = 5000
_UPSERT_LIBRARY_ITEM: Final = (
    "INSERT INTO library_item (media_type, dbid, title, imdb_id, tmdb_id, tvdb_id, "
    "mbid, parent_dbid, season, episode, content_key, updated_at) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
    "ON CONFLICT (media_type, dbid) DO UPDATE SET "
    "title = excluded.title, imdb_id = excluded.imdb_id, tmdb_id = excluded.tmdb_id, "
    "tvdb_id = excluded.tvdb_id, mbid = excluded.mbid, "
    "parent_dbid = excluded.parent_dbid, season = excluded.season, "
    "episode = excluded.episode, content_key = excluded.content_key, "
    "updated_at = excluded.updated_at"
)


def _fetch_paginated(method: str, result_key: str, properties: Optional[list] = None,
                     abort_flag=None) -> Optional[list]:
    """Fetch every item of a paged library call; None on a failed page or abort, never partial."""
    from lib.kodi.client import request

    items: list = []
    start = 0
    while True:
        if abort_flag and abort_flag.is_requested():
            return None
        params: dict = {"limits": {"start": start, "end": start + _PAGE_SIZE}}
        if properties:
            params["properties"] = properties
        resp = request(method, params)
        if not resp:
            return None
        result = resp.get("result") or {}
        page = result.get(result_key) or []
        if not page:
            break
        items.extend(page)
        total = (result.get("limits") or {}).get("total")
        if total is not None and len(items) >= total:
            break
        if len(page) < _PAGE_SIZE:
            break
        start += _PAGE_SIZE
    return items


_LIBRARY_SOURCES = [
    ("movie",   "VideoLibrary.GetMovies",   "movies",   "movieid",
     ["title", "uniqueid"]),
    ("tvshow",  "VideoLibrary.GetTVShows",  "tvshows",  "tvshowid",
     ["title", "uniqueid"]),
    ("episode", "VideoLibrary.GetEpisodes", "episodes", "episodeid",
     ["title", "uniqueid", "season", "episode", "tvshowid"]),
    ("artist",  "AudioLibrary.GetArtists",  "artists",  "artistid",
     ["musicbrainzartistid"]),
]


def _fetch_library_dbids(abort_flag=None) -> Dict[str, Dict[int, _Item]]:
    """Fetch every library DBID per media type; a type that fails is left out, {} on abort."""
    snapshot: Dict[str, Dict[int, _Item]] = {}

    for media_type, method, result_key, id_field, properties in _LIBRARY_SOURCES:
        items = _fetch_paginated(method, result_key, properties, abort_flag)
        if abort_flag and abort_flag.is_requested():
            return {}
        if items is None:
            log("Database", f"DBID sync: {media_type} fetch failed, leaving its rows alone",
                xbmc.LOGWARNING)
            continue
        snapshot[media_type] = {}
        for item in items:
            if media_type == "artist":
                title = item.get("label") or ""
                mbid = item.get("musicbrainzartistid") or None
                if isinstance(mbid, list):
                    mbid = mbid[0] if mbid else None
                record = _Item(title, f"name:{title}", None, None, None, mbid, None, None, None)
            else:
                uniqueid = item.get("uniqueid") or {}
                record = _Item(
                    item.get("title", ""),
                    _build_content_key(uniqueid),
                    uniqueid.get("imdb") or None,
                    as_int(uniqueid.get("tmdb")),
                    as_int(uniqueid.get("tvdb")),
                    None,
                    # a tvshow item carries its own id in tvshowid
                    as_int(item.get("tvshowid")) if media_type == "episode" else None,
                    item.get("season") if media_type == "episode" else None,
                    item.get("episode") if media_type == "episode" else None,
                )
            snapshot[media_type][item[id_field]] = record

    return snapshot


def _cleanup_stale_dbids(
    cursor, media_type: str, dbids: Set[int]
) -> Dict[str, int]:
    """Clean up stale DBIDs in every dependent table, returning the nonzero counts per table."""
    if not dbids:
        return {}
    stats: Dict[str, int] = {}
    dbid_list = sorted(dbids)
    for table, (type_col, id_col) in _DEPENDENT_TABLES.items():
        if type_col is None:
            if media_type != "tvshow":
                continue
            sql = f"DELETE FROM {table} WHERE {id_col} IN ({{placeholders}})"
            stats[table] = _chunked_delete(cursor, sql, [], dbid_list)
        else:
            sql = f"DELETE FROM {table} WHERE {type_col} = ? AND {id_col} IN ({{placeholders}})"
            stats[table] = _chunked_delete(cursor, sql, [media_type], dbid_list)
    return {k: v for k, v in stats.items() if v > 0}


def _cleanup_stale_titles(cursor, media_type: str, tmdb_ids: Set[int]) -> None:
    """Clean up departed items' TMDB titles and online props unless a library row uses them."""
    if media_type not in ("movie", "tvshow") or not tmdb_ids:
        return
    # a survivor can reach the same title through its imdb or tvdb id instead
    still_used = {
        row["tmdb_id"] for row in chunked_in_query(
            cursor,
            "SELECT t.tmdb_id FROM tmdb_title t JOIN library_item li "
            "ON li.media_type = t.media_type AND (li.tmdb_id = t.tmdb_id "
            "OR li.imdb_id = t.imdb_id OR li.tvdb_id = t.tvdb_id) "
            "WHERE t.media_type = ? AND t.tmdb_id IN ({placeholders})",
            [media_type], sorted(tmdb_ids))
    }
    ids = sorted(tmdb_ids - still_used)
    if not ids:
        return
    _chunked_delete(
        cursor,
        "DELETE FROM tmdb_title WHERE media_type = ? AND tmdb_id IN ({placeholders})",
        [media_type], ids)
    _chunked_delete(
        cursor,
        "DELETE FROM online_props WHERE media_type = ? AND item_id IN ({placeholders})",
        [media_type], [str(i) for i in ids])


# a title row with no status yet is only an id mapping, still waiting for its first fetch
_AIRING: Final = "(t.status IS NULL OR t.status NOT IN ('Ended', 'Canceled'))"


def get_airing_shows() -> List[Dict]:
    """Get library shows not ended or canceled, with TMDB schedule and expiry, by next air date."""
    with get_db(DB_PATH) as cursor:
        cursor.execute(
            # a show scraped from TVDB or IMDb has no tmdb_id to join on
            "SELECT t.tmdb_id, t.imdb_id, t.title, t.status, t.next_air_date, t.expires_at, "
            "li.dbid AS tvshowid FROM library_item li "
            "JOIN tmdb_title t ON t.media_type = 'tvshow' AND t.tmdb_id = li.tmdb_id "
            f"WHERE li.media_type = 'tvshow' AND li.tmdb_id IS NOT NULL AND {_AIRING} "
            "UNION "
            "SELECT t.tmdb_id, t.imdb_id, t.title, t.status, t.next_air_date, t.expires_at, "
            "li.dbid AS tvshowid FROM library_item li "
            "JOIN tmdb_title t ON t.media_type = 'tvshow' AND t.imdb_id = li.imdb_id "
            "WHERE li.media_type = 'tvshow' AND li.tmdb_id IS NULL AND li.imdb_id IS NOT NULL "
            f"AND {_AIRING} "
            "UNION "
            "SELECT t.tmdb_id, t.imdb_id, t.title, t.status, t.next_air_date, t.expires_at, "
            "li.dbid AS tvshowid FROM library_item li "
            "JOIN tmdb_title t ON t.media_type = 'tvshow' AND t.tvdb_id = li.tvdb_id "
            "WHERE li.media_type = 'tvshow' AND li.tmdb_id IS NULL AND li.imdb_id IS NULL "
            f"AND li.tvdb_id IS NOT NULL AND {_AIRING} "
            "ORDER BY next_air_date"
        )
        return [
            {
                "tmdb_id": str(row["tmdb_id"]),
                "imdb_id": row["imdb_id"] or "",
                "title": row["title"] or "",
                "status": row["status"] or "",
                "next_air_date": row["next_air_date"] or "",
                "expires_at": row["expires_at"],
                "tvshowid": row["tvshowid"],
            }
            for row in cursor.fetchall()
        ]


def sync_dbids(abort_flag=None) -> Dict[str, Dict[str, int]]:
    """Sync the DBID registry with the Kodi library; change counts per media type, {} if none."""
    snapshot = _fetch_library_dbids(abort_flag)
    now = int(time.time())
    results: Dict[str, Dict[str, int]] = {}

    with get_db(DB_PATH) as cursor:
        for media_type, library_items in snapshot.items():
            if abort_flag and abort_flag.is_requested():
                break
            cursor.execute(
                "SELECT dbid, content_key, tmdb_id FROM library_item WHERE media_type = ?",
                (media_type,),
            )
            existing = {
                row["dbid"]: (row["content_key"] or "", row["tmdb_id"])
                for row in cursor.fetchall()
            }

            library_dbids = set(library_items.keys())
            registry_dbids = set(existing.keys())

            gone = registry_dbids - library_dbids
            new = library_dbids - registry_dbids
            common = registry_dbids & library_dbids

            reused: Set[int] = set()
            for dbid in common:
                old_key = existing[dbid][0]
                new_key = library_items[dbid].content_key
                if old_key and new_key and old_key != new_key:
                    reused.add(dbid)

            stale = gone | reused
            departed_tmdb_ids = {existing[dbid][1] for dbid in stale if existing[dbid][1]}
            if stale:
                cleanup = _cleanup_stale_dbids(cursor, media_type, stale)
                if cleanup:
                    log("Database", f"DBID sync cleanup ({media_type}): {cleanup}", xbmc.LOGDEBUG)

            if gone:
                _chunked_delete(
                    cursor,
                    "DELETE FROM library_item WHERE media_type = ? AND dbid IN ({placeholders})",
                    [media_type],
                    sorted(gone),
                )

            drifted = [
                dbid for dbid in common - reused
                if existing[dbid][1] != library_items[dbid].tmdb_id
            ]
            write = sorted(new) + sorted(reused) + sorted(drifted)
            if write:
                cursor.executemany(_UPSERT_LIBRARY_ITEM, [
                    (media_type, dbid, i.title, i.imdb_id, i.tmdb_id, i.tvdb_id, i.mbid,
                     i.parent_dbid, i.season, i.episode, i.content_key, now)
                    for dbid, i in ((d, library_items[d]) for d in write)
                ])

            # after the upsert, when a re-scraped id is present again
            _cleanup_stale_titles(cursor, media_type, departed_tmdb_ids)

            stats = {
                "added": len(new),
                "removed": len(gone),
                "reused": len(reused),
                "ids": len(drifted),
            }
            if any(v > 0 for v in stats.values()):
                results[media_type] = stats

    if abort_flag and abort_flag.is_requested():
        return results
    if results:
        parts = []
        for mt, s in sorted(results.items()):
            changes = ", ".join(f"{v} {k}" for k, v in s.items() if v > 0)
            parts.append(f"{mt}: {changes}")
        log("Database", f"DBID sync: {'; '.join(parts)}", xbmc.LOGINFO)
    else:
        log("Database", "DBID sync: no changes", xbmc.LOGDEBUG)

    return results


def needs_id_backfill() -> bool:
    """True when the DBID registry is still empty."""
    with get_db(DB_PATH) as cursor:
        cursor.execute("SELECT 1 FROM library_item LIMIT 1")
        return cursor.fetchone() is None


def get_dbids_by_tmdb(media_type: str, tmdb_ids: Iterable) -> Dict[str, int]:
    """Get the library DBIDs for TMDB ids of one media type; ids not in the library are left out."""
    wanted = set()
    for tmdb_id in tmdb_ids:
        try:
            if tmdb_id:
                wanted.add(int(tmdb_id))
        except (TypeError, ValueError):
            continue
    if not wanted:
        return {}

    sql = (
        "SELECT tmdb_id, dbid FROM library_item "
        "WHERE media_type = ? AND tmdb_id IN ({placeholders})"
    )
    try:
        with get_db(DB_PATH) as cursor:
            # the column is INTEGER; callers key on the string form
            return {
                str(row["tmdb_id"]): row["dbid"]
                for row in chunked_in_query(cursor, sql, [media_type], sorted(wanted))
            }
    except sqlite3.OperationalError as e:
        # plugin and script entries never run init_database
        expected = "no such table" in str(e)
        log("Database", f"DBID registry lookup failed: {e}",
            xbmc.LOGDEBUG if expected else xbmc.LOGWARNING)
        return {}


def remove_dbid(media_type: str, dbid: int) -> None:
    """Remove a single DBID from registry and all dependent tables."""
    with get_db(DB_PATH) as cursor:
        for table, (type_col, id_col) in _DEPENDENT_TABLES.items():
            if type_col is None:
                if media_type != "tvshow":
                    continue
                cursor.execute(f"DELETE FROM {table} WHERE {id_col} = ?", (dbid,))
            else:
                cursor.execute(
                    f"DELETE FROM {table} WHERE {type_col} = ? AND {id_col} = ?",
                    (media_type, dbid),
                )
        cursor.execute(
            "DELETE FROM library_item WHERE media_type = ? AND dbid = ?",
            (media_type, dbid),
        )
