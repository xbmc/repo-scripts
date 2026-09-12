"""Property management mixin - widget, background, toggle, options properties."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal

from ..log import get_logger, notify

_log = get_logger("Properties")

try:
    import xbmc
    import xbmcgui
    import xbmcvfs

    IN_KODI = True
except ImportError:
    IN_KODI = False


def _resolve_playlist_path(filepath: str) -> str | None:
    """Resolve a playlist path to an actual readable file path.

    special://videoplaylists/ is a multipath over the video and mixed dirs.
    """
    import xbmcvfs

    translated = xbmcvfs.translatePath(filepath)

    if translated.startswith("multipath://"):
        filename = filepath.rsplit("/", 1)[-1]
        source_dirs = unpack_multipath(translated)
        for source_dir in source_dirs:
            candidate = f"{source_dir.rstrip('/')}/{filename}"
            if xbmcvfs.exists(candidate):
                return candidate
        return None

    return translated


def _parse_smart_playlist(filepath: str) -> tuple[str, str]:
    """Parse a smart playlist (.xsp file) for name and type."""
    if not IN_KODI:
        return "", ""

    try:
        import xml.etree.ElementTree as ET

        import xbmcvfs

        real_path = _resolve_playlist_path(filepath)
        if not real_path:
            _log.debug(f"file not found in source paths: {filepath}")
            return "", ""

        f = xbmcvfs.File(real_path)
        try:
            content = f.read()
        finally:
            f.close()

        root = ET.fromstring(content)
        name_elem = root.find("name")
        name = name_elem.text if name_elem is not None and name_elem.text else ""

        playlist_type = root.get("type") or ""

        return name, playlist_type
    except Exception as e:
        _log.error(f"parse error for {filepath}: {e}")
        return "", ""


from ..loaders import evaluate_condition, load_widgets
from ..loaders.base import apply_suffix_transform
from ..localize import LANGUAGE, resolve_label
from ..models import (
    Background,
    BackgroundType,
    Content,
    MenuItem,
    PlaylistSource,
    Widget,
    WidgetGroup,
)
from ..playlists import playlists_base_path, unpack_multipath
from ..providers import scan_playlist_files
from .pickers import picker_select

if TYPE_CHECKING:
    from ..manager import MenuManager
    from ..models import PropertySchema


def _split_suffix(prop_name: str) -> tuple[str, str]:
    """Split "widget.2" into ("widget", ".2"); an unsuffixed name gives ("widget", "")."""
    if "." in prop_name:
        base, suffix = prop_name.rsplit(".", 1)
        return base, f".{suffix}"
    return prop_name, ""


def _label_property_name(prop_name: str) -> str:
    """Label key for a widget slot: "widget.2" -> "widgetLabel.2"."""
    base, suffix = _split_suffix(prop_name)
    return f"{base}Label{suffix}"


# handled off the button alone; every other type falls through to options, which needs the property
BUTTON_ONLY_TYPES = ("widget", "background", "toggle", "text", "number")


class PropertiesMixin:
    """Mixin providing property management - widget, background, toggle, options.

    Requires DialogBaseMixin and PickersMixin first.
    """

    menu_id: str
    shortcuts_path: str
    manager: MenuManager | None
    property_schema: PropertySchema | None
    property_suffix: str
    dialog_mode: str

    if TYPE_CHECKING:

        def _get_selected_item(self) -> MenuItem | None: ...
        def _get_item_properties(self, item: MenuItem) -> dict[str, str]: ...
        def _get_item_property(self, item: MenuItem, name: str) -> str: ...
        def _refresh_selected_item(self) -> None: ...
        def _log(self, msg: str) -> None: ...

        def _set_item_property(
            self,
            item: MenuItem,
            name: str,
            value: str | None,
            related: dict[str, str | None] | None = None,
            apply_suffix: bool = True,
        ) -> None: ...

        def _browse_with_sources(
            self,
            sources: list,
            title: str,
            browse_type: int,
            item_properties: dict[str, str] | None = None,
            default_path: str = "",
        ) -> str | None: ...

        def _pick_widget_from_groups(
            self,
            items: list[WidgetGroup | Widget | Content],
            item_props: dict[str, str],
            slot: str = "",
        ) -> Widget | None | Literal[False]: ...

        def _pick_widget_flat(
            self, widgets: list, item_props: dict[str, str] | None = None, slot: str = ""
        ) -> Widget | None | Literal[False]: ...

        def _pick_background(
            self,
            item_props: dict[str, str],
            current_value: str = "",
            positions: dict[str, int] | None = None,
        ) -> Background | None | Literal[False]: ...

    def _check_requires(self, item: MenuItem, requires_name: str) -> bool:
        """Check if a required property is satisfied."""
        if item.properties.get(requires_name, ""):
            return True

        base_name = requires_name.split(".")[0] if "." in requires_name else requires_name
        suffix = "." + requires_name.split(".", 1)[1] if "." in requires_name else ""

        if base_name == "widget":
            path_name = f"widgetPath{suffix}"
            if item.properties.get(path_name, ""):
                return True
        elif base_name == "background":
            path_name = f"backgroundPath{suffix}"
            if item.properties.get(path_name, ""):
                return True

        return False

    def _handle_property_button(self, button_id: int) -> bool:
        """Handle a property button click from the schema."""
        if not self.property_schema or not self.manager:
            return False

        prop, button = self.property_schema.get_property_for_button(button_id)
        if not button:
            return False

        item = self._get_selected_item()
        if not item:
            return False

        requires = button.requires or (prop.requires if prop else "")
        if requires:
            requires_name = requires
            if button.suffix and self.property_suffix:
                requires_name = f"{requires}{self.property_suffix}"
            if not self._check_requires(item, requires_name):
                xbmcgui.Dialog().notification(
                    LANGUAGE(32183),
                    LANGUAGE(32184) % requires_name,
                )
                return True

        prop_name = prop.name if prop else button.property_name
        if button.suffix and self.property_suffix:
            prop_name = f"{prop_name}{self.property_suffix}"

        prop_type = button.type or (prop.type if prop else "")

        if prop_type == "widget":
            widget = self._handle_widget_property(prop, item, prop_name)
            if widget is not None and button.rename:
                self._prompt_widget_rename(item, prop_name, widget)
            return True
        if prop_type == "background":
            self._handle_background_property(prop, item, prop_name)
            return True
        if prop_type == "toggle":
            self._handle_toggle_property(prop, item, button, prop_name)
            return True
        if prop_type == "text":
            self._handle_text_property(item, button, prop_name)
            return True
        if prop_type == "number":
            self._handle_number_property(item, button, prop_name)
            return True

        if prop is None:
            notify(
                "Property Button Error",
                f"button {button_id}: '{button.property_name}' not defined",
            )
            return True

        return self._handle_options_property(prop, item, button, prop_name)

    def _handle_widget_property(self, prop, item: MenuItem, prop_name: str) -> Widget | None:
        """Handle a widget-type property.

        Custom list sets widgetType=custom, which an onclose opens the editor for.
        """
        if self.manager is None:
            return None
        menu = self.manager.config.get_menu(self.menu_id)
        if menu and not menu.allow.widgets:
            xbmcgui.Dialog().notification(LANGUAGE(32143), LANGUAGE(32144))
            return None

        prefix = prop_name
        slot = prefix
        widgets_path = Path(self.shortcuts_path) / "widgets.xml"
        widget_config = load_widgets(widgets_path)

        item_props = self._get_item_properties(item)
        result = None

        if widget_config.groupings:
            result = self._pick_widget_from_groups(
                widget_config.groupings, item_props, slot
            )
        else:
            widgets = self.manager.get_widgets()
            if not widgets:
                xbmcgui.Dialog().notification(LANGUAGE(32147), LANGUAGE(32148))
                return None
            result = self._pick_widget_flat(widgets, item_props, slot)

        if result is None:
            return None

        if result is False:
            self._clear_widget_properties(item, prefix)
        else:
            self._log(f"Widget selected: {result.name}")
            self._set_widget_properties(item, prefix, result)

            if (
                self.dialog_mode in ("widgets", "customwidget")
                or self.dialog_mode.startswith("custom-widget")
            ):
                self.manager.set_label(self.menu_id, item.name, result.label)
                item.label = result.label
                if result.icon:
                    self.manager.set_icon(self.menu_id, item.name, result.icon)
                    item.icon = result.icon

        self._refresh_selected_item()
        return None if result is False else result

    def _prompt_widget_rename(self, item: MenuItem, prop_name: str, widget: Widget) -> None:
        """Prompt for a custom widget label after a pick, when the button opts in."""
        if widget.type == "custom":
            return
        if (
            self.dialog_mode in ("widgets", "customwidget")
            or self.dialog_mode.startswith("custom-widget")
        ):
            return

        default_label = resolve_label(widget.label)

        keyboard = xbmc.Keyboard(default_label, xbmc.getLocalizedString(13334))
        keyboard.doModal()
        if not keyboard.isConfirmed():
            return

        # space, because "" gets dropped and the default comes back
        new_label = keyboard.getText() or " "
        if new_label == default_label:
            return

        label_name = _label_property_name(prop_name)
        self._log(f"Renaming {label_name} to '{new_label}' on item {item.name}")
        self._set_item_property(item, label_name, new_label, apply_suffix=False)
        self._refresh_selected_item()

    def _set_widget_properties(self, item: MenuItem, prefix: str, widget: Widget) -> None:
        """Set widget properties on item with auto-populated values."""
        self._log(f"Setting widget properties for {prefix}: {widget.name}")

        base, suffix = _split_suffix(prefix)

        widget_path = widget.path.replace("{menuitem}", item.name)
        related: dict[str, str | None] = {
            f"{base}Label{suffix}": widget.label,
            f"{base}Path{suffix}": widget_path,
            f"{base}Type{suffix}": widget.type or "",
            f"{base}Target{suffix}": widget.target or "",
            f"{base}Source{suffix}": widget.source or "",
        }

        self._set_item_property(item, prefix, widget.name, related, apply_suffix=False)

        if widget.type != "custom" and self.manager is not None:
            self.manager.clear_custom_widget(self.menu_id, item.name, suffix)

    def _clear_widget_properties(self, item: MenuItem, prefix: str) -> None:
        """Clear all widget properties for a prefix."""
        self._log(f"Clearing widget properties for {prefix}")

        base, suffix = _split_suffix(prefix)

        related: dict[str, str | None] = {
            f"{base}Label{suffix}": None,
            f"{base}Path{suffix}": None,
            f"{base}Type{suffix}": None,
            f"{base}Target{suffix}": None,
            f"{base}Source{suffix}": None,
        }

        self._set_item_property(item, prefix, "", related, apply_suffix=False)

        if self.manager is not None:
            self.manager.clear_custom_widget(self.menu_id, item.name, suffix)

    def _handle_background_property(self, prop, item: MenuItem, prop_name: str) -> None:
        """Handle a background-type property."""
        if self.manager is None:
            return
        menu = self.manager.config.get_menu(self.menu_id)
        if menu and not menu.allow.backgrounds:
            xbmcgui.Dialog().notification(LANGUAGE(32143), LANGUAGE(32146))
            return

        prefix = prop_name
        current_bg = self._get_item_property(item, prefix)
        item_props = self._get_item_properties(item)
        positions: dict[str, int] = {}

        while True:
            bg = self._pick_background(item_props, current_bg, positions)

            if bg is None:
                return
            if bg is False:
                self._clear_background_properties(item, prefix)
                self._refresh_selected_item()
                return

            if bg.type == BackgroundType.BROWSE:
                path = self._browse_with_sources(
                    sources=bg.browse_sources,
                    title=resolve_label(bg.label),
                    browse_type=2,  # Image file
                    item_properties=item.properties,
                    default_path=bg.path,
                )
                if path:
                    self._set_background_properties_custom(item, prefix, bg, path)
                    self._refresh_selected_item()
                    return
                continue

            if bg.type == BackgroundType.MULTI:
                path = self._browse_with_sources(
                    sources=bg.browse_sources,
                    title=resolve_label(bg.label),
                    browse_type=0,  # Folder
                    item_properties=item.properties,
                    default_path=bg.path,
                )
                if path:
                    self._set_background_properties_custom(item, prefix, bg, path)
                    self._refresh_selected_item()
                    return
                continue

            if bg.type in (BackgroundType.PLAYLIST, BackgroundType.LIVE_PLAYLIST) and not bg.path:
                base, suffix = _split_suffix(prefix)
                current_playlist = self._get_item_property(item, f"{base}Path{suffix}")
                result = self._pick_playlist(
                    bg.sources, bg.label if bg.sources else "", current_playlist
                )
                if result:
                    path, display_label, playlist_type = result
                    self._set_background_properties_custom(
                        item, prefix, bg, path, display_label, playlist_type
                    )
                    self._refresh_selected_item()
                    return
                continue

            self._set_background_properties(item, prefix, bg)
            self._refresh_selected_item()
            return

    def _set_background_properties(self, item: MenuItem, prefix: str, bg) -> None:
        """Set background properties on item with auto-populated values."""
        self._log(f"Setting background properties for {prefix}: {bg.name}")

        base, suffix = _split_suffix(prefix)

        related: dict[str, str | None] = {
            f"{base}Label{suffix}": bg.label,
            f"{base}Path{suffix}": bg.path,
            f"{base}Type{suffix}": bg.type_name,
        }

        self._set_item_property(item, prefix, bg.name, related, apply_suffix=False)

    def _set_background_properties_custom(
        self,
        item: MenuItem,
        prefix: str,
        bg,
        custom_path: str,
        custom_label: str | None = None,
        playlist_type: str | None = None,
    ) -> None:
        """Set background properties with a user-browsed custom path."""
        self._log(f"Setting custom background for {prefix}: {bg.name} -> {custom_path}")

        base, suffix = _split_suffix(prefix)

        if bg.type in (BackgroundType.BROWSE, BackgroundType.MULTI):
            label = custom_label if custom_label else custom_path
            value = custom_path
        else:
            label = custom_label if custom_label else bg.label
            value = bg.name

        related: dict[str, str | None] = {
            f"{base}Label{suffix}": label,
            f"{base}Path{suffix}": custom_path,
            f"{base}Type{suffix}": bg.type_name,
        }
        if playlist_type:
            related[f"{base}PlaylistType{suffix}"] = playlist_type

        self._set_item_property(item, prefix, value, related, apply_suffix=False)

    def _clear_background_properties(self, item: MenuItem, prefix: str) -> None:
        """Clear all background properties for a prefix."""
        self._log(f"Clearing background properties for {prefix}")

        base, suffix = _split_suffix(prefix)

        related: dict[str, str | None] = {
            f"{base}Label{suffix}": None,
            f"{base}Path{suffix}": None,
            f"{base}Type{suffix}": None,
            f"{base}PlaylistType{suffix}": None,
        }

        self._set_item_property(item, prefix, "", related, apply_suffix=False)

    def _pick_playlist(
        self,
        sources: list | None = None,
        label_prefix: str = "",
        current_path: str = "",
    ) -> tuple[str, str, str] | None:
        """Show picker for available playlists."""
        if not sources:
            base = playlists_base_path()
            sources = [
                PlaylistSource(
                    label=xbmc.getLocalizedString(20012),
                    path=f"{base}video/",
                    icon="DefaultVideoPlaylists.png",
                ),
                PlaylistSource(
                    label=xbmc.getLocalizedString(20011),
                    path=f"{base}music/",
                    icon="DefaultMusicPlaylists.png",
                ),
                PlaylistSource(
                    label=LANGUAGE(32158),
                    path=f"{base}mixed/",
                    icon="DefaultPlaylist.png",
                ),
            ]

        prefix = resolve_label(label_prefix) if label_prefix else ""

        sources = [s for s in sources if xbmcvfs.exists(s.path)]
        if not sources:
            xbmcgui.Dialog().notification(LANGUAGE(32154), LANGUAGE(32155))
            return None

        if len(sources) == 1:
            return self._pick_playlist_from_source(sources[0], prefix, current_path)

        while True:
            source = self._pick_playlist_source(sources, prefix)
            if source is None:
                return None

            result = self._pick_playlist_from_source(source, prefix, current_path)
            if result is not None:
                return result

    def _pick_playlist_source(
        self,
        sources: list[PlaylistSource],
        prefix: str,
    ) -> PlaylistSource | None:
        """Pick which source to scan, skipping the dialog when the skin lists one."""
        if len(sources) == 1:
            return sources[0]

        listitems = []
        for source in sources:
            label = resolve_label(source.label) if source.label else source.path
            listitem = xbmcgui.ListItem(f"{label} >", offscreen=True)
            if source.icon:
                listitem.setArt({"icon": source.icon})
            listitems.append(listitem)

        title = f"{LANGUAGE(32181)} {prefix}" if prefix else LANGUAGE(32157)
        selected = picker_select("playlist", title, listitems, useDetails=True)
        if selected == -1:
            return None
        return sources[selected]

    def _pick_playlist_from_source(
        self,
        source: PlaylistSource,
        prefix: str,
        current_path: str,
    ) -> tuple[str, str, str] | None:
        """Pick a playlist from one source, returning its path, label and type."""
        playlists = []

        for raw_label, path in scan_playlist_files(source.path):
            label = raw_label
            playlist_type = ""
            if path.endswith(".xsp"):
                xsp_name, playlist_type = _parse_smart_playlist(path)
                if xsp_name:
                    label = xsp_name

            display_label = f"{prefix}: {label}" if prefix else label
            playlists.append((display_label, path, source.icon, playlist_type))

        playlists.sort(key=lambda p: p[0].casefold())

        preselect = -1
        if current_path:
            for i, (_label, path, _icon, _type) in enumerate(playlists):
                if path == current_path:
                    preselect = i
                    break

        if not playlists:
            xbmcgui.Dialog().notification(LANGUAGE(32154), LANGUAGE(32156))
            return None

        listitems = []
        for label, _path, icon, _content_type in playlists:
            listitem = xbmcgui.ListItem(label, offscreen=True)
            listitem.setArt({"icon": icon})
            listitems.append(listitem)

        title = resolve_label(source.label) if source.label else LANGUAGE(32157)
        selected = picker_select("playlist", title, listitems, useDetails=True, preselect=preselect)

        if selected == -1:
            return None

        return (playlists[selected][1], playlists[selected][0], playlists[selected][3])

    def _handle_toggle_property(self, prop, item: MenuItem, button, prop_name: str) -> None:
        """Handle a toggle-type property."""
        toggle_value = (prop.value if prop else "") or "True"
        current_value = item.properties.get(prop_name, "")
        if current_value == toggle_value:
            self._log(f"Toggling {prop_name} OFF for item {item.name}")
            self._set_item_property(item, prop_name, None, apply_suffix=False)
        else:
            self._log(f"Toggling {prop_name} ON for item {item.name}")
            self._set_item_property(item, prop_name, toggle_value, apply_suffix=False)

        self._refresh_selected_item()

    def _handle_text_property(self, item: MenuItem, button, prop_name: str) -> None:
        """Handle a text-type property via keyboard input."""
        current_value = resolve_label(item.properties.get(prop_name, ""))
        title = resolve_label(button.title) if button.title else prop_name

        keyboard = xbmc.Keyboard(current_value, title)
        keyboard.doModal()
        if not keyboard.isConfirmed():
            return

        new_value = keyboard.getText()
        if new_value:
            self._log(f"Setting text property {prop_name}={new_value} on item {item.name}")
            self._set_item_property(item, prop_name, new_value, apply_suffix=False)
        else:
            self._log(f"Clearing text property {prop_name} on item {item.name}")
            self._set_item_property(item, prop_name, None, apply_suffix=False)

        self._refresh_selected_item()

    def _handle_number_property(self, item: MenuItem, button, prop_name: str) -> None:
        """Handle a number-type property via numeric input dialog."""
        current_value = item.properties.get(prop_name, "")
        title = resolve_label(button.title) if button.title else prop_name

        result = xbmcgui.Dialog().input(title, current_value, type=xbmcgui.INPUT_NUMERIC)
        if not result and result != "0":
            return

        self._log(f"Setting number property {prop_name}={result} on item {item.name}")
        self._set_item_property(item, prop_name, result, apply_suffix=False)
        self._refresh_selected_item()

    def _handle_options_property(self, prop, item: MenuItem, button, prop_name: str) -> bool:
        """Handle a regular property with options list."""
        item_props = self._get_item_properties(item)
        use_suffix = button.suffix and self.property_suffix

        visible_options = []
        for opt in prop.options:
            condition = opt.condition
            if condition and use_suffix:
                condition = apply_suffix_transform(condition, self.property_suffix)
            if not condition or evaluate_condition(condition, item_props):
                visible_options.append(opt)

        if not visible_options:
            xbmcgui.Dialog().notification(LANGUAGE(32159), LANGUAGE(32160))
            return True

        listitems = []
        if button.show_none:
            none_item = xbmcgui.ListItem(xbmc.getLocalizedString(231), offscreen=True)
            none_item.setArt({"icon": "DefaultAddonNone.png"})
            listitems.append(none_item)

        for opt in visible_options:
            listitem = xbmcgui.ListItem(resolve_label(opt.label), offscreen=True)
            icon = "DefaultAddonNone.png"
            if opt.icons:
                for icon_variant in opt.icons:
                    icon_cond = icon_variant.condition
                    if icon_cond and use_suffix:
                        icon_cond = apply_suffix_transform(icon_cond, self.property_suffix)
                    if not icon_cond or evaluate_condition(icon_cond, item_props):
                        icon = icon_variant.path
                        break
            listitem.setArt({"icon": icon})
            listitems.append(listitem)

        title = resolve_label(button.title) if button.title else prop_name
        current_value = item.properties.get(prop_name, "")
        preselect = -1
        offset = 1 if button.show_none else 0
        for i, opt in enumerate(visible_options):
            if opt.value == current_value:
                preselect = i + offset
                break

        selected = picker_select(
            "property", title, listitems, useDetails=button.show_icons, preselect=preselect
        )

        if selected == -1:
            return True

        if button.show_none and selected == 0:
            self._log(f"Clearing property {prop_name} on item {item.name}")
            self._set_item_property(item, prop_name, None, apply_suffix=False)
        else:
            offset = 1 if button.show_none else 0
            value = visible_options[selected - offset].value
            self._log(f"Setting property {prop_name}={value} on item {item.name}")
            self._set_item_property(item, prop_name, value, apply_suffix=False)

        if self.manager:
            self._log(f"has_changes after property set: {self.manager.has_changes()}")
        self._refresh_selected_item()
        return True
