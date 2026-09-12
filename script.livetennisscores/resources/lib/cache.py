"""A one-file cache of the last live-match poll.

The service writes it after every successful poll; the scoreboard window reads
it and only calls the API itself when the cached copy is older than the polling
cadence. That keeps opening the scoreboard free in request terms, which matters
on a plan capped at 100 requests a day.

Every operation is best-effort. A cache miss, a corrupt file or a read-only
profile directory must never surface as an error, so all failures return the
"nothing cached" answer and the caller falls back to a live request.
"""

import json
import os
import time

import xbmcaddon
import xbmcvfs

FILENAME = "live_matches.json"
_CACHE_VERSION = 1


def _cache_path():
    """Absolute path to the cache file inside the add-on's own profile dir."""
    profile = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo("profile"))
    if not xbmcvfs.exists(profile):
        xbmcvfs.mkdirs(profile)
    return os.path.join(profile, FILENAME)


def write(matches):
    """Store this poll's match list. Returns True when it was written."""
    try:
        payload = {
            "version": _CACHE_VERSION,
            "stored_at": time.time(),
            "matches": matches,
        }
        with open(_cache_path(), "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
        return True
    except (OSError, TypeError, ValueError):
        return False


def read(max_age_seconds):
    """The cached match list when it is fresher than ``max_age_seconds``.

    :returns: ``(matches, age_seconds)``, or ``(None, None)`` when there is
        nothing usable to return.
    """
    try:
        path = _cache_path()
        if not os.path.isfile(path):
            return None, None
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return None, None

    if not isinstance(payload, dict) or payload.get("version") != _CACHE_VERSION:
        return None, None

    stored_at = payload.get("stored_at")
    if not isinstance(stored_at, (int, float)):
        return None, None

    age = time.time() - stored_at
    # A negative age means the clock moved backwards; treat it as unusable.
    if age < 0 or age > max_age_seconds:
        return None, None

    matches = payload.get("matches")
    if not isinstance(matches, list):
        return None, None
    return matches, age
