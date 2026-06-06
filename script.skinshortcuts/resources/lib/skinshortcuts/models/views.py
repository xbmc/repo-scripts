"""View models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class View:
    """A view definition.

    Represents a single view that can be assigned to content types.
    """

    id: str
    label: str
    icon: str = ""


@dataclass
class ViewContent:
    """A content type definition with detection rules and available views.

    Content types define what views are available for specific content
    (movies, tvshows, etc.) and how to detect that content at runtime.
    """

    name: str
    label: str
    visible: str
    views: list[str]
    library_default: str
    plugin_default: str = ""
    icon: str = ""

    def get_default(self, is_plugin: bool) -> str:
        """Get the default view ID for this content type."""
        if is_plugin and self.plugin_default:
            return self.plugin_default
        return self.library_default


@dataclass
class ViewConfig:
    """View configuration including views, content rules, and settings.

    Loaded from views.xml in the skin's shortcuts folder.
    """

    views: list[View] = field(default_factory=list)
    content_rules: list[ViewContent] = field(default_factory=list)
    prefix: str = "ShortcutView_"

    def get_view(self, view_id: str) -> View | None:
        """Get a view by ID."""
        for view in self.views:
            if view.id == view_id:
                return view
        return None

    def get_content(self, name: str) -> ViewContent | None:
        """Get a content rule by name."""
        for content in self.content_rules:
            if content.name == name:
                return content
        return None

    def get_views_for_content(self, name: str) -> list[View]:
        """Get the View objects available for a content type."""
        content = self.get_content(name)
        if not content:
            return []
        result = []
        for view_id in content.views:
            view = self.get_view(view_id)
            if view:
                result.append(view)
        return result
