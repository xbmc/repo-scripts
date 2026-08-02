"""Window property setters for movies, sets, artists, albums, and ratings.

Optimized batch property operations for high-performance UI updates.
"""
from __future__ import annotations

from typing import Any, Optional, List, Tuple, Dict, Set
import os
import urllib.request
import xbmc

from lib.kodi.utilities import (
    clear_prop, clear_group, batch_set_props, format_date, extract_cast_names, MULTI_VALUE_SEP
)
from lib.kodi.formatters import format_number, RATING_SOURCE_NORMALIZE


def _scale_rating(val: Any, max_val: Any) -> Optional[Tuple[float, int]]:
    """Scale a raw rating to 0-10 and compute percentage. Returns (scaled, pct) or None."""
    try:
        scaled = round(float(val) / (float(max_val) / 10.0), 1)
        pct = max(0, min(100, int(round(scaled * 10))))
        return scaled, pct
    except (TypeError, ValueError, ZeroDivisionError):
        return None


_RESOLUTION_TABLE = [
    (720, 480, "480"),
    (768, 576, "576"),
    (960, 544, "540"),
    (1280, 720, "720"),
    (1920, 1080, "1080"),
    (3840, 2160, "4k"),
    (7680, 4320, "8k"),
]

_ASPECT_TABLE = [
    (1.4859, "1.33"),
    (1.7190, "1.66"),
    (1.8147, "1.78"),
    (2.0174, "1.85"),
    (2.2738, "2.20"),
    (float('inf'), "2.35"),
]


def media_streamdetails(filename: str, streamdetails: dict) -> Dict[str, str]:
    info: Dict[str, str] = {}
    video = streamdetails.get("video") or []
    audio = streamdetails.get("audio") or []
    name = (filename or "").lower()

    v0 = video[0] if video else None

    if xbmc.getCondVisibility("ListItem.IsStereoscopic"):
        info["videoresolution"] = "3d"
    elif v0:
        w = int(v0.get("width", 0) or 0)
        h = int(v0.get("height", 0) or 0)
        for max_w, max_h, label in _RESOLUTION_TABLE:
            if w <= max_w and h <= max_h:
                info["videoresolution"] = label
                break
        else:
            info["videoresolution"] = ""
    elif (
        ("dvd" in name and not any(x in name for x in ("hddvd", "hd-dvd")))
        or name.endswith((".vob", ".ifo"))
    ):
        info["videoresolution"] = "576"
    elif any(x in name for x in ("bluray", "blu-ray", "brrip", "bdrip", "hddvd", "hd-dvd")):
        info["videoresolution"] = "1080"
    elif "4k" in name:
        info["videoresolution"] = "4k"
    else:
        info["videoresolution"] = "1080"

    if v0:
        aspect = float(v0.get("aspect", 0) or 0)
        info["videocodec"] = v0.get("codec", "") or ""
        for max_aspect, label in _ASPECT_TABLE:
            if aspect < max_aspect:
                info["videoaspect"] = label
                break
    else:
        info["videocodec"] = ""
        info["videoaspect"] = ""

    if audio:
        a0 = audio[0]
        info["audiocodec"] = a0.get("codec", "") or ""
        ch = a0.get("channels", "")
        info["audiochannels"] = "" if ch is None else str(ch)
    else:
        info["audiocodec"] = ""
        info["audiochannels"] = ""

    return info


def media_path(path: Optional[str]) -> str:
    """Normalize a file path and resolve rar:// or multipath:// prefixes."""
    path = str(path or "")
    try:
        base = os.path.split(path)[0].rsplit(" , ", 1)[1].replace(",,", ",")
    except Exception:
        base = os.path.split(path)[0]

    if base.startswith("rar://"):
        base = urllib.request.url2pathname(base[6:])
    elif base.startswith("multipath://"):
        parts = base[13:].split("%2f/")
        base = urllib.request.url2pathname(parts[0])
    return base

_STATE = {
    "set_movies": 0,
    "artist_albums": 0,
    "album_songs": 0,
    "set_studios": 0,
    "set_writers": 0,
    "set_directors": 0,
    "set_genres": 0,
    "set_countries": 0,
}

VIDEO_ART_KEYS = (
    "poster", "fanart", "clearlogo", "keyart", "landscape",
    "banner", "clearart", "thumb",
)

MOVIE_ART_KEYS = (
    "poster", "fanart", "clearlogo", "keyart", "landscape",
    "banner", "clearart", "discart",
)

SET_ART_KEYS = (
    "poster", "fanart", "clearlogo", "keyart", "landscape",
    "banner", "clearart", "discart",
)

AUDIO_ART_KEYS = ("thumb", "fanart", "discart")

_CR = "[CR]"
_BOLD_OPEN = "[B]"
_BOLD_CLOSE = "[/B]"


def _ordered_unique_push(seen: set, acc: list, items) -> None:
    """Add items to list in order, de-duplicating based on seen set."""
    if not items:
        return
    for x in (items if isinstance(items, list) else [items]):
        if x and x not in seen:
            seen.add(x)
            acc.append(x)


def join_multi(items: Optional[List[Any]], separator: str = MULTI_VALUE_SEP) -> str:
    """Join a list into a Kodi-style multi-value string, dropping falsy entries."""
    if not items:
        return ""
    return separator.join(str(i) for i in items if i)


def _first_or_empty(value) -> str:
    if isinstance(value, list):
        return value[0] if value else ""
    return value or ""


def _extract_artist_names(items, key=None):
    """Extract names from artist/album metadata objects."""
    if not isinstance(items, list):
        return []
    names = []
    for item in items:
        if isinstance(item, dict) and key:
            val = item.get(key)
            if val:
                names.append(val)
        elif isinstance(item, str):
            names.append(item)
    return names


def _calculate_percent_played(details: dict) -> str:
    """Calculate percent played from resume data using Kodi's exact formula."""
    resume = details.get("resume") or {}
    resume_position = resume.get("position", 0)
    resume_total = resume.get("total", 0)
    if resume_position > 0 and resume_total > 0:
        percent_played = round((resume_position / resume_total) * 100)
        return str(percent_played)
    return ""


def _seconds_to_minutes(seconds: int) -> int:
    """Round seconds to whole minutes, matching Kodi's Duration(mins)."""
    return round(seconds / 60)


def _runtime_props(minutes: int, playcount: int = 0) -> Dict[str, str]:
    """Runtime and WatchTime keys, shared by the unified block and the per-type builders."""
    watched = minutes * playcount if minutes > 0 and playcount > 0 else 0
    props: Dict[str, str] = {}
    for key, total in (("Runtime", minutes), ("WatchTime", watched)):
        hrs, mins = divmod(total, 60)
        props[key] = str(total) if total > 0 else ""
        props[f"{key}.Hours"] = str(hrs) if hrs else ""
        props[f"{key}.Minutes"] = str(mins) if mins >= 1 else ""
    return props


