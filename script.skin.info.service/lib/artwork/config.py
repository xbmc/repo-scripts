"""Art types per media type, session-stats shape, and the constants the artwork package shares."""
from __future__ import annotations

import json
from typing import Any, List, Final

import xbmc


# each scope's name as a Kodi core string
REVIEW_SCOPE_OPTIONS = [
    ('movies', 342),
    ('tvshows', 20343),
    ('musicvideos', 20389),
    ('music', 2),
    ('all', 593),
]

REVIEW_MEDIA_FILTERS = {
    'movies': ['movie'],
    'tvshows': ['tvshow', 'season', 'episode'],
    'musicvideos': ['musicvideo'],
    'music': ['artist', 'album'],
}

REVIEW_MODE_MISSING: Final = 'missing_only'


def scope_label(scope: str) -> str:
    """Get a review scope's name in Kodi's language, the raw scope when it is unknown."""
    for option, label_id in REVIEW_SCOPE_OPTIONS:
        if option == scope:
            return xbmc.getLocalizedString(label_id)
    return scope


def scope_media_types(scope: str) -> List[str]:
    """Media types a review scope covers, every one of them for 'all'."""
    if scope == 'all':
        return [media_type for types in REVIEW_MEDIA_FILTERS.values() for media_type in types]
    return list(REVIEW_MEDIA_FILTERS.get(scope, []))


# art types each media type can receive from the providers
ART_TYPES_BY_MEDIA = {
    'movie': ['poster', 'fanart', 'clearlogo', 'clearart', 'banner', 'landscape', 'discart',
              'keyart'],
    'set': ['poster', 'fanart', 'clearlogo', 'clearart', 'banner', 'landscape', 'discart',
            'keyart'],
    'tvshow': ['poster', 'fanart', 'clearlogo', 'clearart', 'banner', 'landscape', 'characterart',
               'keyart'],
    'season': ['poster', 'fanart', 'banner', 'landscape', 'keyart'],
    'episode': ['thumb'],
    'musicvideo': ['thumb', 'fanart'],
    'artist': ['thumb', 'fanart', 'clearlogo', 'clearart', 'banner', 'landscape', 'cutout'],
    'album': ['thumb', 'discart', 'back', 'spine', '3dcase', '3dflat', '3dface', '3dthumb'],
}

# kept out of bulk paths; TheAudioDB's rate limit can't carry a library pass
AUDIODB_ONLY_ART_TYPES = {
    'artist': ('clearart', 'landscape', 'cutout'),
    'album': ('back', 'spine', '3dcase', '3dflat', '3dface', '3dthumb'),
}

# the show's fanart is the only source, and Kodi already falls back to it
MANUAL_ONLY_ART_TYPES = {
    'season': ('fanart',),
}


def bulk_art_types(media_type: str) -> list:
    """Art types a scan or auto-apply can fill, minus the TheAudioDB-only and manual-only ones."""
    excluded = (AUDIODB_ONLY_ART_TYPES.get(media_type, ())
                + MANUAL_ONLY_ART_TYPES.get(media_type, ()))
    return [art_type for art_type in ART_TYPES_BY_MEDIA.get(media_type, [])
            if art_type not in excluded]


def inherited_art_url(media_type: str, art_type: str, art: dict) -> str:
    """Parent art Kodi shows in an empty slot; only a season's fanart inherits, from its show."""
    if media_type == 'season' and art_type == 'fanart':
        return art.get('tvshow.fanart') or ''
    return ''


FANART_DIMENSIONS_VARIANTS = {
    'fanart': [(1920, 1080), (1280, 720), (3840, 2160)],
    'poster': [(1000, 1500), (2000, 3000), (680, 1000)],
    'characterart': [(512, 512), (1000, 1000), (256, 256)],
    'clearlogo': [(800, 310), (400, 155), (1600, 620)],
    'clearart': [(1000, 562), (500, 281), (1500, 843)],
    'banner': [(1000, 185), (758, 140), (1500, 277)],
    'landscape': [(1920, 1080), (1280, 720), (500, 281)],
    'keyart': [(1000, 1500), (2000, 3000), (680, 1000)],
    'discart': [(1000, 1000), (512, 512), (2000, 2000)],
}

AUTO_LANG_REQUIRED_TYPES = {
    'poster',
    'clearlogo',
    'clearart',
    'banner',
    'characterart',
    'discart',
    'landscape',
}

AUTO_NO_LANGUAGE_TYPES = {
    'fanart',
    'keyart',
}

CACHE_ART_TYPES = [
    'poster',
    'fanart',
    'clearlogo',
    'clearart',
    'banner',
    'landscape',
    'keyart',
    'characterart',
    'discart',
]

SESSION_DETAIL_KEYS = (
    'manual_applied',
    'manual_skipped',
    'manual_auto',
    'stale',
)


def default_session_stats() -> dict:
    """Default session statistics: zeroed counters and empty detail lists."""
    return {
        'applied': 0,
        'skipped': 0,
        'auto': 0,
        'remaining': 0,
        'details': {key: [] for key in SESSION_DETAIL_KEYS},
        'review_mode': REVIEW_MODE_MISSING,
    }


def load_session_stats(raw: Any) -> dict:
    """Load session statistics from a dict, a JSON string or nothing, filling in what is absent."""
    stats = default_session_stats()

    if raw:
        source = raw
        if isinstance(raw, str):
            try:
                source = json.loads(raw)
            except Exception:
                source = {}
        if isinstance(source, dict):
            for key in ('applied', 'skipped', 'auto', 'remaining'):
                value = source.get(key)
                if isinstance(value, (int, float)):
                    stats[key] = int(value)

            details = source.get('details')
            if isinstance(details, dict):
                for key in SESSION_DETAIL_KEYS:
                    entries = details.get(key, [])
                    if isinstance(entries, list):
                        stats['details'][key] = [
                            dict(entry) for entry in entries if isinstance(entry, dict)
                        ]

            stats['review_mode'] = REVIEW_MODE_MISSING

    return stats
