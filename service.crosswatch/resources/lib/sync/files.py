# SPDX-License-Identifier: GPL-2.0-only
"""The files library sync shares between the settings scripts and the service.

Settings scripts run in their own interpreter and never call the sync engine. Start writes
the started file, the status screen leaves requests and reads the status file, and the
service thread records the hand marks it classifies in the inbox. Each JSON file is written
whole under storage.file_lock and carries a version, so a reader can tell a file from a
newer add-on.

The inbox is a separate SQLite file because two threads write it: the service thread adds
marks once per tick and the worker removes them once they are in the record. With SQLite
neither rewrites the other's data, which a JSON file replaced whole would.

Log events: sync.inbox.full (dropped), sync.inbox.busy, sync.inbox.write_failed,
sync.inbox.corrupt.
"""
from __future__ import annotations

import contextlib
import os
import sqlite3
import uuid
from collections.abc import Generator
from contextlib import closing, contextmanager
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from resources.lib.log import get_logger
from resources.lib.storage import _read_json, _write_json, file_lock
from resources.lib.sync.constants import INBOX_MAX

_log = get_logger("sync")

FILE_VERSION = 1


# -- started file -----------------------------------------------------------------------


@dataclass(frozen=True)
class StartedFile:
    """What Start decided for one pairing, plus the worker's pause.

    Start writes it whole with a new start_id. The worker only changes its own fields, and
    only while the start_id on disk is the one it read, so a Start run meanwhile wins.
    """

    connection: str
    start_id: str
    paused: bool = False
    paused_reason: str | None = None
    existing_ratings: bool = False
    existing_ratings_sent: bool = False
    bound_device: str = ""


WORKER_FIELDS = frozenset({"paused", "paused_reason", "bound_device", "existing_ratings_sent"})


def new_start_id() -> str:
    return uuid.uuid4().hex


def read_started(path: str) -> StartedFile | None:
    raw = _read_json(path, None)
    if not isinstance(raw, dict) or raw.get("version") != FILE_VERSION:
        return None
    connection, start_id = raw.get("connection"), raw.get("start_id")
    if not isinstance(connection, str) or not isinstance(start_id, str) or not start_id:
        return None
    reason = raw.get("paused_reason")
    bound = raw.get("bound_device")
    return StartedFile(
        connection=connection,
        start_id=start_id,
        paused=raw.get("paused") is True,
        paused_reason=reason if isinstance(reason, str) and reason else None,
        existing_ratings=raw.get("existing_ratings") is True,
        existing_ratings_sent=raw.get("existing_ratings_sent") is True,
        bound_device=bound if isinstance(bound, str) else "",
    )


def write_started(path: str, started: StartedFile) -> bool:
    with file_lock(path):
        return _write_json(path, {"version": FILE_VERSION, **asdict(started)})


def update_started(path: str, start_id: str, **fields: Any) -> bool:
    """The worker's change to its own fields; False when a newer Start replaced the file."""
    unknown = set(fields) - WORKER_FIELDS
    if unknown:
        raise ValueError(f"not the worker's to change: {sorted(unknown)}")
    with file_lock(path):
        current = read_started(path)
        if current is None or current.start_id != start_id:
            return False
        return _write_json(path, {"version": FILE_VERSION, **{**asdict(current), **fields}})


# -- requests -----------------------------------------------------------------------------

RequestKind = Literal["assign", "send_existing_ratings", "mass_ratings_send", "mass_ratings_drop"]
_REQUEST_KINDS: dict[str, RequestKind] = {
    "assign": "assign",
    "send_existing_ratings": "send_existing_ratings",
    "mass_ratings_send": "mass_ratings_send",
    "mass_ratings_drop": "mass_ratings_drop",
}


@dataclass(frozen=True)
class Request:
    id: str
    kind: RequestKind
    args: dict[str, Any] = field(default_factory=dict)


def _requests(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, dict) or raw.get("version") != FILE_VERSION or not isinstance(raw.get("requests"), list):
        return []
    return [r for r in raw["requests"] if isinstance(r, dict)]


def append_request(path: str, request: Request) -> bool:
    with file_lock(path):
        rows = _requests(_read_json(path, None))
        rows.append(asdict(request))
        return _write_json(path, {"version": FILE_VERSION, "requests": rows})


def _request_from(row: dict[str, Any]) -> Request | None:
    kind = _REQUEST_KINDS.get(row["kind"]) if isinstance(row.get("kind"), str) else None
    rid, args = row.get("id"), row.get("args")
    if kind is None or not isinstance(rid, str) or not rid:
        return None
    return Request(id=rid, kind=kind, args=args if isinstance(args, dict) else {})


def read_requests(path: str) -> list[Request]:
    """The waiting requests, left in the file: the worker removes them with done_requests once
    their effect is committed, so a Kodi exit in between never loses the household's choice."""
    return [r for row in _requests(_read_json(path, None)) if (r := _request_from(row)) is not None]


def done_requests(path: str, ids: set[str]) -> bool:
    """Remove these requests, and any the add-on can't read, keeping ones added meanwhile."""
    with file_lock(path):
        rows = _requests(_read_json(path, None))
        keep = [row for row in rows if (r := _request_from(row)) is not None and r.id not in ids]
        if len(keep) == len(rows):
            return True
        return _write_json(path, {"version": FILE_VERSION, "requests": keep})


# -- status -------------------------------------------------------------------------------

StatusState = Literal["off", "waiting", "syncing", "settled", "stopped"]
_STATES = frozenset({"off", "waiting", "syncing", "settled", "stopped"})


