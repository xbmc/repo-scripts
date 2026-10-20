# SPDX-License-Identifier: GPL-2.0-only
"""CrossWatch's own windows, drawn from the add-on's skin files rather than the active skin's.

The only module that touches Kodi window objects. A window closes as a cancel on Back, on
its countdown, when Kodi shuts down, and, when asked, when playback starts. Every close is
logged with its reason, so a question that closed itself can be told apart from one the
household skipped.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

import xbmcgui

from resources.lib.constants import (
    PROMPT_EVERYONE,
    WHO_WATCHED_QUESTION,
    WINDOW_CANCEL,
    WINDOW_CLOSE,
    WINDOW_CLOSES_IN,
    WINDOW_SEARCH,
    WINDOW_VIEWER,
)
from resources.lib.log import get_logger
from resources.lib.ui import list_window as lw
from resources.lib.ui import rating as rt
from resources.lib.ui import viewers_window as vw
from resources.lib.ui import who_watched as ww

_log = get_logger("ui")

# xbmc/input/actions/ActionIDs.h
ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92

WHO_WATCHED_XML = "crosswatch-who.xml"
LIST_VIEWERS = 200
BUTTON_DONE = 20
BUTTON_SKIP = 21

Localised = Callable[[int], str]


class CrossWatchDialog(xbmcgui.WindowXMLDialog):
    """Set up with configure() before doModal(), and call stop() once doModal() returns.

    Configured through a method rather than __init__: Kodi builds the window from the
    constructor arguments, so the constructor keeps Kodi's own signature.
    """

    name = "dialog"

    def configure(
        self,
        localised: Localised,
        properties: dict[str, str],
        autoclose_seconds: int,
        close_on_playback: bool,
        is_playing: Callable[[], bool],
        wait_for_abort: Callable[[float], bool],
    ) -> None:
        self.result: Any = None
        self.close_reason = ""
        self._localised = localised
        self._window_properties = properties
        self._remaining = autoclose_seconds
        self._close_on_playback = close_on_playback
        self._is_playing = is_playing
        self._wait_for_abort = wait_for_abort
        self._lock = threading.Lock()
        self._finished = threading.Event()
        self._filled = False
        self._thread: threading.Thread | None = None

    def fill(self) -> None:
        """Populate the window's controls. Called once, from the first onInit."""

    def onInit(self) -> None:
        for key, value in self._window_properties.items():
            self.setProperty(key, value)
        if self._filled:
            return
        self._filled = True
        try:
            self.fill()
        except Exception as exc:
            # Kodi logs an exception raised here and keeps the window open, and doModal never
            # sees it: without this the caller waits on a window with nothing in it.
            _log.warning("ui.window_failed", window=self.name, error_type=type(exc).__name__)
            self.finish("error")
            return
        self._show_countdown()
        if self._remaining > 0 or self._close_on_playback:
            self._thread = threading.Thread(target=self._watch, name="crosswatch-window", daemon=True)
            self._thread.start()

    def onAction(self, action: Any) -> None:
        if action.getId() in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self.finish("back")

    def finish(self, reason: str, result: Any = None) -> bool:
        """Close once, whoever asks first: the household, the countdown, or Kodi."""
        with self._lock:
            if self._finished.is_set():
                return False
            self._finished.set()
            self.close_reason = reason
            self.result = result
        _log.info("ui.window_closed", window=self.name, reason=reason)
        self.close()
        return True

    def stop(self) -> None:
        """End the watch, also for a window Kodi closed by itself."""
        with self._lock:
            outside = not self._finished.is_set()
            self._finished.set()
            if outside:
                self.close_reason = "closed"
        if outside:
            _log.info("ui.window_closed", window=self.name, reason="closed")
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=2)

    def _watch(self) -> None:
        while not self._finished.is_set():
            reason = self._step()
            if reason:
                self.finish(reason)
                return

    def _step(self) -> str:
        """One second of the watch: the reason to close, or "" to keep waiting."""
        if self._wait_for_abort(1):
            return "shutdown"
        if self._finished.is_set():
            return ""
        if self._close_on_playback and self._is_playing():
            return "playback"
        if self._remaining > 0:
            self._remaining -= 1
            if self._remaining == 0:
                return "timeout"
            self._show_countdown()
        return ""

    def _show_countdown(self) -> None:
        if self._remaining > 0:
            # replace rather than %: a translation that drops the placeholder must not raise.
            self.setProperty("CW.Footer", self._localised(WINDOW_CLOSES_IN).replace("%s", str(self._remaining)))


