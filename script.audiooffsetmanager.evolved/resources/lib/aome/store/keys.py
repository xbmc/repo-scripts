"""Profile-key algebra for the sparse offset store.

Keys are derived from what Kodi reports, accepted verbatim: no whitelist,
no substring matching, no alias table gating which codecs or HDR types are
known. A codec or HDR string this code has never seen becomes a working key
with no code change. Normalization is minimal: case-fold + trim, plus a
defensive ``|`` substitution; the HDR axis also strips internal whitespace
and unifies known cross-build spelling splits (see ``hdr_segment``).

Aliases never grow speculatively. Each exists because the same format was
reported under two spellings by different Kodi builds, where a fragmented
key would strand a learned offset: ``hlghdr`` -> ``hlg`` and ``hdr10+`` ->
``hdr10plus`` (Kodi 21's HDR infolabel says 'HDR10+', Kodi 22's native
detection says 'hdr10plus'). Spaced title-case reports ('Dolby Vision' vs
'dolbyvision') are the same class, handled by the whitespace strip rather
than per-variant aliases.

Key shape: ``<hdr>|<fps>|<audio>|<ch>`` (e.g. ``dolbyvision|23|truehd|all``,
``hdr10plus|all|aac|6``). The ``|`` joiner is why ``normalize_segment`` maps
any stray ``|`` inside a raw string to ``_``, so ``split_key`` always
recovers exactly four parts. Schema-1 keys had three segments (no channel
axis); ``canonical_key`` expands them with a trailing ``all``, which is the
whole migration — lossless, idempotent, and running at the store boundary
where every stored key already passes.

Absence (empty, 'none', 'unknown') collapses to the UNKNOWN sentinel; every
other string passes through verbatim. ``hdr_segment`` maps a blank HDR to
'unknown', not 'sdr': choosing 'sdr' for an absent flag is a
chain-of-evidence decision that belongs to the detector, not this pure
module. FPS uses integer truncation, keeping NTSC fractional rates distinct
from their integer siblings (23.976 -> 23 vs 24.0 -> 24); with per-fps off
the segment is the literal 'all'. The audio axis has its own granularity
mode: with distinct-spatial off, a spatial object-audio variant keys as its
base codec (``formats.SPATIAL_BASE``). The channel axis mirrors fps ('all'
by default, the verbatim source count with distinct-channels on) with one
divergence: an unusable count degrades to 'all' instead of raising, because
no completeness gate screens channels upstream and 'all' is the intended
key for a channel-less stream in lookup and write alike. All modes live in
key composition only — ``canonical_key`` is mode-independent and never
collapses any axis.

Pure Python: stdlib only, no xbmc* imports.
"""

import math

from resources.lib.aome.domain.formats import UNKNOWN, spatial_base

# Segment joiner for the composite profile key.
SEPARATOR = '|'

# Strings meaning "Kodi reported nothing" — one absence rule for every axis.
_ABSENT = ('', 'none', UNKNOWN)

# Cross-build spellings of the same format, unified so a learned offset
# matches on every build (see module docstring). Never grow speculatively.
_HDR_ALIASES = {
    'hlghdr': 'hlg',
    # Kodi 21's HDR infolabel vs Kodi 22's native detection.
    'hdr10+': 'hdr10plus',
}

# --- Display names (used by the management view) ----------------------------
# The fallback for an unrecognized segment is the raw segment itself, never
# a rejection.

HDR_DISPLAY = {
    'dolbyvision': 'Dolby Vision',
    'hdr10': 'HDR10',
    # Only the canonical 'hdr10plus' needs an entry: the store
    # canonicalizes every key at its boundary (see canonical_key), so
    # display code never sees an alias-source spelling like 'hdr10+'.
    'hdr10plus': 'HDR10+',
    'hlg': 'HLG',
    'sdr': 'SDR',
    UNKNOWN: 'Unknown',
}

