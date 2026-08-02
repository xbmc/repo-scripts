"""Library ID operations - lookup, update, and fix missing/invalid IDs."""
from __future__ import annotations

from typing import Dict, List, Optional, Set
import xbmc
import xbmcgui

from lib.kodi.client import (
    request, get_library_items, log, extract_result,
    KODI_SET_DETAILS_METHODS, KODI_ID_KEYS, ADDON,
)
from lib.data.api.tmdb import ApiTmdb, resolve_tmdb_id
from lib.data.api.utilities import is_valid_tmdb_id
from lib.data.api.imdb import get_imdb_dataset
from lib.data.database import cache as db_cache
from lib.data.database._infrastructure import init_database
from lib.data.database import imdb as db_imdb
from lib.infrastructure.dialogs import show_ok, show_notification, show_yesno, DialogProgress


def get_imdb_id_from_tmdb(media_type: str, uniqueid: Dict,
                          season: Optional[int] = None,
                          episode: Optional[int] = None) -> Optional[str]:
    """Resolve IMDb ID via cached metadata -> TMDB API (by TMDB ID) -> TMDB `/find` (by TVDB ID)."""
    tmdb_id = uniqueid.get("tmdb")
    tvdb_id = uniqueid.get("tvdb")

    if not tmdb_id and not tvdb_id:
        return None

    tmdb_client = ApiTmdb()

    cache_media_type = "tvshow" if media_type == "episode" else media_type

    if not tmdb_id and tvdb_id:
        from lib.data.database.mapping import get_tmdb_id_by_tvdb
        tmdb_id = get_tmdb_id_by_tvdb(str(tvdb_id), cache_media_type)
        if not tmdb_id:
            find_type = "episode" if media_type == "episode" else media_type
            result = tmdb_client.find_by_external_id(str(tvdb_id), "tvdb_id", find_type)
            if result:
                tmdb_id = str(result.get("id") or result.get("show_id", ""))
                if media_type == "episode" and result.get("show_id"):
                    tmdb_id = str(result["show_id"])

    if not tmdb_id:
        return None

    if media_type != "episode":
        from lib.data.database.mapping import get_imdb_id
        mapped_imdb = get_imdb_id(tmdb_id, cache_media_type)
        if mapped_imdb:
            return mapped_imdb

    cached = db_cache.get_cached_metadata(cache_media_type, tmdb_id)

    if cached:
        if media_type == "episode" and season is not None and episode is not None:
            pass
        else:
            external_ids = cached.get("external_ids", {})
            imdb_id = external_ids.get("imdb_id")
            if imdb_id:
                return imdb_id

    try:
        if media_type == "movie":
            data = tmdb_client.get_movie_details_extended(int(tmdb_id))
        elif media_type == "tvshow":
            data = tmdb_client.get_tv_details_extended(int(tmdb_id))
        elif media_type == "episode" and season is not None and episode is not None:
            data = tmdb_client.get_episode_details_extended(int(tmdb_id), season, episode)
        else:
            return None

        if data:
            external_ids = data.get("external_ids", {})
            imdb_id = external_ids.get("imdb_id")

            if media_type != "episode":
                release_date = data.get("release_date") or data.get("first_air_date")
                db_cache.cache_metadata(media_type, tmdb_id, data, release_date)

            if not imdb_id:
                if media_type == "episode":
                    log(
                        "Ratings",
                        f"TMDB has no IMDb ID for episode "
                        f"(tmdb={tmdb_id}, S{season:02d}E{episode:02d})",
                        xbmc.LOGDEBUG,
                    )
                else:
                    log(
                        "Ratings",
                        f"TMDB has no IMDb ID for {media_type} (tmdb={tmdb_id})",
                        xbmc.LOGDEBUG,
                    )

            return imdb_id

        if media_type == "episode" and tvdb_id:
            log(
                "Ratings",
                f"TMDB lookup failed for episode "
                f"(tmdb={tmdb_id}, S{season:02d}E{episode:02d}), trying TVDB fallback",
                xbmc.LOGDEBUG,
            )
            return _try_tvdb_episode_fallback(tmdb_client, str(tvdb_id))
        if media_type == "episode":
            log(
                "Ratings",
                f"TMDB lookup failed for episode "
                f"(tmdb={tmdb_id}, S{season:02d}E{episode:02d}), no TVDB ID for fallback",
                xbmc.LOGDEBUG,
            )
        else:
            log(
                "Ratings",
                f"TMDB lookup failed for {media_type} (tmdb={tmdb_id})",
                xbmc.LOGDEBUG,
            )

    except Exception as e:
        log("Ratings", f"Error fetching TMDB data for IMDb ID lookup: {e}", xbmc.LOGWARNING)

    return None


