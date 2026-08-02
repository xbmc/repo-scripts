"""DBID rollcall: tracks valid Kodi library DBIDs and cleans up stale references."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional, Set, Tuple

import xbmc

from lib.data.database._infrastructure import DB_PATH, get_db, chunked_in_modify as _chunked_delete
from lib.kodi.client import log


_DEPENDENT_TABLES: Dict[str, Tuple[Optional[str], str]] = {
    "art_queue": ("media_type", "dbid"),
    "slideshow_pool": ("media_type", "dbid"),
    "ratings_synced": ("media_type", "dbid"),
    "tv_schedule": (None, "tvshowid"),
}

def _build_content_id(uniqueid: dict) -> str:
    """Build a content_id string from Kodi uniqueid dict.

    Priority: imdb > tmdb > tvdb > first available.
    """
    for source in ("imdb", "tmdb", "tvdb"):
        val = uniqueid.get(source)
        if val:
            return f"{source}:{val}"
    for source, val in uniqueid.items():
        if val:
            return f"{source}:{val}"
    return ""


_PAGE_SIZE = 5000


def _fetch_paginated(method: str, result_key: str, properties: Optional[list] = None) -> list:
    """Fetch all items from a JSON-RPC library call, paginating to avoid silent truncation."""
    from lib.kodi.client import request

    items: list = []
    start = 0
    while True:
        params: dict = {"limits": {"start": start, "end": start + _PAGE_SIZE}}
        if properties:
            params["properties"] = properties
        resp = request(method, params)
        if not resp:
            break
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
    # (media_type, method, result_key, id_field, has_uniqueid)
    ("movie",   "VideoLibrary.GetMovies",   "movies",   "movieid",   True),
    ("tvshow",  "VideoLibrary.GetTVShows",  "tvshows",  "tvshowid",  True),
    ("episode", "VideoLibrary.GetEpisodes", "episodes", "episodeid", True),
    ("artist",  "AudioLibrary.GetArtists",  "artists",  "artistid",  False),
]


def _fetch_library_dbids() -> Dict[str, Dict[int, Tuple[str, str]]]:
    """Snapshot all Kodi library DBIDs as `media_type -> {dbid: (title, content_id)}`."""
    snapshot: Dict[str, Dict[int, Tuple[str, str]]] = {}

    for media_type, method, result_key, id_field, has_uniqueid in _LIBRARY_SOURCES:
        properties = ["title", "uniqueid"] if has_uniqueid else None
        items = _fetch_paginated(method, result_key, properties)
        snapshot[media_type] = {}
        for item in items:
            if has_uniqueid:
                title = item.get("title", "")
                content_id = _build_content_id(item.get("uniqueid") or {})
            else:
                title = item.get("label") or ""
                content_id = f"name:{title}"
            snapshot[media_type][item[id_field]] = (title, content_id)

    return snapshot


def _cleanup_stale_dbids(
    cursor, media_type: str, dbids: Set[int]
) -> Dict[str, int]:
    """Delete stale DBIDs from all dependent tables."""
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


def sync_dbids() -> Dict[str, Dict[str, int]]:
    """Sync DBID registry with Kodi library.

    Returns `media_type -> {added, removed, reused}`. Empty dict when no changes.
    """
    snapshot = _fetch_library_dbids()
    now = datetime.now().isoformat()
    results: Dict[str, Dict[str, int]] = {}

    with get_db(DB_PATH) as cursor:
        for media_type, library_items in snapshot.items():
            cursor.execute(
                "SELECT dbid, title, content_id FROM dbid_registry WHERE media_type = ?",
                (media_type,),
            )
            existing = {
                row["dbid"]: (row["title"], row["content_id"] or "")
                for row in cursor.fetchall()
            }

            library_dbids = set(library_items.keys())
            registry_dbids = set(existing.keys())

            gone = registry_dbids - library_dbids
            new = library_dbids - registry_dbids
            common = registry_dbids & library_dbids

            reused: Set[int] = set()
            for dbid in common:
                old_content_id = existing[dbid][1]
                new_content_id = library_items[dbid][1]
                if old_content_id and new_content_id and old_content_id != new_content_id:
                    reused.add(dbid)

            stale = gone | reused
            if stale:
                cleanup = _cleanup_stale_dbids(cursor, media_type, stale)
                if cleanup:
                    log("Database", f"DBID sync cleanup ({media_type}): {cleanup}", xbmc.LOGDEBUG)

            if gone:
                _chunked_delete(
                    cursor,
                    "DELETE FROM dbid_registry WHERE media_type = ? AND dbid IN ({placeholders})",
                    [media_type],
                    sorted(gone),
                )

            for dbid in reused:
                title, content_id = library_items[dbid]
                cursor.execute(
                    "UPDATE dbid_registry SET title = ?, content_id = ?, updated_at = ? "
                    "WHERE media_type = ? AND dbid = ?",
                    (title, content_id, now, media_type, dbid),
                )

            if new:
                rows = [
                    (media_type, dbid, library_items[dbid][0], library_items[dbid][1], now)
                    for dbid in new
                ]
                cursor.executemany(
                    "INSERT INTO dbid_registry (media_type, dbid, title, content_id, updated_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    rows,
                )

            stats = {"added": len(new), "removed": len(gone), "reused": len(reused)}
            if any(v > 0 for v in stats.values()):
                results[media_type] = stats

    if results:
        parts = []
        for mt, s in sorted(results.items()):
            changes = ", ".join(f"{v} {k}" for k, v in s.items() if v > 0)
            parts.append(f"{mt}: {changes}")
        log("Database", f"DBID sync: {'; '.join(parts)}", xbmc.LOGINFO)
    else:
        log("Database", "DBID sync: no changes", xbmc.LOGDEBUG)

    return results


def get_valid_dbids(media_type: str) -> Set[int]:
    """Get all valid DBIDs for a media type from the registry."""
    with get_db(DB_PATH) as cursor:
        cursor.execute(
            "SELECT dbid FROM dbid_registry WHERE media_type = ?",
            (media_type,),
        )
        return {row["dbid"] for row in cursor.fetchall()}


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
            "DELETE FROM dbid_registry WHERE media_type = ? AND dbid = ?",
            (media_type, dbid),
        )


