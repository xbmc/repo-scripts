"""
EasyMovie UI entry point.

Orchestrates the full addon flow:
1. Load settings
2. Apply theme
3. Check for in-progress movie (offer resume)
4. Determine mode (Browse/Playlist/Ask)
5. Run filter wizard (if filters need asking)
6. Query movies + apply filters
7. Apply movie set substitutions
8. Show results (browse) or build playlist
9. Handle Re-roll loop

Logging:
    Logger: 'default'
    Key events:
        - launch.start (INFO): Addon launched
        - launch.mode_selected (INFO): Mode determined
        - launch.resume_offered (INFO): In-progress movie found
    See LOGGING.md for full guidelines.
"""
from __future__ import annotations

import os
import random
import sys
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING, Tuple, cast

import xbmcvfs

from resources.lib.constants import (
    ADDON_ID,
    MODE_BROWSE, MODE_PLAYLIST, MODE_ASK,
    PROP_PLAYLIST_RUNNING,
    RESURFACE_WINDOWS,
)
from resources.lib.utils import (
    get_logger, invalidate_icon_cache, json_query, notify, log_timing, lang,
)
from resources.lib.ui.settings import load_settings
from resources.lib.ui.wizard import WizardFlow
from resources.lib.ui.dialogs import show_confirm_dialog, show_select_dialog
from resources.lib.ui.browse_window import (
    show_browse_window, RESULT_REROLL, RESULT_SURPRISE,
)
from resources.lib.data.queries import (
    get_all_movies_query,
    get_movie_details_with_art_query,
    get_movie_set_details_query,
    get_in_progress_movies_query,
)
from resources.lib.data.filters import apply_filters, filter_by_playlist_ids
from resources.lib.data.smart_playlists import extract_movie_ids_from_playlist
from resources.lib.data.movie_sets import apply_set_substitutions
from resources.lib.data.results import select_and_sort_results
from resources.lib.data.storage import StorageManager

if TYPE_CHECKING:
    from resources.lib.ui.settings import (
        FilterSettings, BrowseSettings, PlaylistSettings,
        SetSettings, PlaybackSettings, AdvancedSettings,
    )

_active_monitors = []  # Keep references to prevent GC


def _check_clone_version(addon_id: str, addon_path: str) -> bool:
    """Check if a clone needs updating. Returns True if OK to proceed.

    For clones, compares clone version against parent version.
    If outdated, prompts for mandatory update.
    Returns False if the clone should not proceed (update triggered or declined).
    """
    import xbmc
    import xbmcaddon
    import xbmcgui

    log = get_logger('default')

    # Check if we just updated (Kodi cache may still report old version)
    window = xbmcgui.Window(10000)
    update_flag = f'EasyMovie.UpdateComplete.{addon_id}'
    parent_addon = xbmcaddon.Addon(ADDON_ID)
    parent_version = parent_addon.getAddonInfo('version')

    update_flag_version = window.getProperty(update_flag)
    if update_flag_version:
        if update_flag_version == parent_version:
            log.info("Clone update flag detected, skipping version check",
                     event="clone.update_flag_cleared", addon_id=addon_id,
                     flag_version=update_flag_version)
            return True
        else:
            # Flag is for an older version — another update happened
            window.clearProperty(update_flag)
            log.info("Clone update flag outdated, checking version",
                     event="clone.update_flag_stale", addon_id=addon_id,
                     flag_version=update_flag_version,
                     parent_version=parent_version)

    clone_addon = xbmcaddon.Addon(addon_id)
    clone_version = clone_addon.getAddonInfo('version')
    clone_name = clone_addon.getAddonInfo('name')

    if clone_version == parent_version:
        return True

    log.warning("Clone out of date", event="clone.outdated",
                clone_version=clone_version, parent_version=parent_version,
                addon_id=addon_id)

    # Mandatory update prompt
    message = (lang(32709) + '\n' + lang(32710) + '\n\n' + lang(32711))
    confirmed = show_confirm_dialog(
        clone_name,
        message,
        yes_label=lang(32712),  # "Update"
        no_label=lang(32301),   # "Cancel"
    )

    if confirmed:
        # Use main addon's update_clone.py (latest update logic)
        parent_path = parent_addon.getAddonInfo('path')
        if not os.path.isdir(parent_path):
            log.error("Parent addon path invalid",
                      event="clone.update_fail", path=parent_path)
            return False
        update_script = os.path.join(parent_path, 'resources', 'update_clone.py')
        if not os.path.isfile(update_script):
            log.error("Update script not found",
                      event="clone.update_fail", path=update_script)
            return False
        xbmc.executebuiltin(
            f'RunScript({update_script},{parent_path},'
            f'{addon_path},{addon_id},{clone_name})'
        )

    return False  # Don't proceed — either updating or user cancelled


