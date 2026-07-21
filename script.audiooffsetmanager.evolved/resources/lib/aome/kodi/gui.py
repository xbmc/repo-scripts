"""Kodi GUI surface: the only place xbmcgui notifications and dialogs are raised.

Single-shot, matching the gateway convention: each method performs exactly
one Kodi GUI call and returns, guarded so a transient failure degrades to a
log line rather than unwinding the caller. String resolution goes through
``getLocalizedString``; the app-layer Notifier owns message assembly and
hands this surface a resolved string.

An ``aome.kodi`` adapter: the only aome layer permitted to import
``xbmcgui``/``xbmcaddon``.
"""

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib.aome.kodi.settings import ADDON_ID


class Gui:
    """Single-shot wrapper over Kodi's notification dialog and string table."""

    def __init__(self, *, log):
        """``log`` is a required ``(message, level)`` sink (production
        injects the ``KodiLogger`` callable), so one logger instance serves
        the whole process."""
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
            self._log(f"AOMe_Gui: Error reading localized string {string_id}: "
                      f"{str(e)}", xbmc.LOGERROR)
            return ''

    def select(self, heading, options):
        """Show a selection list; return the chosen index, -1 on cancel/error.

        Each option is a plain string (single-line row) or a
        ``(label, detail)`` tuple; any tuple upgrades the whole dialog to
        Kodi's two-line detail rows (``useDetails``), with strings rendering
        as detail-less items. -1 (Kodi's cancel value) doubles as the error
        fallback, so a transient failure reads as "user backed out".
        """
        try:
            if any(isinstance(option, tuple) for option in options):
                items = [
                    xbmcgui.ListItem(option[0], option[1], offscreen=True)
                    if isinstance(option, tuple)
                    else xbmcgui.ListItem(option, offscreen=True)
                    for option in options
                ]
                return xbmcgui.Dialog().select(heading, items,
                                               useDetails=True)
            return xbmcgui.Dialog().select(heading, options)
        except Exception as e:
            self._log(f"AOMe_Gui: Error showing select dialog: {str(e)}",
                      xbmc.LOGERROR)
            return -1

    def yesno(self, heading, message):
        """Show a yes/no confirmation; return True only on an explicit yes.

        The error fallback is False — a transient GUI failure must never
        read as consent (the view uses this to confirm delete/clear).
        """
        try:
            return bool(xbmcgui.Dialog().yesno(heading, message))
        except Exception as e:
            self._log(f"AOMe_Gui: Error showing yesno dialog: {str(e)}",
                      xbmc.LOGERROR)
            return False

    def ok(self, heading, message):
        """Show a modal OK dialog; True when it actually rendered.

        The bool matters to callers that gate a side effect on the user
        having seen the dialog (the coexistence once-flag): a swallowed
        failure returns False so the caller can retry rather than mark an
        unshown warning as shown.
        """
        try:
            xbmcgui.Dialog().ok(heading, message)
            return True
        except Exception as e:
            self._log(f"AOMe_Gui: Error showing ok dialog: {str(e)}",
                      xbmc.LOGERROR)
            return False

    def browse_folder(self, heading):
        """Show a writable-folder picker; return the path, '' on cancel/error.

        The export destination surface: type 3 is Kodi's
        ShowAndGetWriteableDirectory over the 'files' shares, so local
        drives, network shares, and USB mounts all offer themselves. Kodi
        answers a cancel with the empty default, so '' doubles as the error
        fallback, like select().
        """
        try:
            return xbmcgui.Dialog().browseSingle(3, heading, 'files')
        except Exception as e:
            self._log(f"AOMe_Gui: Error showing folder browser: {str(e)}",
                      xbmc.LOGERROR)
            return ''

    def browse_file(self, heading, mask):
        """Show a file picker filtered to ``mask``; '' on cancel/error.

        The import source surface: type 1 is ShowAndGetFile, ``mask`` an
        extension filter like '.json'. Cancel/error semantics as
        browse_folder.
        """
        try:
            return xbmcgui.Dialog().browseSingle(1, heading, 'files',
                                                 mask)
        except Exception as e:
            self._log(f"AOMe_Gui: Error showing file browser: {str(e)}",
                      xbmc.LOGERROR)
            return ''

    def notification(self, message, duration_ms, title=None, icon=None):
        """Raise one Kodi toast for ``message`` lasting ``duration_ms``.

        ``title`` and ``icon`` default to the addon's name and icon; callers
        may override them (e.g. ``xbmcgui.NOTIFICATION_ERROR`` toasts).
        Exception guard: a GUI-layer failure logs LOGERROR through the sink
        and never unwinds the caller.
        """
        try:
            xbmcgui.Dialog().notification(
                title if title is not None else self._name,
                message,
                icon if icon is not None else self._icon,
                duration_ms)
        except Exception as e:
            self._log(f"AOMe_Gui: Error raising notification: {str(e)}",
                      xbmc.LOGERROR)
