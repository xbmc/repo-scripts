# SPDX-License-Identifier: GPL-2.0-only
"""Writing CrossWatch's changes into Kodi, and recognising the add-on's own writes.

Kodi announces a play-count write as VideoLibrary.OnUpdate, the same way it announces a
person's "mark as watched" (VideoDatabase.cpp SetPlayCount). OwnWrites remembers what the
add-on wrote, so the service thread can tell its echo from a person's mark: an entry lives
until its echo arrives, or a number of service-thread ticks after the write was read back,
because Kodi delivers announcements asynchronously and rating writes announce nothing.

Kodi's SetDetailsForEpisode copies the play count and last-played date from another watched
copy of the same episode onto the row it writes, silently (VideoDatabase.cpp ~3077-3098). Any
episode write, a rating included, can therefore change a play count; restore_copies puts it
back with a second write that sets it explicitly, which Kodi applies after the copy.

Log events: sync.writer.restored_copy (kodi_id), sync.writer.failed (kind, kodi_id, error),
sync.writer.batch (debug: writes, outcome, duration_ms).
"""
from __future__ import annotations

import threading
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from resources.lib.log import get_logger, log_timing
from resources.lib.media import strip_credentials
from resources.lib.sync.clock import kodi_to_utc, utc_to_kodi
from resources.lib.sync.constants import OWN_WRITE_TICKS
from resources.lib.sync.items import JsonRpc, Library, LibraryRow, RowKey, tokens
from resources.lib.sync.ownership import OwnersOf
from resources.lib.sync.record import Batch, ItemState, PendingWrite, RecordStore, Seen, merge
from resources.lib.sync.rules import kodi_fields, rule_met
from resources.lib.sync.settings import SyncSettings

_log = get_logger("sync")

_DETAILS = {
    "movies": ("VideoLibrary.GetMovieDetails", "movieid", "moviedetails"),
    "episodes": ("VideoLibrary.GetEpisodeDetails", "episodeid", "episodedetails"),
}
_ROW_PROPERTIES = {
    "movies": ["uniqueid", "title", "year", "file", "playcount", "lastplayed", "userrating", "resume", "dateadded"],
    "episodes": ["uniqueid", "title", "file", "playcount", "lastplayed", "userrating", "resume", "dateadded",
                 "tvshowid", "showtitle", "season", "episode"],
}  # fmt: skip


@dataclass
class _Noted:
    fields: dict[str, Any]
    write_id: str
    ticks_left: int | None = None


class OwnWrites:
    """The add-on's own writes not yet echoed, keyed by Kodi's item type and id.

    Thread-safe: the worker notes writes, the service thread matches announcements and ticks.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._noted: dict[tuple[str, int], list[_Noted]] = {}

    def note(self, kodi_type: str, kodi_id: int, fields: Mapping[str, Any], write_id: str) -> None:
        with self._lock:
            self._noted.setdefault((kodi_type, kodi_id), []).append(_Noted(dict(fields), write_id))

    def committed(self, write_id: str) -> None:
        """The write's read-back is committed: from now on its note lasts OWN_WRITE_TICKS."""
        with self._lock:
            for notes in self._noted.values():
                for note in notes:
                    if note.write_id == write_id and note.ticks_left is None:
                        note.ticks_left = OWN_WRITE_TICKS

    def tick(self) -> None:
        with self._lock:
            for key in list(self._noted):
                kept = []
                for note in self._noted[key]:
                    if note.ticks_left is not None:
                        note.ticks_left -= 1
                        if note.ticks_left <= 0:
                            continue
                    kept.append(note)
                if kept:
                    self._noted[key] = kept
                else:
                    del self._noted[key]

    def matches(self, kodi_type: str, kodi_id: int, data: Mapping[str, Any]) -> bool:
        """Whether an OnUpdate for this item is the echo of a noted write; a match uses it up.

        Kodi includes "playcount" only when the count changed, so an announcement without it
        matches any noted write to the item, and one with it only a write of that count.
        """
        with self._lock:
            notes = self._noted.get((kodi_type, kodi_id))
            if not notes:
                return False
            if "playcount" in data:
                candidates = [i for i, n in enumerate(notes) if n.fields.get("playcount") == data["playcount"]]
            else:
                # A write that didn't change the count; one waiting for its own count echo
                # is used last.
                candidates = sorted(range(len(notes)), key=lambda i: "playcount" in notes[i].fields)
            for index in candidates[:1]:
                del notes[index]
                if not notes:
                    del self._noted[(kodi_type, kodi_id)]
                return True
            return False

    def seed(self, writes: Iterable[PendingWrite]) -> None:
        """At start: writes sent before a crash and never read back are the add-on's own."""
        for write in writes:
            for row, fields in in_flight_rows(write).items():
                self.note(_kodi_type(row), row.kodi_id, fields, write.id)
            self.committed(write.id)


