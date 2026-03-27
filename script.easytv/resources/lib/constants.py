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
EasyTV constants - centralized magic values.

This module consolidates all hardcoded values from throughout the codebase
to improve maintainability and make the code self-documenting.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List
from xml.sax.saxutils import escape

# =============================================================================
# Episode Selection Modes (parallel to movie_selection)
# =============================================================================
EPISODE_SELECTION_UNWATCHED = 0
EPISODE_SELECTION_WATCHED = 1
EPISODE_SELECTION_BOTH = 2

# =============================================================================
# Premiere Filter Modes
# =============================================================================
PREMIERE_SKIP = 0
PREMIERE_MIX_IN = 1
PREMIERE_ONLY = 2

# =============================================================================
# Countdown Dialog Control IDs
# =============================================================================
COUNTDOWN_HEADING = 1
COUNTDOWN_MESSAGE = 2
COUNTDOWN_YES_BUTTON = 10
COUNTDOWN_NO_BUTTON = 11
COUNTDOWN_POSTER = 20
COUNTDOWN_TIMER_LABEL = 3
COUNTDOWN_SUBTITLE = 4

# =============================================================================
# Confirm Dialog Control IDs
# =============================================================================
CONFIRM_HEADING = 1
CONFIRM_MESSAGE = 2
CONFIRM_YES_BUTTON = 10
CONFIRM_NO_BUTTON = 11

# =============================================================================
# Select Dialog Control IDs
# =============================================================================
SELECT_HEADING = 1
SELECT_LIST = 100

# =============================================================================
# Show Selector Dialog Control IDs
# =============================================================================
SELECTOR_HEADING = 1
SELECTOR_SEARCH = 2
SELECTOR_CLEAR_SEARCH = 5
SELECTOR_ENABLE_ALL = 10
SELECTOR_IGNORE_ALL = 11
SELECTOR_LIST = 100
SELECTOR_CANCEL = 20
SELECTOR_SAVE = 21

# =============================================================================
# Kodi Window IDs
# =============================================================================
KODI_HOME_WINDOW_ID = 10000
KODI_FULLSCREEN_VIDEO_WINDOW_ID = 12005

# =============================================================================
# Timing Constants (milliseconds)
# =============================================================================
# Main loops
DAEMON_LOOP_SLEEP_MS = 100
MAIN_LOOP_SLEEP_MS = 100

# Playlist operations
PLAYLIST_START_DELAY_MS = 500
PLAYLIST_ADD_DELAY_MS = 50

# Player operations
PLAYER_STOP_DELAY_MS = 100
TARGET_DETECTION_SLEEP_MS = 250

# UI operations
NOTIFICATION_DURATION_MS = 5000
CONTEXT_TOGGLE_DELAY_MS = 500
DIALOG_WAIT_SLEEP_MS = 100

# Addon operations
ADDON_ENABLE_DELAY_MS = 1000
ADDON_RESTART_DELAY_MS = 1000

# File/Service operations
SERVICE_POLL_SLEEP_MS = 10
FILE_WRITE_DELAY_MS = 10
EXPORT_COMPLETE_DELAY_MS = 100

# =============================================================================
# Timing Constants (counts/ticks)
# =============================================================================
TARGET_DETECTION_MAX_TICKS = 20
POSITION_CHECK_INTERVAL_TICKS = 50
SERVICE_POLL_TIMEOUT_TICKS = 500
DIALOG_WAIT_MAX_TICKS = 5
ISTREAM_FIX_MAX_RETRIES = 2

# Database startup timing
DB_STARTUP_CHECK_INTERVAL_MS = 1000  # Check every 1 second
DB_STARTUP_MAX_RETRIES = 30  # Wait up to 30 seconds for DB

# =============================================================================
# Playback Thresholds
# =============================================================================
# Default threshold for considering playback "complete" (90%)
# Note: This should ideally be read from Kodi's advancedsettings.xml
# using get_playcount_minimum_percent() for user customization
PLAYBACK_COMPLETE_THRESHOLD_DEFAULT = 0.90

# Maximum ratio into a movie for random seek start point
MOVIE_RANDOM_SEEK_MAX_RATIO = 0.75

# Minimum percentage into a movie for random seek (skip opening credits)
MOVIE_RANDOM_SEEK_MIN_PERCENT = 5

# Random percentage range for movie seek
RANDOM_PERCENT_MAX = 100

# Seconds to rewind when resuming playback (helps catch context)
RESUME_REWIND_SECONDS = 10

# =============================================================================
# Episode/Playcount Constants
# =============================================================================
# Season 1 - used to ignore specials (Season 0)
FIRST_REGULAR_SEASON = 1

# Initial episode value before finding actual episode
EPISODE_INITIAL_VALUE = 0

# Playcount value indicating "watched"
WATCHED_PLAYCOUNT = 1

