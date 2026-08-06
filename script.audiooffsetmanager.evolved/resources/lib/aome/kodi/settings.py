"""Kodi settings adapter: typed reads/writes plus intent-level accessors.

A plain injected class, no singleton: the runtime constructs exactly one
``Settings`` and injects it everywhere. One instance is enough because
``xbmcaddon.Addon(ADDON_ID).getSettings()`` returns a live proxy onto the
in-process settings store rather than a snapshot, so every read sees current
values and every write is visible everywhere at once.

LIFETIME RULE: that proxy is live only while the ``xbmcaddon.Addon`` it came
from stays alive. A ``Settings`` whose parent ``Addon`` was a
garbage-collected temporary degrades into a detached copy that reports write
success but never persists and never sees outside changes. ``__init__``
therefore keeps the ``Addon`` on ``self``; never rewrite it as
``xbmcaddon.Addon(...).getSettings()``.

The ``store_*_if_changed`` helpers skip a write that would not change the
stored value, so a dialog's save-on-close has nothing to fight over. Only
behavior settings live here; offsets live in the sparse store.

This layer may import ``xbmc*``/``xbmcaddon`` and ``resources.lib.aome.*``
only.
"""

import xbmc
import xbmcaddon
import xbmcvfs

from resources.lib.aome.app.store_mutations import IMPORT_SUFFIX

ADDON_ID = 'script.audiooffsetmanager.evolved'

# The sparse offset store's on-disk home. Lives beside ADDON_ID because BOTH
# processes need it: the service runtime builds the OffsetStore on it, the
# script router points the management view's read-only reader at it.
STORE_PATH = f'special://profile/addon_data/{ADDON_ID}/offsets.json'


def import_staging_path():
    """The import channel's staged-backup path, translated and ready.

    Derived here once because both processes must compute the identical path:
    the script stages, the service reads.
    """
    return xbmcvfs.translatePath(STORE_PATH) + IMPORT_SUFFIX


class Settings:
    """Typed access to the addon settings store over Kodi's live proxy."""

    def __init__(self, *, log):
        """``log`` is a REQUIRED ``(message, level)`` sink, the same
        convention as ``KodiGateway``."""
        self._log = log
        # The Addon must outlive the Settings proxy (see LIFETIME RULE).
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

        The empty-list fallback reads as "no options selected", which is
        every list setting's do-nothing state.
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

        Returns True when the store succeeds or is skipped as already equal,
        False when the underlying write raises. Note that the pre-read runs
        through ``get_bool``, which swallows read errors into the default, so
        a failed read of a setting whose target value equals that default
        skips the write and reports success.
        """
        if self.get_bool(setting_id) == value:
            return True
        return self._store(self._settings.setBool, setting_id, value, "boolean")

    def store_integer_if_changed(self, setting_id, value):
        """Write an integer only if it differs from the stored value.

        Same contract and pre-read caveat as ``store_boolean_if_changed``.
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

    # --- intent-level reads -------------------------------------------------
    # Behavior settings only; offsets live in the sparse store. Each default
    # below is the shipped behavior, so an unreadable setting can never
    # silently change what the addon does.

    def per_fps_offsets_enabled(self):
        """The fps-granularity knob: off means the all-rates key world."""
        return self.get_bool('per_fps_offsets')

    def distinct_spatial_enabled(self):
        """The audio-granularity knob: off means spatial variants share
        their base codec's key."""
        return self.get_bool('distinct_spatial_formats', False)

    def distinct_channels_enabled(self):
        """The channel-granularity knob: off means the all-channels key
        world."""
        return self.get_bool('distinct_channel_counts', False)

    def distinct_devices_enabled(self):
        """The device-granularity knob: off means the all-devices key world,
        with Kodi's audio output device part of no key."""
        return self.get_bool('distinct_output_devices', False)

    def apply_enabled(self):
        """The apply toggle: gates the applier only, never the watcher.

        Learn and apply are orthogonal, and this is the apply half.
        """
        return self.get_bool('apply_offsets', True)

    def remember_adjustments_enabled(self):
        """The learn loop's opt-out."""
        return self.get_bool('remember_adjustments', True)

    def seek_back_config(self, reason):
        """Return ``(enabled, seconds)`` for a seek-back reason; seconds >= 0.

        Enabled is membership in the ``seek_back_events`` multiselect, whose
        option values are the SeekScheduler REASONS verbatim (a contract test
        pins that); the amount is the one shared slider. An unreadable read
        yields 0, which the scheduler treats as disabled.
        """
        return (reason in self.get_string_list('seek_back_events'),
                max(self.get_int('seek_back_seconds'), 0))

    def notify_apply_enabled(self):
        """The 'offset applied' toast gate; each toast kind has its own."""
        return self.get_bool('notify_apply', True)

    def notify_learn_enabled(self):
        """The 'offset saved' toast gate."""
        return self.get_bool('notify_learn', True)

    def notification_duration_ms(self):
        return self.get_int('notification_seconds', 5) * 1000

    def debug_logging_enabled(self):
        return self.get_bool('enable_debug_logging')

    def coexistence_warned(self):
        """The once-flag for the warning shown when the original Audio Offset
        Manager addon is installed alongside this one.

        Behavior state rather than offset data: a hidden bool in
        settings.xml, written through ``store_boolean_if_changed`` after the
        warning actually shows."""
        return self.get_bool('coexistence_warned')