def _rt_status_props(ratings_dict: Optional[dict]) -> Dict[str, str]:
    """Rotten Tomatoes Fresh/Rotten/Spilled labels, shared by the unified block and per-type."""
    props = {"Tomatometer": "", "Popcornmeter": ""}
    if not ratings_dict:
        return props
    for key, sources, low in (("Tomatometer", ("tomatoes", "tomatometerallcritics"), "Rotten"),
                              ("Popcornmeter", ("popcorn", "tomatometerallaudience"), "Spilled")):
        info = next((ratings_dict[s] for s in sources if ratings_dict.get(s)), None)
        if not info or info.get("rating") is None:
            continue
        result = _scale_rating(info["rating"], info.get("max") or 10)
        if result:
            props[key] = "Fresh" if result[1] >= 60 else low
    return props


def _duration_props(seconds: int) -> Dict[str, str]:
    """Duration clock string plus raw seconds; rolls into hours past the 60 minute mark."""
    if seconds <= 0:
        return {"Duration": "", "Duration.Seconds": ""}
    hrs, remainder = divmod(seconds, 3600)
    mins, secs = divmod(remainder, 60)
    clock = f"{hrs}:{mins:02d}:{secs:02d}" if hrs else f"{mins}:{secs:02d}"
    return {"Duration": clock, "Duration.Seconds": str(seconds)}


def _build_listitem_unified_data(
    title: str = "",
    plot: str = "",
    year: str = "",
    genre: str = "",
    runtime_minutes: int = 0,
    playcount: int = 0,
    duration_seconds: int = 0,
    rating: Optional[float] = None,
    votes: Optional[int] = None,
    userrating: Optional[int] = None,
    ratings_dict: Optional[dict] = None,
) -> dict:
    """Build `ListItem.*` property dict shared across media types.

    Video types pass `runtime_minutes`; music/musicvideo pass `duration_seconds`.
    Artist uses `title` for the artist name.
    """
    data: Dict[str, str] = {}

    data["ListItem.Title"] = title
    data["ListItem.Plot"] = plot
    data["ListItem.Year"] = year
    data["ListItem.Genre"] = genre

    for key, val in _runtime_props(runtime_minutes, playcount).items():
        data[f"ListItem.{key}"] = val

    for key, val in _duration_props(duration_seconds).items():
        data[f"ListItem.{key}"] = val

    if rating is not None and rating > 0:
        data["ListItem.Rating"] = f"{rating:.1f}"
        pct = max(0, min(100, int(round(rating * 10))))
        data["ListItem.Rating.Percent"] = str(pct)
    else:
        data["ListItem.Rating"] = ""
        data["ListItem.Rating.Percent"] = ""

    data["ListItem.Rating.Votes"] = format_number(votes) if votes else ""
    data["ListItem.UserRating"] = str(userrating) if userrating else ""

    for key, val in _rt_status_props(ratings_dict).items():
        data[f"ListItem.{key}"] = val

    if ratings_dict:
        for src, info in ratings_dict.items():
            if info.get("rating") is None:
                continue
            result = _scale_rating(info.get("rating"), info.get("max") or 10)
            if not result:
                continue
            scaled, pct = result
            output_src = RATING_SOURCE_NORMALIZE.get(src, src)
            data[f"ListItem.Rating.{output_src}"] = str(scaled)
            data[f"ListItem.Rating.{output_src}.Votes"] = format_number(info.get("votes"))
            data[f"ListItem.Rating.{output_src}.Percent"] = str(pct)

    return data


def set_listitem_unified_properties(data: dict) -> None:
    """Set unified ListItem window properties with SkinInfo prefix."""
    global _LISTITEM_RATING_STATE

    current_sources: Set[str] = set()
    for key in data:
        if key.startswith("ListItem.Rating.") and not key.endswith((".Votes", ".Percent")):
            parts = key.split(".")
            if len(parts) >= 3:
                src = parts[2]
                if src not in ("Votes", "Percent"):
                    current_sources.add(src)

    props = {f"SkinInfo.{k}": v for k, v in data.items()}

    removed_sources = _LISTITEM_RATING_STATE - current_sources
    for src in removed_sources:
        props[f"SkinInfo.ListItem.Rating.{src}"] = ""
        props[f"SkinInfo.ListItem.Rating.{src}.Votes"] = ""
        props[f"SkinInfo.ListItem.Rating.{src}.Percent"] = ""

    batch_set_props(props)
    _LISTITEM_RATING_STATE = current_sources


def clear_listitem_unified_properties() -> None:
    """Clear the shared `SkinInfo.ListItem.*` block; no library item owns it anymore."""
    global _LISTITEM_RATING_STATE
    clear_group("SkinInfo.ListItem.")
    _LISTITEM_RATING_STATE = set()


def _extract_filename(file_path: Optional[str]) -> str:
    """Extract filename from path using Kodi's URIUtils::GetFileName logic."""
    if not file_path:
        return ""

    i = len(file_path) - 1
    while i >= 0:
        ch = file_path[i]
        if ch in ('/', '\\') or (ch == ':' and i == 1):
            break
        i -= 1

    return file_path[i + 1:]


def _extract_file_extension(file_path: Optional[str]) -> str:
    """Extract file extension from path using Kodi's URIUtils::GetExtension logic."""
    if not file_path:
        return ""

    filename = _extract_filename(file_path)

    period_pos = filename.rfind('.')
    if period_pos == -1:
        return ""

    return filename[period_pos:]


def _set_art_props(prefix: str, art: Optional[Dict[str, Any]], keys: Tuple[str, ...],
                   fallbacks: Optional[Dict[str, Any]] = None) -> None:
    art = art or {}
    fallbacks = fallbacks or {}

    art_props = {}
    for key in keys:
        val = art.get(key) or fallbacks.get(key) or ""
        art_props[f"{prefix}.Art({key})"] = val

    batch_set_props(art_props)


def _trim_indexed(prefix: str, prev: int, now: int) -> None:
    if now >= prev:
        return
    suffixes = (
        "DBID",
        "Title",
        "Year",
        "Duration",
        "Runtime",
        "TrackNumber",
        "FileExtension",
        "Genre",
        "Studio",
        "StudioPrimary",
        "Country",
        "Director",
        "Writer",
        "Plot",
        "PlotOutline",
        "Path",
        "VideoResolution",
        "MPAA",
        "Label",
        "Playcount",
        "Rating",
        "Artist",
        "Art(poster)",
        "Art(fanart)",
        "Art(clearlogo)",
        "Art(keyart)",
        "Art(landscape)",
        "Art(banner)",
        "Art(clearart)",
        "Art(thumb)",
        "Art(discart)",
    )
    for i in range(now + 1, prev + 1):
        for sfx in suffixes:
            clear_prop(f"{prefix}.{i}.{sfx}")


