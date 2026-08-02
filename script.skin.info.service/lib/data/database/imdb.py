"""IMDb dataset database operations for ratings, episodes, and metadata."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Generator, Callable

from lib.data.database._infrastructure import get_db


def _select_rating(cursor: sqlite3.Cursor, imdb_id: str) -> Optional[Dict[str, float | int]]:
    cursor.execute(
        "SELECT rating, votes FROM imdb_ratings WHERE imdb_id = ?",
        (imdb_id,)
    )
    row = cursor.fetchone()
    if row:
        return {"rating": row["rating"], "votes": row["votes"]}
    return None


def get_rating(imdb_id: str) -> Optional[Dict[str, float | int]]:
    """Return `{rating, votes}` for an IMDb ID, or None if not in the dataset."""
    with get_db() as cursor:
        return _select_rating(cursor, imdb_id)


def get_rating_with_cursor(imdb_id: str,
                           cursor: sqlite3.Cursor) -> Optional[Dict[str, float | int]]:
    """Same as `get_rating`, but uses a caller-provided cursor for shared-connection loops."""
    return _select_rating(cursor, imdb_id)


def get_ratings_batch(imdb_ids: List[str]) -> Dict[str, Dict[str, float | int]]:
    """Return `imdb_id -> {rating, votes}` for hits; chunks to stay under SQLite param limits."""
    if not imdb_ids:
        return {}

    from lib.data.database._infrastructure import chunked_in_query
    results: Dict[str, Dict[str, float | int]] = {}
    sql = "SELECT imdb_id, rating, votes FROM imdb_ratings WHERE imdb_id IN ({placeholders})"
    with get_db() as cursor:
        for row in chunked_in_query(cursor, sql, [], list(imdb_ids)):
            results[row["imdb_id"]] = {"rating": row["rating"], "votes": row["votes"]}
    return results


def _select_episode_imdb_id(
    cursor: sqlite3.Cursor, show_imdb_id: str, season: int, episode: int
) -> Optional[str]:
    cursor.execute(
        "SELECT episode_id FROM imdb_episodes WHERE parent_id = ? AND season = ? AND episode = ?",
        (show_imdb_id, season, episode)
    )
    row = cursor.fetchone()
    return row["episode_id"] if row else None


def get_episode_imdb_id(show_imdb_id: str, season: int, episode: int) -> Optional[str]:
    """Look up an episode's IMDb ID from the parent show ID and season/episode numbers."""
    with get_db() as cursor:
        return _select_episode_imdb_id(cursor, show_imdb_id, season, episode)


def get_episode_imdb_id_with_cursor(
    show_imdb_id: str, season: int, episode: int, cursor: sqlite3.Cursor
) -> Optional[str]:
    """Same as `get_episode_imdb_id`, but uses a caller-provided cursor."""
    return _select_episode_imdb_id(cursor, show_imdb_id, season, episode)


def get_episodes_for_show(show_imdb_id: str) -> Dict[Tuple[int, int], str]:
    """Return `(season, episode) -> imdb_id` for every known episode of a show."""
    result: Dict[Tuple[int, int], str] = {}
    with get_db() as cursor:
        cursor.execute(
            "SELECT season, episode, episode_id FROM imdb_episodes WHERE parent_id = ?",
            (show_imdb_id,)
        )
        for row in cursor.fetchall():
            result[(row["season"], row["episode"])] = row["episode_id"]
    return result


@contextmanager
def bulk_episode_lookup() -> Generator[Callable[..., Optional[str]], None, None]:
    """Context manager yielding a lookup function with a shared connection."""
    with get_db() as cursor:
        def lookup(show_imdb_id: str, season: int, episode: int) -> Optional[str]:
            cursor.execute(
                "SELECT episode_id FROM imdb_episodes "
                "WHERE parent_id = ? AND season = ? AND episode = ?",
                (show_imdb_id, season, episode)
            )
            row = cursor.fetchone()
            return row["episode_id"] if row else None
        yield lookup


_DATASET_TABLES = {"ratings": "imdb_ratings", "episodes": "imdb_episodes"}


def _is_dataset_available(dataset: str) -> bool:
    table = _DATASET_TABLES[dataset]
    with get_db() as cursor:
        cursor.execute(f"SELECT 1 FROM {table} LIMIT 1")
        return cursor.fetchone() is not None


def _get_dataset_stats(dataset: str) -> Dict[str, int | float | str | bool | None]:
    stats: Dict[str, int | float | str | bool | None] = {
        "entries": 0,
        "last_modified": None,
        "downloaded_at": None,
    }
    with get_db() as cursor:
        cursor.execute(
            "SELECT last_modified, downloaded_at, entry_count FROM imdb_meta WHERE dataset = ?",
            (dataset,)
        )
        row = cursor.fetchone()
        if row:
            stats["last_modified"] = row["last_modified"]
            stats["downloaded_at"] = row["downloaded_at"]
            stats["entries"] = row["entry_count"] or 0
    return stats


def is_dataset_available() -> bool:
    """True if the ratings dataset has been imported."""
    return _is_dataset_available("ratings")


