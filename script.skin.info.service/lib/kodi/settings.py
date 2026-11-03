"""Cached addon settings access."""
from __future__ import annotations

from typing import Any, Dict
import threading


class KodiSettings:
    """Cached addon settings accessor, read through the process's one shared Addon."""

    _cache: Dict[str, Any] = {}
    _cache_lock = threading.Lock()

    @classmethod
    def get_bool(cls, key: str) -> bool:
        """Get boolean setting with caching."""
        with cls._cache_lock:
            if key not in cls._cache:
                from lib.kodi.client import ADDON
                cls._cache[key] = ADDON.getSettingBool(key)
            return cls._cache[key]

    @classmethod
    def get_string(cls, key: str) -> str:
        """Get string setting with caching."""
        with cls._cache_lock:
            if key not in cls._cache:
                from lib.kodi.client import ADDON
                cls._cache[key] = ADDON.getSetting(key).strip()
            return cls._cache[key]

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the settings cache. Use when settings change externally."""
        with cls._cache_lock:
            cls._cache.clear()

    @classmethod
    def debug_enabled(cls) -> bool:
        """Whether debug logging is enabled."""
        return cls.get_bool('enable_debug')

    @classmethod
    def ratings_source_tmdb(cls) -> bool:
        """Whether TMDB takes part in a ratings update."""
        return cls.get_bool('ratings_source_tmdb')

    @classmethod
    def ratings_source_mdblist(cls) -> bool:
        """Whether MDBList takes part in a ratings update."""
        return cls.get_bool('ratings_source_mdblist')

    @classmethod
    def ratings_source_omdb(cls) -> bool:
        """Whether OMDb takes part in a ratings update."""
        return cls.get_bool('ratings_source_omdb')

    @classmethod
    def ratings_source_trakt(cls) -> bool:
        """Whether Trakt takes part in a ratings update."""
        return cls.get_bool('ratings_source_trakt')

    @classmethod
    def ratings_default_source(cls) -> str:
        """Get the rating Kodi shows by default, IMDb when unset."""
        return cls.get_string('ratings_default_source') or 'imdb'

    @classmethod
    def prefer_fanart_language(cls) -> bool:
        """Whether fanart follows the language preference."""
        return cls.get_bool('prefer_fanart_language')

    @classmethod
    def online_metadata_language(cls) -> str:
        """Get preferred language for online metadata (TMDb titles, plots, etc.)."""
        return cls.get_string('online.metadata_language') or 'en'

    @classmethod
    def enable_combo_workflows(cls) -> bool:
        """Whether the download combo workflows are enabled."""
        return cls.get_bool('download.enable_combo_workflows')

    @classmethod
    def download_after_manage_artwork(cls) -> bool:
        """Whether artwork is downloaded after a Manage Artwork selection."""
        return cls.get_bool('download.after_manage_artwork')

    @classmethod
    def existing_file_mode(cls) -> str:
        """Get existing file mode for downloads, 'skip' or 'overwrite'."""
        return 'overwrite' if cls.get_string('download.existing_file_mode') == '1' else 'skip'

    @classmethod
    def tmdb_use_custom_key(cls) -> bool:
        """Whether the user's own TMDB API key is used."""
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
    def musicvideo_thumb_source(cls) -> str:
        """Which image auto-apply puts in an empty music video thumb slot."""
        return cls.get_string('musicvideo_thumb_source') or 'screenshots'

    @classmethod
    def art_types_to_check(cls) -> str:
        """Get the enabled art types as a comma-separated string."""
        art_types = []
        type_map = [
            ('art_type_poster', 'poster'),
            ('art_type_fanart', 'fanart'),
            ('art_type_clearlogo', 'clearlogo'),
            ('art_type_clearart', 'clearart'),
            ('art_type_thumb', 'thumb'),
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
