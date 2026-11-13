"""
MetaMender entry-point action handlers.

Handlers invoked from default.py when the script is launched with an action
argument (for example RunScript(script.metamender,reset_tracker) from a
settings action button).

Logging:
    Logger: 'actions'
    Key events:
        - actions.reset_tracker (INFO): Reset-tracker action finished
        - actions.update_now_start (INFO): Update-now reset scan starting
        - actions.update_now (INFO): Update-now reset scan finished
        - actions.update_now_invalid (WARNING): Update-now bad dbtype/dbid
        - actions.update_now_notfound (WARNING): Update-now item not in library
        - actions.skip_no_key (WARNING): Update-now skipped, no TMDB API key
        - actions.locked (INFO): Update-now skipped, a scan is running
        - actions.error (ERROR): Action handler raised an unexpected exception
"""
from __future__ import annotations

from typing import Dict, Optional

import xbmc
import xbmcgui

from resources.lib.constants import DEFAULT_ADDON_ID
from resources.lib.data.kodi import get_item_by_id
from resources.lib.data.media_types import EPISODE, MOVIE, MediaType
from resources.lib.data.sources import load_source_config
from resources.lib.data.tracker import TrackerDB
from resources.lib.engine.breaker import CircuitBreaker
from resources.lib.engine.scan import run_scan
from resources.lib.service import attention
from resources.lib.service.daemon import (
    _get_db_path,
    _get_sources_config_path,
    _load_settings,
    _prepare_imdb_ratings,
    tvdb_auth_failed,
)
from resources.lib.service.lock import acquire_scan_lock, release_scan_lock
from resources.lib.service.refresh import (
    bring_back_or_busy,
    open_refresh,
    request_reopen,
    show_id_of,
)
from resources.lib.service.wizard import open_setup
from resources.lib.ui.setup_model import WIZARD
from resources.lib.utils import (
    ApiKeyError,
    StructuredLogger,
    get_addon,
    get_bool_setting,
    get_logger,
    is_setup_complete,
    lang,
    notify,
)

log = get_logger('actions')

# Map a Kodi ListItem.DBType string to its MediaType.
_DBTYPE_TO_MEDIA_TYPE: Dict[str, MediaType] = {
    "movie": MOVIE,
    "episode": EPISODE,
}


def _init_logging() -> None:
    """Initialize StructuredLogger for a one-shot action invocation."""
    try:
        debug_on = get_bool_setting('logging')
        addon_id = get_addon().getAddonInfo('id')
    except RuntimeError:
        debug_on = False
        addon_id = DEFAULT_ADDON_ID
    StructuredLogger.reconfigure(debug_enabled=debug_on, addon_id=addon_id)


def reset_tracker() -> None:
    """Clear all maturity facts so the next scan re-pulls everything (settings action)."""
    _init_logging()

    if not xbmcgui.Dialog().yesno(lang(32360), lang(32361)):  # "Reset tracker?" / body
        return

    # Take the scan lock: this mutates the same field_status rows a running
    # scan writes, so the two must not overlap.
    if not acquire_scan_lock():
        log.info(
            "A scan is already running, skipping reset",
            event="actions.locked",
        )
        notify(lang(32344))  # A scan is already running
        return

    tracker = None
    try:
        tracker = TrackerDB(_get_db_path())
        count = tracker.clear_field_status()
        log.info(
            "Tracker reset",
            event="actions.reset_tracker",
            cleared=count,
        )
        notify(lang(32362).format(count))  # "Reset complete: {} fields cleared"
    except Exception:
        log.exception("Reset tracker failed", event="actions.error")
    finally:
        release_scan_lock()
        if tracker is not None:
            tracker.close()


