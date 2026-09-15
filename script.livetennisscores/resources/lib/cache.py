"""The add-on's small persisted files, and how they are written safely.

The one users notice is the cache of the last live-match poll: the service
writes it after every successful poll, and the scoreboard window reads it and
only calls the API itself when the cached copy is older than the polling
cadence. That keeps opening the scoreboard free in request terms, which
matters on a plan capped at 100 requests a day.

:func:`write_json` and :func:`read_json` are the shared half, used for the
request budget in ``budget.py`` as well, because both files are read by one
script while another may be writing them.

Every operation is best-effort. A cache miss, a corrupt file or a read-only
profile directory must never surface as an error, so all failures return the
"nothing stored" answer and the caller falls back to a live request.
"""

import json
import os
import tempfile
import time

import xbmcaddon
import xbmcvfs

FILENAME = "live_matches.json"
_CACHE_VERSION = 1


def profile_path(filename):
    """Absolute path to one of the add-on's own files in its profile dir."""
    profile = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo("profile"))
    if not xbmcvfs.exists(profile):
        xbmcvfs.mkdirs(profile)
    return os.path.join(profile, filename)


def write_json(path, payload):
    """Replace ``path`` with ``payload`` encoded as JSON, atomically.

    A reader must never see half a file. ``open(path, "w")`` truncates the
    real file and only then fills it, so another script reading at the wrong
    moment gets a document that is valid JSON syntax right up to where it
    stops -- and a write that fails part-way leaves that truncation behind
    permanently. Writing a temporary file and then ``os.replace``-ing it over
    the target means a reader sees either the whole old file or the whole new
    one and never anything in between.

    The temporary file is created in the SAME directory as the target on
    purpose: across a filesystem boundary the replace degrades into a copy and
    stops being atomic.

    On POSIX the replace cannot fail for a reader. On Windows it can: the
    underlying move refuses while another process holds the destination open
    without delete sharing, which is exactly what :func:`read_json` does. The
    file is never corrupted by that -- the target is simply left alone and
    this returns False -- so every caller has to treat False as "not stored",
    which is why the request budget keeps an in-memory count of its own.

    :returns: True when the file is now the new content.
    """
    directory = os.path.dirname(path) or "."
    temp_path = None
    try:
        descriptor, temp_path = tempfile.mkstemp(
            dir=directory, prefix=os.path.basename(path) + ".", suffix=".tmp")
        try:
            handle = os.fdopen(descriptor, "w", encoding="utf-8")
        except BaseException:
            # fdopen did not take ownership of the descriptor, so nothing else
            # will ever close it.
            os.close(descriptor)
            raise
        with handle:
            json.dump(payload, handle)
            handle.flush()
            # Get the bytes down before the name moves. Without this a power
            # cut just after the rename can leave the real name pointing at a
            # file whose contents never reached the disk.
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        temp_path = None
        _sweep_abandoned(directory, os.path.basename(path))
        return True
    except (OSError, TypeError, ValueError):
        return False
    finally:
        if temp_path is not None:
            # The replace never happened, so this is litter, not data.
            try:
                os.remove(temp_path)
            except OSError:
                pass


def _sweep_abandoned(directory, basename, older_than_seconds=3600):
    """Delete temporary files a killed write left behind.

    Kodi force-kills a service that has not returned inside its shutdown
    grace, which can happen between ``mkstemp`` and ``os.replace`` and leaves
    a ``.tmp`` file nothing would otherwise remove. Only files older than an
    hour are swept: no write this add-on makes lasts a second, so an hour is
    comfortably past any temporary file still in use by another script.
    """
    cutoff = time.time() - older_than_seconds
    try:
        names = os.listdir(directory)
    except OSError:
        return
    for name in names:
        if not (name.startswith(basename + ".") and name.endswith(".tmp")):
            continue
        stale = os.path.join(directory, name)
        try:
            if os.path.getmtime(stale) < cutoff:
                os.remove(stale)
        except OSError:
            pass


def read_json(path):
    """The JSON object stored at ``path``, or None when there is none usable.

    A missing, corrupt, truncated or half-written file all read the same way:
    as nothing stored. That can still happen despite :func:`write_json` --
    an add-on version that wrote in place left one behind, a filesystem can
    lose a tail on an unclean shutdown, and an SD card can return garbage --
    and none of it may reach the caller as an exception.
    """
    try:
        if not os.path.isfile(path):
            return None
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, TypeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def write(matches):
    """Store this poll's match list. Returns True when it was written."""
    try:
        path = profile_path(FILENAME)
    except Exception:  # noqa: BLE001 - an unreachable profile is not an error
        return False
    return write_json(path, {
        "version": _CACHE_VERSION,
        "stored_at": time.time(),
        "matches": matches,
    })


def read(max_age_seconds):
    """The cached match list when it is fresher than ``max_age_seconds``.

    :returns: ``(matches, age_seconds)``, or ``(None, None)`` when there is
        nothing usable to return.
    """
    try:
        payload = read_json(profile_path(FILENAME))
    except Exception:  # noqa: BLE001 - an unreachable profile is not an error
        return None, None

    if payload is None or payload.get("version") != _CACHE_VERSION:
        return None, None

    stored_at = payload.get("stored_at")
    if isinstance(stored_at, bool) or not isinstance(stored_at, (int, float)):
        return None, None

    age = time.time() - stored_at
    # A negative age means the clock moved backwards; treat it as unusable.
    if age < 0 or age > max_age_seconds:
        return None, None

    matches = payload.get("matches")
    if not isinstance(matches, list):
        return None, None
    return matches, age
