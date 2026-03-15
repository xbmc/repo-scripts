#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Original work Copyright (C) 2013 KODeKarnage
#  Modified work Copyright (C) 2024-2026 Rouzax
#
#  SPDX-License-Identifier: GPL-3.0-or-later
#  See LICENSE.txt for more information.
#

"""
EasyTV Settings Management.

Handles loading, persisting, and initializing addon settings for the service.
Includes show selection storage with ID stability protection - when Kodi 
reassigns show IDs during library rebuilds, settings are automatically
migrated to the new IDs via title matching.

Logging:
    Module: settings
    Events:
        - settings.load (INFO): Settings loaded with full configuration
        - settings.migrate (INFO): Settings migrated from old [id] to new {id: title} format
        - settings.id_shift (INFO): Show ID changed, migrated to new ID via title match
        - settings.validation_complete (INFO): Settings validation summary
        - settings.orphan_cleanup (INFO): Orphaned show IDs removed from settings
"""
from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple, TYPE_CHECKING

import xbmcaddon
import xbmcgui

from resources.lib.constants import KODI_HOME_WINDOW_ID
from resources.lib.utils import (
    get_addon,
    json_query,
    lang,
    get_logger,
)
from resources.lib.data.queries import build_show_details_query, get_all_shows_query

if TYPE_CHECKING:
    from resources.lib.utils import StructuredLogger


# Module-level logger (initialized lazily)
_log: Optional[StructuredLogger] = None


def _get_log() -> StructuredLogger:
    """Get or create the module logger."""
    global _log
    if _log is None:
        _log = get_logger('settings')
    return _log


def _parse_show_setting(raw_value: str) -> Tuple[Dict[str, str], bool]:
    """
    Parse a show setting value, handling both old and new formats.
    
    Old format: "[367, 42]" - list of IDs
    New format: "{'367': 'The Alienist', '42': 'Breaking Bad'}" - dict of ID to title
    
    Args:
        raw_value: The raw setting string from addon.getSetting()
    
    Returns:
        Tuple of (parsed_dict, needs_migration)
        - For new format: ({"367": "Title"}, False)
        - For old format: ({"367": "", "42": ""}, True) - empty titles = needs lookup
        - For invalid/empty: ({}, False)
    """
    if not raw_value or raw_value in ('', '[]', '{}', 'none'):
        return {}, False
    
    try:
        parsed = ast.literal_eval(raw_value)
    except (ValueError, SyntaxError):
        return {}, False
    
    if isinstance(parsed, dict):
        # New format - ensure all keys are strings
        return {str(k): v for k, v in parsed.items()}, False
    
    if isinstance(parsed, list):
        # Old format - convert to dict with empty titles (needs migration)
        return {str(show_id): '' for show_id in parsed}, True
    
    return {}, False


def _migrate_show_setting(
    setting_name: str,
    show_dict: Dict[str, str],
    addon: xbmcaddon.Addon,
    logger: StructuredLogger
) -> Dict[str, str]:
    """
    Migrate old format show setting by looking up current titles.
    
    Queries the Kodi library for all shows and populates the title values
    for each stored show ID. Shows not found in library are removed.
    
    Args:
        setting_name: Name of the setting being migrated ('random_order_shows' or 'selection')
        show_dict: Dict with string IDs as keys, empty strings as values
        addon: The addon instance for saving migrated setting
        logger: Logger instance
    
    Returns:
        Migrated dict with titles populated, orphaned IDs removed
    """
    if not show_dict:
        return {}
    
    # Query library for all shows
    result = json_query(get_all_shows_query(), True)
    shows = result.get('tvshows', [])
    
    # Build ID → title lookup
    id_to_title = {str(show['tvshowid']): show['title'] for show in shows}
    
    # Migrate: populate titles, remove orphaned IDs
    migrated = {}
    orphaned = []
    
    for show_id in show_dict:
        if show_id in id_to_title:
            migrated[show_id] = id_to_title[show_id]
        else:
            orphaned.append(show_id)
    
    # Save migrated format
    addon.setSetting(setting_name, str(migrated))
    
    logger.info(
        "Migrated show setting to new format",
        event="settings.migrate",
        setting=setting_name,
        migrated_count=len(migrated),
        orphaned_count=len(orphaned),
        orphaned_ids=orphaned if orphaned else None
    )
    
    return migrated


