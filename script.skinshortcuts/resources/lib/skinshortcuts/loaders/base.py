"""Base loader functionality."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from ..exceptions import ConfigError

NO_SUFFIX_PROPERTIES = frozenset({
    "name",
    "default",
    "menu",
    "index",
    "id",
    "idprefix",
})

_PROPERTY_PATTERN = re.compile(r"([a-zA-Z_][a-zA-Z0-9_\.]*)([=~])")


def apply_suffix_transform(text: str, suffix: str) -> str:
    """Apply suffix transform to property names in conditions/from attributes.

    Transforms property names (before = or ~) but not values.
    Skips properties in NO_SUFFIX_PROPERTIES.
    """
    if not suffix or not text:
        return text

    def replace_property(match: re.Match) -> str:
        prop_name = match.group(1)
        operator = match.group(2)
        if prop_name in NO_SUFFIX_PROPERTIES:
            return f"{prop_name}{operator}"
        return f"{prop_name}{suffix}{operator}"

    return _PROPERTY_PATTERN.sub(replace_property, text)


def apply_suffix_to_from(from_value: str, suffix: str) -> str:
    """Apply suffix to a from attribute value.

    E.g., "widgetPath" -> "widgetPath.2"

    Skips built-ins like index, name, menu, id.
    """
    if not suffix or not from_value:
        return from_value

    if from_value in NO_SUFFIX_PROPERTIES:
        return from_value

    return f"{from_value}{suffix}"


def parse_xml(path: str | Path, expected_root: str, error_class: type[ConfigError]) -> ET.Element:
    """Parse XML file and validate root element."""
    path = Path(path)

    if not path.exists():
        raise error_class(str(path), "File not found")

    try:
        tree = ET.parse(str(path))
    except ET.ParseError as e:
        line = e.position[0] if e.position else None
        raise error_class(str(path), f"XML parse error: {e}", line) from e

    root = tree.getroot()
    if root.tag != expected_root:
        raise error_class(str(path), f"Expected <{expected_root}>, got <{root.tag}>")

    return root


def get_text(elem: ET.Element, child: str, default: str = "") -> str:
    """Get text content of child element."""
    child_elem = elem.find(child)
    if child_elem is not None and child_elem.text:
        return child_elem.text.strip()
    return default


def get_attr(elem: ET.Element, attr: str, default: str = "") -> str:
    """Get attribute value."""
    return (elem.get(attr) or default).strip()


def get_int(elem: ET.Element, child: str, default: int | None = None) -> int | None:
    """Get integer from child element text."""
    text = get_text(elem, child)
    if not text:
        return default
    try:
        return int(text)
    except ValueError:
        return default


def get_bool(elem: ET.Element, attr: str, default: bool = False) -> bool:
    """Get boolean from attribute value (case-insensitive 'true' match)."""
    value = elem.get(attr)
    if value is None:
        return default
    return value.strip().lower() == "true"


def parse_content(elem: ET.Element):
    """Parse a content reference element.

    Attributes: source, target, path, condition, visible, icon, label, folder

    Returns:
        Content object or None if source is missing
    """
    # Import here to avoid circular dependency
    from ..models.menu import Content

    source = get_attr(elem, "source")
    if not source:
        return None

    return Content(
        source=source,
        target=get_attr(elem, "target") or "",
        path=get_attr(elem, "path") or "",
        condition=get_attr(elem, "condition") or "",
        visible=get_attr(elem, "visible") or "",
        icon=get_attr(elem, "icon") or "",
        label=get_attr(elem, "label") or "",
        folder=get_attr(elem, "folder") or "",
    )
