"""Immutable stream profile: the detection facts, exactly as Kodi reported.

The axes carry what Kodi reported, normalized by ``aome.store.keys``
segment rules. No store key is derived here; it is composed at lookup/write
time by ``aome.store`` (which consults the per_fps toggle then). Display
formatting also lives in ``aome.store.keys``, keeping this module a pure
data class that imports nothing.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class StreamProfile:
    """Immutable stream characteristics, exactly as detected."""

    hdr_type: str        # verbatim segment; 'sdr' default applied by detector
    audio_format: str    # verbatim segment, or 'unknown' when unreported
    video_fps: object    # float | None — the exact reported rate
    player_id: int
    audio_channels: object

    def fps_int(self):
        """The fps key axis: the reported rate truncated to an int, or None.

        Truncation (not rounding) keeps NTSC fractional rates on their own
        keys: 23.976 -> 23 stays distinct from 24.0 -> 24.
        """
        if self.video_fps is None:
            return None
        return int(self.video_fps)

    def channels_int(self):
        """The channel key axis: the reported count as a positive int, or
        None when unusable ('unknown', 0, bool) — mirroring the store's
        channel_segment rule, where an unusable count means the stream has
        no channel axis."""
        if isinstance(self.audio_channels, bool):
            return None
        try:
            # OverflowError: int(float('inf')) — junk like any other.
            count = int(self.audio_channels)
        except (TypeError, ValueError, OverflowError):
            return None
        if count <= 0:
            return None
        return count

    def identity(self):
        """The raw fixed-shape identity tuple; incidental fields excluded.

        Not the runtime comparison: every offset-path caller uses
        ``policies.stream_identity``, which folds each axis in or out per
        the live granularity toggles (fps, spatial, channels). This raw
        form ignores the toggles and the channel axis by construction.
        """
        return (self.hdr_type, self.fps_int(), self.audio_format)

    def describe(self):
        """Compact greppable form for logs: ``hdr|fps|audio|ch``.

        Unusable axes read '?', so a channel-less report is visible in the
        log rather than silently shaped like a real count.
        """
        fps = self.fps_int()
        channels = self.channels_int()
        return "{0}|{1}|{2}|{3}".format(
            self.hdr_type, '?' if fps is None else fps, self.audio_format,
            '?' if channels is None else channels)