def _prepare_movie_pool(
    log,
    all_movies: List[Dict[str, Any]],
    advanced_settings: AdvancedSettings,
    storage: StorageManager,
    addon_id: str,
) -> Optional[Tuple[List[Dict[str, Any]], set]]:
    """Apply playlist pool filter and prepare resurface exclusions.

    Returns:
        (movies, exclude_ids) on success, or None if the pool is empty
        and the user was notified.
    """
    # Apply playlist pool filter (narrow universe before anything else)
    if advanced_settings.movie_pool_enabled and advanced_settings.movie_pool_path:
        pool_ids = extract_movie_ids_from_playlist(advanced_settings.movie_pool_path)
        if pool_ids:
            all_movies = filter_by_playlist_ids(all_movies, pool_ids)
            log.debug("Playlist pool applied", event="pool.filter",
                      pool_movie_count=len(pool_ids), remaining=len(all_movies))
            if not all_movies:
                show_confirm_dialog(
                    "No Movies",
                    "No movies in your library match the selected playlist.",
                    yes_label="OK", no_label="", addon_id=addon_id)
                return None
        else:
            log.warning("Playlist pool enabled but empty, using full library",
                        event="pool.fallback")

    # Prepare resurface exclusion (before wizard, so counts are accurate)
    exclude_ids: set = set()
    if advanced_settings.avoid_resurface:
        storage.validate_suggested(all_movies)
        resurface_hours = RESURFACE_WINDOWS.get(advanced_settings.resurface_window, 24)
        storage.prune_suggested(resurface_hours)
        exclude_ids = storage.get_suggested_ids()
        if exclude_ids:
            log.debug("Resurface exclusion prepared",
                      event="history.exclude_prepared",
                      exclude_count=len(exclude_ids),
                      window_hours=resurface_hours)
    else:
        storage.clear_suggested()

    return all_movies, exclude_ids


def _run_wizard_and_filter(
    log,
    all_movies: List[Dict[str, Any]],
    filter_settings: FilterSettings,
    advanced_settings: AdvancedSettings,
    storage: StorageManager,
    exclude_ids: set,
    addon_id: str,
) -> Optional[List[Dict[str, Any]]]:
    """Run filter wizard and apply filters.

    Returns:
        Filtered movie list, or None if cancelled or no results.
    """
    wizard = WizardFlow(_build_wizard_settings(filter_settings))
    if advanced_settings.remember_filters:
        wizard.load_last_answers(storage.load_last_filters())

    filter_config = _run_wizard(log, wizard, all_movies, addon_id,
                               show_counts=advanced_settings.show_counts,
                               cumulative_counts=advanced_settings.cumulative_counts,
                               exclude_ids=exclude_ids)
    if filter_config is None:
        log.info("Wizard cancelled", event="wizard.cancel")
        return None

    # Apply filters (include resurface exclusions)
    if exclude_ids:
        filter_config.exclude_ids = list(exclude_ids)
    filtered = apply_filters(all_movies, filter_config)
    if not filtered:
        if exclude_ids:
            log.info("All movies excluded by filters and resurface window",
                     event="history.exhausted",
                     total=len(all_movies), excluded=len(exclude_ids))
            show_confirm_dialog("No Results",
                                "All matching movies were recently suggested. "
                                "Try again later or adjust your re-suggestion window.",
                                yes_label="OK", no_label="", addon_id=addon_id)
        else:
            log.info("No movies after filtering", event="filter.no_results",
                     total=len(all_movies))
            show_confirm_dialog("No Results",
                                "No movies match your filters.\nTry relaxing your criteria.",
                                yes_label="OK", no_label="", addon_id=addon_id)
        return None

    log.debug("Filtered movies", count=len(filtered), total=len(all_movies))

    # Save wizard answers for next time
    if advanced_settings.remember_filters:
        storage.save_last_filters(wizard.get_answers())

    return filtered


