# SPDX-License-Identifier: GPL-2.0-only
"""The per-viewer sync record: what each viewer's history, ratings and resume points are,
as the add-on last told CrossWatch and as CrossWatch's queued changes left them.

Everything durable library sync knows lives here, in one SQLite file (sync.db). Every change
to the household's record is one Batch committed in one transaction, which is what keeps a
crash between applying a change, acking it, writing Kodi and uploading from losing or
double-counting anything: either the whole step is in the file or none of it is. The upload
bookkeeping (seq reservations, epochs, settled, the last delta) is written by its own small
transactions, each complete on its own.

The record is keyed by sync id alone. CrossWatch counts uploads per device and viewer, not
per paired address, so the same CrossWatch at a new address continues the same record.

A missing or unreadable file raises RecordMissing instead of starting empty: an empty record
uploaded against CrossWatch's surviving state would look like a household that unwatched
everything. Only Start creates the file.

Log events: none; the engine logs what a batch did.
"""
from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict, dataclass, field, replace
from typing import Any, Literal

from resources.lib.sync.constants import ACKED_SEQS_KEPT
from resources.lib.sync.items import ItemKind, RowKey

SCHEMA_VERSION = 2
Group = Literal["history", "ratings", "progress"]
# CrossWatch's group names (_addon_sync.py GROUPS).
GROUPS: tuple[Group, ...] = ("history", "ratings", "progress")
Origin = Literal["seed", "empty", "cw", "person"]


class RecordMissing(Exception):
    """sync.db is absent or unreadable; sync stops until the user runs Start."""


# -- states -------------------------------------------------------------------------------


@dataclass(frozen=True)
class History:
    watched: bool = False
    playcount: int = 0
    lastplayed: str = ""
    # An explicit unwatch, from CrossWatch or from a person, as CrossWatch's own flag.
    explicit: bool = False
    # A person's unwatch made in Kodi with "Send removals" on, still to go up as
    # unwatched: true. Never set by a CrossWatch change.
    unwatched: bool = False
    # A person unwatched it in Kodi with "Send removals" off: the record keeps the watch for
    # the household's services, but Kodi is not raised again until a newer watch arrives.
    local_unwatch: bool = False
    # The first upload_seq after that unwatch: only a CrossWatch watch with `after` at or above
    # it was made after the unwatch, and lifts it.
    local_unwatch_seq: int = 0
    event: int = 0
    src: int = 0


@dataclass(frozen=True)
class Rating:
    value: int = 0
    # Set when a queued CrossWatch rating was applied, so "Send existing ratings" never fills
    # a rating CrossWatch removed.
    from_cw: bool = False
    # A deliberate removal, by CrossWatch or by a person in Kodi; only this clears Kodi's
    # rating, never an owner who simply hasn't rated it.
    removed: bool = False
    src: int = 0


@dataclass(frozen=True)
class Resume:
    position: float = 0.0
    total: float = 0.0
    at: str = ""
    src: int = 0


@dataclass(frozen=True)
class ItemState:
    history: History = field(default_factory=History)
    rating: Rating = field(default_factory=Rating)
    resume: Resume = field(default_factory=Resume)


def fresh_state() -> ItemState:
    return ItemState()


def _state_from(raw: Mapping[str, Any]) -> ItemState:
    def pick(cls: Any, data: Any) -> Any:
        known = cls.__dataclass_fields__
        return cls(**{k: v for k, v in (data or {}).items() if k in known})

    return ItemState(
        history=pick(History, raw.get("history")),
        rating=pick(Rating, raw.get("rating")),
        resume=pick(Resume, raw.get("resume")),
    )


@dataclass(frozen=True)
class Entry:
    key: str
    tokens: frozenset[str]
    meta: dict[str, Any]
    state: ItemState
    # Group -> UTC time of a person's change not yet settled with CrossWatch.
    unsent: dict[str, str] = field(default_factory=dict)
    # Group -> upload_seq of the accepted upload that carried the person's change; a queued
    # change with `after` at or above it was made after CrossWatch saw it (contract, Queue).
    unsent_upload: dict[str, int] = field(default_factory=dict)
    touched: bool = False
    origin: Origin = "empty"
    # Kodi's rating as the first full stored it, for "Send existing ratings".
    seed_rating: int = 0
    # Raised by every change, so a commit can tell an entry changed after its upload was built.
    change_count: int = 0
    # Group -> seq of a queued CrossWatch change applied to the record and not yet carried by
    # an accepted upload; a merge ranks it above states CrossWatch already has.
    applied_change: dict[str, int] = field(default_factory=dict)
    # Group -> that change's `after`: the upload_seq CrossWatch had seen when it was queued.
    applied_after: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class Seen:
    """A Kodi row as the add-on last read it, in UTC."""

    playcount: int = 0
    lastplayed: str = ""
    userrating: int = 0
    resume: dict[str, Any] = field(default_factory=dict)
    dateadded: str = ""


@dataclass(frozen=True)
class PendingWrite:
    """An intent to bring one group of one item in Kodi in line with the record. Fields are
    worked out when it is written, from the record and a fresh read, never stored here."""

    id: str
    row: RowKey
    tokens: frozenset[str]
    group: Group
    created: str
    fetched_at: str = ""
    # The fields of a write sent but not yet read back, stored before the RPC, so a crash in
    # between can't make the add-on's own write look like a person's change.
    in_flight: dict[str, Any] | None = None