class WhoWatchedDialog(CrossWatchDialog):
    name = "who_watched"

    def prepare(
        self,
        request: ww.WhoWatchedRequest,
        localised: Localised,
        is_playing: Callable[[], bool],
        wait_for_abort: Callable[[float], bool],
    ) -> None:
        self._request = request
        self._ticked = ww.initial(request)
        self.configure(
            localised,
            {
                "CW.Title": request.title,
                "CW.Subtitle": request.subtitle,
                "CW.Poster": request.poster,
                "CW.Question": localised(WHO_WATCHED_QUESTION),
            },
            request.autoclose_seconds,
            request.close_on_playback,
            is_playing,
            wait_for_abort,
        )

    def fill(self) -> None:
        rows: Any = self.getControl(LIST_VIEWERS)
        for label in (self._localised(PROMPT_EVERYONE), *self._request.names):
            rows.addItem(xbmcgui.ListItem(label))
        self._show_ticks()
        # The first row, Everyone, only toggles: a stray OK sends nothing.
        self.setFocusId(LIST_VIEWERS)

    def onClick(self, controlId: int) -> None:
        names = self._request.names
        if controlId == LIST_VIEWERS:
            rows: Any = self.getControl(LIST_VIEWERS)
            self._ticked = ww.toggle(names, self._ticked, rows.getSelectedPosition())
            self._show_ticks()
        elif controlId == BUTTON_DONE:
            self.finish("done", ww.answer(names, self._ticked))
        elif controlId == BUTTON_SKIP:
            self.finish("skip")

    def _show_ticks(self) -> None:
        rows: Any = self.getControl(LIST_VIEWERS)
        names = self._request.names
        rows.getListItem(ww.EVERYONE_ROW).setProperty("chosen", "true" if ww.everyone(names, self._ticked) else "")
        for row, name in enumerate(names, start=1):
            rows.getListItem(row).setProperty("chosen", "true" if name in self._ticked else "")


RATING_XML = "crosswatch-rate.xml"
LIST_SCORES = 100
BUTTON_REMOVE_RATING = 22


class RatingDialog(CrossWatchDialog):
    name = "rating"

    def prepare(
        self,
        request: rt.RateRequest,
        localised: Localised,
        is_playing: Callable[[], bool],
        wait_for_abort: Callable[[float], bool],
    ) -> None:
        self.configure(
            localised,
            {
                "CW.Title": request.title,
                "CW.Subtitle": request.subtitle,
                "CW.Poster": request.poster,
                "CW.Question": request.question,
                "CW.Counter": request.counter,
            },
            request.autoclose_seconds,
            request.close_on_playback,
            is_playing,
            wait_for_abort,
        )

    def fill(self) -> None:
        scores: Any = self.getControl(LIST_SCORES)
        for score, word in enumerate(rt.SCORE_WORDS, start=1):
            item = xbmcgui.ListItem(str(score))
            item.setProperty("word", self._localised(word))
            scores.addItem(item)
        # Skip, not a score: a stray OK must send nothing (cenodude, issue #1).
        self.setFocusId(BUTTON_SKIP)

    def onClick(self, controlId: int) -> None:
        if controlId == LIST_SCORES:
            scores: Any = self.getControl(LIST_SCORES)
            self.finish("score", scores.getSelectedPosition() + 1)
        elif controlId == BUTTON_REMOVE_RATING:
            self.finish("remove", 0)
        elif controlId == BUTTON_SKIP:
            self.finish("skip")


