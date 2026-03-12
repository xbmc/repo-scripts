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
- show_playlist_selection: Present smart playlist chooser
- CountdownDialog: Reusable countdown dialog with live timer

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
from typing import Optional, TYPE_CHECKING, cast

import xbmc
import xbmcgui
import xbmcvfs

from resources.lib.constants import (
    ACTION_NAV_BACK,
    ACTION_PREVIOUS_MENU,
    COUNTDOWN_HEADING,
    COUNTDOWN_MESSAGE,
    COUNTDOWN_NO_BUTTON,
    COUNTDOWN_POSTER,
    COUNTDOWN_YES_BUTTON,
    SECONDS_TO_MS_MULTIPLIER,
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
    
    # Show selection dialog
    # lang(32104) = "Select Playlist"
    input_choice = dialog.select(lang(32104), playlist_list)
    
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
        1  - Heading label (updated by timer)
        2  - Message label
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
            - heading_template: str - Heading with %s for seconds remaining
            - heading_no_timer: str - Heading when duration is 0
            - default_yes: bool - True if Yes is the default on timeout
            - poster: str - Optional poster image path
            - logger: StructuredLogger - Optional logger instance
    """

    def __new__(cls, *args, **kwargs):
        """Create instance, filtering out custom kwargs for parent class."""
        for key in ('message', 'yes_label', 'no_label', 'duration',
                    'heading_template', 'heading_no_timer', 'default_yes',
                    'poster', 'logger'):
            kwargs.pop(key, None)
        return super().__new__(cls, *args, **kwargs)

    def __init__(self, *args, **kwargs):
        """Initialize the countdown dialog."""
        self._message = kwargs.pop('message', '')
        self._yes_label = kwargs.pop('yes_label', '')
        self._no_label = kwargs.pop('no_label', '')
        self._duration = kwargs.pop('duration', 0)
        self._heading_template = kwargs.pop('heading_template', '%s')
        self._heading_no_timer = kwargs.pop('heading_no_timer', '')
        self._default_yes = kwargs.pop('default_yes', True)
        self._poster = kwargs.pop('poster', '')
        self._log = kwargs.pop('logger', None) or _get_log()

        super().__init__(*args, **kwargs)

        # State tracking
        self._closed = False
        self._button_clicked: Optional[int] = None
        self._timer_thread: Optional[threading.Thread] = None

    def onInit(self) -> None:
        """Initialize dialog controls, set labels, and start countdown."""
        # Set message label
        cast(xbmcgui.ControlLabel, self.getControl(COUNTDOWN_MESSAGE)).setLabel(self._message)

        # Set button labels
        cast(xbmcgui.ControlButton, self.getControl(COUNTDOWN_YES_BUTTON)).setLabel(self._yes_label)
        cast(xbmcgui.ControlButton, self.getControl(COUNTDOWN_NO_BUTTON)).setLabel(self._no_label)

        # Set poster image if available and control exists
        if self._poster:
            try:
                cast(xbmcgui.ControlImage, self.getControl(COUNTDOWN_POSTER)).setImage(self._poster)
            except RuntimeError:
                pass  # Control not in this skin XML

        # Set initial heading and focus
        if self._duration > 0:
            cast(xbmcgui.ControlLabel, self.getControl(COUNTDOWN_HEADING)).setLabel(
                self._heading_template % self._duration
            )
            # Focus the non-default button (user must act to override default)
            if self._default_yes:
                self.setFocus(self.getControl(COUNTDOWN_NO_BUTTON))
            else:
                self.setFocus(self.getControl(COUNTDOWN_YES_BUTTON))

            # Start countdown thread
            self._timer_thread = threading.Thread(target=self._countdown_loop, daemon=True)
            self._timer_thread.start()
        else:
            cast(xbmcgui.ControlLabel, self.getControl(COUNTDOWN_HEADING)).setLabel(
                self._heading_no_timer
            )
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
                cast(xbmcgui.ControlLabel, self.getControl(COUNTDOWN_HEADING)).setLabel(
                    self._heading_template % remaining
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
