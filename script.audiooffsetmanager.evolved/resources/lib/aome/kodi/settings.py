"""Kodi settings adapter: typed reads/writes plus intent-level accessors.

A plain, injected class, no singleton: the runtime constructs exactly one
``Settings`` and injects it everywhere. One instance is enough because
Kodi's ``xbmcaddon.Addon(ADDON_ID).getSettings()`` returns a live proxy onto
the in-process settings store, not a frozen snapshot: every read sees
current values and every write is visible everywhere at once.

Lifetime rule: the proxy is live only while the ``xbmcaddon.Addon`` it came
from stays alive. A ``Settings`` whose parent ``Addon`` was a
garbage-collected temporary degrades into a detached copy that reports
write success but never persists, and never sees outside changes.
``__init__`` therefore keeps the ``Addon`` on ``self``; never rewrite it as
``xbmcaddon.Addon(...).getSettings()``.

The ``store_*_if_changed`` helpers skip a write that would not change the
stored value, so a dialog's save-on-close has nothing to fight over. Only
behavior settings live here (offsets live in the sparse store); the one
runtime caller is the coexistence once-flag.

This layer may import ``xbmc*``/``xbmcaddon`` and ``resources.lib.aome.*``
only.
"""

import xbmc
import xbmcaddon
import xbmcvfs

from resources.lib.aome.app.store_mutations import IMPORT_SUFFIX

ADDON_ID = 'script.audiooffsetmanager.evolved'

# The sparse offset store's on-disk home. Lives beside ADDON_ID (addon
# identity constants) because BOTH processes need it: the service runtime
# builds the OffsetStore on it, the script router points the management
# view's read-only reader at it.
STORE_PATH = f'special://profile/addon_data/{ADDON_ID}/offsets.json'


def import_staging_path():
    """The import channel's staged-backup path, translated and ready.

    Derived here once because both processes must compute the identical path
    (the script stages, the service reads): the channel's suffix on the
    translated store path.
    """
    return xbmcvfs.translatePath(STORE_PATH) + IMPORT_SUFFIX


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
                f"AOMe_Settings: Error getting boolean setting '{setting_id}'. "
                f"Using default: {default}", xbmc.LOGWARNING)
            return default

    def get_int(self, setting_id, default=0):
        """Read an integer setting; on ANY error, log and return ``default``."""
        try:
            return self._settings.getInt(setting_id)
        except Exception:
            self._log(
                f"AOMe_Settings: Error getting integer setting '{setting_id}'. "
                f"Using default: {default}", xbmc.LOGWARNING)
            return default

    def get_string_list(self, setting_id):
        """Read a list-of-strings setting; on any error, log and return ``[]``.

        The empty-list fallback reads as "no options selected", every list
        setting's do-nothing state.
        """
        try:
            return list(self._settings.getStringList(setting_id))
        except Exception:
            self._log(
                f"AOMe_Settings: Error getting string list setting "
                f"'{setting_id}'. Using default: []", xbmc.LOGWARNING)
            return []

    def store_boolean_if_changed(self, setting_id, value):
        """Write a boolean only if it differs from the stored value.

        Returns True when the store succeeds or is skipped (already equal);
        False when the underlying write raises. NOTE the pre-read runs
        through get_bool, which swallows read errors into the default — so a
        failed read of a setting whose target value equals that default
        skips the write and reports success (reads
        of valid ids do not fail in practice).
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
                f"AOMe_Settings: Storing {value_type} setting {setting_id}: "
                f"{value}", xbmc.LOGDEBUG)
            operation(setting_id, value)
            return True
        except Exception:
            self._log(
                f"AOMe_Settings: Error storing {value_type} setting "
                f"'{setting_id}'.", xbmc.LOGWARNING)
            return False

    # --- intent-level reads (behavior settings only — offsets live in the
    # sparse store, never here) ------------------------------------------------

    def per_fps_offsets_enabled(self):
        """The ONE fps-granularity knob: OFF = the `all` key world."""
        return self.get_bool('per_fps_offsets')

    def distinct_spatial_enabled(self):
        """The ONE audio-granularity knob: OFF = spatial variants share
        their base codec's key. Defaults OFF like the other granularity
        toggles: collapsed is the shipped behavior, so an unreadable
        setting must not silently start keying variants apart."""
        return self.get_bool('distinct_spatial_formats', False)

    def distinct_channels_enabled(self):
        """The ONE channel-granularity knob: OFF = the all-channels key
        world. Defaults OFF like per_fps: collapsed is the shipped
        behavior, so an unreadable setting must not silently start keying
        by count."""
        return self.get_bool('distinct_channel_counts', False)

    def apply_enabled(self):
        """The apply toggle: gates the applier only, never the watcher.

        Learn and Apply are orthogonal; this is the apply half. Defaults on:
        applying is the product, so an unreadable setting must not silently
        disable it.
        """
        return self.get_bool('apply_offsets', True)

    def remember_adjustments_enabled(self):
        """The learn loop's opt-out. Defaults ON: learning is the product,
        so an unreadable setting must never silently disable it."""
        return self.get_bool('remember_adjustments', True)

    def seek_back_config(self, reason):
        """Return ``(enabled, seconds)`` for a seek-back reason; seconds >= 0.

        enabled = membership in the ``seek_back_events`` multiselect,
        whose option values are the SeekScheduler REASONS verbatim (the
        settings contract test pins that); the amount is the one shared
        slider. An unreadable read yields 0, which the scheduler treats
        as disabled (fail quiet).
        """
        return (reason in self.get_string_list('seek_back_events'),
                max(self.get_int('seek_back_seconds'), 0))

    def notify_apply_enabled(self):
        """The 'offset applied' toast gate (each toast kind has its own
        toggle). Defaults ON — the toasts are the learn loop's teaching
        surface, so an unreadable setting must never silently mute them."""
        return self.get_bool('notify_apply', True)

    def notify_learn_enabled(self):
        """The 'offset saved' toast gate (see notify_apply_enabled)."""
        return self.get_bool('notify_learn', True)

    def notification_duration_ms(self):
        return self.get_int('notification_seconds', 5) * 1000

    def debug_logging_enabled(self):
        return self.get_bool('enable_debug_logging')

    def coexistence_warned(self):
        """The once-flag for the warning shown when the original Audio
        Offset Manager addon is installed alongside this one.

        Behavior STATE, not offset data — a hidden level-4 bool in
        settings.xml, written through store_boolean_if_changed after the
        warning actually shows."""
        return self.get_bool('coexistence_warned')
