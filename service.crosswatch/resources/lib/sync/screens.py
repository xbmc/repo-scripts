# SPDX-License-Identifier: GPL-2.0-only
"""The library sync screens, run as settings scripts: "Set up library sync" and "Library sync
status".

Scripts never call the engine. They leave files for it and bump the sync_request setting so
the service hears of it.

The setup screen reads the library and the playlists itself to show who owns what, and on
Start writes what the engine starts from, in this order, so a Kodi exit part way never
leaves a started file without a record or seed list behind it:
1. sync.db, created when missing;
2. on the first Start ever, the viewers to seed with Kodi's history (a later Start, or a
   viewer added later, is never seeded);
3. the sync_enabled setting turned on;
4. the started file, for the current pairing, with a new start_id, not paused, and the
   existing-ratings choice;
5. sync_request bumped.
A sync.db that can't be opened (damaged, or another add-on version's) is set aside as
sync.db.bad before step 1. Start never changes a viewer's sync id and sends nothing to
CrossWatch itself.

When a playlist can't be read there is no Start: ownership decided without it would be wrong.

The status screen reads only sync_status.json, which the engine keeps, so it opens without a
library read. Its choices (assign a shared change, send existing ratings, the answer to a mass
rating change) go to the engine as requests in sync_requests.json; it reopens after each one,
showing the engine's state as of then.

Log events: sync.setup.started, sync.setup.unreadable (info); sync.setup.library_unreadable,
sync.setup.not_saved, sync.setup.record_set_aside (warning).
"""
from __future__ import annotations

import os
import time
import uuid
from collections.abc import Callable, Sequence
from typing import Any

from resources.lib import log as logmod
from resources.lib import paths
from resources.lib.config import KEY_SYNC_ENABLED, KEY_SYNC_REQUEST, Settings, read_settings
from resources.lib.kodi import KodiApi, KodiRuntime
from resources.lib.log import get_logger
from resources.lib.models import Viewer
from resources.lib.playlist_index import IndexBuilder, PlaylistIndex
from resources.lib.storage import JsonViewerStore, PromptMemory
from resources.lib.sync.clock import kodi_to_utc, parse_utc
from resources.lib.sync.counts import Counts, count_owners, pair
from resources.lib.sync.files import (
    Request,
    RequestKind,
    StartedFile,
    StatusFile,
    append_request,
    new_start_id,
    read_requests,
    read_started,
    read_status,
    write_started,
)
from resources.lib.sync.ids import ensure_sync_ids
from resources.lib.sync.items import ItemKind, Library, read_library
from resources.lib.sync.library_id import library_id, profile_has_own_database
from resources.lib.sync.ownership import IndexSnapshot, owners_of
from resources.lib.sync.record import RecordMissing, RecordStore
from resources.lib.sync.reply import connection_id
from resources.lib.sync.server_maps import read_server_rows
from resources.lib.ui.list_window import ListRequest, ListRow, ListState
from resources.lib.ui.sync_setup import SetupRequest
from resources.lib.ui.sync_status import SEND_RATINGS, StatusRequest, StatusRow, Tone
from resources.lib.ui.who_watched import WhoWatchedRequest

_log = get_logger("sync")

TRAKT_ADDON = "script.trakt"

HEADING, HEADING_AGAIN = 30169, 30170
INTRO, INTRO_AGAIN = 30171, 30172
HISTORY_NOTE = 30173
SHARED, NO_OWNER, LEFT_ALONE = 30174, 30175, 30176
SHOWS, FILMS = 30177, 30178
RATINGS_TICK = 30179
DEVICE_ID_NOTE = 30180
TRAKT_WARNING = 30181
HTTP_WARNING = 30182
UNREADABLE, UNREADABLE_WHY = 30183, 30184
NOT_PAIRED = 30186
NO_LIBRARY = 30187
STARTED = 30188
NO_VIEWERS = 30189
NOT_SAVED = 30190


def _amounts(localised: Callable[[int], str], shows: int, films: int) -> str:
    parts = []
    if shows:
        parts.append(localised(SHOWS).format(count=shows))
    if films:
        parts.append(localised(FILMS).format(count=films))
    return " · ".join(parts) or "0"