def _trim_simple_index(prefix: str, prev: int, now: int) -> None:
    if now >= prev:
        return
    for i in range(now + 1, prev + 1):
        clear_prop(f"{prefix}.{i}")


def build_movie_data(details: dict) -> dict:
    """Build the property dict for a movie ListItem from a JSON-RPC movie details payload."""
    data = {}

    path = media_path(details.get("file"))
    info = media_streamdetails(path, details.get("streamdetails", {}))

    runtime_seconds = int(details.get("runtime") or 0)
    runtime_minutes = _seconds_to_minutes(runtime_seconds)

    year = details.get("year")
    rating = details.get("rating")
    setid = details.get("setid")
    playcount = details.get("playcount")
    top250 = details.get("top250")
    userrating = details.get("userrating")

    data["Path"] = path or ""
    data["Title"] = details.get("title") or ""
    data["Year"] = str(year) if year else ""
    data["Rating"] = f"{rating:.1f}" if rating else ""
    data["Votes"] = format_number(details.get("votes"))
    data["Genre"] = join_multi(details.get("genre"))
    data["Director"] = join_multi(details.get("director"))
    data["Studio"] = join_multi(details.get("studio"))
    data["Country"] = join_multi(details.get("country"))
    data["Tagline"] = details.get("tagline") or ""
    data["Plot"] = details.get("plot") or ""
    data["MPAA"] = details.get("mpaa") or ""
    data.update(_runtime_props(runtime_minutes, int(details.get("playcount") or 0)))
    data["Codec"] = info.get("videocodec") or ""
    data["Resolution"] = info.get("videoresolution") or ""
    data["Aspect"] = info.get("videoaspect") or ""
    data["AudioCodec"] = info.get("audiocodec") or ""
    data["AudioChannels"] = info.get("audiochannels") or ""

    _studios = details.get("studio")
    primary_studio = _first_or_empty(_studios)
    data["StudioPrimary"] = primary_studio or ""

    data["OriginalTitle"] = details.get("originaltitle") or ""
    data["Premiered"] = details.get("premiered") or ""
    data["Trailer"] = details.get("trailer") or ""
    data["Set"] = details.get("set") or ""
    data["SetID"] = str(setid) if setid else ""
    data["Writer"] = join_multi(details.get("writer"))
    data["PlotOutline"] = details.get("plotoutline") or ""
    data["LastPlayed"] = format_date(details.get("lastplayed") or "", include_time=False)
    data["Playcount"] = str(playcount) if playcount else ""
    data["IMDBNumber"] = details.get("imdbnumber") or ""
    data["Top250"] = str(top250) if top250 else ""
    data["DateAdded"] = format_date(details.get("dateadded") or "", include_time=False)
    data["Tag"] = join_multi(details.get("tag"))
    data["UserRating"] = str(userrating) if userrating else ""

    cast_names = extract_cast_names(details.get("cast"))
    data["Cast"] = join_multi(cast_names)

    uniqueid_dict = details.get("uniqueid") or {}
    imdb_id = uniqueid_dict.get("imdb") or ""
    tmdb_id = uniqueid_dict.get("tmdb") or ""
    data["UniqueID.IMDB"] = imdb_id
    data["UniqueID.TMDB"] = tmdb_id

    data["PercentPlayed"] = _calculate_percent_played(details)

    file_path = details.get("file")
    data["FileName"] = _extract_filename(file_path)
    data["FileExtension"] = _extract_file_extension(file_path)

    ratings_dict = details.get("ratings") or {}
    data["_ratings"] = ratings_dict
    data.update(_rt_status_props(ratings_dict))

    data["_streamdetails"] = details.get("streamdetails") or {}

    resume = details.get("resume", {})
    resume_position = 0
    if isinstance(resume, dict) and resume.get('total'):
        resume_position = resume.get('position', 0)
    data["IsResumable"] = "true" if resume_position > 0 else ""

    return data


def set_movie_properties(details: dict) -> None:
    """Set movie window properties with SkinInfo prefix."""
    data = build_movie_data(details)
    props = {f"SkinInfo.Movie.{k}": v for k, v in data.items() if not k.startswith("_")}
    batch_set_props(props)
    _set_art_props("SkinInfo.Movie", details.get("art"), MOVIE_ART_KEYS)

    runtime_seconds = int(details.get("runtime") or 0)
    unified = _build_listitem_unified_data(
        title=details.get("title") or "",
        plot=details.get("plot") or "",
        year=str(details.get("year")) if details.get("year") else "",
        genre=join_multi(details.get("genre")),
        runtime_minutes=_seconds_to_minutes(runtime_seconds),
        playcount=int(details.get("playcount") or 0),
        rating=details.get("rating"),
        votes=details.get("votes"),
        userrating=details.get("userrating"),
        ratings_dict=details.get("ratings"),
    )
    set_listitem_unified_properties(unified)


def set_movie_extras_aggregates(count: int, total_runtime: int, unwatched: int,
                                unwatched_runtime: int) -> None:
    """Set `SkinInfo.Movie.Extras.*` aggregates (Piers+ asset view). Runtimes in minutes."""
    has_extras = count > 0
    total_min = _seconds_to_minutes(total_runtime)
    unwatched_min = _seconds_to_minutes(unwatched_runtime)
    batch_set_props({
        "SkinInfo.Movie.Extras.Count": str(count) if has_extras else "",
        "SkinInfo.Movie.Extras.TotalRuntime": str(total_min) if has_extras and total_min else "",
        "SkinInfo.Movie.Extras.Unwatched": str(unwatched) if has_extras else "",
        "SkinInfo.Movie.Extras.UnwatchedRuntime": (
            str(unwatched_min) if has_extras and unwatched_min else ""
        ),
    })


