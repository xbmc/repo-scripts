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
TV Show Data Functions for EasyTV.

This module provides functions for fetching, filtering, sorting, and processing
TV show and episode data from the Kodi library.

Functions are designed to be pure where possible, taking necessary context
as parameters rather than relying on global state.

Logging:
    Logger: 'data' (via get_logger)
    Key events:
        - library.fetch (DEBUG): TV shows fetched from library
        - library.fallback (WARNING): No shows found in library
        - data.sort (DEBUG): Show sorting operations
        - data.istream (DEBUG): iStream episode resolution
    See LOGGING.md for full guidelines.
"""
from __future__ import annotations

import ast
import os
import random
from typing import Any, Callable, Dict, Optional, Tuple, Union

import xbmc
import xbmcgui

from resources.lib.utils import json_query, get_logger, parse_lastplayed_date, lang, log_timing
from resources.lib.constants import (
    KODI_HOME_WINDOW_ID,
    SEASON_START_EPISODE,
    CATEGORY_START_FRESH,
    CATEGORY_CONTINUE_WATCHING,
    ISTREAM_FIX_MAX_RETRIES,
    SECONDS_PER_MINUTE,
)
from resources.lib.service.episode_tracker import PROP_DURATION
from resources.lib.data.queries import (
    get_all_shows_query,
    build_show_episodes_query,
    build_show_details_query,
    build_episode_details_query,
    build_playlist_get_items_query,
)


# Module-level logger
log = get_logger('data')

# Window reference for property access
WINDOW = xbmcgui.Window(KODI_HOME_WINDOW_ID)


# =============================================================================
# Article Stripping Configuration by Language
# =============================================================================
# Maps languages to their leading articles that should be stripped for sorting.
# Includes both definite ("the") and indefinite ("a/an") articles.
# Example: "The Office" -> "Office", "A Man in Full" -> "Man in Full"
# Languages without articles (Russian, Polish, Turkish, etc.) are not included.
LANGUAGE_ARTICLES: dict[str, list[str]] = {
    'English': ['the ', 'a ', 'an '],
    'Spanish': ['el ', 'la ', 'los ', 'las ', 'un ', 'una ', 'unos ', 'unas '],
    'Dutch': ['de ', 'het ', 'een '],
    'Danish': ['den ', 'det ', 'en ', 'et '],
    'Swedish': ['den ', 'det ', 'en ', 'ett '],
    'German': ['der ', 'die ', 'das ', 'ein ', 'eine '],
    'Afrikaans': ['die ', "'n "],
    'French': ['le ', 'la ', 'les ', "l'", 'un ', 'une ', 'des '],
    'Italian': ['il ', 'lo ', 'la ', 'i ', 'gli ', 'le ', "l'", 'un ', 'uno ', 'una '],
    'Portuguese': ['o ', 'a ', 'os ', 'as ', 'um ', 'uma ', 'uns ', 'umas '],
    'Norwegian': ['den ', 'det ', 'de ', 'en ', 'et ', 'ei '],
    'Catalan': ['el ', 'la ', 'els ', 'les ', "l'", 'un ', 'una ', 'uns ', 'unes '],
    'Romanian': ['a ', 'al ', 'ale ', 'un ', 'o '],
    'Greek': ['ο ', 'η ', 'το ', 'οι ', 'τα ', 'ένας ', 'μια ', 'ένα '],
}


# =============================================================================
# Sorting and Name Processing
# =============================================================================

def generate_sort_key(raw_name: str, language: str = 'English') -> str:
    """
    Generate a sort key by stripping leading articles based on language.
    
    For proper alphabetical sorting of show titles, removes common leading
    articles (like "The", "Die", "Los") based on the user's language setting.
    
    Args:
        raw_name: The original show title.
        language: The user's language (from Kodi's System.Language).
    
    Returns:
        Lowercase name with leading article removed if applicable.
    
    Examples:
        generate_sort_key("The Office", "English") -> "office"
        generate_sort_key("Die Simpsons", "German") -> "simpsons"
        generate_sort_key("Breaking Bad", "English") -> "breaking bad"
    """
    name = raw_name.lower()
    
    # Check for language-specific articles
    articles = None
    
    # Handle compound language names like "English (US)"
    for lang_key, lang_articles in LANGUAGE_ARTICLES.items():
        if lang_key in language:
            articles = lang_articles
            break
    
    if articles:
        for article in articles:
            if name.startswith(article):
                return name[len(article):]
    
    return name


# =============================================================================
# Episode Data Functions
# =============================================================================

def parse_season_episode_string(value: Union[int, str]) -> str:
    """
    Pad season/episode numbers to two digits for consistent formatting.
    
    This ensures consistent string comparison for episode matching,
    particularly needed for iStream content.
    
    Args:
        value: Season or episode number (string or int).
    
    Returns:
        Two-digit string (e.g., "01", "12").
    
    Examples:
        parse_season_episode_string(1) -> "01"
        parse_season_episode_string("5") -> "05"
        parse_season_episode_string(12) -> "12"
    """
    str_value = str(value)
    if len(str_value) == 1:
        return '0' + str_value
    return str_value


def get_episode_sort_key(
    ep: Dict[str, Any],
    include_positioned_specials: bool = False
) -> Tuple[int, int, int, int]:
    """
    Get sort key for episode ordering, optionally including positioned specials.
    
    Args:
        ep: Episode dict with 'season', 'episode', and optionally 
            'specialsortseason', 'specialsortepisode' fields.
        include_positioned_specials: If True, positioned specials sort
            at their designated position (just before the target episode).
    
    Returns:
        Tuple of (sort_season, sort_episode, priority, actual_episode) for sorting.
        - Regular episodes: (season, episode, 0, episode)
        - Positioned specials: (specialsortseason, specialsortepisode, -1, episode)
        The -1 priority ensures specials sort before the episode they're
        positioned at. The actual_episode field breaks ties when multiple
        specials are positioned at the same point.
    
    Example:
        Regular episode S10E55:            (10, 55, 0, 55)
        Special S00E05 before S10E56:      (10, 56, -1, 5)
        Special S00E10 before S10E56:      (10, 56, -1, 10)
        Regular episode S10E56:            (10, 56, 0, 56)
        Non-positioned special S00E20:     (0, 20, 0, 20)
        
        Sort order: S10E55 → S00E05 → S00E10 → S10E56
    """
    season = ep.get('season', 0)
    episode = ep.get('episode', 0)
    
    # Check for positioned special
    if include_positioned_specials and season == 0:
        sort_season = ep.get('specialsortseason', -1)
        sort_episode = ep.get('specialsortepisode', -1)
        
        # Valid positioning: both values must be >= 0
        if sort_season >= 0 and sort_episode >= 0:
            # Priority -1 ensures special sorts before target episode
            return (sort_season, sort_episode, -1, episode)
    
    # Regular episode or non-positioned special
    return (season, episode, 0, episode)


def find_next_episode(
    showid: int,
    random_order_shows: list[int],
    epid: Optional[int] = None,
    eps: Optional[list[int]] = None
) -> tuple[Optional[int], Optional[list]]:
    """
    Determine the next episode to play for a given show.
    
    For shows in random order mode, shuffles available episodes and picks one.
    For sequential shows, returns the next episode in the list.
    
    Args:
        showid: The TV show ID.
        random_order_shows: List of show IDs configured for random playback.
        epid: Current episode ID (to exclude from selection).
        eps: List of available episode IDs.
    
    Returns:
        Tuple of (next_episode_id, [season, episode, remaining_eps, ep_id])
        Returns (None, None) if no next episode.
    """
    if eps is None:
        eps = []
    
    log.debug("Finding next episode", show_id=showid, random_mode=showid in random_order_shows)
    
    if not eps:
        return None, None
    
    if showid in random_order_shows:
        # Random order: shuffle and pick, excluding current episode
        available = eps[:]
        if epid is not None and epid in available:
            available.remove(epid)
        
        if not available:
            return None, None
        
        random.shuffle(available)
        next_ep = available[0]
        remaining = available
    else:
        # Sequential order: get next in list
        try:
            next_ep = eps[1]
            remaining = eps[1:]
        except IndexError:
            return None, None
    
    # Get details of next episode
    ep_details = json_query(build_episode_details_query(next_ep), True)
    
    if 'episodedetails' in ep_details and ep_details['episodedetails']:
        details = ep_details['episodedetails']
        return next_ep, [details['season'], details['episode'], remaining, next_ep]
    
    return None, None


# =============================================================================
# Show Fetching and Sorting
# =============================================================================

def merge_and_sort_shows(
    shows_from_query: list[dict[str, Any]],
    shows_from_service: list[int],
    sort_by: int,
    sort_reverse: bool,
    language: str = 'English'
) -> list[list]:
    """
    Merge query results with service data and sort according to user preference.
    
    Args:
        shows_from_query: Raw show data from Kodi's JSON-RPC query.
        shows_from_service: List of show IDs that have next episodes cached.
        sort_by: Sort method (0=name, 1=lastplayed, 2=unwatched, 3=watched, 4=season).
        sort_reverse: If True, reverse the sort order.
        language: User's language for article stripping.
    
    Returns:
        Sorted list of [lastplayed_timestamp, showid] pairs.
    """
    log.debug("Sorting shows", method=sort_by, reverse=sort_reverse)
    
    if sort_by == 0:
        # SORT BY show name
        intermediate = [
            [x['label'], 
             parse_lastplayed_date(x['lastplayed']) if x.get('lastplayed') else 0, 
             x['tvshowid']] 
            for x in shows_from_query if x['tvshowid'] in shows_from_service
        ]
        intermediate.sort(key=lambda x: generate_sort_key(x[0], language), reverse=sort_reverse)
        return [x[1:] for x in intermediate]
    
    elif sort_by == 2:
        # Sort by Unwatched Episodes count
        intermediate = [
            [int(WINDOW.getProperty("EasyTV.%s.CountonDeckEps" % x['tvshowid']) or 0),
             parse_lastplayed_date(x['lastplayed']) if x.get('lastplayed') else 0,
             x['tvshowid']]
            for x in shows_from_query if x['tvshowid'] in shows_from_service
        ]
        # Default is descending; sort_reverse inverts to ascending
        intermediate.sort(reverse=not sort_reverse)
        return [x[1:] for x in intermediate]
    
    elif sort_by == 3:
        # Sort by Watched Episodes count
        intermediate = [
            [int(WINDOW.getProperty("EasyTV.%s.CountWatchedEps" % x['tvshowid']) or 0),
             parse_lastplayed_date(x['lastplayed']) if x.get('lastplayed') else 0,
             x['tvshowid']]
            for x in shows_from_query if x['tvshowid'] in shows_from_service
        ]
        intermediate.sort(reverse=not sort_reverse)
        return [x[1:] for x in intermediate]
    
    elif sort_by == 4:
        # Sort by Season number
        intermediate = [
            [int(WINDOW.getProperty("EasyTV.%s.Season" % x['tvshowid']) or 0),
             parse_lastplayed_date(x['lastplayed']) if x.get('lastplayed') else 0,
             x['tvshowid']]
            for x in shows_from_query if x['tvshowid'] in shows_from_service
        ]
        intermediate.sort(reverse=not sort_reverse)
        return [x[1:] for x in intermediate]
    
    else:
        # Default: SORT BY LAST WATCHED (sort_by == 1 or other)
        intermediate = [
            [parse_lastplayed_date(x['lastplayed']) if x.get('lastplayed') else 0, 
             x['tvshowid']] 
            for x in shows_from_query if x['tvshowid'] in shows_from_service
        ]
        
        # Separate never-watched shows (timestamp == 0)
        never_watched = [x for x in intermediate if x[0] == 0]
        watched = [x for x in intermediate if x[0] != 0]
        
        # Default is descending; sort_reverse inverts to ascending
        watched.sort(reverse=not sort_reverse)
        
        return watched + never_watched


def fetch_unwatched_shows(sort_by: int, sort_reverse: bool, language: str = 'English') -> list[list]:
    """
    Fetch all TV shows with unwatched episodes, sorted by user preference.
    
    Retrieves shows from Kodi's library and cross-references with the service's
    cached show data. Returns only shows that have next episodes ready.
    
    Args:
        sort_by: Sort method (0=name, 1=lastplayed, 2=unwatched, 3=watched, 4=season).
        sort_reverse: If True, reverse the sort order.
        language: User's language for article stripping.
    
    Returns:
        List of [lastplayed_timestamp, showid, episode_id] triples.
    
    Raises:
        SystemExit: If no shows available from service.
    """
    import sys
    import json
    
    with log_timing(log, "fetch_unwatched_shows", sort_by=sort_by) as timer:
        log.debug("Fetching TV shows", sort_by=sort_by)
        
        # Query Kodi for shows with unwatched episodes
        query = {
            "jsonrpc": "2.0",
            "method": "VideoLibrary.GetTVShows",
            "params": {
                "filter": {"field": "playcount", "operator": "is", "value": "0"},
                "properties": ["lastplayed"],
                "sort": {"order": "descending", "method": "lastplayed"}
            },
            "id": "1"
        }
        
        response = xbmc.executeJSONRPC(json.dumps(query))
        data = json.loads(response)
        
        if 'result' in data and 'tvshows' in data['result'] and data['result']['tvshows']:
            shows_from_query = data['result']['tvshows']
            log.debug("TV shows found", count=len(shows_from_query))
        else:
            log.warning("No unwatched TV shows in library", event="library.fallback")
            shows_from_query = []
        
        timer.mark("query")
        
        # Get shows with cached next episodes from service
        shows_str = WINDOW.getProperty("EasyTV.shows_with_next_episodes")
        
        if shows_str:
            shows_from_service = [int(x) for x in ast.literal_eval(shows_str)]
        else:
            # Service not ready - this is handled by the caller
            from resources.lib.utils import lang
            dialog = xbmcgui.Dialog()
            dialog.ok('EasyTV', lang(32115) + '\n' + lang(32116))
            sys.exit()
        
        sorted_shows = merge_and_sort_shows(
            shows_from_query, shows_from_service, sort_by, sort_reverse, language
        )
        
        timer.mark("sort")
        
        # Add episode IDs from service cache
        stored_data = [
            [x[0], x[1], WINDOW.getProperty("EasyTV.%s.EpisodeID" % x[1])] 
            for x in sorted_shows
        ]
        
        timer.mark("property_lookup")
        
        log.debug("TV shows fetch complete", count=len(stored_data))
    
    return stored_data


def fetch_shows_with_watched_episodes(
    sort_by: int, 
    sort_reverse: bool, 
    language: str = 'English'
) -> list[list]:
    """
    Fetch all TV shows that have at least one watched episode.
    
    Unlike fetch_unwatched_shows, this queries Kodi directly without relying
    on the service cache. Used for "watched" and "both" episode selection modes.
    
    Args:
        sort_by: Sort method (0=name, 1=lastplayed).
        sort_reverse: If True, reverse the sort order.
        language: User's language for article stripping.
    
    Returns:
        List of [lastplayed_timestamp, showid, ''] triples. The episode_id
        field is empty because watched episodes are selected on-demand.
    """
    import json
    
    with log_timing(log, "fetch_shows_with_watched_episodes", sort_by=sort_by) as timer:
        log.debug("Fetching shows with watched episodes", sort_by=sort_by)
        
        # Query Kodi for shows with watched episodes (playcount > 0)
        query = {
            "jsonrpc": "2.0",
            "method": "VideoLibrary.GetTVShows",
            "params": {
                "filter": {"field": "playcount", "operator": "greaterthan", "value": "0"},
                "properties": ["lastplayed"],
                "sort": {"order": "descending", "method": "lastplayed"}
            },
            "id": "1"
        }
        
        response = xbmc.executeJSONRPC(json.dumps(query))
        data = json.loads(response)
        
        if 'result' in data and 'tvshows' in data['result'] and data['result']['tvshows']:
            shows_from_query = data['result']['tvshows']
            log.debug("Shows with watched episodes found", count=len(shows_from_query))
        else:
            log.debug("No shows with watched episodes found")
            return []
        
        timer.mark("query")
        
        # Sort the shows
        if sort_by == 0:
            # Sort by show name
            intermediate = [
                [x['label'], 
                 parse_lastplayed_date(x['lastplayed']) if x.get('lastplayed') else 0, 
                 x['tvshowid']] 
                for x in shows_from_query
            ]
            intermediate.sort(key=lambda x: generate_sort_key(x[0], language), reverse=sort_reverse)
            sorted_shows = [[x[1], x[2]] for x in intermediate]
        else:
            # Default: sort by last played
            intermediate = [
                [parse_lastplayed_date(x['lastplayed']) if x.get('lastplayed') else 0, 
                 x['tvshowid']] 
                for x in shows_from_query
            ]
            
            # Separate never-watched shows (timestamp == 0)
            never_watched = [x for x in intermediate if x[0] == 0]
            watched = [x for x in intermediate if x[0] != 0]
            watched.sort(reverse=not sort_reverse)
            sorted_shows = watched + never_watched
        
        timer.mark("sort")
        
        # Return with empty episode_id field (episodes selected on-demand)
        stored_data = [[x[0], x[1], ''] for x in sorted_shows]
        
        log.debug("Shows with watched episodes fetch complete", count=len(stored_data))
    
    return stored_data


def extract_showids_from_playlist(playlist_path: str, silent: bool = False) -> list[int]:
    """
    Extract TV show IDs from a smart playlist file.
    
    Reads the contents of a video smart playlist and returns the IDs
    of all TV shows contained within it. Shows an error dialog if the
    playlist is empty or contains no TV shows (unless silent=True).
    
    Args:
        playlist_path: Full path to the playlist file.
        silent: If True, suppress error dialogs (for background operations).
    
    Returns:
        List of TV show IDs in the playlist, or empty list on error.
    """
    # Normalize path to Kodi's special:// format
    filename = os.path.split(playlist_path)[1]
    clean_path = 'special://profile/playlists/video/' + filename
    
    playlist_contents = json_query(build_playlist_get_items_query(clean_path), True)
    
    if 'files' not in playlist_contents:
        if not silent:
            dialog = xbmcgui.Dialog()
            dialog.ok("EasyTV", lang(32575))
        return []
    
    if not playlist_contents['files']:
        if not silent:
            dialog = xbmcgui.Dialog()
            dialog.ok("EasyTV", lang(32576))
        return []
    
    filtered_showids = [
        x['id'] for x in playlist_contents['files'] 
        if x.get('type') == 'tvshow'
    ]
    
    log.debug("Shows extracted from playlist", show_ids=filtered_showids)
    
    if not filtered_showids:
        if not silent:
            dialog = xbmcgui.Dialog()
            dialog.ok("EasyTV", lang(32577))
        return []
    
    return filtered_showids


def extract_movieids_from_playlist(playlist_path: str) -> list[int]:
    """
    Extract movie IDs from a smart playlist file.
    
    Reads the contents of a video smart playlist and returns the IDs
    of all movies contained within it. Shows an error dialog if the
    playlist is empty or contains no movies.
    
    Args:
        playlist_path: Full path to the playlist file.
    
    Returns:
        List of movie IDs in the playlist, or empty list on error.
    """
    # Normalize path to Kodi's special:// format
    filename = os.path.split(playlist_path)[1]
    clean_path = 'special://profile/playlists/video/' + filename
    
    playlist_contents = json_query(build_playlist_get_items_query(clean_path), True)
    
    dialog = xbmcgui.Dialog()
    
    if 'files' not in playlist_contents:
        dialog.ok("EasyTV", lang(32575))
        return []
    
    if not playlist_contents['files']:
        dialog.ok("EasyTV", lang(32576))
        return []
    
    filtered_movieids = [
        x['id'] for x in playlist_contents['files'] 
        if x.get('type') == 'movie'
    ]
    
    log.debug("Movies extracted from playlist", movie_ids=filtered_movieids)
    
    if not filtered_movieids:
        # 32605 = "Error: no movies in playlist"
        dialog.ok("EasyTV", lang(32605))
        return []
    
    return filtered_movieids


# =============================================================================
# Smart Playlist Categorization
# =============================================================================

def get_show_category(episode_number: int) -> str:
    """
    Determine which category playlist a show belongs to based on episode number.
    
    Episode 1 of any season means the user hasn't started watching that season yet,
    so it goes in "Start Fresh". Episode 2+ means they're mid-season, so it goes
    in "Continue Watching".
    
    Args:
        episode_number: The episode number (1, 2, 3, etc.)
    
    Returns:
        CATEGORY_START_FRESH if episode == 1, CATEGORY_CONTINUE_WATCHING otherwise.
    """
    if episode_number == SEASON_START_EPISODE:
        return CATEGORY_START_FRESH
    return CATEGORY_CONTINUE_WATCHING


def get_premiere_category(season_number: int, episode_number: int) -> str:
    """
    Determine which premiere playlist a show belongs to, if any.
    
    - S01E01 = Show Premiere (brand new show)
    - S02E01+ = Season Premiere (new season of existing show)
    - Episode > 1 = Not a premiere (empty string)
    
    Args:
        season_number: The season number (1, 2, 3, etc.)
        episode_number: The episode number (1, 2, 3, etc.)
    
    Returns:
        CATEGORY_SHOW_PREMIERE if S01E01
        CATEGORY_SEASON_PREMIERE if S02E01+
        Empty string if episode > 1 (not a premiere)
    """
    from resources.lib.constants import (
        CATEGORY_SHOW_PREMIERE,
        CATEGORY_SEASON_PREMIERE,
    )
    
    # Not a premiere if episode > 1
    if episode_number != SEASON_START_EPISODE:
        return ""
    
    # S01E01 = Show Premiere
    if season_number == SEASON_START_EPISODE:
        return CATEGORY_SHOW_PREMIERE
    
    # S02E01+ = Season Premiere
    return CATEGORY_SEASON_PREMIERE


def _get_playlist_filename(file_path: str) -> str:
    """
    Get the appropriate filename for smart playlist rules.
    
    For plugin URLs (like Jellyfin), returns the full path since these require
    the complete plugin:// URL for playback. For local files, returns just
    the basename to match Kodi's default filename matching.
    
    Args:
        file_path: Full file path or plugin URL.
    
    Returns:
        Full path for plugin:// URLs, basename for local files.
    
    Examples:
        _get_playlist_filename("plugin://plugin.video.jellyfin/...")
            -> "plugin://plugin.video.jellyfin/..."
        _get_playlist_filename("/media/TV/Show/episode.mkv")
            -> "episode.mkv"
    """
    if file_path.startswith('plugin://'):
        return file_path
    return os.path.basename(file_path)


def fetch_show_episode_data(tvshowid: int) -> Optional[dict[str, Any]]:
    """
    Retrieve show data from Window properties for smart playlist operations.
    
    Fetches cached show information from the service's window properties,
    with a fallback to Kodi's library if the title isn't cached.
    
    Args:
        tvshowid: The TV show ID.
    
    Returns:
        Dict with keys: filename, episode_number, season_number, episodeno, show_title
        Returns None if the show is not available (no title found).
    """
    showname = WINDOW.getProperty("EasyTV.%s.TVshowTitle" % tvshowid)
    filename = _get_playlist_filename(WINDOW.getProperty("EasyTV.%s.File" % tvshowid))
    episodeno = WINDOW.getProperty("EasyTV.%s.EpisodeNo" % tvshowid)
    episode_str = WINDOW.getProperty("EasyTV.%s.Episode" % tvshowid)
    season_str = WINDOW.getProperty("EasyTV.%s.Season" % tvshowid)
    
    # Fallback: lookup show name from Kodi library if Window property not set
    # Used only to validate the show exists
    if not showname:
        result = json_query(build_show_details_query(tvshowid), True)
        showname = result.get('tvshowdetails', {}).get('title', '')
    
    if not showname:
        return None
    
    # Parse episode number, default to 1 if parsing fails
    try:
        episode_number = int(episode_str) if episode_str else SEASON_START_EPISODE
    except (ValueError, TypeError):
        episode_number = SEASON_START_EPISODE
    
    # Parse season number, default to 1 if parsing fails
    try:
        season_number = int(season_str) if season_str else SEASON_START_EPISODE
    except (ValueError, TypeError):
        season_number = SEASON_START_EPISODE
    
    return {
        'filename': filename,
        'episode_number': episode_number,
        'season_number': season_number,
        'episodeno': episodeno,
        'show_title': showname
    }


# =============================================================================
# iStream Compatibility
# =============================================================================

def resolve_istream_episode(
    now_playing_show_id: int,
    showtitle: str,
    episode_np: str,
    season_np: str,
    random_order_shows: list[int],
    refresh_callback: Optional[Callable[[list[int]], None]] = None
) -> tuple[bool, int, Union[int, bool]]:
    """
    Handle streams from iStream that don't provide showid and epid.
    
    iStream streams come through as tvshowid=-1 but include episode/season/show name.
    This function looks up the correct IDs from the Kodi library.
    
    Args:
        now_playing_show_id: TV show ID (-1 for iStream).
        showtitle: Name of the TV show.
        episode_np: Episode number (formatted).
        season_np: Season number (formatted).
        random_order_shows: List of show IDs in random playback mode.
        refresh_callback: Optional callback to refresh episode data for a show.
                         Called with [show_id] when episode not in ondeck list.
    
    Returns:
        Tuple of (previous_episode_check_flag, show_id, episode_id)
        previous_episode_check_flag is always False for iStream content.
    """
    now_playing_episode_id: Union[int, bool] = False
    
    log.debug("Resolving iStream episode", 
              show_id=now_playing_show_id, title=showtitle, 
              episode=episode_np, season=season_np)
    
    redo = True
    count = 0
    
    while redo and count < ISTREAM_FIX_MAX_RETRIES:
        redo = False
        count += 1
        
        if now_playing_show_id == -1 and showtitle and episode_np and season_np:
            # Look up show by title
            tmp_shows = json_query(get_all_shows_query(), True)
            log.debug("TV shows query for iStream", shows=tmp_shows)
            
            if 'tvshows' in tmp_shows:
                for show in tmp_shows['tvshows']:
                    if show['label'] == showtitle:
                        now_playing_show_id = show['tvshowid']
                        
                        # Look up episode by season/episode number
                        tmp_eps = json_query(build_show_episodes_query(now_playing_show_id), True)
                        log.debug("Episodes query for iStream", episodes=tmp_eps)
                        
                        if 'episodes' in tmp_eps:
                            for ep in tmp_eps['episodes']:
                                if (parse_season_episode_string(ep['season']) == season_np and 
                                    parse_season_episode_string(ep['episode']) == episode_np):
                                    now_playing_episode_id = ep['episodeid']
                                    log.debug("Found episode in library", episode_id=now_playing_episode_id)
                                    
                                    # Check if episode is in ondeck list
                                    ondeck_str = WINDOW.getProperty(
                                        "EasyTV.%s.ondeck_list" % now_playing_show_id
                                    )
                                    
                                    if ondeck_str:
                                        temp_ondeck_list = ast.literal_eval(ondeck_str)
                                    else:
                                        temp_ondeck_list = []
                                    
                                    # Include offdeck episodes for random order shows
                                    if now_playing_show_id in random_order_shows:
                                        offdeck_str = WINDOW.getProperty(
                                            "EasyTV.%s.offdeck_list" % now_playing_show_id
                                        )
                                        if offdeck_str:
                                            temp_ondeck_list += ast.literal_eval(offdeck_str)
                                    
                                    log.debug("On-deck list for iStream", 
                                             ondeck=temp_ondeck_list, 
                                             episode_id=now_playing_episode_id)
                                    
                                    if now_playing_episode_id not in temp_ondeck_list:
                                        log.debug("iStream fix: episode not in ondeck, refreshing")
                                        if refresh_callback:
                                            refresh_callback([now_playing_show_id])
                                        log.debug("iStream fix: refresh complete")
                                        redo = True
                                    
                                    break
                        break
    
    return False, now_playing_show_id, now_playing_episode_id


# =============================================================================
# Duration Filtering
# =============================================================================

def get_show_duration(
    show_id: int,
    window: Optional[xbmcgui.Window] = None
) -> int:
    """
    Get the cached episode duration for a show.
    
    Retrieves the duration (in seconds) from the window property set during
    service startup. This represents a randomly sampled episode's duration.
    
    Args:
        show_id: The TV show ID.
        window: Window for property lookup (defaults to home window).
    
    Returns:
        Duration in seconds, or 0 if not available.
    """
    if window is None:
        window = WINDOW
    
    prop_key = f"EasyTV.{show_id}.{PROP_DURATION}"
    duration_str = window.getProperty(prop_key)
    
    try:
        return int(duration_str) if duration_str else 0
    except (ValueError, TypeError):
        return 0


def validate_duration_settings(min_minutes: int, max_minutes: int) -> bool:
    """
    Validate duration filter settings and warn user if invalid.
    
    Shows a warning dialog if min > max (when both are non-zero),
    which would result in no shows matching.
    
    Args:
        min_minutes: Minimum duration setting in minutes.
        max_minutes: Maximum duration setting in minutes.
    
    Returns:
        True if valid (filtering should proceed).
        False if invalid (warning shown, filtering should be skipped).
    """
    # Valid cases:
    # - min=0, max=0: No filtering
    # - min>0, max=0: Only minimum
    # - min=0, max>0: Only maximum  
    # - min>0, max>0, min<=max: Valid range
    # Invalid: min>0, max>0, min>max
    if min_minutes > 0 and max_minutes > 0 and min_minutes > max_minutes:
        dialog = xbmcgui.Dialog()
        # 32637 = "Invalid Duration Settings"
        # 32638 = "Minimum duration cannot be greater than maximum. Duration filter disabled."
        dialog.ok(lang(32637), lang(32638))
        log.warning(
            "Invalid duration settings",
            min_minutes=min_minutes,
            max_minutes=max_minutes
        )
        return False
    
    return True


def filter_shows_by_duration(
    shows: list,
    min_minutes: int = 0,
    max_minutes: int = 0,
    window: Optional[xbmcgui.Window] = None
) -> list:
    """
    Filter shows by typical episode duration.
    
    Uses cached duration data (set during service startup) to filter shows
    based on their typical episode length. Shows without duration data
    (duration=0) are excluded when filtering is active.
    
    Args:
        shows: List of shows in one of two formats:
            - List of dicts with 'tvshowid' key (from browse mode)
            - List of [lastplayed, showid, episodeid] (from random playlist)
        min_minutes: Minimum duration in minutes (0 = no minimum).
        max_minutes: Maximum duration in minutes (0 = no maximum).
        window: Window for property lookup (defaults to home window).
    
    Returns:
        Filtered list of shows within duration range (same format as input).
        Shows without duration data (duration=0) are excluded.
    
    Note:
        Call validate_duration_settings() before this function to warn
        users about invalid min > max configurations.
    """
    # No filtering if both are 0
    if min_minutes == 0 and max_minutes == 0:
        return shows
    
    if not shows:
        return shows
    
    if window is None:
        window = WINDOW
    
    # Convert minutes to seconds for comparison
    min_seconds = min_minutes * SECONDS_PER_MINUTE
    max_seconds = max_minutes * SECONDS_PER_MINUTE
    
    # Detect format: dict with 'tvshowid' or list with showid at index 1
    is_dict_format = isinstance(shows[0], dict)
    
    filtered = []
    excluded_no_duration = 0
    for show in shows:
        # Extract show ID based on format
        if is_dict_format:
            show_id = show.get('tvshowid')
        else:
            # List format: [lastplayed, showid, episodeid]
            show_id = show[1] if len(show) > 1 else None
        
        if show_id is None:
            # No show ID, include by default
            filtered.append(show)
            continue
        
        duration = get_show_duration(show_id, window)
        
        # Exclude shows without duration data
        if duration == 0:
            excluded_no_duration += 1
            continue
        
        # Check against min (if set)
        if min_seconds > 0 and duration < min_seconds:
            continue
        
        # Check against max (if set)
        if max_seconds > 0 and duration > max_seconds:
            continue
        
        filtered.append(show)
    
    log.debug(
        "Duration filter applied",
        min_minutes=min_minutes,
        max_minutes=max_minutes,
        input_count=len(shows),
        output_count=len(filtered),
        excluded_no_duration=excluded_no_duration
    )
    
    return filtered
