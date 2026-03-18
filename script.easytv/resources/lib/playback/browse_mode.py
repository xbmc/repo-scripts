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
EasyTV Browse Mode Orchestrator.

Orchestrates the "Browse Mode" feature by coordinating:
- Data fetching (via data/ layer)
- UI display (via ui/browse_window)
- Playback initiation (via browse_player)

This module is intentionally in playback/ despite importing from ui/ because
it's primarily about initiating playback from a browse interface. It serves
as a feature orchestrator that ties together multiple architectural layers.

Logging:
    Logger: 'playback' (via get_logger)
    Key events:
        - playback.list_open (DEBUG): Episode list window opened
        - playback.list_select (DEBUG): Episode selected from list
        - playback.list_close (DEBUG): Episode list window closed
    See LOGGING.md for full guidelines.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

import xbmc
import xbmcgui

from resources.lib.constants import (
    KODI_HOME_WINDOW_ID,
    KODI_FULLSCREEN_VIDEO_WINDOW_ID,
    MAIN_LOOP_SLEEP_MS,
    PLAYLIST_ADD_DELAY_MS,
    DIALOG_WAIT_SLEEP_MS,
    DIALOG_WAIT_MAX_TICKS,
    PREMIERE_MIX_IN,
    PREMIERE_ONLY,
    PREMIERE_SKIP,
    PROP_ART_FETCHED,
    PROP_PLAYLIST_RUNNING,
    PROP_RANDOM_ORDER_SHUFFLE,
)
from resources.lib.data.queries import (
    get_clear_video_playlist_query,
    build_add_episode_query,
    build_shows_art_query,
)
from resources.lib.utils import get_logger, json_query, log_timing, busy_progress
from resources.lib.ui.browse_window import (
    BrowseWindow, BrowseWindowConfig, get_skin_xml_file
)
from resources.lib.playback.browse_player import BrowseModePlayer
from resources.lib.playback.random_player import filter_shows_by_population
from resources.lib.data.shows import filter_shows_by_duration
from resources.lib.data.storage import get_storage

if TYPE_CHECKING:
    from resources.lib.utils import StructuredLogger


# Module-level logger (initialized lazily)
_log: Optional[StructuredLogger] = None


def _get_log() -> StructuredLogger:
    """Get or create the module logger."""
    global _log
    if _log is None:
        _log = get_logger('playback')
    return _log


# Shared window reference for property access
WINDOW = xbmcgui.Window(KODI_HOME_WINDOW_ID)


def _fetch_show_art(logger: 'StructuredLogger') -> None:
    """
    Fetch and cache show art to window properties.
    
    Called when Browse mode opens. Uses a session flag to avoid re-fetching
    art multiple times in the same Kodi session.
    
    Art key mapping:
        - Kodi returns: art.poster, art.fanart
        - Cached as: EasyTV.{showid}.Art(tvshow.poster), EasyTV.{showid}.Art(tvshow.fanart)
    
    Args:
        logger: Logger instance for timing instrumentation.
    """
    # Check session flag - skip if already fetched this session
    if WINDOW.getProperty(PROP_ART_FETCHED) == 'true':
        logger.debug("Art already fetched this session, skipping")
        return
    
    # Fetch art for all shows
    with log_timing(logger, "art_fetch") as timer:
        result = json_query(build_shows_art_query())
        timer.mark("query")
        
        shows = result.get('tvshows', [])
        
        # Cache art to window properties
        for show in shows:
            show_id = show.get('tvshowid')
            if show_id is None:
                continue
            
            art = show.get('art', {})
            prop_prefix = f"EasyTV.{show_id}"
            
            # Map Kodi art keys to window property format
            # poster -> Art(tvshow.poster), fanart -> Art(tvshow.fanart)
            WINDOW.setProperty(f"{prop_prefix}.Art(tvshow.poster)", art.get('poster', ''))
            WINDOW.setProperty(f"{prop_prefix}.Art(tvshow.fanart)", art.get('fanart', ''))
        
        timer.mark("cache")
    
    # Set session flag
    WINDOW.setProperty(PROP_ART_FETCHED, 'true')
    logger.debug("Art fetched and cached", show_count=len(shows))



