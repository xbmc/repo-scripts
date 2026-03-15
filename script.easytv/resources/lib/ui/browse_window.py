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
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING, Union, cast

import xbmc
import xbmcgui
import xbmcaddon

from resources.lib.constants import (
    KODI_HOME_WINDOW_ID,
    MAX_ITEMS_HARD_LIMIT,
    SECONDS_PER_DAY,
    SINGULAR_DAY_VALUE,
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
    CONTROL_OK_BUTTON,
    CONTROL_HEADING,
    CONTROL_LIST,
    CONTROL_CANCEL_BUTTON,
    CONTROL_EXTRA_BUTTON2,
)
from resources.lib.data.storage import get_storage
from resources.lib.utils import get_logger, lang, json_query

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
        skin: Skin style (0=DialogSelect, 1=main, 2=BigScreenList)
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
        self._ctrl6failed: bool = False
        
        # Control references (set during onInit)
        self.name_list: Optional[xbmcgui.ControlList] = None
        
        # Clear running list property
        WINDOW.setProperty('runninglist', '')
    
    def onInit(self) -> None:
        """
        Initialize window controls and populate the list.
        
        Called by Kodi when the window is shown. Sets up the list control
        and populates it with show data.
        """
        if not self._load_items:
            return
            
        self._load_items = False
        self._log.debug("Window initializing")
        
        skin = self._config.skin
        
        if skin == 0:
            # DialogSelect skin
            self._setup_dialog_select_skin()
        else:
            # Custom skins (BigScreenList, main)
            self.name_list = cast(xbmcgui.ControlList, self.getControl(655))
        
        if self._ctrl6failed:
            return
        
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
    
    def _setup_dialog_select_skin(self) -> None:
        """Set up controls for the DialogSelect skin style."""
        try:
            ok_button = cast(xbmcgui.ControlButton, self.getControl(CONTROL_OK_BUTTON))
            ok_button.setLabel(lang(32105))

            heading = cast(xbmcgui.ControlButton, self.getControl(CONTROL_HEADING))
            # Get addon name dynamically (supports clones with custom names)
            addon_name = xbmcaddon.Addon().getAddonInfo('name')
            heading.setLabel(addon_name)
            heading.setVisible(True)

            self.name_list = cast(xbmcgui.ControlList, self.getControl(CONTROL_LIST))
            control_3 = self.getControl(3)
            control_3.setVisible(False)
            ok_button.controlRight(self.name_list)
            
            # Hide the Cancel button (ID 7) and Extra button 2 (ID 8)
            # These buttons cause unintended playback when clicked because
            # onClick receives their control ID which falls through to list handling
            try:
                cancel_button = self.getControl(CONTROL_CANCEL_BUTTON)
                cancel_button.setVisible(False)
            except RuntimeError:
                pass  # Button may not exist in all skins
            
            try:
                extra_button2 = self.getControl(CONTROL_EXTRA_BUTTON2)
                extra_button2.setVisible(False)
            except RuntimeError:
                pass  # Button may not exist in all skins
            
        except RuntimeError:
            # Control 3 doesn't work in some skins - fallback needed
            self._ctrl6failed = True
            self._log.warning(
                "DialogSelect skin control setup failed",
                event="ui.fallback",
                skin=self._config.skin
            )
            self.close()
    
    def _populate_list(self) -> None:
        """Populate the list with show data."""
        assert self.name_list is not None
        self.name_list.reset()  # Clear existing items before repopulating
        now = time.time()
        count = 0
        skin = self._config.skin
        
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
            list_item = self._create_list_item(show_id, lastplayed, now, skin)
            self.name_list.addItem(list_item)
            count += 1
    
    def _create_list_item(self, show_id: int, lastplayed: float, 
                          now: float, skin: int) -> xbmcgui.ListItem:
        """
        Create a list item for a show.
        
        Args:
            show_id: The TV show ID
            lastplayed: Timestamp of last played episode
            now: Current timestamp
            skin: Current skin style
            
        Returns:
            Configured ListItem for the show
        """
        prop_prefix = f"EasyTV.{show_id}"
        
        # Get percent played
        pct_played = WINDOW.getProperty(f"{prop_prefix}.PercentPlayed")
        
        # Calculate time since last watched
        if lastplayed == 0:
            lw_time = lang(32112)  # "Never"
        else:
            gap = round((now - lastplayed) / SECONDS_PER_DAY, 1)
            if gap == SINGULAR_DAY_VALUE:
                lw_time = f"{gap} {lang(32113)}"  # "1.0 day"
            else:
                lw_time = f"{gap} {lang(32114)}"  # "X.X days"
        
        # Format percent played label
        if pct_played == '0%' and skin == 0:
            pct = ''
        elif pct_played == '0%':
            pct = pct_played
        else:
            pct = f"{pct_played}, "
        
        label2 = pct if skin != 0 else pct + lw_time
        
        # Get episode properties
        poster = WINDOW.getProperty(f"{prop_prefix}.Art(tvshow.poster)")
        eptitle = WINDOW.getProperty(f"{prop_prefix}.Title")
        plot = WINDOW.getProperty(f"{prop_prefix}.Plot")
        season = WINDOW.getProperty(f"{prop_prefix}.Season")
        episode = WINDOW.getProperty(f"{prop_prefix}.Episode")
        episode_id = WINDOW.getProperty(f"{prop_prefix}.EpisodeID")
        file_path = WINDOW.getProperty(f"{prop_prefix}.File")
        
        if skin != 0:
            # Custom skin - full info
            title = WINDOW.getProperty(f"{prop_prefix}.TVshowTitle")
            fanart = WINDOW.getProperty(f"{prop_prefix}.Art(tvshow.fanart)")
            num_watched = WINDOW.getProperty(f"{prop_prefix}.CountWatchedEps")
            num_ondeck = WINDOW.getProperty(f"{prop_prefix}.CountonDeckEps")
            
            try:
                num_unwatched = int(WINDOW.getProperty(f"{prop_prefix}.CountUnwatchedEps"))
                num_ondeck_int = int(num_ondeck) if num_ondeck else 0
                num_skipped = str(num_unwatched - num_ondeck_int)
            except ValueError:
                num_skipped = '0'
            
            list_item = xbmcgui.ListItem(label=title, label2=eptitle)
            list_item.setArt({'thumb': poster})
            list_item.setProperty("Fanart_Image", fanart)
            list_item.setProperty("numwatched", num_watched)
            list_item.setProperty("numondeck", num_ondeck)
            list_item.setProperty("numskipped", num_skipped)
            list_item.setProperty("lastwatched", lw_time)
            list_item.setProperty("percentplayed", pct_played)
            list_item.setProperty("watched", 'false')
            list_item.setProperty('ID', str(show_id))
        else:
            # DialogSelect skin - minimal info
            ep_no = WINDOW.getProperty(f"{prop_prefix}.EpisodeNo")
            show_title = WINDOW.getProperty(f"{prop_prefix}.TVshowTitle")
            title = f"{show_title} {ep_no}"
            list_item = xbmcgui.ListItem(label=title, label2=label2)
            list_item.setArt({'thumb': poster})
        
        # Common properties
        list_item.setProperty("file", file_path)
        list_item.setProperty("EpisodeID", episode_id)
        list_item.setInfo('video', {
            'season': season,
            'episode': episode,
            'plot': plot,
            'title': eptitle
        })
        list_item.setLabel(title)
        list_item.setArt({'icon': poster})
        
        return list_item
    
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
        
        # Handle Close/Cancel/Extra buttons - all should close without playback
        # CONTROL_OK_BUTTON (5): Our "Close" button
        # CONTROL_CANCEL_BUTTON (7): Standard cancel button (hidden but may still receive clicks)
        # CONTROL_EXTRA_BUTTON2 (8): Extra button (hidden but may still receive clicks)
        if controlID in (CONTROL_OK_BUTTON, CONTROL_CANCEL_BUTTON, CONTROL_EXTRA_BUTTON2):
            self._should_close = True
            self.close()
            return
        
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
        """Mark selected episodes as watched."""
        assert self.name_list is not None
        self._log.debug("Toggling watched status")
        pos = self.name_list.getSelectedPosition()
        query_batch = []
        
        for i in range(self.name_list.size()):
            item = self.name_list.getListItem(i)
            if item.isSelected() or i == pos:
                episode_id = item.getProperty('EpisodeID')
                if episode_id:
                    self._log.debug("Processing episode", episode_id=episode_id)
                    
                    # Update visual state for custom skins
                    if self._config.skin != 0:
                        if item.getProperty('watched') == 'false':
                            item.setProperty("watched", 'true')
                    
                    # Build batch query
                    query = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "VideoLibrary.SetEpisodeDetails",
                        "params": {"episodeid": int(episode_id), "playcount": 1}
                    }
                    query_batch.append(query)
        
        if query_batch:
            self._log.debug("Watched status batch query", query_count=len(query_batch))
            json_query(query_batch, False)
    
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
        """Request a refresh of the episode list."""
        self._log.debug("Manual refresh requested")
        self._needs_refresh = True
        self.close()
    
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
    
    @property
    def ctrl6failed(self) -> bool:
        """Check if DialogSelect control setup failed."""
        return self._ctrl6failed
    
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
        skin: Skin style (0=DialogSelect, 1=main, 2=BigScreenList)
        
    Returns:
        XML filename for the skin
    """
    skins = {
        1: "script-easytv-main.xml",
        2: "script-easytv-BigScreenList.xml"
    }
    return skins.get(skin, "DialogSelect.xml")
