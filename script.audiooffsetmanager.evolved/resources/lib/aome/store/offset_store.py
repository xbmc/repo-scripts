"""OffsetStore: the sparse JSON offset database (addon_data/offsets.json).

Learned audio offsets are kept here, keyed by stream profile, rather than in
settings.xml. This module is the whole persistence surface for that file. No
disk I/O happens in the constructor; ``load()`` is the only read taken on the
store's own initiative, and it writes only when it rebuilds the file from the
backup sibling.

* **Single writer, no locking.** At runtime the store is owned by the one
  dispatcher thread and every read and mutation happens there, so the class
  is plain synchronous Python with no locks, threads or global state.
* **Verbatim signed integers.** ``delay_ms`` is stored exactly as given at
  1 ms resolution, with no step snapping and no range clamping; deciding
  what values are legal belongs to the caller's parser.
* **Corruption survivable, the future sacred.** An unparseable file is moved
  aside to ``<path>.bad`` and its entries come back from the backup sibling
  when that one parses; failing that the store starts empty, because data
  loss beats a jammed addon. A file from a newer schema is left untouched
  and the store goes read-only, so a downgraded build cannot clobber newer
  data.
* **One backup slot, rotated every persist.** ``<path>.bak`` holds the file
  as it was before the most recent persist ATTEMPT: rotation runs ahead of
  the write and must stay there, since rotating afterwards would copy the
  file just written. The slot trails the live file by a single write —
  including a write the addon makes on its own, such as consuming a reset
  marker — so a restore can resurrect the latest deletion without its reset
  marker. Rotation is best-effort insurance: a failure is logged and the
  persist proceeds. It only ever copies a file this store wrote: the
  rebuilding persist a restore issues skips it, and a quarantine disarms it
  until a persist succeeds, so a corrupt file still sitting at the live path
  can never reach the slot.
* **Atomic-swap durability.** Every persist writes a sibling ``.tmp``,
  flushes and ``fsync``s it, then ``os.replace``s it over the target. The
  swap is atomic on POSIX and NTFS, so a power loss leaves either the old
  file or the new one.
* **Canonical keys.** Every key crossing the store boundary (file load, the
  other-process reader, a restored backup) is re-expressed through
  ``keys.canonical_key``, so entries and markers written by an older key
  codec keep resolving as the spelling rules evolve. This is also the whole
  schema migration, expanding v1 and v2 keys in place with no separate
  migration code. On a spelling collision the canonically-spelled entry wins.
* **Deletion leaves a reset marker.** ``delete``/``clear``, and an import
  that drops keys, record the removed keys in a ``resets`` section. The user
  expects 0 the next time that profile plays, but Kodi's own per-file memory
  still holds the old value, so the marker lets the applier force the 0 once,
  bypassing its "never act first" guard. Markers are consumed by the applier,
  superseded by a new ``set``, and invisible to the management view. The
  section is additive, so it needs no schema bump.
"""

import json
import math
import os
import time
from collections import namedtuple
from datetime import datetime, timezone

from resources.lib.aome.store import keys

_PREFIX = "AOMe_OffsetStore:"
# 3 = five-segment keys (the output-device axis); 2 added channels to the
# original three. Older files load fine, since canonical_key expands them
# with trailing 'all' segments, and the first persist rewrites the file at
# this version, at which point a downgraded build goes read-only on it.
_SCHEMA_VERSION = 3

# The outcomes pop_corruption() reports.
CORRUPTION_QUARANTINED = "quarantined"
CORRUPTION_RECOVERED = "recovered"

# What copy_device() reports for one destination: the segment written to,
# the keys written there, and the keys left alone because it already held
# them.
DeviceCopy = namedtuple("DeviceCopy", "device copied skipped")

