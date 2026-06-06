"""Logging utilities for Skin Shortcuts.

Usage:
    from skinshortcuts.log import get_logger
    log = get_logger("TemplateBuilder")
    log.debug("Loading templates...")  # -> script.skinshortcuts: TemplateBuilder - ...
"""

from __future__ import annotations

try:
    import xbmc

    IN_KODI = True
except ImportError:
    IN_KODI = False

PREFIX = "script.skinshortcuts:"

if IN_KODI:
    import xbmcaddon

    DEBUG = xbmcaddon.Addon().getSettingBool("debug")
else:
    DEBUG = False


class Logger:
    """Component-specific logger."""

    def __init__(self, component: str = "") -> None:
        self.component = component

    def _format(self, msg: str) -> str:
        if self.component:
            return f"{PREFIX} {self.component} - {msg}"
        return f"{PREFIX} {msg}"

    def _log(self, msg: str, level: int | None = None) -> None:
        formatted = self._format(msg)
        if IN_KODI:
            if level is None:
                level = xbmc.LOGINFO
            if DEBUG and level == xbmc.LOGDEBUG:
                level = xbmc.LOGINFO
            xbmc.log(formatted, level)
        else:
            print(formatted)

    def debug(self, msg: str) -> None:
        self._log(msg, xbmc.LOGDEBUG if IN_KODI else None)

    def info(self, msg: str) -> None:
        self._log(msg, xbmc.LOGINFO if IN_KODI else None)

    def warning(self, msg: str) -> None:
        self._log(msg, xbmc.LOGWARNING if IN_KODI else None)

    def error(self, msg: str) -> None:
        self._log(msg, xbmc.LOGERROR if IN_KODI else None)


_loggers: dict[str, Logger] = {}


def get_logger(component: str = "") -> Logger:
    """Get a logger for a specific component."""
    if component not in _loggers:
        _loggers[component] = Logger(component)
    return _loggers[component]


def notify(heading: str, message: str) -> None:
    """Fire a Kodi notification. No-op outside Kodi so loaders stay testable."""
    if not IN_KODI:
        return
    import xbmcgui

    xbmcgui.Dialog().notification(heading, message)
