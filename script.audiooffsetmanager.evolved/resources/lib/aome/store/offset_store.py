"""OffsetStore: the sparse JSON offset database (addon_data/offsets.json).

Learned audio offsets are kept here, keyed by stream profile, rather than in
settings.xml. This module is the whole persistence surface for that file.

Design points:

* **Single writer, no locking.** At runtime the store is owned by the one
  dispatcher thread; every read and mutation happens there. The class is
  plain synchronous Python with no locks, threads, or global state — the
  injected file path, clock, and log sinks are all it depends on.
* **Verbatim signed integers.** ``delay_ms`` is stored exactly as given, at
  1 ms resolution, with no step snapping and no range clamping — deciding
  what values are legal is the caller's parser's job. Any ``int``
  round-trips bit-for-bit.
* **Corruption survivable, the future sacred.** An unparseable file is moved
  aside to ``<path>.bad`` and we start empty (data loss beats a jammed
  addon). A file from a newer schema is left untouched and the store goes
  read-only, so an older build downgraded onto newer data cannot clobber it.
* **Atomic-swap durability.** Every persist writes a sibling ``.tmp``,
  flushes and ``fsync``s it, then ``os.replace``s it over the target. The
  swap is atomic on POSIX and NTFS, so a power loss leaves either the old
  file or the new one, never a half-written one.
* **Canonical keys.** Every key crossing the store boundary (file load, the
  other-process reader, a restored backup) is re-expressed through
  ``keys.canonical_key``, so entries and reset markers written by an older
  key codec keep resolving after the spelling rules evolve. This is also
  the whole schema migration: a version-1 key (three segments, no channel
  axis) expands to its four-segment spelling here, on load and import
  alike, with no separate migration code. On a spelling collision the
  canonically-spelled entry wins (it is the fresher teaching), and a marker
  whose canonical key holds an entry is superseded, like ``set``.
* **Deletion leaves a reset marker.** ``delete``/``clear`` (and an import
  that drops keys) record the removed key(s) in a ``resets`` section: the
  user expects 0 the next time that profile plays, but Kodi's own per-file
  memory still holds the old value, so the marker lets the applier force the
  0 once, bypassing the "never act first" guard. Markers are consumed by the
  applier, superseded by a new ``set``, and invisible to the management view.
  The section is additive: absent in old files, ignored by older builds, no
  schema bump.

No disk I/O happens in the constructor; ``load()`` is the single explicit
read.
"""

import json
import math
import os
import time
from datetime import datetime, timezone

from resources.lib.aome.store import keys

_PREFIX = "AOMe_OffsetStore:"
# 2: keys grew the channel axis (4 segments). Older files (version 1,
# 3-segment keys) load fine — canonical_key expands them with a trailing
# 'all', which is the whole migration — and the first persist rewrites the
# file as version 2, at which point a downgraded build goes read-only on it
# (the guard below).
_SCHEMA_VERSION = 2


def _noop(_message):
    return None


def _is_int(value):
    """True for real ints only — bool is an int subclass and must not pass.

    The single guard shared by every validation site, so the write-path and
    load-path rules never drift apart.
    """
    return isinstance(value, int) and not isinstance(value, bool)


def _shape_ok(data):
    """The schema gate shared by load() and the read-only reader."""
    if not isinstance(data, dict):
        return False
    # The schema started at 1: a version of 0 or below never existed and
    # marks a foreign/scribbled file, which must quarantine rather than
    # load-and-resave as if it were current data.
    if not _is_int(data.get("version")) or data.get("version") < 1:
        return False
    if not isinstance(data.get("profiles"), dict):
        return False
    return True


def _load_entries(profiles, log_debug):
    """Filter entries by the load rules; shared with the reader.

    Keys are re-expressed through ``keys.canonical_key`` on the way in: the
    canonically-spelled entry wins any spelling collision, and among legacy
    spellings of one canonical key the last in file order wins.
    """
    loaded = {}
    rekeyed = {}
    for key, entry in profiles.items():
        if not isinstance(key, str):
            log_debug("{0} dropping non-string key {1!r}"
                      .format(_PREFIX, key))
            continue
        if not isinstance(entry, dict):
            log_debug("{0} dropping non-dict entry for {1!r}"
                      .format(_PREFIX, key))
            continue
        delay = entry.get("delay_ms")
        if not _is_int(delay):
            log_debug("{0} dropping entry {1!r} with non-int delay_ms"
                      .format(_PREFIX, key))
            continue
        canonical = keys.canonical_key(key)
        if canonical == key:
            loaded[key] = dict(entry)
            continue
        log_debug("{0} re-keying {1!r} as {2!r}"
                  .format(_PREFIX, key, canonical))
        rekeyed[canonical] = dict(entry)
    for canonical, entry in rekeyed.items():
        if canonical in loaded:
            log_debug("{0} dropping legacy-spelled duplicate of {1!r}"
                      .format(_PREFIX, canonical))
            continue
        loaded[canonical] = entry
    return loaded


