"""Helper utilities for artwork fetching."""
from __future__ import annotations

import math
from typing import List, Optional

from lib.kodi.client import ADDON
from lib.kodi.settings import KodiSettings
from lib.kodi.utilities import get_preferred_language_code, normalize_language_tag


def compare_art_quality(art_list: List[dict]) -> Optional[dict]:
    """Pick the highest-resolution artwork from a list; None when the list is empty."""
    if not art_list:
        return None

    if len(art_list) == 1:
        return art_list[0]

    def get_pixel_count(art: dict) -> int:
        """Area in pixels, zero when either dimension is missing."""
        width = int(art.get('width', 0) or 0)
        height = int(art.get('height', 0) or 0)
        return width * height

    return max(art_list, key=get_pixel_count)


def sort_artwork_by_popularity(art_list: List[dict], art_type: str = '',
                               sort_mode: str = 'popularity',
                               source_pref: str = 'all') -> List[dict]:
    """Sort a copy by source, language, fanart.tv likes or TMDB's own order, then resolution."""
    if not art_list or len(art_list) <= 1:
        return art_list

    if source_pref == 'tmdb':
        art_list = [art for art in art_list if art.get('source', '').lower() == 'tmdb']
    elif source_pref == 'fanart':
        art_list = [
            art for art in art_list if art.get('source', '').lower() in ('fanart.tv', 'fanarttv')
        ]

    if not art_list:
        return art_list

    preferred_lang = get_preferred_language_code()
    try:
        prefer_fanart_language = KodiSettings.prefer_fanart_language()
    except Exception:
        prefer_fanart_language = False

    use_language_preference = True
    if art_type == 'fanart' and not prefer_fanart_language:
        use_language_preference = False

    def get_sort_key(art: dict) -> tuple:
        """Sort tuple for the chosen mode; every field is negated to sort descending."""
        width = int(art.get('width', 0) or 0)
        height = int(art.get('height', 0) or 0)
        pixels = width * height

        if sort_mode == 'resolution':
            return (-pixels,)

        # likes scaled onto TMDB's rating range; TMDB images share one baseline
        likes = int(art.get('likes', '0') or '0')
        popularity = likes * 0.73 if likes > 0 else 2.3

        if use_language_preference:
            language = normalize_language_tag(art.get('language'))
            if language == preferred_lang:
                lang_match = 0
            elif language == '':
                lang_match = 1
            else:
                lang_match = 2
        else:
            lang_match = 0

        source = art.get('source', '').lower()

        if source == 'theaudiodb':
            source_priority = 2
        elif art_type == 'landscape' and source == 'tmdb':
            source_priority = 1
        else:
            source_priority = 0

        return (source_priority, lang_match, -popularity, art.get('rank', math.inf), -pixels)

    return sorted(art_list, key=get_sort_key)


def get_available_languages(artwork_list: List[dict]) -> List[str]:
    """Unique language codes, sorted, with text-free first."""
    if not artwork_list:
        return []

    languages = set()
    for art in artwork_list:
        lang = normalize_language_tag(art.get('language'))
        languages.add(lang)

    result = sorted(languages)

    if '' in result:
        result.remove('')
        result.insert(0, '')

    return result


def filter_artwork_by_language(
    artwork_list: List[dict],
    art_type: Optional[str] = None,
    language_code: Optional[str] = None,
    include_no_language: bool = True
) -> List[dict]:
    """Keep art matching the wanted language; fanart and keyart take text-free only."""
    if not artwork_list:
        return []

    from lib.artwork.config import AUTO_LANG_REQUIRED_TYPES, AUTO_NO_LANGUAGE_TYPES

    try:
        prefer_fanart_language = KodiSettings.prefer_fanart_language()
    except Exception:
        prefer_fanart_language = False

    if art_type == 'fanart' and prefer_fanart_language:
        pass
    elif art_type in AUTO_NO_LANGUAGE_TYPES:
        return [art for art in artwork_list if not normalize_language_tag(art.get('language'))]

    if language_code is None:
        language_code = get_preferred_language_code()

    filter_code = normalize_language_tag(language_code)

    if art_type in AUTO_LANG_REQUIRED_TYPES and filter_code:
        filtered = []
        for art in artwork_list:
            art_lang = normalize_language_tag(art.get('language'))
            if art_lang == filter_code:
                filtered.append(art)
        return filtered if filtered else artwork_list

    if art_type == 'fanart' and prefer_fanart_language and filter_code:
        filtered = []
        for art in artwork_list:
            art_lang = normalize_language_tag(art.get('language'))
            if art_lang == filter_code or art_lang == '':
                filtered.append(art)
        return filtered if filtered else artwork_list

    filtered = []
    for art in artwork_list:
        art_lang = normalize_language_tag(art.get('language'))
        if art_lang == filter_code:
            filtered.append(art)
        elif include_no_language and art_lang == '':
            filtered.append(art)

    return filtered


