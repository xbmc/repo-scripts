"""Online data for a title: TMDB details plus OMDb, MDBList and Trakt ratings, as properties."""
from __future__ import annotations

from typing import Dict, Optional

import xbmc

from lib.data.database.cache import CacheKey
from lib.kodi.client import log
from lib.kodi.formatters import (
    format_default_rating,
    format_minutes,
    format_rating_props,
    build_common_sense_summary,
    RATING_SOURCE_NORMALIZE,
)
from lib.kodi.utilities import MULTI_VALUE_SEP


# MDBList only
_AWARD_PROPS = {
    "oscar-winner": "Awards.Oscar.Won",
    "oscar-nominated": "Awards.Oscar.Nominated",
    "best-picture-winner": "Awards.BestPicture.Won",
    "best-picture-nominated": "Awards.BestPicture.Nominated",
    "oscar-best-director-winner": "Awards.BestDirector.Won",
    "oscar-best-director-nominee": "Awards.BestDirector.Nominated",
    "golden-globe-winner": "Awards.GoldenGlobe.Won",
    "golden-globe-nominated": "Awards.GoldenGlobe.Nominated",
    "razzie-winner": "Awards.Razzie.Won",
    "razzie-nominee": "Awards.Razzie.Nominated",
    "emmy-award-winner": "Awards.Emmy.Won",
    "emmy-award-nominated": "Awards.Emmy.Nominated",
    "festival-cannes-winner": "Awards.Festival.Cannes",
    "festival-venice-winner": "Awards.Festival.Venice",
    "festival-sundance-winner": "Awards.Festival.Sundance",
    "festival-toronto-winner": "Awards.Festival.Toronto",
    "national-film-preservation-board-winner": "Awards.FilmRegistry",
    "national-film-registry": "Awards.FilmRegistry",
}

_STATUS_PROPS = {
    "tomatoes": "Tomatometer",
    "popcorn": "Popcornmeter",
    "metacritic": "Metacritic",
    "rogerebert": "RogerEbert",
}

_LIBRARY_NAMES = {
    "IMDBNumber": "UniqueID.IMDB",
    "TMDBID": "UniqueID.TMDB",
    "TVDBID": "UniqueID.TVDB",
    "Seasons": "Season",
    "Episodes": "Episode",
}


def fetch_omdb_data(media_type: str, imdb_id: str, abort_flag=None) -> Dict[str, str]:
    """Fetch OMDb awards, short plot and ratings (imdb/metacritic/rotten tomatoes) together."""
    from lib.data.api.omdb import ApiOmdb

    props: Dict[str, str] = {}

    if not imdb_id:
        return props

    if abort_flag and abort_flag.is_requested():
        return props

    try:
        omdb = ApiOmdb()
        data = (omdb.get_omdb_data(media_type, imdb_id)
                or omdb.fetch_data(media_type, imdb_id, abort_flag) or {})
        for key, field in (("Awards", "Awards"), ("PlotOutline", "Plot")):
            if data.get(field) and data[field] != "N/A":
                props[key] = data[field]

        ratings = omdb.fetch_ratings(media_type, {"imdb": imdb_id}, abort_flag=abort_flag)
        if ratings:
            for source, info in ratings.items():
                if isinstance(info, dict) and "rating" in info and "votes" in info:
                    props.update(format_rating_props(source, info["rating"], int(info["votes"])))
    except Exception as e:
        log("Service", f"OMDb fetch error: {e}", xbmc.LOGWARNING)

    return props


