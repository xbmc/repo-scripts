# SPDX-License-Identifier: GPL-2.0-only
"""What is playing, resolved once at start.

Episode-level unique ids are mostly absent: measured on a real library, 361 of 400 sampled
episodes carried only an "unknown" key, which CrossWatch discards. So the usable key is
show-level ids plus season and episode number, with episode ids sent when they are real.

Keys under "unknown" are skipped deliberately: there is no safe way to tell what they are.

So are placeholder values. Scrapers write the string "None" into uniqueid, and a real
library here returned {"imdb": "None", "tvdb": "None", "tvrage": "None"} for a show. Those
reach the wire looking like ids, so the receiver routes on them and the no-usable-id gate
sees an item that is in fact unidentifiable.
"""

import re
from typing import Any
from urllib.parse import unquote_to_bytes, urlsplit, urlunsplit

from resources.lib.kodi import KodiApi
from resources.lib.log import get_logger, log_timing, redact
from resources.lib.models import MediaItem, Source

_log = get_logger("media")

PKC_PREFIX = "plugin://plugin.video.plexkodiconnect"
_RATING_KEY = re.compile(r"/(\d+)/?$")
_REDACTED = "<redacted>"

# Protocols whose hostname is the parent URL, percent-encoded: URIUtils::HasParentInHostname,
# plus the archive protocols the official vfs add-ons register with encodedhostname
# (vfs.rar, vfs.libarchive). The parent can carry credentials of its own.
_PARENT_IN_HOSTNAME = frozenset({"zip", "apk", "bluray", "udf", "iso9660", "xbt", "rar", "archive"})
# What CURL::Encode leaves as is.
_UNENCODED = frozenset(b"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._!()")

_ITEM_PROPERTIES = ["title", "showtitle", "season", "episode", "year", "tvshowid", "file", "uniqueid"]

# Values a scraper leaves behind when it had no id. Compared lowercase. "0" and "-1" are
# here because no provider issues them and both are common "absent" sentinels.
_PLACEHOLDER_IDS = frozenset({"none", "null", "nan", "unknown", "0", "-1", "false"})


def strip_credentials(path: str) -> str:
    """Remove user:password@ and the whole query string and fragment from a VFS URL.

    Kodi carries share credentials inline and strips them in FileOperations but not on the
    Player.GetItem path, so without this they reach the payload and the log. A token in a
    stream URL is a credential too, and payload.py copies this value verbatim into the POST
    body.

    The query is replaced as a whole rather than scanned for where it ends: a parameter
    value may hold dots, spaces or quotes, and any boundary rule leaves what follows it in
    place. A query or fragment counts only when it holds a "=", so a filename with a "?" or
    "#" in it ("S01E01.Are.You.My.Mummy?.mkv") is left intact.

    Request headers ride after the first "|" ("...|User-Agent=Kodi&Cookie=s=1"). They are split
    off first, as CURL::Parse does, and replaced whole by the same "=" rule.
    """
    text = str(path or "")
    if "://" not in text:
        return text
    head, bar, options = text.partition("|")
    # redact() still runs last: it catches what the URL parse cannot see, such as the
    # userinfo of a URL nested in the path ("http://proxy/fetch/http://user:pass@inner/").
    return redact(_strip_url(head) + bar + (_REDACTED if "=" in options else options))


def _strip_url(text: str) -> str:
    try:
        parts = urlsplit(text)
    except ValueError:
        return text
    netloc, query, fragment = parts.netloc, parts.query, parts.fragment
    if "@" in netloc:
        netloc = netloc.rsplit("@", 1)[-1]
    if parts.scheme in _PARENT_IN_HOSTNAME:
        netloc = _strip_parent(netloc)
    if "=" in query:
        query, fragment = _REDACTED, ""
    elif "=" in fragment:
        fragment = _REDACTED
    if (netloc, query, fragment) == (parts.netloc, parts.query, parts.fragment):
        return text
    return urlunsplit((parts.scheme, netloc, parts.path, query, fragment))


def _strip_parent(hostname: str) -> str:
    """The parent URL in an archive path's hostname, stripped as CURL::GetWithoutUserDetails
    does: decoded, stripped, and encoded again. A nested archive recurses, one encoding per
    level. Returned untouched when nothing was stripped, so a path keeps Kodi's own escapes."""
    # CURL::Decode, which reads "+" as a space; surrogateescape round-trips non-UTF-8 bytes.
    parent = unquote_to_bytes(hostname.replace("+", " ")).decode("utf-8", "surrogateescape")
    stripped = strip_credentials(parent)
    if stripped == parent:
        return hostname
    raw = stripped.encode("utf-8", "surrogateescape")
    return "".join(chr(b) if b in _UNENCODED else f"%{b:02x}" for b in raw)


