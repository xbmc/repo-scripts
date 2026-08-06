"""Profile-key algebra for the sparse offset store.

Keys are derived from what Kodi reports, accepted verbatim: no whitelist, no
substring matching, and no alias table gating which codecs or HDR types are
known, so a string this code has never seen becomes a working key with no
code change. Normalization is minimal (case-fold, trim, and a defensive
``|`` substitution), plus an internal-whitespace strip and a few cross-build
aliases on the HDR axis. Aliases never grow speculatively: each exists
because one format was reported under two spellings by different Kodi
builds, where a fragmented key would strand a learned offset.

Key shape: ``<hdr>|<fps>|<audio>|<ch>|<dev>``, e.g.
``dolbyvision|23|truehd|all|all``. Schema-1 keys had three segments and
schema-2 keys four; ``canonical_key`` expands both with trailing ``all``
segments, which is the whole migration.

Absence ('', 'none', 'unknown') collapses to the UNKNOWN sentinel; every
other string passes through verbatim. ``hdr_segment`` maps a blank HDR to
'unknown' rather than 'sdr', because choosing 'sdr' for an absent flag is a
chain-of-evidence decision belonging to the detector. FPS truncates to an
integer so NTSC fractional rates stay distinct from their integer siblings
(23.976 -> 23 vs 24.0 -> 24). Each of the fps, audio, channel and device
axes has its own granularity mode, and every one of them lives in key
COMPOSITION only: ``canonical_key`` is mode-independent and never collapses
an axis. Channels and devices degrade an unusable value to 'all' rather than
raising, identically in lookup and write, because nothing upstream screens
either.

The device axis also owns the one display rule that is not a per-value
lookup: ``device_labels`` labels a whole SET of devices at once, since two
of them can report one friendly name and only the set knows that. Both
surfaces that name a device go through it with the same inputs (the
management view directly, the toast through ``device_label_for``), so one
device can never be named two ways; only the toast's width diverges.

Pure Python: stdlib only, no xbmc* imports.
"""

import math

from resources.lib.aome.domain import formats
from resources.lib.aome.domain.formats import (UNKNOWN, spatial_base,
                                               split_device)

# Segment joiner for the composite profile key. Defined in the domain layer,
# which needs the same character to split and neutralise device strings.
SEPARATOR = formats.KEY_SEPARATOR

# Strings meaning "Kodi reported nothing": one absence rule for every axis.
_ABSENT = formats.ABSENT

# Cross-build spellings of the same format, unified so a learned offset
# matches on every build. Never grow speculatively.
_HDR_ALIASES = {
    'hlghdr': 'hlg',
    # Kodi 21's HDR infolabel vs Kodi 22's native detection.
    'hdr10+': 'hdr10plus',
}

# --- Display names (used by the management view) ----------------------------
# An unrecognized segment renders as itself; these tables never reject.

HDR_DISPLAY = {
    'dolbyvision': 'Dolby Vision',
    'hdr10': 'HDR10',
    # Only the canonical spelling needs an entry: the store canonicalizes
    # every key at its boundary, so display code never sees 'hdr10+'.
    'hdr10plus': 'HDR10+',
    'hlg': 'HLG',
    'sdr': 'SDR',
    UNKNOWN: 'Unknown',
}

