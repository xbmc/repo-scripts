"""
Shared utilities for EasyMovie.

Provides structured logging, Kodi JSON-RPC helpers, settings accessors,
and notification utilities.

Logging:
    Logger: varies (factory function)
    Key events:
        - Varies by consumer module
    See LOGGING.md for full guidelines.
"""
from __future__ import annotations

import json
import os
import threading
import time
import traceback
from contextlib import contextmanager
from datetime import datetime as dt
from typing import Any, Dict, Generator, List, Optional, TextIO, Union

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from resources.lib.constants import (
    ADDON_ID,
    LOG_DIR,
    LOG_FILENAME,
    LOG_MAX_BYTES,
    LOG_BACKUP_COUNT,
    LOG_MAX_VALUE_LENGTH,
    LOG_TIMESTAMP_FORMAT,
    LOG_TIMESTAMP_TRIM,
    NOTIFICATION_DURATION_MS,
)


# Singleton addon instance
_addon: Optional[xbmcaddon.Addon] = None


def get_addon(addon_id: Optional[str] = None) -> xbmcaddon.Addon:
    """Get the addon instance (cached for default addon).

    Args:
        addon_id: Optional addon ID. If None, returns the current addon.
                  If provided, creates a new instance (not cached).

    Returns:
        The addon instance.
    """
    global _addon
    if addon_id is not None:
        return xbmcaddon.Addon(addon_id)
    if _addon is None:
        try:
            _addon = xbmcaddon.Addon()
        except RuntimeError:
            _addon = xbmcaddon.Addon(ADDON_ID)
    return _addon


def get_setting(setting_id: str, addon_id: Optional[str] = None) -> str:
    """Get a setting value as a string."""
    return get_addon(addon_id).getSetting(setting_id)


def get_bool_setting(setting_id: str, addon_id: Optional[str] = None) -> bool:
    """Get a boolean setting value."""
    return get_setting(setting_id, addon_id) == 'true'


def get_int_setting(setting_id: str, addon_id: Optional[str] = None, default: int = 0) -> int:
    """Get an integer setting value."""
    try:
        return int(float(get_setting(setting_id, addon_id)))
    except (ValueError, TypeError):
        return default


def get_string_setting(setting_id: str, addon_id: Optional[str] = None) -> str:
    """Get a string setting value."""
    return get_setting(setting_id, addon_id)


def lang(string_id: int, addon_id: Optional[str] = None) -> str:
    """Get localized string."""
    return get_addon(addon_id).getLocalizedString(string_id)


def notify(message: str, duration: int = NOTIFICATION_DURATION_MS) -> None:
    """Show a Kodi notification toast.

    Args:
        message: The notification message.
        duration: Duration in milliseconds.
    """
    xbmcgui.Dialog().notification(
        "EasyMovie", message, xbmcgui.NOTIFICATION_INFO, duration
    )