class StoreUnreadable(Exception):
    """The offsets file exists but cannot be presented.

    Raised by the read-only readers (the script process must never
    quarantine or mutate the file): instead of load()'s .bad rename it
    reports why the view cannot render — corrupt JSON, wrong shape, an
    unreadable file, or a newer schema version.

    ``future`` is True for the newer-schema case, which the view words
    differently: the service preserves such a file untouched (read-only)
    and never quarantines it, so corruption wording would falsely promise a
    reset.
    """

    def __init__(self, message, *, future=False):
        super().__init__(message)
        self.future = future


def _parse_document(raw):
    """Shared parse/validate head of the read-only readers below: the raw
    text to a shape/version-checked document dict, or StoreUnreadable."""
    try:
        data = json.loads(raw)
    except ValueError as error:
        raise StoreUnreadable("invalid JSON ({0})".format(error))

    if not _shape_ok(data):
        raise StoreUnreadable("unexpected shape")
    if data["version"] > _SCHEMA_VERSION:
        raise StoreUnreadable(
            "newer schema version {0}".format(data["version"]), future=True)
    return data


def _load_reset_keys(raw, log_debug):
    """Validate a resets section: a list of non-empty key strings.

    The single definition shared by load() and the backup reader, so a
    scribbled marker degrades identically everywhere — to 'no pending
    reset', never to a crash or a spurious 0.
    """
    if raw is None:
        return set()
    if not isinstance(raw, list):
        log_debug("{0} dropping non-list resets section".format(_PREFIX))
        return set()
    markers = set()
    for key in raw:
        if isinstance(key, str) and key:
            # Canonicalized like entries, so a marker recorded under a
            # legacy spelling still forces its 0 when the canonical key
            # is consulted (set semantics collapse duplicates for free).
            markers.add(keys.canonical_key(key))
        else:
            log_debug("{0} dropping non-string reset marker {1!r}"
                      .format(_PREFIX, key))
    return markers


