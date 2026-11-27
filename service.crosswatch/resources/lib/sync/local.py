# SPDX-License-Identifier: GPL-2.0-only
"""Telling a person's watched mark in Kodi from everything else Kodi announces.

Kodi announces a play count change with VideoLibrary.OnUpdate carrying "playcount", and it
does so for playback's own count too (VideoDatabase.cpp:6691-6693 through SetPlayCount), for
a JSON-RPC write by this add-on or another one, for a scan and for Refresh information. The
sender is always "xbmc", so only context separates them. Everything here runs on the service
thread when the notification arrives; a person's mark is buffered and reaches the worker
through the inbox file, never directly.

What playback announces, as recorded on Kodi 21.3 and 22 RC1 (verification.md, Task 13a
Step 0): the play's own update reaches an add-on before its onPlayBackStopped or
onPlayBackEnded, while isPlaying() can already be false; back to back, item N's update
arrives before item N+1's start callbacks. So the item stays "playing" here until its stop
callback, never only because isPlaying() turned false: that happens first
(VideoPlayer.cpp:2565-2586), and a tick can run in between. A play whose stop callback never
comes ends after QUIET_END_SECONDS of Kodi playing nothing, or at the next start.

An update after the stop callback is possible too. A stopped item covers one raise for
PLAYBACK_QUIET_SECONDS when Kodi counted the play, or when the add-on can't tell whether it
did (no stop callback, or the callback came for a play the add-on never saw start), unless
its close (a raise, then a bare {"id", "type"} update) already arrived while it played.

Documented limits: a mark made during a scan is not sent; a mark on the playing item is
taken for playback; play counts another add-on writes through JSON-RPC look exactly like a
person's mark (VideoLibrary.cpp:632-638) and are treated as one.

Log events: sync.inbox.flushed (debug), sync.inbox.buffer_full (warning),
sync.files.removed (debug).
"""
from __future__ import annotations

import os
import re
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Literal, Protocol, Tuple
from xml.etree import ElementTree

from resources.lib.kodi import KodiApi
from resources.lib.log import get_logger
from resources.lib.sync.constants import INBOX_MAX, PLAYBACK_QUIET_SECONDS
from resources.lib.sync.files import Inbox, InboxRecord, StartedFile, read_started
from resources.lib.sync.library_id import BARE_AMPERSAND, advanced_settings_text

_log = get_logger("sync")

KodiKind = Literal["movie", "episode"]
Verdict = Literal["own", "playback", "scan", "added", "no_playcount", "not_video", "server", "person"]
_PlayKey = Tuple[str, int]

# How long Kodi plays nothing before a play whose stop callback never came counts as ended.
# The callback trails isPlaying() turning false by about 0.1 s (verification.md, Task 13a
# Step 0), so this only matters for a callback Kodi dropped.
QUIET_END_SECONDS = 10.0


class OwnEchoes(Protocol):
    """What classify needs from the writer's note of its own writes (writer.OwnWrites)."""

    def matches(self, kodi_type: str, kodi_id: int, data: Mapping[str, Any]) -> bool: ...


@dataclass
class _Play:
    key: _PlayKey | None  # None: a video Kodi plays that couldn't be resolved
    start_count: int | None
    # The play's close arrived: Kodi follows it with a bare {"id", "type"} update at once,
    # which a mark made during the play doesn't send.
    close_seen: bool = False


@dataclass
class _Stop:
    at: float
    start_count: int | None
    raised: bool
    spent: bool


