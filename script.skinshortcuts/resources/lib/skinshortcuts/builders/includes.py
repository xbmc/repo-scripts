"""Includes XML builder."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import TYPE_CHECKING

from ..constants import extract_path_from_action

if TYPE_CHECKING:
    from ..models import Menu, MenuItem
    from ..models.menu import SubDialog
    from ..models.property import PropertySchema
    from ..models.template import TemplateSchema
    from ..models.views import ViewConfig
    from ..userdata import UserData


class IncludesBuilder:
    """Builds script-skinshortcuts-includes.xml from models."""

    def __init__(
        self,
        menus: list[Menu],
        templates: TemplateSchema | None = None,
        property_schema: PropertySchema | None = None,
        view_config: ViewConfig | None = None,
        userdata: UserData | None = None,
        subdialogs: list[SubDialog] | None = None,
        submenu_path_all: bool = False,
    ):
        self.menus = menus
        self.templates = templates
        self.property_schema = property_schema
        self.view_config = view_config
        self.userdata = userdata
        self.subdialogs = subdialogs or []
        self.submenu_path_all = submenu_path_all
        self._menu_map: dict[str, Menu] = {m.name: m for m in menus}

    def build(self) -> ET.Element:
        """Build the includes XML tree."""
        root = ET.Element("includes")

        # Build includes only for root menus (not submenus)
        # A menu is a root menu if:
        # 1. It was defined with <menu> tag (is_submenu=False), AND
        # 2. It's not referenced as a submenu by another menu item
        #
        # Submenus defined with <submenu> tag are never built as root includes,
        # even if deleted from the parent menu (they become orphaned).
        #
        # Menus with named submenu templates (e.g., <submenu name="powermenu">)
        # don't get raw includes - only the template version is built.

        template_menu_names: set[str] = set()
        if self.templates:
            for submenu_tpl in self.templates.submenus:
                if submenu_tpl.name:
                    template_menu_names.add(submenu_tpl.name)

        auto_menus: list[Menu] = []
        build_menus: list[Menu] = []

        for menu in self.menus:
            if menu.is_submenu:
                continue
            if menu.name in template_menu_names:
                continue
            if menu.build == "auto":
                auto_menus.append(menu)
            else:
                build_menus.append(menu)

        if auto_menus:
            auto_names = {m.name for m in auto_menus}
            all_actions = self._get_all_actions(auto_names)
            build_menus.extend(
                m for m in auto_menus if m.action and m.action.lower() in all_actions
            )

        for menu in build_menus:
            include = self._build_menu_include(menu)
            root.append(include)

            if "submenu" not in menu.template_only:
                submenu_include = self._build_submenu_include(menu)
                if submenu_include is not None:
                    root.append(submenu_include)

            custom_widget_includes = self._build_custom_widget_includes(menu)
            for cw_include in custom_widget_includes:
                root.append(cw_include)

        emitted_submenu_names: set[str] = set()
        for menu in self.menus:
            if not menu.is_submenu:
                continue
            if not menu.items:
                continue
            if menu.name.startswith("custom-"):
                continue
            if not menu.template_origin:
                continue
            if not menu.standalone:
                continue
            include_name = menu.template_origin
            if "/" in include_name:
                continue
            if include_name in emitted_submenu_names:
                continue
            include = self._build_menu_include(menu, name_override=include_name)
            root.append(include)
            emitted_submenu_names.add(include_name)

        if self.templates and self.templates.templates:
            from .template import TemplateBuilder

            template_builder = TemplateBuilder(
                schema=self.templates,
                menus=self.menus,
                property_schema=self.property_schema,
            )
            template_root = template_builder.build()
            for template_include in template_root:
                root.append(template_include)

        if self.view_config and self.view_config.content_rules and self.userdata:
            from .views import ViewExpressionBuilder

            view_builder = ViewExpressionBuilder(self.view_config, self.userdata)
            for expr in view_builder.build():
                root.append(expr)

        return root

    def _build_menu_include(self, menu: Menu, name_override: str | None = None) -> ET.Element:
        include = ET.Element("include")
        include.set("name", f"skinshortcuts-{name_override or menu.name}")

        start = menu.startid if menu.controltype else 1
        for idx, item in enumerate(menu.items, start=start):
            if item.disabled:
                continue
            item_elem = self._build_item(item, idx, menu)
            include.append(item_elem)

        return include

    def _build_submenu_include(self, parent_menu: Menu) -> ET.Element | None:
        """Build combined submenu include for a root menu."""
        submenu_items: list[tuple[MenuItem, MenuItem, int, Menu]] = []

        for parent_item in parent_menu.items:
            if parent_item.disabled:
                continue
            submenu_key = f"{parent_menu.name}/{parent_item.name}"
            submenu = self._menu_map.get(submenu_key)
            if not submenu:
                continue
            for idx, sub_item in enumerate(submenu.items, start=1):
                if not sub_item.disabled:
                    submenu_items.append((parent_item, sub_item, idx, submenu))

        if not submenu_items:
            return None

        include = ET.Element("include")
        include.set("name", f"skinshortcuts-{parent_menu.name}-submenu")

        global_idx = 1
        for parent_item, sub_item, _, submenu in submenu_items:
            elem = self._build_submenu_item(
                sub_item, global_idx, parent_item, submenu, parent_menu.container
            )
            include.append(elem)
            global_idx += 1

        return include

    def _build_submenu_item(
        self,
        item: MenuItem,
        idx: int,
        parent_item: MenuItem,
        menu: Menu,
        container: str | None,
    ) -> ET.Element:
        """Build a submenu item element with parent linking and visibility."""
        elem = self._build_item(item, idx, menu)
        self._add_property(elem, "parent", parent_item.name)

        if container:
            visibility = (
                f"String.IsEqual(Container({container}).ListItem.Property(name),"
                f"{parent_item.name})"
            )
            existing = elem.find("visible")
            if existing is not None and existing.text:
                existing.text = f"[{existing.text}] + [{visibility}]"
            else:
                if existing is None:
                    existing = ET.SubElement(elem, "visible")
                existing.text = visibility

        return elem

    def _build_custom_widget_includes(self, parent_menu: Menu) -> list[ET.Element]:
        """Build custom widget includes for a root menu.

        Custom widgets are referenced via item properties:
        - customWidget -> slot 1, include: skinshortcuts-{item}-customwidget
        - customWidget.2 -> slot 2, include: skinshortcuts-{item}-customwidget2
        - etc.

        Returns:
            List of include elements, one per custom widget reference found.
        """
        includes = []

        for parent_item in parent_menu.items:
            if parent_item.disabled:
                continue

            for suffix in ["", ".2", ".3", ".4", ".5", ".6", ".7", ".8", ".9", ".10"]:
                prop_name = f"customWidget{suffix}"
                cw_menu_ref = parent_item.properties.get(prop_name)
                if not cw_menu_ref:
                    continue

                cw_menu = self._menu_map.get(cw_menu_ref)
                if not cw_menu or not cw_menu.items:
                    continue

                suffix_name = suffix.replace(".", "") if suffix else ""
                include = ET.Element("include")
                include.set("name", f"skinshortcuts-{parent_item.name}-customwidget{suffix_name}")

                for idx, cw_item in enumerate(cw_menu.items, start=1):
                    if cw_item.disabled:
                        continue
                    elem = self._build_item(cw_item, idx, cw_menu)
                    include.append(elem)

                includes.append(include)

        return includes

    def _build_item(self, item: MenuItem, idx: int, menu: Menu) -> ET.Element:
        if menu.controltype:
            elem = ET.Element("control")
            elem.set("type", menu.controltype)
        else:
            elem = ET.Element("item")
        elem.set("id", str(idx))

        ET.SubElement(elem, "label").text = item.label
        if item.label2:
            ET.SubElement(elem, "label2").text = item.label2
        ET.SubElement(elem, "icon").text = item.icon
        if item.thumb:
            ET.SubElement(elem, "thumb").text = item.thumb

        all_includes = menu.defaults.includes + item.includes
        before_includes = [i for i in all_includes if i.position == "before-onclick"]
        after_includes = [i for i in all_includes if i.position == "after-onclick"]

        for inc in before_includes:
            include_elem = ET.SubElement(elem, "include")
            include_elem.text = inc.name
            if inc.condition:
                include_elem.set("condition", inc.condition)

        before_actions = [a for a in menu.defaults.actions if a.when == "before"]
        after_actions = [a for a in menu.defaults.actions if a.when == "after"]
        conditional = [a for a in item.actions if a.condition]
        unconditional = [a for a in item.actions if not a.condition]

        for act in before_actions:
            onclick = ET.SubElement(elem, "onclick")
            onclick.text = act.action
            if act.condition:
                onclick.set("condition", act.condition)

        for act in conditional + unconditional:
            onclick = ET.SubElement(elem, "onclick")
            onclick.text = act.action
            if act.condition:
                onclick.set("condition", act.condition)

        for act in after_actions:
            onclick = ET.SubElement(elem, "onclick")
            onclick.text = act.action
            if act.condition:
                onclick.set("condition", act.condition)

        for inc in after_includes:
            include_elem = ET.SubElement(elem, "include")
            include_elem.text = inc.name
            if inc.condition:
                include_elem.set("condition", inc.condition)

        if item.visible:
            ET.SubElement(elem, "visible").text = item.visible

        if not menu.controltype:
            self._add_property(elem, "id", str(idx))
            self._add_property(elem, "name", item.name)
            self._add_property(elem, "menu", menu.template_origin or menu.name)
            self._add_property(elem, "action", item.action)
            path = extract_path_from_action(item.action) if item.action else ""
            self._add_property(elem, "path", path)

            self._add_property(elem, "submenuVisibility", item.name)

            submenu_key = f"{menu.name}/{item.name}"
            submenu = self._menu_map.get(submenu_key)
            if submenu and submenu.items:
                self._add_property(elem, "hasSubmenu", "True")

            all_properties = {**menu.defaults.properties, **item.properties}
            all_properties.update(self._submenu_paths_for_item(item, menu))
            for key, value in all_properties.items():
                if self._is_template_only(key):
                    continue
                self._add_property(elem, key, value)

        return elem

    @staticmethod
    def _enabled_widgets(submenu: Menu) -> list[MenuItem]:
        """Submenu items that are widgets: enabled and carrying a widgetPath."""
        return [
            sub_item
            for sub_item in submenu.items
            if not sub_item.disabled and sub_item.properties.get("widgetPath")
        ]

    def _widget_submenu_for_item(self, item: MenuItem) -> Menu | None:
        """The item's widgets submenu, found via a {item}.X subdialog ref.

        Matched by widget content, not menu_type (runtime submenus have none).
        Skips custom-widget content menus.
        """
        cw_ids = {
            value
            for key, value in item.properties.items()
            if key.startswith("customWidget") and value
        }
        for sub in self.subdialogs:
            refs = [sub.menu]
            refs.extend(oc.menu for oc in sub.onclose if oc.action == "menu")
            for ref in refs:
                if not ref or "{item}" not in ref:
                    continue
                if ref.startswith("{customWidget") or ".customwidget" in ref:
                    continue
                resolved = ref.replace("{item}", item.name)
                if resolved in cw_ids:
                    continue
                submenu = self._menu_map.get(resolved)
                if submenu is not None and self._enabled_widgets(submenu):
                    return submenu
        return None

    def _submenu_paths_for_item(self, item: MenuItem, parent_menu: Menu) -> dict[str, str]:
        """The item's submenuPath (its first widget), plus the numbered
        submenuPath.N tail when "all" is opted in on the parent menu or globally
        on <menus>."""
        submenu = self._widget_submenu_for_item(item)
        if submenu is None:
            return {}
        widgets = self._enabled_widgets(submenu)
        paths = {"submenuPath": widgets[0].properties["widgetPath"]}
        emit_tail = self.submenu_path_all or parent_menu.submenu_path == "all"
        if emit_tail:
            for index, widget in enumerate(widgets[1:], start=2):
                paths[f"submenuPath.{index}"] = widget.properties["widgetPath"]
        return paths

    def _get_all_actions(self, exclude: set[str]) -> set[str]:
        """Collect all item actions (lowercased) from menus not in exclude set."""
        actions: set[str] = set()
        for menu in self.menus:
            if menu.name in exclude:
                continue
            for item in menu.items:
                if item.disabled:
                    continue
                for act in item.actions:
                    if act.action:
                        actions.add(act.action.lower())
        return actions

    def _is_template_only(self, prop_name: str) -> bool:
        """Whether a property is template_only: built but not emitted to includes.

        Numeric slot variants (widgetSortby.2) inherit the base property's flag.
        """
        if not self.property_schema:
            return False
        prop = self.property_schema.get_property(prop_name)
        if prop is None:
            base, sep, tail = prop_name.rpartition(".")
            if sep and tail.isdigit():
                prop = self.property_schema.get_property(base)
        return prop is not None and prop.template_only

    @staticmethod
    def _add_property(parent: ET.Element, name: str, value: str) -> None:
        if value:
            prop = ET.SubElement(parent, "property")
            prop.set("name", name)
            prop.text = value

    def write(self, path: str | Path, indent: bool = True) -> None:
        """Write includes XML to file."""
        root = self.build()
        if indent:
            _indent_xml(root)
        tree = ET.ElementTree(root)
        tree.write(str(path), encoding="UTF-8", xml_declaration=True)


def _indent_xml(elem: ET.Element, level: int = 0) -> None:
    """Add indentation to XML tree."""
    indent = "\n" + "\t" * level
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = indent + "\t"
        if not elem.tail or not elem.tail.strip():
            elem.tail = indent
        for child in elem:
            _indent_xml(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = indent
    elif level and (not elem.tail or not elem.tail.strip()):
        elem.tail = indent
