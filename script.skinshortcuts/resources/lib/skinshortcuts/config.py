"""Skin configuration loader."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path

from .builders import IncludesBuilder
from .loaders import (
    load_backgrounds,
    load_menus,
    load_properties,
    load_templates,
    load_views,
    load_widgets,
)
from .localize import resolve_label
from .models import Background, Menu, Widget
from .models.background import BackgroundConfig, BackgroundGroup
from .models.menu import ActionOverride, SubDialog
from .models.property import PropertySchema
from .models.template import TemplateSchema
from .models.views import ViewConfig
from .models.widget import WidgetConfig
from .userdata import (
    UserData,
    _create_item_from_override,
    load_userdata,
    merge_menu,
)


@dataclass
class SkinConfig:
    """Complete skin shortcuts configuration."""

    menus: list[Menu] = field(default_factory=list)
    default_menus: list[Menu] = field(default_factory=list)
    _widget_config: WidgetConfig = field(default_factory=WidgetConfig)
    _background_config: BackgroundConfig = field(default_factory=BackgroundConfig)
    _view_config: ViewConfig = field(default_factory=ViewConfig)
    userdata: UserData = field(default_factory=UserData)
    templates: TemplateSchema = field(default_factory=TemplateSchema)
    property_schema: PropertySchema = field(default_factory=PropertySchema)
    subdialogs: list[SubDialog] = field(default_factory=list)
    icon_overrides: dict[str, str] = field(default_factory=dict)
    submenu_path_all: bool = False

    @property
    def widgets(self) -> list[Widget]:
        """Get list of widgets."""
        return self._widget_config.widgets

    @property
    def widget_groupings(self) -> list:
        """Get widget groupings for picker dialog."""
        return self._widget_config.groupings

    @property
    def backgrounds(self) -> list[Background]:
        """Get list of backgrounds."""
        return self._background_config.backgrounds

    @property
    def background_groupings(self) -> list:
        """Get background groupings for picker dialog."""
        return self._background_config.groupings

    @property
    def view_config(self) -> ViewConfig:
        """Get view configuration."""
        return self._view_config

    @classmethod
    def load(
        cls,
        shortcuts_path: str | Path,
        load_user: bool = True,
        userdata_path: str | None = None,
    ) -> SkinConfig:
        """Load configuration from shortcuts directory.

        Args:
            shortcuts_path: Path to skin's shortcuts folder
            load_user: Whether to load and merge user customizations
            userdata_path: Optional path to userdata file (for testing)
        """
        path = Path(shortcuts_path)

        menu_config = load_menus(path / "menus.xml")
        widgets = load_widgets(path / "widgets.xml")
        backgrounds = load_backgrounds(
            path / "backgrounds.xml", icon_overrides=menu_config.icon_overrides
        )
        templates = load_templates(path / "templates.xml")
        property_schema = load_properties(path / "properties.xml")
        views = load_views(path / "views.xml")

        userdata = load_userdata(userdata_path) if load_user else UserData()

        template_map = {m.name: m for m in menu_config.menus if m.is_submenu}

        referenced_templates: set[str] = set()
        for menu in menu_config.menus:
            if menu.is_submenu:
                continue
            for item in menu.items:
                if item.submenu and item.submenu in template_map:
                    referenced_templates.add(item.submenu)
        for menu_override in userdata.menus.values():
            for item_override in menu_override.items:
                if item_override.submenu and item_override.submenu in template_map:
                    referenced_templates.add(item_override.submenu)

        menus = []
        skin_menu_names = set()
        top_level_names: set[str] = set()
        for menu in menu_config.menus:
            skin_menu_names.add(menu.name)
            if not menu.is_submenu:
                top_level_names.add(menu.name)
            if menu.is_submenu:
                if menu.name in referenced_templates:
                    continue
                # source="N" lookups read flat keys; merge user customizations there too
                override = userdata.menus.get(menu.name)
                merged = merge_menu(menu, override) if override else menu
                _apply_action_overrides(merged, menu_config.action_overrides)
                menus.append(merged)
                continue
            override = userdata.menus.get(menu.name)
            merged = merge_menu(menu, override)
            _apply_action_overrides(merged, menu_config.action_overrides)
            menus.append(merged)

            for item in merged.items:
                template_name = item.submenu or ""
                template = template_map.get(template_name) if template_name else None
                key = f"{merged.name}/{item.name}"
                instance_override = userdata.menus.get(key)
                if template is None:
                    # No template means item owns its submenu without seed defaults.
                    if instance_override is None:
                        continue
                    instance = Menu(name=key, is_submenu=True)
                    for item_override in instance_override.items:
                        instance.items.append(_create_item_from_override(item_override))
                else:
                    instance = merge_menu(template, instance_override)
                    instance.name = key
                    instance.template_origin = template_name
                _apply_action_overrides(instance, menu_config.action_overrides)
                menus.append(instance)

        for menu_name, menu_override in userdata.menus.items():
            if menu_name in skin_menu_names:
                continue
            # Per-item submenu entries already expanded above; skip duplicates.
            if "/" in menu_name:
                parent_name, _, _ = menu_name.partition("/")
                if parent_name in skin_menu_names:
                    continue
            user_menu = Menu(name=menu_name, is_submenu=True)
            for item_override in menu_override.items:
                user_menu.items.append(_create_item_from_override(item_override))
            menus.append(user_menu)

        return cls(
            menus=menus,
            default_menus=copy.deepcopy(menu_config.menus),
            _widget_config=widgets,
            _background_config=backgrounds,
            _view_config=views,
            userdata=userdata,
            templates=templates,
            property_schema=property_schema,
            subdialogs=menu_config.subdialogs,
            icon_overrides=menu_config.icon_overrides,
            submenu_path_all=menu_config.submenu_path_all,
        )

    def get_widget(self, widget_name: str) -> Widget | None:
        """Get widget by name.

        Searches both top-level widgets and widgets within groupings.
        """
        for widget in self.widgets:
            if widget.name == widget_name:
                return widget

        return self._find_widget_in_groupings(widget_name, self.widget_groupings)

    def _find_widget_in_groupings(self, widget_name: str, groups: list) -> Widget | None:
        """Recursively search for a widget within groupings."""
        from .models.widget import WidgetGroup

        for group in groups:
            if not isinstance(group, WidgetGroup):
                continue
            for item in group.items:
                if isinstance(item, Widget) and item.name == widget_name:
                    return item
                if isinstance(item, WidgetGroup):
                    result = self._find_widget_in_groupings(widget_name, [item])
                    if result:
                        return result
        return None

    def get_background(self, bg_name: str) -> Background | None:
        """Get background by name.

        Searches both top-level backgrounds and backgrounds within groupings.
        """
        for bg in self.backgrounds:
            if bg.name == bg_name:
                return bg

        return self._find_background_in_groupings(bg_name, self.background_groupings)

    def _find_background_in_groupings(self, bg_name: str, groups: list) -> Background | None:
        """Recursively search for a background within groupings."""
        for group in groups:
            if not isinstance(group, BackgroundGroup):
                continue
            for item in group.items:
                if isinstance(item, Background) and item.name == bg_name:
                    return item
                if isinstance(item, BackgroundGroup):
                    result = self._find_background_in_groupings(bg_name, [item])
                    if result:
                        return result
        return None

    def get_menu(self, menu_name: str) -> Menu | None:
        """Get menu by name."""
        for menu in self.menus:
            if menu.name == menu_name:
                return menu
        return None

    def get_default_menu(self, menu_name: str) -> Menu | None:
        """Get original skin default menu by name (before userdata merge)."""
        for menu in self.default_menus:
            if menu.name == menu_name:
                return menu
        return None

    def get_subdialog(self, button_id: int) -> SubDialog | None:
        """Get subdialog definition by button ID."""
        for subdialog in self.subdialogs:
            if subdialog.button_id == button_id:
                return subdialog
        return None

    def build_includes(self, output_path: str | Path) -> None:
        """Build and write includes.xml (including templates if present)."""
        self.build_includes_from_menus(output_path, self.menus)

    def build_includes_from_menus(
        self, output_path: str | Path, menus: list[Menu]
    ) -> None:
        """Build and write includes.xml from provided menus.

        Args:
            output_path: Path to write includes.xml
            menus: List of Menu objects (typically merged with userdata)
        """
        for menu in menus:
            self.resolve_item_properties(menu)

        builder = IncludesBuilder(
            menus=menus,
            templates=self.templates,
            property_schema=self.property_schema,
            view_config=self._view_config,
            userdata=self.userdata,
            subdialogs=self.subdialogs,
            submenu_path_all=self.submenu_path_all,
        )
        builder.write(output_path)

    def resolve_item_properties(self, menu: Menu) -> None:
        """Resolve background and widget names to their full properties."""
        for item in menu.items:
            bg_name = item.properties.get("background")
            if bg_name and "backgroundLabel" not in item.properties:
                bg = self.get_background(bg_name)
                if bg:
                    item.properties["backgroundLabel"] = resolve_label(bg.label)
                    item.properties["backgroundPath"] = bg.path

            widget_name = item.properties.get("widget")
            if widget_name and "widgetLabel" not in item.properties:
                widget = self.get_widget(widget_name)
                if widget:
                    props = widget.to_properties()
                    if "widgetLabel" in props:
                        props["widgetLabel"] = resolve_label(props["widgetLabel"])
                    for key, value in props.items():
                        if key not in item.properties:
                            item.properties[key] = value


def _apply_action_overrides(menu: Menu, overrides: list[ActionOverride]) -> None:
    """Apply action overrides to all items in a menu.

    Replaces deprecated/changed actions with their updated versions.
    Comparison is case-insensitive to handle variations in action strings.
    """
    if not overrides:
        return

    override_map = {o.replace.lower(): o.action for o in overrides}

    for item in menu.items:
        for action in item.actions:
            action_lower = action.action.lower()
            if action_lower in override_map:
                action.action = override_map[action_lower]
