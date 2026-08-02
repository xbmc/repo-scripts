"""Worker queue infrastructure for background processing."""
from __future__ import annotations

import time
import threading
import xbmc
from queue import Queue, Empty
from typing import Optional, Set, List, Dict, Any
from multiprocessing import cpu_count
from lib.kodi.client import log


def get_optimal_worker_count() -> int:
    """Calculate optimal number of worker threads based on CPU cores."""
    try:
        cores = cpu_count()
    except (NotImplementedError, AttributeError):
        return 3

    if cores <= 0:
        return 3

    return min(max(3, cores), 8)


# Kodi serialises all NFS/SMB I/O on one global lock and caches textures one at a time.
VFS_WORKER_COUNT = 2

STALL_TIMEOUT_SECONDS = 120


class WorkerQueue:
    """Multi-threaded worker queue base. Subclasses override `_process_item()` for specific work."""

    def __init__(self, num_workers: Optional[int] = None, abort_flag=None, task_context=None,
                 result_retention: str = 'failed'):
        self.num_workers = num_workers or get_optimal_worker_count()
        self.abort_flag = abort_flag
        self.task_context = task_context
        self.result_retention = result_retention

        self.queue: Queue = Queue()
        self.processing_set: Set[Any] = set()
        self.processing_lock = threading.Lock()

        self.results: List[Dict] = []
        self.results_lock = threading.Lock()
        self.completed_count = 0
        self.successful_count = 0
        self.failed_count = 0

        self.workers: List[threading.Thread] = []
        self.running = False
        self.total_queued = 0

    def start(self) -> None:
        """Start background worker threads."""
        if self.running:
            return

        self.running = True
        self._on_start()

        for i in range(self.num_workers):
            worker = threading.Thread(
                target=self._worker,
                args=(i,),
                daemon=True,
                name=f"{self.__class__.__name__}-Worker-{i}"
            )
            worker.start()
            self.workers.append(worker)

    def stop(self, wait: bool = True) -> None:
        """Stop workers. `wait=False` clears pending items and interrupts in-flight work."""
        if not self.running:
            return

        self.running = False

        # A worker past the join is unreachable otherwise: `running` is only read at the top
        # of the loop, and TaskContext clears the abort property moments after this returns.
        if not wait and self.abort_flag:
            self.abort_flag.request()

        if not wait:
            while not self.queue.empty():
                try:
                    self.queue.get_nowait()
                    self.queue.task_done()
                except Empty:
                    break
            with self.processing_lock:
                self.processing_set.clear()

        for _ in self.workers:
            self.queue.put(None)

        for worker in self.workers:
            worker.join(timeout=2.0 if not wait else 5.0)

    def add_item(self, item: Any, dedupe_key: Optional[Any] = None) -> bool:
        """Queue an item for background processing. Returns False if already queued/processing."""
        if not self.running:
            log(
                "General",
                f"{self.__class__.__name__} cannot add item, queue not started",
                xbmc.LOGWARNING,
            )
            return False

        key = dedupe_key if dedupe_key is not None else item

        with self.processing_lock:
            if key in self.processing_set:
                return False

            if not self._should_process_item(item, key):
                return False

            self.processing_set.add(key)

        self.queue.put((item, key, time.time()))
        self.total_queued += 1
        return True

    def bulk_add_items(self, items: List[Any]) -> int:
        """Queue multiple items. Returns count successfully queued (skips duplicates)."""
        queued = 0
        for item in items:
            if self.add_item(item):
                queued += 1
        return queued

    def wait(self, timeout: Optional[float] = None) -> bool:
        """Block until the queue is empty. Returns False on timeout or Kodi abort."""
        try:
            if timeout:
                start = time.time()
                monitor = xbmc.Monitor()
                while not self.queue.empty() or self.processing_set:
                    if time.time() - start > timeout:
                        return False
                    if monitor.waitForAbort(0.1):
                        return False
            else:
                self.queue.join()
            return True
        except Exception as e:
            log("General", f"{self.__class__.__name__} wait error: {str(e)}", xbmc.LOGERROR)
            return False

    def get_stats(self) -> Dict:
        """Return current queue statistics.

        Keys: `queued, processing, completed, successful, failed, total_queued,
        num_workers, results`.
        """
        with self.results_lock:
            return {
                'queued': self.queue.qsize(),
                'processing': len(self.processing_set),
                'completed': self.completed_count,
                'successful': self.successful_count,
                'failed': self.failed_count,
                'total_queued': self.total_queued,
                'num_workers': self.num_workers,
                'results': list(self.results)
            }

    def _record_result(self, result: Dict) -> None:
        """Count one finished item, keeping its dict only if retention asks for it."""
        success = result.get('success', False)
        with self.results_lock:
            self.completed_count += 1
            if success:
                self.successful_count += 1
            else:
                self.failed_count += 1

            if self.result_retention == 'all' or (
                self.result_retention == 'failed' and not success
            ):
                self.results.append(result)

    def get_progress(self) -> Dict:
        """Return `{percent, completed, total}` for the current queue run."""
        if self.total_queued == 0:
            return {'percent': 0, 'completed': 0, 'total': 0}

        with self.results_lock:
            completed = self.completed_count

        return {
            'percent': int((completed / self.total_queued) * 100),
            'completed': completed,
            'total': self.total_queued
        }

    def _worker(self, worker_id: int) -> None:
        """Worker thread loop: pull from queue, hand off to `_run_item`, repeat."""
        monitor = xbmc.Monitor()

        while self.running:
            if monitor.abortRequested() or (self.abort_flag and self.abort_flag.is_requested()):
                break

            try:
                item = self.queue.get(timeout=0.1)
                if item is None:
                    break
                if not self._run_item(item, worker_id, monitor):
                    break
            except Empty:
                continue
            except Exception as e:
                log(
                    "General",
                    f"{self.__class__.__name__} worker {worker_id} unexpected error: {str(e)}",
                    xbmc.LOGERROR,
                )

    def _run_item(self, item: tuple, worker_id: int, monitor: xbmc.Monitor) -> bool:
        """Process one queued item, record result, fire callbacks, clean up.

        Returns False if processing was aborted before _process_item ran (caller breaks out
        of the worker loop). Returns True otherwise, including on _process_item exceptions.
        """
        item_data, dedupe_key, start_time = item

        if monitor.abortRequested() or (self.abort_flag and self.abort_flag.is_requested()):
            with self.processing_lock:
                self.processing_set.discard(dedupe_key)
            self.queue.task_done()
            return False

        try:
            result = self._process_item(item_data, worker_id)

            if result is None:
                result = {}

            result['success'] = result.get('success', True)
            result['elapsed'] = time.time() - start_time
            result['worker'] = worker_id

            self._record_result(result)

            self._on_item_complete(item_data, result)

        except Exception as e:
            result = {
                'success': False,
                'elapsed': time.time() - start_time,
                'worker': worker_id,
                'error': str(e),
            }

            self._record_result(result)

            log(
                "General",
                f"{self.__class__.__name__} worker {worker_id} error: {str(e)}",
                xbmc.LOGWARNING,
            )

            self._on_item_complete(item_data, result)

        finally:
            with self.processing_lock:
                self.processing_set.discard(dedupe_key)

            self.queue.task_done()

            if self.task_context:
                self.task_context.mark_progress()

        return True

    def _process_item(self, item: Any, worker_id: int) -> Optional[Dict]:
        """Override in subclass. Return a result dict (must include `success`)."""
        raise NotImplementedError("Subclasses must implement _process_item()")

    def _on_start(self) -> None:
        """Optional subclass hook: called once when `start()` spins up workers."""
        pass

    def _should_process_item(self, item: Any, dedupe_key: Any) -> bool:
        """Optional subclass hook: return False to skip queuing an item."""
        return True

    def _on_item_complete(self, item: Any, result: Dict) -> None:
        """Optional subclass hook: called after every item (success or failure)."""
        pass
