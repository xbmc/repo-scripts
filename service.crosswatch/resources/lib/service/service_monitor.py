# SPDX-License-Identifier: GPL-2.0-only
"""Lifecycle callbacks: settings changes and video library scans."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import xbmc

from resources.lib.log import get_logger

_log = get_logger("service")


class ServiceMonitor(xbmc.Monitor):
    def __init__(self, controller: Any, on_settings_changed: Callable[[], None]) -> None:
        super().__init__()
        self._controller = controller
        self._on_settings_changed = on_settings_changed

    def onSettingsChanged(self) -> None:
        try:
            self._on_settings_changed()
        except Exception as exc:
            _log.error("service.settings_reload_failed", error=str(exc))

    def _safely(self, name: str, action) -> None:
        try:
            action()
        except Exception as exc:
            _log.error("service.callback_failed", callback=name, error=str(exc))

    def onScanFinished(self, library: str) -> None:
        if library == "video":
            self._safely("onScanFinished", self._controller.invalidate_index)

    def onCleanFinished(self, library: str) -> None:
        if library == "video":
            self._safely("onCleanFinished", self._controller.invalidate_index)
