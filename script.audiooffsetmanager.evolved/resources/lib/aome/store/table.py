"""OffsetTable: the sparse-store adapter the pipeline speaks to.

Wraps the pure store and the injected settings reads. Keys are composed at
call time from the profile's verbatim facts plus the live granularity
toggles (``per_fps_offsets``, ``distinct_spatial_formats``,
``distinct_channel_counts``), never captured and never conditional on
lookup history. Lookup routes through ``resolve.resolve`` (one candidate key per
mode); writes route through ``resolve.write_key``, the only sanctioned
write-key derivation. The store-entry dict shape stays inside the store
package: consumers read values via ``Resolution.ms`` and ``stored_ms_at``.
"""

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
            distinct_channels=self._settings.distinct_channels_enabled())

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
                distinct_channels=self._settings.distinct_channels_enabled())
        except ValueError:
            return None

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

        The exact reported rate rides along as entry metadata for the
        management view.
        """
        key = self.write_key(profile)
        if key is None:
            return None
        if not self._store.set(key, ms, video_fps=profile.video_fps):
            return None
        return key