# Commercial display names for the codecs Kodi can report, sourced from
# Kodi's demuxer codec naming plus FFmpeg's canonical names. Display-only:
# these never participate in key matching and an unlisted codec renders
# verbatim, so the table can change without touching stored data.
AUDIO_DISPLAY = {
    # Dolby family ('truehd_atmos' and 'eac3_ddp_atmos' are Kodi's verbatim
    # profile reports).
    'truehd': 'Dolby TrueHD',
    'truehd_atmos': 'Dolby TrueHD Atmos',
    'eac3': 'Dolby Digital Plus',
    'eac3_ddp_atmos': 'Dolby Digital Plus Atmos',
    'ac3': 'Dolby Digital',
    # Kodi's demuxer knows AC-4 but StreamUtils has no special case for it,
    # so the reported name is FFmpeg's canonical 'ac4' (one spelling only:
    # FFmpeg has no Atmos profile variant for it).
    'ac4': 'Dolby AC-4',
    'mlp': 'MLP',
    # DTS family. Modern Kodi reports 'dts' for the base profile; 'dca' is
    # FFmpeg's canonical spelling kept for older report paths.
    'dts': 'DTS',
    'dca': 'DTS',
    'dts_es': 'DTS-ES',
    'dts_96_24': 'DTS 96/24',
    'dts_express': 'DTS Express',
    'dtshd_ma': 'DTS-HD MA',
    'dtshd_hra': 'DTS-HD HRA',
    'dtshd_ma_x': 'DTS:X',
    'dtshd_ma_x_imax': 'DTS:X IMAX',
    # AAC family (Kodi maps the MPEG profiles to their own names).
    'aac': 'AAC',
    'aac_lc': 'AAC-LC',
    'he_aac': 'HE-AAC',
    'he_aac_v2': 'HE-AAC v2',
    'aac_ssr': 'AAC SSR',
    'aac_ltp': 'AAC LTP',
    'aac_latm': 'AAC (LATM)',
    # Lossless / other.
    'flac': 'FLAC',
    'alac': 'ALAC',
    'opus': 'Opus',
    'vorbis': 'Vorbis',
    'mp3': 'MP3',
    'mp2': 'MP2',
    'wmav2': 'WMA',
    'wmapro': 'WMA Pro',
    'wmalossless': 'WMA Lossless',
    # PCM: FFmpeg names carry the sample layout; render the part a user
    # recognises. Rare layouts fall back verbatim like any other stranger.
    'pcm': 'PCM',
    'pcm_s16le': 'PCM 16-bit',
    'pcm_s24le': 'PCM 24-bit',
    'pcm_s32le': 'PCM 32-bit',
    'pcm_f32le': 'PCM 32-bit float',
    'pcm_bluray': 'PCM (Blu-ray)',
    'pcm_dvd': 'PCM (DVD)',
    UNKNOWN: 'Unknown Format',
}

# --- Toast short names (profile_summary only) --------------------------------
# The offset toast is a single narrow line and the full commercial names
# ('Dolby Digital Plus Atmos') force Estuary's auto-scroll, so it uses
# standard AV shorthand. A segment missing here falls back to the full
# display table, then verbatim. Established short forms only.

HDR_DISPLAY_SHORT = {
    'dolbyvision': 'DV',
}

AUDIO_DISPLAY_SHORT = {
    'truehd': 'TrueHD',
    'truehd_atmos': 'TrueHD Atmos',
    'eac3': 'DD+',
    'eac3_ddp_atmos': 'DD+ Atmos',
    # 'AC3', not 'DD': it matches what Kodi's own OSD calls the codec,
    # where a bare 'DD' next to 'DD+' reads as a typo.
    'ac3': 'AC3',
    'ac4': 'AC-4',
    UNKNOWN: 'Unknown',
}

# Channel-count segments with an established layout name. Only unambiguous
# counts are mapped (4 could be quad or 3.1, 7 could be 6.1 or 7.0; those
# render verbatim as '<n> ch'). Keyed by the segment string, since display
# always starts from a stored key.
CHANNEL_DISPLAY = {
    '1': '1.0',
    '2': '2.0',
    '6': '5.1',
    '8': '7.1',
}

# The all-devices bucket's heading, and a text no DEVICE may render:
# ``_device_label_parts`` reserves it so a device whose friendly name is
# literally this cannot file a row under what reads as the every-device
# scope.
DEVICE_ALL_LABEL = 'All devices'

# Toast-only cap on the device label (``_narrow_device_label``). Device
# names are the one axis with no bounded vocabulary, and the toast is a
# single line.
DEVICE_SUMMARY_MAX_CHARS = 24

# Axis names for the describe functions' ``omit_axes``. A caller drops the
# axis its surrounding heading already states; the axis is named rather than
# its display string, so an omission cannot depend on a display table.
AXIS_HDR = 'hdr'
AXIS_FPS = 'fps'
AXIS_AUDIO = 'audio'
AXIS_CHANNELS = 'ch'
AXIS_DEVICE = 'device'


