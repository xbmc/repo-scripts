"""Skin configuration loader."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from itertools import chain
from pathlib import Path

from .builders.includes import IncludesBuilder
from .loaders.background import load_backgrounds
from .loaders.base import iter_nested
from .loaders.menu import load_menus
from .loaders.property import load_properties
from .loaders.template import load_templates
from .loaders.views import load_views
from .loaders.widget import load_widgets
from .migrations import apply_overrides
from .models.background import Background, BackgroundConfig, BackgroundGroup
from .models.menu import IconOverrides, Menu, MenuItem, SubDialog
from .models.override import Override
from .models.property import PropertySchema
from .models.template import TemplateSchema
from .models.views import ViewConfig
from .models.widget import Widget, WidgetConfig, WidgetGroup
from .userdata import (
    UserData,
    _create_item_from_diff,
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
    icon_overrides: IconOverrides = field(default_factory=IconOverrides)
    submenu_path_all: bool = False
    userdata_path: str | None = None
    migrated: int = 0

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
        """Load configuration from shortcuts directory."""
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
        migrated = (
            apply_overrides(userdata, property_schema, widgets, backgrounds) if load_user else 0
        )

        template_map = {m.name: m for m in menu_config.menus if m.is_submenu}

        referenced_templates: set[str] = set()
        for menu in menu_config.menus:
            if menu.is_submenu:
                continue
            for item in menu.items:
                if item.submenu and item.submenu in template_map:
                    referenced_templates.add(item.submenu)
        for menu_diff in userdata.menus.values():
            for item_diff in menu_diff.items:
                if item_diff.submenu and item_diff.submenu in template_map:
                    referenced_templates.add(item_diff.submenu)

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
                diff = userdata.menus.get(menu.name)
                merged = (
                    merge_menu(menu, diff, menu_config.icon_overrides) if diff else menu
                )
                _apply_action_overrides(merged, menu_config.action_overrides)
                menus.append(merged)
                continue
            diff = userdata.menus.get(menu.name)
            merged = merge_menu(menu, diff, menu_config.icon_overrides)
            _apply_action_overrides(merged, menu_config.action_overrides)
            menus.append(merged)

            for item in merged.items:
                template_name = item.submenu or ""
                template = template_map.get(template_name) if template_name else None
                key = f"{merged.name}/{item.name}"
                instance_diff = userdata.menus.get(key)
                if template is None:
                    # No template means item owns its submenu without seed defaults.
                    if instance_diff is None:
                        continue
                    instance = Menu(name=key, is_submenu=True)
                    for item_diff in instance_diff.items:
                        instance.items.append(
                            _create_item_from_diff(item_diff, menu_config.icon_overrides)
                        )
                else:
                    instance = merge_menu(template, instance_diff, menu_config.icon_overrides)
                    instance.name = key
                    instance.template_origin = template_name
                _apply_action_overrides(instance, menu_config.action_overrides)
                menus.append(instance)

        for menu_name, menu_diff in userdata.menus.items():
            if menu_name in skin_menu_names:
                continue
            # Per-item submenu entries already expanded above; skip duplicates.
            if "/" in menu_name:
                parent_name, _, _ = menu_name.partition("/")
                if parent_name in skin_menu_names:
                    continue
            user_menu = Menu(name=menu_name, is_submenu=True)
            for item_diff in menu_diff.items:
                user_menu.items.append(
                    _create_item_from_diff(item_diff, menu_config.icon_overrides)
                )
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
            userdata_path=userdata_path,
            migrated=migrated,
        )

    def get_widget(self, widget_name: str) -> Widget | None:
        """Get widget by name, top level first, then nested in groupings."""
        nested = iter_nested(self.widget_groupings, Widget, WidgetGroup)
        return next((w for w in chain(self.widgets, nested) if w.name == widget_name), None)

    def get_background(self, bg_name: str) -> Background | None:
        """Get background by name, top level first, then nested in groupings."""
        nested = iter_nested(self.background_groupings, Background, BackgroundGroup)
        return next((b for b in chain(self.backgrounds, nested) if b.name == bg_name), None)

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

    def build_includes(self, output_path: str | Path) -> None:
        """Build and write includes.xml (including templates if present)."""
        self.build_includes_from_menus(output_path, self.menus)

    def build_includes_from_menus(
        self, output_path: str | Path, menus: list[Menu]
    ) -> None:
        """Build and write includes.xml from provided menus."""
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

    def derived_item_properties(self, item: MenuItem) -> dict[str, str]:
        """Widget/background sub-properties the item's names imply; labels stay $LOCALIZE."""
        derived: dict[str, str] = {}

        for key, name in item.properties.items():
            if not name:
                continue
            base, _, slot = key.partition(".")
            if slot and not slot.isdigit():
                continue
            tail = f".{slot}" if slot else ""
            if base == "background":
                bg = self.get_background(name)
                if bg:
                    derived[f"backgroundLabel{tail}"] = bg.label
                    derived[f"backgroundPath{tail}"] = bg.path
                    derived[f"backgroundType{tail}"] = bg.type_name
            elif base == "widget":
                widget = self.get_widget(name)
                if widget:
                    derived[f"widgetLabel{tail}"] = widget.label
                    derived[f"widgetPath{tail}"] = widget.path.replace("{menuitem}", item.name)
                    derived[f"widgetType{tail}"] = widget.type
                    derived[f"widgetTarget{tail}"] = widget.target
                    derived[f"widgetSource{tail}"] = widget.source
                    derived[f"widgetLimit{tail}"] = str(widget.limit or "")
                    derived[f"widgetSortBy{tail}"] = widget.sort_by
                    derived[f"widgetSortOrder{tail}"] = widget.sort_order

        return {self.property_schema.declared_name(k): v for k, v in derived.items() if v}

    def resolve_item_properties(self, menu: Menu) -> None:
        """Fill widget/background sub-properties, keeping any the user set."""
        for item in menu.items:
            present = {k.lower() for k in item.properties}
            for key, value in self.derived_item_properties(item).items():
                if key.lower() not in present:
                    item.properties[key] = value


def _apply_action_overrides(menu: Menu, overrides: list[Override]) -> None:
    """Apply action overrides to all items in a menu."""
    if not overrides:
        return

    override_map = {o.replace.lower(): o.value for o in overrides}

    for item in menu.items:
        for action in item.actions:
            action_lower = action.action.lower()
            if action_lower in override_map:
                action.action = override_map[action_lower]
