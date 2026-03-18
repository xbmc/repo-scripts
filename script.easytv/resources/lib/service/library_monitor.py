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
EasyTV Library Monitor.

Monitors Kodi library and settings changes to keep the service in sync.
Extracted from service.py as part of modularization.

Logging:
    Module: library_monitor
    Events: None (debug/info logging only, no formal events)
"""
from __future__ import annotations

import ast
from typing import Callable, List, Optional, TYPE_CHECKING

import xbmc
import xbmcgui

from resources.lib.constants import WATCHED_PLAYCOUNT, PROP_ART_FETCHED
from resources.lib.utils import get_logger, json_query
from resources.lib.data.queries import build_episode_show_id_query

if TYPE_CHECKING:
    from resources.lib.utils import StructuredLogger


# Type aliases for callbacks
# Note: Use List instead of list for Python 3.8 compatibility (Kodi uses 3.8)
SettingsReloadCallback = Callable[[], None]
GetEpisodesCallback = Callable[[List[int]], None]
GetRandomShowsCallback = Callable[[], List[int]]


class LibraryMonitor(xbmc.Monitor):
    """
    Monitors Kodi library updates and settings changes.
    
    Responds to:
    - Settings changes: Triggers settings reload
    - Library scan completion: Triggers full refresh and clears art cache
    - VideoLibrary.OnUpdate notifications: Handles watched/unwatched changes
    
    Args:
        window: The Kodi home window for property access.
        on_settings_changed: Callback when settings change.
        on_library_updated: Callback to set library update flag.
        get_random_order_shows: Callback to get current random order shows list.
        on_refresh_show: Callback to refresh a specific show's episodes.
        on_playing_episode_watched: Callback(show_id, episode_id) when a tracked
            episode is marked watched. Called before on_refresh_show to allow the
            daemon to complete tracking before the refresh blocks the loop.
        logger: Optional logger instance.
    """
    
    def __init__(
        self,
        window: xbmcgui.Window,
        on_settings_changed: SettingsReloadCallback,
        on_library_updated: Callable[[], None],
        get_random_order_shows: GetRandomShowsCallback,
        on_refresh_show: GetEpisodesCallback,
        on_playing_episode_watched: Callable[[int, int], None],
        logger: Optional[StructuredLogger] = None,
    ):
        """Initialize the library monitor with callbacks."""
        super().__init__()

        self._window = window
        self._on_settings_changed = on_settings_changed
        self._on_library_updated = on_library_updated
        self._get_random_order_shows = get_random_order_shows
        self._on_refresh_show = on_refresh_show
        self._on_playing_episode_watched = on_playing_episode_watched
        self._log = logger or get_logger('library_monitor')
        
        # Notification data storage
        self._notification_data: dict = {}
    
    def onSettingsChanged(self) -> None:
        """Handle settings changes by triggering a reload."""
        self._on_settings_changed()
    
    def onScanFinished(self, library: str) -> None:
        """
        Handle library scan completion.
        
        When a video library scan completes, triggers a full refresh to pick up
        any new shows or episodes. Also clears the art cache flag so that new
        shows will have their art fetched when Browse mode opens.
        
        Args:
            library: The library that was scanned ('video' or 'music').
        """
        if library == 'video':
            self._log.info(
                "Library scan finished, refreshing episode list",
                event="library.scan_finished"
            )
            # Clear art cache flag so new shows get art on next Browse
            self._window.clearProperty(PROP_ART_FETCHED)
            self._on_library_updated()
    
    def onNotification(self, _sender: str, method: str, data: str) -> None:
        """
        Handle Kodi notifications.
        
        Processes VideoLibrary.OnUpdate notifications to detect:
        - Episodes marked as watched: Refreshes show tracking
        - Episodes marked as unwatched: Refreshes show tracking
        
        Args:
            _sender: The notification sender (unused, required by Kodi API).
            method: The notification method/type.
            data: JSON string with notification data.
        """
        # Only process VideoLibrary.OnUpdate notifications
        if method != 'VideoLibrary.OnUpdate':
            return
        
        # Parse notification data
        try:
            self._notification_data = ast.literal_eval(data)
        except (ValueError, SyntaxError):
            return
        
        # Check for valid episode update with playcount
        if 'item' not in self._notification_data:
            return
        if 'playcount' not in self._notification_data:
            return
        if 'type' not in self._notification_data['item']:
            return
        if self._notification_data['item']['type'] != 'episode':
            return
        
        episode_id = self._notification_data['item']['id']
        playcount = self._notification_data['playcount']
        
        self._log.debug(
            "Episode update notification",
            episode_id=episode_id,
            playcount=playcount
        )
        
        if playcount >= WATCHED_PLAYCOUNT:
            self._handle_episode_watched(episode_id)
        elif playcount == 0:
            self._handle_episode_unwatched(episode_id)
    
    def _handle_episode_watched(self, episode_id: int) -> None:
        """
        Handle an episode being marked as watched.
        
        Checks if the episode is in the current show's ondeck/offdeck list
        and refreshes the show's tracking data if so.
        
        Args:
            episode_id: The ID of the watched episode.
        """
        self._log.debug("Watched status change detected", data=self._notification_data)
        
        # Get the show ID for this episode
        result = json_query(build_episode_show_id_query(episode_id), True)
        if 'episodedetails' not in result:
            return
        
        show_id = result['episodedetails']['tvshowid']
        
        random_order_shows = self._get_random_order_shows()
        proceed = False
        
        if show_id in random_order_shows:
            # For random order shows, check both ondeck and offdeck
            ondeck_list = self._get_episode_list(show_id, 'ondeck_list')
            offdeck_list = self._get_episode_list(show_id, 'offdeck_list')
            
            if episode_id in ondeck_list or episode_id in offdeck_list:
                proceed = True
        else:
            # For sequential shows, only check ondeck
            ondeck_list = self._get_episode_list(show_id, 'ondeck_list')
            if episode_id in ondeck_list:
                proceed = True
        
        if proceed:
            # Notify daemon before refresh — the refresh blocks the daemon loop
            # for 1-2 seconds, which can cause the position check to miss the
            # threshold. This callback lets the daemon complete tracking first.
            self._on_playing_episode_watched(show_id, episode_id)
            self._log.info(
                "Refreshing show after watched",
                event="library.refresh_watched",
                show_id=show_id,
                episode_id=episode_id
            )
            self._on_refresh_show([show_id])
    
    def _handle_episode_unwatched(self, episode_id: int) -> None:
        """
        Handle an episode being marked as unwatched.
        
        Refreshes the show's tracking data to pick up the now-unwatched episode.
        
        Args:
            episode_id: The ID of the unwatched episode.
        """
        self._log.debug("Episode marked unwatched", data=self._notification_data)
        
        result = json_query(build_episode_show_id_query(episode_id), True)
        if 'episodedetails' in result:
            show_id = result['episodedetails']['tvshowid']
            self._log.info(
                "Refreshing show after unwatched",
                event="library.refresh_unwatched",
                show_id=show_id,
                episode_id=episode_id
            )
            self._on_refresh_show([show_id])
    
    def _get_episode_list(self, show_id: int, list_name: str) -> List[int]:
        """
        Get an episode list from window properties.
        
        Args:
            show_id: The TV show ID.
            list_name: Either 'ondeck_list' or 'offdeck_list'.
        
        Returns:
            List of episode IDs, or empty list if not found/invalid.
        """
        property_name = f"EasyTV.{show_id}.{list_name}"
        property_value = self._window.getProperty(property_name)
        
        try:
            return ast.literal_eval(property_value)
        except (ValueError, SyntaxError):
            return []
