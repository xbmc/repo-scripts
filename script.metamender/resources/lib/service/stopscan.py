"""Stop scan: a request from the context menu to end the running background scan.

The request is a home window property, so the context-menu script and the
service (separate interpreters) share it. The scan checks it before each item
(engine/scan.py); the service clears it at the start and end of every cycle,
so a request never carries over into the next scan.

Logging:
    Logger: none (state only)
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import xbmcgui

from resources.lib.constants import KODI_HOME_WINDOW_ID, STOP_SCAN_PROPERTY


def _home() -> Any:
    return xbmcgui.Window(KODI_HOME_WINDOW_ID)


def request_stop() -> None:
    _home().setProperty(STOP_SCAN_PROPERTY, "1")


def clear_stop() -> None:
    _home().clearProperty(STOP_SCAN_PROPERTY)


def stop_requested() -> bool:
    return _home().getProperty(STOP_SCAN_PROPERTY) == "1"


def user_stopped(all_stats: Iterable[dict[str, Any]]) -> bool:
    """Whether a pass of the cycle ended on the user's Stop."""
    return any(s.get("stopped") for s in all_stats)


def mark_stopped(all_stats: dict[str, dict[str, Any]]) -> None:
    """Record a stop that arrived between or after a pass on the last pass
    that ran, so the cycle counts as cut short (left open, like a shutdown)
    even though no per-item check saw the request."""
    if all_stats:
        last = all_stats[next(reversed(all_stats))]
        last["stopped"] = True
        last["aborted"] = True