def normalize_segment(raw):
    """Case-fold + trim a raw segment, then neutralise any stray separator.

    The ``|`` substitution is defensive: it is never expected inside a real
    codec/HDR string, but replacing it guarantees ``split_key`` always
    recovers exactly five parts. An empty raw string normalises to ''.

    Not defensive on the device axis, where a ``|`` is expected and load
    bearing: ``formats.split_device`` must partition the raw string before
    anything normalises it, or the friendly half folds into the key.
    """
    return str(raw).strip().lower().replace(SEPARATOR, '_')


def audio_segment(raw, distinct_spatial=True):
    """Normalise an audio string; collapse reported-absence to UNKNOWN.

    '', 'none' and 'unknown' all mean Kodi reported no audio format and map
    to the UNKNOWN sentinel. Every other value passes through verbatim, with
    no substring collapse ('pcm_s24le' stays 'pcm_s24le').

    ``distinct_spatial`` falsy collapses a spatial object-audio variant to
    its base codec, so TrueHD Atmos keys as 'truehd'. It defaults to verbatim
    because mode-independent callers (``canonical_key``, display) must never
    collapse.
    """
    segment = normalize_segment(raw)
    if segment in _ABSENT:
        return UNKNOWN
    if not distinct_spatial:
        return spatial_base(segment)
    return segment


def hdr_segment(raw):
    """Normalize an HDR string: whitespace strip, aliases, absence to UNKNOWN.

    Absence follows the same rule as audio. Choosing 'sdr' for an absent HDR
    axis is the detector's chain-of-evidence job, not this module's.
    Internal whitespace is stripped ('Dolby Vision' -> 'dolbyvision') and
    ``_HDR_ALIASES`` unifies the cross-build spellings that differ by more
    than spacing; the audio axis needs neither.
    """
    segment = ''.join(normalize_segment(raw).split())
    if segment in _ABSENT:
        return UNKNOWN
    return _HDR_ALIASES.get(segment, segment)


def fps_segment(fps, per_fps):
    """The fps segment: 'all' when per-FPS is off, else the truncated integer.

    When ``per_fps`` is falsy the value is ignored and the literal 'all' is
    returned. Otherwise the rate is truncated so fractional NTSC rates stay
    distinct from their integer siblings. Unparseable input raises
    ValueError: callers must gate on profile completeness before composing a
    per-FPS key.
    """
    if not per_fps:
        return 'all'
    if isinstance(fps, bool):
        # bool is an int subclass: True would silently become segment '1'.
        raise ValueError("fps_segment: unparseable fps value {!r}".format(fps))
    try:
        # OverflowError covers int(float('inf')): non-finite rates are
        # unparseable too, and this module is a public seam.
        return str(int(float(fps)))
    except (TypeError, ValueError, OverflowError):
        raise ValueError("fps_segment: unparseable fps value {!r}".format(fps))


def channel_segment(channels, distinct_channels=False):
    """The channel segment: 'all' when distinct-channels is off, else the
    verbatim source count.

    Unlike ``fps_segment`` this never raises: an unusable count (None,
    'unknown', 0, bool) degrades to 'all' even with the toggle on, because no
    completeness gate screens channels upstream and the all-channels key IS
    the intended key for a channel-less stream. The degradation is
    symmetrical in lookup and write, so it never strands a value where
    lookup will not find it.
    """
    if not distinct_channels:
        return 'all'
    if isinstance(channels, bool):
        # bool is an int subclass: True would silently become segment '1'.
        return 'all'
    try:
        # OverflowError covers int(float('inf')), as in fps_segment.
        count = int(channels)
    except (TypeError, ValueError, OverflowError):
        return 'all'
    if count <= 0:
        return 'all'
    return str(count)


def normalize_device(raw):
    """The device axis's spelling rule, independent of the granularity mode.

    Delegates to ``formats.normalize_device``, which owns the rule. It lives
    in the domain layer because ``profile.device_id()`` needs the identical
    spelling for stream identity and the domain may not import the store.
    """
    return formats.normalize_device(raw)


