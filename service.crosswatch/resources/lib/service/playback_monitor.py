# SPDX-License-Identifier: GPL-2.0-only
"""Forwards Kodi's player callbacks to the controller.

Kodi queues these and executes them on this addon's own service thread, from inside
Monitor.waitForAbort and from a window's doModal (the who-watched question), so they are not
running on a Kodi thread and there is no concurrency here. The reason to keep them trivial is different: this thread is the only thing that
delivers callbacks and observes abort, so parking it stalls everything.
"""

from __future__ import annotations

from typing import Any

import xbmc

from resources.lib.log import get_logger

_log = get_logger("player")


class PlaybackMonitor(xbmc.Player):
    def __init__(self, controller: Any) -> None:
        super().__init__()
        self._controller = controller

    def _safely(self, name: str, action) -> None:
        try:
            action()
        except Exception as exc:
            _log.error("player.callback_failed", callback=name, error=str(exc))

    def onAVStarted(self) -> None:
        self._safely("onAVStarted", self._controller.on_av_started)

    def onPlayBackPaused(self) -> None:
        self._safely("onPlayBackPaused", self._controller.on_paused)

    def onPlayBackResumed(self) -> None:
        self._safely("onPlayBackResumed", self._controller.on_resumed)

    def onPlayBackSeek(self, time: int, seekOffset: int) -> None:
        # Neither argument is used: they describe the requested seek, and the tick re-samples
        # the position Kodi actually reached.
        self._safely("onPlayBackSeek", self._controller.on_seek)

    def onPlayBackSeekChapter(self, chapter: int) -> None:
        self._safely("onPlayBackSeekChapter", self._controller.on_seek)

    def onPlayBackStopped(self) -> None:
        self._safely("onPlayBackStopped", lambda: self._controller.on_stopped(completed=False))

    def onPlayBackEnded(self) -> None:
        self._safely("onPlayBackEnded", lambda: self._controller.on_stopped(completed=True))
