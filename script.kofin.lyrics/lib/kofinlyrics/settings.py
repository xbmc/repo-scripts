"""Addon settings, read through a new Addon() each time: an instance caches
them, so a long-lived one would not see changes.

Nothing here raises. Addon() throws during teardown, when the service still
has its window to close, so a failed read returns the default.
"""

from typing import Any

import xbmcaddon

DEFAULTS = {
    "showAutomatically": True,
    "showUntimed": True,
    "offset": 0.0,
    "windowHeight": 480,
}


def _get(setting_id: str, reader: str) -> Any:
    try:
        return getattr(xbmcaddon.Addon(), reader)(setting_id)
    except Exception:
        return DEFAULTS[setting_id]


def show_automatically() -> bool:
    """Whether lyrics come up on their own, or wait to be asked for."""
    return bool(_get("showAutomatically", "getSettingBool"))


def show_untimed() -> bool:
    """Whether to show lyrics that have no timings."""
    return bool(_get("showUntimed", "getSettingBool"))


def offset() -> float:
    """Seconds to shift the timings by; positive means later."""
    try:
        return float(_get("offset", "getSettingNumber"))
    except (TypeError, ValueError):
        return 0.0


def window_height() -> int:
    """The lyrics panel's height in 1080p skin pixels, for our window and an
    opted-in skin overlay."""
    try:
        return int(_get("windowHeight", "getSettingInt"))
    except (TypeError, ValueError):
        return int(DEFAULTS["windowHeight"])
