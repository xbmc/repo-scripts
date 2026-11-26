"""
MetaMender's own picker, in the setup windows' style, opened over them
wherever setup offers a list of options (a language, a country, what to do
with a library). Kodi's select dialog would look different in every skin.

The window sizes itself to the options: the XML holds the largest layout
and onInit shrinks the panel and list to the row count, since Kodi cannot
size a panel to a list. The scrollbar keeps its full height: it only shows
when the list scrolls, which needs the full seven rows.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, cast

import xbmcgui

from resources.lib.ui.theme import publish_theme
from resources.lib.utils import get_addon, lang

_XML = "script-metamender-select.xml"
PANEL = 10
PANEL_IMAGE = 11
FRAME_IMAGE = 12
LIST = 100
CANCEL = 23
_ACTION_PREVIOUS_MENU = 10
_ACTION_NAV_BACK = 92

# Geometry, in the 1080i coordinates of the XML. The list scrolls past
# MAX_ROWS rows.
MAX_ROWS = 7
ROW_HEIGHT = 84
LIST_WIDTH = 900
PANEL_WIDTH = 1000
_SCREEN_HEIGHT = 1080
# The panel above the list (heading and divider) and below it (the gap,
# Cancel, the bottom margin).
_ABOVE_LIST = 130
_CANCEL_GAP = 28
_CANCEL_LEFT = 370
_BELOW_LIST = _CANCEL_GAP + 72 + 40


@dataclass(frozen=True)
class SelectLayout:
    rows: int
    list_height: int
    panel_height: int
    top: int


@dataclass(frozen=True)
class SelectItem:
    label: str
    detail: str
    chosen: bool
    # "radio" for a choice, "" for an action.
    marker: str


def select_layout(count: int) -> SelectLayout:
    """The window's size for ``count`` options, centred on the screen."""
    rows = min(max(count, 1), MAX_ROWS)
    list_height = rows * ROW_HEIGHT
    panel_height = _ABOVE_LIST + list_height + _BELOW_LIST
    return SelectLayout(rows, list_height, panel_height, (_SCREEN_HEIGHT - panel_height) // 2)


def select_items(options: list[str], details: Optional[list[str]], preselect: int,
                 marked: bool) -> list[SelectItem]:
    """One item per option. A choice (``marked``) shows a radio marker,
    lit on the current option; a list of actions shows none."""
    lines = details if details is not None else [""] * len(options)
    return [SelectItem(label, detail, marked and i == preselect, "radio" if marked else "")
            for i, (label, detail) in enumerate(zip(options, lines))]


def select_properties(heading: str) -> dict[str, str]:
    """Every window property the XML reads."""
    props = {"MM.Heading": heading, "MM.Cancel": lang(32408)}
    return props


class SelectWindow(xbmcgui.WindowXMLDialog):
    """``result`` is the picked index, -1 when cancelled. The items and
    ``preselect`` are set before doModal()."""

    items: list[SelectItem]
    preselect: int = 0
    result: int = -1

    def onInit(self) -> None:
        layout = select_layout(len(self.items))
        self.getControl(PANEL).setPosition((1920 - PANEL_WIDTH) // 2, layout.top)
        self.getControl(PANEL_IMAGE).setHeight(layout.panel_height)
        self.getControl(FRAME_IMAGE).setHeight(layout.panel_height)
        control = self._list()
        control.setHeight(layout.list_height)
        self.getControl(CANCEL).setPosition(
            _CANCEL_LEFT, _ABOVE_LIST + layout.list_height + _CANCEL_GAP)
        control.reset()
        listitems = []
        for entry in self.items:
            item = xbmcgui.ListItem(entry.label, offscreen=True)
            item.setProperty("detail", entry.detail)
            item.setProperty("chosen", "true" if entry.chosen else "")
            item.setProperty("marker", entry.marker)
            listitems.append(item)
        control.addItems(listitems)
        if 0 <= self.preselect < len(listitems):
            control.selectItem(self.preselect)
        self.setFocusId(LIST)

    def onClick(self, controlId: int) -> None:
        if controlId == LIST:
            self.result = self._list().getSelectedPosition()
        self.close()

    def onAction(self, action: Any) -> None:
        if action.getId() in (_ACTION_PREVIOUS_MENU, _ACTION_NAV_BACK):
            self.close()

    def _list(self) -> xbmcgui.ControlList:
        return cast(xbmcgui.ControlList, self.getControl(LIST))


def show_select(heading: str, options: list[str], preselect: int,
                details: Optional[list[str]] = None, marked: bool = True) -> int:
    """The picked index, -1 when cancelled. ``details`` puts a sub-line
    under each option; ``marked`` False shows the options as actions,
    without a current one."""
    window = SelectWindow(_XML, get_addon().getAddonInfo("path"), "Default", "1080i")
    window.items = select_items(options, details, preselect, marked)
    window.preselect = preselect
    for key, value in select_properties(heading).items():
        window.setProperty(key, value)
    publish_theme()
    window.doModal()
    result = window.result
    del window
    return result