def setup_request(
    localised: Callable[[int], str],
    viewers: Sequence[Viewer],
    counts: Counts,
    *,
    again: bool,
    trakt: bool,
    insecure: bool,
    unreadable: Sequence[str],
) -> SetupRequest:
    lines = [
        f"{v.name}: {_amounts(localised, len(counts.shows.get(v.sync_id, ())), counts.films.get(v.sync_id, 0))}"
        for v in viewers
        if v.sync_id
    ]
    lines.append(f"{localised(SHARED)}: {_amounts(localised, len(counts.shared_shows), counts.shared_films)}")
    unowned = _amounts(localised, len(counts.unowned_shows), counts.unowned_films)
    lines.append(f"{localised(NO_OWNER)}: {unowned} {localised(LEFT_ALONE)}")
    heading = localised(HEADING_AGAIN if again else HEADING)
    if unreadable:
        why = localised(UNREADABLE).format(names=", ".join(unreadable))
        return SetupRequest(
            heading=heading,
            intro=f"{why}\n{localised(UNREADABLE_WHY)}",
            counts=(),
            note="",
            warnings=(),
            ratings_label="",
            can_start=False,
        )
    warnings = [localised(DEVICE_ID_NOTE)]
    if trakt:
        warnings.append(localised(TRAKT_WARNING))
    if insecure:
        warnings.append(localised(HTTP_WARNING))
    return SetupRequest(
        heading=heading,
        intro=localised(INTRO_AGAIN if again else INTRO),
        counts=tuple(lines),
        note="" if again else localised(HISTORY_NOTE),
        warnings=tuple(warnings),
        ratings_label=localised(RATINGS_TICK),
    )


def start(
    kodi: KodiApi,
    settings: Settings,
    viewers: Sequence[Viewer],
    *,
    db_path: str,
    started_path: str,
    existing_ratings: bool,
    now_utc: str,
) -> bool:
    """Start, in the order the module docstring gives. False when the record or the started
    file couldn't be written: then sync_request is not bumped, so the service starts nothing."""
    store = RecordStore(db_path, busy_timeout=10.0)
    try:
        store.open(create=True)
    except RecordMissing:
        # Damaged, or written by another version of the add-on: kept as sync.db.bad, never
        # deleted, and replaced by a new record. Each viewer then starts over at CrossWatch.
        _set_aside(db_path)
        store.open(create=True)
    try:
        # Kept by the record once set, so only the first Start ever writes it.
        store.set_seed_viewers([v.sync_id for v in viewers if v.sync_id], now_utc)
    finally:
        store.close()
    kodi.set_setting(KEY_SYNC_ENABLED, "true")
    written = write_started(
        started_path,
        StartedFile(
            connection=connection_id(settings.webhook_base_url),
            start_id=new_start_id(),
            existing_ratings=existing_ratings,
        ),
    )
    if not written:
        return False
    kodi.set_setting(KEY_SYNC_REQUEST, str(settings.sync_request + 1))
    _log.info("sync.setup.started", viewers=len(viewers), existing_ratings=existing_ratings)
    return True


def _set_aside(db_path: str) -> None:
    for suffix in ("", "-wal", "-shm"):
        if os.path.exists(db_path + suffix):
            os.replace(db_path + suffix, f"{db_path}.bad{suffix}")
    _log.warning("sync.setup.record_set_aside")


def started_before(db_path: str, started_path: str, settings: Settings) -> bool:
    """Whether Start ran before for this record or this pairing: then nothing is seeded."""
    started = read_started(started_path)
    if started is not None and started.connection == connection_id(settings.webhook_base_url):
        return True
    if not os.path.exists(db_path):
        return False
    store = RecordStore(db_path)
    try:
        store.open()
    except Exception:
        return False
    try:
        return bool(store.seed_viewers() or store.seed_started_at())
    finally:
        store.close()


def _trakt_installed(kodi: KodiApi) -> bool:
    try:
        details = kodi.jsonrpc("Addons.GetAddonDetails", {"addonid": TRAKT_ADDON, "properties": ["enabled"]})
    except Exception:
        return False
    addon = details.get("addon")
    return isinstance(addon, dict) and addon.get("enabled") is not False