def get_language_display_name(language_code: str) -> str:
    """Human-readable name for ISO 639-1 code; empty returns localized 'Text-free / Untagged'."""
    if not language_code or language_code == '':
        return ADDON.getLocalizedString(32122)

    language_names = {
        'en': 'English',
        'es': 'Spanish',
        'fr': 'French',
        'de': 'German',
        'it': 'Italian',
        'pt': 'Portuguese',
        'ru': 'Russian',
        'ja': 'Japanese',
        'ko': 'Korean',
        'zh': 'Chinese',
        'ar': 'Arabic',
        'hi': 'Hindi',
        'nl': 'Dutch',
        'sv': 'Swedish',
        'no': 'Norwegian',
        'da': 'Danish',
        'fi': 'Finnish',
        'pl': 'Polish',
        'tr': 'Turkish',
        'el': 'Greek',
        'he': 'Hebrew',
        'th': 'Thai',
        'cs': 'Czech',
        'hu': 'Hungarian',
        'ro': 'Romanian',
        'uk': 'Ukrainian',
        'id': 'Indonesian',
        'vi': 'Vietnamese',
        'ca': 'Catalan',
        'hr': 'Croatian',
        'sr': 'Serbian',
        'sk': 'Slovak',
        'bg': 'Bulgarian',
        'lt': 'Lithuanian',
        'lv': 'Latvian',
        'et': 'Estonian',
        'sl': 'Slovenian',
        'ms': 'Malay',
        'fa': 'Persian',
        'ka': 'Georgian',
        'mo': 'Moldavian',
        'la': 'Latin',
        'mn': 'Mongolian',
        'uz': 'Uzbek',
        'ht': 'Haitian Creole',
        'mk': 'Macedonian',
        'yi': 'Yiddish',
        'te': 'Telugu',
    }

    return language_names.get(language_code, language_code.upper())


def parse_art_slot_index(slot_name: str) -> int:
    """0-based slot index ('fanart' is 0, 'fanart1' is 1), or -1 if not a fanart slot."""
    if slot_name == 'fanart':
        return 0
    elif slot_name.startswith('fanart'):
        try:
            return int(slot_name[6:])
        except (ValueError, IndexError):
            return -1
    return -1


FEED_FOR_MEDIA = {
    'movie': 'movies',
    'set': 'movies',
    'tvshow': 'tv',
    'season': 'tv',
    'episode': 'tv',
    'artist': 'music',
    'album': 'music',
    'musicvideo': 'music',
}


def _feed_item_ids(entries: List[dict]) -> set:
    """Ids from a fanart.tv latest response; movies carry both tmdb and imdb."""
    ids = set()
    for entry in entries:
        for key in ('id', 'tmdb_id', 'imdb_id'):
            value = entry.get(key)
            if value:
                ids.add(str(value))
    return ids


def sync_feed_changes(fanart_api, feeds: List[str]) -> dict:
    """Queue rechecks for items each fanart.tv feed reports changed since its checkpoint."""
    import time

    from lib.data.database import cache as db_cache
    from lib.data.database.mapping import get_tmdb_ids_by_tvdb
    from lib.kodi.client import log
    import xbmc

    delay_hours = db_cache.get_fanarttv_cache_ttl_hours()
    now = int(time.time())
    outcome = {}

    for feed in feeds:
        since = db_cache.get_feed_checkpoint(feed)
        if not since:
            db_cache.set_feed_checkpoint(feed, now)
            outcome[feed] = 'synced'
            continue

        entries = fanart_api.get_latest(feed, since)
        if entries is None:
            outcome[feed] = 'unavailable'
            continue

        item_ids = sorted(_feed_item_ids(entries))
        db_cache.add_rechecks(feed, item_ids, now + delay_hours * 3600)
        db_cache.set_feed_checkpoint(feed, now)
        outcome[feed] = 'synced'
        log("Artwork", f"Feed '{feed}': {len(item_ids)} changed since last scan", xbmc.LOGDEBUG)

    for feed in feeds:
        due = db_cache.take_due_rechecks(feed, now)
        if due:
            ids = list(due)
            if feed == 'tv':
                # a show's completion marker is keyed by its TMDB id, the feed sends TVDB ids
                ids += get_tmdb_ids_by_tvdb(due, 'tvshow')
            cleared = db_cache.clear_artwork_for_ids(ids)
            log("Artwork", f"Feed '{feed}': cleared {cleared} cached rows for {len(due)} items",
                xbmc.LOGDEBUG)

    return outcome