def _validate_and_migrate_shows(
    setting_name: str,
    show_dict: Dict[str, str],
    id_to_title: Dict[int, str],
    title_to_id: Dict[str, int],
    current_show_ids: set,
    logger: StructuredLogger
) -> Tuple[Dict[str, str], int, int, int]:
    """
    Validate stored shows against current library, detecting and fixing ID shifts.
    
    For each stored show:
    1. If ID exists and title matches: keep as-is
    2. If ID exists but title differs: ID shifted, search by stored title for new ID
    3. If ID doesn't exist: search by stored title for new ID
    4. If title not found in library: show was deleted, remove as orphan
    
    Args:
        setting_name: Name of setting for logging
        show_dict: Dict of {str_id: title} from stored setting
        id_to_title: Current library mapping {int_id: title}
        title_to_id: Reverse lookup {title: int_id} for migration
        current_show_ids: Set of valid show IDs in library
        logger: Logger instance
    
    Returns:
        Tuple of (validated_dict, orphaned_count, migrated_count, unchanged_count)
    """
    valid_dict = {}
    orphaned_count = 0
    migrated_count = 0
    unchanged_count = 0
    
    for str_id, stored_title in show_dict.items():
        int_id = int(str_id)
        current_title = id_to_title.get(int_id)
        
        if int_id in current_show_ids:
            # ID exists in library
            if not stored_title:
                # Old format migration - no stored title to compare
                valid_dict[str_id] = current_title
                unchanged_count += 1
            elif current_title == stored_title:
                # Title matches - no shift, keep as-is
                valid_dict[str_id] = current_title
                unchanged_count += 1
            else:
                # Title mismatch - ID now points to different show!
                # Search for stored title to find its new ID
                new_id = title_to_id.get(stored_title)
                if new_id is not None:
                    # Found the show with new ID - migrate
                    new_str_id = str(new_id)
                    if new_str_id not in valid_dict:  # Avoid duplicates
                        valid_dict[new_str_id] = stored_title
                        migrated_count += 1
                        logger.info(
                            "Show ID shifted, migrated to new ID",
                            event="settings.id_shift",
                            setting=setting_name,
                            show_title=stored_title,
                            old_id=int_id,
                            new_id=new_id
                        )
                else:
                    # Stored title not found - show was renamed or deleted
                    orphaned_count += 1
                    logger.info(
                        "Show title not found after ID shift, removing",
                        event="settings.orphan_cleanup",
                        setting=setting_name,
                        show_title=stored_title,
                        old_id=int_id
                    )
        else:
            # ID doesn't exist in current_show_ids (e.g. fully watched
            # shows filtered out by unwatched query) - search by title
            if stored_title:
                new_id = title_to_id.get(stored_title)
                if new_id is not None:
                    new_str_id = str(new_id)
                    if new_id == int_id:
                        # Same ID - show exists but wasn't in current_show_ids
                        # (e.g. fully watched). Not a shift, keep as-is.
                        valid_dict[str_id] = stored_title
                        unchanged_count += 1
                    elif new_str_id not in valid_dict:  # Avoid duplicates
                        # Different ID - actual shift, migrate
                        valid_dict[new_str_id] = stored_title
                        migrated_count += 1
                        logger.info(
                            "Show ID shifted, migrated to new ID",
                            event="settings.id_shift",
                            setting=setting_name,
                            show_title=stored_title,
                            old_id=int_id,
                            new_id=new_id
                        )
                else:
                    # Title not found - show deleted from library
                    orphaned_count += 1
                    logger.debug(
                        "Show not found in library, removing",
                        setting=setting_name,
                        show_title=stored_title,
                        old_id=int_id
                    )
            else:
                # No title stored (old format) and ID gone - orphan
                orphaned_count += 1
                logger.debug(
                    "Show ID not found in library, removing",
                    setting=setting_name,
                    old_id=int_id
                )
    
    return valid_dict, orphaned_count, migrated_count, unchanged_count


