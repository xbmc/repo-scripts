# SPDX-License-Identifier: GPL-2.0-only
"""Structured logging: fixed event names, key-value fields, no interpolated prose.

INFO and above reach Kodi's log and carry mechanism only: no names, no titles, no paths.
INFO arrives there at Kodi's debug level (see KodiRuntime.log). DEBUG carries identity and goes only to the addon's own file, only on opt-in, because that
file is what users paste into public issues.

Every value is escaped and redacted on the way out. The webhook token is a query parameter
and urllib puts whole URLs into exception messages, so one un-redacted error=str(exc) at any
future call site would otherwise leak a credential at ERROR.
"""

import os
import re
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any, TextIO

from resources.lib.constants import LOG_BACKUP_COUNT, LOG_MAX_BYTES, LOG_NAME

DEBUG, INFO, WARNING, ERROR = 10, 20, 30, 40

MAX_BYTES = LOG_MAX_BYTES

# A query is only treated as one when it looks like key=value. Without that, any media
# filename containing a question mark is mangled: "S01E01.Are.You.My.Mummy?.mkv" would
# lose its extension, and that field is exactly what the debug log exists to carry.
# The value stops before trailing dots, so a URL ending a sentence keeps the full stop
# that follows it: "See http://host/a?tok=1. Next sentence." must not lose the period.
# Dots followed by more value ("a..b") are part of it, or the pairs after them would leak.
# A raw space still ends the value: prose cannot tell it from the end of the URL, which is
# why media.strip_credentials drops the query whole instead of relying on this.
_VALUE = r"(?:[^\s'\".]|\.+(?=[^\s'\".]))*"
_PAIR = r"[\w.\-%~+]+=" + _VALUE
_QUERY = re.compile(
    r"(?P<scheme>[a-z][a-z0-9+.\-]*://[^\s'\"]*?)\?" + _PAIR + r"(?:&" + _PAIR + r")*", re.IGNORECASE
)
_USERINFO = re.compile(r"(?P<scheme>[a-z][a-z0-9+.\-]*://)[^/\s'\"@]+@", re.IGNORECASE)
# The bare form needs a host that looks like one: a dot or a port, then a path.
_BARE_QUERY = re.compile(
    r"(?P<host>(?:[\w\-]+\.[\w\-.]+|[\w\-]+:\d+)/[^\s'\"]*?)\?" + _PAIR + r"(?:&" + _PAIR + r")*"
)



def _null_sink(_message: str, _level: int) -> None:
    """Swallow a line.

    Installed before configure() runs and reinstalled by reset(), so every call site can
    emit unconditionally instead of testing whether a sink has been supplied yet.
    """


_lock = threading.Lock()
_log_dir: str | None = None
_debug = False
_secrets: tuple[str, ...] = ()
_sink: Callable[[str, int], None] = _null_sink
_handle: TextIO | None = None
_written = 0


def reset() -> None:
    """Return the module to its unconfigured state. Used by tests and by re-configuration."""
    global _log_dir, _debug, _sink, _handle, _written, _secrets
    with _lock:
        if _handle is not None:
            try:
                _handle.close()
            except OSError:
                pass
        _log_dir, _debug, _handle, _written = None, False, None, 0
        _sink = _null_sink
        _secrets = ()


def configure(log_dir: str | None, debug: bool, sink: Callable[[str, int], None]) -> None:
    global _log_dir, _debug, _sink
    with _lock:
        _sink = sink
        _debug = debug
        _log_dir = None
        if log_dir:
            try:
                os.makedirs(log_dir, mode=0o700, exist_ok=True)
                _log_dir = log_dir
            except OSError:
                # Logging is best effort. A read-only profile must not stop the addon
                # starting, and the Kodi sink above still works.
                _log_dir = None


def set_secret(value: str) -> None:
    """Register a literal that must never appear in a log line.

    redact() matches things that look like URLs, which is the right shape for a share path or
    a webhook address but cannot recognise a bare credential. A token reaches a log line by
    routes redact() will never see: http.client puts an illegal header value verbatim into
    its exception message, and that message is logged as a field. Matching the literal closes
    the class rather than the instance.
    """
    global _secrets
    cleaned = str(value or "").strip()
    if not cleaned:
        return
    # Both the literal and its escaped form. A token containing a newline reaches the log
    # through an exception message that embeds its repr, where that newline is a backslash
    # and an n rather than the byte itself, so matching only the literal misses exactly the
    # malformed tokens that cause the leak in the first place.
    forms = {cleaned, repr(cleaned)[1:-1]}
    with _lock:
        _secrets = (*_secrets, *(f for f in sorted(forms, key=len, reverse=True) if f not in _secrets))


def set_debug(debug: bool) -> None:
    """Change verbosity at runtime, so switching the setting off stops writing immediately."""
    global _debug
    with _lock:
        _debug = debug


def is_debug() -> bool:
    return _debug


