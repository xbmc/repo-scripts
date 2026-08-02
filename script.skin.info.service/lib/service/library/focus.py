"""Focus dispatcher: reads ListItem.DBID and sets per-type SkinInfo.* properties."""
from __future__ import annotations

import re
import threading
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

import xbmc

from lib.kodi.client import (
    request, get_cache_only, extract_result, get_item_details,
    KODI_MOVIE_PROPERTIES,
)
from lib.kodi.utilities import clear_group, gui_transition_settled, is_kodi_piers_or_later
from lib.service.properties import (
    set_artist_properties,
    set_album_properties,
    set_movie_properties,
    set_movieset_properties,
    set_tvshow_properties,
    set_season_properties,
    set_episode_properties,
    set_ratings_properties,
    set_movie_extras_aggregates,
    clear_listitem_unified_properties,
)

if TYPE_CHECKING:
    from lib.service.library.main import ServiceMain


CACHE_MOVIESET_TTL = 300

_ASSET_VIEW_PATH_RE = re.compile(r"^videodb://.*?/(\d+)/-?\d+/?(?:\?|$)")


def _fetch_extras_aggregates(parent_dbid: str) -> Tuple[int, int, int, int]:
    """Return (count, total_runtime, unwatched, unwatched_runtime) for a movie's extras folder.

    Uncached: invalidate_asset_view() plus the _last_asset_parent dedup already limit
    refetches; per-file length reads streamdetails since `runtime` here is the parent
    movie's duration.
    """
    resp = request(
        "Files.GetDirectory",
        {
            "directory": f"videodb://movies/titles/{parent_dbid}/2/",
            "media": "video",
            "properties": ["streamdetails", "playcount"],
        },
    )
    files = extract_result(resp, "files", [])
    if not isinstance(files, list) or not files:
        return 0, 0, 0, 0
    count = len(files)
    total_runtime = 0
    unwatched = 0
    unwatched_runtime = 0
    for f in files:
        video = (f.get("streamdetails") or {}).get("video") or []
        duration = int(video[0].get("duration") or 0) if video else 0
        total_runtime += duration
        if int(f.get("playcount") or 0) == 0:
            unwatched += 1
            unwatched_runtime += duration
    return count, total_runtime, unwatched, unwatched_runtime


_MEDIA_TYPE_PREFIXES = {
    "movie": "SkinInfo.Movie.",
    "set": "SkinInfo.Set.",
    "artist": "SkinInfo.Artist.",
    "album": "SkinInfo.Album.",
    "tvshow": "SkinInfo.TVShow.",
    "season": "SkinInfo.Season.",
    "episode": "SkinInfo.Episode.",
    "musicvideo": "SkinInfo.MusicVideo.",
    "musicvideo_artist": "SkinInfo.MusicVideo.",
    "musicvideo_album": "SkinInfo.MusicVideo.",
    "player": "SkinInfo.Player.",
}


def _get_episode_runtimes(tvshowid: int, season: Optional[int] = None) -> List[int]:
    props = ["runtime"] if is_kodi_piers_or_later() else ["runtime", "streamdetails"]
    params: Dict = {"tvshowid": tvshowid, "properties": props}
    cache_key = f"tvshow:{tvshowid}:episode_runtimes"
    if season is not None:
        params["season"] = season
        cache_key = f"tvshow:{tvshowid}:s{season}:episode_runtimes"
    resp = request("VideoLibrary.GetEpisodes", params, cache_key=cache_key)
    episodes = extract_result(resp, "episodes")
    return [e["runtime"] for e in episodes if e.get("runtime", 0) > 0]


def resolve_show_runtime(tvshowid: int) -> Tuple[int, int]:
    """Return (total_runtime, avg_episode_runtime); cache-miss fetches via GetEpisodes."""
    from lib.data.database import runtime as runtime_cache
    cached = runtime_cache.get_show_runtime(tvshowid)
    if cached is not None:
        return cached
    runtimes = _get_episode_runtimes(tvshowid)
    total = sum(runtimes)
    avg = total // len(runtimes) if runtimes else 0
    runtime_cache.save_show_runtime(tvshowid, total, avg, len(runtimes))
    return total, avg


