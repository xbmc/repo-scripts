"""Focus dispatcher: reads ListItem.DBID and sets per-type SkinInfo.* properties."""
from __future__ import annotations

import re
import threading
from typing import Optional, Tuple, TYPE_CHECKING, Final

from lib.kodi.client import (
    request, get_cache_only, extract_result, get_item_details,
    KODI_MOVIE_PROPERTIES,
)
from lib.kodi.utilities import (
    LabelSnapshot, clear_group, is_kodi_piers_or_later, modal_dialog_active, normalize_dbtype,
    tvshow_version_fields,
)
from lib.kodi.library import (
    cached_watch_minutes, cached_watched_episodes, resolve_season_runtime, resolve_show_runtime,
    resolve_watch_minutes,
)
from lib.kodi.properties import (
    set_artist_properties,
    set_album_properties,
    set_movie_properties,
    set_movieset_properties,
    set_tvshow_properties,
    set_season_properties,
    set_episode_properties,
    set_ratings_properties,
    set_movie_extras_aggregates,
    set_watched_properties,
    clear_listitem_unified_properties,
)

if TYPE_CHECKING:
    from lib.service.library.main import ServiceMain


CACHE_MOVIESET_TTL: Final = 300
FOCUS_LABELS: Final = ("ListItem.DBID", "ListItem.DBType",
                       "ListItem.Property(musicvideomediatype)", "Container.Content")

_ASSET_VIEW_PATH_RE = re.compile(r"^videodb://.*?/(\d+)/-?\d+/?(?:\?|$)")


def _fetch_extras_aggregates(parent_dbid: str) -> Tuple[int, int, int, int]:
    """Fetch the count, runtime, unwatched count and unwatched runtime of a movie's extras."""
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


_CONTAINER_CONTENT_TYPES = {
    "sets": "set",
    "movies": "movie",
    "artists": "artist",
    "albums": "album",
    "tvshows": "tvshow",
    "seasons": "season",
    "episodes": "episode",
    "musicvideos": "musicvideo",
}


