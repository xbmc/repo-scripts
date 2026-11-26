"""
Background service daemon for MetaMender.

Runs as a Kodi service, periodically scanning the library for
metadata gaps and backfilling from TMDB, TheTVDB and the IMDb ratings store.

Logging:
    Logger: 'service'
    Key events:
        - service.start (INFO): Service started
        - service.stop (INFO): Service stopped
        - service.scan_trigger (INFO): Scan triggered (scheduled or library event)
        - service.scan_complete (INFO): Scan finished with summary
        - service.scan_error (ERROR): Scan failed
        - service.scan_apikey (ERROR): A provider rejected the API key; the
          scan stops and backs off
        - service.skip_playback (DEBUG): Scan skipped because video is playing
        - service.library_scan_finished (INFO): Library scan event received
        - service.orphans_pruned (INFO/DEBUG): Orphan prune result (INFO when >0)
        - service.prune_skip (DEBUG): Prune skipped (targeted scan or disabled)
        - service.imdb_prepare_failed (ERROR): Preparing the IMDb ratings store
          raised; IMDb ratings are transient for the cycle
        - libraries.damaged (ERROR): sources.json is not a readable v2 file;
          the cycle is skipped and the file left alone
        - service.libraries_converted (INFO): 1.1 settings became libraries
        - service.convert_skipped (INFO): the libraries were converted
          meanwhile (by the setup dialog or the service), nothing written
        - service.convert_deferred (INFO): conversion waits, Kodi listed no
          libraries or the query failed
        - service.convert_failed (ERROR): the converted libraries could not
          be saved; the old settings stay and conversion retries
        - service.libraries_added (INFO): libraries new to Kodi were added,
          not included
        - service.libraries_restarted (INFO): sources.json was gone after
          the conversion; the libraries were found again, none included
        - service.copy_failed (ERROR): the settings copy at service start
          raised; the conversion makes it later
"""
from __future__ import annotations

import os
import time
from collections.abc import Iterable
from datetime import date, timedelta
from functools import partial
from typing import Any, Optional

import xbmc
import xbmcvfs

from resources.lib.constants import (
    BACKFILL_DB_FILENAME,
    DEFAULT_ADDON_ID,
    DEFAULT_SCAN_INTERVAL_HOURS,
    LIBRARY_SCAN_DEBOUNCE_SEC,
    SCAN_FAILURE_BACKOFF_SEC,
    SCAN_LOCKED_RETRY_SEC,
    SERVICE_SLEEP_INTERVAL_SEC,
    SOURCES_CONFIG_FILENAME,
)
from resources.lib.data.libraries import (
    FILE_DAMAGED,
    FILE_LEGACY,
    FILE_MISSING,
    FILE_OK,
    Library,
    LibraryConfig,
    add_new_libraries,
    read_libraries,
    save_libraries,
)
from resources.lib.data.media_types import EPISODE, MOVIE, SEASON, SET, TVSHOW
from resources.lib.data.sources import (
    discover_folders,
    kodi_ui_language,
    library_folders_in_use,
    load_source_config,
)
from resources.lib.data.tracker import TrackerDB
from resources.lib.data.upgrade import (
    COPY_FILE_NAME,
    MOVED_IDS,
    convert,
    ensure_copy,
    read_user_settings,
)
from resources.lib.engine.breaker import CircuitBreaker
from resources.lib.engine.certchain import SiteGate
from resources.lib.engine.resolve import rating_sources
from resources.lib.engine.scan import run_scan, scans_seasons, scans_sets
from resources.lib.providers import imdb_ratings
from resources.lib.service import attention
from resources.lib.service.lock import (
    acquire_scan_lock,
    clear_file_lock,
    release_scan_lock,
)
from resources.lib.service.stopscan import (
    clear_stop,
    mark_stopped,
    stop_requested,
    user_stopped,
)
from resources.lib.ui.attention_window import show_attention_window
from resources.lib.utils import (
    ApiKeyError,
    KodiQueryError,
    StructuredLogger,
    display_path,
    get_addon,
    get_bool_setting,
    get_float_setting,
    get_int_setting,
    get_logger,
    get_setting,
    is_setup_complete,
    lang,
    notify,
    set_bool_setting,
)

log = get_logger('service')