def device_segment(raw, distinct_devices=False):
    """The device segment: 'all' when distinct-devices is off, else the
    normalized id half of Kodi's audio-device string.

    Never raises, exactly like ``channel_segment``: an absent reading
    degrades to 'all' even with the toggle on, symmetrically in lookup and
    write.

    One divergence from the channel axis: a device read that FAILED (the
    gateway's None) is screened upstream by ``policies.is_complete``, since
    silently keying a live session onto 'all' would lose its applied offset.
    This function still degrades None so a pure key codec never raises, but
    that path is defensive; the empty-reading path is the real seam.
    """
    if not distinct_devices:
        return 'all'
    return normalize_device(raw)


def profile_key(hdr_raw, fps, audio_raw, *, per_fps, distinct_spatial=True,
                channels=None, distinct_channels=False, device=None,
                distinct_devices=False):
    """Compose the full ``<hdr>|<fps>|<audio>|<ch>|<dev>`` profile key."""
    return SEPARATOR.join((
        hdr_segment(hdr_raw),
        fps_segment(fps, per_fps),
        audio_segment(audio_raw, distinct_spatial),
        channel_segment(channels, distinct_channels),
        device_segment(device, distinct_devices),
    ))


def all_key(hdr_raw, audio_raw, *, distinct_spatial=True, channels=None,
            distinct_channels=False, device=None, distinct_devices=False):
    """The all-rates key: the candidate whenever the fps axis does not exist
    (toggle off, or a stream with no parseable rate).

    Delegates to ``profile_key`` with the fps toggle off, so the key shape
    has exactly one composition point. The other axes ride through.
    """
    return profile_key(hdr_raw, None, audio_raw, per_fps=False,
                       distinct_spatial=distinct_spatial,
                       channels=channels,
                       distinct_channels=distinct_channels,
                       device=device,
                       distinct_devices=distinct_devices)


def split_key(key):
    """Invert a profile key into ``(hdr, fps, audio, ch, dev)``; ValueError
    if not 5 parts. Callers see post-canonicalization keys, so the legacy 3-
    and 4-segment shapes never reach here."""
    parts = key.split(SEPARATOR)
    if len(parts) != 5:
        raise ValueError("split_key: expected 5 segments, got {!r}".format(key))
    return parts[0], parts[1], parts[2], parts[3], parts[4]


def key_device(key):
    """The device a stored key belongs to: its device segment, or the
    all-devices bucket.

    THE bucketing rule for the axis, shared by the management view's index
    levels and by ``device_names`` so two callers cannot bucket differently.
    A key that does not split, or one whose device segment is blank, joins
    the all-devices bucket, which is where a device-less read resolves and
    why that level needs no 'Other' bucket.
    """
    try:
        segment = split_key(key)[4]
    except ValueError:
        return formats.DEVICE_ALL
    return segment if segment.strip() else formats.DEVICE_ALL


def canonical_key(key):
    """Re-express a stored key in the current canonical spelling.

    The store runs every key crossing its boundary (file load, the
    other-process reader, import) through this, so the spelling rules reach
    data written by an older codec exactly as they reach live composition. A
    schema-1 key gains two trailing 'all' segments and a schema-2 key gains
    one, which is the entire migration. An unsplittable key returns
    unchanged, and the whole thing is idempotent.

    Mode-independent by design, since canonicalization must not rewrite
    stored keys when a granularity toggle flips: the fps and channel segments
    pass through untouched and the audio segment never spatial-collapses. The
    device segment is the exception and re-runs ``normalize_device``, because
    it is the one axis whose spelling is platform-supplied free text.
    """
    parts = key.split(SEPARATOR)
    if len(parts) == 3:
        hdr, fps, audio = parts
        ch = device = 'all'
    elif len(parts) == 4:
        hdr, fps, audio, ch = parts
        device = 'all'
    elif len(parts) == 5:
        hdr, fps, audio, ch, device = parts
    else:
        return key
    return SEPARATOR.join((hdr_segment(hdr), fps, audio_segment(audio), ch,
                           normalize_device(device)))


def _display_fps(segment, video_fps=None, per_fps=False):
    if segment == 'all':
        # With per_fps on an 'all' entry is dormant, so the label states its
        # scope. With it off, 'all' is the only key consulted, so the axis
        # carries no information and is omitted.
        return 'All FPS' if per_fps else None
    if isinstance(video_fps, (int, float)) and \
            not isinstance(video_fps, bool) and math.isfinite(video_fps):
        return "{0:g} fps".format(video_fps)
    return "{} fps".format(segment)


