"""One background task slot shared across add-on processes, with heartbeat and stale checks."""
from __future__ import annotations

import threading
import json
import time
import uuid
import xbmc
import xbmcgui
from typing import Optional, Dict, Any, Final
from lib.kodi.client import log, ADDON

# stale after about three missed heartbeats
HEARTBEAT_INTERVAL: Final = 5
STALE_TIMEOUT: Final = 15
STUCK_TIMEOUT: Final = 60
ABORT_POLL_INTERVAL: Final = 1.0
MAX_REQUEST_SECONDS: Final = 8.0

_lock = threading.RLock()
# Home window properties survive between script runs
_home_window = xbmcgui.Window(10000)
_PROPERTY_TASK: Final = 'SkinInfo.ActiveTask'
_PROPERTY_ABORT: Final = 'SkinInfo.CurrentAbortFlag'


def _read_task_data() -> Optional[Dict[str, Any]]:
    """Read the active-task JSON from the home window. None on missing or corrupt."""
    task_json = _home_window.getProperty(_PROPERTY_TASK)
    if not task_json:
        return None
    try:
        return json.loads(task_json)
    except json.JSONDecodeError:
        return None


def _write_task_data(data: Dict[str, Any]) -> None:
    """Write the active-task JSON to the home window."""
    _home_window.setProperty(_PROPERTY_TASK, json.dumps(data))


class ServiceAbortFlag:
    """Abort flag for online API calls, set on Kodi abort or service stop, with an optional cap."""

    def __init__(self, abort_event: threading.Event,
                 max_request_seconds: Optional[float] = None):
        self._abort_event = abort_event
        self._monitor = xbmc.Monitor()
        self.max_request_seconds = max_request_seconds

    def is_requested(self) -> bool:
        """True if the service or Kodi is aborting."""
        if self._monitor.abortRequested():
            return True
        return self._abort_event.is_set()


class ShutdownAbortFlag:
    """Abort flag for script work with no task to cancel; only shutdown or `request` stops it."""

    def __init__(self, max_request_seconds: Optional[float] = None) -> None:
        self.max_request_seconds = max_request_seconds
        self._monitor = xbmc.Monitor()
        self._requested = False

    def request(self) -> None:
        """Abort everything sharing this flag, e.g. the rate-limit cancel-all choice."""
        self._requested = True

    def is_requested(self) -> bool:
        """True once Kodi is shutting down or an abort was requested."""
        return self._requested or self._monitor.abortRequested()


class AbortFlag:
    """Per-task abort flag in a Home property, true only for the task it names or on shutdown."""

    def __init__(self, task_id: str, max_request_seconds: Optional[float] = None) -> None:
        self.task_id = task_id
        self.max_request_seconds = max_request_seconds
        self._monitor = xbmc.Monitor()
        self._poll_lock = threading.Lock()
        self._last_poll = 0.0
        self._cached = False

    def request(self) -> None:
        """Request abort for this task."""
        with _lock:
            _home_window.setProperty(_PROPERTY_ABORT, self.task_id)
        with self._poll_lock:
            self._cached = True
            self._last_poll = time.monotonic()

    def clear(self) -> None:
        """Clear the abort flag only if it still belongs to this task."""
        with _lock:
            current = _home_window.getProperty(_PROPERTY_ABORT)
            if current == self.task_id:
                _home_window.clearProperty(_PROPERTY_ABORT)

    def is_requested(self) -> bool:
        """True when this task was cancelled or Kodi is shutting down; polled once a second."""
        if self._monitor.abortRequested():
            return True

        # getProperty takes Kodi's global graphics lock, contended with the render thread
        now = time.monotonic()
        with self._poll_lock:
            if now - self._last_poll < ABORT_POLL_INTERVAL:
                return self._cached
            self._last_poll = now
            self._cached = _home_window.getProperty(_PROPERTY_ABORT) == self.task_id
            return self._cached