class MetaMendMonitor(xbmc.Monitor):
    """Monitor subclass that tracks library scan/clean events."""

    def __init__(self) -> None:
        super().__init__()
        self._scan_requested: bool = False
        self._last_scan_event: float = 0.0

    def onScanFinished(self, library: str) -> None:
        if library == "video":
            self._scan_requested = True
            self._last_scan_event = time.time()
            log.info(
                "Library scan finished, metadata scan queued",
                event="service.library_scan_finished",
            )

    def onCleanFinished(self, library: str) -> None:
        if library == "video":
            self._scan_requested = True
            self._last_scan_event = time.time()
            log.info(
                "Library clean finished, metadata scan queued",
                event="service.library_clean_finished",
            )

    def has_pending_scan(self, debounce_sec: float) -> bool:
        """Check if a library-triggered scan is pending and debounce has elapsed."""
        if not self._scan_requested:
            return False
        return (time.time() - self._last_scan_event) >= debounce_sec

    def clear_scan_request(self) -> None:
        """Clear the pending scan flag after a scan runs."""
        self._scan_requested = False


# ---------------------------------------------------------------------------
# Settings helpers
# ---------------------------------------------------------------------------


def _load_settings() -> dict[str, Any]:
    """The general settings the scan engine and the service read, plus
    Kodi's interface language (read once here rather than per pass). What a
    library does comes from its own settings (_load_libraries)."""
    return {
        "tmdb_api_key": get_setting("tmdb_api_key"),
        "fanart_client_key": get_setting("fanart_client_key"),
        "stale_threshold_days": get_int_setting("stale_threshold_days", 365),
        "refetch_schedule": get_setting("refetch_schedule"),
        "rate_limit": get_float_setting("rate_limit", 0.25),
        "scan_interval": get_int_setting("scan_interval", DEFAULT_SCAN_INTERVAL_HOURS),
        "show_notifications": get_bool_setting("show_notifications"),
        "resume_interrupted": get_bool_setting("resume_interrupted"),
        "orphan_retention_days": get_int_setting("orphan_retention_days", 30),
        # Which certification websites may be asked; see scan._cert_config.
        "cert_sites": frozenset(
            site for site in ("fsk", "bbfc", "medieraadet")
            if get_bool_setting("enable_" + site)
        ),
        "ui_language": kodi_ui_language(),
    }


def _addon_data_file(name: str) -> str:
    addon_data = xbmcvfs.translatePath(
        "special://profile/addon_data/{}/".format(DEFAULT_ADDON_ID)
    )
    return os.path.join(addon_data, name)


def _get_db_path() -> str:
    """Build the absolute path to the backfill tracker database."""
    addon_data = xbmcvfs.translatePath(
        "special://profile/addon_data/{}/".format(DEFAULT_ADDON_ID)
    )
    if not xbmcvfs.exists(addon_data):
        xbmcvfs.mkdirs(addon_data)
    return os.path.join(addon_data, BACKFILL_DB_FILENAME)


def _get_sources_config_path() -> str:
    """Build the absolute path to the sources configuration file."""
    return _addon_data_file(SOURCES_CONFIG_FILENAME)


# Hidden setting: the 1.1 settings were converted to libraries once.
_CONVERTED = "libraries_converted"


def _libraries_converted() -> bool:
    return get_bool_setting(_CONVERTED)


def _copy_old_settings() -> None:
    """Save the 1.1 values aside at service start. Kodi drops ids that
    left resources/settings.xml whenever it next saves the add-on settings
    (the user opening them is enough), which can come long before the
    first scan cycle gets past playback, the key and the scan lock."""
    if not is_setup_complete() or _libraries_converted():
        return
    if read_libraries(_get_sources_config_path())[1] not in (FILE_MISSING, FILE_LEGACY):
        return
    ensure_copy(_addon_data_file("settings.xml"), _addon_data_file(COPY_FILE_NAME))


def _converted_meanwhile(path: str) -> tuple[bool, Optional[LibraryConfig]]:
    """(True, its config) when path is no longer a file to convert: version
    2 was written, or it is damaged (config None; never converted over).
    (False, None) while it is still missing or in the 1.1 shape."""
    config, state = read_libraries(path)
    if state in (FILE_MISSING, FILE_LEGACY):
        return False, None
    log.info("Libraries already converted, conversion skipped",
             event="service.convert_skipped", path=path, state=state)
    return True, config


def _remove_copy(copy_path: str) -> None:
    try:
        os.remove(copy_path)
    except FileNotFoundError:
        pass
    except OSError:
        log.exception("Settings copy could not be deleted", event="service.convert_failed",
                      path=copy_path)


