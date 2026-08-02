"""IMDb dataset handler - downloads and caches IMDb's public ratings dataset.

IMDb provides free daily dataset exports at https://datasets.imdbws.com/ for
personal, non-commercial use. This module handles downloading, caching, and
lookups from the title.ratings.tsv dataset.

Data is stored in SQLite for minimal RAM usage on low-end devices.
"""
from __future__ import annotations

import gzip
from enum import Enum
import xbmc
from typing import Optional

from lib.data.api.client import ApiSession
from lib.kodi.client import log
from lib.data.database._infrastructure import get_db
from lib.data.database import imdb as db_imdb

DATASET_URL = "https://datasets.imdbws.com/title.ratings.tsv.gz"
EPISODE_DATASET_URL = "https://datasets.imdbws.com/title.episode.tsv.gz"
BATCH_SIZE = 10000


class RefreshResult(Enum):
    """Outcome of `refresh_if_stale`. `Failed` means an attempt was made but errored."""
    Updated = "updated"
    Current = "current"
    Failed = "failed"


class _ImportAborted(Exception):
    pass


class ApiImdbDataset:
    """Handles IMDb dataset download, caching, and lookup via SQLite."""

    def __init__(self):
        self.session = ApiSession(
            service_name="IMDb Dataset",
            base_url="https://datasets.imdbws.com",
            timeout=(10.0, 120.0),
            max_retries=2,
            backoff_factor=1.0
        )

    def get_rating(self, imdb_id: str, cursor=None) -> Optional[dict[str, float | int]]:
        """Look up rating for an IMDb ID. Pass cursor for bulk operations to avoid connection
        overhead.

        Returns {"rating": 9.3, "votes": 2800000} or None if not found.
        """
        if cursor:
            return db_imdb.get_rating_with_cursor(imdb_id, cursor)
        return db_imdb.get_rating(imdb_id)

    def get_ratings_batch(self, imdb_ids: list[str]) -> dict[str, dict[str, float | int]]:
        """Look up ratings for multiple IMDb IDs. Missing IDs are not included in the result."""
        return db_imdb.get_ratings_batch(imdb_ids)

    def is_dataset_available(self) -> bool:
        """Check if the dataset has been imported to the database."""
        return db_imdb.is_dataset_available()

    def refresh_if_stale(self, abort_flag=None, on_download_start=None) -> RefreshResult:
        """Check for updates (via HTTP Last-Modified) and download if remote is newer.

        `Updated` if dataset was downloaded, `Current` if local matches remote,
        `Failed` if any network/import step errored. `on_download_start` fires once
        if a download actually begins, so callers can skip UI on the up-to-date path.
        """
        try:
            remote_mod = self._get_remote_last_modified(abort_flag)
            if not remote_mod:
                return RefreshResult.Failed

            local_mod = db_imdb.get_meta_last_modified("ratings")

            if local_mod == remote_mod:
                return RefreshResult.Current

            log("IMDb", f"Dataset update available (local: {local_mod}, remote: {remote_mod})")
            return (RefreshResult.Updated
                    if self._download_and_import(abort_flag, on_download_start=on_download_start)
                    else RefreshResult.Failed)

        except Exception as e:
            log("IMDb", f"Error checking for dataset updates: {e}", xbmc.LOGWARNING)
            return RefreshResult.Failed

    def force_download(self, abort_flag=None, on_download_start=None) -> bool:
        """Force download the dataset regardless of cache state."""
        return self._download_and_import(abort_flag, force=True,
                                         on_download_start=on_download_start)

    def get_stats(self) -> dict[str, int | float | str | bool | None]:
        """Get dataset statistics (entry count, last modified date, downloaded timestamp)."""
        return db_imdb.get_dataset_stats()

    def _download_and_import(self, abort_flag=None, force: bool = False,
                             on_download_start=None) -> bool:
        """Download the dataset and swap it into the DB.

        `on_download_start` fires once the server returns fresh data, right before the
        multi-second stream+import, so callers can show progress for a real download only.
        """
        try:
            log("IMDb", f"Downloading dataset from {DATASET_URL}...")

            headers = None
            if not force:
                local_mod = db_imdb.get_meta_last_modified("ratings")
                headers = {"If-Modified-Since": local_mod} if local_mod else None

            response = self.session.get_raw(
                "/title.ratings.tsv.gz",
                headers=headers,
                abort_flag=abort_flag,
                stream=True
            )

            if response is None:
                return False

            if response.status_code == 304:
                log("IMDb", "Dataset not modified (304), using cached version")
                return False

            if on_download_start:
                try:
                    on_download_start()
                except Exception:
                    pass

            last_mod = response.headers.get("Last-Modified")

            count = self._stream_and_import_ratings(response, abort_flag)

            if count == 0:
                log("IMDb", "Ratings dataset had no usable rows; keeping existing data",
                    xbmc.LOGWARNING)
                return False

            if last_mod:
                db_imdb.save_meta("ratings", last_mod, count)

            log("IMDb", f"Imported {count:,} ratings to database")
            return True

        except _ImportAborted:
            return False
        except Exception as e:
            log("IMDb", f"Failed to download dataset: {e}", xbmc.LOGERROR)
            return False

    def _stream_and_import_ratings(self, response, abort_flag=None) -> int:
        count = 0
        batch: list[tuple[str, float, int]] = []

        with get_db() as cursor:
            db_imdb.import_ratings_begin(cursor)

            with gzip.open(response.raw, "rt", encoding="utf-8") as f:
                next(f)
                for line in f:
                    if abort_flag and abort_flag.is_requested():
                        log("IMDb", "Ratings import aborted by user")
                        raise _ImportAborted()

                    parts = line.strip().split("\t")
                    if len(parts) >= 3:
                        try:
                            batch.append((parts[0], float(parts[1]), int(parts[2])))
                            count += 1

                            if len(batch) >= BATCH_SIZE:
                                db_imdb.import_ratings_batch(cursor, batch)
                                batch = []
                        except ValueError:
                            continue

            if batch:
                db_imdb.import_ratings_batch(cursor, batch)

            if count > 0:
                db_imdb.import_ratings_commit(cursor)

        return count

    def _get_remote_last_modified(self, abort_flag=None) -> Optional[str]:
        """Get Last-Modified header from remote server via HEAD request."""
        try:
            response = self.session.head(
                "/title.ratings.tsv.gz",
                abort_flag=abort_flag,
                timeout=(5.0, 10.0)
            )
            if response:
                return response.headers.get("Last-Modified")
            return None
        except Exception as e:
            log("IMDb", f"Failed to check remote Last-Modified: {e}", xbmc.LOGWARNING)
            return None

    # Episode dataset methods

    def get_episode_imdb_id(
        self, show_imdb_id: str, season: int, episode: int, cursor=None
    ) -> Optional[str]:
        """Look up episode IMDb ID by show + season + episode. Pass cursor for bulk operations."""
        if cursor:
            return db_imdb.get_episode_imdb_id_with_cursor(show_imdb_id, season, episode, cursor)
        return db_imdb.get_episode_imdb_id(show_imdb_id, season, episode)

    def get_episodes_for_show(self, show_imdb_id: str) -> dict[tuple[int, int], str]:
        """Get all episode IMDb IDs for a show, keyed by (season, episode) tuple."""
        return db_imdb.get_episodes_for_show(show_imdb_id)

    def is_episode_dataset_available(self) -> bool:
        """Check if the episode dataset has been imported."""
        return db_imdb.is_episode_dataset_available()

    def get_episode_dataset_stats(self) -> dict[str, int | str | None]:
        """Get episode dataset statistics."""
        return db_imdb.get_episode_dataset_stats()

    def refresh_episode_dataset(
        self,
        user_show_ids: set[str],
        library_episode_count: int = 0,
        progress_callback=None,
        abort_flag=None
    ) -> int:
        """Download episode dataset and filter to user's shows.

        library_episode_count is the current Kodi total, used for cache invalidation.
        Returns number of episodes imported, or -1 on error.
        """
        if not user_show_ids:
            return 0

        try:
            if progress_callback:
                progress_callback("Downloading episode data...")

            log("IMDb", f"Downloading episode dataset from {EPISODE_DATASET_URL}...")

            response = self.session.get_raw(
                "/title.episode.tsv.gz",
                abort_flag=abort_flag,
                stream=True,
                timeout=(10.0, 180.0)
            )

            if response is None:
                return -1

            last_mod = response.headers.get("Last-Modified")

            if progress_callback:
                progress_callback("Processing episodes...")

            count = self._stream_and_filter_episodes(response, user_show_ids, abort_flag)

            if last_mod:
                db_imdb.save_meta("episodes", last_mod, count,
                                  library_episode_count=library_episode_count)

            log("IMDb", f"Imported {count:,} episode IDs for {len(user_show_ids)} shows")
            return count

        except _ImportAborted:
            return -1
        except Exception as e:
            log("IMDb", f"Failed to download episode dataset: {e}", xbmc.LOGERROR)
            return -1

    def _stream_and_filter_episodes(
        self, response, user_show_ids: set[str], abort_flag=None
    ) -> int:
        """
        Stream gzip response and filter to user's shows.

        Processes the file line-by-line without loading entire dataset into memory.
        """
        count = 0
        batch: list[tuple[str, int, int, str]] = []

        with get_db() as cursor:
            db_imdb.import_episodes_begin(cursor)

            with gzip.open(response.raw, "rt", encoding="utf-8") as f:
                next(f)

                for line in f:
                    if abort_flag and abort_flag.is_requested():
                        log("IMDb", "Episode import aborted by user")
                        raise _ImportAborted()

                    parts = line.strip().split("\t")
                    if len(parts) >= 4:
                        ep_id, parent_id, season_str, episode_str = (
                            parts[0], parts[1], parts[2], parts[3])

                        if (parent_id in user_show_ids and season_str != "\\N"
                                and episode_str != "\\N"):
                            try:
                                season = int(season_str)
                                episode = int(episode_str)
                                batch.append((parent_id, season, episode, ep_id))
                                count += 1

                                if len(batch) >= BATCH_SIZE:
                                    db_imdb.import_episodes_batch(cursor, batch)
                                    batch = []
                            except ValueError:
                                continue

            if batch:
                db_imdb.import_episodes_batch(cursor, batch)

            db_imdb.import_episodes_commit(cursor)

        return count

    def needs_episode_refresh(self, library_episode_count: int, abort_flag=None) -> bool:
        """Check if episode dataset needs refresh without actually downloading."""
        try:
            local_mod, stored_ep_count = db_imdb.get_episode_meta()

            if stored_ep_count != library_episode_count:
                log("IMDb",
                    f"Library episode count changed ({stored_ep_count} -> {library_episode_count})")
                return True

            response = self.session.head(
                "/title.episode.tsv.gz",
                abort_flag=abort_flag,
                timeout=(5.0, 10.0)
            )

            if response:
                remote_mod = response.headers.get("Last-Modified")
                if not local_mod or local_mod != remote_mod:
                    log("IMDb", "IMDb dataset updated")
                    return True

            return False

        except Exception as e:
            log("IMDb", f"Error checking episode dataset status: {e}", xbmc.LOGWARNING)
            return False


_imdb_dataset: ApiImdbDataset | None = None


def get_imdb_dataset() -> ApiImdbDataset:
    """Get the singleton IMDb dataset instance."""
    global _imdb_dataset
    if _imdb_dataset is None:
        _imdb_dataset = ApiImdbDataset()
    return _imdb_dataset
