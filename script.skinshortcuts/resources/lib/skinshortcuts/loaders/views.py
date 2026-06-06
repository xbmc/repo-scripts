"""View loader."""

from __future__ import annotations

from pathlib import Path

from ..constants import DEFAULT_VIEW_PREFIX
from ..exceptions import ViewConfigError
from ..models.views import View, ViewConfig, ViewContent
from .base import get_attr, parse_xml


def load_views(path: str | Path) -> ViewConfig:
    """Load view configuration from views.xml.

    Returns:
        ViewConfig containing view definitions, content rules, and settings.
    """
    path = Path(path)
    if not path.exists():
        return ViewConfig()

    root = parse_xml(path, "views", ViewConfigError)
    path_str = str(path)

    prefix = get_attr(root, "prefix") or DEFAULT_VIEW_PREFIX
    views = _parse_views(root, path_str)
    content_rules = _parse_rules(root, path_str, views)

    return ViewConfig(
        views=views,
        content_rules=content_rules,
        prefix=prefix,
    )


def _parse_views(root, path: str) -> list[View]:
    """Parse view definitions from direct children of root."""
    views = []

    for elem in root.findall("view"):
        view_id = get_attr(elem, "id")
        if not view_id:
            raise ViewConfigError(path, "View missing 'id' attribute")

        label = get_attr(elem, "label")
        if not label:
            raise ViewConfigError(path, f"View '{view_id}' missing 'label' attribute")

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
        content = _parse_content(elem, path, view_ids)
        if content:
            content_rules.append(content)

    return content_rules


def _parse_content(elem, path: str, valid_view_ids: set[str]) -> ViewContent | None:
    """Parse a content element."""
    name = get_attr(elem, "name")
    if not name:
        raise ViewConfigError(path, "Content rule missing 'name' attribute")

    label = get_attr(elem, "label")
    if not label:
        raise ViewConfigError(path, f"Content '{name}' missing 'label' attribute")

    library_default = get_attr(elem, "library")
    if not library_default:
        raise ViewConfigError(path, f"Content '{name}' missing 'library' attribute")

    visible_elem = elem.find("visible")
    if visible_elem is None or not visible_elem.text:
        raise ViewConfigError(path, f"Content '{name}' missing <visible> element")
    visible = visible_elem.text.strip()

    views_elem = elem.find("views")
    if views_elem is None or not views_elem.text:
        raise ViewConfigError(path, f"Content '{name}' missing <views> element")

    view_ids = [v.strip() for v in views_elem.text.split(",")]
    view_ids = [v for v in view_ids if v and v in valid_view_ids]

    if not view_ids:
        raise ViewConfigError(path, f"Content '{name}' has no valid view IDs")

    if library_default not in valid_view_ids:
        raise ViewConfigError(
            path, f"Content '{name}' library default '{library_default}' is not a defined view"
        )

    plugin_default = get_attr(elem, "plugin") or ""
    if plugin_default and plugin_default not in valid_view_ids:
        raise ViewConfigError(
            path, f"Content '{name}' plugin default '{plugin_default}' is not a defined view"
        )

    return ViewContent(
        name=name,
        label=label,
        visible=visible,
        views=view_ids,
        library_default=library_default,
        plugin_default=plugin_default,
        icon=get_attr(elem, "icon") or "",
    )