# What copy_device() reports overall: the totals, whether the file reflects
# the result, and the per-destination breakdown.
CopyResult = namedtuple("CopyResult", "copied skipped durable devices")


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

    Raised by the read-only readers, since the script process must never
    quarantine or mutate the file: instead of ``load()``'s .bad rename it
    reports why the view cannot render.

    ``future`` is True for the newer-schema case, which the view words
    differently: the service preserves such a file untouched rather than
    quarantining it, so corruption wording would falsely promise a reset.
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

    Shared by ``load()`` and the backup reader so a scribbled marker
    degrades identically everywhere, to "no pending reset" rather than to a
    crash or a spurious 0.
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

    Not ``OffsetStore.load()``: only the service's dispatcher thread may
    touch the file, so this has no quarantine, no corruption flag and no
    instance state. A missing file reads as an empty store; anything
    unpresentable raises :class:`StoreUnreadable`.
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
    replacing the store. Same rules as :func:`read_profiles` except that a
    missing file raises :class:`StoreUnreadable` rather than reading as an
    empty store, since a restore source that is not there is a failed import
    rather than "replace everything with nothing".

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

    Lives here so the app-layer mutation handler does no direct file I/O. A
    missing file is the normal case; any other failure is logged and
    swallowed, since a stale staging file is inert (the script process
    overwrites it before every import request).
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
        self._corruption = None
        self._live_file_trusted = True

    # -- loading --------------------------------------------------------------

    def load(self):
        """Read the file once, populating in-memory state.

        Missing file → empty and writable (normal first run). Unreadable or
        malformed → the file is renamed to ``<path>.bad`` and we start from
        the backup sibling, or empty, writable either way and with the
        corruption flag saying which. A future schema version → the file is
        left untouched and the store becomes read-only.
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

        self._adopt(data)

    def _adopt(self, data):
        """Populate memory from a parsed, shape-checked document."""
        self._profiles = self._load_entries(data["profiles"])
        # A marker whose canonical key now holds an entry is superseded,
        # mirroring set(). Runtime writes never produce that coexistence, so
        # it can only come from re-keying a legacy spelling, where the
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
        """Move a corrupt file aside, then rebuild it from the backup."""
        self._live_file_trusted = False
        bad = self._path + ".bad"
        try:
            os.replace(self._path, bad)
        except OSError as error:
            # Losing the quarantine rename is non-fatal: the load carries on.
            self._log_warning("{0} could not rename to .bad ({1})"
                              .format(_PREFIX, error))
        self._profiles = {}
        self._resets = set()
        self._corruption = CORRUPTION_QUARANTINED
        self._restore_backup()

    def _restore_backup(self):
        """Adopt the backup sibling in place of the quarantined file.

        A backup that is absent, unreadable or itself unusable writes
        nothing, leaving the empty state and the plain quarantine flag.
        """
        try:
            with open(self._path + ".bak", "r", encoding="utf-8") as handle:
                raw = handle.read()
        except FileNotFoundError:
            return
        except OSError as error:
            self._log_warning("{0} backup unreadable ({1})"
                              .format(_PREFIX, error))
            return
        try:
            data = _parse_document(raw)
        except StoreUnreadable as error:
            self._log_warning("{0} backup unusable ({1})"
                              .format(_PREFIX, error))
            return

        self._adopt(data)
        self._corruption = CORRUPTION_RECOVERED
        self._log_warning("{0} restored {1} entries from the backup"
                          .format(_PREFIX, len(self._profiles)))
        if not self._persist(rotate=False):
            self._log_warning("{0} restored entries are in memory only"
                              .format(_PREFIX))

    def pop_corruption(self):
        """Return the load's corruption outcome and clear it (one-shot).

        None when nothing was quarantined, else ``CORRUPTION_QUARANTINED``
        (the store started empty) or ``CORRUPTION_RECOVERED``.
        """
        outcome = self._corruption
        self._corruption = None
        return outcome

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

    def set(self, key, delay_ms, *, source="user", video_fps=None,
            device_name=None):
        """Store an offset for ``key``, persist, and report success.

        ``key`` must be a non-empty str and ``delay_ms`` an int (bool
        rejected); violating either raises ValueError, since that is a
        programmer error rather than a runtime condition. A fresh ``updated``
        timestamp is stamped every call.

        ``video_fps`` and ``device_name`` are optional display metadata for
        the management view, validated at the door because a malformed value
        would outlive the call inside the file. A blank ``device_name`` is
        treated as absent and not written, so the view falls back to the id
        segment. Returns False after a warning if the store is read-only or
        the write fails.
        """
        if not isinstance(key, str) or not key:
            raise ValueError("key must be a non-empty str")
        if not _is_int(delay_ms):
            raise ValueError("delay_ms must be an int")
        if video_fps is not None:
            # Metadata only, but NaN/Infinity would serialize as bare tokens
            # that stricter JSON readers reject, so refuse at the door rather
            # than poison the file.
            if isinstance(video_fps, bool) or \
                    not isinstance(video_fps, (int, float)) or \
                    not math.isfinite(video_fps):
                raise ValueError("video_fps must be a finite number or None")
        if device_name is not None and not isinstance(device_name, str):
            raise ValueError("device_name must be a str or None")

        if self._read_only:
            self._log_warning("{0} read-only; refusing set({1!r})"
                              .format(_PREFIX, key))
            return False

        self._profiles[key] = self._compose_entry(delay_ms, source, video_fps,
                                                  device_name)
        # A fresh value supersedes any pending reset for the key: the user
        # re-learned the profile before it was ever played back.
        self._resets.discard(key)
        if not self._persist():
            return False
        return True

    def delete(self, key):
        """Remove ``key`` if present and persist; True only when both happen.

        The removed key is recorded as a reset marker. A missing key touches
        no disk, and a read-only store refuses. A persist failure also
        returns False, since the entry would resurrect on the next load,
        while the in-memory removal stands, consistent with ``set``.
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
        Persists only when something was removed, and returns 0 when
        read-only or when the persist failed, with the in-memory removal
        standing in that second case.
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

        Restore semantics, not merge: after this call the store holds exactly
        the given entries, filtered by the same rules as ``load()``. The
        reset markers merge three sources, all minus the imported keys: the
        live pending markers, every live key the import drops (which means
        "expect 0 next time", like ``delete``), and the backup's own pending
        markers. Refused when read-only; a persist failure returns False with
        the in-memory replacement standing, consistent with
        ``set``/``delete``/``clear``.
        """
        if self._read_only:
            self._log_warning("{0} read-only; refusing replace_all()"
                              .format(_PREFIX))
            return False
        replaced = self._load_entries(entries)
        # The caller normally passes the backup reader's already-canonical
        # output, but re-filtering keeps this method safe on its own.
        carried = self._load_resets(list(resets))
        self._resets = ((self._resets | set(self._profiles) | carried)
                        - set(replaced))
        self._profiles = replaced
        return self._persist()

    def copy_device(self, source_segment, destinations):
        """Seed each destination from the entries keyed on ``source_segment``.

        ``destinations`` is a sequence of ``(segment, device_name)`` pairs,
        the name being the display metadata stamped on the entries written
        there; a non-str name raises ValueError, as in ``set``.

        Each destination gets every source entry's key with its device
        segment swapped, carrying the same ``delay_ms`` and ``video_fps`` and
        a fresh timestamp. A key a destination already holds is SKIPPED,
        since what was taught there outranks a seed, and the source's own
        entries and reset markers stay untouched. A destination marker is
        superseded by the entry written over it, exactly as in ``set``.

        Returns a :class:`CopyResult` whose ``devices`` breaks the totals
        down per destination, in the order given. One persist covers the
        whole batch, and it runs only when something was written. A read-only
        store refuses.
        """
        targets = tuple(destinations)
        for _segment, device_name in targets:
            if device_name is not None and not isinstance(device_name, str):
                raise ValueError("device_name must be a str or None")
        if self._read_only:
            self._log_warning("{0} read-only; refusing copy_device({1!r})"
                              .format(_PREFIX, source_segment))
            return CopyResult(0, 0, False, ())
        written = {}
        per_device = []
        for segment, device_name in targets:
            copied = 0
            skipped = 0
            for key, entry in self._profiles.items():
                try:
                    parts = keys.split_key(key)
                except ValueError:
                    continue
                if parts[4] != source_segment:
                    continue
                target = keys.SEPARATOR.join(parts[:4] + (segment,))
                if target in self._profiles or target in written:
                    skipped += 1
                    continue
                written[target] = self._compose_entry(
                    entry["delay_ms"], "user", entry.get("video_fps"),
                    device_name)
                copied += 1
            per_device.append(DeviceCopy(segment, copied, skipped))
        devices = tuple(per_device)
        total_copied = sum(entry.copied for entry in devices)
        total_skipped = sum(entry.skipped for entry in devices)
        if not written:
            return CopyResult(0, total_skipped, True, devices)
        self._profiles.update(written)
        self._resets.difference_update(written)
        return CopyResult(total_copied, total_skipped, self._persist(),
                          devices)

    # -- reset markers ----------------------------------------------------------

    def reset_pending(self, key):
        """True when ``key`` was deleted and its forced 0 has not run yet."""
        return key in self._resets

    def consume_reset(self, key):
        """Discard the reset marker for ``key`` and persist the removal.

        Called by the applier once it has acted on the marker, by forcing the
        0 or finding the delay already there. Consuming an absent marker is a
        no-op returning True. A persist failure returns False; the in-memory
        removal stands and the reset simply repeats after a restart, which is
        harmless because it is idempotent.
        """
        if key not in self._resets:
            return True
        self._resets.discard(key)
        return self._persist()

    # -- internals ------------------------------------------------------------

    def _timestamp(self):
        moment = datetime.fromtimestamp(self._clock(), timezone.utc)
        return moment.strftime("%Y-%m-%dT%H:%M:%SZ")

    def _compose_entry(self, delay_ms, source, video_fps, device_name):
        """The stored entry's shape, shared by every write path."""
        entry = {
            "delay_ms": delay_ms,
            "updated": self._timestamp(),
            "source": source,
        }
        if video_fps is not None:
            entry["video_fps"] = video_fps
        if isinstance(device_name, str) and device_name.strip():
            entry["device_name"] = device_name
        return entry

    def _persist(self, *, rotate=True):
        """Serialize and atomically swap the file into place.

        On OSError the in-memory state is left as mutated (rolling back the
        dict would surprise a single-threaded caller more than a
        stale-on-disk file does) and False is returned so the caller can
        react to the durability miss.
        """
        if rotate:
            self._rotate_backup()
        payload = {"version": _SCHEMA_VERSION, "profiles": self._profiles}
        if self._resets:
            # Additive section, written only when markers exist.
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
        self._live_file_trusted = True
        return True

    def _rotate_backup(self):
        """Copy the live file onto ``.bak`` before this persist replaces it.

        Nothing to rotate when the target is absent.
        """
        if not self._live_file_trusted:
            return
        try:
            with open(self._path, "rb") as handle:
                blob = handle.read()
        except FileNotFoundError:
            return
        except OSError as error:
            self._log_warning("{0} backup rotation could not read the store "
                              "({1})".format(_PREFIX, error))
            return
        tmp = self._path + ".bak.tmp"
        try:
            with open(tmp, "wb") as handle:
                handle.write(blob)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, self._path + ".bak")
        except OSError as error:
            self._log_warning("{0} backup rotation failed ({1})"
                              .format(_PREFIX, error))
            try:
                os.remove(tmp)
            except OSError:
                pass

    def _replace_with_retry(self, tmp):
        """``os.replace`` with two short retries for Windows share violations.

        On Windows a concurrent reader holding the target open (the script
        process's ``read_profiles`` while the management view renders) makes
        ``os.replace`` fail with a sharing violation. That read window is
        sub-millisecond, so a brief retry closes the race; a persistent
        failure re-raises into ``_persist``'s handler.
        """
        for _attempt in range(2):
            try:
                os.replace(tmp, self._path)
                return
            except OSError:
                time.sleep(0.05)
        os.replace(tmp, self._path)
