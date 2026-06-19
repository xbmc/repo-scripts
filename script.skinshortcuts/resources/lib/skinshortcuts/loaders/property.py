"""Property loader for Skin Shortcuts.

Parses properties.xml with Kodi-style includes and suffix transforms.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from ..exceptions import PropertyConfigError
from ..log import get_logger
from ..models.property import (
    ButtonMapping,
    FallbackRule,
    IconVariant,
    PropertyFallback,
    PropertySchema,
    SchemaOption,
    SchemaProperty,
)
from .base import apply_suffix_transform, get_bool

log = get_logger("PropertyLoader")


class PropertyLoader:
    """Loads property schema from properties.xml."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._includes: dict[str, list[ET.Element]] = {}

    def load(self) -> PropertySchema:
        """Load and parse the property schema."""
        if not self.path.exists():
            return PropertySchema()

        try:
            tree = ET.parse(str(self.path))
            root = tree.getroot()
        except ET.ParseError as e:
            raise PropertyConfigError(
                str(self.path), f"XML parse error: {e}", e.position[0]
            ) from e
        except Exception as e:
            raise PropertyConfigError(str(self.path), f"Failed to load file: {e}") from e

        if root.tag != "properties":
            raise PropertyConfigError(
                str(self.path), f"Root element must be <properties>, got <{root.tag}>"
            )

        self._parse_includes(root)

        properties = {}
        for elem in root.findall("property"):
            prop = self._parse_property(elem)
            properties[prop.name] = prop

        fallbacks = {}
        fallbacks_elem = root.find("fallbacks")
        if fallbacks_elem is not None:
            for fb_elem in fallbacks_elem.findall("fallback"):
                fb = self._parse_fallback(fb_elem)
                fallbacks[fb.property_name] = fb

        buttons = {}
        buttons_elem = root.find("buttons")
        if buttons_elem is not None:
            default_suffix = get_bool(buttons_elem, "suffix")
            for child in buttons_elem:
                if child.tag == "button":
                    btn = self._parse_button(child, default_suffix)
                    if btn:
                        buttons[btn.button_id] = btn
                elif child.tag == "group":
                    group_suffix_attr = child.get("suffix")
                    if group_suffix_attr is not None:
                        group_suffix = group_suffix_attr.lower() == "true"
                    else:
                        group_suffix = default_suffix
                    for btn_elem in child.findall("button"):
                        btn = self._parse_button(btn_elem, group_suffix)
                        if btn:
                            buttons[btn.button_id] = btn

        return PropertySchema(
            properties=properties,
            fallbacks=fallbacks,
            buttons=buttons,
        )

    def _parse_includes(self, root: ET.Element) -> None:
        """Parse include definitions from <includes> section."""
        includes_section = root.find("includes")
        if includes_section is None:
            return
        for include_elem in includes_section.findall("include"):
            name = (include_elem.get("name") or "").strip()
            if not name:
                log.warning(f"{self.path}: <include> definition missing 'name' attribute, skipping")
                continue
            self._includes[name] = list(include_elem)

    def _expand_include(
        self, include_elem: ET.Element, suffix: str = ""
    ) -> list[ET.Element]:
        """Expand an include reference."""
        content_name = (include_elem.get("content") or "").strip()
        if not content_name or content_name not in self._includes:
            return []

        suffix = suffix or include_elem.get("suffix") or ""

        result = []
        for elem in self._includes[content_name]:
            copied = self._copy_element_with_suffix(elem, suffix)
            result.append(copied)

        return result

    def _copy_element_with_suffix(self, elem: ET.Element, suffix: str) -> ET.Element:
        """Deep copy element, applying suffix transform to conditions."""
        new_elem = ET.Element(elem.tag, elem.attrib.copy())
        new_elem.text = elem.text
        new_elem.tail = elem.tail

        if suffix and "condition" in new_elem.attrib:
            new_elem.attrib["condition"] = apply_suffix_transform(
                new_elem.attrib["condition"], suffix
            )

        for child in elem:
            new_child = self._copy_element_with_suffix(child, suffix)
            new_elem.append(new_child)

        return new_elem

    def _parse_property(self, elem: ET.Element) -> SchemaProperty:
        """Parse a property element."""
        name = (elem.get("name") or "").strip()
        if not name:
            raise PropertyConfigError(str(self.path), "Property missing name attribute")

        template_only = get_bool(elem, "templateonly")
        prop_type = (elem.get("type") or "").strip()  # "widget", "background", "toggle"

        requires = (elem.get("requires") or "").strip()
        # Also support nested <requires> element for backwards compat during transition
        if not requires:
            requires_elem = elem.find("requires")
            if requires_elem is not None:
                requires = (requires_elem.get("property") or "").strip()

        options = []
        options_elem = elem.find("options")
        if options_elem is not None:
            options = self._parse_options(options_elem)

        value = (elem.get("value") or "").strip()

        return SchemaProperty(
            name=name,
            template_only=template_only,
            requires=requires,
            options=options,
            type=prop_type,
            value=value,
        )

    def _parse_button(
        self, elem: ET.Element, default_suffix: bool = False
    ) -> ButtonMapping | None:
        """Parse a button element from the buttons section."""
        button_id_str = (elem.get("id") or "").strip()
        if not button_id_str:
            log.warning(f"{self.path}: <button> mapping missing 'id' attribute, skipping")
            return None

        try:
            button_id = int(button_id_str)
        except ValueError:
            raise PropertyConfigError(
                str(self.path),
                f"Invalid button id '{button_id_str}'",
            )

        property_name = (elem.get("property") or "").strip()
        if not property_name:
            raise PropertyConfigError(
                str(self.path),
                f"Button {button_id} missing property attribute",
            )

        suffix_attr = elem.get("suffix")
        if suffix_attr is not None:
            suffix = suffix_attr.lower() == "true"
        else:
            suffix = default_suffix

        title = (elem.get("title") or "").strip()
        show_none = (elem.get("showNone") or "true").lower() != "false"
        show_icons = (elem.get("showIcons") or "true").lower() != "false"
        prop_type = (elem.get("type") or "").strip()
        requires = (elem.get("requires") or "").strip()

        return ButtonMapping(
            button_id=button_id,
            property_name=property_name,
            suffix=suffix,
            title=title,
            show_none=show_none,
            show_icons=show_icons,
            type=prop_type,
            requires=requires,
        )

    def _parse_options(self, options_elem: ET.Element) -> list[SchemaOption]:
        """Parse options element, expanding includes."""
        result = []

        for child in options_elem:
            if child.tag == "include":
                expanded = self._expand_include(child)
                for exp_child in expanded:
                    if exp_child.tag == "option":
                        result.append(self._parse_option(exp_child))
            elif child.tag == "option":
                result.append(self._parse_option(child))

        return result

    def _parse_option(self, elem: ET.Element) -> SchemaOption:
        """Parse a single option element."""
        value = (elem.get("value") or "").strip()
        label = (elem.get("label") or "").strip()
        condition = (elem.get("condition") or "").strip()

        icons = []
        for icon_elem in elem.findall("icon"):
            icon_path = (icon_elem.text or "").strip()
            icon_condition = (icon_elem.get("condition") or "").strip()
            if icon_path:
                icons.append(IconVariant(path=icon_path, condition=icon_condition))

        return SchemaOption(
            value=value,
            label=label,
            condition=condition,
            icons=icons,
        )

    def _parse_fallback(self, elem: ET.Element) -> PropertyFallback:
        """Parse a fallback element."""
        property_name = (elem.get("property") or "").strip()
        if not property_name:
            raise PropertyConfigError(
                str(self.path), "Fallback missing property attribute"
            )

        rules = []

        expanded_children = []
        for child in elem:
            if child.tag == "include":
                expanded = self._expand_include(child)
                expanded_children.extend(expanded)
            else:
                expanded_children.append(child)

        for child in expanded_children:
            if child.tag == "when":
                condition = child.get("condition", "").strip()
                value = (child.text or "").strip()
                rules.append(FallbackRule(value=value, condition=condition))
            elif child.tag == "default":
                value = (child.text or "").strip()
                rules.append(FallbackRule(value=value, condition=""))

        return PropertyFallback(property_name=property_name, rules=rules)


def load_properties(path: str | Path) -> PropertySchema:
    """Load property schema from file."""
    loader = PropertyLoader(path)
    return loader.load()
