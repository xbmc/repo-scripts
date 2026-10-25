# SPDX-License-Identifier: GPL-2.0-only
"""Completed watches, kept on disk until CrossWatch accepts them.

The one event persisted. A lost stop loses who watched, which is what the addon exists to
report, and Kodi's own shared playcount cannot recover it. Everything else is only worth
sending while it is still true, so it stays in memory and expires.

An entry holds the exact payload that was built for sending, so a replay carries the
original event_id and sent_at, and a fingerprint of the token it was meant for, never the
token itself. A duplicate caused by a crash between acceptance and removal is harmless: the
receiving sinks dedupe or set an idempotent watched flag.
"""

import hashlib
import json
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from resources.lib.constants import OUTBOX_MAX_AGE_SECONDS, OUTBOX_MAX_ENTRIES, PING_INTERVAL_SECONDS
from resources.lib.log import get_logger
from resources.lib.storage import _write_json

_log = get_logger("reporter")

_FORMAT_VERSION = 1


def config_fingerprint(token: str) -> str:
    """Which CrossWatch instance an entry was meant for.

    The token alone, not the URL: CrossWatch maps each token to one Kodi instance on one
    server, so the same server reached under a new address keeps its stored watches, and
    another instance, which may route viewers differently, does not get them.
    """
    return hashlib.sha256(token.encode()).hexdigest()


@dataclass
class OutboxEntry:
    event_id: str
    kind: str
    body: dict[str, Any]
    stored_at: float
    fingerprint: str
    # Monotonic and never persisted: everything left over from a previous run is due at once.
    due_at: float = 0.0


