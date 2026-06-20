"""Media identification helpers for PunchPlay."""

from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING, Any

import xbmc

if TYPE_CHECKING:
    from api import APIClient
    from cache import Cache


_YEAR_RE = re.compile(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)")
_SXXEXX_RE = re.compile(
    r"(?i)\bS(?P<season>\d{1,2})E(?P<episode>\d{1,3})(?:[- ]?E?(?P<episode_end>\d{2,3}))?\b"
)
_ONE_X_RE = re.compile(
    r"(?i)\b(?P<season>\d{1,2})x(?P<episode>\d{1,3})(?:x(?P<episode_end>\d{2,3}))?\b"
)
_EPISODE_WORD_RE = re.compile(r"(?i)\bEpisode\s*(?P<episode>\d{1,4})\b")
_LEADING_NUMBER_RE = re.compile(r"^(?P<episode>\d{1,4})(?:\s*[-.]\s*(?P<episode_title>.+))?$")
_TITLE_NUMBER_RE = re.compile(
    r"^(?P<title>.+?)\s*-\s*(?P<episode>\d{1,4})(?:\s*-\s*(?P<episode_title>.+))?$"
)
_SEASON_FOLDER_RE = re.compile(r"(?i)^(?:season\s*|s)(?P<season>\d{1,2})$")
_LEADING_GROUP_RE = re.compile(r"^(?:\[[^\]]+\]\s*)+")
_TRAILING_CHECKSUM_RE = re.compile(r"\[[A-Fa-f0-9]{6,12}\]")
_BRACKET_TOKEN_RE = re.compile(r"\[[^\]]+\]|\([^\)]+\)")
_ABSOLUTE_EP_RE = re.compile(
    r"^(?P<title>.+?)\s*[- ]\s*(?P<episode>\d{1,4})(?:\s*[- ]\s*(?P<episode_title>.+))?$",
    re.IGNORECASE,
)
_ANIME_GROUP_RE = re.compile(r"^\[[^\]]+\]")

_TECH_TOKEN_RE = re.compile(
    r"(?i)\b("
    r"480p|720p|1080p|2160p|4k|"
    r"bluray|bdrip|brrip|web[- ]?dl|webrip|hdtv|dvdrip|remux|"
    r"x264|x265|h\.?264|h\.?265|hevc|avc|"
    r"aac|ac3|dts|ddp(?:\d\.\d)?|atmos|flac|"
    r"hdr|hdr10|dv|dolby[ .-]?vision|"
    r"proper|repack|extended|theatrical|remastered|"
    r"dual[ .-]?audio|multi(?:sub|subs)?|subs?|subbed|dubbed|eng|jpn"
    r")\b"
)


def _normalise_separators(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace(".", " ").replace("_", " ")).strip()


def _clean_title(raw: str) -> str:
    text = _normalise_separators(raw)
    text = _LEADING_GROUP_RE.sub("", text)
    text = _TRAILING_CHECKSUM_RE.sub("", text)

    def _strip_brackets(match: re.Match[str]) -> str:
        token = match.group(0).strip("[]() ").strip()
        if _looks_like_year(token):
            return " {0} ".format(token)
        if _is_probable_title_token(token):
            return " {0} ".format(token)
        return " "

    text = _BRACKET_TOKEN_RE.sub(_strip_brackets, text)
    text = _TECH_TOKEN_RE.sub(" ", text)
    text = re.sub(r"\b(?:v\d+|sample)\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+-\s+$", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" -._")


def _looks_like_year(token: str) -> bool:
    if not token.isdigit() or len(token) != 4:
        return False
    year = int(token)
    return 1900 <= year <= 2035


def _is_probable_title_token(token: str) -> bool:
    lowered = token.lower()
    if not lowered:
        return False
    if _TECH_TOKEN_RE.search(lowered):
        return False
    if re.fullmatch(r"[A-Fa-f0-9]{6,12}", token):
        return False
    if re.fullmatch(r"\d{3,4}p", lowered):
        return False
    return True


def _extract_year(text: str) -> int | None:
    match = _YEAR_RE.search(text)
    if not match:
        return None
    year = int(match.group(1))
    if 1900 <= year <= 2035:
        return year
    return None


def _trim_before_year(text: str, year: int) -> str:
    prefix = text[: text.find(str(year))]
    return prefix.rstrip(" ([{-_.")


def _path_parts(path: str) -> list[str]:
    parts = [part for part in re.split(r"[\\/]+", path or "") if part]
    return parts


def _season_from_parts(parts: list[str]) -> int | None:
    for part in reversed(parts):
        match = _SEASON_FOLDER_RE.match(part.strip())
        if match:
            return int(match.group("season"))
    return None