def update_now(dbtype: str, dbid: str) -> None:
    """Force a fresh single-item correction (D3 "Update now" context action).

    Runs a reset scan of one library item: it bypasses the disabled-source
    gate, the playback yield, and the cycle-processed skip, treats every
    enabled field as due, and leaves each field's refresh schedule as it was
    (a manual refresh is not a sample of the item's ageing). A show or a
    season refreshes everything under it with a progress window
    (service/refresh.py). Acquires the shared scan lock so it never runs
    concurrently with another scan; while one runs, a click inside the show
    being refreshed brings its window back.

    Args:
        dbtype: Kodi ListItem.DBTYPE ("movie", "tvshow", "season" or
            "episode").
        dbid: Kodi database ID as a string (from $INFO[ListItem.DBID]).
    """
    _init_logging()

    if not is_setup_complete():
        log.info("Setup not finished, opening the wizard", event="actions.needs_setup")
        open_setup(WIZARD)
        return

    log.info(
        "Update now action starting",
        event="actions.update_now_start",
        media_type=dbtype,
        item_id=str(dbid),
    )

    if dbtype in ("tvshow", "season"):
        try:
            show_or_season = int(dbid)
        except (TypeError, ValueError):
            notify(lang(32343))  # Invalid item
            return
        open_refresh(dbtype, show_or_season)
        return

    media_type: Optional[MediaType] = _DBTYPE_TO_MEDIA_TYPE.get(dbtype)
    if media_type is None:
        log.warning(
            "Update now called with unknown dbtype",
            event="actions.update_now_invalid",
            dbtype=dbtype,
        )
        notify(lang(32342))  # Cannot update this item type
        return

    try:
        item_id = int(dbid)
    except (TypeError, ValueError):
        log.warning(
            "Update now called with invalid dbid",
            event="actions.update_now_invalid",
            dbid=str(dbid),
        )
        notify(lang(32343))  # Invalid item
        return

    if not acquire_scan_lock():
        if bring_back_or_busy(show_id_of(dbtype, item_id)) == "reopen":
            log.info("Refresh running for this show, showing its window",
                     event="actions.reopen_refresh")
            request_reopen()
            return
        log.info(
            "A scan is already running, skipping update now",
            event="actions.locked",
        )
        notify(lang(32344))  # A scan is already running
        return

    tracker = None
    # One log file per Update now, like a scan, so the item's whole check
    # is in one place when someone reports a wrong value.
    StructuredLogger.start_scan_log()
    try:
        item = get_item_by_id(media_type, item_id)
        if item is None:
            log.warning(
                "Update now could not find the item",
                event="actions.update_now_notfound",
                media_type=media_type.name,
                item_id=item_id,
            )
            notify(lang(32345))  # Item not found
            return

        settings = _load_settings()
        tmdb_api_key = settings["tmdb_api_key"]
        if not tmdb_api_key:
            log.warning(
                "No TMDB API key configured, cannot update",
                event="actions.skip_no_key",
            )
            notify(lang(32346))  # No TMDB API key configured
            return

        tracker = TrackerDB(_get_db_path())
        source_config = load_source_config(_get_sources_config_path())

        show_id_map: Optional[Dict[int, str]] = None
        if media_type.name == "episode":
            show_id_map = tracker.get_show_id_map()

        monitor = xbmc.Monitor()
        settings["imdb_ready"] = _prepare_imdb_ratings(settings, monitor)
        stats = run_scan(
            media_type=media_type,
            tracker=tracker,
            source_config=source_config,
            enabled_fields=settings["enabled_fields"],
            tmdb_api_key=tmdb_api_key,
            settings=settings,
            monitor=monitor,
            items=[item],
            reset=True,
            breaker=CircuitBreaker(),
            show_id_map=show_id_map,
        )

        # TMDB answered, so the key works: a rejected-key problem is over.
        if stats.get("tmdb_answered"):
            attention.update(tracker, lambda a: a.clear(attention.KEY_REJECTED))
        title = item.get("title", "") or str(item_id)
        updated = stats.get("updated", 0)
        log.info(
            "Update now complete",
            event="actions.update_now",
            media_type=media_type.name,
            title=title,
            updated=updated,
            unreachable=stats.get("unreachable", 0),
            transient=stats.get("transient", 0),
            aborted=bool(stats.get("aborted")),
        )
        unchecked = (stats.get("unreachable") or stats.get("transient")
                     or stats.get("aborted"))
        if updated:
            notify(lang(32350).format(title))  # Updated: {}
        elif unchecked:
            notify(lang(32353).format(title))  # Could not check now: {}
        else:
            notify(lang(32351).format(title))  # No changes: {}
        if tvdb_auth_failed([stats]):
            notify(lang(32352))  # TheTVDB rejected the credentials
    except ApiKeyError:
        log.exception("Update now stopped: invalid API key", event="actions.apikey")
        notify(lang(32341))  # Invalid TMDB API key
        if tracker is not None:
            attention.update(
                tracker, lambda a: a.raise_problem(attention.KEY_REJECTED))
    except Exception:
        log.exception("Update now action failed", event="actions.error")
        notify(lang(32347))  # Update failed
    finally:
        StructuredLogger.stop_scan_log()
        release_scan_lock()
        if tracker is not None:
            tracker.close()
