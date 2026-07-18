"""Kodi GUI toast surface — the only place xbmcgui notifications are raised.

Single-shot BY DESIGN, matching the gateway convention: each method performs
exactly one Kodi GUI call and returns, guarded so a transient GUI-layer
failure degrades to a log line rather than unwinding the caller mid-handler.

String resolution goes through ``getLocalizedString``: the app-layer
Notifier owns message assembly and hands this surface a fully-resolved
string.

This is an ``aom.kodi`` adapter: the only aom layer permitted to import
``xbmcgui``/``xbmcaddon``.
"""

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib.aom.kodi.settings import ADDON_ID


class Gui:
    """Single-shot wrapper over Kodi's notification dialog and string table."""

    def __init__(self, *, log):
        """``log`` is a REQUIRED ``(message, level)`` sink — production
        injects the ``aom.kodi.log.KodiLogger`` callable, matching the
        gateway convention, so one logger instance (and its cached debug
        escalation) serves the whole process.
        """
        addon = xbmcaddon.Addon(ADDON_ID)
        self._addon = addon
        self._name = addon.getAddonInfo('name')
        self._icon = addon.getAddonInfo('icon')
        self._log = log

    def localized(self, string_id):
        """Return the localized string for ``string_id`` ('' on failure).

        The exception guard mirrors the gateway's reads: a transient string
        lookup failure yields the empty sentinel instead of unwinding the
        caller's message assembly.
        """
        try:
            return self._addon.getLocalizedString(string_id)
        except Exception as e:
            self._log(f"AOM_Gui: Error reading localized string {string_id}: "
                      f"{str(e)}", xbmc.LOGERROR)
            return ''

    def notification(self, message, duration_ms, title=None):
        """Raise one Kodi toast for ``message`` lasting ``duration_ms``.

        ``title`` defaults to the addon's name; the icon is always the
        addon's own. Exception guard: a GUI-layer failure logs LOGERROR
        through the sink and never unwinds the caller.
        """
        try:
            xbmcgui.Dialog().notification(
                title if title is not None else self._name,
                message,
                self._icon,
                duration_ms)
        except Exception as e:
            self._log(f"AOM_Gui: Error raising notification: {str(e)}",
                      xbmc.LOGERROR)
