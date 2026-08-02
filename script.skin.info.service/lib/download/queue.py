"""Multi-threaded artwork download queue."""
from __future__ import annotations

import os
import threading
from typing import Optional, Dict, Any
import xbmcvfs

from lib.infrastructure.workers import WorkerQueue, VFS_WORKER_COUNT
from lib.download.artwork import DownloadArtwork


class DownloadQueue(WorkerQueue):
    """Multi-threaded artwork download queue; each worker owns its own `DownloadArtwork`."""

    def __init__(self, num_workers: Optional[int] = None, existing_file_mode: str = 'skip',
                 abort_flag=None, task_context=None):
        super().__init__(
            num_workers=num_workers or VFS_WORKER_COUNT,
            abort_flag=abort_flag,
            task_context=task_context,
            result_retention='none'
        )

        self.existing_file_mode = existing_file_mode
        self.artworks: Dict[int, DownloadArtwork] = {}

        self._stats_lock = threading.Lock()
        self.stats_downloaded = 0
        self.stats_skipped = 0
        self.stats_failed = 0
        self.stats_bytes = 0
        self.stats_folders: Dict[str, int] = {}
        self.stats_error_categories: Dict[str, int] = {}
        self.stats_activity = 0

    def add_download(self, url: str, local_path: str, artwork_type: str, title: str,
                     alternate_path: Optional[str] = None, media_type: str = '') -> bool:
        """Queue a download. Returns False if the `(url, local_path)` pair is already queued."""
        item = (url, local_path, artwork_type, title, alternate_path, media_type)
        dedupe_key = (url, local_path)
        return self.add_item(item, dedupe_key=dedupe_key)

    def stop(self, wait: bool = True) -> None:
        """Stop workers, then release each worker's pooled connections."""
        super().stop(wait=wait)
        for downloader in list(self.artworks.values()):
            downloader.close()
        self.artworks.clear()

    def get_stats(self) -> Dict:
        """Return WorkerQueue stats plus download counters and folder breakdown."""
        base_stats = super().get_stats()
        with self._stats_lock:
            base_stats.update({
                'downloaded': self.stats_downloaded,
                'skipped': self.stats_skipped,
                'failed': self.stats_failed,
                'bytes_downloaded': self.stats_bytes,
                'folder_counts': dict(self.stats_folders),
                'error_categories': dict(self.stats_error_categories),
                'activity': self.stats_activity
            })
        return base_stats

    def _on_progress(self, _chunk_bytes: int) -> None:
        """Per-chunk heartbeat so the coordinator can tell a slow download from a stalled one."""
        with self._stats_lock:
            self.stats_activity += 1

    def _process_item(self, item: Any, worker_id: int) -> Dict:
        """WorkerQueue entry point: download one item and update per-queue stats."""
        url, local_path, artwork_type, title, alternate_path, _media_type = item

        if worker_id not in self.artworks:
            self.artworks[worker_id] = DownloadArtwork()

        downloader = self.artworks[worker_id]

        success, error, bytes_downloaded, error_category = downloader.download_artwork(
            url=url,
            local_path=local_path,            existing_file_mode=self.existing_file_mode,
            alternate_path=alternate_path,            abort_flag=self.abort_flag,
            progress_callback=self._on_progress
        )

        with self._stats_lock:
            if success:
                self.stats_downloaded += 1
                self.stats_bytes += bytes_downloaded
                validated_path = xbmcvfs.validatePath(local_path)
                folder_path = os.path.dirname(validated_path)
                if folder_path:
                    self.stats_folders[folder_path] = self.stats_folders.get(folder_path, 0) + 1
            elif error is None:
                self.stats_skipped += 1
            elif error_category != DownloadArtwork.ERROR_ABORTED:
                self.stats_failed += 1
                category = error_category or DownloadArtwork.ERROR_UNEXPECTED
                self.stats_error_categories[category] = (
                    self.stats_error_categories.get(category, 0) + 1
                )

        return {
            'url': url,
            'local_path': local_path,
            'artwork_type': artwork_type,
            'title': title,
            'success': success,
            'error': error,
            'bytes_downloaded': bytes_downloaded
        }
