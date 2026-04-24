"""
identifier.py — Media identification pipeline.

Priority order:
  1. Kodi library metadata via xbmc.InfoTagVideo (best quality).
  2. Regex filename parser (scene release tags, SxxExx, year extraction).
  3. Raw filename sent as-is so the server can attempt its own lookup.

Results are cached in SQLite to avoid re-parsing on every play event.
"""

import os
import re
from typing import TYPE_CHECKING, Any

import xbmc

if TYPE_CHECKING:
    from cache import Cache


# ---------------------------------------------------------------------------
# Regex filename parser
# ---------------------------------------------------------------------------

# Common scene/release tags that appear after the real title.
_SCENE_TAGS = re.compile(
    r"\b(1080[pi]|720[pi]|4[Kk]|2160[pi]|"
    r"BluRay|BDRip|BRRip|WEB[-.]?DL|WEBRip|HDTV|DVDRip|"
    r"x264|x265|HEVC|H\.?264|H\.?265|AAC|AC3|DTS|"
    r"PROPER|REPACK|EXTENDED|THEATRICAL|DIRECTORS\.CUT)\b.*",
    re.IGNORECASE,
)
_YEAR_RE = re.compile(r"[\(\[\s]?(\d{4})[\)\]\s]?")
_EP_RE = re.compile(
    r"[Ss](\d{1,2})[Ee](\d{1,2})"  # S01E02
    r"|(\d{1,2})[xX](\d{2})"        # 1x02
)


def _clean_title(raw: str) -> str:
    """Replace dots/underscores with spaces and strip trailing junk."""
    title = raw.replace(".", " ").replace("_", " ").replace("-", " ")
    title = _SCENE_TAGS.sub("", title)
    return re.sub(r"\s+", " ", title).strip()


def _regex_guess(path: str) -> dict[str, Any]:
    """Parse title, year, and episode info from a scene-style filename."""
    name = os.path.splitext(os.path.basename(path))[0]

    ep_match = _EP_RE.search(name)
    if ep_match:
        if ep_match.group(1):  # S01E02 style
            season = int(ep_match.group(1))
            episode = int(ep_match.group(2))
        else:  # 1x02 style
            season = int(ep_match.group(3))
            episode = int(ep_match.group(4))

        raw_title = name[: ep_match.start()]
        year_m = _YEAR_RE.search(raw_title)
        year = int(year_m.group(1)) if year_m else None
        if year_m:
            raw_title = raw_title[: year_m.start()]

        return {
            "media_type": "episode",
            "title": _clean_title(raw_title),
            "year": year,
            "season": season,
            "episode": episode,
        }

    # Movie fallback.
    year_m = _YEAR_RE.search(name)
    year = int(year_m.group(1)) if year_m else None
    raw_title = name[: year_m.start()] if year_m else name

    return {
        "media_type": "movie",
        "title": _clean_title(raw_title),
        "year": year,
    }


# ---------------------------------------------------------------------------
# Anime genre detection
# ---------------------------------------------------------------------------

