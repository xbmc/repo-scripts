"""MusicBrainz studio albums for an artist."""
from __future__ import annotations

import threading
from typing import Optional

from lib.data.api.client import ApiSession


class ApiMusicBrainz:
    """MusicBrainz web service client, paced to its one request a second."""

    BASE_URL = "https://musicbrainz.org/ws/2"

    def __init__(self):
        self.session = ApiSession(
            service_name="MusicBrainz",
            base_url=self.BASE_URL,
            timeout=(5.0, 15.0),
            max_retries=2,
            backoff_factor=1.0,
            rate_limit=(1, 1.0),
            default_headers={
                "Accept": "application/json"
            }
        )

    def get_studio_albums(self, artist_mbid: str, abort_flag=None) -> Optional[dict]:
        """Get the raw release-group search for an artist's official studio albums, or None."""
        query = (f"arid:{artist_mbid} AND primarytype:album AND status:official"
                 " AND NOT secondarytype:*")
        return self.session.get("/release-group",
                                params={"query": query, "limit": 100, "fmt": "json"},
                                abort_flag=abort_flag)


_SHARED: Optional[ApiMusicBrainz] = None
_SHARED_LOCK = threading.Lock()


def get_musicbrainz() -> ApiMusicBrainz:
    """Get the shared MusicBrainz client, one rate-limit window for every caller."""
    global _SHARED
    if _SHARED is None:
        with _SHARED_LOCK:
            if _SHARED is None:
                _SHARED = ApiMusicBrainz()
    return _SHARED