def _kodi_type(row: RowKey) -> str:
    return "movie" if row.kind == "movies" else "episode"


def in_flight_rows(write: PendingWrite) -> dict[RowKey, dict[str, Any]]:
    """The fields an intent sent per Kodi row and hasn't read back yet. One intent writes to
    every copy of its item, and a moved row is written at its new id, so they are kept per
    row (PendingWrite.in_flight = {"rows": [{"kind", "kodi_id", "file", "fields"}]})."""
    out: dict[RowKey, dict[str, Any]] = {}
    for item in (write.in_flight or {}).get("rows") or []:
        try:
            key = RowKey(write.row.library_id, item["kind"], int(item["kodi_id"]), str(item["file"]))
        except (KeyError, TypeError, ValueError):
            continue
        out[key] = dict(item.get("fields") or {})
    return out


def announcement_item(data: Mapping[str, Any]) -> tuple[str, int] | None:
    """The (Kodi type, id) an OnUpdate is about, from either shape Kodi sends: {"item":
    {"type", "id"}, ...} for a database write and {"type", "id"} for playback's own."""
    nested = data.get("item")
    item: Mapping[str, Any] = nested if isinstance(nested, Mapping) else data
    kodi_type, kodi_id = item.get("type"), item.get("id")
    if kodi_type not in ("movie", "episode") or not isinstance(kodi_id, int) or isinstance(kodi_id, bool):
        return None
    return kodi_type, kodi_id


def episode_counts(kodi: JsonRpc, kodi_id: int) -> tuple[int, str]:
    """An episode's play count and last-played date (UTC), as Kodi has them now."""
    details = kodi.jsonrpc(
        "VideoLibrary.GetEpisodeDetails", {"episodeid": kodi_id, "properties": ["playcount", "lastplayed"]}
    )
    episode = details.get("episodedetails") or {}
    return int(episode.get("playcount") or 0), kodi_to_utc(str(episode.get("lastplayed") or ""))


def restore_copies(kodi: JsonRpc, own: OwnWrites, kodi_id: int, before: tuple[int, str], write_id: str) -> bool:
    """Undo Kodi's copy of another episode's play count onto this one; True when it did.

    Raises what Kodi raises; the caller decides what a failed restore means. Its note is
    committed either way, so it expires rather than hiding a person's mark for ever.
    """
    now = episode_counts(kodi, kodi_id)
    if now == before:
        return False
    fields = {"playcount": before[0], "lastplayed": utc_to_kodi(before[1])}
    own.note("episode", kodi_id, fields, write_id)
    try:
        kodi.jsonrpc("VideoLibrary.SetEpisodeDetails", {"episodeid": kodi_id, **fields})
    finally:
        own.committed(write_id)
    _log.info("sync.writer.restored_copy", kodi_id=kodi_id)
    return True


