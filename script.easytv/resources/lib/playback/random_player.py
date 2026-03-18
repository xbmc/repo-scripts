#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Original work Copyright (C) 2013 KODeKarnage
#  Modified work Copyright (C) 2024-2026 Rouzax
#
#  SPDX-License-Identifier: GPL-3.0-or-later
#  See LICENSE.txt for more information.
#

"""
EasyTV Random Playlist Builder.

Builds and plays a randomized "channel surfing" playlist of TV episodes
and optionally movies. Creates an experience similar to traditional TV
where content plays continuously in random order.

Extracted from default.py as part of modularization.

Logging:
    Logger: 'playback' (via get_logger)
    Key events:
        - playlist.create (INFO): Playlist generation started
        - playlist.start (INFO): Playlist playback started
        - playlist.parse_fail (WARNING): Failed to parse episode data
    See LOGGING.md for full guidelines.
"""
from __future__ import annotations

import ast
import json
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

import xbmc
import xbmcgui

from resources.lib.constants import (
    KODI_HOME_WINDOW_ID,
    PLAYLIST_BUILD_BREAK_VALUE,
    EPISODE_SELECTION_UNWATCHED,
    EPISODE_SELECTION_WATCHED,
    EPISODE_SELECTION_BOTH,
    PREMIERE_MIX_IN,
    PREMIERE_ONLY,
    PREMIERE_SKIP,
    PROP_PLAYLIST_CONFIG,
    LAZY_QUEUE_BUFFER_SIZE,
    PROP_PLAYLIST_RUNNING,
    PROP_RANDOM_ORDER_SHUFFLE,
)
from resources.lib.data.queries import (
    get_clear_video_playlist_query,
    build_add_episode_query,
    build_add_movie_query,
    build_random_movies_query,
    build_random_episodes_query,
    build_inprogress_episodes_query,
    build_inprogress_movies_query,
    get_episode_filter,
)
from resources.lib.data.shows import (
    find_next_episode,
    fetch_unwatched_shows,
    fetch_shows_with_watched_episodes,
    extract_showids_from_playlist,
    extract_movieids_from_playlist,
    filter_shows_by_duration,
    validate_duration_settings,
)
from resources.lib.playback.playlist_session import PlaylistSession, calculate_movie_target
from resources.lib.data.storage import get_storage
from resources.lib.utils import get_logger, json_query, log_timing, busy_progress

if TYPE_CHECKING:
    from resources.lib.utils import StructuredLogger


# Module-level logger (initialized lazily)
_log: Optional[StructuredLogger] = None


def _get_log() -> StructuredLogger:
    """Get or create the module logger."""
    global _log
    if _log is None:
        _log = get_logger('playback')
    return _log


# Shared window reference for property access
WINDOW = xbmcgui.Window(KODI_HOME_WINDOW_ID)

# Playlist content type constants - single source of truth
CONTENT_TV_ONLY = 0
CONTENT_MIXED = 1
CONTENT_MOVIES_ONLY = 2


@dataclass
class RandomPlaylistConfig:
    """
    Configuration for the random playlist builder.
    
    Attributes:
        length: Target number of items in the playlist
        playlist_content: Content type (CONTENT_TV_ONLY=0, CONTENT_MIXED=1, CONTENT_MOVIES_ONLY=2)
        episode_selection: Which episodes to include (0=unwatched, 1=watched, 2=both)
        movie_selection: Which movies to include (0=unwatched, 1=watched, 2=both)
        movie_chance: Percentage of playlist that should be movies (0-100), only applies to CONTENT_MIXED
        start_partials_tv: Whether to prioritize partially watched TV episodes
        start_partials_movies: Whether to prioritize partially watched movies
        premieres: Series premiere filter mode (PREMIERE_SKIP=0, PREMIERE_MIX_IN=1, PREMIERE_ONLY=2)
        season_premieres: Season premiere filter mode (PREMIERE_SKIP=0, PREMIERE_MIX_IN=1, PREMIERE_ONLY=2)
        multiple_shows: Whether the same show can appear multiple times
        sort_by: Sort method for shows (0=name, 1=last played, 2=random)
        sort_reverse: Whether to reverse the sort order
        language: System language for sorting
        movie_playlist: Optional path to movie playlist filter (None = all movies)
        unwatched_ratio: Chance of picking unwatched vs watched in "Both" mode (0-100)
        duration_filter_enabled: Whether to filter shows by episode duration
        duration_min: Minimum episode duration in minutes (0 = no minimum)
        duration_max: Maximum episode duration in minutes (0 = no maximum)
    """
    length: int = 10
    playlist_content: int = CONTENT_MIXED
    episode_selection: int = 0  # 0=unwatched, 1=watched, 2=both
    movie_selection: int = 0  # 0=unwatched, 1=watched, 2=both
    movie_chance: int = 25
    start_partials_tv: bool = True
    start_partials_movies: bool = True
    premieres: int = PREMIERE_MIX_IN
    season_premieres: int = PREMIERE_MIX_IN
    multiple_shows: bool = False
    sort_by: int = 0
    sort_reverse: bool = False
    language: str = 'English'
    movie_playlist: Optional[str] = None
    unwatched_ratio: int = 50  # 0-100, used when episode_selection is BOTH
    duration_filter_enabled: bool = False
    duration_min: int = 0
    duration_max: int = 0


def _serialize_playlist_config(config: RandomPlaylistConfig) -> Dict[str, Any]:
    """
    Serialize a RandomPlaylistConfig to a dictionary for storage.
    
    Used for both lazy queue sessions and playlist continuation state.
    
    Args:
        config: The playlist configuration to serialize.
    
    Returns:
        Dictionary with all config fields suitable for JSON serialization.
    """
    return {
        'length': config.length,
        'playlist_content': config.playlist_content,
        'episode_selection': config.episode_selection,
        'movie_selection': config.movie_selection,
        'movie_chance': config.movie_chance,
        'start_partials_tv': config.start_partials_tv,
        'start_partials_movies': config.start_partials_movies,
        'premieres': config.premieres,
        'season_premieres': config.season_premieres,
        'multiple_shows': config.multiple_shows,
        'sort_by': config.sort_by,
        'sort_reverse': config.sort_reverse,
        'language': config.language,
        'movie_playlist': config.movie_playlist,
        'unwatched_ratio': config.unwatched_ratio,
        'duration_filter_enabled': config.duration_filter_enabled,
        'duration_min': config.duration_min,
        'duration_max': config.duration_max,
    }


