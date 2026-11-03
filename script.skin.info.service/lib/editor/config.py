"""Field definitions and media type configuration for metadata editor."""
from __future__ import annotations

from enum import Enum
from typing import TypedDict

import xbmc

from lib.kodi.client import ADDON


class FieldType(Enum):
    """Types of editable fields, each with its own edit handler and display format."""

    TEXT = "text"
    TEXT_LONG = "text_long"
    INTEGER = "integer"
    DATE = "date"
    DATETIME = "datetime"
    LIST = "list"
    USERRATING = "userrating"
    RATINGS = "ratings"
    STATUS = "status"
    UNIQUEIDS = "uniqueids"


class FieldDef(TypedDict):
    """One editable field: its JSON-RPC name, label and type."""

    api_name: str
    display_name: int | str
    field_type: FieldType


def field(api: str, display: int | str, ftype: FieldType) -> FieldDef:
    """Build a FieldDef, its label a string ID or literal text."""
    return {"api_name": api, "display_name": display, "field_type": ftype}


def get_display_name(field_def: FieldDef) -> str:
    """Get the field label: a str as-is, 32000-32999 from our strings, else Kodi's own."""
    name = field_def["display_name"]
    if isinstance(name, str):
        return name
    if 32000 <= name <= 32999:
        return ADDON.getLocalizedString(name)
    return xbmc.getLocalizedString(name)


FIELD_DEFINITIONS: dict[str, FieldDef] = {
    "title": field("title", 369, FieldType.TEXT),
    "artist": field("artist", 557, FieldType.TEXT),
    "plot": field("plot", 207, FieldType.TEXT_LONG),
    "tagline": field("tagline", 202, FieldType.TEXT),
    "sorttitle": field("sorttitle", 171, FieldType.TEXT),
    "sortname": field("sortname", 32674, FieldType.TEXT),
    "description": field("description", 21821, FieldType.TEXT_LONG),
    "disambiguation": field("disambiguation", 39026, FieldType.TEXT),
    "displayartist": field("displayartist", 32670, FieldType.TEXT),
    "sortartist": field("sortartist", 32671, FieldType.TEXT),
    "albumlabel": field("albumlabel", 32672, FieldType.TEXT),
    "comment": field("comment", 569, FieldType.TEXT_LONG),
    "disctitle": field("disctitle", 38076, FieldType.TEXT),
    "originaltitle": field("originaltitle", 20376, FieldType.TEXT),
    "year": field("year", 562, FieldType.INTEGER),
    "premiered": field("premiered", 20473, FieldType.DATE),
    "firstaired": field("firstaired", 20416, FieldType.DATE),
    "runtime": field("runtime", 2050, FieldType.INTEGER),
    "mpaa": field("mpaa", 20074, FieldType.TEXT),
    "born": field("born", 21893, FieldType.TEXT),
    "formed": field("formed", 21894, FieldType.TEXT),
    "died": field("died", 21897, FieldType.TEXT),
    "disbanded": field("disbanded", 21896, FieldType.TEXT),
    "artisttype": field("type", 564, FieldType.TEXT),
    "gender": field("gender", 39025, FieldType.TEXT),
    "top250": field("top250", 13409, FieldType.INTEGER),
    "track": field("track", 554, FieldType.INTEGER),
    "disc": field("disc", 427, FieldType.INTEGER),
    "duration": field("duration", 180, FieldType.INTEGER),
    "bpm": field("bpm", 38080, FieldType.INTEGER),
    "releasedate": field("releasedate", 172, FieldType.TEXT),
    "originaldate": field("originaldate", 38079, FieldType.TEXT),
    "albumtype": field("type", 32673, FieldType.TEXT),
    "genre": field("genre", 515, FieldType.LIST),
    "studio": field("studio", 572, FieldType.LIST),
    "director": field("director", 20339, FieldType.LIST),
    "writer": field("writer", 20417, FieldType.LIST),
    "country": field("country", 21875, FieldType.LIST),
    "tag": field("tag", 20459, FieldType.LIST),
    "style": field("style", 176, FieldType.LIST),
    "mood": field("mood", 175, FieldType.LIST),
    "songmood": field("mood", 175, FieldType.LIST),
    "instrument": field("instrument", 21892, FieldType.LIST),
    "yearsactive": field("yearsactive", 21898, FieldType.LIST),
    "theme": field("theme", 21895, FieldType.LIST),
    "artistlist": field("artist", 557, FieldType.LIST),
    "userrating": field("userrating", 32668, FieldType.USERRATING),
    "ratings": field("ratings", 32669, FieldType.RATINGS),
    "uniqueid": field("uniqueid", "Unique IDs", FieldType.UNIQUEIDS),
    "status": field("status", 126, FieldType.STATUS),
    "playcount": field("playcount", 567, FieldType.INTEGER),
    "lastplayed": field("lastplayed", 568, FieldType.DATETIME),
}