def _convert_libraries(tracker: TrackerDB, path: str) -> Optional[LibraryConfig]:
    """Turn the 1.1 settings into libraries, once. The moved settings are
    read from a copy of their own, which is deleted only after the new
    file is written, so a failure at any step converts again next time.
    None when the conversion waits or failed.

    The service and the setup dialog (a separate process) can both
    convert. The file is checked again before the copy is made and before
    the result is saved: once the other one has written version 2, its
    result stands, and the copy, which it may already have deleted, goes."""
    copy_path = _addon_data_file(COPY_FILE_NAME)
    user_path = _addon_data_file("settings.xml")
    done, existing = _converted_meanwhile(path)
    if done:
        return existing
    legacy = ensure_copy(user_path, copy_path)
    if legacy is None and any(key in read_user_settings(user_path) for key in MOVED_IDS):
        # The copy could not be written (ensure_copy logged it); the old
        # settings stay where they are until it can.
        return None
    # legacy None from here: Kodi writes every setting, defaults included,
    # so no moved id at all means Kodi dropped them before a copy was
    # made. convert then switches nothing on rather than guess.
    discovered = discover_folders()
    if not discovered:
        # A failed query, or Kodi listed no sources and the library no
        # folders (a shared database without sources): converting now
        # would lose every per-folder language.
        log.info("Library conversion deferred, no libraries found",
                 event="service.convert_deferred")
        return None
    # The 1.1 sources.json, or an empty one when there is none.
    old_sources = load_source_config(path)
    config = convert(legacy, old_sources, discovered, kodi_ui_language())
    done, existing = _converted_meanwhile(path)
    if done:
        _remove_copy(copy_path)
        return existing
    if not save_libraries(path, config):
        log.error("Converted libraries could not be saved", event="service.convert_failed",
                  path=path)
        return None
    _remove_copy(copy_path)
    set_bool_setting(_CONVERTED, True)
    log.info("Settings converted to libraries", event="service.libraries_converted",
             library_count=len(config.libraries),
             included=sum(1 for lib in config.libraries if lib.included),
             settings_read=legacy is not None)
    detail = "" if legacy is not None else attention.SETTINGS_UNREAD
    attention.update(
        tracker, lambda a: a.raise_problem(attention.LIBRARIES_CONVERTED, detail))
    return config


def _add_found(tracker: TrackerDB, libraries: LibraryConfig,
               found: list[dict[str, str]], ui_language: str) -> bool:
    """Add the found sources libraries does not hold yet, not included,
    save and raise the new-library notice. False when they could not be
    saved."""
    added = add_new_libraries(libraries, found, ui_language)
    if not added:
        return True
    if not save_libraries(_get_sources_config_path(), libraries):
        return False
    labels = [lib.label or display_path(lib.path) for lib in added]
    log.info("New libraries added, not included", event="service.libraries_added",
             libraries=labels)
    attention.update(tracker, lambda a: a.add_new_libraries(labels))
    return True


def _start_afresh(tracker: TrackerDB) -> Optional[LibraryConfig]:
    """sources.json is gone after the libraries were converted: the 1.1
    values still in Kodi's file are stale, so every library is found again
    as on a fresh install, not included. None when discovery failed."""
    found = discover_folders()
    if found is None:
        log.info("Libraries not found again yet, discovery failed",
                 event="service.convert_deferred")
        return None
    config = LibraryConfig()
    if not _add_found(tracker, config, found, kodi_ui_language()):
        return None
    log.info("Libraries found again, none included", event="service.libraries_restarted",
             library_count=len(config.libraries))
    return config


def _load_libraries(tracker: TrackerDB) -> Optional[LibraryConfig]:
    """The libraries, converting the 1.1 settings when there is no v2 file
    yet and setup was finished. None skips the cycle: setup is not
    finished, the conversion waits or failed, or the file is damaged.

    A damaged v2 file is never converted over: the 1.1 copy is gone by
    then, so a conversion would reset every library to the defaults."""
    path = _get_sources_config_path()
    config, state = read_libraries(path)
    if state == FILE_OK:
        return config
    if state == FILE_DAMAGED:
        log.error("Library settings unreadable, scan skipped", event="libraries.damaged",
                  path=path)
        attention.update(tracker, lambda a: a.attempt(True, time.time()))
        return None
    if not is_setup_complete():
        return None
    if state == FILE_MISSING and _libraries_converted():
        return _start_afresh(tracker)
    return _convert_libraries(tracker, path)


def _sync_libraries(tracker: TrackerDB, ui_language: str) -> Optional[LibraryConfig]:
    """_load_libraries, plus the sources Kodi gained since: added as not
    included, with the new-library notice. A failed discovery adds
    nothing (what it found is incomplete)."""
    libraries = _load_libraries(tracker)
    if libraries is None:
        return None
    found = discover_folders()
    if found is not None:
        _add_found(tracker, libraries, found, ui_language)
    return libraries