@dataclass
class EpisodeListConfig:
    """
    Configuration for the episode list builder.
    
    Attributes:
        skin: Skin style (0=DialogSelect, 1=main, 2=BigScreenList)
        limit_shows: Whether to limit the number of shows displayed
        window_length: Maximum number of shows when limit_shows is True
        skin_return: Whether to return to the window after playback
        excl_random_order_shows: Whether to exclude random-order shows
        script_path: Path to the addon for locating resources
        duration_filter_enabled: Whether to filter shows by episode duration
        duration_min: Minimum episode duration in minutes (0 = no minimum)
        duration_max: Maximum episode duration in minutes (0 = no maximum)
        sort_by: Sort method for shows (0=name, 1=last played, 2=random)
        sort_reverse: Whether to reverse the sort order
        language: System language for sorting
        series_premieres: Series premiere filter mode (PREMIERE_SKIP=0, PREMIERE_MIX_IN=1, PREMIERE_ONLY=2)
        season_premieres: Season premiere filter mode (PREMIERE_SKIP=0, PREMIERE_MIX_IN=1, PREMIERE_ONLY=2)
    """
    skin: int = 0
    limit_shows: bool = False
    window_length: int = 20
    skin_return: bool = True
    excl_random_order_shows: bool = False
    script_path: str = ''
    duration_filter_enabled: bool = False
    duration_min: int = 0
    duration_max: int = 0
    sort_by: int = 1
    sort_reverse: bool = False
    language: str = 'English'
    series_premieres: int = PREMIERE_MIX_IN
    season_premieres: int = PREMIERE_MIX_IN