def filter_shows_by_population(
    population: dict,
    sort_by: int,
    sort_reverse: bool,
    language: str,
    episode_selection: int = EPISODE_SELECTION_UNWATCHED,
    logger: Optional[StructuredLogger] = None
) -> list:
    """
    Filter shows based on population criteria and episode selection mode.
    
    Retrieves shows based on the episode_selection mode and optionally filters
    them based on a smart playlist or user-selected show list.
    
    Args:
        population: Dict with one of:
            - {'playlist': path} - Filter by smart playlist contents
            - {'usersel': [show_ids]} - Filter by user-selected shows
            - {'none': ''} - No filtering
        sort_by: Sort method (0=name, 1=last played, 2=random)
        sort_reverse: Whether to reverse sort order
        language: System language for sorting
        episode_selection: Which episodes to include:
            - 0 (UNWATCHED): Only shows with unwatched episodes
            - 1 (WATCHED): Only shows with watched episodes  
            - 2 (BOTH): Shows with either unwatched or watched episodes
        logger: Optional logger instance
    
    Returns:
        List of [lastplayed_timestamp, showid, episode_id] for matching shows.
        For watched-only shows, episode_id will be empty (selected on-demand).
    """
    log = logger or _get_log()
    
    # Fetch shows based on episode selection mode
    if episode_selection == EPISODE_SELECTION_UNWATCHED:
        # Unwatched only - use service cache (fast path)
        stored_data = fetch_unwatched_shows(sort_by, sort_reverse, language)
        log.debug("Fetched shows with unwatched episodes", count=len(stored_data))
        
    elif episode_selection == EPISODE_SELECTION_WATCHED:
        # Watched only - query directly
        stored_data = fetch_shows_with_watched_episodes(sort_by, sort_reverse, language)
        log.debug("Fetched shows with watched episodes", count=len(stored_data))
        
    else:
        # Both - merge unwatched and watched show lists
        unwatched_shows = fetch_unwatched_shows(sort_by, sort_reverse, language)
        watched_shows = fetch_shows_with_watched_episodes(sort_by, sort_reverse, language)
        
        # Merge lists, avoiding duplicates (prefer unwatched entry as it has episode_id)
        unwatched_ids = {x[1] for x in unwatched_shows}
        watched_only = [x for x in watched_shows if x[1] not in unwatched_ids]
        
        stored_data = unwatched_shows + watched_only
        log.debug("Fetched shows for both mode", 
                 unwatched=len(unwatched_shows), 
                 watched_only=len(watched_only),
                 total=len(stored_data))
    
    log.debug("Processing stored show data")
    
    if 'playlist' in population:
        extracted_showlist = extract_showids_from_playlist(population['playlist'])
        # If playlist extraction returned empty, return empty (filter failed)
        if not extracted_showlist:
            log.debug("Playlist extraction returned no shows, returning empty")
            return []
    elif 'usersel' in population:
        extracted_showlist = population['usersel']
    else:
        extracted_showlist = None  # No filter configured
    
    if extracted_showlist is not None:
        stored_data_filtered = [x for x in stored_data if x[1] in extracted_showlist]
    else:
        stored_data_filtered = stored_data
    
    log.debug("Stored data processing complete", count=len(stored_data_filtered))
    
    return stored_data_filtered


def _fetch_movies(
    movie_selection: int,
    limit: Optional[int] = None,
    movie_ids: Optional[List[int]] = None,
    logger: Optional[StructuredLogger] = None
) -> List[int]:
    """
    Fetch movie IDs based on watch status settings.

    Uses server-side random sorting for better performance when a limit
    is specified, avoiding the need to fetch and shuffle all movies.

    When movie_ids is provided (from a playlist filter), fetches all movies
    matching watch status (ignoring limit), then intersects with the playlist.
    The limit is applied after intersection to respect the movie chance setting.
    
    Args:
        movie_selection: Which movies to include (0=unwatched, 1=watched, 2=both)
        limit: Optional maximum number of movies to return (ignored when movie_ids provided)
        movie_ids: Optional list of movie IDs to filter by (from playlist)
        logger: Logger instance
    
    Returns:
        List of movie IDs, randomly sorted by the server.
    """
    log = logger or _get_log()
    
    # Get the appropriate filter for the selection mode
    watch_filter = get_episode_filter(movie_selection)
    filters = [watch_filter] if watch_filter else []
    
    # When playlist filter is active, don't limit the query - we need to
    # fetch all movies matching watch status, then intersect with playlist.
    # Otherwise the limit could exclude valid playlist matches.
    query_limit = None if movie_ids is not None else limit
    
    # Use optimized query with server-side random sort
    query = build_random_movies_query(filters=filters, limit=query_limit)
    mov = json_query(query, True)
    
    if 'movies' in mov and mov['movies']:
        movie_list = [x['movieid'] for x in mov['movies']]
        
        # If movie_ids filter is provided, intersect with fetched list
        if movie_ids is not None:
            movie_id_set = set(movie_ids)
            movie_list = [m for m in movie_list if m in movie_id_set]
            # Apply limit after intersection to respect movie chance
            if limit is not None and len(movie_list) > limit:
                movie_list = movie_list[:limit]
            log.debug("Movies filtered by playlist",
                     total_fetched=len(mov['movies']),
                     after_filter=len(movie_list))
        else:
            log.debug("Movies found", count=len(movie_list), limit=limit)
        
        return movie_list
    
    return []


def _fetch_random_episode_for_show(
    show_id: int,
    episode_selection: int,
    exclude_episode_ids: Optional[List[int]] = None,
    logger: Optional[StructuredLogger] = None
) -> Optional[int]:
    """
    Fetch a random episode ID from a specific show based on episode selection.
    
    Uses server-side random sorting and the episode selection filter to
    efficiently get a random episode without loading all episodes.
    
    This is used when episode_selection is WATCHED or BOTH, since the
    service only caches unwatched episodes in Window properties.
    
    Args:
        show_id: The TV show ID
        episode_selection: Which episodes to include (0=unwatched, 1=watched, 2=both)
        exclude_episode_ids: Optional list of episode IDs to exclude
        logger: Logger instance
    
    Returns:
        Episode ID or None if no matching episodes found.
    """
    log = logger or _get_log()
    
    # Get the appropriate filter for the selection mode
    watch_filter = get_episode_filter(episode_selection)
    filters = [watch_filter] if watch_filter else []
    
    # Query with server-side random sort, get a few extras in case we need to exclude some
    limit = 5 if exclude_episode_ids else 1
    query = build_random_episodes_query(tvshowid=show_id, filters=filters, limit=limit)
    result = json_query(query, True)
    
    if 'episodes' in result and result['episodes']:
        for ep in result['episodes']:
            episode_id = ep['episodeid']
            if exclude_episode_ids and episode_id in exclude_episode_ids:
                continue
            log.debug("Random episode fetched", show_id=show_id, episode_id=episode_id)
            return episode_id
    
    return None