@dataclass(frozen=True)
class Assignment:
    """A hand change on a shared item, waiting for the household to say whose it was."""

    id: str
    entry_key: str
    tokens: frozenset[str]
    group: Literal["history", "ratings"]
    value: ItemState
    title: str
    at: str
    # The item's info as the mark found it, so an entry made from the assignment can go up
    # as a removed row CrossWatch can place, should the item leave the library meanwhile.
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SeqState:
    # Highest upload_seq reserved, committed before the send.
    sent: int = 0
    # Highest upload_seq CrossWatch answered ok for.
    confirmed: int = 0
    # Raised whenever an upload for the viewer starts or ends.
    epoch: int = 0


@dataclass(frozen=True)
class Acked:
    """A queued change the add-on acked. seq and change_id together identify it, so a
    redelivery is recognised and an old ack never confirms a newer change, even after a
    restore of CrossWatch's state (contract, Queue)."""

    seq: int
    change_id: str
    entry_key: str
    group: str


@dataclass(frozen=True)
class Carried:
    """What an accepted upload carried for one entry, as it stood when the upload was built.

    groups maps each carried group to the upload's upload_seq, for a person change it held;
    change_count guards those: a later change to the entry keeps its person change unsettled.
    applied maps each carried group to the applied CrossWatch change seq it held, cleared only
    while the entry still holds that same seq for the group.
    """

    change_count: int
    groups: dict[str, int]
    applied: dict[str, int] = field(default_factory=dict)


@dataclass
class Batch:
    """Every change one engine step makes, committed together. Maps are keyed by sync id."""

    entries: dict[str, list[Entry]] = field(default_factory=dict)
    removed_entries: dict[str, list[str]] = field(default_factory=dict)
    # viewer -> surviving key -> keys merged into it.
    merged: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    seen: dict[RowKey, Seen | None] = field(default_factory=dict)
    # The tokens of rows whose Seen is written, so seen_for_tokens finds it after the row goes.
    seen_tokens: dict[RowKey, tuple[str, ...]] = field(default_factory=dict)
    pending_add: list[PendingWrite] = field(default_factory=list)
    pending_done: list[str] = field(default_factory=list)
    in_flight: dict[str, dict[str, Any] | None] = field(default_factory=dict)
    assignments_add: list[Assignment] = field(default_factory=list)
    assignments_done: list[str] = field(default_factory=list)
    applied_seq: dict[str, int] = field(default_factory=dict)
    acked_add: dict[str, list[Acked]] = field(default_factory=dict)
    acks_add: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    # viewer -> (seq, change_id) of acks CrossWatch answered.
    acks_done: dict[str, list[tuple[int, str]]] = field(default_factory=dict)
    # viewer -> entry -> what an accepted upload carried for it, every entry it carried.
    unsent_carried: dict[str, dict[str, Carried]] = field(default_factory=dict)
    # When that upload was accepted (UTC); a carried entry unchanged since is no longer
    # touched, so the next delta leaves it out. Also the viewer's last upload time.
    uploaded_at: str = ""
    # viewer -> entry -> groups whose person change is settled.
    unsent_cleared: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    full_library_id: dict[str, str] = field(default_factory=dict)
    first_full_done: set[str] = field(default_factory=set)
    # Viewers whose fresh full was accepted.
    fresh_done: set[str] = field(default_factory=set)
    # The highest inbox record id this batch applied: the inbox file is another database,
    # so a crash between this commit and the inbox's removal must not apply a mark twice.
    inbox_applied: int = 0


# -- store --------------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (name TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS entries (
    viewer TEXT, key TEXT, body TEXT, PRIMARY KEY (viewer, key));
CREATE TABLE IF NOT EXISTS tokens (
    viewer TEXT, token TEXT, key TEXT, PRIMARY KEY (viewer, token, key));
CREATE TABLE IF NOT EXISTS aliases (
    viewer TEXT, old_key TEXT, new_key TEXT, PRIMARY KEY (viewer, old_key));
CREATE TABLE IF NOT EXISTS seen (
    library_id TEXT, kind TEXT, kodi_id INTEGER, file TEXT, body TEXT,
    PRIMARY KEY (library_id, kind, kodi_id, file));
CREATE TABLE IF NOT EXISTS seen_by_token (token TEXT PRIMARY KEY, body TEXT, stamp INTEGER);
CREATE TABLE IF NOT EXISTS pending (id TEXT PRIMARY KEY, body TEXT);
CREATE TABLE IF NOT EXISTS assignments (id TEXT PRIMARY KEY, body TEXT);
CREATE TABLE IF NOT EXISTS viewers (viewer TEXT PRIMARY KEY, body TEXT);
CREATE TABLE IF NOT EXISTS acked (
    viewer TEXT, seq INTEGER, change_id TEXT, key TEXT, grp TEXT, PRIMARY KEY (viewer, seq, change_id, grp));
CREATE TABLE IF NOT EXISTS acks_pending (
    viewer TEXT, seq INTEGER, change_id TEXT, body TEXT, PRIMARY KEY (viewer, seq, change_id));