class StructuredLogger:
    """Structured logging for EasyMovie addon.

    Output Routing:
        - ERROR/WARNING/INFO: Kodi log (always) + easymovie.log (if debug enabled)
        - DEBUG: easymovie.log only (never pollutes Kodi log)

    See LOGGING.md for full guidelines.
    """

    # Class-level shared state for file handling
    _log_file: Optional[TextIO] = None
    _log_file_path: Optional[str] = None
    _log_file_size: int = 0
    _addon_id: str = ADDON_ID
    _debug_enabled: bool = False
    _initialized: bool = False
    _lock: threading.Lock = threading.Lock()

    def __init__(self, module_name: str) -> None:
        """Initialize a logger for a specific module."""
        self.module = module_name

    @classmethod
    def initialize(cls, debug_enabled: bool, addon_id: str = ADDON_ID) -> None:
        """Initialize the logging system. Idempotent."""
        with cls._lock:
            cls._addon_id = addon_id
            cls._debug_enabled = debug_enabled

            if cls._initialized:
                return

            cls._initialized = True

            if debug_enabled:
                cls._init_log_file()

    @classmethod
    def _init_log_file(cls) -> None:
        """Initialize log file with rotation. Must be called with lock held."""
        try:
            log_dir = xbmcvfs.translatePath(
                f"special://profile/addon_data/{cls._addon_id}/{LOG_DIR}/"
            )

            if not xbmcvfs.exists(log_dir):
                xbmcvfs.mkdirs(log_dir)

            log_path = os.path.join(log_dir, LOG_FILENAME)

            existing_size = 0
            if xbmcvfs.exists(log_path):
                try:
                    stat_result = xbmcvfs.Stat(log_path)
                    existing_size = stat_result.st_size()
                except (OSError, AttributeError):
                    existing_size = 0

                if existing_size > LOG_MAX_BYTES:
                    cls._rotate_logs(log_dir)
                    existing_size = 0

            cls._log_file_path = log_path
            try:
                cls._log_file = open(log_path, "a", encoding="utf-8")
                cls._log_file_size = existing_size
            except (OSError, IOError):
                cls._log_file = None
                raise
        except (OSError, IOError) as e:
            xbmc.log(
                f"[EasyMovie.logging] Failed to initialize log file: {e}",
                xbmc.LOGWARNING
            )
            cls._log_file = None

    @classmethod
    def _rotate_logs(cls, log_dir: str) -> None:
        """Rotate log files. Must be called with lock held."""
        try:
            oldest = os.path.join(log_dir, f"easymovie.{LOG_BACKUP_COUNT}.log")
            if xbmcvfs.exists(oldest):
                xbmcvfs.delete(oldest)

            for i in range(LOG_BACKUP_COUNT - 1, 0, -1):
                src = os.path.join(log_dir, f"easymovie.{i}.log")
                dst = os.path.join(log_dir, f"easymovie.{i + 1}.log")
                if xbmcvfs.exists(src):
                    xbmcvfs.rename(src, dst)

            current = os.path.join(log_dir, LOG_FILENAME)
            if xbmcvfs.exists(current):
                xbmcvfs.rename(current, os.path.join(log_dir, "easymovie.1.log"))
        except (OSError, IOError):
            pass

    @classmethod
    def shutdown(cls) -> None:
        """Close log file cleanly."""
        with cls._lock:
            if cls._log_file:
                try:
                    cls._log_file.close()
                except (OSError, IOError):
                    pass
                cls._log_file = None
            cls._initialized = False

    def _format_message(self, message: str, **kwargs: Any) -> str:
        """Format log message with optional key=value pairs."""
        base = f"[EasyMovie.{self.module}] {message}"
        if kwargs:
            pairs = []
            for k, v in kwargs.items():
                str_v = str(v)
                if k != 'trace' and len(str_v) > LOG_MAX_VALUE_LENGTH:
                    str_v = str_v[:LOG_MAX_VALUE_LENGTH] + "..."
                pairs.append(f"{k}={str_v}")
            return f"{base} | {', '.join(pairs)}"
        return base

    def _format_file_line(self, level: str, formatted_message: str) -> str:
        """Format a log line for file output with timestamp."""
        timestamp = dt.now().strftime(LOG_TIMESTAMP_FORMAT)[:LOG_TIMESTAMP_TRIM]
        return f"{timestamp} [{level:5}] {formatted_message}\n"

    def _write_to_file(self, level: str, formatted_message: str) -> None:
        """Write to log file if enabled, with thread safety."""
        if not StructuredLogger._debug_enabled or StructuredLogger._log_file is None:
            return

        line = self._format_file_line(level, formatted_message)

        with StructuredLogger._lock:
            try:
                if StructuredLogger._log_file is None:
                    return

                StructuredLogger._log_file.write(line)
                StructuredLogger._log_file.flush()
                StructuredLogger._log_file_size += len(line.encode("utf-8"))

                if StructuredLogger._log_file_size > LOG_MAX_BYTES:
                    StructuredLogger._log_file.close()
                    log_dir = os.path.dirname(StructuredLogger._log_file_path or "")
                    if log_dir:
                        StructuredLogger._rotate_logs(log_dir)
                    StructuredLogger._init_log_file()
            except (IOError, OSError):
                pass

    def _ensure_event(self, level: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure event= is present for INFO/WARNING/ERROR logs."""
        if "event" not in kwargs:
            kwargs["event"] = f"misc.{level}"
            kwargs["_missing_event"] = True
        return kwargs

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug-level message (file only when enabled)."""
        if StructuredLogger._debug_enabled:
            formatted = self._format_message(message, **kwargs)
            self._write_to_file("DEBUG", formatted)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info-level message (Kodi log + file)."""
        kwargs = self._ensure_event("info", kwargs)
        formatted = self._format_message(message, **kwargs)
        xbmc.log(formatted, xbmc.LOGINFO)
        self._write_to_file("INFO", formatted)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning-level message (Kodi log + file)."""
        kwargs = self._ensure_event("warning", kwargs)
        formatted = self._format_message(message, **kwargs)
        xbmc.log(formatted, xbmc.LOGWARNING)
        self._write_to_file("WARN", formatted)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error-level message (Kodi log + file)."""
        kwargs = self._ensure_event("error", kwargs)
        formatted = self._format_message(message, **kwargs)
        xbmc.log(formatted, xbmc.LOGERROR)
        self._write_to_file("ERROR", formatted)

    def exception(self, message: str, **kwargs: Any) -> None:
        """Log error with automatic stack trace capture."""
        kwargs["trace"] = traceback.format_exc()
        self.error(message, **kwargs)


def get_logger(module_name: str) -> StructuredLogger:
    """Get a logger for the specified module. Auto-initializes on first call."""
    if not StructuredLogger._initialized:
        try:
            debug_enabled = get_bool_setting('logging')
        except RuntimeError:
            debug_enabled = False

        try:
            addon_id = get_addon().getAddonInfo('id')
        except RuntimeError:
            addon_id = ADDON_ID

        StructuredLogger.initialize(debug_enabled=debug_enabled, addon_id=addon_id)

    return StructuredLogger(module_name)


class TimedOperation:
    """Timer object for marking phases within a timed operation."""

    def __init__(self, start_time: float) -> None:
        self._start = start_time
        self._phases: Dict[str, float] = {}
        self._last_mark = start_time

    def mark(self, phase_name: str) -> None:
        """Record elapsed time for a phase."""
        now = time.perf_counter()
        self._phases[phase_name] = now - self._last_mark
        self._last_mark = now

    def _get_phase_kwargs(self) -> Dict[str, int]:
        """Get phase timings as keyword arguments."""
        return {
            f"{name}_ms": int(duration * 1000)
            for name, duration in self._phases.items()
        }


@contextmanager
def log_timing(
    logger: StructuredLogger,
    operation: str,
    **context: Any
) -> Generator[TimedOperation, None, None]:
    """Context manager for timing operations.

    Args:
        logger: The logger instance to use.
        operation: Name of the operation being timed.
        **context: Additional context to include in the log.

    Yields:
        TimedOperation: Timer object with .mark(phase_name) method.
    """
    start = time.perf_counter()
    timer = TimedOperation(start)
    try:
        yield timer
    finally:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        phase_kwargs = timer._get_phase_kwargs()
        logger.debug(
            f"{operation} completed",
            duration_ms=elapsed_ms,
            **phase_kwargs,
            **context
        )


def invalidate_icon_cache(addon_id: str) -> None:
    """Remove the addon icon from Kodi's texture cache.

    Kodi caches textures by file path. After replacing icon.png,
    the old cached version persists until removed via JSON-RPC.
    """
    _log = get_logger('default')
    result = json_query({
        "jsonrpc": "2.0",
        "method": "Textures.GetTextures",
        "params": {
            "filter": {
                "field": "url",
                "operator": "contains",
                "value": addon_id,
            }
        },
        "id": 1,
    })
    for texture in result.get("textures", []):
        tid = texture.get("textureid")
        if tid:
            json_query({
                "jsonrpc": "2.0",
                "method": "Textures.RemoveTexture",
                "params": {"textureid": tid},
                "id": 1,
            }, return_result=False)
    _log.debug("Icon texture cache invalidated", event="icon.cache_clear",
               addon_id=addon_id)


def json_query(query: Union[Dict[str, Any], List[Dict[str, Any]]], return_result: bool = True) -> Dict[str, Any]:
    """Execute a JSON-RPC query against Kodi.

    Args:
        query: The JSON-RPC query dictionary.
        return_result: If True, return only the 'result' key.

    Returns:
        The query result or empty dict on error.
    """
    try:
        request = json.dumps(query)
        response = xbmc.executeJSONRPC(request)
        data = json.loads(response)

        if return_result:
            return data.get('result', {})
        return data
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        try:
            _log = get_logger('data')
            method = query.get("method", "unknown") if isinstance(query, dict) else "batch"
            _log.warning("JSON-RPC query failed", event="jsonrpc.error",
                         method=method, error=str(exc))
        except Exception:
            pass
        return {}
