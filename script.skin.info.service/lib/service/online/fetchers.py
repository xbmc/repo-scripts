"""Public fetchers for online data: combined TMDB + ratings, TMDB-only, music helpers."""
from __future__ import annotations

from typing import Dict, List, Optional, TYPE_CHECKING

import xbmc

from lib.kodi.client import log

if TYPE_CHECKING:
    from lib.service.online.main import ServiceAbortFlag


def fetch_all_online_data(media_type: str, imdb_id: str, tmdb_id: str,
                          abort_flag: Optional['ServiceAbortFlag'] = None,
                          is_library_item: bool = True) -> Dict[str, str]:
    """Fetch TMDB details + ratings (OMDb/MDBList/Trakt) and return as flat property dict.

    `is_library_item=False` shortens TTL to 24h and skips season fetches.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from lib.data.api.tmdb import resolve_tmdb_id
    from lib.plugin.online import (
        fetch_omdb_data,
        fetch_mdblist_data,
        fetch_trakt_data,
    )

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

        if imdb_id:
            futures[executor.submit(
                fetch_omdb_data,
                media_type,
                imdb_id,
                abort_flag
            )] = "omdb"

        if imdb_id or resolved_tmdb_id:
            futures[executor.submit(
                fetch_mdblist_data,
                media_type,
                imdb_id,
                resolved_tmdb_id or "",
                is_episode,
                abort_flag
            )] = "mdblist"

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

    # Merge in priority order: MDBList (richer aggregator) wins shared rating keys, OMDb
    # only backfills.
    for source in ("tmdb", "omdb", "mdblist", "trakt"):
        if source in results:
            props.update(results[source])

    return props


def fetch_tmdb_online_data(
    media_type: str,
    imdb_id: str,
    tmdb_id: str,
    abort_flag: Optional['ServiceAbortFlag'] = None,
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
                          abort_flag: Optional['ServiceAbortFlag'] = None,
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


def get_playing_artist_mbids() -> List[str]:
    """Return MusicBrainz artist IDs for the currently playing audio (or `[]`)."""
    try:
        player = xbmc.Player()
        if not player.isPlayingAudio():
            return []
        tag = player.getMusicInfoTag()
        mbids = tag.getMusicBrainzArtistID()
        if isinstance(mbids, list):
            return [m for m in mbids if m]
        return []
    except Exception:
        return []
