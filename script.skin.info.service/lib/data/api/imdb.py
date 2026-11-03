"""IMDb's daily ratings and episode dataset exports, imported into SQLite and looked up there."""
from __future__ import annotations

import gzip
import time
from contextlib import contextmanager
from enum import Enum
import xbmc
import xbmcgui
from typing import Generator, Optional, Final

from lib.data.api.client import ApiSession
from lib.kodi.client import log
from lib.data.database._infrastructure import get_bulk_db
from lib.data.database import imdb as db_imdb

_IMPORT_SLOT_PROP: Final = "SkinInfo.ImdbImportRunning"
_IMPORT_SLOT_STALE_S: Final = 1800


@contextmanager
def _import_slot() -> Generator[bool, None, None]:
    """Guard the import against the other process, yielding False while held; 30 minutes is dead."""
    window = xbmcgui.Window(10000)
    held = window.getProperty(_IMPORT_SLOT_PROP)
    if held:
        try:
            stale = (time.time() - float(held)) >= _IMPORT_SLOT_STALE_S
        except ValueError:
            stale = True
        if not stale:
            yield False
            return
    window.setProperty(_IMPORT_SLOT_PROP, str(time.time()))
    try:
        yield True
    finally:
        window.clearProperty(_IMPORT_SLOT_PROP)


DATASET_URL: Final = "https://datasets.imdbws.com/title.ratings.tsv.gz"
EPISODE_DATASET_URL: Final = "https://datasets.imdbws.com/title.episode.tsv.gz"
BATCH_SIZE: Final = 10000


class RefreshResult(Enum):
    """Outcome of `refresh_if_stale`. `Failed` means an attempt was made but errored."""
    Updated = "updated"
    Current = "current"
    Failed = "failed"


class _ImportAborted(Exception):
    """Raised to unwind the dataset import loop when the user aborts mid-stream."""


class ApiImdbDataset:
    """IMDb ratings and episode datasets: download, import into SQLite, and lookup."""

    def __init__(self):
        self.session = ApiSession(
            service_name="IMDb Dataset",
            base_url="https://datasets.imdbws.com",
            timeout=(10.0, 120.0),
            max_retries=2,
            backoff_factor=1.0
        )

    def get_rating(self, imdb_id: str, cursor=None) -> Optional[dict[str, float | int]]:
        """Look up the rating and vote count for an IMDb id; None when the dataset has no row."""
        if cursor:
            return db_imdb.get_rating_with_cursor(imdb_id, cursor)
        return db_imdb.get_rating(imdb_id)

    def get_ratings_batch(self, imdb_ids: list[str]) -> dict[str, dict[str, float | int]]:
        """Look up ratings for many IMDb ids; an id with no row is left out of the result."""
        return db_imdb.get_ratings_batch(imdb_ids)

    def is_dataset_available(self) -> bool:
        """Whether the ratings dataset has been imported."""
        return db_imdb.is_dataset_available()

    def refresh_if_stale(self, abort_flag=None, on_download_start=None) -> RefreshResult:
        """Refresh the dataset when the remote Last-Modified differs from the stored one."""
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
        """Force a download without the If-Modified-Since check."""
        return self._download_and_import(abort_flag, force=True,
                                         on_download_start=on_download_start)

    def get_stats(self) -> dict[str, int | float | str | bool | None]:
        """Get dataset statistics (entry count, last modified date, downloaded timestamp)."""
        return db_imdb.get_dataset_stats()

    def _download_and_import(self, abort_flag=None, force: bool = False,
                             on_download_start=None) -> bool:
        """Download and import the dataset into a new table that replaces the old one on success."""
        with _import_slot() as acquired:
            if not acquired:
                log("IMDb", "Dataset import already running elsewhere, skipping")
                return False
            return self._download_and_import_locked(abort_flag, force, on_download_start)

    def _download_and_import_locked(self, abort_flag, force, on_download_start) -> bool:
        """Body of `_download_and_import`, run only while the import slot is held."""
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
        """Stream the gzipped ratings dataset into the replacement table in batches."""
        count = 0
        batch: list[tuple[str, float, int]] = []

        with get_bulk_db() as cursor:
            db_imdb.import_ratings_begin(cursor)

        # a concurrent write must not wait on the download
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
                    except ValueError:
                        continue

                    if len(batch) >= BATCH_SIZE:
                        with get_bulk_db() as cursor:
                            db_imdb.import_ratings_batch(cursor, batch)
                        batch = []

        if batch:
            with get_bulk_db() as cursor:
                db_imdb.import_ratings_batch(cursor, batch)

        if count > 0:
            with get_bulk_db() as cursor:
                db_imdb.import_ratings_commit(cursor)

        return count

    def _get_remote_last_modified(self, abort_flag=None) -> Optional[str]:
        """Get the dataset's remote Last-Modified with a HEAD request."""
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

    def get_episode_imdb_id(
        self, show_imdb_id: str, season: int, episode: int, cursor=None
    ) -> Optional[str]:
        """Look up an episode's IMDb id by show id, season and episode."""
        if cursor:
            return db_imdb.get_episode_imdb_id_with_cursor(show_imdb_id, season, episode, cursor)
        return db_imdb.get_episode_imdb_id(show_imdb_id, season, episode)

    def get_episodes_for_show(self, show_imdb_id: str) -> dict[tuple[int, int], str]:
        """Get every episode IMDb id for a show, keyed by season and episode number."""
        return db_imdb.get_episodes_for_show(show_imdb_id)

    def is_episode_dataset_available(self) -> bool:
        """Whether the episode dataset has been imported."""
        return db_imdb.is_episode_dataset_available()

    def get_episode_dataset_stats(self) -> dict[str, int | str | None]:
        """Get episode dataset statistics (entry count, last modified, downloaded timestamp)."""
        return db_imdb.get_episode_dataset_stats()

    def refresh_episode_dataset(
        self,
        user_show_ids: set[str],
        library_episode_count: Optional[int] = None,
        progress_callback=None,
        abort_flag=None
    ) -> int:
        """Download the episode dataset filtered to the user's shows; episodes kept, or -1."""
        if not user_show_ids:
            return 0

        with _import_slot() as acquired:
            if not acquired:
                log("IMDb", "Dataset import already running elsewhere, skipping")
                return -1
            return self._refresh_episode_dataset_locked(
                user_show_ids, library_episode_count, progress_callback, abort_flag)

    def _refresh_episode_dataset_locked(
        self, user_show_ids, library_episode_count, progress_callback, abort_flag
    ) -> int:
        """Body of `refresh_episode_dataset`, run only while the import slot is held."""
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
        """Stream the gzipped episode dataset into the replacement table, the user's shows only."""
        count = 0
        batch: list[tuple[str, int, int, str]] = []

        with get_bulk_db() as cursor:
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
                        except ValueError:
                            continue

                        if len(batch) >= BATCH_SIZE:
                            with get_bulk_db() as cursor:
                                db_imdb.import_episodes_batch(cursor, batch)
                            batch = []

        if batch:
            with get_bulk_db() as cursor:
                db_imdb.import_episodes_batch(cursor, batch)

        with get_bulk_db() as cursor:
            db_imdb.import_episodes_commit(cursor)

        return count

    def needs_episode_refresh(self, library_episode_count: int, abort_flag=None) -> bool:
        """Whether the library episode count moved or the remote dataset changed, without a get."""
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
    """Get the process-wide IMDb dataset instance, building it on first use."""
    global _imdb_dataset
    if _imdb_dataset is None:
        _imdb_dataset = ApiImdbDataset()
    return _imdb_dataset
