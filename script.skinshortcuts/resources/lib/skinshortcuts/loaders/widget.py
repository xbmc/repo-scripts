"""Widget loader."""

from __future__ import annotations

from pathlib import Path

from ..constants import TARGET_MAP
from ..exceptions import WidgetConfigError
from ..log import get_logger, notify
from ..models import Content, Widget, WidgetGroup
from ..models.widget import WidgetConfig
from .base import get_attr, get_bool, get_int, get_text, parse_content, parse_xml

log = get_logger("WidgetLoader")


def load_widgets(path: str | Path) -> WidgetConfig:
    """Load widget configuration from XML file.

    Parses <widget>, <group>, and <content> elements directly from the root
    <widgets> element. Widgets at root level appear flat in picker, groups
    create nested navigation, and root-level <content> resolves dynamically.

    Returns:
        WidgetConfig containing widgets, groupings, and settings.
    """
    path = Path(path)
    if not path.exists():
        return WidgetConfig()

    root = parse_xml(path, "widgets", WidgetConfigError)

    widgets: list[Widget] = []
    groupings: list[WidgetGroup | Widget | Content] = []

    for child in root:
        if child.tag == "widget":
            widget = _parse_widget(child, str(path))
            widgets.append(widget)
            groupings.append(widget)
        elif child.tag == "group":
            group = _parse_widget_group(child, str(path))
            if group:
                groupings.append(group)
        elif child.tag == "content":
            content = parse_content(child)
            if content:
                groupings.append(content)

    return WidgetConfig(
        widgets=widgets,
        groupings=groupings,
    )


def _parse_widget(elem, path: str, default_source: str = "") -> Widget:
    widget_name = get_attr(elem, "name")
    if not widget_name:
        raise WidgetConfigError(path, "Widget missing 'name' attribute")

    label = get_attr(elem, "label")
    if not label:
        raise WidgetConfigError(path, f"Widget '{widget_name}' missing 'label' attribute")

    widget_type = get_attr(elem, "type") or ""
    widget_path = get_text(elem, "path") or ""

    if not widget_path and widget_type != "custom":
        raise WidgetConfigError(path, f"Widget '{widget_name}' missing <path>")

    source = get_attr(elem, "source") or default_source

    raw_target = get_attr(elem, "target") or "videos"
    target = TARGET_MAP.get(raw_target.lower(), raw_target)

    browse = get_bool(elem, "browse")

    return Widget(
        name=widget_name,
        label=label,
        path=widget_path,
        type=widget_type,
        target=target,
        icon=get_attr(elem, "icon") or "",
        condition=get_attr(elem, "condition") or "",
        visible=get_attr(elem, "visible") or "",
        limit=get_int(elem, "limit"),
        sort_by=get_text(elem, "sortby") or "",
        sort_order=get_text(elem, "sortorder") or "",
        source=source,
        slot=get_attr(elem, "slot") or "",
        browse=browse,
    )


def _parse_widget_group(elem, path: str, default_source: str = "") -> WidgetGroup | None:
    """Parse a widget group element (supports nested groups, widgets, and content)."""
    group_name = get_attr(elem, "name")
    label = get_attr(elem, "label")
    flat = get_bool(elem, "flat")

    if not group_name:
        log.warning(f"Widget group in {path} missing 'name' attribute")
        notify("Widget Group Error", "Group missing 'name' (see log)")
        return None
    if not label and not flat:
        log.warning(f"Widget group '{group_name}' in {path} missing 'label' (required when not flat)")
        notify("Widget Group Error", f"'{group_name}' missing label")
        return None

    condition = get_attr(elem, "condition") or ""
    source = get_attr(elem, "source") or default_source
    items: list[Widget | WidgetGroup | Content] = []

    for child in elem:
        if child.tag == "widget":
            widget = _parse_widget(child, path, default_source=source)
            items.append(widget)
        elif child.tag == "group":
            nested = _parse_widget_group(child, path, default_source=source)
            if nested:
                items.append(nested)
        elif child.tag == "content":
            content = parse_content(child)
            if content:
                items.append(content)

    visible = get_attr(elem, "visible") or ""
    icon = get_attr(elem, "icon") or ""
    return WidgetGroup(
        name=group_name,
        label=label,
        condition=condition,
        visible=visible,
        icon=icon,
        items=items,
        flat=flat,
    )
