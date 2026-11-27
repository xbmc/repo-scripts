# SPDX-License-Identifier: GPL-2.0-only
"""What the service thread tells library sync, and the marks it catches for it.

Kodi delivers notifications and callbacks on the service thread only, in order, so this is
where a VideoLibrary.OnUpdate is classified the moment it arrives (sync/local.py): RecentPlays
and the add-on's own writes are as they were then, which a later look could not tell. A
person's mark is buffered here and written to the inbox file on the controller's tick; the
engine hears only that the inbox has records.

The tick also tells the engine when Kodi turned quiet (nothing played for
PLAYBACK_QUIET_SECONDS), a new playlist index, and the scan count, which is resynced from
Kodi now and then because a scan's end notification can be missed.

Log events: sync.hooks.bad_notification (debug), sync.hooks.person_mark (debug).
"""
from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, Protocol

from resources.lib.config import Settings
from resources.lib.kodi import KodiApi
from resources.lib.log import get_logger
from resources.lib.sync.constants import PLAYBACK_QUIET_SECONDS, RATING_SCAN_SECONDS
from resources.lib.sync.files import InboxRecord
from resources.lib.sync.local import FileIndex, MarkGate, PersonBuffer, RecentPlays, classify, update_item
from resources.lib.sync.ownership import IndexSnapshot
from resources.lib.sync.reply import connection_id
from resources.lib.sync.writer import OwnWrites

_log = get_logger("sync")

_SCAN_STARTED = frozenset({"VideoLibrary.OnScanStarted", "VideoLibrary.OnCleanStarted"})
_SCAN_FINISHED = frozenset({"VideoLibrary.OnScanFinished", "VideoLibrary.OnCleanFinished"})


class Engine(Protocol):
    """What the hooks call on the sync engine (sync/engine.py)."""

    server_backed_rows: frozenset[tuple[str, int]]

    def on_settings(self, settings: Settings) -> None: ...
    def on_scan(self, active: bool, at: float | None = None) -> None: ...
    def on_viewers(self, at: float) -> None: ...
    def on_quiet(self, quiet: bool) -> None: ...
    def on_window(self, open_: bool) -> None: ...
    def on_wake(self) -> None: ...
    def on_request(self) -> None: ...
    def on_snapshot(self, snapshot: IndexSnapshot) -> None: ...


