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
Smart Playlist File I/O for EasyTV.

This module handles reading and writing of Kodi smart playlist (.xsp) files.
EasyTV maintains two sets of five auto-updated smart playlists:

Episode Playlists (type="episodes"):
    Used for channel surfing / random playback. Ordered randomly.
    - EasyTV - Episode - All Shows
    - EasyTV - Episode - Continue Watching
    - EasyTV - Episode - Start Fresh
    - EasyTV - Episode - Show Premieres
    - EasyTV - Episode - Season Premieres

TVShow Playlists (type="tvshows"):
    Used for skin widgets / browsing. Ordered alphabetically by title.
    - EasyTV - TVShow - All Shows
    - EasyTV - TVShow - Continue Watching
    - EasyTV - TVShow - Start Fresh
    - EasyTV - TVShow - Show Premieres
    - EasyTV - TVShow - Season Premieres

Playlist Categories:
    - All Shows: Every show with an ondeck episode
    - Continue Watching: Shows where next episode > 1 (mid-season)
    - Start Fresh: Shows where next episode = 1 (any season start)
    - Show Premieres: Shows at S01E01 (brand new shows)
    - Season Premieres: Shows at S02E01+ (new season of existing show)

Format Versioning:
    Playlist format changes (like marker format or XML structure) are tracked
    via a version file. On startup, if the version doesn't match, all playlists
    are deleted and regenerated to ensure consistency.

Batch Mode:
    For bulk operations (startup, library rescan), batch mode can be enabled
    to collect all playlist updates and write them in a single operation per
    playlist file.
    
    IMPORTANT: Batch mode performs a FULL REBUILD of playlist files. Only
    entries collected during the batch operation are written - existing file
    contents are ignored. This automatically eliminates orphaned entries
    (shows deleted from the library) without needing explicit cleanup.
    
    Usage:
        start_playlist_batch()
        # ... perform many playlist updates ...
        flush_playlist_batch(episode_enabled=True, tvshow_enabled=True)

Logging:
    Logger: 'data' (via get_logger)
    Key events:
        - playlist.write (DEBUG): Playlist file written
        - playlist.fail (ERROR): Playlist write failed
        - playlist.batch_flush (DEBUG): Batch mode flushed
        - playlist.version_mismatch (INFO): Format version changed, regenerating
    See LOGGING.md for full guidelines.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple

import xbmc
import xbmcvfs

from resources.lib.utils import get_logger, log_timing
from resources.lib.constants import (
    FILE_WRITE_DELAY_MS,
    PLAYLIST_FORMAT_FILENAME,
    PLAYLIST_CONFIG,
    LEGACY_PLAYLIST_FILES,
    CATEGORY_START_FRESH,
    CATEGORY_SHOW_PREMIERE,
    CATEGORY_SEASON_PREMIERE,
)


# Module-level logger
log = get_logger('data')

# Video playlist location
_video_playlist_location: Optional[str] = None

# Batch mode state
# When enabled, playlist updates are collected instead of written immediately
_batch_mode: bool = False

# Batch updates structure:
# {
#     'shows': {show_id: {'filename': str, 'title': str, 'category': str, 'premiere_category': str}},
#     'removals': set([show_id, ...])  # Shows to remove from all playlists
# }
_batch_updates: Dict[str, Any] = {}


def _get_playlist_location() -> str:
    """
    Get the video playlist directory path.
    
    Lazily initializes and caches the translated path.
    
    Returns:
        Filesystem path to special://profile/playlists/video/
    """
    global _video_playlist_location
    if _video_playlist_location is None:
        _video_playlist_location = xbmcvfs.translatePath(
            'special://profile/playlists/video/'
        )
    return _video_playlist_location


# =============================================================================
# Format Version Functions
# =============================================================================

def get_format_file_path() -> str:
    """
    Get the path to the playlist format version file.
    
    The version file is stored in the addon's data directory alongside
    other persistent data like the duration cache.
    
    Returns:
        Filesystem path to playlist_format.json
    """
    addon_data = xbmcvfs.translatePath('special://profile/addon_data/script.easytv/')
    return os.path.join(addon_data, PLAYLIST_FORMAT_FILENAME)