CONFIRM_XML = "crosswatch-confirm.xml"
BUTTON_YES = 10
BUTTON_NO = 11


class ConfirmDialog(CrossWatchDialog):
    name = "confirm"

    def prepare(self, heading: str, message: str, localised: Localised) -> None:
        self.configure(
            localised,
            {"CW.Heading": heading, "CW.Message": message},
            autoclose_seconds=0,
            close_on_playback=False,
            is_playing=lambda: False,
            wait_for_abort=lambda _: False,
        )

    def fill(self) -> None:
        # No first: the question always guards something that cannot be undone.
        self.setFocusId(BUTTON_NO)

    def onClick(self, controlId: int) -> None:
        if controlId == BUTTON_YES:
            self.finish("yes", True)
        elif controlId == BUTTON_NO:
            self.finish("no", False)


VIEWERS_XML = "crosswatch-viewers.xml"
VIEWERS_ROWS = 100
# Ids 10 to 13: never 2, 3 or 4, which WindowXML keeps for its own buttons.
BUTTON_PLAYLISTS = 10
BUTTON_PROFILES = 11
BUTTON_RENAME = 12
BUTTON_REMOVE = 13
BUTTON_ADD = 20
BUTTON_VIEWERS_CLOSE = 21
_VIEWERS_ACTIONS = {
    BUTTON_PLAYLISTS: "playlists",
    BUTTON_PROFILES: "profiles",
    BUTTON_RENAME: "rename",
    BUTTON_REMOVE: "remove",
}


class ViewersDialog(CrossWatchDialog):
    """The viewers on the left, the highlighted one's setup and actions on the right.

    The panel reads the highlighted row's properties, so Kodi redraws it on a focus move
    without calling in here; the buttons act on whichever row is highlighted.
    """

    name = "viewers"

    def prepare(self, request: vw.ViewersRequest, key: str, localised: Localised) -> None:
        self._request = request
        self._position = vw.start_position(request.rows, key)
        self.configure(
            localised,
            {
                "CW.Heading": request.heading,
                "CW.Count": request.count,
                "CW.Empty": "" if request.rows else "true",
            },
            autoclose_seconds=0,
            close_on_playback=False,
            is_playing=lambda: False,
            wait_for_abort=lambda _: False,
        )

    def fill(self) -> None:
        rows: Any = self.getControl(VIEWERS_ROWS)
        for row in self._request.rows:
            item = xbmcgui.ListItem(row.key)
            for key, value in vw.properties(row, self._request).items():
                item.setProperty(key, value)
            rows.addItem(item)
        if self._request.rows:
            rows.selectItem(self._position)
            self.setFocusId(VIEWERS_ROWS)
        else:
            # Always visible, unlike the actions, so it can take focus in this same call.
            self.setFocusId(BUTTON_ADD)

    def onClick(self, controlId: int) -> None:
        action = _VIEWERS_ACTIONS.get(controlId)
        if controlId == VIEWERS_ROWS:
            # The row has no action of its own; OK there means "go to the actions".
            self.setFocusId(BUTTON_PLAYLISTS)
        elif action and self._request.rows:
            # A linked viewer's name is CrossWatch's: Rename is hidden on its row, and a stray
            # click there does nothing.
            if controlId != BUTTON_RENAME or not self._selected_row_linked():
                self.finish(action, vw.ViewersResult(action, self._selected()))
        elif controlId == BUTTON_ADD:
            self.finish("add", vw.ViewersResult("add", self._selected()))
        elif controlId == BUTTON_VIEWERS_CLOSE:
            self.finish("close", vw.ViewersResult("close", self._selected()))

    def _selected_row(self) -> vw.ViewerRow | None:
        rows = self._request.rows
        if not rows:
            return None
        control: Any = self.getControl(VIEWERS_ROWS)
        return rows[min(max(int(control.getSelectedPosition()), 0), len(rows) - 1)]

    def _selected(self) -> str:
        row = self._selected_row()
        return row.key if row else ""

    def _selected_row_linked(self) -> bool:
        row = self._selected_row()
        return bool(row and row.linked)