# =============================================================================
# Smart Playlist Configuration
# =============================================================================
# Format version for playlist migration (increment when format changes)
# Version 3: Renamed playlists with Episode/TVShow prefixes
PLAYLIST_FORMAT_VERSION = 3
PLAYLIST_FORMAT_FILENAME = "playlist_format.json"


@dataclass(frozen=True)
class PlaylistDef:
    """Definition for a single smart playlist file."""
    filename: str
    display_name: str


@dataclass(frozen=True)
class PlaylistCategory:
    """
    Group of 5 playlists for one content type (Episode or TVShow).
    
    Each category contains playlists for:
    - all_shows: Every show with an ondeck episode
    - continue_watching: Shows where next episode > 1 (mid-season)
    - start_fresh: Shows where next episode = 1 (any season start)
    - show_premieres: Shows at S01E01 (brand new shows)
    - season_premieres: Shows at S02E01+ (new season of existing show)
    """
    all_shows: PlaylistDef
    continue_watching: PlaylistDef
    start_fresh: PlaylistDef
    show_premieres: PlaylistDef
    season_premieres: PlaylistDef


@dataclass(frozen=True)
class PlaylistConfig:
    """
    Complete smart playlist configuration for EasyTV.
    
    Contains definitions for both Episode and TVShow playlist types,
    plus methods for generating XML content.
    """
    episode: PlaylistCategory
    tvshow: PlaylistCategory
    episode_xml_footer: str
    tvshow_xml_footer: str
    
    def episode_xml_header(self, name: str) -> str:
        """Generate XML header for an Episode playlist."""
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
            '<smartplaylist type="episodes">'
            '<name>{name}</name>'
            '<match>one</match>\n'
        ).format(name=escape(name))
    
    def tvshow_xml_header(self, name: str) -> str:
        """Generate XML header for a TVShow playlist."""
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
            '<smartplaylist type="tvshows">'
            '<name>{name}</name>'
            '<match>one</match>\n'
        ).format(name=escape(name))
    
    def episode_entry(self, show_id: int, filename: str) -> str:
        """Generate an Episode playlist entry (matches by filename)."""
        return '<!--{show_id}--><rule field="filename" operator="is"><value>{filename}</value></rule>\n'.format(
            show_id=show_id, filename=escape(filename)
        )
    
    def tvshow_entry(self, show_id: int, title: str) -> str:
        """Generate a TVShow playlist entry (matches by show title)."""
        return '<!--{show_id}--><rule field="title" operator="is"><value>{title}</value></rule>\n'.format(
            show_id=show_id, title=escape(title)
        )
    
    def all_episode_filenames(self) -> List[str]:
        """Return list of all Episode playlist filenames."""
        return [
            self.episode.all_shows.filename,
            self.episode.continue_watching.filename,
            self.episode.start_fresh.filename,
            self.episode.show_premieres.filename,
            self.episode.season_premieres.filename,
        ]
    
    def all_tvshow_filenames(self) -> List[str]:
        """Return list of all TVShow playlist filenames."""
        return [
            self.tvshow.all_shows.filename,
            self.tvshow.continue_watching.filename,
            self.tvshow.start_fresh.filename,
            self.tvshow.show_premieres.filename,
            self.tvshow.season_premieres.filename,
        ]
    
    def all_filenames(self) -> List[str]:
        """Return list of all playlist filenames (Episode + TVShow)."""
        return self.all_episode_filenames() + self.all_tvshow_filenames()


# Singleton configuration instance
PLAYLIST_CONFIG = PlaylistConfig(
    episode=PlaylistCategory(
        all_shows=PlaylistDef(
            "EasyTV - Episode - All Shows.xsp",
            "EasyTV - Episode - All Shows"
        ),
        continue_watching=PlaylistDef(
            "EasyTV - Episode - Continue Watching.xsp",
            "EasyTV - Episode - Continue Watching"
        ),
        start_fresh=PlaylistDef(
            "EasyTV - Episode - Start Fresh.xsp",
            "EasyTV - Episode - Start Fresh"
        ),
        show_premieres=PlaylistDef(
            "EasyTV - Episode - Show Premieres.xsp",
            "EasyTV - Episode - Show Premieres"
        ),
        season_premieres=PlaylistDef(
            "EasyTV - Episode - Season Premieres.xsp",
            "EasyTV - Episode - Season Premieres"
        ),
    ),
    tvshow=PlaylistCategory(
        all_shows=PlaylistDef(
            "EasyTV - TVShow - All Shows.xsp",
            "EasyTV - TVShow - All Shows"
        ),
        continue_watching=PlaylistDef(
            "EasyTV - TVShow - Continue Watching.xsp",
            "EasyTV - TVShow - Continue Watching"
        ),
        start_fresh=PlaylistDef(
            "EasyTV - TVShow - Start Fresh.xsp",
            "EasyTV - TVShow - Start Fresh"
        ),
        show_premieres=PlaylistDef(
            "EasyTV - TVShow - Show Premieres.xsp",
            "EasyTV - TVShow - Show Premieres"
        ),
        season_premieres=PlaylistDef(
            "EasyTV - TVShow - Season Premieres.xsp",
            "EasyTV - TVShow - Season Premieres"
        ),
    ),
    episode_xml_footer='<order direction="ascending">random</order></smartplaylist>',
    tvshow_xml_footer='<order direction="ascending">sorttitle</order></smartplaylist>'
)

