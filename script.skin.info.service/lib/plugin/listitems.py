"""Build dictionaries for ListItem properties from Kodi library data."""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from lib.kodi.properties import (
    build_movie_data as _build_movie_base,
    build_movieset_data as _build_movieset_base,
    build_tvshow_data as _build_tvshow_base,
    build_season_data as _build_season_base,
    build_episode_data as _build_episode_base,
    build_musicvideo_data as _build_musicvideo_base,
    build_artist_data as _build_artist_base,
    build_album_data as _build_album_base,
    VIDEO_ART_KEYS,
    MOVIE_ART_KEYS,
    SET_ART_KEYS,
    AUDIO_ART_KEYS,
)


def _build_art_dict(art: Optional[dict], keys: Tuple[str, ...],
                    fallbacks: Optional[dict] = None) -> Dict[str, str]:
    """Build `Art.<type>` entries for the given art types, each with its own fallback."""
    art = art or {}
    fallbacks = fallbacks or {}

    art_dict = {}
    for key in keys:
        val = art.get(key) or fallbacks.get(key) or ""
        if val:
            art_dict[f"Art.{key}"] = val

    return art_dict


def _flatten_items_art(data: dict, items: List[dict], prefix: str,
                       keys: Tuple[str, ...], thumb_fallback: bool = True) -> None:
    """Flatten each item's art into `{prefix}.{n}.Art.*` entries, thumb falling back optionally."""
    for idx, item in enumerate(items, 1):
        fallbacks = {"thumb": item.get("thumbnail") or ""} if thumb_fallback else None
        item_art = _build_art_dict(item.get("art"), keys, fallbacks=fallbacks)
        for art_key, art_val in item_art.items():
            data[f"{prefix}.{idx}.{art_key}"] = art_val


def build_movie_data(details: dict) -> dict:
    """Build movie data for a ListItem: the service's properties plus `Art.*` keys."""
    data = _build_movie_base(details)
    data.update(_build_art_dict(details.get("art"), MOVIE_ART_KEYS))
    return data


def build_movieset_data(set_details: dict, movies: List[dict]) -> dict:
    """Build movie set data for a ListItem: the service's properties plus set and movie art."""
    data = _build_movieset_base(set_details, movies)
    data.pop("_metadata", None)

    data.update(_build_art_dict(set_details.get("art"), SET_ART_KEYS))
    _flatten_items_art(data, movies, "Movie", MOVIE_ART_KEYS)

    return data


def build_tvshow_data(details: dict) -> dict:
    """Build TV show data for a ListItem: the service's properties plus `Art.*` keys."""
    data = _build_tvshow_base(details)
    data.update(_build_art_dict(details.get("art"), VIDEO_ART_KEYS))
    return data


def build_season_data(details: dict) -> dict:
    """Build season data for a ListItem: the service's properties plus `Art.*` keys."""
    data = _build_season_base(details)
    data.update(_build_art_dict(details.get("art"), VIDEO_ART_KEYS))
    return data


def build_episode_data(details: dict) -> dict:
    """Build episode data for a ListItem: the service's properties plus `Art.*` keys."""
    data = _build_episode_base(details)
    data.update(_build_art_dict(details.get("art"), VIDEO_ART_KEYS))
    return data


def build_musicvideo_data(details: dict) -> dict:
    """Build music video data for a ListItem: the service's properties plus `Art.*` keys."""
    data = _build_musicvideo_base(details)
    data.update(_build_art_dict(details.get("art"), VIDEO_ART_KEYS))
    return data


def build_artist_data(artist: dict, albums: List[dict]) -> dict:
    """Build artist data for a ListItem: the service's properties plus artist and album art."""
    data = _build_artist_base(artist, albums)
    data.pop("_metadata", None)

    data.update(_build_art_dict(
        artist.get("art"),
        ("thumb", "fanart"),
        fallbacks={
            "thumb": artist.get("thumbnail") or "",
            "fanart": artist.get("fanart") or "",
        }
    ))
    _flatten_items_art(data, albums, "Album", ("thumb", "discart"))

    return data


def build_album_data(album: dict, songs: List[dict]) -> dict:
    """Build album data for a ListItem: the service's properties plus `Art.*` keys."""
    data = _build_album_base(album, songs)
    data.pop("_metadata", None)

    data.update(_build_art_dict(
        album.get("art"),
        AUDIO_ART_KEYS,
        fallbacks={
            "thumb": album.get("thumbnail") or "",
            "fanart": album.get("fanart") or "",
        }
    ))

    return data
