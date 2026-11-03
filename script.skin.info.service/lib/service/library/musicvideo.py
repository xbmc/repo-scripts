"""Local artist/album library art for focused music videos and nodes."""
from __future__ import annotations

import threading
from typing import Dict, Optional

import xbmc

from lib.kodi.client import get_item_details, log
from lib.kodi.utilities import LabelSnapshot, batch_set_props


class MusicVideoArt:
    """Sets local musicvideo artist/album art from the Kodi music library."""

    def __init__(self):
        self._art_generation = 0

    def set_artist_node(self, labels: LabelSnapshot) -> None:
        """Set art for an artist musicvideo node (DBID-less, name from ListItem.Label)."""
        artist_name = labels.get("ListItem.Label")
        if not artist_name:
            return
        details: dict = {"artist": [artist_name], "album": ""}
        self.set_library_art(details)

    def set_album_node(self, labels: LabelSnapshot) -> None:
        """Set art for an album musicvideo node."""
        labels.read(("ListItem.Label", "ListItem.Artist"))
        album_name = labels.get("ListItem.Label")
        if not album_name:
            return
        artist_name = labels.get("ListItem.Artist")
        details: dict = {
            "artist": [artist_name] if artist_name else [],
            "album": album_name,
        }
        self.set_library_art(details)

    def invalidate_for(self, musicvideoid: int) -> None:
        """Drop cached music data for the artist/track/album of this music video."""
        from lib.kodi.utilities import join_multi
        details = get_item_details(
            'musicvideo', musicvideoid, ["title", "artist", "album"],
            cache_key=f"musicvideo:{musicvideoid}:invalidate",
        )
        if not isinstance(details, dict):
            return
        artist = join_multi(details.get("artist"))
        if not artist:
            return
        from lib.data.database.music import invalidate_music_cache
        invalidate_music_cache(
            artist,
            track=details.get("title", ""),
            album=details.get("album", ""),
        )

    def set_focus_details(self, musicvideoid: str) -> None:
        """Fetch musicvideo details + set library art for a focused item."""
        from lib.kodi.properties import set_musicvideo_properties
        details = get_item_details(
            'musicvideo', int(musicvideoid),
            [
                "title", "artist", "album", "genre", "year", "plot", "runtime",
                "director", "studio", "file", "streamdetails", "art", "premiered",
                "tag", "playcount",
                "lastplayed", "resume", "dateadded", "rating", "userrating", "uniqueid", "track",
            ],
            cache_key=f"musicvideo:{musicvideoid}:details",
        )
        if not isinstance(details, dict):
            return

        set_musicvideo_properties(details)
        self.set_library_art(details)

    def set_library_art(self, details: dict, prefix: str = "SkinInfo.MusicVideo.") -> None:
        """Set local artist art plus deferred album thumb."""
        from lib.kodi.library import get_musicvideo_artist_art

        self._art_generation += 1
        artist_art, artist_id = get_musicvideo_artist_art(details)
        artist_keys = ("Artist.Fanart", "Artist.Thumb", "Artist.Clearlogo", "Artist.Banner")
        props: dict = {f"{prefix}{k}": artist_art.get(k, "") for k in artist_keys}
        batch_set_props(props)
        self._defer_album_thumb(details, artist_id, prefix, self._art_generation)

    def _defer_album_thumb(self, details: dict, artist_id: object, prefix: str,
                           generation: int) -> None:
        """Look up the album thumb off-thread and publish it if focus has not moved."""
        def _worker() -> None:
            try:
                from lib.kodi.library import get_musicvideo_album_art
                album_thumb = get_musicvideo_album_art(details, artist_id)
                if generation != self._art_generation:
                    return
                props: Dict[str, Optional[str]] = {f"{prefix}Album.Thumb": album_thumb}
                batch_set_props(props)
            except Exception as e:
                log("Service", f"Deferred album thumb error: {e}", xbmc.LOGWARNING)

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