def _try_tvdb_episode_fallback(tmdb_client: ApiTmdb, tvdb_id: str) -> Optional[str]:
    """Resolve episode IMDb ID via TMDB `/find` by-tvdb when direct TMDB lookup misses."""
    result = tmdb_client.find_by_external_id(tvdb_id, "tvdb_id", "episode")
    if not result:
        log("Ratings", f"TVDB fallback failed for episode (tvdb={tvdb_id})", xbmc.LOGDEBUG)
        return None

    found_show_id = result.get("show_id")
    found_season = result.get("season_number")
    found_episode = result.get("episode_number")
    if not (found_show_id and found_season is not None and found_episode is not None):
        return None

    ep_data = tmdb_client.get_episode_details_extended(found_show_id, found_season, found_episode)
    if not ep_data:
        log(
            "Ratings",
            f"TVDB fallback episode details fetch failed (tvdb={tvdb_id})",
            xbmc.LOGDEBUG,
        )
        return None

    imdb_id = ep_data.get("external_ids", {}).get("imdb_id")
    if imdb_id:
        return imdb_id
    log("Ratings", f"TVDB fallback found episode but no IMDb ID (tvdb={tvdb_id})", xbmc.LOGDEBUG)
    return None


def update_kodi_uniqueid(media_type: str, dbid: int, uniqueid: Dict, imdb_id: str) -> bool:
    """Convenience wrapper: set the `imdb` field on a Kodi uniqueid dict."""
    return update_kodi_uniqueid_field(media_type, dbid, uniqueid, "imdb", imdb_id)


def update_kodi_uniqueid_field(media_type: str, dbid: int, uniqueid: Dict,
                               field: str, value: str) -> bool:
    """Set a single `uniqueid` field on a Kodi library item via `SetXDetails` JSON-RPC."""
    method_info = KODI_SET_DETAILS_METHODS.get(media_type)
    if not method_info:
        return False
    method, id_key = method_info

    new_uniqueid = dict(uniqueid)
    new_uniqueid[field] = value

    response = request(method, {id_key: dbid, "uniqueid": new_uniqueid})
    if response:
        log("Ratings", f"Updated {media_type} {dbid} {field}={value}", xbmc.LOGDEBUG)
        return True

    return False


