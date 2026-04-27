"""
EasyMovie Dialog Helpers.

Provides dialog classes and helper functions for the wizard
and general-purpose dialogs.

Logging:
    Logger: 'ui'
    Key events:
        - ui.dialog_open (DEBUG): Dialog opened
        - ui.dialog_select (DEBUG): User made selection
        - ui.dialog_cancel (DEBUG): User cancelled dialog
    See LOGGING.md for full guidelines.
"""
from __future__ import annotations

from typing import List, Optional, Set, cast

import xbmcgui

from resources.lib.constants import (
    ACTION_MOVE_DOWN,
    ACTION_MOVE_UP,
    ACTION_NAV_BACK,
    ACTION_PREVIOUS_MENU,
    ADDON_ID,
)
from resources.lib.utils import get_logger

# Control IDs matching the XML files
SELECT_HEADING = 1
SELECT_LIST = 100
SELECT_OK = 10
SELECT_BACK = 11

CONFIRM_HEADING = 1
CONFIRM_MESSAGE = 2
CONFIRM_YES = 10
CONFIRM_NO = 11

# Module-level logger
log = get_logger('ui')


def _get_addon_path() -> str:
    """Get the addon root path (Kodi resolves the skin subdirectory)."""
    import xbmcaddon
    return xbmcaddon.Addon(ADDON_ID).getAddonInfo('path')


class SelectDialog(xbmcgui.WindowXMLDialog):
    """Multi-purpose selection dialog with checkbox support."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._addon_id: str = ADDON_ID
        self.heading = ""
        self.items: List[str] = []
        self.preselected: List[int] = []
        self.multi_select = True
        self.headers: Set[int] = set()
        self.selected: List[int] = []
        self.cancelled = False
        self._back_pressed = False

    def onInit(self):
        """Populate the dialog when it opens."""
        from resources.lib.ui import apply_theme
        apply_theme(self, self._addon_id)

        cast(xbmcgui.ControlLabel, self.getControl(SELECT_HEADING)).setLabel(self.heading)

        list_control = cast(xbmcgui.ControlList, self.getControl(SELECT_LIST))
        list_control.reset()

        for i, item_label in enumerate(self.items):
            li = xbmcgui.ListItem(item_label)
            if i in self.headers:
                li.setProperty('is_header', 'true')
            elif i in self.preselected:
                li.setProperty('checked', 'true')
                self.selected.append(i)
            list_control.addItem(li)

        # Single-select: set property so XML hides checkboxes and OK button
        if not self.multi_select:
            self.setProperty('EasyMovie.SingleSelect', 'true')

        if self.items:
            self.setFocusId(SELECT_LIST)

    def onClick(self, controlId):
        """Handle button and list item clicks."""
        if controlId == SELECT_LIST:
            list_control = cast(xbmcgui.ControlList, self.getControl(SELECT_LIST))
            if self.multi_select:
                idx = list_control.getSelectedPosition()
                li = list_control.getSelectedItem()
                if li and li.getProperty('is_header') == 'true':
                    return
                if li.getProperty('checked') == 'true':
                    li.setProperty('checked', '')
                    if idx in self.selected:
                        self.selected.remove(idx)
                else:
                    li.setProperty('checked', 'true')
                    if idx not in self.selected:
                        self.selected.append(idx)
            else:
                # Single select: close immediately (skip headers)
                li = list_control.getSelectedItem()
                if li and li.getProperty('is_header') == 'true':
                    return
                self.selected = [list_control.getSelectedPosition()]
                self.close()

        elif controlId == SELECT_OK:
            self.close()

        elif controlId == SELECT_BACK:
            self._back_pressed = True
            self.cancelled = True
            self.close()

    def onAction(self, action):
        """Handle back/escape and skip header items on navigation."""
        action_id = action.getId()
        if action_id in (ACTION_NAV_BACK, ACTION_PREVIOUS_MENU):
            self._back_pressed = True
            self.cancelled = True
            self.close()
        elif action_id in (ACTION_MOVE_UP, ACTION_MOVE_DOWN) and self.headers:
            list_control = cast(xbmcgui.ControlList, self.getControl(SELECT_LIST))
            pos = list_control.getSelectedPosition()
            if pos in self.headers:
                step = 1 if action_id == ACTION_MOVE_DOWN else -1
                new_pos = pos + step
                # Clamp to valid range
                new_pos = max(0, min(new_pos, list_control.size() - 1))
                if new_pos not in self.headers:
                    list_control.selectItem(new_pos)

    @property
    def back_pressed(self) -> bool:
        """Whether the user pressed back (vs OK or item select)."""
        return self._back_pressed


class ConfirmDialog(xbmcgui.WindowXMLDialog):
    """Simple yes/no confirmation dialog."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._addon_id: str = ADDON_ID
        self.heading = ""
        self.message = ""
        self.yes_label = ""
        self.no_label = ""
        self.confirmed = False
        self.cancelled = False

    def onInit(self):
        """Set up the dialog labels."""
        from resources.lib.ui import apply_theme
        apply_theme(self, self._addon_id)

        cast(xbmcgui.ControlLabel, self.getControl(CONFIRM_HEADING)).setLabel(self.heading)
        cast(xbmcgui.ControlLabel, self.getControl(CONFIRM_MESSAGE)).setLabel(self.message)
        if self.yes_label:
            cast(xbmcgui.ControlButton, self.getControl(CONFIRM_YES)).setLabel(self.yes_label)
        if self.no_label:
            cast(xbmcgui.ControlButton, self.getControl(CONFIRM_NO)).setLabel(self.no_label)
        else:
            self.setProperty('EasyMovie.SingleButton', 'true')
        self.setFocus(self.getControl(CONFIRM_YES))

    def onClick(self, controlId):
        """Handle button clicks."""
        if controlId == CONFIRM_YES:
            self.confirmed = True
            self.close()
        elif controlId == CONFIRM_NO:
            self.confirmed = False
            self.close()

    def onAction(self, action):
        """Handle back/escape."""
        action_id = action.getId()
        if action_id in (ACTION_NAV_BACK, ACTION_PREVIOUS_MENU):
            self.cancelled = True
            self.close()