def is_anime(info_tag: "xbmc.InfoTagVideo") -> bool:
    """Return True if the item's genre list includes 'anime'.

    Deliberately excludes the broad 'animation' genre to avoid misclassifying
    Western cartoons and CGI films as anime.
    """
    try:
        genres = [g.lower() for g in (info_tag.getGenres() or [])]
        return "anime" in genres
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def identify(
    *,
    list_item_path: str | None = None,
    info_tag: "xbmc.InfoTagVideo | None" = None,
    cache: "Cache | None" = None,
) -> dict[str, Any]:
    """
    Return a metadata dict suitable for merging into a scrobble payload.
    Keys that may be present: media_type, title, year, imdb_id, tmdb_id,
    tvdb_id, season, episode, raw_filename.
    """

    # ------------------------------------------------------------------
    # 1. Kodi library metadata (most reliable)
    # ------------------------------------------------------------------
    if info_tag is not None:
        try:
            result = _from_info_tag(info_tag)
            if result and result.get("title"):
                xbmc.log(
                    f"[PunchPlay] Identified via Kodi library: {result.get('title')!r}",
                    xbmc.LOGDEBUG,
                )
                return result
        except Exception as exc:
            xbmc.log(f"[PunchPlay] InfoTag parse error: {exc}", xbmc.LOGDEBUG)

    # ------------------------------------------------------------------
    # 2. Filename parse (regex), with cache
    # ------------------------------------------------------------------
    if list_item_path:
        cache_key = f"path:{list_item_path}"
        if cache is not None:
            cached = cache.get_identifier(cache_key)
            if cached:
                xbmc.log(
                    f"[PunchPlay] Identifier cache hit for {os.path.basename(list_item_path)!r}",
                    xbmc.LOGDEBUG,
                )
                return cached

        guess = _regex_guess(list_item_path)

        if guess.get("title"):
            if cache is not None:
                cache.set_identifier(cache_key, guess)
            xbmc.log(
                f"[PunchPlay] Identified via filename: {guess.get('title')!r}",
                xbmc.LOGDEBUG,
            )
            return guess

    # ------------------------------------------------------------------
    # 4. Raw filename fallback
    # ------------------------------------------------------------------
    if list_item_path:
        raw_name = os.path.splitext(os.path.basename(list_item_path))[0]
        xbmc.log(
            f"[PunchPlay] Falling back to raw filename: {raw_name!r}", xbmc.LOGDEBUG
        )
        return {
            "media_type": "movie",
            "title": raw_name,
            "raw_filename": list_item_path,
        }

    return {}


def _from_info_tag(info_tag: "xbmc.InfoTagVideo") -> dict[str, Any]:
    """Extract structured metadata from a Kodi InfoTagVideo object."""
    media_type_raw = (info_tag.getMediaType() or "").lower()
    title = info_tag.getTitle() or ""
    year: int | None = info_tag.getYear() or None
    imdb: str | None = info_tag.getIMDBNumber() or None

    # Unique IDs dict (added Kodi 19+, safe on 20/21).
    unique_ids: dict[str, str] = {}
    try:
        unique_ids = info_tag.getUniqueIDs() or {}
    except Exception:
        pass

    def _int_id(key: str) -> int | None:
        val = unique_ids.get(key) or unique_ids.get(f"the{key}")
        try:
            return int(val) if val else None
        except (ValueError, TypeError):
            return None

    tmdb_id = _int_id("tmdb") or _int_id("themoviedb")
    tvdb_id = _int_id("tvdb") or _int_id("thetvdb")

    result: dict[str, Any] = {}

    if media_type_raw == "episode":
        show_title = info_tag.getTVShowTitle() or title
        season = info_tag.getSeason()
        episode = info_tag.getEpisode()
        result = {
            "media_type": "episode",
            "title": show_title,
            "year": year,
            "season": season if season > 0 else None,
            "episode": episode if episode > 0 else None,
        }
    elif media_type_raw == "movie":
        result = {
            "media_type": "movie",
            "title": title,
            "year": year,
        }
    else:
        # Unknown type — try to infer from available fields.
        season = info_tag.getSeason() if hasattr(info_tag, "getSeason") else 0
        episode = info_tag.getEpisode() if hasattr(info_tag, "getEpisode") else 0
        if season > 0 and episode > 0:
            show_title = (
                (info_tag.getTVShowTitle() if hasattr(info_tag, "getTVShowTitle") else None)
                or title
            )
            result = {
                "media_type": "episode",
                "title": show_title,
                "year": year,
                "season": season,
                "episode": episode,
            }
        elif title:
            result = {"media_type": "movie", "title": title, "year": year}

    if not result.get("title"):
        return {}

    if imdb:
        result["imdb_id"] = imdb
    if tmdb_id:
        result["tmdb_id"] = tmdb_id
    if tvdb_id:
        result["tvdb_id"] = tvdb_id

    return result