def main(addon_id: str = ADDON_ID) -> None:
    """Entry point for the EasyMovie addon.

    Args:
        addon_id: Addon ID (different for clones).
    """
    import xbmc
    import xbmcaddon
    log = get_logger('default')
    addon = xbmcaddon.Addon(addon_id)

    # Check clone version before proceeding
    if addon_id != ADDON_ID:
        addon_path_str = addon.getAddonInfo('path')
        if not _check_clone_version(addon_id, addon_path_str):
            return

    version = addon.getAddonInfo('version')
    kodi_build = xbmc.getInfoLabel('System.BuildVersion')
    kodi_version = kodi_build.split()[0] if kodi_build else 'unknown'
    log.info("EasyMovie launched", event="launch.start",
             addon_id=addon_id, version=version, kodi=kodi_version)

    # 1. Load settings
    (primary_function, _theme, filter_settings, browse_settings,
     playlist_settings, set_settings, playback_settings,
     advanced_settings) = load_settings(addon_id if addon_id != ADDON_ID else None)

    log.debug("Settings", event="launch.settings",
              # Mode
              mode=primary_function,
              # Browse
              view_style=browse_settings.view_style,
              browse_count=browse_settings.result_count,
              browse_sort=browse_settings.sort_by,
              browse_sort_dir=browse_settings.sort_dir,
              # Playlist
              playlist_count=playlist_settings.movie_count,
              playlist_sort=playlist_settings.sort_by,
              prioritize_in_progress=playlist_settings.prioritize_in_progress,
              # Filters
              genre_mode=filter_settings.genre_mode,
              watched_mode=filter_settings.watched_mode,
              mpaa_mode=filter_settings.mpaa_mode,
              runtime_mode=filter_settings.runtime_mode,
              year_mode=filter_settings.year_mode,
              score_mode=filter_settings.score_mode,
              # Sets
              set_enabled=set_settings.enabled,
              continuation=set_settings.continuation_enabled,
              continuation_duration=set_settings.continuation_duration,
              # Playback
              check_in_progress=playback_settings.check_in_progress,
              show_info=playback_settings.show_info_when_playing,
              # Advanced
              pool_enabled=advanced_settings.movie_pool_enabled,
              avoid_resurface=advanced_settings.avoid_resurface,
              resurface_window=advanced_settings.resurface_window,
              remember_filters=advanced_settings.remember_filters,
              show_counts=advanced_settings.show_counts,
              cumulative_counts=advanced_settings.cumulative_counts)

    # 1b. Get storage for history (needed for resume check and later)
    storage = _get_storage(addon_id)

    # 2. Check for in-progress movie
    if playback_settings.check_in_progress:
        resumed = _check_in_progress(log, advanced_settings, addon_id, storage=storage)
        if resumed:
            return

    # 4. Determine mode
    mode = primary_function
    if mode == MODE_ASK:
        mode = _ask_mode(log, addon_id)
        if mode is None:
            return  # User cancelled

    log.info("Mode selected", event="launch.mode_selected",
             mode="browse" if mode == MODE_BROWSE else "playlist")

    # 5. Show processing notification
    if playback_settings.show_processing_notifications:
        notify(lang(32350))

    # 6. Query all movies (bulk, no art)
    with log_timing(log, "movie_query"):
        result = json_query(get_all_movies_query())
        all_movies = result.get("movies", [])

    if not all_movies:
        show_confirm_dialog("No Movies", "Your library has no movies.",
                            yes_label="OK", no_label="", addon_id=addon_id)
        return

    log.debug("Movies loaded", count=len(all_movies))

    # 6a. Clean up stale started entries (housekeeping)
    storage.validate_started(all_movies)

    # 6b–7. Apply pool filter and prepare resurface exclusions
    pool_result = _prepare_movie_pool(log, all_movies, advanced_settings,
                                      storage, addon_id)
    if pool_result is None:
        return
    all_movies, exclude_ids = pool_result

    # 8–10. Run wizard, apply filters, save answers
    filtered = _run_wizard_and_filter(log, all_movies, filter_settings,
                                      advanced_settings, storage,
                                      exclude_ids, addon_id)
    if filtered is None:
        return

    # 11. Show processing notification (wizard dismisses the earlier one)
    if playback_settings.show_processing_notifications:
        notify(lang(32350))

    # 12. Execute mode
    # Set window property so background service skips set-awareness check
    import xbmcgui
    window = xbmcgui.Window(10000)
    window.setProperty(PROP_PLAYLIST_RUNNING, 'true')
    try:
        if mode == MODE_BROWSE:
            _run_browse_mode(log, filtered, browse_settings, set_settings,
                             playback_settings, advanced_settings, storage, addon_id)
        else:
            _run_playlist_mode(log, filtered, playlist_settings, set_settings,
                               playback_settings, advanced_settings, storage, addon_id)
    finally:
        window.clearProperty(PROP_PLAYLIST_RUNNING)


def _check_in_progress(
    log, advanced_settings: AdvancedSettings, addon_id: str,
    storage: Optional['StorageManager'] = None,
) -> bool:
    """Check for in-progress movies started by EasyMovie and offer to resume."""
    from resources.lib.playback.player import play_movie, get_resume_info
    result = json_query(get_in_progress_movies_query())
    movies = result.get("movies", [])
    if not movies:
        return False

    # Only consider movies that EasyMovie started
    started_ids = storage.get_started_ids() if storage else set()
    if started_ids:
        movies = [m for m in movies if m.get("movieid", 0) in started_ids]
        if not movies:
            log.debug("In-progress movies found but none started by EasyMovie",
                      event="launch.resume_skip_foreign")
            return False
    else:
        # No tracking data yet — skip resume check entirely
        # (first run, or storage was cleared)
        log.debug("No EasyMovie-started movies tracked, skipping resume check",
                  event="launch.resume_skip_no_history")
        return False

    movie = movies[0]
    resume = get_resume_info(movie)
    if not resume:
        return False

    title = movie.get("title", "Unknown")
    remaining = resume["remaining_minutes"]

    log.info("In-progress movie found", event="launch.resume_offered",
             title=title, remaining_minutes=remaining)

    confirmed = show_confirm_dialog(
        "Resume Movie?",
        f"{title}\n{remaining} minutes remaining",
        yes_label="Resume",
        no_label="New Selection",
        addon_id=addon_id,
    )

    if confirmed:
        play_movie(movie, resume=True, storage=storage)
        return True
    return False


