"""Field definitions and media type configuration for metadata editor."""
from __future__ import annotations

from enum import Enum
from typing import TypedDict

import xbmc

from lib.kodi.client import ADDON


class FieldType(Enum):
    """Types of editable fields."""

    TEXT = "text"
    TEXT_LONG = "text_long"
    INTEGER = "integer"
    NUMBER = "number"
    DATE = "date"
    DATETIME = "datetime"
    LIST = "list"
    USERRATING = "userrating"
    RATINGS = "ratings"
    STATUS = "status"
    UNIQUEIDS = "uniqueids"


class FieldDef(TypedDict):
    """Definition for an editable field.

    `display_name` resolves at render time: an int in 32000-32999 is our string,
    any other int is a Kodi core string, a str is used verbatim.
    """

    api_name: str
    display_name: int | str
    field_type: FieldType
    category: str
    get_property: str


CATEGORY_CORE_TEXT = "Core Text"
CATEGORY_DATES_NUMBERS = "Dates & Numbers"
CATEGORY_LISTS = "Lists"
CATEGORY_RATINGS = "Ratings"
CATEGORY_IDS = "IDs"

def field(api: str, display: int | str, ftype: FieldType, category: str) -> FieldDef:
    """Build a FieldDef. `get_property` always mirrors `api`."""
    return {
        "api_name": api,
        "display_name": display,
        "field_type": ftype,
        "category": category,
        "get_property": api,
    }


def get_display_name(field_def: FieldDef) -> str:
    """Field label: str verbatim (Kodi terminology), 32000-32999 is ours, else a core string."""
    name = field_def["display_name"]
    if isinstance(name, str):
        return name
    if 32000 <= name <= 32999:
        return ADDON.getLocalizedString(name)
    return xbmc.getLocalizedString(name)