def read_row(kodi: JsonRpc, row: RowKey, shows: Mapping[int, Mapping[str, Any]]) -> LibraryRow | None:
    """The row at this Kodi id now, or None when it's gone or is no longer the same file."""
    method, id_field, result_key = _DETAILS[row.kind]
    try:
        details = kodi.jsonrpc(method, {id_field: row.kodi_id, "properties": _ROW_PROPERTIES[row.kind]})
    except Exception:
        return None
    raw = details.get(result_key)
    if not isinstance(raw, dict):
        return None
    file = strip_credentials(str(raw.get("file") or ""))
    if file != row.file:
        # SQLite reuses the highest id: the same id may now be another item.
        return None
    converted = {**raw, "file": file}
    for name in ("lastplayed", "dateadded"):
        converted[name] = kodi_to_utc(str(raw.get(name) or ""))
    show_id = (int(raw.get("tvshowid") or 0) or None) if row.kind == "episodes" else None
    show = shows.get(show_id) if show_id is not None else None
    return LibraryRow(key=row, tokens=tuple(tokens(row.kind, converted, show)), raw=converted, show_kodi_id=show_id)


# -- the writer ---------------------------------------------------------------------------


@dataclass
class WriteReport:
    written: int = 0
    dropped: int = 0
    deferred: int = 0


def seen_of(raw: Mapping[str, Any]) -> Seen:
    resume = raw.get("resume") or {}
    return Seen(
        playcount=int(raw.get("playcount") or 0),
        lastplayed=str(raw.get("lastplayed") or ""),
        userrating=int(raw.get("userrating") or 0),
        resume={"position": float(resume.get("position") or 0), "total": float(resume.get("total") or 0)},
        dateadded=str(raw.get("dateadded") or ""),
    )