def build_movieset_data(set_details: dict, movies: List[dict]) -> dict:
    """Build movie set data dictionary for ListItem properties."""
    data = {}

    title = set_details.get("title") or set_details.get("label") or ""
    data["Title"] = title
    data["Plot"] = set_details.get("plot") or ""

    total_runtime_min = 0
    title_list_parts = []
    plot_blocks = []
    years = []
    studios_set, genres_set, countries_set = set(), set(), set()
    seen_dirs, agg_dirs = set(), []
    seen_wrs, agg_wrs = set(), []
    prim_seen, prim_list = set(), []

    for idx, m in enumerate(movies, 1):
        label = m.get("title") or m.get("label") or ""
        year = m.get("year")
        runtime = int(m.get("runtime") or 0)
        duration_min = _seconds_to_minutes(runtime)
        total_runtime_min += duration_min
        years.append(str(year) if year is not None else "")

        path = media_path(m.get("file"))
        info = media_streamdetails(path, m.get("streamdetails", {}))

        data[f"Movie.{idx}.DBID"] = str(m.get("movieid") or "")
        data[f"Movie.{idx}.Title"] = label or ""
        data[f"Movie.{idx}.Plot"] = m.get("plot") or ""
        data[f"Movie.{idx}.PlotOutline"] = m.get("plotoutline") or ""
        data[f"Movie.{idx}.Path"] = path or ""
        data[f"Movie.{idx}.Year"] = str(year) if year is not None else ""
        data[f"Movie.{idx}.Runtime"] = str(duration_min) if duration_min else ""
        data[f"Movie.{idx}.VideoResolution"] = info.get("videoresolution") or ""
        data[f"Movie.{idx}.MPAA"] = m.get("mpaa") or ""
        data[f"Movie.{idx}.Genre"] = join_multi(m.get("genre"))
        data[f"Movie.{idx}.Director"] = join_multi(m.get("director"))
        data[f"Movie.{idx}.Writer"] = join_multi(m.get("writer"))
        data[f"Movie.{idx}.Studio"] = join_multi(m.get("studio"))
        data[f"Movie.{idx}.Country"] = join_multi(m.get("country"))

        _studios = m.get("studio")
        primary = _first_or_empty(_studios)
        data[f"Movie.{idx}.StudioPrimary"] = primary

        if year is not None:
            title_list_parts.append(f"{label} ({year}){_CR}")
        else:
            title_list_parts.append(f"{label}{_CR}")

        use_outline = (m.get("plotoutline") or "").strip()
        block_plot = use_outline if use_outline else (m.get("plot") or "")
        if label:
            if year is not None:
                plot_blocks.append(
                    f"{_BOLD_OPEN}{label} ({year}){_BOLD_CLOSE}{_CR}{block_plot}{_CR}{_CR}"
                )
            else:
                plot_blocks.append(f"{_BOLD_OPEN}{label}{_BOLD_CLOSE}{_CR}{block_plot}{_CR}{_CR}")

        _ordered_unique_push(seen_dirs, agg_dirs, m.get("director"))
        _ordered_unique_push(seen_wrs, agg_wrs, m.get("writer"))
        studios_set.update(m.get("studio") or [])
        genres_set.update(m.get("genre") or [])
        countries_set.update(m.get("country") or [])

        if primary:
            key = primary.casefold()
            if key not in prim_seen:
                prim_seen.add(key)
                prim_list.append(primary)

    total_count = len(movies)
    title_list = "".join(title_list_parts)
    plot_joined = "".join(plot_blocks)

    data["Plots"] = plot_joined or ""
    data["ExtendedPlots"] = plot_joined or ""
    data["Titles"] = title_list or ""

    data["Runtime"] = str(total_runtime_min) if total_runtime_min else ""

    hrs = total_runtime_min // 60
    mins = total_runtime_min % 60
    data["Runtime.Hours"] = str(hrs) if hrs else ""
    data["Runtime.Minutes"] = str(mins) if mins >= 1 else ""

    data["Writers"] = join_multi(agg_wrs)
    data["Directors"] = join_multi(agg_dirs)
    genres_sorted = sorted(genres_set, key=str.casefold) if genres_set else []
    countries_sorted = sorted(countries_set, key=str.casefold) if countries_set else []
    data["Genres"] = join_multi(genres_sorted)
    data["Countries"] = join_multi(countries_sorted)
    data["Studios"] = join_multi(sorted(studios_set, key=str.casefold))

    for i, studio in enumerate(prim_list, 1):
        data[f"Studios.{i}"] = studio

    for i, w in enumerate(agg_wrs, 1):
        data[f"Writers.{i}"] = w

    for i, d in enumerate(agg_dirs, 1):
        data[f"Directors.{i}"] = d

    for i, g in enumerate(genres_sorted, 1):
        data[f"Genres.{i}"] = g

    for i, c in enumerate(countries_sorted, 1):
        data[f"Countries.{i}"] = c

    distinct_years = sorted({int(y) for y in years if y} - {0})
    data["Years"] = join_multi(distinct_years)
    if distinct_years:
        first, last = distinct_years[0], distinct_years[-1]
        data["Years.Range"] = str(first) if first == last else f"{first} - {last}"
    else:
        data["Years.Range"] = ""
    data["Count"] = str(total_count)

    data["_metadata"] = {
        "prim_list_count": len(prim_list),
        "writers_count": len(agg_wrs),
        "directors_count": len(agg_dirs),
        "genres_count": len(genres_sorted),
        "countries_count": len(countries_sorted),
        "movies_count": total_count,
        "total_runtime_min": total_runtime_min,
        "genres_sorted": genres_sorted,
    }

    return data


def set_movieset_properties(set_details: dict, movies: List[dict]) -> None:
    """Set movie set window properties with SkinInfo.Set prefix."""
    data = build_movieset_data(set_details, movies)

    metadata = data.pop("_metadata")
    props = {f"SkinInfo.Set.{k}": v for k, v in data.items()}
    batch_set_props(props)

    set_art = set_details.get("art") or {}
    art_props = {f"SkinInfo.Set.Art({key})": set_art.get(key) or "" for key in SET_ART_KEYS}

    for idx, m in enumerate(movies, 1):
        m_art = m.get("art") or {}
        for key in MOVIE_ART_KEYS:
            art_props[f"SkinInfo.Set.Movie.{idx}.Art({key})"] = (
                m_art.get(key) or (m.get("thumbnail") if key == "thumbnail" else "")
            )

    batch_set_props(art_props)

    _trim_simple_index("SkinInfo.Set.Studios", _STATE["set_studios"], metadata["prim_list_count"])
    _STATE["set_studios"] = metadata["prim_list_count"]
    _trim_simple_index("SkinInfo.Set.Writers", _STATE["set_writers"], metadata["writers_count"])
    _STATE["set_writers"] = metadata["writers_count"]
    _trim_simple_index(
        "SkinInfo.Set.Directors", _STATE["set_directors"], metadata["directors_count"]
    )
    _STATE["set_directors"] = metadata["directors_count"]
    _trim_simple_index("SkinInfo.Set.Genres", _STATE["set_genres"], metadata["genres_count"])
    _STATE["set_genres"] = metadata["genres_count"]
    _trim_simple_index(
        "SkinInfo.Set.Countries", _STATE["set_countries"], metadata["countries_count"]
    )
    _STATE["set_countries"] = metadata["countries_count"]
    _trim_indexed("SkinInfo.Set.Movie", _STATE["set_movies"], metadata["movies_count"])
    _STATE["set_movies"] = metadata["movies_count"]

    unified = _build_listitem_unified_data(
        title=set_details.get("title") or set_details.get("label") or "",
        plot=set_details.get("plot") or "",
        genre=join_multi(metadata["genres_sorted"]),
        runtime_minutes=metadata["total_runtime_min"],
    )
    set_listitem_unified_properties(unified)