def _find_all_partial_episodes(
    show_ids: List[int],
    logger: StructuredLogger
) -> List[Tuple[str, int, int, int, str]]:
    """
    Find all genuinely in-progress TV episodes from the given shows.

    Uses Kodi's efficient 'inprogress' filter to find all episodes with
    resume points in a single query (~94ms), then filters client-side to
    only include genuinely in-progress episodes (playcount == 0).

    Episodes with playcount > 0 and a resume point are stale artifacts
    (Kodi marked them watched but didn't clear the resume point) and are
    excluded regardless of the episode_selection mode.

    Args:
        show_ids: List of TV show IDs to check
        logger: Logger instance

    Returns:
        List of tuples: (lastplayed, tvshowid, season, episode, episodeid)
        for genuinely in-progress episodes (playcount == 0, resume > 0).
    """
    if not show_ids:
        return []
    
    # Convert to set for O(1) lookup
    show_id_set = set(show_ids)
    
    # Single bulk query for all in-progress episodes
    query = build_inprogress_episodes_query()
    with log_timing(logger, "inprogress_episodes_query") as timer:
        result = json_query(query, True)
        timer.mark("query")
    
    if 'episodes' not in result or not result['episodes']:
        logger.debug("No in-progress episodes found in library")
        return []
    
    # Filter by show_ids and watch status
    partial_episodes: List[Tuple[str, int, int, int, str]] = []
    
    for ep in result['episodes']:
        tvshowid = ep.get('tvshowid', 0)
        
        # Skip if not in our show set
        if tvshowid not in show_id_set:
            continue
        
        # Only genuinely in-progress episodes qualify (playcount == 0).
        # Episodes with playcount > 0 have stale resume points.
        playcount = ep.get('playcount', 0)
        if playcount > 0:
            continue
        
        partial_episodes.append((
            ep.get('lastplayed', ''),
            tvshowid,
            ep.get('season', 0),
            ep.get('episode', 0),
            str(ep.get('episodeid', 0))
        ))
    
    logger.debug("Found partial episodes", 
                 total_inprogress=len(result['episodes']),
                 matching=len(partial_episodes),
                 shows_checked=len(show_id_set))
    return partial_episodes


def _find_all_partial_movies(
    movie_ids: Optional[List[int]],
    logger: StructuredLogger
) -> List[Tuple[str, int]]:
    """
    Find all genuinely in-progress movies.

    Uses Kodi's efficient 'inprogress' filter to find all movies with
    resume points in a single query (~109ms), then filters client-side to
    only include genuinely in-progress movies (playcount == 0).

    Movies with playcount > 0 and a resume point are stale artifacts
    and are excluded regardless of the movie_selection mode.

    Args:
        movie_ids: Optional list of movie IDs to filter by (from playlist).
                   If None, checks all movies.
        logger: Logger instance

    Returns:
        List of tuples: (lastplayed, movieid)
        for genuinely in-progress movies (playcount == 0, resume > 0).
    """
    # Single bulk query for all in-progress movies
    query = build_inprogress_movies_query()
    with log_timing(logger, "inprogress_movies_query") as timer:
        result = json_query(query, True)
        timer.mark("query")
    
    if 'movies' not in result or not result['movies']:
        logger.debug("No in-progress movies found in library")
        return []
    
    # Filter by playlist movie_ids and watch status
    partial_movies: List[Tuple[str, int]] = []
    movie_id_set = set(movie_ids) if movie_ids is not None else None
    
    for movie in result['movies']:
        movie_id = movie.get('movieid', 0)
        
        # Skip if not in playlist filter
        if movie_id_set is not None and movie_id not in movie_id_set:
            continue
        
        # Only genuinely in-progress movies qualify (playcount == 0).
        # Movies with playcount > 0 have stale resume points.
        playcount = movie.get('playcount', 0)
        if playcount > 0:
            continue
        
        partial_movies.append((
            movie.get('lastplayed', ''),
            movie_id
        ))
    
    logger.debug("Found partial movies", 
                 total_inprogress=len(result['movies']),
                 matching=len(partial_movies),
                 playlist_filter=movie_id_set is not None)
    return partial_movies


def _sort_partials_for_priority(
    partial_episodes: List[Tuple[str, int, int, int, str]],
    partial_movies: List[Tuple[str, int]],
    logger: StructuredLogger
) -> Tuple[List[str], Dict[int, int]]:
    """
    Sort partial items for playlist prioritization.

    Combines TV episodes and movies, sorts by recency (lastplayed descending).
    For episodes from the same show, maintains episode order (season, episode).

    Also builds a partial_episode_map that maps show_id to the specific
    episode_id that should be served on first encounter. For shows with
    multiple partial episodes, the earliest by (season, episode) is used.

    Args:
        partial_episodes: List of (lastplayed, tvshowid, season, episode, episodeid)
        partial_movies: List of (lastplayed, movieid)
        logger: Logger instance

    Returns:
        Tuple of:
        - List of candidate tags in priority order: 't{showid}' or 'm{movieid}'
        - Dict mapping show_id (int) to episode_id (int) for partial TV episodes
    """
    if not partial_episodes and not partial_movies:
        return [], {}
    
    # Group episodes by show and find most recent per show
    show_episodes: Dict[int, List[Tuple[str, int, int, str]]] = {}
    show_most_recent: Dict[int, str] = {}
    
    for lastplayed, showid, season, episode, epid in partial_episodes:
        if showid not in show_episodes:
            show_episodes[showid] = []
            show_most_recent[showid] = lastplayed
        show_episodes[showid].append((lastplayed, season, episode, epid))
        # Track most recent lastplayed for this show
        if lastplayed > show_most_recent[showid]:
            show_most_recent[showid] = lastplayed
    
    # Sort episodes within each show by episode order (season, episode)
    for showid in show_episodes:
        show_episodes[showid].sort(key=lambda x: (x[1], x[2]))  # season, episode
    
    # Build combined list with recency info
    # For TV: use show's most recent lastplayed for sorting, but keep all episodes
    # Format: (lastplayed, type, id, sub_items)
    combined: List[Tuple[str, str, int, List]] = []
    
    for showid, most_recent in show_most_recent.items():
        # sub_items contains episode info for maintaining order
        combined.append((most_recent, 't', showid, show_episodes[showid]))
    
    for lastplayed, movieid in partial_movies:
        combined.append((lastplayed, 'm', movieid, []))
    
    # Sort by recency (descending)
    combined.sort(key=lambda x: x[0], reverse=True)
    
    # Build final candidate list and partial episode map
    result: List[str] = []
    partial_episode_map: Dict[int, int] = {}
    for _, item_type, item_id, sub_items in combined:
        if item_type == 't':
            # For TV shows with multiple partial episodes, add show once
            # (the playlist building logic handles multiple episodes)
            result.append(f't{item_id}')
            # Use the earliest episode (already sorted by season, episode)
            if sub_items:
                partial_episode_map[item_id] = int(sub_items[0][3])
        else:
            result.append(f'm{item_id}')

    logger.debug("Sorted partials for priority",
                 tv_shows=len([x for x in result if x.startswith('t')]),
                 movies=len([x for x in result if x.startswith('m')]),
                 episode_map_size=len(partial_episode_map))
    return result, partial_episode_map


