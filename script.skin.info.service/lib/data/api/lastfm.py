"""Last.fm wiki text, tags, listener stats and similar artists for tracks, artists and albums."""
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
    """Last.fm API client; every getInfo takes a name pair or an MBID, and autocorrects names."""

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
        """Last.fm GET, raising on the error codes they return inside a 200 body."""
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

    def _get_info(self, kind: str, identity: Dict[str, Any], mbid: Optional[str],
                  lang: str, abort_flag) -> Optional[dict]:
        """Raw `<kind>` dict from a Last.fm `<kind>.getInfo` call, or None."""
        params: Dict[str, Any] = ({"mbid": mbid, "lang": lang} if mbid
                                  else {**identity, "lang": lang})
        data = self._request(f"{kind}.getInfo", params, abort_flag)
        if not data:
            return None
        info = data.get(kind)
        return info if isinstance(info, dict) else None

    def get_track_info(
        self,
        artist: str,
        track: str,
        mbid: Optional[str] = None,
        lang: str = "en",
        abort_flag=None
    ) -> Optional[dict]:
        """Raw `track` dict from Last.fm, or None."""
        return self._get_info("track", {"artist": artist, "track": track},
                              mbid, lang, abort_flag)

    def get_artist_info(
        self,
        artist: str,
        mbid: Optional[str] = None,
        lang: str = "en",
        abort_flag=None
    ) -> Optional[dict]:
        """Raw `artist` dict from Last.fm, or None."""
        return self._get_info("artist", {"artist": artist}, mbid, lang, abort_flag)

    def get_similar_artists(self, mbid: str, limit: int, abort_flag=None) -> Optional[dict]:
        """Raw `similarartists` dict from Last.fm for an artist's MBID, or None."""
        data = self._request("artist.getSimilar", {"mbid": mbid, "limit": limit}, abort_flag)
        similar = data.get("similarartists") if data else None
        return similar if isinstance(similar, dict) else None

    def get_album_info(
        self,
        artist: str,
        album: str,
        mbid: Optional[str] = None,
        lang: str = "en",
        abort_flag=None
    ) -> Optional[dict]:
        """Raw `album` dict from Last.fm, or None."""
        return self._get_info("album", {"artist": artist, "album": album},
                              mbid, lang, abort_flag)
