"""Update now on a TV show or a season: refresh the show record (for a show),
the season posters and every episode under it, with a progress window that
can be stopped or sent to Kodi's background progress bar.

Logging:
    Logger: 'refresh'
    Key events:
        - refresh.not_included (INFO): Update now outside the included
          libraries; nothing changed
        - refresh.skip_excluded (INFO): episodes in a subfolder that is not
          included were left out of a refresh
"""
from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import xbmc
import xbmcgui

from resources.lib.data.kodi import (
    get_all_items,
    get_episode_show_id,
    get_item_by_id,
    get_season_info,
    get_seasons_for_scan,
)
from resources.lib.data.libraries import Library, LibraryConfig, load_libraries
from resources.lib.data.media_types import EPISODE, SEASON, TVSHOW, MediaType
from resources.lib.data.tracker import TrackerDB
from resources.lib.engine.breaker import CircuitBreaker
from resources.lib.engine.scan import manages_art, run_scan, scans_seasons
from resources.lib.service import attention
from resources.lib.service.daemon import (
    _get_db_path,
    _get_sources_config_path,
    _load_settings,
    _prepare_imdb_ratings,
    fanart_auth_failed,
    fanart_auth_string,
    tvdb_auth_failed,
)
from resources.lib.service.lock import (
    _home_window,
    acquire_scan_lock,
    release_scan_lock,
)
from resources.lib.ui.progress_window import show_progress_window
from resources.lib.utils import (
    ApiKeyError,
    StructuredLogger,
    display_path,
    get_logger,
    lang,
    notify,
)

log = get_logger('refresh')


@dataclass(frozen=True)
class Scope:
    """What one refresh covers: a whole show (season None) or one season.
    ``file`` is the show's folder, which places it in a library."""
    tvshowid: int
    season: int | None
    title: str
    file: str = ""


def resolve_scope(dbtype: str, dbid: int) -> Scope | None:
    """The refresh scope of a clicked show or season, or None for anything
    else or an item Kodi no longer has."""
    if dbtype == "tvshow":
        tvshowid, season = dbid, None
    elif dbtype == "season":
        info = get_season_info(dbid)
        if info is None:
            return None
        tvshowid, season = info
    else:
        return None
    show = get_item_by_id(TVSHOW, tvshowid)
    if show is None:
        return None
    return Scope(tvshowid, season, str(show.get("title") or tvshowid),
                 str(show.get("file") or ""))


def included_library(file_path: str) -> Library | None:
    """The included library Update now may work in for this file; None,
    after telling the user, when the file's library or subfolder is not
    included or the file is in no library."""
    libraries = load_libraries(_get_sources_config_path()) or LibraryConfig()
    lib = libraries.included_for(file_path)
    if lib is None:
        log.info("Update now outside the included libraries", event="refresh.not_included",
                 file_path=display_path(file_path))
        notify(lang(32650))  # This library isn't included in MetaMender
    return lib


def show_id_of(dbtype: str, dbid: int) -> int | None:
    """The show a clicked show, season or episode belongs to; None for a
    movie or anything Kodi cannot place."""
    if dbtype == "tvshow":
        return dbid
    if dbtype == "season":
        info = get_season_info(dbid)
        return info[0] if info else None
    if dbtype == "episode":
        return get_episode_show_id(dbid)
    return None


# Items done before the time left is shown: the first ones include the slow
# show record and warm-up, so an early estimate is mostly noise.
_ETA_MIN_DONE = 3