def _display_channels(segment, distinct_channels=False):
    # Same shape as _display_fps. A specific count always renders, via the
    # layout table or verbatim as '<n> ch'.
    if segment == 'all':
        return 'All channels' if distinct_channels else None
    return CHANNEL_DISPLAY.get(segment, "{} ch".format(segment))


def display_device(segment, device_label=None, distinct_devices=False):
    """The device axis's rendering of one key segment, or None when the axis
    carries no information.

    Same shape as ``_display_fps``/``_display_channels``. A specific device
    renders ``device_label``, falling back to the raw id segment.

    ``device_label`` must be THE LABEL for the device, not an entry's raw
    ``device_name`` metadata: the two coincide only where no second device
    reports the same name, often enough that passing the metadata looks
    right and reads wrong. (This function is also the base-name step inside
    ``device_labels``, where the metadata is genuinely what it takes.)

    Public where the other axes' helpers are private, because the management
    view groups by device and needs a label for a heading or an index row,
    with no key in hand to describe.
    """
    if segment == 'all':
        return DEVICE_ALL_LABEL if distinct_devices else None
    if isinstance(device_label, str) and device_label.strip():
        return device_label.strip()
    return segment


def _suffixed(base, part):
    """A disambiguated label: the base plus one parenthesised part."""
    return "{0} ({1})".format(base, part)


def _device_label_parts(names):
    """Every known device's ``(label, name part)``, keyed by segment.

    The mechanics of the rule ``device_labels`` publishes: one pass, three
    candidates per device, and the first candidate no OTHER device could
    render wins.

    1. the device's base: its friendly name, or its raw id segment where
       Kodi reported none (``display_device``);
    2. that base with the device's own key segment in parentheses;
    3. the key segment alone.

    A text is reserved when some other device could render it, which is
    exactly that device's own three candidates, plus ``DEVICE_ALL_LABEL``,
    which no device may impersonate. Key segments are unique per device by
    definition, so candidate 3 is always free and the rule is total: no
    search, no fixpoint, nothing that can fail to land.

    The second element is the label's NAME part: the base for a
    parenthesised label and the label itself otherwise. It is always a
    prefix of the label, and it is what the toast falls back to.
    """
    bases = {}
    for segment, name in names.items():
        if segment == formats.DEVICE_ALL:
            continue
        bases[segment] = display_device(segment, name, True)

    # What every device COULD render, counted rather than gathered per
    # device, so the rule is a membership test costing one pass over the
    # devices rather than one per pair.
    base_counts = {}
    suffixed_counts = {}
    for segment, base in bases.items():
        base_counts[base] = base_counts.get(base, 0) + 1
        text = _suffixed(base, segment)
        suffixed_counts[text] = suffixed_counts.get(text, 0) + 1

    def reserved(text, segment, own_base):
        """Whether some device OTHER than ``segment`` could render ``text``."""
        if text == DEVICE_ALL_LABEL:
            return True
        # Another device's base, discounting this device's own.
        if base_counts.get(text, 0) - (1 if text == own_base else 0) > 0:
            return True
        # Another device's parenthesised form. Two devices CAN produce the
        # same one (a segment may itself contain ' ('), hence the count.
        own_suffixed = _suffixed(own_base, segment)
        if suffixed_counts.get(text, 0) - (1 if text == own_suffixed else 0) \
                > 0:
            return True
        # Another device's key segment, which is what a collision demotes it
        # to. Reserving these is what keeps candidate 3 free.
        return text in bases and text != segment

    parts = {}
    for segment, base in bases.items():
        if not reserved(base, segment, base):
            parts[segment] = (base, base)
            continue
        suffixed = _suffixed(base, segment)
        if not reserved(suffixed, segment, base):
            parts[segment] = (suffixed, base)
            continue
        parts[segment] = (segment, segment)
    return parts