def fetch_mdblist_data(
    media_type: str,
    imdb_id: str,
    tmdb_id: str,
    is_episode: bool,
    abort_flag=None
) -> Dict[str, str]:
    """Fetch MDBList data (extra info, common sense, ratings)."""
    from lib.data.api.mdblist import ApiMdblist

    props: Dict[str, str] = {}

    if not imdb_id and not tmdb_id:
        return props

    if abort_flag and abort_flag.is_requested():
        return props

    mdblist_media_type = "tvshow" if is_episode else media_type

    try:
        mdblist = ApiMdblist()
        ids = {"imdb": imdb_id, "tmdb": tmdb_id}

        extra_data = mdblist.get_extra_data(mdblist_media_type, ids, abort_flag=abort_flag)
        if abort_flag and abort_flag.is_requested():
            return props
        if extra_data:
            if "trailer" in extra_data:
                props["MDBList.Trailer"] = extra_data["trailer"]
            if "certification" in extra_data:
                props["MDBList.Certification"] = extra_data["certification"]

        cs_data = mdblist.get_common_sense_data(mdblist_media_type, ids, abort_flag=abort_flag)
        if abort_flag and abort_flag.is_requested():
            return props
        if cs_data:
            props["CommonSense.Age"] = str(cs_data["age"])
            props["CommonSense.Violence"] = str(cs_data["violence"])
            props["CommonSense.Nudity"] = str(cs_data["nudity"])
            props["CommonSense.Language"] = str(cs_data["language"])
            props["CommonSense.Drinking"] = str(cs_data["drinking"])
            props["CommonSense.Selection"] = "true" if cs_data["selection"] else "false"

            summary, reasons = build_common_sense_summary(cs_data)
            if summary:
                props["CommonSense.Summary"] = summary
                props["CommonSense.Reasons"] = reasons

        service_ratings = mdblist.get_service_ratings(
            mdblist_media_type, ids, abort_flag=abort_flag
        )
        if abort_flag and abort_flag.is_requested():
            return props
        if service_ratings:
            for source, rating_data in service_ratings.items():
                if (
                    isinstance(rating_data, dict)
                    and "rating" in rating_data and "votes" in rating_data
                ):
                    normalized_source = RATING_SOURCE_NORMALIZE.get(source, source)
                    props.update(format_rating_props(
                        normalized_source, rating_data["rating"], int(rating_data["votes"])
                    ))

        status = mdblist.get_rating_status(mdblist_media_type, ids, abort_flag=abort_flag)
        for source, state in (status or {}).items():
            prop = _STATUS_PROPS.get(source)
            if prop:
                props[prop] = state

        for tag in mdblist.get_award_tags(mdblist_media_type, ids, abort_flag=abort_flag):
            prop = _AWARD_PROPS.get(tag)
            if prop:
                props[prop] = "true"

        score = mdblist.get_score(mdblist_media_type, ids, abort_flag=abort_flag)
        if score is not None:
            props.update(format_rating_props("mdblistscore", score, 0))

    except Exception as e:
        log("Service", f"MDBList fetch error: {e}", xbmc.LOGWARNING)

    return props


def fetch_trakt_data(
    media_type: str,
    imdb_id: str,
    tmdb_id: str,
    is_episode: bool,
    season: Optional[int],
    episode: Optional[int],
    abort_flag=None
) -> Dict[str, str]:
    """Fetch Trakt ratings and subgenres."""
    from lib.data.api.trakt import ApiTrakt

    props: Dict[str, str] = {}

    if not imdb_id and not tmdb_id:
        return props

    if abort_flag and abort_flag.is_requested():
        return props

    try:
        trakt = ApiTrakt()
        trakt_ids: Dict[str, str] = {"imdb": imdb_id or "", "tmdb": tmdb_id or ""}
        if is_episode and season is not None and episode is not None:
            trakt_ids["season"] = str(season)
            trakt_ids["episode"] = str(episode)

        trakt_ratings = trakt.fetch_ratings(media_type, trakt_ids, abort_flag=abort_flag)
        if abort_flag and abort_flag.is_requested():
            return props
        if trakt_ratings and "trakt" in trakt_ratings:
            trakt_data = trakt_ratings["trakt"]
            props.update(format_rating_props(
                "trakt", trakt_data["rating"], int(trakt_data["votes"])
            ))

        if not is_episode:
            trakt_id = imdb_id or tmdb_id
            subgenres = trakt.get_subgenres(trakt_id, media_type, abort_flag=abort_flag)
            if subgenres:
                props["Trakt.Subgenres"] = MULTI_VALUE_SEP.join(subgenres)
    except Exception as e:
        log("Service", f"Trakt fetch error: {e}", xbmc.LOGWARNING)

    return props


