# SPDX-License-Identifier: GPL-2.0-only
"""Library sync's worker: one thread that carries out what plan.next_action decides.

The service thread hands it inputs (settings, ping replies, playback quiet, scans, the
playlist index, the inbox having marks) through thread-safe methods; the worker folds them
into plan.EngineState between actions, so the decision always sees one consistent state. An
input that fails is logged and the others still apply; the thread never dies of one.

It owns the record (sync.db, opened on this thread, as sqlite3 connections belong to the
thread that made them), the last library read and the HTTP client. What it publishes for the
service thread is replaced whole, never changed in place: the upload epochs the ping ticket
carries, and the rows a media server add-on owns. Each row's file lives in the shared
local.FileIndex, which the service thread also updates on VideoLibrary.OnRemove.

JSON-RPC from this thread is allowed (executeJSONRPC releases the GIL, ModuleXbmc.cpp:125-128,
verified live, verification.md 2026-11-20); settings, dialogs and notifications stay on the
service thread.

Log events: sync.engine.started, sync.engine.stopped, sync.engine.action_failed (warning),
sync.engine.input_failed (warning), sync.engine.record_busy (info), sync.engine.waiting_on_action
(debug), sync.drain.applied (debug), sync.drain.dropped (info), sync.drain.server_backed (debug),
sync.owners_moved (info),
sync.owners_moved_failed (warning), sync.record.missing (warning).
"""
from __future__ import annotations

import os
import sqlite3
import threading
import time
from collections.abc import Mapping
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Any, Callable, Literal

from resources.lib import paths
from resources.lib.config import Settings
from resources.lib.kodi import KodiApi
from resources.lib.log import get_logger
from resources.lib.media import strip_credentials
from resources.lib.storage import PromptMemory, ViewerStore
from resources.lib.sync import plan
from resources.lib.sync.apply import apply_changes, settle_unsent
from resources.lib.sync.client import SyncClient, SyncError
from resources.lib.sync.clock import kodi_to_utc, parse_utc
from resources.lib.sync.constants import (
    INBOX_MAX_AGE_SECONDS,
    QUEUE_FALLBACK_SECONDS,
    RATING_SCAN_SECONDS,
    STATUS_FIGURES_SECONDS,
)
from resources.lib.sync.counts import count_owners, to_status, unowned_titles
from resources.lib.sync.files import (
    Inbox,
    InboxRecord,
    Request,
    StatusFile,
    StatusState,
    done_requests,
    read_requests,
    read_started,
    read_status,
    update_started,
    write_status,
)
from resources.lib.sync.items import ItemKind, Library, LibraryRow, RowKey, is_server_backed, read_library
from resources.lib.sync.library_id import library_id, profile_has_own_database
from resources.lib.sync.local import FileIndex
from resources.lib.sync.manual import (
    LocalOutcome,
    Recorded,
    ToAssign,
    apply_assignment,
    existing_ratings,
    rating_change,
    rating_window_write,
    watched_change,
)
from resources.lib.sync.ownership import IndexSnapshot, moved_viewers, owners_of
from resources.lib.sync.ping import device_id_changed, pause_reason
from resources.lib.sync.rating_scan import FoundRating, rating_scan
from resources.lib.sync.record import Batch, Carried, Entry, PendingWrite, RecordMissing, RecordStore, merge
from resources.lib.sync.reply import PingTicket, SyncReply, connection_id
from resources.lib.sync.rows import ViewerRows, viewer_rows
from resources.lib.sync.server_maps import read_server_rows
from resources.lib.sync.settings import SyncSettings
from resources.lib.sync.upload import UploadBody, UploadTooLarge, deltas, full_parts
from resources.lib.sync.writer import OwnWrites, Writer, in_flight_rows, read_row, seen_of

_log = get_logger("sync")

# How long the worker sleeps when there is nothing to do and no deadline: inputs wake it.
IDLE_SECONDS = 30.0
# Marks drained per commit: a long drain commits as it goes, so an exit loses nothing.
DRAIN_BATCH = 100

_KINDS: dict[str, ItemKind] = {"movie": "movies", "episode": "episodes"}
_KODI_TYPES: dict[ItemKind, str] = {"movies": "movie", "episodes": "episode"}
_DETAILS: dict[ItemKind, tuple[str, str, str]] = {
    "movies": ("VideoLibrary.GetMovieDetails", "movieid", "moviedetails"),
    "episodes": ("VideoLibrary.GetEpisodeDetails", "episodeid", "episodedetails"),
}

Drained = Literal["applied", "dropped", "server", "wait", "retry"]

ClientFactory = Callable[[str, str, str, threading.Event], SyncClient]


def _client(base_url: str, token: str, device_id: str, abort: threading.Event) -> SyncClient:
    return SyncClient(base_url, token=token, device_id=device_id, abort=abort)


@dataclass
class _Full:
    """A full upload going up, one part per step, so inputs are taken between parts."""

    seq: int
    parts: list[UploadBody]
    rows: ViewerRows
    # Each of the viewer's entries as the record held it when the upload was built; the
    # commit stores the build's changes to one only while the record still holds that.
    stored: dict[str, Entry]
    # The rows this viewer owns in that read.
    owned: frozenset[RowKey]
    library: Library
    queue_settled: bool
    fresh: bool
    first: bool
    next: int = 0


@dataclass(frozen=True)
class SyncPaths:
    db: str
    inbox: str
    started: str
    requests: str
    status: str

    @classmethod
    def of(cls, kodi: KodiApi) -> SyncPaths:
        return cls(
            db=paths.sync_db_path(kodi),
            inbox=paths.sync_inbox_path(kodi),
            started=paths.sync_started_path(kodi),
            requests=paths.sync_requests_path(kodi),
            status=paths.sync_status_path(kodi),
        )


class _Gone(Exception):
    """Kodi has no row at that id."""


class _InboxBusy(Exception):
    """The inbox couldn't take the waiting marks back; the drain is retried after a pause."""


