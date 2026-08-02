"""Library artwork URL discovery + texture-cache DB queries (Textures.* JSON-RPC + library scan)."""
from __future__ import annotations

import threading
from typing import Optional, List, Dict, Set, Any, Callable

import xbmc

from lib.kodi.client import request, get_library_items, log, decode_image_url
from lib.infrastructure.dialogs import ProgressDialog


DEFAULT_TEXTURE_MEDIA_TYPES = [
    'movie', 'tvshow', 'season', 'episode', 'musicvideo', 'set', 'artist', 'album',
]
_CAST_MEDIA_TYPES = {'movie', 'tvshow', 'episode'}

_cache_lock = threading.Lock()
_cached_urls_set: Optional[Set[str]] = None


def get_cached_textures(url_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return cached textures from `Textures13.db`. `url_filter` does a partial-match filter."""
    params: Dict[str, Any] = {
        "properties": ["url", "cachedurl", "lasthashcheck", "imagehash", "sizes"]
    }

    if url_filter:
        params["filter"] = {
            "field": "url",
            "operator": "contains",
            "value": url_filter
        }

    try:
        resp = request("Textures.GetTextures", params)
        if resp and "result" in resp and "textures" in resp["result"]:
            return resp["result"]["textures"]
        log("Artwork", f"Textures.GetTextures unexpected response: {resp}")
        return []
    except Exception as e:
        log("Texture", f"Error getting textures: {str(e)}", xbmc.LOGERROR)
        return []


def remove_texture(texture_id: int) -> bool:
    """Remove a texture from Kodi's cache. Kodi re-caches the image when next displayed."""
    try:
        resp = request("Textures.RemoveTexture", {"textureid": texture_id})
        return resp is not None
    except Exception as e:
        log("Texture", f"Error removing texture {texture_id}: {str(e)}", xbmc.LOGERROR)
        return False


def get_all_library_artwork_urls(media_types: Optional[List[str]] = None,
                                 progress_callback: Optional[Callable] = None,
                                 include_cast: bool = False,
                                 abort_check: Optional[Callable[[], bool]] = None) -> Set[str]:
    """Return all decoded artwork URLs across `media_types`.

    `include_cast=True` walks `cast[].thumbnail` for cleanup-protection use.
    Precache callers leave it False so cast thumbs aren't proactively downloaded.
    `progress_callback(type_index, type_count, media_type, done, total)` fires per fetched page.
    Propagates `LibraryScanAborted` so callers never act on a partial scan.
    """
    if media_types is None:
        media_types = list(DEFAULT_TEXTURE_MEDIA_TYPES)

    all_urls: Set[str] = set()
    type_count = len(media_types)

    for type_index, media_type in enumerate(media_types, 1):
        want_cast = include_cast and media_type in _CAST_MEDIA_TYPES
        properties = ["art", "cast"] if want_cast else ["art"]

        def page_cb(mt: str, done: int, total: int, _idx: int = type_index) -> None:
            if progress_callback:
                progress_callback(_idx, type_count, mt, done, total)

        items = get_library_items(
            media_types=[media_type],
            properties=properties,
            decode_urls=True,
            progress_callback=page_cb,
            abort_check=abort_check,
        )

        for item in items:
            art = item.get('art', {})
            if art and isinstance(art, dict):
                for art_url in art.values():
                    if art_url:
                        all_urls.add(art_url)

            if want_cast:
                cast = item.get('cast', [])
                if cast and isinstance(cast, list):
                    for member in cast:
                        if not isinstance(member, dict):
                            continue
                        thumb = member.get('thumbnail')
                        if thumb:
                            all_urls.add(decode_image_url(thumb))

    return all_urls


def load_cached_urls_once() -> Set[str]:
    """Cache all texture URLs in memory for O(1) lookups during one operation."""
    global _cached_urls_set

    with _cache_lock:
        if _cached_urls_set is not None:
            return _cached_urls_set

    textures = get_cached_textures()
    new_set = set()

    for texture in textures:
        url = texture.get('url', '')
        if url:
            decoded = decode_image_url(url)
            new_set.add(decoded)

    with _cache_lock:
        if _cached_urls_set is None:
            _cached_urls_set = new_set
        return _cached_urls_set


def clear_cached_urls_cache() -> None:
    """Clear the in-memory cached URLs set to force reload on next operation."""
    global _cached_urls_set
    with _cache_lock:
        _cached_urls_set = None


def get_library_scan_data(media_types: Optional[List[str]] = None,
                          progress_dialog: Optional[ProgressDialog] = None,
                          include_cast: bool = False,
                          abort_check: Optional[Callable[[], bool]] = None) -> Dict[str, Any]:
    """Scan library + texture cache, return `{library_urls, cached_textures, cached_urls, stats}`.

    `include_cast=True` adds `cast[].thumbnail` URLs (cleanup protection only).
    """
    if media_types is None:
        media_types = list(DEFAULT_TEXTURE_MEDIA_TYPES)

    def progress_callback(type_index: int, type_count: int, media_type: str,
                          done: int, total: int):
        if progress_dialog:
            frac = (type_index - 1 + (done / total if total else 1)) / type_count
            progress_dialog.update(10 + int(frac * 15),
                                   f"Scanning {media_type}: {done:,} / {total:,}")

    library_urls = get_all_library_artwork_urls(
        media_types, progress_callback=progress_callback, include_cast=include_cast,
        abort_check=abort_check,
    )

    if progress_dialog:
        progress_dialog.update(25, f"Found {len(library_urls)} library URLs")
        progress_dialog.update(30, "Checking texture cache...")

    cached_textures = get_cached_textures()
    cached_urls = {t['url'] for t in cached_textures}

    log("Artwork",
        f"Library scan complete - {len(library_urls)} library URLs, "
        f"{len(cached_textures)} cached textures"
    )

    return {
        'library_urls': library_urls,
        'cached_textures': cached_textures,
        'cached_urls': cached_urls,
        'stats': {
            'total_library': len(library_urls),
            'total_cached': len(cached_textures)
        }
    }