def fetch_all_online_data(media_type: str, imdb_id: str, tmdb_id: str,
                          abort_flag=None,
                          is_library_item: bool = True) -> Dict[str, str]:
    """Fetch TMDB details, OMDb, MDBList and Trakt ratings, plus derived props, as one flat dict."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from lib.data.api.tmdb import resolve_tmdb_id

    props: Dict[str, str] = {}
    is_episode = media_type == "episode"

    if abort_flag and abort_flag.is_requested():
        return props

    resolved_tmdb_id = resolve_tmdb_id(
        tmdb_id,
        imdb_id,
        "tvshow" if is_episode else media_type
    )

    if not imdb_id and not resolved_tmdb_id:
        return props

    if abort_flag and abort_flag.is_requested():
        return props

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {}

        if resolved_tmdb_id and not is_episode:
            futures[executor.submit(
                _fetch_tmdb_full_data,
                media_type,
                resolved_tmdb_id,
                abort_flag,
                is_library_item
            )] = "tmdb"

        if imdb_id and not is_episode:
            futures[executor.submit(
                fetch_omdb_data,
                media_type,
                imdb_id,
                abort_flag
            )] = "omdb"

        if (imdb_id or resolved_tmdb_id) and not is_episode:
            futures[executor.submit(
                fetch_mdblist_data,
                media_type,
                imdb_id,
                resolved_tmdb_id or "",
                is_episode,
                abort_flag
            )] = "mdblist"

        if imdb_id or resolved_tmdb_id:
            futures[executor.submit(
                fetch_trakt_data,
                media_type,
                imdb_id,
                resolved_tmdb_id or "",
                is_episode,
                None,
                None,
                abort_flag
            )] = "trakt"

        results: Dict[str, Dict[str, str]] = {}
        for future in as_completed(futures):
            if abort_flag and abort_flag.is_requested():
                executor.shutdown(wait=False)
                return props

            source = futures[future]
            try:
                result = future.result()
                if result:
                    results[source] = result
            except Exception as e:
                log("Service", f"Online fetch error ({source}): {e}", xbmc.LOGWARNING)

    # a later source wins a shared key, so MDBList's ratings override OMDb's
    for source in ("tmdb", "omdb", "mdblist", "trakt"):
        if source in results:
            props.update(results[source])

    return apply_derived_props(props, media_type, imdb_id, resolved_tmdb_id or "")


def _tomatoes_split(props: Dict[str, str]) -> None:
    """Set the tomatoes fresh and rotten review counts from its percent and votes."""
    try:
        percent = int(props.get("Rating.tomatoes.Percent") or "")
        votes = int((props.get("Rating.tomatoes.Votes") or "").replace(",", ""))
    except ValueError:
        percent = votes = 0
    if votes <= 0:
        props.pop("Rating.tomatoes.Fresh", None)
        props.pop("Rating.tomatoes.Rotten", None)
        return
    fresh = (percent * votes + 50) // 100
    props["Rating.tomatoes.Fresh"] = f"{fresh:,}"
    props["Rating.tomatoes.Rotten"] = f"{votes - fresh:,}"


def _runtime_split(props: Dict[str, str]) -> None:
    """Set the runtime hours and minutes from its total in minutes."""
    try:
        minutes = int(props.get("Runtime") or "")
    except ValueError:
        return
    props.update(format_minutes("Runtime", minutes))


def _primaries(props: Dict[str, str]) -> None:
    """Set the primary studio and genre, the first of each list."""
    for key in ("Studio", "Genre"):
        first = (props.get(key) or "").partition(MULTI_VALUE_SEP)[0]
        if first:
            props[f"{key}Primary"] = first


def _library_names(props: Dict[str, str]) -> None:
    """Copy each value the library sets under another name, such as its `UniqueID.*` keys."""
    for key, name in _LIBRARY_NAMES.items():
        if props.get(key):
            props[name] = props[key]


def apply_derived_props(props: Dict[str, str], media_type: str, imdb_id: str,
                        tmdb_id: str) -> Dict[str, str]:
    """Apply what is computed, not fetched: award counts, tomatoes split, library properties."""
    from lib.data.awards import apply_awards

    _tomatoes_split(props)
    _runtime_split(props)
    _primaries(props)
    _library_names(props)
    props.update(format_default_rating(props))
    return apply_awards(props, media_type, imdb_id, tmdb_id)


def fetch_tmdb_online_data(
    media_type: str,
    imdb_id: str,
    tmdb_id: str,
    abort_flag=None,
    is_library_item: bool = True
) -> Dict[str, str]:
    """Fetch only TMDB data and return as property dictionary."""
    from lib.data.api.tmdb import resolve_tmdb_id

    is_episode = media_type == "episode"

    if abort_flag and abort_flag.is_requested():
        return {}

    resolved_tmdb_id = resolve_tmdb_id(
        tmdb_id, imdb_id, "tvshow" if is_episode else media_type
    )
    if not resolved_tmdb_id or is_episode:
        return {}

    return _fetch_tmdb_full_data(
        media_type, resolved_tmdb_id, abort_flag, is_library_item=is_library_item
    ) or {}


def _fetch_tmdb_full_data(media_type: str, tmdb_id: str,
                          abort_flag=None,
                          is_library_item: bool = True) -> Dict[str, str]:
    """Fetch TMDB metadata and format as a property dict via `lib.kodi.formatters`."""
    from lib.data.api.tmdb import ApiTmdb
    from lib.kodi.formatters import (
        format_rating_props,
        format_movie_props,
        format_tvshow_props,
        format_credits_props,
        format_images_props,
        format_extra_props,
    )

    props: Dict[str, str] = {}

    if abort_flag and abort_flag.is_requested():
        return props

    try:
        api = ApiTmdb()
        data = api.get_complete_data(
            media_type, int(tmdb_id), abort_flag=abort_flag, is_library_item=is_library_item
        )

        if abort_flag and abort_flag.is_requested():
            return props

        if not data:
            return props

        if media_type == "movie":
            props.update(format_movie_props(data))
        else:
            props.update(format_tvshow_props(data))

        vote_avg = data.get("vote_average")
        vote_cnt = data.get("vote_count")
        if vote_avg is not None and vote_cnt is not None:
            props.update(format_rating_props("tmdb", float(vote_avg), int(vote_cnt)))

        props.update(format_credits_props(data))
        props.update(format_images_props(data))
        props.update(format_extra_props(data))

    except Exception as e:
        log("Service", f"TMDb full fetch error: {e}", xbmc.LOGWARNING)

    return props


def get_online_ttl(media_type: str, tmdb_id: str) -> int:
    """Get the online-properties TTL from the title's cached TMDB data, 72 hours without it."""
    from lib.data.database.cache import get_title_ttl_hours

    return get_title_ttl_hours(media_type, tmdb_id) or 72


def make_cache_key(media_type: str, imdb_id: str, tmdb_id: str,
                   scope: str = '') -> Optional[CacheKey]:
    """Build a cache key on the TMDB id, the IMDb id when there is none."""
    item_id = tmdb_id or imdb_id
    return CacheKey(media_type, item_id, scope) if item_id else None


def show_scoped_props(props: Dict[str, str]) -> Dict[str, str]:
    """Move a show's ratings, statuses and counts under `TVShow.`, for its episode or season."""
    scoped = set(_STATUS_PROPS.values()) | {"Rating", "Votes", "Season", "Episode"}
    return {f"TVShow.{key}" if key.startswith("Rating.") or key in scoped else key: value
            for key, value in props.items()}
