#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Copyright (C) 2024-2026 Rouzax
#
#  SPDX-License-Identifier: GPL-3.0-or-later
#  See LICENSE.txt for more information.
#

"""
Storage abstraction layer for EasyTV.

Provides a unified interface for storing and retrieving ondeck episode data,
with two backend implementations:

1. WindowPropertyStorage: For single-instance users. Uses Kodi window properties
   as the source of truth. Always returns revision=0 (always fresh).

2. SharedDatabaseStorage: For multi-instance users sharing a MySQL/MariaDB
   database. Uses the database as source of truth, with window properties
   as a local cache. Supports staleness detection via global revision counter.

The factory function `get_storage()` returns the appropriate backend based on
user settings and availability of dependencies.

Architecture:
    Consumer code calls get_storage() to get the singleton backend, then uses
    the StorageBackend interface methods. The backend handles the details of
    where data is actually stored.

Logging:
    Logger name: 'storage'
    Key events:
        - storage.init_local: Using window property storage
        - storage.init_shared: Using shared database storage
        - storage.pymysql_missing: pymysql not available, falling back
        - storage.batch_preload_error: Preload failed, falling back to unbatched
        - storage.clear_stale: Cleared window props for show deleted elsewhere
        - storage.reset: Storage singleton reset (settings changed)
"""
from __future__ import annotations

import ast
import contextlib
from abc import ABC, abstractmethod
from typing import Any, Dict, Generator, List, Optional, Tuple, Union

import xbmcaddon
import xbmcgui

from resources.lib.constants import (
    DEFAULT_ADDON_ID,
    KODI_HOME_WINDOW_ID,
    PERCENT_MULTIPLIER,
    PROP_SYNC_REV,
    SETTING_MULTI_INSTANCE_SYNC,
)
from resources.lib.utils import get_bool_setting, get_logger, json_query, lang
from resources.lib.data.queries import build_episode_details_query

log = get_logger('storage')

# Window for storing properties
WINDOW = xbmcgui.Window(KODI_HOME_WINDOW_ID)

# Property prefix for EasyTV window properties
PROPERTY_PREFIX = "EasyTV"

# All window properties that need to be managed for a show
# These match the properties defined in episode_tracker.py
SHOW_PROPERTIES = [
    "Title",
    "Episode",
    "EpisodeNo",
    "Season",
    "TVshowTitle",
    "Art(tvshow.poster)",
    "Resume",
    "PercentPlayed",
    "CountWatchedEps",
    "CountUnwatchedEps",
    "CountonDeckEps",
    "EpisodeID",
    "ondeck_list",
    "offdeck_list",
    "File",
    "Art(tvshow.fanart)",
    "Premiered",
    "Plot",
    "IsSkipped",
    "Duration",
]


def _build_property_key(show_id: Union[int, str], prop_name: str) -> str:
    """Build a window property key for a show."""
    return f"{PROPERTY_PREFIX}.{show_id}.{prop_name}"


def _parse_list(value: str) -> List[int]:
    """
    Parse a string representation of a list into a list of integers.
    
    Handles both '[]' string format and actual list representations.
    
    Args:
        value: String like '[1, 2, 3]' or empty string.
    
    Returns:
        List of integers, or empty list if parsing fails.
    """
    if not value or value == '[]':
        return []
    try:
        parsed = ast.literal_eval(value)
        if isinstance(parsed, list):
            return [int(x) for x in parsed]
        return []
    except (ValueError, SyntaxError):
        return []


# =============================================================================
# Abstract Base Class
# =============================================================================

