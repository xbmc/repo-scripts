"""Stable tracker identity for library items.

Kodi reassigns its internal DB IDs on library rebuild, so the tracker cannot
key on kodi_id. External IDs (tmdb/imdb from uniqueid) are stable across
rebuilds and are preferred. Movies/shows without an external ID fall back to
"title (year)". Episodes use a composite "{show} S..E.." key (their own S/E
numbering within Kodi is internally consistent).

Logging:
    None (pure function).
"""
from __future__ import annotations

from typing import Any, Dict

from resources.lib.data.media_types import MediaType


def compute_identity(item: Dict[str, Any], media_type: MediaType) -> str:
    """Return a stable tracker key for a Kodi library item.

    Movies/shows: "tmdb:<id>", else "imdb:<id>", else "title (year)" or "title".
    Episodes: "{showtitle} S{season:02d}E{episode:02d}".
    """
    if media_type.name == "episode":
        return "{showtitle} S{season:02d}E{episode:02d}".format(
            showtitle=item.get("showtitle", ""),
            season=int(item.get("season", 0) or 0),
            episode=int(item.get("episode", 0) or 0),
        )

    uid = item.get("uniqueid") or {}
    tmdb = uid.get("tmdb") or uid.get("themoviedb")
    if tmdb:
        return "tmdb:{}".format(tmdb)
    imdb = uid.get("imdb")
    if imdb:
        return "imdb:{}".format(imdb)

    # No external ID: fall back to "title (year)". The year is derived from the
    # date field the scan already requests (premiered/firstaired); Kodi does not
    # return a `year` property unless explicitly asked, and the scan does not ask.
    title = item.get("title", "")
    date_value = item.get(media_type.date_field) or ""
    year = date_value[:4]
    if len(year) == 4 and year.isdigit():
        return "{} ({})".format(title, year)
    return title