def _process_tv_candidate(
    show_id: int,
    added_ep_dict: dict,
    candidate_list: List[str],
    random_order_shows: List[int],
    config: RandomPlaylistConfig,
    logger: StructuredLogger,
    partial_episode_map: Optional[Dict[int, int]] = None
) -> Tuple[Optional[int], bool]:
    """
    Process a TV show candidate for playlist addition.

    Args:
        show_id: The TV show ID
        added_ep_dict: Dict tracking added episodes per show
        candidate_list: List of remaining candidates (modified in place)
        random_order_shows: List of show IDs with random episode order
        config: Playlist configuration (includes episode_selection)
        logger: Logger instance
        partial_episode_map: Optional map of show_id → episode_id for shows
            with genuinely in-progress episodes. On first encounter, the
            specific partial episode is served directly.

    Returns:
        Tuple of (episode_id, is_multi_episode) or (None, False) if skipped.
    """
    candidate_tag = f't{show_id}'
    
    if show_id in added_ep_dict:
        # Show already added to playlist
        if config.multiple_shows:
            # Find next episode for multi-episode mode
            # For watched/both mode, use library query; for unwatched, use cached data
            if config.episode_selection == EPISODE_SELECTION_UNWATCHED:
                # Use existing sequential/random order logic with cached data
                tmp_episode_id, tmp_details = find_next_episode(
                    show_id, random_order_shows,
                    epid=added_ep_dict[show_id][3],
                    eps=added_ep_dict[show_id][2]
                )
                
                if tmp_episode_id is None:
                    if candidate_tag in candidate_list:
                        candidate_list.remove(candidate_tag)
                    return None, False
                
                return int(tmp_episode_id), True
            elif config.episode_selection == EPISODE_SELECTION_WATCHED:
                # Query for another random watched episode
                # Exclude already-used episodes from this show
                used_episodes = added_ep_dict[show_id][2] if added_ep_dict[show_id][2] else []
                if added_ep_dict[show_id][3]:
                    used_episodes = [added_ep_dict[show_id][3]] + list(used_episodes)
                
                tmp_episode_id = _fetch_random_episode_for_show(
                    show_id, EPISODE_SELECTION_WATCHED,
                    exclude_episode_ids=used_episodes, logger=logger
                )
                
                if tmp_episode_id is None:
                    if candidate_tag in candidate_list:
                        candidate_list.remove(candidate_tag)
                    return None, False
                
                return tmp_episode_id, True
            else:
                # BOTH mode: use state dict to track on-deck and watched usage
                state = added_ep_dict[show_id]
                
                # Handle legacy list format (upgrade safety)
                if isinstance(state, list):
                    # Convert old format to new state dict
                    state = {
                        'ondeck_used': True,  # Assume used since we can't know
                        'ondeck_id': state[3] if state[3] else None,
                        'watched_used': list(state[2]) if state[2] else []
                    }
                    added_ep_dict[show_id] = state
                
                # Get on-deck episode ID from window property (may still be available)
                ondeck_id_str = WINDOW.getProperty(f"EasyTV.{show_id}.EpisodeID")
                ondeck_available = bool(ondeck_id_str) and not state.get('ondeck_used', False)
                ondeck_id = int(ondeck_id_str) if ondeck_id_str else None
                
                # Get watched exclusion list
                watched_used = state.get('watched_used', [])
                
                # Use unwatched_ratio setting (0-100) to determine preference
                prefer_unwatched = random.randint(1, 100) <= config.unwatched_ratio
                
                if prefer_unwatched and ondeck_available:
                    # Use the on-deck episode (appears only once per show)
                    state['ondeck_used'] = True
                    return ondeck_id, True
                else:
                    # Try to get a random watched episode
                    tmp_episode_id = _fetch_random_episode_for_show(
                        show_id, EPISODE_SELECTION_WATCHED,
                        exclude_episode_ids=watched_used, logger=logger
                    )
                    
                    if tmp_episode_id is not None:
                        return tmp_episode_id, True
                    elif ondeck_available:
                        # No more watched episodes, fall back to on-deck
                        state['ondeck_used'] = True
                        return ondeck_id, True
                    else:
                        # Both sources exhausted - remove from candidates
                        if candidate_tag in candidate_list:
                            candidate_list.remove(candidate_tag)
                        return None, False
        else:
            # Not multi-episode mode, skip this show
            return None, False
    else:
        # First episode from this show

        # Check if this show has a specific partial episode to serve
        if partial_episode_map and show_id in partial_episode_map:
            tmp_episode_id = partial_episode_map[show_id]
            logger.debug("Serving partial episode directly",
                         show_id=show_id, episode_id=tmp_episode_id)

            if not config.multiple_shows:
                if candidate_tag in candidate_list:
                    candidate_list.remove(candidate_tag)

            return tmp_episode_id, False

        # Get episode based on selection mode
        if config.episode_selection == EPISODE_SELECTION_UNWATCHED:
            # Use cached next unwatched episode from service
            episode_id_str = WINDOW.getProperty(f"EasyTV.{show_id}.EpisodeID")
            if not episode_id_str:
                if candidate_tag in candidate_list:
                    candidate_list.remove(candidate_tag)
                return None, False
            tmp_episode_id = int(episode_id_str)
        elif config.episode_selection == EPISODE_SELECTION_WATCHED:
            # Query library for a random watched episode
            tmp_episode_id = _fetch_random_episode_for_show(
                show_id, EPISODE_SELECTION_WATCHED, logger=logger
            )
            if tmp_episode_id is None:
                if candidate_tag in candidate_list:
                    candidate_list.remove(candidate_tag)
                return None, False
        else:
            # BOTH mode: randomly choose between on-deck unwatched OR random watched
            # This preserves sequential order for unwatched episodes
            episode_id_str = WINDOW.getProperty(f"EasyTV.{show_id}.EpisodeID")
            has_unwatched = bool(episode_id_str)
            
            # Use unwatched_ratio setting (0-100) to determine choice
            if has_unwatched and random.randint(1, 100) <= config.unwatched_ratio:
                # Use the next sequential unwatched episode
                tmp_episode_id = int(episode_id_str)
            else:
                # Query for a random watched episode
                tmp_episode_id = _fetch_random_episode_for_show(
                    show_id, EPISODE_SELECTION_WATCHED, logger=logger
                )
                if tmp_episode_id is None:
                    # No watched episodes, fall back to unwatched if available
                    if has_unwatched:
                        tmp_episode_id = int(episode_id_str)
                    else:
                        if candidate_tag in candidate_list:
                            candidate_list.remove(candidate_tag)
                        return None, False
        
        if not config.multiple_shows:
            # Remove from candidates if not allowing multiple
            if candidate_tag in candidate_list:
                candidate_list.remove(candidate_tag)
        
        return tmp_episode_id, False


