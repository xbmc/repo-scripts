"""Where lyrics are drawn, and keeping the sung line in view.

A skin that draws lyrics itself names its list in ``kofin.lyric.control``;
only that list's selection is driven. Any other skin gets this addon's own
window, which becomes the active window, so it is only opened over the
visualisation screen.
"""

from typing import Callable, List, Optional

import xbmc
import xbmcaddon
import xbmcgui

from . import lyrics as source
from . import paging, settings
from .summon import notify_no_lyrics
from .window import (
    FULL_HEIGHT,
    XML_FILENAME,
    LyricsWindow,
    estimate_px,
    width_for,
)

ADDON = xbmcaddon.Addon()
ADDON_PATH = ADDON.getAddonInfo("path")

WINDOW_VISUALISATION = 12006

# What a skin publishing kofin.lyric.panel authors: 60px rows, in a list 20px
# shorter than its panel, at FULL_HEIGHT.
SKIN_ROW_HEIGHT = 60
SKIN_VERTICAL_INSET = 20
SKIN_PAGE_ROWS = (FULL_HEIGHT - SKIN_VERTICAL_INSET) // SKIN_ROW_HEIGHT

# The overlay widths Contuary authors (Includes_Lyrics.xml).
PANEL_NARROW = 520
PANEL_MID = 760
PANEL_MEDIUM = 1000


def log(message: str) -> None:
    xbmc.log("[kofin-lyrics] %s" % message, xbmc.LOGDEBUG)


def _skin_list_position(control: int) -> int:
    """The skin list's selected index, or -1 if it cannot be read.

    CurrentItem counts from one; Position is the cursor's row, not the line.
    """
    try:
        return int(xbmc.getInfoLabel("Container(%d).CurrentItem" % control)) - 1
    except (TypeError, ValueError):
        return -1


def _skin_select(control: int, index: int) -> None:
    """Select ``index`` in a skin's list.

    Without ``absolute`` the index would count from the top of the view.
    """
    xbmc.executebuiltin("Control.SetFocus(%d,%d,absolute)" % (control, index))


def _skin_list_length(control: int) -> int:
    """Rows in the skin's list, including kofin's blank tail; 0 if unreadable."""
    try:
        return int(xbmc.getInfoLabel("Container(%d).NumItems" % control))
    except (TypeError, ValueError):
        return 0


def _size_bucket(lines: List[source.LyricLine]) -> str:
    """The coarse width class of a song, for skins to switch variants on."""
    widest = max((estimate_px(text) for _, text in lines if text.strip()), default=0)
    width = width_for(widest)
    if width <= PANEL_NARROW:
        return "narrow"
    if width <= PANEL_MID:
        return "mid"
    if width <= PANEL_MEDIUM:
        return "medium"
    return "wide"


