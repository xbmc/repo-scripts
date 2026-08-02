"""Validation and formatting utilities for metadata editor."""
from __future__ import annotations

import re
from typing import Any

from lib.editor.config import FieldType


def _range_check(value: float, lo: float, hi: float, error: str) -> tuple[bool, str]:
    """Return (True, '') if value is in [lo, hi], else (False, error)."""
    if lo <= value <= hi:
        return True, ""
    return False, error


def validate_date(value: str) -> tuple[bool, str]:
    """Validate YYYY-MM-DD date format."""
    if not value:
        return True, ""

    if not re.match(r"^\d{4}-\d{2}-\d{2}$", value):
        return False, "Invalid date format (use YYYY-MM-DD)"

    try:
        year, month, day = map(int, value.split("-"))
        if not (1 <= month <= 12):
            return False, "Month must be 1-12"
        if not (1 <= day <= 31):
            return False, "Day must be 1-31"
        if year < 1800 or year > 2100:
            return False, "Year seems invalid"
    except ValueError:
        return False, "Invalid date"

    return True, ""


def normalize_date(value: str) -> str:
    """Normalize unambiguous YYYY-first date input to YYYY-MM-DD.

    Accepts `/`, `.` or space separators and single-digit month/day. Ambiguous or
    unrecognized input (DD/MM/YYYY, bare year, month names) is returned unchanged so
    validate_date rejects it rather than guessing.
    """
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
    return _range_check(value, 1800, 2100, "Year must be between 1800 and 2100")


def validate_runtime(value: int) -> tuple[bool, str]:
    """Validate runtime in seconds."""
    return _range_check(value, 0, 86400 * 7, "Runtime must be 0 to 7 days")


def validate_rating(value: float) -> tuple[bool, str]:
    """Validate rating 0-10."""
    return _range_check(value, 0, 10, "Rating must be 0-10")


def validate_top250(value: int) -> tuple[bool, str]:
    """Validate top 250 position."""
    return _range_check(value, 0, 250, "Top 250 must be 0-250")


def format_runtime_display(seconds: int) -> str:
    """Format runtime seconds for display."""
    if not seconds:
        return "(not set)"

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
    """Parse minutes string to runtime seconds."""
    if not minutes_str:
        return 0
    try:
        minutes = int(minutes_str)
        return minutes * 60
    except ValueError:
        return 0


def format_duration_for_edit(seconds: int) -> str:
    """Format duration seconds as MM:SS for editing."""
    if not seconds:
        return "0:00"
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}:{secs:02d}"


def parse_duration_from_edit(text: str) -> int:
    """Parse MM:SS or plain seconds string to duration seconds."""
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
        return 0


def format_list_display(values: list[str] | None, max_items: int = 3) -> str:
    """Format list values for display in menu."""
    if not values:
        return "(not set)"

    if len(values) <= max_items:
        return ", ".join(values)

    shown = ", ".join(values[:max_items])
    return f"{shown} (+{len(values) - max_items} more)"


def format_userrating_display(value: int) -> str:
    """Format user rating for display."""
    if not value:
        return "(not rated)"
    return f"{value}/10"


def format_uniqueids_display(uniqueids: dict[str, Any] | None) -> str:
    """Format unique IDs as 'type value' pairs."""
    if not uniqueids:
        return "(not set)"
    parts = [f"{id_type} {value}" for id_type, value in uniqueids.items() if value]
    return ", ".join(parts) if parts else "(not set)"


def format_ratings_display(ratings: dict[str, Any] | None) -> str:
    """Format external ratings dict for display."""
    if not ratings:
        return "(no ratings)"

    parts = []
    for source, data in ratings.items():
        if isinstance(data, dict):
            rating = data.get("rating", 0)
            parts.append(f"{source}: {rating:.1f}")
        else:
            parts.append(f"{source}: {data}")

    if not parts:
        return "(no ratings)"

    return ", ".join(parts[:3])


_MENU_TEXT_TRUNCATE_LEN = 50


def format_value_for_display(value: Any, field_type: FieldType) -> str:
    """Format a field value for menu display based on type."""
    if not value:
        return "(not set)"

    if field_type == FieldType.TEXT or field_type == FieldType.TEXT_LONG:
        text = str(value)
        if len(text) > _MENU_TEXT_TRUNCATE_LEN:
            return text[:_MENU_TEXT_TRUNCATE_LEN - 3] + "..."
        return text

    if field_type == FieldType.INTEGER:
        return str(value)

    if field_type == FieldType.NUMBER:
        return f"{value:.1f}"

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