def load_playlist_format_version() -> int:
    """
    Load the playlist format version from the version file.
    
    Returns:
        The stored format version, or 0 if the file doesn't exist or is invalid.
        A return value of 0 indicates playlists need to be regenerated.
    """
    version_path = get_format_file_path()
    try:
        with open(version_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('version', 0)
    except (IOError, OSError, json.JSONDecodeError, KeyError):
        return 0


def save_playlist_format_version(version: int, addon_version: str) -> bool:
    """
    Save the playlist format version to the version file.
    
    Args:
        version: The format version number to save
        addon_version: The addon version string for reference
        
    Returns:
        True if saved successfully, False on error
    """
    version_path = get_format_file_path()
    try:
        # Ensure directory exists
        addon_data = os.path.dirname(version_path)
        if not os.path.exists(addon_data):
            os.makedirs(addon_data)
        
        data = {
            'version': version,
            'addon_version': addon_version
        }
        with open(version_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        log.debug("Playlist format version saved",
                 event="playlist.version_saved",
                 version=version,
                 addon_version=addon_version)
        return True
        
    except (IOError, OSError) as e:
        log.exception("Failed to save playlist format version",
                     event="playlist.version_save_fail",
                     error=str(e))
        return False


def delete_easytv_playlists() -> int:
    """
    Delete all EasyTV smart playlist files.
    
    Deletes both current format playlists (Episode and TVShow) and
    legacy format playlists from previous versions. Used during format
    migration to ensure clean regeneration of playlists in the new format.
    
    Returns:
        Number of playlist files deleted
    """
    playlist_dir = _get_playlist_location()
    
    # Combine current filenames and legacy filenames
    playlist_files = PLAYLIST_CONFIG.all_filenames() + LEGACY_PLAYLIST_FILES
    
    deleted_count = 0
    for playlist_file in playlist_files:
        playlist_path = os.path.join(playlist_dir, playlist_file)
        try:
            if os.path.exists(playlist_path):
                os.remove(playlist_path)
                deleted_count += 1
                log.debug("Deleted playlist file",
                         event="playlist.deleted",
                         file=playlist_file)
        except (IOError, OSError) as e:
            log.warning("Failed to delete playlist file",
                       event="playlist.delete_fail",
                       file=playlist_file,
                       error=str(e))
    
    log.info("EasyTV playlists deleted for format migration",
            event="playlist.migration_delete",
            deleted_count=deleted_count)
    
    return deleted_count


# =============================================================================
# Batch Mode Functions
# =============================================================================

def is_batch_mode() -> bool:
    """
    Check if batch mode is currently enabled.
    
    Returns:
        True if batch mode is active, False otherwise.
    """
    return _batch_mode


def start_playlist_batch() -> None:
    """
    Enable batch mode for playlist updates.
    
    When batch mode is enabled, calls to update_show_in_playlists() and
    remove_show_from_all_playlists() will collect updates in memory instead
    of writing to disk immediately. Call flush_playlist_batch() to write
    all collected updates at once.
    
    This significantly improves performance for bulk operations by reducing
    individual file writes.
    """
    global _batch_mode, _batch_updates
    _batch_mode = True
    _batch_updates = {
        'shows': {},  # {show_id: {'filename': str, 'title': str, 'category': str, 'premiere_category': str}}
        'removals': set()  # show_ids to remove
    }
    log.debug("Playlist batch mode started")


def flush_playlist_batch(
    episode_enabled: bool = True,
    tvshow_enabled: bool = False,
    filter_show_ids: Optional[set] = None
) -> None:
    """
    Write all collected playlist updates and disable batch mode.
    
    Performs a FULL REBUILD of each playlist file using only the entries
    collected during batch mode. This eliminates orphaned entries (shows
    that were deleted from the library) by design - if a show isn't in
    the batch updates, it won't be in the output file.
    
    Args:
        episode_enabled: If True, write Episode playlists
        tvshow_enabled: If True, write TVShow playlists
        filter_show_ids: Optional set of show IDs to include. If provided,
            only shows in this set will be written to playlists.
    
    After flushing, batch mode is disabled and subsequent updates will
    be written immediately as normal.
    """
    global _batch_mode, _batch_updates
    
    if not _batch_mode:
        return
    
    with log_timing(log, "playlist_batch_flush"):
        files_written = 0
        shows_in_playlists = 0
        
        # Get shows data (excluding removals)
        shows_data = _batch_updates.get('shows', {})
        removals = _batch_updates.get('removals', set())
        
        # Filter out removed shows
        active_shows = {sid: data for sid, data in shows_data.items() if sid not in removals}
        
        # Apply show filter if provided
        if filter_show_ids is not None:
            active_shows = {sid: data for sid, data in active_shows.items() 
                          if sid in filter_show_ids}
        
        # Categorize shows
        all_shows_list: List[Tuple[int, str, str]] = []
        continue_watching_list: List[Tuple[int, str, str]] = []
        start_fresh_list: List[Tuple[int, str, str]] = []
        show_premieres_list: List[Tuple[int, str, str]] = []
        season_premieres_list: List[Tuple[int, str, str]] = []
        
        for show_id, data in active_shows.items():
            entry = (show_id, data['filename'], data['title'])
            all_shows_list.append(entry)
            
            # Category playlists
            if data['category'] == CATEGORY_START_FRESH:
                start_fresh_list.append(entry)
            else:
                continue_watching_list.append(entry)
            
            # Premiere playlists
            if data['premiere_category'] == CATEGORY_SHOW_PREMIERE:
                show_premieres_list.append(entry)
            elif data['premiere_category'] == CATEGORY_SEASON_PREMIERE:
                season_premieres_list.append(entry)
        
        shows_in_playlists = len(all_shows_list)
        
        # Write Episode playlists
        if episode_enabled:
            files_written += _write_episode_playlists(
                all_shows_list,
                continue_watching_list,
                start_fresh_list,
                show_premieres_list,
                season_premieres_list
            )
        
        # Write TVShow playlists
        if tvshow_enabled:
            files_written += _write_tvshow_playlists(
                all_shows_list,
                continue_watching_list,
                start_fresh_list,
                show_premieres_list,
                season_premieres_list
            )
        
        log.debug("Playlist batch complete",
                 event="playlist.batch_flush",
                 files_written=files_written,
                 shows_count=shows_in_playlists,
                 episode_enabled=episode_enabled,
                 tvshow_enabled=tvshow_enabled)
    
    # Reset batch state
    _batch_mode = False
    _batch_updates = {}


def _write_episode_playlists(
    all_shows: List[Tuple[int, str, str]],
    continue_watching: List[Tuple[int, str, str]],
    start_fresh: List[Tuple[int, str, str]],
    show_premieres: List[Tuple[int, str, str]],
    season_premieres: List[Tuple[int, str, str]]
) -> int:
    """
    Write all Episode-type playlists.
    
    Args:
        all_shows: List of (show_id, filename, title) tuples
        continue_watching: List of entries for Continue Watching
        start_fresh: List of entries for Start Fresh
        show_premieres: List of entries for Show Premieres
        season_premieres: List of entries for Season Premieres
        
    Returns:
        Number of files written
    """
    config = PLAYLIST_CONFIG
    playlist_dir = _get_playlist_location()
    files_written = 0
    
    playlists = [
        (config.episode.all_shows, all_shows),
        (config.episode.continue_watching, continue_watching),
        (config.episode.start_fresh, start_fresh),
        (config.episode.show_premieres, show_premieres),
        (config.episode.season_premieres, season_premieres),
    ]
    
    for playlist_def, entries in playlists:
        playlist_path = os.path.join(playlist_dir, playlist_def.filename)
        
        try:
            xbmc.sleep(FILE_WRITE_DELAY_MS)
            
            with open(playlist_path, 'w', encoding='utf-8') as f:
                # Write header
                f.write(config.episode_xml_header(playlist_def.display_name))
                
                # Write entries sorted by show_id for consistent output
                for show_id, filename, _ in sorted(entries, key=lambda x: x[0]):
                    f.write(config.episode_entry(show_id, filename))
                
                # Write footer
                f.write(config.episode_xml_footer)
            
            files_written += 1
            
        except (IOError, OSError):
            log.exception("Episode playlist write failed",
                         event="playlist.fail",
                         playlist=playlist_def.filename)
    
    return files_written


def _write_tvshow_playlists(
    all_shows: List[Tuple[int, str, str]],
    continue_watching: List[Tuple[int, str, str]],
    start_fresh: List[Tuple[int, str, str]],
    show_premieres: List[Tuple[int, str, str]],
    season_premieres: List[Tuple[int, str, str]]
) -> int:
    """
    Write all TVShow-type playlists.
    
    Args:
        all_shows: List of (show_id, filename, title) tuples
        continue_watching: List of entries for Continue Watching
        start_fresh: List of entries for Start Fresh
        show_premieres: List of entries for Show Premieres
        season_premieres: List of entries for Season Premieres
        
    Returns:
        Number of files written
    """
    config = PLAYLIST_CONFIG
    playlist_dir = _get_playlist_location()
    files_written = 0
    
    playlists = [
        (config.tvshow.all_shows, all_shows),
        (config.tvshow.continue_watching, continue_watching),
        (config.tvshow.start_fresh, start_fresh),
        (config.tvshow.show_premieres, show_premieres),
        (config.tvshow.season_premieres, season_premieres),
    ]
    
    for playlist_def, entries in playlists:
        playlist_path = os.path.join(playlist_dir, playlist_def.filename)
        
        try:
            xbmc.sleep(FILE_WRITE_DELAY_MS)
            
            with open(playlist_path, 'w', encoding='utf-8') as f:
                # Write header
                f.write(config.tvshow_xml_header(playlist_def.display_name))
                
                # Write entries sorted by show_id for consistent output
                for show_id, _, title in sorted(entries, key=lambda x: x[0]):
                    f.write(config.tvshow_entry(show_id, title))
                
                # Write footer
                f.write(config.tvshow_xml_footer)
            
            files_written += 1
            
        except (IOError, OSError):
            log.exception("TVShow playlist write failed",
                         event="playlist.fail",
                         playlist=playlist_def.filename)
    
    return files_written


# =============================================================================
# Public API Functions
# =============================================================================

def remove_show_from_all_playlists(
    show_id: int,
    episode_enabled: bool = True,
    tvshow_enabled: bool = False,
    quiet: bool = False
) -> None:
    """
    Remove a show from all EasyTV smart playlists.
    
    Called when a show has no more unwatched episodes (user completed the series).
    
    Args:
        show_id: TV show database ID to remove
        episode_enabled: If True, remove from Episode playlists
        tvshow_enabled: If True, remove from TVShow playlists
        quiet: If True, suppress debug logging (for bulk operations)
    """
    # In batch mode, mark for removal
    if _batch_mode:
        _batch_updates['removals'].add(show_id)
        # Also remove from shows dict if present
        if show_id in _batch_updates['shows']:
            del _batch_updates['shows'][show_id]
        return
    
    # Non-batch mode: immediate removal from all playlist files
    if not quiet:
        log.debug("Removing show from all playlists", show_id=show_id)
    
    config = PLAYLIST_CONFIG
    
    if episode_enabled:
        for playlist_def in [
            config.episode.all_shows,
            config.episode.continue_watching,
            config.episode.start_fresh,
            config.episode.show_premieres,
            config.episode.season_premieres,
        ]:
            _remove_show_from_playlist_file(
                playlist_def.filename,
                playlist_def.display_name,
                show_id,
                quiet
            )
    
    if tvshow_enabled:
        for playlist_def in [
            config.tvshow.all_shows,
            config.tvshow.continue_watching,
            config.tvshow.start_fresh,
            config.tvshow.show_premieres,
            config.tvshow.season_premieres,
        ]:
            _remove_show_from_playlist_file(
                playlist_def.filename,
                playlist_def.display_name,
                show_id,
                quiet
            )
    
    if not quiet:
        log.debug("Show removed from all playlists", show_id=show_id)


def update_show_in_playlists(
    show_id: int,
    filename: str,
    show_title: str,
    category: str,
    premiere_category: str,
    episode_enabled: bool = True,
    tvshow_enabled: bool = False,
    quiet: bool = False
) -> None:
    """
    Update a show's entry across all EasyTV smart playlists.
    
    Adds/updates the show in "All Shows" and the appropriate category playlists,
    while removing it from inapplicable playlists (in case show moved categories).
    
    Args:
        show_id: TV show database ID
        filename: Episode filename for Episode playlist rules
        show_title: TV show title for TVShow playlist rules
        category: Category identifier (CATEGORY_START_FRESH or CATEGORY_CONTINUE_WATCHING)
        premiere_category: Premiere type (CATEGORY_SHOW_PREMIERE, CATEGORY_SEASON_PREMIERE, or empty)
        episode_enabled: If True, update Episode playlists
        tvshow_enabled: If True, update TVShow playlists
        quiet: If True, suppress debug logging (for bulk operations)
    """
    # In batch mode, collect the update
    if _batch_mode:
        # Remove from removals set if present (show has episodes again)
        _batch_updates['removals'].discard(show_id)
        
        # Store show data
        _batch_updates['shows'][show_id] = {
            'filename': filename,
            'title': show_title,
            'category': category,
            'premiere_category': premiere_category
        }
        return
    
    # Non-batch mode: immediate update to playlist files
    if not quiet:
        log.debug("Updating smart playlists",
                 show_id=show_id, category=category,
                 premiere_category=premiere_category)
    
    config = PLAYLIST_CONFIG
    
    # Update Episode playlists
    if episode_enabled:
        _update_episode_playlists(
            show_id, filename, category, premiere_category, config, quiet
        )
    
    # Update TVShow playlists
    if tvshow_enabled:
        _update_tvshow_playlists(
            show_id, show_title, category, premiere_category, config, quiet
        )
    
    if not quiet:
        log.debug("Smart playlists updated",
                 show_id=show_id, category=category)


def _update_episode_playlists(
    show_id: int,
    filename: str,
    category: str,
    premiere_category: str,
    config: Any,
    quiet: bool
) -> None:
    """Update Episode-type playlists for a show."""
    # Always write to "All Shows"
    _write_show_to_playlist_file(
        config.episode.all_shows.filename,
        config.episode.all_shows.display_name,
        show_id, filename, 'episode', quiet
    )
    
    # Write to appropriate category playlist and remove from opposite
    if category == CATEGORY_START_FRESH:
        _write_show_to_playlist_file(
            config.episode.start_fresh.filename,
            config.episode.start_fresh.display_name,
            show_id, filename, 'episode', quiet
        )
        _remove_show_from_playlist_file(
            config.episode.continue_watching.filename,
            config.episode.continue_watching.display_name,
            show_id, quiet
        )
    else:
        _write_show_to_playlist_file(
            config.episode.continue_watching.filename,
            config.episode.continue_watching.display_name,
            show_id, filename, 'episode', quiet
        )
        _remove_show_from_playlist_file(
            config.episode.start_fresh.filename,
            config.episode.start_fresh.display_name,
            show_id, quiet
        )
    
    # Handle premiere playlists
    if premiere_category == CATEGORY_SHOW_PREMIERE:
        _write_show_to_playlist_file(
            config.episode.show_premieres.filename,
            config.episode.show_premieres.display_name,
            show_id, filename, 'episode', quiet
        )
        _remove_show_from_playlist_file(
            config.episode.season_premieres.filename,
            config.episode.season_premieres.display_name,
            show_id, quiet
        )
    elif premiere_category == CATEGORY_SEASON_PREMIERE:
        _write_show_to_playlist_file(
            config.episode.season_premieres.filename,
            config.episode.season_premieres.display_name,
            show_id, filename, 'episode', quiet
        )
        _remove_show_from_playlist_file(
            config.episode.show_premieres.filename,
            config.episode.show_premieres.display_name,
            show_id, quiet
        )
    else:
        _remove_show_from_playlist_file(
            config.episode.show_premieres.filename,
            config.episode.show_premieres.display_name,
            show_id, quiet
        )
        _remove_show_from_playlist_file(
            config.episode.season_premieres.filename,
            config.episode.season_premieres.display_name,
            show_id, quiet
        )


def _update_tvshow_playlists(
    show_id: int,
    show_title: str,
    category: str,
    premiere_category: str,
    config: Any,
    quiet: bool
) -> None:
    """Update TVShow-type playlists for a show."""
    # Always write to "All Shows"
    _write_show_to_playlist_file(
        config.tvshow.all_shows.filename,
        config.tvshow.all_shows.display_name,
        show_id, show_title, 'tvshow', quiet
    )
    
    # Write to appropriate category playlist and remove from opposite
    if category == CATEGORY_START_FRESH:
        _write_show_to_playlist_file(
            config.tvshow.start_fresh.filename,
            config.tvshow.start_fresh.display_name,
            show_id, show_title, 'tvshow', quiet
        )
        _remove_show_from_playlist_file(
            config.tvshow.continue_watching.filename,
            config.tvshow.continue_watching.display_name,
            show_id, quiet
        )
    else:
        _write_show_to_playlist_file(
            config.tvshow.continue_watching.filename,
            config.tvshow.continue_watching.display_name,
            show_id, show_title, 'tvshow', quiet
        )
        _remove_show_from_playlist_file(
            config.tvshow.start_fresh.filename,
            config.tvshow.start_fresh.display_name,
            show_id, quiet
        )
    
    # Handle premiere playlists
    if premiere_category == CATEGORY_SHOW_PREMIERE:
        _write_show_to_playlist_file(
            config.tvshow.show_premieres.filename,
            config.tvshow.show_premieres.display_name,
            show_id, show_title, 'tvshow', quiet
        )
        _remove_show_from_playlist_file(
            config.tvshow.season_premieres.filename,
            config.tvshow.season_premieres.display_name,
            show_id, quiet
        )
    elif premiere_category == CATEGORY_SEASON_PREMIERE:
        _write_show_to_playlist_file(
            config.tvshow.season_premieres.filename,
            config.tvshow.season_premieres.display_name,
            show_id, show_title, 'tvshow', quiet
        )
        _remove_show_from_playlist_file(
            config.tvshow.show_premieres.filename,
            config.tvshow.show_premieres.display_name,
            show_id, quiet
        )
    else:
        _remove_show_from_playlist_file(
            config.tvshow.show_premieres.filename,
            config.tvshow.show_premieres.display_name,
            show_id, quiet
        )
        _remove_show_from_playlist_file(
            config.tvshow.season_premieres.filename,
            config.tvshow.season_premieres.display_name,
            show_id, quiet
        )


# =============================================================================
# Internal File Operations
# =============================================================================

def _write_show_to_playlist_file(
    playlist_filename: str,
    playlist_name: str,
    show_id: int,
    value: str,
    playlist_type: str,
    quiet: bool = False
) -> bool:
    """
    Write or update a show entry in a playlist file.
    
    Args:
        playlist_filename: Filename for the .xsp file
        playlist_name: Display name for the playlist
        show_id: TV show database ID
        value: Filename (for episode) or title (for tvshow)
        playlist_type: 'episode' or 'tvshow'
        quiet: If True, suppress debug logging
        
    Returns:
        True if operation succeeded, False on error
    """
    playlist_path = os.path.join(_get_playlist_location(), playlist_filename)
    config = PLAYLIST_CONFIG
    
    # Determine header, footer, and entry format based on type
    if playlist_type == 'episode':
        header = config.episode_xml_header(playlist_name)
        footer = config.episode_xml_footer
        show_entry = config.episode_entry(show_id, value)
    else:
        header = config.tvshow_xml_header(playlist_name)
        footer = config.tvshow_xml_footer
        show_entry = config.tvshow_entry(show_id, value)
    
    show_marker = "<!--%s-->" % show_id
    
    # Read existing file contents
    try:
        with open(playlist_path, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
    except (IOError, OSError):
        all_lines = []
    
    content = []
    found = False
    action_taken = None
    
    xbmc.sleep(FILE_WRITE_DELAY_MS)
    
    try:
        with open(playlist_path, 'w+', encoding='utf-8') as f:
            if not all_lines:
                # Create new file
                content.append(header)
                content.append(show_entry)
                content.append(footer)
                action_taken = 'created'
            else:
                for line in all_lines:
                    if show_marker in line:
                        found = True
                        content.append(show_entry)
                        action_taken = 'updated'
                        continue
                    
                    if not found and line.strip() == footer.strip():
                        content.append(show_entry)
                        action_taken = 'added'
                        content.append(line)
                    else:
                        content.append(line)
            
            f.write(''.join(content))
        
        if action_taken and not quiet:
            log.debug("Playlist entry %s" % action_taken,
                     playlist=playlist_name, show_id=show_id)
        
        return True
        
    except (IOError, OSError):
        log.exception("Playlist write failed",
                      event="playlist.fail",
                      playlist=playlist_name, show_id=show_id)
        return False


def _remove_show_from_playlist_file(
    playlist_filename: str,
    playlist_name: str,
    show_id: int,
    quiet: bool = False
) -> bool:
    """
    Remove a show entry from a playlist file.
    
    Args:
        playlist_filename: Filename for the .xsp file
        playlist_name: Display name for the playlist
        show_id: TV show database ID
        quiet: If True, suppress debug logging
        
    Returns:
        True if operation succeeded, False on error
    """
    playlist_path = os.path.join(_get_playlist_location(), playlist_filename)
    
    # Read existing file contents
    try:
        with open(playlist_path, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
    except (IOError, OSError):
        # File doesn't exist, nothing to remove
        return True
    
    show_marker = "<!--%s-->" % show_id
    content = []
    removed = False
    
    for line in all_lines:
        if show_marker in line:
            removed = True
            continue
        content.append(line)
    
    if not removed:
        # Show wasn't in this playlist
        return True
    
    xbmc.sleep(FILE_WRITE_DELAY_MS)
    
    try:
        with open(playlist_path, 'w', encoding='utf-8') as f:
            f.write(''.join(content))
        
        if not quiet:
            log.debug("Playlist entry removed",
                     playlist=playlist_name, show_id=show_id)
        
        return True
        
    except (IOError, OSError):
        log.exception("Playlist removal failed",
                      event="playlist.fail",
                      playlist=playlist_name, show_id=show_id)
        return False
