"""Cross-process scan lock via a shared Kodi window property.

The service and a RunScript-launched manual scan run in separate Python
interpreters but the SAME Kodi process, so a Home-window (10000) property is
visible to both and serves as a mutex preventing concurrent scans (which would
otherwise contend on the SQLite tracker).

A headless Kodi has no home window (xbmcgui.Window raises RuntimeError), so
there the same token protocol runs on a file in special://temp instead. Unlike
a window property, that file outlives a killed Kodi, so the service clears it
at startup (clear_file_lock), when no scan can be running yet.

Logging:
    Logger: 'lock'
    Key events:
        - service.lock_reclaimed (WARNING): A stale lock was reclaimed (prior
          scan likely crashed). Normal acquire/release are not logged.
"""
from __future__ import annotations

import os
import time
import uuid
from typing import Any, Optional

import xbmcgui
import xbmcvfs

from resources.lib.constants import KODI_HOME_WINDOW_ID
from resources.lib.utils import get_logger

log = get_logger('lock')

_PROP = "metamender_scan_lock"
# Reclaim a lock older than this, so a crashed scan never wedges scanning
# forever. 6h is far beyond any real scan; it only guards against a crash that
# left the property set.
_STALE_SECONDS = 6 * 3600

# This process's current lock token (timestamp:nonce), set on a successful
# acquire and checked on release so we never clear a lock another process now
# holds (for example after ours was reclaimed as stale). None when unheld.
_my_token: Optional[str] = None

# Whether this interpreter runs in a Kodi without a home window. Every failed
# Window() lookup makes Kodi log an ERROR line, so it is asked only once.
_headless: Optional[bool] = None


def _lock_file_path() -> str:
    return xbmcvfs.translatePath("special://temp/metamender_scan.lock")


class _FileProperty:
    """The lock property kept in a file, with the window-property interface.

    Writes go through a temporary file and os.replace, so a reader never sees
    a partly written token.
    """

    def __init__(self, path: str) -> None:
        self._path = path

    def getProperty(self, _name: str) -> str:
        try:
            with open(self._path, encoding="utf-8") as fh:
                return fh.read().strip()
        except OSError:
            return ""

    def setProperty(self, _name: str, value: str) -> None:
        tmp = "{}.{}".format(self._path, uuid.uuid4().hex)
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(value)
        os.replace(tmp, self._path)

    def clearProperty(self, _name: str) -> None:
        try:
            os.remove(self._path)
        except OSError:
            pass


def _home_window() -> Any:
    global _headless
    if not _headless:
        try:
            window = xbmcgui.Window(KODI_HOME_WINDOW_ID)
        except RuntimeError:
            _headless = True
        else:
            _headless = False
            return window
    return _FileProperty(_lock_file_path())


def clear_file_lock() -> None:
    """Remove a file lock left behind by a Kodi that was killed mid-scan.

    Only the service calls this, once at startup: Kodi starts the service
    before any scan can run, so a file present then belongs to a dead process.
    Kodi with a home window never writes the file, so this is a no-op there.
    """
    _FileProperty(_lock_file_path()).clearProperty(_PROP)


def _now() -> float:
    return time.time()


def _is_stale(value: str) -> bool:
    """True if a stored lock value is old enough to reclaim (or unparseable)."""
    try:
        ts = float(value.split(":", 1)[0])
    except (ValueError, IndexError):
        return True
    return (_now() - ts) >= _STALE_SECONDS


def acquire_scan_lock() -> bool:
    """Acquire the scan lock. Returns False if another scan holds it.

    Window properties have no compare-and-set, so this cannot be perfectly
    atomic. The race is narrowed with write-then-verify: claim the lock with a
    unique token, re-read, and proceed only if our token is the one stored. A
    concurrent acquirer whose write lost is detected here and backs off. A lock
    older than _STALE_SECONDS (for example from a crashed scan) is reclaimed.
    """
    global _my_token
    win = _home_window()
    held = win.getProperty(_PROP)
    if held and not _is_stale(held):
        return False
    if held:
        log.warning(
            "Reclaimed stale scan lock (previous scan likely crashed)",
            event="service.lock_reclaimed",
        )
    token = "{}:{}".format(_now(), uuid.uuid4().hex)
    win.setProperty(_PROP, token)
    if win.getProperty(_PROP) != token:
        # A concurrent acquirer overwrote our claim; they win, we back off.
        return False
    _my_token = token
    return True


def release_scan_lock() -> None:
    """Release the lock, but only if this process still holds it."""
    global _my_token
    win = _home_window()
    if _my_token is not None and win.getProperty(_PROP) == _my_token:
        win.clearProperty(_PROP)
    _my_token = None