def redact(value: str) -> str:
    """Strip credentials from anything in a field value that looks like a URL."""
    text = str(value)
    text = _USERINFO.sub(lambda m: f"{m.group('scheme')}<redacted>@", text)
    text = _QUERY.sub(lambda m: f"{m.group('scheme')}?<redacted>", text)
    return _BARE_QUERY.sub(lambda m: f"{m.group('host')}?<redacted>", text)


_ESCAPES = {"\\": r"\\", "\n": r"\n", "\r": r"\r", "\t": r"\t"}


def _clean(value: Any) -> str:
    text = str(value)
    for secret in _secrets:
        text = text.replace(secret, "<redacted>")
    text = redact(text)
    out = "".join(_ESCAPES.get(ch, ch) for ch in text)
    return "".join(ch for ch in out if ch >= " " or ch == " ")


def _format(name: str, event: str, fields: dict[str, Any]) -> str:
    if not fields:
        return f"[{name}] {event}"
    rendered = ", ".join(f"{k}={_clean(v)}" for k, v in fields.items())
    return f"[{name}] {event} | {rendered}"


def _path(index: int = 0) -> str:
    assert _log_dir is not None
    name = f"{LOG_NAME}.log" if index == 0 else f"{LOG_NAME}.{index}.log"
    return os.path.join(_log_dir, name)


def _open_handle() -> TextIO:
    global _handle, _written
    handle = open(_path(), "a", encoding="utf-8")
    _handle = handle
    try:
        _written = os.path.getsize(_path())
        os.chmod(_path(), 0o600)
    except OSError:
        _written = 0
    return handle


def _rotate() -> None:
    global _handle, _written
    if _handle is not None:
        _handle.close()
        _handle = None
    oldest = _path(LOG_BACKUP_COUNT)
    if os.path.exists(oldest):
        os.remove(oldest)
    for index in range(LOG_BACKUP_COUNT - 1, 0, -1):
        source = _path(index)
        if os.path.exists(source):
            os.replace(source, _path(index + 1))
    os.replace(_path(), _path(1))
    _written = 0


def _write_file(line: str) -> None:
    global _handle, _written
    if not _log_dir:
        return
    stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    record = f"{stamp} {line}\n"
    with _lock:
        try:
            # A local, not the global: a type checker cannot see a call reassign a module
            # global, so it would still think the handle is None after opening it.
            handle = _handle if _handle is not None else _open_handle()
            if _written >= MAX_BYTES:
                _rotate()
                handle = _open_handle()
            handle.write(record)
            handle.flush()
            _written += len(record.encode("utf-8"))
        except OSError:
            _handle = None


class StructuredLogger:
    """The event name is positional-only.

    Field names must be unconstrained: a caller logging an event field, a name field or a
    self field is ordinary, and reserving those words turns a log line into a TypeError at
    the moment something has already gone wrong.
    """

    def __init__(self, name: str, bound: dict[str, Any] | None = None) -> None:
        self._name = name
        self._bound = dict(bound or {})

    def bind(self, **fields: Any) -> "StructuredLogger":
        return StructuredLogger(self._name, {**self._bound, **fields})

    def _emit(self, level: int, event: str, fields: dict[str, Any]) -> None:
        if level == DEBUG and not _debug:
            return
        line = _format(self._name, event, {**self._bound, **fields})
        if level > DEBUG:
            _sink(line, level)
        if _debug:
            _write_file(line)

    def debug(self, event: str, /, **fields: Any) -> None:
        self._emit(DEBUG, event, fields)

    def info(self, event: str, /, **fields: Any) -> None:
        self._emit(INFO, event, fields)

    def warning(self, event: str, /, **fields: Any) -> None:
        self._emit(WARNING, event, fields)

    def error(self, event: str, /, **fields: Any) -> None:
        self._emit(ERROR, event, fields)


def get_logger(name: str) -> StructuredLogger:
    return StructuredLogger(name)


class Timer:
    def __init__(self) -> None:
        self._start = time.monotonic()
        self._last = self._start
        self.phases: dict[str, int] = {}

    def mark(self, phase: str) -> None:
        now = time.monotonic()
        # Namespaced, because build_index marks user-chosen playlist names and a playlist
        # called "duration" would otherwise collide with the reserved field.
        self.phases[f"phase_{phase}_ms"] = int((now - self._last) * 1000)
        self._last = now

    def elapsed_ms(self) -> int:
        return int((time.monotonic() - self._start) * 1000)


@contextmanager
def log_timing(log: StructuredLogger, event: str, /, **fields: Any) -> Iterator[Timer]:
    """Time an operation, reporting duration and outcome even when it raises.

    A slow failure is usually the strongest signal, so the line is emitted from a finally
    block. The emit is guarded: instrumentation must never replace the caller's exception.
    """
    timer = Timer()
    outcome = "success"
    try:
        yield timer
    except BaseException:
        outcome = "error"
        raise
    finally:
        try:
            merged = {**fields, "outcome": outcome, "duration_ms": timer.elapsed_ms(), **timer.phases}
            log.debug(event, **merged)
        except Exception:
            pass
