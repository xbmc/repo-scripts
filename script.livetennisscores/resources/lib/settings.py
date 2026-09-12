"""Typed, total reads of the add-on's settings.

Every getter has a fallback. ``getSettingBool``/``getSettingInt``/
``getSettingString`` raise ``TypeError`` ("Invalid setting type") when the id
is absent or is of another type -- they do not return a falsy default -- which
would otherwise reach the Kodi log as a traceback from the service thread. Each
id read here is declared in ``resources/settings.xml``, so the fallbacks are a
safety net for an upgrade that adds a setting, not the normal path.

Nothing in this module logs the API key.
"""

import os

import xbmc
import xbmcaddon
import xbmcvfs

from . import cadence

LOG_PREFIX = "[script.livetennisscores] "


def log(message, level=xbmc.LOGDEBUG):
    """Write one line to the Kodi log, prefixed with the add-on id.

    Debug level by design: the Kodi add-on rules require add-ons to
    "use the debug logging level only" (https://kodi.wiki/view/Add-on_rules),
    and LOGDEBUG is also ``xbmc.log``'s own default. Genuine failures go
    through :func:`log_error`.
    """
    xbmc.log(f"{LOG_PREFIX}{message}", level=level)


def log_error(message):
    """Report a real failure -- a rejected key, an unusable response."""
    log(message, level=xbmc.LOGERROR)


class Settings:
    """Reads add-on settings afresh, so changes take effect without a restart.

    A new ``xbmcaddon.Addon`` is constructed per read on purpose: a long-lived
    instance can serve stale values after the user edits the settings dialog.
    """

    def _addon(self):
        return xbmcaddon.Addon()

    def _string(self, setting_id, default=""):
        try:
            value = self._addon().getSettingString(setting_id)
        except Exception:  # noqa: BLE001 - a missing id must not reach the log
            return default
        return value if isinstance(value, str) else default

    def _bool(self, setting_id, default=False):
        try:
            return bool(self._addon().getSettingBool(setting_id))
        except Exception:  # noqa: BLE001
            return default

    def _int(self, setting_id, default=0):
        try:
            return int(self._addon().getSettingInt(setting_id))
        except Exception:  # noqa: BLE001
            return default

    # -- the key ----------------------------------------------------------
    @property
    def api_key(self):
        """The user's API key, whitespace trimmed. Never logged."""
        return self._string("api_key").strip()

    @property
    def has_api_key(self):
        return bool(self.api_key)

    # -- cadence ----------------------------------------------------------
    @property
    def poll_minutes(self):
        """The cadence, clamped to what the free-tier quota can sustain."""
        return cadence.clamp_poll_minutes(
            self._int("poll_minutes", cadence.DEFAULT_POLL_MINUTES))

    @property
    def poll_seconds(self):
        return self.poll_minutes * cadence.SECONDS_PER_MINUTE

    # -- which changes interrupt the viewer -------------------------------
    @property
    def notify_match_live(self):
        return self._bool("notify_match_live", True)

    @property
    def notify_set_done(self):
        return self._bool("notify_set_done", True)

    @property
    def notify_match_done(self):
        return self._bool("notify_match_done", True)

    @property
    def notify_break_point(self):
        """Opt-in: off unless the user asks for break-point alerts."""
        return self._bool("notify_break_point", False)

    @property
    def display_seconds(self):
        seconds = self._int("display_seconds", 6)
        return min(30, max(2, seconds))

    def localized(self, string_id, fallback=""):
        """A translated string, falling back rather than raising."""
        try:
            value = self._addon().getLocalizedString(string_id)
        except Exception:  # noqa: BLE001
            return fallback
        return value or fallback

    def icon_path(self):
        """Absolute path to the add-on icon, used as the notification image."""
        try:
            base = xbmcvfs.translatePath(self._addon().getAddonInfo("path"))
            return os.path.join(base, "resources", "icon.png")
        except Exception:  # noqa: BLE001
            return ""