# Legacy playlist filenames (for cleanup during format migration)
LEGACY_PLAYLIST_FILES = [
    "EasyTV - All Shows.xsp",
    "EasyTV - Continue Watching.xsp",
    "EasyTV - Start Fresh.xsp",
    "EasyTV - Show Premieres.xsp",
    "EasyTV - Season Premieres.xsp",
]

# =============================================================================
# Show Categorization Constants
# =============================================================================
# Episode threshold for categorization
# Episode 1 (any season) = "Start Fresh", Episode > 1 = "Continue Watching"
# S01E01 = "Show Premiere", S02E01+ = "Season Premiere"
SEASON_START_EPISODE = 1

# Category identifiers (returned by categorization logic)
CATEGORY_START_FRESH = "start_fresh"
CATEGORY_CONTINUE_WATCHING = "continue_watching"
CATEGORY_SHOW_PREMIERE = "show_premiere"
CATEGORY_SEASON_PREMIERE = "season_premiere"

# =============================================================================
# Limits
# =============================================================================
# Maximum items in list views
MAX_ITEMS_HARD_LIMIT = 1000

# Initial loop limit for iStream fix
INITIAL_LOOP_LIMIT = 10

# Value to break out of playlist building loop
PLAYLIST_BUILD_BREAK_VALUE = 99999

# =============================================================================
# Time Conversions
# =============================================================================
SECONDS_PER_MINUTE = 60
SECONDS_PER_DAY = 86400.0
SECONDS_TO_MS_MULTIPLIER = 1000
PERCENT_MULTIPLIER = 100

# Decimal places for day calculations
DAYS_DECIMAL_PLACES = 1

# Singular day value for grammar check
SINGULAR_DAY_VALUE = 1.0

# =============================================================================
# Candidate Type Prefixes
# =============================================================================
# Used in random playlist to distinguish TV shows from movies
TV_CANDIDATE_PREFIX = 't'
MOVIE_CANDIDATE_PREFIX = 'm'

# =============================================================================
# Kodi Action IDs
# =============================================================================
ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92
ACTION_CONTEXT_MENU = 117
ACTION_SELECT_ITEM = 7

# =============================================================================
# Context Menu Control IDs
# =============================================================================
CONTEXT_TOGGLE_MULTISELECT = 110
CONTEXT_PLAY_SELECTION = 120
CONTEXT_PLAY_FROM_HERE = 130
CONTEXT_EXPORT_SELECTION = 140
CONTEXT_TOGGLE_WATCHED = 150
CONTEXT_IGNORE_SHOW = 160
CONTEXT_UPDATE_LIBRARY = 170
CONTEXT_REFRESH = 180

# =============================================================================
# String Utilities
# =============================================================================
# Length of "The " for sorting (to strip leading article)
ARTICLE_THE_LENGTH = 4

# =============================================================================
# Movie Weight
# =============================================================================
# Weight value when movies are disabled
NO_MOVIE_WEIGHT = 0.0

# =============================================================================
# Logging Configuration
# =============================================================================
# Log file settings
LOG_DIR_NAME = "logs"
LOG_FILENAME = "easytv.log"
LOG_MAX_SIZE_BYTES = 512 * 1024  # 500KB per file
LOG_MAX_ROTATED_FILES = 3  # Keep 3 old log files

# Log format settings
LOG_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
LOG_TIMESTAMP_TRIM = -3  # Trim microseconds to milliseconds (remove last 3 chars)
LOG_MAX_VALUE_LENGTH = 200  # Truncate long values in log output

# Default addon ID (fallback when context unavailable)
DEFAULT_ADDON_ID = "script.easytv"

# =============================================================================
# Playlist Continuation Window Properties
# =============================================================================
# JSON-encoded config for regenerating playlist
PROP_PLAYLIST_CONFIG = "EasyTV.playlist_config"
# Flag to trigger playlist regeneration from daemon
PROP_PLAYLIST_REGENERATE = "EasyTV.playlist_regenerate"
# Addon ID of the instance (main or clone) that started current playback
PROP_SOURCE_ADDON_ID = "EasyTV.SourceAddonId"

# =============================================================================
# Browse Mode Window Properties
# =============================================================================
# Session flag indicating show art has been fetched (cleared on library scan)
PROP_ART_FETCHED = "EasyTV.ArtFetched"