def device_labels(names):
    """Label every known device, disambiguating a shared friendly name.

    THE device label rule, and the only one either surface uses: the
    management view labels its rows, headings and index rows from it, and
    the toast labels the live device from it through ``device_label_for``,
    so one device can never be named two ways. ``names`` maps every known
    device segment to its friendly name (None where none is known); the
    answer maps each segment to its label.

    A friendly name no other device could render is the label. Where two or
    more devices report one name, each takes its OWN key segment in
    parentheses after it ('AML-AUGESOUND (alsa:hdmi:card=x,dev=0)'), and
    where even that could read as another device's text, the key segment
    stands alone (``_device_label_parts``). A device with no friendly name
    at all, as on Kodi 20, labels by its raw id segment.

    A shared name is an upstream fact, not a misread:
    ``CAEDeviceInfo::GetFriendlyName`` returns ``m_displayName``, which the
    ALSA sink sets from the CARD name while the distinguishing token
    ('HDMI', 'Analog', 'S/PDIF') goes to ``m_displayNameExtra``. Every PCM
    on one card therefore reports one name, and no way of reading the stored
    setting can separate them.

    Every candidate is derived from the device's OWN facts rather than from
    its position among the others, so adding or deleting a device can move a
    label between the three forms but a text that named device X can never
    come to name device Y. The trade is length, since a collision hands a
    device its whole key segment; the toast's width is handled at the toast,
    never by making a label mean something else.

    Two devices never share a label here. What is NOT promised is that two
    labels stay apart in a TOAST: two sharing a friendly name narrow to that
    shared name, and the management view is where they are told apart.
    """
    return {segment: label for segment, (label, _head)
            in _device_label_parts(names).items()}


def device_names(entries):
    """Every device a stored snapshot knows, mapped to its friendly name.

    The INPUT half of the label rule, shared so the two surfaces cannot feed
    ``device_labels`` different worlds. ``entries`` is a ``{key: entry}``
    store snapshot; the answer maps each device segment to the
    ``device_name`` metadata to render it by, or None where no entry carries
    one. A device no entry names still appears, because the label rule has to
    see it to judge whether anything collides with it.

    A device is named once for the whole store, by its most recently updated
    named entry with the key as a tie-break: the friendly half is whatever
    Kodi last reported, so the newest write is the current spelling, and
    iteration order (neither stable nor meaningful across two processes
    reading one file) decides nothing.
    """
    best = {}
    for key, entry in entries.items():
        segment = key_device(key)
        name = entry.get('device_name')
        if not isinstance(name, str) or not name.strip():
            name = None
        stamp = entry.get('updated')
        if not isinstance(stamp, str):
            stamp = ''
        if segment not in best:
            best[segment] = (name, stamp, key)
        elif name is not None:
            known, known_stamp, known_key = best[segment]
            if known is None or (stamp, key) > (known_stamp, known_key):
                best[segment] = (name, stamp, key)
    return {segment: name for segment, (name, _s, _k) in best.items()}


# The toast's width cap is spent as head + ellipsis + tail, eliding a run
# out of the MIDDLE. Truncating the tail instead would cut exactly where
# endpoints differ (',dev=0' vs ',dev=1', '(HDMI 1)' vs '(HDMI 2)'), which
# is also why the tail takes the odd character.
_NARROW_ELLIPSIS = '…'
_NARROW_TAIL_CHARS = DEVICE_SUMMARY_MAX_CHARS // 2
_NARROW_HEAD_CHARS = DEVICE_SUMMARY_MAX_CHARS - 1 - _NARROW_TAIL_CHARS


def _narrow_label(text):
    """Any text held to the toast's width, eliding a run out of its middle.

    The elision primitive, used on a device's name part
    (``_narrow_device_label``) and on the notifier's withheld log copy
    (``_summary_device``). Pure text work with no knowledge of what it cuts.
    """
    if len(text) <= DEVICE_SUMMARY_MAX_CHARS:
        return text
    return (text[:_NARROW_HEAD_CHARS] + _NARROW_ELLIPSIS +
            text[len(text) - _NARROW_TAIL_CHARS:])


