"""Validation and formatting utilities for metadata editor."""
from __future__ import annotations

import re
from datetime import date
from typing import Any, Final

from lib.kodi.client import ADDON
from lib.kodi.formatters import format_rating
from lib.editor.config import FieldType


_INVALID: Final = -1  # below every range check's lower bound


def _range_check(value: float, lo: float, hi: float, error: str) -> tuple[bool, str]:
    """Return (True, '') if value is in [lo, hi], else (False, error)."""
    if lo <= value <= hi:
        return True, ""
    return False, error


def validate_date(value: str) -> tuple[bool, str]:
    """Validate a YYYY-MM-DD date; an empty value passes as unset."""
    if not value:
        return True, ""

    if not re.match(r"^\d{4}-\d{2}-\d{2}$", value):
        return False, ADDON.getLocalizedString(32724)

    year, month, day = map(int, value.split("-"))
    if year < 1800 or year > 2100:
        return False, ADDON.getLocalizedString(32018)
    try:
        date(year, month, day)
    except ValueError:
        return False, ADDON.getLocalizedString(32725)

    return True, ""


def normalize_date(value: str) -> str:
    """Normalize YYYY-first date input to YYYY-MM-DD; anything else is returned unchanged."""
    value = value.strip()
    match = re.match(r"^(\d{4})[-/. ](\d{1,2})[-/. ](\d{1,2})$", value)
    if not match:
        return value
    year, month, day = match.groups()
    return f"{year}-{int(month):02d}-{int(day):02d}"


def validate_year(value: int) -> tuple[bool, str]:
    """Validate year value (0 means unset and is allowed)."""
    if value == 0:
        return True, ""
    return _range_check(value, 1800, 2100, ADDON.getLocalizedString(32018))


def validate_runtime(value: int) -> tuple[bool, str]:
    """Validate runtime in seconds."""
    return _range_check(value, 0, 86400 * 7, ADDON.getLocalizedString(32021))


def validate_duration(value: int) -> tuple[bool, str]:
    """Validate duration in seconds."""
    return _range_check(value, 0, 86400 * 7, ADDON.getLocalizedString(32034))


def parse_rating(text: str) -> float:
    """Parse rating text as a float, comma decimal separator accepted."""
    try:
        return float(text.strip().replace(",", "."))
    except ValueError:
        return _INVALID


def validate_rating(value: float) -> tuple[bool, str]:
    """Validate rating 0-10."""
    return _range_check(value, 0, 10, ADDON.getLocalizedString(32005))


def validate_top250(value: int) -> tuple[bool, str]:
    """Validate top 250 position."""
    return _range_check(value, 0, 250, ADDON.getLocalizedString(32026))


def format_runtime_display(seconds: int) -> str:
    """Format runtime seconds for display."""
    if not seconds:
        return ADDON.getLocalizedString(32392)

    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60

    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def format_runtime_for_edit(seconds: int) -> str:
    """Format runtime seconds as minutes for editing."""
    if not seconds:
        return ""
    return str(seconds // 60)


def parse_runtime_from_edit(minutes_str: str) -> int:
    """Parse a minutes string as runtime seconds."""
    if not minutes_str:
        return 0
    try:
        return int(minutes_str) * 60
    except ValueError:
        return _INVALID


def format_duration_for_edit(seconds: int) -> str:
    """Format duration seconds as MM:SS for editing."""
    if not seconds:
        return "0:00"
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}:{secs:02d}"


def parse_duration_from_edit(text: str) -> int:
    """Parse MM:SS, H:MM:SS or plain seconds as duration seconds."""
    if not text:
        return 0
    text = text.strip()
    try:
        if ':' in text:
            parts = text.split(':')
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        return int(text)
    except ValueError:
        return _INVALID


def format_list_display(values: list[str] | None, max_items: int = 3) -> str:
    """Format list values for the menu, the first few then a count of the rest."""
    if not values:
        return ADDON.getLocalizedString(32392)

    if len(values) <= max_items:
        return ", ".join(values)

    shown = ", ".join(values[:max_items])
    return f"{shown} {ADDON.getLocalizedString(32729).format(len(values) - max_items)}"


def format_userrating_display(value: int) -> str:
    """Format user rating for display."""
    if not value:
        return f"({ADDON.getLocalizedString(32391)})"
    return f"{value}/10"


def format_uniqueids_display(uniqueids: dict[str, Any] | None) -> str:
    """Format unique IDs as 'type value' pairs."""
    if not uniqueids:
        return ADDON.getLocalizedString(32392)
    parts = [f"{id_type} {value}" for id_type, value in uniqueids.items() if value]
    return ", ".join(parts) if parts else ADDON.getLocalizedString(32392)


def format_ratings_display(ratings: dict[str, Any] | None) -> str:
    """Format external ratings for display, the first three sources only."""
    if not ratings:
        return ADDON.getLocalizedString(32392)

    parts = []
    for source, data in ratings.items():
        if isinstance(data, dict):
            rating = data.get("rating", 0)
            parts.append(f"{source}: {format_rating(rating)}")
        else:
            parts.append(f"{source}: {data}")

    if not parts:
        return ADDON.getLocalizedString(32392)

    return ", ".join(parts[:3])


_MENU_TEXT_TRUNCATE_LEN: Final = 50


def format_value_for_display(value: Any, field_type: FieldType) -> str:
    """Format a field value for menu display based on type."""
    if not value:
        return ADDON.getLocalizedString(32392)

    if field_type == FieldType.TEXT or field_type == FieldType.TEXT_LONG:
        text = str(value)
        if len(text) > _MENU_TEXT_TRUNCATE_LEN:
            return text[:_MENU_TEXT_TRUNCATE_LEN - 3] + "..."
        return text

    if field_type == FieldType.INTEGER:
        return str(value)

    if field_type == FieldType.DATE:
        return str(value)

    if field_type == FieldType.LIST:
        return format_list_display(value)

    if field_type == FieldType.USERRATING:
        return format_userrating_display(value)

    if field_type == FieldType.RATINGS:
        return format_ratings_display(value)

    if field_type == FieldType.STATUS:
        return str(value).title()

    if field_type == FieldType.UNIQUEIDS:
        return format_uniqueids_display(value)

    return str(value)
