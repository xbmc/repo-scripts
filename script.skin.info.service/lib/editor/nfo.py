"""Write library metadata to local NFO files, matching Kodi's exporter field-for-field.

Mirrors `CVideoInfoTag::Save()` (Omega) element order, tags and value formats so the
output imports into Kodi identically to its own export. Not byte-identical: Kodi's
scraper `<thumb>`/`<fanart>` art XML and tinyxml2 whitespace can't be reproduced from
JSON-RPC. Merge preserves any element we do not write (incl. those art blocks).
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple

import xbmc
import xbmcvfs

from lib.kodi.client import get_item_details, decode_image_url, log, ADDON

# Root NFO element per media type (episode uses "episodedetails").
_ROOT_TAG = {
    'movie': 'movie',
    'tvshow': 'tvshow',
    'episode': 'episodedetails',
    'musicvideo': 'musicvideo',
}

# JSON-RPC properties needed to populate the NFO, per media type.
_NFO_PROPERTIES = {
    'movie': [
        "title", "originaltitle", "sorttitle", "ratings", "userrating", "top250",
        "plotoutline", "plot", "tagline", "runtime", "mpaa", "playcount", "lastplayed",
        "imdbnumber", "uniqueid", "genre", "country", "set", "setid", "tag", "writer", "director",
        "premiered", "year", "studio", "trailer", "streamdetails", "cast", "showlink",
        "resume", "dateadded", "file",
    ],
    'tvshow': [
        "title", "originaltitle", "sorttitle", "ratings", "userrating", "season", "episode",
        "plot", "runtime", "mpaa", "playcount", "lastplayed", "episodeguide", "imdbnumber",
        "uniqueid", "genre", "tag", "premiered", "year", "studio", "trailer", "cast",
        "dateadded", "file",
    ],
    'episode': [
        "title", "originaltitle", "ratings", "userrating", "season", "episode",
        "specialsortseason", "specialsortepisode", "plot", "runtime", "playcount", "lastplayed",
        "uniqueid", "genre", "showtitle", "writer", "director", "firstaired", "productioncode",
        "studio", "streamdetails", "cast", "resume", "dateadded", "file",
    ],
    'musicvideo': [
        "title", "userrating", "track", "album", "plot", "runtime", "playcount", "lastplayed",
        "uniqueid", "genre", "tag", "director", "premiered", "year", "studio", "streamdetails",
        "artist", "resume", "dateadded", "file",
    ],
}


def _sep(path: str) -> str:
    """Path separator: '/' for URLs/POSIX paths, '\\' for pure Windows paths."""
    return '/' if '/' in path else '\\'


def _nfo_path(media_type: str, media_file: str) -> Optional[str]:
    """Resolve the NFO path: `<file>.nfo`, or `tvshow.nfo` in the show folder."""
    if not media_file:
        return None
    if media_type == 'tvshow':
        folder = media_file if media_file.endswith(('/', '\\')) else media_file + _sep(media_file)
        return folder + 'tvshow.nfo'
    dot = media_file.rfind('.')
    slash = max(media_file.rfind('/'), media_file.rfind('\\'))
    if dot <= slash:
        return None
    return media_file[:dot] + '.nfo'


_ILLEGAL_XML = re.compile('[^\t\n\r\x20-\uD7FF\uE000-\uFFFD\U00010000-\U0010FFFF]')


def _xml_safe(value: Any) -> str:
    return _ILLEGAL_XML.sub('', '' if value is None else str(value))


def _set_str(parent: ET.Element, tag: str, value: Any) -> None:
    ET.SubElement(parent, tag).text = _xml_safe(value)


def _set_str_if(parent: ET.Element, tag: str, value: Any) -> None:
    if value:
        ET.SubElement(parent, tag).text = _xml_safe(value)


def _set_int(parent: ET.Element, tag: str, value: Any) -> None:
    try:
        ET.SubElement(parent, tag).text = str(int(value or 0))
    except (TypeError, ValueError):
        ET.SubElement(parent, tag).text = "0"


def _set_float(parent: ET.Element, tag: str, value: Any) -> None:
    try:
        ET.SubElement(parent, tag).text = "%.6f" % float(value or 0)
    except (TypeError, ValueError):
        ET.SubElement(parent, tag).text = "%.6f" % 0.0


def _set_array(parent: ET.Element, tag: str, values: Any) -> None:
    if isinstance(values, list):
        for v in values:
            if v:
                ET.SubElement(parent, tag).text = _xml_safe(v)


def _date_only(value: str) -> str:
    return value[:10] if value else ''


def _add_ratings(root: ET.Element, ratings: Dict[str, Any]) -> None:
    elem = ET.SubElement(root, "ratings")
    for name, data in ratings.items():
        if not isinstance(data, dict):
            continue
        rating = ET.SubElement(elem, "rating")
        rating.set("name", name)
        _set_float(rating, "value", data.get("rating"))
        _set_int(rating, "votes", data.get("votes"))
        rating.set("max", "10")
        if data.get("default"):
            rating.set("default", "true")


def _add_uniqueids(root: ET.Element, default_id: str, uniqueids: Dict[str, str]) -> None:
    _set_str_if(root, "id", default_id)
    for id_type, value in uniqueids.items():
        if not value:
            continue
        elem = ET.SubElement(root, "uniqueid")
        elem.set("type", id_type)
        if value == default_id:
            elem.set("default", "true")
        elem.text = _xml_safe(value)


def _add_streamdetails(root: ET.Element, streamdetails: Dict[str, Any]) -> None:
    video = streamdetails.get("video") or []
    audio = streamdetails.get("audio") or []
    subtitle = streamdetails.get("subtitle") or []
    if not (video or audio or subtitle):
        return
    fileinfo = ET.SubElement(root, "fileinfo")
    sd = ET.SubElement(fileinfo, "streamdetails")
    for v in video:
        stream = ET.SubElement(sd, "video")
        _set_str(stream, "codec", v.get("codec"))
        _set_float(stream, "aspect", v.get("aspect"))
        _set_int(stream, "width", v.get("width"))
        _set_int(stream, "height", v.get("height"))
        _set_int(stream, "durationinseconds", v.get("duration"))
        _set_str(stream, "stereomode", v.get("stereomode"))
        _set_str(stream, "hdrtype", v.get("hdrtype"))
    for a in audio:
        stream = ET.SubElement(sd, "audio")
        _set_str(stream, "codec", a.get("codec"))
        _set_str(stream, "language", a.get("language"))
        _set_int(stream, "channels", a.get("channels"))
    for s in subtitle:
        stream = ET.SubElement(sd, "subtitle")
        _set_str(stream, "language", s.get("language"))


def _add_cast(root: ET.Element, cast: List[Dict[str, Any]]) -> None:
    for member in cast:
        if not isinstance(member, dict):
            continue
        actor = ET.SubElement(root, "actor")
        _set_str(actor, "name", member.get("name"))
        _set_str(actor, "role", member.get("role"))
        _set_int(actor, "order", member.get("order"))
        thumb = member.get("thumbnail")
        if thumb:
            _set_str(actor, "thumb", decode_image_url(thumb))


def _fetch_set_overview(setid: Any) -> str:
    """The set overview lives on the set, not the movie, so resolve it by setid."""
    try:
        sid = int(setid)
    except (TypeError, ValueError):
        return ""
    if sid <= 0:
        return ""
    details = get_item_details('set', sid, ['plot'])
    if isinstance(details, dict):
        return details.get('plot') or ""
    return ""


def _build_root(media_type: str, d: Dict[str, Any], include_watched: bool = True) -> ET.Element:
    """Serialize details into an NFO root element in Kodi's exact field order."""
    tag = _ROOT_TAG[media_type]
    root = ET.Element(tag)
    is_episode_like = tag in ("episodedetails", "tvshow")

    _set_str(root, "title", d.get("title"))
    _set_str_if(root, "originaltitle", d.get("originaltitle"))
    _set_str_if(root, "showtitle", d.get("showtitle"))
    _set_str_if(root, "sorttitle", d.get("sorttitle"))

    ratings = d.get("ratings")
    if isinstance(ratings, dict) and ratings:
        _add_ratings(root, ratings)

    _set_int(root, "userrating", d.get("userrating"))
    _set_int(root, "top250", d.get("top250"))

    if is_episode_like:
        _set_int(root, "season", d.get("season"))
        _set_int(root, "episode", d.get("episode"))
        _set_int(root, "displayseason", d.get("specialsortseason", -1))
        _set_int(root, "displayepisode", d.get("specialsortepisode", -1))
    if media_type == "musicvideo":
        _set_int(root, "track", d.get("track"))
        _set_str_if(root, "album", d.get("album"))

    _set_str_if(root, "outline", d.get("plotoutline"))
    _set_str_if(root, "plot", d.get("plot"))
    _set_str_if(root, "tagline", d.get("tagline"))
    _set_int(root, "runtime", int(d.get("runtime") or 0) // 60)
    _set_str_if(root, "mpaa", d.get("mpaa"))
    if include_watched:
        _set_int(root, "playcount", d.get("playcount"))
        _set_str_if(root, "lastplayed", _date_only(d.get("lastplayed", "")))

    episodeguide = d.get("episodeguide")
    if episodeguide:
        _set_str(root, "episodeguide", episodeguide)

    _add_uniqueids(root, d.get("imdbnumber", ""), d.get("uniqueid") or {})
    _set_array(root, "genre", d.get("genre"))
    _set_array(root, "country", d.get("country"))

    set_name = d.get("set")
    if set_name:
        set_elem = ET.SubElement(root, "set")
        _set_str(set_elem, "name", set_name)
        _set_str_if(set_elem, "overview", _fetch_set_overview(d.get("setid")))

    _set_array(root, "tag", d.get("tag"))
    _set_array(root, "credits", d.get("writer"))
    _set_array(root, "director", d.get("director"))
    _set_str_if(root, "premiered", d.get("premiered"))
    if d.get("year"):
        _set_int(root, "year", d.get("year"))
    _set_str_if(root, "status", d.get("status"))
    _set_str_if(root, "code", d.get("productioncode"))
    if d.get("firstaired"):
        _set_str(root, "aired", _date_only(d.get("firstaired", "")))
    _set_array(root, "studio", d.get("studio"))
    _set_str_if(root, "trailer", d.get("trailer"))

    _add_streamdetails(root, d.get("streamdetails") or {})
    _add_cast(root, d.get("cast") or [])
    _set_array(root, "artist", d.get("artist"))
    _set_array(root, "showlink", d.get("showlink"))

    resume = d.get("resume")
    if isinstance(resume, dict):
        resume_elem = ET.SubElement(root, "resume")
        _set_float(resume_elem, "position", resume.get("position"))
        _set_float(resume_elem, "total", resume.get("total"))

    _set_str_if(root, "dateadded", d.get("dateadded"))

    return root


def _merge_preserve(fresh: ET.Element, existing: ET.Element) -> None:
    """Append elements from `existing` whose tag the fresh write did not emit."""
    emitted = {child.tag for child in fresh}
    for child in list(existing):
        if child.tag not in emitted:
            fresh.append(child)


def _indent(elem: ET.Element, level: int = 0) -> None:
    """In-place pretty-print (ET.indent backport for Python 3.8)."""
    pad = "\n" + "    " * level
    if len(elem):
        if not (elem.text or "").strip():
            elem.text = pad + "    "
        for child in elem:
            _indent(child, level + 1)
            if not (child.tail or "").strip():
                child.tail = pad + "    "
        if not (elem[-1].tail or "").strip():
            elem[-1].tail = pad
    elif level and not (elem.tail or "").strip():
        elem.tail = pad


def _read_existing(path: str) -> Optional[ET.Element]:
    try:
        with xbmcvfs.File(path) as f:
            content = f.read()
        if content:
            return ET.fromstring(content)
    except Exception as e:
        log("Editor", f"NFO: failed to read existing {path}: {e}", xbmc.LOGWARNING)
    return None


def _write(path: str, root: ET.Element) -> bool:
    _indent(root)
    body = ET.tostring(root, encoding="unicode")
    content = '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n' + body + '\n'
    try:
        with xbmcvfs.File(path, 'w') as f:
            return bool(f.write(content))
    except Exception as e:
        log("Editor", f"NFO: failed to write {path}: {e}", xbmc.LOGERROR)
        return False


def _write_one(path: str, media_type: str, details: Dict[str, Any],
               include_watched: bool, force_create: bool = False) -> bool:
    existing = _read_existing(path) if xbmcvfs.exists(path) else None
    if existing is None and not force_create and not ADDON.getSettingBool('nfo.create_missing'):
        return False
    root = _build_root(media_type, details, include_watched)
    if existing is not None:
        _merge_preserve(root, existing)
    return _write(path, root)


def write_nfo(media_type: str, dbid: int, forced: bool = False) -> bool:
    """Write/update the NFO for a library item, matching Kodi's export fields.

    Gated by the `nfo.write_on_edit` setting unless `forced`. Returns True on write.
    """
    if not forced and not ADDON.getSettingBool('nfo.write_on_edit'):
        return False
    if media_type not in _ROOT_TAG:
        return False

    details = get_item_details(media_type, dbid, _NFO_PROPERTIES[media_type])
    if not isinstance(details, dict):
        log("Editor", f"NFO: no details for {media_type} {dbid}", xbmc.LOGWARNING)
        return False

    media_file = details.get("file", "")
    path = _nfo_path(media_type, media_file)
    if not path:
        log("Editor", f"NFO: no path for {media_type} {dbid}", xbmc.LOGWARNING)
        return False

    include_watched = ADDON.getSettingBool('nfo.write_watched_state')

    targets: List[Tuple[str, str]] = [(path, media_type)]
    # Movies also support a sibling movie.nfo; update it only if it already exists.
    if media_type == "movie":
        slash = max(media_file.rfind('/'), media_file.rfind('\\'))
        if slash != -1:
            alt = media_file[:slash + 1] + "movie.nfo"
            if alt != path and xbmcvfs.exists(alt):
                targets.append((alt, media_type))

    wrote = False
    for target_path, target_type in targets:
        if _write_one(target_path, target_type, details, include_watched, force_create=forced):
            wrote = True
            log("Editor", f"NFO: wrote {target_path}", xbmc.LOGDEBUG)
    return wrote