def validate_show_selections(
    current_show_ids: set,
    addon: Optional[xbmcaddon.Addon] = None,
    logger: Optional[StructuredLogger] = None
) -> Tuple[int, int]:
    """
    Validate show selections and handle ID shifts via title matching.
    
    Checks both 'random_order_shows' and 'selection' settings for:
    1. Show IDs that no longer exist (orphans)
    2. Show IDs that now point to different shows (ID shifts)
    
    When an ID shift is detected (stored title doesn't match current title
    for that ID), searches for the show by its stored title and migrates
    to the new ID. This protects against Kodi's ID reassignment behavior
    during library rebuilds.
    
    Args:
        current_show_ids: Set of valid show IDs currently in the library
        addon: The addon instance. If None, uses get_addon().
        logger: Logger instance to use. If None, uses module logger.
    
    Returns:
        Tuple of (random_order_removed_count, selection_removed_count)
    """
    log = logger or _get_log()
    
    if addon is None:
        addon = get_addon()
    
    # Build lookups from current library
    result = json_query(get_all_shows_query(), True)
    shows = result.get('tvshows', [])
    id_to_title = {show['tvshowid']: show['title'] for show in shows}
    title_to_id = {show['title']: show['tvshowid'] for show in shows}
    
    random_order_removed = 0
    selection_removed = 0
    settings_changed = False
    
    # Validate random_order_shows
    show_dict, needs_migration = _parse_show_setting(addon.getSetting('random_order_shows'))
    if show_dict:
        valid_dict, orphaned, migrated, unchanged = _validate_and_migrate_shows(
            'random_order_shows', show_dict, id_to_title, title_to_id,
            current_show_ids, log
        )
        random_order_removed = orphaned
        
        # Save if anything changed
        if orphaned > 0 or migrated > 0 or needs_migration:
            addon.setSetting('random_order_shows', str(valid_dict))
            settings_changed = True
            
            if orphaned > 0:
                log.info(
                    "Cleaned random_order_shows",
                    event="settings.validation_complete",
                    setting="random_order_shows",
                    orphaned=orphaned,
                    migrated=migrated,
                    kept=unchanged
                )
            elif migrated > 0:
                log.info(
                    "Migrated random_order_shows after ID shifts",
                    event="settings.validation_complete",
                    setting="random_order_shows",
                    migrated=migrated,
                    kept=unchanged
                )
            elif needs_migration:
                log.info(
                    "Migrated random_order_shows to new format",
                    event="settings.migrate",
                    setting="random_order_shows",
                    count=len(valid_dict)
                )
    
    # Validate selection (usersel)
    show_dict, needs_migration = _parse_show_setting(addon.getSetting('selection'))
    if show_dict:
        valid_dict, orphaned, migrated, unchanged = _validate_and_migrate_shows(
            'selection', show_dict, id_to_title, title_to_id,
            current_show_ids, log
        )
        selection_removed = orphaned
        
        # Save if anything changed
        if orphaned > 0 or migrated > 0 or needs_migration:
            addon.setSetting('selection', str(valid_dict))
            settings_changed = True
            
            if orphaned > 0:
                log.info(
                    "Cleaned selection",
                    event="settings.validation_complete",
                    setting="selection",
                    orphaned=orphaned,
                    migrated=migrated,
                    kept=unchanged
                )
            elif migrated > 0:
                log.info(
                    "Migrated selection after ID shifts",
                    event="settings.validation_complete",
                    setting="selection",
                    migrated=migrated,
                    kept=unchanged
                )
            elif needs_migration:
                log.info(
                    "Migrated selection to new format",
                    event="settings.migrate",
                    setting="selection",
                    count=len(valid_dict)
                )
    
    # Update display settings if anything changed
    if settings_changed:
        init_display_settings(addon)
    
    return (random_order_removed, selection_removed)


