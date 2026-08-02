"""Player tracking handlers (video + music). Each owns its own last-seen state."""
from __future__ import annotations

import threading
from typing import Dict, List, Optional, TYPE_CHECKING

import xbmc

from lib.kodi.client import (
    request, extract_result, get_item_details, KODI_MOVIE_PROPERTIES, decode_image_url,
)
from lib.kodi.utilities import batch_set_props, clear_group, MULTI_VALUE_SEP
from lib.service.properties import set_ratings_properties

if TYPE_CHECKING:
    from lib.service.library.main import ServiceMain


class PlayerVideoTracker:
    """Watches `VideoPlayer.*` and sets `SkinInfo.Player.*` props per content type."""

    def __init__(self, service: 'ServiceMain'):
        self._service = service
        self._last_player_id: Optional[str] = None
        self._last_player_type: Optional[str] = None

    def handle(self) -> None:
        """Update Player props for the currently playing video."""
        if not xbmc.getCondVisibility("Player.HasVideo"):
            if self._last_player_id:
                self._service._clear_media_type("player")
                self._last_player_id = None
                self._last_player_type = None
            return

        player_dbid = xbmc.getInfoLabel("VideoPlayer.DBID") or ""
        if not player_dbid:
            if self._last_player_id:
                self._service._clear_media_type("player")
                self._last_player_id = None
                self._last_player_type = None
            return

        is_movie = xbmc.getCondVisibility("VideoPlayer.Content(movies)")
        is_episode = xbmc.getCondVisibility("VideoPlayer.Content(episodes)")
        is_musicvideo = xbmc.getCondVisibility("VideoPlayer.Content(musicvideos)")

        if is_movie:
            player_type = "movie"
        elif is_episode:
            player_type = "episode"
        elif is_musicvideo:
            player_type = "musicvideo"
        else:
            return

        if player_dbid == self._last_player_id and player_type == self._last_player_type:
            return

        self._last_player_id = player_dbid
        self._last_player_type = player_type

        if player_type == "movie":
            self._set_movie(player_dbid)
        elif player_type == "episode":
            self._set_episode(player_dbid)
        elif player_type == "musicvideo":
            self._set_musicvideo(player_dbid)

    def _set_movie(self, movieid: str) -> None:
        details = get_item_details(
            'movie', int(movieid), KODI_MOVIE_PROPERTIES,
            cache_key=f"player:movie:{movieid}:details",
        )
        if not isinstance(details, dict):
            return
        set_ratings_properties(details, "Player")

    def _set_episode(self, episodeid: str) -> None:
        details = get_item_details(
            'episode', int(episodeid),
            ["title", "ratings", "tvshowid", "season", "episode", "showtitle"],
            cache_key=f"player:episode:{episodeid}:details",
        )
        if not isinstance(details, dict):
            return
        set_ratings_properties(details, "Player")

        tvshowid = details.get("tvshowid")
        if tvshowid and tvshowid != -1:
            self._set_tvshow(str(tvshowid))

    def _set_tvshow(self, tvshowid: str) -> None:
        details = get_item_details(
            'tvshow', int(tvshowid),
            [
                "title", "plot", "year", "premiered", "rating", "votes",
                "genre", "studio", "mpaa", "runtime", "episode", "season",
                "watchedepisodes", "imdbnumber", "originaltitle",
                "art", "userrating", "ratings",
            ],
            cache_key=f"player:tvshow:{tvshowid}:details",
        )
        if not isinstance(details, dict):
            return

        from lib.service.library.focus import resolve_show_runtime
        total, avg = resolve_show_runtime(int(tvshowid))
        if not details.get("runtime") and avg:
            details["runtime"] = avg
        details["total_runtime"] = total

        from lib.service.properties import build_tvshow_data
        data = build_tvshow_data(details)
        props = {f"SkinInfo.Player.TVShow.{k}": v for k, v in data.items() if not k.startswith("_")}
        batch_set_props(props)

        set_ratings_properties(details, "Player.TVShow")

    def _set_musicvideo(self, musicvideoid: str) -> None:
        details = get_item_details(
            'musicvideo', int(musicvideoid),
            [
                "title", "artist", "album", "genre", "year", "plot", "runtime",
                "director", "studio", "file", "streamdetails", "art", "premiered",
                "tag", "playcount", "lastplayed", "resume", "dateadded",
                "rating", "userrating", "uniqueid", "track",
            ],
            cache_key=f"player:musicvideo:{musicvideoid}:details",
        )
        if not isinstance(details, dict):
            return

        from lib.service.properties import build_musicvideo_data
        data = build_musicvideo_data(details)
        props = {
            f"SkinInfo.Player.MusicVideo.{k}": v
            for k, v in data.items() if not k.startswith("_")
        }
        batch_set_props(props)

        self._service.musicvideo.set_library_art(details, prefix="SkinInfo.Player.MusicVideo.")


