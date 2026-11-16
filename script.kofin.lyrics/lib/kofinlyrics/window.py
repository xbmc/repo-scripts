"""This addon's own lyrics window, for skins that draw none themselves.

Everything here runs on the service thread, callbacks included: Kodi delivers
onInit and onAction inside the thread's xbmc.sleep and waitForAbort calls.
Callbacks must stay trivial -- measuring from onInit crashes Kodi -- so
measuring happens in refit(), called from the service loop.

Kodi can close this dialog itself, freeing the controls behind our wrappers,
and a write through a freed control crashes Kodi. Every control write checks
_alive() first.
"""

import math
import time
from typing import Any, List, Optional, cast

import xbmc
import xbmcgui

from . import paging

LIST_ID = 100
PANEL_ID = 101
TITLE_ID = 102
# Hidden auto-width labels the panel is measured with. Each can be read once:
# a control wrapper keeps the geometry of its first getControl().
MEASURE_ID_FIRST = 3901
MEASURE_ID_LAST = 3940
# A hidden label only this XML has, to tell our dialog's id from others'.
SENTINEL_ID = 3999
XML_FILENAME = "script-kofin-lyrics.xml"
# Kodi's WINDOW_PYTHON_START..END.
PYTHON_WINDOW_FIRST = 13000
PYTHON_WINDOW_LAST = 13099
# Must outlast the 5 s Kodi gives a script it is stopping (PYTHON_SCRIPT_TIMEOUT).
SHUTDOWN_CLOSE_WAIT_S = 30.0

HOME_WINDOW = 10000
# Bound by the measure labels; on Home because this window's id is only known
# at runtime.
PROP_MEASURE = "kofin.lyric.measure"

# Panel width bounds. FULL_WIDTH, the authored width, fits a ~74-character
# line at font14; the right edge stays put.
FULL_WIDTH = 1240
MIN_WIDTH = 300
# Panel height bounds; the top edge stays put.
FULL_HEIGHT = 800
MIN_HEIGHT = 260
# Inset of the list and title inside the panel, each side.
LIST_LEFT = 20
# Total space beside the widest line, split between both sides.
PADDING = 80
# Vertical framing; ROW_HEIGHT must match the XML's item layouts.
TITLE_STRIP = 60
BOTTOM_PAD = 20
ROW_HEIGHT = 60

# How long the renderer gets to lay out a measure line before its one read.
SETTLE_MS = 400
# Measurement rounds that come back empty before a track keeps the estimate.
PROBE_ATTEMPTS = 3

# The resize glide between songs; changes up to TWEEN_SNAP_PX apply at once.
TWEEN_MS = 300
TWEEN_STEP_MS = 16
TWEEN_SNAP_PX = 12

# Per-glyph-class advances of NotoSans at font14 (33px), for the width
# estimate used before, or instead of, a measurement.
_NARROW = set("iljI!.,'|:;()[]\" ")
_WIDE = set("MWmw@%&")
_NARROW_PX = 9
_WIDE_PX = 31
_UPPER_PX = 22
_OTHER_PX = 17

ACTION_PARENT_DIR = 9
ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92
CLOSE_ACTIONS = (ACTION_PARENT_DIR, ACTION_PREVIOUS_MENU, ACTION_NAV_BACK)

# Actions that mean the viewer took the list over; following stops until the
# next song: Up, Down, PageUp, PageDown, the mouse wheel, ScrollUp/ScrollDown
# and Home/End (FirstPage/LastPage).
SCROLL_ACTIONS = (3, 4, 5, 6, 104, 105, 111, 112, 159, 160)
# A touch swipe scrolls the list under the finger; it is corrected once the
# gesture ends, not while it moves.
ACTION_GESTURE_PAN = 504
GESTURE_DONE_ACTIONS = (599, 505)  # ACTION_GESTURE_END, ACTION_GESTURE_ABORT


def estimate_px(line: str) -> int:
    """Rendered-width estimate in pixels, for ranking and for fallback."""
    total = 0
    for ch in line:
        if ch in _NARROW:
            total += _NARROW_PX
        elif ch in _WIDE or ord(ch) >= 0x2E80:
            # CJK and beyond: full-width.
            total += _WIDE_PX
        elif ch.isupper():
            total += _UPPER_PX
        else:
            total += _OTHER_PX
    return total