def _check_premiere_exclusion(
    show_id: int,
    candidate_list: List[str],
    config: RandomPlaylistConfig,
    logger: StructuredLogger
) -> bool:
    """
    Check if episode should be excluded due to premiere settings.

    Each premiere type has three modes: SKIP (exclude), MIX_IN (normal),
    ONLY (premieres-only). When either type is ONLY, non-premiere episodes
    are excluded and the other selector controls which premiere types appear.

    Args:
        show_id: The TV show ID
        candidate_list: List of remaining candidates (modified in place)
        config: Playlist configuration
        logger: Logger instance

    Returns:
        True if episode should be excluded, False otherwise.
    """
    only_mode = (config.premieres == PREMIERE_ONLY
                 or config.season_premieres == PREMIERE_ONLY)

    # Fast path: both MIX_IN and no ONLY → nothing to filter
    if not only_mode and config.premieres == PREMIERE_MIX_IN and config.season_premieres == PREMIERE_MIX_IN:
        return False

    episode_no = WINDOW.getProperty(f"EasyTV.{show_id}.EpisodeNo")
    if not episode_no:
        # Can't determine episode type; exclude in ONLY mode, keep otherwise
        return _remove_candidate(show_id, candidate_list) if only_mode else False

    # Parse episode number (format: 's01e01', 's02e05', etc.)
    try:
        season_num = int(episode_no[1:3])
        episode_num = int(episode_no[4:6])
    except (ValueError, IndexError):
        return _remove_candidate(show_id, candidate_list) if only_mode else False

    is_premiere = (episode_num == 1)

    if only_mode:
        # Non-premieres are always excluded in ONLY mode
        if not is_premiere:
            return _remove_candidate(show_id, candidate_list)
        # Check if this specific premiere type is allowed
        if season_num == 1 and config.premieres == PREMIERE_SKIP:
            return _remove_candidate(show_id, candidate_list)
        if season_num > 1 and config.season_premieres == PREMIERE_SKIP:
            return _remove_candidate(show_id, candidate_list)
        return False
    else:
        # Normal mode: only SKIP excludes premieres
        if not is_premiere:
            return False
        if season_num == 1 and config.premieres == PREMIERE_SKIP:
            return _remove_candidate(show_id, candidate_list)
        if season_num > 1 and config.season_premieres == PREMIERE_SKIP:
            return _remove_candidate(show_id, candidate_list)
        return False


def _remove_candidate(show_id: int, candidate_list: List[str]) -> bool:
    """Remove a show from the candidate list and return True (excluded)."""
    candidate_tag = f't{show_id}'
    if candidate_tag in candidate_list:
        candidate_list.remove(candidate_tag)
    return True