"""


@dataclass(frozen=True)
class _ViewerRow:
    applied_seq: int = 0
    sent: int = 0
    confirmed: int = 0
    epoch: int = 0
    first_full: bool = False
    settled: bool = False
    full_library_id: str = ""
    first_mapped_at: str = ""
    last_delta: list[list[Any]] = field(default_factory=list)
    # The record was older than CrossWatch: the next full goes "fresh" until one is accepted.
    fresh_pending: bool = False
    # When the first complete full was accepted (UTC), for the settled first round.
    first_full_at: str = ""
    # When CrossWatch last accepted an upload for this viewer (UTC), for the status screen.
    last_upload_at: str = ""


def _dump(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _entry_body(entry: Entry) -> str:
    body = asdict(entry)
    body["tokens"] = sorted(entry.tokens)
    return _dump(body)


def _entry_from(body: str) -> Entry:
    raw = json.loads(body)
    return Entry(
        key=raw["key"],
        tokens=frozenset(raw.get("tokens") or ()),
        meta=dict(raw.get("meta") or {}),
        state=_state_from(raw.get("state") or {}),
        unsent=dict(raw.get("unsent") or {}),
        unsent_upload={k: int(v) for k, v in (raw.get("unsent_upload") or {}).items()},
        touched=bool(raw.get("touched")),
        origin=raw.get("origin") or "empty",
        seed_rating=int(raw.get("seed_rating") or 0),
        change_count=int(raw.get("change_count") or 0),
        applied_change={k: int(v) for k, v in (raw.get("applied_change") or {}).items()},
        applied_after={k: int(v) for k, v in (raw.get("applied_after") or {}).items()},
    )


def _seen_from(body: str) -> Seen:
    raw = json.loads(body)
    return Seen(**{k: v for k, v in raw.items() if k in Seen.__dataclass_fields__})


def _pending_body(write: PendingWrite) -> str:
    body = asdict(write)
    body["tokens"] = sorted(write.tokens)
    return _dump(body)


def _pending_from(body: str) -> PendingWrite:
    raw = json.loads(body)
    row = raw["row"]
    kind: ItemKind = row["kind"]
    return PendingWrite(
        id=raw["id"],
        row=RowKey(row["library_id"], kind, int(row["kodi_id"]), row["file"]),
        tokens=frozenset(raw.get("tokens") or ()),
        group=raw["group"],
        created=raw["created"],
        fetched_at=raw.get("fetched_at") or "",
        in_flight=raw.get("in_flight"),
    )


def _assignment_body(a: Assignment) -> str:
    body = asdict(a)
    body["tokens"] = sorted(a.tokens)
    return _dump(body)


def _assignment_from(body: str) -> Assignment:
    raw = json.loads(body)
    return Assignment(
        id=raw["id"],
        entry_key=raw["entry_key"],
        tokens=frozenset(raw.get("tokens") or ()),
        group=raw["group"],
        value=_state_from(raw.get("value") or {}),
        title=raw.get("title") or "",
        at=raw.get("at") or "",
        meta=raw.get("meta") or {},
    )


class RecordStore:
    """sync.db, used from one thread (the sync worker), plus Start's one write in a script.

    Writes take BEGIN IMMEDIATE with a busy timeout, so Start running in another
    interpreter waits for the worker's transaction instead of failing. The worker's timeout
    stays under its stop budget; Start passes a longer one.
    """

    def __init__(
        self, path: str, connect: Callable[..., sqlite3.Connection] = sqlite3.connect, busy_timeout: float = 1.5
    ) -> None:
        self._path = path
        self._connect = connect
        self._timeout = busy_timeout
        self._conn: sqlite3.Connection | None = None
        # Counts committed batches, so a reader can tell the record changed since it looked.
        self.commits = 0

    def open(self, create: bool = False) -> None:
        """Open sync.db. Without create, a file that isn't there stays absent: it is opened
        read-write only, so one removed after a check is never recreated empty. A busy file
        raises sqlite3.OperationalError, which means try later, not a lost record."""
        if create:
            os.makedirs(os.path.dirname(self._path) or ".", mode=0o700, exist_ok=True)
            target, uri = self._path, False
        else:
            if not os.path.exists(self._path):
                raise RecordMissing(self._path)
            target, uri = f"file:{self._path}?mode=rw", True
        conn: sqlite3.Connection | None = None
        try:
            conn = self._connect(target, timeout=self._timeout, isolation_level=None, uri=uri)
            if create:
                conn.executescript(_SCHEMA)
                conn.execute("INSERT OR IGNORE INTO meta VALUES ('schema', ?)", (str(SCHEMA_VERSION),))
            row = conn.execute("SELECT value FROM meta WHERE name = 'schema'").fetchone()
        except sqlite3.OperationalError as exc:
            if conn is not None:
                conn.close()
            if "locked" in str(exc) or "busy" in str(exc):
                raise
            raise RecordMissing(self._path) from exc
        except sqlite3.DatabaseError as exc:
            if conn is not None:
                conn.close()
            raise RecordMissing(self._path) from exc
        if row is None or row[0] != str(SCHEMA_VERSION):
            conn.close()
            raise RecordMissing(self._path)
        self._conn = conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    @property
    def _db(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RecordMissing(self._path)
        return self._conn

    # -- reads ------------------------------------------------------------------------

    def resolve(self, viewer: str, key: str) -> str:
        """The key an entry has now, following merges."""
        for _ in range(32):
            row = self._db.execute(
                "SELECT new_key FROM aliases WHERE viewer = ? AND old_key = ?", (viewer, key)
            ).fetchone()
            if row is None:
                return key
            key = row[0]
        return key

    def entry(self, viewer: str, key: str) -> Entry | None:
        row = self._db.execute(
            "SELECT body FROM entries WHERE viewer = ? AND key = ?", (viewer, self.resolve(viewer, key))
        ).fetchone()
        return _entry_from(row[0]) if row else None

    def match(self, viewer: str, tokens: Iterable[str]) -> list[Entry]:
        """Every entry sharing any token, in key order."""
        wanted = sorted(set(tokens))
        if not wanted:
            return []
        marks = ",".join("?" * len(wanted))
        rows = self._db.execute(
            f"SELECT DISTINCT e.body FROM tokens t JOIN entries e ON e.viewer = t.viewer AND e.key = t.key "  # noqa: S608
            f"WHERE t.viewer = ? AND t.token IN ({marks}) ORDER BY e.key",
            (viewer, *wanted),
        ).fetchall()
        return [_entry_from(r[0]) for r in rows]

    def entries(self, viewer: str) -> list[Entry]:
        rows = self._db.execute("SELECT body FROM entries WHERE viewer = ? ORDER BY key", (viewer,)).fetchall()
        return [_entry_from(r[0]) for r in rows]

    def seen(self, row: RowKey) -> Seen | None:
        found = self._db.execute(
            "SELECT body FROM seen WHERE library_id = ? AND kind = ? AND kodi_id = ? AND file = ?",
            (row.library_id, row.kind, row.kodi_id, row.file),
        ).fetchone()
        return _seen_from(found[0]) if found else None

    def seen_for_library(self, library_id: str) -> dict[RowKey, Seen]:
        rows = self._db.execute(
            "SELECT kind, kodi_id, file, body FROM seen WHERE library_id = ?", (library_id,)
        ).fetchall()
        return {RowKey(library_id, r[0], int(r[1]), r[2]): _seen_from(r[3]) for r in rows}

    def seen_for_tokens(self, tokens: Iterable[str], file: str) -> Seen | None:
        """The newest Seen stored for a row sharing the file or a token, kept after that row
        left the library, so a returning item can be caught up.

        Newest, because a person's later unwatch must win over a watched state stored before
        it. The same file wins over a token match. Among rows stored by the same read, a
        watched copy wins over an unwatched one. Files are only kept for movies: one episode
        file can hold several episodes, each with its own state.
        """

        def newest(keys: list[str]) -> Seen | None:
            if not keys:
                return None
            marks = ",".join("?" * len(keys))
            rows = self._db.execute(
                f"SELECT body, stamp FROM seen_by_token WHERE token IN ({marks})",  # noqa: S608
                keys,
            ).fetchall()
            if not rows:
                return None
            best = max(rows, key=lambda r: (r[1] or 0, _seen_from(r[0]).playcount))
            return _seen_from(best[0])

        return newest([f"file:{file}"] if file else []) or newest(sorted(set(tokens)))

    def pending_writes(self) -> list[PendingWrite]:
        rows = self._db.execute("SELECT body FROM pending ORDER BY id").fetchall()
        return [_pending_from(r[0]) for r in rows]

    def assignments(self) -> list[Assignment]:
        rows = self._db.execute("SELECT body FROM assignments ORDER BY id").fetchall()
        return [_assignment_from(r[0]) for r in rows]

    def acks_pending(self, viewer: str) -> list[dict[str, Any]]:
        rows = self._db.execute("SELECT body FROM acks_pending WHERE viewer = ? ORDER BY seq", (viewer,)).fetchall()
        return [json.loads(r[0]) for r in rows]

    def acked(self, viewer: str, seq: int, change_id: str) -> list[Acked]:
        """The groups this change was acked for, with entry keys resolved through merges."""
        rows = self._db.execute(
            "SELECT key, grp FROM acked WHERE viewer = ? AND seq = ? AND change_id = ?", (viewer, seq, change_id)
        ).fetchall()
        return [Acked(seq=seq, change_id=change_id, entry_key=self.resolve(viewer, r[0]), group=r[1]) for r in rows]

    def _viewer(self, viewer: str) -> _ViewerRow:
        row = self._db.execute("SELECT body FROM viewers WHERE viewer = ?", (viewer,)).fetchone()
        if row is None:
            return _ViewerRow()
        raw = json.loads(row[0])
        return _ViewerRow(**{k: v for k, v in raw.items() if k in _ViewerRow.__dataclass_fields__})

    def applied_seq(self, viewer: str) -> int:
        return self._viewer(viewer).applied_seq

    def seqs(self, viewer: str) -> SeqState:
        v = self._viewer(viewer)
        return SeqState(sent=v.sent, confirmed=v.confirmed, epoch=v.epoch)

    def first_full_committed(self, viewer: str) -> bool:
        return self._viewer(viewer).first_full

    def settled(self, viewer: str) -> bool:
        return self._viewer(viewer).settled

    def full_library_id(self, viewer: str) -> str:
        return self._viewer(viewer).full_library_id

    def first_mapped_at(self, viewer: str) -> str:
        return self._viewer(viewer).first_mapped_at

    def last_delta(self, viewer: str) -> list[tuple[int, bytes]]:
        return [(int(seq), bytes.fromhex(body)) for seq, body in self._viewer(viewer).last_delta]

    def _meta(self, name: str) -> str | None:
        row = self._db.execute("SELECT value FROM meta WHERE name = ?", (name,)).fetchone()
        return row[0] if row else None

    def seed_viewers(self) -> frozenset[str]:
        raw = self._meta("seed_viewers")
        return frozenset(json.loads(raw)) if raw else frozenset()

    def seed_started_at(self) -> str:
        return self._meta("seed_started_at") or ""

    # -- writes -----------------------------------------------------------------------

    def _rollback(self) -> None:
        # SQLite may already have rolled back after an I/O error; a second ROLLBACK would then
        # raise and hide the original error.
        if self._db.in_transaction:
            self._db.execute("ROLLBACK")

    def _put_viewer(self, viewer: str, value: _ViewerRow) -> None:
        self._db.execute("INSERT OR REPLACE INTO viewers VALUES (?, ?)", (viewer, _dump(asdict(value))))

    def _change_viewer(self, viewer: str, change: Callable[[_ViewerRow], _ViewerRow]) -> _ViewerRow:
        db = self._db
        db.execute("BEGIN IMMEDIATE")
        try:
            value = change(self._viewer(viewer))
            self._put_viewer(viewer, value)
            db.execute("COMMIT")
        except BaseException:
            self._rollback()
            raise
        return value

    def reserve_upload_seqs(self, viewer: str, floor: int, count: int) -> list[int]:
        """Consecutive seqs above everything sent and above CrossWatch's, committed before
        the send, so a crash mid-send can never reuse one."""
        if count < 1:
            raise ValueError(f"count must be at least 1, not {count}")
        start = 0

        def change(v: _ViewerRow) -> _ViewerRow:
            nonlocal start
            start = max(v.sent, floor) + 1
            return replace(v, sent=start + count - 1, epoch=v.epoch + 1)

        self._change_viewer(viewer, change)
        return list(range(start, start + count))

    def confirm_upload_seq(self, viewer: str, seq: int) -> None:
        self._change_viewer(viewer, lambda v: replace(v, confirmed=max(v.confirmed, seq), sent=max(v.sent, seq)))

    def upload_ended(self, viewer: str) -> None:
        self._change_viewer(viewer, lambda v: replace(v, epoch=v.epoch + 1))

    def reset_for_cw(self, viewer: str, cw_seq: int, fresh: bool = False) -> None:
        """CrossWatch lost state, or the record is older than CrossWatch (fresh): start this
        viewer over with it, keeping what the household did. The acked changes stay: a change
        id identifies a change even after a restore. fresh is stored in the same transaction,
        because the reset erases the evidence it came from."""
        db = self._db
        db.execute("BEGIN IMMEDIATE")
        try:
            v = self._viewer(viewer)
            self._put_viewer(
                viewer,
                replace(
                    v,
                    applied_seq=0,
                    confirmed=cw_seq,
                    sent=max(v.sent, cw_seq),
                    full_library_id="",
                    last_delta=[],
                    epoch=v.epoch + 1,
                    fresh_pending=v.fresh_pending or fresh,
                ),
            )
            db.execute("DELETE FROM acks_pending WHERE viewer = ?", (viewer,))
            for (body,) in db.execute("SELECT body FROM entries WHERE viewer = ?", (viewer,)).fetchall():
                entry = _entry_from(body)
                if entry.unsent_upload:
                    self._put_entry(viewer, replace(entry, unsent_upload={}))
            db.execute("COMMIT")
        except BaseException:
            self._rollback()
            raise

    def first_full_at(self, viewer: str) -> str:
        return self._viewer(viewer).first_full_at

    def last_upload_at(self, viewer: str) -> str:
        return self._viewer(viewer).last_upload_at

    def fresh_pending(self, viewer: str) -> bool:
        return self._viewer(viewer).fresh_pending

    def inbox_applied(self) -> int:
        return int(self._meta("inbox_applied") or 0)

    def set_settled(self, viewer: str) -> None:
        self._change_viewer(viewer, lambda v: replace(v, settled=True))

    def set_first_mapped_at(self, viewer: str, at: str) -> None:
        self._change_viewer(viewer, lambda v: v if v.first_mapped_at else replace(v, first_mapped_at=at))

    def set_last_delta(self, viewer: str, bodies: list[tuple[int, bytes]]) -> None:
        self._change_viewer(viewer, lambda v: replace(v, last_delta=[[seq, body.hex()] for seq, body in bodies]))

    def set_seed_viewers(self, ids: Iterable[str], at: str) -> bool:
        """Written by the first Start only; False when the seed viewers were already set."""
        db = self._db
        db.execute("BEGIN IMMEDIATE")
        try:
            if self._meta("seed_viewers") is not None:
                db.execute("ROLLBACK")
                return False
            db.execute("INSERT INTO meta VALUES ('seed_viewers', ?)", (_dump(sorted(set(ids))),))
            db.execute("INSERT INTO meta VALUES ('seed_started_at', ?)", (at,))
            db.execute("COMMIT")
        except BaseException:
            self._rollback()
            raise
        return True

    def _put_entry(self, viewer: str, entry: Entry) -> None:
        db = self._db
        db.execute("INSERT OR REPLACE INTO entries VALUES (?, ?, ?)", (viewer, entry.key, _entry_body(entry)))
        # A key that is an entry again is no longer an alias of another.
        db.execute("DELETE FROM aliases WHERE viewer = ? AND old_key = ?", (viewer, entry.key))
        db.execute("DELETE FROM tokens WHERE viewer = ? AND key = ?", (viewer, entry.key))
        db.executemany(
            "INSERT OR IGNORE INTO tokens VALUES (?, ?, ?)", [(viewer, t, entry.key) for t in sorted(entry.tokens)]
        )

    def _drop_entry(self, viewer: str, key: str) -> None:
        self._db.execute("DELETE FROM entries WHERE viewer = ? AND key = ?", (viewer, key))
        self._db.execute("DELETE FROM tokens WHERE viewer = ? AND key = ?", (viewer, key))

    def commit(self, batch: Batch) -> None:
        db = self._db
        db.execute("BEGIN IMMEDIATE")
        try:
            self._apply(batch)
            db.execute("COMMIT")
        except BaseException:
            self._rollback()
            raise
        self.commits += 1

    def _apply(self, batch: Batch) -> None:
        db = self._db
        for viewer, groups in batch.merged.items():
            for new_key, old_keys in groups.items():
                for old in old_keys:
                    if old == new_key:
                        continue
                    self._drop_entry(viewer, old)
                    db.execute("INSERT OR REPLACE INTO aliases VALUES (?, ?, ?)", (viewer, old, new_key))
                    # An alias that pointed at the merged-away key now points at the survivor.
                    db.execute(
                        "UPDATE aliases SET new_key = ? WHERE viewer = ? AND new_key = ? AND old_key != ?",
                        (new_key, viewer, old, new_key),
                    )
        for viewer, keys in batch.removed_entries.items():
            for key in keys:
                self._drop_entry(viewer, key)
                db.execute("DELETE FROM aliases WHERE viewer = ? AND new_key = ?", (viewer, key))
        for viewer, entries in batch.entries.items():
            for entry in entries:
                self._put_entry(viewer, entry)
        for viewer, by_entry in batch.unsent_carried.items():
            for key, carried in by_entry.items():
                current = self.entry(viewer, key)
                if current is None:
                    continue
                # Changed since the upload was built: the newer person change wasn't carried.
                stamped = (
                    {g: s for g, s in carried.groups.items() if g in current.unsent}
                    if current.change_count == carried.change_count
                    else {}
                )
                # CrossWatch has these applied changes now, so they are ordinary uploaded
                # states again; one applied since the upload was built stays.
                applied = {g: s for g, s in current.applied_change.items() if carried.applied.get(g) != s}
                after = {g: a for g, a in current.applied_after.items() if g in applied}
                unchanged = current.change_count == carried.change_count
                # Still touched while a person change it held went up unstamped (the queue
                # wasn't fetched first): the next delta carries it again, stamped then.
                unstamped = set(current.unsent) - set(current.unsent_upload) - set(stamped)
                sent = unchanged and bool(batch.uploaded_at) and not unstamped
                if stamped or applied != current.applied_change or (sent and current.touched):
                    self._put_entry(
                        viewer,
                        replace(
                            current,
                            unsent_upload={**current.unsent_upload, **stamped},
                            applied_change=applied,
                            applied_after=after,
                            touched=current.touched and not sent,
                        ),
                    )
        for viewer, by_entry in batch.unsent_cleared.items():
            for key, groups in by_entry.items():
                current = self.entry(viewer, key)
                if current is not None:
                    history = current.state.history
                    if "history" in groups and history.unwatched:
                        # Settled with CrossWatch: stop sending unwatched: true, which would
                        # restamp CrossWatch's event on every upload.
                        history = replace(history, unwatched=False)
                    self._put_entry(
                        viewer,
                        replace(
                            current,
                            state=replace(current.state, history=history),
                            unsent={g: t for g, t in current.unsent.items() if g not in groups},
                            unsent_upload={g: s for g, s in current.unsent_upload.items() if g not in groups},
                        ),
                    )
        stamp = int(self._meta("seen_stamp") or 0) + 1
        if batch.seen:
            db.execute("INSERT OR REPLACE INTO meta VALUES ('seen_stamp', ?)", (str(stamp),))
        by_token: dict[str, Seen] = {}
        for row, seen in batch.seen.items():
            if seen is None:
                db.execute(
                    "DELETE FROM seen WHERE library_id = ? AND kind = ? AND kodi_id = ? AND file = ?",
                    (row.library_id, row.kind, row.kodi_id, row.file),
                )
                continue
            body = _dump(asdict(seen))
            db.execute(
                "INSERT OR REPLACE INTO seen VALUES (?, ?, ?, ?, ?)",
                (row.library_id, row.kind, row.kodi_id, row.file, body),
            )
            # Kept by token and file beyond the row's life, for catch-up.
            keys = set(batch.seen_tokens.get(row, ()))
            if row.kind == "movies" and row.file:
                keys.add(f"file:{row.file}")
            for key in keys:
                # Copies read together share a token: the watched one is kept.
                if key not in by_token or seen.playcount > by_token[key].playcount:
                    by_token[key] = seen
        db.executemany(
            "INSERT OR REPLACE INTO seen_by_token VALUES (?, ?, ?)",
            [(k, _dump(asdict(v)), stamp) for k, v in sorted(by_token.items())],
        )
        self._apply_pending(batch)
        for assignment in batch.assignments_add:
            db.execute(
                "INSERT OR REPLACE INTO assignments VALUES (?, ?)", (assignment.id, _assignment_body(assignment))
            )
        for aid in batch.assignments_done:
            db.execute("DELETE FROM assignments WHERE id = ?", (aid,))
        for viewer, acked in batch.acked_add.items():
            db.executemany(
                "INSERT OR REPLACE INTO acked VALUES (?, ?, ?, ?, ?)",
                [(viewer, a.seq, a.change_id, a.entry_key, a.group) for a in acked],
            )
            db.execute(
                "DELETE FROM acked WHERE viewer = ? AND seq NOT IN "
                "(SELECT DISTINCT seq FROM acked WHERE viewer = ? ORDER BY seq DESC LIMIT ?)",
                (viewer, viewer, ACKED_SEQS_KEPT),
            )
        for viewer, acks in batch.acks_add.items():
            db.executemany(
                "INSERT OR REPLACE INTO acks_pending VALUES (?, ?, ?, ?)",
                [(viewer, int(a["seq"]), str(a["change_id"]), _dump(a)) for a in acks],
            )
        for viewer, done in batch.acks_done.items():
            db.executemany(
                "DELETE FROM acks_pending WHERE viewer = ? AND seq = ? AND change_id = ?",
                [(viewer, seq, change_id) for seq, change_id in done],
            )
        # An upload's commit carries uploaded_at, with its viewer in first_full_done (a full)
        # or unsent_carried (a delta).
        uploaded = {*batch.first_full_done, *batch.unsent_carried} if batch.uploaded_at else set()
        viewers = {*batch.applied_seq, *batch.full_library_id, *batch.first_full_done, *batch.fresh_done, *uploaded}
        for viewer in viewers:
            v = self._viewer(viewer)
            self._put_viewer(
                viewer,
                replace(
                    v,
                    applied_seq=max(v.applied_seq, batch.applied_seq.get(viewer, 0)),
                    full_library_id=batch.full_library_id.get(viewer, v.full_library_id),
                    first_full=v.first_full or viewer in batch.first_full_done,
                    first_full_at=v.first_full_at
                    or (batch.uploaded_at if viewer in batch.first_full_done else ""),
                    fresh_pending=v.fresh_pending and viewer not in batch.fresh_done,
                    last_upload_at=max(v.last_upload_at, batch.uploaded_at) if viewer in uploaded else v.last_upload_at,
                ),
            )
        if batch.inbox_applied > self.inbox_applied():
            db.execute("INSERT OR REPLACE INTO meta VALUES ('inbox_applied', ?)", (str(batch.inbox_applied),))

    def _apply_pending(self, batch: Batch) -> None:
        db = self._db
        for wid in batch.pending_done:
            db.execute("DELETE FROM pending WHERE id = ?", (wid,))
        if batch.pending_add:
            existing = self.pending_writes()
            for write in batch.pending_add:
                # A newer intent for the same item and group supersedes the older one, also
                # one added earlier in this batch.
                # A write still in flight for the older one carries over, so a crash before its
                # read-back still knows the value in Kodi is the add-on's own.
                carried_flight = write.in_flight
                for old in existing:
                    if old.group == write.group and old.tokens & write.tokens and old.id != write.id:
                        db.execute("DELETE FROM pending WHERE id = ?", (old.id,))
                        carried_flight = carried_flight or old.in_flight
                write = replace(write, in_flight=carried_flight)
                existing = [w for w in existing if not (w.group == write.group and w.tokens & write.tokens)]
                existing.append(write)
                db.execute("INSERT OR REPLACE INTO pending VALUES (?, ?)", (write.id, _pending_body(write)))
        for wid, fields in batch.in_flight.items():
            row = db.execute("SELECT body FROM pending WHERE id = ?", (wid,)).fetchone()
            if row is not None:
                write = replace(_pending_from(row[0]), in_flight=fields)
                db.execute("UPDATE pending SET body = ? WHERE id = ?", (_pending_body(write), wid))


# -- merging ------------------------------------------------------------------------------
# One item can end up with two entries: an episode that gains ids of its own after Refresh
# information, two copies scraped differently. When an upload row's tokens hit more than one
# entry, CrossWatch merges them with _merge_keys and _merge_wins (_addon_sync.py). The add-on
# uses that rule for the states CrossWatch already has and ranks what CrossWatch hasn't seen
# above them (see merge), so the next upload makes both sides end in the same state.


def _event(group_state: History) -> int:
    return group_state.event or group_state.src


def _merge_wins(group: Group, theirs: History | Rating | Resume, mine: History | Rating | Resume) -> bool:
    """CrossWatch's _merge_wins: whether the merged-in entry's group replaces the target's."""
    if group != "history" or not isinstance(theirs, History) or not isinstance(mine, History):
        return theirs.src > mine.src
    if theirs.watched != mine.watched:
        negative, positive = (mine, theirs) if theirs.watched else (theirs, mine)
        unwatch_wins = negative.explicit and _event(negative) > _event(positive)
        return (negative is theirs) == unwatch_wins
    return _event(theirs) > _event(mine)


