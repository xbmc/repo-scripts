from __future__ import annotations

VALID_SORT_METHODS = frozenset((
    "none", "label", "date", "size", "file", "path", "drivetype", "title", "track",
    "time", "artist", "album", "albumtype", "genre", "country", "year", "rating",
    "userrating", "votes", "top250", "programcount", "playlist", "episode", "season",
    "totalepisodes", "watchedepisodes", "tvshowstatus", "tvshowtitle", "sorttitle",
    "productioncode", "mpaa", "studio", "dateadded", "lastplayed", "playcount",
    "listeners", "bitrate", "random", "totaldiscs", "originaldate", "bpm", "originaltitle",
))


def validate_sort_method(method: str, fallback: str) -> str:
    """Kodi rejects unknown sort methods with -32602, which surfaces as a silently empty widget."""
    return method if method in VALID_SORT_METHODS else fallback