def _prepare_imdb_ratings(libraries: Iterable[Library], monitor: Any) -> bool:
    """Load or refresh the IMDb ratings store once per cycle; True when ready.

    Skipped (False) when none of ``libraries`` (those the run scans) has
    ratings on with a rating source that consults IMDb. The download yields
    to shutdown and to video playback. Any failure means "not ready": IMDb
    ratings are then transient for the cycle while every other field
    proceeds, and the service keeps running.
    """
    if not any("rating" in lib.fields() and rating_sources(lib.rating_source)[1]
               for lib in libraries):
        return False

    def abort() -> bool:
        return bool(
            monitor.abortRequested() or xbmc.getCondVisibility("Player.HasVideo")
        )

    try:
        return imdb_ratings.prepare(abort)
    except Exception:
        log.exception(
            "Preparing the IMDb ratings store failed",
            event="service.imdb_prepare_failed",
        )
        return False


def tvdb_auth_failed(all_stats: Iterable[dict[str, Any]]) -> bool:
    """True when any pass of a cycle reports that TheTVDB rejected the
    add-on's credentials. The callers notify once per cycle on it: the key
    ships with the add-on, so the user cannot fix it, but TVDB titles and
    plots stay paused until it works again."""
    return any(s.get("tvdb_auth_failed") for s in all_stats)


def fanart_auth_failed(all_stats: Iterable[dict[str, Any]]) -> bool:
    """True when any pass of a cycle reports that fanart.tv rejected the
    key. Art that needs fanart.tv waits (it is never swapped to
    TMDB), so the user is told."""
    return any(s.get("fanart_auth_failed") for s in all_stats)


def fanart_auth_string(personal_key: bool) -> int:
    """The string id of the notice for a fanart.tv key rejection; it
    differs because only a personal key is the user's to fix."""
    return 32742 if personal_key else 32743


def _run_scan(
    tracker: TrackerDB,
    libraries: LibraryConfig,
    settings: dict[str, Any],
    monitor: MetaMendMonitor,
    new_only: bool = False,
) -> dict[str, dict[str, int]]:
    """Run scan for MOVIE, SET, TVSHOW, SEASON and EPISODE in order; with
    ``new_only`` only the items new to the tracker (run_scan's new_only).

    Movie sets follow the movies, whose pass stores each movie's TMDB
    collection; the set pass runs only when an included library has Movie
    sets ticked (scan.scans_sets). TV shows are scanned before seasons and
    episodes so their TMDB IDs are available for the season lookups. The
    season pass runs only when an included library manages season posters
    (scan.scans_seasons).

    A Stop scan request ends the cycle after the pass it arrived in: the
    later passes, and the show id map between them, are skipped.

    Returns:
        Dict keyed by media type name with stats dicts as values.
    """
    tmdb_api_key = settings["tmdb_api_key"]
    included = [lib for lib in libraries.libraries if lib.included]
    settings = dict(settings, imdb_ready=_prepare_imdb_ratings(included, monitor))

    all_stats: dict[str, dict[str, int]] = {}

    # One breaker for the whole cycle: a provider that fails repeatedly
    # stays disabled across the movie/tvshow/episode passes.
    breaker = CircuitBreaker()
    # One certification site gate per cycle too: its request cap and memo
    # span the movie and TV show passes.
    cert_gate = SiteGate(settings.get("cert_sites", frozenset()), breaker, monitor)
    # And one set of answer caches: a show's fanart.tv answer and TMDB record
    # serve its season posters in the season pass.
    fanart_cache: dict[tuple[str, str], Any] = {}
    show_cache: dict[str, Any] = {}

    first = (MOVIE, SET, TVSHOW) if scans_sets(libraries) else (MOVIE, TVSHOW)
    for media_type in first:
        stats = run_scan(
            media_type=media_type,
            tracker=tracker,
            libraries=libraries,
            tmdb_api_key=tmdb_api_key,
            settings=settings,
            monitor=monitor,
            new_only=new_only,
            breaker=breaker,
            cert_gate=cert_gate,
            fanart_cache=fanart_cache,
            show_cache=show_cache,
        )
        all_stats[media_type.name] = stats
        if stop_requested():
            mark_stopped(all_stats)
            return all_stats

    show_id_map = tracker.get_show_id_map()
    log.info(
        "Show ID map built for season and episode scans",
        event="service.show_id_map",
        shows=len(show_id_map),
    )

    later = (SEASON, EPISODE) if scans_seasons(libraries) else (EPISODE,)
    for media_type in later:
        all_stats[media_type.name] = run_scan(
            media_type=media_type,
            tracker=tracker,
            libraries=libraries,
            tmdb_api_key=tmdb_api_key,
            settings=settings,
            monitor=monitor,
            show_id_map=show_id_map,
            new_only=new_only,
            breaker=breaker,
            fanart_cache=fanart_cache,
            show_cache=show_cache,
        )
        if stop_requested():
            mark_stopped(all_stats)
            break

    return all_stats


