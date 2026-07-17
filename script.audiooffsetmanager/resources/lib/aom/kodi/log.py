"""Kodi logging adapter: a callable ``(message, level)`` sink.

The adapter holds a plain cached ``debug_escalation`` flag: the runtime seeds
it once at construction (from a value the caller reads out of settings) and
refreshes it on Kodi's ``SettingsChanged`` callback. No settings import here —
a logger<->settings import knot would stop the logger being a leaf.

The cached flag is a bare attribute deliberately. Its only writer is the
runtime's ``SettingsChanged`` handler (Kodi's callback thread) and its only
reader is the dispatcher thread; a stale read costs at most one log line's
level (LOGDEBUG vs LOGINFO) and nothing else, so it carries no lock.

Escalation and prefix behavior: a LOGDEBUG line escalates to LOGINFO when the
addon debug toggle is on (so users can capture addon debug lines without
turning on Kodi-wide debug), and a message already prefixed ``AOM_`` or
``[AOM]`` is not double-tagged.

This layer may import ``xbmc*`` and ``resources.lib.aom.*`` only.
"""

import xbmc


class KodiLogger:
    """Callable ``(message, level)`` log sink."""

    def __init__(self, debug_escalation=False):
        # Refreshed by the runtime's SettingsChanged handler; plain attribute
        # write, single-threaded consumer (the dispatcher thread) + Kodi's
        # callback thread — a stale read costs one log line's level, nothing
        # else, so no locking.
        self.debug_escalation = debug_escalation

    def __call__(self, message, level=xbmc.LOGDEBUG):
        # LOGDEBUG escalates to LOGINFO when the addon debug toggle is on
        # (so users can capture addon debug lines without Kodi-wide debug).
        # Messages already prefixed 'AOM_' or '[AOM]' are not double-tagged.
        effective_level = (
            xbmc.LOGINFO
            if (level == xbmc.LOGDEBUG and self.debug_escalation)
            else level)
        use_prefix = (
            '' if message.startswith('[AOM]') or message.startswith('AOM_')
            else '[AOM]')
        xbmc.log(f"{use_prefix} {message}".strip(), effective_level)

    def debug(self, message):
        self(message, xbmc.LOGDEBUG)

    def warning(self, message):
        self(message, xbmc.LOGWARNING)

    def error(self, message):
        self(message, xbmc.LOGERROR)