def run(kodi: KodiApi, now_utc: Callable[[], str], clock: Callable[[], float]) -> None:
    """The settings action: count, ask, and on Start write what the engine starts from."""
    settings = read_settings(kodi)
    if not settings.webhook_base_url or not settings.webhook_token:
        kodi.ok(kodi.localised(HEADING), kodi.localised(NOT_PAIRED))
        return
    store = JsonViewerStore(paths.viewers_path(kodi))
    viewers = ensure_sync_ids(store)
    if not viewers:
        # Nothing would be owned, and the first Start's seed list would be empty for good.
        kodi.ok(kodi.localised(HEADING), kodi.localised(NO_VIEWERS))
        return
    kodi.busy(True)
    try:
        maps = read_server_rows(kodi)
        library = None if maps.unreadable else _read_library(kodi, maps.rows)
        builder = IndexBuilder(kodi, viewers, clock)
        while not builder.step():
            pass
        index = builder.result()
    finally:
        kodi.busy(False)
    if maps.unreadable:
        kodi.ok(kodi.localised(HEADING), kodi.localised(SERVER_MAP_UNREADABLE))
        return
    if library is None:
        kodi.ok(kodi.localised(HEADING), kodi.localised(NO_LIBRARY))
        return
    unreadable = _unreadable(index)
    if unreadable:
        _log.info("sync.setup.unreadable", count=len(unreadable))
    snapshot = IndexSnapshot(index=index, built_at=clock(), invalidated_at=0.0, viewers=tuple(viewers))
    owners = owners_of(
        snapshot,
        library.tvshows,
        PromptMemory(paths.prompts_path(kodi)).entries(),
        _profile(kodi),
        profile_has_own_database(kodi),
    )
    db_path, started_path = paths.sync_db_path(kodi), paths.sync_started_path(kodi)
    request = setup_request(
        kodi.localised,
        viewers,
        count_owners(library, owners),
        again=started_before(db_path, started_path, settings),
        trakt=_trakt_installed(kodi),
        insecure=settings.webhook_base_url.lower().startswith("http://"),
        unreadable=unreadable,
    )
    result = kodi.sync_setup_window(request)
    if result is None or not result.start:
        return
    try:
        started = start(kodi, settings, viewers, db_path=db_path, started_path=started_path,
                        existing_ratings=result.existing_ratings, now_utc=now_utc())  # fmt: skip
    except Exception as exc:
        # A busy or unusable sync.db; the order in start() leaves nothing half-started.
        _log.warning("sync.setup.not_saved", error_type=type(exc).__name__)
        started = False
    if not started:
        kodi.ok(kodi.localised(HEADING), kodi.localised(NOT_SAVED))
        return
    kodi.notify(kodi.localised(HEADING), kodi.localised(STARTED))


def _read_library(kodi: KodiApi, server_rows: frozenset[tuple[ItemKind, int]]) -> Library | None:
    """The whole library, or None when Kodi couldn't give it in one consistent read (a scan
    changed it underneath, or JSON-RPC failed): counts from part of it would mislead."""
    try:
        library = read_library(kodi, library_id(kodi), may_continue=lambda: True, previous_shows={}, to_utc=kodi_to_utc,
                               server_rows=server_rows)  # fmt: skip
    except Exception as exc:
        _log.warning("sync.setup.library_unreadable", error_type=type(exc).__name__)
        return None
    if library is None or not library.complete:
        return None
    return library


def _unreadable(index: PlaylistIndex | None) -> tuple[str, ...]:
    """The playlists that couldn't be read. A finished build always has an index; without
    one, ownership is unknown and no Start is offered."""
    if index is None:
        return ("?",)
    return tuple(sorted(index.unreadable))


def _profile(kodi: KodiApi) -> str:
    try:
        return str(kodi.jsonrpc("Profiles.GetCurrentProfile").get("label") or "").strip()
    except Exception:
        return ""


def main() -> None:
    """The settings action's entry point, in its own interpreter as every settings script."""
    kodi = KodiRuntime()
    settings = read_settings(kodi)
    logmod.configure(log_dir=paths.log_dir(kodi), debug=settings.debug_logging, sink=kodi.log)
    logmod.set_secret(settings.webhook_token)
    run(kodi, lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), time.monotonic)


# -- the status screen -------------------------------------------------------------------

