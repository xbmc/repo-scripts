#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Original work Copyright (C) 2013 KODeKarnage
#  Modified work Copyright (C) 2024-2026 Rouzax
#
#  SPDX-License-Identifier: GPL-3.0-or-later
#  See LICENSE.txt for more information.
#

"""
Shared utilities for EasyTV addon.

Consolidates common functions to avoid duplication across modules.

Logging:
    This module contains the StructuredLogger implementation used by all
    other modules. See LOGGING.md for complete documentation.
    
    Key exports:
        - StructuredLogger: Thread-safe structured logging class
        - get_logger(module_name): Factory function to get module loggers
"""
from __future__ import annotations

import datetime
import json
import os
import threading
import time
import traceback
from contextlib import contextmanager
from datetime import datetime as dt
import re
from typing import Any, Dict, Generator, List, Optional, TextIO, Tuple, Union, cast

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from resources.lib.constants import (
    DEFAULT_ADDON_ID,
    KODI_HOME_WINDOW_ID,
    PROP_SERVICE_RUNNING,
    LOG_DIR_NAME,
    LOG_FILENAME,
    LOG_MAX_ROTATED_FILES,
    LOG_MAX_SIZE_BYTES,
    LOG_MAX_VALUE_LENGTH,
    LOG_TIMESTAMP_FORMAT,
    LOG_TIMESTAMP_TRIM,
    VERSION_PRERELEASE_ALPHA,
    VERSION_PRERELEASE_BETA,
    VERSION_PRERELEASE_RELEASE,
)


# Singleton addon instance
_addon: Optional[xbmcaddon.Addon] = None


def get_addon(addon_id: Optional[str] = None) -> xbmcaddon.Addon:
    """
    Get the addon instance (cached for default addon).
    
    Args:
        addon_id: Optional addon ID. If None, returns the current addon.
                  If provided, creates a new instance (not cached).
    
    Returns:
        The addon instance.
    
    Note:
        When invoked via RunScript without proper addon context, Kodi cannot
        determine the addon automatically. In this case, we fall back to
        'script.easytv' as the default.
    """
    global _addon
    if addon_id is not None:
        return xbmcaddon.Addon(addon_id)
    if _addon is None:
        try:
            _addon = xbmcaddon.Addon()
        except RuntimeError:
            # Script invoked without addon context - use explicit ID
            _addon = xbmcaddon.Addon('script.easytv')
    return _addon


def get_setting(setting_id: str, addon_id: Optional[str] = None) -> str:
    """
    Get a setting value.
    
    Args:
        setting_id: The setting identifier.
        addon_id: Optional addon ID for cloned addons.
    
    Returns:
        The setting value as a string.
    """
    return get_addon(addon_id).getSetting(setting_id)


def get_bool_setting(setting_id: str, addon_id: Optional[str] = None) -> bool:
    """
    Get a boolean setting value.
    
    Args:
        setting_id: The setting identifier.
        addon_id: Optional addon ID for cloned addons.
    
    Returns:
        True if setting is 'true', False otherwise.
    """
    return get_setting(setting_id, addon_id) == 'true'


def get_int_setting(setting_id: str, addon_id: Optional[str] = None, default: int = 0) -> int:
    """
    Get an integer setting value.
    
    Args:
        setting_id: The setting identifier.
        addon_id: Optional addon ID for cloned addons.
        default: Default value if parsing fails.
    
    Returns:
        The setting value as an integer.
    """
    try:
        return int(float(get_setting(setting_id, addon_id)))
    except (ValueError, TypeError):
        return default


def get_float_setting(setting_id: str, addon_id: Optional[str] = None, default: float = 0.0) -> float:
    """
    Get a float setting value.
    
    Args:
        setting_id: The setting identifier.
        addon_id: Optional addon ID for cloned addons.
        default: Default value if parsing fails.
    
    Returns:
        The setting value as a float.
    """
    try:
        return float(get_setting(setting_id, addon_id))
    except (ValueError, TypeError):
        return default


def lang(string_id: int, addon_id: Optional[str] = None) -> str:
    """
    Get localized string.
    
    Args:
        string_id: The string ID from strings.po.
        addon_id: Optional addon ID for cloned addons.
    
    Returns:
        The localized string.
    """
    return get_addon(addon_id).getLocalizedString(string_id)