def show_select_dialog(
    heading: str,
    items: List[str],
    multi_select: bool = True,
    preselected: Optional[List[int]] = None,
    addon_id: Optional[str] = None,
    headers: Optional[Set[int]] = None,
) -> Optional[List[int]]:
    """Show a themed selection dialog.

    Args:
        heading: Dialog heading text.
        items: List of item labels.
        multi_select: If True, checkboxes. If False, single-select closes on pick.
        preselected: Indices of pre-selected items.
        addon_id: Optional addon ID (for clone support).
        headers: Indices of non-selectable group header items.

    Returns:
        List of selected indices, or None if cancelled/back pressed.
    """
    log.debug("Select dialog opened", event="ui.dialog_open",
              heading=heading, item_count=len(items),
              multi_select=multi_select)
    dialog = SelectDialog(
        'script-easymovie-select.xml',
        _get_addon_path(),
        'Default', '1080i'
    )
    dialog._addon_id = addon_id or ADDON_ID
    dialog.heading = heading
    dialog.items = items
    dialog.multi_select = multi_select
    dialog.preselected = preselected or []
    dialog.headers = headers or set()
    dialog.doModal()

    if dialog.cancelled:
        log.debug("Select dialog cancelled", event="ui.dialog_cancel",
                  heading=heading)
        return None
    selected = sorted(dialog.selected)
    if not selected:
        log.debug("Select dialog empty selection", event="ui.dialog_empty",
                  heading=heading)
        return []  # OK with nothing selected = no filter
    log.debug("Select dialog selection made", event="ui.dialog_select",
              heading=heading, selected_count=len(selected))
    return selected


def show_confirm_dialog(
    heading: str,
    message: str,
    yes_label: str = "",
    no_label: str = "",
    addon_id: Optional[str] = None,
) -> Optional[bool]:
    """Show a themed confirmation dialog.

    Args:
        heading: Dialog heading text.
        message: Message body.
        yes_label: Custom label for the yes button.
        no_label: Custom label for the no button.
        addon_id: Optional addon ID (for clone support).

    Returns:
        True if user confirmed, False if declined, None if cancelled/back.
    """
    log.debug("Confirm dialog opened", event="ui.dialog_open",
              heading=heading)
    dialog = ConfirmDialog(
        'script-easymovie-confirm.xml',
        _get_addon_path(),
        'Default', '1080i'
    )
    dialog._addon_id = addon_id or ADDON_ID
    dialog.heading = heading
    dialog.message = message
    dialog.yes_label = yes_label
    dialog.no_label = no_label
    dialog.doModal()

    if dialog.cancelled:
        log.debug("Confirm dialog cancelled", event="ui.dialog_cancel",
                  heading=heading)
        return None
    log.debug("Confirm dialog result", event="ui.dialog_select",
              heading=heading, confirmed=dialog.confirmed)
    return dialog.confirmed