def run_fix_library_ids(prompt: bool = True) -> None:
    """Fix missing IMDb IDs (via TMDB or IMDb dataset) and invalid TMDB IDs (via IMDb lookup)."""
    init_database()

    progress = DialogProgress()
    progress.create(ADDON.getLocalizedString(32260), ADDON.getLocalizedString(32350))

    movies = get_library_items(["movie"], properties=["title", "year", "uniqueid"])
    progress.update(20, ADDON.getLocalizedString(32351))
    shows = get_library_items(["tvshow"], properties=["title", "uniqueid"])
    progress.update(40, ADDON.getLocalizedString(32352))
    episodes = get_library_items(
        ["episode"], properties=["title", "season", "episode", "tvshowid", "uniqueid"]
    )

    progress.update(60, ADDON.getLocalizedString(32353))

    missing_imdb_movies: List[Dict] = []
    invalid_tmdb_movies: List[Dict] = []

    for movie in movies:
        uniqueid = movie.get("uniqueid", {})
        imdb_id = uniqueid.get("imdb")
        tmdb_id = str(uniqueid.get("tmdb", "")) if uniqueid.get("tmdb") else ""

        if not imdb_id and is_valid_tmdb_id(tmdb_id):
            missing_imdb_movies.append({
                "movieid": movie.get("movieid"),
                "title": movie.get("title"),
                "year": movie.get("year"),
                "uniqueid": uniqueid
            })
        elif imdb_id and tmdb_id and not is_valid_tmdb_id(tmdb_id):
            invalid_tmdb_movies.append({
                "movieid": movie.get("movieid"),
                "title": movie.get("title"),
                "year": movie.get("year"),
                "imdb_id": imdb_id,
                "invalid_tmdb": tmdb_id,
                "uniqueid": uniqueid
            })

    missing_imdb_shows: List[Dict] = []
    invalid_tmdb_shows: List[Dict] = []
    show_imdb_map: Dict[int, str] = {}
    show_tmdb_map: Dict[int, str] = {}

    for show in shows:
        tvshowid = show.get("tvshowid")
        uniqueid = show.get("uniqueid", {})
        imdb_id = uniqueid.get("imdb")
        tmdb_id = str(uniqueid.get("tmdb", "")) if uniqueid.get("tmdb") else ""

        if tvshowid:
            if imdb_id:
                show_imdb_map[tvshowid] = imdb_id
            if tmdb_id and is_valid_tmdb_id(tmdb_id):
                show_tmdb_map[tvshowid] = tmdb_id

        if not imdb_id and is_valid_tmdb_id(tmdb_id):
            missing_imdb_shows.append({
                "tvshowid": tvshowid,
                "title": show.get("title"),
                "uniqueid": uniqueid
            })
        elif imdb_id and tmdb_id and not is_valid_tmdb_id(tmdb_id):
            invalid_tmdb_shows.append({
                "tvshowid": tvshowid,
                "title": show.get("title"),
                "imdb_id": imdb_id,
                "invalid_tmdb": tmdb_id,
                "uniqueid": uniqueid
            })

    missing_imdb_episodes: List[Dict] = []
    user_show_ids: Set[str] = set()
    for ep in episodes:
        if not ep.get("uniqueid", {}).get("imdb"):
            tvshowid: int | None = ep.get("tvshowid")
            show_imdb = show_imdb_map.get(tvshowid) if tvshowid else None
            show_tmdb = show_tmdb_map.get(tvshowid) if tvshowid else None
            if show_imdb or show_tmdb:
                if show_imdb:
                    user_show_ids.add(show_imdb)
                missing_imdb_episodes.append({
                    "episodeid": ep.get("episodeid"),
                    "title": ep.get("title"),
                    "season": ep.get("season"),
                    "episode": ep.get("episode"),
                    "tvshowid": tvshowid,
                    "show_imdb": show_imdb,
                    "show_tmdb": show_tmdb,
                    "uniqueid": ep.get("uniqueid", {})
                })

    progress.close()

    total_missing_imdb = (
        len(missing_imdb_movies) + len(missing_imdb_shows) + len(missing_imdb_episodes)
    )
    total_invalid_tmdb = len(invalid_tmdb_movies) + len(invalid_tmdb_shows)

    if total_missing_imdb == 0 and total_invalid_tmdb == 0:
        show_notification(
            ADDON.getLocalizedString(32260),
            ADDON.getLocalizedString(32261),
            xbmcgui.NOTIFICATION_INFO,
            3000,
        )
        return

    if prompt:
        lines = []

        if total_missing_imdb > 0:
            parts = []
            if missing_imdb_movies:
                parts.append(f"{len(missing_imdb_movies):,} movies")
            if missing_imdb_shows:
                parts.append(f"{len(missing_imdb_shows):,} TV shows")
            if missing_imdb_episodes:
                parts.append(f"{len(missing_imdb_episodes):,} episodes")
            lines.append(f"Missing IMDb IDs: {', '.join(parts)}")

        if total_invalid_tmdb > 0:
            parts = []
            if invalid_tmdb_movies:
                parts.append(f"{len(invalid_tmdb_movies):,} movies")
            if invalid_tmdb_shows:
                parts.append(f"{len(invalid_tmdb_shows):,} TV shows")
            lines.append(f"Invalid TMDB IDs: {', '.join(parts)}")

        message = "\n".join(lines) + "\n\nFix these issues?"

        if not show_yesno(ADDON.getLocalizedString(32260), message):
            return

    progress = DialogProgress()
    progress.create(ADDON.getLocalizedString(32260), "Starting...")

    total_imdb_fixed = 0
    total_tmdb_fixed = 0

    if invalid_tmdb_movies or invalid_tmdb_shows:
        tmdb_fixed = _fix_invalid_tmdb_ids(
            invalid_tmdb_movies + invalid_tmdb_shows,
            progress
        )
        total_tmdb_fixed = tmdb_fixed

    if missing_imdb_movies and not progress.iscanceled():
        matched = _fix_missing_ids_via_tmdb(missing_imdb_movies, "movie", progress, "movies")
        total_imdb_fixed += matched

    if missing_imdb_shows and not progress.iscanceled():
        matched = _fix_missing_ids_via_tmdb(
            missing_imdb_shows, "tvshow", progress, "TV shows", show_imdb_map
        )
        total_imdb_fixed += matched

    # Refresh show_imdb mapping for episodes whose shows were just fixed
    for ep in missing_imdb_episodes:
        tvshowid = ep.get("tvshowid")
        if tvshowid and tvshowid in show_imdb_map:
            ep["show_imdb"] = show_imdb_map[tvshowid]
            user_show_ids.add(show_imdb_map[tvshowid])

    if missing_imdb_episodes and not progress.iscanceled():
        total_imdb_fixed += _fix_missing_episode_ids(
            missing_imdb_episodes, user_show_ids, progress
        )

    progress.close()

    if total_imdb_fixed > 0 or total_tmdb_fixed > 0:
        results = []
        if total_imdb_fixed > 0:
            results.append(f"Added {total_imdb_fixed:,} IMDb IDs")
        if total_tmdb_fixed > 0:
            results.append(f"Fixed {total_tmdb_fixed:,} TMDB IDs")
        show_ok(ADDON.getLocalizedString(32260), "\n".join(results))
        xbmc.executebuiltin("Container.Refresh")
    else:
        show_ok(ADDON.getLocalizedString(32260), ADDON.getLocalizedString(32359))