def _update_added_dict(
    show_id: int,
    added_ep_dict: dict,
    random_order_shows: List[int],
    is_multi: bool,
    tmp_details: Optional[list],
    config: RandomPlaylistConfig,
    episode_id: Optional[int] = None
) -> None:
    """
    Update the added episodes dictionary after adding an episode.
    
    The dict structure varies by episode_selection mode:
    - Unwatched: [season, episode, eps_list, episode_id] for sequential tracking
    - Watched: [season, episode, used_list, episode_id] for duplicate prevention  
    - Both: {'ondeck_used': bool, 'ondeck_id': int, 'watched_used': list}
      This state dict ensures on-deck appears at most once and watched episodes
      don't repeat within a single playlist.
    
    Args:
        show_id: The TV show ID
        added_ep_dict: Dict tracking added episodes (modified in place)
        random_order_shows: List of show IDs with random episode order
        is_multi: Whether this is a multi-episode add
        tmp_details: Details from find_next_episode if multi (unwatched mode only)
        config: Playlist configuration
        episode_id: The episode ID that was just added (for watched/both modes)
    """
    if is_multi and tmp_details:
        # Multi-episode with details from find_next_episode (unwatched mode)
        added_ep_dict[show_id] = [
            tmp_details[0], tmp_details[1],
            tmp_details[2], tmp_details[3]
        ]
    elif is_multi and config.episode_selection == EPISODE_SELECTION_BOTH:
        # Multi-episode for Both mode - update watched_used in state dict
        # Note: ondeck_used is already updated in _process_tv_candidate
        if show_id in added_ep_dict and isinstance(added_ep_dict[show_id], dict):
            state = added_ep_dict[show_id]
            watched_used = state.get('watched_used', [])
            # Only add to watched_used if this is a watched episode (not on-deck)
            ondeck_id = state.get('ondeck_id')
            if episode_id and episode_id != ondeck_id and episode_id not in watched_used:
                state['watched_used'] = watched_used + [episode_id]
    elif is_multi and config.episode_selection == EPISODE_SELECTION_WATCHED:
        # Multi-episode for Watched mode - track used episodes
        if show_id in added_ep_dict and added_ep_dict[show_id]:
            # Add the new episode to the used list
            used_list = added_ep_dict[show_id][2] or []
            if episode_id and episode_id not in used_list:
                used_list = list(used_list) + [episode_id]
            added_ep_dict[show_id][2] = used_list
            added_ep_dict[show_id][3] = episode_id
    elif config.multiple_shows:
        # First episode from this show, set up for potential future additions
        if config.episode_selection == EPISODE_SELECTION_UNWATCHED:
            # Use cached episode lists from service
            if show_id in random_order_shows:
                ondeck = WINDOW.getProperty(f"EasyTV.{show_id}.ondeck_list")
                offdeck = WINDOW.getProperty(f"EasyTV.{show_id}.offdeck_list")
                try:
                    eps_list = ast.literal_eval(ondeck) + ast.literal_eval(offdeck)
                except (ValueError, SyntaxError):
                    eps_list = []
            else:
                ondeck = WINDOW.getProperty(f"EasyTV.{show_id}.ondeck_list")
                try:
                    eps_list = ast.literal_eval(ondeck)
                except (ValueError, SyntaxError):
                    eps_list = []
            
            added_ep_dict[show_id] = [
                WINDOW.getProperty(f"EasyTV.{show_id}.Season"),
                WINDOW.getProperty(f"EasyTV.{show_id}.Episode"),
                eps_list,
                WINDOW.getProperty(f"EasyTV.{show_id}.EpisodeID")
            ]
        elif config.episode_selection == EPISODE_SELECTION_BOTH:
            # Both mode: use state dict to track on-deck and watched usage
            ondeck_id_str = WINDOW.getProperty(f"EasyTV.{show_id}.EpisodeID")
            ondeck_id = int(ondeck_id_str) if ondeck_id_str else None
            
            # Determine if the first episode used was the on-deck
            used_ondeck = (episode_id == ondeck_id) if episode_id and ondeck_id else False
            
            added_ep_dict[show_id] = {
                'ondeck_used': used_ondeck,
                'ondeck_id': ondeck_id,
                'watched_used': [] if used_ondeck else ([episode_id] if episode_id else [])
            }
        else:
            # Watched mode: track the first episode
            # We'll query for more episodes as needed
            added_ep_dict[show_id] = [
                '', '',  # Season/episode not needed for library queries
                [episode_id] if episode_id else [],  # Used episodes list
                episode_id
            ]
    else:
        added_ep_dict[show_id] = ''


def _build_lazy_queue_playlist(
    population: dict,
    random_order_shows: list,
    config: RandomPlaylistConfig,
    candidate_list: list,
    logger: StructuredLogger,
    partial_episode_map: Optional[Dict[int, int]] = None,
    addon_id: Optional[str] = None
) -> None:
    """
    Build a lazy queue playlist for Both mode.

    Instead of building the full playlist upfront, creates a small initial
    buffer (LAZY_QUEUE_BUFFER_SIZE items) and relies on the playback monitor
    to replenish as episodes are watched. This allows on-deck episodes to
    progress naturally as content is consumed.

    The key difference from batch mode is that on-deck episodes can appear
    multiple times for the same show, advancing as each episode is watched
    (e.g., S02E05 → S02E06 → S02E07).

    Args:
        population: Show population filter dict
        random_order_shows: List of show IDs with random episode order
        config: Playlist configuration
        candidate_list: Shuffled list of candidates like ['t123', 'm456']
        logger: Logger instance
        partial_episode_map: Optional map of show_id → episode_id for shows
            with genuinely in-progress episodes. Passed through to the
            PlaylistSession for first-encounter serving.

    Side Effects:
        - Creates PlaylistSession and saves to window property
        - Adds initial buffer items to video playlist
        - Sets 'EasyTV.playlist_running' to 'true'
        - Sets 'EasyTV.random_order_shuffle' to 'true'
        - Starts playlist playback via xbmc.Player
    """
    log = logger
    
    with log_timing(log, "lazy_queue_build",
                    buffer_size=LAZY_QUEUE_BUFFER_SIZE,
                    target_length=config.length) as timer:
        # Serialize config for session storage
        config_dict = _serialize_playlist_config(config)
        
        # Clear any existing lazy queue session
        PlaylistSession.clear()
        
        # Create new session
        session = PlaylistSession.create(
            config=config_dict,
            population=population,
            random_order_shows=random_order_shows,
            candidate_list=candidate_list.copy(),  # Copy to avoid mutation
            target_length=config.length,
            partial_episode_map=partial_episode_map
        )
        timer.mark("session_create")
        
        # Pick initial buffer items
        items_added = 0
        buffer_target = min(LAZY_QUEUE_BUFFER_SIZE, config.length)
        
        while items_added < buffer_target:
            result = session.pick_next_item()
            if result is None:
                # No more candidates available
                log.debug("Lazy queue exhausted during initial build",
                          items_added=items_added,
                          buffer_target=buffer_target)
                break
            
            item_type, item_id = result
            
            # Add to playlist
            if item_type == 'episode':
                json_query(build_add_episode_query(item_id), False)
            elif item_type == 'movie':
                json_query(build_add_movie_query(item_id), False)
            
            items_added += 1
        
        timer.mark("initial_buffer")
        
        # Save session state for playback monitor to use
        session.save()
        
        # Notify service that playlist is running
        WINDOW.setProperty(PROP_PLAYLIST_RUNNING, 'true')
        WINDOW.setProperty(PROP_RANDOM_ORDER_SHUFFLE, 'true')
        
        # Also store config for playlist continuation (same as batch mode)
        playlist_state = {
            'addon_id': addon_id,
            'population': population,
            'random_order_shows': random_order_shows,
            'config': config_dict
        }
        WINDOW.setProperty(PROP_PLAYLIST_CONFIG, json.dumps(playlist_state))
        
        # Start playback
        xbmc.Player().play(xbmc.PlayList(1))
        
        log.info("Lazy queue playlist started",
                 event="playlist.lazy_queue_start",
                 initial_items=items_added,
                 target_length=config.length,
                 candidates_remaining=len(session.candidate_list))