FIELD_DEFINITIONS: dict[str, FieldDef] = {
    # Core Text
    "title": field("title", 369, FieldType.TEXT, CATEGORY_CORE_TEXT),
    "artist": field("artist", 557, FieldType.TEXT, CATEGORY_CORE_TEXT),
    "plot": field("plot", 207, FieldType.TEXT_LONG, CATEGORY_CORE_TEXT),
    "tagline": field("tagline", 202, FieldType.TEXT, CATEGORY_CORE_TEXT),
    "sorttitle": field("sorttitle", 171, FieldType.TEXT, CATEGORY_CORE_TEXT),
    "sortname": field("sortname", 32674, FieldType.TEXT, CATEGORY_CORE_TEXT),
    "description": field("description", 21821, FieldType.TEXT_LONG, CATEGORY_CORE_TEXT),
    "disambiguation": field("disambiguation", 39026, FieldType.TEXT, CATEGORY_CORE_TEXT),
    "displayartist": field("displayartist", 32670, FieldType.TEXT, CATEGORY_CORE_TEXT),
    "sortartist": field("sortartist", 32671, FieldType.TEXT, CATEGORY_CORE_TEXT),
    "albumlabel": field("albumlabel", 32672, FieldType.TEXT, CATEGORY_CORE_TEXT),
    "comment": field("comment", 569, FieldType.TEXT_LONG, CATEGORY_CORE_TEXT),
    "disctitle": field("disctitle", 38076, FieldType.TEXT, CATEGORY_CORE_TEXT),
    "originaltitle": field("originaltitle", 20376, FieldType.TEXT, CATEGORY_CORE_TEXT),
    # Dates Numbers
    "year": field("year", 562, FieldType.INTEGER, CATEGORY_DATES_NUMBERS),
    "premiered": field("premiered", 20473, FieldType.DATE, CATEGORY_DATES_NUMBERS),
    "firstaired": field("firstaired", 20416, FieldType.DATE, CATEGORY_DATES_NUMBERS),
    "runtime": field("runtime", 2050, FieldType.INTEGER, CATEGORY_DATES_NUMBERS),
    "mpaa": field("mpaa", 20074, FieldType.TEXT, CATEGORY_DATES_NUMBERS),
    "born": field("born", 21893, FieldType.TEXT, CATEGORY_DATES_NUMBERS),
    "formed": field("formed", 21894, FieldType.TEXT, CATEGORY_DATES_NUMBERS),
    "died": field("died", 21897, FieldType.TEXT, CATEGORY_DATES_NUMBERS),
    "disbanded": field("disbanded", 21896, FieldType.TEXT, CATEGORY_DATES_NUMBERS),
    "artisttype": field("type", 564, FieldType.TEXT, CATEGORY_DATES_NUMBERS),
    "gender": field("gender", 39025, FieldType.TEXT, CATEGORY_DATES_NUMBERS),
    "top250": field("top250", 13409, FieldType.INTEGER, CATEGORY_DATES_NUMBERS),
    "track": field("track", 554, FieldType.INTEGER, CATEGORY_DATES_NUMBERS),
    "disc": field("disc", 427, FieldType.INTEGER, CATEGORY_DATES_NUMBERS),
    "duration": field("duration", 180, FieldType.INTEGER, CATEGORY_DATES_NUMBERS),
    "bpm": field("bpm", 38080, FieldType.INTEGER, CATEGORY_DATES_NUMBERS),
    "releasedate": field("releasedate", 172, FieldType.TEXT, CATEGORY_DATES_NUMBERS),
    "originaldate": field("originaldate", 38079, FieldType.TEXT, CATEGORY_DATES_NUMBERS),
    "albumtype": field("type", 32673, FieldType.TEXT, CATEGORY_DATES_NUMBERS),
    # Lists
    "genre": field("genre", 515, FieldType.LIST, CATEGORY_LISTS),
    "studio": field("studio", 572, FieldType.LIST, CATEGORY_LISTS),
    "director": field("director", 20339, FieldType.LIST, CATEGORY_LISTS),
    "writer": field("writer", 20417, FieldType.LIST, CATEGORY_LISTS),
    "country": field("country", 21875, FieldType.LIST, CATEGORY_LISTS),
    "tag": field("tag", 20459, FieldType.LIST, CATEGORY_LISTS),
    "style": field("style", 176, FieldType.LIST, CATEGORY_LISTS),
    "mood": field("mood", 175, FieldType.LIST, CATEGORY_LISTS),
    "songmood": field("mood", 175, FieldType.LIST, CATEGORY_LISTS),
    "instrument": field("instrument", 21892, FieldType.LIST, CATEGORY_LISTS),
    "yearsactive": field("yearsactive", 21898, FieldType.LIST, CATEGORY_LISTS),
    "theme": field("theme", 21895, FieldType.LIST, CATEGORY_LISTS),
    "artistlist": field("artist", 557, FieldType.LIST, CATEGORY_LISTS),
    # Ratings
    "userrating": field("userrating", 32668, FieldType.USERRATING, CATEGORY_RATINGS),
    "ratings": field("ratings", 32669, FieldType.RATINGS, CATEGORY_RATINGS),
    # IDs
    "uniqueid": field("uniqueid", "Unique IDs", FieldType.UNIQUEIDS, CATEGORY_IDS),
    # Dates Numbers
    "status": field("status", 126, FieldType.STATUS, CATEGORY_DATES_NUMBERS),
    "playcount": field("playcount", 567, FieldType.INTEGER, CATEGORY_DATES_NUMBERS),
    "lastplayed": field("lastplayed", 568, FieldType.DATETIME, CATEGORY_DATES_NUMBERS),
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
    """Get list of editable fields for a media type.

    tvshow `status` is included only on Kodi builds that can read it back (xbmc/xbmc#28520);
    older builds reject it on Get, so exposing it would break the field's load/preselect.
    """
    fields = list(MEDIA_TYPE_FIELDS.get(media_type, []))
    if media_type == "tvshow":
        from lib.kodi.utilities import tvshow_status_gettable
        if tvshow_status_gettable():
            idx = fields.index("mpaa") + 1 if "mpaa" in fields else len(fields)
            fields.insert(idx, "status")
    return fields


def get_field_def(field_name: str) -> FieldDef | None:
    """Get field definition by name."""
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
            prop = field_def["get_property"]
            if prop not in properties and prop not in unrequestable:
                properties.append(prop)
    return properties


# Validate at module load that every name in MEDIA_TYPE_FIELDS exists in FIELD_DEFINITIONS.
for _mt, _fields in MEDIA_TYPE_FIELDS.items():
    for _f in _fields:
        if _f not in FIELD_DEFINITIONS:
            raise ValueError(
                f"MEDIA_TYPE_FIELDS[{_mt!r}] references unknown field {_f!r}"
            )