class SyncEngine:
    def __init__(
        self,
        *,
        kodi: KodiApi,
        viewer_store: ViewerStore,
        memory: PromptMemory,
        inbox: Inbox,
        files: FileIndex,
        ping_requested: threading.Event,
        rebuild_requested: threading.Event,
        sync_paths: SyncPaths,
        utc_now: Callable[[], str],
        own: OwnWrites | None = None,
        device_id: Callable[[], str] = lambda: "",
        clock: Callable[[], float] = time.monotonic,
        store_factory: Callable[[str], RecordStore] = RecordStore,
        client_factory: ClientFactory = _client,
    ) -> None:
        self._kodi = kodi
        self._viewers = viewer_store
        self._memory = memory
        self._inbox = inbox
        self._files = files
        self._ping_requested = ping_requested
        self._rebuild_requested = rebuild_requested
        self._paths = sync_paths
        self._clock = clock
        self._utc_now = utc_now
        self._store_factory = store_factory
        self._device_id = device_id
        self._own = own if own is not None else OwnWrites()
        self._client_factory = client_factory
        self._client_cache: tuple[tuple[str, str, str], SyncClient] | None = None
        self._fulls: dict[str, _Full] = {}
        self._mapping: plan.ViewerMapping | None = None
        self._last_rating_scan: float | None = None
        # Ratings held back for the household's answer (the mass-rating question), with the
        # value each row had when the question was raised.
        self.held_ratings: list[FoundRating] = []
        # Viewers that sent their existing ratings since Start chose it.
        self._existing_sent: set[str] = set()

        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._stopping = threading.Event()
        self._inputs: list[tuple[str, Any]] = []
        self._thread: threading.Thread | None = None

        # Worker-only from here on.
        self._store: RecordStore | None = None
        self._state = plan.EngineState()
        self._settings: Settings | None = None
        self._snapshot: IndexSnapshot | None = None
        self._scan_ended_at = 0.0
        self._viewers_changed_at = 0.0
        # The household turned sync off since the last reply: an answer to a block with
        # enabled false then pauses this device (sync/ping.py pause_reason).
        self._turned_off = False
        self._show_ids_changed_at = 0.0
        self._last_status: StatusFile | None = None
        # Why the started file says paused, for the status screen.
        self._pause_cause = ""
        self._last_full_asked: float | None = None
        self._last_fallback_fetch = 0.0
        # Rating window writes, applied by the rating step before the next scan.
        self.rating_writes: list[tuple[str, int, int, tuple[str, ...]]] = []
        self.library: Library | None = None
        self.dropped_marks = 0
        # CrossWatch still holds this install's old device id as the sync device.
        self.device_id_changed = False
        # Seed viewers whose first full started after their window: the status names them.
        self.late_seeds: set[str] = set()
        # The status screen's figures, recounted only when what they come from changed: the
        # record's commit count, and the library and index the ownership was counted from.
        self._record_figures: tuple[int, str, int] | None = None
        self._figures_at = 0.0
        self._owned_from: tuple[Library, IndexSnapshot, Mapping[str, Any]] | None = None
        self._owned: tuple[dict[str, Any], list[str]] = ({}, [])
        # The index and remembered answers ownership was last judged by, to tell when an
        # item moved between viewers.
        self._owner_inputs: tuple[IndexSnapshot, Mapping[str, Any]] | None = None

        # Published for the service thread; replaced whole.
        self.server_backed_rows: frozenset[tuple[str, int]] = frozenset()
        self.epochs: Mapping[str, int] = MappingProxyType({})

    # -- lifecycle ----------------------------------------------------------------------

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="crosswatch-sync", daemon=True)
        self._thread.start()

    def stop(self, budget: float = 2.0) -> bool:
        """Ask the worker to stop and wait up to budget seconds; True when it did. Kodi waits
        for every thread after the service's main returns (PythonInvoker.cpp:384-405), so the
        worker stops at its next step or drained mark, never in the middle of a commit."""
        self._stopping.set()
        self._wake.set()
        client = self._client_cache
        if client is not None:
            # A request in flight is closed, so a 10 s timeout never outlasts Kodi's 5 s window.
            client[1].cancel()
        thread = self._thread
        if thread is None:
            return True
        thread.join(budget)
        return not thread.is_alive()

    def _run(self) -> None:
        _log.info("sync.engine.started")
        try:
            self.begin()
            while not self._stopping.is_set():
                wait = self.step()
                if wait is not None and not self._stopping.is_set():
                    self._wake.wait(max(wait, 0.0))
                    self._wake.clear()
        finally:
            self.end()
            _log.info("sync.engine.stopped")

    def begin(self) -> None:
        """Start a session: open the record, and look at what a Kodi exit left behind (marks in
        the inbox, requests waiting)."""
        # The session's own full and first fetch count as the day's and the interval's.
        self._last_full_asked = self._last_fallback_fetch = self._clock()
        self._state = replace(
            plan.session_start(self._state, self._clock()),
            inbox_waiting=True,
            requests_waiting=bool(read_requests(self._paths.requests)),
        )
        self._open_store()
        # The counts as the last session left them, until this session has read the library:
        # a session that never gets that far would otherwise wipe them from the screen.
        previous = read_status(self._paths.status)
        if previous is not None and not self._owned[0]:
            self._owned = (previous.counts, previous.unowned_titles)

    def step(self) -> float | None:
        """Take the inputs, do what next_action says, write the status. The seconds to wait
        before the next step, or None for at once."""
        self._take_inputs()
        if self._stopping.is_set():
            return None
        if self._store is None and not self._state.record_missing:
            self._open_store()
            if self._store is None:
                return IDLE_SECONDS
        if (
            self.rating_writes
            and self._store is not None
            and self.library is not None
            and plan.local_active(self._state)
        ):
            self._rating_writes(self._store, self.library)
        now = self._clock()
        if plan.active(self._state):
            self._follow_owner_moves()
            # A box left on for weeks still gets a full now and then, and a queue fetch even when
            # no reply asked for one; next_action holds both while Kodi is busy.
            if plan.daily_full_due(self._last_full_asked, now):
                self._state = plan.request_full(self._state)
                self._last_full_asked = now
            if now - self._last_fallback_fetch >= QUEUE_FALLBACK_SECONDS:
                self._state = plan.queue_fallback(self._state)
                self._last_fallback_fetch = now
        due = self._last_rating_scan is None or now - self._last_rating_scan >= RATING_SCAN_SECONDS
        if due != self._state.rating_scan_due:
            self._state = replace(self._state, rating_scan_due=due)
        wait = self._act(plan.next_action(self._state, now))
        self._write_status()
        return wait

    def end(self) -> None:
        if self._store is not None and self.library is not None and self.rating_writes:
            try:
                self._rating_writes(self._store, self.library)
            except Exception as exc:
                _log.warning("sync.engine.rating_writes_lost", count=len(self.rating_writes), error=str(exc))
        if self._store is not None:
            self._store.close()
            self._store = None

    @property
    def state(self) -> plan.EngineState:
        return self._state

    def _snapshot_usable(self, snapshot: IndexSnapshot) -> bool:
        return snapshot.usable(
            last_scan_end=self._scan_ended_at,
            last_viewer_change=self._viewers_changed_at,
            show_ids_changed_at=self._show_ids_changed_at,
        )

    def _retry_record(self) -> None:
        if self._state.record_missing and self._store is None:
            self._state = replace(self._state, record_missing=False)
            self._open_store()

    def _open_store(self) -> None:
        store = self._store_factory(self._paths.db)
        try:
            store.open()
        except RecordMissing:
            if self._state.started:
                _log.warning("sync.record.missing")
            self._state = replace(self._state, record_missing=True)
            return
        except sqlite3.OperationalError as exc:
            # Busy, for example while Start writes it: tried again on the next step.
            _log.info("sync.engine.record_busy", error=str(exc))
            return
        self._store = store
        self._load_record()

    def _load_record(self) -> None:
        """What the record knows that the plan needs: per viewer, a fresh full still owed and
        whether the first full is committed; and the files of the rows it has seen."""
        store = self._store
        assert store is not None
        viewers = dict(self._state.viewers)
        for viewer in self._known_viewers():
            vs = viewers.get(viewer, plan.ViewerState())
            fresh = store.fresh_pending(viewer)
            viewers[viewer] = replace(
                vs,
                fresh=fresh,
                full_due=vs.full_due or fresh,
                first_full_committed=store.first_full_committed(viewer),
                settled=store.settled(viewer),
                unsent=any(e.touched for e in store.entries(viewer)),
                acks_pending=bool(store.acks_pending(viewer)),
            )
        started = read_started(self._paths.started)
        if started is not None and started.existing_ratings and not started.existing_ratings_sent:
            viewers = {v: replace(vs, existing_ratings_due=vs.settled) for v, vs in viewers.items()}
        self._state = replace(self._state, viewers=viewers, writes_pending=bool(store.pending_writes()))
        # Writes sent before a crash and never read back are the add-on's own.
        self._own.seed(store.pending_writes())
        generation = self._files.generation()
        seen = store.seen_for_library(library_id(self._kodi))
        self._files.replace({(_KODI_TYPES[k.kind], k.kodi_id): k.file for k in seen}, generation)
        self._publish_epochs()

    def _publish_epochs(self) -> None:
        store = self._store
        if store is None:
            return
        reply = self._state.reply
        viewers = {*self._known_viewers(), *(reply.viewers if reply is not None else ())}
        self.epochs = MappingProxyType({v: store.seqs(v).epoch for v in viewers})

    # -- inputs, from any thread ---------------------------------------------------------

    def _put(self, name: str, value: Any = None) -> None:
        with self._lock:
            self._inputs.append((name, value))
        self._wake.set()

    def on_settings(self, settings: Settings) -> None:
        self._put("settings", settings)

    def on_ping_reply(self, reply: SyncReply | None, ticket: PingTicket | None) -> None:
        self._put("reply", (reply, ticket))

    def on_inbox(self) -> None:
        self._put("inbox")

    def on_scan(self, active: bool, at: float | None = None) -> None:
        """at is when Kodi announced it, so a busy worker doesn't date a scan's end late."""
        self._put("scan", (active, self._clock() if at is None else at))

    def on_viewers(self, at: float) -> None:
        """The household's viewers changed: an index built before this can't decide owners."""
        self._put("viewers", at)

    def on_quiet(self, quiet: bool) -> None:
        self._put("quiet", quiet)

    def on_window(self, open_: bool) -> None:
        self._put("window", open_)

    def on_wake(self) -> None:
        self._put("wake")

    def on_request(self) -> None:
        self._put("request")

    def on_snapshot(self, snapshot: IndexSnapshot) -> None:
        self._put("snapshot", snapshot)

    def on_rating_written(self, kind: str, kodi_id: int, value: int, sync_ids: tuple[str, ...]) -> None:
        self._put("rating_written", (kind, kodi_id, value, sync_ids))

    # -- folding inputs into the state -------------------------------------------------------

    def _take_inputs(self) -> None:
        with self._lock:
            inputs, self._inputs = self._inputs, []
        for name, value in inputs:
            try:
                self._apply_input(name, value)
            except Exception as exc:
                _log.warning("sync.engine.input_failed", input=name, error=str(exc))

    def _apply_input(self, name: str, value: Any) -> None:
        state = self._state
        if name == "settings":
            self._apply_settings(value)
            return
        if name == "reply":
            self._apply_reply(*value)
            return
        if name == "inbox":
            state = replace(state, inbox_waiting=True)
        elif name == "scan":
            active, at = value
            if state.scanning and not active:
                self._scan_ended_at = at
            state = replace(state, scanning=bool(active))
        elif name == "viewers":
            self._viewers_changed_at = value
            if self._snapshot is not None and not self._snapshot_usable(self._snapshot):
                state = replace(state, snapshot_usable=False)
        elif name == "quiet":
            state = replace(state, quiet=bool(value))
        elif name == "window":
            state = replace(state, window_open=bool(value))
        elif name == "wake":
            state = plan.request_full(state)
        elif name == "request":
            state = replace(state, requests_waiting=bool(read_requests(self._paths.requests)))
            self._state = state
            # Start may just have created the record.
            self._retry_record()
            return
        elif name == "rating_written":
            self.rating_writes.append(value)
        elif name == "snapshot":
            previous, self._snapshot = self._snapshot, value
            usable = self._snapshot_usable(value)
            after_scan = self._scan_ended_at > (previous.built_at if previous is not None else 0.0)
            state = plan.on_snapshot(state, usable=usable, after_scan=usable and after_scan)
        self._state = state

    def _apply_reply(self, reply: SyncReply | None, ticket: PingTicket | None) -> None:
        store = self._store
        seqs = {v: store.seqs(v) for v in reply.viewers} if store is not None and reply is not None else {}
        state, resets = plan.on_reply(self._state, reply, ticket, seqs, self._clock())
        if store is not None:
            for reset in resets:
                store.reset_for_cw(reset.viewer, reset.cw_seq, fresh=reset.fresh)
                self._fulls.pop(reset.viewer, None)
            for viewer in reply.viewers if reply is not None else ():
                # The seed window runs from the first reply that mapped the viewer.
                if not store.first_mapped_at(viewer):
                    store.set_first_mapped_at(viewer, self._utc_now())
        if reply is not None and ticket is not None:
            state = self._judge_device(state, reply, ticket)
        if reply is not None and store is not None:
            state = self._judge_settled(state, reply, store)
            mapping = plan.mapping_of(library_id(self._kodi), reply)
            full_ids = {v: store.full_library_id(v) for v in reply.viewers}
            state = plan.on_mapping(state, mapping, self._mapping, full_ids)
            self._mapping = mapping
        self._state = state
        self._publish_epochs()

    def _judge_device(self, state: plan.EngineState, reply: SyncReply, ticket: PingTicket) -> plan.EngineState:
        """What CrossWatch's answer says about this device: the sync device's id is recorded
        when an enabled block is answered enabled, and the device pauses until Start when
        another device holds the library or the household turned sync off and CrossWatch
        took that (sync/ping.py)."""
        started = read_started(self._paths.started)
        if started is None:
            return state
        device_id = self._device_id()
        if (
            reply.enabled
            and reply.reason is None
            and ticket.enabled
            and device_id
            and started.bound_device != device_id
        ):
            update_started(self._paths.started, started.start_id, bound_device=device_id)
        block = {"enabled": ticket.enabled}
        reason = pause_reason(block, reply, turned_off=self._turned_off)
        self._turned_off = False
        if reason is not None and not started.paused:
            update_started(self._paths.started, started.start_id, paused=True, paused_reason=reason)
            self._pause_cause = reason
            _log.info("sync.paused", reason=reason)
            state = replace(state, paused=True)
        # Each judged answer decides afresh, so the status clears once the old id is set back.
        self.device_id_changed = device_id_changed(reply, device_id, started)
        return state

    def _apply_settings(self, settings: Settings) -> None:
        previous, self._settings = self._settings, settings
        started = read_started(self._paths.started)
        on_this = started is not None and started.connection == connection_id(settings.webhook_base_url)
        # Paused too while this install's device id isn't the one CrossWatch bound: the ping
        # asks for nothing until Start runs again (sync/ping.py block_state), so nothing else
        # goes either.
        moved_id = started is not None and bool(started.bound_device) and started.bound_device != self._device_id()
        self._pause_cause = started.paused_reason if started is not None and started.paused else ""
        state = replace(
            self._state,
            started=on_this,
            sync_enabled=settings.sync_enabled,
            paused=bool(on_this and started is not None and (started.paused or moved_id)),
        )
        moved = previous is not None and (
            previous.webhook_base_url != settings.webhook_base_url or previous.webhook_token != settings.webhook_token
        )
        if moved:
            state = plan.on_token_changed(state, self._clock())
        if previous is not None and previous.sync_enabled and not settings.sync_enabled:
            self._turned_off = True
        self._state = state
        self._retry_record()

    # -- actions ------------------------------------------------------------------------

    def _act(self, action: plan.Action) -> float | None:
        """Carry out one action; the seconds to wait before the next, or None for at once."""
        now = self._clock()
        if isinstance(action, plan.Idle):
            return IDLE_SECONDS
        if isinstance(action, plan.Wait):
            return action.until - now
        viewer = getattr(action, "viewer", None)
        if isinstance(viewer, str):
            # The next turn starts after this viewer, so one busy viewer can't starve the others.
            self._state = replace(self._state, last_viewer=viewer)
        try:
            if isinstance(action, plan.Ping):
                self._ping_requested.set()
                self._state = plan.on_ping_asked(self._state, now)
            elif isinstance(action, plan.RequestRebuild):
                self._rebuild_requested.set()
                self._state = plan.on_rebuild_asked(self._state)
            elif isinstance(action, plan.DrainInbox):
                self._drain_inbox()
            elif isinstance(action, plan.FullUpload):
                self._full_upload(action)
            elif isinstance(action, plan.Delta):
                self._delta(action.viewer)
            elif isinstance(action, plan.FetchQueue):
                self._fetch_queue(action.viewer)
            elif isinstance(action, plan.SendAcks):
                self._send_acks(action.viewer)
            elif isinstance(action, plan.WriteKodi):
                self._write_kodi()
            elif isinstance(action, plan.RatingScan):
                self._rating_scan()
            elif isinstance(action, plan.ReadLibrary):
                self._read_library()
            elif isinstance(action, plan.TakeRequests):
                self._take_requests()
            elif isinstance(action, plan.SendExistingRatings):
                self._send_existing_ratings(action.viewer)
        except Exception as exc:
            _log.warning("sync.engine.action_failed", action=type(action).__name__, error=str(exc))
            return IDLE_SECONDS
        return None

    # -- the inbox ----------------------------------------------------------------------

    def _drain_inbox(self) -> None:
        """A person's marks, from the inbox file into the record, a batch per commit; a record
        leaves the inbox only after the commit that took it, and the record keeps the highest
        id it applied, so a crash in between never applies a mark twice.

        A mark is applied to the row it was made on: a fresh read whose file is the recorded
        one, or the entry the recorded file and the fresh row's tokens agree on (the same item
        under a new id); a mark that matches neither is dropped and counted. A mark Kodi can't
        be asked about right now stays for the next drain. A mark on an episode whose show the
        last library read didn't have goes to the back of the inbox and waits for a read.

        A mark on a row a media server add-on manages is left out, not counted as dropped. The
        add-on's map is read again here: the service thread knows only the last library read's
        server rows, so a mark from before the first read, or on a row the add-on added since,
        would otherwise reach the record. A map that can't be read holds the drain.
        """
        store, library = self._store, self.library
        if store is None or library is None:
            self._state = replace(self._state, inbox_waiting=False)
            return
        maps = read_server_rows(self._kodi)
        if maps.unreadable:
            self._state = plan.on_server_map(self._state, unreadable=True, now=self._clock())
            return
        server = maps.rows | library.server_backed
        records = self._inbox.pending(DRAIN_BATCH)
        applied_upto = store.inbox_applied()
        owners = self._owners(library)
        batch = Batch()
        waiting: list[InboxRecord] = []
        dropped = 0
        last = 0
        progress = False
        for record in records:
            if self._stopping.is_set():
                break
            if record.id <= applied_upto:
                last = record.id
                continue
            outcome = self._drain_one(store, library, owners, record, batch, server)
            if outcome == "retry":
                break
            last = record.id
            if outcome == "wait":
                waiting.append(record)
                continue
            progress = True
            dropped += outcome == "dropped"
        if last:
            # Back of the queue, so the marks behind them aren't held up. Before the commit:
            # once inbox_applied is past them, the remove below takes them too, so a file
            # that won't take them leaves the whole batch for a later drain (step pauses
            # after the raise). A crash between the two leaves a waiting mark in the inbox
            # twice, which applies to the same result.
            if waiting and not self._inbox.add_many([replace(r, id=0) for r in waiting]):
                raise _InboxBusy("waiting marks not re-queued")
            batch.inbox_applied = last
            store.commit(batch)
            self.dropped_marks += dropped
            for viewer, changed in batch.entries.items():
                if any(e.touched for e in changed):
                    # A person change waits: the queue is fetched before it goes up.
                    self._set_viewer(viewer, unsent=True, queue_settled=False)
            self._inbox.remove(last)
        # A full batch of nothing but waiting marks is not a reason to drain again: those wait
        # for a library read, which the drain outranks, so going round again would never end.
        # _read_library drains them once it has read.
        more = (len(records) == DRAIN_BATCH and len(waiting) < len(records)) or (bool(waiting) and progress)
        self._state = replace(self._state, inbox_waiting=more and last > 0)

    def _drain_one(
        self,
        store: RecordStore,
        library: Library,
        owners_of_row: Callable[[LibraryRow], tuple[str, ...]],
        record: InboxRecord,
        batch: Batch,
        server: frozenset[tuple[ItemKind, int]],
    ) -> Drained:
        kind = _KINDS.get(record.kind)
        if kind is None:
            _log.info("sync.drain.dropped", kind=record.kind, kodi_id=record.kodi_id, reason="kind")
            return "dropped"
        if (kind, record.kodi_id) in server or is_server_backed(record.file):
            _log.debug("sync.drain.server_backed", kind=record.kind, kodi_id=record.kodi_id)
            return "server"
        made, now = parse_utc(record.at), parse_utc(self._utc_now())
        if made is not None and now is not None and (now - made).total_seconds() > INBOX_MAX_AGE_SECONDS:
            # Kodi's state may have moved on since; a month-old mark is no longer the person's
            # latest word on the item.
            _log.info("sync.drain.dropped", kind=record.kind, kodi_id=record.kodi_id, reason="too_old")
            return "dropped"
        try:
            fresh = self._fresh_row(library, kind, record.kodi_id, record.file)
        except _Gone:
            fresh = None
        except Exception:
            return "retry"
        if fresh is None:
            _log.info("sync.drain.dropped", kind=record.kind, kodi_id=record.kodi_id, reason="other_item")
            return "dropped"
        if is_server_backed(fresh.key.file):
            # Added by the server add-on since the last read: the service thread had no file
            # for the row, so only the fresh read tells.
            _log.debug("sync.drain.server_backed", kind=record.kind, kodi_id=record.kodi_id)
            return "server"
        show = library.tvshows.get(fresh.show_kodi_id) if fresh.show_kodi_id is not None else None
        if kind == "episodes" and show is None:
            return "wait"
        owners = owners_of_row(fresh)
        entries = self._merged_entries(store, batch, owners, fresh)
        settings = self._settings.sync_settings if self._settings is not None else SyncSettings()
        outcomes = watched_change(
            entries,
            fresh,
            show,
            playcount=record.playcount,
            lastplayed=str(fresh.raw.get("lastplayed") or ""),
            owners=owners,
            settings=settings,
            made_at=record.at,
            next_upload_seq=self._next_upload_seq(store, owners),
            new_id=_new_id,
        )
        self._apply_outcomes(batch, outcomes)
        # Kodi announces nothing for a rating, so the rating and date the scan compares keep
        # their stored values; the rest is what Kodi has now.
        stored = store.seen(fresh.key)
        now_seen = seen_of(fresh.raw)
        if stored is not None:
            now_seen = replace(now_seen, userrating=stored.userrating, dateadded=stored.dateadded)
        batch.seen[fresh.key] = now_seen
        batch.seen_tokens[fresh.key] = fresh.tokens
        _log.debug("sync.drain.applied", kind=record.kind, kodi_id=record.kodi_id, outcomes=len(outcomes))
        return "applied"

    def _fresh_row(self, library: Library, kind: ItemKind, kodi_id: int, file: str) -> LibraryRow | None:
        """The row the mark was made on, read now; None when the id holds another item.
        Raises _Gone when Kodi has no such row, and what Kodi raises when it can't answer."""
        method, id_field, key = _DETAILS[kind]
        details = self._kodi.jsonrpc(method, {id_field: kodi_id, "properties": ["file"]}).get(key)
        if not isinstance(details, dict):
            raise _Gone
        current = strip_credentials(str(details.get("file") or ""))
        row = read_row(self._kodi, RowKey(library.library_id, kind, kodi_id, current), library.tvshows)
        if row is None:
            raise _Gone
        if not file or file == current:
            return row
        store = self._store
        if store is not None:
            for viewer in self._known_viewers():
                if any(entry.meta.get("file") == file for entry in store.match(viewer, row.tokens)):
                    return row
        return None

    def _known_viewers(self) -> list[str]:
        return [v.sync_id for v in self._viewers.viewers() if v.sync_id]

    def _owners(self, library: Library) -> Callable[[LibraryRow], tuple[str, ...]]:
        snapshot = self._snapshot
        if snapshot is None:
            return lambda row: ()
        return owners_of(
            snapshot,
            library.tvshows,
            self._memory.entries(),
            _profile_label(self._kodi),
            profile_has_own_database(self._kodi),
        )

    def _follow_owner_moves(self) -> None:
        """A full for each viewer who gained or lost an item since the index and remembered
        answers ownership was last judged by, so a playlist edit or a new answer reaches
        CrossWatch at the next index rather than at the daily full: a delta never removes a
        row, so only a full takes an item from its old owner. Both decisions run over the
        current library, so a row a scan removed never counts, while a row the new index is
        the first to place counts as a gain. Waits while something plays: the two passes over
        a large library take a while on a small box."""
        library, snapshot = self.library, self._snapshot
        if (
            not self._state.quiet
            or library is None
            or not library.complete
            or snapshot is None
            or not self._snapshot_usable(snapshot)
        ):
            return
        try:
            answers = self._memory.entries()
            last = self._owner_inputs
            if last is None or _same_owner_inputs(last, (snapshot, answers)):
                self._owner_inputs = (snapshot, answers)
                return
            profile, private = _profile_label(self._kodi), profile_has_own_database(self._kodi)
            before = owners_of(last[0], library.tvshows, last[1], profile, private)
            after = owners_of(snapshot, library.tvshows, answers, profile, private)
            moved = moved_viewers([*library.movies, *library.episodes], before, after)
        except Exception as exc:
            # The last judged inputs stay, so the next step tries again.
            _log.warning("sync.owners_moved_failed", error=str(exc))
            return
        self._owner_inputs = (snapshot, answers)
        mapped = self._state.reply.viewers if self._state.reply is not None else {}
        # A viewer whose full is going up gets another after it (request_full): the running
        # one was built before the move.
        wanted = sorted(v for v in moved if v in mapped)
        if wanted:
            _log.info("sync.owners_moved", viewers=len(wanted))
            self._state = plan.request_full(self._state, wanted)

    def _next_upload_seq(self, store: RecordStore, owners: tuple[str, ...]) -> int:
        reply = self._state.reply
        highest = 0
        for viewer in owners:
            highest = max(highest, store.seqs(viewer).sent)
            if reply is not None and viewer in reply.viewers:
                highest = max(highest, reply.viewers[viewer].upload_seq)
        return highest + 1

    # -- status -------------------------------------------------------------------------

    def _write_status(self) -> None:
        """The status screen's file, written when what it says changed."""
        state = self._state
        status: StatusState
        reason = ""
        if not state.started or not state.sync_enabled:
            status = "off"
        elif state.record_missing or state.unauthorized or state.no_sync:
            status = "stopped"
            reason = "record_missing" if state.record_missing else "unauthorized" if state.unauthorized else "no_sync"
        elif state.paused:
            # The status screen says why: each cause has its own way out.
            if self.device_id_changed:
                reason = "device_id_changed"
            elif self._pause_cause == "not_sync_device":
                reason = "not_sync_device"
            else:
                reason = "paused"
            status = "stopped"
        elif state.reply is not None and state.reply.reason:
            status, reason = "waiting", state.reply.reason
        elif (
            state.reply is not None
            and state.reply.enabled
            and not state.reply.viewers
            and not state.ping_failures
            and self._known_viewers()
        ):
            # CrossWatch answers but maps none of the viewers now: several viewers and none with
            # a sync user yet, or a Kodi it reaches over JSON-RPC and syncs itself. The reply, not the engine's
            # viewers, which keep a viewer CrossWatch stopped mapping; a failing ping keeps the
            # last reply, so this holds only while pings get answers. Only the household can
            # fix it, so it outranks the waits that end by themselves.
            status, reason = "waiting", "no_viewers"
        elif not plan.active(state) or plan.waiting_on(state) is not None:
            status, reason = "waiting", plan.waiting_on(state) or ""
        elif state.ping_failures or any(vs.run_unknown or vs.failures for vs in state.viewers.values()):
            # A ping CrossWatch refused, a call that failed and backs off, or a full CrossWatch
            # hasn't judged yet: the next step is CrossWatch's.
            status, reason = "waiting", "crosswatch"
        elif state.viewers and all(vs.settled and not _has_work(vs) for vs in state.viewers.values()):
            # settled alone stays true once the first round settled; up to date also needs
            # nothing waiting to go up or be acknowledged.
            status = "settled"
        else:
            status = "syncing"
        # A too_large while uploads go on is the parts being halved; only a stop is news.
        per_viewer = {
            v: problem
            for v, vs in state.viewers.items()
            if (problem := vs.uploads_stopped or ("" if vs.error == "too_large" else vs.error))
        }
        for viewer in self.late_seeds:
            per_viewer.setdefault(viewer, "late_seed")
        dropped = self.dropped_marks
        if os.path.exists(self._paths.inbox):
            try:
                dropped += self._inbox.dropped()
            except Exception:
                pass
        store = self._store
        try:
            listed = store.assignments() if store is not None else []
        except Exception:
            listed = []
        assignments = [{"id": a.id, "title": a.title, "group": a.group, "at": a.at} for a in listed]
        last_upload, waiting = self._upload_figures()
        counts, unowned = self._ownership_figures()
        snapshot = self._snapshot
        unreadable = sorted(snapshot.index.unreadable) if snapshot is not None and snapshot.index is not None else []
        current = StatusFile(
            state=status,
            reason=reason,
            per_viewer=per_viewer,
            dropped_marks=dropped,
            mass_ratings=len(self.held_ratings),
            assignments=assignments,
            last_upload=last_upload,
            waiting_changes=waiting,
            counts=counts,
            unowned_titles=unowned,
            unreadable_playlists=unreadable,
        )
        if current == self._last_status:
            return
        if status == "off" and self._last_status is None and not os.path.exists(self._paths.status):
            # A household that never set library sync up gets no file for it.
            self._last_status = current
            return
        if write_status(self._paths.status, replace(current, updated=self._utc_now())):
            self._last_status = current

    def _upload_figures(self) -> tuple[str, int]:
        """The last upload's time and the entries not yet sent, across viewers."""
        store = self._store
        if store is None:
            return "", 0
        known = self._record_figures
        if known is not None and (
            known[0] == store.commits or self._clock() - self._figures_at < STATUS_FIGURES_SECONDS
        ):
            return known[1], known[2]
        last, waiting = "", 0
        try:
            for viewer in self._known_viewers():
                last = max(last, store.last_upload_at(viewer))
                waiting += sum(entry.touched for entry in store.entries(viewer))
        except Exception:
            return (known[1], known[2]) if known is not None else ("", 0)
        self._record_figures = (store.commits, last, waiting)
        self._figures_at = self._clock()
        return last, waiting

    def _ownership_figures(self) -> tuple[dict[str, Any], list[str]]:
        """Who owns what, as of the last complete library read with an index."""
        library, snapshot = self.library, self._snapshot
        if library is None or snapshot is None or not library.complete:
            return self._owned
        try:
            # Ownership also follows the remembered answers, which change without a new library
            # read or index (a viewer change brings a new index).
            inputs = self._memory.entries()
            known = self._owned_from
            if known is not None and known[0] is library and known[1] is snapshot and known[2] == inputs:
                return self._owned
            counted = count_owners(library, self._owners(library))
        except Exception:
            return self._owned
        self._owned_from = (library, snapshot, inputs)
        self._owned = (to_status(counted), unowned_titles(counted, library))
        return self._owned

    # -- the library and uploads ----------------------------------------------------------

    def _interrupted(self) -> bool:
        """Stop a library read, a scan or a write run when the worker stops, Kodi starts
        playing or a window opens: such an input is waiting."""
        if self._stopping.is_set():
            return True
        with self._lock:
            return any((name == "quiet" and not value) or (name == "window" and value) for name, value in self._inputs)

    def _read_library(self) -> Library | None:
        """A full read of the library; publishes what the service thread needs from it, drops the
        Seen of rows gone from a complete read, and asks for a new index when the shows changed."""
        store = self._store
        assert store is not None
        previous = self.library
        generation = self._files.generation()
        maps = read_server_rows(self._kodi)
        # A map that can't be read leaves its add-on's rows unknown: no read counts until one
        # gets it, and the last read's rows, server-backed ones included, stay as they were.
        self._state = plan.on_server_map(self._state, unreadable=bool(maps.unreadable), now=self._clock())
        if maps.unreadable:
            return None
        library = read_library(
            self._kodi,
            library_id(self._kodi),
            may_continue=lambda: not self._interrupted(),
            previous_shows=previous.tvshows if previous is not None else {},
            to_utc=kodi_to_utc,
            server_rows=maps.rows,
        )
        if library is None:
            return None
        self.library = library
        rows = [*library.movies, *library.episodes]
        self._files.replace({(_KODI_TYPES[r.key.kind], r.key.kodi_id): r.key.file for r in rows}, generation)
        self.server_backed_rows = frozenset((_KODI_TYPES[kind], kodi_id) for kind, kodi_id in library.server_backed)
        if library.complete:
            live = {r.key for r in rows}
            gone = {key: None for key in store.seen_for_library(library.library_id) if key not in live}
            if gone:
                store.commit(Batch(seen=dict(gone)))
        shows = frozenset(library.tvshows)
        before = frozenset(previous.tvshows) if previous is not None else None
        state = plan.on_library_read(self._state, shows, before)
        if state.rebuild_wanted:
            self._show_ids_changed_at = self._clock()
        # Marks waiting for a show this read may have, and writes deferred for a row it may.
        self._state = replace(
            state,
            library_complete=library.complete,
            inbox_waiting=True,
            writes_pending=bool(store.pending_writes()),
        )
        return library

    def _sync_client(self) -> SyncClient | None:
        settings = self._settings
        if settings is None or not settings.webhook_base_url:
            return None
        key = (settings.webhook_base_url, settings.webhook_token, self._device_id())
        cached = self._client_cache
        if cached is None or cached[0] != key:
            self._client_cache = (key, self._client_factory(*key, self._stopping))
        assert self._client_cache is not None
        return self._client_cache[1]

    def _cw_seq(self, viewer: str) -> int:
        reply = self._state.reply
        seen = reply.viewers.get(viewer) if reply is not None else None
        return seen.upload_seq if seen is not None else 0

    def _set_viewer(self, viewer: str, **fields: Any) -> None:
        vs = self._state.viewers.get(viewer, plan.ViewerState())
        self._state = replace(self._state, viewers={**self._state.viewers, viewer: replace(vs, **fields)})

    def _build_full(self, action: plan.FullUpload) -> _Full | None:
        store = self._store
        assert store is not None
        viewer = action.viewer
        library = self._read_library()
        if library is None or self._state.rebuild_wanted:
            return None
        vs = self._state.viewers.get(viewer, plan.ViewerState())
        now_utc = self._utc_now()
        first = not store.first_full_committed(viewer)
        seed_args = {
            "first_full_committed": not first,
            "seed_viewers": store.seed_viewers(),
            "seed_started_at": store.seed_started_at(),
            "first_mapped_at": store.first_mapped_at(viewer),
            "now_utc": now_utc,
        }
        if plan.late_seed(viewer, **seed_args):
            self.late_seeds.add(viewer)
        entries = store.entries(viewer)
        owners = self._owners(library)
        if self._owner_inputs is None and self._snapshot is not None:
            # Moves after this full was built are judged against what it was built from.
            self._owner_inputs = (self._snapshot, self._memory.entries())
        owned = frozenset(r.key for r in [*library.movies, *library.episodes] if viewer in owners(r))
        rows = viewer_rows(
            library,
            viewer=viewer,
            owners=owners,
            match=lambda tokens: store.match(viewer, tokens),
            seen_for=lambda tokens, file: store.seen_for_tokens(tokens, file),
            new_id=_new_id,
            seed=plan.seeded(viewer, **seed_args),
            entries=entries,
            seen=store.seen_for_library(library.library_id),
            mode="full",
            touched=set(),
            now_utc=now_utc,
        )
        [seq] = store.reserve_upload_seqs(viewer, self._cw_seq(viewer), 1)
        self._publish_epochs()
        try:
            parts = full_parts(
                rows.rows,
                rows.tvshows,
                viewer_id=viewer,
                upload_id=_new_id(),
                upload_seq=seq,
                applied_seq=store.applied_seq(viewer),
                sources=library.sources,
                max_rows=vs.part_rows,
                fresh=vs.fresh,
            )
        except UploadTooLarge:
            store.upload_ended(viewer)
            self._publish_epochs()
            self._state = plan.on_too_large(self._state, viewer)
            return None
        stored = {e.key: e for e in entries}
        return _Full(seq, parts, rows, stored, owned, library, action.queue_settled, vs.fresh, first)

    def _full_upload(self, action: plan.FullUpload) -> None:
        store, client = self._store, self._sync_client()
        assert store is not None
        viewer = action.viewer
        if client is None:
            self._no_client(viewer)
            return
        vs = self._state.viewers.get(viewer, plan.ViewerState())
        job = self._fulls.get(viewer) if vs.full_in_progress else None
        if job is None:
            job = self._build_full(action)
            if job is None:
                return
            self._fulls[viewer] = job
            # Built and going up: a failure that doesn't drop it sends the same part again
            # (contract, Errors: a 503 on a first or fresh full), a single part included.
            self._set_viewer(viewer, full_in_progress=True)
        part = job.parts[job.next]
        try:
            answer = client.upload(part.body)
        except SyncError as err:
            self._upload_failed(viewer, "full", err, [part])
            return
        self._state = plan.on_success(self._state, viewer)
        if job.next + 1 < len(job.parts):
            job.next += 1
            self._state = plan.on_full_part(self._state, viewer, complete=False, fresh=job.fresh)
            return
        if answer.get("complete") is not True:
            # Every part went and CrossWatch didn't commit it, so it dropped this full: a new
            # one goes up with a higher seq, after a backoff, as for upload_stale.
            self._upload_failed(viewer, "full", SyncError(409, "upload_stale", False, from_crosswatch=True), [part])
            return
        self._commit_full(viewer, job)

    def _commit_full(self, viewer: str, job: _Full) -> None:
        """CrossWatch committed the full: store the build's entries and merges where the
        record still holds what they were built from (a mark drained between parts wins, and
        its item goes up again with the next delta), the catch-up writes, a Seen for each of
        the viewer's rows that has none yet (an existing Seen is the rating scan's and the
        catch-up's baseline, whoever set it), what the upload carried, and the first full."""
        store = self._store
        assert store is not None
        batch = Batch(
            uploaded_at=self._utc_now(), first_full_done={viewer}, full_library_id={viewer: job.library.library_id}
        )
        current = {e.key: e for e in store.entries(viewer)}

        def unchanged(key: str) -> bool:
            before, now = job.stored.get(key), current.get(key)
            return (before is None and now is None) or (
                before is not None and now is not None and before.change_count == now.change_count
            )

        written = dict(current)
        for entry in job.rows.entries:
            keys = job.rows.merged.get(entry.key, [entry.key])
            if all(unchanged(k) for k in keys):
                batch.entries.setdefault(viewer, []).append(entry)
                written[entry.key] = entry
                if len(keys) > 1:
                    batch.merged.setdefault(viewer, {})[entry.key] = list(keys)
                    for k in keys:
                        if k != entry.key:
                            written.pop(k, None)
        batch.pending_add.extend(job.rows.catch_up)
        stored = store.seen_for_library(job.library.library_id)
        for row in [*job.library.movies, *job.library.episodes]:
            if row.key in job.owned and row.key not in stored:
                batch.seen[row.key] = seen_of(row.raw)
                batch.seen_tokens[row.key] = row.tokens
        batch.unsent_carried[viewer] = _carried(written, job.parts, job.seq, job.queue_settled)
        if job.fresh:
            batch.fresh_done.add(viewer)
        store.commit(batch)
        store.confirm_upload_seq(viewer, job.seq)
        store.upload_ended(viewer)
        self._fulls.pop(viewer, None)
        self._publish_epochs()
        self._state = plan.on_full_part(self._state, viewer, complete=True, fresh=job.fresh)
        self._set_viewer(viewer, unsent=any(e.touched for e in store.entries(viewer)))

    def _delta(self, viewer: str) -> None:
        """The entries changed since their last upload. A resend keeps its seqs only for the
        identical bodies, and leaves out the ones CrossWatch already confirmed: it refuses
        anything not newer except an exact retry of its last delta."""
        store, client = self._store, self._sync_client()
        assert store is not None
        if client is None:
            self._no_client(viewer)
            return
        library = self.library or self._read_library()
        if library is None or self._state.rebuild_wanted:
            return
        entries = store.entries(viewer)
        touched = {e.key for e in entries if e.touched}
        vs = self._state.viewers.get(viewer, plan.ViewerState())
        rows = viewer_rows(
            library,
            viewer=viewer,
            owners=self._owners(library),
            match=lambda tokens: store.match(viewer, tokens),
            seen_for=lambda tokens, file: store.seen_for_tokens(tokens, file),
            new_id=_new_id,
            seed=False,
            entries=entries,
            seen=store.seen_for_library(library.library_id),
            mode="delta",
            touched=touched,
            now_utc=self._utc_now(),
        )
        applied = store.applied_seq(viewer)

        def build(first_seq: int) -> list[UploadBody]:
            return deltas(rows.rows, rows.tvshows, viewer_id=viewer, first_seq=first_seq, applied_seq=applied,
                          max_rows=vs.part_rows)  # fmt: skip

        if rows.entries or rows.merged:
            # The build's tidy-ups (merges, new tokens and meta) are the record's own, made in
            # this step with no input between: stored now, so what goes up is what's kept.
            store.commit(Batch(entries={viewer: list(rows.entries)}, merged={viewer: dict(rows.merged)}))
            entries = store.entries(viewer)
        probe = build(1)
        if not probe:
            self._set_viewer(viewer, unsent=False)
            return
        last = store.last_delta(viewer)
        bodies = build(last[0][0]) if last and len(last) == len(probe) else []
        if not bodies or [b.body for b in bodies] != [body for _, body in last]:
            seqs = store.reserve_upload_seqs(viewer, self._cw_seq(viewer), len(probe))
            bodies = build(seqs[0])
            store.set_last_delta(viewer, [(b.seq, b.body) for b in bodies])
        self._publish_epochs()
        built = {e.key: e for e in entries}
        confirmed = store.seqs(viewer).confirmed
        sent: list[UploadBody] = []
        changed = False
        try:
            for body in bodies:
                if self._stopping.is_set():
                    break
                if body.seq > confirmed:
                    answer = client.upload(body.body)
                    changed = changed or answer.get("changed") is True
                # A body CrossWatch already confirmed (its answer came, the commit after it
                # didn't) settles now, so its entries don't stay touched.
                store.confirm_upload_seq(viewer, body.seq)
                store.commit(
                    Batch(uploaded_at=self._utc_now(), unsent_carried={viewer: _carried(built, [body], body.seq, True)})
                )
                sent.append(body)
        except SyncError as err:
            # A body CrossWatch accepted before the failure may already have started a run.
            self._state = plan.on_delta(self._state, viewer, changed=changed)
            self._upload_failed(viewer, "delta", err, [b for b in bodies if b not in sent])
            return
        store.upload_ended(viewer)
        self._publish_epochs()
        self._state = plan.on_delta(plan.on_success(self._state, viewer), viewer, changed=changed)
        self._set_viewer(viewer, unsent=any(e.touched for e in store.entries(viewer)))

    def _upload_failed(self, viewer: str, kind: plan.Request, err: SyncError, bodies: list[UploadBody]) -> None:
        store = self._store
        assert store is not None
        self._state, outcome = plan.on_error(self._state, viewer, kind, err, self._clock())
        vs = self._state.viewers.get(viewer, plan.ViewerState())
        if kind == "delta" or not vs.full_in_progress:
            self._fulls.pop(viewer, None)
            store.upload_ended(viewer)
        if kind == "delta" and err.from_crosswatch and err.code == "upload_stale":
            # CrossWatch has a newer upload than these bodies: they go again under new seqs.
            store.set_last_delta(viewer, [])
        if outcome.drop_unsent:
            # CrossWatch refused the delta and would refuse it again: its person changes leave
            # unsent, so they can't win over CrossWatch forever.
            keys = {key for body in bodies for key in body.carried}
            dropped = [
                replace(e, unsent={}, unsent_upload={}, touched=False) for e in store.entries(viewer) if e.key in keys
            ]
            if dropped:
                store.commit(Batch(entries={viewer: dropped}))
                _log.warning("sync.upload.unsent_dropped", viewer=viewer, entries=len(dropped))
        self._publish_epochs()

    # -- the queue and Kodi --------------------------------------------------------------

    def _no_client(self, viewer: str) -> None:
        """No paired server to talk to: the viewer waits rather than being asked again."""
        self._set_viewer(viewer, backoff_until=self._clock() + IDLE_SECONDS)

    def _refresh_viewer(self, viewer: str) -> None:
        """What the record now owes CrossWatch and Kodi, after a fetch however far it got."""
        store = self._store
        assert store is not None
        self._set_viewer(
            viewer,
            acks_pending=bool(store.acks_pending(viewer)),
            unsent=any(e.touched for e in store.entries(viewer)),
        )
        self._state = replace(self._state, writes_pending=bool(store.pending_writes()))

    def _fetch_queue(self, viewer: str) -> None:
        """Every queued change for the viewer, page by page, into the record; then the person
        changes those pages answered are settled, only once every page arrived. Each page is
        committed on its own with the acks it owes, so an exit mid-fetch loses nothing
        CrossWatch would not send again."""
        store, client = self._store, self._sync_client()
        assert store is not None
        library = self.library
        if client is None or library is None:
            self._no_client(viewer)
            return
        fetched: set[tuple[str, str]] = set()
        after, pages, changed = 0, 0, 0
        try:
            while True:
                answer = client.queue(viewer, after)
                changes = answer.get("changes")
                changes = changes if isinstance(changes, list) else []
                applied = apply_changes(
                    viewer, changes, store=store, library=library, fetched_at=self._utc_now(), new_id=_new_id
                )
                store.commit(applied.batch)
                fetched |= applied.fetched
                pages, changed = pages + 1, changed + len(changes)
                if answer.get("has_more") is not True:
                    break
                following = answer.get("next_after")
                if not isinstance(following, int) or isinstance(following, bool) or following <= after:
                    # More pages and no way to ask for them: not every change arrived, so
                    # nothing is settled; the next fetch starts over.
                    _log.warning("sync.queue.bad_page", viewer=viewer, after=after)
                    self._refresh_viewer(viewer)
                    return
                if self._stopping.is_set():
                    self._refresh_viewer(viewer)
                    return
                after = following
        except SyncError as err:
            self._state, _ = plan.on_error(self._state, viewer, "queue", err, self._clock())
            self._refresh_viewer(viewer)
            self._publish_epochs()
            return
        store.commit(settle_unsent(viewer, fetched, store))
        _log.info("sync.queue.fetched", viewer=viewer, pages=pages, changes=changed)
        self._state = plan.on_success(self._state, viewer)
        self._set_viewer(viewer, queue_due=False, queue_settled=True)
        self._refresh_viewer(viewer)

    def _send_acks(self, viewer: str) -> None:
        """The acks the record owes CrossWatch, ack_batch per request; they leave the record
        only once CrossWatch answered, or when it refused them (CrossWatch keeps the changes
        queued, and they come back with a later fetch)."""
        store, client = self._store, self._sync_client()
        assert store is not None
        if client is None:
            self._no_client(viewer)
            return
        vs = self._state.viewers.get(viewer, plan.ViewerState())
        acks = store.acks_pending(viewer)[: vs.ack_batch]
        if not acks:
            self._set_viewer(viewer, acks_pending=False)
            return
        done = [(int(a["seq"]), str(a["change_id"])) for a in acks]
        try:
            client.ack(viewer, acks)
        except SyncError as err:
            self._state, outcome = plan.on_error(self._state, viewer, "ack", err, self._clock())
            if outcome.drop_acks:
                store.commit(Batch(acks_done={viewer: done}))
                _log.warning("sync.acks.dropped", viewer=viewer, count=len(done))
            self._set_viewer(viewer, acks_pending=bool(store.acks_pending(viewer)))
            self._publish_epochs()
            return
        store.commit(Batch(acks_done={viewer: done}))
        _log.info("sync.acks.sent", viewer=viewer, count=len(done))
        self._state = plan.on_success(self._state, viewer)
        self._set_viewer(viewer, acks_pending=bool(store.acks_pending(viewer)))

    def _write_kodi(self) -> None:
        """The pending writes, in batches. Between batches the inputs are taken and the inbox
        drained (under the same checks as its own step), so a person's mark is never held
        only in memory during a long run. A playback start queued meanwhile stops the run
        inside a batch; a scan, a window or anything else is seen between batches. Settings,
        ownership and remembered answers are those of the run's start."""
        store, library = self._store, self.library
        assert store is not None
        if library is None:
            self._state = replace(self._state, writes_pending=False)
            return
        settings = self._settings.sync_settings if self._settings is not None else SyncSettings()

        def free(state: plan.EngineState) -> bool:
            return plan.local_active(state) and plan.waiting_on(state) is None and not state.rebuild_wanted

        def between() -> None:
            self._take_inputs()
            if self._state.inbox_waiting and free(self._state):
                self._drain_inbox()

        def pause(seconds: float) -> None:
            # Ends early on stop: the pause between batches never holds the worker past it.
            self._stopping.wait(seconds)

        def may_write() -> bool:
            return (
                not self._stopping.is_set()
                and not self._interrupted()
                and free(self._state)
                and not self._state.window_open
            )

        report = Writer(
            self._kodi,
            store,
            self._own,
            may_write,
            self._clock,
            pause,
            settings=settings,
            library=library,
            owners=self._owners(library),
            between_batches=between,
            now_utc=self._utc_now,
            held_rows=lambda: frozenset(k for f in self.held_ratings for k in f.rated),
        ).run()
        _log.info("sync.writer.run", written=report.written, deferred=report.deferred, dropped=report.dropped)
        # Writes cut short by playback or a window wait for the next quiet moment; writes the
        # writer deferred (nothing written) wait for the next fetch or library read instead of
        # being retried in a loop.
        remaining = bool(store.pending_writes())
        self._state = replace(self._state, writes_pending=remaining and (report.written > 0 or not may_write()))

    # -- ratings, requests and the first round ------------------------------------------

    def _apply_outcomes(self, batch: Batch, outcomes: list[LocalOutcome]) -> bool:
        """Into the batch; True when an owner's record took the change and it goes up."""
        recorded = False
        for out in outcomes:
            if isinstance(out, Recorded):
                _put_entry(batch, out.viewer, out.entry)
                recorded = recorded or out.sent
            elif isinstance(out, ToAssign):
                batch.assignments_add.append(out.assignment)
        return recorded

    def _merged_entries(
        self, store: RecordStore, batch: Batch, viewers: tuple[str, ...], row: LibraryRow
    ) -> dict[str, Entry]:
        entries: dict[str, Entry] = {}
        for viewer in viewers:
            found = [_pending(batch, viewer, e) for e in store.match(viewer, row.tokens)]
            if len(found) > 1:
                entry = merge(found)
                batch.merged.setdefault(viewer, {})[entry.key] = sorted({e.key for e in found})
                _put_entry(batch, viewer, entry)
                entries[viewer] = entry
            elif found:
                entries[viewer] = found[0]
        return entries

    def _after_record(self, store: RecordStore, batch: Batch) -> None:
        """Viewers whose records a batch changed: their change waits for the queue and goes up."""
        for viewer, changed in batch.entries.items():
            if any(e.touched for e in changed):
                self._set_viewer(viewer, unsent=True, queue_settled=False)
        self._state = replace(self._state, writes_pending=bool(store.pending_writes()))

    def _rating_writes(self, store: RecordStore, library: Library) -> None:
        """The rating window's writes, as soon as Kodi can be asked, playback or not (one row
        read each): each row read back; recorded only when Kodi holds the value (the write may
        not have landed when its answer was lost) and the viewers who rated are the item's
        owners. The rating is stored as the row's Seen and pending rating writes for the item
        are dropped in every case, so neither the scan nor the writer takes it for anything
        else. A row Kodi can't answer about now stays for the next step. As in the drain, the
        media server add-ons' maps are read again, so a row an add-on added since the last
        read (direct paths look like any file) is left to it; a map that can't be read keeps
        the writes."""
        if not self.rating_writes:
            return
        maps = read_server_rows(self._kodi)
        if maps.unreadable:
            self._state = plan.on_server_map(self._state, unreadable=True, now=self._clock())
            return
        server = maps.rows | library.server_backed
        writes, self.rating_writes = self.rating_writes, []
        owners_of_row = self._owners(library)
        for write in writes:
            kind_name, kodi_id, value, rated = write
            kind = _KINDS.get(kind_name)
            if kind is None:
                continue
            try:
                row = self._fresh_row(library, kind, kodi_id, "")
            except _Gone:
                continue
            except Exception:
                self.rating_writes.append(write)
                continue
            if row is None or (kind, kodi_id) in server or is_server_backed(row.key.file):
                # A media server add-on's item: it syncs that item with its server itself.
                continue
            batch = Batch()
            if int(row.raw.get("userrating") or 0) == value:
                show = library.tvshows.get(row.show_kodi_id) if row.show_kodi_id is not None else None
                owners = owners_of_row(row)
                entries = self._merged_entries(store, batch, owners, row)
                outcome = rating_window_write(
                    entries, row, show, value=value, rated=rated, owners=owners, made_at=self._utc_now()
                )
                self._apply_outcomes(batch, outcome)
            stored = store.seen(row.key)
            now_seen = seen_of(row.raw)
            if stored is not None:
                now_seen = replace(now_seen, dateadded=stored.dateadded)
            batch.seen[row.key] = now_seen
            batch.seen_tokens[row.key] = row.tokens
            batch.pending_done.extend(
                w.id for w in store.pending_writes() if w.group == "ratings" and w.tokens & frozenset(row.tokens)
            )
            store.commit(batch)
            self._after_record(store, batch)

    def _rating_scan(self) -> None:
        store, library = self._store, self.library
        assert store is not None
        self._state = replace(self._state, rating_scan_due=False)
        if library is None:
            self._last_rating_scan = self._clock()
            return
        self._rating_writes(store, library)
        in_flight: dict[RowKey, dict[str, Any]] = {}
        for write in store.pending_writes():
            in_flight.update(in_flight_rows(write))
        held = {k: f.value for f in self.held_ratings for k in f.rated}
        result = rating_scan(
            self._kodi,
            library,
            store.seen_for_library(library.library_id),
            in_flight,
            lambda key: read_row(self._kodi, key, library.tvshows),
            held=held,
            may_continue=lambda: not self._interrupted(),
        )
        if result.complete or not self._interrupted():
            # A scan over an incomplete read is never complete, so waiting for a complete one
            # would scan again at once until the next full; it waits its interval instead.
            self._last_rating_scan = self._clock()
        if not library.complete and not self._interrupted():
            # The read is what keeps the scan (and fetches and deltas) short of complete, and
            # nothing else reads again before the daily full.
            self._state = plan.request_full(self._state)
        if result.released:
            self.held_ratings = [f for f in self.held_ratings if not set(f.rated) & result.released]
        if result.held:
            # Added to what is already held: the household answers for all of them at once.
            known = {f.row.key for f in self.held_ratings}
            self.held_ratings += [f for f in result.held if f.row.key not in known]
        batch = Batch(seen=dict(result.seen))
        self._record_ratings(store, library, result.found, batch)
        store.commit(batch)
        self._after_record(store, batch)
        _log.info("sync.rating_scan", found=len(result.found), held=len(self.held_ratings), complete=result.complete)

    def _record_ratings(self, store: RecordStore, library: Library, found: list[FoundRating], batch: Batch) -> None:
        """Ratings set in Kodi into the owners' records. Only a rating a record took gives the
        item's other copies the value: one left on the assignment list or not sent (a cleared
        rating with removals off) leaves Kodi as the person set it."""
        owners_of_row = self._owners(library)
        settings = self._settings.sync_settings if self._settings is not None else SyncSettings()
        now = self._utc_now()
        for rating in found:
            row = rating.row
            show = library.tvshows.get(row.show_kodi_id) if row.show_kodi_id is not None else None
            owners = owners_of_row(row)
            entries = self._merged_entries(store, batch, owners, row)
            outcomes = rating_change(
                entries, row, show, value=rating.value, owners=owners, settings=settings, made_at=now, new_id=_new_id
            )
            if not self._apply_outcomes(batch, outcomes):
                continue
            for copy in rating.copies:
                batch.pending_add.append(
                    PendingWrite(id=_new_id(), row=copy, tokens=frozenset(row.tokens), group="ratings", created=now)
                )

    def _take_requests(self) -> None:
        """The household's requests from the settings scripts and the status screen. Each
        leaves the file only after its effect is committed; one that fails, or has to wait for
        Kodi to be quiet, stays for the next request or session, and the worker doesn't spin
        on it."""
        store = self._store
        assert store is not None
        done: set[str] = set()
        for request in read_requests(self._paths.requests):
            try:
                if self._take_request(store, request):
                    done.add(request.id)
            except Exception as exc:
                _log.warning("sync.request.failed", kind=request.kind, error=str(exc))
        if done and not done_requests(self._paths.requests, done):
            _log.warning("sync.request.not_removed", count=len(done))
        self._state = replace(self._state, requests_waiting=False)

    def _take_request(self, store: RecordStore, request: Request) -> bool:
        """True when the request's effect is committed (or there is nothing to do)."""
        settings = self._settings.sync_settings if self._settings is not None else SyncSettings()
        if request.kind == "assign":
            wanted = request.args.get("assignment")
            raw = request.args.get("viewers")
            viewers = [v for v in raw if isinstance(v, str)] if isinstance(raw, list) else []
            assignment = next((a for a in store.assignments() if a.id == wanted), None)
            if assignment is None:
                return True
            reply = self._state.reply
            floor = max(
                [store.seqs(v).sent for v in viewers]
                + [reply.viewers[v].upload_seq for v in viewers if reply is not None and v in reply.viewers]
                + [0]
            )
            batch = apply_assignment(assignment, viewers, store, settings, floor + 1)
            store.commit(batch)
            self._after_record(store, batch)
            return True
        if request.kind == "send_existing_ratings":
            for viewer in self._known_viewers():
                self._set_viewer(viewer, existing_ratings_due=True)
            self._existing_sent.clear()
            return True
        if request.kind in ("mass_ratings_send", "mass_ratings_drop"):
            library = self.library
            if not self.held_ratings:
                # Nothing held (an answer from before a restart): the next scan asks again.
                return True
            if library is None or plan.waiting_on(self._state) is not None:
                return False
            if request.kind == "mass_ratings_send":
                self._send_held(store, library)
            else:
                self._drop_held(store)
            return True
        return True

    def _send_held(self, store: RecordStore, library: Library) -> None:
        """The household said send: each held rating is read again and recorded as a person's
        change, except where a record took a rating from CrossWatch during the hold, which is
        newer. Every copy's Seen takes the value either way."""
        owners_of_row = self._owners(library)
        batch = Batch()
        fresh: list[FoundRating] = []
        for held in self.held_ratings:
            row = read_row(self._kodi, held.row.key, library.tvshows)
            if row is None or int(row.raw.get("userrating") or 0) != held.value:
                continue
            owners = owners_of_row(row)
            took_cw = any("ratings" in e.applied_change for v in owners for e in store.match(v, row.tokens))
            if not took_cw:
                fresh.append(held)
        self._record_ratings(store, library, fresh, batch)
        self._seen_for_held(store, batch)
        store.commit(batch)
        self.held_ratings = []
        self._after_record(store, batch)

    def _drop_held(self, store: RecordStore) -> None:
        """The household said don't send: Kodi's values become every copy's Seen, nothing goes up."""
        batch = Batch()
        self._seen_for_held(store, batch)
        store.commit(batch)
        self.held_ratings = []

    def _seen_for_held(self, store: RecordStore, batch: Batch) -> None:
        for held in self.held_ratings:
            for key in held.rated:
                stored = store.seen(key)
                if stored is not None:
                    batch.seen[key] = replace(stored, userrating=held.value)

    def _send_existing_ratings(self, viewer: str) -> None:
        """Kodi's own ratings for the viewer's seeded single-owner items, once the first round
        settled, from a complete read of Kodi as it is now. The started file says so once every
        viewer CrossWatch maps has sent."""
        store = self._store
        assert store is not None
        library = self._read_library()
        if library is None or self._state.rebuild_wanted or not library.complete:
            return
        rows = [*library.movies, *library.episodes]
        sent = existing_ratings(store.entries(viewer), rows, self._owners(library), viewer, self._utc_now())
        if sent:
            batch = Batch(entries={viewer: sent})
            store.commit(batch)
            self._after_record(store, batch)
        self._set_viewer(viewer, existing_ratings_due=False)
        self._existing_sent.add(viewer)
        _log.info("sync.existing_ratings", viewer=viewer, count=len(sent))
        reply = self._state.reply
        mapped = set(reply.viewers) if reply is not None else set()
        if mapped and mapped <= self._existing_sent:
            started = read_started(self._paths.started)
            if started is not None:
                update_started(self._paths.started, started.start_id, existing_ratings_sent=True)

    def _judge_settled(self, state: plan.EngineState, reply: SyncReply, store: RecordStore) -> plan.EngineState:
        """The first round settles at a quiet ping judged for the viewer, long enough after its
        first full, with nothing waiting either way; then, if Start chose it, the viewer's
        existing ratings are due once."""
        started = read_started(self._paths.started)
        wanted = started is not None and started.existing_ratings and not started.existing_ratings_sent
        pending = bool(store.pending_writes())
        viewers = dict(state.viewers)
        for viewer, seen in reply.viewers.items():
            vs = viewers.get(viewer, plan.ViewerState())
            if vs.settled or not vs.first_full_committed or not vs.judged or vs.run_unknown:
                continue
            if plan.first_round_settled(
                first_full_at=store.first_full_at(viewer),
                now_utc=self._utc_now(),
                queue_pending=reply.queue_pending,
                run_pending=seen.run_pending,
                unsent=vs.unsent,
                unapplied=pending or vs.acks_pending,
            ):
                store.set_settled(viewer)
                viewers[viewer] = replace(vs, settled=True, existing_ratings_due=vs.existing_ratings_due or wanted)
                _log.info("sync.first_round_settled", viewer=viewer)
        return replace(state, viewers=viewers)