LIST_XML = "crosswatch-list.xml"
# Not 2, 3 or 4: WindowXML keeps those ids for its own view and sort buttons.
LIST_SEARCH = 30
LIST_FILTER = 31
LIST_ROWS = 100
BUTTON_BULK = 20
BUTTON_CLOSE = 21
BUTTON_PICK_DONE = 22
BUTTON_PICK_EXTRA = 23


class ListDialog(CrossWatchDialog):
    """A searchable list: the screen acts on what comes back, then reopens it."""

    name = "list"

    def prepare(self, request: lw.ListRequest, state: lw.ListState, localised: Localised) -> None:
        self._request = request
        self._search = state.search
        in_range = 0 <= state.filter_index < len(request.filters)
        self._filter_index = state.filter_index if in_range else 0
        self._start = state
        self._shown: list[lw.ListRow] = []
        self.configure(
            localised,
            {
                "CW.Heading": request.heading,
                "CW.Close": localised(WINDOW_CLOSE),
            },
            autoclose_seconds=0,
            close_on_playback=False,
            is_playing=lambda: False,
            wait_for_abort=lambda _: False,
        )

    def state(self) -> lw.ListState:
        rows: Any = self.getControl(LIST_ROWS)
        position = int(rows.getSelectedPosition())
        key = self._shown[position].key if 0 <= position < len(self._shown) else ""
        return lw.ListState(self._search, self._filter_index, position, key)

    def fill(self) -> None:
        search: Any = self.getControl(LIST_SEARCH)
        # Kodi heads its keyboard "Enter value" unless the edit control is told otherwise.
        search.setType(xbmcgui.INPUT_TYPE_TEXT, self._localised(WINDOW_SEARCH))
        search.setText(self._search)
        self._show(self._start)
        if self._shown:
            self.setFocusId(LIST_ROWS)
        else:
            # An empty list cannot take focus, and no direction leads out of it. Not the
            # bulk button: its visibility follows a property set in this same call, and Kodi
            # only re-evaluates it on the next frame, so focusing it here fails.
            self.setFocusId(LIST_SEARCH)

    def onAction(self, action: Any) -> None:
        super().onAction(action)
        # Kodi reports no text change, so the search box is read after every key press
        # while it has focus.
        try:
            focused = self.getFocusId()
        except RuntimeError:
            return
        if focused == LIST_SEARCH:
            self._read_search()

    def onClick(self, controlId: int) -> None:
        if controlId == LIST_SEARCH:
            self._read_search()  # after Kodi's keyboard closes
        elif controlId == LIST_FILTER and self._request.filters:
            self._filter_index = (self._filter_index + 1) % len(self._request.filters)
            self._show(lw.ListState())
        elif controlId == BUTTON_BULK and lw.bulk_label(self._request, len(self._shown)):
            keys = tuple(row.key for row in self._shown)
            self.finish("bulk", lw.ListResult("bulk", self.state(), keys=keys))
        elif controlId == BUTTON_CLOSE:
            self.finish("close", lw.ListResult("close", self.state()))

    def _read_search(self) -> None:
        search: Any = self.getControl(LIST_SEARCH)
        text = str(search.getText())
        if text != self._search:
            self._search = text
            self._show(lw.ListState())

    def _show(self, start: lw.ListState) -> None:
        request = self._request
        row_filter = request.filters[self._filter_index] if request.filters else None
        self._shown = lw.visible(request.rows, self._search, row_filter)
        rows: Any = self.getControl(LIST_ROWS)
        rows.reset()
        for row in self._shown:
            item = xbmcgui.ListItem(row.title)
            item.setArt({"thumb": row.thumb})
            item.setProperty("detail", row.detail)
            item.setProperty("tag", row.tag)
            for key, value in row.properties:
                item.setProperty(key, value)
            rows.addItem(item)
        if self._shown:
            rows.selectItem(lw.start_index(self._shown, start))
        label = self._localised(WINDOW_VIEWER).replace("%s", row_filter.label) if row_filter else ""
        self.setProperty("CW.Filter", label)
        self.setProperty("CW.Count", lw.count_text(request, self._localised, len(self._shown)))
        self.setProperty("CW.Bulk", lw.bulk_label(request, len(self._shown)))
        self.setProperty("CW.Empty", "" if self._shown else "true")