def _kodi_format(fields: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(fields)
    if "lastplayed" in out:
        out["lastplayed"] = utc_to_kodi(str(out["lastplayed"]))
    return out


def _landed(sent: Mapping[str, Any], raw: Mapping[str, Any]) -> bool:
    """Whether Kodi holds what was sent, compared as Kodi formats it."""
    for name, value in sent.items():
        if name == "resume":
            got = raw.get("resume") or {}
            if abs(float(got.get("position") or 0) - float(value.get("position") or 0)) >= 1:
                return False
        elif name == "lastplayed":
            if str(raw.get("lastplayed") or "")[:19] != str(value)[:19]:
                return False
        elif raw.get(name) != value:
            return False
    return True


_SET = {
    "movies": ("VideoLibrary.SetMovieDetails", "movieid"),
    "episodes": ("VideoLibrary.SetEpisodeDetails", "episodeid"),
}
BATCH = 5
MIN_GAP_SECONDS = 0.1


class Writer:
    """Brings Kodi in line with the record for every pending intent, a few writes at a time.

    Runs on the sync worker. Each intent is worked out from the record and a fresh read just
    before its write, so a change queued weeks ago never overwrites what happened in Kodi
    since. The fields of a write are stored as in flight before the request, so a crash
    before the read-back still knows the value in Kodi is the add-on's own.
    """

    def __init__(
        self,
        kodi: JsonRpc,
        store: RecordStore,
        own: OwnWrites,
        may_write: Callable[[], bool],
        clock: Callable[[], float],
        sleep: Callable[[float], None],
        *,
        settings: SyncSettings,
        library: Library,
        owners: OwnersOf,
        between_batches: Callable[[], None],
        now_utc: Callable[[], str],
        held_rows: Callable[[], frozenset[RowKey]] = frozenset,
    ) -> None:
        self._kodi, self._store, self._own = kodi, store, own
        self._may_write, self._clock, self._sleep = may_write, clock, sleep
        self._settings, self._library, self._owners = settings, library, owners
        self._between = between_batches
        self._now = now_utc
        self._held_rows = held_rows
        rows = [*library.movies, *library.episodes]
        self._by_token: dict[str, list[LibraryRow]] = {}
        for row in rows:
            for token in row.tokens:
                self._by_token.setdefault(token, []).append(row)
        self._by_file: dict[str, list[LibraryRow]] = {}
        for row in library.episodes:
            self._by_file.setdefault(row.key.file, []).append(row)

    def run(self) -> WriteReport:
        report = WriteReport()
        pending = self._store.pending_writes()
        while pending:
            if not self._may_write():
                report.deferred += len(pending)
                break
            batch, pending = pending[:BATCH], pending[BATCH:]
            started = self._clock()
            with log_timing(_log, "sync.writer.batch", writes=len(batch)):
                outcome = self._write_batch(batch)
            # Every intent that sent anything has its in-flight fields cleared and its notes
            # committed, whether it finished, waits or failed: the read-back is done, and a
            # note never committed would hide a person's mark for ever.
            self._store.commit(
                Batch(pending_done=outcome.done, in_flight={w: None for w in outcome.attempted}, seen=outcome.seen)
            )
            for write_id in outcome.attempted:
                self._own.committed(write_id)
            report.written += len(outcome.written)
            report.dropped += outcome.dropped
            report.deferred += outcome.deferred
            gap = max(self._clock() - started, MIN_GAP_SECONDS)
            self._between()
            if pending:
                self._sleep(gap)
        return report

    def _copies(self, write: PendingWrite) -> list[LibraryRow]:
        found: dict[RowKey, LibraryRow] = {}
        for token in write.tokens:
            for row in self._by_token.get(token, []):
                if row.key.kind == write.row.kind:
                    found[row.key] = row
        return sorted(found.values(), key=lambda r: r.key.kodi_id)

    def _states(self, row: LibraryRow) -> list[ItemState]:
        states = []
        for owner in self._owners(row):
            found = self._store.match(owner, row.tokens)
            if found:
                states.append(merge(found).state if len(found) > 1 else found[0].state)
        return states

    def _siblings(self, row: LibraryRow) -> list[LibraryRow]:
        if row.key.kind != "episodes":
            return []
        return [
            r for r in self._by_file.get(row.key.file, []) if r.key != row.key and not set(r.tokens) & set(row.tokens)
        ]

    def _read(self, key: RowKey) -> LibraryRow | None:
        if not self._may_write():
            raise _Stop
        return read_row(self._kodi, key, self._library.tvshows)

    def _write_batch(self, batch: list[PendingWrite]) -> _BatchOutcome:
        out = _BatchOutcome()
        for write in batch:
            try:
                self._write_one(write, out)
            except _Stop:
                out.deferred += 1
        return out

    def _write_one(self, write: PendingWrite, out: _BatchOutcome) -> None:
        if not self._may_write():
            raise _Stop
        fresh = [r for r in (self._read(c.key) for c in self._copies(write)) if r is not None]
        if not fresh:
            # Not in the library now (or moved and not read yet): stays pending.
            out.deferred += 1
            return
        if write.group == "ratings" and self._held_rows() & {r.key for r in fresh}:
            # A row held for the household's answer on many rating changes: CrossWatch's
            # rating waits for that answer instead of being dropped as a person's change.
            out.deferred += 1
            return
        if write.group == "ratings" and any(
            (seen := self._store.seen(r.key)) is not None and int(r.raw.get("userrating") or 0) != seen.userrating
            for r in fresh
        ):
            # A person rated one copy and the scan hasn't seen it yet: their rating goes up
            # first; writing CrossWatch's over the other copies would split them.
            out.done.append(write.id)
            out.dropped += 1
            return
        sent_any = waiting = False
        flights: list[dict[str, Any]] = []
        for row in fresh:
            fields = self._fields_for(write, row, copies=len(fresh))
            if fields is None:
                waiting = True
                continue
            if not fields:
                continue
            result = self._send(write, row, fields, flights, out)
            if result is None:
                waiting = True
            elif result:
                sent_any = True
        if waiting:
            out.deferred += 1
            return
        out.done.append(write.id)
        if sent_any:
            out.written.append(write.id)
        else:
            out.dropped += 1

    def _fields_for(self, write: PendingWrite, row: LibraryRow, copies: int) -> dict[str, Any] | None:
        """The fields for one copy; {} for nothing to write; None to wait (multi-episode file)."""
        states = self._states(row)
        seen = self._store.seen(row.key)
        kodi_now = seen_of(row.raw)
        siblings = self._siblings(row)
        sibling_states = [[st.history for st in self._states(s)] for s in siblings]
        siblings_watched = any(rule_met(h, self._settings) for h in sibling_states)
        if write.group == "ratings" and seen is None and copies > 1 and kodi_now.userrating == 0:
            # Filling an empty rating on one of several copies would make the copies
            # disagree; the rating scan reconciles copies instead (L-42).
            return {}
        fields = kodi_fields(write.group, owners=states, kodi=kodi_now, seen=seen, siblings_watched=siblings_watched,
                             settings=self._settings, now_utc=self._now(), fetched_at=write.fetched_at)  # fmt: skip
        if write.group == "history" and fields.get("playcount", 0) > kodi_now.playcount and siblings:
            # Kodi keeps one play count per file, so a raise on a file holding several
            # episodes raises them all: it waits until every one qualifies, and never raises
            # an episode a person unwatched here (L-01).
            ready = all(
                rule_met(h, self._settings) and not any(x.local_unwatch for x in h) for h in sibling_states
            ) and all(sibling_states)
            if not ready:
                return None
        return fields

    def _send(
        self,
        write: PendingWrite,
        row: LibraryRow,
        fields: dict[str, Any],
        flights: list[dict[str, Any]],
        out: _BatchOutcome,
    ) -> bool | None:
        """True when the write landed, False when Kodi holds something else, None when the
        request failed or the writer had to stop."""
        method, id_field = _SET[row.key.kind]
        kodi_type = _kodi_type(row.key)
        sent = _kodi_format(fields)
        try:
            before = None
            if row.key.kind == "episodes" and write.group != "history":
                if not self._may_write():
                    raise _Stop
                before = episode_counts(self._kodi, row.key.kodi_id)
            # Stored before the request: a crash before the read-back must still know it's ours.
            flights.append({"kind": row.key.kind, "kodi_id": row.key.kodi_id, "file": row.key.file, "fields": sent})
            self._store.commit(Batch(in_flight={write.id: {"rows": list(flights)}}))
            self._own.note(kodi_type, row.key.kodi_id, sent, write.id)
            out.attempted.add(write.id)
            if not self._may_write():
                raise _Stop
            self._kodi.jsonrpc(method, {id_field: row.key.kodi_id, **sent})
            if before is not None:
                restore_copies(self._kodi, self._own, row.key.kodi_id, before, f"{write.id}-restore")
            after = self._read(row.key)
        except _Stop:
            raise
        except Exception as exc:
            _log.warning("sync.writer.failed", kind=row.key.kind, kodi_id=row.key.kodi_id, error=str(exc))
            return None
        if after is None:
            return False
        raw_after = {**after.raw, "lastplayed": utc_to_kodi(str(after.raw.get("lastplayed") or ""))}
        landed = _landed(sent, raw_after)
        stored = self._store.seen(row.key)
        now_seen = seen_of(after.raw)
        if stored is not None:
            keep: dict[str, Any] = {}
            if "userrating" not in fields:
                # Only the rating scan and the add-on's own rating writes say what rating
                # was seen.
                keep.update(userrating=stored.userrating, dateadded=stored.dateadded)
            if "lastplayed" in fields:
                # "The last play here" stays what Kodi showed before the add-on's own write,
                # so a resume decided later isn't judged against the add-on's own date.
                keep.update(lastplayed=stored.lastplayed)
            now_seen = replace(now_seen, **keep)
        out.seen[row.key] = now_seen
        return landed


class _Stop(Exception):
    """may_write turned False mid-intent: playback started or the service is stopping."""


@dataclass
class _BatchOutcome:
    done: list[str] = field(default_factory=list)
    written: list[str] = field(default_factory=list)
    attempted: set[str] = field(default_factory=set)
    seen: dict[RowKey, Seen | None] = field(default_factory=dict)
    dropped: int = 0
    deferred: int = 0