def _narrow_device_label(label, name_part):
    """A device's label at the toast's width, preferring the most it can
    show whole.

    Width is the ONE sanctioned divergence between the toast and the
    management view: both name a device through ``device_labels``, and this
    shortens THAT label rather than substituting a different one.

    In order: the whole label when it fits, else the name part alone (a true
    prefix of the label, and better reading than an id's elided tail), else
    that name part with a run elided out of its middle. It decides nothing,
    which is why two devices CAN narrow alike.
    """
    if len(label) <= DEVICE_SUMMARY_MAX_CHARS:
        return label
    if len(name_part) <= DEVICE_SUMMARY_MAX_CHARS:
        return name_part
    return _narrow_label(name_part)


def device_label_for(raw_device, entries):
    """The toast's label for a LIVE device reading, given the store.

    The service side's single call: the shared rule over every device the
    store knows, narrowed to the toast's width. None when the reading names
    no device, which the toast renders as nothing, since it states facts
    rather than scope.

    The label for a device the store KNOWS comes from the store alone, so
    both surfaces label it from identical inputs. The live reading is folded
    in only for a device no entry mentions, which the view cannot render at
    all, so there is no parity to break. That gap is real rather than
    theoretical: a Kodi 20 store carries no ``device_name`` anywhere, and an
    apply-only user never rewrites the metadata after upgrading.
    """
    segment = device_segment(raw_device, True)
    if segment == formats.DEVICE_ALL:
        return None
    names = device_names(entries)
    if segment not in names:
        names[segment] = split_device(raw_device)[1]
    label, name_part = _device_label_parts(names)[segment]
    return _narrow_device_label(label, name_part)


def _axis_labels(key, video_fps, per_fps, distinct_channels, device_label,
                 distinct_devices):
    """Every axis's display label for one key, None where the axis carries
    no information.

    One vocabulary for both describe functions, which differ only in which
    axes they lay out, in what order, and how they join them. Raises
    ValueError on an unsplittable key, which is the contract the callers'
    verbatim fallbacks are built on.
    """
    hdr, fps, audio, ch, device = split_key(key)
    return {
        AXIS_HDR: HDR_DISPLAY.get(hdr, hdr),
        AXIS_FPS: _display_fps(fps, video_fps, per_fps),
        AXIS_AUDIO: AUDIO_DISPLAY.get(audio, audio),
        AXIS_CHANNELS: _display_channels(ch, distinct_channels),
        AXIS_DEVICE: display_device(device, device_label, distinct_devices),
    }


# Axis layouts. The full line leads with the HDR type; the in-group line
# has no HDR slot at all (the open group's heading names it) and leads
# with the codec, the stable-width part.
_FULL_ORDER = (AXIS_HDR, AXIS_FPS, AXIS_AUDIO, AXIS_CHANNELS, AXIS_DEVICE)
_IN_GROUP_ORDER = (AXIS_AUDIO, AXIS_FPS, AXIS_CHANNELS, AXIS_DEVICE)


def _join_axes(labels, order, omit_axes, joiner):
    """Lay out the labels an axis order asks for, minus the omitted ones."""
    return joiner.join(labels[axis] for axis in order
                       if axis not in omit_axes and labels[axis] is not None)


def describe_key(key, video_fps=None, per_fps=False, distinct_channels=False,
                 device_label=None, distinct_devices=False,
                 omit_axes=frozenset()):
    """Human-readable label, e.g. 'Dolby Vision | 23.976 fps | TrueHD | 5.1'.

    Segments use the display tables, falling back to the raw segment when
    unrecognized. An 'all' segment states its scope in the mode where it is
    dormant and is omitted in the mode where it is the only key consulted. A
    numeric fps segment renders the exact reported rate from the entry's
    ``video_fps`` metadata, degrading to the truncated segment when that is
    absent or malformed. ``omit_axes`` (``AXIS_*`` names) drops axes the
    caller's surrounding heading already states.
    """
    return _join_axes(
        _axis_labels(key, video_fps, per_fps, distinct_channels, device_label,
                     distinct_devices),
        _FULL_ORDER, omit_axes, " | ")