def _fold(group: Group, mine: Any, theirs: Any, empty: Any) -> Any:
    """The target's group after merging another entry's into it."""
    if theirs != empty and (mine == empty or _merge_wins(group, theirs, mine)):
        return theirs
    return mine


def _group_of(state: ItemState, group: Group) -> Any:
    return {"history": state.history, "ratings": state.rating, "progress": state.resume}[group]


def merge(entries: list[Entry]) -> Entry:
    """Merge the entries of one item: the lowest key survives, as in CrossWatch's _merge_keys.

    Per group, CrossWatch merges only states it already received, so its rule decides the
    states the add-on uploaded. The record also holds two things CrossWatch hasn't seen,
    which rank above any uploaded state, still carrying stamps from older uploads:
    - a person's change not yet settled with CrossWatch: the newest wins (equal times: the
      lowest key, as for everything else in a merge);
    - a queued CrossWatch change applied here and not yet uploaded back: the highest seq
      wins, as CrossWatch moves pending changes onto the surviving key by seq.
    A person change already carried by an upload that an applied CrossWatch change was made
    after (its `after` at or above that upload's seq) was answered by that change, which
    wins, as it would on one entry. What goes up next is then the newer decision, so CrossWatch's
    own merge agrees with it.
    """
    if not entries:
        raise ValueError("nothing to merge")
    ordered = sorted(entries, key=lambda e: e.key)
    target = ordered[0]
    meta = dict(target.meta)
    for other in ordered[1:]:
        meta = {**other.meta, **meta}
    empty: dict[Group, Any] = {"history": History(), "ratings": Rating(), "progress": Resume()}
    states: dict[Group, Any] = {}
    unsent: dict[str, str] = {}
    unsent_upload: dict[str, int] = {}
    applied_change: dict[str, int] = {}
    applied_after: dict[str, int] = {}
    newest_history: Entry | None = None
    for group in GROUPS:
        applied = [e for e in ordered if group in e.applied_change]
        newest = max(applied, key=lambda e: e.applied_change[group]) if applied else None
        newest_after = newest.applied_after.get(group, 0) if newest is not None else -1
        person = [
            e
            for e in ordered
            if group in e.unsent and not (group in e.unsent_upload and e.unsent_upload[group] <= newest_after)
        ]
        if person:
            winner = max(person, key=lambda e: e.unsent[group])
            states[group] = _group_of(winner.state, group)
            unsent[group] = winner.unsent[group]
            # The winner's own carrying upload, or none: an older change's upload must not
            # settle the newer one.
            if group in winner.unsent_upload:
                unsent_upload[group] = winner.unsent_upload[group]
        elif newest is not None:
            states[group] = _group_of(newest.state, group)
        else:
            folded = _group_of(target.state, group)
            for other in ordered[1:]:
                folded = _fold(group, folded, _group_of(other.state, group), empty[group])
            states[group] = folded
        if group == "history":
            newest_history = newest
        if newest is not None:
            applied_change[group] = newest.applied_change[group]
            if group in newest.applied_after:
                applied_after[group] = newest.applied_after[group]
    history = states["history"]
    noted = [e.state.history for e in ordered if e.state.history.local_unwatch]
    if noted and history.watched and not history.local_unwatch:
        # A person's unwatch noted on any copy holds for the item, unless the CrossWatch
        # watch that won was made after it (apply.py lifts it the same way on one entry).
        seq = max(h.local_unwatch_seq for h in noted)
        lifted = newest_history is not None and newest_history.applied_after.get("history", -1) >= seq
        if not lifted:
            states["history"] = replace(history, local_unwatch=True, local_unwatch_seq=seq)
    rating = states["ratings"]
    if any(e.state.rating.from_cw for e in ordered):
        # A rating CrossWatch removed on any copy stays removed for "Send existing ratings".
        rating = replace(rating, from_cw=True)
    origins = {e.origin for e in ordered}
    all_seed = origins == {"seed"}
    # A merge of mixed origins is the most deliberate one: a person's, then CrossWatch's.
    origin: Origin = "seed" if all_seed else next(o for o in ("person", "cw", "empty", "seed") if o in origins)
    return Entry(
        key=target.key,
        tokens=frozenset().union(*(e.tokens for e in ordered)),
        meta=meta,
        state=ItemState(history=states["history"], rating=rating, resume=states["progress"]),
        unsent=unsent,
        unsent_upload=unsent_upload,
        touched=any(e.touched for e in ordered),
        origin=origin,
        seed_rating=max(e.seed_rating for e in ordered) if all_seed else 0,
        change_count=max(e.change_count for e in ordered) + 1,
        applied_change=applied_change,
        applied_after=applied_after,
    )
