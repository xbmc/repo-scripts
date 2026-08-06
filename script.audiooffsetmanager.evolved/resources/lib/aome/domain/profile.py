"""Immutable stream profile: the offset-relevant facts, exactly as reported.

Most axes are stream facts; ``audio_device`` is the one config fact (Kodi's
audio output device setting verbatim), because where the audio lands changes
the lipsync as much as what is in the bitstream. It is also the one axis
with two distinct absences, which ``policies.is_complete`` separates (see
the field comment).

``passthrough`` is neither: it is the ``Player.Passthrough`` reading the
gather was taken under, which is also the reading that chose which of Kodi's
two device settings was read. It joins no store key and no identity, and its
false doubles as "not knowable yet", which is Kodi's own default routing.

No store key is derived here: keys are composed at lookup/write time by
``aome.store``, which consults the granularity toggles, and display
formatting lives in ``aome.store.keys``. The only import is the domain's own
``formats``, which ``device_id`` shares with the key codec so the two cannot
spell a device differently.

``__repr__`` is overridden to withhold the device's friendly half, since
whole profiles are logged.
"""

from dataclasses import dataclass

from resources.lib.aome.domain.formats import (DEVICE_ALL, normalize_device,
                                               split_device)


@dataclass(frozen=True, repr=False)
class StreamProfile:
    """Immutable stream characteristics, exactly as detected."""

    hdr_type: str        # verbatim segment; 'sdr' default applied by detector
    audio_format: str    # verbatim segment, or 'unknown' when unreported
    video_fps: object    # float | None — the exact reported rate
    player_id: int
    audio_channels: object
    # str | None: Kodi's audio device setting verbatim
    # ('DRIVER:name|Friendly', or 'DRIVER:name' on Kodi 20). Two distinct
    # absences, and the difference decides completeness: '' means the axis
    # was deliberately not read (the toggle is off, so no key consults it),
    # while None means the read failed. policies.is_complete treats None as
    # incomplete so the detector keeps probing instead of re-keying the
    # session onto the all-devices bucket.
    audio_device: object = ''
    passthrough: bool = False

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
        None when unusable ('unknown', 0, bool), mirroring the store's
        ``channel_segment`` rule."""
        if isinstance(self.audio_channels, bool):
            return None
        try:
            # OverflowError: int(float('inf')) is junk like any other.
            count = int(self.audio_channels)
        except (TypeError, ValueError, OverflowError):
            return None
        if count <= 0:
            return None
        return count

    def device_id(self):
        """The device key axis: the canonical segment for this reading.

        ``formats.normalize_device`` verbatim, the same function
        ``keys.device_segment`` composes the key from, so two readings that
        compose one store key can never read as two streams. Case,
        surrounding whitespace and a friendly-name-only change all fold away
        exactly as they do in the key, and every absent reading (unread,
        unreadable, or empty) answers 'all'.
        """
        return normalize_device(self.audio_device)

    def device_name(self):
        """The friendly half, for display metadata, or None.

        None on Kodi 20 (which writes no friendly half) and for a blank
        one, so the store simply omits the metadata and display falls back
        to the id segment.
        """
        return split_device(self.audio_device)[1]

    def identity(self):
        """The raw fixed-shape identity tuple; incidental fields excluded.

        Not the runtime comparison: every offset-path caller uses
        ``policies.stream_identity``, which folds each axis in or out per the
        live granularity toggles.
        """
        return (self.hdr_type, self.fps_int(), self.audio_format)

    def __repr__(self):
        """Dataclass-shaped repr with the device's friendly half withheld.

        Whole profiles are interpolated into log lines and a Bluetooth
        endpoint's friendly name routinely carries a person's name, while
        the support-log export redacts paths, not names. Only the id half is
        rendered, under the field name ``device_id`` so no reader mistakes
        it for the raw setting string. Replacing ``__repr__`` rather than
        adding ``__str__`` keeps both ``{profile}`` and ``{profile!r}`` safe.
        """
        return ("StreamProfile(hdr_type={0!r}, audio_format={1!r}, "
                "video_fps={2!r}, player_id={3!r}, audio_channels={4!r}, "
                "device_id={5!r})").format(
                    self.hdr_type, self.audio_format, self.video_fps,
                    self.player_id, self.audio_channels, self.device_id())

    def describe(self):
        """Compact greppable form for logs: ``hdr|fps|audio|ch|dev``.

        Unusable axes read '?', so a missing fact is visible rather than
        silently shaped like a real value. The device axis carries the
        canonical key segment (the key material, and the half worth
        grepping); '?' covers all three device absences alike, and the
        detector's probe line is where the raw reading tells them apart.
        """
        fps = self.fps_int()
        channels = self.channels_int()
        device = self.device_id()
        return "{0}|{1}|{2}|{3}|{4}".format(
            self.hdr_type, '?' if fps is None else fps, self.audio_format,
            '?' if channels is None else channels,
            '?' if device == DEVICE_ALL else device)