STATUS_HEADING = 30191
STATE_SETTLED, STATE_SYNCING = 30192, 30193
WAIT_PLAYBACK, WAIT_SCAN, WAIT_INDEX, WAIT_CROSSWATCH = 30194, 30195, 30196, 30197
STATE_OFF = 30198
STOP_RECORD, STOP_TOKEN, STOP_NO_SYNC, STOP_PAUSED, STOP_DEVICE_ID = 30199, 30200, 30201, 30202, 30203
LAST_UPLOAD = 30204
NEVER, JUST_NOW, MINUTES_AGO, HOURS_AGO, DAYS_AGO = 30205, 30206, 30207, 30208, 30209
NEEDS_YOU, NOTHING_NEEDS_YOU = 30210, 30211
ASSIGN_WATCHED, ASSIGN_RATED = 30212, 30213
UNOWNED_ROW = 30214
MASS_RATINGS = 30215
OTHER_SYNC_DEVICE, NO_DEVICE_ID = 30216, 30217
PLAYLISTS_UNREADABLE = 30218
VIEWER_UNKNOWN, VIEWER_TOO_LARGE, VIEWER_REFUSED, VIEWER_BUSY, VIEWER_LATE_SEED = 30219, 30220, 30221, 30222, 30223
MARKS_DROPPED = 30224
ADDRESS_CHANGED = 30225
OTHER_DEVICES_NOTE = 30226
SEND_RATINGS_LABEL, RATINGS_REQUESTED = 30227, 30228
MASS_QUESTION, MASS_SEND, MASS_DONT_SEND = 30229, 30230, 30231
UNOWNED_HEADING, TITLES_ONE, TITLES_ALL = 30232, 30233, 30234
REMOVED_VIEWER = 30235
MASS_ROW_ASK = 30236
VIEWER_PROBLEM = 30237
ASSIGN_WATCHED_HERE, ASSIGN_RATED_HERE, ASSIGN_RATING_QUESTION = 30238, 30239, 30240
STOP_OTHER_DEVICE = 30241
WAIT_NO_VIEWERS = 30242
WAIT_SERVER_MAP = 30243
SERVER_MAP_UNREADABLE = 30244

_STOPPED = {
    "record_missing": STOP_RECORD,
    "unauthorized": STOP_TOKEN,
    "no_sync": STOP_NO_SYNC,
    "paused": STOP_PAUSED,
    "device_id_changed": STOP_DEVICE_ID,
    "not_sync_device": STOP_OTHER_DEVICE,
}
_WAITING = {
    "playback": WAIT_PLAYBACK,
    "scan": WAIT_SCAN,
    "index": WAIT_INDEX,
    "crosswatch": WAIT_CROSSWATCH,
    "no_viewers": WAIT_NO_VIEWERS,
    "server_map": WAIT_SERVER_MAP,
}
_VIEWER_PROBLEMS = {
    "viewer_unknown": VIEWER_UNKNOWN,
    "too_large": VIEWER_TOO_LARGE,
    "library_too_large": VIEWER_TOO_LARGE,
    "rejected": VIEWER_REFUSED,
    "refused": VIEWER_REFUSED,
    "busy": VIEWER_BUSY,
    "late_seed": VIEWER_LATE_SEED,
}