def build_artist_data(artist: dict, albums: List[dict]) -> dict:
    """Build artist data dictionary for ListItem properties."""
    data = {}

    data["Artist"] = artist.get("artist") or ""
    data["Description"] = artist.get("description") or ""
    data["Genre"] = join_multi(artist.get("genre"))
    data["DateAdded"] = format_date(artist.get("dateadded") or "", include_time=False)

    data["Roles"] = join_multi(_extract_artist_names(artist.get("roles"), "role"))
    data["SongGenres"] = join_multi(_extract_artist_names(artist.get("songgenres"), "title"))
    data["Style"] = join_multi(artist.get("style"))
    data["Mood"] = join_multi(artist.get("mood"))
    data["Instrument"] = join_multi(artist.get("instrument"))
    data["YearsActive"] = join_multi(artist.get("yearsactive"))
    data["Born"] = artist.get("born") or ""
    data["Formed"] = artist.get("formed") or ""
    data["Died"] = artist.get("died") or ""
    data["Disbanded"] = artist.get("disbanded") or ""
    data["Type"] = artist.get("type") or ""
    data["Gender"] = artist.get("gender") or ""
    data["SortName"] = artist.get("sortname") or ""
    data["Disambiguation"] = artist.get("disambiguation") or ""

    mbids = artist.get("musicbrainzartistid") or []
    if isinstance(mbids, list):
        data["MusicBrainzID"] = ", ".join(mbids)
    else:
        data["MusicBrainzID"] = mbids or ""

    latestyear = 0
    firstyear = 0
    playcount_total = 0

    for idx, a in enumerate(albums, 1):
        a_year = a.get("year")
        a_albumid = a.get("albumid")
        a_playcount = a.get("playcount")
        a_rating = a.get("rating")

        data[f"Album.{idx}.Title"] = a.get("title") or ""
        data[f"Album.{idx}.Year"] = str(a_year) if a_year else ""
        data[f"Album.{idx}.Artist"] = join_multi(a.get("artist"))
        data[f"Album.{idx}.Genre"] = join_multi(a.get("genre"))
        data[f"Album.{idx}.DBID"] = str(a_albumid) if a_albumid else ""
        data[f"Album.{idx}.Label"] = a.get("albumlabel") or ""
        data[f"Album.{idx}.Playcount"] = str(a_playcount) if a_playcount else ""
        data[f"Album.{idx}.Rating"] = f"{a_rating:.1f}" if a_rating else ""

        y = a.get("year") or 0
        if y:
            if y > latestyear:
                latestyear = y
            if firstyear == 0 or y < firstyear:
                firstyear = y
        playcount_total += int(a.get("playcount") or 0)

    count = len(albums)
    if firstyear > 0 and latestyear < 2030:
        data["Albums.Newest"] = str(latestyear)
        data["Albums.Oldest"] = str(firstyear)
    else:
        data["Albums.Newest"] = ""
        data["Albums.Oldest"] = ""
    data["Albums.Count"] = str(count)
    data["Albums.Playcount"] = str(playcount_total)

    data["_metadata"] = {"albums_count": count}

    return data


def set_artist_properties(artist: dict, albums: List[dict]) -> None:
    """Set artist window properties with SkinInfo.Artist prefix."""
    data = build_artist_data(artist, albums)

    metadata = data.pop("_metadata")
    props = {f"SkinInfo.Artist.{k}": v for k, v in data.items()}
    batch_set_props(props)

    artist_art = artist.get("art") or {}
    art_props = {}
    art_props["SkinInfo.Artist.Art(thumb)"] = (
        artist_art.get("thumb") or artist.get("thumbnail") or ""
    )
    art_props["SkinInfo.Artist.Art(fanart)"] = (
        artist_art.get("fanart") or artist.get("fanart") or ""
    )

    for idx, a in enumerate(albums, 1):
        a_art = a.get("art") or {}
        art_props[f"SkinInfo.Artist.Album.{idx}.Art(thumb)"] = (
            a_art.get("thumb") or a.get("thumbnail") or ""
        )
        art_props[f"SkinInfo.Artist.Album.{idx}.Art(discart)"] = a_art.get("discart") or ""

    batch_set_props(art_props)

    _trim_indexed("SkinInfo.Artist.Album", _STATE["artist_albums"], metadata["albums_count"])
    _STATE["artist_albums"] = metadata["albums_count"]

    unified = _build_listitem_unified_data(
        title=artist.get("artist") or "",
        plot=artist.get("description") or "",
        genre=join_multi(artist.get("genre")),
    )
    set_listitem_unified_properties(unified)


