"""
Settings loader for EasyMovie.

Reads all addon settings and produces typed configuration
objects used by the rest of the addon.

Logging:
    Logger: 'ui'
    Key events: None (settings are logged by ui/main.py at launch.settings)
    See LOGGING.md for full guidelines.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List, Optional, Tuple

from resources.lib.utils import get_bool_setting, get_int_setting, get_string_setting, get_logger
from resources.lib.constants import (
    FILTER_ASK, FILTER_SKIP,
    WATCHED_UNWATCHED,
    YEAR_FILTER_AFTER,
    VIEW_SHOWCASE,
    SORT_RANDOM, SORT_DESC,
    CONTINUATION_DEFAULT_CONTINUE_SET,
    MODE_ASK,
    THEME_GOLDEN_HOUR,
)

log = get_logger('ui')


@dataclass
class FilterSettings:
    """Pre-configured filter values from settings."""
    ignore_genre_mode: int = FILTER_SKIP
    ignore_genre_match_and: bool = False
    preset_ignore_genres: Optional[List[str]] = None
    genre_mode: int = FILTER_ASK
    genre_match_and: bool = False
    preset_genres: Optional[List[str]] = None
    watched_mode: int = FILTER_ASK
    watched_preset: int = WATCHED_UNWATCHED
    mpaa_mode: int = FILTER_SKIP
    preset_mpaa: Optional[List[str]] = None
    runtime_mode: int = FILTER_SKIP
    runtime_min: int = 0
    runtime_max: int = 0
    year_mode: int = FILTER_SKIP
    year_filter_type: int = YEAR_FILTER_AFTER
    year_from: int = 0
    year_to: int = 0
    year_recency: int = 5
    score_mode: int = FILTER_SKIP
    min_score: int = 0


@dataclass
class BrowseSettings:
    """Browse mode configuration."""
    view_style: int = VIEW_SHOWCASE
    return_to_list: bool = True
    result_count: int = 10
    sort_by: int = SORT_RANDOM
    sort_dir: int = SORT_DESC


@dataclass
class PlaylistSettings:
    """Playlist mode configuration."""
    movie_count: int = 5
    sort_by: int = SORT_RANDOM
    sort_dir: int = SORT_DESC
    prioritize_in_progress: bool = True
    resume_from_position: bool = True


@dataclass
class SetSettings:
    """Movie set configuration."""
    enabled: bool = True
    show_set_info: bool = True
    continuation_enabled: bool = True
    continuation_duration: int = 20
    continuation_default: int = CONTINUATION_DEFAULT_CONTINUE_SET


@dataclass
class PlaybackSettings:
    """Playback configuration."""
    check_in_progress: bool = True
    show_info_when_playing: bool = True
    show_processing_notifications: bool = True


@dataclass
class AdvancedSettings:
    """Advanced configuration."""
    movie_pool_enabled: bool = False
    movie_pool_path: str = ""
    avoid_resurface: bool = True
    resurface_window: int = 3  # Index into RESURFACE_WINDOWS (24h)
    remember_filters: bool = True
    show_counts: bool = True
    cumulative_counts: bool = False
    debug_logging: bool = False


def _parse_json_list(value: str) -> Optional[List[str]]:
    """Parse a JSON string into a list, returning None on failure."""
    if not value:
        return None
    try:
        result = json.loads(value)
        if isinstance(result, list):
            return result
    except (json.JSONDecodeError, TypeError):
        pass
    return None


def load_settings(
    addon_id: Optional[str] = None,
) -> Tuple[int, int, FilterSettings, BrowseSettings, PlaylistSettings,
           SetSettings, PlaybackSettings, AdvancedSettings]:
    """Load all settings.

    Args:
        addon_id: Optional addon ID for clone support.

    Returns:
        Tuple of (primary_function, theme, FilterSettings,
        BrowseSettings, PlaylistSettings, SetSettings,
        PlaybackSettings, AdvancedSettings)
    """
    # Main
    primary_function = get_int_setting('primary_function', addon_id, default=MODE_ASK)
    theme = get_int_setting('theme', addon_id, default=THEME_GOLDEN_HOUR)

    # Filters
    filter_settings = FilterSettings(
        ignore_genre_mode=get_int_setting('ignore_genre_mode', addon_id, default=FILTER_SKIP),
        ignore_genre_match_and=get_int_setting('ignore_genre_match', addon_id, default=0) == 1,
        preset_ignore_genres=_parse_json_list(get_string_setting('selected_ignore_genres', addon_id)),
        genre_mode=get_int_setting('genre_mode', addon_id, default=FILTER_ASK),
        genre_match_and=get_int_setting('genre_match', addon_id, default=0) == 1,
        preset_genres=_parse_json_list(get_string_setting('selected_genres', addon_id)),
        watched_mode=get_int_setting('watched_mode', addon_id, default=FILTER_ASK),
        watched_preset=get_int_setting('watched_preset', addon_id, default=WATCHED_UNWATCHED),
        mpaa_mode=get_int_setting('mpaa_mode', addon_id, default=FILTER_SKIP),
        preset_mpaa=_parse_json_list(get_string_setting('selected_mpaa', addon_id)),
        runtime_mode=get_int_setting('runtime_mode', addon_id, default=FILTER_SKIP),
        runtime_min=get_int_setting('runtime_min', addon_id, default=0),
        runtime_max=get_int_setting('runtime_max', addon_id, default=0),
        year_mode=get_int_setting('year_mode', addon_id, default=FILTER_SKIP),
        year_filter_type=get_int_setting('year_filter_type', addon_id, default=YEAR_FILTER_AFTER),
        year_from=get_int_setting('year_from', addon_id, default=0),
        year_to=get_int_setting('year_to', addon_id, default=0),
        year_recency=get_int_setting('year_recency', addon_id, default=5),
        score_mode=get_int_setting('score_mode', addon_id, default=FILTER_SKIP),
        min_score=get_int_setting('min_score', addon_id, default=0),
    )

    # Browse
    browse_settings = BrowseSettings(
        view_style=get_int_setting('view_style', addon_id, default=VIEW_SHOWCASE),
        return_to_list=get_bool_setting('return_to_list', addon_id),
        result_count=get_int_setting('browse_count', addon_id, default=10),
        sort_by=get_int_setting('browse_sort', addon_id, default=SORT_RANDOM),
        sort_dir=get_int_setting('browse_sort_dir', addon_id, default=SORT_DESC),
    )

    # Playlist
    playlist_settings = PlaylistSettings(
        movie_count=get_int_setting('playlist_count', addon_id, default=5),
        sort_by=get_int_setting('playlist_sort', addon_id, default=SORT_RANDOM),
        sort_dir=get_int_setting('playlist_sort_dir', addon_id, default=SORT_DESC),
        prioritize_in_progress=get_bool_setting('prioritize_in_progress', addon_id),
        resume_from_position=get_bool_setting('resume_from_position', addon_id),
    )

    # Movie Sets
    set_settings = SetSettings(
        enabled=get_bool_setting('set_enabled', addon_id),
        show_set_info=get_bool_setting('set_show_info', addon_id),
        continuation_enabled=get_bool_setting('continuation_enabled', addon_id),
        continuation_duration=get_int_setting('continuation_duration', addon_id, default=20),
        continuation_default=get_int_setting('continuation_default', addon_id,
                                             default=CONTINUATION_DEFAULT_CONTINUE_SET),
    )

    # Playback
    playback_settings = PlaybackSettings(
        check_in_progress=get_bool_setting('check_in_progress', addon_id),
        show_info_when_playing=get_bool_setting('show_info_playing', addon_id),
        show_processing_notifications=get_bool_setting('show_notifications', addon_id),
    )

    # Advanced
    advanced_settings = AdvancedSettings(
        movie_pool_enabled=get_bool_setting('pool_enabled', addon_id),
        movie_pool_path=get_string_setting('movie_pool_playlist_path', addon_id),
        avoid_resurface=get_bool_setting('avoid_resurface', addon_id),
        resurface_window=get_int_setting('resurface_window', addon_id, default=3),
        remember_filters=get_bool_setting('remember_filters', addon_id),
        show_counts=get_bool_setting('show_counts', addon_id),
        cumulative_counts=get_bool_setting('cumulative_counts', addon_id),
        debug_logging=get_bool_setting('logging', addon_id),
    )

    return (primary_function, theme, filter_settings, browse_settings,
            playlist_settings, set_settings, playback_settings, advanced_settings)