class FocusDispatcher:
    """Dispatcher setting the focused library item's properties, idle while focus holds still."""

    def __init__(self, service: 'ServiceMain'):
        self._service = service
        self._last_id: Optional[str] = None
        self._last_type: Optional[str] = None
        self._last_dbtype: Optional[str] = None
        self._last_asset_parent: Optional[str] = None

    def clear_media_type(self, media_type: str) -> None:
        """Clear all `SkinInfo.<MediaType>.*` props for the given type."""
        prefix = _MEDIA_TYPE_PREFIXES.get(media_type)
        if prefix:
            clear_group(prefix)
        if media_type == "season":
            clear_group(_MEDIA_TYPE_PREFIXES["tvshow"])

    def invalidate_item(self, media_type: str, dbid) -> None:
        """Drop the memo and the cached details for an item Kodi has just written to."""
        from lib.kodi.client import drop_cached
        drop_cached(f"{media_type}:{dbid}:")
        if self._last_id == str(dbid):
            self._last_id = None

    def invalidate_asset_view(self) -> None:
        """Invalidate the extras aggregates, refetched on the next tick."""
        self._last_asset_parent = None

    def _handle_asset_view(self, labels: LabelSnapshot) -> bool:
        """Handle a versions or extras view as its parent movie; True while one is open."""
        if not is_kodi_piers_or_later():
            return False
        if labels.get("Container.Content").lower() not in ("videoversions", "videoextras"):
            if self._last_asset_parent is not None and not modal_dialog_active():
                set_movie_extras_aggregates(0, 0, 0, 0)
                self._last_asset_parent = None
            return False
        match = _ASSET_VIEW_PATH_RE.match(labels.get("Container.FolderPath"))
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

    def process(self, labels: LabelSnapshot) -> None:
        """Read ListItem.DBID/DBType, dispatch to its detail setter, then run the focus blur."""
        in_asset_view = self._handle_asset_view(labels)

        dbid = labels.get("ListItem.DBID")
        if not dbid:
            if in_asset_view:
                self._service.blur.handle_focus(labels)
                return
            if modal_dialog_active():
                self._service.blur.handle_focus(labels)
                return
            if self._last_type:
                self.clear_media_type(self._last_type)
                clear_listitem_unified_properties()
                self._last_type = ""
                self._last_dbtype = None
                self._last_id = None
            self._service.blur.handle_focus(labels)
            return

        dbtype = normalize_dbtype(labels.get("ListItem.DBType"))

        mv_mediatype = ""
        if dbtype in ("actor", "album"):
            mv_mediatype = labels.get("ListItem.Property(musicvideomediatype)")

        # one person is the same dbid+DBType in the actors and artists nodes; only this differs
        identity = f"{dbtype}|{mv_mediatype}"
        if dbid == self._last_id and self._last_type and identity == self._last_dbtype:
            self._service.blur.handle_focus(labels)
            return

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
            # Container.Content(x) is a case-insensitive compare against this label
            cur_type = _CONTAINER_CONTENT_TYPES.get(labels.get("Container.Content").lower(), "")

        if self._last_id and dbid != self._last_id:
            if self._last_type and self._last_type != cur_type:
                self.clear_media_type(self._last_type)
            self._last_type = ""

        if dbid == self._last_id and cur_type == self._last_type:
            self._service.blur.handle_focus(labels)
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
            self._service.musicvideo.set_artist_node(labels)
        elif cur_type == "musicvideo_album":
            self._last_id = dbid
            self._last_type = "musicvideo_album"
            self._service.musicvideo.set_album_node(labels)
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

        self._last_dbtype = identity
        self._service.blur.handle_focus(labels)

    def _set_movie(self, movieid: str) -> None:
        """Set movie properties for the focused item."""
        details = get_item_details(
            'movie', int(movieid), KODI_MOVIE_PROPERTIES,
            cache_key=f"movie:{movieid}:details",
        )
        if not isinstance(details, dict):
            return
        set_movie_properties(details)
        set_ratings_properties(details, "Movie")

    def _set_movieset(self, setid: str) -> None:
        """Set movie set properties, preferring a cached full record over a minimal fetch."""
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
        """Fetch a movie set's members, publishing only while that set is still focused."""
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
        """Set artist properties for the focused item."""
        from lib.kodi.library import fetch_artist_details
        result = fetch_artist_details(int(artistid))
        if result:
            set_artist_properties(*result)

    def _set_album(self, albumid: str) -> None:
        """Set album properties for the focused item."""
        from lib.kodi.library import fetch_album_details
        result = fetch_album_details(int(albumid))
        if result:
            set_album_properties(*result)

    def _set_tvshow(self, tvshowid: str, defer: bool = True) -> bool:
        """Set tvshow properties for the focused item; True when its watch time is still due."""
        details = get_item_details(
            'tvshow', int(tvshowid),
            [
                "title", "plot", "year", "premiered", "rating", "votes",
                "genre", "studio", "mpaa", "runtime", "episode", "season",
                "watchedepisodes", "imdbnumber", "originaltitle", "sorttitle",
                "episodeguide", "tag", "art", "userrating", "ratings",
                "cast", "uniqueid", "dateadded", "file", "lastplayed", "playcount",
            ] + tvshow_version_fields(),
            cache_key=f"tvshow:{tvshowid}:details",
        )
        if not isinstance(details, dict):
            return False

        total, avg = resolve_show_runtime(int(tvshowid), details.get("episode"))
        if not details.get("runtime") and avg:
            details["runtime"] = avg
        details["total_runtime"] = total
        pending = self._watch_minutes_now(details, int(tvshowid))

        set_tvshow_properties(details)
        set_ratings_properties(details, "TVShow")
        if pending and defer:
            self._defer_watch_minutes(int(tvshowid), None, tvshowid, "tvshow")
        return pending

    @staticmethod
    def _watch_minutes_now(details: dict, tvshowid: int) -> bool:
        """Fill in a show's minutes watched from the cache; True when a fetch is still needed."""
        if not details.get("watchedepisodes"):
            details["watch_minutes"] = 0
            return False
        cached = cached_watch_minutes(tvshowid)
        details["watch_minutes"] = cached or 0
        return cached is None

    def _defer_watch_minutes(self, tvshowid: int, season: Optional[int], focus_id: str,
                             focus_type: str) -> None:
        """Fetch minutes watched off-thread, publishing them only while the item holds focus."""
        def worker() -> None:
            if self._service.abort.wait(0.3) or self._last_id != focus_id:
                return
            show = resolve_watch_minutes(tvshowid)
            season_minutes = resolve_watch_minutes(tvshowid, season) if season is not None else 0
            if self._last_id != focus_id or self._last_type != focus_type:
                return
            set_watched_properties("TVShow", show, unified=season is None)
            if season is not None:
                set_watched_properties("Season", season_minutes, unified=True,
                                       episodes=cached_watched_episodes(tvshowid, season) or 0)

        threading.Thread(target=worker, daemon=True).start()

    def _set_season(self, seasonid: str) -> None:
        """Set season properties, filling runtime from the parent show's episodes."""
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
                details["total_runtime"] = resolve_season_runtime(
                    int(tvshowid), int(season_num), details.get("episode"))

        pending: Optional[Tuple[int, int]] = None
        if tvshowid and tvshowid != -1:
            show_due = self._set_tvshow(str(tvshowid), defer=False)
            if season_num is not None:
                key = (int(tvshowid), int(season_num))
                details["watch_minutes"] = cached_watch_minutes(*key) or 0
                # GetSeasonDetails never returns watchedepisodes
                details["watchedepisodes"] = cached_watched_episodes(*key) or 0
                if show_due:
                    pending = key
        # after the show, which also writes the unified ListItem block
        set_season_properties(details)
        if pending:
            self._defer_watch_minutes(*pending, seasonid, "season")

    def _set_episode(self, episodeid: str) -> None:
        """Set episode properties for the focused item."""
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