def build_album_data(album: dict, songs: List[dict]) -> dict:
    """Build album data dictionary for ListItem properties."""
    data = {}

    album_year = album.get("year")
    album_playcount = album.get("playcount")
    album_rating = album.get("rating")
    album_userrating = album.get("userrating")
    album_compilation = album.get("compilation")
    album_totaldiscs = album.get("totaldiscs")

    data["Title"] = album.get("title") or ""
    data["Year"] = str(album_year) if album_year else ""
    data["Artist"] = join_multi(album.get("artist"))
    data["Genre"] = join_multi(album.get("genre"))
    data["Label"] = album.get("albumlabel") or ""
    data["Playcount"] = str(album_playcount) if album_playcount else ""
    data["Rating"] = f"{album_rating:.1f}" if album_rating else ""
    data["UserRating"] = f"{album_userrating:.1f}" if album_userrating else ""
    data["MusicBrainzID"] = album.get("musicbrainzalbumid") or ""
    data["ReleaseGroupID"] = album.get("musicbrainzreleasegroupid") or ""
    data["LastPlayed"] = format_date(album.get("lastplayed") or "", include_time=False)
    data["DateAdded"] = format_date(album.get("dateadded") or "", include_time=False)
    data["Description"] = album.get("description") or ""
    data["Votes"] = format_number(album.get("votes"))
    data["DisplayArtist"] = album.get("displayartist") or ""
    data["Compilation"] = str(album_compilation) if album_compilation is not None else ""
    data["ReleaseType"] = album.get("releasetype") or ""
    data["SortArtist"] = album.get("sortartist") or ""
    data["TotalDiscs"] = str(album_totaldiscs) if album_totaldiscs else ""
    data["ReleaseDate"] = album.get("releasedate") or ""
    data["OriginalDate"] = album.get("originaldate") or ""

    songgenres_list = album.get("songgenres") or []
    if songgenres_list:
        genre_titles = [
            g.get("title") for g in songgenres_list if isinstance(g, dict) and g.get("title")
        ]
        data["SongGenres"] = join_multi(genre_titles)
    else:
        data["SongGenres"] = ""

    disc_max = 0
    total_seconds = 0
    tracklist_parts = []

    for idx, s in enumerate(songs, 1):
        s_duration = s.get("duration")
        s_track = s.get("track")

        data[f"Song.{idx}.Title"] = s.get("title") or ""
        data[f"Song.{idx}.Duration"] = str(s_duration) if s_duration else ""
        data[f"Song.{idx}.TrackNumber"] = str(s_track) if s_track else ""

        f = s.get("file") or ""
        ext = f.rsplit(".", 1)[-1] if "." in f else ""
        data[f"Song.{idx}.FileExtension"] = ext or ""

        d = int(s.get("disc") or 0)
        if d > disc_max:
            disc_max = d
        total_seconds += int(s_duration or 0)
        trk = s.get("track")
        title = s.get("title") or ""
        if trk is not None and title:
            tracklist_parts.append(f"{_BOLD_OPEN}{trk}{_BOLD_CLOSE}: {title}{_CR}")

    album_seconds = int(album.get("albumduration") or 0) or total_seconds
    data["AlbumDuration"] = str(album_seconds) if album_seconds else ""
    data["Songs.Discs"] = str(disc_max)
    data["Songs.Duration"] = _duration_props(total_seconds)["Duration"]
    data["Songs.Tracklist"] = "".join(tracklist_parts)
    data["Songs.Count"] = str(len(songs))

    data["_metadata"] = {"songs_count": len(songs)}

    return data


def set_album_properties(album: dict, songs: List[dict]) -> None:
    """Set album window properties with SkinInfo.Album prefix."""
    data = build_album_data(album, songs)

    metadata = data.pop("_metadata")
    props = {f"SkinInfo.Album.{k}": v for k, v in data.items()}
    batch_set_props(props)

    album_art = album.get("art") or {}
    art_props = {}
    art_props["SkinInfo.Album.Art(thumb)"] = album_art.get("thumb") or album.get("thumbnail") or ""
    art_props["SkinInfo.Album.Art(fanart)"] = album_art.get("fanart") or album.get("fanart") or ""
    art_props["SkinInfo.Album.Art(discart)"] = album_art.get("discart") or ""

    batch_set_props(art_props)

    _trim_indexed("SkinInfo.Album.Song", _STATE["album_songs"], metadata["songs_count"])
    _STATE["album_songs"] = metadata["songs_count"]

    total_seconds = sum(int(s.get("duration") or 0) for s in songs)

    unified = _build_listitem_unified_data(
        title=album.get("title") or "",
        plot=album.get("description") or "",
        year=str(album.get("year")) if album.get("year") else "",
        genre=join_multi(album.get("genre")),
        duration_seconds=total_seconds,
        rating=album.get("rating"),
        votes=album.get("votes"),
        userrating=album.get("userrating"),
    )
    set_listitem_unified_properties(unified)


_RATING_STATE: Dict[str, Set[str]] = {}
_LISTITEM_RATING_STATE: Set[str] = set()


def set_ratings_properties(item: dict, media_type: str = "Movie") -> None:
    ratings = item.get("ratings") or {}
    prefix = f"SkinInfo.{media_type}.Rating"
    props: Dict[str, Optional[str]] = {}
    current_sources: Set[str] = set()

    for src, info in ratings.items():
        if info.get("rating") is None:
            continue
        result = _scale_rating(info.get("rating"), info.get("max") or 10)
        if not result:
            continue
        scaled, pct = result
        output_src = RATING_SOURCE_NORMALIZE.get(src) or src
        current_sources.add(output_src)
        props[f"{prefix}.{output_src}"] = str(scaled)
        props[f"{prefix}.{output_src}.Votes"] = format_number(info.get("votes"))
        props[f"{prefix}.{output_src}.Percent"] = str(pct)

    prev_sources = _RATING_STATE.get(media_type, set())
    removed_sources = prev_sources - current_sources
    for src in removed_sources:
        props[f"{prefix}.{src}"] = ""
        props[f"{prefix}.{src}.Votes"] = ""
        props[f"{prefix}.{src}.Percent"] = ""

    if not ratings:
        props[prefix] = ""

    batch_set_props(props)

    _RATING_STATE[media_type] = current_sources


def build_tvshow_data(details: dict) -> dict:
    """Build the property dict for a TV show ListItem from a JSON-RPC show details payload."""
    data = {}

    year = details.get("year")
    rating = details.get("rating")
    runtime_seconds = int(details.get("runtime") or 0)
    runtime_minutes = _seconds_to_minutes(runtime_seconds)
    episode = details.get("episode")
    season = details.get("season")
    watchedepisodes = details.get("watchedepisodes")
    playcount = details.get("playcount")

    data["Title"] = details.get("title") or ""
    data["Plot"] = details.get("plot") or ""
    data["Year"] = str(year) if year else ""
    data["Premiered"] = details.get("premiered") or ""
    data["Rating"] = f"{rating:.1f}" if rating else ""
    data["Votes"] = format_number(details.get("votes"))
    data["Genre"] = join_multi(details.get("genre"))
    data["Studio"] = join_multi(details.get("studio"))
    data["MPAA"] = details.get("mpaa") or ""
    data["Status"] = details.get("status") or ""
    hrs = runtime_minutes // 60
    mins = runtime_minutes % 60
    data["Runtime"] = str(runtime_minutes) if runtime_minutes else ""
    data["Runtime.Hours"] = str(hrs) if hrs else ""
    data["Runtime.Minutes"] = str(mins) if mins >= 1 else ""
    total_seconds = int(details.get("total_runtime") or 0)
    total_minutes = _seconds_to_minutes(total_seconds)
    total_hrs = total_minutes // 60
    total_mins = total_minutes % 60
    data["TotalRuntime"] = str(total_minutes) if total_minutes else ""
    data["TotalRuntime.Hours"] = str(total_hrs) if total_hrs else ""
    data["TotalRuntime.Minutes"] = str(total_mins) if total_mins >= 1 else ""
    data["Episode"] = str(episode) if episode else ""
    data["Season"] = str(season) if season else ""
    data["WatchedEpisodes"] = str(watchedepisodes) if watchedepisodes else ""
    data["IMDBNumber"] = details.get("imdbnumber") or ""
    data["OriginalTitle"] = details.get("originaltitle") or ""
    data["SortTitle"] = details.get("sorttitle") or ""
    data["EpisodeGuide"] = details.get("episodeguide") or ""
    data["Tag"] = join_multi(details.get("tag"))
    data["Path"] = media_path(details.get("file")) or ""
    data["DateAdded"] = format_date(details.get("dateadded") or "", include_time=False)
    data["LastPlayed"] = format_date(details.get("lastplayed") or "", include_time=False)
    data["Playcount"] = str(playcount) if playcount else ""
    data["Trailer"] = details.get("trailer") or ""
    data["UserRating"] = str(details.get("userrating")) if details.get("userrating") else ""

    cast_names = extract_cast_names(details.get("cast"))
    data["Cast"] = join_multi(cast_names)

    uniqueid_dict = details.get("uniqueid") or {}
    imdb_id = uniqueid_dict.get("imdb") or ""
    tmdb_id = uniqueid_dict.get("tmdb") or ""
    data["UniqueID.IMDB"] = imdb_id
    data["UniqueID.TMDB"] = tmdb_id
    data["UniqueID.TVDB"] = uniqueid_dict.get("tvdb") or ""

    _studios = details.get("studio")
    primary_studio = _first_or_empty(_studios)
    data["StudioPrimary"] = primary_studio or ""

    if episode and episode > 0 and watchedepisodes is not None:
        # integer math, not round(), to match Kodi's own WatchedEpisodePercent
        watched_percent = (watchedepisodes * 100) // episode
    else:
        watched_percent = 0
    data["WatchedEpisodePercent"] = str(watched_percent)

    ratings_dict = details.get("ratings") or {}
    data["_ratings"] = ratings_dict
    data.update(_rt_status_props(ratings_dict))

    return data