class TaskContext:
    """Registered background task with a heartbeat; `mark_progress` tells stuck from alive."""

    def __init__(self, name: str, max_request_seconds: Optional[float] = None) -> None:
        self.name = name
        task_id = str(uuid.uuid4())
        self.abort_flag = AbortFlag(task_id, max_request_seconds=max_request_seconds)
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._stop_heartbeat = threading.Event()
        self._progress_lock = threading.Lock()
        self.started_at = time.time()
        self.last_progress = time.time()

    def __enter__(self) -> 'TaskContext':
        if not register_task(self.name, self.abort_flag):
            log("General", f"Failed to register task '{self.name}'", xbmc.LOGWARNING)
            raise RuntimeError(f"Failed to register task: {self.name}")

        self._stop_heartbeat.clear()
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True
        )
        self._heartbeat_thread.start()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._stop_heartbeat.set()
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=1.0)

        clear_task()
        return False

    def _heartbeat_loop(self) -> None:
        """Stamp heartbeat and progress times, re-registering the task if it was cleared."""
        while not self._stop_heartbeat.wait(HEARTBEAT_INTERVAL):
            with self._progress_lock:
                last_progress = self.last_progress

            with _lock:
                data = _read_task_data() or {
                    'name': self.name,
                    'task_id': self.abort_flag.task_id,
                    'started_at': self.started_at,
                }
                data['last_heartbeat'] = time.time()
                data['last_progress'] = last_progress
                _write_task_data(data)

    def mark_progress(self) -> None:
        """Mark that work is actively happening (called by workers)."""
        with self._progress_lock:
            self.last_progress = time.time()


def _is_task_running_unlocked() -> bool:
    """True when a task is registered; the caller holds the lock."""
    task_json = _home_window.getProperty(_PROPERTY_TASK)
    return bool(task_json)


def register_task(name: str, abort_flag: AbortFlag) -> bool:
    """Register a new background task. Returns False if another task is already running."""
    with _lock:
        if _is_task_running_unlocked():
            return False

        now = time.time()
        _write_task_data({
            'name': name,
            'task_id': abort_flag.task_id,
            'started_at': now,
            'last_heartbeat': now,
            'last_progress': now,
        })
        return True


def cancel_task() -> bool:
    """Set the running task's abort flag. Returns False if no task is running."""
    with _lock:
        data = _read_task_data()
        if not data:
            return False
        task_id = data.get('task_id')
        if not task_id:
            return False
        AbortFlag(task_id).request()
        return True


def get_task_info() -> Optional[Dict[str, Any]]:
    """Return the running task's metadata dict, or None if no task is running."""
    with _lock:
        return _read_task_data()


def is_task_running() -> bool:
    """True if a background task is registered."""
    with _lock:
        return _is_task_running_unlocked()


def acquire_task_slot(operation_name: str, use_background: bool) -> bool:
    """Resolve a task collision; background mode refuses, foreground offers to cancel and waits."""
    if not is_task_running():
        return True

    if use_background:
        task_info = get_task_info()
        current_task = task_info['name'] if task_info else "Unknown task"
        xbmcgui.Dialog().ok(
            ADDON.getLocalizedString(32172),
            f"{ADDON.getLocalizedString(32457).format(current_task)}[CR][CR]{ADDON.getLocalizedString(32458)}"
        )
        return False

    from lib.infrastructure.menus import confirm_cancel_running_task
    if not confirm_cancel_running_task(operation_name):
        return False

    cancel_task()
    monitor = xbmc.Monitor()
    while is_task_running() and not monitor.abortRequested():
        # a dead task owner never deregisters; stale detection unblocks the wait
        cleanup_stale_tasks()
        monitor.waitForAbort(0.5)
    return True


def clear_task() -> None:
    """Clear the current task registration and abort flag."""
    with _lock:
        data = _read_task_data()
        if data:
            task_id = data.get('task_id')
            if task_id:
                AbortFlag(task_id).clear()
        _home_window.clearProperty(_PROPERTY_TASK)


def cleanup_stale_tasks() -> None:
    """Remove stale tasks: no heartbeat 15s (crash) or no progress 60s (stuck)."""
    task_info = get_task_info()
    if not task_info:
        return

    now = time.time()

    heartbeat_age = now - task_info.get('last_heartbeat', 0)
    if heartbeat_age > STALE_TIMEOUT:
        log(
            "General",
            f"Clearing stale task '{task_info['name']}' (no heartbeat for {heartbeat_age:.0f}s)",
            xbmc.LOGWARNING,
        )
        clear_task()
        return

    progress_age = now - task_info.get('last_progress', 0)
    if progress_age > STUCK_TIMEOUT:
        log(
            "General",
            f"Clearing stuck task '{task_info['name']}' (no progress for {progress_age:.0f}s)",
            xbmc.LOGWARNING,
        )
        clear_task()
        return