def _resolve_season_runtime(tvshowid: int, season: int) -> int:
    """Return season total_runtime; cache-miss fetches via GetEpisodes."""
    from lib.data.database import runtime as runtime_cache
    cached = runtime_cache.get_season_runtime(tvshowid, season)
    if cached is not None:
        return cached
    runtimes = _get_episode_runtimes(tvshowid, season)
    total = sum(runtimes)
    runtime_cache.save_season_runtime(tvshowid, season, total, len(runtimes))
    return total


class FocusDispatcher:
    """Reads `ListItem.DBID` each tick and dispatches to per-type detail setters.

    Holds last-seen `(dbid, type)` to skip work when nothing changed.
    """

    def __init__(self, service: 'ServiceMain'):
        self._service = service
        self._last_id: Optional[str] = None
        self._last_type: Optional[str] = None
        self._last_asset_parent: Optional[str] = None

    def clear_media_type(self, media_type: str) -> None:
        """Clear all `SkinInfo.<MediaType>.*` props for the given type."""
        prefix = _MEDIA_TYPE_PREFIXES.get(media_type)
        if prefix:
            clear_group(prefix)
        if media_type == "season":
            clear_group(_MEDIA_TYPE_PREFIXES["tvshow"])

    def invalidate_asset_view(self) -> None:
        """Force a refetch of extras aggregates on the next tick. Called from the
        library monitor on playcount-relevant events (extra watched / marked watched).
        """
        self._last_asset_parent = None

    def _handle_asset_view(self) -> bool:
        """Treat the parent movie as focus context inside a videoversions/videoextras
        container (Piers+ only).

        Driven by `Container.FolderPath` since focused items there often lack a DBID;
        returns True while active so `process()` keeps `SkinInfo.Movie.*` on empty-DBID focus.
        """
        if not is_kodi_piers_or_later():
            return False
        in_container = xbmc.getCondVisibility(
            "Container.Content(videoversions) | Container.Content(videoextras)"
        )
        if not in_container:
            if self._last_asset_parent is not None:
                set_movie_extras_aggregates(0, 0, 0, 0)
                self._last_asset_parent = None
            return False
        folder_path = xbmc.getInfoLabel("Container.FolderPath") or ""
        match = _ASSET_VIEW_PATH_RE.match(folder_path)
        if not match:
            return True
        parent_dbid = match.group(1)
        if parent_dbid != self._last_asset_parent:
            self._set_movie(parent_dbid)
            self._last_id = parent_dbid
            self._last_type = "movie"
            count, total_runtime, unwatched, unwatched_runtime = (
                _fetch_extras_aggregates(parent_dbid)
            )
            set_movie_extras_aggregates(count, total_runtime, unwatched, unwatched_runtime)
            self._last_asset_parent = parent_dbid
        return True

    def process(self) -> None:
        """Read ListItem.DBID/DBType and dispatch to the matching detail setter."""
        if not gui_transition_settled():
            return
        in_asset_view = self._handle_asset_view()

        dbid = xbmc.getInfoLabel("ListItem.DBID") or ""
        if not dbid:
            if in_asset_view:
                self._service.blur.handle_focus()
                return
            if self._last_type:
                self.clear_media_type(self._last_type)
                clear_listitem_unified_properties()
                self._last_type = ""
                self._last_id = None
            self._service.blur.handle_focus()
            return

        dbtype = xbmc.getInfoLabel("ListItem.DBType") or ""
        if dbid == self._last_id and dbtype and dbtype == self._last_type:
            self._service.blur.handle_focus()
            return

        mv_mediatype = ""
        if dbtype in ("actor", "album"):
            mv_mediatype = xbmc.getInfoLabel("ListItem.Property(musicvideomediatype)")

        if dbtype == "actor" and mv_mediatype == "artist":
            cur_type = "musicvideo_artist"
        elif dbtype == "album" and mv_mediatype == "album":
            cur_type = "musicvideo_album"
        elif dbtype in (
            "set", "movie", "artist", "album", "tvshow", "season", "episode", "musicvideo"
        ):
            cur_type = dbtype
        elif dbid == self._last_id and self._last_type:
            cur_type = self._last_type
        else:
            is_set = xbmc.getCondVisibility(
                "ListItem.IsCollection | String.IsEqual(ListItem.DBType,set)"
            )
            if is_set or xbmc.getCondVisibility("Container.Content(sets)"):
                cur_type = "set"
            elif xbmc.getCondVisibility("Container.Content(movies)"):
                cur_type = "movie"
            elif xbmc.getCondVisibility("Container.Content(artists)"):
                cur_type = "artist"
            elif xbmc.getCondVisibility("Container.Content(albums)"):
                cur_type = "album"
            elif xbmc.getCondVisibility("Container.Content(tvshows)"):
                cur_type = "tvshow"
            elif xbmc.getCondVisibility("Container.Content(seasons)"):
                cur_type = "season"
            elif xbmc.getCondVisibility("Container.Content(episodes)"):
                cur_type = "episode"
            elif xbmc.getCondVisibility("Container.Content(musicvideos)"):
                cur_type = "musicvideo"
            else:
                cur_type = ""

        if self._last_id and dbid != self._last_id:
            if self._last_type and self._last_type != cur_type:
                self.clear_media_type(self._last_type)
            self._last_type = ""

        if dbid == self._last_id and cur_type == self._last_type:
            self._service.blur.handle_focus()
            return

        if cur_type == "set":
            self._last_id = dbid
            self._last_type = "set"
            self._set_movieset(dbid)
        elif cur_type == "movie":
            self._last_id = dbid
            self._last_type = "movie"
            self._set_movie(dbid)
        elif cur_type == "artist":
            if self._last_type != "artist":
                self.clear_media_type("album")
            self._last_id = dbid
            self._last_type = "artist"
            self._set_artist(dbid)
        elif cur_type == "album":
            if self._last_type != "album":
                self.clear_media_type("artist")
            self._last_id = dbid
            self._last_type = "album"
            self._set_album(dbid)
        elif cur_type == "tvshow":
            self._last_id = dbid
            self._last_type = "tvshow"
            self._set_tvshow(dbid)
        elif cur_type == "season":
            self._last_id = dbid
            self._last_type = "season"
            self._set_season(dbid)
        elif cur_type == "episode":
            self._last_id = dbid
            self._last_type = "episode"
            self._set_episode(dbid)
        elif cur_type == "musicvideo_artist":
            self._last_id = dbid
            self._last_type = "musicvideo_artist"
            self._service.musicvideo.set_artist_node()
        elif cur_type == "musicvideo_album":
            self._last_id = dbid
            self._last_type = "musicvideo_album"
            self._service.musicvideo.set_album_node()
        elif cur_type == "musicvideo":
            self._last_id = dbid
            self._last_type = "musicvideo"
            self._service.musicvideo.set_focus_details(dbid)
        else:
            if self._last_type in (
                "movie", "set", "artist", "album", "tvshow", "season", "episode",
                "musicvideo", "musicvideo_artist", "musicvideo_album",
            ):
                self.clear_media_type(self._last_type)
                clear_listitem_unified_properties()
            self._last_id = dbid
            self._last_type = ""

        self._service.blur.handle_focus()

    def _set_movie(self, movieid: str) -> None:
        details = get_item_details(
            'movie', int(movieid), KODI_MOVIE_PROPERTIES,
            cache_key=f"movie:{movieid}:details",
        )
        if not isinstance(details, dict):
            return
        set_movie_properties(details)
        set_ratings_properties(details, "Movie")

    def _set_movieset(self, setid: str) -> None:
        cached_full = get_cache_only(f"set:{setid}:details")
        if cached_full:
            details = extract_result(cached_full, "setdetails")
            if isinstance(details, dict):
                set_movieset_properties(details, details.get("movies") or [])
                return

        min_details = get_item_details(
            'set', int(setid),
            ["title", "plot", "art"],
            cache_key=f"set:{setid}:min",
            ttl_seconds=CACHE_MOVIESET_TTL,
            movies={
                "properties": [
                    "title", "year", "runtime", "thumbnail", "art", "file",
                ],
                "sort": {"method": "year", "order": "ascending"},
            },
        )
        if isinstance(min_details, dict):
            set_movieset_properties(min_details, min_details.get("movies") or [])

        cached_movies = get_cache_only(f"set:{setid}:movies")
        if cached_movies and min_details and isinstance(min_details, dict):
            movies_list = extract_result(cached_movies, "movies")
            if isinstance(movies_list, list):
                set_movieset_properties(min_details, movies_list)

        if isinstance(min_details, dict):
            threading.Thread(
                target=self._fetch_movieset_movies,
                args=(setid, min_details),
                daemon=True,
            ).start()

    def _fetch_movieset_movies(self, current_id: str, base_details: dict) -> None:
        movies_req = {
            "filter": {"setid": int(current_id)},
            "properties": [
                "title", "year", "runtime", "genre", "director", "studio",
                "country", "writer", "plot", "plotoutline", "mpaa", "file",
                "streamdetails", "art", "thumbnail",
            ],
            "sort": {"method": "year", "order": "ascending"},
        }
        mresp = request(
            "VideoLibrary.GetMovies", movies_req,
            cache_key=f"set:{current_id}:movies",
            ttl_seconds=CACHE_MOVIESET_TTL,
        )
        if not mresp:
            return
        movies = extract_result(mresp, "movies")
        if not isinstance(movies, list):
            return
        if self._last_id == current_id and self._last_type == "set":
            set_movieset_properties(base_details, movies)

    def _set_artist(self, artistid: str) -> None:
        from lib.plugin.dbid import fetch_artist_details
        result = fetch_artist_details(int(artistid))
        if result:
            set_artist_properties(*result)

    def _set_album(self, albumid: str) -> None:
        from lib.plugin.dbid import fetch_album_details
        result = fetch_album_details(int(albumid))
        if result:
            set_album_properties(*result)

    def _set_tvshow(self, tvshowid: str) -> None:
        details = get_item_details(
            'tvshow', int(tvshowid),
            [
                "title", "plot", "year", "premiered", "rating", "votes",
                "genre", "studio", "mpaa", "runtime", "episode", "season",
                "watchedepisodes", "imdbnumber", "originaltitle", "sorttitle",
                "episodeguide", "tag", "art", "userrating", "ratings",
                "cast", "uniqueid", "dateadded", "file", "lastplayed", "playcount",
                "trailer",
            ],
            cache_key=f"tvshow:{tvshowid}:details",
        )
        if not isinstance(details, dict):
            return

        total, avg = resolve_show_runtime(int(tvshowid))
        if not details.get("runtime") and avg:
            details["runtime"] = avg
        details["total_runtime"] = total

        set_tvshow_properties(details)
        set_ratings_properties(details, "TVShow")

    def _set_season(self, seasonid: str) -> None:
        details = get_item_details(
            'season', int(seasonid),
            [
                "season", "showtitle", "playcount", "episode",
                "tvshowid", "watchedepisodes", "art", "userrating", "title",
            ],
            cache_key=f"season:{seasonid}:details",
        )
        if not isinstance(details, dict):
            return

        tvshowid = details.get("tvshowid")
        season_num = details.get("season")
        if tvshowid and tvshowid != -1:
            _, avg = resolve_show_runtime(int(tvshowid))
            if avg:
                details["runtime"] = avg
            if season_num is not None:
                details["total_runtime"] = _resolve_season_runtime(int(tvshowid), int(season_num))

        set_season_properties(details)

        if tvshowid and tvshowid != -1:
            self._set_tvshow(str(tvshowid))

    def _set_episode(self, episodeid: str) -> None:
        details = get_item_details(
            'episode', int(episodeid),
            [
                "title", "plot", "rating", "votes", "ratings", "season", "episode",
                "showtitle", "firstaired", "runtime", "director", "writer", "file",
                "streamdetails", "art", "productioncode", "originaltitle", "playcount",
                "cast", "lastplayed", "resume", "tvshowid", "dateadded", "uniqueid",
                "userrating", "seasonid", "genre", "studio",
            ],
            cache_key=f"episode:{episodeid}:details",
        )
        if not isinstance(details, dict):
            return

        set_episode_properties(details)
        set_ratings_properties(details, "Episode")

