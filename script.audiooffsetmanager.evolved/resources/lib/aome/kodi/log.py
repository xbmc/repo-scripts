"""Kodi logging adapter: a callable ``(message, level)`` sink.

A cached ``debug_escalation`` flag (seeded at construction, refreshed on
Kodi's ``SettingsChanged``) avoids a logger<->settings import cycle. It is
a bare attribute with no lock: its only writer is Kodi's callback thread
and its only reader is the dispatcher thread, and a stale read costs at
most one line's level (LOGDEBUG vs LOGINFO).

When set, the flag escalates LOGDEBUG lines to LOGINFO so users can
capture addon debug output without Kodi-wide debug logging. A message
already prefixed ``AOMe_`` or ``[AOM]`` is not double-tagged.
"""

import xbmc


class KodiLogger:
    """Callable ``(message, level)`` log sink."""

    def __init__(self, debug_escalation=False):
        # Refreshed by the runtime on SettingsChanged; no lock (see above).
        self.debug_escalation = debug_escalation

    def __call__(self, message, level=xbmc.LOGDEBUG):
        effective_level = (
            xbmc.LOGINFO
            if (level == xbmc.LOGDEBUG and self.debug_escalation)
            else level)
        use_prefix = (
            '' if message.startswith('[AOM]') or message.startswith('AOMe_')
            else '[AOM]')
        xbmc.log(f"{use_prefix} {message}".strip(), effective_level)

    def debug(self, message):
        self(message, xbmc.LOGDEBUG)

    def warning(self, message):
        self(message, xbmc.LOGWARNING)

    def error(self, message):
        self(message, xbmc.LOGERROR)
