"""External API fetching and caching for artwork.

Centralizes retrieval of artwork from TMDB and fanart.tv APIs.
Handles caching, batch fetching, and dimension normalization.
"""
from __future__ import annotations

import xbmc
from typing import Optional, Dict, List, Any

from lib.data import database as db
from lib.data.api.tmdb import ApiTmdb, transform_tmdb_images
from lib.data.api.fanarttv import ApiFanarttv
from lib.kodi.client import get_item_details, KODI_GET_DETAILS_METHODS
from lib.kodi.client import log
from lib.kodi.utilities import MULTI_VALUE_SEP


def _resolve_musicvideo_artist_mbid(
    artist_name: str,
    album: Optional[str],
    title: Optional[str],
) -> Optional[str]:
    from lib.service.music import resolve_artist_mbids
    mbids, _ = resolve_artist_mbids(artist_name, album=album, track=title)
    return mbids[0] if mbids else None


class ApiArtworkFetcher:
    """Retrieves and caches artwork from TMDB and fanart.tv.

    Caches results with dynamic TTL based on media age. Batch-fetches to
    minimize API calls.
    """

    def __init__(self, tmdb_api: ApiTmdb, fanart_api: ApiFanarttv):
        self.tmdb_api = tmdb_api
        self.fanart_api = fanart_api

    def get_external_ids(self, media_type: str, dbid: int) -> dict:
        """Get external IDs and release date from Kodi library.

        Returns:
            Dict with keys: tmdb_id (int), tvdb_id (int), release_date (str, YYYY-MM-DD).
        """
        if media_type not in KODI_GET_DETAILS_METHODS:
            return {}

        properties = ['uniqueid']

        if media_type in ('movie', 'tvshow'):
            properties.append('premiered')
        elif media_type == 'episode':
            properties.append('firstaired')

        try:
            details = get_item_details(media_type, dbid, properties)
        except Exception as e:
            log("API", f"Error getting external IDs for {media_type}:{dbid}: {e}", xbmc.LOGERROR)
            return {}

        if not isinstance(details, dict):
            return {}

        unique_ids = details.get('uniqueid', {}) or {}
        result: Dict[str, Any] = {}

        tmdb_id = unique_ids.get('tmdb')
        tvdb_id = unique_ids.get('tvdb')

        if tmdb_id:
            try:
                result['tmdb_id'] = int(tmdb_id)
            except (TypeError, ValueError):
                pass
        if tvdb_id:
            try:
                result['tvdb_id'] = int(tvdb_id)
            except (TypeError, ValueError):
                pass

        result['release_date'] = details.get('premiered') or details.get('firstaired')

        return result

    def fetch_all(
        self, media_type: str, dbid: int, season_number: Optional[int] = None,
        episode_number: Optional[int] = None, bypass_cache: bool = False,
    ) -> Dict[str, List[dict]]:
        """Fetch ALL artwork types for an item in a single operation.

        Performance-critical: minimizes API calls by checking cache first
        (with completion marker), fetching all art types from TMDB + fanart.tv
        in one pass, and caching with dynamic TTL (24hr/3day/7day based on age).
        """
        if media_type == 'season':
            return self._fetch_season_artwork(dbid, season_number)
        elif media_type == 'episode':
            return self._fetch_episode_artwork(dbid, season_number, episode_number)
        elif media_type == 'set':
            return self._fetch_movieset_artwork(dbid)
        elif media_type == 'artist':
            return self._fetch_artist_artwork(dbid, bypass_cache=bypass_cache)
        elif media_type == 'album':
            return self._fetch_album_artwork(dbid, bypass_cache=bypass_cache)
        elif media_type == 'musicvideo':
            return self._fetch_musicvideo_artwork(dbid, bypass_cache)
        elif media_type not in ('movie', 'tvshow'):
            return {}

        ids = self.get_external_ids(media_type, dbid)
        tmdb_id = ids.get('tmdb_id')
        tvdb_id = ids.get('tvdb_id')
        release_date = ids.get('release_date')

        if not tmdb_id:
            return {}

        ttl_hours = db.get_cache_ttl_hours(release_date)
        cache_marker_type = '_full_fetch_complete'

        if not bypass_cache:
            cached_marker = db.get_cached_artwork(
                media_type, str(tmdb_id), 'system', cache_marker_type
            )

            if cached_marker is not None:
                cached_art = self._load_cached_artwork(media_type, tmdb_id, tvdb_id)
                return self._finalise_artwork(media_type, cached_art)

        all_art: Dict[str, List[dict]] = {}

        complete_data = self.tmdb_api.get_complete_data(
            media_type, tmdb_id, release_date, force_refresh=bypass_cache
        )

        if complete_data and 'images' in complete_data:
            images = complete_data['images']
            tmdb_art = transform_tmdb_images(images)
            for art_type, artworks in tmdb_art.items():
                all_art.setdefault(art_type, []).extend(artworks)

        fanart_items = self._fetch_fanart_art(media_type, tmdb_id, tvdb_id)
        for art_type, artworks in fanart_items.items():
            if artworks:
                cache_id = str(tvdb_id) if tvdb_id and media_type == 'tvshow' else str(tmdb_id)
                db.cache_artwork(
                    media_type, cache_id, 'fanarttv', art_type, artworks, release_date, ttl_hours
                )
                all_art.setdefault(art_type, []).extend(artworks)

        if tmdb_id:
            db.cache_artwork(
                media_type, str(tmdb_id), 'system', cache_marker_type,
                [{'marker': 'complete'}], release_date, ttl_hours,
            )

        finalised = self._finalise_artwork(media_type, all_art)

        total_items = sum(len(v) for v in finalised.values())
        source_summary = [f"{key}:{len(values)}" for key, values in finalised.items()]
        log(
            "Artwork",
            f"Fetched {media_type}:{dbid} - {total_items} art items "
            f"({', '.join(source_summary)})",
        )

        return finalised

    def _load_cached_artwork(
        self, media_type: str, tmdb_id: int, tvdb_id: Optional[int]
    ) -> Dict[str, List[dict]]:
        cache_id = str(tvdb_id) if tvdb_id and media_type == 'tvshow' else str(tmdb_id)

        media_ids = {
            'tmdb': str(tmdb_id),
            'fanarttv': cache_id
        }

        from lib.artwork.config import CACHE_ART_TYPES
        batch_results = db.get_cached_artwork_batch(media_type, media_ids, CACHE_ART_TYPES)

        cached: Dict[str, List[dict]] = {}
        for (_source, art_type), artworks in batch_results.items():
            cached.setdefault(art_type, []).extend(artworks)

        return cached

    def _load_music_cached_artwork(self, media_type: str, mbid: str) -> Dict[str, List[dict]]:
        music_art_types = ['thumb', 'fanart', 'clearlogo', 'banner', 'discart']
        media_ids = {'fanarttv': mbid, 'theaudiodb': mbid}

        batch_results = db.get_cached_artwork_batch(media_type, media_ids, music_art_types)

        cached: Dict[str, List[dict]] = {}
        for (_source, art_type), artworks in batch_results.items():
            cached.setdefault(art_type, []).extend(artworks)

        return cached

    def _fetch_fanart_art(
        self, media_type: str, tmdb_id: int, tvdb_id: Optional[int]
    ) -> Dict[str, List[dict]]:
        if media_type == 'tvshow' and tvdb_id:
            art = self.fanart_api.get_tv_artwork(tvdb_id)
        else:
            art = self.fanart_api.get_movie_artwork(tmdb_id)
        return art or {}

    def _finalise_artwork(
        self, _media_type: str, artwork: Dict[str, List[dict]]
    ) -> Dict[str, List[dict]]:
        """Finalize artwork: sort each type's list by popularity."""
        if not artwork:
            return {}

        from lib.artwork.utilities import sort_artwork_by_popularity
        for art_type, artworks in artwork.items():
            artwork[art_type] = sort_artwork_by_popularity(artworks, art_type)

        return artwork

    def _fetch_season_artwork(
        self, season_dbid: int, season_number: Optional[int] = None
    ) -> Dict[str, List[dict]]:
        """Fetch artwork for a TV season from TMDB and fanart.tv."""
        details = get_item_details('season', season_dbid, ['season', 'tvshowid'])
        if not isinstance(details, dict):
            return {}

        if season_number is None:
            season_number = details.get('season')

        tvshow_id = details.get('tvshowid')
        if not tvshow_id or season_number is None:
            return {}

        tvshow_ids = self.get_external_ids('tvshow', tvshow_id)
        tmdb_id = tvshow_ids.get('tmdb_id')
        tvdb_id = tvshow_ids.get('tvdb_id')

        if not tmdb_id:
            return {}

        all_art: Dict[str, List[dict]] = {}

        tmdb_art = self.tmdb_api.get_season_images(tmdb_id, season_number)
        for art_type, artworks in tmdb_art.items():
            all_art.setdefault(art_type, []).extend(artworks)

        if tvdb_id:
            fanart_art = self.fanart_api.get_season_artwork(tvdb_id, season_number)
            for art_type, artworks in fanart_art.items():
                all_art.setdefault(art_type, []).extend(artworks)

        return self._finalise_artwork('season', all_art)

    def _fetch_episode_artwork(
        self, episode_dbid: int, season_number: Optional[int] = None,
        episode_number: Optional[int] = None,
    ) -> Dict[str, List[dict]]:
        """Fetch artwork for a TV episode. Season/episode numbers fetched from Kodi if None."""
        details = get_item_details('episode', episode_dbid, ['season', 'episode', 'tvshowid'])
        if not isinstance(details, dict):
            return {}

        if season_number is None:
            season_number = details.get('season')
        if episode_number is None:
            episode_number = details.get('episode')

        tvshow_id = details.get('tvshowid')
        if not tvshow_id or season_number is None or episode_number is None:
            return {}

        tvshow_ids = self.get_external_ids('tvshow', tvshow_id)
        tmdb_id = tvshow_ids.get('tmdb_id')

        if not tmdb_id:
            return {}

        tmdb_art = self.tmdb_api.get_episode_images(tmdb_id, season_number, episode_number)

        return self._finalise_artwork('episode', tmdb_art)

    def _fetch_movieset_artwork(self, set_dbid: int) -> Dict[str, List[dict]]:
        """Fetch artwork for a movie set (collection)."""
        details = get_item_details(
            'set',
            set_dbid,
            ['title'],
            movies={
                'properties': ['uniqueid'],
                'limits': {'end': 1}
            }
        )
        if not isinstance(details, dict):
            return {}

        movies = details.get('movies', [])
        if not movies:
            return {}

        first_movie_ids = movies[0].get('uniqueid', {})
        movie_tmdb_id = first_movie_ids.get('tmdb')

        if not movie_tmdb_id:
            return {}

        try:
            movie_details = self.tmdb_api.get_complete_data('movie', int(movie_tmdb_id))
        except (ValueError, TypeError):
            return {}

        if not movie_details:
            return {}

        belongs_to = movie_details.get('belongs_to_collection')
        if not belongs_to:
            return {}

        collection_id = belongs_to.get('id')
        if not collection_id:
            return {}

        all_art: Dict[str, List[dict]] = {}

        tmdb_art = self.tmdb_api.get_collection_images(collection_id)
        for art_type, artworks in tmdb_art.items():
            if artworks:
                all_art.setdefault(art_type, []).extend(artworks)

        fanart_art = self.fanart_api.get_movie_artwork(collection_id)
        for art_type, artworks in fanart_art.items():
            if artworks:
                all_art.setdefault(art_type, []).extend(artworks)

        return self._finalise_artwork('set', all_art)

    def _fetch_artist_artwork(
        self, artist_dbid: int, bypass_cache: bool = False
    ) -> Dict[str, List[dict]]:
        """Fetch artwork for a music artist from fanart.tv."""
        details = get_item_details('artist', artist_dbid, ['musicbrainzartistid'])
        if not isinstance(details, dict):
            return {}

        mbid = details.get('musicbrainzartistid')
        if not mbid:
            log("Artwork", f"No MusicBrainz ID for artist {artist_dbid}", xbmc.LOGWARNING)
            return {}

        if isinstance(mbid, list):
            mbid = mbid[0] if mbid else None
        if not mbid:
            return {}

        ttl_hours = db.get_fanarttv_cache_ttl_hours()
        cache_marker_type = '_full_fetch_complete'

        if not bypass_cache:
            cached_marker = db.get_cached_artwork('artist', mbid, 'system', cache_marker_type)
            if cached_marker is not None:
                cached_art = self._load_music_cached_artwork('artist', mbid)
                return self._finalise_artwork('artist', cached_art)

        all_art: Dict[str, List[dict]] = {}

        fanart_art = self.fanart_api.get_artist_artwork(mbid)
        for art_type, artworks in fanart_art.items():
            if art_type != 'albums' and artworks:
                db.cache_artwork('artist', mbid, 'fanarttv', art_type, artworks, None, ttl_hours)
                all_art.setdefault(art_type, []).extend(artworks)

        from lib.data.api.audiodb import ApiAudioDb
        audiodb = ApiAudioDb()
        audiodb_art = audiodb.get_artist_artwork(mbid)
        for art_type, artworks in audiodb_art.items():
            if artworks:
                db.cache_artwork('artist', mbid, 'theaudiodb', art_type, artworks, None, ttl_hours)
                all_art.setdefault(art_type, []).extend(artworks)

        db.cache_artwork(
            'artist', mbid, 'system', cache_marker_type,
            [{'marker': 'complete'}], None, ttl_hours,
        )

        return self._finalise_artwork('artist', all_art)

    def _fetch_musicvideo_artwork(
        self, musicvideo_dbid: int, bypass_cache: bool = False
    ) -> Dict[str, List[dict]]:
        """Fetch artwork for a music video.

        Tries track screenshots from AudioDB first, falls back to artist artwork
        from Fanart.tv + AudioDB when no screenshots exist.
        """
        details = get_item_details('musicvideo', musicvideo_dbid, ['artist', 'title', 'album'])
        if not isinstance(details, dict):
            return {}

        artist_list = details.get('artist')
        artist_name = (
            MULTI_VALUE_SEP.join(artist_list)
            if isinstance(artist_list, list)
            else str(artist_list or '')
        )
        title = details.get('title') or ''
        if not artist_name or not title:
            return {}

        cache_key = f"{artist_name}\0{title}".lower()
        ttl_hours = db.get_fanarttv_cache_ttl_hours()

        if not bypass_cache:
            marker = db.get_cached_artwork(
                'musicvideo', cache_key, 'system', '_full_fetch_complete'
            )
            if marker is not None:
                return self._finalise_artwork(
                    'musicvideo', self._load_musicvideo_cached_artwork(cache_key)
                )

        from lib.data.api.audiodb import ApiAudioDb
        audiodb = ApiAudioDb()

        all_art: Dict[str, List[dict]] = {}

        track_data = audiodb.search_track(artist_name, title)
        if track_data:
            track_art = audiodb.get_track_artwork_from_data(track_data)
            for art_type, artworks in track_art.items():
                if artworks:
                    db.cache_artwork(
                        'musicvideo', cache_key, 'theaudiodb', art_type, artworks, None, ttl_hours
                    )
                    all_art.setdefault(art_type, []).extend(artworks)

        album = details.get('album') or None
        mbid = _resolve_musicvideo_artist_mbid(artist_name, album, title)
        if mbid:
            try:
                fanart_art = self.fanart_api.get_artist_artwork(mbid)
                for art_type, artworks in fanart_art.items():
                    if art_type != 'albums' and artworks:
                        db.cache_artwork(
                            'musicvideo', cache_key, 'fanarttv', art_type, artworks, None, ttl_hours
                        )
                        all_art.setdefault(art_type, []).extend(artworks)
            except Exception as e:
                log(
                    "Artwork",
                    f"Fanart.tv artist artwork error for musicvideo {musicvideo_dbid}: {e}",
                    xbmc.LOGWARNING,
                )

            try:
                from lib.data.database.music import get_cached_artist, SOURCE_AUDIODB
                audiodb_artist = get_cached_artist(SOURCE_AUDIODB, mbid=mbid)
                if not audiodb_artist:
                    audiodb_artist = audiodb.get_artist(mbid)
                if audiodb_artist:
                    tadb_art = audiodb.get_artist_artwork_from_data(audiodb_artist)
                    for art_type, artworks in tadb_art.items():
                        if artworks:
                            db.cache_artwork(
                                'musicvideo', cache_key, 'theaudiodb', art_type, artworks,
                                None, ttl_hours,
                            )
                            all_art.setdefault(art_type, []).extend(artworks)
            except Exception as e:
                log(
                    "Artwork",
                    f"AudioDB artist artwork error for musicvideo {musicvideo_dbid}: {e}",
                    xbmc.LOGWARNING,
                )

        db.cache_artwork(
            'musicvideo', cache_key, 'system', '_full_fetch_complete',
            [{'marker': 'complete'}], None, ttl_hours,
        )
        return self._finalise_artwork('musicvideo', all_art)

    def _load_musicvideo_cached_artwork(self, cache_key: str) -> Dict[str, List[dict]]:
        art_types = ['thumb', 'fanart', 'clearlogo', 'banner', 'clearart', 'landscape']
        media_ids = {'fanarttv': cache_key, 'theaudiodb': cache_key}
        batch_results = db.get_cached_artwork_batch('musicvideo', media_ids, art_types)
        cached: Dict[str, List[dict]] = {}
        for (_source, art_type), artworks in batch_results.items():
            cached.setdefault(art_type, []).extend(artworks)
        return cached

    def _fetch_album_artwork(
        self, album_dbid: int, bypass_cache: bool = False
    ) -> Dict[str, List[dict]]:
        """Fetch artwork for a music album from fanart.tv and TheAudioDB.

        Uses artist endpoint and extracts album-specific artwork by release group ID.
        Falls back to TheAudioDB name search if the release group ID is stale (merged
        on MusicBrainz but not updated on artwork services).
        """
        details = get_item_details('album', album_dbid, [
            'musicbrainzalbumartistid',
            'musicbrainzreleasegroupid',
            'title',
            'displayartist'
        ])
        if not isinstance(details, dict):
            return {}

        artist_mbid = details.get('musicbrainzalbumartistid')
        release_group_id = details.get('musicbrainzreleasegroupid')

        if isinstance(artist_mbid, list):
            artist_mbid = artist_mbid[0] if artist_mbid else None
        if not artist_mbid:
            log("Artwork", f"No MusicBrainz artist ID for album {album_dbid}", xbmc.LOGWARNING)
            return {}

        if not release_group_id:
            log(
                "Artwork",
                f"No MusicBrainz release group ID for album {album_dbid}",
                xbmc.LOGWARNING,
            )
            return {}

        ttl_hours = db.get_fanarttv_cache_ttl_hours()
        cache_marker_type = '_full_fetch_complete'

        if not bypass_cache:
            cached_marker = db.get_cached_artwork(
                'album', release_group_id, 'system', cache_marker_type
            )
            if cached_marker is not None:
                cached_art = self._load_music_cached_artwork('album', release_group_id)
                return self._finalise_artwork('album', cached_art)

        all_art: Dict[str, List[dict]] = {}

        log(
            "Artwork",
            f"Album {album_dbid}: looking up release_group={release_group_id}, "
            f"artist={artist_mbid}",
            xbmc.LOGDEBUG,
        )

        artist_data = self.fanart_api.get_artist_artwork(artist_mbid)
        albums = artist_data.get('albums', {})
        album_art = albums.get(release_group_id, {})

        # Stale ID fallback: try cached mapping or TheAudioDB name search
        resolved_old_id: Optional[str] = None
        audiodb_search_result: Optional[dict] = None

        if not album_art and albums:
            resolved_old_id, audiodb_search_result = self._resolve_album_id_mismatch(
                album_dbid, release_group_id, albums, details
            )
            if resolved_old_id:
                album_art = albums.get(resolved_old_id, {})

        if not album_art and not albums:
            log(
                "Artwork",
                f"Album {album_dbid}: no album artwork on Fanart.tv for artist {artist_mbid}",
                xbmc.LOGDEBUG,
            )

        for art_type, artworks in album_art.items():
            if artworks:
                db.cache_artwork(
                    'album', release_group_id, 'fanarttv', art_type, artworks, None, ttl_hours
                )
                all_art.setdefault(art_type, []).extend(artworks)

        from lib.data.api.audiodb import ApiAudioDb
        audiodb = ApiAudioDb()

        album_data: Optional[dict] = None
        if audiodb_search_result:
            album_data = audiodb_search_result
        else:
            lookup_id = resolved_old_id or release_group_id
            album_data = audiodb.get_album(lookup_id)
            if not album_data and resolved_old_id:
                album_data = audiodb.get_album(release_group_id)

        audiodb_art: Dict[str, List[dict]] = {}
        if album_data:
            audiodb_art = audiodb.get_album_artwork_from_data(album_data)
        else:
            log(
                "Artwork",
                f"Album {album_dbid}: no data on TheAudioDB for release_group={release_group_id}",
                xbmc.LOGDEBUG,
            )

        for art_type, artworks in audiodb_art.items():
            if artworks:
                db.cache_artwork(
                    'album', release_group_id, 'theaudiodb', art_type, artworks, None, ttl_hours
                )
                all_art.setdefault(art_type, []).extend(artworks)

        db.cache_artwork(
            'album', release_group_id, 'system', cache_marker_type,
            [{'marker': 'complete'}], None, ttl_hours,
        )

        return self._finalise_artwork('album', all_art)

    def _resolve_album_id_mismatch(
        self,
        album_dbid: int,
        canonical_id: str,
        fanart_albums: Dict[str, Any],
        album_details: dict
    ) -> tuple:
        """Resolve stale MusicBrainz release group ID via cached mapping or TheAudioDB name search.

        Returns (old_id or None, audiodb_search_result or None).
        """
        # Check cached mapping first
        cached_old_ids = db.get_mb_id_mappings_by_canonical(canonical_id)
        for old_id in cached_old_ids:
            if old_id in fanart_albums:
                log(
                    "Artwork",
                    f"Album {album_dbid}: resolved via cached mapping {old_id} -> {canonical_id}",
                    xbmc.LOGDEBUG,
                )
                return old_id, None

        # Fall back to TheAudioDB name search
        album_title = album_details.get('title', '')
        artist_name = album_details.get('displayartist', '')
        if not album_title or not artist_name:
            log(
                "Artwork",
                f"Album {album_dbid}: release_group={canonical_id} not found on Fanart.tv, "
                "cannot search (missing title/artist)",
                xbmc.LOGDEBUG,
            )
            return None, None

        log(
            "Artwork",
            f"Album {album_dbid}: ID mismatch, searching TheAudioDB for "
            f"'{artist_name}' - '{album_title}'",
            xbmc.LOGDEBUG,
        )

        from lib.data.api.audiodb import ApiAudioDb
        audiodb = ApiAudioDb()

        try:
            search_result = audiodb.search_album(artist_name, album_title)
        except Exception as e:
            log("Artwork", f"Album {album_dbid}: TheAudioDB search failed: {e}", xbmc.LOGWARNING)
            return None, None

        if not search_result:
            log(
                "Artwork",
                f"Album {album_dbid}: not found on TheAudioDB by name search",
                xbmc.LOGDEBUG,
            )
            return None, None

        tadb_mbid = search_result.get('strMusicBrainzID', '')
        if not tadb_mbid or tadb_mbid == canonical_id:
            return None, search_result

        # Found an old ID, cache the mapping
        db.save_mb_id_mapping(tadb_mbid, canonical_id)
        log(
            "Artwork",
            f"Album {album_dbid}: resolved stale ID {tadb_mbid} -> {canonical_id} via TheAudioDB",
            xbmc.LOGINFO,
        )

        if tadb_mbid in fanart_albums:
            return tadb_mbid, search_result

        log(
            "Artwork",
            f"Album {album_dbid}: TheAudioDB has ID {tadb_mbid} but not found on Fanart.tv either",
            xbmc.LOGDEBUG,
        )
        return None, search_result


# Global singleton instance for convenience
# Other modules can import this or create their own instance
def create_default_fetcher() -> ApiArtworkFetcher:
    """Create default fetcher instance with default API clients."""
    from lib.data.api.tmdb import ApiTmdb
    from lib.data.api.fanarttv import ApiFanarttv
    return ApiArtworkFetcher(ApiTmdb(), ApiFanarttv())