def _skin_rows(height: int) -> int:
    return max(3, (height - SKIN_VERTICAL_INSET) // SKIN_ROW_HEIGHT)


class Presenter:
    """Owns whichever surface is showing the current song's lyrics."""

    def __init__(self, monitor: xbmc.Monitor) -> None:
        # The service's own: abortRequested() is only set on monitors that
        # existed when Kodi asked.
        self._monitor = monitor
        self._lines: List[source.LyricLine] = []
        self._window: Optional[LyricsWindow] = None
        self._sent: Optional[int] = None
        self._following = False
        # Our window has taken over from the skin's overlay for scrolling.
        self._interactive = False
        # The skin overlay's geometry needs (re)applying; a window reload
        # resets it to the authored size.
        self._skin_stale = True
        # Rows the skin's overlay currently shows.
        self._skin_visible = SKIN_PAGE_ROWS
        self._up = False  # surface is up, including empty between songs

    # -- lifecycle ----------------------------------------------------------

    def start_song(self) -> None:
        """Take up what kofin has published for the playing song.

        An open window is refilled, not reopened, so it does not flash
        between songs.
        """
        lines = source.published_lines()
        if not lines:
            self.stop_song()
            return
        timed = source.is_timed(lines)
        if not timed and not settings.show_untimed():
            log("%d lines, but untimed lyrics are turned off" % len(lines))
            self.stop_song()
            return
        self._lines = lines
        self._following = timed
        self._sent = None
        self._skin_stale = True
        source.set_size(_size_bucket(lines))
        if self._window is not None and not self._window.closed:
            self._window.set_target_height(settings.window_height())
            self._window.set_lines([text for _, text in lines])
        if not timed:
            self._rewind_skin_list()
        source.set_show(True)
        self._up = True
        log("%d lines%s" % (len(lines), "" if timed else " (untimed)"))

    def stop_song(self) -> None:
        source.set_show(False)
        source.set_size(None)
        self._leave_interactive()
        self._rewind_skin_list()
        self._close_window()
        self._lines = []
        self._sent = None
        self._following = False
        self._up = False

    def blank_song(self) -> None:
        """Take the last song's lines down for a new song that nothing has
        been published for, yet or at all.

        The window stays up, empty, for the grace the service gives kofin's
        fetch: lines that arrive refill it in place, and none closes it by
        stop_song. A skin's list is kofin's directory, which kofin has
        already cleared.
        """
        self._lines = []
        self._sent = None
        self._following = False
        if self._window is not None and not self._window.closed:
            self._window.clear_lines()

    def holding(self) -> bool:
        """Whether a surface is still up, including empty between songs."""
        return self._up

    def awaiting_lines(self) -> bool:
        """Held empty so a fetch can refill it in place."""
        return self._up and not self._lines

    def summon(self) -> None:
        """Hand the lyrics to our own window for scrolling by hand.

        A skin's overlay never gets the arrow keys: the visualisation
        window's keymap binds them to StepBack/SkipNext.
        """
        if not self._lines:
            # Not taken up yet: showAutomatically is off, or the window was
            # dismissed earlier in this song.
            self.start_song()
            if not self._lines:
                # Nothing published, or untimed lyrics that are turned off.
                notify_no_lyrics()
                return
        if source.skin_control_id() and not self._interactive:
            self._interactive = True
            source.set_interactive(True)
            self._sent = None
            log("handing over to our own window for scrolling")
            return
        if self._window is None or self._window.closed:
            self._window = None
            self._sent = None
            self._lines = source.published_lines()

    def close(self) -> None:
        """Let everything go as the service ends.

        The window goes last, by LyricsWindow.close_at_shutdown, so the skin's
        properties are cleared even if Kodi kills the script during its wait.
        """
        window, self._window = self._window, None
        try:
            self.stop_song()
        finally:
            if window is not None:
                window.close_at_shutdown()

    # -- the tick -----------------------------------------------------------

    def tick(self, position: Optional[float]) -> None:
        if not self._lines:
            return

        visualisation = xbmc.getCondVisibility(
            "Window.IsVisible(%d)" % WINDOW_VISUALISATION
        )
        control = 0 if self._interactive else source.skin_control_id()

        if not (control and visualisation):
            # A skin reload while the overlay is away resets its geometry.
            self._skin_stale = True

        if control:
            # The skin draws; our window must not also be up.
            self._close_window()
            if visualisation:
                self._drive_skin(control, position)
            return

        if not visualisation:
            self._close_window()
            return
        self._drive_window(position)

    # -- driving a skin's list ----------------------------------------------

    def _drive_skin(self, control: int, position: Optional[float]) -> None:
        """Keep a skin's list on the sung line.

        Re-asserted every tick: the viewer cannot scroll the list, so any
        divergence is ours to correct.
        """
        where = _skin_list_position(control)
        if where < 0:
            # Unaddressable, e.g. under the OSD, where Control.SetFocus would
            # land instead. Its geometry is pushed again when it is back.
            self._skin_stale = True
            return
        resized = False
        if self._skin_stale:
            applied = self._apply_skin_geometry(control)
            if applied is None:
                return  # mid-reload; pushed again next tick
            self._skin_stale = False
            resized = applied
        if not self._following:
            # Untimed: hold the first line (see _rewind_skin_list). No resize
            # wait: the first line tops the view on any page.
            if where != 0:
                _skin_select(control, 0)
            return
        if resized:
            # Place from the next tick: a selection handled before Kodi's
            # next frame would use the old page.
            self._sent = None
            return
        active = self._active(position)
        if active is None:
            return
        if active == self._sent and where == active:
            return
        self._sent = active
        self._position_list(
            lambda index: _skin_select(control, index),
            active,
            paging.middle_row(self._skin_visible),
            paging.lead_rows(self._skin_visible, SKIN_PAGE_ROWS),
            (_skin_list_length(control) or len(self._lines)) - 1,
        )

    def _apply_skin_geometry(self, control: int) -> Optional[bool]:
        """Write the height setting onto a skin overlay that opted in.

        The full height is written too, restoring a list shortened earlier.
        Returns whether the list's height changed, or None mid-reload.

        Call once per application, not per tick: wrappers built at polling
        rate crash Kodi. A fresh wrapper is also what reads the live height;
        a control wrapper keeps the geometry it was created with.
        """
        panel_ids = source.skin_panel_ids()
        if not panel_ids:
            self._skin_visible = SKIN_PAGE_ROWS
            return False
        height = min(FULL_HEIGHT, settings.window_height())
        rows = _skin_rows(height)
        try:
            visualisation = xbmcgui.Window(WINDOW_VISUALISATION)
            for panel_id in panel_ids:
                visualisation.getControl(panel_id).setHeight(height)
            skin_list = visualisation.getControl(control)
            resized = skin_list.getHeight() != rows * SKIN_ROW_HEIGHT
            skin_list.setHeight(rows * SKIN_ROW_HEIGHT)
        except Exception:
            return None
        self._skin_visible = rows
        if resized:
            log("skin overlay height set to %d" % height)
        return resized

    def _rewind_skin_list(self) -> None:
        """Put the skin's list back on its first line, if it is addressable.

        The list outlives the song and Kodi keeps its selection when the rows
        change, so without this a song opens where the last one ended.
        """
        control = 0 if self._interactive else source.skin_control_id()
        if control and _skin_list_position(control) > 0:
            _skin_select(control, 0)

    # -- driving our own window ---------------------------------------------

    def _drive_window(self, position: Optional[float]) -> None:
        if self._window is None:
            if self._monitor.abortRequested():
                # show() would block like close(); see
                # LyricsWindow.close_at_shutdown.
                return
            self._open_window()
        if self._window is None:
            return
        if self._window.closed:
            window = self._window
            self._window = None
            if not window.dismissed:
                # Closed by Kodi, not the viewer: reopen.
                self._sent = None
                log("window closed out from under us; reopening")
            elif self._interactive:
                # Handed back to the skin's overlay.
                self._leave_interactive()
                self._following = source.is_timed(self._lines)
                self._sent = None
            else:
                self._lines = []  # dismissed; leave it shut for this song
                self._up = False
            return
        self._window.refit()
        if not self._following or self._window.scrolled:
            return
        if not self._window.ready:
            # Just opened: a selection now would be lost but counted as sent.
            return
        active = self._active(position)
        if active is None or active == self._sent:
            return
        self._sent = active
        window = self._window
        lead = window.lead_rows()
        self._position_list(
            window.highlight,
            active,
            window.middle_row(),
            lead,
            len(self._lines) - 1 + lead,  # the list ends in ``lead`` blank rows
        )

    def _open_window(self) -> None:
        try:
            window = LyricsWindow(
                XML_FILENAME,
                ADDON_PATH,
                "default",
                "1080i",
                lines=[text for _, text in self._lines],
                height=settings.window_height(),
                monitor=self._monitor,
            )
            window.show()
            self._window = window
            self._sent = None
        except Exception as error:  # pragma: no cover - defensive
            log("could not open the lyrics window: %s" % error)
            self._window = None

    def _leave_interactive(self) -> None:
        if self._interactive:
            self._interactive = False
            source.set_interactive(False)

    def _close_window(self) -> None:
        if self._window is not None:
            self._window.close()
            self._window = None

    # -- shared -------------------------------------------------------------

    @staticmethod
    def _position_list(
        select: Callable[[int], None], active: int, mid: int, lead: int, last: int
    ) -> None:
        """Select ``active`` so that, once scrolling, it sits on row ``mid``.

        A list scrolls only when the selection leaves its page: a line
        selected before the page lands on the top row, one after it on the
        bottom row. So select ``mid`` lines back (tops the view after a seek
        backwards), then ``lead`` lines on (drags the view down until the
        sung line is ``mid`` rows down), then the sung line, which only moves
        the cursor. Played forwards, that is one one-row scroll per line.
        ``last`` caps the drag at the list's end.
        """
        select(max(0, active - mid))
        select(min(active + lead, last))
        select(active)

    def _active(self, position: Optional[float]) -> Optional[int]:
        """The line to sit on, or None. Before any line is sung, the first."""
        if position is None:
            return None
        active = source.active_index(self._lines, position - settings.offset())
        if active is None and self._following:
            return 0
        return active