class PlayerMusicTracker:
    """Watches `MusicPlayer.*` and sets `SkinInfo.Player.Music.*` props.

    Data fetch runs in a background thread so the main service loop never blocks on it.
    """

    def __init__(self):
        self._last_music_artist: Optional[str] = None

    def handle(self) -> None:
        """Update Player.Music props for the currently playing audio."""
        if not xbmc.getCondVisibility("Player.HasAudio"):
            if self._last_music_artist:
                clear_group("SkinInfo.Player.Music.")
                self._last_music_artist = None
            return

        artist_name = xbmc.getInfoLabel("MusicPlayer.Artist") or ""
        if not artist_name:
            if self._last_music_artist:
                clear_group("SkinInfo.Player.Music.")
                self._last_music_artist = None
            return

        if artist_name == self._last_music_artist:
            return

        clear_group("SkinInfo.Player.Music.")
        self._last_music_artist = artist_name
        thread = threading.Thread(target=self._set_details, args=(artist_name,), daemon=True)
        thread.start()

    def _set_details(self, artist_name: str) -> None:
        artists = [a.strip() for a in artist_name.split(MULTI_VALUE_SEP)]
        bio = ""
        library_fanart = ""
        all_albums: List[dict] = []

        for name in artists:
            if not name:
                continue

            result = request("AudioLibrary.GetArtists", {
                "filter": {"field": "artist", "operator": "is", "value": name},
                "properties": ["description", "fanart"],
                "limits": {"end": 1},
            })

            if not result:
                continue

            artists_list = extract_result(result, 'artists')
            if not artists_list:
                continue

            artist = artists_list[0]
            artist_id = artist.get("artistid")

            if not bio:
                bio = artist.get("description", "") or ""

            if not library_fanart:
                library_fanart = decode_image_url(artist.get("fanart", "") or "")

            if artist_id:
                albums_result = request("AudioLibrary.GetAlbums", {
                    "filter": {"artistid": artist_id},
                    "properties": ["title", "year", "art"],
                    "sort": {"method": "year", "order": "ascending"},
                })
                if albums_result:
                    album_list = extract_result(albums_result, 'albums')
                    if isinstance(album_list, list):
                        all_albums.extend(album_list)

        prefix = "SkinInfo.Player.Music."
        props: Dict[str, Optional[str]] = {
            f"{prefix}Artist": artist_name,
            f"{prefix}Bio": bio,
            f"{prefix}FanArt": library_fanart,
        }

        album_count = min(len(all_albums), 20)
        props[f"{prefix}Album.Count"] = str(album_count)

        for i, album in enumerate(all_albums[:20]):
            props[f"{prefix}Album.{i + 1}.Title"] = album.get('title', '')
            year = album.get('year')
            props[f"{prefix}Album.{i + 1}.Year"] = str(year) if year else ''
            props[f"{prefix}Album.{i + 1}.Thumb"] = decode_image_url(
                album.get('art', {}).get('thumb', '')
            )

        # a fast track skip can change the artist while this thread was fetching
        if artist_name != self._last_music_artist:
            return

        batch_set_props(props)