def set_tvshow_properties(details: dict) -> None:
    """Set TV show window properties with SkinInfo.TVShow prefix."""
    data = build_tvshow_data(details)
    props = {f"SkinInfo.TVShow.{k}": v for k, v in data.items() if not k.startswith("_")}
    batch_set_props(props)
    _set_art_props("SkinInfo.TVShow", details.get("art"), VIDEO_ART_KEYS)

    runtime_seconds = int(details.get("runtime") or 0)
    unified = _build_listitem_unified_data(
        title=details.get("title") or "",
        plot=details.get("plot") or "",
        year=str(details.get("year")) if details.get("year") else "",
        genre=join_multi(details.get("genre")),
        runtime_minutes=_seconds_to_minutes(runtime_seconds),
        rating=details.get("rating"),
        votes=details.get("votes"),
        userrating=details.get("userrating"),
        ratings_dict=details.get("ratings"),
    )
    set_listitem_unified_properties(unified)


def build_season_data(details: dict) -> dict:
    """Build season data dictionary for ListItem properties."""
    data = {}

    season = details.get("season")
    episode = details.get("episode")
    watchedepisodes = details.get("watchedepisodes")
    playcount = details.get("playcount")
    tvshowid = details.get("tvshowid")
    userrating = details.get("userrating")
    runtime_seconds = int(details.get("runtime") or 0)
    runtime_minutes = _seconds_to_minutes(runtime_seconds)

    hrs = runtime_minutes // 60
    mins = runtime_minutes % 60
    data["Title"] = details.get("title") or ""
    data["Season"] = str(season) if season is not None else ""
    data["ShowTitle"] = details.get("showtitle") or ""
    data["Episode"] = str(episode) if episode else ""
    data["WatchedEpisodes"] = str(watchedepisodes) if watchedepisodes else ""
    data["Runtime"] = str(runtime_minutes) if runtime_minutes else ""
    data["Runtime.Hours"] = str(hrs) if hrs else ""
    data["Runtime.Minutes"] = str(mins) if mins >= 1 else ""
    total_seconds = int(details.get("total_runtime") or 0)
    total_minutes = _seconds_to_minutes(total_seconds)
    total_hrs = total_minutes // 60
    total_mins = total_minutes % 60
    data["TotalRuntime"] = str(total_minutes) if total_minutes else ""
    data["TotalRuntime.Hours"] = str(total_hrs) if total_hrs else ""
    data["TotalRuntime.Minutes"] = str(total_mins) if total_mins >= 1 else ""
    data["Playcount"] = str(playcount) if playcount else ""
    data["UserRating"] = str(userrating) if userrating else ""
    data["TVShowID"] = str(tvshowid) if tvshowid and tvshowid != -1 else ""

    return data


def set_season_properties(details: dict) -> None:
    """Set season window properties with SkinInfo.Season prefix."""
    data = build_season_data(details)
    props = {f"SkinInfo.Season.{k}": v for k, v in data.items()}
    batch_set_props(props)
    _set_art_props("SkinInfo.Season", details.get("art"), VIDEO_ART_KEYS)

    runtime_seconds = int(details.get("runtime") or 0)
    unified = _build_listitem_unified_data(
        title=details.get("title") or "",
        runtime_minutes=_seconds_to_minutes(runtime_seconds),
        userrating=details.get("userrating"),
    )
    set_listitem_unified_properties(unified)