# Type alias for callback functions used by load_settings
# Note: Use List instead of list for Python 3.8 compatibility (Kodi uses 3.8)
RandomOrderCallback = Callable[[int], None]
StoreNextEpCallback = Callable[[int, int, List, List, int, int], None]
RemoveShowCallback = Callable[[int], None]
UpdatePlaylistCallback = Callable[[int], None]


@dataclass
class ServiceSettings:
    """
    Container for all service settings.
    
    Groups all settings loaded from the addon configuration into a single
    object for easier passing between components.
    """
    # Notification and display
    playlist_notifications: bool = True
    
    # Playback behavior - separate TV and movie resume settings
    resume_partials_tv: bool = True
    resume_partials_movies: bool = True
    nextprompt: bool = False
    nextprompt_in_playlist: bool = False
    previous_episode_check: bool = False
    
    # Prompt configuration
    promptduration: int = 0
    promptdefaultaction: int = 0
    
    # Playlist continuation
    playlist_continuation: bool = False
    playlist_continuation_duration: int = 20
    playlist_continuation_default_action: int = 0
    
    # Feature flags
    startup: bool = False
    maintainsmartplaylist: bool = False  # Legacy - kept for Phase 4 migration
    
    # Smart playlist export settings
    # Episode playlists default True for migration compatibility (existing users had this enabled)
    # TVShow playlists default False (new feature, opt-in)
    playlist_export_episodes: bool = True
    playlist_export_tvshows: bool = False
    smartplaylist_filter_enabled: bool = False
    
    # Positioned specials - include TVDB-positioned specials in watch order
    include_positioned_specials: bool = False
    
    # Show filter playlist path (used for smart playlist filtering)
    user_playlist_path: str = 'none'
    
    # Random order shows (list of show IDs)
    random_order_shows: list[int] = field(default_factory=list)
    
    # Manual show selection (list of show IDs for usersel filter)
    selection: list[int] = field(default_factory=list)
    
    # Logging
    keep_logs: bool = False


def init_display_settings(addon: Optional[xbmcaddon.Addon] = None) -> None:
    """
    Initialize display settings with current stored values.
    
    Called on first run and on settings reload to ensure display settings 
    show correct values when the settings dialog is opened.
    
    Args:
        addon: The addon instance. If None, uses get_addon().
    """
    log = _get_log()
    
    if addon is None:
        addon = get_addon()
    
    setting = addon.getSetting
    
    # Random order shows display - handles both old and new formats
    show_dict, _ = _parse_show_setting(setting('random_order_shows'))
    count = len(show_dict)
    display_text = lang(32569) % count if count > 0 else lang(32571)
    addon.setSetting(id="random_order_shows_display", value=display_text)
    log.debug("Init random_order_shows_display", value=display_text, count=count)
    
    # Selection (usersel) display - handles both old and new formats
    show_dict, _ = _parse_show_setting(setting('selection'))
    count = len(show_dict)
    display_text = lang(32569) % count if count > 0 else lang(32571)
    addon.setSetting(id="selection_display", value=display_text)
    log.debug("Init selection_display", value=display_text, count=count)
    
    # Playlist file display
    playlist_path = setting('user_playlist_path')
    if playlist_path and playlist_path != 'none' and playlist_path != 'empty':
        filename = os.path.basename(playlist_path)
        if filename.endswith('.xsp'):
            filename = filename[:-4]
        display_text = filename
    else:
        display_text = lang(32570)
    addon.setSetting(id="playlist_file_display", value=display_text)
    # Mirror to Advanced settings section
    addon.setSetting(id="smartplaylist_filter_display", value=display_text)
    log.debug("Init playlist_file_display", value=display_text, path=playlist_path)
    
    # Movie playlist file display
    movie_playlist_path = setting('movie_user_playlist_path')
    if movie_playlist_path and movie_playlist_path != 'none' and movie_playlist_path != 'empty':
        filename = os.path.basename(movie_playlist_path)
        if filename.endswith('.xsp'):
            filename = filename[:-4]
        display_text = filename
    else:
        display_text = lang(32603)  # "All movies"
    addon.setSetting(id="movie_playlist_file_display", value=display_text)
    log.debug("Init movie_playlist_file_display", value=display_text, path=movie_playlist_path)