class SyncHooks:
    def __init__(
        self,
        *,
        kodi: KodiApi,
        engine: Engine,
        own: OwnWrites,
        plays: RecentPlays,
        files: FileIndex,
        gate: MarkGate,
        buffer: PersonBuffer,
        clock: Callable[[], float],
        utc_now: Callable[[], str],
        viewers: Callable[[], object] = lambda: None,
        on_viewers_changed: Callable[[], object] = lambda: None,
    ) -> None:
        self._kodi = kodi
        self._engine = engine
        self._own = own
        self._plays = plays
        self._files = files
        self._gate = gate
        self._buffer = buffer
        self._clock = clock
        self._utc_now = utc_now
        self._scans = 0
        self._scans_read_at: float | None = None
        self._last_played: float | None = None
        self._quiet: bool | None = None
        self._snapshot: IndexSnapshot | None = None
        self._sync_request: int | None = None
        self._viewers = viewers
        self._viewers_seen: object = None
        self._on_viewers_changed = on_viewers_changed

    # -- notifications ---------------------------------------------------------------

    def on_notification(self, method: str, data: str) -> None:
        if not (method.startswith("VideoLibrary.") or method == "System.OnWake"):
            return
        try:
            parsed = json.loads(data) if data else {}
        except ValueError:
            _log.debug("sync.hooks.bad_notification", method=method)
            return
        if not isinstance(parsed, dict):
            parsed = {}
        if method == "VideoLibrary.OnUpdate":
            self._on_update(parsed)
        elif method == "VideoLibrary.OnRemove":
            item = update_item(parsed)
            if item is not None:
                # At once, on this thread: a mark on the reused id must not take the old file.
                # The row's Seen goes with the next complete library read.
                self._files.remove(*item)
        elif method in _SCAN_STARTED:
            self._scans += 1
            self._engine.on_scan(True, self._clock())
        elif method in _SCAN_FINISHED:
            # Clamped: a clean inside a scan finishes first, and an end seen without its start
            # (the service started mid-scan) must not go below zero.
            if self._scans > 0:
                self._scans -= 1
                if self._scans == 0:
                    self._engine.on_scan(False, self._clock())
        elif method == "System.OnWake":
            self._engine.on_wake()

    def _on_update(self, data: dict[str, Any]) -> None:
        verdict = classify(
            data,
            received=self._clock(),
            own=self._own,
            plays=self._plays,
            scanning=self._scans > 0,
            server_backed=lambda kind, kodi_id: (kind, kodi_id) in self._engine.server_backed_rows,
        )
        if verdict != "person" or not self._gate.open():
            return
        item = update_item(data)
        playcount = data.get("playcount")
        if item is None or not isinstance(playcount, int) or isinstance(playcount, bool):
            return
        kind, kodi_id = item
        self._buffer.add(
            InboxRecord(
                at=self._utc_now(),
                kind=kind,
                kodi_id=kodi_id,
                file=self._files.file(kind, kodi_id),
                playcount=playcount,
            )
        )
        _log.debug("sync.hooks.person_mark", kind=kind, kodi_id=kodi_id)

    # -- settings ----------------------------------------------------------------------

    def on_settings(self, settings: Settings) -> None:
        self._gate.on_settings(connection_id(settings.webhook_base_url), settings.sync_enabled)
        self._engine.on_settings(settings)
        if self._sync_request is not None and settings.sync_request != self._sync_request:
            # A settings script left a request and bumped the counter.
            self._engine.on_request()
        self._sync_request = settings.sync_request

    # -- the tick ------------------------------------------------------------------------

    def tick(self, *, playing: bool, snapshot: IndexSnapshot) -> None:
        now = self._clock()
        self._own.tick()
        self._gate.refresh()
        if playing:
            self._last_played = now
        quiet = not playing and (self._last_played is None or now - self._last_played >= PLAYBACK_QUIET_SECONDS)
        if quiet != self._quiet:
            self._quiet = quiet
            self._engine.on_quiet(quiet)
        if snapshot is not self._snapshot:
            self._snapshot = snapshot
            self._engine.on_snapshot(snapshot)
        seen = self._viewers()
        if seen != self._viewers_seen:
            # The Viewers screen keeps the settings screen open, so its changes come with no
            # settings event: new viewers get sync ids here, and the engine hears the time.
            first = self._viewers_seen is None
            self._viewers_seen = seen
            if not first:
                self._on_viewers_changed()
                self._engine.on_viewers(now)
        if self._scans_read_at is None or now - self._scans_read_at >= RATING_SCAN_SECONDS:
            first = self._scans_read_at is None
            self._scans_read_at = now
            self._resync_scans(first)

    def _resync_scans(self, first: bool) -> None:
        """Kodi starts its startup scan before service add-ons (Application.cpp:818 vs :832),
        so the first look seeds the count; later ones only clear a count whose end
        notification was lost. A later look never raises it: Kodi's flag turns on when a scan
        is queued, before its start notification, which would count it twice."""
        try:
            answer = self._kodi.jsonrpc("XBMC.GetInfoBooleans", {"booleans": ["Library.IsScanningVideo"]})
        except Exception:
            return
        scanning = answer.get("Library.IsScanningVideo") is True
        if scanning and self._scans == 0 and first:
            self._scans = 1
            self._engine.on_scan(True, self._clock())
        elif not scanning and self._scans > 0:
            self._scans = 0
            self._engine.on_scan(False, self._clock())

    def on_window(self, open_: bool) -> None:
        self._engine.on_window(open_)
