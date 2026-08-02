"""Cached addon settings access."""
from __future__ import annotations

from typing import Any, Dict, Optional
import threading

import xbmcaddon


class KodiSettings:
    """Cached addon settings accessor to reduce repeated xbmcaddon.Addon() instantiation."""

    _cache: Dict[str, Any] = {}
    _cache_lock = threading.Lock()
    _addon: Optional[xbmcaddon.Addon] = None
    _addon_lock = threading.Lock()

    @classmethod
    def _get_addon(cls) -> xbmcaddon.Addon:
        """Get cached addon instance with thread safety."""
        if cls._addon is None:
            with cls._addon_lock:
                if cls._addon is None:
                    cls._addon = xbmcaddon.Addon()
        return cls._addon

    @classmethod
    def get_bool(cls, key: str) -> bool:
        """Get boolean setting with caching."""
        with cls._cache_lock:
            if key not in cls._cache:
                cls._cache[key] = cls._get_addon().getSettingBool(key)
            return cls._cache[key]

    @classmethod
    def get_string(cls, key: str) -> str:
        """Get string setting with caching."""
        with cls._cache_lock:
            if key not in cls._cache:
                cls._cache[key] = cls._get_addon().getSetting(key).strip()
            return cls._cache[key]

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the settings cache. Use when settings change externally."""
        with cls._cache_lock:
            cls._cache.clear()

    @classmethod
    def debug_enabled(cls) -> bool:
        """Check if debug logging is enabled."""
        return cls.get_bool('enable_debug')

    @classmethod
    def prefer_fanart_language(cls) -> bool:
        """Check if fanart language preference is enabled."""
        return cls.get_bool('prefer_fanart_language')

    @classmethod
    def online_metadata_language(cls) -> str:
        """Get preferred language for online metadata (TMDb titles, plots, etc.)."""
        return cls.get_string('online.metadata_language') or 'en'

    @classmethod
    def enable_combo_workflows(cls) -> bool:
        """Check if download combo workflows are enabled."""
        return cls.get_bool('download.enable_combo_workflows')

    @classmethod
    def download_after_manage_artwork(cls) -> bool:
        """Check if artwork should be downloaded after Manage Artwork selection."""
        return cls.get_bool('download.after_manage_artwork')

    @classmethod
    def existing_file_mode(cls) -> str:
        """Get existing file mode for downloads."""
        return cls.get_string('download.existing_file_mode')

    @classmethod
    def tmdb_use_custom_key(cls) -> bool:
        """Check if custom TMDB API key should be used."""
        return cls.get_bool('tmdb_use_custom_key')

    @classmethod
    def tmdb_api_key(cls) -> str:
        """Get TMDB API key."""
        return cls.get_string('tmdb_api_key')

    @classmethod
    def fanarttv_api_key(cls) -> str:
        """Get Fanart.tv personal API key."""
        return cls.get_string('fanarttv_api_key')

    @classmethod
    def preferred_language(cls) -> str:
        """Get preferred language setting."""
        return cls.get_string('preferred_language')

    @classmethod
    def art_types_to_check(cls) -> str:
        """Get enabled art types from individual boolean settings."""
        art_types = []
        type_map = [
            ('art_type_poster', 'poster'),
            ('art_type_fanart', 'fanart'),
            ('art_type_clearlogo', 'clearlogo'),
            ('art_type_clearart', 'clearart'),
            ('art_type_banner', 'banner'),
            ('art_type_landscape', 'landscape'),
            ('art_type_discart', 'discart'),
            ('art_type_keyart', 'keyart'),
            ('art_type_characterart', 'characterart'),
        ]
        for setting_id, art_type in type_map:
            if cls.get_bool(setting_id):
                art_types.append(art_type)
        return ','.join(art_types)

