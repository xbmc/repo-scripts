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
EasyTV Context Menu Window.

Provides a context menu dialog for the browse window with options like:
- Toggle multiselect mode
- Play selection / Play from here
- Export selection
- Toggle watched status
- Update library
- Refresh

Extracted from default.py as part of modularization.

Logging:
    Logger: 'ui' (via get_logger)
    Key events:
        - ui.context_init (DEBUG): Context menu initialized
        - ui.context_select (DEBUG): User selected context option
    See LOGGING.md for full guidelines.
"""
from __future__ import annotations

from typing import Optional, TYPE_CHECKING, Union, cast

import xbmc
import xbmcgui

from resources.lib.constants import (
    CONTEXT_TOGGLE_DELAY_MS,
    CONTEXT_TOGGLE_MULTISELECT,
    CONTEXT_PLAY_SELECTION,
    CONTEXT_PLAY_FROM_HERE,
    CONTEXT_EXPORT_SELECTION,
    CONTEXT_TOGGLE_WATCHED,
    CONTEXT_UPDATE_LIBRARY,
    CONTEXT_REFRESH,
)
from resources.lib.utils import get_logger, lang

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


class ContextMenuWindow(xbmcgui.WindowXMLDialog):
    """
    Context menu dialog for the browse window.
    
    Displays options for the user to interact with the current selection:
    - Toggle between single and multi-select modes
    - Play selected episodes or play from current position
    - Export selected episodes
    - Toggle watched/unwatched status
    - Update Kodi library
    - Refresh the episode list
    
    The selected option is stored in `contextoption` after the dialog closes.
    
    Args:
        *args: Positional args passed to WindowXMLDialog.
        **kwargs: Keyword args. Special kwargs:
            - multiselect: bool - Whether multiselect mode is active
            - logger: StructuredLogger - Optional logger instance
    """
    
    def __new__(cls, *args, **kwargs):
        """Create instance, filtering out custom kwargs for parent class."""
        # Remove our custom kwargs before calling parent
        kwargs.pop('multiselect', None)
        kwargs.pop('logger', None)
        return super().__new__(cls, *args, **kwargs)
    
    def __init__(self, *args, **kwargs):
        """Initialize the context menu window."""
        # Extract our custom kwargs
        self._multiselect = kwargs.pop('multiselect', False)
        self._log = kwargs.pop('logger', None) or _get_log()
        
        # Call parent init
        super().__init__(*args, **kwargs)
        
        # Will be set during onInit
        self.contextoption: Union[int, str] = ''
    
    def onInit(self) -> None:
        """
        Initialize the context menu controls.
        
        Sets up button labels based on current multiselect state.
        """
        self.contextoption = ''
        
        self._log.debug("Context window init", multiselect=self._multiselect)
        
        if self._multiselect:
            # Multiselect mode - show options for selection
            cast(xbmcgui.ControlButton, self.getControl(CONTEXT_TOGGLE_MULTISELECT)).setLabel(lang(32200))
            cast(xbmcgui.ControlButton, self.getControl(CONTEXT_PLAY_SELECTION)).setLabel(lang(32202))
            cast(xbmcgui.ControlButton, self.getControl(CONTEXT_EXPORT_SELECTION)).setLabel(lang(32203))
        else:
            # Single select mode
            cast(xbmcgui.ControlButton, self.getControl(CONTEXT_TOGGLE_MULTISELECT)).setLabel(lang(32201))
            cast(xbmcgui.ControlButton, self.getControl(CONTEXT_PLAY_SELECTION)).setLabel(lang(32204))
            cast(xbmcgui.ControlButton, self.getControl(CONTEXT_EXPORT_SELECTION)).setLabel(lang(32205))

        cast(xbmcgui.ControlButton, self.getControl(CONTEXT_PLAY_FROM_HERE)).setLabel(lang(32206))
        cast(xbmcgui.ControlButton, self.getControl(CONTEXT_TOGGLE_WATCHED)).setLabel(lang(32207))
        cast(xbmcgui.ControlButton, self.getControl(CONTEXT_UPDATE_LIBRARY)).setLabel(lang(32208))
        cast(xbmcgui.ControlButton, self.getControl(CONTEXT_REFRESH)).setLabel(lang(32209))

        self.setFocus(self.getControl(CONTEXT_TOGGLE_MULTISELECT))
    
    def onClick(self, controlID: int) -> None:
        """
        Handle button clicks.
        
        Stores the clicked control ID and closes the dialog.
        For the multiselect toggle, also updates the button label.
        
        Args:
            controlID: The ID of the clicked control.
        """
        self.contextoption = controlID
        
        if controlID == CONTEXT_TOGGLE_MULTISELECT:
            # Toggle the multiselect label
            btn = cast(xbmcgui.ControlButton, self.getControl(CONTEXT_TOGGLE_MULTISELECT))
            if btn.getLabel() == lang(32200):
                btn.setLabel(lang(32201))
                xbmc.sleep(CONTEXT_TOGGLE_DELAY_MS)
            else:
                btn.setLabel(lang(32200))
                xbmc.sleep(CONTEXT_TOGGLE_DELAY_MS)
        
        self.close()
    
    def set_multiselect(self, multiselect: bool) -> None:
        """
        Update the multiselect state.
        
        Can be called to update the state before re-showing the dialog.
        
        Args:
            multiselect: Whether multiselect mode is active.
        """
        self._multiselect = multiselect
