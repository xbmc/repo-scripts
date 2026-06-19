"""Property management mixin - widget, background, toggle, options properties."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from ..log import get_logger

_log = get_logger("Properties")

try:
    import xbmc
    import xbmcgui
    import xbmcvfs

    IN_KODI = True
except ImportError:
    IN_KODI = False


def _get_playlists_base_path() -> str:
    """Get the playlist base path from Kodi settings.

    Returns the user-configured playlist path, or the default
    special://profile/playlists/ if not set.
    """
    if not IN_KODI:
        return "special://profile/playlists/"

    try:
        request = {
            "jsonrpc": "2.0",
            "method": "Settings.GetSettingValue",
            "params": {"setting": "system.playlistspath"},
            "id": 1,
        }
        response = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
        if "result" in response and response["result"].get("value"):
            base = response["result"]["value"]
            if not base.endswith("/"):
                base += "/"
            return base
    except Exception:
        pass
    return "special://profile/playlists/"


def _resolve_playlist_path(filepath: str) -> str | None:
    """Resolve a playlist path to an actual readable file path.

    Handles special://videoplaylists/ which is a multipath combining
    video and mixed playlist directories.
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
    """Parse a smart playlist (.xsp file) for name and type.

    Returns:
        Tuple of (name, playlist_type). Falls back to ("", "") on error.
        playlist_type is the raw type: movies, tvshows, episodes, musicvideos,
        songs, albums, artists, mixed, etc.
    """
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
from ..playlists import unpack_multipath
from ..providers import scan_playlist_files

if TYPE_CHECKING:
    from ..manager import MenuManager
    from ..models import PropertySchema


