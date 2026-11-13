"""The item details window: the Ids entry and the item's fields on the left,
grouped under headings, the focused entry's story on the right, and the
buttons below. Same family style as the setup, progress and attention
windows.

The window only shows what the session gives it and passes the buttons on;
reading the tracker and writing Kodi happen in service/details.py.

Logging: none (the session logs what it does).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, cast

import xbmcgui

from resources.lib.ui.details_model import (
    ACTION_KEEP,
    ACTION_RESTORE,
    ACTION_UNLOCK,
    GROUP_HEADINGS,
    IDS_KEY,
    DetailRow,
)
from resources.lib.ui.theme import theme_colours
from resources.lib.utils import get_addon, lang

_XML = "script-metamender-details.xml"
ROW_LIST = 50
ROW_ACTION = 31
UPDATE_NOW = 32
CLOSE = 33

_ACTION_PREVIOUS_MENU = 10
_ACTION_NAV_BACK = 92
# Moves that can land the list on a heading, and the way each one went.
_UPWARD = frozenset({3, 5, 104})      # up, page up, wheel up
_DOWNWARD = frozenset({4, 6, 105})    # down, page down, wheel down

_ACTION_LABELS = {ACTION_RESTORE: 32586, ACTION_UNLOCK: 32587, ACTION_KEEP: 32626}
# The grey of a label in the right pane's "label  text" lines.
_LABEL_COLOUR = "FF7D8592"


@dataclass
class ListEntry:
    """One item of the left list: a heading (``row`` None) or a row."""

    label: str
    label2: str
    heading: bool
    row: DetailRow | None


class ViewLike(Protocol):
    """What the window reads of service.details.DetailsView."""

    heading: str
    sub: str
    rows: list[DetailRow]


class SessionLike(Protocol):
    """What the window calls on service.details.DetailsSession."""

    def reload(self) -> ViewLike | None: ...
    def update_now(self) -> None: ...
    def run_action(self, row: DetailRow) -> None: ...


def list_entries(rows: list[DetailRow]) -> list[ListEntry]:
    """The rows in order, with a heading before the first row of each group.
    The Ids entry has no group and no heading."""
    entries: list[ListEntry] = []
    group = ""
    for row in rows:
        if row.group and row.group != group:
            entries.append(ListEntry(lang(GROUP_HEADINGS[row.group]), "", True, None))
        group = row.group
        entries.append(ListEntry(row.label, row.hint, False, row))
    return entries


def entry_properties(entry: ListEntry) -> dict[str, str]:
    """The list item's properties the row layout reads: a heading, and the
    padlock of a locked field."""
    return {
        "heading": "1" if entry.heading else "",
        "locked": "1" if entry.row is not None and entry.row.locked else "",
    }


def first_field_position(entries: list[ListEntry]) -> int:
    """Where focus starts: the first field, else the Ids entry."""
    for pos, entry in enumerate(entries):
        if entry.row is not None and entry.row.key != IDS_KEY:
            return pos
    return 0


def skip_heading(entries: list[ListEntry], position: int, step: int) -> int:
    """The row to select when a move left the list on ``position``: past a
    heading in the direction of the move, or back the other way at an end."""
    for direction in (step, -step):
        pos = position
        while 0 <= pos < len(entries) and entries[pos].heading:
            pos += direction
        if 0 <= pos < len(entries):
            return pos
    return position


def _row_lines(row: DetailRow) -> tuple[str, str]:
    """(value box text, the lines below it). A field's leading unlabelled
    line is its whole current value; any other unlabelled line is a note."""
    lines = list(row.lines)
    value = ""
    if row.key != IDS_KEY and lines and not lines[0][0]:
        value = lines.pop(0)[1]
    text = [
        "[COLOR {}]{}[/COLOR]   {}".format(_LABEL_COLOUR, label, body) if label else body
        for label, body in lines
    ]
    return value, "\n".join(text)


def details_properties(rows: list[DetailRow], focused: int) -> dict[str, str]:
    """The right pane's window properties for ``rows[focused]``."""
    row = rows[focused]
    value, lines = _row_lines(row)
    action = _ACTION_LABELS.get(row.action)
    return {
        "MM.RowTitle": row.title,
        "MM.RowValue": value,
        "MM.RowLines": lines,
        "MM.RowAction": lang(action) if action else "",
    }