def load_settings(
    firstrun: bool = False,
    window: Optional[xbmcgui.Window] = None,
    addon: Optional[xbmcaddon.Addon] = None,
    logger: Optional[StructuredLogger] = None,
    # Callbacks for Main class interactions
    on_add_random_show: Optional[RandomOrderCallback] = None,
    on_reshuffle_random_shows: Optional[Callable[[list[int]], None]] = None,
    on_store_next_ep: Optional[StoreNextEpCallback] = None,
    on_remove_show: Optional[RemoveShowCallback] = None,
    on_update_smartplaylist: Optional[UpdatePlaylistCallback] = None,
    shows_with_next_episodes: Optional[list[int]] = None,
) -> ServiceSettings:
    """
    Load all settings from the addon configuration.
    
    On first run, also initializes display settings. On subsequent calls,
    handles changes to random_order_shows by calling the appropriate callbacks.
    
    Args:
        firstrun: True if this is the initial load at service startup.
        window: The Kodi home window instance. If None, creates one.
        addon: The addon instance. If None, uses get_addon().
        logger: Logger instance to use. If None, uses module logger.
        on_add_random_show: Callback when a show is added to random order.
        on_reshuffle_random_shows: Callback to reshuffle random shows.
        on_store_next_ep: Callback to store next episode for a show.
        on_remove_show: Callback to remove a show from tracking.
        on_update_smartplaylist: Callback to update smart playlists.
        shows_with_next_episodes: Current list of tracked shows.
    
    Returns:
        ServiceSettings containing all loaded settings.
    """
    log = logger or _get_log()
    
    if window is None:
        window = xbmcgui.Window(KODI_HOME_WINDOW_ID)
    
    # For settings reload (not firstrun), get a fresh addon instance
    # to ensure we read the updated values from Kodi
    if addon is None or not firstrun:
        addon = xbmcaddon.Addon()
    
    setting = addon.getSetting
    
    # Load all settings
    settings = ServiceSettings(
        playlist_notifications=setting("notify") == 'true',
        resume_partials_tv=setting('resume_partials_tv') == 'true',
        resume_partials_movies=setting('resume_partials_movies') == 'true',
        keep_logs=setting('logging') == 'true',
        nextprompt=setting('nextprompt') == 'true',
        nextprompt_in_playlist=setting('nextprompt_in_playlist') == 'true',
        startup=setting('startup') == 'true',
        promptduration=int(float(setting('promptduration'))),
        previous_episode_check=setting('previous_episode_check') == 'true',
        promptdefaultaction=int(float(setting('promptdefaultaction'))),
        playlist_continuation=setting('playlist_continuation') == 'true',
        playlist_continuation_duration=int(float(setting('playlist_continuation_duration'))),
        playlist_continuation_default_action=int(float(setting('playlist_continuation_default_action'))),
    )
    
    # Handle maintainsmartplaylist setting (legacy)
    # Note: We only parse the setting here. The actual playlist updates
    # are triggered in daemon._on_settings_changed() AFTER self._settings
    # is updated, to avoid race condition where _update_smartplaylist
    # checks self._settings.maintainsmartplaylist (the old value).
    settings.maintainsmartplaylist = setting('maintainsmartplaylist') == 'true'
    
    # New playlist export settings with migration from old maintainsmartplaylist
    episode_setting = setting('playlist_export_episodes')
    tvshow_setting = setting('playlist_export_tvshows')
    old_maintain_setting = setting('maintainsmartplaylist')
    
    # Migration logic: if old setting exists but new settings don't, migrate
    # This handles upgrade from versions that used maintainsmartplaylist
    if episode_setting == '' and old_maintain_setting != '':
        # Old setting exists, new one doesn't - perform migration
        if old_maintain_setting == 'true':
            # User had playlists enabled - enable Episode playlists
            settings.playlist_export_episodes = True
            addon.setSetting('playlist_export_episodes', 'true')
            log.info(
                "Migrated maintainsmartplaylist to playlist_export_episodes",
                event="settings.migrate",
                old_value=True,
                new_episode_value=True
            )
        else:
            # User had playlists disabled - keep disabled
            settings.playlist_export_episodes = False
            addon.setSetting('playlist_export_episodes', 'false')
            log.info(
                "Migrated maintainsmartplaylist to playlist_export_episodes",
                event="settings.migrate",
                old_value=False,
                new_episode_value=False
            )
        # TVShow playlists default to False (new opt-in feature)
        settings.playlist_export_tvshows = False
        addon.setSetting('playlist_export_tvshows', 'false')
        # Clear the old setting to complete migration
        addon.setSetting('maintainsmartplaylist', '')
    else:
        # Normal load - read from settings or use defaults
        if episode_setting != '':
            settings.playlist_export_episodes = episode_setting == 'true'
        # else: keep dataclass default (True)
        
        if tvshow_setting != '':
            settings.playlist_export_tvshows = tvshow_setting == 'true'
        # else: keep dataclass default (False)
    
    # Smart playlist filter settings
    settings.smartplaylist_filter_enabled = setting('smartplaylist_filter_enabled') == 'true'
    settings.user_playlist_path = setting('user_playlist_path') or 'none'
    
    # Positioned specials setting
    settings.include_positioned_specials = setting('include_positioned_specials') == 'true'
    
    # Parse random_order_shows - handles both old [id] and new {id: title} formats
    show_dict, needs_migration = _parse_show_setting(setting('random_order_shows'))
    if needs_migration:
        show_dict = _migrate_show_setting('random_order_shows', show_dict, addon, log)
    # Extract list[int] from dict keys for consumers
    settings.random_order_shows = [int(sid) for sid in show_dict.keys()]
    
    # Get previous random_order_shows from window property
    try:
        old_random_order_shows = ast.literal_eval(
            window.getProperty("EasyTV.random_order_shows")
        )
    except (ValueError, SyntaxError):
        old_random_order_shows = []
    
    # Update window property immediately to prevent duplicate processing
    # when multiple onSettingsChanged events fire in quick succession
    window.setProperty("EasyTV.random_order_shows", str(settings.random_order_shows))
    
    # Handle changes to random_order_shows
    if old_random_order_shows != settings.random_order_shows and not firstrun:
        # Process newly added random order shows
        for show_id in settings.random_order_shows:
            if show_id not in old_random_order_shows:
                show_name = window.getProperty(f"EasyTV.{show_id}.TVshowTitle")
                if not show_name:
                    # Fallback: lookup from Kodi library if Window property not set yet
                    result = json_query(build_show_details_query(show_id), True)
                    show_name = result.get('tvshowdetails', {}).get('title', 'Unknown')
                log.debug("Adding random order show", show=show_name, show_id=show_id)
                
                # Add to shows_with_next_episodes and shuffle
                if on_add_random_show:
                    on_add_random_show(show_id)
                if on_reshuffle_random_shows:
                    on_reshuffle_random_shows([show_id])
        
        # Process removed random order shows
        for old_show_id in old_random_order_shows:
            if old_show_id not in settings.random_order_shows:
                old_show_name = window.getProperty(f"EasyTV.{old_show_id}.TVshowTitle")
                if not old_show_name:
                    # Fallback: lookup from Kodi library if Window property not set
                    result = json_query(build_show_details_query(old_show_id), True)
                    old_show_name = result.get('tvshowdetails', {}).get('title', 'Unknown')
                log.debug("Removing random order show", show=old_show_name, show_id=old_show_id)
                
                # Check if show has ondeck episodes
                try:
                    has_ondeck = ast.literal_eval(
                        window.getProperty(f"EasyTV.{old_show_id}.ondeck_list")
                    )
                    log.debug("Checking ondeck for removed show", ondeck=has_ondeck)
                except (ValueError, SyntaxError):
                    has_ondeck = False
                
                # If show has ondeck episodes, store next episode before removing
                if has_ondeck:
                    log.debug("Storing ondeck episode for removed random show")
                    retrieved_ondeck_string = window.getProperty(
                        f"EasyTV.{old_show_id}.ondeck_list"
                    )
                    retrieved_offdeck_string = window.getProperty(
                        f"EasyTV.{old_show_id}.offdeck_list"
                    )
                    offdeck_list = ast.literal_eval(retrieved_offdeck_string)
                    ondeck_list = ast.literal_eval(retrieved_ondeck_string)
                    temp_watched_count = int(
                        window.getProperty(f"EasyTV.{old_show_id}.CountWatchedEps")
                        .replace("''", '0')
                    ) + 1
                    temp_unwatched_count = max(
                        0,
                        int(
                            window.getProperty(f"EasyTV.{old_show_id}.CountUnwatchedEps")
                            .replace("''", '0')
                        ) - 1
                    )
                    
                    if on_store_next_ep:
                        on_store_next_ep(
                            ondeck_list[0], old_show_id, ondeck_list, offdeck_list,
                            temp_unwatched_count, temp_watched_count
                        )
                else:
                    if on_remove_show:
                        on_remove_show(old_show_id)
    
    log.debug("Random order shows", shows=settings.random_order_shows)
    
    # Parse selection (usersel) - handles both old [id] and new {id: title} formats
    # Unlike random_order_shows, selection has no change callbacks - it's just a filter
    # read at runtime by default.py
    show_dict, needs_migration = _parse_show_setting(setting('selection'))
    if needs_migration:
        show_dict = _migrate_show_setting('selection', show_dict, addon, log)
    # Extract list[int] from dict keys for consumers
    settings.selection = [int(sid) for sid in show_dict.keys()]
    
    # Update window property for default.py to read
    window.setProperty("EasyTV.selection", str(settings.selection))
    
    log.debug("Selection shows", shows=settings.selection)
    
    if firstrun:
        log.info(
            "Settings loaded",
            event="settings.load",
            # Playback behavior
            next_prompt=settings.nextprompt,
            next_prompt_in_playlist=settings.nextprompt_in_playlist,
            prompt_duration=settings.promptduration,
            prompt_default_action=settings.promptdefaultaction,
            previous_check=settings.previous_episode_check,
            resume_partials_tv=settings.resume_partials_tv,
            resume_partials_movies=settings.resume_partials_movies,
            # Playlist continuation
            playlist_continuation=settings.playlist_continuation,
            playlist_continuation_duration=settings.playlist_continuation_duration,
            playlist_continuation_default_action=settings.playlist_continuation_default_action,
            # Notifications
            notifications=settings.playlist_notifications,
            # Smart playlist export
            playlist_export_episodes=settings.playlist_export_episodes,
            playlist_export_tvshows=settings.playlist_export_tvshows,
            smartplaylist_filter=settings.smartplaylist_filter_enabled,
            # Episode selection
            include_positioned_specials=settings.include_positioned_specials,
            # Service behavior
            startup=settings.startup,
            keep_logs=settings.keep_logs,
        )
        
        # Initialize display settings with current values
        init_display_settings(addon)
    
    return settings
