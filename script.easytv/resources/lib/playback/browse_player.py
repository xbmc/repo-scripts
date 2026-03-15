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
EasyTV Browse Mode Player.

Provides a player class that integrates with the BrowseWindow to handle
playback events. When playback starts, it closes the browse window.
When playback ends, it triggers a data refresh so the user sees updated
episode information.

Extracted from default.py as part of modularization.

Logging:
    Logger: 'playback' (via get_logger)
    Key events:
        - playback.browse_start (DEBUG): Playback started in browse mode
        - playback.browse_end (DEBUG): Playback ended in browse mode
    See LOGGING.md for full guidelines.
"""
from __future__ import annotations

from typing import Optional, TYPE_CHECKING

import xbmc

from resources.lib.utils import get_logger

if TYPE_CHECKING:
    from resources.lib.ui.browse_window import BrowseWindow
    from resources.lib.utils import StructuredLogger


# Module-level logger (initialized lazily)
_log: Optional[StructuredLogger] = None


def _get_log() -> StructuredLogger:
    """Get or create the module logger."""
    global _log
    if _log is None:
        _log = get_logger('playback')
    return _log


class BrowseModePlayer(xbmc.Player):
    """
    Player for browse mode that coordinates with the BrowseWindow.
    
    This player monitors playback events and updates the browse window
    accordingly:
    - On playback start: Closes the window (video takes over screen)
    - On playback end/stop: Triggers data refresh to update episode info
    
    This allows users to see the updated "next episode" after watching
    something, without needing to manually refresh.
    
    Args:
        parent: The BrowseWindow instance to coordinate with
        *args: Additional positional args passed to xbmc.Player
        **kwargs: Additional keyword args passed to xbmc.Player
    
    Example:
        ```python
        browse_window = BrowseWindow(...)
        player = BrowseModePlayer(parent=browse_window)
        
        # When user selects episode:
        player.play(xbmc.PlayList(1))
        
        # Player automatically:
        # - Closes browse_window on playback start
        # - Calls browse_window.data_refresh() on playback end
        ```
    """
    
    def __init__(self, parent: BrowseWindow, *args, **kwargs):
        """
        Initialize the browse mode player.
        
        Args:
            parent: The BrowseWindow to coordinate with
            *args: Additional args for xbmc.Player
            **kwargs: Additional kwargs for xbmc.Player
        """
        super().__init__(*args, **kwargs)
        self._browse_window = parent
        self._log = _get_log()
    
    def onPlayBackStarted(self) -> None:
        """
        Handle playback started event.
        
        Closes the browse window so the video player takes over the screen.
        """
        self._log.debug("Playback started (browse mode)")
        self._browse_window.close()
    
    def onPlayBackStopped(self) -> None:
        """
        Handle playback stopped event (user stopped playback).
        
        Delegates to onPlayBackEnded for consistent behavior.
        """
        self.onPlayBackEnded()
    
    def onPlayBackEnded(self) -> None:
        """
        Handle playback ended event (video finished naturally).
        
        Triggers a data refresh on the browse window so the user sees
        updated episode information (e.g., next unwatched episode).
        """
        self._log.debug("Playback ended (browse mode)")
        self._browse_window.data_refresh()
    
    @property
    def browse_window(self) -> BrowseWindow:
        """Get the associated browse window."""
        return self._browse_window
