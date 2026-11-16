"""View loader."""

from __future__ import annotations

from pathlib import Path

from ..constants import DEFAULT_VIEW_PREFIX
from ..exceptions import ViewConfigError
from ..log import notify
from ..models.views import View, ViewConfig, ViewContent
from .base import get_attr, get_text, parse_xml, report_missing, warn_duplicate_names


def load_views(path: str | Path) -> ViewConfig:
    """Load view configuration from views.xml."""
    path = Path(path)
    if not path.exists():
        return ViewConfig()

    root = parse_xml(path, "views", ViewConfigError)
    path_str = str(path)

    prefix = get_attr(root, "prefix") or DEFAULT_VIEW_PREFIX
    views = _parse_views(root, path_str)
    warn_duplicate_names((v.id for v in views), "view", path_str)

    content_rules = _parse_rules(root, path_str, views)
    warn_duplicate_names((c.name for c in content_rules), "content", path_str)

    return ViewConfig(
        views=views,
        content_rules=content_rules,
        prefix=prefix,
    )


def _parse_views(root, path: str) -> list[View]:
    """Parse top-level view definitions, reporting one with no id or label."""
    views = []

    for elem in root.findall("view"):
        view_id = get_attr(elem, "id")
        label = get_attr(elem, "label")
        if not view_id:
            report_missing("View Error", path, elem, "id", key="id")
            continue
        if not label:
            report_missing("View Error", path, elem, "label", key="id")
            continue

        views.append(View(
            id=view_id,
            label=label,
            icon=get_attr(elem, "icon") or "",
        ))

    return views


def _parse_rules(root, path: str, views: list[View]) -> list[ViewContent]:
    """Parse content rules from <rules> element."""
    rules_elem = root.find("rules")
    if rules_elem is None:
        return []

    view_ids = {v.id for v in views}
    content_rules = []

    for elem in rules_elem.findall("content"):
        content = _parse_content_rule(elem, path, view_ids)
        if content:
            content_rules.append(content)

    return content_rules


def _parse_content_rule(elem, path: str, valid_view_ids: set[str]) -> ViewContent | None:
    """Parse a content rule, reporting a missing field or undefined view."""
    name = get_attr(elem, "name")
    label = get_attr(elem, "label")
    library_default = get_attr(elem, "library")
    visible = get_text(elem, "visible")
    views_text = get_text(elem, "views")
    required = (
        ("name", name), ("label", label), ("library", library_default),
        ("<visible>", visible), ("<views>", views_text),
    )
    for field, value in required:
        if not value:
            report_missing("View Error", path, elem, field)
            return None

    written = f'<content name="{name}">'
    view_ids = []
    for view_id in filter(None, (v.strip() for v in views_text.split(","))):
        if view_id in valid_view_ids:
            view_ids.append(view_id)
        else:
            notify(
                "View Error",
                f"'{name}' lists undefined view '{view_id}'",
                f"{path}: {written} <views> lists '{view_id}', which is not a defined view id; "
                "it is skipped; use a defined view id",
            )

    if not view_ids:
        notify(
            "View Error",
            f"'{name}' lists no defined view",
            f"{path}: {written} <views> names no defined view id; content skipped; "
            "list the ids of defined views",
        )
        return None

    if library_default not in valid_view_ids:
        notify(
            "View Error",
            f"'{name}' library view not defined",
            f'{path}: {written} has library="{library_default}", which is not a defined view id; '
            "content skipped; use a defined view id",
        )
        return None

    plugin_default = get_attr(elem, "plugin") or ""
    if plugin_default and plugin_default not in valid_view_ids:
        notify(
            "View Error",
            f"'{name}' plugin view not defined",
            f'{path}: {written} has plugin="{plugin_default}", which is not a defined view id; '
            "plugin default ignored; use a defined view id",
        )
        plugin_default = ""

    return ViewContent(
        name=name,
        label=label,
        visible=visible,
        views=view_ids,
        library_default=library_default,
        plugin_default=plugin_default,
        icon=get_attr(elem, "icon") or "",
    )