MEDIA_TYPE_FIELDS: dict[str, list[str]] = {
    "movie": [
        "title",
        "plot",
        "tagline",
        "sorttitle",
        "originaltitle",
        "year",
        "premiered",
        "runtime",
        "mpaa",
        "top250",
        "genre",
        "studio",
        "director",
        "writer",
        "country",
        "tag",
        "playcount",
        "lastplayed",
        "userrating",
        "ratings",
        "uniqueid",
    ],
    "tvshow": [
        "title",
        "plot",
        "sorttitle",
        "originaltitle",
        "premiered",
        "runtime",
        "mpaa",
        "genre",
        "studio",
        "tag",
        "userrating",
        "ratings",
        "uniqueid",
    ],
    "episode": [
        "title",
        "plot",
        "originaltitle",
        "firstaired",
        "runtime",
        "director",
        "writer",
        "playcount",
        "lastplayed",
        "userrating",
        "ratings",
        "uniqueid",
    ],
    "season": [
        "title",
        "userrating",
    ],
    "musicvideo": [
        "title",
        "plot",
        "year",
        "premiered",
        "runtime",
        "genre",
        "studio",
        "director",
        "tag",
        "playcount",
        "lastplayed",
        "userrating",
        "uniqueid",
    ],
    "set": [
        "title",
        "plot",
    ],
    "artist": [
        "artist",
        "sortname",
        "description",
        "disambiguation",
        "born",
        "formed",
        "died",
        "disbanded",
        "artisttype",
        "gender",
        "genre",
        "style",
        "mood",
        "instrument",
        "yearsactive",
    ],
    "album": [
        "title",
        "description",
        "displayartist",
        "sortartist",
        "albumlabel",
        "albumtype",
        "year",
        "releasedate",
        "originaldate",
        "genre",
        "theme",
        "mood",
        "style",
        "artistlist",
        "userrating",
    ],
    "song": [
        "title",
        "displayartist",
        "sortartist",
        "comment",
        "songmood",
        "disctitle",
        "year",
        "track",
        "disc",
        "duration",
        "releasedate",
        "originaldate",
        "bpm",
        "genre",
        "artistlist",
        "userrating",
        "playcount",
        "lastplayed",
    ],
}

TVSHOW_STATUS_VALUES = [
    "",
    "returning series",
    "in production",
    "planned",
    "cancelled",
    "ended",
]


def get_fields_for_media_type(media_type: str) -> list[str]:
    """Get the editable fields for a media type; tvshow status only where Kodi can read it back."""
    fields = list(MEDIA_TYPE_FIELDS.get(media_type, []))
    if media_type == "tvshow":
        from lib.kodi.utilities import tvshow_status_gettable
        if tvshow_status_gettable():
            idx = fields.index("mpaa") + 1 if "mpaa" in fields else len(fields)
            fields.insert(idx, "status")
    return fields


def get_field_def(field_name: str) -> FieldDef | None:
    """Get a field's definition, None for a name the editor does not know."""
    return FIELD_DEFINITIONS.get(field_name)


# imdbnumber fetched to identify default uniqueid
_DEFAULT_PROPERTIES: dict[str, list[str]] = {
    "artist": [],
    "movie": ["title", "imdbnumber"],
    "tvshow": ["title", "imdbnumber"],
}

_UNREQUESTABLE_PROPERTIES: dict[str, set[str]] = {
    "artist": {"artist"},
}


def get_properties_for_media_type(media_type: str) -> list[str]:
    """Get JSON-RPC properties to fetch for a media type."""
    properties = list(_DEFAULT_PROPERTIES.get(media_type, ["title"]))
    unrequestable = _UNREQUESTABLE_PROPERTIES.get(media_type, set())
    for field_name in get_fields_for_media_type(media_type):
        field_def = get_field_def(field_name)
        if field_def:
            prop = field_def["api_name"]
            if prop not in properties and prop not in unrequestable:
                properties.append(prop)
    return properties


for _mt, _fields in MEDIA_TYPE_FIELDS.items():
    for _f in _fields:
        if _f not in FIELD_DEFINITIONS:
            raise ValueError(
                f"MEDIA_TYPE_FIELDS[{_mt!r}] references unknown field {_f!r}"
            )