def read_profiles(path, log_debug=None):
    """Read-only entry snapshot for another process (the management view).

    Not OffsetStore.load(): only the service's dispatcher thread may touch
    the file, so this has no quarantine, no corruption flag, and no instance
    state — it opens, parses, filters (same shape rules as load()), and
    returns. A missing file is an empty store ({}); anything unpresentable
    raises :class:`StoreUnreadable`.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = handle.read()
    except FileNotFoundError:
        return {}
    except OSError as error:
        raise StoreUnreadable("unreadable ({0})".format(error))
    return _load_entries(_parse_document(raw)["profiles"], log_debug or _noop)


def read_import_document(path, log_debug=None):
    """Validated ``(entries, reset_keys)`` of an offsets backup file.

    The restore-source reader, used by both channel ends: the script process
    pre-validates the staged backup and the service validates again before
    replacing the store. Same rules as :func:`read_profiles`, with one
    divergence: a missing file raises :class:`StoreUnreadable` rather than
    reading as an empty store — a restore source that is not there is a
    failed import, never "replace everything with nothing".

    The backup's ``resets`` section rides along so a restore preserves
    pending "expect 0" promises.
    """
    log = log_debug or _noop
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = handle.read()
    except OSError as error:
        raise StoreUnreadable("unreadable ({0})".format(error))
    data = _parse_document(raw)
    return (_load_entries(data["profiles"], log),
            _load_reset_keys(data.get("resets"), log))


def read_import(path, log_debug=None):
    """The entries half of :func:`read_import_document` (the script
    process's pre-flight only needs the count/validity)."""
    return read_import_document(path, log_debug)[0]


def discard_import(path, log_warning=None):
    """Best-effort removal of a consumed or stale staged backup file.

    Lives here so the app-layer mutation handler does no direct file I/O.
    A missing file is the normal case (already consumed); any other failure
    is logged and swallowed, since a stale staging file is inert (the script
    process overwrites it before every import request).
    """
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    except OSError as error:
        (log_warning or _noop)(
            "{0} could not remove staged backup ({1})".format(_PREFIX, error))


class OffsetStore:
    """Sparse per-profile offset database backed by a single JSON file."""

    def __init__(self, path, *, clock=time.time, log_debug=None, log_warning=None):
        self._path = path
        self._clock = clock
        self._log_debug = log_debug or _noop
        self._log_warning = log_warning or _noop
        self._profiles = {}
        self._resets = set()
        self._read_only = False
        self._corruption = False

    # -- loading --------------------------------------------------------------

    def load(self):
        """Read the file once, populating in-memory state.

        Missing file → empty and writable (normal first run). Unreadable or
        malformed → the file is renamed to ``<path>.bad`` and we start empty,
        writable, with the corruption flag set. A future schema version → the
        file is left untouched and the store becomes read-only.
        """
        try:
            with open(self._path, "r", encoding="utf-8") as handle:
                raw = handle.read()
        except FileNotFoundError:
            # Normal first run: nothing on disk yet.
            self._profiles = {}
            self._resets = set()
            return
        except OSError as error:
            self._log_warning("{0} unreadable ({1}); quarantining"
                              .format(_PREFIX, error))
            self._quarantine()
            return

        try:
            data = json.loads(raw)
        except ValueError as error:
            self._log_warning("{0} invalid JSON ({1}); quarantining"
                              .format(_PREFIX, error))
            self._quarantine()
            return

        if not self._shape_ok(data):
            self._log_warning("{0} unexpected shape; quarantining".format(_PREFIX))
            self._quarantine()
            return

        version = data["version"]
        if version > _SCHEMA_VERSION:
            # A newer build wrote this. Leave it exactly as-is and refuse all
            # writes so a downgrade can never overwrite newer data.
            self._read_only = True
            self._profiles = {}
            self._resets = set()
            self._log_warning("{0} file version {1} > {2}; read-only"
                              .format(_PREFIX, version, _SCHEMA_VERSION))
            return

        self._profiles = self._load_entries(data["profiles"])
        # A marker whose canonical key now holds an entry is superseded,
        # mirroring set(): runtime writes never produce that coexistence,
        # so it can only arise from re-keying legacy spellings, where the
        # canonical entry is the fresher teaching.
        self._resets = self._load_resets(data.get("resets")) \
            - set(self._profiles)

    def _shape_ok(self, data):
        return _shape_ok(data)

    def _load_entries(self, profiles):
        return _load_entries(profiles, self._log_debug)

    def _load_resets(self, raw):
        """The shared resets-section validation (see _load_reset_keys)."""
        return _load_reset_keys(raw, self._log_debug)

    def _quarantine(self):
        """Move a corrupt file aside and start empty but writable."""
        bad = self._path + ".bad"
        try:
            os.replace(self._path, bad)
        except OSError as error:
            # Losing the quarantine rename is non-fatal: we still start empty.
            self._log_warning("{0} could not rename to .bad ({1})"
                              .format(_PREFIX, error))
        self._profiles = {}
        self._resets = set()
        self._corruption = True

    def pop_corruption(self):
        """Return the corruption flag and clear it (one-shot for the notifier)."""
        flagged = self._corruption
        self._corruption = False
        return flagged

    @property
    def read_only(self):
        """True when a newer-schema file was found and all writes are refused.

        Public so the management view can say WHY mutations are refused
        instead of conflating read-only with a persist failure.
        """
        return self._read_only

    # -- reads ----------------------------------------------------------------

    def get(self, key):
        """Return a COPY of the entry for ``key`` (or None) — never the live dict."""
        entry = self._profiles.get(key)
        if entry is None:
            return None
        return dict(entry)

    def entries(self):
        """Snapshot: ``{key: entry_copy}`` for every stored profile."""
        return {key: dict(entry) for key, entry in self._profiles.items()}

    def __len__(self):
        return len(self._profiles)

    # -- writes ---------------------------------------------------------------

    def set(self, key, delay_ms, *, source="user", video_fps=None):
        """Store an offset for ``key``, persist, and report success.

        ``key`` must be a non-empty str and ``delay_ms`` an int (bool rejected);
        violating either raises ValueError — that is a programmer error, not a
        runtime condition. A fresh ``updated`` timestamp is stamped every call.
        Returns False (after a warning) if the store is read-only or the write
        fails; True otherwise.
        """
        if not isinstance(key, str) or not key:
            raise ValueError("key must be a non-empty str")
        if not _is_int(delay_ms):
            raise ValueError("delay_ms must be an int")
        if video_fps is not None:
            # Metadata only, but NaN/Infinity would serialize as bare tokens
            # that are not valid JSON for stricter readers — refuse at the
            # door rather than poison the file.
            if isinstance(video_fps, bool) or \
                    not isinstance(video_fps, (int, float)) or \
                    not math.isfinite(video_fps):
                raise ValueError("video_fps must be a finite number or None")

        if self._read_only:
            self._log_warning("{0} read-only; refusing set({1!r})"
                              .format(_PREFIX, key))
            return False

        entry = {
            "delay_ms": delay_ms,
            "updated": self._timestamp(),
            "source": source,
        }
        if video_fps is not None:
            entry["video_fps"] = video_fps

        self._profiles[key] = entry
        # A fresh value supersedes any pending reset for the key: the user
        # re-learned the profile before it was ever played back.
        self._resets.discard(key)
        if not self._persist():
            return False
        return True

    def delete(self, key):
        """Remove ``key`` if present and persist; True only when both happen.

        The removed key is recorded as a reset marker (see the module
        docstring), so the applier forces the delay to 0 the next time the
        key is consulted and misses. A missing key touches no disk (returns
        False). Refused when read-only. A persist failure also returns False
        — the entry would resurrect on the next load — while the removal
        stays in memory, consistent with ``set``.
        """
        if self._read_only:
            self._log_warning("{0} read-only; refusing delete({1!r})"
                              .format(_PREFIX, key))
            return False
        if key not in self._profiles:
            return False
        del self._profiles[key]
        self._resets.add(key)
        return self._persist()

    def clear(self):
        """Remove all entries; return how many were durably removed.

        Every removed key is recorded as a reset marker, same as ``delete``.
        Persists only when something was removed. Refused (returns 0) when
        read-only. A persist failure also returns 0 — the entries would
        resurrect on the next load — while the in-memory removal stands,
        consistent with set/delete.
        """
        if self._read_only:
            self._log_warning("{0} read-only; refusing clear()".format(_PREFIX))
            return 0
        count = len(self._profiles)
        if count == 0:
            return 0
        self._resets.update(self._profiles)
        self._profiles = {}
        if not self._persist():
            return 0
        return count

    def replace_all(self, entries, resets=()):
        """Replace the whole store with ``entries`` (import/restore) and persist.

        Restore semantics, not merge: after this call the store holds
        exactly the given entries, filtered by the same rules as ``load()``.
        The reset markers merge three sources, all minus the imported keys:
        the live pending markers, every live key the import drops (a restore
        that drops a profile means "expect 0 next time", like
        ``delete``/``clear``), and ``resets`` — the backup's own pending
        markers. A marker whose key the import (re)fills is superseded, like
        ``set``. Refused (False) when read-only; a persist failure returns
        False with the in-memory replacement standing, consistent with
        set/delete/clear.
        """
        if self._read_only:
            self._log_warning("{0} read-only; refusing replace_all()"
                              .format(_PREFIX))
            return False
        replaced = self._load_entries(entries)
        # Same validation and canonicalization the load path applies (the
        # caller normally passes the backup reader's already-canonical
        # output, but the write path re-filters so it stays safe alone).
        carried = self._load_resets(list(resets))
        self._resets = ((self._resets | set(self._profiles) | carried)
                        - set(replaced))
        self._profiles = replaced
        return self._persist()

    # -- reset markers ----------------------------------------------------------

    def reset_pending(self, key):
        """True when ``key`` was deleted and its forced 0 has not run yet."""
        return key in self._resets

    def consume_reset(self, key):
        """Discard the reset marker for ``key`` and persist the removal.

        Called by the applier once it has acted on the marker (forced the
        0, or found the delay already there). Consuming an absent
        marker is a no-op returning True. A persist failure returns False;
        the in-memory removal stands and the reset simply repeats after a
        restart — it is idempotent by construction.
        """
        if key not in self._resets:
            return True
        self._resets.discard(key)
        return self._persist()

    # -- internals ------------------------------------------------------------

    def _timestamp(self):
        moment = datetime.fromtimestamp(self._clock(), timezone.utc)
        return moment.strftime("%Y-%m-%dT%H:%M:%SZ")

    def _persist(self):
        """Serialize and atomically swap the file into place.

        On OSError the in-memory state is left as mutated (rolling back the
        dict would surprise a single-threaded caller more than a
        stale-on-disk file does) and False is returned so the caller can
        react to the durability miss.
        """
        payload = {"version": _SCHEMA_VERSION, "profiles": self._profiles}
        if self._resets:
            # Additive section: written only when markers exist, so a store
            # with none persists byte-identically to the pre-marker format.
            payload["resets"] = sorted(self._resets)
        blob = json.dumps(payload, indent=2, sort_keys=True)
        tmp = self._path + ".tmp"
        try:
            parent = os.path.dirname(self._path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(tmp, "w", encoding="utf-8") as handle:
                handle.write(blob)
                handle.flush()
                os.fsync(handle.fileno())
            self._replace_with_retry(tmp)
        except OSError as error:
            self._log_warning("{0} persist failed ({1})".format(_PREFIX, error))
            return False
        return True

    def _replace_with_retry(self, tmp):
        """``os.replace`` with two short retries for Windows share violations.

        On Windows a concurrent reader holding the target open (the script
        process's ``read_profiles`` while the management view renders)
        makes ``os.replace`` fail with a sharing violation. That read
        window is sub-millisecond, so a brief retry closes the race;
        a persistent failure re-raises into _persist's handler.
        """
        for _attempt in range(2):
            try:
                os.replace(tmp, self._path)
                return
            except OSError:
                time.sleep(0.05)
        os.replace(tmp, self._path)
