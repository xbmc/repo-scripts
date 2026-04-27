"""
Persistent storage for EasyMovie data.

Manages suggested movie history, playback tracking, and
last-used filter answers. Data is stored as JSON in the
addon's userdata directory.

Logging:
    Logger: 'data'
    Key events:
        - history.validate (DEBUG): Stale entries removed
        - history.prune (DEBUG): Old entries pruned
        - history.clear (DEBUG): History cleared
        - history.load_fail (WARNING): Storage file corrupt or unreadable
        - history.save_fail (WARNING): Failed to save storage
    See LOGGING.md for full guidelines.
"""
import json
import os
import time
from typing import Any, Dict, List, Optional, Set, Union


class StorageManager:
    """Manages persistent JSON storage for EasyMovie.

    Data structure:
        {
            "suggested": [{"movieid": int, "timestamp": float}, ...],
            "started": [{"movieid": int, "timestamp": float}, ...],
            "last_filters": {...}
        }
    """

    def __init__(self, path: str) -> None:
        """Initialize storage, loading existing data if available.

        Args:
            path: Full path to the JSON storage file.
        """
        self._path = path
        self._logger: Optional[Union[object, bool]] = None
        self._data: Dict[str, Any] = {
            "suggested": [],
            "started": [],
            "last_filters": {},
        }
        self._load()

    @property
    def _log(self) -> Optional[Any]:
        """Lazy-init logger to avoid circular imports at module load time."""
        if self._logger is None:
            try:
                from resources.lib.utils import get_logger
                self._logger = get_logger('data')
            except Exception:
                self._logger = False  # Sentinel: don't retry
        return self._logger if self._logger else None

    def _load(self) -> None:
        """Load data from disk."""
        if os.path.exists(self._path):
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    self._data["suggested"] = loaded.get("suggested", [])
                    self._data["started"] = loaded.get("started", [])
                    self._data["last_filters"] = loaded.get("last_filters", {})
            except (json.JSONDecodeError, IOError, OSError):
                if self._log:
                    self._log.warning(
                        "Storage file corrupt or unreadable",
                        event="history.load_fail",
                        path=self._path)

    def save(self) -> None:
        """Write data to disk atomically (write to temp, then replace)."""
        try:
            dir_path = os.path.dirname(self._path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
            tmp_path = self._path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
            os.replace(tmp_path, self._path)
        except (IOError, OSError) as exc:
            if self._log:
                self._log.warning("Failed to save storage",
                                  event="history.save_fail",
                                  path=self._path, error=str(exc))

    # ------------------------------------------------------------------
    # Internal helpers for suggested/started entry management
    # ------------------------------------------------------------------

    def _add_entry(self, key: str, movieid: int, title: str) -> None:
        """Add a movie entry, avoiding duplicates."""
        existing_ids = {s.get("movieid", 0) for s in self._data[key]}
        if movieid not in existing_ids:
            self._data[key].append({
                "movieid": movieid,
                "title": title,
                "timestamp": time.time(),
            })
            self.save()

    def _validate_entries(
        self, key: str, movies: List[Dict[str, Any]], event: str,
    ) -> None:
        """Remove entries whose movie ID was reused for a different title.

        Kodi reuses movie IDs after deletion. By comparing stored titles
        against current library titles, we detect and remove stale entries.
        """
        title_by_id = {m.get("movieid", 0): m.get("title", "") for m in movies}
        before = len(self._data[key])
        self._data[key] = [
            s for s in self._data[key]
            if s.get("title") and s.get("movieid", 0) in title_by_id
            and title_by_id[s.get("movieid", 0)] == s.get("title")
        ]
        after = len(self._data[key])
        if before != after:
            if self._log:
                self._log.debug(
                    "Stale %s entries removed" % key,
                    event=event,
                    removed=before - after, remaining=after)
            self.save()

    # ------------------------------------------------------------------
    # Suggested movie tracking (re-suggestion avoidance)
    # ------------------------------------------------------------------

    def add_suggested(self, movieid: int, title: str = "") -> None:
        """Record a movie as suggested (for re-suggestion avoidance).

        Args:
            movieid: The Kodi movie ID.
            title: Movie title (stored for debugging, not used in logic).
        """
        self._add_entry("suggested", movieid, title)

    def get_suggested_ids(self) -> Set[int]:
        """Get all suggested movie IDs."""
        return {s.get("movieid", 0) for s in self._data["suggested"]}

    def clear_suggested(self) -> None:
        """Remove all suggested entries."""
        if self._data["suggested"]:
            count = len(self._data["suggested"])
            self._data["suggested"] = []
            self.save()
            if self._log:
                self._log.debug(
                    "Suggested history cleared",
                    event="history.clear", removed=count)

    def validate_suggested(self, movies: List[Dict[str, Any]]) -> None:
        """Remove suggested entries where the ID was reused for a different movie.

        Args:
            movies: Current library movies (must include movieid and title).
        """
        self._validate_entries("suggested", movies, "history.validate")

    def prune_suggested(self, max_age_hours: int) -> None:
        """Remove suggested entries older than max_age_hours.

        Args:
            max_age_hours: Maximum age in hours.
        """
        cutoff = time.time() - (max_age_hours * 3600)
        before = len(self._data["suggested"])
        self._data["suggested"] = [
            s for s in self._data["suggested"]
            if s.get("timestamp", 0) >= cutoff
        ]
        after = len(self._data["suggested"])
        if before != after:
            if self._log:
                self._log.debug(
                    "Old suggested entries pruned",
                    event="history.prune",
                    removed=before - after, remaining=after,
                    max_age_hours=max_age_hours)
            self.save()

    # ------------------------------------------------------------------
    # Started movie tracking (in-progress detection)
    # ------------------------------------------------------------------

    def add_started(self, movieid: int, title: str = "") -> None:
        """Record a movie as started through EasyMovie.

        Args:
            movieid: The Kodi movie ID.
            title: Movie title (stored for debugging, not used in logic).
        """
        self._add_entry("started", movieid, title)

    def get_started_ids(self) -> Set[int]:
        """Get all started movie IDs."""
        return {s.get("movieid", 0) for s in self._data["started"]}

    def validate_started(self, movies: List[Dict[str, Any]]) -> None:
        """Remove started entries for movies no longer in the library.

        Args:
            movies: Current library movies (must include movieid and title).
        """
        self._validate_entries("started", movies, "history.validate_started")

    # ------------------------------------------------------------------
    # Filter persistence
    # ------------------------------------------------------------------

    def save_last_filters(self, filters: Dict[str, Any]) -> None:
        """Save wizard filter answers for next session.

        Args:
            filters: Dict of filter answers.
        """
        self._data["last_filters"] = filters
        self.save()

    def load_last_filters(self) -> Dict[str, Any]:
        """Load last wizard filter answers."""
        return self._data.get("last_filters", {})