def _maybe_prune_orphans(
    tracker: TrackerDB,
    settings: dict[str, Any],
    targeted: bool,
    scanned: Iterable[str] | None = None,
) -> None:
    """Prune orphaned tracker rows, but ONLY after a full scan.

    CRITICAL CORRECTNESS GUARD: pruning compares each item's `last_seen`
    stamp against a retention cutoff. A targeted (library-event) scan only
    stamps `last_seen` on the few new items it touches, so pruning after one
    would wrongly delete EVERYTHING not in that small set. Only a full scan
    refreshes `last_seen` for the whole library, so pruning is safe only then.

    A retention of 0 disables pruning entirely.
    """
    if targeted:
        # Targeted scan: last_seen was only refreshed for a subset of items.
        # Pruning here would delete the rest of the library. Never prune.
        log.debug(
            "Prune skipped: targeted scan",
            event="service.prune_skip",
            reason="targeted",
        )
        return
    retention = settings["orphan_retention_days"]
    if retention <= 0:
        log.debug(
            "Prune skipped: disabled",
            event="service.prune_skip",
            reason="disabled",
        )
        return
    cutoff = (date.today() - timedelta(days=retention)).isoformat()
    total_removed = 0
    # Only a type whose pass ran refreshed its last_seen stamps: seasons are
    # not scanned while no library manages their poster, nor sets while no
    # library has Movie sets ticked, and their rows (kept originals
    # included) must outlive that. Sets are pruned only when ``scanned``
    # names their pass.
    names = None if scanned is None else set(scanned)
    for mt in (MOVIE, TVSHOW, SEASON, EPISODE, SET):
        if names is not None and mt.name not in names:
            continue
        if mt is SET and names is None:
            continue
        total_removed += tracker.prune_orphans(mt.name, cutoff=cutoff)
    if total_removed:
        log.info(
            "Pruned orphaned tracker rows",
            event="service.orphans_pruned",
            removed=total_removed,
            retention_days=retention,
        )
    else:
        log.debug(
            "Prune ran, no orphans removed",
            event="service.orphans_pruned",
            removed=0,
            retention_days=retention,
        )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def _select_trigger(
    now: float,
    last_scan: float,
    interval_sec: float,
    has_pending_event: bool,
) -> tuple[bool, str]:
    """Decide whether to scan this tick and why.

    A due scheduled scan takes precedence over a library event in the same
    tick: the scheduled scan re-evaluates maturity for every item and also
    covers the newly added items, so the pending event is satisfied by it.
    Only fall back to a targeted library-event scan when no scheduled scan
    is due.

    Returns (should_scan, reason) where reason is "scheduled" or "library_event".
    """
    if now - last_scan >= interval_sec:
        return (True, "scheduled")
    if has_pending_event:
        return (True, "library_event")
    return (False, "scheduled")


def _playing() -> bool:
    """Whether anything plays, video or audio: the background shows
    nothing then."""
    return bool(xbmc.getCondVisibility("Player.HasMedia"))


def _check_folders(libraries: LibraryConfig) -> dict[str, bool]:
    """Whether each library folder answers, for the offline-folder
    problem (see library_folders_in_use for which folders count)."""
    reachable: dict[str, bool] = {}
    for path in library_folders_in_use(libraries):
        try:
            reachable[path] = bool(xbmcvfs.exists(path))
        except Exception:
            log.exception("Folder check failed", event="service.folder_check_failed")
            reachable[path] = False
    return reachable


def _record_cycle(
    record: attention.Attention, *, shutdown: bool, aborted: bool,
    tvdb_rejected: bool, tmdb_answered: bool, tvdb_answered: bool,
    fanart_rejected: bool, fanart_answered: bool, fanart_personal: bool,
    folders: dict[str, bool] | None, now: float, unmatched: int | None = None,
) -> None:
    """What a finished background cycle tells the problem record: the
    attempt for the failure streak (not when Kodi shut down), TheTVDB's
    credentials, fanart.tv's key, and, after a full pass over the library,
    the folders and the number of items in no library. A key or credential
    problem clears only when that provider answered: a cycle that never
    asked it proves nothing, and clearing would show the problem again the
    next time it is hit."""
    if tmdb_answered:
        record.clear(attention.KEY_REJECTED)
    if not shutdown:
        record.attempt(aborted, now)
    if tvdb_rejected:
        record.raise_problem(attention.TVDB_AUTH)
    elif tvdb_answered:
        record.clear(attention.TVDB_AUTH)
    if fanart_rejected:
        record.raise_problem(
            attention.FANART_AUTH, attention.PERSONAL_KEY if fanart_personal else "")
    elif fanart_answered:
        record.clear(attention.FANART_AUTH)
    if folders is not None:
        record.folders_checked(folders, now)
    if unmatched:
        record.raise_problem(attention.UNMATCHED, str(unmatched))
    elif unmatched == 0:
        record.clear(attention.UNMATCHED)


