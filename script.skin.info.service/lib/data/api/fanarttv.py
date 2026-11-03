"""Fanart.tv artwork for movies, TV shows, seasons, music artists and their albums."""
from __future__ import annotations

from collections import OrderedDict
from typing import Any, Optional, List, Dict, Final

from lib.data.api.client import ApiSession
from lib.data.api.utilities import decode_key
from lib.kodi.settings import KodiSettings

# TV blobs run larger
_MUSIC_BLOB_CACHE_SIZE: Final = 32
_TV_BLOB_CACHE_SIZE: Final = 4


class ApiFanarttv:
    """Fanart.tv API client; the artwork getters return {} for a miss or a failed fetch."""

    BASE_URL = "https://webservice.fanart.tv/v3.2"

    API_KEY = decode_key("MWZmZmExMWNjMGU1NThlZmFkOWM0ZGE2YjljZDJjZWY=")

    def __init__(self):
        self.session = ApiSession(
            service_name="Fanart.tv",
            base_url=self.BASE_URL,
            timeout=(5.0, 15.0),
            max_retries=3,
            backoff_factor=1.0,
            rate_limit=(10, 1.0),
            default_headers={
                "Accept": "application/json"
            }
        )
        self._tv_blob_cache: "OrderedDict[int, Optional[dict]]" = OrderedDict()
        self._music_blob_cache: "OrderedDict[str, Optional[dict]]" = OrderedDict()

    @staticmethod
    def _blob_cache_get(cache: OrderedDict, key, fetch, limit: int) -> Optional[dict]:
        """Memoize a fetch result, None included, dropping the least recently used."""
        if key in cache:
            cache.move_to_end(key)
            return cache[key]

        cache[key] = fetch()
        if len(cache) > limit:
            cache.popitem(last=False)
        return cache[key]

    def _get_music_blob(self, musicbrainz_id: str, abort_flag=None) -> Optional[dict]:
        """Fetch and memoize /music/{mbid}; artist, album and music video art share it."""
        return self._blob_cache_get(
            self._music_blob_cache, musicbrainz_id,
            lambda: self._make_request(f"/music/{musicbrainz_id}", abort_flag),
            _MUSIC_BLOB_CACHE_SIZE,
        )

    def _get_tv_blob(self, tvdb_id: int, abort_flag=None) -> Optional[dict]:
        """Fetch and memoize /tv/{tvdb_id}; show and season art share it."""
        return self._blob_cache_get(
            self._tv_blob_cache, tvdb_id,
            lambda: self._make_request(f"/tv/{tvdb_id}", abort_flag),
            _TV_BLOB_CACHE_SIZE,
        )

    def get_latest(self, feed: str, since: int) -> Optional[List[dict]]:
        """Items with new images since a unix timestamp, or None if the feed is unreachable."""
        data = self._make_request(f"/{feed}/latest?date={since}")
        if data is None:
            return None
        return data if isinstance(data, list) else []

    def get_api_key(self) -> str:
        """Get the built-in fanart.tv project API key."""
        return self.API_KEY.strip()

    def get_client_key(self) -> Optional[str]:
        """Get user's personal API key (client_key) if configured."""
        return KodiSettings.fanarttv_api_key() or None

    def _make_request(self, endpoint: str, abort_flag=None) -> Optional[dict]:
        """Make HTTP request to fanart.tv API, sending the personal key when there is one."""
        headers = {"api-key": self.get_api_key()}

        client_key = self.get_client_key()
        if client_key:
            headers["client-key"] = client_key

        return self.session.get(
            endpoint,
            headers=headers,
            abort_flag=abort_flag
        )

    def _format_artwork_item(self, item: dict, fanart_type: str) -> dict:
        """Format a fanart.tv artwork item to common format, its preview derived from the URL."""
        full_url = item.get('url', '')

        if 'banner' in fanart_type:
            preview = full_url
        else:
            preview = full_url.replace('/fanart/', '/preview/')

        artwork: Dict[str, object] = {
            'url': full_url,
            'previewurl': preview,
            'language': item.get('lang', ''),
            'likes': item.get('likes', '0'),
            'id': item.get('id', ''),
            'source': 'fanart.tv'
        }

        width = item.get('width')
        height = item.get('height')
        if width:
            artwork['width'] = int(width)
        if height:
            artwork['height'] = int(height)

        season = item.get('season')
        if season:
            artwork['season'] = season

        disc = item.get('disc')
        if disc:
            artwork['disc'] = disc
        disc_type = item.get('disc_type')
        if disc_type:
            artwork['disc_type'] = disc_type

        size = item.get('size')
        if size:
            artwork['size'] = size

        added = item.get('added')
        if added:
            artwork['added'] = added

        return artwork

    def get_movie_artwork(self, tmdb_id: int, abort_flag=None) -> dict:
        """Get all artwork for a movie from fanart.tv."""
        data = self._make_request(f"/movies/{tmdb_id}", abort_flag)

        if not data:
            return {}

        result: Dict[str, List[dict]] = {}

        type_map = {
            'movieposter': 'poster',
            'moviebackground': 'fanart',
            'movie4kbackground': 'fanart',
            'hdmovielogo': 'clearlogo',
            'movielogo': 'clearlogo',
            'hdmovieclearart': 'clearart',
            'movieart': 'clearart',
            'moviebanner': 'banner',
            'moviedisc': 'discart',
            'moviethumb': 'landscape'
        }

        for fanart_type, kodi_type in type_map.items():
            if fanart_type in data:
                items = data[fanart_type]
                if kodi_type not in result:
                    result[kodi_type] = []

                for item in items:
                    artwork = self._format_artwork_item(item, fanart_type)
                    result[kodi_type].append(artwork)

        return result

    def get_tv_artwork(self, tvdb_id: int, abort_flag=None) -> dict:
        """Get all artwork for a TV show from fanart.tv, season art under `season.<type>` keys."""
        data = self._get_tv_blob(tvdb_id, abort_flag)

        if not data:
            return {}

        result: Dict[str, List[dict]] = {}

        show_type_map = {
            'tvposter': 'poster',
            'showbackground': 'fanart',
            'show4kbackground': 'fanart',
            'hdtvlogo': 'clearlogo',
            'clearlogo': 'clearlogo',
            'hdclearart': 'clearart',
            'clearart': 'clearart',
            'tvbanner': 'banner',
            'tvthumb': 'landscape',
            'characterart': 'characterart',
        }

        season_type_map = {
            'seasonposter': 'season.poster',
            'seasonbanner': 'season.banner',
            'seasonthumb': 'season.landscape',
        }

        for fanart_type, kodi_type in show_type_map.items():
            if fanart_type in data:
                items = data[fanart_type]
                if kodi_type not in result:
                    result[kodi_type] = []

                for item in items:
                    artwork = self._format_artwork_item(item, fanart_type)
                    result[kodi_type].append(artwork)

        for fanart_type, kodi_type in season_type_map.items():
            if fanart_type in data:
                items = data[fanart_type]
                if kodi_type not in result:
                    result[kodi_type] = []

                for item in items:
                    artwork = self._format_artwork_item(item, fanart_type)
                    result[kodi_type].append(artwork)

        return result

    def get_season_artwork(self, tvdb_id: int, season_number: int, abort_flag=None) -> dict:
        """Get all artwork for one TV season from fanart.tv."""
        data = self._get_tv_blob(tvdb_id, abort_flag)

        if not data:
            return {}

        result: Dict[str, List[dict]] = {}
        season_str = str(season_number)

        season_type_map = {
            'seasonposter': 'poster',
            'seasonbanner': 'banner',
            'seasonthumb': 'landscape',
        }

        for fanart_type, kodi_type in season_type_map.items():
            if fanart_type in data:
                items = data[fanart_type]

                for item in items:
                    item_season = item.get('season', '')
                    if item_season == season_str or item_season == 'all':
                        if kodi_type not in result:
                            result[kodi_type] = []
                        artwork = self._format_artwork_item(item, fanart_type)
                        result[kodi_type].append(artwork)

        return result

    def get_artist_artwork(self, musicbrainz_id: str, abort_flag=None) -> dict:
        """Get all artwork for a music artist from fanart.tv, album art nested under `albums`."""
        data = self._get_music_blob(musicbrainz_id, abort_flag)

        if not data:
            return {}

        result: Dict[str, Any] = {}

        artist_type_map = {
            'artistbackground': 'fanart',
            'artist4kbackground': 'fanart',
            'artistthumb': 'thumb',
            'hdmusiclogo': 'clearlogo',
            'musiclogo': 'clearlogo',
            'musicbanner': 'banner',
        }

        for fanart_type, kodi_type in artist_type_map.items():
            if fanart_type in data:
                items = data[fanart_type]
                if kodi_type not in result:
                    result[kodi_type] = []

                for item in items:
                    artwork = self._format_artwork_item(item, fanart_type)
                    result[kodi_type].append(artwork)

        album_type_map = {
            'albumcover': 'thumb',
            'cdart': 'discart',
        }

        albums_data = data.get('albums', [])
        if albums_data:
            albums_result: Dict[str, Dict[str, List[dict]]] = {}

            for album in albums_data:
                release_group_id = album.get('release_group_id')
                if not release_group_id:
                    continue

                album_artwork: Dict[str, List[dict]] = {}

                for fanart_type, kodi_type in album_type_map.items():
                    if fanart_type in album:
                        items = album[fanart_type]
                        if kodi_type not in album_artwork:
                            album_artwork[kodi_type] = []

                        for item in items:
                            artwork = self._format_artwork_item(item, fanart_type)
                            album_artwork[kodi_type].append(artwork)

                if album_artwork:
                    albums_result[release_group_id] = album_artwork

            if albums_result:
                result['albums'] = albums_result

        return result

    def test_connection(self) -> bool:
        """Test fanart.tv API connection with the user's personal key; False when none is set."""
        client_key = self.get_client_key()
        if not client_key:
            return False
        try:
            data = self.session.get("/movies/11", headers={"client-key": client_key})
            return data is not None and data.get('name') is not None
        except Exception:
            return False

    @staticmethod
    def get_attribution() -> str:
        """Get required fanart.tv attribution text."""
        return "Artwork provided by fanart.tv"
