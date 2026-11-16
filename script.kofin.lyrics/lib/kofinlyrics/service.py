"""The service loop: follow playback and feed the presenter.

It waits in waitForAbort, which is also what delivers the lyrics window's
callbacks.
"""

from typing import Optional

import xbmc
import xbmcgui

from . import lyrics as source
from . import settings
from .presenter import Presenter, log
from .summon import PROP_SUMMON, notify_no_lyrics

TICK_SECONDS = 0.25

# Kofin clears its lyrics between songs, so a few empty ticks are expected.
EMPTY_TICKS_BEFORE_STOP = 12


def _playing_file(player: xbmc.Player) -> str:
    """What is playing; it changes with every song, published or not."""
    try:
        return player.getPlayingFile()
    except RuntimeError:
        return ""  # playback ended under us


def _position(player: xbmc.Player) -> Optional[float]:
    try:
        return float(player.getTime())
    except (RuntimeError, ValueError):
        return None  # not playing, or playback ended under us


def _take_summons() -> bool:
    """Whether the script entry point asked for the lyrics to be brought up."""
    window = xbmcgui.Window(source.HOME_WINDOW)
    if not window.getProperty(PROP_SUMMON):
        return False
    window.clearProperty(PROP_SUMMON)
    return True


def _loop(monitor: xbmc.Monitor, presenter: Presenter) -> None:
    # Last published path we consumed. Empty while waiting on a fetch.
    showing = ""
    # Playing file for that path; a change while unpublished blanks.
    shown_file = ""
    empty_ticks = 0
    pending_summon = False

    while not monitor.abortRequested():
        try:
            player = xbmc.Player()
            audio = player.isPlayingAudio()
            published = source.directory_path() if source.has_lyrics() else ""
            if _take_summons():
                pending_summon = True

            if not audio:
                if presenter.holding():
                    presenter.stop_song()
                showing = ""
                shown_file = ""
                empty_ticks = 0
                pending_summon = False
            elif not published:
                playing = _playing_file(player)
                if playing != shown_file:
                    if presenter.holding():
                        presenter.blank_song()
                    shown_file = playing
                    empty_ticks = 1
                else:
                    empty_ticks += 1
                if empty_ticks >= EMPTY_TICKS_BEFORE_STOP:
                    if presenter.holding():
                        presenter.stop_song()
                        showing = ""
                    if pending_summon:
                        notify_no_lyrics()
                        pending_summon = False
            elif published != showing:
                empty_ticks = 0
                # A new path. Auto-off closes even a summoned window; a press
                # during the fetch is pending_summon and still shows. Load the
                # new lines first: summon() keeps _lines when they are already
                # set, which is the last song if this tick missed the blank.
                if pending_summon:
                    pending_summon = False
                    presenter.start_song()
                    presenter.summon()
                elif settings.show_automatically():
                    presenter.start_song()
                else:
                    presenter.stop_song()
                showing = published
                shown_file = _playing_file(player)
            else:
                empty_ticks = 0
                if presenter.awaiting_lines():
                    # Same path after a blank: repeat-one with a per-play URL.
                    presenter.start_song()
                    shown_file = _playing_file(player)
                if pending_summon:
                    pending_summon = False
                    presenter.summon()
                presenter.tick(_position(player))
        except Exception as error:  # never let a tick kill the service
            log("tick failed: %s" % error)

        if monitor.waitForAbort(TICK_SECONDS):
            break


def run() -> None:
    monitor = xbmc.Monitor()
    presenter = Presenter(monitor)
    log("service started")
    try:
        _loop(monitor, presenter)
    except Exception as error:  # pragma: no cover - defensive
        log("service loop failed: %s" % error)
    finally:
        # The window has to go: one left open pins Kodi's UI to it.
        try:
            presenter.close()
        except Exception:
            pass
    log("service stopped")
