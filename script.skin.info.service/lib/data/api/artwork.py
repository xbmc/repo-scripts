"""Artwork retrieval and caching for TMDB, fanart.tv and TheAudioDB."""
from __future__ import annotations

import xbmc
from collections import OrderedDict
from typing import Optional, Dict, List, Any, Tuple, Final

from lib.data.database import cache as db_cache
from lib.data.api.tmdb import ApiTmdb, transform_tmdb_images
from lib.data.api.fanarttv import ApiFanarttv
from lib.kodi.client import get_item_details, KODI_GET_DETAILS_METHODS
from lib.kodi.client import log
from lib.kodi.utilities import MULTI_VALUE_SEP

# one entry per show, reused by every season and episode under it
_EXTERNAL_IDS_CACHE_SIZE: Final = 256


def _resolve_musicvideo_artist_mbid(
    artist_name: str,
    album: Optional[str],
    title: Optional[str],
    bulk: bool = False,
) -> Optional[str]:
    """Artist MBID for a music video, from the music library or TheAudioDB."""
    from lib.kodi.library import library_artist_mbid
    from lib.data.music import resolve_artist_mbids

    mbid = library_artist_mbid(artist_name)
    if mbid or bulk:
        return mbid

    mbids, _ = resolve_artist_mbids(artist_name, album=album, track=title)
    return mbids[0] if mbids else None


_MUSIC_CACHE_ART_TYPES: Final = {
    'artist': ['thumb', 'fanart', 'clearlogo', 'banner', 'discart'],
    'album': ['thumb', 'fanart', 'clearlogo', 'banner', 'discart'],
    'musicvideo': ['thumb', 'fanart', 'clearlogo', 'banner', 'clearart', 'landscape'],
}


