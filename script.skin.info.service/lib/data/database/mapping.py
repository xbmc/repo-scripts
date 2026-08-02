"""Cross-provider ID mapping table for instant ID lookups."""
from __future__ import annotations

from typing import Dict, Optional

from lib.data.database._infrastructure import get_db, chunked_in_query


def save_id_mapping(
    tmdb_id: str,
    media_type: str,
    imdb_id: Optional[str] = None,
    tvdb_id: Optional[str] = None,
) -> None:
    """Store or update an ID mapping from TMDB data."""
    if not tmdb_id or not media_type:
        return
    with get_db() as cursor:
        cursor.execute(
            """INSERT INTO id_mappings (tmdb_id, media_type, imdb_id, tvdb_id)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(tmdb_id, media_type) DO UPDATE SET
                   imdb_id = COALESCE(excluded.imdb_id, imdb_id),
                   tvdb_id = COALESCE(excluded.tvdb_id, tvdb_id),
                   updated_at = CURRENT_TIMESTAMP""",
            (tmdb_id, media_type, imdb_id or None, tvdb_id or None),
        )


def _lookup(select_col: str, where_col: str, value: str, media_type: str) -> Optional[str]:
    """Single-column ID lookup keyed by `where_col` + media_type."""
    with get_db() as cursor:
        cursor.execute(
            f"SELECT {select_col} FROM id_mappings WHERE {where_col} = ? AND media_type = ?",
            (value, media_type),
        )
        row = cursor.fetchone()
        return row[select_col] if row and row[select_col] else None


def get_imdb_id(tmdb_id: str, media_type: str) -> Optional[str]:
    """Look up imdb_id from tmdb_id."""
    return _lookup("imdb_id", "tmdb_id", tmdb_id, media_type)


def get_imdb_ids_batch(tmdb_ids: set, media_type: str) -> Dict[str, str]:
    """Look up imdb_ids for multiple tmdb_ids; chunked to stay under SQLite's parameter limit."""
    if not tmdb_ids:
        return {}
    results: Dict[str, str] = {}
    sql = (
        "SELECT tmdb_id, imdb_id FROM id_mappings "
        "WHERE media_type = ? AND tmdb_id IN ({placeholders})"
    )
    with get_db() as cursor:
        for row in chunked_in_query(cursor, sql, [media_type], list(tmdb_ids)):
            if row["imdb_id"]:
                results[row["tmdb_id"]] = row["imdb_id"]
    return results


def get_tmdb_id_by_imdb(imdb_id: str, media_type: str) -> Optional[str]:
    """Look up tmdb_id from imdb_id."""
    return _lookup("tmdb_id", "imdb_id", imdb_id, media_type)


def get_tmdb_id_by_tvdb(tvdb_id: str, media_type: str) -> Optional[str]:
    """Look up tmdb_id from tvdb_id."""
    return _lookup("tmdb_id", "tvdb_id", tvdb_id, media_type)
