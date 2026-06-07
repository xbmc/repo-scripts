"""Background loader."""

from __future__ import annotations

from pathlib import Path

from ..exceptions import BackgroundConfigError
from ..log import get_logger, notify
from ..models.background import (
    Background,
    BackgroundConfig,
    BackgroundGroup,
    BackgroundType,
    BrowseSource,
    PlaylistSource,
)
from .base import get_attr, get_bool, get_text, parse_content, parse_xml

log = get_logger("BackgroundLoader")

TYPE_MAP = {
    "static": BackgroundType.STATIC,
    "playlist": BackgroundType.PLAYLIST,
    "browse": BackgroundType.BROWSE,
    "multi": BackgroundType.MULTI,
    "property": BackgroundType.PROPERTY,
    "live": BackgroundType.LIVE,
    "live-playlist": BackgroundType.LIVE_PLAYLIST,
}

OPTIONAL_PATH_TYPES = {
    BackgroundType.BROWSE,
    BackgroundType.MULTI,
    BackgroundType.PLAYLIST,
    BackgroundType.LIVE_PLAYLIST,
}


def load_backgrounds(
    path: str | Path, icon_overrides: dict[str, str] | None = None
) -> BackgroundConfig:
    """Load background configuration from XML file.

    Parses <background> and <group> elements directly from root <backgrounds> element.
    Backgrounds at root level appear flat in picker, groups create nested navigation.

    Returns:
        BackgroundConfig containing backgrounds, groupings, and settings.
    """
    overrides = icon_overrides or {}
    path = Path(path)
    if not path.exists():
        return BackgroundConfig()

    root = parse_xml(path, "backgrounds", BackgroundConfigError)

    backgrounds: list[Background] = []
    groupings: list[BackgroundGroup | Background] = []

    for child in root:
        if child.tag == "background":
            bg = _parse_background(child, str(path), overrides)
            backgrounds.append(bg)
            groupings.append(bg)
        elif child.tag == "group":
            group = _parse_background_group(child, str(path))
            if group:
                groupings.append(group)

    return BackgroundConfig(
        backgrounds=backgrounds,
        groupings=groupings,
    )


def _parse_background(
    elem, path: str, icon_overrides: dict[str, str] | None = None
) -> Background:
    bg_name = get_attr(elem, "name")
    if not bg_name:
        raise BackgroundConfigError(path, "Background missing 'name' attribute")

    label = get_attr(elem, "label")
    if not label:
        raise BackgroundConfigError(path, f"Background '{bg_name}' missing 'label' attribute")

    bg_path = get_text(elem, "path")
    type_str = get_attr(elem, "type", "static")
    bg_type = TYPE_MAP.get(type_str.lower(), BackgroundType.STATIC)

    if not bg_path and bg_type not in OPTIONAL_PATH_TYPES:
        raise BackgroundConfigError(path, f"Background '{bg_name}' missing <path>")

    if bg_path and bg_type in (BackgroundType.BROWSE, BackgroundType.MULTI) and elem.find("source") is not None:
        log.warning(
            f"Background '{bg_name}' in {path} has both <path> and <source>; ignoring <path>"
        )
        notify("Background Config", f"'{bg_name}' has both <path> and <source>")
        bg_path = ""

    sources = []
    browse_sources = []

    for source_elem in elem.findall("source"):
        source_label = get_attr(source_elem, "label", "")
        source_path = source_elem.text.strip() if source_elem.text else ""
        if not source_path:
            continue

        if bg_type in (BackgroundType.BROWSE, BackgroundType.MULTI):
            browse_sources.append(BrowseSource(
                label=source_label,
                path=source_path,
                condition=get_attr(source_elem, "condition") or "",
                visible=get_attr(source_elem, "visible") or "",
                icon=get_attr(source_elem, "icon") or "",
            ))
        else:
            overrides = icon_overrides or {}
            explicit_icon = get_attr(source_elem, "icon")
            sources.append(PlaylistSource(
                label=source_label,
                path=source_path,
                icon=explicit_icon or overrides.get("DefaultPlaylist.png", "DefaultPlaylist.png"),
            ))

    return Background(
        name=bg_name,
        label=label,
        path=bg_path or "",
        type=bg_type,
        icon=get_text(elem, "icon") or "",
        condition=get_attr(elem, "condition") or "",
        visible=get_attr(elem, "visible") or "",
        sources=sources,
        browse_sources=browse_sources,
    )


def _parse_background_group(elem, path: str) -> BackgroundGroup | None:
    """Parse a background group element (supports nested groups, backgrounds, and content)."""
    group_name = get_attr(elem, "name")
    label = get_attr(elem, "label")
    flat = get_bool(elem, "flat")

    if not group_name:
        log.warning(f"Background group in {path} missing 'name' attribute")
        notify("Background Group Error", "Group missing 'name' (see log)")
        return None
    if not label and not flat:
        log.warning(f"Background group '{group_name}' in {path} missing 'label' (required when not flat)")
        notify("Background Group Error", f"'{group_name}' missing label")
        return None

    condition = get_attr(elem, "condition") or ""
    visible = get_attr(elem, "visible") or ""
    icon = get_attr(elem, "icon") or ""
    items: list = []

    for child in elem:
        if child.tag == "background":
            bg = _parse_background(child, path)
            items.append(bg)
        elif child.tag == "group":
            nested = _parse_background_group(child, path)
            if nested:
                items.append(nested)
        elif child.tag == "content":
            content = parse_content(child)
            if content:
                items.append(content)

    return BackgroundGroup(
        name=group_name,
        label=label,
        condition=condition,
        visible=visible,
        icon=icon,
        items=items,
        flat=flat,
    )