class ApiArtworkFetcher:
    """Artwork fetcher for a single library item, caching what each provider returns."""

    def __init__(self, tmdb_api: ApiTmdb, fanart_api: ApiFanarttv):
        self.tmdb_api = tmdb_api
        self.fanart_api = fanart_api
        self._external_ids: "OrderedDict[Tuple[str, int], dict]" = OrderedDict()

    def get_external_ids(self, media_type: str, dbid: int) -> dict:
        """TMDB id, TVDB id and release date for a library item."""
        if media_type not in KODI_GET_DETAILS_METHODS:
            return {}

        cache_key = (media_type, dbid)
        if cache_key in self._external_ids:
            self._external_ids.move_to_end(cache_key)
            return self._external_ids[cache_key]

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

        self._external_ids[cache_key] = result
        if len(self._external_ids) > _EXTERNAL_IDS_CACHE_SIZE:
            self._external_ids.popitem(last=False)

        return result

    def fetch_all(
        self, media_type: str, dbid: int, season_number: Optional[int] = None,
        episode_number: Optional[int] = None, bypass_cache: bool = False,
        bulk: bool = False,
    ) -> Dict[str, List[dict]]:
        """Every artwork type for an item; a cache marker stops an art-less item refetching."""
        if media_type == 'season':
            return self._fetch_season_artwork(dbid, season_number, bulk=bulk)
        elif media_type == 'episode':
            return self._fetch_episode_artwork(dbid, season_number, episode_number)
        elif media_type == 'set':
            return self._fetch_movieset_artwork(dbid)
        elif media_type == 'artist':
            return self._fetch_artist_artwork(dbid, bypass_cache=bypass_cache, bulk=bulk)
        elif media_type == 'album':
            return self._fetch_album_artwork(dbid, bypass_cache=bypass_cache, bulk=bulk)
        elif media_type == 'musicvideo':
            return self._fetch_musicvideo_artwork(dbid, bypass_cache, bulk=bulk)
        elif media_type not in ('movie', 'tvshow'):
            return {}

        ids = self.get_external_ids(media_type, dbid)
        tmdb_id = ids.get('tmdb_id')
        tvdb_id = ids.get('tvdb_id')
        release_date = ids.get('release_date')

        if not tmdb_id:
            return {}

        ttl_hours = db_cache.get_cache_ttl_hours(release_date)
        cache_marker_type = '_full_fetch_complete'

        if not bypass_cache:
            cached_marker = db_cache.get_cached_artwork(
                media_type, str(tmdb_id), 'system', cache_marker_type
            )

            if cached_marker is not None:
                cached_art = self._load_cached_artwork(media_type, tmdb_id, tvdb_id)
                return self._finalize_artwork(media_type, cached_art)

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
                db_cache.cache_artwork(
                    media_type, cache_id, 'fanarttv', art_type, artworks, release_date, ttl_hours
                )
                all_art.setdefault(art_type, []).extend(artworks)

        if complete_data:
            db_cache.cache_artwork(
                media_type, str(tmdb_id), 'system', cache_marker_type,
                [{'marker': 'complete'}], release_date, ttl_hours,
            )

        finalized = self._finalize_artwork(media_type, all_art)

        total_items = sum(len(v) for v in finalized.values())
        source_summary = [f"{key}:{len(values)}" for key, values in finalized.items()]
        log(
            "Artwork",
            f"Fetched {media_type}:{dbid} - {total_items} art items "
            f"({', '.join(source_summary)})",
        )

        return finalized

    def _load_cached_artwork(
        self, media_type: str, tmdb_id: int, tvdb_id: Optional[int]
    ) -> Dict[str, List[dict]]:
        """Cached art from both providers; TV shows key the fanart.tv side by tvdb id."""
        cache_id = str(tvdb_id) if tvdb_id and media_type == 'tvshow' else str(tmdb_id)

        media_ids = {
            'tmdb': str(tmdb_id),
            'fanarttv': cache_id
        }

        from lib.artwork.config import CACHE_ART_TYPES
        batch_results = db_cache.get_cached_artwork_batch(media_type, media_ids, CACHE_ART_TYPES)

        cached: Dict[str, List[dict]] = {}
        for (_source, art_type), artworks in batch_results.items():
            cached.setdefault(art_type, []).extend(artworks)

        return cached

    def _load_music_cached_artwork(self, media_type: str, key: str) -> Dict[str, List[dict]]:
        """Cached music art from both providers, keyed by MusicBrainz id or music video key."""
        art_types = _MUSIC_CACHE_ART_TYPES[media_type]
        media_ids = {'fanarttv': key, 'theaudiodb': key}

        batch_results = db_cache.get_cached_artwork_batch(media_type, media_ids, art_types)

        cached: Dict[str, List[dict]] = {}
        for (_source, art_type), artworks in batch_results.items():
            cached.setdefault(art_type, []).extend(artworks)

        return cached

    def _fetch_fanart_art(
        self, media_type: str, tmdb_id: int, tvdb_id: Optional[int]
    ) -> Dict[str, List[dict]]:
        """Fanart.tv art, by tvdb id for shows and tmdb id otherwise."""
        if media_type == 'tvshow' and tvdb_id:
            art = self.fanart_api.get_tv_artwork(tvdb_id)
        else:
            art = self.fanart_api.get_movie_artwork(tmdb_id)
        return art or {}

    def _finalize_artwork(
        self, _media_type: str, artwork: Dict[str, List[dict]]
    ) -> Dict[str, List[dict]]:
        """Sort every art type's list before the fetcher hands the results back."""
        if not artwork:
            return {}

        from lib.artwork.utilities import sort_artwork_by_popularity
        for art_type, artworks in artwork.items():
            artwork[art_type] = sort_artwork_by_popularity(artworks, art_type)

        return artwork

    def _fetch_season_artwork(
        self, season_dbid: int, season_number: Optional[int] = None, bulk: bool = False
    ) -> Dict[str, List[dict]]:
        """Fetch artwork for a season from TMDB, fanart.tv, plus show fanart outside bulk runs."""
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

        # no provider has season fanart
        if not bulk:
            show_fanart = self.fetch_all('tvshow', tvshow_id).get('fanart')
            if show_fanart:
                all_art['fanart'] = list(show_fanart)

        return self._finalize_artwork('season', all_art)

    def _fetch_episode_artwork(
        self, episode_dbid: int, season_number: Optional[int] = None,
        episode_number: Optional[int] = None,
    ) -> Dict[str, List[dict]]:
        """Fetch artwork for a TV episode from TMDB."""
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

        return self._finalize_artwork('episode', tmdb_art)

    def _fetch_movieset_artwork(self, set_dbid: int) -> Dict[str, List[dict]]:
        """Fetch artwork for a movie set, via the TMDB collection of its first movie."""
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

        return self._finalize_artwork('set', all_art)

    def _fetch_artist_artwork(
        self, artist_dbid: int, bypass_cache: bool = False, bulk: bool = False
    ) -> Dict[str, List[dict]]:
        """Fetch artwork for a music artist from fanart.tv, and TheAudioDB outside bulk runs."""
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

        ttl_hours = db_cache.get_fanarttv_cache_ttl_hours()
        cache_marker_type = '_full_fetch_complete'

        if not bypass_cache:
            cached_marker = db_cache.get_cached_artwork('artist', mbid, 'system', cache_marker_type)
            if cached_marker is not None:
                cached_art = self._load_music_cached_artwork('artist', mbid)
                return self._finalize_artwork('artist', cached_art)

        all_art: Dict[str, List[dict]] = {}

        fanart_art = self.fanart_api.get_artist_artwork(mbid)
        for art_type, artworks in fanart_art.items():
            if art_type != 'albums' and artworks:
                db_cache.cache_artwork(
                    'artist', mbid, 'fanarttv', art_type, artworks, None, ttl_hours
                )
                all_art.setdefault(art_type, []).extend(artworks)

        if not bulk:
            from lib.data.api.audiodb import get_audiodb
            audiodb = get_audiodb()
            audiodb_art = audiodb.get_artist_artwork(mbid)
            for art_type, artworks in audiodb_art.items():
                if artworks:
                    db_cache.cache_artwork(
                        'artist', mbid, 'theaudiodb', art_type, artworks, None, ttl_hours
                    )
                    all_art.setdefault(art_type, []).extend(artworks)

            db_cache.cache_artwork(
                'artist', mbid, 'system', cache_marker_type,
                [{'marker': 'complete'}], None, ttl_hours,
            )

        return self._finalize_artwork('artist', all_art)

    def _fetch_musicvideo_artwork(
        self, musicvideo_dbid: int, bypass_cache: bool = False, bulk: bool = False
    ) -> Dict[str, List[dict]]:
        """Fetch artwork for a music video, from track screenshots and the artist's art."""
        details = get_item_details(
            'musicvideo', musicvideo_dbid, ['artist', 'title', 'album', 'uniqueid']
        )
        if not isinstance(details, dict):
            return {}

        unique_ids = details.get('uniqueid') or {}
        scraped_mbid = unique_ids.get('musicbrainz_artist') or None
        audiodb_track_id = unique_ids.get('audiodb') or None

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
        ttl_hours = db_cache.get_fanarttv_cache_ttl_hours()

        if not bypass_cache:
            marker = db_cache.get_cached_artwork(
                'musicvideo', cache_key, 'system', '_full_fetch_complete'
            )
            if marker is not None:
                return self._finalize_artwork(
                    'musicvideo', self._load_music_cached_artwork('musicvideo', cache_key)
                )

        from lib.data.api.audiodb import get_audiodb
        audiodb = get_audiodb()

        all_art: Dict[str, List[dict]] = {}

        from lib.kodi.settings import KodiSettings
        thumb_source = KodiSettings.musicvideo_thumb_source()

        release_group_id = None
        if not bulk or thumb_source in ('screenshots', 'album_cover'):
            track_data = (audiodb.get_track(audiodb_track_id) if audiodb_track_id
                          else audiodb.search_track(artist_name, title))
            if track_data:
                release_group_id = track_data.get('strMusicBrainzAlbumID') or None
                track_art = audiodb.get_track_artwork_from_data(track_data)
                for art_type, artworks in track_art.items():
                    if artworks:
                        db_cache.cache_artwork(
                            'musicvideo', cache_key, 'theaudiodb', art_type, artworks,
                            None, ttl_hours
                        )
                        all_art.setdefault(art_type, []).extend(artworks)

        album = details.get('album') or None
        mbid = scraped_mbid or _resolve_musicvideo_artist_mbid(
            artist_name, album, title, bulk=bulk
        )
        if mbid:
            try:
                fanart_art = self.fanart_api.get_artist_artwork(mbid)
                for art_type, artworks in fanart_art.items():
                    if art_type != 'albums' and artworks:
                        db_cache.cache_artwork(
                            'musicvideo', cache_key, 'fanarttv', art_type, artworks, None, ttl_hours
                        )
                        all_art.setdefault(art_type, []).extend(artworks)

                album_art = (fanart_art.get('albums') or {}).get(release_group_id or '', {})
                for artworks in (album_art.get('thumb'),):
                    if artworks:
                        db_cache.cache_artwork(
                            'musicvideo', cache_key, 'fanarttv', 'thumb', artworks,
                            None, ttl_hours
                        )
                        all_art.setdefault('thumb', []).extend(artworks)
            except Exception as e:
                log(
                    "Artwork",
                    f"Fanart.tv artist artwork error for musicvideo {musicvideo_dbid}: {e}",
                    xbmc.LOGWARNING,
                )

            if not bulk:
                try:
                    from lib.data.database.music import get_cached_artist, SOURCE_AUDIODB
                    audiodb_artist = get_cached_artist(SOURCE_AUDIODB, mbid=mbid)
                    if not audiodb_artist:
                        audiodb_artist = audiodb.get_artist(mbid)
                    if audiodb_artist:
                        tadb_art = audiodb.get_artist_artwork_from_data(audiodb_artist)
                        for art_type, artworks in tadb_art.items():
                            if artworks:
                                db_cache.cache_artwork(
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

        if not bulk:
            db_cache.cache_artwork(
                'musicvideo', cache_key, 'system', '_full_fetch_complete',
                [{'marker': 'complete'}], None, ttl_hours,
            )
        return self._finalize_artwork('musicvideo', all_art)

    def _fetch_album_artwork(
        self, album_dbid: int, bypass_cache: bool = False, bulk: bool = False
    ) -> Dict[str, List[dict]]:
        """Fetch artwork for a music album from fanart.tv and TheAudioDB."""
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

        ttl_hours = db_cache.get_fanarttv_cache_ttl_hours()
        cache_marker_type = '_full_fetch_complete'

        if not bypass_cache:
            cached_marker = db_cache.get_cached_artwork(
                'album', release_group_id, 'system', cache_marker_type
            )
            if cached_marker is not None:
                cached_art = self._load_music_cached_artwork('album', release_group_id)
                return self._finalize_artwork('album', cached_art)

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

        resolved_old_id: Optional[str] = None
        audiodb_search_result: Optional[dict] = None

        if not album_art and albums and not bulk:
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
                db_cache.cache_artwork(
                    'album', release_group_id, 'fanarttv', art_type, artworks, None, ttl_hours
                )
                all_art.setdefault(art_type, []).extend(artworks)

        if bulk:
            return self._finalize_artwork('album', all_art)

        from lib.data.api.audiodb import get_audiodb
        audiodb = get_audiodb()

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
                db_cache.cache_artwork(
                    'album', release_group_id, 'theaudiodb', art_type, artworks, None, ttl_hours
                )
                all_art.setdefault(art_type, []).extend(artworks)

        db_cache.cache_artwork(
            'album', release_group_id, 'system', cache_marker_type,
            [{'marker': 'complete'}], None, ttl_hours,
        )

        return self._finalize_artwork('album', all_art)

    def _resolve_album_id_mismatch(
        self,
        album_dbid: int,
        canonical_id: str,
        fanart_albums: Dict[str, Any],
        album_details: dict
    ) -> tuple:
        """Resolve a MusicBrainz release group id the artwork services have not caught up to."""
        cached_old_ids = db_cache.get_mb_id_aliases(canonical_id)
        for old_id in cached_old_ids:
            if old_id in fanart_albums:
                log(
                    "Artwork",
                    f"Album {album_dbid}: resolved via cached mapping {old_id} -> {canonical_id}",
                    xbmc.LOGDEBUG,
                )
                return old_id, None

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

        from lib.data.api.audiodb import get_audiodb
        audiodb = get_audiodb()

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

        db_cache.save_mb_id_mapping(tadb_mbid, canonical_id)
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


def create_default_fetcher() -> ApiArtworkFetcher:
    """Create a fetcher with the default TMDB and fanart.tv clients."""
    from lib.data.api.tmdb import ApiTmdb
    from lib.data.api.fanarttv import ApiFanarttv
    return ApiArtworkFetcher(ApiTmdb(), ApiFanarttv())
