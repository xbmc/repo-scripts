"""Widget loader."""

from __future__ import annotations

from pathlib import Path

from ..constants import TARGET_MAP
from ..exceptions import WidgetConfigError
from ..log import notify
from ..models.menu import Content
from ..models.widget import Widget, WidgetConfig, WidgetGroup
from .base import (
    get_attr,
    get_bool,
    get_int,
    get_text,
    iter_nested,
    parse_content,
    parse_name_overrides,
    parse_xml,
    report_missing,
    warn_duplicate_names,
)


def load_widgets(path: str | Path) -> WidgetConfig:
    """Load widget configuration from XML file."""
    path = Path(path)
    if not path.exists():
        return WidgetConfig()

    root = parse_xml(path, "widgets", WidgetConfigError)

    widgets: list[Widget] = []
    groupings: list[WidgetGroup | Widget | Content] = []

    for child in root:
        if child.tag == "widget":
            widget = _parse_widget(child, str(path))
            if widget:
                widgets.append(widget)
                groupings.append(widget)
        elif child.tag == "group":
            group = _parse_widget_group(child, str(path))
            if group:
                groupings.append(group)
        elif child.tag == "content":
            content = parse_content(child, str(path), "Widget Error")
            if content:
                groupings.append(content)

    names = (w.name for w in iter_nested(groupings, Widget, WidgetGroup))
    warn_duplicate_names(names, "widget", str(path))

    return WidgetConfig(
        widgets=widgets,
        groupings=groupings,
        overrides=parse_name_overrides(root, "widget", path),
    )


def _parse_widget(elem, path: str, default_source: str = "") -> Widget | None:
    """Parse a widget element, reporting one that lacks a field; only a custom one needs no path."""
    widget_name = get_attr(elem, "name")
    label = get_attr(elem, "label")
    widget_type = get_attr(elem, "type") or ""
    widget_path = get_text(elem, "path") or ""

    if not widget_name:
        report_missing("Widget Error", path, elem, "name")
        return None
    if not label:
        report_missing("Widget Error", path, elem, "label")
        return None
    if not widget_path and widget_type != "custom":
        report_missing("Widget Error", path, elem, "<path>")
        return None

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
        report_missing("Widget Group Error", path, elem, "name")
        return None
    if not label and not flat:
        notify(
            "Widget Group Error",
            f"'{group_name}' missing label",
            f"{path}: <group name=\"{group_name}\"> has no label and is not flat; group "
            "skipped; add label=\"...\" or flat=\"true\"",
        )
        return None

    condition = get_attr(elem, "condition") or ""
    source = get_attr(elem, "source") or default_source
    items: list[Widget | WidgetGroup | Content] = []

    for child in elem:
        if child.tag == "widget":
            widget = _parse_widget(child, path, default_source=source)
            if widget:
                items.append(widget)
        elif child.tag == "group":
            nested = _parse_widget_group(child, path, default_source=source)
            if nested:
                items.append(nested)
        elif child.tag == "content":
            content = parse_content(child, path, "Widget Error")
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