def _ask_mode(log, addon_id: str = ADDON_ID) -> Optional[int]:
    """Ask the user to choose Browse or Playlist mode."""
    import xbmcaddon
    addon_name = xbmcaddon.Addon(addon_id).getAddonInfo('name')
    result = show_confirm_dialog(
        heading=addon_name,
        message=lang(32320),  # "Choose Mode"
        yes_label=lang(32321),  # "Browse"
        no_label=lang(32322),  # "Playlist"
        addon_id=addon_id,
    )
    if result is None:
        return None  # User pressed back/escape
    return MODE_BROWSE if result else MODE_PLAYLIST


def _build_wizard_settings(filter_settings: FilterSettings) -> Dict[str, Any]:
    """Convert FilterSettings to the dict format WizardFlow expects."""
    return {
        "ignore_genre_mode": filter_settings.ignore_genre_mode,
        "ignore_genre_match_and": filter_settings.ignore_genre_match_and,
        "preset_ignore_genres": filter_settings.preset_ignore_genres,
        "genre_mode": filter_settings.genre_mode,
        "genre_match_and": filter_settings.genre_match_and,
        "preset_genres": filter_settings.preset_genres,
        "watched_mode": filter_settings.watched_mode,
        "watched_preset": filter_settings.watched_preset,
        "mpaa_mode": filter_settings.mpaa_mode,
        "preset_mpaa": filter_settings.preset_mpaa,
        "runtime_mode": filter_settings.runtime_mode,
        "runtime_min": filter_settings.runtime_min,
        "runtime_max": filter_settings.runtime_max,
        "year_mode": filter_settings.year_mode,
        "year_filter_type": filter_settings.year_filter_type,
        "year_from": filter_settings.year_from,
        "year_to": filter_settings.year_to,
        "year_recency": filter_settings.year_recency,
        "score_mode": filter_settings.score_mode,
        "min_score": filter_settings.min_score,
    }


def _run_multi_select_step(
    items: List[str],
    pool: list,
    value_fn: Callable[[Dict[str, Any]], List[str]],
    dialog_title: str,
    preselected: List[str],
    addon_id: str,
    show_counts: bool,
    fmt_fn: Callable[[str, int], str],
) -> Optional[List[str]]:
    """Run a multi-select filter step with optional counts.

    Args:
        items: The unique values to display (e.g. genre names).
        pool: Movie pool for counting.
        value_fn: Extracts matching values from a movie dict
                  (e.g. ``lambda m: m.get("genre", [])``).
        dialog_title: Heading for the select dialog.
        preselected: Previously selected values (for back-navigation).
        addon_id: Addon ID for theming.
        show_counts: Whether to append counts to labels.
        fmt_fn: Formats a label with its count.

    Returns:
        List of selected values, or None if cancelled.
    """
    if show_counts:
        counts: Dict[str, int] = {}
        for m in pool:
            for v in value_fn(m):
                counts[v] = counts.get(v, 0) + 1
        labels = [fmt_fn(item, counts.get(item, 0)) for item in items]
    else:
        labels = list(items)
    pre_indices = [i for i, item in enumerate(items) if item in preselected]
    result = show_select_dialog(dialog_title, labels,
                                multi_select=True, preselected=pre_indices,
                                addon_id=addon_id)
    if result is None:
        return None
    return [items[i] for i in result]


def _run_range_select_step(
    ranges: list,
    pool: list,
    match_fn: Callable[[Dict[str, Any], tuple], bool],
    label_fn: Callable[[tuple], str],
    dialog_title: str,
    addon_id: str,
    show_counts: bool,
    fmt_fn: Callable[[str, int], str],
) -> Optional[List[int]]:
    """Run a single-select range filter step with optional counts.

    Args:
        ranges: List of range tuples from constants.
        pool: Movie pool for counting.
        match_fn: Tests whether a movie matches a given range tuple.
        label_fn: Extracts the display label from a range tuple.
        dialog_title: Heading for the select dialog.
        addon_id: Addon ID for theming.
        show_counts: Whether to append counts to labels.
        fmt_fn: Formats a label with its count.

    Returns:
        Dialog result (list of selected indices), or None if cancelled.
    """
    items: List[str] = []
    for r in ranges:
        label = label_fn(r)
        if show_counts:
            count = sum(1 for m in pool if match_fn(m, r))
            items.append(fmt_fn(label, count))
        else:
            items.append(label)
    return show_select_dialog(dialog_title, items, multi_select=False,
                              addon_id=addon_id)


