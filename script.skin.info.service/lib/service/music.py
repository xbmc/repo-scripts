"""Unified music artist resolution and online data fetching.

Provides a single resolution chain for MusicBrainz artist IDs from any entry point
(audio playback, music video playback, music video focus). Fetches artist bio, fanart,
and artwork URLs from AudioDB and Fanart.tv, with persistent caching in music_metadata.db.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Tuple

import xbmc

from lib.data.database.music import (
    SOURCE_AUDIODB,
    SOURCE_LASTFM,
    SOURCE_WIKIPEDIA,
    audiodb_text_field,
    cache_album,
    cache_artist,
    cache_track,
    get_best_artist_bio,
    get_cached_album,
    get_cached_artist,
    get_cached_track,
)
from lib.kodi.client import log
from lib.kodi.formatters import format_number
from lib.kodi.settings import KodiSettings
from lib.kodi.utilities import MULTI_VALUE_SEP


def resolve_artist_mbids(artist_name: str, *, mbids: Optional[List[str]] = None,
                         album: Optional[str] = None, track: Optional[str] = None,
                         abort_flag=None) -> Tuple[List[str], Optional[dict]]:
    """Resolve MusicBrainz artist IDs via MBID direct -> album -> track -> name search.

    Returns `(mbids, audiodb_artist_data)`. The dict is populated only when the
    name-search branch is taken (avoids a later refetch).
    """
    if mbids:
        return mbids, None

    primary_name = artist_name.split(MULTI_VALUE_SEP)[0].strip()
    if not primary_name:
        return [], None

    from lib.data.api.audiodb import ApiAudioDb
    audiodb = ApiAudioDb()

    if album:
        if abort_flag and abort_flag.is_requested():
            return [], None
        try:
            result = audiodb.search_album(primary_name, album, abort_flag)
            if result:
                mbid = result.get('strMusicBrainzArtistID', '')
                if mbid:
                    return [mbid], None
        except Exception as e:
            log("Service", f"AudioDB album search error: {e}", xbmc.LOGDEBUG)

    if track:
        if abort_flag and abort_flag.is_requested():
            return [], None
        try:
            result = audiodb.search_track(primary_name, track, abort_flag)
            if result:
                mbid = result.get('strMusicBrainzArtistID', '')
                if mbid:
                    return [mbid], None
        except Exception as e:
            log("Service", f"AudioDB track search error: {e}", xbmc.LOGDEBUG)

    if abort_flag and abort_flag.is_requested():
        return [], None
    try:
        artist_data = audiodb.search_artist(primary_name, abort_flag)
        if artist_data:
            mbid = artist_data.get('strMusicBrainzID', '')
            if mbid:
                return [mbid], artist_data
    except Exception as e:
        log("Service", f"AudioDB artist search error: {e}", xbmc.LOGDEBUG)

    return [], None


def read_cached_fanart(mbids: List[str]) -> List[str]:
    """Read cached fanart URLs for artist MBIDs.

    Prefers Fanart.tv over AudioDB. Returns deduplicated URL list.
    """
    from lib.data.database import cache as db_cache

    seen: set = set()
    urls: List[str] = []

    for mbid in mbids:
        cached = db_cache.get_cached_artwork('artist', mbid, 'fanarttv', 'fanart')
        if cached:
            for art in cached:
                url = art.get('url', '')
                if url and url not in seen:
                    seen.add(url)
                    urls.append(url)

    if urls:
        return urls

    for mbid in mbids:
        cached = db_cache.get_cached_artwork('artist', mbid, 'theaudiodb', 'fanart')
        if cached:
            for art in cached:
                url = art.get('url', '')
                if url and url not in seen:
                    seen.add(url)
                    urls.append(url)

    return urls


def read_cached_artist_art(mbids: List[str]) -> Dict[str, str]:
    """Read cached thumb/clearlogo/banner URLs for artist MBIDs.

    Prefers Fanart.tv over AudioDB for each type.
    """
    from lib.data.database import cache as db_cache

    result: Dict[str, str] = {}

    for art_type in ('thumb', 'clearlogo', 'banner'):
        for mbid in mbids:
            for source in ('fanarttv', 'theaudiodb'):
                cached = db_cache.get_cached_artwork('artist', mbid, source, art_type)
                if cached:
                    url = cached[0].get('url', '')
                    if url:
                        result[art_type] = url
                        break
            if art_type in result:
                break

    return result


def fetch_and_cache_artist_artwork(
    mbids: List[str],
    abort_flag,
    cached_artist_data: Optional[dict] = None,
) -> Optional[dict]:
    """Fetch and cache artist artwork from Fanart.tv and AudioDB.

    Uses music metadata DB cache to avoid redundant AudioDB API calls.
    Returns AudioDB artist data dict if available (for bio extraction).
    """
    from lib.data.api.fanarttv import ApiFanarttv
    from lib.data.api.audiodb import ApiAudioDb
    from lib.data.database import cache as db_cache

    ttl_hours = db_cache.get_fanarttv_cache_ttl_hours()
    fanart_api = ApiFanarttv()
    audiodb = ApiAudioDb()
    artist_data = cached_artist_data

    for mbid in mbids:
        if abort_flag and abort_flag.is_requested():
            return artist_data

        marker = db_cache.get_cached_artwork(
            'artist', mbid, 'system', '_full_fetch_complete'
        )
        if marker is not None:
            continue

        try:
            fanart_art = fanart_api.get_artist_artwork(mbid, abort_flag)
            for art_type, artworks in fanart_art.items():
                if art_type != 'albums' and artworks:
                    db_cache.cache_artwork(
                        'artist', mbid, 'fanarttv', art_type, artworks, None, ttl_hours
                    )
        except Exception as e:
            log("Service", f"Fanart.tv artist fetch error for {mbid}: {e}", xbmc.LOGWARNING)

        try:
            # Check music DB first to avoid redundant AudioDB call
            tadb_artist = get_cached_artist(SOURCE_AUDIODB, mbid=mbid)
            if not tadb_artist:
                tadb_artist = audiodb.get_artist(mbid, abort_flag)
                if tadb_artist:
                    tadb_name = tadb_artist.get('strArtist', '')
                    cache_artist(SOURCE_AUDIODB, tadb_artist, mbid=mbid, name=tadb_name)

            if tadb_artist:
                if not artist_data:
                    artist_data = tadb_artist
                tadb_art = audiodb.get_artist_artwork_from_data(tadb_artist)
                for art_type, artworks in tadb_art.items():
                    if artworks:
                        db_cache.cache_artwork(
                            'artist', mbid, 'theaudiodb', art_type, artworks, None, ttl_hours
                        )
        except Exception as e:
            log("Service", f"TheAudioDB artist fetch error for {mbid}: {e}", xbmc.LOGWARNING)

        db_cache.cache_artwork(
            'artist', mbid, 'system', '_full_fetch_complete',
            [{'marker': 'complete'}], None, ttl_hours
        )

    return artist_data


class MusicOnlineResult:
    """Result container for fetch_artist_online_data."""
    __slots__ = ('bio', 'fanart_urls', 'artist_art')

    def __init__(
        self,
        bio: str,
        fanart_urls: List[str],
        artist_art: Dict[str, str],
    ):
        self.bio = bio
        self.fanart_urls = fanart_urls
        self.artist_art = artist_art


def _fetch_and_cache_artist_metadata(
    mbid: str,
    name: str,
    *,
    abort_flag=None,
) -> str:
    """Parallel fetch AudioDB + Last.fm artist data, cache both.

    Returns best available bio string.
    """
    from lib.data.api.audiodb import ApiAudioDb
    from lib.data.api.lastfm import ApiLastfm

    lang = KodiSettings.online_metadata_language()
    def _fetch_audiodb() -> Optional[dict]:
        if not mbid:
            return None
        try:
            return ApiAudioDb().get_artist(mbid, abort_flag)
        except Exception as e:
            log("Service", f"AudioDB artist metadata fetch error: {e}", xbmc.LOGDEBUG)
            return None

    def _fetch_lastfm() -> Optional[dict]:
        try:
            return ApiLastfm().get_artist_info(name, mbid=mbid or None, lang=lang,
                                               abort_flag=abort_flag)
        except Exception as e:
            log("Service", f"Last.fm artist metadata fetch error: {e}", xbmc.LOGDEBUG)
            return None

    with ThreadPoolExecutor(max_workers=2) as executor:
        audiodb_future = executor.submit(_fetch_audiodb)
        lastfm_future = executor.submit(_fetch_lastfm)
        audiodb_data = audiodb_future.result()
        lastfm_data = lastfm_future.result()

    if audiodb_data:
        cache_artist(SOURCE_AUDIODB, audiodb_data, mbid=mbid, name=name)
    else:
        cache_artist(SOURCE_AUDIODB, {}, mbid=mbid, name=name)

    if lastfm_data:
        cache_artist(SOURCE_LASTFM, lastfm_data, mbid=mbid, name=name,
                      audiodb_artist=audiodb_data, lang=lang)
    else:
        cache_artist(SOURCE_LASTFM, {}, mbid=mbid, name=name, lang=lang)

    return get_best_artist_bio(mbid=mbid, name=name)


def fetch_artist_online_data(
    artist_name: str,
    *,
    mbids: Optional[List[str]] = None,
    album: Optional[str] = None,
    track: Optional[str] = None,
    abort_flag=None,
) -> Optional[MusicOnlineResult]:
    """Top-level function: resolve MBIDs, fetch artwork + bio.

    Returns MusicOnlineResult or None on abort/failure.
    """
    resolved_mbids, artist_data = resolve_artist_mbids(
        artist_name, mbids=mbids, album=album, track=track, abort_flag=abort_flag
    )

    if abort_flag and abort_flag.is_requested():
        return None

    if not resolved_mbids:
        return None

    primary_mbid = resolved_mbids[0]
    primary_name = artist_name.split(MULTI_VALUE_SEP)[0].strip()

    # Cache AudioDB artist data from resolution if we got it
    if artist_data:
        cache_artist(SOURCE_AUDIODB, artist_data, mbid=primary_mbid, name=primary_name)
    else:
        # Ensure name index exists for previously MBID-only cached entries
        existing = get_cached_artist(SOURCE_AUDIODB, mbid=primary_mbid)
        if existing:
            cache_artist(SOURCE_AUDIODB, existing, mbid=primary_mbid, name=primary_name)

    fanart_urls = read_cached_fanart(resolved_mbids)

    if not fanart_urls:
        artist_data = fetch_and_cache_artist_artwork(
            resolved_mbids, abort_flag, artist_data
        )
        if abort_flag and abort_flag.is_requested():
            return None
        fanart_urls = read_cached_fanart(resolved_mbids)

    # Try cached bio first, fetch if missing
    bio = get_best_artist_bio(mbid=primary_mbid, name=primary_name)
    if not bio:
        bio = _fetch_and_cache_artist_metadata(
            primary_mbid, primary_name, abort_flag=abort_flag
        )

    artist_art = read_cached_artist_art(resolved_mbids)

    return MusicOnlineResult(bio=bio, fanart_urls=fanart_urls, artist_art=artist_art)


def fetch_track_online_data(
    artist: str,
    track: str,
    *,
    abort_flag=None,
) -> Optional[dict]:
    """Fetch and cache track metadata from Last.fm, Wikipedia, and AudioDB."""
    if not artist or not track:
        return None

    lang = KodiSettings.online_metadata_language()
    cached_lastfm = get_cached_track(SOURCE_LASTFM, artist, track, lang=lang)
    cached_wiki = get_cached_track(SOURCE_WIKIPEDIA, artist, track, lang=lang)
    cached_audiodb = get_cached_track(SOURCE_AUDIODB, artist, track)
    if (cached_lastfm is not None and cached_wiki is not None
            and cached_audiodb is not None):
        return cached_lastfm or cached_wiki or cached_audiodb or None

    from lib.data.api.lastfm import ApiLastfm
    from lib.data.api.audiodb import ApiAudioDb
    from lib.data.api.wikipedia import ApiWikipedia

    def _fetch_lastfm() -> Optional[dict]:
        if cached_lastfm is not None:
            return None
        try:
            return ApiLastfm().get_track_info(artist, track, lang=lang, abort_flag=abort_flag)
        except Exception as e:
            log("Service", f"Last.fm track fetch error: {e}", xbmc.LOGDEBUG)
            return None

    def _fetch_wikipedia() -> Optional[dict]:
        if cached_wiki is not None:
            return None
        try:
            summary = ApiWikipedia().get_track_summary(artist, track, lang=lang,
                                                       abort_flag=abort_flag)
            return {'summary': summary} if summary else None
        except Exception as e:
            log("Service", f"Wikipedia track fetch error: {e}", xbmc.LOGDEBUG)
            return None

    def _fetch_audiodb() -> Optional[dict]:
        if cached_audiodb is not None:
            return None
        try:
            return ApiAudioDb().search_track(artist, track, abort_flag)
        except Exception as e:
            log("Service", f"AudioDB track fetch error: {e}", xbmc.LOGDEBUG)
            return None

    with ThreadPoolExecutor(max_workers=3) as executor:
        lastfm_future = executor.submit(_fetch_lastfm)
        wiki_future = executor.submit(_fetch_wikipedia)
        audiodb_future = executor.submit(_fetch_audiodb)
        lastfm_data = lastfm_future.result()
        wiki_data = wiki_future.result()
        audiodb_data = audiodb_future.result()

    if cached_lastfm is None:
        cache_track(SOURCE_LASTFM, lastfm_data or {}, artist, track, lang=lang)
    if cached_wiki is None:
        cache_track(SOURCE_WIKIPEDIA, wiki_data or {}, artist, track, lang=lang)
    if cached_audiodb is None:
        cache_track(SOURCE_AUDIODB, audiodb_data or {}, artist, track)

    return (cached_lastfm or lastfm_data
            or cached_wiki or wiki_data
            or cached_audiodb or audiodb_data
            or None)


def fetch_album_online_data(
    artist: str,
    album: str,
    *,
    mbid: str = '',
    abort_flag=None,
) -> Optional[dict]:
    """Fetch and cache album metadata from Last.fm, Wikipedia, and AudioDB."""
    if not artist or not album:
        return None

    lang = KodiSettings.online_metadata_language()
    cached_lastfm = get_cached_album(SOURCE_LASTFM, artist=artist, album=album, mbid=mbid,
                                      lang=lang)
    cached_wiki = get_cached_album(SOURCE_WIKIPEDIA, artist=artist, album=album, lang=lang)
    cached_audiodb = get_cached_album(SOURCE_AUDIODB, artist=artist, album=album, mbid=mbid)
    if (cached_lastfm is not None and cached_wiki is not None
            and cached_audiodb is not None):
        return cached_lastfm or cached_wiki or cached_audiodb or None

    from lib.data.api.lastfm import ApiLastfm
    from lib.data.api.audiodb import ApiAudioDb
    from lib.data.api.wikipedia import ApiWikipedia

    def _fetch_lastfm() -> Optional[dict]:
        if cached_lastfm is not None:
            return None
        try:
            return ApiLastfm().get_album_info(artist, album, lang=lang, abort_flag=abort_flag)
        except Exception as e:
            log("Service", f"Last.fm album fetch error: {e}", xbmc.LOGDEBUG)
            return None

    def _fetch_wikipedia() -> Optional[dict]:
        if cached_wiki is not None:
            return None
        try:
            summary = ApiWikipedia().get_album_summary(artist, album, lang=lang,
                                                       abort_flag=abort_flag)
            return {'summary': summary} if summary else None
        except Exception as e:
            log("Service", f"Wikipedia album fetch error: {e}", xbmc.LOGDEBUG)
            return None

    def _fetch_audiodb() -> Optional[dict]:
        if cached_audiodb is not None:
            return None
        try:
            api = ApiAudioDb()
            return (api.get_album(mbid, abort_flag) if mbid
                    else api.search_album(artist, album, abort_flag))
        except Exception as e:
            log("Service", f"AudioDB album fetch error: {e}", xbmc.LOGDEBUG)
            return None

    with ThreadPoolExecutor(max_workers=3) as executor:
        lastfm_future = executor.submit(_fetch_lastfm)
        wiki_future = executor.submit(_fetch_wikipedia)
        audiodb_future = executor.submit(_fetch_audiodb)
        lastfm_data = lastfm_future.result()
        wiki_data = wiki_future.result()
        audiodb_data = audiodb_future.result()

    if cached_lastfm is None:
        cache_album(SOURCE_LASTFM, lastfm_data or {}, artist=artist, album=album,
                     mbid=mbid, lang=lang)
    if cached_wiki is None:
        cache_album(SOURCE_WIKIPEDIA, wiki_data or {}, artist=artist, album=album,
                     lang=lang)
    if cached_audiodb is None:
        cache_album(SOURCE_AUDIODB, audiodb_data or {}, artist=artist, album=album, mbid=mbid)

    return (cached_lastfm or lastfm_data
            or cached_wiki or wiki_data
            or cached_audiodb or audiodb_data
            or None)


def _extract_wiki(data: Optional[dict]) -> str:
    """Extract wiki/bio text from a Last.fm response, stripping the HTML suffix."""
    if not isinstance(data, dict):
        return ''
    wiki = data.get('wiki') or data.get('bio')
    if not isinstance(wiki, dict):
        return ''
    content = wiki.get('content') or wiki.get('summary') or ''
    if not content:
        return ''
    href_idx = content.find('<a href=')
    if href_idx > 0:
        content = content[:href_idx].rstrip()
    return content


def _extract_tags(data: Optional[dict]) -> str:
    """Extract top tags from a Last.fm response as MULTI_VALUE_SEP joined string."""
    if not isinstance(data, dict):
        return ''
    container = data.get('toptags') or data.get('tags')
    if not isinstance(container, dict):
        return ''
    tags = container.get('tag')
    if not isinstance(tags, list):
        return ''
    names = [t['name'] for t in tags if isinstance(t, dict) and t.get('name')]
    return MULTI_VALUE_SEP.join(names[:10])


def extract_track_properties(artist: str, track: str) -> Dict[str, str]:
    """Extract displayable properties from cached track data."""
    props: Dict[str, str] = {}

    lang = KodiSettings.online_metadata_language()
    lastfm = get_cached_track(SOURCE_LASTFM, artist, track, lang=lang)
    audiodb = get_cached_track(SOURCE_AUDIODB, artist, track)

    wiki = _extract_wiki(lastfm)
    if not wiki:
        wikipedia = get_cached_track(SOURCE_WIKIPEDIA, artist, track, lang=lang)
        if isinstance(wikipedia, dict):
            wiki = wikipedia.get('summary') or ''
    if not wiki and isinstance(audiodb, dict):
        field = audiodb_text_field('strDescription')
        wiki = audiodb.get(field) or ''
        if not wiki and field != 'strDescriptionEN':
            wiki = audiodb.get('strDescriptionEN') or ''
    if wiki:
        props['Wiki'] = wiki

    tags = _extract_tags(lastfm)
    if tags:
        props['Tags'] = tags

    if isinstance(lastfm, dict):
        listeners = lastfm.get('listeners')
        if listeners:
            props['Listeners'] = format_number(listeners)
        playcount = lastfm.get('playcount')
        if playcount:
            props['Playcount'] = format_number(playcount)

    return props


def get_similar_artist_names(artist_name: str) -> List[str]:
    """Extract similar artist names from cached Last.fm data.

    Falls back to inline API fetch if not cached.
    """
    primary_name = artist_name.split(MULTI_VALUE_SEP)[0].strip()
    if not primary_name:
        return []

    lang = KodiSettings.online_metadata_language()
    cached = get_cached_artist(SOURCE_LASTFM, name=primary_name, lang=lang)
    if cached is None:
        from lib.data.api.lastfm import ApiLastfm
        api = ApiLastfm()
        data = api.get_artist_info(primary_name, lang=lang)
        if data:
            cache_artist(SOURCE_LASTFM, data, name=primary_name, lang=lang)
            cached = data
        else:
            cache_artist(SOURCE_LASTFM, {}, name=primary_name, lang=lang)
            return []

    if not isinstance(cached, dict):
        return []

    similar = cached.get('similar')
    if not isinstance(similar, dict):
        return []

    artists = similar.get('artist')
    if not isinstance(artists, list):
        return []

    return [a['name'] for a in artists if isinstance(a, dict) and a.get('name')]


def extract_album_properties(artist: str, album: str, *, mbid: str = '') -> Dict[str, str]:
    """Extract displayable properties from cached album data."""
    props: Dict[str, str] = {}

    lang = KodiSettings.online_metadata_language()
    lastfm = get_cached_album(SOURCE_LASTFM, artist=artist, album=album, mbid=mbid,
                               lang=lang)
    audiodb_data = get_cached_album(SOURCE_AUDIODB, artist=artist, album=album, mbid=mbid)

    wiki = _extract_wiki(lastfm)
    if not wiki:
        wikipedia = get_cached_album(SOURCE_WIKIPEDIA, artist=artist, album=album, lang=lang)
        if isinstance(wikipedia, dict):
            wiki = wikipedia.get('summary') or ''
    if not wiki and isinstance(audiodb_data, dict):
        field = audiodb_text_field('strDescription')
        wiki = audiodb_data.get(field) or ''
        if not wiki and field != 'strDescriptionEN':
            wiki = audiodb_data.get('strDescriptionEN') or ''
    if wiki:
        props['Wiki'] = wiki

    tags = _extract_tags(lastfm)
    if tags:
        props['Tags'] = tags

    if isinstance(audiodb_data, dict):
        label = audiodb_data.get('strLabel') or ''
        if label:
            props['Label'] = label

    return props


def fill_artist_online_props(
    props: Dict[str, Optional[str]],
    prefix: str,
    result: MusicOnlineResult,
    *,
    name: Optional[str] = None,
) -> None:
    """Fill {prefix}Artist.* from a resolved result; pass name to add .Name."""
    ap = f"{prefix}Artist."
    if name is not None:
        props[f"{ap}Name"] = name
    props[f"{ap}Bio"] = result.bio or ""
    props[f"{ap}FanArt.Count"] = str(len(result.fanart_urls))
    props[f"{ap}FanArt"] = result.fanart_urls[0] if result.fanart_urls else ""
    for art_type in ('thumb', 'clearlogo', 'banner'):
        key = art_type[0].upper() + art_type[1:]
        props[f"{ap}{key}"] = result.artist_art.get(art_type, '')


def fill_track_online_props(
    props: Dict[str, Optional[str]],
    prefix: str,
    artist: str,
    track: str,
    *,
    abort_flag=None,
) -> None:
    """Fetch track data, fill {prefix}Track.*."""
    fetch_track_online_data(artist, track, abort_flag=abort_flag)
    for k, v in extract_track_properties(artist, track).items():
        props[f"{prefix}Track.{k}"] = v


def fill_album_online_props(
    props: Dict[str, Optional[str]],
    prefix: str,
    artist: str,
    album: str,
    *,
    abort_flag=None,
) -> None:
    """Fetch album data, fill {prefix}Album.*."""
    fetch_album_online_data(artist, album, abort_flag=abort_flag)
    for k, v in extract_album_properties(artist, album).items():
        props[f"{prefix}Album.{k}"] = v
