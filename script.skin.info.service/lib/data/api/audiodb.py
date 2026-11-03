"""TheAudioDB metadata and artwork for artists, albums and music-video tracks."""
from __future__ import annotations

import threading
from typing import Optional, List, Dict

from lib.data.api.client import ApiSession


def _straight_quotes(text: str) -> str:
    """Straighten the curly single quotes Kodi scrapers may store, for a TheAudioDB search."""
    return text.replace('\u2018', "'").replace('\u2019', "'")


class ApiAudioDb:
    """TheAudioDB API client with rate limiting."""

    BASE_URL = "https://www.theaudiodb.com/api/v1/json"
    API_KEY = "123"

    def __init__(self):
        self.session = ApiSession(
            service_name="TheAudioDB",
            base_url=f"{self.BASE_URL}/{self.API_KEY}",
            timeout=(5.0, 15.0),
            max_retries=3,
            backoff_factor=1.0,
            rate_limit=(30, 60.0),
            default_headers={
                "Accept": "application/json"
            }
        )

    def _make_request(self, endpoint: str, abort_flag=None) -> Optional[dict]:
        """Make HTTP request to TheAudioDB API."""
        return self.session.get(endpoint, abort_flag=abort_flag)

    def get_artist(self, musicbrainz_id: str, abort_flag=None) -> Optional[dict]:
        """Get artist data by MusicBrainz ID."""
        data = self._make_request(f"/artist-mb.php?i={musicbrainz_id}", abort_flag)
        if not data:
            return None

        artists = data.get('artists')
        if not artists or not isinstance(artists, list):
            return None

        return artists[0] if artists else None

    def get_album(self, musicbrainz_release_group_id: str, abort_flag=None) -> Optional[dict]:
        """Get album data by MusicBrainz Release Group ID."""
        data = self._make_request(f"/album-mb.php?i={musicbrainz_release_group_id}", abort_flag)
        if not data:
            return None

        albums = data.get('album')
        if not albums or not isinstance(albums, list):
            return None

        return albums[0] if albums else None

    def get_track(self, track_id: str, abort_flag=None) -> Optional[dict]:
        """Get track data by TheAudioDB track ID, as stored in a music video's uniqueid."""
        data = self._make_request(f"/track.php?h={track_id}", abort_flag)
        if not data:
            return None

        tracks = data.get('track')
        if not tracks or not isinstance(tracks, list):
            return None

        return tracks[0] if tracks else None

    def search_album(self, artist_name: str, album_name: str, abort_flag=None) -> Optional[dict]:
        """Search for an album by artist and album name."""
        artist_name = _straight_quotes(artist_name)
        album_name = _straight_quotes(album_name)

        data = self.session.get(
            "/searchalbum.php",
            params={"s": artist_name, "a": album_name},
            abort_flag=abort_flag
        )
        if not data:
            return None

        albums = data.get('album')
        if not albums or not isinstance(albums, list):
            return None

        return albums[0] if albums else None

    def search_track(self, artist_name: str, track_name: str, abort_flag=None) -> Optional[dict]:
        """Search for a track by artist and track name."""
        artist_name = _straight_quotes(artist_name)
        track_name = _straight_quotes(track_name)

        data = self.session.get(
            "/searchtrack.php",
            params={"s": artist_name, "t": track_name},
            abort_flag=abort_flag
        )
        if not data:
            return None

        tracks = data.get('track')
        if not tracks or not isinstance(tracks, list):
            return None

        return tracks[0] if tracks else None

    def search_artist(self, artist_name: str, abort_flag=None) -> Optional[dict]:
        """Search for an artist, returning only an exact name match."""
        artist_name = _straight_quotes(artist_name)

        data = self.session.get(
            "/search.php",
            params={"s": artist_name},
            abort_flag=abort_flag
        )
        if not data:
            return None

        artists = data.get('artists')
        if not artists or not isinstance(artists, list):
            return None

        search_lower = artist_name.lower()
        for artist in artists:
            if isinstance(artist, dict):
                name = artist.get('strArtist', '')
                if name and name.lower() == search_lower:
                    return artist

        return None

    def get_artist_artwork(self, musicbrainz_id: str, abort_flag=None) -> Dict[str, List[dict]]:
        """Get artwork for an artist from TheAudioDB."""
        artist = self.get_artist(musicbrainz_id, abort_flag)
        if not artist:
            return {}

        return self.get_artist_artwork_from_data(artist)

    def get_artist_artwork_from_data(self, artist: dict) -> Dict[str, List[dict]]:
        """Extract artwork from an already-fetched artist dict (no API call)."""
        result: Dict[str, List[dict]] = {}

        artwork_map = {
            'strArtistThumb': 'thumb',
            'strArtistLogo': 'clearlogo',
            'strArtistBanner': 'banner',
            'strArtistFanart': 'fanart',
            'strArtistFanart2': 'fanart',
            'strArtistFanart3': 'fanart',
            'strArtistFanart4': 'fanart',
            'strArtistClearart': 'clearart',
            'strArtistWideThumb': 'landscape',
            'strArtistCutout': 'cutout',
        }

        for api_key, art_type in artwork_map.items():
            url = artist.get(api_key)
            if url:
                artwork = self._format_artwork_item(url)
                result.setdefault(art_type, []).append(artwork)

        return result

    def get_album_artwork_from_data(self, album: dict) -> Dict[str, List[dict]]:
        """Extract artwork from an already-fetched album dict (no API call)."""
        result: Dict[str, List[dict]] = {}

        artwork_map = {
            'strAlbumThumb': 'thumb',
            'strAlbumCDart': 'discart',
            'strAlbumThumbBack': 'back',
            'strAlbumSpine': 'spine',
            'strAlbum3DCase': '3dcase',
            'strAlbum3DFlat': '3dflat',
            'strAlbum3DFace': '3dface',
            'strAlbum3DThumb': '3dthumb',
        }

        for api_key, art_type in artwork_map.items():
            url = album.get(api_key)
            if url:
                artwork = self._format_artwork_item(url)
                result.setdefault(art_type, []).append(artwork)

        return result

    def get_track_artwork_from_data(self, track: dict) -> Dict[str, List[dict]]:
        """Extract music video screenshot artwork from an already-fetched track dict."""
        result: Dict[str, List[dict]] = {}

        for i in range(1, 13):
            url = track.get(f'strMusicVidScreen{i}')
            if url:
                result.setdefault('thumb', []).append(self._format_artwork_item(url))

        return result

    def _format_artwork_item(self, url: str) -> dict:
        """Format a TheAudioDB artwork URL to common format, its preview derived from the URL."""
        return {
            'url': url,
            'previewurl': f"{url}/preview",
            'language': '',
            'likes': '0',
            'id': '',
            'source': 'theaudiodb'
        }

    def test_connection(self) -> bool:
        """Test TheAudioDB API connection."""
        try:
            data = self._make_request("/artist-mb.php?i=f27ec8db-af05-4f36-916e-3d57f91ecf5e")
            return data is not None and data.get('artists') is not None
        except Exception:
            return False

    @staticmethod
    def get_attribution() -> str:
        """Get required TheAudioDB attribution text."""
        return "Metadata provided by TheAudioDB.com"


_SHARED: Optional[ApiAudioDb] = None
_SHARED_LOCK = threading.Lock()


def get_audiodb() -> ApiAudioDb:
    """Get the shared TheAudioDB client, one rate-limit window for every caller."""
    global _SHARED
    if _SHARED is None:
        with _SHARED_LOCK:
            if _SHARED is None:
                _SHARED = ApiAudioDb()
    return _SHARED