class Outbox:
    """Thread-safe: the service thread adds, the reporter thread delivers and removes.

    No method does network I/O, so holding the lock across a file write never makes a
    callback wait on CrossWatch.
    """

    def __init__(
        self,
        path: str,
        fingerprint: str,
        *,
        wall: Callable[[], float] = time.time,
        clock: Callable[[], float] = time.monotonic,
        max_entries: int = OUTBOX_MAX_ENTRIES,
        max_age: float = OUTBOX_MAX_AGE_SECONDS,
        retry_interval: float = PING_INTERVAL_SECONDS,
    ) -> None:
        self._path = path
        self._fingerprint = fingerprint
        # Age spans restarts, so it has to be wall time; retry spacing does not, so it is
        # monotonic and immune to the clock stepping at NTP sync.
        self._wall = wall
        self._clock = clock
        self._max_entries = max_entries
        self._max_age = max_age
        self._retry_interval = retry_interval
        self._entries: list[OutboxEntry] = []
        self._lock = threading.Lock()

    def load(self) -> None:
        with self._lock:
            entries = self._read()
            now = self._wall()
            kept: list[OutboxEntry] = []
            dropped = {"age": 0, "config": 0}
            for entry in entries:
                if entry.fingerprint != self._fingerprint:
                    dropped["config"] += 1
                elif self._too_old(entry, now):
                    dropped["age"] += 1
                else:
                    kept.append(entry)
            self._entries = kept
            for reason, count in dropped.items():
                if count:
                    _log.warning("reporter.outbox_dropped", reason=reason, count=count)
            if len(kept) != len(entries):
                self._save()
            if kept:
                _log.info("reporter.outbox_loaded", count=len(kept))

    def rebind(self, fingerprint: str) -> None:
        """Point the store at another token, dropping what was kept for a different one.

        The service keeps one store for its whole life and rebinds it, rather than building a
        second over the same file: two stores would each save their own entries over the
        other's.
        """
        with self._lock:
            if fingerprint == self._fingerprint:
                return
            self._fingerprint = fingerprint
            kept = [e for e in self._entries if e.fingerprint == fingerprint]
            dropped = len(self._entries) - len(kept)
            self._entries = kept
            if dropped:
                _log.warning("reporter.outbox_dropped", reason="config", count=dropped)
                self._save()

    def add(self, body: dict[str, Any], kind: str) -> bool:
        """Store before the first send attempt. False means it is held in memory only."""
        entry = OutboxEntry(
            event_id=str(body.get("event_id") or ""),
            kind=kind,
            body=body,
            stored_at=self._wall(),
            fingerprint=self._fingerprint,
            # The live queue is about to try it for its whole freshness window; the outbox
            # takes over only once that has failed.
            due_at=self._clock() + self._retry_interval,
        )
        with self._lock:
            self._entries.append(entry)
            if len(self._entries) > self._max_entries:
                del self._entries[0]
                _log.warning("reporter.outbox_dropped", reason="cap", count=1)
            saved = self._save()
        _log.info("reporter.outbox_stored", event=kind, pending=len(self._entries))
        return saved

    def next_due(self) -> OutboxEntry | None:
        now = self._clock()
        with self._lock:
            # Kodi can run for longer than the age limit, so the limit applied at load has to
            # hold here too; this is the one place every replay passes through.
            wall = self._wall()
            kept = [e for e in self._entries if not self._too_old(e, wall)]
            if len(kept) != len(self._entries):
                _log.warning("reporter.outbox_dropped", reason="age", count=len(self._entries) - len(kept))
                self._entries = kept
                self._save()
            return next((e for e in self._entries if e.due_at <= now), None)

    def defer(self, event_id: str) -> None:
        with self._lock:
            for entry in self._entries:
                if entry.event_id == event_id:
                    entry.due_at = self._clock() + self._retry_interval

    def delivered(self, event_id: str) -> None:
        if self._remove(event_id):
            _log.info("reporter.outbox_delivered", pending=self.pending())

    def refused(self, event_id: str) -> None:
        if self._remove(event_id):
            _log.warning("reporter.outbox_refused", pending=self.pending())

    def rename_viewer(self, old: str, new: str) -> int:
        """Carry a renamed viewer into kept watches, so a replay still names a route CrossWatch has.

        Returns how many entries changed; the file is written once, and only when some did.
        """
        with self._lock:
            changed = 0
            for entry in self._entries:
                names = entry.body.get("viewers")
                if isinstance(names, list) and old in names:
                    entry.body["viewers"] = [new if n == old else n for n in names]
                    changed += 1
            if changed:
                self._save()
            return changed

    def pending(self) -> int:
        with self._lock:
            return len(self._entries)

    def _too_old(self, entry: OutboxEntry, wall: float) -> bool:
        # An entry stamped in the future was stored or is being judged on a clock that had
        # not synced yet. Neither says it is old.
        return wall - entry.stored_at > self._max_age

    def _remove(self, event_id: str) -> bool:
        with self._lock:
            before = len(self._entries)
            self._entries = [e for e in self._entries if e.event_id != event_id]
            if len(self._entries) == before:
                return False
            self._save()
            return True

    def _save(self) -> bool:
        document = {
            "version": _FORMAT_VERSION,
            "entries": [
                {
                    "event_id": e.event_id,
                    "kind": e.kind,
                    "body": e.body,
                    "stored_at": e.stored_at,
                    "fingerprint": e.fingerprint,
                }
                for e in self._entries
            ],
        }
        if _write_json(self._path, document):
            return True
        _log.warning("reporter.outbox_write_failed", pending=len(self._entries))
        return False

    def _read(self) -> list[OutboxEntry]:
        try:
            with open(self._path, encoding="utf-8") as handle:
                document = json.load(handle)
            return _parse(document)
        except FileNotFoundError:
            return []
        except (OSError, ValueError, KeyError, TypeError) as exc:
            # Set aside, never overwritten: it may hold someone's watches, and it is the only
            # evidence of what wrote it.
            _log.error("reporter.outbox_corrupt", error=type(exc).__name__)
            try:
                os.replace(self._path, f"{self._path}.corrupt")
            except OSError:
                pass
            return []


def _parse(document: Any) -> list[OutboxEntry]:
    if not isinstance(document, dict) or not isinstance(document["entries"], list):
        raise TypeError("outbox document")
    entries: list[OutboxEntry] = []
    for raw in document["entries"]:
        body = raw["body"]
        if not isinstance(body, dict):
            raise TypeError("outbox body")
        entries.append(
            OutboxEntry(
                event_id=str(raw["event_id"]),
                kind=str(raw["kind"]),
                body=body,
                stored_at=float(raw["stored_at"]),
                fingerprint=str(raw["fingerprint"]),
            )
        )
    return entries
