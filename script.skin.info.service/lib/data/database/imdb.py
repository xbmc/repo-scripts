"""IMDb dataset database operations for ratings, episodes, and metadata."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
import time
from typing import Optional, Dict, List, Tuple, Generator, Callable

from lib.data.database._infrastructure import get_db, chunked_in_query


def _select_rating(cursor: sqlite3.Cursor, imdb_id: str) -> Optional[Dict[str, float | int]]:
    """Rating and vote count for one IMDb id."""
    cursor.execute(
        "SELECT rating, votes FROM imdb_rating WHERE imdb_id = ?",
        (imdb_id,)
    )
    row = cursor.fetchone()
    if row:
        return {"rating": row["rating"], "votes": row["votes"]}
    return None


def get_rating(imdb_id: str) -> Optional[Dict[str, float | int]]:
    """Get `{rating, votes}` for an IMDb id, or None when the dataset has no row."""
    with get_db() as cursor:
        return _select_rating(cursor, imdb_id)


def get_rating_with_cursor(imdb_id: str,
                           cursor: sqlite3.Cursor) -> Optional[Dict[str, float | int]]:
    """Same as `get_rating`, but uses a caller-provided cursor for shared-connection loops."""
    return _select_rating(cursor, imdb_id)


def get_ratings_batch(imdb_ids: List[str]) -> Dict[str, Dict[str, float | int]]:
    """Get `imdb_id -> {rating, votes}` for many ids; an id with no row is left out."""
    if not imdb_ids:
        return {}

    results: Dict[str, Dict[str, float | int]] = {}
    sql = "SELECT imdb_id, rating, votes FROM imdb_rating WHERE imdb_id IN ({placeholders})"
    with get_db() as cursor:
        for row in chunked_in_query(cursor, sql, [], list(imdb_ids)):
            results[row["imdb_id"]] = {"rating": row["rating"], "votes": row["votes"]}
    return results


def _select_episode_imdb_id(
    cursor: sqlite3.Cursor, show_imdb_id: str, season: int, episode: int
) -> Optional[str]:
    """Episode IMDb id from the parent show's id and its numbering."""
    cursor.execute(
        "SELECT episode_id FROM imdb_episode WHERE parent_id = ? AND season = ? AND episode = ?",
        (show_imdb_id, season, episode)
    )
    row = cursor.fetchone()
    return row["episode_id"] if row else None


def get_episode_imdb_id(show_imdb_id: str, season: int, episode: int) -> Optional[str]:
    """Get an episode's IMDb id from the parent show's id and its season and episode numbers."""
    with get_db() as cursor:
        return _select_episode_imdb_id(cursor, show_imdb_id, season, episode)


def get_episode_imdb_id_with_cursor(
    show_imdb_id: str, season: int, episode: int, cursor: sqlite3.Cursor
) -> Optional[str]:
    """Same as `get_episode_imdb_id`, but uses a caller-provided cursor."""
    return _select_episode_imdb_id(cursor, show_imdb_id, season, episode)