class PickListDialog(ListDialog):
    """A list to tick rows in. OK ticks a row in place; Done returns every ticked row, also
    those a search hides; Cancel and Back change nothing."""

    name = "pick_list"

    def prepare(self, request: lw.ListRequest, state: lw.ListState, localised: Localised) -> None:
        super().prepare(request, state, localised)
        self._ticked = frozenset(request.ticked)
        self._window_properties["CW.Close"] = localised(WINDOW_CANCEL)
        self._window_properties["CW.Extra"] = request.extra

    def onClick(self, controlId: int) -> None:
        if controlId == LIST_ROWS:
            position = self.state().position
            if 0 <= position < len(self._shown):
                key = self._shown[position].key
                self._ticked = lw.toggle(self._ticked, key)
                # In place: refilling the list would move the household off the row.
                rows: Any = self.getControl(LIST_ROWS)
                rows.getListItem(position).setProperty("chosen", "true" if key in self._ticked else "")
        elif controlId == BUTTON_PICK_DONE:
            keys = lw.picked(self._request.rows, self._ticked)
            self.finish("done", lw.ListResult("done", self.state(), keys=keys))
        elif controlId == BUTTON_PICK_EXTRA and self._request.extra:
            keys = lw.picked(self._request.rows, self._ticked)
            self.finish("extra", lw.ListResult("extra", self.state(), keys=keys))
        else:
            super().onClick(controlId)

    def _show(self, start: lw.ListState) -> None:
        super()._show(start)
        rows: Any = self.getControl(LIST_ROWS)
        for index, row in enumerate(self._shown):
            rows.getListItem(index).setProperty("chosen", "true" if row.key in self._ticked else "")


REMEMBERED_XML = "crosswatch-remembered.xml"
BUTTON_CHANGE = 40
BUTTON_FORGET_ONE = 41


class RememberedDialog(ListDialog):
    """The searchable list of shows, the highlighted one's panel, and Change and Forget.

    Each row's panel is in its properties; "changeable" is empty for an answer that can
    only be forgotten, which the XML reads to hide Change.
    """

    name = "remembered"

    def onClick(self, controlId: int) -> None:
        row = self._selected()
        if controlId == LIST_ROWS:
            # The row has no action of its own; OK there means "go to the actions".
            if row is not None:
                self.setFocusId(BUTTON_CHANGE if _changeable(row) else BUTTON_FORGET_ONE)
        elif controlId == BUTTON_CHANGE:
            if row is not None and _changeable(row):
                self.finish("change", lw.ListResult("change", self.state(), key=row.key))
        elif controlId == BUTTON_FORGET_ONE:
            if row is not None:
                self.finish("forget", lw.ListResult("forget", self.state(), key=row.key))
        else:
            super().onClick(controlId)

    def _selected(self) -> lw.ListRow | None:
        position = self.state().position
        return self._shown[position] if 0 <= position < len(self._shown) else None


def _changeable(row: lw.ListRow) -> bool:
    return dict(row.properties).get("changeable") == "true"