class PropertiesMixin:
    """Mixin providing property management - widget, background, toggle, options.

    This mixin implements:
    - Property button handling from schema
    - Widget property setting/clearing
    - Background property setting/clearing
    - Toggle property handling
    - Options list property handling
    - Playlist picker

    Requires DialogBaseMixin and PickersMixin to be mixed in first.
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
            mask: str = "",
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
            self, item_props: dict[str, str], current_value: str = ""
        ) -> Background | None | Literal[False]: ...

    def _check_requires(self, item: MenuItem, requires_name: str) -> bool:
        """Check if a required property is satisfied.

        For widget/background requirements, also accepts the Path variant
        as proof the property is configured (e.g., widgetPath for widget).

        Args:
            item: The menu item to check
            requires_name: The required property name (e.g., "widget", "widget.2")

        Returns:
            True if requirement is satisfied, False otherwise
        """
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
        """Handle a property button click from the schema.

        Args:
            button_id: The control button ID that was clicked

        Returns:
            True if handled, False if not a property button
        """
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
            self._handle_widget_property(prop, item, prop_name)
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

        return self._handle_options_property(prop, item, button, prop_name)

    def _handle_widget_property(self, prop, item: MenuItem, prop_name: str) -> None:
        """Handle a widget-type property.

        Shows widget picker and auto-populates related properties:
        - {prefix}Name, {prefix}Path, {prefix}Type, {prefix}Target

        For custom widgets, the user selects "Custom list" which sets widgetType=custom.
        When the subdialog closes, the onclose action checks this condition and opens
        the custom widget menu editor automatically.

        Args:
            prop: The property schema
            item: The menu item
            prop_name: Effective property name (may include suffix like "widget.2")
        """
        if self.manager is None:
            return
        menu = self.manager.config.get_menu(self.menu_id)
        if menu and not menu.allow.widgets:
            xbmcgui.Dialog().notification(LANGUAGE(32143), LANGUAGE(32144))
            return

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
                return
            result = self._pick_widget_flat(widgets, item_props, slot)

        if result is None:
            return

        if result is False:
            self._clear_widget_properties(item, prefix)
        else:
            self._log(f"Widget selected: {result.name}")
            self._set_widget_properties(item, prefix, result)

            if self.dialog_mode in ("widgets", "customwidget") or self.dialog_mode.startswith("custom-widget"):
                self.manager.set_label(self.menu_id, item.name, result.label)
                item.label = result.label
                if result.icon:
                    self.manager.set_icon(self.menu_id, item.name, result.icon)
                    item.icon = result.icon

        self._refresh_selected_item()

    def _set_widget_properties(self, item: MenuItem, prefix: str, widget: Widget) -> None:
        """Set widget properties on item with auto-populated values.

        Args:
            item: The menu item
            prefix: Property name prefix (e.g., "widget" or "widget.2")
            widget: The Widget object
        """
        self._log(f"Setting widget properties for {prefix}: {widget.name}")

        if "." in prefix:
            base, suffix = prefix.rsplit(".", 1)
            suffix = f".{suffix}"
        else:
            base = prefix
            suffix = ""

        widget_path = widget.path.replace("{menuitem}", item.name)
        related: dict[str, str | None] = {
            f"{base}Label{suffix}": resolve_label(widget.label),
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

        if "." in prefix:
            base, suffix = prefix.rsplit(".", 1)
            suffix = f".{suffix}"
        else:
            base = prefix
            suffix = ""

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
        """Handle a background-type property.

        Shows background picker and auto-populates related properties:
        - {prefix}Name, {prefix}Path

        For type="browse" backgrounds, opens single image browser.
        For type="multi" backgrounds, opens folder browser.

        Args:
            prop: The property schema
            item: The menu item
            prop_name: Effective property name (may include suffix)
        """
        if self.manager is None:
            return
        menu = self.manager.config.get_menu(self.menu_id)
        if menu and not menu.allow.backgrounds:
            xbmcgui.Dialog().notification(LANGUAGE(32143), LANGUAGE(32146))
            return

        prefix = prop_name
        current_bg = self._get_item_property(item, prefix)
        item_props = self._get_item_properties(item)

        while True:
            bg = self._pick_background(item_props, current_value=current_bg)

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
                    mask=".jpg|.png|.gif",
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
                current_playlist = self._get_item_property(item, f"{prefix}Path")
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

        related: dict[str, str | None] = {
            f"{prefix}Label": resolve_label(bg.label),
            f"{prefix}Path": bg.path,
            f"{prefix}Type": bg.type_name,
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
        """Set background properties with a user-browsed custom path.

        Used for type="browse" (single image), type="multi" (folder),
        and type="playlist" backgrounds.

        Args:
            item: The menu item
            prefix: Property name prefix
            bg: The Background object
            custom_path: User-selected path
            custom_label: Optional custom label (e.g., "Live Background: Random Movies")
            playlist_type: Optional playlist content type ("video" or "music")
        """
        self._log(f"Setting custom background for {prefix}: {bg.name} -> {custom_path}")

        if bg.type in (BackgroundType.BROWSE, BackgroundType.MULTI):
            label = custom_label if custom_label else custom_path
            value = custom_path
        else:
            label = custom_label if custom_label else resolve_label(bg.label)
            value = bg.name

        related: dict[str, str | None] = {
            f"{prefix}Label": label,
            f"{prefix}Path": custom_path,
            f"{prefix}Type": bg.type_name,
        }
        if playlist_type:
            related[f"{prefix}PlaylistType"] = playlist_type

        self._set_item_property(item, prefix, value, related, apply_suffix=False)

    def _clear_background_properties(self, item: MenuItem, prefix: str) -> None:
        """Clear all background properties for a prefix."""
        self._log(f"Clearing background properties for {prefix}")

        related: dict[str, str | None] = {
            f"{prefix}Label": None,
            f"{prefix}Path": None,
            f"{prefix}Type": None,
            f"{prefix}PlaylistType": None,
        }

        self._set_item_property(item, prefix, "", related, apply_suffix=False)

    def _pick_playlist(
        self,
        sources: list | None = None,
        label_prefix: str = "",
        current_path: str = "",
    ) -> tuple[str, str, str] | None:
        """Show picker for available playlists.

        Args:
            sources: List of PlaylistSource objects defining where to scan.
                     If None/empty, uses default user playlist locations.
            label_prefix: Prefix to show on all playlist labels (e.g., "Live Background")
            current_path: Current playlist path to preselect

        Returns:
            Tuple of (path, display_label, playlist_type) or None if cancelled.
            display_label includes the prefix if provided.
            playlist_type is the raw type from the .xsp file (movies, tvshows, etc.)
        """
        if not sources:
            base = _get_playlists_base_path()
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
        if len(sources) == 1:
            return sources[0]

        listitems = []
        for source in sources:
            label = resolve_label(source.label) if source.label else source.path
            listitem = xbmcgui.ListItem(label)
            if source.icon:
                listitem.setArt({"icon": source.icon})
            listitems.append(listitem)

        title = f"{LANGUAGE(32181)} {prefix}" if prefix else LANGUAGE(32157)
        selected = xbmcgui.Dialog().select(title, listitems, useDetails=True)
        if selected == -1:
            return None
        return sources[selected]

    def _pick_playlist_from_source(
        self,
        source: PlaylistSource,
        prefix: str,
        current_path: str,
    ) -> tuple[str, str, str] | None:
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
            listitem = xbmcgui.ListItem(label)
            listitem.setArt({"icon": icon})
            listitems.append(listitem)

        title = resolve_label(source.label) if source.label else LANGUAGE(32157)
        selected = xbmcgui.Dialog().select(title, listitems, useDetails=True, preselect=preselect)

        if selected == -1:
            return None

        return (playlists[selected][1], playlists[selected][0], playlists[selected][3])

    def _handle_toggle_property(self, prop, item: MenuItem, button, prop_name: str) -> None:
        """Handle a toggle-type property.

        Toggles between a value and empty (cleared).
        Uses prop.value if set, otherwise defaults to "True".

        Args:
            prop: The property schema
            item: The menu item
            button: The button mapping
            prop_name: Effective property name (may include suffix)
        """
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
        """Handle a regular property with options list.

        Args:
            prop: The property schema
            item: The menu item
            button: The button mapping
            prop_name: Effective property name (may include suffix)
        """
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
            none_item = xbmcgui.ListItem(xbmc.getLocalizedString(231))
            none_item.setArt({"icon": "DefaultAddonNone.png"})
            listitems.append(none_item)

        for opt in visible_options:
            listitem = xbmcgui.ListItem(resolve_label(opt.label))
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

        selected = xbmcgui.Dialog().select(
            title, listitems, useDetails=button.show_icons, preselect=preselect
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