def get_episodes_for_show(show_imdb_id: str) -> Dict[Tuple[int, int], str]:
    """Get `(season, episode) -> imdb_id` for every known episode of a show."""
    result: Dict[Tuple[int, int], str] = {}
    with get_db() as cursor:
        cursor.execute(
            "SELECT season, episode, episode_id FROM imdb_episode WHERE parent_id = ?",
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
            """Episode IMDb id through the caller's open cursor."""
            return _select_episode_imdb_id(cursor, show_imdb_id, season, episode)
        yield lookup


_DATASET_TABLES = {"ratings": "imdb_rating", "episodes": "imdb_episode"}


def _is_dataset_available(dataset: str) -> bool:
    """Whether the dataset table holds any rows."""
    table = _DATASET_TABLES[dataset]
    with get_db() as cursor:
        cursor.execute(f"SELECT 1 FROM {table} LIMIT 1")
        return cursor.fetchone() is not None


def _get_dataset_stats(dataset: str) -> Dict[str, int | float | str | bool | None]:
    """Entry count and download timestamps for one IMDb dataset."""
    stats: Dict[str, int | float | str | bool | None] = {
        "entries": 0,
        "last_modified": None,
        "downloaded_at": None,
    }
    with get_db() as cursor:
        cursor.execute(
            "SELECT last_modified, downloaded_at, entry_count FROM imdb_dataset WHERE dataset = ?",
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
    """Get ratings dataset stats: entries, last_modified, downloaded_at."""
    return _get_dataset_stats("ratings")


def is_episode_dataset_available() -> bool:
    """True if the episodes dataset has been imported."""
    return _is_dataset_available("episodes")


def get_episode_dataset_stats() -> Dict[str, int | str | None]:
    """Get episode dataset stats: entries, last_modified, downloaded_at."""
    return _get_dataset_stats("episodes")  # type: ignore[return-value]


def get_meta_last_modified(dataset: str) -> Optional[str]:
    """Get a dataset's stored Last-Modified header, or None when there is none."""
    with get_db() as cursor:
        cursor.execute(
            "SELECT last_modified FROM imdb_dataset WHERE dataset = ?",
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
    """Save dataset metadata stamped now; an omitted library count keeps the stored one."""
    with get_db() as cursor:
        if library_episode_count is None:
            cursor.execute(
                "SELECT library_count FROM imdb_dataset WHERE dataset = ?", (dataset,))
            row = cursor.fetchone()
            library_episode_count = (row["library_count"] if row else 0) or 0

        cursor.execute(
            """INSERT OR REPLACE INTO imdb_dataset
               (dataset, last_modified, downloaded_at, entry_count, library_count)
               VALUES (?, ?, ?, ?, ?)""",
            (dataset, last_mod, int(time.time()), entry_count, library_episode_count)
        )


def get_episode_meta() -> Tuple[Optional[str], int]:
    """Get (last_modified, library_episode_count) for the episodes dataset."""
    with get_db() as cursor:
        cursor.execute(
            "SELECT last_modified, library_count FROM imdb_dataset WHERE dataset = ?",
            ("episodes",)
        )
        row = cursor.fetchone()
        if row:
            return row["last_modified"], row["library_count"] or 0
        return None, 0


def import_ratings_begin(cursor: sqlite3.Cursor) -> None:
    """Create a fresh `imdb_rating_new` staging table; live table untouched until commit."""
    cursor.execute("DROP TABLE IF EXISTS imdb_rating_new")
    cursor.execute('''
        CREATE TABLE imdb_rating_new (
            imdb_id TEXT NOT NULL,
            rating REAL NOT NULL,
            votes INTEGER NOT NULL,
            PRIMARY KEY (imdb_id)
        ) WITHOUT ROWID
    ''')


def import_ratings_batch(cursor: sqlite3.Cursor, batch: List[Tuple[str, float, int]]) -> None:
    """Bulk-insert a batch of (imdb_id, rating, votes) tuples into the staging table."""
    cursor.executemany(
        "INSERT INTO imdb_rating_new (imdb_id, rating, votes) VALUES (?, ?, ?)",
        batch
    )


def import_ratings_commit(cursor: sqlite3.Cursor) -> None:
    """Swap the staging table in for `imdb_rating`; the live table survives an aborted fill."""
    # DDL autocommits unless a transaction is already open
    cursor.execute("BEGIN")
    cursor.execute("DROP TABLE IF EXISTS imdb_rating")
    cursor.execute("ALTER TABLE imdb_rating_new RENAME TO imdb_rating")


def import_episodes_begin(cursor: sqlite3.Cursor) -> None:
    """Create a fresh `imdb_episode_new` staging table; live table untouched until commit."""
    cursor.execute("DROP TABLE IF EXISTS imdb_episode_new")
    cursor.execute('''
        CREATE TABLE imdb_episode_new (
            parent_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            episode INTEGER NOT NULL,
            episode_id TEXT NOT NULL,
            PRIMARY KEY (parent_id, season, episode)
        ) WITHOUT ROWID
    ''')


def import_episodes_batch(cursor: sqlite3.Cursor,
                          batch: List[Tuple[str, int, int, str]]) -> None:
    """Bulk-insert (parent_id, season, episode, episode_id) tuples into the staging table."""
    cursor.executemany(
        "INSERT OR REPLACE INTO imdb_episode_new (parent_id, season, episode, episode_id) "
        "VALUES (?, ?, ?, ?)",
        batch
    )


def import_episodes_commit(cursor: sqlite3.Cursor) -> None:
    """Swap the staging table in for `imdb_episode`; the PK prefix serves parent lookups."""
    cursor.execute("BEGIN")
    cursor.execute("DROP TABLE IF EXISTS imdb_episode")
    cursor.execute("DROP INDEX IF EXISTS idx_imdb_episode_parent")
    cursor.execute("ALTER TABLE imdb_episode_new RENAME TO imdb_episode")