def describe_key_in_group(key, video_fps=None, per_fps=False,
                          distinct_channels=False, device_label=None,
                          distinct_devices=False, omit_axes=frozenset()):
    """In-group row label, e.g. 'Dolby TrueHD · 23.976 fps · 5.1'.

    The grouped drill-down lists one HDR type at a time, so the layout has
    no HDR slot and the codec leads. Same vocabulary, axis semantics,
    ``omit_axes`` handling and ValueError contract as ``describe_key``.
    """
    return _join_axes(
        _axis_labels(key, video_fps, per_fps, distinct_channels, device_label,
                     distinct_devices),
        _IN_GROUP_ORDER, omit_axes, " · ")


def _axis_rank(segment):
    """Sort rank for an 'all'-or-numeric axis segment: the 'all' entry
    first, numeric values in numeric order (string-sorting '119' before
    '23' is the bug this avoids), non-numeric junk after them."""
    if segment == 'all':
        return (0, 0)
    try:
        return (1, int(segment))
    except ValueError:
        return (2, 0)


def _device_rank(segment, device_label=None):
    """Sort rank for the device axis: 'all' first, then named devices
    alphabetically by the label the user actually sees.

    Device segments are opaque strings rather than numerics, so they rank by
    their label (what ``device_labels`` resolved, else the raw id). Ranking
    by the segment would order a Windows store by GUID, which reads as
    random.
    """
    if segment == 'all':
        return (0, '')
    return (1, display_device(segment, device_label, True).lower())


def sort_key(key, device_label=None):
    """Deterministic display ordering: device, HDR type, codec, rate,
    channels.

    Groups the view's rows the way a user scans them: one output device
    together ('all' first, then device names alphabetically), one HDR mode
    together within it, codecs alphabetical within that, and each codec's
    'all' entry before its per-fps entries in numeric rate order.
    ``device_label`` is the device's LABEL over the whole store, so rows
    order by the name the view shows. Total over hand-edited files: an
    unsplittable key sorts by its raw text and the raw key is the final
    tie-break.
    """
    try:
        hdr, fps, audio, ch, device = split_key(key)
    except ValueError:
        return ((0, ''), key.lower(), '', (0, 0), (0, 0), key)
    return (
        _device_rank(device, device_label),
        HDR_DISPLAY.get(hdr, hdr).lower(),
        AUDIO_DISPLAY.get(audio, audio).lower(),
        _axis_rank(fps),
        _axis_rank(ch),
        key,
    )


def _summary_device(label):
    """The toast's device text: a plain string held to the toast's width.

    ``device_label_for`` has already narrowed a real label and narrowing is
    idempotent, so this is really the cap for the one caller arriving with
    no label at all: the notifier's withheld log copy, which passes the
    unbounded canonical id segment.
    """
    # A blank label is no label. ``device_labels`` cannot produce one, but
    # the toast must never grow an empty ' | ' tail from a caller's absence
    # spelling.
    if not label or not label.strip():
        return None
    return _narrow_label(label)


def profile_summary(hdr_segment_value, audio_segment_value, video_fps=None,
                    channels=None, device_label=None):
    """Toast/log summary straight from profile facts (no key needed).

    E.g. 'DV | 23.976 fps | TrueHD Atmos | 7.1 | Soundbar'; without a rate,
    count or device, 'DV | TrueHD'. Uses the short display overlays, falling
    back to the full table and then verbatim. The caller passes ``channels``
    and ``device_label`` only when that axis is offset-relevant, and
    ``device_label`` must be a LABEL from ``device_label_for`` rather than a
    raw setting string.
    """
    parts = [HDR_DISPLAY_SHORT.get(
        hdr_segment_value,
        HDR_DISPLAY.get(hdr_segment_value, hdr_segment_value))]
    if video_fps is not None:
        parts.append("{0:g} fps".format(video_fps))
    parts.append(AUDIO_DISPLAY_SHORT.get(
        audio_segment_value,
        AUDIO_DISPLAY.get(audio_segment_value, audio_segment_value)))
    if channels is not None:
        segment = channel_segment(channels, True)
        # A degraded segment ('all' from an unusable count) renders nothing:
        # the toast states facts, not scope.
        if segment != 'all':
            parts.append(_display_channels(segment, True))
    if device_label is not None:
        # Same rule as the channel axis: an unreadable device resolves to no
        # label at all, and scope is not a fact worth toasting.
        label = _summary_device(device_label)
        if label is not None:
            parts.append(label)
    return " | ".join(parts)
