"""Format facts shared across layers.

The absence sentinel, the spatial-variant table, and the audio-device axis:
its passthrough condition, Kodi's two device setting ids, the rule choosing
between them, the string split, and the canonical key spelling.

Formats are accepted verbatim, so nothing here gates which are known;
display names live in ``aome.store.keys``.

The device axis lives in the domain layer because both the store and the
profile need it while the domain may not import the store, so the axis
cannot grow two spellings. Its Kodi-side derivation is in
docs/kodi-platform-notes.md.

Pure Python: no Kodi imports.
"""

# Sentinel for any undetected axis, and the absence key segment.
UNKNOWN = 'unknown'

# Strings meaning "Kodi reported nothing": one absence rule for every axis,
# reused by ``aome.store.keys`` so the vocabulary has a single definition.
ABSENT = ('', 'none', UNKNOWN)

# The store key's segment joiner. Defined here because the device rules both
# split on it and have to neutralise it; ``aome.store.keys.SEPARATOR`` is
# this same constant.
KEY_SEPARATOR = '|'

# The device axis's absence segment: every read that names no device keys
# the all-devices bucket, in lookup and write alike.
DEVICE_ALL = 'all'

# Is the PLAYER bitstreaming this stream? An in-process boolean condition,
# recomputed on every demux packet, so a mid-playback flip shows up within
# one packet.
#
# The implication runs ONE WAY: true means the sink opens the passthrough
# device, but false does NOT mean the sink format is PCM. Read it as "the
# player is bitstreaming", never as "the sink format is RAW".
#
# Two other sources look like they would answer this and do not; both were
# checked against Kodi source and rejected. Read
# docs/kodi-platform-notes.md before switching to either.
CONDITION_PASSTHROUGH = 'Player.Passthrough'

# Kodi's TWO configured audio output devices. Both are CORE settings, so
# they read through ``gateway.setting_value`` and never through
# ``Settings.GetSettings``, which would rewrite them (see that method).
SETTING_AUDIO_DEVICE = 'audiooutput.audiodevice'
SETTING_PASSTHROUGH_DEVICE = 'audiooutput.passthroughdevice'

# Spatial variant -> base codec, on normalized audio segments. Observed Kodi
# spellings only (StreamUtils::GetCodecName has exactly these variant
# cases), never speculative. Lossy DTS:X over DTS-HD HRA has no entry
# because FFmpeg detects the X syncword only inside the lossless XLL
# substream, so Kodi already reports such a stream as plain 'dtshd_hra'.
SPATIAL_BASE = {
    'truehd_atmos': 'truehd',
    'eac3_ddp_atmos': 'eac3',
    'dtshd_ma_x': 'dtshd_ma',
    'dtshd_ma_x_imax': 'dtshd_ma',
}


def spatial_base(segment):
    """The base codec a spatial variant collapses to; itself when not one."""
    return SPATIAL_BASE.get(segment, segment)


def device_setting_id(passthrough):
    """The setting naming the endpoint THIS stream actually lands on.

    Kodi keeps two output devices and obeys exactly one at a time, chosen per
    stream when the sink opens, so reading ``audiooutput.audiodevice``
    unconditionally would key a bitstreamed stream on a device it never
    touched.

    THE one place this mapping lives: the StreamDetector, the DeviceWatcher
    and the AdjustmentWatcher's pre-store re-check all call it, so none of
    them can poll one endpoint while keying, or vetoing against, another.

    ``passthrough`` is a reading of ``CONDITION_PASSTHROUGH``, whose false
    also covers "no player yet / could not read". That is the right default,
    since Kodi routes a decoded stream to the ordinary device, so an unknown
    answer names the setting that stream would use rather than stranding the
    read.

    KNOWN LIMITATION, accepted rather than engineered around: ActiveAE's
    AC3-transcode mode turns a PCM source RAW by itself, so Kodi opens the
    passthrough device while this function answers the ordinary one and the
    stream keys on the PCM device. Nothing Kodi exposes reports it. The
    config it needs, and why inferring it is not worth the round trips, are
    in docs/kodi-platform-notes.md.
    """
    return SETTING_PASSTHROUGH_DEVICE if passthrough else SETTING_AUDIO_DEVICE


def split_device(raw):
    """Split Kodi's audio device string into ``(device_id, friendly_name)``.

    Kodi 21+ stores ``audiooutput.audiodevice`` as ``DRIVER:name|Friendly``
    and splits it back on the LAST ``|`` when opening the sink, which this
    mirrors exactly. Kodi 20 writes no friendly half, so a string with no
    ``|`` yields ``(whole string, None)``, making the id half (and therefore
    the key) identical across a Kodi 20 -> 21 upgrade. ``raw`` may be None,
    which reads as the empty string.

    Load-bearing ordering: this runs BEFORE ``keys.normalize_segment``,
    which maps a stray ``|`` to ``_``. Normalizing first would erase the
    split point and fold the friendly half into the key.
    """
    text = '' if raw is None else str(raw)
    device_id, separator, name = text.rpartition(KEY_SEPARATOR)
    if not separator:
        return text, None
    # A blank friendly half is no name: it would render as an empty device
    # label and, stored as entry metadata, outlive the read.
    return device_id, (name if name.strip() else None)


def normalize_device(raw):
    """The device axis's canonical key segment, independent of the toggle.

    The id half (``split_device``), case-folded and trimmed, with any
    remaining ``|`` neutralised to ``_``. An absent reading becomes
    ``DEVICE_ALL``, so this never raises, and it is idempotent.

    THE one spelling of this axis: ``keys.device_segment`` composes the key
    from it and ``profile.device_id()`` returns it for stream identity, so
    two readings that compose the same key can never read as different
    streams. Being mode-independent is what lets ``keys.canonical_key``
    re-spell a stored segment without consulting the toggle; folding the
    axis away when the toggle is off belongs to ``device_segment``.
    """
    segment = split_device(raw)[0].strip().lower()
    # Absence is judged with the joiner removed, so a reading that is
    # nothing but joiners ('||') degrades like an empty one instead of
    # keying the '_' its substitution would leave behind.
    if segment.replace(KEY_SEPARATOR, '').strip() in ABSENT:
        return DEVICE_ALL
    return segment.replace(KEY_SEPARATOR, '_')