def clean_ids(uniqueid: Any) -> dict[str, str]:
    if not isinstance(uniqueid, dict):
        return {}
    out: dict[str, str] = {}
    for key, value in uniqueid.items():
        name = str(key or "").strip().lower()
        text = str(value or "").strip()
        if not text or name == "unknown" or text.lower() in _PLACEHOLDER_IDS:
            continue
        out[name] = text
    return out


def _int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


class MediaResolver:
    def __init__(self, kodi: KodiApi) -> None:
        self._kodi = kodi
        self._shows: dict[int, tuple[dict[str, str], int | None]] = {}

    def forget_shows(self) -> None:
        """Drop memoised show details; a library scan can change them."""
        self._shows.clear()

    def resolve(self) -> MediaItem | None:
        with log_timing(_log, "media.resolve") as timer:
            player_id = self._active_player()
            if player_id is None:
                return None
            timer.mark("active_player")

            payload = self._kodi.jsonrpc("Player.GetItem", {"playerid": player_id, "properties": _ITEM_PROPERTIES})
            item = payload.get("item")
            if not isinstance(item, dict):
                return None
            timer.mark("get_item")

            media_type = str(item.get("type") or "").strip().lower()
            if media_type not in {"episode", "movie"}:
                _log.info("media.ignored", media_type=media_type or "unknown")
                return None

            file_path = strip_credentials(str(item.get("file") or ""))
            is_pkc = file_path.startswith(PKC_PREFIX)
            own_ids = clean_ids(item.get("uniqueid"))
            raw_id = _int_or_none(item.get("id"))
            library_id = raw_id if raw_id is not None and raw_id >= 0 else None
            source: Source = "plexkodiconnect" if is_pkc else "library"
            rating_key = self._rating_key(file_path) if is_pkc else None

            if media_type == "episode":
                tvshowid = _int_or_none(item.get("tvshowid"))
                tvshowid = tvshowid if tvshowid and tvshowid > 0 else None
                show_ids, show_year = self._lookup_show(tvshowid) if tvshowid else ({}, None)
                timer.mark("show_ids")
                # A scraper can store the series' id on an episode. Sent bare it reads as the
                # episode's own id and the receiver looks up a show as an episode, so an id
                # equal to the show's of the same type is not an episode id.
                own_ids = {name: value for name, value in own_ids.items() if show_ids.get(name) != value}
                media = MediaItem(
                    media_type="episode",
                    library_id=library_id,
                    show_library_id=tvshowid,
                    title=str(item.get("showtitle") or "") or None,
                    year=_int_or_none(item.get("year")),
                    season=_int_or_none(item.get("season")),
                    episode=_int_or_none(item.get("episode")),
                    episode_title=str(item.get("title") or "") or None,
                    show_ids=show_ids,
                    episode_ids=own_ids,
                    file=file_path or None,
                    source=source,
                    is_pkc=is_pkc,
                    plex_rating_key=rating_key,
                    show_year=show_year,
                )
            else:
                media = MediaItem(
                    media_type="movie",
                    library_id=library_id,
                    show_library_id=None,
                    title=str(item.get("title") or "") or None,
                    year=_int_or_none(item.get("year")),
                    season=None,
                    episode=None,
                    episode_title=None,
                    show_ids=own_ids,
                    episode_ids={},
                    file=file_path or None,
                    source=source,
                    is_pkc=is_pkc,
                    plex_rating_key=rating_key,
                )

        _log.info(
            "media.resolved",
            media_type=media.media_type,
            library_id=media.library_id,
            show_library_id=media.show_library_id,
            source=media.source,
            ids=",".join(sorted(media.show_ids)) or "none",
        )
        return media

    def _active_player(self) -> int | None:
        result = self._kodi.jsonrpc("Player.GetActivePlayers")
        # Bound once: a guard written over a second .get() call says nothing about the
        # value the first one returned.
        players = result.get("result")
        if not isinstance(players, list):
            return None
        for player in players:
            if isinstance(player, dict) and player.get("type") == "video":
                return int(player.get("playerid", 1))
        return None

    def _lookup_show(self, tvshowid: int) -> tuple[dict[str, str], int | None]:
        cached = self._shows.get(tvshowid)
        if cached is not None:
            return dict(cached[0]), cached[1]
        try:
            details = self._kodi.jsonrpc(
                "VideoLibrary.GetTVShowDetails", {"tvshowid": tvshowid, "properties": ["uniqueid", "year"]}
            )
        except Exception as exc:
            _log.warning("media.show_lookup_failed", tvshowid=tvshowid, error=str(exc))
            return {}, None
        show = details.get("tvshowdetails")
        ids = clean_ids(show.get("uniqueid")) if isinstance(show, dict) else {}
        year = _int_or_none(show.get("year")) if isinstance(show, dict) else None
        # Negative results are cached too, so a show with no ids is not re-queried per episode.
        self._shows[tvshowid] = (ids, year or None)
        return dict(ids), year or None

    @staticmethod
    def _rating_key(file_path: str) -> str | None:
        match = _RATING_KEY.search(file_path)
        return match.group(1) if match else None