def _show_title_from_parts(parts: list[str]) -> str | None:
    if not parts:
        return None
    for index, part in enumerate(parts):
        if part.lower() == "anime" and index + 1 < len(parts):
            return _clean_title(parts[index + 1])
    for index, part in enumerate(parts):
        if _SEASON_FOLDER_RE.match(part.strip()) and index > 0:
            return _clean_title(parts[index - 1])
    if len(parts) >= 2:
        return _clean_title(parts[-2])
    return None


def _movie_folder_guess(parts: list[str]) -> tuple[str | None, int | None]:
    for part in reversed(parts):
        cleaned = _clean_title(part)
        year = _extract_year(part)
        if cleaned and year:
            title = _clean_title(_trim_before_year(part, year))
            if title:
                return title, year
    return None, None


def _extract_episode_title(text: str) -> str | None:
    cleaned = _clean_title(text)
    if not cleaned:
        return None
    if re.fullmatch(r"\d{1,4}", cleaned):
        return None
    return cleaned


def _build_episode_result(
    *,
    title: str,
    season: int | None,
    episode: int | None,
    episode_end: int | None = None,
    episode_title: str | None = None,
    year: int | None = None,
    absolute_episode: int | None = None,
    anime: bool = False,
    parser_confidence: float,
    parser_source: str,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "media_type": "episode",
        "title": title,
        "year": year,
        "season": season,
        "episode": episode,
        "parser_confidence": parser_confidence,
        "parser_source": parser_source,
    }
    if episode_end is not None and episode is not None and episode_end > episode:
        result["episode_end"] = episode_end
        result["multi_episode"] = True
    if episode_title:
        result["episode_title"] = episode_title
    if absolute_episode is not None:
        result["absolute_episode"] = absolute_episode
    if anime:
        result["anime"] = True
    return result


def _build_movie_result(
    title: str,
    *,
    year: int | None,
    parser_confidence: float,
    parser_source: str,
) -> dict[str, Any]:
    return {
        "media_type": "movie",
        "title": title,
        "year": year,
        "parser_confidence": parser_confidence,
        "parser_source": parser_source,
    }


def _choose_title(prefix: str, folder_title: str | None) -> str:
    candidate = _clean_title(prefix)
    if candidate:
        return candidate
    return folder_title or ""


def _anime_signals_from_path(path: str) -> bool:
    lowered = path.lower()
    return "/anime/" in lowered or "\\anime\\" in lowered or lowered.startswith("anime/")


def _absolute_episode_allowed(
    anime_preference: str,
    *,
    anime_signals: bool,
    has_season_episode: bool,
) -> bool:
    preference = (anime_preference or "auto").lower()
    if preference == "season_episode":
        return False
    if preference == "absolute":
        return True
    return anime_signals and not has_season_episode


def _parse_episode_from_filename(
    raw_name: str,
    parts: list[str],
    *,
    anime_preference: str,
) -> dict[str, Any] | None:
    season_from_folder = _season_from_parts(parts[:-1])
    folder_title = _show_title_from_parts(parts[:-1])
    normalised = _normalise_separators(raw_name)
    joined_path = "/".join(parts)

    for pattern, source in (
        (_SXXEXX_RE, "filename_sxxexx"),
        (_ONE_X_RE, "filename_1x"),
    ):
        match = pattern.search(raw_name)
        if not match:
            continue
        season = int(match.group("season"))
        episode = int(match.group("episode"))
        episode_end_raw = match.groupdict().get("episode_end")
        episode_end = int(episode_end_raw) if episode_end_raw else None
        title = _choose_title(raw_name[: match.start()], folder_title)
        if not title:
            return None
        episode_title = _extract_episode_title(raw_name[match.end() :])
        return _build_episode_result(
            title=title,
            season=season,
            episode=episode,
            episode_end=episode_end,
            episode_title=episode_title,
            anime=_anime_signals_from_path(joined_path),
            parser_confidence=0.97 if source == "filename_sxxexx" else 0.95,
            parser_source=source,
        )

    if season_from_folder is not None:
        match = _LEADING_NUMBER_RE.match(normalised)
        if match and folder_title:
            episode = int(match.group("episode"))
            return _build_episode_result(
                title=folder_title,
                season=season_from_folder,
                episode=episode,
                episode_title=_extract_episode_title(match.group("episode_title") or ""),
                parser_confidence=0.82,
                parser_source="season_folder_numeric",
            )
        titled_match = _TITLE_NUMBER_RE.match(normalised)
        if titled_match and folder_title:
            episode = int(titled_match.group("episode"))
            return _build_episode_result(
                title=folder_title,
                season=season_from_folder,
                episode=episode,
                episode_title=_extract_episode_title(titled_match.group("episode_title") or ""),
                parser_confidence=0.84,
                parser_source="season_folder_titled_numeric",
            )

    word_match = _EPISODE_WORD_RE.search(normalised)
    if word_match:
        title = _choose_title(normalised[: word_match.start()], folder_title)
        if title:
            episode = int(word_match.group("episode"))
            return _build_episode_result(
                title=title,
                season=season_from_folder,
                episode=episode,
                episode_title=_extract_episode_title(normalised[word_match.end() :]),
                anime=_anime_signals_from_path(joined_path),
                parser_confidence=0.79 if season_from_folder is not None else 0.72,
                parser_source="episode_word",
            )

    anime_signals = _anime_signals_from_path(joined_path) or bool(_ANIME_GROUP_RE.match(raw_name))
    if _absolute_episode_allowed(
        anime_preference,
        anime_signals=anime_signals,
        has_season_episode=False,
    ):
        stripped = _clean_title(raw_name)
        absolute_match = _ABSOLUTE_EP_RE.match(stripped)
        if absolute_match:
            title = _clean_title(absolute_match.group("title"))
            if title:
                absolute_episode = int(absolute_match.group("episode"))
                return _build_episode_result(
                    title=title,
                    season=season_from_folder if anime_preference == "season_episode" else None,
                    episode=None,
                    absolute_episode=absolute_episode,
                    episode_title=_extract_episode_title(
                        absolute_match.group("episode_title") or ""
                    ),
                    anime=True,
                    parser_confidence=0.84 if anime_signals else 0.76,
                    parser_source="anime_absolute_filename",
                )
    return None


