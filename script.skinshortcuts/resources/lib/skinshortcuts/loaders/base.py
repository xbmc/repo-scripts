"""Base loader functionality."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import TypeVar

from ..conditions import NO_SUFFIX_PROPERTIES
from ..exceptions import ConfigError
from ..log import get_logger, notify
from ..models.override import Override

log = get_logger("loaders.base")

T = TypeVar("T")

def apply_suffix_to_from(from_value: str, suffix: str) -> str:
    """Apply a suffix to a from attribute value, except for the built-in sources."""
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
    """Parse a content reference element."""
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


def parse_name_overrides(root, tag: str) -> list[Override]:
    """Parse an <overrides> section listing names the skin retired."""
    section = root.find("overrides")
    if section is None:
        return []

    overrides = []
    for elem in section.findall(tag):
        replace = get_attr(elem, "replace")
        if replace:
            overrides.append(Override(replace=replace, value=(elem.text or "").strip()))

    return overrides


def warn_duplicate_names(names: Iterable[str], kind: str, path: str, scope: str = "") -> None:
    """Warn per repeated name; lookups take one match, so a duplicate is unreachable."""
    seen: set[str] = set()
    for name in names:
        if name in seen:
            where = f" in {scope}" if scope else ""
            log.warning(
                f"{path}: {kind} '{name}' is defined more than once{where}; "
                "names must be unique"
            )
            notify("Duplicate Name", f"{kind} '{name}'{where} (see log)")
        seen.add(name)


def iter_nested(items: Iterable, item_type: type[T], group_type: type) -> Iterator[T]:
    """Every item of a type in a picker hierarchy in document order, nested groups included."""
    for item in items:
        if isinstance(item, group_type):
            yield from iter_nested(item.items, item_type, group_type)
        elif isinstance(item, item_type):
            yield item
