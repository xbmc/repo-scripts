"""Kodi settings adapter: typed reads/writes plus intent-level accessors.

A plain, injected class — no singleton: the runtime constructs exactly one
``Settings`` and injects it into every component that needs settings
(required constructor deps are the house rule, same as ``KodiGateway``).

Why one instance is enough — and not a correctness barrier: Kodi's
``xbmcaddon.Addon(ADDON_ID).getSettings()`` returns a LIVE proxy onto the
in-process settings store, not a frozen snapshot. Every read sees current
values and every write is visible everywhere at once, so the store cannot
drift out of sync with itself. Holding one proxy per process is a tidiness
convenience, not the thing that makes reads/writes consistent.

LIFETIME RULE (field-verified on Kodi 21.2/Windows): the proxy is
live ONLY while the ``xbmcaddon.Addon`` it came from stays alive. A
``Settings`` object whose parent ``Addon`` was a garbage-collected temporary
degrades into a detached copy — writes report success but never persist to
the real store or ``settings.xml``, and outside changes (settings dialog
edits) never arrive. ``__init__`` therefore keeps the ``Addon`` on ``self``;
never rewrite it as ``xbmcaddon.Addon(...).getSettings()``.

The read-before-write skip in the ``store_*_if_changed`` helpers is
load-bearing: it keeps the settings-dialog clobber surface minimal (no write
means nothing for a dialog save-on-close to fight over) per the doctrine.

This layer may import ``xbmc*``/``xbmcaddon`` and ``resources.lib.aom.*``
only (``tests/contract/test_architecture.py`` enforces the layering).
"""

import xbmc
import xbmcaddon

ADDON_ID = 'script.audiooffsetmanager'


class Settings:
    """Typed access to the addon settings store over Kodi's live proxy."""

    def __init__(self, *, log):
        """``log`` is a REQUIRED ``(message, level)`` sink (same convention as
        ``KodiGateway``)."""
        self._log = log
        # The Addon must outlive the Settings proxy (see LIFETIME RULE above).
        self._addon = xbmcaddon.Addon(ADDON_ID)
        self._settings = self._addon.getSettings()

    # --- typed primitives ---------------------------------------------------

    def get_bool(self, setting_id, default=False):
        """Read a boolean setting; on ANY error, log and return ``default``."""
        try:
            return self._settings.getBool(setting_id)
        except Exception:
            self._log(
                f"AOM_Settings: Error getting boolean setting '{setting_id}'. "
                f"Using default: {default}", xbmc.LOGWARNING)
            return default

    def get_int(self, setting_id, default=0):
        """Read an integer setting; on ANY error, log and return ``default``."""
        try:
            return self._settings.getInt(setting_id)
        except Exception:
            self._log(
                f"AOM_Settings: Error getting integer setting '{setting_id}'. "
                f"Using default: {default}", xbmc.LOGWARNING)
            return default

    def store_boolean_if_changed(self, setting_id, value):
        """Write a boolean only if it differs from the stored value.

        Returns True when the store succeeds or is skipped (already equal);
        False when the underlying write raises. NOTE the pre-read runs
        through get_bool, which swallows read errors into the default — so a
        failed read of a setting whose target value equals that default
        skips the write and reports success (accepted: reads of valid ids
        do not fail in practice).
        """
        if self.get_bool(setting_id) == value:
            return True
        return self._store(self._settings.setBool, setting_id, value, "boolean")

    def store_integer_if_changed(self, setting_id, value):
        """Write an integer only if it differs from the stored value.

        Returns True when the store succeeds or is skipped (already equal);
        False when the underlying write raises. See store_boolean_if_changed
        for the pre-read-vs-default caveat.
        """
        if self.get_int(setting_id) == value:
            return True
        return self._store(self._settings.setInt, setting_id, value, "integer")

    def _store(self, operation, setting_id, value, value_type):
        """Log the store at LOGDEBUG and write; on error log LOGWARNING."""
        try:
            self._log(
                f"AOM_Settings: Storing {value_type} setting {setting_id}: "
                f"{value}", xbmc.LOGDEBUG)
            operation(setting_id, value)
            return True
        except Exception:
            self._log(
                f"AOM_Settings: Error storing {value_type} setting "
                f"'{setting_id}'.", xbmc.LOGWARNING)
            return False

    # --- intent-level reads -------------------------------------------------

    def is_hdr_enabled(self, hdr_type):
        return self.get_bool(f"enable_{hdr_type}")

    def fps_override_enabled(self, hdr_type):
        return self.get_bool(f"enable_fps_{hdr_type}")

    def active_monitoring_enabled(self):
        return self.get_bool('enable_active_monitoring')

    def seek_back_config(self, reason):
        """Return ``(enabled, seconds)`` for a seek-back reason; seconds >= 0."""
        return (self.get_bool(f"enable_seek_back_{reason}"),
                max(self.get_int(f"seek_back_{reason}_seconds"), 0))

    def notifications_enabled(self):
        return self.get_bool('enable_notifications')

    def notification_duration_ms(self):
        return self.get_int('notification_seconds') * 1000

    def debug_logging_enabled(self):
        return self.get_bool('enable_debug_logging')

    def is_new_install(self):
        return self.get_bool('new_install')


class OffsetTable:
    """Per-profile offset storage. tools/generate_settings.py guarantees every
    <hdr>_<fps>_<audio> setting id exists, so get() always answers an int
    ('no stored value' is not a state). The setting key is derived from the
    profile AT CALL TIME (settings doctrine: never a captured key)."""

    def __init__(self, settings):
        self._settings = settings

    def get(self, profile):
        return self._settings.get_int(profile.setting_id())

    def store(self, profile, ms):
        return self._settings.store_integer_if_changed(profile.setting_id(), ms)
