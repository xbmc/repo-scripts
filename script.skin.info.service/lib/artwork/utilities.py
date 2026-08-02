"""Helper classes and utilities for artwork fetching."""
from __future__ import annotations

from typing import List, Optional

from lib.kodi.settings import KodiSettings
from lib.kodi.utilities import get_preferred_language_code, normalize_language_tag


def compare_art_quality(art_list: List[dict]) -> Optional[dict]:
    """Find highest quality artwork from list based on resolution (width x height)."""
    if not art_list:
        return None

    if len(art_list) == 1:
        return art_list[0]

    def get_pixel_count(art: dict) -> int:
        width = int(art.get('width', 0) or 0)
        height = int(art.get('height', 0) or 0)
        return width * height

    return max(art_list, key=get_pixel_count)


def sort_artwork_by_popularity(art_list: List[dict], art_type: str = '',
                               sort_mode: str = 'popularity',
                               source_pref: str = 'all') -> List[dict]:
    """Sort artwork by quality and popularity. Returns a new list (input not modified).

    sort_mode:
    - 'popularity' (default): Language > Weighted Popularity > Resolution.
      Uses IMDb Bayesian averaging to balance rating quality vs. vote confidence.
    - 'resolution': Resolution only (highest pixel count first).

    source_pref:
    - 'all' (default): TMDB and Fanart.tv mixed, sorted fairly.
    - 'tmdb': Only TMDB items.
    - 'fanart': Only Fanart.tv items.

    Popularity mode sorting priority:
    - Source tier: Primary sources first (TMDB, Fanart.tv), TheAudioDB last.
    - Source preference (landscape only): Fanart.tv before TMDB.
    - Language preference (if enabled for art type).
    - Weighted popularity:
      * TMDB: Bayesian (m=3, C=2.3): weighted = (votes/(votes+3)) * rating + (3/(votes+3)) * 2.3
        Prevents single-vote ratings from dominating.
      * Fanart.tv: Normalized likes (likes * 0.73) to match TMDB rating range.
    - Resolution (pixel count) as tiebreaker.
    """
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
        width = int(art.get('width', 0) or 0)
        height = int(art.get('height', 0) or 0)
        pixels = width * height

        if sort_mode == 'resolution':
            return (-pixels,)

        m = 3
        C = 2.3

        rating = float(art.get('rating', 0) or 0)
        vote_count = int(art.get('vote_count', 0) or 0)
        likes = int(art.get('likes', '0') or '0')

        if rating > 0 and vote_count >= 0:
            weighted_rating = (vote_count / (vote_count + m)) * rating + (m / (vote_count + m)) * C
            popularity = weighted_rating
        elif likes > 0:
            popularity = likes * 0.73
        else:
            popularity = C if rating > 0 or vote_count == 0 else 0

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

        return (source_priority, lang_match, -popularity, -pixels)

    return sorted(art_list, key=get_sort_key)


def get_available_languages(artwork_list: List[dict]) -> List[str]:
    """Extract unique language codes from artwork list.

    Returned list is sorted, with empty string (text-free) first if present.
    """
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
    """Filter artwork based on art type rules and language preferences.

    Art type filtering rules:
    - AUTO_NO_LANGUAGE_TYPES (fanart, keyart): Only text-free items (unless
      prefer_fanart_language=True).
    - AUTO_LANG_REQUIRED_TYPES (poster, clearlogo, etc.): Preferred language + text-free,
      fallback to all.
    - Other types or explicit language_code: Filter to specified language.

    When language_code is None, uses the preferred language from settings.
    """
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
        return KodiSettings._get_addon().getLocalizedString(32122)

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
    """Parse 0-based index from art slot name ('fanart' -> 0, 'fanart1' -> 1).

    Returns -1 if not a fanart slot.
    """
    if slot_name == 'fanart':
        return 0
    elif slot_name.startswith('fanart'):
        try:
            return int(slot_name[6:])  # Extract number after 'fanart'
        except (ValueError, IndexError):
            return -1
    return -1
