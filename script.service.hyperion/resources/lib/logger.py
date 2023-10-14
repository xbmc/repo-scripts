"""Logging facility."""
import xbmc


class Logger:
    """Logging facility for Kodi add-ons."""

    def __init__(self, addon_name: str) -> None:
        self._addon_name = addon_name

    def log(self, message: str, level: int = xbmc.LOGDEBUG) -> None:
        """Writes the message to the logger with the addon name as prefix."""
        xbmc.log(f"[{self._addon_name}] - {message}", level=level)

    def debug(self, message: str) -> None:
        """Writes a debug message to the log."""
        self.log(message)

    def info(self, message: str) -> None:
        """Writes an info message to the log."""
        self.log(message, level=xbmc.LOGINFO)

    def error(self, message: str) -> None:
        """Writes an error message to the log."""
        self.log(message, level=xbmc.LOGERROR)
