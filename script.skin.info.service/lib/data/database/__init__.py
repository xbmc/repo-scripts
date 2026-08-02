"""Database package for queue management, API caching, and data operations.

Unified database containing:
- Queue management for artwork review workflow
- API response caching (TMDB, fanart.tv)
- Workflow tracking for sessions and operations
- IMDb dataset storage and lookups
- Ratings provider caching and API usage tracking
- Slideshow pool management
- ID correction cache

Modules:
- _infrastructure: Database connections and schema
- cache: API response caching and TTL management
- correction: TMDB/IMDB ID correction cache
- gif: GIF scan cache
- imdb: IMDb dataset operations (ratings, episodes, metadata)
- music: Music metadata cache (AudioDB/Last.fm, separate DB)
- queue: Queue CRUD operations for artwork workflow
- rating: Ratings API usage tracking and provider caching
- slideshow: Slideshow pool operations
- workflow: Session and operation history tracking
"""
from lib.data.database._infrastructure import (
    DB_PATH,
    DB_VERSION,
    get_connection,
    get_db,
    init_database,
)

from lib.data.database.cache import (
    get_cache_ttl_hours,
    get_fanarttv_cache_ttl_hours,
    get_cached_artwork,
    get_cached_artwork_batch,
    cache_artwork,
    get_cached_metadata,
    cache_metadata,
    get_cached_season_metadata,
    cache_season_metadata,
    get_cached_tmdb_genre_list,
    cache_tmdb_genre_list,
    cache_person_data,
    get_cached_person_data,
    clear_expired_cache,
    get_mb_id_mapping,
    get_mb_id_mappings_by_canonical,
    save_mb_id_mapping,
)

from lib.data.database.queue import (
    ARTITEM_REVIEW_MISSING,
    clear_queue_and_sessions,
    clear_queue_for_media,
    add_to_queue,
    add_art_item,
    add_to_queue_batch,
    add_art_items_batch,
    get_next_batch,
    get_art_items_for_queue,
    get_art_items_for_queue_batch,
    update_queue_status,
    update_art_item,
    update_art_item_status,
    get_queue_stats,
    count_queue_items,
    count_pending_missing_art,
    cleanup_old_queue_items,
)

from lib.data.database.workflow import (
    get_session_media_types,
    get_session_art_types,
    create_scan_session,
    update_session_stats,
    complete_session,
    cancel_session,
    get_session,
    get_last_manual_review_session,
    save_operation_stats,
    get_last_operation_stats,
)

# New modules exported as namespaces (callers use e.g. `from lib.data.database import imdb`)
from lib.data.database import correction  # noqa: F401
from lib.data.database import gif  # noqa: F401
from lib.data.database import imdb  # noqa: F401
from lib.data.database import music  # noqa: F401
from lib.data.database import rating  # noqa: F401
from lib.data.database import runtime  # noqa: F401
from lib.data.database import slideshow  # noqa: F401

__all__ = [
    'DB_PATH',
    'DB_VERSION',
    'get_connection',
    'get_db',
    'init_database',
    'get_cache_ttl_hours',
    'get_fanarttv_cache_ttl_hours',
    'get_cached_artwork',
    'get_cached_artwork_batch',
    'cache_artwork',
    'get_cached_metadata',
    'cache_metadata',
    'get_cached_season_metadata',
    'cache_season_metadata',
    'get_cached_tmdb_genre_list',
    'cache_tmdb_genre_list',
    'cache_person_data',
    'get_cached_person_data',
    'clear_expired_cache',
    'get_mb_id_mapping',
    'get_mb_id_mappings_by_canonical',
    'save_mb_id_mapping',
    'ARTITEM_REVIEW_MISSING',
    'clear_queue_and_sessions',
    'clear_queue_for_media',
    'add_to_queue',
    'add_art_item',
    'add_to_queue_batch',
    'add_art_items_batch',
    'get_next_batch',
    'get_art_items_for_queue',
    'get_art_items_for_queue_batch',
    'update_queue_status',
    'update_art_item',
    'update_art_item_status',
    'get_queue_stats',
    'count_queue_items',
    'count_pending_missing_art',
    'cleanup_old_queue_items',
    'get_session_media_types',
    'get_session_art_types',
    'create_scan_session',
    'update_session_stats',
    'complete_session',
    'cancel_session',
    'get_session',
    'get_last_manual_review_session',
    'save_operation_stats',
    'get_last_operation_stats',
    'correction',
    'gif',
    'imdb',
    'music',
    'rating',
    'runtime',
    'slideshow',
]