def updated_text(count: int) -> str:
    """"1 item updated" / "N items updated"."""
    return lang(32504) if count == 1 else lang(32349).format(count)


def _attention_tick(
    tracker: TrackerDB, monitor: Any, shown: set[tuple[str, str]],
) -> None:
    """Show what the problem record holds that was not shown yet: the
    attention window, and the TheTVDB and fanart.tv toasts. Nothing while
    anything plays (it waits for the next tick without playback) or while
    Kodi quits.

    ``shown`` is what this service run already showed: should saving the
    record fail, the same window still never comes back within a session.

    Never raises: the service loop calls it outside its own error handling,
    and a window that cannot open counts as shown, so it is not retried
    every second."""
    try:
        if monitor.abortRequested() or _playing():
            return
        record = attention.load(tracker)
        pending = record.pending_window()
        if pending is not None:
            main, others = pending
            displayed = [main, *others]
            seen = {(p.kind, p.detail) for p in displayed}
            if not seen <= shown:
                shown |= seen
                log.info("Attention window shown", event="service.attention_shown",
                         kind=main.kind, others=[p.kind for p in others])
                answer = "later"
                try:
                    answer = show_attention_window(main, others)
                finally:
                    attention.update(tracker, lambda a: a.mark_window_shown(displayed))
                if answer == "setup":
                    xbmc.executebuiltin("RunScript(script.metamender,wizard)")
                elif answer == "libraries":
                    xbmc.executebuiltin("RunScript(script.metamender,libraries)")
        toast = (attention.TVDB_AUTH, "")
        if record.pending_toast(attention.TVDB_AUTH) and toast not in shown:
            shown.add(toast)
            attention.update(
                tracker, lambda a: a.mark_toast_shown(attention.TVDB_AUTH))
            notify(lang(32352))  # TheTVDB rejected the credentials
        fanart = record.open_detail(attention.FANART_AUTH)
        toast = (attention.FANART_AUTH, fanart)
        if record.pending_toast(attention.FANART_AUTH) and toast not in shown:
            shown.add(toast)
            attention.update(
                tracker, lambda a: a.mark_toast_shown(attention.FANART_AUTH))
            notify(lang(fanart_auth_string(fanart == attention.PERSONAL_KEY)))
    except Exception:
        log.exception("Showing a problem failed", event="service.attention_failed")


