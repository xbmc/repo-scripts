"""Format vocabulary — the single source of truth for stream classification.

Everything that enumerates HDR types, audio formats, or FPS buckets derives
from this module: stream detection, `StreamProfile` display names and
setting keys, the settings.xml generator (tools/generate_settings.py), and the
contract tests. Changing the vocabulary here is how a format is added or
removed; nothing else may hardcode these lists. (Sole exception:
tests/contract/test_settings_matrix.py keeps an intentionally independent
hardcoded copy as a drift oracle — see the comment there.)

Pure Python: no Kodi imports.
"""

# HDR types, in settings.xml category order.
HDR_TYPES = ('dolbyvision', 'hdr10', 'hdr10plus', 'hlg', 'sdr')

# Audio formats, in settings.xml row order. ORDER IS LOAD-BEARING for
# substring matching: 'ac3' is a substring of 'eac3', so 'eac3' must be
# tested first or Dolby Digital+ streams would key to the ac3 bucket.
AUDIO_FORMATS = ('truehd', 'eac3', 'ac3', 'dtshd_ma', 'dtshd_hra', 'dca', 'pcm')

# Specific FPS buckets (integer values as detected from the player), plus the
# 'all' pseudo-bucket used when the per-HDR FPS override is disabled.
# Elements are ints ON PURPOSE: the stream detector membership-tests the player's
# integer fps against this tuple. Setting keys and display lookups use
# str(bucket). test_formats pins the int-ness.
FPS_BUCKETS = (23, 24, 25, 29, 30, 50, 59, 60)
FPS_ALL = 'all'

# Sentinel for any axis that could not be detected.
UNKNOWN = 'unknown'

# --- Display names (user-facing, used in notifications/log summaries) -------

HDR_DISPLAY_NAMES = {
    'dolbyvision': 'DV',
    'hdr10': 'HDR10',
    'hdr10plus': 'HDR10+',
    'hlg': 'HLG',
    'sdr': 'SDR',
}

AUDIO_DISPLAY_NAMES = {
    'truehd': 'TrueHD',
    'eac3': 'DD+',
    'ac3': 'DD',
    'dtshd_ma': 'DTS-HD MA',
    'dtshd_hra': 'DTS-HD HRA',
    'dca': 'DTS',
    'pcm': 'PCM',
    'unknown': 'Unknown Format',
}

# Keyed by str(fps_bucket): fps_type travels as int or str depending on source.
FPS_DISPLAY_NAMES = {
    '23': '23.98',
    '24': '24.00',
    '25': '25.00',
    '29': '29.97',
    '30': '30.00',
    '50': '50.00',
    '59': '59.94',
    '60': '60.00',
}

# --- strings.po ids paired with the vocabulary (used by the generator) ------

# (label_id, help_id) of the offset slider for each audio format. Identical
# across every HDR category and FPS group in settings.xml (verified by scan).
AUDIO_STRING_IDS = {
    'truehd': ('32004', '32005'),
    'eac3': ('32006', '32007'),
    'ac3': ('32008', '32009'),
    'dtshd_hra': ('32010', '32011'),
    'dtshd_ma': ('32012', '32013'),
    'dca': ('32014', '32015'),
    'pcm': ('32061', '32062'),
}

# Per-HDR enable-toggle (label_id, help_id).
HDR_ENABLE_STRING_IDS = {
    'dolbyvision': ('32026', '32027'),
    'hdr10': ('32028', '32029'),
    'hdr10plus': ('32042', '32043'),
    'hlg': ('32030', '32031'),
    'sdr': ('32032', '32033'),
}

# Per-HDR settings category (label_id, help_id).
HDR_CATEGORY_LABELS = {
    'dolbyvision': ('32076', '32088'),
    'hdr10': ('32023', '32084'),
    'hdr10plus': ('32044', '32085'),
    'hlg': ('32025', '32086'),
    'sdr': ('32024', '32087'),
}

# Per-HDR settings group id (the hand-written file numbers groups 1..10,12).
HDR_GROUP_IDS = {
    'dolbyvision': '2',
    'hdr10': '3',
    'hdr10plus': '4',
    'hlg': '5',
    'sdr': '6',
}

# The per-HDR FPS spinner: shared label/help, one option label per bucket.
FPS_SPINNER_STRING_IDS = ('32065', '32078')
FPS_OPTION_LABEL_IDS = {
    23: '32066',
    24: '32067',
    25: '32068',
    29: '32069',
    30: '32070',
    50: '32071',
    59: '32072',
    60: '32073',
}


def setting_key(hdr_type, fps_key, audio_format):
    """The settings.xml id for an offset: `<hdr>_<fps>_<audio>`.

    This format is FROZEN: existing users' stored offsets are keyed by it.
    """
    return f"{hdr_type}_{fps_key}_{audio_format}"


def all_setting_keys():
    """Every valid offset setting id, in settings.xml order (315 total)."""
    keys = []
    for hdr in HDR_TYPES:
        for fps in (FPS_ALL,) + FPS_BUCKETS:
            for audio in AUDIO_FORMATS:
                keys.append(setting_key(hdr, fps, audio))
    return keys