class RefreshProgress:
    """Counts and the current item of one refresh, shared between the worker
    thread that runs it and the main thread that shows it."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.total = 0
        self.done = 0
        self.updated = 0
        self.unchanged = 0
        self.unchecked = 0
        # The show's own record (a show refresh only): a step of its own,
        # not counted among the episodes.
        self.show_updated = False
        self.show_unchecked = False
        self.current = ""
        self._started = 0.0
        self._stop = False

    def begin(self, total: int, now: float) -> None:
        with self._lock:
            self.total, self._started = total, now

    def item_started(self, label: str) -> None:
        with self._lock:
            self.current = label

    def item_finished(
        self, before: dict[str, Any], after: dict[str, Any], counted: bool = True,
    ) -> None:
        """Count one item by what changed in the scan stats while it ran: an
        update wins over a field that could not be checked. The show's own
        record and its season posters (``counted`` False) are remembered
        apart from the episodes, together: any of them updated, else any of
        them unchecked."""
        def grew(key: str) -> bool:
            return int(after.get(key) or 0) > int(before.get(key) or 0)
        with self._lock:
            if not counted:
                self.show_updated = self.show_updated or grew("updated")
                self.show_unchecked = not self.show_updated and (
                    self.show_unchecked or grew("transient") or grew("unreachable"))
                return
            self.done += 1
            if grew("updated"):
                self.updated += 1
            elif grew("transient") or grew("unreachable"):
                self.unchecked += 1
            else:
                self.unchanged += 1

    def request_stop(self) -> None:
        with self._lock:
            self._stop = True

    @property
    def stop_requested(self) -> bool:
        with self._lock:
            return self._stop

    def seconds_left(self, now: float) -> int | None:
        with self._lock:
            if self.total <= 0 or self.done < _ETA_MIN_DONE:
                return None
            per_item = (now - self._started) / self.done
            return round(per_item * max(self.total - self.done, 0))

    def percent(self) -> int:
        with self._lock:
            return 0 if self.total <= 0 else min(100, self.done * 100 // self.total)

    def bar_text(self) -> str:
        with self._lock:
            return lang(32474).format(self.done, self.total)

    def toast(self, title: str, stopped: bool, could_not_finish: bool) -> str:
        with self._lock:
            if stopped:
                return lang(32483).format(self.done, self.total, title)
            if could_not_finish:
                return lang(32484).format(title)
            if self.updated:
                return lang(32482).format(title, self.updated, self.total)
            if self.show_updated:
                return lang(32350).format(title)
            if self.unchecked or self.show_unchecked:
                return lang(32353).format(title)
            return lang(32351).format(title)


@dataclass
class RefreshOutcome:
    """How a refresh ended: stopped by the user, cut short because every
    provider it needed was down, or interrupted by Kodi shutting down."""
    stopped: bool = False
    could_not_finish: bool = False
    aborted: bool = False
    # TheTVDB rejected the add-on's credentials during the refresh.
    tvdb_auth_failed: bool = False
    # fanart.tv rejected the key during the refresh.
    fanart_auth_failed: bool = False
    # TMDB answered at least once: the key works.
    tmdb_answered: bool = False


def _label(media_type: MediaType, item: dict[str, Any]) -> str:
    if media_type is TVSHOW:
        return lang(32472)
    if media_type is SEASON:
        # Kodi's own season title, so specials read "Specials" in Kodi's language.
        return lang(32718).format(item.get("title") or item.get("season", ""))
    return lang(32473).format(item.get("season", ""), item.get("episode", ""),
                              item.get("title", ""))


def _pass(
    media_type: MediaType,
    items: list[dict[str, Any]],
    progress: RefreshProgress,
    settings: dict[str, Any],
    libraries: LibraryConfig,
    tracker: TrackerDB,
    monitor: Any,
    breaker: CircuitBreaker,
    show_id_map: dict[int, str] | None = None,
    caches: tuple[dict[tuple[str, str], Any], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """One run_scan pass over ``items``, counting each finished item into
    ``progress``: an item is counted when the next one starts or the pass
    ends, by what it changed in the stats. Only episodes count towards the
    total; the show's own record and the season posters are reported
    apart."""
    pending: list[dict[str, Any]] = []
    counted = media_type is EPISODE

    def on_item(index: int, item: dict[str, Any], stats: dict[str, Any]) -> bool:
        if pending:
            progress.item_finished(pending.pop(), stats, counted)
        if progress.stop_requested:
            return False
        pending.append(dict(stats))
        progress.item_started(_label(media_type, item))
        return True

    stats = run_scan(
        media_type, tracker, libraries,
        settings["tmdb_api_key"], settings, monitor=monitor, items=items,
        reset=True, breaker=breaker, show_id_map=show_id_map, progress=on_item,
        fanart_cache=caches[0] if caches else None,
        show_cache=caches[1] if caches else None,
    )
    if pending:
        progress.item_finished(pending.pop(), stats, counted)
    return stats


def run_refresh(
    scope: Scope,
    progress: RefreshProgress,
    settings: dict[str, Any],
    libraries: LibraryConfig,
    tracker: TrackerDB,
    monitor: Any,
    prepare: Callable[[], bool] | None = None,
) -> RefreshOutcome:
    """Refresh a show (its record, its season posters, then every episode) or
    a season (its poster, then its episodes), as Update now does for one
    item. The season and episode passes build their show id maps after the
    show pass, so they use the ids that pass found. Only what lies in an
    included library and subfolder is refreshed.

    ``prepare`` readies the IMDb ratings store (its first use downloads the
    dataset, which takes a while) and answers ``settings["imdb_ready"]``;
    it runs after the episode count is known, so the window shows it, and a
    Stop pressed meanwhile ends the refresh before the first item."""
    listed = get_all_items(EPISODE, tvshowid=scope.tvshowid, season=scope.season,
                           art=manages_art(EPISODE, libraries))
    episodes = [e for e in listed if libraries.included_for(e.get("file", ""))]
    if len(episodes) < len(listed):
        log.info("Episodes outside the included libraries left out",
                 event="refresh.skip_excluded", tvshowid=scope.tvshowid,
                 skipped=len(listed) - len(episodes))
    show = get_item_by_id(TVSHOW, scope.tvshowid) if scope.season is None else None
    if show and not libraries.included_for(show.get("file", "")):
        show = None
    progress.begin(len(episodes), now=time.monotonic())
    log.info("Refresh starting", event="refresh.start", tvshowid=scope.tvshowid,
             season=scope.season, episodes=len(episodes))
    if prepare is not None:
        progress.item_started(lang(32486))  # Preparing IMDb ratings
        settings["imdb_ready"] = prepare()
        if progress.stop_requested:
            log.info("Refresh stopped before the first item", event="refresh.finish",
                     tvshowid=scope.tvshowid, season=scope.season, done=0,
                     total=progress.total, stopped=True)
            return RefreshOutcome(stopped=True)
        # Progress counts from the first item, not from the download.
        progress.begin(len(episodes), now=time.monotonic())
    breaker = CircuitBreaker()
    # Shared by the passes like the breaker: the show's fanart.tv answer and
    # TMDB record serve its season posters.
    caches: tuple[dict[tuple[str, str], Any], dict[str, Any]] = ({}, {})
    passes: list[dict[str, Any]] = []

    def halted() -> bool:
        return bool(passes and (passes[-1]["stopped"] or passes[-1]["aborted"]))

    if show:
        passes.append(_pass(TVSHOW, [show], progress, settings, libraries,
                            tracker, monitor, breaker, caches=caches))
    if scans_seasons(libraries) and not halted():
        show_id_map = tracker.get_show_id_map()
        seasons = [
            s for s in get_seasons_for_scan(show_id_map, tvshowid=scope.tvshowid,
                                            show_tvdb_map=tracker.get_show_tvdb_map())
            if (scope.season is None or s.get("season") == scope.season)
            and libraries.included_for(s.get("file", ""))
        ]
        if seasons:
            passes.append(_pass(SEASON, seasons, progress, settings, libraries,
                                tracker, monitor, breaker, show_id_map, caches))
    if episodes and not halted():
        passes.append(_pass(EPISODE, episodes, progress, settings, libraries,
                            tracker, monitor, breaker, tracker.get_show_id_map(), caches))
    shutdown = bool(monitor is not None and monitor.abortRequested())
    outcome = RefreshOutcome(
        stopped=any(s.get("stopped") for s in passes),
        could_not_finish=not shutdown and any(s.get("aborted") for s in passes),
        aborted=shutdown,
        tvdb_auth_failed=tvdb_auth_failed(passes),
        fanart_auth_failed=fanart_auth_failed(passes),
        tmdb_answered=any(s.get("tmdb_answered") for s in passes),
    )
    log.info("Refresh finished", event="refresh.finish", tvshowid=scope.tvshowid,
             season=scope.season, done=progress.done, total=progress.total,
             updated=progress.updated, unchecked=progress.unchecked,
             stopped=outcome.stopped, could_not_finish=outcome.could_not_finish,
             aborted=outcome.aborted)
    return outcome


# Home-window properties shared with a second Update now (its own process):
# the running refresh's show, and its request to show the window again.
_RUNNING_SHOW = "metamender_refresh_show"
_REOPEN = "metamender_refresh_reopen"
# Set once Stop was pressed: the refresh is finishing its item in progress.
_STOPPING = "metamender_refresh_stopping"
# How often the background bar is updated and the reopen request checked.
_POLL_SECONDS = 0.5


def refresh_running_show() -> int | None:
    value = _home_window().getProperty(_RUNNING_SHOW)
    return int(value) if value.isdigit() else None


def _refresh_stopping() -> bool:
    return _home_window().getProperty(_STOPPING) == "1"


def request_reopen() -> None:
    _home_window().setProperty(_REOPEN, "1")


def _take_reopen() -> bool:
    window = _home_window()
    if window.getProperty(_REOPEN):
        window.clearProperty(_REOPEN)
        return True
    return False


def bring_back_or_busy(clicked_show: int | None) -> str:
    """What a second Update now does while a scan holds the lock: "reopen"
    when it points into the running refresh's show, "stopping" when that
    refresh was stopped and only finishes its item in progress, else
    "busy"."""
    running = refresh_running_show()
    if running is not None and clicked_show == running:
        return "stopping" if _refresh_stopping() else "reopen"
    return "busy"


def drive_views(
    progress: RefreshProgress,
    done: threading.Event,
    bar_heading: str,
    show_window: Callable[[], str],
    make_bar: Callable[[], Any],
    take_reopen: Callable[[], bool],
    poll: float = _POLL_SECONDS,
) -> None:
    """Show the window, and after Background or Stop Kodi's background bar,
    until the refresh is done. A reopen request brings the window back;
    after Stop the bar only waits for the item in progress to finish."""
    while not done.is_set():
        choice = show_window()
        if choice == "stop":
            progress.request_stop()
        if done.is_set():
            return
        bar = make_bar()
        bar.create(bar_heading, progress.bar_text())
        try:
            while not done.wait(poll):
                bar.update(progress.percent(), bar_heading, progress.bar_text())
                if choice != "stop" and take_reopen():
                    break
        finally:
            bar.close()


def open_refresh(dbtype: str, dbid: int) -> None:
    """Update now on a show or season: run the refresh on a worker thread
    while this thread shows its progress, then report the result."""
    scope = resolve_scope(dbtype, dbid)
    if scope is None:
        notify(lang(32345))  # Item not found
        return
    lib = included_library(scope.file)
    if lib is None:
        return
    if not acquire_scan_lock():
        answer = bring_back_or_busy(scope.tvshowid)
        if answer == "reopen":
            request_reopen()
        elif answer == "stopping":
            notify(lang(32487))  # Stopping: the episode in progress finishes first
        else:
            notify(lang(32344))  # A scan is already running
        return
    home = _home_window()
    home.setProperty(_RUNNING_SHOW, str(scope.tvshowid))
    home.clearProperty(_REOPEN)
    home.clearProperty(_STOPPING)
    StructuredLogger.start_scan_log()
    try:
        settings = _load_settings()
        if not settings.get("tmdb_api_key"):
            notify(lang(32346))  # No TMDB API key configured
            return
        progress = RefreshProgress()
        done = threading.Event()
        result: dict[str, Any] = {}
        monitor = xbmc.Monitor()

        def work() -> None:
            # The tracker's SQLite connection belongs to the thread that
            # opens it, so the worker opens its own.
            tracker = None
            try:
                tracker = TrackerDB(_get_db_path())
                result["outcome"] = run_refresh(
                    scope, progress, settings, LibraryConfig([lib]), tracker, monitor,
                    prepare=lambda: _prepare_imdb_ratings([lib], monitor))
                if result["outcome"].tmdb_answered:
                    attention.update(
                        tracker, lambda a: a.clear(attention.KEY_REJECTED))
            except ApiKeyError:
                log.exception("Refresh stopped: invalid API key", event="refresh.apikey")
                result["error"] = 32341
                if tracker is not None:
                    attention.update(
                        tracker, lambda a: a.raise_problem(attention.KEY_REJECTED))
            except Exception:
                log.exception("Refresh failed", event="refresh.error")
                result["error"] = 32347
            finally:
                if tracker is not None:
                    tracker.close()
                done.set()

        worker = threading.Thread(target=work, name="metamender-refresh")
        worker.start()
        heading = (lang(32470).format(scope.title) if scope.season is None
                   else lang(32471).format(scope.title, scope.season))
        def window() -> str:
            choice = show_progress_window(progress, heading, done)
            if choice == "stop":
                home.setProperty(_STOPPING, "1")
            return choice

        try:
            drive_views(progress, done, lang(32485).format(scope.title),
                        window, xbmcgui.DialogProgressBG, _take_reopen)
        except Exception:
            # Without its window the refresh cannot be followed or stopped,
            # so it stops; it must also end before the lock is released.
            log.exception("Refresh window failed", event="refresh.view_error")
            result.setdefault("error", 32347)
        finally:
            if not done.is_set():
                progress.request_stop()
            worker.join()
        if "error" in result:
            # A failure while Kodi shuts down is the shutdown, not news.
            if not monitor.abortRequested():
                notify(lang(result["error"]))
        else:
            outcome: RefreshOutcome = result["outcome"]
            if not outcome.aborted:
                notify(progress.toast(scope.title, outcome.stopped, outcome.could_not_finish))
                if outcome.tvdb_auth_failed:
                    notify(lang(32352))  # TheTVDB rejected the credentials
                if outcome.fanart_auth_failed:
                    notify(lang(fanart_auth_string(
                        bool(settings.get("fanart_client_key")))))
    finally:
        home.clearProperty(_RUNNING_SHOW)
        home.clearProperty(_REOPEN)
        home.clearProperty(_STOPPING)
        StructuredLogger.stop_scan_log()
        release_scan_lock()