def _has_work(vs: plan.ViewerState) -> bool:
    return (
        vs.unsent
        or vs.acks_pending
        or vs.full_due
        or vs.full_in_progress
        or vs.full_again
        or vs.in_flight
        or vs.existing_ratings_due
    )


def _carried(job_built: Mapping[str, Entry], bodies: list[UploadBody], seq: int, settled: bool) -> dict[str, Carried]:
    """What accepted bodies carried per entry: the person changes they held settle only when
    the queue was fetched and applied first (a CrossWatch change could be newer)."""
    out: dict[str, Carried] = {}
    for body in bodies:
        for key, groups in body.carried.items():
            entry = job_built.get(key)
            if entry is None:
                continue
            out[key] = Carried(
                change_count=entry.change_count,
                groups={g: seq for g in groups if g in entry.unsent} if settled else {},
                applied={g: entry.applied_change[g] for g in groups if g in entry.applied_change},
            )
    return out


def _new_id() -> str:
    return os.urandom(8).hex()


def _profile_label(kodi: KodiApi) -> str:
    try:
        return str(kodi.jsonrpc("Profiles.GetCurrentProfile").get("label") or "").strip()
    except Exception:
        return ""


def _pending(batch: Batch, viewer: str, entry: Entry) -> Entry:
    """The entry as this batch already changed it, so two marks on one item build on each
    other."""
    for e in batch.entries.get(viewer, []):
        if e.key == entry.key:
            return e
    return entry


def _put_entry(batch: Batch, viewer: str, entry: Entry) -> None:
    entries = batch.entries.setdefault(viewer, [])
    entries[:] = [e for e in entries if e.key != entry.key] + [entry]


def _same_owner_inputs(a: tuple[IndexSnapshot, Mapping[str, Any]], b: tuple[IndexSnapshot, Mapping[str, Any]]) -> bool:
    """Whether two judgments would decide alike: the hourly rebuild of an unchanged index is a
    new snapshot with the same membership."""
    (snap_a, answers_a), (snap_b, answers_b) = a, b
    if snap_a is snap_b:
        return answers_a == answers_b
    if snap_a.index is None or snap_b.index is None:
        return False
    return snap_a.index.by_key == snap_b.index.by_key and snap_a.viewers == snap_b.viewers and answers_a == answers_b