def _run_wizard(log, wizard: WizardFlow, all_movies: list,
                addon_id: str = ADDON_ID,
                show_counts: bool = True,
                cumulative_counts: bool = False,
                exclude_ids: Optional[set] = None) -> Optional[Any]:
    """Run the wizard flow, returning a FilterConfig or None if cancelled."""
    from resources.lib.data.filters import (
        extract_unique_genres, extract_unique_mpaa,
    )
    from resources.lib.constants import RUNTIME_RANGES, SCORE_RANGES

    from resources.lib.data.filters import apply_filters as _apply_filters

    def _count_pool() -> list:
        """Get the movie pool for counting — full or cumulative."""
        if not show_counts:
            return []
        if not cumulative_counts:
            if exclude_ids:
                return [m for m in all_movies
                        if m.get("movieid", 0) not in exclude_ids]
            return all_movies
        # Build partial filter config from completed steps only
        partial_config = wizard.build_partial_filter_config()
        if exclude_ids:
            partial_config.exclude_ids = list(exclude_ids)
        return _apply_filters(all_movies, partial_config, reason="cumulative_count")

    def _fmt(label: str, count: int) -> str:
        """Format a label with optional count."""
        if show_counts:
            return f"{label} ({count})"
        return label

    if wizard.is_complete:
        return wizard.build_filter_config()

    while not wizard.is_complete:
        step = wizard.current_step
        if step is None:
            break

        filter_type = step.filter_type
        answer = None

        if filter_type == "ignore_genre":
            genres = extract_unique_genres(all_movies)
            answer = _run_multi_select_step(
                genres, _count_pool(),
                lambda m: m.get("genre", []),
                lang(32204),
                wizard.get_answers().get("ignore_genre", []),
                addon_id, show_counts, _fmt,
            )
            if answer is None:
                if not wizard.go_back():
                    return None
                continue

        elif filter_type == "genre":
            genres = extract_unique_genres(all_movies)
            answer = _run_multi_select_step(
                genres, _count_pool(),
                lambda m: m.get("genre", []),
                "Select Genres",
                wizard.get_answers().get("genre", []),
                addon_id, show_counts, _fmt,
            )
            if answer is None:
                if not wizard.go_back():
                    return None
                continue

        elif filter_type == "watched":
            pool = _count_pool()
            if show_counts:
                unwatched = sum(1 for m in pool if m.get("playcount", 0) == 0)
                watched = len(pool) - unwatched
                items = [
                    _fmt("Unwatched only", unwatched),
                    _fmt("Watched only", watched),
                    _fmt("Both", len(pool)),
                ]
            else:
                items = ["Unwatched only", "Watched only", "Both"]
            result = show_select_dialog("Watched Status", items, multi_select=False,
                                        addon_id=addon_id)
            if result is None:
                if not wizard.go_back():
                    return None
                continue
            answer = result[0]  # 0=unwatched, 1=watched, 2=both

        elif filter_type == "mpaa":
            ratings = extract_unique_mpaa(all_movies)
            answer = _run_multi_select_step(
                ratings, _count_pool(),
                lambda m: [m.get("mpaa", "")] if m.get("mpaa", "") else [],
                "Select Age Ratings",
                wizard.get_answers().get("mpaa", []),
                addon_id, show_counts, _fmt,
            )
            if answer is None:
                if not wizard.go_back():
                    return None
                continue

        elif filter_type == "runtime":
            result = _run_range_select_step(
                RUNTIME_RANGES, _count_pool(),
                lambda m, r: ((r[0] == 0 or m.get("runtime", 0) >= r[0] * 60)
                              and (r[1] == 0 or m.get("runtime", 0) <= r[1] * 60)),
                lambda r: r[2],
                "Select Runtime", addon_id, show_counts, _fmt,
            )
            if result is None:
                if not wizard.go_back():
                    return None
                continue
            idx = result[0]
            rt_min, rt_max, _ = RUNTIME_RANGES[idx]
            answer = {"min": rt_min, "max": rt_max}

        elif filter_type == "year":
            # Combined recency + decade picker
            from resources.lib.data.filters import extract_decade_buckets
            from resources.lib.constants import RECENCY_RANGES
            import datetime

            current_year = datetime.datetime.now().year
            pool = _count_pool()
            buckets = extract_decade_buckets(pool if show_counts else all_movies)

            # Build items: recency, then header + decades, then "Any year"
            items = []
            header_indices = set()

            for years_ago, label_id in RECENCY_RANGES:
                if show_counts:
                    cutoff_year = current_year - years_ago
                    rcount = sum(1 for m in pool if m.get("year", 0) >= cutoff_year)
                    items.append(_fmt(lang(label_id), rcount))
                else:
                    items.append(lang(label_id))

            # "— By decade —" group header (only if there are decade buckets)
            if buckets:
                header_indices.add(len(items))
                items.append(lang(32206))

            for _, count, label in buckets:
                items.append(_fmt(label, count) if show_counts else label)
            items.append(_fmt(lang(32220), len(pool)) if show_counts
                         else lang(32220))

            result = show_select_dialog(lang(32202), items, multi_select=False,
                                        addon_id=addon_id,
                                        headers=header_indices)
            if result is None:
                if not wizard.go_back():
                    return None
                continue
            if not result:
                answer = {"from": 0, "to": 0}  # No filter, same as "Any year"
                wizard.set_answer(filter_type, answer)
                log.debug("Wizard answer", event="wizard.answer",
                          filter_type=filter_type, answer=answer)
                if not wizard.advance():
                    break
                continue

            # Map selected index back to data index (skip headers)
            idx = result[0]
            headers_before = sum(1 for h in header_indices if h < idx)
            data_idx = idx - headers_before

            recency_count = len(RECENCY_RANGES)
            if data_idx < recency_count:
                # Recency selection
                years_ago = RECENCY_RANGES[data_idx][0]
                answer = {"from": current_year - years_ago, "to": 0}
            elif data_idx < recency_count + len(buckets):
                # Decade selection
                bucket_idx = data_idx - recency_count
                decade_start, _, _ = buckets[bucket_idx]
                answer = {"from": decade_start, "to": decade_start + 9}
            else:
                answer = {"from": 0, "to": 0}

        elif filter_type == "score":
            result = _run_range_select_step(
                SCORE_RANGES, _count_pool(),
                lambda m, r: m.get("rating", 0.0) * 10 >= r[0],
                lambda r: r[1],
                "Select Score", addon_id, show_counts, _fmt,
            )
            if result is None:
                if not wizard.go_back():
                    return None
                continue
            if not result:
                answer = 0  # No filter, same as "Any score"
                wizard.set_answer(filter_type, answer)
                log.debug("Wizard answer", event="wizard.answer",
                          filter_type=filter_type, answer=answer)
                if not wizard.advance():
                    break
                continue
            idx = result[0]
            answer = SCORE_RANGES[idx][0]

        wizard.set_answer(filter_type, answer)
        log.debug("Wizard answer", event="wizard.answer",
                  filter_type=filter_type, answer=answer)
        if not wizard.advance():
            break  # Wizard complete

    config = wizard.build_filter_config()
    log.debug("Wizard complete", event="wizard.complete")
    return config