class RecentPlays:
    """What is playing and what just stopped, as the playback callbacks report it.

    Thread-safe; the service thread writes it from the callbacks and reads it in classify.
    A play whose item couldn't be resolved covers every announcement while it lasts and for
    PLAYBACK_QUIET_SECONDS after, since its library id is unknown.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._playing: _Play | None = None
        self._quiet_since: float | None = None
        self._unresolved_until: float | None = None
        self._stopped: dict[_PlayKey, _Stop] = {}

    def started(self, kind: str | None, kodi_id: int | None, playcount: int | None, now: float) -> None:
        """A play began; kind and kodi_id None for a video that couldn't be resolved."""
        with self._lock:
            self._end(now)
            key = (kind, kodi_id) if kind is not None and kodi_id is not None else None
            self._playing = _Play(key, playcount)
            self._quiet_since = None

    def stopped(self, kind: str, kodi_id: int, raised: bool, now: float) -> None:
        """The play of this item ended; raised is whether Kodi's threshold counted it."""
        with self._lock:
            playing = self._playing
            if playing is not None and playing.key == (kind, kodi_id):
                self._playing = None
                self._stopped[(kind, kodi_id)] = _Stop(now, playing.start_count, raised, playing.close_seen)
            else:
                # No start was seen for it (a play skipped before resolving, or a callback
                # Kodi dropped): the raise it may announce is still playback's.
                self._stopped[(kind, kodi_id)] = _Stop(now, None, raised, False)

    def quiet(self, now: float) -> None:
        """Kodi plays nothing (or plays something that isn't a library video). Ends a play
        that couldn't be resolved at once; a resolved play ends at its stop callback, which
        trails isPlaying(), or after QUIET_END_SECONDS when that callback never comes."""
        with self._lock:
            playing = self._playing
            if playing is None:
                return
            if playing.key is None:
                self._end(now)
            elif self._quiet_since is None:
                self._quiet_since = now
            elif now - self._quiet_since >= QUIET_END_SECONDS:
                self._end(now)

    def active(self) -> None:
        """Kodi plays something: a gap in isPlaying() between two items isn't an end."""
        with self._lock:
            self._quiet_since = None

    def covers(self, kind: str, kodi_id: int, data: Mapping[str, Any], now: float) -> bool:
        with self._lock:
            self._expire(now)
            if self._unresolved_until is not None:
                return True
            playing = self._playing
            if playing is not None:
                if playing.key is None:
                    return True
                if playing.key == (kind, kodi_id):
                    if "item" not in data:
                        playing.close_seen = True
                    return True
            stop = self._stopped.get((kind, kodi_id))
            if stop is None or not stop.raised or stop.spent:
                return False
            if not _raises(data.get("playcount"), stop.start_count):
                return False
            stop.spent = True
            return True

    def _end(self, now: float) -> None:
        playing = self._playing
        self._playing = None
        self._quiet_since = None
        if playing is None:
            return
        if playing.key is None:
            self._unresolved_until = now + PLAYBACK_QUIET_SECONDS
        else:
            # A resolved play that ended without its stop callback: whether it passed the
            # threshold is unknown, so its one raise is still taken for playback's.
            self._stopped[playing.key] = _Stop(now, playing.start_count, True, playing.close_seen)

    def _expire(self, now: float) -> None:
        if self._unresolved_until is not None and now > self._unresolved_until:
            self._unresolved_until = None
        for key in [k for k, s in self._stopped.items() if now - s.at > PLAYBACK_QUIET_SECONDS]:
            del self._stopped[key]


# Kodi's defaults and range for <video><playcountminimumpercent> (AdvancedSettings.cpp:609).
PLAYCOUNT_MINIMUM_PERCENT = 90.0
_PERCENT_RANGE = (0.0, 101.0)
_SYSTEM_SETTINGS = "special://xbmc/system/advancedsettings.xml"
# What atof reads: a leading number, the rest ignored; no number at all reads as 0.
_ATOF = re.compile(r"\s*[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?")


def _percent_from(text: str | None, current: float) -> float:
    if not text:
        return current
    try:
        root = ElementTree.fromstring(BARE_AMPERSAND.sub("&amp;", text))
    except ElementTree.ParseError:
        return current  # Kodi logs the error and loads nothing from that file
    if root.tag.lower() != "advancedsettings":
        return current
    element = root.find("video/playcountminimumpercent")
    if element is None or not (element.text or "").strip():
        return current
    match = _ATOF.match(element.text or "")
    value = float(match.group()) if match else 0.0
    return min(max(value, _PERCENT_RANGE[0]), _PERCENT_RANGE[1])


