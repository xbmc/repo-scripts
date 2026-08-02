"""Last.fm API client for music metadata.

Provides:
- Track info (wiki/description, tags, listeners, playcount, album)
- Artist info (bio, tags, similar artists, stats)
- Album info (wiki, tags, tracklist, stats)

Free tier: project API key, 5 req/s averaged over 5 min
"""
from __future__ import annotations

import xbmc
from typing import Optional, Dict, Any

from lib.data.api.client import ApiSession
from lib.data.api.client import RateLimitHit, RetryableError
from lib.data.api.utilities import decode_key
from lib.kodi.client import log

_RETRYABLE_ERRORS = {2, 8, 11, 16}
_NOT_FOUND_ERRORS = {6, 7, 17}
_PERMANENT_ERRORS = {3, 4, 5, 9, 10, 13, 26}


class ApiLastfm:
    """Last.fm API client."""

    BASE_URL = "https://ws.audioscrobbler.com/2.0"
    API_KEY = decode_key("NzVlNmVlZjAxNGUwZWFlODI5ZWFlZDM3OWYyOWJmMTY=")

    def __init__(self):
        self.session = ApiSession(
            service_name="Last.fm",
            base_url=self.BASE_URL,
            timeout=(5.0, 15.0),
            max_retries=3,
            backoff_factor=1.0,
            rate_limit=(30, 60.0),
            default_headers={
                "Accept": "application/json"
            }
        )

    def _request(self, method: str, params: Dict[str, Any], abort_flag=None) -> Optional[dict]:
        params = {
            "method": method,
            "api_key": self.API_KEY,
            "format": "json",
            "autocorrect": 1,
            **params,
        }
        data = self.session.get("", params=params, abort_flag=abort_flag)
        if not data:
            return None

        error_code = data.get('error')
        if error_code is None:
            return data

        error_msg = data.get('message', 'Unknown error')

        if error_code == 29:
            raise RateLimitHit("Last.fm")

        if error_code in _RETRYABLE_ERRORS:
            raise RetryableError("Last.fm", f"error {error_code}: {error_msg}")

        if error_code in _NOT_FOUND_ERRORS:
            return None

        if error_code in _PERMANENT_ERRORS:
            level = xbmc.LOGERROR if error_code in (10, 26) else xbmc.LOGWARNING
            log("API", f"Last.fm: error {error_code}: {error_msg}", level)

        return None

    def get_track_info(
        self,
        artist: str,
        track: str,
        mbid: Optional[str] = None,
        lang: str = "en",
        abort_flag=None
    ) -> Optional[dict]:
        """Get track metadata from Last.fm.

        Returns the raw 'track' dict from the API response, or None.
        """
        if mbid:
            params: Dict[str, Any] = {"mbid": mbid, "lang": lang}
        else:
            params = {"artist": artist, "track": track, "lang": lang}

        data = self._request("track.getInfo", params, abort_flag)
        if not data:
            return None

        track_data = data.get('track')
        if not isinstance(track_data, dict):
            return None
        return track_data

    def get_artist_info(
        self,
        artist: str,
        mbid: Optional[str] = None,
        lang: str = "en",
        abort_flag=None
    ) -> Optional[dict]:
        """Get artist metadata from Last.fm.

        Returns the raw 'artist' dict from the API response, or None.
        """
        if mbid:
            params: Dict[str, Any] = {"mbid": mbid, "lang": lang}
        else:
            params = {"artist": artist, "lang": lang}

        data = self._request("artist.getInfo", params, abort_flag)
        if not data:
            return None

        artist_data = data.get('artist')
        if not isinstance(artist_data, dict):
            return None
        return artist_data

    def get_album_info(
        self,
        artist: str,
        album: str,
        mbid: Optional[str] = None,
        lang: str = "en",
        abort_flag=None
    ) -> Optional[dict]:
        """Get album metadata from Last.fm.

        Returns the raw 'album' dict from the API response, or None.
        """
        if mbid:
            params: Dict[str, Any] = {"mbid": mbid, "lang": lang}
        else:
            params = {"artist": artist, "album": album, "lang": lang}

        data = self._request("album.getInfo", params, abort_flag)
        if not data:
            return None

        album_data = data.get('album')
        if not isinstance(album_data, dict):
            return None
        return album_data