def run() -> None:
    """Main service entry point. Blocks until Kodi requests abort."""
    # Re-initialize the logger now that Kodi settings are readable.
    # get_logger() at module import time may have initialized with
    # debug_enabled=False because settings weren't available yet, so
    # reconfigure now that settings are readable.
    try:
        debug_on = get_bool_setting('logging')
        addon_id = get_addon().getAddonInfo('id')
    except RuntimeError:
        debug_on = False
        addon_id = DEFAULT_ADDON_ID
    StructuredLogger.reconfigure(debug_enabled=debug_on, addon_id=addon_id)

    log.info("Service started", event="service.start")
    clear_file_lock()

    monitor = MetaMendMonitor()
    tracker: TrackerDB | None = None
    last_scan = 0.0  # Force scan on first loop iteration
    next_retry_after = 0.0  # Backoff gate after a failed scan (both triggers)
    # What this service last wrote about setup, so the record is written on
    # a change only, not every tick.
    setup_known: bool | None = None
    # Problems this service run showed (see _attention_tick).
    shown: set[tuple[str, str]] = set()

    try:
        tracker = TrackerDB(_get_db_path())
        try:
            _copy_old_settings()
        except Exception:
            log.exception("Saving the old settings aside failed",
                          event="service.copy_failed")

        while not monitor.abortRequested():
            try:
                now = time.time()

                setup_done = is_setup_complete()
                if setup_done != setup_known:
                    setup_known = setup_done
                    if setup_done:
                        attention.update(tracker, lambda a: a.clear(attention.SETUP))
                    else:
                        log.info("Waiting for setup", event="service.needs_setup")
                        attention.update(
                            tracker, lambda a: a.raise_problem(attention.SETUP))
                if not setup_done:
                    # Nothing scans before the wizard has run: no key, and
                    # no language the user confirmed. The wizard's Finish
                    # starts the first scan itself, so the schedule counts
                    # from now and library events seen meanwhile are dropped.
                    last_scan = now
                    monitor.clear_scan_request()
                    _attention_tick(tracker, monitor, shown)
                    if monitor.waitForAbort(SERVICE_SLEEP_INTERVAL_SEC):
                        break
                    continue

                # Trigger selection (scheduled takes precedence over a
                # same-tick library event; see _select_trigger). Only the scan
                # interval is needed to decide this, so read it cheaply each
                # tick; the full settings dict is loaded only when about to scan.
                interval_sec = get_int_setting("scan_interval", 24) * 3600
                should_scan, reason = _select_trigger(
                    now, last_scan, interval_sec,
                    monitor.has_pending_scan(LIBRARY_SCAN_DEBOUNCE_SEC),
                )

                # Honor a post-failure backoff for BOTH trigger types so a
                # persistently-failing Kodi query is not re-attempted every loop
                # (the library-event trigger is independent of last_scan).
                if should_scan and now < next_retry_after:
                    should_scan = False

                # Guard: skip while video is playing
                if should_scan and xbmc.getCondVisibility("Player.HasVideo"):
                    should_scan = False
                    log.debug(
                        "Skipping scan, video is playing",
                        event="service.skip_playback",
                    )

                settings: dict[str, Any] | None = None
                if should_scan:
                    settings = _load_settings()
                    if not settings.get("tmdb_api_key"):
                        log.warning(
                            "No TMDB API key configured, skipping scan",
                            event="service.skip_no_key",
                        )
                        attention.update(
                            tracker, lambda a: a.raise_problem(attention.NO_KEY))
                        last_scan = time.time()
                        should_scan = False
                    else:
                        attention.update(tracker, lambda a: a.clear(attention.NO_KEY))

                if should_scan and not acquire_scan_lock():
                    log.info(
                        "Scan already running elsewhere, skipping",
                        event="service.locked",
                    )
                    should_scan = False
                    # The other scan can take hours; ask again later rather
                    # than every service tick.
                    next_retry_after = now + SCAN_LOCKED_RETRY_SEC

                if should_scan:
                    # settings is always loaded above when should_scan stays True.
                    assert settings is not None
                    # Lock acquired above; release on EVERY exit path
                    # (success, KodiQueryError continue, unexpected error).
                    try:
                        libraries = _sync_libraries(tracker, settings["ui_language"])
                        if libraries is None:
                            # Retried after a pause rather than every tick.
                            next_retry_after = time.time() + SCAN_FAILURE_BACKOFF_SEC
                            continue

                        StructuredLogger.start_scan_log()

                        # A library event scans only the items new to the
                        # tracker, once a full scan has seen the library.
                        targeted = reason == "library_event" and bool(
                            tracker.get_scan_state("last_scan_completed")
                        )

                        log.info(
                            "Scan triggered",
                            event="service.scan_trigger",
                            reason=reason,
                            targeted=targeted,
                        )

                        tracker.begin_cycle(settings["resume_interrupted"])
                        # A Stop scan chosen while no scan ran must not end
                        # this one.
                        clear_stop()

                        scan_start = time.perf_counter()
                        try:
                            all_stats = _run_scan(
                                tracker, libraries, settings, monitor,
                                new_only=targeted,
                            )
                        except KodiQueryError:
                            # A Kodi library query failed (RPC/parse error),
                            # which is NOT an empty library. Treat the cycle as
                            # FAILED: do not advance the schedule or the
                            # watermark, and do not clear a library-event
                            # request, so it retries. Set a short backoff
                            # instead of a full interval so the next loop
                            # re-attempts soon without hammering Kodi.
                            # A query failing because Kodi is shutting down says
                            # nothing about whether scans work.
                            if not monitor.abortRequested():
                                attention.update(
                                    tracker, lambda a: a.attempt(True, time.time()))
                            log.exception(
                                "Scan aborted on Kodi query failure",
                                event="service.scan_failed",
                                reason=reason,
                            )
                            next_retry_after = (
                                time.time() + SCAN_FAILURE_BACKOFF_SEC
                            )
                            continue
                        except ApiKeyError as exc:
                            # A provider rejected the API key. This is terminal
                            # for the cycle: notify the user, do NOT advance the
                            # watermark or clear a library-event request, and back
                            # off so we do not re-attempt every loop while the key
                            # stays invalid. The scan leaves the logging to here.
                            log.exception(
                                "Scan stopped: invalid API key",
                                event="service.scan_apikey",
                                reason=reason,
                                provider=exc.provider,
                            )
                            attention.update(
                                tracker,
                                lambda a: a.raise_problem(attention.KEY_REJECTED),
                            )
                            next_retry_after = (
                                time.time() + SCAN_FAILURE_BACKOFF_SEC
                            )
                            continue
                        finally:
                            StructuredLogger.stop_scan_log()

                        duration_ms = int((time.perf_counter() - scan_start) * 1000)

                        movie_stats = all_stats.get("movie", {})
                        tvshow_stats = all_stats.get("tvshow", {})
                        season_stats = all_stats.get("season", {})
                        episode_stats = all_stats.get("episode", {})
                        set_stats = all_stats.get("set", {})

                        log.info(
                            "Scan complete",
                            event="service.scan_complete",
                            movies_updated=movie_stats.get("updated", 0),
                            sets_updated=set_stats.get("updated", 0),
                            movies_moved=set_stats.get("moved", 0),
                            movies_joined=set_stats.get("joined", 0),
                            sets_created=set_stats.get("sets_created", 0),
                            tvshows_updated=tvshow_stats.get("updated", 0),
                            seasons_updated=season_stats.get("updated", 0),
                            episodes_updated=episode_stats.get("updated", 0),
                            duration_ms=duration_ms,
                        )

                        last_scan = time.time()
                        monitor.clear_scan_request()

                        # A pass that stopped early (shutdown, providers down)
                        # did not cover the library. Closing the cycle then
                        # would advance the watermark over items it never
                        # visited, and pruning would delete the tracker rows of
                        # items whose last_seen it never refreshed.
                        cycle_aborted = any(
                            s.get("aborted") for s in all_stats.values()
                        )
                        if cycle_aborted:
                            log.info(
                                "Scan cycle left open after early termination",
                                event="service.cycle_incomplete",
                            )
                        else:
                            tracker.mark_cycle_complete()
                            tracker.set_scan_state(
                                "last_scan_completed",
                                time.strftime("%Y-%m-%d %H:%M:%S"),
                            )

                            # Prune orphaned tracker rows. Guarded to run only
                            # after a FULL scan (not targeted); see
                            # _maybe_prune_orphans for why a targeted scan must
                            # never prune.
                            _maybe_prune_orphans(tracker, settings, targeted,
                                                 scanned=all_stats.keys())

                        # A pass stopped by Kodi shutting down or by the
                        # user's Stop scan says nothing about whether scans
                        # work; any other early stop (every provider down)
                        # counts as a failed attempt.
                        stopped = user_stopped(all_stats.values())
                        clear_stop()
                        shutdown = monitor.abortRequested() or stopped
                        tvdb_rejected = tvdb_auth_failed(all_stats.values())
                        tmdb_answered = any(
                            s.get("tmdb_answered") for s in all_stats.values())
                        tvdb_answered = any(
                            s.get("tvdb_answered") for s in all_stats.values())
                        fanart_rejected = fanart_auth_failed(all_stats.values())
                        fanart_answered = any(
                            s.get("fanart_answered") for s in all_stats.values())
                        full_pass = not targeted and not cycle_aborted
                        folders = _check_folders(libraries) if full_pass else None
                        unmatched = (
                            sum(int(s.get("unmatched", 0)) for s in all_stats.values())
                            if full_pass else None
                        )

                        attention.update(tracker, partial(
                            _record_cycle, shutdown=shutdown, aborted=cycle_aborted,
                            tvdb_rejected=tvdb_rejected, tmdb_answered=tmdb_answered,
                            tvdb_answered=tvdb_answered, fanart_rejected=fanart_rejected,
                            fanart_answered=fanart_answered,
                            fanart_personal=bool(settings.get("fanart_client_key")),
                            folders=folders,
                            now=time.time(), unmatched=unmatched,
                        ))

                        total_updated = (
                            movie_stats.get("updated", 0)
                            + tvshow_stats.get("updated", 0)
                            + episode_stats.get("updated", 0)
                        )
                        if (settings["show_notifications"] and total_updated
                                and not _playing()):
                            notify(updated_text(total_updated))
                    finally:
                        release_scan_lock()

            except Exception:
                # Back off like the typed handlers above. Without this the loop
                # re-triggers on the very next tick (SERVICE_SLEEP_INTERVAL_SEC
                # is 1s) because neither last_scan nor next_retry_after moved,
                # turning any unanticipated fault into a 1 Hz full-library scan.
                log.exception("Scan cycle failed", event="service.scan_error")
                next_retry_after = time.time() + SCAN_FAILURE_BACKOFF_SEC
                if tracker is not None and not monitor.abortRequested():
                    attention.update(tracker, lambda a: a.attempt(True, time.time()))

            if tracker is not None:
                _attention_tick(tracker, monitor, shown)
            if monitor.waitForAbort(SERVICE_SLEEP_INTERVAL_SEC):
                break

    finally:
        if tracker is not None:
            tracker.close()
        log.info("Service stopped", event="service.stop")
        StructuredLogger.shutdown()