def build_episode_data(details: dict) -> dict:
    """Build episode data dictionary for ListItem properties."""
    data = {}

    path = media_path(details.get("file"))
    info = media_streamdetails(path, details.get("streamdetails", {}))

    rating = details.get("rating")
    season = details.get("season")
    episode = details.get("episode")
    runtime_seconds = int(details.get("runtime") or 0)
    runtime_minutes = _seconds_to_minutes(runtime_seconds)
    playcount = details.get("playcount")
    tvshowid = details.get("tvshowid")
    userrating = details.get("userrating")
    seasonid = details.get("seasonid")

    data["Title"] = details.get("title") or ""
    data["Plot"] = details.get("plot") or ""
    data["Rating"] = f"{rating:.1f}" if rating else ""
    data["Votes"] = format_number(details.get("votes"))
    data["Season"] = str(season) if season is not None else ""
    data["Episode"] = str(episode) if episode is not None else ""
    data["TVShow"] = details.get("showtitle") or ""
    data["FirstAired"] = details.get("firstaired") or ""
    data.update(_runtime_props(runtime_minutes, int(playcount or 0)))
    data["Director"] = join_multi(details.get("director"))
    data["Writer"] = join_multi(details.get("writer"))
    data["Path"] = path or ""
    data["ProductionCode"] = details.get("productioncode") or ""
    data["OriginalTitle"] = details.get("originaltitle") or ""
    data["Playcount"] = str(playcount) if playcount else ""

    data["Codec"] = info.get("videocodec") or ""
    data["Resolution"] = info.get("videoresolution") or ""
    data["Aspect"] = info.get("videoaspect") or ""
    data["AudioCodec"] = info.get("audiocodec") or ""
    data["AudioChannels"] = info.get("audiochannels") or ""

    data["LastPlayed"] = format_date(details.get("lastplayed") or "", include_time=False)
    data["TVShowID"] = str(tvshowid) if tvshowid else ""
    data["DateAdded"] = format_date(details.get("dateadded") or "", include_time=False)
    data["UserRating"] = str(userrating) if userrating else ""
    data["SeasonID"] = str(seasonid) if seasonid else ""
    data["Genre"] = join_multi(details.get("genre"))
    data["Studio"] = join_multi(details.get("studio"))

    cast_names = extract_cast_names(details.get("cast"))
    data["Cast"] = join_multi(cast_names)

    uniqueid_dict = details.get("uniqueid") or {}
    data["UniqueID.IMDB"] = uniqueid_dict.get("imdb") or ""
    data["UniqueID.TMDB"] = uniqueid_dict.get("tmdb") or ""
    data["UniqueID.TVDB"] = uniqueid_dict.get("tvdb") or ""

    data["PercentPlayed"] = _calculate_percent_played(details)

    file_path = details.get("file")
    data["FileName"] = _extract_filename(file_path)
    data["FileExtension"] = _extract_file_extension(file_path)

    ratings_dict = details.get("ratings") or {}
    data["_ratings"] = ratings_dict
    data.update(_rt_status_props(ratings_dict))

    data["_streamdetails"] = details.get("streamdetails") or {}

    resume = details.get("resume", {})
    resume_position = 0
    if isinstance(resume, dict) and resume.get('total'):
        resume_position = resume.get('position', 0)
    data["IsResumable"] = "true" if resume_position > 0 else ""

    return data


def set_episode_properties(details: dict) -> None:
    """Set `SkinInfo.Episode.*` window properties from a JSON-RPC episode details payload."""
    data = build_episode_data(details)
    props = {f"SkinInfo.Episode.{k}": v for k, v in data.items() if not k.startswith("_")}
    batch_set_props(props)
    _set_art_props("SkinInfo.Episode", details.get("art"), VIDEO_ART_KEYS)

    runtime_seconds = int(details.get("runtime") or 0)
    unified = _build_listitem_unified_data(
        title=details.get("title") or "",
        plot=details.get("plot") or "",
        genre=join_multi(details.get("genre")),
        runtime_minutes=_seconds_to_minutes(runtime_seconds),
        playcount=int(details.get("playcount") or 0),
        rating=details.get("rating"),
        votes=details.get("votes"),
        userrating=details.get("userrating"),
        ratings_dict=details.get("ratings"),
    )
    set_listitem_unified_properties(unified)


def build_musicvideo_data(details: dict) -> dict:
    """Build music video data dictionary for ListItem properties."""
    data = {}

    path = media_path(details.get("file"))
    info = media_streamdetails(path, details.get("streamdetails", {}))

    runtime_seconds = int(details.get("runtime") or 0)

    year = details.get("year")
    playcount = details.get("playcount")
    rating = details.get("rating")
    userrating = details.get("userrating")
    track = details.get("track")

    data["Title"] = details.get("title") or ""
    data["Artist"] = join_multi(details.get("artist"))
    data["Album"] = details.get("album") or ""
    data["Genre"] = join_multi(details.get("genre"))
    data["Year"] = str(year) if year else ""
    data["Plot"] = details.get("plot") or ""
    data.update(_runtime_props(_seconds_to_minutes(runtime_seconds), int(playcount or 0)))
    data.update(_duration_props(runtime_seconds))
    data["Director"] = join_multi(details.get("director"))
    data["Studio"] = join_multi(details.get("studio"))
    data["Path"] = path or ""
    data["Premiered"] = details.get("premiered") or ""
    data["Tag"] = join_multi(details.get("tag"))
    data["Playcount"] = str(playcount) if playcount else ""

    data["Codec"] = info.get("videocodec") or ""
    data["Resolution"] = info.get("videoresolution") or ""
    data["Aspect"] = info.get("videoaspect") or ""
    data["AudioCodec"] = info.get("audiocodec") or ""
    data["AudioChannels"] = info.get("audiochannels") or ""

    _artists = details.get("artist")
    primary_artist = _first_or_empty(_artists)
    data["ArtistPrimary"] = primary_artist or ""

    data["LastPlayed"] = format_date(details.get("lastplayed") or "", include_time=False)
    data["DateAdded"] = format_date(details.get("dateadded") or "", include_time=False)
    data["Rating"] = f"{rating:.1f}" if rating else ""
    data["UserRating"] = str(userrating) if userrating else ""
    data["Track"] = str(track) if track else ""

    uniqueid_dict = details.get("uniqueid") or {}
    data["UniqueID.IMDB"] = uniqueid_dict.get("imdb") or ""
    data["UniqueID.TMDB"] = uniqueid_dict.get("tmdb") or ""

    data["PercentPlayed"] = _calculate_percent_played(details)

    file_path = details.get("file")
    data["FileName"] = _extract_filename(file_path)
    data["FileExtension"] = _extract_file_extension(file_path)

    ratings_dict = details.get("ratings") or {}
    data["_ratings"] = ratings_dict
    data.update(_rt_status_props(ratings_dict))

    data["_streamdetails"] = details.get("streamdetails") or {}

    resume = details.get("resume", {})
    resume_position = 0
    if isinstance(resume, dict) and resume.get('total'):
        resume_position = resume.get('position', 0)
    data["IsResumable"] = "true" if resume_position > 0 else ""

    return data


def set_musicvideo_properties(details: dict) -> None:
    """Set music video window properties with SkinInfo.MusicVideo prefix."""
    data = build_musicvideo_data(details)
    props = {f"SkinInfo.MusicVideo.{k}": v for k, v in data.items() if not k.startswith("_")}
    batch_set_props(props)
    _set_art_props("SkinInfo.MusicVideo", details.get("art"), VIDEO_ART_KEYS)

    runtime_seconds = int(details.get("runtime") or 0)
    unified = _build_listitem_unified_data(
        title=details.get("title") or "",
        plot=details.get("plot") or "",
        year=str(details.get("year")) if details.get("year") else "",
        genre=join_multi(details.get("genre")),
        runtime_minutes=_seconds_to_minutes(runtime_seconds),
        playcount=int(details.get("playcount") or 0),
        duration_seconds=runtime_seconds,
        rating=details.get("rating"),
        userrating=details.get("userrating"),
    )
    set_listitem_unified_properties(unified)