def width_for(longest_px: int) -> int:
    """Panel width for a widest line, clamped to the authored bounds."""
    return min(FULL_WIDTH, max(MIN_WIDTH, longest_px + PADDING))


def rows_for(height: int) -> int:
    """Whole rows that fit a panel of ``height`` alongside the title strip."""
    return max(3, (height - TITLE_STRIP - BOTTOM_PAD) // ROW_HEIGHT)


PAGE_ROWS = rows_for(FULL_HEIGHT)


class LyricsWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Taken here because onInit, which applies them, runs after show()
        # returns.
        self._lines: List[str] = list(kwargs.pop("lines", []))
        self._target_height: int = self._clamp_height(
            int(kwargs.pop("height", FULL_HEIGHT))
        )
        self._monitor: xbmc.Monitor = kwargs.pop("monitor")
        super().__init__(*args)
        self.closed = False
        # Closed by the viewer (stay shut this song), not by Kodi (reopen).
        self.dismissed = False
        self.scrolled = False
        self._list: Optional[xbmcgui.ControlList] = None
        self._window_id: Optional[int] = None
        self._width = 0
        self._height = 0
        self._next_probe = MEASURE_ID_FIRST
        self._measured = False
        self._probe_attempts = 0

    def onInit(self) -> None:
        try:
            self._list = cast(xbmcgui.ControlList, self.getControl(LIST_ID))
        except Exception:  # pragma: no cover - window torn down mid-init
            self._list = None
            return
        self._fill()
        self.setFocusId(LIST_ID)  # only now: an empty list cannot take focus
        # The estimate now, so the opening fade plays at about the right
        # width; refit() measures.
        self._fit(self._estimate_width(self._lines))

    def set_lines(self, lines: List[str]) -> None:
        """Show the next track's lines, measured first so the swap and the
        resize land together."""
        self._lines = list(lines)
        if self._list is None or not self._alive():
            return
        self.scrolled = False
        self._measured = False
        self._probe_attempts = 0
        measured = self._measure_longest(self._lines)
        if measured is None:
            self._probe_attempts = 1
            width = self._estimate_width(self._lines)
        else:
            self._measured = True
            width = width_for(measured)
        if not self._alive():  # measuring takes about a second
            return
        self._fill()
        self._tween_to(width)

    def clear_lines(self) -> None:
        """Show no lines, keeping the panel as it is.

        For the gap between a song and the next one's lines, which refill
        the list in place; a song that has none closes the window from
        outside.
        """
        self._lines = []
        if self._list is None or not self._alive():
            return
        self.scrolled = False
        self._fill()

    def set_target_height(self, height: int) -> None:
        """The user's panel height; applied with the next fit."""
        self._target_height = self._clamp_height(height)

    @property
    def ready(self) -> bool:
        """Whether onInit has run; a selection made before then is lost."""
        return self._list is not None

    def refit(self) -> None:
        """Measure the widest line in the skin's own font and glide to it.

        A no-op once measured.
        """
        if self._list is None or self._measured or not self._alive():
            return
        self._probe_attempts += 1
        measured = self._measure_longest(self._lines)
        if measured is None:
            if self._probe_attempts >= PROBE_ATTEMPTS:
                self._measured = True  # the estimate stands for this track
            return
        self._measured = True
        self._tween_to(width_for(measured))

    def lead_rows(self) -> int:
        """How far past the sung line to drag the view; see
        Presenter._position_list."""
        return paging.lead_rows(rows_for(self._target_height), PAGE_ROWS)

    def middle_row(self) -> int:
        """The row the sung line settles on at the current height."""
        return paging.middle_row(rows_for(self._target_height))

    def _fill(self) -> None:
        """Fill the list with the lines and lead_rows() blank rows.

        Empty lines keep their rows, since lines are addressed by index. The
        blank tail lets the last lines reach the middle row: a list scrolls
        no further than its last item.
        """
        if self._list is None:
            return
        self._list.reset()
        for line in self._lines:
            self._list.addItem(xbmcgui.ListItem(line or " ", offscreen=True))
        for _ in range(self.lead_rows()):
            self._list.addItem(xbmcgui.ListItem(" ", offscreen=True))

    # -- liveness ------------------------------------------------------------

    def _alive(self) -> bool:
        """Whether the dialog is still open.

        The id is learned once from the topmost dialog and checked against
        the sentinel. Until then -- something else on top -- it counts as
        alive.
        """
        if self.closed:
            return False
        if self._window_id is None:
            dialog_id = xbmcgui.getCurrentWindowDialogId()
            try:
                xbmcgui.Window(dialog_id).getControl(SENTINEL_ID)
            except Exception:
                return True
            self._window_id = dialog_id
            return True
        if xbmc.getCondVisibility("Window.IsVisible(%d)" % self._window_id):
            return True
        self.closed = True
        return False

    # -- fitting -------------------------------------------------------------

    def _estimate_width(self, lines: List[str]) -> int:
        widest = max((estimate_px(line) for line in lines if line.strip()), default=0)
        return width_for(widest)

    @staticmethod
    def _clamp_height(height: int) -> int:
        return min(FULL_HEIGHT, max(MIN_HEIGHT, height))

    def _tween_to(self, width: int) -> None:
        """Glide the panel's left edge to ``width`` over TWEEN_MS.

        Stepped writes are the only way to animate it: Python cannot trigger
        skin animations, and skin geometry cannot bind a property. Steps
        follow the clock, as waitForAbort overruns while it pumps callbacks.
        Kodi stopping the add-on ends it where it is.
        """
        if self._width == 0 or abs(width - self._width) <= TWEEN_SNAP_PX:
            self._fit(width)
            return
        start = self._width
        began = time.monotonic()
        while True:
            if not self._alive():
                return
            part = (time.monotonic() - began) * 1000 / TWEEN_MS
            if part >= 1:
                break
            eased = (1 - math.cos(math.pi * part)) / 2
            self._fit(round(start + (width - start) * eased))
            if self._monitor.waitForAbort(TWEEN_STEP_MS / 1000):
                return
        self._fit(width)

    def _fit(self, width: int) -> None:
        """Put the panel at ``width`` and the target height.

        The list keeps its authored width -- an item layout cannot be resized
        at runtime -- and moves to stay centred on the panel. It shows whole
        rows; the panel takes the exact height.
        """
        height = self._target_height
        left = FULL_WIDTH - width  # right-anchored
        self._width = width
        try:
            panel = self.getControl(PANEL_ID)
            panel.setWidth(width)
            panel.setPosition(left, 0)
            title = self.getControl(TITLE_ID)
            title.setWidth(width - 2 * LIST_LEFT)
            title.setPosition(left + LIST_LEFT, 10)
            if self._list is not None:
                # Half the shrink keeps the list's centre on the panel's.
                self._list.setPosition(LIST_LEFT + left // 2, TITLE_STRIP)
            if height != self._height:
                panel.setHeight(height)
                if self._list is not None:
                    self._list.setHeight(rows_for(height) * ROW_HEIGHT)
                self._height = height
        except Exception:  # pragma: no cover - window torn down under us
            pass

    # -- measuring ----------------------------------------------------------

    def _measure_longest(self, lines: List[str]) -> Optional[int]:
        """Rendered width of the widest line, or None if unmeasurable now."""
        candidates = self._candidates(lines)
        if not candidates:
            return 0
        home = xbmcgui.Window(HOME_WINDOW)
        measured = 0
        try:
            for line in candidates:
                width = self._probe(home, line)
                if width is None:
                    return None
                measured = max(measured, width)
                if measured >= FULL_WIDTH - PADDING:
                    # Clamped regardless; a wider runner-up changes nothing.
                    break
        except Exception:
            return None  # torn down mid-probe
        finally:
            try:
                home.clearProperty(PROP_MEASURE)
            except Exception:  # pragma: no cover - teardown race
                pass
        return measured

    @staticmethod
    def _candidates(lines: List[str]) -> List[str]:
        """Up to three lines within 15% of the widest estimate, widest first.

        The estimate only mis-ranks lines of close widths.
        """
        unique = sorted(
            {line for line in lines if line.strip()}, key=estimate_px, reverse=True
        )
        if not unique:
            return []
        floor = estimate_px(unique[0]) * 85 // 100
        return [line for line in unique[:3] if estimate_px(line) >= floor]

    def _probe(self, home: xbmcgui.Window, line: str) -> Optional[int]:
        """Measure ``line`` with the next unread label, or None.

        Unread labels sit at width 1 while the property is empty, so a width
        of 1 means the renderer had not laid this line out yet.
        """
        if self._next_probe > MEASURE_ID_LAST:
            return None  # pool exhausted; the estimate stands
        home.setProperty(PROP_MEASURE, line)
        xbmc.sleep(SETTLE_MS)
        cid = self._next_probe
        self._next_probe += 1
        width = self.getControl(cid).getWidth()
        home.setProperty(PROP_MEASURE, "")
        if width <= 1:
            return None
        return width

    # -- driving ------------------------------------------------------------

    def highlight(self, index: int) -> None:
        if self._list is None or self.scrolled or not self._alive():
            return
        try:
            self._list.selectItem(index)
        except Exception:  # pragma: no cover - list emptied under us
            pass

    def close(self) -> None:
        self.closed = True
        try:
            super().close()
        except Exception:  # window already torn down with the player
            pass

    def close_at_shutdown(self) -> None:
        """Close the dialog as the service stops, without deadlocking Kodi.

        While Kodi stops a service, its main thread waits for the script, and
        close() -- which freeing this object also runs while the dialog is
        visible -- waits for the main thread holding the GIL. At its 5 s timeout Kodi takes the GIL to kill
        the script, and nothing moves again. So the close is posted, and this
        sleeps without the GIL until the dialog is gone; the caller must keep
        this object until then.
        """
        self.closed = True
        if self._window_id is not None:
            window_ids = [self._window_id]
        else:
            window_ids = self._open_window_ids()
        for window_id in window_ids:
            xbmc.executebuiltin("Dialog.Close(%d,true)" % window_id)
        deadline = time.monotonic() + SHUTDOWN_CLOSE_WAIT_S
        while time.monotonic() < deadline and any(
            xbmc.getCondVisibility("Window.IsVisible(%d)" % window_id)
            for window_id in window_ids
        ):
            time.sleep(0.05)  # not xbmc.sleep, which pumps callbacks

    @staticmethod
    def _open_window_ids() -> List[int]:
        """Every visible window built from this addon's XML."""
        found: List[int] = []
        for window_id in range(PYTHON_WINDOW_FIRST, PYTHON_WINDOW_LAST + 1):
            if not xbmc.getCondVisibility("Window.IsVisible(%d)" % window_id):
                continue
            try:
                xbmcgui.Window(window_id).getControl(SENTINEL_ID)
            except Exception:
                continue
            found.append(window_id)
        return found

    def onAction(self, action: xbmcgui.Action) -> None:
        action_id = action.getId()
        if action_id in CLOSE_ACTIONS:
            self.dismissed = True
            self.close()
        elif action_id in SCROLL_ACTIONS:
            self.scrolled = True
            self._stop_at_last_line()
        elif action_id == ACTION_GESTURE_PAN:
            self.scrolled = True
        elif action_id in GESTURE_DONE_ACTIONS and self.scrolled:
            self._stop_at_last_line()

    def _stop_at_last_line(self) -> None:
        """Bring a list scrolled by hand back from the blank rows after the
        last line with text, which are there only for following (see _fill)."""
        if self._list is None or not self._alive():
            return
        last = max((i for i, line in enumerate(self._lines) if line.strip()), default=0)
        if self._list.getSelectedPosition() <= last:
            return
        # An item above the view lands on the top row (see
        # Presenter._position_list), leaving the last line on the bottom row.
        self._list.selectItem(max(0, last - (rows_for(self._target_height) - 1)))
        self._list.selectItem(last)