def kodi_playcount_percent(kodi: KodiApi) -> float:
    """playcountminimumpercent exactly as Kodi loads it: the system file, then the profile's
    file whole or else the master's (as library_id.py), a value that isn't a number read as
    Kodi's atof reads it (so "abc" is 0, which turns automatic marking off), clamped to 0-101.

    advanced_settings.read_thresholds keeps the default for a value that isn't a number,
    which is right for the reporter; sync has to agree with what Kodi actually announces.
    """
    percent = _percent_from(kodi.read_text(_SYSTEM_SETTINGS), PLAYCOUNT_MINIMUM_PERCENT)
    return _percent_from(advanced_settings_text(kodi), percent)


def kodi_counts_play(percent: float | None, minimum: float, band: float = 0.0) -> bool:
    """Whether Kodi raised the play count when this play stopped: 0 < minimum <= percent
    (ApplicationPlayerCallback.cpp:127-133; 0 and 101 turn automatic marking off).

    band widens it by one sample's worth of percent: the add-on's percent is its last sample,
    which can trail the position Kodi judged at the stop.
    """
    if percent is None or not 0 < minimum <= 100:
        return False
    return percent >= minimum - band


def plays_at_start(kodi: KodiApi, now: float) -> RecentPlays:
    """RecentPlays for a service that starts while Kodi may already play something, whose
    start callbacks it never saw. A library movie or episode is keyed as it is; a video Kodi
    doesn't name is taken for an unresolved play, since a person's mark lost to coverage is
    the safer error than playback taken for a mark. Live TV, music and files outside the
    library start nothing (Kodi announces no library update for them)."""
    plays = RecentPlays()
    if not kodi.is_playing_video():
        return plays
    try:
        players = kodi.jsonrpc("Player.GetActivePlayers").get("result") or []
        player_id = next(p["playerid"] for p in players if isinstance(p, Mapping) and p.get("type") == "video")
        item = kodi.jsonrpc("Player.GetItem", {"playerid": player_id, "properties": ["playcount"]}).get("item")
    except Exception:
        plays.started(None, None, None, now)
        return plays
    if not isinstance(item, Mapping):
        plays.started(None, None, None, now)
        return plays
    kind, kodi_id, playcount = item.get("type"), item.get("id"), item.get("playcount")
    if kind in ("movie", "episode") and isinstance(kodi_id, int) and not isinstance(kodi_id, bool) and kodi_id >= 0:
        count = playcount if isinstance(playcount, int) and not isinstance(playcount, bool) else None
        plays.started(kind, kodi_id, count, now)
    return plays


def _raises(playcount: Any, start_count: int | None) -> bool:
    """A count above the one the play started from. A count changed during the play, by a
    mark on the playing item or another box, is still playback's own close
    (VideoDatabase.cpp:6672-6673), so only "above the start" matters, not "start + 1"."""
    if not isinstance(playcount, int) or isinstance(playcount, bool):
        return False
    return start_count is None or playcount > start_count


def update_item(data: Mapping[str, Any]) -> tuple[str, int] | None:
    """The item an OnUpdate names: {"item": {"id", "type"}, ...} or the bare {"id", "type"}."""
    nested = data.get("item")
    item: Mapping[str, Any] = nested if isinstance(nested, Mapping) else data
    kind, kodi_id = item.get("type"), item.get("id")
    if not isinstance(kind, str) or not isinstance(kodi_id, int) or isinstance(kodi_id, bool):
        return None
    return kind, kodi_id


def classify(
    data: Mapping[str, Any],
    *,
    received: float,
    own: OwnEchoes,
    plays: RecentPlays,
    scanning: bool,
    server_backed: Callable[[str, int], bool],
) -> Verdict:
    item = update_item(data)
    if item is None or item[0] not in ("movie", "episode"):
        return "not_video"
    kind, kodi_id = item
    # First: matching uses the note up, and the echo of a write without a count change has no
    # "playcount" either.
    if own.matches(kind, kodi_id, data):
        return "own"
    if data.get("added"):
        return "added"
    if data.get("transaction") or scanning:
        return "scan"
    # Before the playcount check: the bare update that follows a play's close carries none,
    # and it is what tells the close from a mark made during the play.
    if plays.covers(kind, kodi_id, data, received):
        return "playback"
    if "playcount" not in data:
        return "no_playcount"
    if server_backed(kind, kodi_id):
        return "server"
    return "person"