def _parse_movie_from_path(raw_name: str, parts: list[str]) -> dict[str, Any]:
    folder_title, folder_year = _movie_folder_guess(parts[:-1])
    filename_year = _extract_year(raw_name)
    title_source = raw_name
    year = filename_year

    if filename_year is not None:
        title_source = _trim_before_year(raw_name, filename_year)
    elif folder_title:
        title_source = folder_title
        year = folder_year

    title = _clean_title(title_source)
    if not title and folder_title:
        title = folder_title

    if year is not None and not title:
        title = _clean_title(raw_name.replace(str(year), " "))

    confidence = 0.9 if year is not None and title else 0.7 if title else 0.3
    source = "movie_title_year" if year is not None else "movie_title_only"
    return _build_movie_result(
        title=title or _clean_title(raw_name),
        year=year,
        parser_confidence=confidence,
        parser_source=source,
    )


def _regex_guess(path: str, anime_preference: str = "auto") -> dict[str, Any]:
    raw_name = os.path.splitext(os.path.basename(path))[0]
    parts = _path_parts(path)

    episode_result = _parse_episode_from_filename(
        raw_name,
        parts,
        anime_preference=anime_preference,
    )
    if episode_result:
        return episode_result

    return _parse_movie_from_path(raw_name, parts)


