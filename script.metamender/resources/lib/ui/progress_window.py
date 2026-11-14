"""The refresh progress window: what a show or season refresh shows while it
runs, with Stop and Background. Same family style as the setup window.

Logging:
    Logger: 'progress'
"""
from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast

import xbmc
import xbmcgui

from resources.lib.ui.theme import theme_colours
from resources.lib.utils import get_addon, lang

if TYPE_CHECKING:
    # Type only: refresh.py imports this module to show the window.
    from resources.lib.service.refresh import RefreshProgress

_XML = "script-metamender-progress.xml"
_BAR = 40
STOP = 31
BACKGROUND = 32
_ACTION_PREVIOUS_MENU = 10
_ACTION_NAV_BACK = 92
# How often the open window copies the progress in.
_REFRESH_SECONDS = 0.5


def _time_left(seconds: int | None) -> str:
    if seconds is None:
        return ""
    if seconds < 60:
        return lang(32476)
    return lang(32475).format((seconds + 59) // 60)


def progress_properties(progress: RefreshProgress, heading: str, now: float) -> dict[str, str]:
    """Every window property the progress XML reads."""
    props = {
        "MM.Heading": heading,
        "MM.Current": progress.current,
        "MM.Count": progress.bar_text(),
        "MM.TimeLeft": _time_left(progress.seconds_left(now)),
        "MM.Percent": str(progress.percent()),
        "MM.Updated": lang(32477).format(progress.updated),
        "MM.Unchanged": lang(32478).format(progress.unchanged),
        "MM.Unchecked": lang(32479).format(progress.unchecked),
        "MM.Stop": lang(32480),
        "MM.Background": lang(32481),
    }
    props.update(theme_colours())
    return props


class CloseOnce:
    """Whether the window is still open, claimed by exactly one closer.

    The follower thread (the refresh ended) and a button press can close the
    window at the same moment; Kodi treats a second close() as Back and steps
    one screen back, so only the first claim may close it.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._open = False

    def opened(self) -> None:
        with self._lock:
            self._open = True

    @property
    def is_open(self) -> bool:
        with self._lock:
            return self._open

    def claim(self) -> bool:
        """True for the one caller that closes the window."""
        with self._lock:
            if not self._open:
                return False
            self._open = False
            return True


def follow(
    state: CloseOnce,
    done: threading.Event,
    render: Callable[[], None],
    close: Callable[[str], None],
    monitor: Any,
) -> None:
    """Keep an open window's numbers current until the refresh ends ("done")
    or Kodi quits ("background"). It waits on Kodi's abort rather than
    sleeping, so a quitting Kodi is not held up by it."""
    while state.is_open:
        if done.is_set():
            close("done")
            return
        render()
        if monitor.waitForAbort(_REFRESH_SECONDS):
            close("background")
            return


class ProgressWindow(xbmcgui.WindowXMLDialog):
    """Shows a running refresh. ``result`` is "stop", "background", or
    "done" when the refresh finished while the window was open. The
    attributes are set before doModal()."""

    progress: RefreshProgress
    heading: str
    done: threading.Event
    result: str = "background"
    _state: CloseOnce

    def onInit(self) -> None:
        self._state.opened()
        self._render()
        self.setFocusId(BACKGROUND)
        threading.Thread(target=self._follow, daemon=True).start()

    def _render(self) -> None:
        props = progress_properties(self.progress, self.heading, time.monotonic())
        for key, value in props.items():
            self.setProperty(key, value)
        try:
            cast(xbmcgui.ControlProgress, self.getControl(_BAR)).setPercent(
                float(props["MM.Percent"]))
        except RuntimeError:
            pass

    def _follow(self) -> None:
        # Kodi lets a script thread update an open window.
        follow(self._state, self.done, self._render, self._close, xbmc.Monitor())

    def _close(self, result: str) -> None:
        if self._state.claim():
            self.result = result
            self.close()

    def onClick(self, controlId: int) -> None:
        if controlId == STOP:
            self._close("stop")
        elif controlId == BACKGROUND:
            self._close("background")

    def onAction(self, action: Any) -> None:
        if action.getId() in (_ACTION_PREVIOUS_MENU, _ACTION_NAV_BACK):
            self._close("background")


def show_progress_window(progress: RefreshProgress, heading: str, done: threading.Event) -> str:
    """Show the window until Stop, Background or the end of the refresh."""
    window = ProgressWindow(_XML, get_addon().getAddonInfo("path"), "Default", "1080i")
    window.progress, window.heading, window.done = progress, heading, done
    window._state = CloseOnce()
    window.doModal()
    result = window.result
    del window
    return result