def header_properties(heading: str, sub: str) -> dict[str, str]:
    """The window properties that do not follow the focused row."""
    props = {
        "MM.Heading": heading,
        "MM.Sub": sub,
        "MM.UpdateNow": lang(32588),
        "MM.Close": lang(32589),
    }
    props.update(theme_colours())
    return props


class DetailsWindow(xbmcgui.WindowXMLDialog):
    """The properties of the first view are set before doModal(), so the
    visibility conditions hold from the first frame."""

    session: SessionLike
    view: ViewLike
    entries: list[ListEntry]

    def onInit(self) -> None:
        self._fill(None)
        self.setFocusId(ROW_LIST)

    def _list(self) -> xbmcgui.ControlList:
        return cast(xbmcgui.ControlList, self.getControl(ROW_LIST))

    def _fill(self, keep_key: str | None) -> None:
        """Fill the list from ``self.view`` and select ``keep_key``'s row
        (after a rebuild), else the first field."""
        self.entries = list_entries(self.view.rows)
        control = self._list()
        control.reset()
        items = []
        for entry in self.entries:
            item = xbmcgui.ListItem(entry.label, entry.label2)
            for key, value in entry_properties(entry).items():
                item.setProperty(key, value)
            items.append(item)
        control.addItems(items)
        position = first_field_position(self.entries)
        if keep_key is not None:
            for pos, entry in enumerate(self.entries):
                if entry.row is not None and entry.row.key == keep_key:
                    position = pos
                    break
        control.selectItem(position)
        self._show_row(position)

    def _show_row(self, position: int) -> None:
        entry = self.entries[position] if 0 <= position < len(self.entries) else None
        if entry is None or entry.row is None:
            return
        for key, value in details_properties([entry.row], 0).items():
            self.setProperty(key, value)

    def _selected(self) -> DetailRow | None:
        position = self._list().getSelectedPosition()
        if 0 <= position < len(self.entries):
            return self.entries[position].row
        return None

    def _reload(self) -> None:
        """Read the item again after a change, keeping the selected row."""
        row = self._selected()
        view = self.session.reload()
        if view is None:
            # The item left the library or could not be read; the session
            # has told the user which.
            self.close()
            return
        self.view = view
        for key, value in header_properties(view.heading, view.sub).items():
            self.setProperty(key, value)
        self._fill(row.key if row else None)
        if not self.getProperty("MM.RowAction") and self.getFocusId() == ROW_ACTION:
            self.setFocusId(UPDATE_NOW)

    def onAction(self, action: Any) -> None:
        action_id = action.getId()
        if action_id in (_ACTION_PREVIOUS_MENU, _ACTION_NAV_BACK):
            self.close()
            return
        if self.getFocusId() != ROW_LIST:
            return
        # Kodi has already moved the list when this runs; a heading is not
        # a row, so the move carries on past it.
        control = self._list()
        position = control.getSelectedPosition()
        step = -1 if action_id in _UPWARD else 1
        target = skip_heading(self.entries, position, step)
        if target != position:
            control.selectItem(target)
        self._show_row(target)

    def onClick(self, controlId: int) -> None:
        if controlId == CLOSE:
            self.close()
        elif controlId == UPDATE_NOW:
            self.session.update_now()
            self._reload()
        elif controlId == ROW_ACTION:
            row = self._selected()
            if row is not None and row.action:
                self.session.run_action(row)
                self._reload()


def show_details_window(session: SessionLike, view: ViewLike) -> None:
    """Show the window until the user closes it."""
    window = DetailsWindow(_XML, get_addon().getAddonInfo("path"), "Default", "1080i")
    window.session = session
    window.view = view
    props = header_properties(view.heading, view.sub)
    entries = list_entries(view.rows)
    first = entries[first_field_position(entries)].row
    if first is not None:
        props.update(details_properties([first], 0))
    for key, value in props.items():
        window.setProperty(key, value)
    window.doModal()
    del window