def get_dataset_stats() -> Dict[str, int | float | str | bool | None]:
    """Return ratings dataset stats: entries, last_modified, downloaded_at."""
    return _get_dataset_stats("ratings")


def is_episode_dataset_available() -> bool:
    """True if the episodes dataset has been imported."""
    return _is_dataset_available("episodes")


def get_episode_dataset_stats() -> Dict[str, int | str | None]:
    """Return episode dataset stats: entries, last_modified, downloaded_at."""
    return _get_dataset_stats("episodes")  # type: ignore[return-value]


def get_meta_last_modified(dataset: str) -> Optional[str]:
    """Return the stored Last-Modified header for a dataset ('ratings' or 'episodes')."""
    with get_db() as cursor:
        cursor.execute(
            "SELECT last_modified FROM imdb_meta WHERE dataset = ?",
            (dataset,)
        )
        row = cursor.fetchone()
        if row and row["last_modified"]:
            return row["last_modified"]
    return None


def save_meta(
    dataset: str,
    last_mod: str,
    entry_count: int = 0,
    library_episode_count: Optional[int] = None
) -> None:
    """Upsert dataset metadata (last-modified, downloaded-at, counts)."""
    with get_db() as cursor:
        if library_episode_count is not None:
            cursor.execute(
                """INSERT OR REPLACE INTO imdb_meta
                   (dataset, last_modified, downloaded_at, entry_count, library_episode_count)
                   VALUES (?, ?, ?, ?, ?)""",
                (dataset, last_mod, datetime.now().isoformat(), entry_count, library_episode_count)
            )
        else:
            cursor.execute(
                """INSERT OR REPLACE INTO imdb_meta
                   (dataset, last_modified, downloaded_at, entry_count)
                   VALUES (?, ?, ?, ?)""",
                (dataset, last_mod, datetime.now().isoformat(), entry_count)
            )


def get_episode_meta() -> Tuple[Optional[str], int]:
    """Return (last_modified, library_episode_count) for the episodes dataset."""
    with get_db() as cursor:
        cursor.execute(
            "SELECT last_modified, library_episode_count FROM imdb_meta WHERE dataset = ?",
            ("episodes",)
        )
        row = cursor.fetchone()
        if row:
            return row["last_modified"], row["library_episode_count"] or 0
        return None, 0


def import_ratings_begin(cursor: sqlite3.Cursor) -> None:
    """Create a fresh `imdb_ratings_new` staging table; live table untouched until commit."""
    cursor.execute("PRAGMA synchronous = OFF")
    cursor.execute("DROP TABLE IF EXISTS imdb_ratings_new")
    cursor.execute('''
        CREATE TABLE imdb_ratings_new (
            imdb_id TEXT PRIMARY KEY,
            rating REAL NOT NULL,
            votes INTEGER NOT NULL
        )
    ''')


def import_ratings_batch(cursor: sqlite3.Cursor, batch: List[Tuple[str, float, int]]) -> None:
    """Bulk-insert a batch of (imdb_id, rating, votes) tuples into the staging table."""
    cursor.executemany(
        "INSERT INTO imdb_ratings_new (imdb_id, rating, votes) VALUES (?, ?, ?)",
        batch
    )


def import_ratings_commit(cursor: sqlite3.Cursor) -> None:
    """Swap the staging table in for `imdb_ratings`.

    The DROP/RENAME join the open insert transaction, so an aborted import rolls
    back to the previous table instead of leaving the live table dropped and empty.
    """
    cursor.execute("DROP TABLE IF EXISTS imdb_ratings")
    cursor.execute("ALTER TABLE imdb_ratings_new RENAME TO imdb_ratings")


def import_episodes_begin(cursor: sqlite3.Cursor) -> None:
    """Create a fresh `imdb_episodes_new` staging table; live table untouched until commit."""
    cursor.execute("PRAGMA synchronous = OFF")
    cursor.execute("DROP TABLE IF EXISTS imdb_episodes_new")
    cursor.execute('''
        CREATE TABLE imdb_episodes_new (
            parent_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            episode INTEGER NOT NULL,
            episode_id TEXT NOT NULL,
            PRIMARY KEY (parent_id, season, episode)
        )
    ''')


def import_episodes_batch(cursor: sqlite3.Cursor,
                          batch: List[Tuple[str, int, int, str]]) -> None:
    """Bulk-insert (parent_id, season, episode, episode_id) tuples into the staging table."""
    cursor.executemany(
        "INSERT OR REPLACE INTO imdb_episodes_new (parent_id, season, episode, episode_id) "
        "VALUES (?, ?, ?, ?)",
        batch
    )


def import_episodes_commit(cursor: sqlite3.Cursor) -> None:
    """Swap the staging table in for `imdb_episodes` and rebuild its lookup index.

    The DROP/RENAME join the open insert transaction, so an aborted import rolls
    back to the previous table instead of leaving the live table dropped and empty.
    """
    cursor.execute("DROP TABLE IF EXISTS imdb_episodes")
    cursor.execute("ALTER TABLE imdb_episodes_new RENAME TO imdb_episodes")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_imdb_episodes_parent ON imdb_episodes(parent_id)"
    )