# =============================================================================
# Duration Filter Settings
# =============================================================================
SETTING_DURATION_FILTER_ENABLED = "duration_filter_enabled"
SETTING_DURATION_MIN = "duration_min"
SETTING_DURATION_MAX = "duration_max"

# =============================================================================
# Duration Cache
# =============================================================================
# Cache file for storing median episode durations per show
DURATION_CACHE_FILENAME = "duration_cache.json"
# Schema version for cache file format (increment on breaking changes)
DURATION_CACHE_VERSION = 1

# =============================================================================
# Service / System Window Properties
# =============================================================================
# Service lifecycle status ('starting', 'true', 'marco', 'polo')
PROP_SERVICE_RUNNING = "EasyTV_service_running"
# Addon version string
PROP_VERSION = "EasyTV.Version"
# Path to addon directory
PROP_SERVICE_PATH = "EasyTV.ServicePath"
# Whether a playlist is currently playing ('true'/'false'/'listview')
PROP_PLAYLIST_RUNNING = "EasyTV.playlist_running"
# Signal to reshuffle random order shows
PROP_RANDOM_ORDER_SHUFFLE = "EasyTV.random_order_shuffle"
# JSON-encoded list of show IDs with next episodes
PROP_SHOWS_WITH_NEXT_EPISODES = "EasyTV.shows_with_next_episodes"
# Sync revision counter for multi-instance coordination
PROP_SYNC_REV = "EasyTV.sync_rev"

# =============================================================================
# Setting IDs
# =============================================================================
SETTING_THEME = "theme"
SETTING_MULTI_INSTANCE_SYNC = "multi_instance_sync"

# =============================================================================
# Lazy Queue (Both Mode) Settings
# =============================================================================
# JSON-encoded session state for lazy queue playlist
PROP_LAZY_QUEUE_SESSION = "EasyTV.lazy_queue_session"
# Number of items to maintain in playlist buffer
LAZY_QUEUE_BUFFER_SIZE = 3

# =============================================================================
# Version Parsing
# =============================================================================
# Prerelease type ordering for version comparison
# Lower value = earlier in release cycle (alpha < beta < release)
VERSION_PRERELEASE_ALPHA = 0
VERSION_PRERELEASE_BETA = 1
VERSION_PRERELEASE_RELEASE = 2

# =============================================================================
# Shared Database Configuration (Multi-Instance Sync)
# =============================================================================
# EasyTV database naming: easytv_{kodi_base_name} (e.g., easytv_mastervideo)
EASYTV_DB_PREFIX = "easytv_"
# Table prefix for fallback when CREATE DATABASE denied
EASYTV_TABLE_PREFIX = "easytv_"
# Schema version for migrations (increment when schema changes)
EASYTV_SCHEMA_VERSION = 1
# Backoff period after DB connection failure (seconds)
EASYTV_DB_BACKOFF_SECONDS = 30
# Migration lock TTL for crash recovery (minutes)
EASYTV_MIGRATION_LOCK_TTL_MINUTES = 5
# Default Kodi video database base name
KODI_DEFAULT_VIDEO_DB_NAME = "MyVideos"

# =============================================================================
# Theme Colors (set as window properties for skin XML $INFO references)
# =============================================================================
# Theme ID → property name → AARRGGBB color value
THEME_COLORS = {
    '0': {  # Golden Hour
        'EasyTV.Accent': 'FFF5A623',
        'EasyTV.AccentGlow': 'FFF5C564',
        'EasyTV.AccentBG': '59B4781E',
        'EasyTV.ButtonTextFocused': 'FF0D1117',
        'EasyTV.ButtonFocus': 'FFD4912A',
    },
    '1': {  # Ultraviolet
        'EasyTV.Accent': 'FFA78BFA',
        'EasyTV.AccentGlow': 'FFC4B5FD',
        'EasyTV.AccentBG': '596432B4',
        'EasyTV.ButtonTextFocused': 'FFFFFFFF',
        'EasyTV.ButtonFocus': 'FF7C3AED',
    },
    '2': {  # Ember
        'EasyTV.Accent': 'FFF87171',
        'EasyTV.AccentGlow': 'FFFCA5A5',
        'EasyTV.AccentBG': '59B43232',
        'EasyTV.ButtonTextFocused': 'FFFFFFFF',
        'EasyTV.ButtonFocus': 'FFEF4444',
    },
    '3': {  # Nightfall
        'EasyTV.Accent': 'FF60A5FA',
        'EasyTV.AccentGlow': 'FF93C5FD',
        'EasyTV.AccentBG': '59286AB4',
        'EasyTV.ButtonTextFocused': 'FFFFFFFF',
        'EasyTV.ButtonFocus': 'FF3B82F6',
    },
}
