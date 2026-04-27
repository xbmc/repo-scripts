"""
Context menu for the EasyMovie browse window.

Options:
- Play: Play the selected movie
- Play Full Set: Play all movies in the set (hidden if not in a set)

Logging:
    Logger: 'ui'
    Key events:
        - ui.context_open (DEBUG): Context menu opened
        - ui.context_select (DEBUG): Option selected
    See LOGGING.md for full guidelines.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, cast

import xbmcgui

from resources.lib.constants import ACTION_NAV_BACK, ACTION_PREVIOUS_MENU, ADDON_ID
from resources.lib.utils import get_logger, lang

# Context menu action constants
CONTEXT_PLAY = "play"
CONTEXT_PLAY_SET = "play_set"

# Control IDs matching the XML
_BUTTON_PLAY = 110
_BUTTON_PLAY_SET = 120

# Module-level logger
log = get_logger('ui')


class ContextMenuWindow(xbmcgui.WindowXMLDialog):
    """Themed context menu dialog for the browse window."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._addon_id: str = ADDON_ID
        self._has_set: bool = False
        self._set_name: str = ""
        self._result: Optional[str] = None

    @property
    def result(self) -> Optional[str]:
        """The selected action, or None if cancelled."""
        return self._result

    def onInit(self):
        """Set up button labels and visibility."""
        from resources.lib.ui import apply_theme
        apply_theme(self, self._addon_id)

        log.debug("Context menu opened", event="ui.context_open",
                  has_set=self._has_set)

        cast(xbmcgui.ControlButton, self.getControl(_BUTTON_PLAY)).setLabel(
            lang(32312))  # "Play"

        set_label = lang(32313)  # "Play Full Set"
        cast(xbmcgui.ControlButton, self.getControl(_BUTTON_PLAY_SET)).setLabel(
            set_label)

        # Hide "Play Full Set" if movie is not in a set
        if not self._has_set:
            self.getControl(_BUTTON_PLAY_SET).setVisible(False)

        self.setFocus(self.getControl(_BUTTON_PLAY))

    def onClick(self, controlId):
        """Handle button clicks."""
        if controlId == _BUTTON_PLAY:
            self._result = CONTEXT_PLAY
        elif controlId == _BUTTON_PLAY_SET:
            self._result = CONTEXT_PLAY_SET

        log.debug("Context option selected", event="ui.context_select",
                  result=self._result)
        self.close()

    def onAction(self, action):
        """Handle back/escape."""
        action_id = action.getId()
        if action_id in (ACTION_NAV_BACK, ACTION_PREVIOUS_MENU):
            self.close()


def show_context_menu(
    movie: Dict[str, Any],
    addon_id: Optional[str] = None,
) -> Optional[str]:
    """Show the themed context menu for a movie.

    Args:
        movie: The movie dict for the focused item.
        addon_id: Optional addon ID (for clone support).

    Returns:
        CONTEXT_PLAY, CONTEXT_PLAY_SET, or None.
    """
    import xbmcaddon
    addon_path = xbmcaddon.Addon(addon_id or ADDON_ID).getAddonInfo('path')

    dialog = ContextMenuWindow(
        'script-easymovie-contextwindow.xml',
        addon_path, 'Default', '1080i'
    )
    dialog._addon_id = addon_id or ADDON_ID
    set_name = movie.get("set", "")
    dialog._has_set = bool(set_name)
    dialog._set_name = set_name
    dialog.doModal()

    return dialog.result