class StructuredLogger:
    """
    Structured logging for EasyTV addon.
    
    Output Routing:
        - ERROR/WARNING/INFO: Kodi log (always) + easytv.log (if debug enabled)
        - DEBUG: easytv.log only (never pollutes Kodi log)
    
    Level Guidelines:
        - ERROR: Operation failed. Use log.exception() for stack traces.
        - WARNING: Unexpected but handled. Include event=X.fallback
        - INFO: Significant event. Include event=domain.action
        - DEBUG: Developer details. No event= needed.
    
    Event Naming:
        Format: domain.action (e.g., "playback.start", "next.pick", "clone.fail")
        Required for INFO/WARNING/ERROR (auto-injected if missing), optional for DEBUG.
    
    Thread Safety:
        All file operations protected by threading.Lock(). Safe for concurrent
        logging from service loop and monitor callbacks.
    
    See LOGGING.md for full guidelines.
    
    Example:
        log = get_logger('daemon')
        log.info("Service started", event="service.start", version="4.0.8")
        log.debug("Processing shows", count=47)
        log.warning("Show not found", event="library.fallback", show_id=123)
        try:
            risky_operation()
        except Exception:
            log.exception("Operation failed", event="operation.fail")
    """
    
    # Class-level shared state for file handling
    _log_file: Optional[TextIO] = None
    _log_file_path: Optional[str] = None
    _log_file_size: int = 0
    _addon_id: str = DEFAULT_ADDON_ID
    _debug_enabled: bool = False
    _initialized: bool = False
    _lock: threading.Lock = threading.Lock()
    
    def __init__(self, module_name: str) -> None:
        """
        Initialize a logger for a specific module.
        
        Args:
            module_name: Name to identify the module (e.g., 'service', 'daemon').
        """
        self.module = module_name
    
    @classmethod
    def initialize(cls, debug_enabled: bool, addon_id: str = DEFAULT_ADDON_ID) -> None:
        """
        Initialize the logging system.
        
        Idempotent - safe to call multiple times. Sets up file logging
        if debug is enabled.
        
        Args:
            debug_enabled: Whether to enable debug logging (writes to file).
            addon_id: The addon ID for determining log file location.
        """
        with cls._lock:
            # Store settings even if already initialized (allows reconfiguration)
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
                f"special://profile/addon_data/{cls._addon_id}/{LOG_DIR_NAME}/"
            )
            
            # Ensure directory exists
            if not xbmcvfs.exists(log_dir):
                xbmcvfs.mkdirs(log_dir)
            
            log_path = os.path.join(log_dir, LOG_FILENAME)
            
            # Check if existing file needs rotation (exceeds size limit)
            existing_size = 0
            if xbmcvfs.exists(log_path):
                try:
                    stat_result = xbmcvfs.Stat(log_path)
                    existing_size = stat_result.st_size()
                except (OSError, AttributeError):
                    existing_size = 0
                
                if existing_size > LOG_MAX_SIZE_BYTES:
                    cls._rotate_logs(log_dir)
                    existing_size = 0  # File was rotated, new file is empty
            
            cls._log_file_path = log_path
            try:
                cls._log_file = open(log_path, "a", encoding="utf-8")
                cls._log_file_size = existing_size
            except (OSError, IOError):
                cls._log_file = None
                raise  # Re-raise to hit the outer except
        except (OSError, IOError) as e:
            # Log to Kodi if file init fails
            xbmc.log(
                f"[EasyTV.logging] Failed to initialize log file: {e}",
                xbmc.LOGWARNING
            )
            cls._log_file = None
    
    @classmethod
    def _rotate_logs(cls, log_dir: str) -> None:
        """
        Rotate log files: easytv.log -> easytv.1.log -> easytv.2.log -> deleted.
        Must be called with lock held.
        """
        try:
            # Delete oldest
            oldest = os.path.join(log_dir, f"easytv.{LOG_MAX_ROTATED_FILES}.log")
            if xbmcvfs.exists(oldest):
                xbmcvfs.delete(oldest)
            
            # Shift others down
            for i in range(LOG_MAX_ROTATED_FILES - 1, 0, -1):
                src = os.path.join(log_dir, f"easytv.{i}.log")
                dst = os.path.join(log_dir, f"easytv.{i + 1}.log")
                if xbmcvfs.exists(src):
                    xbmcvfs.rename(src, dst)
            
            # Current becomes .1
            current = os.path.join(log_dir, LOG_FILENAME)
            if xbmcvfs.exists(current):
                xbmcvfs.rename(current, os.path.join(log_dir, "easytv.1.log"))
        except (OSError, IOError):
            pass  # Best effort rotation
    
    @classmethod
    def shutdown(cls) -> None:
        """
        Close log file cleanly.
        
        Call this when the service stops to ensure all data is flushed.
        """
        with cls._lock:
            if cls._log_file:
                try:
                    cls._log_file.close()
                except (OSError, IOError):
                    pass
                cls._log_file = None
            cls._initialized = False
    
    def _format_message(self, message: str, **kwargs: Any) -> str:
        """
        Format log message with optional key=value pairs.
        
        Args:
            message: The main log message.
            **kwargs: Additional context as key=value pairs.
        
        Returns:
            Formatted string: "[EasyTV.module] message | key=value, ..."
        """
        base = f"[EasyTV.{self.module}] {message}"
        if kwargs:
            pairs = []
            for k, v in kwargs.items():
                str_v = str(v)
                if len(str_v) > LOG_MAX_VALUE_LENGTH:
                    str_v = str_v[:LOG_MAX_VALUE_LENGTH] + "..."
                pairs.append(f"{k}={str_v}")
            return f"{base} | {', '.join(pairs)}"
        return base
    
    def _format_file_line(self, level: str, formatted_message: str) -> str:
        """
        Format a log line for file output with timestamp.
        
        Args:
            level: Log level (DEBUG, INFO, WARN, ERROR).
            formatted_message: Already formatted message string.
        
        Returns:
            Timestamped log line with newline.
        """
        timestamp = dt.now().strftime(LOG_TIMESTAMP_FORMAT)[:LOG_TIMESTAMP_TRIM]
        return f"{timestamp} [{level:5}] {formatted_message}\n"
    
    def _write_to_file(self, level: str, formatted_message: str) -> None:
        """
        Write to log file if enabled, with thread safety and size-based rotation.
        
        Args:
            level: Log level string.
            formatted_message: Already formatted message.
        """
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
                
                # Mid-session rotation if file too large
                if StructuredLogger._log_file_size > LOG_MAX_SIZE_BYTES:
                    StructuredLogger._log_file.close()
                    log_dir = os.path.dirname(StructuredLogger._log_file_path or "")
                    if log_dir:
                        StructuredLogger._rotate_logs(log_dir)
                    StructuredLogger._init_log_file()
            except (IOError, OSError):
                pass  # Don't crash on log write failure
    
    def _ensure_event(self, level: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensure event= is present for INFO/WARNING/ERROR logs.
        
        If missing, injects a placeholder event and marks it for detection.
        
        Args:
            level: Log level (info, warning, error).
            kwargs: The keyword arguments dict.
        
        Returns:
            Updated kwargs dict with event injected if missing.
        """
        if "event" not in kwargs:
            kwargs["event"] = f"misc.{level}"
            kwargs["_missing_event"] = True
        return kwargs
    
    def debug(self, message: str, **kwargs: Any) -> None:
        """
        Log debug-level message (developer diagnostics).
        
        DEBUG goes to file only when enabled - never appears in Kodi log.
        No event= required for debug logs.
        
        Use for: function entry, algorithm decisions, loop summaries, timing.
        
        Args:
            message: The message to log.
            **kwargs: Additional context as key=value pairs.
        """
        if StructuredLogger._debug_enabled:
            formatted = self._format_message(message, **kwargs)
            self._write_to_file("DEBUG", formatted)
    
    def info(self, message: str, **kwargs: Any) -> None:
        """
        Log info-level message (significant events).
        
        INFO always goes to Kodi log, and to file when debug is enabled.
        Should include event= kwarg (auto-injected if missing).
        
        Use for: lifecycle events, user actions, operation completion.
        
        Args:
            message: The message to log.
            **kwargs: Additional context. Include event="domain.action".
        """
        kwargs = self._ensure_event("info", kwargs)
        formatted = self._format_message(message, **kwargs)
        xbmc.log(formatted, xbmc.LOGINFO)
        self._write_to_file("INFO", formatted)
    
    def warning(self, message: str, **kwargs: Any) -> None:
        """
        Log warning-level message (unexpected but handled).
        
        WARNING always goes to Kodi log, and to file when debug is enabled.
        Should include event= kwarg (auto-injected if missing).
        
        Use for: fallbacks taken, missing data recovered, retries needed.
        
        Args:
            message: The message to log.
            **kwargs: Additional context. Include event="domain.fallback".
        """
        kwargs = self._ensure_event("warning", kwargs)
        formatted = self._format_message(message, **kwargs)
        xbmc.log(formatted, xbmc.LOGWARNING)
        self._write_to_file("WARN", formatted)
    
    def error(self, message: str, **kwargs: Any) -> None:
        """
        Log error-level message (operation failed).
        
        ERROR always goes to Kodi log, and to file when debug is enabled.
        Should include event= kwarg (auto-injected if missing).
        
        For exceptions, prefer log.exception() which auto-captures stack trace.
        
        Args:
            message: The message to log.
            **kwargs: Additional context. Include event="domain.fail".
        """
        kwargs = self._ensure_event("error", kwargs)
        formatted = self._format_message(message, **kwargs)
        xbmc.log(formatted, xbmc.LOGERROR)
        self._write_to_file("ERROR", formatted)
    
    def exception(self, message: str, **kwargs: Any) -> None:
        """
        Log error with automatic stack trace capture.
        
        Use this in except blocks to automatically capture the full stack trace.
        The trace is included in the log output.
        
        Args:
            message: The message to log.
            **kwargs: Additional context. Include event="domain.fail".
        
        Example:
            try:
                risky_operation()
            except Exception:
                log.exception("Operation failed", event="operation.fail", id=123)
        """
        kwargs["trace"] = traceback.format_exc()
        self.error(message, **kwargs)


def get_logger(module_name: str) -> StructuredLogger:
    """
    Get a logger for the specified module.
    
    Auto-initializes the logging system on first call if not already initialized.
    Safe to call from any entry point (service.py, default.py, clone scripts).
    
    Args:
        module_name: Name to identify the module (e.g., 'service', 'daemon').
    
    Returns:
        A StructuredLogger instance for the module.
    
    Example:
        log = get_logger('service')
        log.info("Service started", event="service.start", version="4.0.8")
        log.debug("Processing shows", count=47)
    """
    # Lazy initialization - auto-init if not already done
    if not StructuredLogger._initialized:
        try:
            debug_enabled = get_bool_setting('logging')
        except RuntimeError:
            debug_enabled = False  # Default OFF when settings unavailable
        
        try:
            addon_id = get_addon().getAddonInfo('id')
        except RuntimeError:
            addon_id = DEFAULT_ADDON_ID
        
        StructuredLogger.initialize(debug_enabled=debug_enabled, addon_id=addon_id)
    
    return StructuredLogger(module_name)


class TimedOperation:
    """
    Timer object for marking phases within a timed operation.
    
    Yielded by log_timing() to allow marking intermediate phases.
    Each phase records the elapsed time since the operation started.
    
    Usage is optional - existing log_timing() calls that don't use the
    yielded timer will continue to work unchanged.
    
    Example:
        with log_timing(log, "bulk_refresh") as timer:
            # ... do queries ...
            timer.mark("queries")
            # ... do playlists ...
            timer.mark("playlists")
        # Logs: "bulk_refresh completed | duration_ms=11600, queries_ms=9200, playlists_ms=2400"
    """
    
    def __init__(self, start_time: float) -> None:
        """
        Initialize the timer.
        
        Args:
            start_time: The perf_counter() value when the operation started.
        """
        self._start = start_time
        self._phases: Dict[str, float] = {}
        self._last_mark = start_time
    
    def mark(self, phase_name: str) -> None:
        """
        Record elapsed time for a phase.
        
        Records the time from the previous mark (or operation start) to now.
        
        Args:
            phase_name: Name of the phase that just completed.
        """
        now = time.perf_counter()
        # Record time since last mark (or start)
        self._phases[phase_name] = now - self._last_mark
        self._last_mark = now
    
    def _get_phase_kwargs(self) -> Dict[str, int]:
        """
        Get phase timings as keyword arguments for logging.
        
        Returns:
            Dict mapping phase names (with _ms suffix) to duration in milliseconds.
        """
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
    """
    Context manager for timing operations with optional phase breakdown.
    
    Logs the duration of the wrapped code block at DEBUG level.
    Useful for performance monitoring without cluttering code with timing logic.
    
    Yields a TimedOperation object that can be used to mark phases within
    the operation. Phase timings are included in the final log message.
    Using the yielded timer is optional - existing code that ignores it
    will continue to work unchanged.
    
    Args:
        logger: The logger instance to use.
        operation: Name of the operation being timed.
        **context: Additional context to include in the log.
    
    Yields:
        TimedOperation: Timer object with .mark(phase_name) method for
            recording intermediate phase timings.
    
    Example (simple):
        log = get_logger('playback')
        with log_timing(log, "playlist_build", mode="random"):
            build_playlist()
        # Logs: "playlist_build completed | duration_ms=312, mode=random"
    
    Example (with phases):
        with log_timing(log, "bulk_refresh") as timer:
            do_queries()
            timer.mark("queries")
            build_playlists()
            timer.mark("playlists")
        # Logs: "bulk_refresh completed | duration_ms=11600, queries_ms=9200, playlists_ms=2400"
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


def json_query(query: Union[Dict[str, Any], List[Dict[str, Any]]], return_result: bool = True) -> Dict[str, Any]:
    """
    Execute a JSON-RPC query against Kodi.
    
    Args:
        query: The JSON-RPC query dictionary.
        return_result: If True, return only the 'result' key; otherwise return full response.
    
    Returns:
        The query result or empty dict on error.
    """
    try:
        request = json.dumps(query)
        response = xbmc.executeJSONRPC(request)
        # In Python 3, executeJSONRPC already returns a string
        data = json.loads(response)
        
        if return_result:
            return data.get('result', {})
        return data
    except (json.JSONDecodeError, KeyError, TypeError):
        return {}


def runtime_converter(time_string: str) -> int:
    """
    Convert a runtime string to seconds.
    
    Args:
        time_string: Runtime in HH:MM:SS or MM:SS format.
    
    Returns:
        Total seconds, or 0 if parsing fails.
    """
    if not time_string:
        return 0
    
    try:
        parts = time_string.split(':')
        if len(parts) == 3:
            hours, minutes, seconds = map(int, parts)
            return hours * 3600 + minutes * 60 + seconds
        elif len(parts) == 2:
            minutes, seconds = map(int, parts)
            return minutes * 60 + seconds
        else:
            return int(parts[0])
    except (ValueError, TypeError, IndexError):
        return 0


def format_duration(seconds: Union[int, str]) -> str:
    """
    Format a duration in seconds to a human-readable string.

    Args:
        seconds: Duration in seconds (int or string).

    Returns:
        Formatted string like "43 min" or "1h 30min". Empty string if zero/invalid.
    """
    try:
        total = int(seconds)
    except (ValueError, TypeError):
        return ''
    if total <= 0:
        return ''
    minutes = round(total / 60)
    if minutes < 60:
        return f"{minutes} min"
    hours = minutes // 60
    remaining = minutes % 60
    if remaining == 0:
        return f"{hours}h"
    return f"{hours}h {remaining}min"


def get_playcount_minimum_percent() -> int:
    """
    Get Kodi's watched threshold from advancedsettings.xml.
    
    This is the percentage of a video that must be watched before
    Kodi automatically marks it as watched. EasyTV uses this to
    determine when to prepare the next episode.
    
    The setting is read from:
        <advancedsettings>
            <video>
                <playcountminimumpercent>90</playcountminimumpercent>
            </video>
        </advancedsettings>
    
    Returns:
        Percentage (0-100). Default is 90 if not configured or on error.
    
    Example:
        threshold = get_playcount_minimum_percent() / 100.0  # 0.90
        target_time = duration * threshold
    """
    from xml.etree import ElementTree as ET
    
    DEFAULT_THRESHOLD = 90
    
    try:
        advanced_settings_path = xbmcvfs.translatePath(
            'special://masterprofile/advancedsettings.xml'
        )
        tree = ET.parse(advanced_settings_path)
        root = tree.getroot()
        
        element = root.find('video/playcountminimumpercent')
        if element is not None and element.text:
            value = int(element.text)
            # Validate range (Kodi accepts 0-100)
            if 0 <= value <= 100:
                return value
    except FileNotFoundError:
        pass  # File doesn't exist - use default
    except ET.ParseError:
        pass  # Malformed XML - use default
    except (ValueError, AttributeError):
        pass  # Invalid value - use default
    
    return DEFAULT_THRESHOLD


def get_ignore_seconds_at_start() -> int:
    """
    Get Kodi's ignore seconds at start from advancedsettings.xml.
    
    This is the number of seconds at the start of a video that must
    pass before Kodi will create a resume point. Allows users to
    preview videos without creating resume marks.
    
    The setting is read from:
        <advancedsettings>
            <video>
                <ignoresecondsatstart>180</ignoresecondsatstart>
            </video>
        </advancedsettings>
    
    Returns:
        Seconds (0+). Default is 180 if not configured or on error.
    """
    from xml.etree import ElementTree as ET
    
    DEFAULT_SECONDS = 180
    
    try:
        advanced_settings_path = xbmcvfs.translatePath(
            'special://masterprofile/advancedsettings.xml'
        )
        tree = ET.parse(advanced_settings_path)
        root = tree.getroot()
        
        element = root.find('video/ignoresecondsatstart')
        if element is not None and element.text:
            value = int(element.text)
            if value >= 0:
                return value
    except FileNotFoundError:
        pass  # File doesn't exist - use default
    except ET.ParseError:
        pass  # Malformed XML - use default
    except (ValueError, AttributeError):
        pass  # Invalid value - use default
    
    return DEFAULT_SECONDS


def get_ignore_percent_at_end() -> int:
    """
    Get Kodi's ignore percent at end from advancedsettings.xml.
    
    This is the percentage at the end of a video where Kodi will
    not create a resume point. Prevents resume marks during credits.
    
    The setting is read from:
        <advancedsettings>
            <video>
                <ignorepercentatend>8</ignorepercentatend>
            </video>
        </advancedsettings>
    
    Returns:
        Percentage (0-100). Default is 8 if not configured or on error.
    """
    from xml.etree import ElementTree as ET
    
    DEFAULT_PERCENT = 8
    
    try:
        advanced_settings_path = xbmcvfs.translatePath(
            'special://masterprofile/advancedsettings.xml'
        )
        tree = ET.parse(advanced_settings_path)
        root = tree.getroot()
        
        element = root.find('video/ignorepercentatend')
        if element is not None and element.text:
            value = int(element.text)
            if 0 <= value <= 100:
                return value
    except FileNotFoundError:
        pass  # File doesn't exist - use default
    except ET.ParseError:
        pass  # Malformed XML - use default
    except (ValueError, AttributeError):
        pass  # Invalid value - use default
    
    return DEFAULT_PERCENT


def is_shared_video_database() -> bool:
    """
    Check if Kodi's video library uses a shared MySQL/MariaDB database.
    
    Reads from advancedsettings.xml:
        <advancedsettings>
            <videodatabase>
                <type>mysql</type>
            </videodatabase>
        </advancedsettings>
    
    Returns:
        True if videodatabase type is 'mysql', False otherwise
        (including when advancedsettings.xml doesn't exist or has no
        videodatabase section).
    """
    from xml.etree import ElementTree as ET
    
    try:
        advanced_settings_path = xbmcvfs.translatePath(
            'special://masterprofile/advancedsettings.xml'
        )
        tree = ET.parse(advanced_settings_path)
        root = tree.getroot()
        
        element = root.find('videodatabase/type')
        if element is not None and element.text:
            return element.text.strip().lower() == 'mysql'
    except FileNotFoundError:
        pass  # File doesn't exist - local DB
    except ET.ParseError:
        pass  # Malformed XML - assume local
    except (ValueError, AttributeError):
        pass  # Invalid value - assume local
    
    return False


def sanitize_filename(dirty_string: str) -> str:
    """
    Sanitize a string for use as a filename or addon ID.
    
    Removes or replaces characters that are invalid in filenames
    or addon identifiers. Spaces are converted to underscores and
    the result is lowercased.
    
    Args:
        dirty_string: The string to sanitize.
    
    Returns:
        A safe string containing only alphanumeric characters,
        underscores, hyphens, periods, and parentheses.
    
    Example:
        sanitize_filename("My Show! (2024)")  # Returns "my_show_2024"
        sanitize_filename("  Test & Demo  ")  # Returns "test__demo"
    """
    import string as string_module
    
    dirty_string = dirty_string.strip()
    valid_chars = f"-_.(){string_module.ascii_letters}{string_module.digits} "
    sanitized = ''.join(c for c in dirty_string if c in valid_chars)
    sanitized = sanitized.replace(' ', '_').lower()
    return sanitized


# =============================================================================
# Icon Management
# =============================================================================

_icon_log: Optional[StructuredLogger] = None


def _get_icon_log() -> StructuredLogger:
    """Lazy-init logger for icon management functions."""
    global _icon_log
    if _icon_log is None:
        _icon_log = get_logger('icon')
    return _icon_log


def set_custom_icon(addon_id: Optional[str] = None) -> bool:
    """Open image browser and copy selected image to addon's icon.png.

    Also saves a copy to addon_data for persistence across addon/clone updates.

    Args:
        addon_id: Addon to set icon for. None for the current addon.

    Returns:
        True if icon was successfully set, False if cancelled or failed.
    """
    log = _get_icon_log()
    addon = xbmcaddon.Addon(addon_id) if addon_id else xbmcaddon.Addon()
    addon_path = addon.getAddonInfo('path')

    dialog = xbmcgui.Dialog()
    image_path = cast(str, dialog.browse(
        2, lang(32739), 'files', '.png|.jpg|.jpeg', False, False
    ))
    if not image_path:
        log.debug("Icon selection cancelled", event="icon.set_cancelled")
        return False

    log.debug("Icon selected", event="icon.selected", path=image_path)
    icon_path = os.path.join(addon_path, 'icon.png')

    # Save to addon_data for persistence across updates
    addon_data = xbmcvfs.translatePath(addon.getAddonInfo('profile'))
    os.makedirs(addon_data, exist_ok=True)
    backup_path = os.path.join(addon_data, 'custom_icon.png')
    backup_ok = xbmcvfs.copy(image_path, backup_path)
    if not backup_ok:
        log.warning("Failed to backup icon to addon_data",
                    event="icon.backup_fail", path=backup_path)

    # Copy to addon folder
    result = xbmcvfs.copy(image_path, icon_path)
    if result:
        log.info("Custom icon set", event="icon.set",
                 source=image_path, addon_id=addon.getAddonInfo('id'))
    else:
        log.warning("Failed to copy icon to addon folder",
                    event="icon.set_fail", source=image_path, target=icon_path)
    return result


def reset_icon(addon_id: Optional[str] = None) -> bool:
    """Restore the default icon and remove custom icon from addon_data.

    Args:
        addon_id: Addon to reset icon for. None for the current addon.

    Returns:
        True if icon was successfully reset, False if default icon not found.
    """
    log = _get_icon_log()
    addon = xbmcaddon.Addon(addon_id) if addon_id else xbmcaddon.Addon()
    addon_path = addon.getAddonInfo('path')

    default_path = os.path.join(addon_path, 'icon_default.png')
    icon_path = os.path.join(addon_path, 'icon.png')

    # Remove custom icon backup
    addon_data = xbmcvfs.translatePath(addon.getAddonInfo('profile'))
    custom_backup = os.path.join(addon_data, 'custom_icon.png')
    if xbmcvfs.exists(custom_backup):
        xbmcvfs.delete(custom_backup)
        log.debug("Removed custom icon backup", event="icon.backup_removed",
                  path=custom_backup)

    if xbmcvfs.exists(default_path):
        result = xbmcvfs.copy(default_path, icon_path)
        if result:
            log.info("Icon reset to default", event="icon.reset",
                     addon_id=addon.getAddonInfo('id'))
        else:
            log.warning("Failed to restore default icon",
                        event="icon.reset_fail", source=default_path)
        return result

    log.warning("Default icon not found", event="icon.default_missing",
                path=default_path)
    return False


def restore_custom_icon(addon_id: Optional[str] = None) -> bool:
    """Restore custom icon from addon_data after an addon/clone update.

    No-op if no custom icon was previously set. Called on service startup
    to handle the case where a Kodi addon update overwrote icon.png.

    Args:
        addon_id: Addon to restore icon for. None for the current addon.

    Returns:
        True if custom icon was restored, False if none was set.
    """
    log = _get_icon_log()
    addon = xbmcaddon.Addon(addon_id) if addon_id else xbmcaddon.Addon()
    addon_data = xbmcvfs.translatePath(addon.getAddonInfo('profile'))
    custom_backup = os.path.join(addon_data, 'custom_icon.png')
    if xbmcvfs.exists(custom_backup):
        icon_path = os.path.join(addon.getAddonInfo('path'), 'icon.png')
        result = xbmcvfs.copy(custom_backup, icon_path)
        if result:
            log.info("Custom icon restored after update", event="icon.restore",
                     addon_id=addon.getAddonInfo('id'))
        else:
            log.warning("Failed to restore custom icon",
                        event="icon.restore_fail", source=custom_backup)
        return result
    log.debug("No custom icon to restore", event="icon.restore_skip")
    return False


# =============================================================================
# Kodi Interaction Utilities
# =============================================================================

# Module-level monitor for abort checking
_monitor: Optional[xbmc.Monitor] = None


def _get_monitor() -> xbmc.Monitor:
    """Get or create the module-level Monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = xbmc.Monitor()
    return _monitor


def is_abort_requested() -> bool:
    """
    Check if Kodi has requested an abort (shutdown/restart).
    
    Use this in long-running loops to allow graceful exit when
    Kodi is shutting down or the addon is being disabled.
    
    Returns:
        True if Kodi has requested an abort, False otherwise.
    
    Example:
        while not is_abort_requested():
            do_work()
            xbmc.sleep(100)
    """
    return _get_monitor().abortRequested()


def service_heartbeat() -> None:
    """
    Respond to service liveness checks from the UI.
    
    The background service (service.py) must respond to "marco/polo" pings 
    from the UI (default.py) to confirm it is running. Call this regularly
    in service loops to maintain responsiveness and allow the UI to detect
    service availability.
    
    When default.py sets the property to 'marco', this function responds
    with 'polo' to confirm the service is alive.
    
    Example:
        while not is_abort_requested():
            do_processing()
            service_heartbeat()
            xbmc.sleep(100)
    """
    window = xbmcgui.Window(KODI_HOME_WINDOW_ID)
    
    # Respond to service liveness check from the addon
    # When default.py sends 'marco', respond with 'polo' to confirm service is running
    if window.getProperty(PROP_SERVICE_RUNNING) == 'marco':
        window.setProperty(PROP_SERVICE_RUNNING, 'polo')


def restart_addon(addon_id: str, delay_ms: int = 500) -> None:
    """Disable and re-enable a Kodi addon to force a restart.

    Args:
        addon_id: The addon ID to restart.
        delay_ms: Milliseconds to wait between disable and enable.
    """
    import json as _json
    xbmc.executeJSONRPC(_json.dumps({
        "jsonrpc": "2.0",
        "method": "Addons.SetAddonEnabled",
        "id": 1,
        "params": {"addonid": addon_id, "enabled": False}
    }))
    xbmc.sleep(delay_ms)
    xbmc.executeJSONRPC(_json.dumps({
        "jsonrpc": "2.0",
        "method": "Addons.SetAddonEnabled",
        "id": 1,
        "params": {"addonid": addon_id, "enabled": True}
    }))


def parse_lastplayed_date(date_string: str) -> float:
    """
    Parse a lastplayed date string into a Unix timestamp.
    
    Kodi stores lastplayed dates in 'YYYY-MM-DD HH:MM:SS' format.
    This function converts them to Unix timestamps for comparison
    and sorting operations.
    
    Args:
        date_string: Date in 'YYYY-MM-DD HH:MM:SS' format.
    
    Returns:
        Unix timestamp (float), or 0.0 if parsing fails or string is empty.
    
    Example:
        timestamp = parse_lastplayed_date("2024-03-15 20:30:00")
        # Returns something like 1710531000.0
        
        timestamp = parse_lastplayed_date("")
        # Returns 0.0
    """
    if not date_string:
        return 0.0
    
    try:
        parsed = time.strptime(date_string, '%Y-%m-%d %H:%M:%S')
        Y, M, D, h, mn, s = parsed[:6]
        dt = datetime.datetime(Y, M, D, h, mn, s)
        return time.mktime(dt.timetuple())
    except (ValueError, TypeError):
        return 0.0


@contextmanager
def busy_progress(message: str = "Loading...") -> Generator[None, None, None]:
    """
    Show a background progress dialog during slow operations.
    
    Uses DialogProgressBG which shows in the corner, non-modal.
    Automatically closes on exit (normal or exception).
    
    Args:
        message: Text to display in the progress dialog.
        
    Yields:
        None - this is a simple context manager for visual feedback.
        
    Example:
        with busy_progress("Loading shows..."):
            slow_operation()
    """
    dialog = xbmcgui.DialogProgressBG()
    dialog.create("EasyTV", message)
    try:
        yield
    finally:
        dialog.close()


# =============================================================================
# Version Parsing
# =============================================================================

# Regex pattern for version strings: major.minor.patch[~alpha|beta<num>]
_VERSION_PATTERN = re.compile(r'^(\d+)\.(\d+)\.(\d+)(?:~(alpha|beta)(\d+))?$')


def parse_version(version_str: str) -> Tuple[int, int, int, int, int]:
    """
    Parse version string with prerelease support.
    
    Handles Kodi addon version format including optional ~alpha/~beta suffixes.
    Returns a 5-tuple suitable for comparison using Python's native tuple ordering.
    
    Args:
        version_str: Version string like "1.2.3", "1.2.3~beta1", "1.2.3~alpha2"
    
    Returns:
        Tuple of (major, minor, patch, prerelease_type, prerelease_num) where:
        - prerelease_type: 0=alpha, 1=beta, 2=release
        - prerelease_num: number after alpha/beta, or 0 for release
    
    Ordering (via tuple comparison):
        1.2.3~alpha1 < 1.2.3~alpha2 < 1.2.3~beta1 < 1.2.3~beta10 < 1.2.3
    
    Example:
        parse_version("1.2.3")        -> (1, 2, 3, 2, 0)
        parse_version("1.2.3~beta1")  -> (1, 2, 3, 1, 1)
        parse_version("1.2.3~alpha2") -> (1, 2, 3, 0, 2)
    
    Raises:
        ValueError: If version string doesn't match expected format.
    """
    match = _VERSION_PATTERN.match(version_str)
    if not match:
        raise ValueError(f"Invalid version format: {version_str}")
    
    major = int(match.group(1))
    minor = int(match.group(2))
    patch = int(match.group(3))
    prerelease_tag = match.group(4)  # 'alpha', 'beta', or None
    prerelease_num_str = match.group(5)  # digit string or None
    
    if prerelease_tag is None:
        # Release version
        prerelease_type = VERSION_PRERELEASE_RELEASE
        prerelease_num = 0
    elif prerelease_tag == 'alpha':
        prerelease_type = VERSION_PRERELEASE_ALPHA
        prerelease_num = int(prerelease_num_str)
    else:  # beta
        prerelease_type = VERSION_PRERELEASE_BETA
        prerelease_num = int(prerelease_num_str)
    
    return (major, minor, patch, prerelease_type, prerelease_num)


def compare_versions(v1: str, v2: str) -> int:
    """
    Compare two version strings.
    
    Uses parse_version() to convert strings to comparable tuples,
    then uses Python's native tuple comparison.
    
    Args:
        v1: First version string
        v2: Second version string
    
    Returns:
        -1 if v1 < v2
         0 if v1 == v2
         1 if v1 > v2
    
    Ordering follows Kodi's versioning rules:
        1.2.3~alpha1 < 1.2.3~beta1 < 1.2.3
    
    Example:
        compare_versions("1.2.3~beta1", "1.2.3")  -> -1  (beta < release)
        compare_versions("1.2.3", "1.2.3")        ->  0  (equal)
        compare_versions("1.2.4", "1.2.3~beta1")  ->  1  (1.2.4 > 1.2.3~beta1)
    
    Raises:
        ValueError: If either version string doesn't match expected format.
    """
    t1 = parse_version(v1)
    t2 = parse_version(v2)
    
    if t1 < t2:
        return -1
    elif t1 > t2:
        return 1
    else:
        return 0