# Commercial display names for the codecs Kodi can report. Sourced from
# Kodi's StreamUtils::GetCodecName (the names JSON-RPC
# `currentaudiostream.codec` carries; the gateway strips the `pt-`
# passthrough prefix first) plus FFmpeg's canonical names. Display-only:
# these never participate in key matching, and an unlisted codec renders
# verbatim, so this table can grow or shrink without touching stored data.
AUDIO_DISPLAY = {
    # Dolby family, consistently branded ('truehd_atmos' and
    # 'eac3_ddp_atmos' are Kodi's verbatim profile reports).
    'truehd': 'Dolby TrueHD',
    'truehd_atmos': 'Dolby TrueHD Atmos',
    'eac3': 'Dolby Digital Plus',
    'eac3_ddp_atmos': 'Dolby Digital Plus Atmos',
    'ac3': 'Dolby Digital',
    # Kodi's demuxer knows AC-4 but StreamUtils has no special case for
    # it, so the reported name is FFmpeg's canonical 'ac4' (no Atmos
    # profile variant exists in FFmpeg — one spelling only).
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
# The offset toast is a single narrow line: the full commercial names
# ('Dolby Digital Plus Atmos') force Estuary's auto-scroll, so the toast
# uses standard AV shorthand. A segment missing here falls back to the full
# display table, then verbatim. Only names with an established shorter form
# appear; nothing is invented.

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
# counts are mapped (4 could be quad or 3.1, 7 could be 6.1 or 7.0 — those
# render verbatim as '<n> ch'); nothing is invented. Keyed by the segment
# string, since display always starts from a stored key.
CHANNEL_DISPLAY = {
    '1': '1.0',
    '2': '2.0',
    '6': '5.1',
    '8': '7.1',
}


def normalize_segment(raw):
    """Case-fold + trim a raw segment, then neutralise any stray separator.

    The `|` substitution is purely defensive: `|` is the key joiner and is
    never expected inside a real codec/HDR string, but replacing it with `_`
    guarantees `split_key` can always recover exactly three parts. May return
    '' (an empty raw string normalises to '').
    """
    return str(raw).strip().lower().replace(SEPARATOR, '_')


def audio_segment(raw, distinct_spatial=True):
    """Normalise an audio string; collapse reported-absence to UNKNOWN.

    '', 'none', and 'unknown' all mean Kodi reported no audio format and map to
    the UNKNOWN sentinel. Every other value passes through verbatim — no
    whitelist, no substring collapse (e.g. 'pcm_s24le' stays 'pcm_s24le').

    ``distinct_spatial`` is the audio-granularity mode (the
    distinct-spatial toggle): falsy collapses a spatial object-audio
    variant to its base codec (``formats.SPATIAL_BASE``), so TrueHD Atmos
    keys as 'truehd'. The default is verbatim because mode-independent
    callers (``canonical_key``, display) must never collapse — the mode
    belongs to key composition, exactly like the fps axis.
    """
    segment = normalize_segment(raw)
    if segment in _ABSENT:
        return UNKNOWN
    if not distinct_spatial:
        return spatial_base(segment)
    return segment


def hdr_segment(raw):
    """Normalize an HDR string: whitespace strip, aliases, absence to UNKNOWN.

    Absence follows the same rule as audio ('', 'none', 'unknown' ->
    UNKNOWN). Choosing 'sdr' for an absent HDR axis is the detector's
    chain-of-evidence job, not this module's. Internal whitespace is
    stripped and ``_HDR_ALIASES`` unifies the cross-build spellings that
    differ by more than spacing (see the module docstring); the audio axis
    needs neither.
    """
    segment = ''.join(normalize_segment(raw).split())
    if segment in _ABSENT:
        return UNKNOWN
    return _HDR_ALIASES.get(segment, segment)


def fps_segment(fps, per_fps):
    """The fps segment: 'all' when per-FPS is off, else the truncated integer.

    When `per_fps` is falsy the value is ignored and the literal 'all' is
    returned. Otherwise the rate is truncated to an integer via
    ``int(float(fps))`` so fractional NTSC rates stay distinct from their
    integer siblings. Unparseable input (None, '', 'abc') raises ValueError —
    callers must gate on profile completeness before composing a per-FPS key.
    """
    if not per_fps:
        return 'all'
    if isinstance(fps, bool):
        # bool is an int subclass: True would silently become segment '1'.
        raise ValueError("fps_segment: unparseable fps value {!r}".format(fps))
    try:
        # OverflowError: int(float('inf')) — non-finite rates are unparseable
        # too (the detector screens them, but this module is a public seam).
        return str(int(float(fps)))
    except (TypeError, ValueError, OverflowError):
        raise ValueError("fps_segment: unparseable fps value {!r}".format(fps))


def channel_segment(channels, distinct_channels=False):
    """The channel segment: 'all' when distinct-channels is off, else the
    verbatim source count.

    Unlike ``fps_segment`` this never raises: an unusable count (None,
    'unknown', 0, bool) degrades to 'all' even with the toggle on, because
    no completeness gate screens channels upstream and the all-channels key
    IS the intended key for a channel-less stream — symmetrically in lookup
    and write, so a degraded write never strands a value where lookup will
    not find it. In practice the gateway reports channels and codec from the
    same response, so a missing count implies an incomplete profile that
    never reaches key composition anyway.
    """
    if not distinct_channels:
        return 'all'
    if isinstance(channels, bool):
        # bool is an int subclass: True would silently become segment '1'.
        return 'all'
    try:
        # OverflowError: int(float('inf')) — non-finite counts are junk
        # too (this module is a public seam, like fps_segment).
        count = int(channels)
    except (TypeError, ValueError, OverflowError):
        return 'all'
    if count <= 0:
        return 'all'
    return str(count)


def profile_key(hdr_raw, fps, audio_raw, *, per_fps, distinct_spatial=True,
                channels=None, distinct_channels=False):
    """Compose the full ``<hdr>|<fps>|<audio>|<ch>`` profile key."""
    return SEPARATOR.join((
        hdr_segment(hdr_raw),
        fps_segment(fps, per_fps),
        audio_segment(audio_raw, distinct_spatial),
        channel_segment(channels, distinct_channels),
    ))


def all_key(hdr_raw, audio_raw, *, distinct_spatial=True, channels=None,
            distinct_channels=False):
    """The all-rates key ``<hdr>|all|<audio>|<ch>`` — the candidate whenever
    the fps axis does not exist (toggle off, or a stream with no
    parseable rate). The channel axis is independent and rides through.

    Delegates to ``profile_key`` with the fps toggle off (which forces the
    'all' segment) so the key shape has exactly one composition point.
    """
    return profile_key(hdr_raw, None, audio_raw, per_fps=False,
                       distinct_spatial=distinct_spatial,
                       channels=channels,
                       distinct_channels=distinct_channels)


def split_key(key):
    """Invert a profile key into ``(hdr, fps, audio, ch)``; ValueError if
    not 4 parts. Callers see post-canonicalization keys, so the legacy
    3-segment shape never reaches here."""
    parts = key.split(SEPARATOR)
    if len(parts) != 4:
        raise ValueError("split_key: expected 4 segments, got {!r}".format(key))
    return parts[0], parts[1], parts[2], parts[3]


def canonical_key(key):
    """Re-express a stored key in the current canonical spelling.

    The store runs every key crossing its boundary (file load, the
    other-process reader, import) through this, so the spelling rules reach
    data written by an older codec exactly as they reach live composition.
    Segments re-run their own segment functions, so a format this code has
    never seen round-trips verbatim. A schema-1 key (three segments, no
    channel axis) is expanded with a trailing 'all' — the entire v1→v2
    migration, lossless by construction. Mode-independent by design: the
    fps and channel segments pass through untouched and the audio segment
    never spatial-collapses, since canonicalization must not rewrite stored
    keys when a granularity toggle flips. An unsplittable key returns
    unchanged. Idempotent by construction.
    """
    parts = key.split(SEPARATOR)
    if len(parts) == 3:
        hdr, fps, audio = parts
        ch = 'all'
    elif len(parts) == 4:
        hdr, fps, audio, ch = parts
    else:
        return key
    return SEPARATOR.join((hdr_segment(hdr), fps, audio_segment(audio), ch))


def _display_fps(segment, video_fps=None, per_fps=False):
    if segment == 'all':
        # With per_fps on, an 'all' entry is dormant, so 'All FPS' states
        # its scope (every rate, in the other mode). With per_fps off, 'all'
        # is the only key consulted, so the axis carries no information and
        # the segment is omitted (None).
        return 'All FPS' if per_fps else None
    if isinstance(video_fps, (int, float)) and \
            not isinstance(video_fps, bool) and math.isfinite(video_fps):
        return "{0:g} fps".format(video_fps)
    return "{} fps".format(segment)


def _display_channels(segment, distinct_channels=False):
    # Same shape as _display_fps: 'all' states its scope only in the mode
    # where it is dormant, and is omitted when it is the only key consulted.
    # A specific count always renders (it is what distinguishes a dormant
    # row), via the layout table or verbatim as '<n> ch'.
    if segment == 'all':
        return 'All channels' if distinct_channels else None
    return CHANNEL_DISPLAY.get(segment, "{} ch".format(segment))


def describe_key(key, video_fps=None, per_fps=False, distinct_channels=False):
    """Human-readable label, e.g. 'Dolby Vision | 23.976 fps | TrueHD | 5.1'.

    HDR and audio segments use the display tables, falling back to the raw
    segment when unrecognized. The 'all' fps segment renders as 'All FPS'
    when ``per_fps`` is on and is omitted when off; the channel segment
    follows the same rule under ``distinct_channels`` ('All channels' /
    omitted), with a specific count rendering its layout name or '<n> ch'.
    A numeric fps segment renders the exact reported rate from the entry's
    ``video_fps`` metadata when the caller supplies a finite number,
    degrading to the truncated segment ('<n> fps') when it is absent or
    malformed.
    """
    hdr, fps, audio, ch = split_key(key)
    parts = [HDR_DISPLAY.get(hdr, hdr)]
    fps_name = _display_fps(fps, video_fps, per_fps)
    if fps_name is not None:
        parts.append(fps_name)
    parts.append(AUDIO_DISPLAY.get(audio, audio))
    ch_name = _display_channels(ch, distinct_channels)
    if ch_name is not None:
        parts.append(ch_name)
    return " | ".join(parts)


def describe_key_in_group(key, video_fps=None, per_fps=False,
                          distinct_channels=False):
    """In-group row label, e.g. 'Dolby TrueHD · 23.976 fps · 5.1'.

    The grouped drill-down lists one HDR type at a time, so rows drop the
    redundant HDR name and lead with the codec. Same display vocabulary,
    axis semantics, and verbatim fallbacks as ``describe_key``, and it
    raises ValueError on an unsplittable key the same way.
    """
    _hdr, fps, audio, ch = split_key(key)
    parts = [AUDIO_DISPLAY.get(audio, audio)]
    fps_name = _display_fps(fps, video_fps, per_fps)
    if fps_name is not None:
        parts.append(fps_name)
    ch_name = _display_channels(ch, distinct_channels)
    if ch_name is not None:
        parts.append(ch_name)
    return " · ".join(parts)


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


def sort_key(key):
    """Deterministic display ordering: HDR type, codec, rate, channels.

    Groups the view's rows the way a user scans them: one HDR mode
    together, codecs alphabetical within it, each codec's 'all' entry
    before its per-fps entries in numeric rate order, and the channel axis
    breaking ties the same way ('all' first, counts ascending). Total over
    hand-edited files: an unsplittable key sorts by its raw text, a
    non-numeric axis segment sorts after the numeric values, and the raw
    key is the final tie-break.
    """
    try:
        hdr, fps, audio, ch = split_key(key)
    except ValueError:
        return (key.lower(), '', (0, 0), (0, 0), key)
    return (
        HDR_DISPLAY.get(hdr, hdr).lower(),
        AUDIO_DISPLAY.get(audio, audio).lower(),
        _axis_rank(fps),
        _axis_rank(ch),
        key,
    )


def profile_summary(hdr_segment_value, audio_segment_value, video_fps=None,
                    channels=None):
    """Toast/log summary straight from profile facts (no key needed).

    E.g. 'DV | 23.976 fps | TrueHD Atmos | 7.1'; without a rate or count,
    'DV | TrueHD'. Uses the short display overlays (the toast is one narrow
    line), falling back to the full table and then verbatim. The exact
    reported rate is shown; the caller passes ``channels`` only when the
    count is offset-relevant (distinct-channels on), mirroring the fps
    axis.
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
        # A degraded segment ('all' from an unusable count) renders
        # nothing: the toast states facts, not scope.
        if segment != 'all':
            parts.append(_display_channels(segment, True))
    return " | ".join(parts)