class StorageBackend(ABC):
    """
    Abstract interface for ondeck data storage.
    
    Implementations must provide methods for reading and writing ondeck
    episode data, as well as staleness detection for multi-instance sync.
    """
    
    @abstractmethod
    def get_ondeck(self, show_id: int) -> Optional[Dict[str, Any]]:
        """
        Get ondeck data for a single show.
        
        Args:
            show_id: The Kodi TV show ID.
        
        Returns:
            Dictionary with ondeck data, or None if not found.
            Keys: ondeck_episode_id, ondeck_list, offdeck_list,
                  watched_count, unwatched_count, show_title, show_year
        """
        ...
    
    @abstractmethod
    def get_ondeck_bulk(self, show_ids: List[int], refresh_display: bool = False) -> Tuple[Dict[int, Dict[str, Any]], int]:
        """
        Get ondeck data for multiple shows.

        Args:
            show_ids: List of Kodi TV show IDs.
            refresh_display: If True, fetch display properties from Kodi for
                shows where the ondeck episode has changed (SharedDatabaseStorage only).

        Returns:
            Tuple of (data_dict, current_revision) where:
                - data_dict: {show_id: {ondeck data}}
                - current_revision: The global_rev at time of read
        """
        ...
    
    @abstractmethod
    def set_ondeck(self, show_id: int, data: Dict[str, Any]) -> None:
        """
        Store ondeck data for a show.
        
        For SharedDatabaseStorage, this atomically increments the global
        revision counter.
        
        Args:
            show_id: The Kodi TV show ID.
            data: Dictionary containing:
                - ondeck_episode_id: int
                - ondeck_list: List[int] (optional)
                - offdeck_list: List[int] (optional)
                - watched_count: int (optional)
                - unwatched_count: int (optional)
                - show_title: str (optional)
                - show_year: int (optional)
        """
        ...
    
    @abstractmethod
    def needs_refresh(self) -> bool:
        """
        Check if local cache may be stale.
        
        This is an O(1) operation - just compares revision numbers.
        
        Returns:
            True if data should be refreshed from the source, False otherwise.
            WindowPropertyStorage always returns False (single instance is
            always authoritative). SharedDatabaseStorage compares local vs
            remote revision.
        """
        ...
    
    @abstractmethod
    def mark_refreshed(self, revision: int) -> None:
        """
        Mark local cache as current with the given revision.
        
        Call this after successfully refreshing data, passing the revision
        that was returned by get_ondeck_bulk().
        
        Args:
            revision: The revision number from the read operation.
        """
        ...
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if storage backend is operational.
        
        Returns:
            True if backend is available and can handle requests.
        """
        ...
    
    @contextlib.contextmanager
    def batch_write(
        self, show_ids: List[int]
    ) -> Generator[None, None, None]:
        """
        Context manager for batch write operations.
        
        Optimizes bulk writes by deferring commits and revision updates.
        After the context exits, all writes are committed in a single
        transaction.
        
        The default implementation is a no-op (yields immediately),
        suitable for WindowPropertyStorage where no batching is needed.
        SharedDatabaseStorage overrides this to provide preload, deferred
        commit, and revision management.
        
        Args:
            show_ids: List of show IDs that will be written in this batch.
                     Used by SharedDatabaseStorage to preload existing data
                     for skip-if-unchanged optimization.
        """
        yield


# =============================================================================
# WindowPropertyStorage (Single Instance)
# =============================================================================

class WindowPropertyStorage(StorageBackend):
    """
    Storage backed by window properties only.
    
    For single-instance users where window properties are the source of truth.
    Always returns revision=0 and needs_refresh() always returns False since
    there's no external source that could have newer data.
    """
    
    def get_ondeck(self, show_id: int) -> Optional[Dict[str, Any]]:
        """Get ondeck data from window properties."""
        episode_id_str = WINDOW.getProperty(_build_property_key(show_id, "EpisodeID"))
        if not episode_id_str:
            return None
        
        try:
            ondeck_episode_id = int(episode_id_str)
        except (ValueError, TypeError):
            return None
        
        return {
            'ondeck_episode_id': ondeck_episode_id,
            'ondeck_list': _parse_list(
                WINDOW.getProperty(_build_property_key(show_id, "ondeck_list"))
            ),
            'offdeck_list': _parse_list(
                WINDOW.getProperty(_build_property_key(show_id, "offdeck_list"))
            ),
            'watched_count': self._get_int_property(show_id, "CountWatchedEps"),
            'unwatched_count': self._get_int_property(show_id, "CountUnwatchedEps"),
            'show_title': WINDOW.getProperty(_build_property_key(show_id, "TVshowTitle")),
            'show_year': None,  # Not stored in window properties
        }
    
    def get_ondeck_bulk(self, show_ids: List[int], refresh_display: bool = False) -> Tuple[Dict[int, Dict[str, Any]], int]:
        """Get ondeck data for multiple shows."""
        data = {}
        for show_id in show_ids:
            show_data = self.get_ondeck(show_id)
            if show_data is not None:
                data[show_id] = show_data
        return data, 0  # Revision 0 = always fresh for single instance
    
    def set_ondeck(self, show_id: int, data: Dict[str, Any]) -> None:
        """Store ondeck data in window properties."""
        WINDOW.setProperty(
            _build_property_key(show_id, "EpisodeID"),
            str(data.get('ondeck_episode_id', ''))
        )
        WINDOW.setProperty(
            _build_property_key(show_id, "ondeck_list"),
            str(data.get('ondeck_list', []))
        )
        WINDOW.setProperty(
            _build_property_key(show_id, "offdeck_list"),
            str(data.get('offdeck_list', []))
        )
        WINDOW.setProperty(
            _build_property_key(show_id, "CountWatchedEps"),
            str(data.get('watched_count', 0))
        )
        WINDOW.setProperty(
            _build_property_key(show_id, "CountUnwatchedEps"),
            str(data.get('unwatched_count', 0))
        )
    
    def needs_refresh(self) -> bool:
        """Single instance: local cache is always authoritative."""
        return False
    
    def mark_refreshed(self, revision: int) -> None:
        """No-op for single instance."""
        pass
    
    def is_available(self) -> bool:
        """Always available."""
        return True
    
    def _get_int_property(self, show_id: int, prop_name: str) -> int:
        """Get an integer property, defaulting to 0."""
        value = WINDOW.getProperty(_build_property_key(show_id, prop_name))
        try:
            return int(value) if value else 0
        except (ValueError, TypeError):
            return 0


# =============================================================================
# SharedDatabaseStorage (Multi-Instance)
# =============================================================================

class SharedDatabaseStorage(StorageBackend):
    """
    Storage backed by shared MySQL/MariaDB database.
    
    Uses the database as the source of truth, with window properties as a
    local cache. Supports staleness detection via global revision counter,
    allowing multiple Kodi instances to stay synchronized.
    
    Window properties are updated on both read (to cache) and write (for
    local consistency). When reading, shows that exist in the request but
    not in the database have their window properties cleared (they were
    deleted on another instance).
    """
    
    def __init__(self, db: Any) -> None:
        """
        Initialize with a SharedDatabase instance.
        
        Args:
            db: A SharedDatabase instance from shared_db module.
        """
        self._db = db
        self._batch_active: bool = False
    
    @property
    def db(self) -> Any:
        """
        Expose database for advanced operations.
        
        Used by daemon.py for operations like ID migration and
        initial data migration.
        """
        return self._db
    
    def get_ondeck(self, show_id: int) -> Optional[Dict[str, Any]]:
        """Get ondeck data from database and update local cache."""
        data = self._db.get_show_tracking(show_id)
        if data:
            self._update_window_properties(show_id, data)
        return data
    
    def get_ondeck_bulk(
        self, show_ids: List[int], refresh_display: bool = False
    ) -> Tuple[Dict[int, Dict[str, Any]], int]:
        """
        Bulk fetch with atomic revision read via CROSS JOIN.
        
        Returns data and the revision AT TIME OF READ, so mark_refreshed
        stores the correct value even if another write happens during refresh.
        
        Args:
            show_ids: List of show IDs to fetch
            refresh_display: If True, fetch display properties from Kodi for
                shows where the ondeck episode has changed. Use True for
                staleness refresh (browse mode, random playlist). Use False
                for service startup (properties populated via cache_next_episode).
        """
        data, revision = self._db.get_show_tracking_bulk_with_rev(show_ids)
        
        # Update window properties for found shows
        display_refreshed = 0
        for show_id, show_data in data.items():
            if refresh_display:
                # Check if episode changed and needs display refresh
                db_episode_id = show_data.get('ondeck_episode_id')
                current_episode_str = WINDOW.getProperty(
                    _build_property_key(show_id, "EpisodeID")
                )
                
                # Compare episode IDs (handle empty/missing values)
                try:
                    current_episode_id = int(current_episode_str) if current_episode_str else None
                except (ValueError, TypeError):
                    current_episode_id = None
                
                if db_episode_id and db_episode_id != current_episode_id:
                    # Episode changed - fetch display properties from Kodi
                    if self._fetch_and_set_display_properties(show_id, db_episode_id, show_data):
                        display_refreshed += 1
                        continue
                    # Kodi query failed - fall back to tracking properties only
            
            # Default: just update tracking properties
            self._update_window_properties(show_id, show_data)
        
        if display_refreshed > 0:
            log.debug("Display properties refreshed from Kodi",
                     event="storage.display_refresh",
                     shows_refreshed=display_refreshed)
        
        # Clear window properties for shows NOT in DB (deleted elsewhere)
        for show_id in show_ids:
            if show_id not in data:
                self._clear_window_properties(show_id)
        
        return data, revision
    
    def set_ondeck(self, show_id: int, data: Dict[str, Any]) -> None:
        """
        Store ondeck data with atomic revision increment.
        
        Writes to database, updates local window property cache, and
        updates local revision to match the new revision from the write.
        
        In batch mode, the per-write revision update is skipped — the
        batch_write() context manager updates the revision once on exit.
        """
        # Atomic: write data + increment rev, returns new revision
        # (In batch mode: returns sentinel rev, real rev set by batch_write)
        new_rev = self._db.set_show_tracking(show_id, data)
        
        # Update local cache
        self._update_window_properties(show_id, data)
        
        # Update local revision (skip in batch mode — handled by batch_write)
        if not self._batch_active:
            WINDOW.setProperty(PROP_SYNC_REV, str(new_rev))
    
    def needs_refresh(self) -> bool:
        """
        Check if local cache may be stale.
        
        Compares local revision (from last refresh) with remote revision
        (current database state). If they differ, another instance has
        written data since our last refresh.
        """
        if not self._db.is_available():
            return False  # Can't refresh, use what we have
        
        remote_rev = self._db.get_global_rev()
        local_rev_str = WINDOW.getProperty(PROP_SYNC_REV)
        
        # Empty/missing local rev = definitely stale (first run or reset)
        if not local_rev_str:
            return True
        
        try:
            local_rev = int(local_rev_str)
            return remote_rev != local_rev
        except (ValueError, TypeError):
            return True
    
    def mark_refreshed(self, revision: int) -> None:
        """Store the revision that was current when we read the data."""
        WINDOW.setProperty(PROP_SYNC_REV, str(revision))
    
    def is_available(self) -> bool:
        """Check if database is available."""
        return self._db.is_available()
    
    @contextlib.contextmanager
    def batch_write(
        self, show_ids: List[int]
    ) -> Generator[None, None, None]:
        """
        Batch write with preload, deferred commit, and revision management.
        
        Preloads existing data for skip-if-unchanged optimization, then
        delegates to SharedDatabase.batch_write() for the deferred commit
        transaction. On completion, updates the local sync revision from
        the batch's final revision.
        
        If preload fails (e.g., DB temporarily unavailable), falls back to
        a no-op context — writes proceed individually without batching.
        
        Args:
            show_ids: List of show IDs that will be written in this batch.
        """
        try:
            preload_data, current_rev = self.get_ondeck_bulk(show_ids)
        except Exception as e:
            log.warning(
                "Shared DB preload failed, proceeding without batch optimization",
                event="storage.batch_preload_error",
                error=str(e)
            )
            yield
            return
        
        self._batch_active = True
        try:
            with self._db.batch_write(
                preload=preload_data, current_rev=current_rev
            ):
                yield
        finally:
            self._batch_active = False
            final_rev = self._db.batch_final_rev
            if final_rev is not None:
                WINDOW.setProperty(PROP_SYNC_REV, str(final_rev))
    
    def _update_window_properties(self, show_id: int, data: Dict[str, Any]) -> None:
        """
        Update window property cache from database data.
        
        Only updates the core tracking properties, not display properties
        like Title, Plot, etc. which are managed by episode_tracker.
        """
        WINDOW.setProperty(
            _build_property_key(show_id, "EpisodeID"),
            str(data.get('ondeck_episode_id', ''))
        )
        WINDOW.setProperty(
            _build_property_key(show_id, "ondeck_list"),
            str(data.get('ondeck_list', []))
        )
        WINDOW.setProperty(
            _build_property_key(show_id, "offdeck_list"),
            str(data.get('offdeck_list', []))
        )
        WINDOW.setProperty(
            _build_property_key(show_id, "CountWatchedEps"),
            str(data.get('watched_count', 0))
        )
        WINDOW.setProperty(
            _build_property_key(show_id, "CountUnwatchedEps"),
            str(data.get('unwatched_count', 0))
        )
    
    def _fetch_and_set_display_properties(
        self, show_id: int, episode_id: int, db_data: Dict[str, Any]
    ) -> bool:
        """
        Fetch episode details from Kodi and set all window properties.
        
        Called when the ondeck episode ID has changed (another instance
        advanced the show). Queries Kodi for the new episode's display
        properties and updates both tracking and display window properties.
        
        Args:
            show_id: The TV show ID
            episode_id: The new ondeck episode ID to fetch details for
            db_data: Tracking data from shared DB (counts, lists)
        
        Returns:
            True if successful, False if Kodi query failed
        """
        # Query Kodi for episode details
        ep_result = json_query(build_episode_details_query(episode_id), True)
        
        if 'episodedetails' not in ep_result:
            log.warning("Episode details not found during sync refresh",
                       event="storage.episode_not_found",
                       show_id=show_id, episode_id=episode_id)
            return False
        
        ep = ep_result['episodedetails']
        
        # Format episode and season numbers
        episode_num = "%02d" % int(ep.get('episode', 0))
        season_num = "%02d" % int(ep.get('season', 0))
        episode_no = f"s{season_num}e{episode_num}"
        
        # Calculate resume state
        resume_dict = ep.get('resume', {})
        resume_pos = resume_dict.get('position', 0)
        resume_total = resume_dict.get('total', 0)
        
        if resume_pos and resume_total:
            resume = "true"
            percent = int((float(resume_pos) / float(resume_total)) * PERCENT_MULTIPLIER)
            percent_played = f"{percent}%"
        else:
            resume = "false"
            percent_played = "0%"
        
        # Get artwork
        art = ep.get('art', {})
        
        # Get counts from DB data
        ondeck_list = db_data.get('ondeck_list', [])
        offdeck_list = db_data.get('offdeck_list', [])
        watched_count = db_data.get('watched_count', 0)
        unwatched_count = db_data.get('unwatched_count', 0)
        
        # Set all window properties
        props = {
            "Title": ep.get('title', ''),
            "Episode": episode_num,
            "EpisodeNo": episode_no,
            "Season": season_num,
            "TVshowTitle": ep.get('showtitle', ''),
            "Art(tvshow.poster)": art.get('tvshow.poster', ''),
            "Art(tvshow.fanart)": art.get('tvshow.fanart', ''),
            "Resume": resume,
            "PercentPlayed": percent_played,
            "CountWatchedEps": str(watched_count),
            "CountUnwatchedEps": str(unwatched_count),
            "CountonDeckEps": str(len(ondeck_list)),
            "EpisodeID": str(episode_id),
            "ondeck_list": str(ondeck_list),
            "offdeck_list": str(offdeck_list),
            "File": ep.get('file', ''),
            "Premiered": ep.get('firstaired', ''),
            "Plot": ep.get('plot', ''),
            "IsSkipped": "false",
        }
        
        for prop_name, value in props.items():
            WINDOW.setProperty(_build_property_key(show_id, prop_name), value)
        
        return True
    
    def _clear_window_properties(self, show_id: int) -> None:
        """
        Clear window properties for a show deleted on another instance.
        
        Clears all properties to ensure the show doesn't appear in the
        local instance's browse window or playlists.
        """
        for prop_name in SHOW_PROPERTIES:
            WINDOW.clearProperty(_build_property_key(show_id, prop_name))
        
        log.debug("Cleared stale window properties",
                 event="storage.clear_stale",
                 show_id=show_id)


# =============================================================================
# Factory Function
# =============================================================================

_storage_instance: Optional[StorageBackend] = None


def get_storage() -> StorageBackend:
    """
    Get the appropriate storage backend based on configuration.
    
    Returns a singleton instance - the same backend is returned on
    subsequent calls unless reset_storage() is called.
    
    Selection logic:
        1. If multi_instance_sync setting is disabled: WindowPropertyStorage
        2. If pymysql not available: WindowPropertyStorage (with warning)
        3. If database not available: WindowPropertyStorage (with warning)
        4. Otherwise: SharedDatabaseStorage
    
    Returns:
        The appropriate StorageBackend instance.
    """
    global _storage_instance
    
    if _storage_instance is not None:
        return _storage_instance
    
    # Check if multi-instance sync is enabled
    if not get_bool_setting(SETTING_MULTI_INSTANCE_SYNC):
        _storage_instance = WindowPropertyStorage()
        log.info("Using window property storage", event="storage.init_local")
        return _storage_instance
    
    # Try to import pymysql
    try:
        import pymysql
        # Check it's actually importable (suppresses unused warning)
        _ = pymysql.__version__
        del pymysql
    except ImportError:
        log.warning("Multi-instance sync enabled but pymysql not available",
                   event="storage.pymysql_missing")
        # Notify user and disable the setting
        xbmcgui.Dialog().ok("EasyTV", lang(32710))
        xbmcaddon.Addon(DEFAULT_ADDON_ID).setSetting(SETTING_MULTI_INSTANCE_SYNC, 'false')
        _storage_instance = WindowPropertyStorage()
        return _storage_instance
    
    # Try to connect to database
    from resources.lib.data.shared_db import SharedDatabase
    
    db = SharedDatabase()
    if db.is_available():
        _storage_instance = SharedDatabaseStorage(db)
        log.info("Using shared database storage",
                event="storage.init_shared",
                database=db.easytv_db_name)
    else:
        _storage_instance = WindowPropertyStorage()
        log.info("Shared DB unavailable, using window properties",
                event="storage.init_local")
    
    return _storage_instance


def reset_storage() -> None:
    """
    Reset storage instance.
    
    Call when settings change (e.g., multi_instance_sync toggled).
    Closes the database connection if one exists, then clears the
    singleton so the next get_storage() call creates a fresh instance.
    """
    global _storage_instance
    
    if _storage_instance is not None:
        # Clean up database connection if using shared storage
        if isinstance(_storage_instance, SharedDatabaseStorage):
            _storage_instance._db.close()
        
        _storage_instance = None
        log.info("Storage instance reset", event="storage.reset")


def is_shared_storage() -> bool:
    """
    Check if currently using shared database storage.
    
    Useful for code that needs to behave differently based on
    storage type without directly checking the instance type.
    
    Returns:
        True if using SharedDatabaseStorage, False otherwise.
    """
    return isinstance(_storage_instance, SharedDatabaseStorage)