def _ago(localised: Callable[[int], str], then: str, now: str) -> str:
    now_at, then_at = parse_utc(now), parse_utc(then)
    if now_at is None or then_at is None:
        return localised(NEVER)
    seconds = (now_at - then_at).total_seconds()
    if seconds < 60:
        return localised(JUST_NOW)
    if seconds < 3600:
        return localised(MINUTES_AGO).format(count=int(seconds // 60))
    if seconds < 86400:
        return localised(HOURS_AGO).format(count=int(seconds // 3600))
    return localised(DAYS_AGO).format(count=int(seconds // 86400))


def _state_line(localised: Callable[[int], str], status: StatusFile) -> tuple[str, Tone]:
    if status.state == "settled":
        return localised(STATE_SETTLED), "good"
    if status.state == "syncing":
        return localised(STATE_SYNCING), "busy"
    if status.state == "waiting":
        return localised(_WAITING.get(status.reason, WAIT_CROSSWATCH)), "busy"
    if status.state == "stopped":
        return localised(_STOPPED.get(status.reason, STOP_NO_SYNC)), "stopped"
    return localised(STATE_OFF), "busy"


def status_request(
    localised: Callable[[int], str],
    status: StatusFile | None,
    viewers: Sequence[Viewer],
    *,
    now_utc: str,
    insecure: bool,
    address_changed: bool,
    answered: frozenset[str] = frozenset(),
) -> StatusRequest:
    """answered: the rows whose answer is waiting in the requests file, left off so the screen
    reopened after an answer doesn't ask again before the engine has taken it."""
    status = status or StatusFile()
    names = {v.sync_id: v.name for v in viewers if v.sync_id}
    state, tone = _state_line(localised, status)
    off = status.state == "off"
    summary = ""
    if not off:
        when = _ago(localised, status.last_upload, now_utc) if status.last_upload else localised(NEVER)
        summary = localised(LAST_UPLOAD).format(when=when, count=status.waiting_changes)
    counts: list[str] = []
    if status.counts:
        owned = status.counts.get("viewers")
        owned = owned if isinstance(owned, dict) else {}
        for v in viewers:
            if v.sync_id:
                counts.append(f"{v.name}: {_amounts(localised, *pair(owned.get(v.sync_id)))}")
        counts.append(f"{localised(SHARED)}: {_amounts(localised, *pair(status.counts.get('shared')))}")
        counts.append(f"{localised(NO_OWNER)}: {_amounts(localised, *pair(status.counts.get('unowned')))}")
    problems: list[str] = []
    if address_changed:
        problems.append(localised(ADDRESS_CHANGED))
    if status.reason in ("library_has_sync_device", "not_sync_device"):
        problems.append(localised(OTHER_SYNC_DEVICE))
    elif status.reason == "device_id_missing":
        problems.append(localised(NO_DEVICE_ID))
    if status.unreadable_playlists:
        problems.append(localised(PLAYLISTS_UNREADABLE).format(names=", ".join(status.unreadable_playlists)))
    for sync_id, problem in sorted(status.per_viewer.items()):
        name = names.get(sync_id) or localised(REMOVED_VIEWER)
        string_id = _VIEWER_PROBLEMS.get(problem)
        if string_id is not None:
            problems.append(localised(string_id).format(name=name))
        else:
            problems.append(localised(VIEWER_PROBLEM).format(name=name, error=problem))
    if status.dropped_marks:
        problems.append(localised(MARKS_DROPPED).format(count=status.dropped_marks))
    if insecure:
        problems.append(localised(HTTP_WARNING))
    rows = [StatusRow(key=f"problem:{i}", text=text, problem=True) for i, text in enumerate(problems)]
    if status.mass_ratings and "mass" not in answered:
        text = f"{localised(MASS_RATINGS).format(count=status.mass_ratings)}. {localised(MASS_ROW_ASK)}"
        rows.append(StatusRow(key="mass", text=text))
    for a in status.assignments:
        if isinstance(a, dict) and isinstance(a.get("id"), str) and f"assign:{a['id']}" not in answered:
            string_id = ASSIGN_RATED if a.get("group") == "ratings" else ASSIGN_WATCHED
            rows.append(
                StatusRow(key=f"assign:{a['id']}", text=localised(string_id).format(title=a.get("title") or "?"))
            )
    unowned = sum(pair(status.counts.get("unowned"))) if status.counts else 0
    if unowned and status.unowned_titles:
        rows.append(StatusRow(key="unowned", text=localised(UNOWNED_ROW).format(count=unowned)))
    return StatusRequest(
        heading=localised(STATUS_HEADING),
        state=state,
        tone=tone,
        summary=summary,
        counts=tuple(counts),
        # Off: nothing below the state line means anything yet.
        needs_you="" if off else localised(NEEDS_YOU),
        rows=tuple(rows),
        empty="" if off else localised(NOTHING_NEEDS_YOU),
        note="" if off else localised(OTHER_DEVICES_NOTE),
        send_ratings="" if off else localised(SEND_RATINGS_LABEL),
    )


def _ask(kodi: KodiApi, settings_path: str, request: Request) -> bool:
    """Leave a request for the engine and bump sync_request so the service hears of it."""
    if not append_request(settings_path, request):
        kodi.ok(kodi.localised(STATUS_HEADING), kodi.localised(NOT_SAVED))
        return False
    settings = read_settings(kodi)
    kodi.set_setting(KEY_SYNC_REQUEST, str(settings.sync_request + 1))
    return True


def _new_request(kind: RequestKind, **args: Any) -> Request:
    return Request(id=uuid.uuid4().hex, kind=kind, args=dict(args))


def run_status(kodi: KodiApi, now_utc: Callable[[], str]) -> None:
    """The settings action: show the status, and run whatever the household picks from it,
    reopening the status after each step."""
    requests_path = paths.sync_requests_path(kodi)
    while True:
        settings = read_settings(kodi)
        viewers = JsonViewerStore(paths.viewers_path(kodi)).viewers()
        status = read_status(paths.sync_status_path(kodi))
        started = read_started(paths.sync_started_path(kodi))
        changed = started is not None and started.connection != connection_id(settings.webhook_base_url)
        request = status_request(
            kodi.localised,
            status,
            viewers,
            now_utc=now_utc(),
            insecure=settings.webhook_base_url.lower().startswith("http://"),
            address_changed=changed,
            answered=_answered(read_requests(requests_path)),
        )
        chosen = kodi.sync_status_window(request)
        if not chosen:
            return
        heading = kodi.localised(STATUS_HEADING)
        if chosen == SEND_RATINGS:
            if _ask(kodi, requests_path, _new_request("send_existing_ratings")):
                kodi.notify(heading, kodi.localised(RATINGS_REQUESTED))
        elif chosen.startswith("problem:"):
            row = next((r for r in request.rows if r.key == chosen), None)
            if row is not None:
                kodi.ok(heading, row.text)
        elif chosen == "mass" and status is not None and status.mass_ratings:
            answer = kodi.choice_window(
                kodi.localised(MASS_RATINGS).format(count=status.mass_ratings),
                kodi.localised(MASS_QUESTION),
                kodi.localised(MASS_SEND),
                kodi.localised(MASS_DONT_SEND),
            )
            if answer is not None:
                _ask(kodi, requests_path, _new_request("mass_ratings_send" if answer else "mass_ratings_drop"))
        elif chosen.startswith("assign:") and status is not None:
            _assign(kodi, requests_path, chosen[len("assign:") :], status, viewers)
        elif chosen == "unowned" and status is not None:
            _show_unowned(kodi, status.unowned_titles)


def _answered(requests: Sequence[Request]) -> frozenset[str]:
    keys = set()
    for r in requests:
        if r.kind == "assign":
            keys.add(f"assign:{r.args.get('assignment')}")
        elif r.kind in ("mass_ratings_send", "mass_ratings_drop"):
            keys.add("mass")
    return frozenset(keys)


def _assign(kodi: KodiApi, requests_path: str, assignment: str, status: StatusFile, viewers: Sequence[Viewer]) -> None:
    listed = next((a for a in status.assignments if isinstance(a, dict) and a.get("id") == assignment), None)
    named = [v for v in viewers if v.sync_id]
    if listed is None or not named:
        return
    rated = listed.get("group") == "ratings"
    ticked = kodi.who_watched(
        WhoWatchedRequest(
            title=str(listed.get("title") or "?"),
            subtitle=kodi.localised(ASSIGN_RATED_HERE if rated else ASSIGN_WATCHED_HERE),
            poster="",
            names=tuple(v.name for v in named),
            question=kodi.localised(ASSIGN_RATING_QUESTION) if rated else "",
        )
    )
    if not ticked:
        # Skip, Back, or Done with nobody ticked: the change stays on the list.
        return
    ids = [v.sync_id for v in named if v.name in ticked]
    _ask(kodi, requests_path, _new_request("assign", assignment=assignment, viewers=ids))


def _show_unowned(kodi: KodiApi, titles: Sequence[str]) -> None:
    request = ListRequest(
        heading=kodi.localised(UNOWNED_HEADING),
        rows=tuple(ListRow(key=str(i), title=t) for i, t in enumerate(titles)),
        count_one=kodi.localised(TITLES_ONE),
        count_all=kodi.localised(TITLES_ALL),
        read_only=True,
    )
    kodi.list_window(request, ListState())


def status_main() -> None:
    """The status action's entry point."""
    kodi = KodiRuntime()
    settings = read_settings(kodi)
    logmod.configure(log_dir=paths.log_dir(kodi), debug=settings.debug_logging, sink=kodi.log)
    logmod.set_secret(settings.webhook_token)
    run_status(kodi, lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