@dataclass(frozen=True)
class StatusFile:
    """What the status screen shows. Holds titles, so it is never logged."""

    state: StatusState = "off"
    reason: str = ""
    message: str = ""
    last_upload: str = ""
    waiting_changes: int = 0
    counts: dict[str, Any] = field(default_factory=dict)
    unowned_titles: list[str] = field(default_factory=list)
    assignments: list[dict[str, Any]] = field(default_factory=list)
    mass_ratings: int = 0
    per_viewer: dict[str, str] = field(default_factory=dict)
    dropped_marks: int = 0
    unreadable_playlists: list[str] = field(default_factory=list)
    updated: str = ""


def write_status(path: str, status: StatusFile) -> bool:
    with file_lock(path):
        return _write_json(path, {"version": FILE_VERSION, **asdict(status)})


def read_status(path: str) -> StatusFile | None:
    raw = _read_json(path, None)
    if not isinstance(raw, dict) or raw.get("version") != FILE_VERSION:
        return None
    defaults = StatusFile()
    values: dict[str, Any] = {}
    for name in StatusFile.__dataclass_fields__:
        if name in raw and isinstance(raw[name], type(getattr(defaults, name))):
            values[name] = raw[name]
    if values.get("state", defaults.state) not in _STATES:
        values.pop("state", None)
    return StatusFile(**values)


# -- inbox --------------------------------------------------------------------------------


@dataclass(frozen=True)
class InboxRecord:
    """A hand mark the service thread saw, waiting for the worker.

    kind is Kodi's "movie" or "episode"; file is the row's file as the last library read had
    it, so the worker can tell a reused SQLite id from the row the mark was made on.
    """

    at: str
    kind: str
    kodi_id: int
    file: str
    playcount: int
    lastplayed: str = ""
    id: int = 0


_SCHEMA = (
    "CREATE TABLE IF NOT EXISTS inbox ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT, kind TEXT, kodi_id INTEGER, file TEXT, "
    "playcount INTEGER, lastplayed TEXT)"
)


class Inbox:
    """One connection per call, so each thread uses its own (sqlite3 connections are bound
    to the thread that made them). busy_timeout is short on purpose for the service thread:
    a busy file keeps the marks in memory for the next tick instead of stalling callbacks."""

    def __init__(self, path: str, busy_timeout: float = 0.2) -> None:
        self._path = path
        self._timeout = busy_timeout

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection]:
        os.makedirs(os.path.dirname(self._path), mode=0o700, exist_ok=True)
        with closing(sqlite3.connect(self._path, timeout=self._timeout, isolation_level=None)) as conn:
            # WAL lets the worker read while the service thread adds; where the storage can't
            # do WAL (some network and FUSE file systems) SQLite keeps its rollback journal,
            # which only means a busy file more often. NORMAL is enough with either.
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute(_SCHEMA)
            conn.execute("CREATE TABLE IF NOT EXISTS counters (name TEXT PRIMARY KEY, value INTEGER)")
            yield conn

    def add_many(self, records: list[InboxRecord]) -> bool:
        """All records in one transaction; False (nothing written) when the file is busy."""
        if not records:
            return True
        try:
            with self._connect() as conn:
                conn.execute("BEGIN IMMEDIATE")
                conn.executemany(
                    "INSERT INTO inbox (at, kind, kodi_id, file, playcount, lastplayed) VALUES (?, ?, ?, ?, ?, ?)",
                    [(r.at, r.kind, r.kodi_id, r.file, r.playcount, r.lastplayed) for r in records],
                )
                total = conn.execute("SELECT COUNT(*) FROM inbox").fetchone()[0]
                dropped = max(total - INBOX_MAX, 0)
                if dropped:
                    conn.execute("DELETE FROM inbox WHERE id IN (SELECT id FROM inbox ORDER BY id LIMIT ?)", (dropped,))
                    conn.execute("INSERT OR IGNORE INTO counters VALUES ('dropped', 0)")
                    conn.execute("UPDATE counters SET value = value + ? WHERE name = 'dropped'", (dropped,))
                conn.execute("COMMIT")
        except sqlite3.OperationalError as exc:
            if "locked" in str(exc) or "busy" in str(exc):
                _log.debug("sync.inbox.busy")
            else:
                _log.warning("sync.inbox.write_failed", error=str(exc))
            return False
        except sqlite3.DatabaseError as exc:
            # A file damaged by a power cut would fail every tick from now on; it is set aside
            # so the next add starts a fresh one. The marks in it were already unreadable.
            _log.error("sync.inbox.corrupt", error=str(exc))
            with contextlib.suppress(OSError):
                os.replace(self._path, self._path + ".corrupt")
            return False
        except OSError as exc:
            _log.warning("sync.inbox.write_failed", error=str(exc))
            return False
        if dropped:
            _log.warning("sync.inbox.full", dropped=dropped)
        return True

    def pending(self, limit: int = 1000) -> list[InboxRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, at, kind, kodi_id, file, playcount, lastplayed FROM inbox ORDER BY id LIMIT ?", (limit,)
            ).fetchall()
        return [
            InboxRecord(id=r[0], at=r[1], kind=r[2], kodi_id=r[3], file=r[4], playcount=r[5], lastplayed=r[6] or "")
            for r in rows
        ]

    def dropped(self) -> int:
        """Marks dropped because the inbox was full, since the file was made, for the status
        screen."""
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM counters WHERE name = 'dropped'").fetchone()
        return int(row[0]) if row else 0

    def remove(self, upto_id: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM inbox WHERE id <= ?", (upto_id,))
