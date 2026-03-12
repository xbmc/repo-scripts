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
EasyTV Episode Tracker.

Manages episode state and window properties for TV show tracking.
Handles caching next episode data and transitioning between episodes
when playback completion is detected.

The episode tracker uses Kodi window properties to store episode
metadata that can be accessed by both the service and UI components.
Properties use the format: EasyTV.{showid}.{property}

A special 'temp' show ID is used to stage next episode data before
it's committed when playback crosses the completion threshold.

Performance Optimization:
    cache_next_episode() accepts an optional `ep_data` parameter containing
    pre-fetched episode data from bulk queries. When provided, this skips
    the per-episode Kodi query, significantly improving startup performance
    for large libraries (277+ shows → ~1s instead of ~10s).

Extracted from service.py as part of modularization.

Logging:
    Module: episode_tracker
    Events: None (debug/warning logging only, no formal events)
"""
from __future__ import annotations

import ast
from typing import Any, Callable, Dict, Optional, TYPE_CHECKING, Union

import xbmcgui

from resources.lib.constants import PERCENT_MULTIPLIER
from resources.lib.utils import (
    get_logger,
    json_query,
    is_abort_requested,
    service_heartbeat,
)
from resources.lib.data.queries import build_episode_details_query
from resources.lib.data.storage import get_storage

if TYPE_CHECKING:
    from resources.lib.utils import StructuredLogger


# =============================================================================
# Window Property Names
# =============================================================================
# These are the standard property names used for episode data.
# Format: EasyTV.{showid}.{PROPERTY_NAME}
PROP_TITLE = "Title"
PROP_EPISODE = "Episode"
PROP_EPISODE_NO = "EpisodeNo"
PROP_SEASON = "Season"
PROP_TVSHOW_TITLE = "TVshowTitle"
PROP_ART_POSTER = "Art(tvshow.poster)"
PROP_RESUME = "Resume"
PROP_PERCENT_PLAYED = "PercentPlayed"
PROP_COUNT_WATCHED = "CountWatchedEps"
PROP_COUNT_UNWATCHED = "CountUnwatchedEps"
PROP_COUNT_ONDECK = "CountonDeckEps"
PROP_EPISODE_ID = "EpisodeID"
PROP_ONDECK_LIST = "ondeck_list"
PROP_OFFDECK_LIST = "offdeck_list"
PROP_FILE = "File"
PROP_ART_FANART = "Art(tvshow.fanart)"
PROP_PREMIERED = "Premiered"
PROP_PLOT = "Plot"
PROP_IS_SKIPPED = "IsSkipped"
PROP_DURATION = "Duration"
PROP_YEAR = "Year"

# All properties that need to be copied during swap_over
EPISODE_PROPERTIES = [
    PROP_TITLE,
    PROP_EPISODE,
    PROP_EPISODE_NO,
    PROP_SEASON,
    PROP_TVSHOW_TITLE,
    PROP_ART_POSTER,
    PROP_RESUME,
    PROP_PERCENT_PLAYED,
    PROP_COUNT_WATCHED,
    PROP_COUNT_UNWATCHED,
    PROP_COUNT_ONDECK,
    PROP_EPISODE_ID,
    PROP_ONDECK_LIST,
    PROP_OFFDECK_LIST,
    PROP_FILE,
    PROP_ART_FANART,
    PROP_PREMIERED,
    PROP_PLOT,
    PROP_IS_SKIPPED,
]

# Temporary show ID used for staging next episode data
TEMP_SHOW_ID = "temp"

# Property prefix for EasyTV window properties
PROPERTY_PREFIX = "EasyTV"


# =============================================================================
# Type Aliases for Callbacks
# =============================================================================

# Callback to update smart playlists when episode data changes
# Note: Use Union instead of | for Python 3.8 compatibility (Kodi uses 3.8)
# The callback accepts (show_id, **kwargs) where kwargs may include quiet=bool, remove=bool
SmartPlaylistUpdateCallback = Callable[..., None]


# =============================================================================
# Episode Tracker Class
# =============================================================================

class EpisodeTracker:
    """
    Manages episode state through Kodi window properties.
    
    The tracker provides two main operations:
    
    1. cache_next_episode(): Stores episode data in 'temp' properties,
       preparing it to replace the current show's data when playback
       completes. Also can store directly to a show ID for initial
       population during library scans.
       
    2. transition_to_next_episode(): Copies all 'temp' properties to the
       actual show ID properties when playback crosses the completion
       threshold. This "commits" the next episode as the new current.
    
    Args:
        window: The Kodi home window for property access.
        on_update_smartplaylist: Optional callback to update smart playlists
            when episode data changes for a show.
        logger: Optional logger instance.
    """
    
    def __init__(
        self,
        window: xbmcgui.Window,
        on_update_smartplaylist: Optional[SmartPlaylistUpdateCallback] = None,
        logger: Optional[StructuredLogger] = None,
    ):
        """Initialize the episode tracker."""
        self._window = window
        self._on_update_smartplaylist = on_update_smartplaylist
        self._log = logger or get_logger("episode_tracker")
    
    def _build_property_key(self, show_id: Union[int, str], prop_name: str) -> str:
        """
        Build a window property key.
        
        Args:
            show_id: The show ID or 'temp' for staging.
            prop_name: The property name (e.g., 'Title', 'Episode').
        
        Returns:
            The full property key: 'EasyTV.{show_id}.{prop_name}'
        """
        return f"{PROPERTY_PREFIX}.{show_id}.{prop_name}"
    
    def _set_property(self, show_id: Union[int, str], prop_name: str, value: str) -> None:
        """
        Set a window property for a show.
        
        Args:
            show_id: The show ID or 'temp'.
            prop_name: The property name.
            value: The value to set.
        """
        key = self._build_property_key(show_id, prop_name)
        self._window.setProperty(key, value)
    
    def _get_property(self, show_id: Union[int, str], prop_name: str) -> str:
        """
        Get a window property for a show.
        
        Args:
            show_id: The show ID or 'temp'.
            prop_name: The property name.
        
        Returns:
            The property value, or empty string if not set.
        """
        key = self._build_property_key(show_id, prop_name)
        return self._window.getProperty(key)
    
    def cache_next_episode(
        self,
        episode_id: int,
        show_id: Union[int, str],
        ondeck_list: list[int],
        offdeck_list: list[int],
        unwatched_count: Union[int, str] = 0,
        watched_count: Union[int, str] = 0,
        is_skipped: bool = False,
        quiet: bool = False,
        ep_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Cache episode data in window properties.
        
        Fetches episode details from Kodi (or uses pre-fetched data) and stores
        them in window properties for the specified show ID. When show_id is
        'temp', this stages data for the next episode that will be committed
        when playback completes.
        
        Args:
            episode_id: The Kodi episode ID to cache.
            show_id: The show ID to store under, or 'temp' for staging.
            ondeck_list: List of episode IDs still to watch (in order).
            offdeck_list: List of skipped episode IDs (for random shows).
            unwatched_count: Total unwatched episodes for the show.
            watched_count: Total watched episodes for the show.
            is_skipped: True if this episode is from offdeck (a skipped episode).
            quiet: If True, suppress debug logging (for bulk operations).
            ep_data: Optional pre-fetched episode data dict from bulk query.
                     If provided, skips the Kodi query for episode details.
                     Expected keys: episode, season, resume, art, title,
                     showtitle, file, firstaired, plot, episodeid.
        """
        # Normalize show ID
        try:
            normalized_show_id = int(show_id)
        except (ValueError, TypeError):
            normalized_show_id = show_id
        
        # Check for abort before doing work
        if is_abort_requested():
            return
        
        # Signal liveness
        service_heartbeat()
        
        # Get episode details: use pre-fetched data or query Kodi
        if ep_data is not None:
            # Use pre-fetched data from bulk query
            ep_details = ep_data
        else:
            # Fetch episode details from Kodi
            ep_result = json_query(build_episode_details_query(episode_id), True)
            
            if 'episodedetails' not in ep_result:
                self._log.warning(
                    "Episode details not found",
                    event="episode.not_found",
                    episode_id=episode_id,
                    show_id=normalized_show_id
                )
                return
            
            ep_details = ep_result['episodedetails']
        
        # Format episode and season numbers (use .get() for defensive access)
        episode = "%.2d" % float(ep_details.get('episode', 0))
        season = "%.2d" % float(ep_details.get('season', 0))
        episode_no = f"s{season}e{episode}"
        
        # Calculate resume state (use .get() for defensive access)
        resume_dict = ep_details.get('resume', {})
        resume_pos = resume_dict.get('position', 0)
        resume_total = resume_dict.get('total', 0)
        
        if resume_pos and resume_total:
            resume = "true"
            percent = int((float(resume_pos) / float(resume_total)) * PERCENT_MULTIPLIER)
            percent_played = f"{percent}%"
        else:
            resume = "false"
            percent_played = "0%"
        
        # Get artwork (use .get() for defensive access)
        art = ep_details.get('art', {})
        
        # Store all properties (use .get() for defensive access)
        self._set_property(normalized_show_id, PROP_TITLE, ep_details.get('title', ''))
        self._set_property(normalized_show_id, PROP_EPISODE, episode)
        self._set_property(normalized_show_id, PROP_EPISODE_NO, episode_no)
        self._set_property(normalized_show_id, PROP_SEASON, season)
        self._set_property(normalized_show_id, PROP_TVSHOW_TITLE, ep_details.get('showtitle', ''))
        self._set_property(normalized_show_id, PROP_ART_POSTER, art.get('tvshow.poster', ''))
        self._set_property(normalized_show_id, PROP_RESUME, resume)
        self._set_property(normalized_show_id, PROP_PERCENT_PLAYED, percent_played)
        self._set_property(normalized_show_id, PROP_COUNT_WATCHED, str(watched_count))
        self._set_property(normalized_show_id, PROP_COUNT_UNWATCHED, str(unwatched_count))
        self._set_property(normalized_show_id, PROP_COUNT_ONDECK, str(len(ondeck_list)))
        self._set_property(normalized_show_id, PROP_EPISODE_ID, str(ep_details.get('episodeid', '')))
        self._set_property(normalized_show_id, PROP_ONDECK_LIST, str(ondeck_list))
        self._set_property(normalized_show_id, PROP_OFFDECK_LIST, str(offdeck_list))
        self._set_property(normalized_show_id, PROP_FILE, ep_details.get('file', ''))
        self._set_property(normalized_show_id, PROP_ART_FANART, art.get('tvshow.fanart', ''))
        self._set_property(normalized_show_id, PROP_PREMIERED, ep_details.get('firstaired', ''))
        self._set_property(normalized_show_id, PROP_PLOT, ep_details.get('plot', ''))
        self._set_property(normalized_show_id, PROP_IS_SKIPPED, str(is_skipped).lower())
        
        # Clean up (only if we queried)
        if ep_data is None:
            del ep_details
        
        # Update smart playlists for non-temp show IDs
        if normalized_show_id != TEMP_SHOW_ID and self._on_update_smartplaylist:
            self._on_update_smartplaylist(normalized_show_id, quiet=quiet)
        
        # Write-through to shared storage (multi-instance sync)
        # Only for non-temp show IDs - temp is staging data that doesn't need persistence
        if normalized_show_id != TEMP_SHOW_ID and isinstance(normalized_show_id, int):
            try:
                storage = get_storage()
                # Get show_year from window property (set during bulk refresh)
                show_year_str = self._get_property(normalized_show_id, PROP_YEAR)
                show_year = int(show_year_str) if show_year_str else None
                # Get show title from window property (just set above)
                show_title = self._get_property(normalized_show_id, PROP_TVSHOW_TITLE)

                storage.set_ondeck(normalized_show_id, {
                    'show_title': show_title,
                    'show_year': show_year,
                    'ondeck_episode_id': episode_id,
                    'ondeck_list': ondeck_list,
                    'offdeck_list': offdeck_list,
                    'watched_count': int(watched_count) if watched_count else 0,
                    'unwatched_count': int(unwatched_count) if unwatched_count else 0,
                })
            except Exception as e:
                # Log but don't fail - graceful degradation
                self._log.warning("Storage write failed",
                                event="storage.write_error",
                                show_id=normalized_show_id,
                                error=str(e))
        
        if not quiet:
            self._log.debug(
                "Episode cached",
                episode_id=episode_id,
                show_id=normalized_show_id,
                episode_no=episode_no,
                is_skipped=is_skipped
            )
    
    def transition_to_next_episode(self, show_id: Union[int, str]) -> None:
        """
        Copy temp episode data to the show's actual properties.
        
        Called when playback crosses the completion threshold. Copies all
        episode properties from 'temp' to the specified show ID, effectively
        "committing" the next episode as the current one.
        
        Args:
            show_id: The show ID to update.
        """
        self._log.debug("Transitioning episode data", show_id=show_id)
        
        # Copy all properties from temp to show ID
        for prop_name in EPISODE_PROPERTIES:
            temp_value = self._get_property(TEMP_SHOW_ID, prop_name)
            self._set_property(show_id, prop_name, temp_value)
        
        # Update smart playlists
        if self._on_update_smartplaylist:
            self._on_update_smartplaylist(show_id)
        
        # Write-through to shared storage (multi-instance sync)
        # Data was just copied from temp, so read from actual show_id properties
        try:
            storage = get_storage()
            
            # Parse ondeck/offdeck lists from window properties
            ondeck_str = self._get_property(show_id, PROP_ONDECK_LIST)
            offdeck_str = self._get_property(show_id, PROP_OFFDECK_LIST)
            ondeck_list = ast.literal_eval(ondeck_str) if ondeck_str else []
            offdeck_list = ast.literal_eval(offdeck_str) if offdeck_str else []
            
            # Get episode ID
            episode_id_str = self._get_property(show_id, PROP_EPISODE_ID)
            episode_id = int(episode_id_str) if episode_id_str else None
            
            # Get counts
            watched_str = self._get_property(show_id, PROP_COUNT_WATCHED)
            unwatched_str = self._get_property(show_id, PROP_COUNT_UNWATCHED)
            watched_count = int(watched_str) if watched_str else 0
            unwatched_count = int(unwatched_str) if unwatched_str else 0
            
            # Get show metadata (year is on show_id, not temp)
            show_year_str = self._get_property(show_id, PROP_YEAR)
            show_year = int(show_year_str) if show_year_str else None
            show_title = self._get_property(show_id, PROP_TVSHOW_TITLE)
            
            if episode_id is not None:
                storage.set_ondeck(int(show_id), {
                    'show_title': show_title,
                    'show_year': show_year,
                    'ondeck_episode_id': episode_id,
                    'ondeck_list': ondeck_list,
                    'offdeck_list': offdeck_list,
                    'watched_count': watched_count,
                    'unwatched_count': unwatched_count,
                })
        except Exception as e:
            # Log but don't fail - graceful degradation
            self._log.warning("Storage write failed during transition",
                            event="storage.transition_error",
                            show_id=show_id,
                            error=str(e))
        
        self._log.debug("Episode transition complete", show_id=show_id)
    
    def get_ondeck_list(self, show_id: Union[int, str]) -> str:
        """
        Get the ondeck episode list for a show.
        
        Args:
            show_id: The show ID.
        
        Returns:
            String representation of the ondeck list.
        """
        return self._get_property(show_id, PROP_ONDECK_LIST)
    
    def get_offdeck_list(self, show_id: Union[int, str]) -> str:
        """
        Get the offdeck episode list for a show.
        
        Args:
            show_id: The show ID.
        
        Returns:
            String representation of the offdeck list.
        """
        return self._get_property(show_id, PROP_OFFDECK_LIST)
    
    def get_episode_id(self, show_id: Union[int, str]) -> str:
        """
        Get the current episode ID for a show.
        
        Args:
            show_id: The show ID.
        
        Returns:
            The episode ID as a string.
        """
        return self._get_property(show_id, PROP_EPISODE_ID)
    
    def get_watched_count(self, show_id: Union[int, str]) -> str:
        """
        Get the watched episode count for a show.
        
        Args:
            show_id: The show ID.
        
        Returns:
            The watched count as a string.
        """
        return self._get_property(show_id, PROP_COUNT_WATCHED)
    
    def get_unwatched_count(self, show_id: Union[int, str]) -> str:
        """
        Get the unwatched episode count for a show.
        
        Args:
            show_id: The show ID.
        
        Returns:
            The unwatched count as a string.
        """
        return self._get_property(show_id, PROP_COUNT_UNWATCHED)