def is_anime(
    info_tag: "xbmc.InfoTagVideo | None" = None,
    *,
    path: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> bool:
    """Return True when the item is likely anime without treating animation as anime."""
    if metadata and metadata.get("anime"):
        return True
    if path and _anime_signals_from_path(path):
        return True
    if info_tag is not None:
        try:
            genres = [g.lower() for g in (info_tag.getGenres() or [])]
            return "anime" in genres
        except Exception:
            return False
    return False


def _has_reliable_ids(metadata: dict[str, Any]) -> bool:
    return any(metadata.get(key) for key in ("tmdb_id", "tvdb_id", "imdb_id", "punchplay_id"))


def _merge_missing_fields(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overlay.items():
        if value is None:
            continue
        if key not in merged or merged.get(key) in ("", None):
            merged[key] = value
    return merged


def _from_info_tag(info_tag: "xbmc.InfoTagVideo") -> dict[str, Any]:
    media_type_raw = (info_tag.getMediaType() or "").lower()
    title = info_tag.getTitle() or ""
    year: int | None = info_tag.getYear() or None
    imdb: str | None = info_tag.getIMDBNumber() or None

    unique_ids: dict[str, str] = {}
    try:
        unique_ids = info_tag.getUniqueIDs() or {}
    except Exception:
        pass

    def _int_id(key: str) -> int | None:
        val = unique_ids.get(key) or unique_ids.get("the{0}".format(key))
        try:
            return int(val) if val else None
        except (ValueError, TypeError):
            return None

    tmdb_id = _int_id("tmdb") or _int_id("moviedb")
    tvdb_id = _int_id("tvdb")

    result: dict[str, Any] = {
        "parser_source": "kodi_info_tag",
        "parser_confidence": 0.99,
    }

    if media_type_raw == "episode":
        show_title = info_tag.getTVShowTitle() or title
        season = info_tag.getSeason()
        episode = info_tag.getEpisode()
        result.update(
            {
                "media_type": "episode",
                "title": show_title,
                "year": year,
                "season": season if season > 0 else None,
                "episode": episode if episode > 0 else None,
                "episode_title": title or None,
            }
        )
    elif media_type_raw == "movie":
        result.update(
            {
                "media_type": "movie",
                "title": title,
                "year": year,
            }
        )
    else:
        season = info_tag.getSeason() if hasattr(info_tag, "getSeason") else 0
        episode = info_tag.getEpisode() if hasattr(info_tag, "getEpisode") else 0
        if season > 0 and episode > 0:
            show_title = (
                (info_tag.getTVShowTitle() if hasattr(info_tag, "getTVShowTitle") else None)
                or title
            )
            result.update(
                {
                    "media_type": "episode",
                    "title": show_title,
                    "year": year,
                    "season": season,
                    "episode": episode,
                    "episode_title": title or None,
                }
            )
        elif title:
            result.update({"media_type": "movie", "title": title, "year": year})

    if not result.get("title"):
        return {}

    if imdb:
        result["imdb_id"] = imdb
    if tmdb_id:
        result["tmdb_id"] = tmdb_id
    if tvdb_id:
        result["tvdb_id"] = tvdb_id

    return result


def identify(
    *,
    list_item_path: str | None = None,
    info_tag: "xbmc.InfoTagVideo | None" = None,
    cache: "Cache | None" = None,
    api_client: "APIClient | None" = None,
    duration_seconds: int | None = None,
    anime_preference: str = "auto",
) -> dict[str, Any]:
    """
    Return metadata suitable for merging into a scrobble payload.
    """
    metadata: dict[str, Any] = {}

    if info_tag is not None:
        try:
            metadata = _from_info_tag(info_tag)
            if metadata.get("title"):
                xbmc.log(
                    "[PunchPlay] Identified via Kodi library: {0!r}".format(
                        metadata.get("title")
                    ),
                    xbmc.LOGDEBUG,
                )
        except Exception as exc:
            xbmc.log("[PunchPlay] InfoTag parse error: {0}".format(exc), xbmc.LOGDEBUG)
            metadata = {}

    local_guess: dict[str, Any] = {}
    if list_item_path:
        cache_key = "path:{0}:{1}".format(list_item_path, anime_preference)
        if cache is not None:
            cached = cache.get_identifier(cache_key)
            if cached:
                xbmc.log(
                    "[PunchPlay] Identifier cache hit for {0!r}".format(
                        os.path.basename(list_item_path)
                    ),
                    xbmc.LOGDEBUG,
                )
                local_guess = cached
            else:
                local_guess = _regex_guess(list_item_path, anime_preference=anime_preference)
                cache.set_identifier(cache_key, local_guess)
        else:
            local_guess = _regex_guess(list_item_path, anime_preference=anime_preference)

        if local_guess.get("title"):
            xbmc.log(
                "[PunchPlay] Identified via filename: {0!r}".format(local_guess.get("title")),
                xbmc.LOGDEBUG,
            )

    metadata = _merge_missing_fields(metadata, local_guess)

    if list_item_path:
        metadata["raw_filename"] = list_item_path
    if is_anime(info_tag, path=list_item_path, metadata=metadata):
        metadata["anime"] = True

    if (
        metadata.get("title")
        and not _has_reliable_ids(metadata)
        and api_client is not None
    ):
        canonical = api_client.identify_media(
            metadata,
            raw_filename=list_item_path,
            duration_seconds=duration_seconds,
        )
        if canonical:
            metadata = _merge_missing_fields(metadata, canonical)
            for key in (
                "media_type",
                "title",
                "year",
                "season",
                "episode",
                "episode_end",
                "absolute_episode",
                "episode_title",
                "tmdb_id",
                "tvdb_id",
                "imdb_id",
                "punchplay_id",
            ):
                if canonical.get(key) is not None:
                    metadata[key] = canonical[key]

    if metadata.get("title"):
        return metadata

    if list_item_path:
        raw_name = os.path.splitext(os.path.basename(list_item_path))[0]
        xbmc.log(
            "[PunchPlay] Falling back to raw filename: {0!r}".format(raw_name),
            xbmc.LOGDEBUG,
        )
        return {
            "media_type": "movie",
            "title": _clean_title(raw_name) or raw_name,
            "raw_filename": list_item_path,
            "parser_source": "raw_filename_fallback",
            "parser_confidence": 0.2,
        }

    return {}
