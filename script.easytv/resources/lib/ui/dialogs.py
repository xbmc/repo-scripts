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
EasyTV Dialog Helpers.

Provides common dialog functions and custom dialog classes:
- show_confirm: Present themed confirmation dialog (replaces Dialog.yesno)
- show_select: Present themed selection dialog (replaces Dialog.select)
- show_playlist_selection: Present smart playlist chooser
- CountdownDialog: Reusable countdown dialog with live timer
- ConfirmDialog: Themed yes/no confirmation dialog
- SelectDialog: Themed item selection dialog
- ShowSelectorDialog: Multi-select show chooser with search filtering

Extracted from default.py as part of modularization.

Logging:
    Logger: 'ui' (via get_logger)
    Key events:
        - ui.dialog_open (DEBUG): Dialog opened
        - ui.dialog_select (DEBUG): User made selection
        - ui.dialog_cancel (DEBUG): User cancelled dialog
        - ui.countdown_timeout (DEBUG): Countdown timer expired
    See LOGGING.md for full guidelines.
"""
from __future__ import annotations

import os
import threading
import xml.etree.ElementTree as ET
from typing import List, Optional, TYPE_CHECKING, cast

import xbmc
import xbmcgui
import xbmcvfs

from resources.lib.constants import (
    ACTION_NAV_BACK,
    ACTION_PREVIOUS_MENU,
    CONFIRM_HEADING,
    CONFIRM_MESSAGE,
    CONFIRM_NO_BUTTON,
    CONFIRM_YES_BUTTON,
    COUNTDOWN_HEADING,
    COUNTDOWN_MESSAGE,
    COUNTDOWN_NO_BUTTON,
    COUNTDOWN_POSTER,
    COUNTDOWN_SUBTITLE,
    COUNTDOWN_TIMER_LABEL,
    COUNTDOWN_YES_BUTTON,
    SECONDS_TO_MS_MULTIPLIER,
    SELECT_HEADING,
    SELECT_LIST,
    SELECTOR_CANCEL,
    SELECTOR_CLEAR_SEARCH,
    SELECTOR_ENABLE_ALL,
    SELECTOR_HEADING,
    SELECTOR_IGNORE_ALL,
    SELECTOR_LIST,
    SELECTOR_SAVE,
    SELECTOR_SEARCH,
    THEME_COLORS,
    SETTING_THEME,
)
from resources.lib.utils import get_logger, json_query, lang
from resources.lib.data.queries import get_playlist_files_query

if TYPE_CHECKING:
    from resources.lib.utils import StructuredLogger


# Prefix for auto-generated EasyTV TVShow playlists (excluded from selector)
# User-created playlists should not use this prefix
EASYTV_TVSHOW_PREFIX = "EasyTV - TVShow - "


# Module-level logger (initialized lazily)
_log: Optional[StructuredLogger] = None


def _get_log() -> StructuredLogger:
    """Get or create the module logger."""
    global _log
    if _log is None:
        _log = get_logger('ui')
    return _log


def _get_playlist_type(filepath: str) -> Optional[str]:
    """
    Read a .xsp playlist file and return its type.
    
    Parses the smart playlist XML to extract the type attribute from the
    root <smartplaylist> element.
    
    Args:
        filepath: Full path to the playlist file (special:// format OK).
    
    Returns:
        Playlist type ('movies', 'tvshows', 'episodes') or None if unreadable.
    
    Example:
        >>> _get_playlist_type('special://profile/playlists/video/Action.xsp')
        'movies'
    """
    log = _get_log()
    
    try:
        # Use xbmcvfs.File for Kodi path compatibility
        file_handle = xbmcvfs.File(filepath, 'r')
        try:
            content = file_handle.read()
        finally:
            file_handle.close()
        
        if not content:
            log.debug("Playlist file empty or unreadable", filepath=filepath)
            return None
        
        # Parse XML and get type attribute
        root = ET.fromstring(content)
        playlist_type = root.get('type')
        
        log.debug("Playlist type detected", filepath=filepath, type=playlist_type)
        return playlist_type
        
    except ET.ParseError as e:
        log.warning("Playlist XML parse error", filepath=filepath, error=str(e))
        return None
    except Exception as e:
        log.warning("Playlist read error", filepath=filepath, error=str(e))
        return None


def show_playlist_selection(
    dialog: Optional[xbmcgui.Dialog] = None,
    logger: Optional[StructuredLogger] = None,
    playlist_type: Optional[str] = None,
) -> str:
    """
    Launch a selection dialog populated with video smart playlists.
    
    Queries Kodi for all video playlists in the playlists directory
    and presents them in a selection dialog for the user to choose.
    Optionally filters playlists by type (tvshows, movies, episodes).
    
    Args:
        dialog: Optional Dialog instance. If None, creates one.
        logger: Optional logger instance. If None, uses module logger.
        playlist_type: Optional filter. If provided, only shows playlists
                      of this type ('tvshows', 'movies', 'episodes').
    
    Returns:
        The file path of the selected playlist, or 'empty' if:
        - No playlists found (or none match the type filter)
        - User cancelled the dialog
    """
    log = logger or _get_log()
    
    if dialog is None:
        dialog = xbmcgui.Dialog()
    
    log.debug("Playlist selection dialog opening", filter_type=playlist_type)
    
    # Query Kodi for available playlists
    result = json_query(get_playlist_files_query(), True)
    playlist_files = result.get('files') if result else None
    
    if not playlist_files:
        log.debug("No playlists found")
        return 'empty'
    
    # Build dict for label -> file path mapping
    # Optionally filter by playlist type
    # Exclude auto-generated EasyTV TVShow playlists
    playlist_file_dict = {}
    excluded_count = 0
    for item in playlist_files:
        # Extract filename from path for exclusion check
        filename = os.path.basename(item['file'])
        
        # Exclude auto-generated EasyTV TVShow playlists
        # These are for skin widgets, not for user selection
        if filename.startswith(EASYTV_TVSHOW_PREFIX):
            excluded_count += 1
            continue
        
        if playlist_type is not None:
            # Check playlist type matches filter
            detected_type = _get_playlist_type(item['file'])
            if detected_type != playlist_type:
                continue
        playlist_file_dict[item['label']] = item['file']
    
    if excluded_count > 0:
        log.debug("Excluded auto-generated EasyTV TVShow playlists", count=excluded_count)
    
    # Handle no matching playlists after filtering
    if not playlist_file_dict:
        if playlist_type == 'tvshows':
            # 32600 = "No TV show playlists found"
            dialog.ok("EasyTV", lang(32600))
        elif playlist_type == 'movies':
            # 32601 = "No movie playlists found"
            dialog.ok("EasyTV", lang(32601))
        else:
            log.debug("No playlists found matching filter", filter_type=playlist_type)
        return 'empty'
    
    playlist_list = sorted(playlist_file_dict.keys())
    
    log.debug("Playlist selection dialog displayed", 
              count=len(playlist_list), filter_type=playlist_type)
    
    # Show selection dialog using themed SelectDialog
    # lang(32104) = "Select Playlist"
    input_choice = show_select(lang(32104), playlist_list)

    # Handle user cancellation (input_choice == -1)
    if input_choice < 0:
        log.debug("Playlist selection cancelled by user")
        return 'empty'

    selected_playlist = playlist_file_dict[playlist_list[input_choice]]
    log.debug("Playlist selection made", playlist=selected_playlist)

    return selected_playlist


class CountdownDialog(xbmcgui.WindowXMLDialog):
    """
    Reusable countdown dialog with live timer updates.

    A WindowXMLDialog subclass that provides:
    - A daemon timer thread that updates the heading label every second
    - Two-button layout with configurable labels and default action
    - A result property indicating whether the affirmative action was chosen

    Control IDs (must match skin XML):
        1  - Heading label (static, e.g. addon name)
        2  - Message label
        3  - Timer label (auto-close countdown, below buttons)
        10 - "Yes" button (left)
        11 - "No" button (right)
        20 - Poster image (optional, used by next episode dialog)

    Args:
        *args: Positional args passed to WindowXMLDialog.
        **kwargs: Keyword args. Custom kwargs:
            - message: str - Dialog message text
            - yes_label: str - Label for the Yes button (left)
            - no_label: str - Label for the No button (right)
            - duration: int - Countdown seconds (0 = no timer)
            - heading: str - Static heading text (e.g. addon/clone name)
            - timer_template: str - Timer format with %s for seconds
            - default_yes: bool - True if Yes is the default on timeout
            - poster: str - Optional poster image path
            - logger: StructuredLogger - Optional logger instance
    """

    def __new__(cls, *args, **kwargs):
        """Create instance, filtering out custom kwargs for parent class."""
        for key in ('message', 'subtitle', 'yes_label', 'no_label', 'duration',
                    'heading', 'timer_template', 'default_yes',
                    'poster', 'addon_id', 'logger'):
            kwargs.pop(key, None)
        return super().__new__(cls, *args, **kwargs)

    def __init__(self, *args, **kwargs):
        """Initialize the countdown dialog."""
        self._message = kwargs.pop('message', '')
        self._subtitle = kwargs.pop('subtitle', '')
        self._yes_label = kwargs.pop('yes_label', '')
        self._no_label = kwargs.pop('no_label', '')
        self._duration = kwargs.pop('duration', 0)
        self._heading = kwargs.pop('heading', '')
        self._timer_template = kwargs.pop('timer_template', '')
        self._default_yes = kwargs.pop('default_yes', True)
        self._poster = kwargs.pop('poster', '')
        self._addon_id: Optional[str] = kwargs.pop('addon_id', None)
        self._log = kwargs.pop('logger', None) or _get_log()

        super().__init__(*args, **kwargs)

        # State tracking
        self._closed = False
        self._button_clicked: Optional[int] = None
        self._timer_thread: Optional[threading.Thread] = None

    def onInit(self) -> None:
        """Initialize dialog controls, set labels, and start countdown."""
        # Set theme color properties for skin XML (uses source addon for clones)
        from resources.lib.ui import apply_theme
        apply_theme(self, addon_id=self._addon_id)

        # Get theme colors for button styling ($INFO doesn't resolve in
        # WindowXMLDialog focusedcolor, so we set it via Python)
        import xbmcaddon
        addon = xbmcaddon.Addon(self._addon_id) if self._addon_id else xbmcaddon.Addon()
        theme = addon.getSetting(SETTING_THEME) or '0'
        colors = THEME_COLORS.get(theme, THEME_COLORS['0'])
        focused_color = colors['EasyTV.ButtonTextFocused']

        # Set message label
        cast(xbmcgui.ControlLabel, self.getControl(COUNTDOWN_MESSAGE)).setLabel(self._message)

        # Set subtitle label (secondary text, smaller + dimmer)
        # Always set to clear the default "-" placeholder from the XML
        try:
            cast(xbmcgui.ControlLabel, self.getControl(COUNTDOWN_SUBTITLE)).setLabel(
                self._subtitle)
        except RuntimeError:
            pass  # Control not in this skin XML

        # Set button labels with focusedColor
        cast(xbmcgui.ControlButton, self.getControl(COUNTDOWN_YES_BUTTON)).setLabel(
            self._yes_label, focusedColor=focused_color)
        cast(xbmcgui.ControlButton, self.getControl(COUNTDOWN_NO_BUTTON)).setLabel(
            self._no_label, focusedColor=focused_color)

        # Set poster image if available and control exists
        if self._poster:
            try:
                cast(xbmcgui.ControlImage, self.getControl(COUNTDOWN_POSTER)).setImage(self._poster)
            except RuntimeError:
                pass  # Control not in this skin XML

        # Set static heading (addon/clone name)
        cast(xbmcgui.ControlLabel, self.getControl(COUNTDOWN_HEADING)).setLabel(
            self._heading
        )

        # Set timer label and focus
        if self._duration > 0:
            try:
                cast(xbmcgui.ControlLabel, self.getControl(COUNTDOWN_TIMER_LABEL)).setLabel(
                    self._timer_template % self._duration
                )
            except RuntimeError:
                pass  # Timer control not in this skin XML

            # Focus the non-default button (user must act to override default)
            if self._default_yes:
                self.setFocus(self.getControl(COUNTDOWN_NO_BUTTON))
            else:
                self.setFocus(self.getControl(COUNTDOWN_YES_BUTTON))

            # Start countdown thread
            self._timer_thread = threading.Thread(target=self._countdown_loop, daemon=True)
            self._timer_thread.start()
        else:
            # Hide timer label when no countdown
            try:
                cast(xbmcgui.ControlLabel, self.getControl(COUNTDOWN_TIMER_LABEL)).setLabel('')
            except RuntimeError:
                pass
            # No timer — focus Yes button as natural default
            self.setFocus(self.getControl(COUNTDOWN_YES_BUTTON))

    def _countdown_loop(self) -> None:
        """Daemon thread: count down, update heading, close on expiry."""
        remaining = self._duration
        while remaining > 0 and not self._closed:
            xbmc.sleep(SECONDS_TO_MS_MULTIPLIER)
            if self._closed:
                return
            remaining -= 1
            try:
                cast(xbmcgui.ControlLabel, self.getControl(COUNTDOWN_TIMER_LABEL)).setLabel(
                    self._timer_template % remaining
                )
            except RuntimeError:
                return  # Dialog already destroyed

        if not self._closed:
            self._log.debug("Countdown expired", event="ui.countdown_timeout")
            self.close()

    def onClick(self, controlID: int) -> None:
        """Handle button clicks."""
        if controlID in (COUNTDOWN_YES_BUTTON, COUNTDOWN_NO_BUTTON):
            self._button_clicked = controlID
            self._closed = True
            self.close()

    def onAction(self, action: xbmcgui.Action) -> None:
        """Handle ESC/back as decline."""
        if action.getId() in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self._button_clicked = COUNTDOWN_NO_BUTTON
            self._closed = True
            self.close()

    @property
    def result(self) -> bool:
        """
        Whether the affirmative action was chosen.

        Returns True if:
        - User clicked Yes button, OR
        - Timer expired and default_yes is True

        Returns False otherwise (No button, ESC, or timer expired with
        default_yes False).
        """
        if self._button_clicked == COUNTDOWN_YES_BUTTON:
            return True
        if self._button_clicked == COUNTDOWN_NO_BUTTON:
            return False
        # Timeout — use default
        return self._default_yes


class ConfirmDialog(xbmcgui.WindowXMLDialog):
    """
    Themed yes/no confirmation dialog.

    Replaces Dialog.yesno() with a themed, accent-colored dialog.

    Control IDs (must match script-easytv-confirm.xml):
        1  - Heading label
        2  - Message label
        10 - "Yes" button (left)
        11 - "No" button (right)
    """

    def __new__(cls, *args, **kwargs):
        """Create instance, filtering out custom kwargs for parent class."""
        for key in ('heading', 'message', 'yes_label', 'no_label', 'addon_id'):
            kwargs.pop(key, None)
        return super().__new__(cls, *args, **kwargs)

    def __init__(self, *args, **kwargs):
        """Initialize the confirm dialog."""
        self._heading = kwargs.pop('heading', '')
        self._message = kwargs.pop('message', '')
        self._yes_label = kwargs.pop('yes_label', '')
        self._no_label = kwargs.pop('no_label', '')
        self._addon_id: Optional[str] = kwargs.pop('addon_id', None)
        super().__init__(*args, **kwargs)
        self._result = False

    def onInit(self) -> None:
        """Initialize dialog controls and set labels."""
        from resources.lib.ui import apply_theme
        apply_theme(self, addon_id=self._addon_id)

        import xbmcaddon
        addon = xbmcaddon.Addon(self._addon_id) if self._addon_id else xbmcaddon.Addon()
        theme = addon.getSetting(SETTING_THEME) or '0'
        colors = THEME_COLORS.get(theme, THEME_COLORS['0'])
        focused_color = colors['EasyTV.ButtonTextFocused']

        cast(xbmcgui.ControlLabel, self.getControl(CONFIRM_HEADING)).setLabel(
            self._heading)
        cast(xbmcgui.ControlLabel, self.getControl(CONFIRM_MESSAGE)).setLabel(
            self._message)
        cast(xbmcgui.ControlButton, self.getControl(CONFIRM_YES_BUTTON)).setLabel(
            self._yes_label, focusedColor=focused_color)
        cast(xbmcgui.ControlButton, self.getControl(CONFIRM_NO_BUTTON)).setLabel(
            self._no_label, focusedColor=focused_color)
        self.setFocus(self.getControl(CONFIRM_YES_BUTTON))

    def onClick(self, controlID: int) -> None:
        """Handle button clicks."""
        if controlID == CONFIRM_YES_BUTTON:
            self._result = True
            self.close()
        elif controlID == CONFIRM_NO_BUTTON:
            self._result = False
            self.close()

    def onAction(self, action: xbmcgui.Action) -> None:
        """Handle ESC/back as decline."""
        if action.getId() in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self._result = False
            self.close()

    @property
    def result(self) -> bool:
        """Whether the user clicked Yes."""
        return self._result


def show_confirm(
    heading: str,
    message: str,
    yes_label: str = '',
    no_label: str = '',
    addon_id: Optional[str] = None,
) -> bool:
    """
    Show a themed confirmation dialog.

    Drop-in replacement for Dialog.yesno() with EasyTV theming.

    Args:
        heading: Dialog heading text.
        message: Dialog message text.
        yes_label: Label for the Yes button. Defaults to lang(32078) "Yes".
        no_label: Label for the No button. Defaults to lang(32079) "No".
        addon_id: Optional addon ID for theme (clone support).

    Returns:
        True if the user clicked Yes, False otherwise.
    """
    import xbmcaddon
    addon = xbmcaddon.Addon(addon_id) if addon_id else xbmcaddon.Addon()
    addon_path = addon.getAddonInfo('path')

    dlg = ConfirmDialog(
        'script-easytv-confirm.xml', addon_path, 'Default',
        heading=heading,
        message=message,
        yes_label=yes_label or lang(32078),
        no_label=no_label or lang(32079),
        addon_id=addon_id,
    )
    dlg.doModal()
    result = dlg.result
    del dlg
    return result


class SelectDialog(xbmcgui.WindowXMLDialog):
    """
    Themed item selection dialog.

    Replaces Dialog.select() with a themed, accent-colored dialog.

    Control IDs (must match script-easytv-select.xml):
        1   - Heading label
        100 - Scrollable list
    """

    def __new__(cls, *args, **kwargs):
        """Create instance, filtering out custom kwargs for parent class."""
        for key in ('heading', 'items', 'addon_id'):
            kwargs.pop(key, None)
        return super().__new__(cls, *args, **kwargs)

    def __init__(self, *args, **kwargs):
        """Initialize the select dialog."""
        self._heading = kwargs.pop('heading', '')
        self._items: List[str] = kwargs.pop('items', [])
        self._addon_id: Optional[str] = kwargs.pop('addon_id', None)
        super().__init__(*args, **kwargs)
        self._result = -1

    def onInit(self) -> None:
        """Initialize dialog controls and populate the list."""
        from resources.lib.ui import apply_theme
        apply_theme(self, addon_id=self._addon_id)

        cast(xbmcgui.ControlLabel, self.getControl(SELECT_HEADING)).setLabel(
            self._heading)

        name_list = cast(xbmcgui.ControlList, self.getControl(SELECT_LIST))
        for item_text in self._items:
            name_list.addItem(xbmcgui.ListItem(item_text))
        self.setFocus(name_list)

    def onClick(self, controlID: int) -> None:
        """Handle list item clicks."""
        if controlID == SELECT_LIST:
            name_list = cast(xbmcgui.ControlList, self.getControl(SELECT_LIST))
            self._result = name_list.getSelectedPosition()
            self.close()

    def onAction(self, action: xbmcgui.Action) -> None:
        """Handle ESC/back as cancel."""
        if action.getId() in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self._result = -1
            self.close()

    @property
    def result(self) -> int:
        """Selected index, or -1 if cancelled."""
        return self._result


def show_select(
    heading: str,
    items: List[str],
    addon_id: Optional[str] = None,
) -> int:
    """
    Show a themed selection dialog.

    Drop-in replacement for Dialog.select() with EasyTV theming.

    Args:
        heading: Dialog heading text.
        items: List of item labels to display.
        addon_id: Optional addon ID for theme (clone support).

    Returns:
        Selected item index, or -1 if cancelled.
    """
    import xbmcaddon
    addon = xbmcaddon.Addon(addon_id) if addon_id else xbmcaddon.Addon()
    addon_path = addon.getAddonInfo('path')

    dlg = SelectDialog(
        'script-easytv-select.xml', addon_path, 'Default',
        heading=heading,
        items=items,
        addon_id=addon_id,
    )
    dlg.doModal()
    result = dlg.result
    del dlg
    return result


class ShowSelectorDialog(xbmcgui.WindowXMLDialog):
    """
    Multi-select show chooser with search-as-you-type filtering.

    Replaces the xGUI class in selector.py with a custom themed dialog
    that supports search filtering and explicit Enable All/Ignore All
    buttons that act on filtered results only.

    Control IDs (must match script-easytv-showselector.xml):
        1   - Heading label
        2   - Search edit control
        10  - Enable All button
        11  - Ignore All button
        100 - Show list
        20  - Cancel button
        21  - Save button
    """

    def __new__(cls, *args, **kwargs):
        """Create instance, filtering out custom kwargs for parent class."""
        for key in ('heading', 'all_shows_data', 'current_list',
                    'addon_id', 'logger'):
            kwargs.pop(key, None)
        return super().__new__(cls, *args, **kwargs)

    def __init__(self, *args, **kwargs):
        """Initialize the show selector dialog."""
        self._heading = kwargs.pop('heading', '')
        self._all_shows_data = kwargs.pop('all_shows_data', [])
        self._current_list = kwargs.pop('current_list', [])
        self._addon_id: Optional[str] = kwargs.pop('addon_id', None)
        self._log = kwargs.pop('logger', None) or _get_log()
        super().__init__(*args, **kwargs)

        # Track selection by show_id
        self._selected = {
            show_id: (show_id in self._current_list)
            for _, show_id, _ in self._all_shows_data
        }
        self._search_text = ''
        self._filtered_shows = list(self._all_shows_data)
        self._closed = False
        self._saved = False
        self._hint_text = 'Search shows...'

    def onInit(self) -> None:
        """Initialize dialog controls and populate the list."""
        from resources.lib.ui import apply_theme
        apply_theme(self, addon_id=self._addon_id)

        import xbmcaddon
        addon = xbmcaddon.Addon(self._addon_id) if self._addon_id else xbmcaddon.Addon()
        theme = addon.getSetting(SETTING_THEME) or '0'
        colors = THEME_COLORS.get(theme, THEME_COLORS['0'])
        focused_color = colors['EasyTV.ButtonTextFocused']

        # Heading
        cast(xbmcgui.ControlLabel, self.getControl(SELECTOR_HEADING)).setLabel(
            self._heading)

        # Buttons
        # Search edit hint text is set in XML via <hinttext>
        cast(xbmcgui.ControlButton, self.getControl(SELECTOR_ENABLE_ALL)).setLabel(
            lang(32732), focusedColor=focused_color)
        cast(xbmcgui.ControlButton, self.getControl(SELECTOR_IGNORE_ALL)).setLabel(
            lang(32733), focusedColor=focused_color)
        cast(xbmcgui.ControlButton, self.getControl(SELECTOR_CLEAR_SEARCH)).setLabel(
            'X', focusedColor=focused_color)
        cast(xbmcgui.ControlButton, self.getControl(SELECTOR_CANCEL)).setLabel(
            lang(32734), focusedColor=focused_color)
        cast(xbmcgui.ControlButton, self.getControl(SELECTOR_SAVE)).setLabel(
            lang(32170), focusedColor=focused_color)

        # Populate list and focus it
        self._populate_list()
        self.setFocus(self.getControl(SELECTOR_LIST))

    def _filter_shows(self, search_text: str) -> None:
        """Filter the show list based on search text."""
        if search_text:
            search_lower = search_text.lower()
            self._filtered_shows = [
                s for s in self._all_shows_data
                if search_lower in s[0].lower()
            ]
        else:
            self._filtered_shows = list(self._all_shows_data)
        self._populate_list()

    def _populate_list(self) -> None:
        """Populate the list control with filtered shows."""
        name_list = cast(xbmcgui.ControlList, self.getControl(SELECTOR_LIST))
        name_list.reset()

        for show_name, show_id, thumbnail in self._filtered_shows:
            item = xbmcgui.ListItem(show_name)
            item.setArt({'thumb': thumbnail})
            item.setProperty('show_id', str(show_id))
            name_list.addItem(item)

            # Set selection state
            if self._selected.get(show_id, False):
                name_list.getListItem(name_list.size() - 1).select(True)

    def onClick(self, controlID: int) -> None:
        """Handle button and list clicks."""
        if self._log:
            self._log.debug("ShowSelector onClick", controlID=controlID)
        if controlID == SELECTOR_SAVE:
            self._saved = True
            self._closed = True
            self.close()
        elif controlID == SELECTOR_CANCEL:
            self._closed = True
            self.close()
        elif controlID == SELECTOR_SEARCH:
            search_ctrl = cast(xbmcgui.ControlEdit,
                               self.getControl(SELECTOR_SEARCH))
            self._search_text = search_ctrl.getText()
            self._filter_shows(self._search_text)
        elif controlID == SELECTOR_CLEAR_SEARCH:
            self._search_text = ''
            cast(xbmcgui.ControlEdit,
                 self.getControl(SELECTOR_SEARCH)).setText('')
            self._filter_shows('')
            self.setFocus(self.getControl(SELECTOR_LIST))
        elif controlID == SELECTOR_ENABLE_ALL:
            for _, show_id, _ in self._filtered_shows:
                self._selected[show_id] = True
            self._populate_list()
        elif controlID == SELECTOR_IGNORE_ALL:
            for _, show_id, _ in self._filtered_shows:
                self._selected[show_id] = False
            self._populate_list()
        elif controlID == SELECTOR_LIST:
            name_list = cast(xbmcgui.ControlList, self.getControl(SELECTOR_LIST))
            pos = name_list.getSelectedPosition()
            if 0 <= pos < len(self._filtered_shows):
                show_id = self._filtered_shows[pos][1]
                self._selected[show_id] = not self._selected.get(show_id, False)
                item = name_list.getSelectedItem()
                if item is not None:
                    item.select(self._selected[show_id])

    def onAction(self, action: xbmcgui.Action) -> None:
        """Handle ESC/back as cancel and live search filtering."""
        if action.getId() in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self._closed = True
            self.close()
            return
        # Live filter: check if search text changed while edit is focused
        try:
            focused_id = self.getFocusId()
        except RuntimeError:
            return
        if focused_id == SELECTOR_SEARCH:
            search_ctrl = cast(xbmcgui.ControlEdit,
                               self.getControl(SELECTOR_SEARCH))
            current_text = search_ctrl.getText()
            if current_text != self._search_text:
                self._search_text = current_text
                self._filter_shows(self._search_text)

    @property
    def saved(self) -> bool:
        """Whether the user clicked Save."""
        return self._saved

    @property
    def selected_ids(self) -> List[int]:
        """Return list of selected show IDs."""
        return [show_id for show_id, selected in self._selected.items()
                if selected]