def build_episode_list(
    population: dict,
    random_order_shows: list,
    config: EpisodeListConfig,
    monitor: Optional[xbmc.Monitor] = None,
    logger: Optional[StructuredLogger] = None
) -> None:
    """
    Build and display an episode list window for browsing TV shows.
    
    Fetches show data based on population filter, applies duration and premiere
    filters, then creates a browse window showing next unwatched episodes.
    Users can select episodes for playback, use context menu options, and
    interact with the list.
    
    The function runs a modal loop until the user closes the window or
    Kodi requests abort.
    
    Args:
        population: Dict with one of:
            - {'playlist': path} - Filter by smart playlist contents
            - {'usersel': [show_ids]} - Filter by user-selected shows
            - {'none': ''} - No filtering
        random_order_shows: List of show IDs marked for random ordering
        config: EpisodeListConfig with display and behavior settings
        monitor: Optional xbmc.Monitor for abort checking (creates one if None)
        logger: Optional logger instance (uses module logger if None)
    
    Side Effects:
        - Sets 'EasyTV.playlist_running' property when playback starts
        - Sets 'EasyTV.random_order_shuffle' property to trigger reshuffling
        - Starts video playlist playback when user selects episodes
    
    Example:
        ```python
        config = EpisodeListConfig(
            skin=1,
            limit_shows=True,
            window_length=25,
            script_path='/path/to/addon',
            sort_by=1,
            language='English'
        )
        build_episode_list({'none': ''}, [], config)
        ```
    """
    log = logger or _get_log()
    mon = monitor or xbmc.Monitor()
    
    # Premiere filter helper (needed by _fetch_data)
    only_mode = (config.series_premieres == PREMIERE_ONLY
                 or config.season_premieres == PREMIERE_ONLY)
    needs_premiere_filter = (only_mode
                             or config.series_premieres == PREMIERE_SKIP
                             or config.season_premieres == PREMIERE_SKIP)

    def should_include(show_entry):
        """Check if episode should be included based on premiere settings."""
        episode_no = WINDOW.getProperty(f"EasyTV.{show_entry[1]}.EpisodeNo")
        if not episode_no or len(episode_no) < 6:
            return not only_mode
        try:
            season_num = int(episode_no[1:3])
            episode_num = int(episode_no[4:6])
        except (ValueError, IndexError):
            return not only_mode

        is_premiere = (episode_num == 1)

        if only_mode:
            if not is_premiere:
                return False
            if season_num == 1 and config.series_premieres == PREMIERE_SKIP:
                return False
            if season_num > 1 and config.season_premieres == PREMIERE_SKIP:
                return False
            return True
        else:
            if not is_premiere:
                return True
            if season_num == 1:
                return config.series_premieres != PREMIERE_SKIP
            return config.season_premieres != PREMIERE_SKIP

    def _fetch_data():
        """Fetch, filter, and sort show data from Kodi."""
        show_data = filter_shows_by_population(
            population, config.sort_by, config.sort_reverse, config.language, logger=log
        )
        if config.duration_filter_enabled and show_data:
            show_data = filter_shows_by_duration(
                show_data,
                min_minutes=config.duration_min,
                max_minutes=config.duration_max
            )
        if needs_premiere_filter:
            show_data = [x for x in show_data if should_include(x)]
        if config.excl_random_order_shows and random_order_shows:
            return [x for x in show_data if x[1] not in random_order_shows]
        return show_data

    # Show loading indicator during data fetching operations
    with busy_progress("Loading shows..."):
        filtered_data = _fetch_data()

        # Refresh from shared storage if stale (multi-instance sync)
        # This ensures window properties are up-to-date before displaying
        if filtered_data:
            storage = get_storage()
            if storage.needs_refresh():
                show_ids = [show[1] for show in filtered_data]
                log.debug("Cache stale, refreshing before browse",
                         event="browse.refresh", show_count=len(show_ids))
                try:
                    _, revision = storage.get_ondeck_bulk(show_ids, refresh_display=True)
                    storage.mark_refreshed(revision)
                except Exception as e:
                    log.warning("Refresh failed, using cached data",
                               event="browse.refresh_error", error=str(e))

        log.info("Browse mode starting", event="browse.start", show_count=len(filtered_data))

        # Fetch show art if not already cached this session
        _fetch_show_art(log)
    
    # Get appropriate XML file for skin
    xmlfile = get_skin_xml_file(config.skin)
    
    # Create browse window configuration
    browse_config = BrowseWindowConfig(
        skin=config.skin,
        limit_shows=config.limit_shows,
        window_length=config.window_length,
        skin_return=config.skin_return
    )
    
    # Create the browse window
    list_window = BrowseWindow(
        xmlfile, config.script_path, 'Default',
        data=filtered_data,
        config=browse_config,
        script_path=config.script_path,
        logger=log
    )
    
    # Create player that coordinates with the window
    player = BrowseModePlayer(parent=list_window)
    
    # Main UI loop
    stay_open = True
    open_window = True
    
    while stay_open and not mon.abortRequested():
        
        if open_window:
            log.debug("Opening episode list window", 
                     existing_window=xbmc.getInfoLabel('Window.Property(xmlfile)'))
            
            # Wait for any existing dialogs to close
            # This prevents the window from covering YesNo dialogs from the service
            count = 0
            while count < DIALOG_WAIT_MAX_TICKS and \
                  xbmc.getInfoLabel('Window.Property(xmlfile)') == 'DialogYesNo.xml':
                xbmc.sleep(DIALOG_WAIT_SLEEP_MS)
                count += 1
            
            open_window = False
            list_window.doModal()
        
        # Check window state after modal closes
        if list_window.should_close:
            stay_open = False
            continue
        
        if list_window.needs_refresh:
            # Re-fetch show data with fresh sort order from Kodi
            filtered_data = _fetch_data()
            list_window.update_data(filtered_data)
            open_window = True
            list_window.reset_state()
            continue
        
        selected = list_window.selected_show
        
        if selected is not None and list_window.play_requested:
            log.debug("Starting playback from episode list")
            
            # Mark playlist as running in listview mode
            WINDOW.setProperty(PROP_PLAYLIST_RUNNING, 'listview')
            
            # Clear and rebuild playlist
            # This approach is needed because .strm files won't start via JSON-RPC
            json_query(get_clear_video_playlist_query(), False)
            
            # Add selected episode(s) to playlist
            if isinstance(selected, list):
                for ep in selected:
                    json_query(build_add_episode_query(int(ep)), False)
            else:
                json_query(build_add_episode_query(int(selected)), False)
            
            # Start playback
            xbmc.sleep(PLAYLIST_ADD_DELAY_MS)
            player.play(xbmc.PlayList(1))
            xbmc.executebuiltin('ActivateWindow(%d)' % KODI_FULLSCREEN_VIDEO_WINDOW_ID)
            
            # Reset for next iteration
            list_window.reset_state()
            
            # Notify service to reshuffle random order shows
            WINDOW.setProperty(PROP_RANDOM_ORDER_SHUFFLE, 'true')
        
        # Check if we should stay open after playback
        if not config.skin_return:
            stay_open = False
        
        xbmc.sleep(MAIN_LOOP_SLEEP_MS)
    
    # Cleanup
    del list_window
    del player
    
    # Final notification to service
    WINDOW.setProperty(PROP_RANDOM_ORDER_SHUFFLE, 'true')
    
    log.info("Browse mode closed", event="browse.stop")