def build_random_playlist(
    population: dict,
    random_order_shows: List[int],
    config: RandomPlaylistConfig,
    logger: Optional[StructuredLogger] = None,
    addon_id: Optional[str] = None
) -> None:
    """
    Build and play a randomized playlist of TV episodes and optionally movies.
    
    Creates a "channel surfing" experience by randomly selecting episodes
    from available TV shows and movies, then playing them as a playlist.
    
    Episode Selection:
        The episode_selection setting controls which TV episodes are included:
        - 0 (unwatched): Only unwatched episodes (default, matches original behavior)
        - 1 (watched): Only watched episodes (for re-watching favorites)
        - 2 (both): Any episode regardless of watch status
        
        For unwatched mode, uses cached data from the service for efficiency.
        For watched/both modes, queries the library directly with server-side
        random sorting for optimal performance.
    
    Movie Chance:
        The movie_chance setting (0-100%) controls what fraction of the playlist
        should be movies:
        - 0%: No movies, only TV episodes
        - 25%: 5 movies in a 20-item playlist (default)
        - 50%: Equal mix of movies and TV episodes
        - 100%: All movies

        Formula: movie_target = round(length * movie_chance / 100)
        Budget enforcement ensures the final playlist respects this target.
    
    Candidate Selection:
        1. Filters shows based on population parameter (playlist/user selection)
        2. Retrieves movies based on movie_selection (unwatched/watched/both)
        3. Creates candidate list with prefixed IDs: 't123' for TV, 'm456' for movie
        4. Shuffles combined list for random order
        5. Optionally prioritizes genuinely in-progress items (start_partials_tv/movies)
           - Only playcount == 0 with resume point qualifies (stale resume on
             watched episodes is ignored)
           - Sorts by recency (lastplayed), same-show episodes in episode order
           - Moves all partials to front of candidate list
           - Builds partial_episode_map (show_id → episode_id) so the specific
             partial episode is served on first encounter
    
    Playlist Building:
        - Loops until 'length' items added or all candidates exhausted
        - For TV: adds episode based on episode_selection, tracks for multi-episode
        - For movies: adds movie, removes from candidate pool (no duplicates)
        - Skips premiere episodes (S01E01) if 'premieres' setting is false
        - For 'multiple_shows' mode: same show can appear multiple times
    
    Args:
        population: Dict with filter mode:
            - {'playlist': path} - Filter by smart playlist
            - {'usersel': [ids]} - Filter by user selection
            - {'none': ''} - No filtering
        random_order_shows: List of show IDs with random episode ordering
        config: RandomPlaylistConfig with all playlist settings (including episode_selection)
        logger: Optional logger instance
    
    Side Effects:
        - Clears existing video playlist
        - Sets 'EasyTV.playlist_running' to 'true'
        - Sets 'EasyTV.random_order_shuffle' to 'true'
        - Starts playlist playback via xbmc.Player
    """
    log = logger or _get_log()
    
    with log_timing(log, "random_playlist_build", 
                   playlist_content=config.playlist_content,
                   length=config.length) as outer_timer:
        # Show loading indicator during data fetching operations
        with busy_progress("Building playlist..."):
            # Skip TV show fetching for Movies Only mode
            if config.playlist_content == CONTENT_MOVIES_ONLY:
                stored_data_filtered = []
            else:
                # Get filtered show data based on episode selection mode
                stored_data_filtered = filter_shows_by_population(
                    population, config.sort_by, config.sort_reverse, config.language,
                    episode_selection=config.episode_selection, logger=log
                )
                
                # Apply duration filter if enabled
                if config.duration_filter_enabled and stored_data_filtered:
                    if validate_duration_settings(config.duration_min, config.duration_max):
                        stored_data_filtered = filter_shows_by_duration(
                            stored_data_filtered,
                            config.duration_min,
                            config.duration_max
                        )
                
                # Refresh from shared storage if stale (multi-instance sync)
                if stored_data_filtered:
                    storage = get_storage()
                    if storage.needs_refresh():
                        show_ids = [show[1] for show in stored_data_filtered]
                        log.debug("Cache stale, refreshing before playlist build",
                                 event="playlist.refresh", show_count=len(show_ids))
                        try:
                            _, revision = storage.get_ondeck_bulk(show_ids, refresh_display=True)
                            storage.mark_refreshed(revision)
                        except Exception as e:
                            log.warning("Refresh failed, using cached data",
                                       event="playlist.refresh_error", error=str(e))
            
            outer_timer.mark("show_fetch")
            
            log.debug("Building random playlist")
            
            # Clear existing playlist
            json_query(get_clear_video_playlist_query(), False)
            
            added_ep_dict: dict = {}
            count = 0
            iterations = 0  # Track total iterations for summary
            
            # Determine movie inclusion based on playlist content type
            include_movies = config.playlist_content != CONTENT_TV_ONLY
            
            # Get show count for movie limit calculation
            stored_show_count = len(stored_data_filtered)
            
            # Fetch movies if enabled, with appropriate limit
            movie_list: List[int] = []
            if include_movies:
                # Calculate movie limit based on content type and chance
                if config.playlist_content == CONTENT_MOVIES_ONLY:
                    # Movies only: fetch up to playlist length
                    movie_limit = config.length
                else:
                    # Mixed mode: percentage-based target
                    movie_limit = calculate_movie_target(config.movie_chance, config.length)
                
                if movie_limit > 0:
                    # Extract movie IDs from playlist if filter is set
                    playlist_movie_ids: Optional[List[int]] = None
                    if config.movie_playlist:
                        playlist_movie_ids = extract_movieids_from_playlist(config.movie_playlist)
                        log.debug("Movie playlist filter applied", 
                                 playlist=config.movie_playlist, 
                                 movie_count=len(playlist_movie_ids))
                    
                    # Use optimized fetch with server-side random and limit
                    movie_list = _fetch_movies(
                        config.movie_selection, 
                        limit=movie_limit, 
                        movie_ids=playlist_movie_ids,
                        logger=log
                    )
            
            # Handle content-type specific logic
            if config.playlist_content == CONTENT_MOVIES_ONLY:
                # Movies only: clear TV shows
                stored_data_filtered = []
                stored_show_count = 0
            elif config.playlist_content == CONTENT_TV_ONLY:
                # TV only: ensure no movies
                movie_list = []
            
            # Log with content type name for clarity
            content_names = ["TV only", "TV and movies", "Movies only"]
            movie_target = calculate_movie_target(config.movie_chance, config.length) if config.playlist_content == CONTENT_MIXED else len(movie_list)
            log.info("Random playlist starting", event="playlist.create",
                     content=content_names[config.playlist_content],
                     target_length=config.length,
                     shows=stored_show_count, movies=len(movie_list),
                     movie_target=movie_target)
            
            outer_timer.mark("movie_fetch")
            
            # Build candidate list with type prefixes
            candidate_list = (
                [f't{x[1]}' for x in stored_data_filtered] +
                [f'm{x}' for x in movie_list]
            )
            random.shuffle(candidate_list)
            
            # Handle partial prioritization - find all partial items and move to front
            partial_episode_map: Dict[int, int] = {}
            if config.start_partials_tv or config.start_partials_movies:
                with log_timing(log, "partial_prioritization", 
                               tv_enabled=config.start_partials_tv,
                               movies_enabled=config.start_partials_movies) as timer:
                    # Get show IDs for TV partial search
                    tv_show_ids = [int(x[1:]) for x in candidate_list if x.startswith('t')]
                    
                    # Find partial episodes (if TV partials enabled and we have TV content)
                    partial_episodes: List[Tuple[str, int, int, int, str]] = []
                    if config.start_partials_tv and tv_show_ids:
                        partial_episodes = _find_all_partial_episodes(
                            tv_show_ids, log
                        )
                        timer.mark("tv_episodes_query")
                    
                    # Find partial movies (if movie partials enabled and we have movies)
                    partial_movies: List[Tuple[str, int]] = []
                    if config.start_partials_movies and movie_list:
                        # Get movie IDs from playlist filter if set
                        playlist_movie_ids: Optional[List[int]] = None
                        if config.movie_playlist:
                            playlist_movie_ids = extract_movieids_from_playlist(config.movie_playlist)
                        partial_movies = _find_all_partial_movies(
                            playlist_movie_ids, log
                        )
                        timer.mark("movies_query")
                    
                    # Sort partials by recency and rebuild candidate list
                    if partial_episodes or partial_movies:
                        sorted_partials, partial_episode_map = _sort_partials_for_priority(
                            partial_episodes, partial_movies, log
                        )
                        timer.mark("sort")
                        
                        # Remove partial items from shuffled list and prepend sorted partials
                        partial_set = set(sorted_partials)
                        non_partial_candidates = [c for c in candidate_list if c not in partial_set]
                        candidate_list = sorted_partials + non_partial_candidates
                        
                        log.debug("Partials prioritized", 
                                 partial_count=len(sorted_partials),
                                 remaining=len(non_partial_candidates))
            
            outer_timer.mark("partial_priority")
        
        # Busy indicator now closed - ready for playlist building
        
        # Both mode with multiple_shows uses lazy queue for on-deck progression
        # This allows the same show to appear multiple times with its on-deck
        # episode advancing naturally as content is watched (S02E05 → S02E06 → ...)
        if (config.episode_selection == EPISODE_SELECTION_BOTH and 
            config.multiple_shows and 
            config.playlist_content != CONTENT_MOVIES_ONLY):
            log.debug("Using lazy queue for Both mode",
                      event="playlist.lazy_queue_mode",
                      candidates=len(candidate_list))
            _build_lazy_queue_playlist(
                population, random_order_shows, config, candidate_list, log,
                partial_episode_map=partial_episode_map,
                addon_id=addon_id
            )
            return
        
        # Budget tracking for mixed mode (movie_target computed above with log)
        show_target = config.length - movie_target
        movies_added = 0
        shows_added = 0

        # Main playlist building loop (batch mode for Unwatched/Watched/Both without multiple_shows)
        # Candidates are ordered: partials first (priority sorted), then shuffled non-partials
        # Always pick from front (index 0) to respect this ordering
        while count < config.length and candidate_list:
            iterations += 1
            
            # Always pick from front of list (partials are prioritized there)
            candidate = candidate_list[0]
            candidate_type = candidate[0]
            candidate_id = int(candidate[1:])

            # Budget enforcement: defer over-budget type when other type available
            if candidate_type == 'm' and movies_added >= movie_target:
                if any(c[0] == 't' for c in candidate_list):
                    candidate_list.remove(candidate)
                    candidate_list.append(candidate)
                    continue

            if candidate_type == 't' and shows_added >= show_target:
                if any(c[0] == 'm' for c in candidate_list):
                    candidate_list.remove(candidate)
                    candidate_list.append(candidate)
                    continue

            if candidate_type == 't':
                # TV episode candidate
                episode_id, is_multi = _process_tv_candidate(
                    candidate_id, added_ep_dict, candidate_list,
                    random_order_shows, config, log,
                    partial_episode_map=partial_episode_map
                )
                
                if episode_id is None:
                    continue
                
                # Check premiere exclusion
                if _check_premiere_exclusion(candidate_id, candidate_list, config, log):
                    continue
                
                # Add episode to playlist
                json_query(build_add_episode_query(episode_id), False)
                
                # Update tracking dict
                tmp_details = None
                if is_multi and config.episode_selection == EPISODE_SELECTION_UNWATCHED:
                    # Get details from find_next_episode result (only for unwatched mode)
                    _, tmp_details = find_next_episode(
                        candidate_id, random_order_shows,
                        epid=added_ep_dict.get(candidate_id, ['', '', [], ''])[3],
                        eps=added_ep_dict.get(candidate_id, ['', '', [], ''])[2]
                    )
                
                _update_added_dict(
                    candidate_id, added_ep_dict, random_order_shows,
                    is_multi, tmp_details, config, episode_id=episode_id
                )
                
                # Move show to end of list so other shows get a turn
                # (only when multiple_shows is enabled and show wasn't exhausted)
                if config.multiple_shows:
                    candidate_tag = f't{candidate_id}'
                    if candidate_tag in candidate_list:
                        candidate_list.remove(candidate_tag)
                        candidate_list.append(candidate_tag)

                shows_added += 1

            elif candidate_type == 'm':
                # Movie candidate
                json_query(build_add_movie_query(candidate_id), False)
                candidate_list.remove(f'm{candidate_id}')
                movies_added += 1
                
            else:
                # Unknown type - break out
                count = PLAYLIST_BUILD_BREAK_VALUE
            
            count += 1
        
        outer_timer.mark("playlist_build")
        
        # Notify service that playlist is running
        WINDOW.setProperty(PROP_PLAYLIST_RUNNING, 'true')
        WINDOW.setProperty(PROP_RANDOM_ORDER_SHUFFLE, 'true')
        
        # Store config for potential playlist continuation
        # Serialize config and population for regeneration
        playlist_state = {
            'addon_id': addon_id,
            'population': population,
            'random_order_shows': random_order_shows,
            'config': _serialize_playlist_config(config)
        }
        WINDOW.setProperty(PROP_PLAYLIST_CONFIG, json.dumps(playlist_state))
        
        # Start playback
        xbmc.Player().play(xbmc.PlayList(1))
        log.info("Random playlist created and started", event="playlist.start", 
                 item_count=count, iterations=iterations)