class FileIndex:
    """Each library row's file as the last library read had it, kept on the service thread.

    The worker replaces it whole after a read; VideoLibrary.OnRemove takes a row out at once,
    so a mark on a SQLite id Kodi reuses for another file isn't recorded under the old file.
    A read that began before a removal doesn't bring the row back: the worker takes
    generation() before it reads and hands it to replace().
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._files: dict[_PlayKey, str] = {}
        self._generation = 0
        # The generation each removal was made in, until a read taken after it replaces them.
        self._removed: dict[_PlayKey, int] = {}

    def generation(self) -> int:
        with self._lock:
            return self._generation

    def replace(self, files: Mapping[_PlayKey, str], read_from: int) -> None:
        with self._lock:
            removed_since = {key for key, gen in self._removed.items() if gen >= read_from}
            self._files = {key: file for key, file in files.items() if key not in removed_since}
            self._removed = {key: gen for key, gen in self._removed.items() if key in removed_since}

    def remove(self, kind: str, kodi_id: int) -> None:
        with self._lock:
            removed = self._files.pop((kind, kodi_id), None)
            self._removed[(kind, kodi_id)] = self._generation
            self._generation += 1
        if removed is not None:
            _log.debug("sync.files.removed", kind=kind, kodi_id=kodi_id)

    def file(self, kind: str, kodi_id: int) -> str:
        return self._files.get((kind, kodi_id), "")


class PersonBuffer:
    """A person's marks between the notification and the tick that writes them to the inbox.

    Kept in memory only until that tick: the inbox file is what survives a Kodi exit while
    the worker is busy. A file that can't be written keeps them for the next tick, up to the
    inbox's own limit, oldest dropped first as the inbox does.
    """

    def __init__(self) -> None:
        self._records: list[InboxRecord] = []

    def add(self, record: InboxRecord) -> None:
        self._records.append(record)
        if len(self._records) > INBOX_MAX:
            del self._records[0]
            _log.warning("sync.inbox.buffer_full", kept=INBOX_MAX)

    def __len__(self) -> int:
        return len(self._records)

    def flush(self, inbox: Inbox) -> bool:
        """True when records were written and the worker should be told."""
        if not self._records:
            return False
        records = list(self._records)
        if not inbox.add_many(records):
            return False
        self._records.clear()
        _log.debug("sync.inbox.flushed", count=len(records))
        return True


class MarkGate:
    """Whether a person's mark is recorded: Start ran for the current pairing, sync is on and
    the worker hasn't paused this device.

    The started file is read again only when its signature (modification time, size and
    inode) changes, one stat per tick, so a pause the worker writes is seen without reading
    the file per notification. The file is replaced atomically, so the inode changes on every
    write even where two writes share a coarse timestamp (FAT, some network shares).
    """

    def __init__(
        self, path: str, stat: Callable[[str], tuple[int, int, int] | None], device_id: Callable[[], str] = lambda: ""
    ) -> None:
        self._path = path
        self._stat = stat
        self._device_id = device_id
        self._mtime: tuple[int, int, int] | None = None
        self._started: StartedFile | None = None
        self._connection = ""
        self._sync_enabled = False

    def on_settings(self, connection: str, sync_enabled: bool) -> None:
        self._connection = connection
        self._sync_enabled = sync_enabled
        self._mtime = None
        self.refresh()

    def refresh(self) -> None:
        mtime = self._stat(self._path)
        if mtime is not None and mtime == self._mtime:
            return
        self._mtime = mtime
        self._started = read_started(self._path) if mtime is not None else None

    def open(self) -> bool:
        started = self._started
        if started is None or started.connection != self._connection or not self._sync_enabled or started.paused:
            return False
        # Another device id than the one CrossWatch bound: paused until Start, as the worker is.
        return not started.bound_device or started.bound_device == self._device_id()


def file_signature(path: str) -> tuple[int, int, int] | None:
    try:
        st = os.stat(path)
    except OSError:
        return None
    return st.st_mtime_ns, st.st_size, st.st_ino
