"""OffsetTable: the sparse-store adapter the pipeline speaks to.

Wraps the pure store and the injected settings reads. Keys are composed at
call time from the profile's verbatim facts plus the live granularity
toggles, never captured and never conditional on lookup history. Lookup
routes through ``resolve.resolve``, writes through ``resolve.write_key``,
the only sanctioned write-key derivation. The store-entry dict shape stays
inside the store package: consumers read values via ``Resolution.ms`` and
``stored_ms_at``.
"""

from resources.lib.aome.store import keys as store_keys
from resources.lib.aome.store import resolve as store_resolve


class OffsetTable:
    """Adapter over the OffsetStore keyed from profiles + the live toggle."""

    def __init__(self, store, settings):
        self._store = store
        self._settings = settings

    @property
    def read_only(self):
        """True when the store refuses all writes (newer-schema file).

        The watcher checks this so a permanently unwritable store stops the
        learn loop rather than re-failing the same adjustment every cycle.
        """
        return self._store.read_only

    def resolve(self, profile):
        """Look up the entry for the profile: a ``resolve.Resolution``."""
        return store_resolve.resolve(
            self._store, profile.hdr_type, profile.video_fps,
            profile.audio_format, profile.audio_channels,
            per_fps=self._settings.per_fps_offsets_enabled(),
            distinct_spatial=self._settings.distinct_spatial_enabled(),
            distinct_channels=self._settings.distinct_channels_enabled(),
            device=profile.audio_device,
            distinct_devices=self._settings.distinct_devices_enabled())

    def consume_reset(self, key):
        """Discard a pending reset marker (applier acted on it)."""
        return self._store.consume_reset(key)

    def write_key(self, profile):
        """The write key for the profile now, or None if not composable
        (unparseable fps under per-fps; callers gate on completeness first)."""
        try:
            return store_resolve.write_key(
                profile.hdr_type, profile.video_fps, profile.audio_format,
                profile.audio_channels,
                per_fps=self._settings.per_fps_offsets_enabled(),
                distinct_spatial=self._settings.distinct_spatial_enabled(),
                distinct_channels=self._settings.distinct_channels_enabled(),
                device=profile.audio_device,
                distinct_devices=self._settings.distinct_devices_enabled())
        except ValueError:
            return None

    def device_label(self, raw_device):
        """The toast's display label for a live device reading, or None.

        The service side's reach into the shared device label rule
        (``keys.device_label_for``), fed the store's OWN entries, which is
        the same input the management view feeds it, so a toast and a row
        can never name one device two ways. Narrowed to the toast's width,
        the one divergence the rule sanctions.

        Reads the store rather than a Kodi setting, so it costs no round
        trip; callers still gate it on the distinct-devices toggle, since
        with the toggle off no surface names a device at all.
        """
        return store_keys.device_label_for(raw_device, self._store.entries())

    def get_at(self, key):
        """The entry stored at an exact key (or None) — no fallback chain."""
        return self._store.get(key)

    def stored_ms_at(self, key):
        """The ms stored at an exact key, or None (keeps the entry dict
        shape inside the store package)."""
        entry = self._store.get(key)
        if entry is None:
            return None
        return entry['delay_ms']

    def store(self, profile, ms):
        """Store a user adjustment; returns the key written, or None.

        The exact reported rate and the audio device's friendly name ride
        along as entry metadata for the management view. Both are already in
        the facts the key came from, so they cost nothing here; the device
        name is absent on Kodi 20, where the view falls back to the key's id
        segment.
        """
        key = self.write_key(profile)
        if key is None:
            return None
        if not self._store.set(key, ms, video_fps=profile.video_fps,
                               device_name=profile.device_name()):
            return None
        return key