def _fix_invalid_tmdb_ids(items: List[Dict], progress: xbmcgui.DialogProgress) -> int:
    """Fix invalid TMDB IDs by looking up correct ID via IMDb."""
    if not items:
        return 0

    fixed = 0
    total = len(items)
    last_percent = -1
    update_interval = max(1, total // 100)

    for i, item in enumerate(items):
        if progress.iscanceled():
            break

        if i % update_interval == 0:
            percent = int((i / total) * 100)
            if percent != last_percent:
                progress.update(
                    percent,
                    ADDON.getLocalizedString(32357).format(f"{i + 1:,}", f"{total:,}"),
                )
                last_percent = percent

        imdb_id = item.get("imdb_id")
        if not imdb_id:
            continue

        if "movieid" in item:
            media_type = "movie"
            dbid = item["movieid"]
        elif "tvshowid" in item:
            media_type = "tvshow"
            dbid = item["tvshowid"]
        else:
            continue

        corrected_tmdb = resolve_tmdb_id(None, imdb_id, media_type)

        if corrected_tmdb and is_valid_tmdb_id(corrected_tmdb):
            if update_kodi_uniqueid_field(
                media_type, dbid, item["uniqueid"], "tmdb", corrected_tmdb
            ):
                fixed += 1
                log(
                    "Ratings",
                    f"Fixed TMDB ID for {item.get('title', 'unknown')}: "
                    f"{item.get('invalid_tmdb')} -> {corrected_tmdb}",
                )

    return fixed


def _fix_missing_ids_via_tmdb(items: List[Dict], media_type: str,
                              progress: xbmcgui.DialogProgress, label: str,
                              id_map: Optional[Dict[int, str]] = None) -> int:
    """Fill missing IMDb IDs on movies/shows from TMDB. `id_map` populated for tvshows."""
    matched = 0
    total = len(items)
    last_percent = -1
    update_interval = max(1, total // 100)
    id_key = KODI_ID_KEYS[media_type]

    for i, item in enumerate(items):
        if progress.iscanceled():
            break

        if i % update_interval == 0:
            percent = int((i / total) * 100)
            if percent != last_percent:
                progress.update(
                    percent,
                    ADDON.getLocalizedString(32358).format(label, f"{i + 1:,}", f"{total:,}"),
                )
                last_percent = percent

        imdb_id = get_imdb_id_from_tmdb(media_type, item["uniqueid"])
        if imdb_id:
            if update_kodi_uniqueid(media_type, item[id_key], item["uniqueid"], imdb_id):
                matched += 1
                if id_map is not None and media_type == "tvshow":
                    id_map[item[id_key]] = imdb_id

    return matched


def _fix_missing_episode_ids(episodes: List[Dict], user_show_ids: Set[str],
                             progress: xbmcgui.DialogProgress) -> int:
    """Fill episode IMDb IDs via IMDb dataset bulk lookup, then per-episode TMDB fallback."""
    progress.update(0, ADDON.getLocalizedString(32354))

    def progress_callback(status: str):
        progress.update(50, status)

    dataset = get_imdb_dataset()
    result = dataset.refresh_episode_dataset(user_show_ids, progress_callback=progress_callback)

    fixed = 0
    unmatched: List[Dict] = []

    if result >= 0:
        total = len(episodes)
        last_percent = -1
        update_interval = max(1, total // 100)

        with db_imdb.bulk_episode_lookup() as lookup_episode:
            for i, ep in enumerate(episodes):
                if progress.iscanceled():
                    break

                if i % update_interval == 0:
                    percent = int((i / total) * 100)
                    if percent != last_percent:
                        progress.update(
                            percent,
                            ADDON.getLocalizedString(32355).format(f"{i + 1:,}", f"{total:,}"),
                        )
                        last_percent = percent

                if ep["show_imdb"]:
                    ep_imdb = lookup_episode(
                        ep["show_imdb"],
                        ep["season"],
                        ep["episode"]
                    )

                    if ep_imdb:
                        if update_kodi_uniqueid(
                            "episode", ep["episodeid"], ep["uniqueid"], ep_imdb
                        ):
                            fixed += 1
                        continue

                if ep.get("show_tmdb"):
                    unmatched.append(ep)

    if unmatched and not progress.iscanceled():
        total = len(unmatched)
        last_percent = -1
        update_interval = max(1, total // 100)

        for i, ep in enumerate(unmatched):
            if progress.iscanceled():
                break

            if i % update_interval == 0:
                percent = int((i / total) * 100)
                if percent != last_percent:
                    progress.update(
                        percent,
                        ADDON.getLocalizedString(32356).format(f"{i + 1:,}", f"{total:,}"),
                    )
                    last_percent = percent

            show_tmdb = ep.get("show_tmdb")
            ep_tvdb = ep.get("uniqueid", {}).get("tvdb")
            if show_tmdb or ep_tvdb:
                ep_imdb = get_imdb_id_from_tmdb(
                    "episode",
                    {"tmdb": show_tmdb, "tvdb": ep_tvdb},
                    ep["season"],
                    ep["episode"]
                )
                if ep_imdb:
                    if update_kodi_uniqueid("episode", ep["episodeid"], ep["uniqueid"], ep_imdb):
                        fixed += 1

    return fixed


_tvshow_uniqueid_cache: Dict[int, Dict[str, str]] = {}


def clear_tvshow_uniqueid_cache() -> None:
    """Clear the tvshow uniqueid cache. Call at the start of batch operations."""
    _tvshow_uniqueid_cache.clear()


def prefetch_tvshow_uniqueids(tvshow_ids: Optional[Set[int]] = None) -> None:
    """Pre-fetch all TV show uniqueids in one request to populate the cache.

    `tvshow_ids` skips the request entirely when every wanted show is already cached.
    """
    if tvshow_ids is not None and not (set(tvshow_ids) - set(_tvshow_uniqueid_cache)):
        return
    response = request("VideoLibrary.GetTVShows", {"properties": ["uniqueid"]})
    if not response:
        return
    shows = extract_result(response, 'tvshows', [])
    for show in shows:
        tvshowid = show.get("tvshowid")
        uniqueid = show.get("uniqueid", {})
        if tvshowid:
            _tvshow_uniqueid_cache[tvshowid] = uniqueid
    log("Ratings", f"Pre-fetched uniqueids for {len(shows)} TV shows", xbmc.LOGDEBUG)


def get_tvshow_uniqueid(tvshow_dbid: int) -> Dict[str, str]:
    """Fetch a TV show's uniqueid dict, cached to avoid refetching per episode."""
    if tvshow_dbid in _tvshow_uniqueid_cache:
        return _tvshow_uniqueid_cache[tvshow_dbid]

    response = request("VideoLibrary.GetTVShowDetails", {
        "tvshowid": tvshow_dbid,
        "properties": ["uniqueid"]
    })
    if response and "tvshowdetails" in response.get("result", {}):
        uniqueid = response["result"]["tvshowdetails"].get("uniqueid", {})
        _tvshow_uniqueid_cache[tvshow_dbid] = uniqueid
        return uniqueid

    _tvshow_uniqueid_cache[tvshow_dbid] = {}
    return {}


def build_external_ids(ids: Dict) -> Dict[str, str]:
    """Build the external_ids dict for database sync from a resolved ids dict."""
    external_ids: Dict[str, str] = {}
    imdb_id = ids.get("imdb_episode") or ids.get("imdb")
    if imdb_id:
        external_ids["imdb"] = str(imdb_id)
    tmdb_id = ids.get("tmdb")
    if tmdb_id:
        external_ids["themoviedb"] = str(tmdb_id)
        external_ids["tmdb"] = str(tmdb_id)
    return external_ids
