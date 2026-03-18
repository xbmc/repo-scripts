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
EasyTV Browse Window.

Provides the main episode browse window for selecting and viewing TV show episodes.
Users can:
- Browse available episodes across all shows
- Select episodes for playback
- Toggle multiselect mode for batch operations
- Export episodes
- Mark episodes as watched
- Refresh the episode list

Extracted from default.py as part of modularization.

Logging:
    Logger: 'ui' (via get_logger)
    Key events:
        - ui.init (DEBUG): Window initialization
        - ui.select (DEBUG): Episode/item selection
        - ui.context (DEBUG): Context menu interaction
        - ui.fallback (WARNING): Skin control setup failures
    See LOGGING.md for full guidelines.
"""
from __future__ import annotations

import os
import time
from datetime import date
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING, Union, cast

import xbmc
import xbmcgui
import xbmcaddon

from resources.lib.constants import (
    KODI_HOME_WINDOW_ID,
    MAX_ITEMS_HARD_LIMIT,
    ACTION_PREVIOUS_MENU,
    ACTION_NAV_BACK,
    ACTION_CONTEXT_MENU,
    CONTEXT_TOGGLE_MULTISELECT,
    CONTEXT_PLAY_SELECTION,
    CONTEXT_PLAY_FROM_HERE,
    CONTEXT_EXPORT_SELECTION,
    CONTEXT_TOGGLE_WATCHED,
    CONTEXT_IGNORE_SHOW,
    CONTEXT_UPDATE_LIBRARY,
    CONTEXT_REFRESH,
)
from resources.lib.data.storage import get_storage
from resources.lib.utils import get_logger, lang, json_query, format_duration

if TYPE_CHECKING:
    from resources.lib.utils import StructuredLogger


# Module-level logger (initialized lazily)
_log: Optional[StructuredLogger] = None


def _get_log() -> StructuredLogger:
    """Get or create the module logger."""
    global _log
    if _log is None:
        _log = get_logger('ui')
    return _log


# Shared window reference for property access
WINDOW = xbmcgui.Window(KODI_HOME_WINDOW_ID)


@dataclass
class BrowseWindowConfig:
    """
    Configuration for the BrowseWindow.

    Attributes:
        skin: Skin style (0=CardList, 1=Posters, 2=BigScreen, 3=SplitView)
        limit_shows: Whether to limit the number of shows displayed
        window_length: Maximum number of shows to display when limit_shows is True
        skin_return: Whether to return to the window after playback
    """
    skin: int = 0
    limit_shows: bool = False
    window_length: int = 20
    skin_return: bool = True


class BrowseWindow(xbmcgui.WindowXMLDialog):
    """
    Main browse window for displaying TV show episodes.
    
    Shows a list of TV shows with their next unwatched episode. Users can:
    - Click to play an episode
    - Use context menu for additional options
    - Toggle multiselect mode for batch operations
    
    Args:
        *args: Positional args passed to WindowXMLDialog.
        **kwargs: Keyword args. Special kwargs:
            - data: List of show data [[lastplayed, showid, episodeid], ...]
            - config: BrowseWindowConfig instance
            - script_path: Path to the addon for locating resources
            - logger: Optional StructuredLogger instance
    """
    
    # Class-level state for multiselect (persists across instances)
    _multiselect: bool = False
    
    def __new__(cls, *args, **kwargs):
        """Create instance, filtering out custom kwargs for parent class."""
        # Remove our custom kwargs before calling parent
        kwargs.pop('data', None)
        kwargs.pop('config', None)
        kwargs.pop('script_path', None)
        kwargs.pop('logger', None)
        return super().__new__(cls, *args, **kwargs)
    
    def __init__(self, *args, **kwargs):
        """Initialize the browse window."""
        # Extract custom kwargs
        self._data = kwargs.pop('data', [])
        self._config = kwargs.pop('config', BrowseWindowConfig())
        self._script_path = kwargs.pop('script_path', '')
        self._log = kwargs.pop('logger', None) or _get_log()
        
        # Call parent init
        super().__init__(*args, **kwargs)
        
        # Instance state
        self._selected_show: Optional[Union[int, list]] = None
        self._load_items: bool = True
        self._play_requested: bool = False
        self._should_close: bool = False
        self._needs_refresh: bool = False

        # Control references (set during onInit)
        self.name_list: Optional[xbmcgui.ControlList] = None

    def onInit(self) -> None:
        """
        Initialize window controls and populate the list.

        Called by Kodi when the window is shown. Sets up the list control
        and populates it with show data.
        """
        # Set theme color properties for skin XML
        from resources.lib.ui import apply_theme
        apply_theme(self)

        # Set addon name for skin heading (shows clone name for clones)
        self.setProperty('EasyTV.AddonName', xbmcaddon.Addon().getAddonInfo('name'))

        if not self._load_items:
            return

        self._load_items = False
        self._log.debug("Window initializing")

        # All skins use control ID 655
        self.name_list = cast(xbmcgui.ControlList, self.getControl(655))

        # Refresh from shared storage if stale (multi-instance sync)
        # This ensures browse window shows fresh data on each open
        if self._data:
            storage = get_storage()
            if storage.needs_refresh():
                show_ids = [show[1] for show in self._data]
                self._log.debug("Cache stale, refreshing before browse window",
                               event="ui.refresh", show_count=len(show_ids))
                try:
                    _, revision = storage.get_ondeck_bulk(show_ids, refresh_display=True)
                    storage.mark_refreshed(revision)
                except Exception as e:
                    self._log.warning("Refresh failed, using cached data",
                                     event="ui.refresh_error", error=str(e))

        self._populate_list()
        assert self.name_list is not None
        self.setFocus(self.name_list)
        self._log.debug("Window initialization complete")
    
    def _populate_list(self) -> None:
        """Populate the list with show data."""
        assert self.name_list is not None
        self.name_list.reset()  # Clear existing items before repopulating
        now = time.time()
        count = 0

        self._log.debug("Window data loaded", show_count=len(self._data))

        for i, show in enumerate(self._data):
            # Check limits
            if count >= MAX_ITEMS_HARD_LIMIT:
                break
            if self._config.limit_shows and i >= self._config.window_length:
                break

            show_id = show[1]
            lastplayed = show[0]

            # Build list item
            list_item = self._create_list_item(show_id, lastplayed, now)
            self.name_list.addItem(list_item)
            count += 1

    def _create_list_item(self, show_id: int, lastplayed: float,
                          now: float) -> xbmcgui.ListItem:
        """
        Create a list item for a show.

        Args:
            show_id: The TV show ID
            lastplayed: Timestamp of last played episode
            now: Current timestamp
            
        Returns:
            Configured ListItem for the show
        """
        prop_prefix = f"EasyTV.{show_id}"
        
        # Get episode properties
        pct_played = WINDOW.getProperty(f"{prop_prefix}.PercentPlayed")
        poster = WINDOW.getProperty(f"{prop_prefix}.Art(tvshow.poster)")
        eptitle = WINDOW.getProperty(f"{prop_prefix}.Title")
        plot = WINDOW.getProperty(f"{prop_prefix}.Plot")
        season = WINDOW.getProperty(f"{prop_prefix}.Season")
        episode = WINDOW.getProperty(f"{prop_prefix}.Episode")
        episode_id = WINDOW.getProperty(f"{prop_prefix}.EpisodeID")
        file_path = WINDOW.getProperty(f"{prop_prefix}.File")
        title = WINDOW.getProperty(f"{prop_prefix}.TVshowTitle")
        fanart = WINDOW.getProperty(f"{prop_prefix}.Art(tvshow.fanart)")
        ep_no = WINDOW.getProperty(f"{prop_prefix}.EpisodeNo")
        num_watched = WINDOW.getProperty(f"{prop_prefix}.CountWatchedEps")
        num_ondeck = WINDOW.getProperty(f"{prop_prefix}.CountonDeckEps")
        genre = WINDOW.getProperty(f"{prop_prefix}.Genre")
        duration_secs = WINDOW.getProperty(f"{prop_prefix}.Duration")

        # Calculate time since last watched (calendar-day aware)
        if lastplayed == 0:
            lw_time = lang(32112)  # "Never"
        else:
            today = date.fromtimestamp(now)
            watched_date = date.fromtimestamp(lastplayed)
            gap_days = (today - watched_date).days
            if gap_days == 0:
                lw_time = lang(32120)  # "Today"
            elif gap_days == 1:
                lw_time = f"1 {lang(32113)}"  # "1 day"
            else:
                lw_time = f"{gap_days} {lang(32114)}"  # "X days"

        # Calculate skipped episodes
        try:
            num_unwatched = int(WINDOW.getProperty(f"{prop_prefix}.CountUnwatchedEps"))
            num_ondeck_int = int(num_ondeck) if num_ondeck else 0
            num_skipped = str(num_unwatched - num_ondeck_int)
        except ValueError:
            num_skipped = '0'

        list_item = xbmcgui.ListItem(label=title, label2=eptitle)
        list_item.setArt({'thumb': poster, 'icon': poster})
        list_item.setProperty("Fanart_Image", fanart)
        list_item.setProperty("numwatched", num_watched)
        list_item.setProperty("numondeck", num_ondeck)
        list_item.setProperty("numskipped", num_skipped)
        list_item.setProperty("lastwatched", lw_time)
        list_item.setProperty("percentplayed", pct_played)
        list_item.setProperty("episodeno", ep_no)
        list_item.setProperty("genre", genre)
        list_item.setProperty("duration", format_duration(duration_secs))

        list_item.setProperty('ID', str(show_id))
        list_item.setProperty("file", file_path)
        list_item.setProperty("EpisodeID", episode_id)
        info_tag = list_item.getVideoInfoTag()
        info_tag.setSeason(int(season) if season else 0)
        info_tag.setEpisode(int(episode) if episode else 0)
        info_tag.setPlot(plot)
        info_tag.setTitle(eptitle)
        
        return list_item

    def _update_list_item(self, item: xbmcgui.ListItem, show_id: int) -> None:
        """Update a list item in-place from current window properties."""
        prop_prefix = f"EasyTV.{show_id}"

        # Re-read all properties from the daemon's updated cache
        pct_played = WINDOW.getProperty(f"{prop_prefix}.PercentPlayed")
        poster = WINDOW.getProperty(f"{prop_prefix}.Art(tvshow.poster)")
        eptitle = WINDOW.getProperty(f"{prop_prefix}.Title")
        plot = WINDOW.getProperty(f"{prop_prefix}.Plot")
        season = WINDOW.getProperty(f"{prop_prefix}.Season")
        episode = WINDOW.getProperty(f"{prop_prefix}.Episode")
        episode_id = WINDOW.getProperty(f"{prop_prefix}.EpisodeID")
        file_path = WINDOW.getProperty(f"{prop_prefix}.File")
        fanart = WINDOW.getProperty(f"{prop_prefix}.Art(tvshow.fanart)")
        ep_no = WINDOW.getProperty(f"{prop_prefix}.EpisodeNo")
        num_watched = WINDOW.getProperty(f"{prop_prefix}.CountWatchedEps")
        num_ondeck = WINDOW.getProperty(f"{prop_prefix}.CountonDeckEps")

        # Calculate skipped episodes
        try:
            num_unwatched = int(WINDOW.getProperty(f"{prop_prefix}.CountUnwatchedEps"))
            num_ondeck_int = int(num_ondeck) if num_ondeck else 0
            num_skipped = str(num_unwatched - num_ondeck_int)
        except ValueError:
            num_skipped = '0'

        genre = WINDOW.getProperty(f"{prop_prefix}.Genre")
        duration_secs = WINDOW.getProperty(f"{prop_prefix}.Duration")

        # Update the item in-place
        item.setLabel2(eptitle)
        item.setArt({'thumb': poster, 'icon': poster})
        item.setProperty("Fanart_Image", fanart)
        item.setProperty("numwatched", num_watched)
        item.setProperty("numondeck", num_ondeck)
        item.setProperty("numskipped", num_skipped)
        item.setProperty("lastwatched", lang(32120))  # "Today"
        item.setProperty("percentplayed", pct_played)
        item.setProperty("episodeno", ep_no)
        item.setProperty("genre", genre)
        item.setProperty("duration", format_duration(duration_secs))
        item.setProperty("file", file_path)
        item.setProperty("EpisodeID", episode_id)
        info_tag = item.getVideoInfoTag()
        info_tag.setSeason(int(season) if season else 0)
        info_tag.setEpisode(int(episode) if episode else 0)
        info_tag.setPlot(plot)
        info_tag.setTitle(eptitle)

    def onAction(self, action: xbmcgui.Action) -> None:
        """
        Handle user actions (key presses, button clicks).
        
        Args:
            action: The action that was triggered
        """
        action_id = action.getId()
        
        if action_id in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self._log.debug("Window closing (back action)")
            self._should_close = True
            self.close()
            
        elif action_id == ACTION_CONTEXT_MENU:
            self._handle_context_menu()
    
    def _handle_context_menu(self) -> None:
        """Show and process the context menu."""
        self._log.debug("Context menu opened")
        
        # Import here to avoid circular imports
        from resources.lib.ui.context_menu import ContextMenuWindow
        
        context_menu = ContextMenuWindow(
            'script-easytv-contextwindow.xml', 
            self._script_path, 
            'Default',
            multiselect=BrowseWindow._multiselect,
            logger=self._log
        )
        
        context_menu.doModal()
        option = context_menu.contextoption
        
        self._log.debug("Context menu option selected", option=option)
        
        if option == CONTEXT_TOGGLE_MULTISELECT:
            self._toggle_multiselect()
        elif option == CONTEXT_PLAY_SELECTION:
            self._play_selection()
        elif option == CONTEXT_PLAY_FROM_HERE:
            self._play_from_here()
        elif option == CONTEXT_EXPORT_SELECTION:
            self._export_selection()
        elif option == CONTEXT_TOGGLE_WATCHED:
            self._toggle_watched()
        elif option == CONTEXT_IGNORE_SHOW:
            pass  # Not implemented yet
        elif option == CONTEXT_UPDATE_LIBRARY:
            self._update_library()
        elif option == CONTEXT_REFRESH:
            self._refresh()
        
        del context_menu
    
    def onClick(self, controlID: int) -> None:
        """
        Handle control clicks.

        Args:
            controlID: The ID of the clicked control
        """
        assert self.name_list is not None
        self._log.debug("Control clicked", control_id=controlID)

        pos = self.name_list.getSelectedPosition()
        
        if not BrowseWindow._multiselect:
            # Single select - play immediately
            play_item = self.name_list.getListItem(pos)
            episode_id = play_item.getProperty('EpisodeID')
            
            if episode_id:
                self._selected_show = int(episode_id)
                self._log.debug("Episode selected for playback", episode_id=self._selected_show)
                self._play_requested = True
                self.close()
        else:
            # Multiselect - toggle selection
            selection = self.name_list.getSelectedItem()
            if selection.isSelected():
                selection.select(False)
                self._log.debug("Item deselected", position=pos)
            else:
                selection.select(True)
                self._log.debug("Item selected", position=pos)
    
    def _toggle_multiselect(self) -> None:
        """Toggle multiselect mode on/off."""
        assert self.name_list is not None
        if BrowseWindow._multiselect:
            BrowseWindow._multiselect = False
            # Deselect all items
            for i in range(self.name_list.size()):
                self.name_list.getListItem(i).select(False)
        else:
            BrowseWindow._multiselect = True
        
        self._log.debug("Multiselect toggled", enabled=BrowseWindow._multiselect)
    
    def _play_selection(self) -> None:
        """Play selected episodes (in multiselect) or current episode."""
        assert self.name_list is not None
        selected_episodes = []
        pos = self.name_list.getSelectedPosition()
        
        for i in range(self.name_list.size()):
            item = self.name_list.getListItem(i)
            if item.isSelected() or i == pos:
                episode_id = item.getProperty('EpisodeID')
                if episode_id:
                    selected_episodes.append(episode_id)
        
        if selected_episodes:
            self._selected_show = selected_episodes
            self._play_requested = True
            self._log.debug("Playing selection", count=len(selected_episodes))
            self.close()
    
    def _play_from_here(self) -> None:
        """Play all episodes from current position to end of list."""
        assert self.name_list is not None
        pos = self.name_list.getSelectedPosition()
        selected_episodes = []
        
        for i in range(pos, self.name_list.size()):
            item = self.name_list.getListItem(i)
            episode_id = item.getProperty('EpisodeID')
            if episode_id:
                selected_episodes.append(episode_id)
        
        if selected_episodes:
            self._selected_show = selected_episodes
            self._play_requested = True
            self._log.debug("Playing from here", start_pos=pos, count=len(selected_episodes))
            self.close()
    
    def _toggle_watched(self) -> None:
        """Mark selected episodes as watched and update list in-place."""
        assert self.name_list is not None
        self._log.debug("Toggling watched status")
        pos = self.name_list.getSelectedPosition()
        query_batch = []
        affected_indices = []

        for i in range(self.name_list.size()):
            item = self.name_list.getListItem(i)
            if item.isSelected() or i == pos:
                episode_id = item.getProperty('EpisodeID')
                if episode_id:
                    self._log.debug("Processing episode", episode_id=episode_id)

                    # Build batch query
                    query = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "VideoLibrary.SetEpisodeDetails",
                        "params": {"episodeid": int(episode_id), "playcount": 1}
                    }
                    query_batch.append(query)
                    affected_indices.append(i)

        if query_batch:
            self._log.debug("Watched status batch query", query_count=len(query_batch))
            json_query(query_batch, False)
            # Wait for daemon to process OnUpdate notifications
            xbmc.sleep(500)
            # Update affected items in-place from refreshed window properties
            for i in affected_indices:
                item = self.name_list.getListItem(i)
                show_id = item.getProperty('ID')
                if show_id:
                    self._update_list_item(item, int(show_id))
    
    def _export_selection(self) -> None:
        """Export selected episodes via episode_exporter."""
        assert self.name_list is not None
        pos = self.name_list.getSelectedPosition()
        self._log.debug("Export starting", position=pos)
        
        export_list = []
        for i in range(self.name_list.size()):
            item = self.name_list.getListItem(i)
            if item.isSelected() or i == pos:
                filename = item.getProperty('file')
                if filename:
                    export_list.append(filename)
        
        if export_list:
            export_string = ':-exporter-:'.join(export_list)
            self._log.debug("Export list prepared", file_count=len(export_list))
            
            addon = xbmcaddon.Addon()
            resource_path = os.path.join(addon.getAddonInfo('path'), 'resources')
            script = os.path.join(resource_path, 'episode_exporter.py')
            xbmc.executebuiltin(f'RunScript({script},{export_string})')
        
        # Clear selection state
        self._selected_show = []
    
    def _update_library(self) -> None:
        """Trigger a Kodi library update."""
        self._log.debug("Library update requested")
        xbmc.executebuiltin('UpdateLibrary(video)')
    
    def _refresh(self) -> None:
        """Refresh the episode list in-place."""
        self._log.debug("Manual refresh requested")
        self._populate_list()
    
    def data_refresh(self) -> None:
        """
        Signal that episode data needs to be refreshed.
        
        Called by BrowseModePlayer when playback ends. Sets the refresh flag
        which causes the browse mode loop to close and reopen the window with
        fresh data from the service's updated window properties.
        """
        self._log.debug("Data refresh requested")
        self._needs_refresh = True
    
    @property
    def selected_show(self) -> Optional[Union[int, list]]:
        """Get the selected show/episode ID(s)."""
        return self._selected_show
    
    @property
    def play_requested(self) -> bool:
        """Check if playback was requested."""
        return self._play_requested
    
    @property
    def should_close(self) -> bool:
        """Check if window should close."""
        return self._should_close
    
    @property
    def needs_refresh(self) -> bool:
        """Check if a refresh was requested."""
        return self._needs_refresh
    
    def update_data(self, data: list) -> None:
        """Update the show data for the next window open."""
        self._data = data

    def reset_state(self) -> None:
        """Reset state for re-showing the window."""
        self._selected_show = None
        self._play_requested = False
        self._should_close = False
        self._needs_refresh = False
        self._load_items = True


def get_skin_xml_file(skin: int) -> str:
    """
    Get the XML file name for the given skin style.

    Args:
        skin: Skin style (0=CardList, 1=Posters, 2=BigScreen, 3=SplitView)

    Returns:
        XML filename for the skin
    """
    skins = {
        0: "script-easytv-cardlist.xml",
        1: "script-easytv-main.xml",
        2: "script-easytv-BigScreenList.xml",
        3: "script-easytv-splitlist.xml"
    }
    return skins.get(skin, "script-easytv-cardlist.xml")
