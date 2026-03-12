#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Copyright (C) 2024-2026 Rouzax
#
#  SPDX-License-Identifier: GPL-3.0-or-later
#  See LICENSE.txt for more information.
#

"""
Duration Cache for EasyTV.

This module manages a persistent cache of median episode durations per TV show.
Caching avoids expensive streamdetails queries on every startup by only
recalculating durations when episode counts change.

Cache File:
    Location: special://profile/addon_data/script.easytv/duration_cache.json
    
    Format:
        {
            "version": 1,
            "shows": {
                "123": {
                    "title": "Breaking Bad",
                    "median_seconds": 2580,
                    "episode_count": 45,
                    "calculated_at": "2025-01-21T14:30:00"
                }
            }
        }

Usage:
    # At startup (bulk refresh)
    cache = load_duration_cache()
    current_counts = {show_id: len(episodes) for show_id, episodes in episodes_by_show.items()}
    show_titles = {show_id: eps[0]['showtitle'] for show_id, eps in episodes_by_show.items() if eps}
    shows_to_calc = get_shows_needing_calculation(cache, current_counts)
    
    # Calculate durations for changed shows only
    for show_id in shows_to_calc:
        episodes = fetch_episodes_with_streamdetails(show_id)
        median = calculate_median_duration(episodes)
        cache['shows'][str(show_id)] = {
            'title': show_titles.get(show_id, ''),
            'median_seconds': median,
            'episode_count': current_counts[show_id],
            'calculated_at': datetime.now().isoformat()
        }
    
    save_duration_cache(cache)

Logging:
    Logger: 'data' (via get_logger)
    Key events:
        - cache.load (DEBUG): Cache loaded successfully
        - cache.load_error (WARNING): Cache load failed, using empty cache
        - cache.save (DEBUG): Cache saved successfully
        - cache.save_error (WARNING): Cache save failed
        - cache.compare (DEBUG): Shows needing calculation identified
    See LOGGING.md for full guidelines.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

import xbmcvfs

from resources.lib.constants import (
    DEFAULT_ADDON_ID,
    DURATION_CACHE_FILENAME,
    DURATION_CACHE_VERSION,
)
from resources.lib.utils import get_logger


# Module-level logger
log = get_logger('data')

# Cached file path (lazily initialized)
_cache_file_path: Optional[str] = None


def get_cache_file_path() -> str:
    """
    Get the duration cache file path.
    
    Lazily initializes and caches the translated path.
    Creates the parent directory if it doesn't exist.
    
    Returns:
        Filesystem path to the duration cache JSON file.
    """
    global _cache_file_path
    if _cache_file_path is None:
        cache_dir = xbmcvfs.translatePath(
            f"special://profile/addon_data/{DEFAULT_ADDON_ID}/"
        )
        # Ensure directory exists
        if not xbmcvfs.exists(cache_dir):
            xbmcvfs.mkdirs(cache_dir)
        _cache_file_path = os.path.join(cache_dir, DURATION_CACHE_FILENAME)
    return _cache_file_path


def load_duration_cache() -> Dict[str, Any]:
    """
    Load the duration cache from disk.
    
    Handles missing files, corrupted JSON, and version mismatches gracefully
    by returning an empty cache structure.
    
    Returns:
        Cache dictionary with 'version' and 'shows' keys.
        Empty cache if file missing, corrupted, or version mismatch.
    
    Example:
        >>> cache = load_duration_cache()
        >>> cache['shows'].get('123', {}).get('median_seconds', 0)
        2580
    """
    cache_path = get_cache_file_path()
    
    # Return empty cache if file doesn't exist
    if not xbmcvfs.exists(cache_path):
        log.debug("Duration cache file not found, starting fresh")
        return _empty_cache()
    
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Validate structure
        if not isinstance(data, dict):
            log.warning("Duration cache invalid structure, starting fresh")
            return _empty_cache()
        
        # Check version compatibility
        version = data.get('version', 0)
        if version != DURATION_CACHE_VERSION:
            log.warning(
                "Duration cache version mismatch",
                file_version=version,
                expected_version=DURATION_CACHE_VERSION
            )
            return _empty_cache()
        
        # Ensure shows dict exists
        if 'shows' not in data or not isinstance(data['shows'], dict):
            log.warning("Duration cache missing shows dict, starting fresh")
            return _empty_cache()
        
        show_count = len(data['shows'])
        log.debug("Duration cache loaded", show_count=show_count)
        return data
        
    except json.JSONDecodeError as e:
        log.warning("Duration cache corrupted", error=str(e))
        return _empty_cache()
    except (OSError, IOError) as e:
        log.warning("Duration cache read error", error=str(e))
        return _empty_cache()


def save_duration_cache(cache: Dict[str, Any]) -> bool:
    """
    Save the duration cache to disk.
    
    Writes atomically by ensuring the full JSON is serialized before writing.
    
    Args:
        cache: Cache dictionary with 'version' and 'shows' keys.
    
    Returns:
        True if saved successfully, False on error.
    
    Example:
        >>> cache = load_duration_cache()
        >>> cache['shows']['123'] = {
        ...     'median_seconds': 2700,
        ...     'episode_count': 50,
        ...     'calculated_at': '2025-01-21T15:00:00'
        ... }
        >>> save_duration_cache(cache)
        True
    """
    cache_path = get_cache_file_path()
    
    # Ensure version is set
    cache['version'] = DURATION_CACHE_VERSION
    
    try:
        # Serialize first to catch errors before opening file
        json_data = json.dumps(cache, indent=2)
        
        with open(cache_path, 'w', encoding='utf-8') as f:
            f.write(json_data)
        
        show_count = len(cache.get('shows', {}))
        log.debug("Duration cache saved", show_count=show_count)
        return True
        
    except (OSError, IOError, TypeError) as e:
        log.warning("Duration cache save failed", error=str(e))
        return False


def calculate_median_duration(episodes: List[Dict[str, Any]]) -> int:
    """
    Calculate the median episode duration from a list of episodes.
    
    Extracts duration from streamdetails.video[0].duration for each episode.
    Episodes without valid duration data are excluded from the calculation.
    
    Args:
        episodes: List of episode dicts, each containing a 'streamdetails' key
                  with nested video stream information.
    
    Returns:
        Median duration in seconds, or 0 if no valid durations found.
    
    Example:
        >>> episodes = [
        ...     {'streamdetails': {'video': [{'duration': 2500}]}},
        ...     {'streamdetails': {'video': [{'duration': 2600}]}},
        ...     {'streamdetails': {'video': [{'duration': 2700}]}},
        ... ]
        >>> calculate_median_duration(episodes)
        2600
    
    Note:
        Median is used instead of mean to be robust against outliers
        like double-length finales or specials.
    """
    durations = []
    
    for ep in episodes:
        stream_details = ep.get('streamdetails', {})
        video_streams = stream_details.get('video', [])
        if video_streams:
            duration = video_streams[0].get('duration', 0)
            if duration > 0:
                durations.append(duration)
    
    if not durations:
        return 0
    
    # Calculate median (middle value of sorted list)
    sorted_durations = sorted(durations)
    mid_index = len(sorted_durations) // 2
    return sorted_durations[mid_index]


def get_shows_needing_calculation(
    cache: Dict[str, Any],
    current_episode_counts: Dict[int, int]
) -> Set[int]:
    """
    Determine which shows need their duration recalculated.
    
    A show needs recalculation if:
    - It's not in the cache
    - Its episode count has changed since last calculation
    - It was previously cached with median=0 (incomplete data)
    
    Shows that exist in cache but not in current_episode_counts are pruned
    (they were removed from the library).
    
    Args:
        cache: Loaded cache dictionary from load_duration_cache().
        current_episode_counts: Dict mapping show_id (int) to episode count.
    
    Returns:
        Set of show IDs (int) that need duration calculation.
    
    Example:
        >>> cache = {'version': 1, 'shows': {
        ...     '100': {'median_seconds': 2700, 'episode_count': 20},
        ...     '200': {'median_seconds': 0, 'episode_count': 0},
        ... }}
        >>> current = {100: 20, 200: 5, 300: 10}
        >>> get_shows_needing_calculation(cache, current)
        {200, 300}  # 200: was 0 eps now 5, 300: new show
    """
    needs_calculation: Set[int] = set()
    cached_shows = cache.get('shows', {})
    
    for show_id, episode_count in current_episode_counts.items():
        show_id_str = str(show_id)
        
        if show_id_str not in cached_shows:
            # New show, not in cache
            needs_calculation.add(show_id)
            continue
        
        cached_data = cached_shows[show_id_str]
        cached_count = cached_data.get('episode_count', 0)
        cached_median = cached_data.get('median_seconds', 0)
        
        # Recalculate if episode count changed
        if episode_count != cached_count:
            needs_calculation.add(show_id)
            continue
        
        # Recalculate if previously had no duration data
        # (episodes existed but streamdetails was missing)
        if cached_median == 0 and episode_count > 0:
            needs_calculation.add(show_id)
    
    # Log summary
    cached_count = len(current_episode_counts) - len(needs_calculation)
    log.debug(
        "Duration cache comparison",
        total_shows=len(current_episode_counts),
        cached_shows=cached_count,
        needs_calculation=len(needs_calculation)
    )
    
    return needs_calculation


def build_updated_cache(
    old_cache: Dict[str, Any],
    current_episode_counts: Dict[int, int],
    new_durations: Dict[int, int],
    show_titles: Optional[Dict[int, str]] = None
) -> Dict[str, Any]:
    """
    Build an updated cache from old cache, current counts, and new calculations.
    
    This function:
    - Preserves cached entries for shows with unchanged episode counts
    - Updates entries for shows in new_durations with fresh calculations
    - Prunes entries for shows no longer in the library
    - Includes show titles for debugging/readability
    
    Args:
        old_cache: Previously loaded cache dictionary.
        current_episode_counts: Dict mapping show_id (int) to current episode count.
        new_durations: Dict mapping show_id (int) to newly calculated median duration.
        show_titles: Optional dict mapping show_id (int) to show title string.
    
    Returns:
        New cache dictionary ready to be saved.
    
    Example:
        >>> old = {'version': 1, 'shows': {'100': {'median_seconds': 2700, 'episode_count': 20}}}
        >>> counts = {100: 20, 200: 10}
        >>> new_durations = {200: 1800}
        >>> titles = {100: 'Show A', 200: 'Show B'}
        >>> updated = build_updated_cache(old, counts, new_durations, titles)
        >>> '100' in updated['shows'] and '200' in updated['shows']
        True
    """
    new_cache = _empty_cache()
    old_shows = old_cache.get('shows', {})
    now = datetime.now().isoformat(timespec='seconds')
    titles = show_titles or {}
    
    for show_id, episode_count in current_episode_counts.items():
        show_id_str = str(show_id)
        title = titles.get(show_id, '')
        
        if show_id in new_durations:
            # Freshly calculated
            median = new_durations[show_id]
            # Only cache if we got a valid duration
            if median > 0:
                new_cache['shows'][show_id_str] = {
                    'title': title,
                    'median_seconds': median,
                    'episode_count': episode_count,
                    'calculated_at': now
                }
        elif show_id_str in old_shows:
            # Carry over from old cache (unchanged)
            old_entry = old_shows[show_id_str].copy()
            # Update title if we have a newer one (handles renames)
            if title:
                old_entry['title'] = title
            elif 'title' not in old_entry:
                old_entry['title'] = ''
            new_cache['shows'][show_id_str] = old_entry
    
    return new_cache


def _empty_cache() -> Dict[str, Any]:
    """
    Create an empty cache structure.
    
    Returns:
        Empty cache dict with version and empty shows dict.
    """
    return {
        'version': DURATION_CACHE_VERSION,
        'shows': {}
    }
