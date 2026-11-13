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
"""
from __future__ import annotations

import os
import time
from collections.abc import Iterable
from datetime import date, timedelta
from functools import partial
from typing import Any

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
from resources.lib.data.media_types import EPISODE, MOVIE, TVSHOW
from resources.lib.data.presets import country_for_setting
from resources.lib.data.sources import (
    kodi_ui_language,
    library_folders_in_use,
    load_source_config,
)
from resources.lib.data.tracker import TrackerDB
from resources.lib.engine.breaker import CircuitBreaker
from resources.lib.engine.certchain import SiteGate
from resources.lib.engine.resolve import FOLLOW_SCRAPER, rating_sources
from resources.lib.engine.scan import run_scan
from resources.lib.providers import imdb_ratings
from resources.lib.service import attention
from resources.lib.service.lock import (
    acquire_scan_lock,
    clear_file_lock,
    release_scan_lock,
)
from resources.lib.ui.attention_window import show_attention_window
from resources.lib.utils import (
    ApiKeyError,
    KodiQueryError,
    StructuredLogger,
    get_addon,
    get_bool_setting,
    get_float_setting,
    get_int_setting,
    get_logger,
    get_setting,
    is_setup_complete,
    lang,
    notify,
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

_FIELD_TOGGLES = {
    "enable_ratings": frozenset({"rating"}),
    "enable_plots": frozenset({"plot"}),
    "enable_episode_titles": frozenset({"title"}),
    # Show and movie titles: "main_title" stands for their "title" field, so
    # the episode-title toggle does not switch them (see candidate_fields).
    "enable_main_titles": frozenset({"main_title"}),
    "enable_certifications": frozenset({"mpaa"}),
    "enable_credits": frozenset({"director", "writer"}),
    "enable_trailers": frozenset({"trailer"}),
    "enable_taglines": frozenset({"tagline"}),
    "enable_details": frozenset({"genre", "studio", "country", "runtime", "firstaired"}),
}


def _load_settings() -> dict[str, Any]:
    """Read all settings needed by the scan engine.

    Returns:
        Dict with tmdb_api_key, rating_source, text_source_order,
        fallback_order, enabled_fields (FrozenSet),
        stale_threshold_days, refetch_schedule, rate_limit, scan_interval,
        show_notifications, resume_interrupted and orphan_retention_days.
    """
    # Build enabled fields from individual toggles
    fields: set = set()
    for setting_id, field_names in _FIELD_TOGGLES.items():
        if get_bool_setting(setting_id):
            fields.update(field_names)

    return {
        "tmdb_api_key": get_setting("tmdb_api_key"),
        "rating_source": get_int_setting("rating_source", FOLLOW_SCRAPER),
        "text_source_order": get_int_setting("text_source_order", 2),
        "fallback_order": get_int_setting("fallback_order", 0),
        "enabled_fields": frozenset(fields),
        "stale_threshold_days": get_int_setting("stale_threshold_days", 365),
        "refetch_schedule": get_setting("refetch_schedule"),
        "rate_limit": get_float_setting("rate_limit", 0.25),
        "scan_interval": get_int_setting("scan_interval", DEFAULT_SCAN_INTERVAL_HOURS),
        "show_notifications": get_bool_setting("show_notifications"),
        "resume_interrupted": get_bool_setting("resume_interrupted"),
        "orphan_retention_days": get_int_setting("orphan_retention_days", 30),
        # Certifications (Certifications tab); see scan._cert_config.
        "cert_country": country_for_setting(get_int_setting("country", 0), kodi_ui_language()),
        "cert_prefix_override": (
            get_setting("rating_prefix") if get_bool_setting("override_prefix") else None
        ),
        "cert_sites": frozenset(
            site for site in ("fsk", "bbfc", "medieraadet")
            if get_bool_setting("enable_" + site)
        ),
        "cert_replace_foreign": get_bool_setting("replace_incorrect"),
        "cert_not_found": (
            get_setting("fallback_rating").strip() or None
            if get_bool_setting("enable_fallback") else None
        ),
    }


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
    addon_data = xbmcvfs.translatePath(
        "special://profile/addon_data/{}/".format(DEFAULT_ADDON_ID)
    )
    return os.path.join(addon_data, SOURCES_CONFIG_FILENAME)




def _prepare_imdb_ratings(settings: dict[str, Any], monitor: Any) -> bool:
    """Load or refresh the IMDb ratings store once per cycle; True when ready.

    Skipped (False) when ratings are off or rating_source never consults IMDb.
    The download yields to shutdown and to video playback. Any failure means
    "not ready": IMDb ratings are then transient for the cycle while every
    other field proceeds, and the service keeps running.
    """
    if "rating" not in settings["enabled_fields"]:
        return False
    if not rating_sources(settings.get("rating_source", FOLLOW_SCRAPER))[1]:
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


def _run_scan(
    tracker: TrackerDB,
    source_config: dict[str, Any],
    settings: dict[str, Any],
    monitor: MetaMendMonitor,
    new_only: bool = False,
) -> dict[str, dict[str, int]]:
    """Run scan for MOVIE, TVSHOW, and EPISODE in order; with ``new_only``
    only the items new to the tracker (run_scan's new_only).

    TV shows are scanned before episodes so their TMDB IDs are
    available for the episode season lookups.

    Returns:
        Dict keyed by media type name with stats dicts as values.
    """
    tmdb_api_key = settings["tmdb_api_key"]
    enabled_fields = settings["enabled_fields"]
    settings = dict(settings, imdb_ready=_prepare_imdb_ratings(settings, monitor))

    all_stats: dict[str, dict[str, int]] = {}

    # One breaker for the whole cycle: a provider that fails repeatedly
    # stays disabled across the movie/tvshow/episode passes.
    breaker = CircuitBreaker()
    # One certification site gate per cycle too: its request cap and memo
    # span the movie and TV show passes.
    cert_gate = SiteGate(settings.get("cert_sites", frozenset()), breaker, monitor)

    for media_type in (MOVIE, TVSHOW):
        stats = run_scan(
            media_type=media_type,
            tracker=tracker,
            source_config=source_config,
            enabled_fields=enabled_fields,
            tmdb_api_key=tmdb_api_key,
            settings=settings,
            monitor=monitor,
            new_only=new_only,
            breaker=breaker,
            cert_gate=cert_gate,
        )
        all_stats[media_type.name] = stats

    show_id_map = tracker.get_show_id_map()
    log.info(
        "Show ID map built for episode scan",
        event="service.show_id_map",
        shows=len(show_id_map),
    )

    episode_stats = run_scan(
        media_type=EPISODE,
        tracker=tracker,
        source_config=source_config,
        enabled_fields=enabled_fields,
        tmdb_api_key=tmdb_api_key,
        settings=settings,
        monitor=monitor,
        show_id_map=show_id_map,
        new_only=new_only,
        breaker=breaker,
    )
    all_stats[EPISODE.name] = episode_stats

    return all_stats


def _maybe_prune_orphans(
    tracker: TrackerDB,
    settings: dict[str, Any],
    targeted: bool,
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
    for mt in (MOVIE, TVSHOW, EPISODE):
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


def _check_folders(source_config: dict[str, Any]) -> dict[str, bool]:
    """Whether each library folder answers, for the offline-folder
    problem (see library_folders_in_use for which folders count)."""
    reachable: dict[str, bool] = {}
    for path in library_folders_in_use(source_config.get("sources", [])):
        try:
            reachable[path] = bool(xbmcvfs.exists(path))
        except Exception:
            log.exception("Folder check failed", event="service.folder_check_failed")
            reachable[path] = False
    return reachable


def _record_cycle(
    record: attention.Attention, *, shutdown: bool, aborted: bool,
    tvdb_rejected: bool, tmdb_answered: bool, tvdb_answered: bool,
    folders: dict[str, bool] | None, now: float,
) -> None:
    """What a finished background cycle tells the problem record: the
    attempt for the failure streak (not when Kodi shut down), TheTVDB's
    credentials, and the folders when they were checked. A key or
    credential problem clears only when that provider answered: a cycle
    that never asked it proves nothing, and clearing would show the problem
    again the next time it is hit."""
    if tmdb_answered:
        record.clear(attention.KEY_REJECTED)
    if not shutdown:
        record.attempt(aborted, now)
    if tvdb_rejected:
        record.raise_problem(attention.TVDB_AUTH)
    elif tvdb_answered:
        record.clear(attention.TVDB_AUTH)
    if folders is not None:
        record.folders_checked(folders, now)


def updated_text(count: int) -> str:
    """"1 item updated" / "N items updated"."""
    return lang(32504) if count == 1 else lang(32349).format(count)


def _attention_tick(
    tracker: TrackerDB, monitor: Any, shown: set[tuple[str, str]],
) -> None:
    """Show what the problem record holds that was not shown yet: the
    attention window, and the TheTVDB toast. Nothing while anything plays
    (it waits for the next tick without playback) or while Kodi quits.

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
        toast = (attention.TVDB_AUTH, "")
        if record.pending_toast(attention.TVDB_AUTH) and toast not in shown:
            shown.add(toast)
            attention.update(
                tracker, lambda a: a.mark_toast_shown(attention.TVDB_AUTH))
            notify(lang(32352))  # TheTVDB rejected the credentials
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

                        source_config = load_source_config(
                            _get_sources_config_path()
                        )

                        tracker.begin_cycle(settings["resume_interrupted"])

                        scan_start = time.perf_counter()
                        try:
                            all_stats = _run_scan(
                                tracker, source_config, settings, monitor,
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
                        episode_stats = all_stats.get("episode", {})

                        log.info(
                            "Scan complete",
                            event="service.scan_complete",
                            movies_updated=movie_stats.get("updated", 0),
                            tvshows_updated=tvshow_stats.get("updated", 0),
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
                            _maybe_prune_orphans(tracker, settings, targeted)

                        # A pass stopped by Kodi shutting down says nothing
                        # about whether scans work; any other early stop
                        # (every provider down) counts as a failed attempt.
                        shutdown = monitor.abortRequested()
                        tvdb_rejected = tvdb_auth_failed(all_stats.values())
                        tmdb_answered = any(
                            s.get("tmdb_answered") for s in all_stats.values())
                        tvdb_answered = any(
                            s.get("tvdb_answered") for s in all_stats.values())
                        folders = (
                            _check_folders(source_config)
                            if not targeted and not cycle_aborted else None
                        )

                        attention.update(tracker, partial(
                            _record_cycle, shutdown=shutdown, aborted=cycle_aborted,
                            tvdb_rejected=tvdb_rejected, tmdb_answered=tmdb_answered,
                            tvdb_answered=tvdb_answered, folders=folders,
                            now=time.time(),
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