def _get_storage(addon_id: str) -> StorageManager:
    """Get the storage manager for the addon."""
    storage_dir = xbmcvfs.translatePath(
        f"special://profile/addon_data/{addon_id}/"
    )
    import os
    os.makedirs(storage_dir, exist_ok=True)
    return StorageManager(os.path.join(storage_dir, "easymovie_data.json"))


def _load_set_details(
    movies: List[Dict[str, Any]]
) -> Dict[int, Dict[str, Any]]:
    """Load movie set details for all set-member movies."""
    _log = get_logger('data')
    set_ids = {m.get("setid", 0) for m in movies if m.get("setid", 0)}
    set_cache: Dict[int, Dict[str, Any]] = {}
    with log_timing(_log, "load_set_details", set_count=len(set_ids)):
        for set_id in set_ids:
            result = json_query(get_movie_set_details_query(set_id))
            if result:
                # Unwrap: json_query returns {"setdetails": {...}}
                set_cache[set_id] = result.get("setdetails", result)
    # Remove sets with only 1 movie in library (not useful for set features)
    set_cache = {
        sid: details for sid, details in set_cache.items()
        if len(details.get("movies", [])) >= 2
    }
    return set_cache


def _load_art_for_movies(
    movies: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Load art and plot for a list of movies via individual detail queries."""
    if not movies:
        return movies
    _log = get_logger('data')
    enriched: List[Dict[str, Any]] = []
    with log_timing(_log, "load_art_for_movies", movie_count=len(movies)):
        for movie in movies:
            movie_id = movie.get("movieid", 0)
            if not movie_id:
                enriched.append(movie)
                continue
            result = json_query(get_movie_details_with_art_query(movie_id))
            details = result.get("moviedetails")
            if details:
                enriched.append(details)
            else:
                enriched.append(movie)
    return enriched


def _run_browse_mode(
    log,
    filtered: List[Dict[str, Any]],
    browse_settings: BrowseSettings,
    set_settings: SetSettings,
    playback_settings: PlaybackSettings,
    advanced_settings: AdvancedSettings,
    storage: StorageManager,
    addon_id: str,
) -> None:
    """Run the browse mode loop with Re-roll support."""
    from resources.lib.playback.player import play_movie
    from resources.lib.playback.playlist_builder import build_and_play_playlist
    while True:
        # Exclude previously suggested from this session's pool
        if advanced_settings.avoid_resurface:
            suggested_ids = storage.get_suggested_ids()
            available = [m for m in filtered if m.get("movieid", 0) not in suggested_ids]
            if not available:
                log.info("All filtered movies exhausted, resetting pool",
                         event="ui.pool_reset", total=len(filtered))
                available = filtered
        else:
            available = filtered

        # Select and sort
        results = select_and_sort_results(
            available, browse_settings.result_count,
            browse_settings.sort_by, browse_settings.sort_dir,
        )

        # Apply movie set substitutions
        if set_settings.enabled:
            set_cache = _load_set_details(results)
            results = apply_set_substitutions(results, set_cache)

        # Load art for display (re-fetches full details including set/setid)
        results = _load_art_for_movies(results)

        # Strip set info from single-movie sets after art loading
        if set_settings.enabled:
            valid_set_ids = set(set_cache.keys())
            for movie in results:
                if movie.get("setid", 0) and movie["setid"] not in valid_set_ids:
                    movie["set"] = ""
                    movie["setid"] = 0

        # Record as suggested (only when resurface avoidance is on)
        if advanced_settings.avoid_resurface:
            for movie in results:
                storage.add_suggested(movie.get("movieid", 0), movie.get("title", ""))

        # Show browse window
        titles = [m.get("title", "") for m in results]
        log.debug("Presenting movies", event="browse.present",
                  count=len(results), pool=len(available), titles=titles)
        result = show_browse_window(results, browse_settings.view_style, addon_id)

        if result == RESULT_REROLL:
            log.info("Re-rolling", event="ui.reroll")
            if playback_settings.show_processing_notifications:
                notify(lang(32350))
            continue
        elif result == RESULT_SURPRISE:
            if not results:
                continue
            movie = random.choice(results)
            log.info("Surprise Me", event="ui.surprise",
                     title=movie.get("title", ""))
            play_movie(movie, storage=storage)
            break
        elif isinstance(result, dict) and result.get("__play_set__"):
            # Play Full Set from context menu
            movie = result["movie"]
            set_id = movie.get("setid", 0)
            if set_id:
                raw = json_query(get_movie_set_details_query(set_id))
                set_details = raw.get("setdetails", raw) if raw else {}
                set_movies = set_details.get("movies", [])
                if set_movies:
                    log.info("Playing full set", event="playlist.play_set",
                             set_name=movie.get("set", ""),
                             movie_count=len(set_movies))
                    build_and_play_playlist(set_movies, storage=storage)
                    break
        elif result is not None:
            log.info("Playing movie", event="playback.start",
                     title=result.get("title", ""),
                     movieid=result.get("movieid", 0))
            play_movie(result, storage=storage)
            break
        else:
            break  # User closed


def _run_playlist_mode(
    log,
    filtered: List[Dict[str, Any]],
    playlist_settings: PlaylistSettings,
    set_settings: SetSettings,
    playback_settings: PlaybackSettings,
    advanced_settings: AdvancedSettings,
    storage: StorageManager,
    addon_id: str,
) -> None:
    """Run playlist mode."""
    from resources.lib.playback.playlist_builder import build_and_play_playlist
    from resources.lib.playback.playback_monitor import PlaybackMonitor
    # Select and sort
    results = select_and_sort_results(
        filtered, playlist_settings.movie_count,
        playlist_settings.sort_by, playlist_settings.sort_dir,
    )

    # Apply movie set substitutions
    if set_settings.enabled:
        set_cache = _load_set_details(results)
        results = apply_set_substitutions(results, set_cache)
        # Strip set info from movies whose sets were filtered out
        valid_set_ids = set(set_cache.keys())
        for movie in results:
            if movie.get("setid", 0) and movie["setid"] not in valid_set_ids:
                movie["set"] = ""
                movie["setid"] = 0

    # Record as suggested (only when resurface avoidance is on)
    if advanced_settings.avoid_resurface:
        for movie in results:
            storage.add_suggested(movie.get("movieid", 0), movie.get("title", ""))

    # Build and play playlist
    success = build_and_play_playlist(
        results,
        show_notifications=playback_settings.show_processing_notifications,
        prioritize_in_progress=playlist_settings.prioritize_in_progress,
        resume_from_position=playlist_settings.resume_from_position,
        storage=storage,
    )

    if not success:
        return

    # Start playback monitor for set continuation
    if set_settings.enabled and set_settings.continuation_enabled:
        set_cache = _load_set_details(results)
        movies_by_id = {m.get("movieid", 0): m for m in results}
        # Monitor runs as part of xbmc.Player — Kodi calls its callbacks.
        # Must keep reference to prevent GC during playback session.
        monitor = PlaybackMonitor(
            set_cache=set_cache,
            movies=movies_by_id,
            continuation_duration=set_settings.continuation_duration,
            continuation_default=set_settings.continuation_default,
            addon_id=addon_id,
        )
        _active_monitors.append(monitor)


def _reopen_settings(addon_id: str) -> None:
    """Force-close dialogs and reopen settings to show updated values.

    Kodi's settings dialog caches values in memory. After a selector
    changes settings via setSetting(), we must close and reopen to
    pick up the new values.
    """
    import xbmc
    xbmc.executebuiltin('Dialog.Close(all,true)')
    xbmc.executebuiltin(
        f'AlarmClock(EasyMovieSettings,Addon.OpenSettings({addon_id}),00:01,silent)'
    )


def _handle_entry_args(addon_id: str) -> bool:
    """Handle command-line arguments for special entry points.

    Returns True if the args were handled (caller should exit).
    """
    if len(sys.argv) < 2:
        return False

    action = sys.argv[1]

    if action == 'selector':
        from resources.selector import main as selector_main
        selector_main()
        _reopen_settings(addon_id)
        return True
    elif action == 'clone':
        from resources.clone import create_clone
        create_clone()
        return True
    elif action == 'dialog_preview':
        from resources import dialog_preview
        override = sys.argv[2] if len(sys.argv) > 2 else None
        dialog_preview.Main(override)
        return True
    elif action == 'set_icon':
        from resources.lib.utils import get_addon
        import xbmcvfs as _xbmcvfs
        import xbmcgui
        log = get_logger('default')
        addon = get_addon(addon_id)
        addon_path = addon.getAddonInfo('path')
        icons_dir = os.path.join(addon_path, 'resources', 'icons')
        icon_names = ["Golden Hour", "Ultraviolet", "Ember", "Nightfall", "Browse..."]
        icon_files = [
            "icon-golden-hour.png", "icon-ultraviolet.png",
            "icon-ember.png", "icon-nightfall.png",
        ]
        from resources.lib.constants import CUSTOM_ICON_BACKUP
        addon_data = _xbmcvfs.translatePath(
            f'special://profile/addon_data/{addon_id}/'
        )
        backup_path = os.path.join(addon_data, CUSTOM_ICON_BACKUP)
        result = show_select_dialog(
            heading="Choose Icon",
            items=icon_names,
            multi_select=False,
            addon_id=addon_id,
        )
        if result is not None:
            idx = result[0]
            dst = os.path.join(addon_path, 'icon.png')
            if idx < len(icon_files):
                src = os.path.join(icons_dir, icon_files[idx])
                ok = _xbmcvfs.copy(src, dst)
                if ok:
                    addon.setSetting('icon_choice',
                                     f'built-in:{icon_files[idx]}')
                    _xbmcvfs.copy(src, backup_path)
                log.info("Icon set" if ok else "Icon set failed",
                         event="icon.set", source=src, target=dst, success=ok)
            else:
                dialog = xbmcgui.Dialog()
                image = dialog.browse(2, "Select Icon", 'files', '.png|.jpg|.jpeg')
                if image:
                    ok = _xbmcvfs.copy(cast(str, image), dst)
                    if ok:
                        addon.setSetting('icon_choice', 'custom')
                        _xbmcvfs.copy(cast(str, image), backup_path)
                    log.info("Custom icon set" if ok else "Custom icon set failed",
                             event="icon.set", source=cast(str, image),
                             target=dst, success=ok)
        invalidate_icon_cache(addon_id)
        _reopen_settings(addon_id)
        return True
    elif action == 'reset_icon':
        from resources.lib.utils import get_addon
        from resources.lib.constants import CUSTOM_ICON_BACKUP
        import xbmcvfs as _xbmcvfs
        addon = get_addon(addon_id)
        addon_path = addon.getAddonInfo('path')
        default_icon = os.path.join(addon_path, 'icon_default.png')
        icon_path = os.path.join(addon_path, 'icon.png')
        if _xbmcvfs.exists(default_icon):
            _xbmcvfs.copy(default_icon, icon_path)
        addon.setSetting('icon_choice', '')
        addon_data = _xbmcvfs.translatePath(
            f'special://profile/addon_data/{addon_id}/'
        )
        backup_path = os.path.join(addon_data, CUSTOM_ICON_BACKUP)
        if _xbmcvfs.exists(backup_path):
            _xbmcvfs.delete(backup_path)
        invalidate_icon_cache(addon_id)
        _reopen_settings(addon_id)
        return True

    return False
