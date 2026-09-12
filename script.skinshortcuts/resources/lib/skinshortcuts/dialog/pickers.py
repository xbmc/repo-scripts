"""Picker dialogs mixin - shortcut, widget, background pickers."""

from __future__ import annotations

import contextlib
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Literal, Protocol, runtime_checkable

try:
    import xbmc
    import xbmcgui

    IN_KODI = True
except ImportError:
    IN_KODI = False


def _check_visible(visible: str) -> bool:
    """Evaluate a Kodi visibility condition."""
    if not visible:
        return True
    if not IN_KODI:
        return True
    return xbmc.getCondVisibility(visible)


@runtime_checkable
class PickerItem(Protocol):
    """Protocol for leaf items in picker hierarchy (Shortcut, Widget, Background)."""

    name: str
    label: str
    icon: str
    condition: str
    visible: str


@runtime_checkable
class PickerGroup(Protocol):
    """Protocol for group items in picker hierarchy."""

    name: str
    label: str
    icon: str
    condition: str
    visible: str
    items: list


from ..constants import (
    ADDONS_SOURCE_MAP,
    TARGET_MAP,
    WINDOW_MAP,
    extract_path_from_action,
    extract_window_from_action,
)
from ..loaders import evaluate_condition, load_groupings
from ..localize import LANGUAGE, resolve_label
from ..log import get_logger
from ..playlists import (
    SORT_OPTIONS,
    SortOption,
    build_smartplaylist_xml,
    display_options,
    path_has_content,
    save_playlist,
    unpack_multipath,
)
from ..models import (
    Action,
    Background,
    BackgroundGroup,
    BackgroundType,
    Content,
    Input,
    MenuItem,
    Shortcut,
    ShortcutGroup,
    Widget,
    WidgetGroup,
)
from ..providers import ContentProvider, get_browse_provider, library_node_type

if TYPE_CHECKING:
    from ..manager import MenuManager
    from ..providers.content import ResolvedShortcut


from ..models.menu import IconOverrides

log = get_logger("Pickers")

PLACEHOLDER_PREFIX = "content-placeholder-"


SLOW_RESOLVE_MS = 250


def _ms(start: float) -> float:
    """Elapsed milliseconds, for the picker's timing lines."""
    return (time.monotonic() - start) * 1000


def _log_slow_resolve(content: Content, rows: int, start: float) -> None:
    """Name the <content> element when resolving it takes long enough to notice."""
    elapsed = _ms(start)
    if elapsed >= SLOW_RESOLVE_MS:
        log.debug(
            f"slow content: source={content.source} target={content.target} "
            f"rows={rows} {elapsed:.0f}ms"
        )


def picker_kind(leaf_types: tuple) -> str:
    """skinshortcuts-picker value for a hierarchy picker, from what it is picking."""
    if Widget in leaf_types:
        return "widget"
    if Background in leaf_types:
        return "background"
    return "shortcut"


@contextlib.contextmanager
def picker_context(kind: str):
    """Set Window(Home).Property(skinshortcuts-picker)=kind for the duration of the block.

    Marker goes on Home, not the dialog: while select() is up the active window is
    DialogSelect, so a bare Window.Property() would resolve there, not against our dialog.
    """
    home = xbmcgui.Window(10000)
    home.setProperty("skinshortcuts-picker", kind)
    try:
        yield
    finally:
        home.clearProperty("skinshortcuts-picker")


def picker_select(kind: str, *args, **kwargs):
    """Dialog().select() with the skinshortcuts-picker marker set for its lifetime."""
    with picker_context(kind):
        return xbmcgui.Dialog().select(*args, **kwargs)


def _group_count(
    item: object,
    item_props: dict[str, str],
    content_resolver: Callable[[Content], list] | None = None,
) -> str:
    """Rows a group will show; empty when a content element cannot be counted."""
    total = 0
    for child in getattr(item, "items", []):
        if not _check_visible(getattr(child, "visible", "")):
            continue
        condition = getattr(child, "condition", "")
        if condition and not evaluate_condition(condition, item_props):
            continue
        if isinstance(child, Content):
            if content_resolver is None:
                return ""
            start = time.monotonic()
            resolved = content_resolver(child)
            _log_slow_resolve(child, len(resolved), start)
            if child.folder:
                # folder row is dropped when it resolves to nothing
                if resolved or _browse_placeholder_for_content(child):
                    total += 1
                continue
            total += len(resolved)
            continue
        if getattr(child, "name", "").startswith(PLACEHOLDER_PREFIX):
            continue
        if getattr(child, "flat", False):
            nested = _group_count(child, item_props, content_resolver)
            if not nested:
                return ""
            total += int(nested)
            continue
        total += 1
    return str(total)


def stamp_picker_props(
    listitem: xbmcgui.ListItem,
    item: object,
    item_props: dict[str, str] | None = None,
    content_resolver: Callable[[Content], list] | None = None,
) -> None:
    """Stamp an option's metadata as ListItem properties for DialogSelect layouts."""
    if isinstance(item, Widget):
        props = item.to_properties()
        props["path"] = item.path
        props["type"] = item.type
    elif isinstance(item, Background):
        props = item.to_properties()
        props["path"] = item.path
        props["type"] = item.type_name
    elif isinstance(item, Shortcut):
        props = {
            "path": item.path or (extract_path_from_action(item.action) if item.action else ""),
            "type": item.type,
            "action": item.action or "",
        }
    elif isinstance(item, (WidgetGroup, ShortcutGroup, BackgroundGroup)):
        props = {
            "path": item.path,
            "type": "group",
            "count": _group_count(item, item_props or {}, content_resolver),
        }
    else:
        return

    props["name"] = item.name
    for key, value in props.items():
        listitem.setProperty(key, value)


def _drills_down(item: object) -> bool:
    """Leaf that opens another dialog rather than committing on click."""
    if isinstance(item, Background):
        if item.type in (BackgroundType.BROWSE, BackgroundType.MULTI):
            return True
        playlist = (BackgroundType.PLAYLIST, BackgroundType.LIVE_PLAYLIST)
        return item.type in playlist and not item.path
    return isinstance(item, (Shortcut, Widget)) and bool(item.browse and item.path)


def _content_folder_path(content: Content) -> str:
    """Real browsable path behind an addons content folder; empty for other sources."""
    if content.source.lower() != "addons":
        return ""
    target = content.target.lower() if content.target else "video"
    entry = ADDONS_SOURCE_MAP.get(target)
    return entry[0] if entry else ""


def _browse_placeholder_for_content(
    content: Content, *, as_widget: bool = False, parent_label: str = "", parent_icon: str = ""
) -> Shortcut | Widget | None:
    """Create a "Create menu item to here" placeholder for an addons content section.

    Shortcut or Widget pointing at addons://sources/<type>/, so a menu item can
    commit to the addon category root with no addons of that type installed. The
    picker shows this row as string 32058, so the label and icon set here are the
    ones the committed item gets.
    """
    if content.source.lower() != "addons":
        return None

    target = content.target.lower() if content.target else "video"
    if target not in ADDONS_SOURCE_MAP:
        return None

    path, window = ADDONS_SOURCE_MAP[target]
    name = f"{PLACEHOLDER_PREFIX}{content.source}-{target}"
    icon = content.icon or parent_icon or "DefaultFolder.png"

    label = content.label or content.folder or parent_label or LANGUAGE(32058)

    if as_widget:
        return Widget(
            name=name,
            label=label,
            path=path,
            type="addons",
            target=window,
            icon=icon,
            source="addon",
        )

    return Shortcut(
        name=name,
        label=label,
        actions=[f"ActivateWindow({window},{path},return)"],
        icon=icon,
    )


class PickersMixin:
    """Mixin providing picker dialogs for shortcuts and widgets.

    Requires DialogBaseMixin first.
    """

    menu_id: str
    shortcuts_path: str
    manager: MenuManager | None
    items: list[MenuItem]
    _content_provider: ContentProvider | None = None

    if TYPE_CHECKING:
        def _get_selected_item(self) -> MenuItem | None: ...
        def _get_item_properties(self, item: MenuItem) -> dict[str, str]: ...
        def _refresh_selected_item(self) -> None: ...
        def _log(self, msg: str) -> None: ...

    def _icon_overrides(self) -> IconOverrides:
        """Icon override map from the active skin config, empty if none loaded."""
        if self.manager and self.manager.config:
            return self.manager.config.icon_overrides
        return IconOverrides()

    def _choose_shortcut(self) -> None:
        """Choose a shortcut from groupings."""
        if not self.manager:
            return

        item = self._get_selected_item()
        if not item:
            return

        menus_path = Path(self.shortcuts_path) / "menus.xml"
        groups = load_groupings(menus_path, self.menu_id)

        if not groups:
            xbmcgui.Dialog().notification(
                LANGUAGE(32179),
                LANGUAGE(32180),
            )
            return

        item_props = self._get_item_properties(item)

        shortcut = self._pick_shortcut(groups, item_props)
        if shortcut:
            if shortcut.source_media:
                action = self._source_playlist_action(shortcut, item)
                actions = [action] if action else None
            else:
                actions = self._get_shortcut_actions(shortcut)
            if actions is None:
                return

            result_label = shortcut.label
            self.manager.set_label(self.menu_id, item.name, result_label)
            item.label = result_label
            self.manager.set_action(self.menu_id, item.name, actions)
            item.actions = [Action(action=a) for a in actions] if actions else []

            if shortcut.icon:
                self.manager.set_icon(self.menu_id, item.name, shortcut.icon)
                item.icon = shortcut.icon

            if shortcut.item_visible:
                self.manager.set_visible(self.menu_id, item.name, shortcut.item_visible)
                item.visible = shortcut.item_visible

            previous_submenu = item.submenu
            new_submenu: str | None = None
            if shortcut.name:
                template = self.manager.config.get_default_menu(shortcut.name)
                if template and template.is_submenu:
                    new_submenu = shortcut.name

            if new_submenu != previous_submenu:
                self.manager.set_submenu(self.menu_id, item.name, new_submenu)
                item.submenu = new_submenu
                self.manager.drop_per_item_submenu(self.menu_id, item.name)

            self._refresh_selected_item()

    def _get_shortcut_actions(self, shortcut: Shortcut) -> list[str] | None:
        """Get actions from shortcut, showing playlist choice dialog if applicable."""
        if shortcut.action_play:
            action = self._choose_playlist_action(shortcut)
            return [action] if action else None
        if shortcut.browse and shortcut.path:
            return [shortcut.get_action()]
        return shortcut.actions if shortcut.actions else None

    def _choose_playlist_action(self, shortcut: Shortcut) -> str | None:
        """Show dialog asking what to do with a playlist shortcut."""
        if shortcut.action_party:
            result = xbmcgui.Dialog().yesnocustom(
                LANGUAGE(32040),
                LANGUAGE(32060),
                customlabel=xbmc.getLocalizedString(589),
                nolabel=LANGUAGE(32061),
                yeslabel=LANGUAGE(32062),
            )
            if result == -1:
                return None
            if result == 0:
                return shortcut.action
            if result == 1:
                return shortcut.action_play
            return shortcut.action_party

        result = xbmcgui.Dialog().yesno(
            LANGUAGE(32040),
            LANGUAGE(32060),
            nolabel=LANGUAGE(32061),
            yeslabel=LANGUAGE(32062),
        )
        return shortcut.action_play if result else shortcut.action

    def _source_playlist_action(self, shortcut: Shortcut, item: MenuItem) -> str | None:
        """Pick how to show a source: Files view, or a path-filtered library playlist.

        Returns the action string, or None if cancelled. The option list is built from
        the source's detected library domain; an exclude with no remaining content falls
        back to Files view rather than an empty playlist.
        """
        paths = unpack_multipath(shortcut.path)
        options = display_options(shortcut.source_media, paths)
        if len(options) == 1:
            return shortcut.get_action()  # not a library source -> Files view, no dialog

        labels = [
            xbmc.getLocalizedString(o.label_id) if o.core else LANGUAGE(o.label_id)
            for o in options
        ]
        choice = picker_select("sourceview", LANGUAGE(32078), labels)
        if choice == -1:
            return None
        option = options[choice]
        if not option.media_type:
            return shortcut.get_action()

        # only an exclude can legitimately come back empty
        if option.exclude and not path_has_content(option.media_type, paths, exclude=True):
            use_files = xbmcgui.Dialog().yesno(
                LANGUAGE(32078),
                LANGUAGE(32205),
                nolabel=xbmc.getLocalizedString(222),
                yeslabel=LANGUAGE(32079),
            )
            return shortcut.get_action() if use_files else None

        sort = self._pick_sort()
        if sort is None:
            return None

        xml = build_smartplaylist_xml(
            option.media_type,
            shortcut.label,
            paths,
            exclude=option.exclude,
            sort_field=sort.field,
            sort_order=sort.direction,
        )
        path = save_playlist(self.menu_id, item.name, xml)
        window = WINDOW_MAP.get(shortcut.source_media, "Videos")
        return f"ActivateWindow({window},{path},return)"

    def _pick_sort(self) -> SortOption | None:
        """Pick a sort order for a generated playlist. None if cancelled."""
        labels = [xbmc.getLocalizedString(o.label_id) for o in SORT_OPTIONS]
        choice = picker_select("sort", LANGUAGE(32203), labels)
        if choice == -1:
            return None
        return SORT_OPTIONS[choice]

    def _pick_shortcut(
        self, groups: list[Shortcut | ShortcutGroup | Content | Input], item_props: dict[str, str]
    ) -> Shortcut | None:
        """Pick a shortcut from groupings using generic hierarchy picker."""
        result = self._pick_from_hierarchy(
            groups,
            item_props,
            title=LANGUAGE(32043),
            leaf_types=(Shortcut,),
            group_types=(ShortcutGroup,),
            default_leaf_icon="DefaultShortcut.png",
            default_group_icon="DefaultFolder.png",
            show_none=False,
            content_resolver=self._resolve_content_to_shortcuts,
            create_folder_group=lambda label, items, icon, path: ShortcutGroup(
                name=f"folder-{label}",
                label=label,
                icon=icon or "DefaultFolder.png",
                items=items,
                path=path,
            ),
        )
        return result if isinstance(result, Shortcut) else None

    def _pick_widget_from_groups(
        self,
        items: list[WidgetGroup | Widget | Content],
        item_props: dict[str, str],
        slot: str = "",
    ) -> Widget | None | Literal[False]:
        """Widget picker with back navigation over widgets, groups, and content.

        Returns the chosen Widget, None if cancelled, False if "None" picked.
        """
        current_widget = item_props.get(slot, "")
        items = self._filter_widgets_by_slot(items, slot)

        result = self._pick_from_hierarchy(
            items,
            item_props,
            title=LANGUAGE(32044),
            leaf_types=(Widget,),
            group_types=(WidgetGroup,),
            default_leaf_icon="DefaultAddonNone.png",
            default_group_icon="DefaultFolder.png",
            show_none=True,
            current_value=current_widget,
            content_resolver=self._resolve_content_to_widgets,
            create_folder_group=lambda label, grp_items, icon, path: WidgetGroup(
                name=f"folder-{label}",
                label=label,
                icon=icon or "DefaultFolder.png",
                items=grp_items,
                path=path,
            ),
        )

        return result

    def _pick_widget_flat(
        self, widgets: list, item_props: dict[str, str] | None = None, slot: str = ""
    ) -> Widget | None | Literal[False]:
        """Pick from a flat widget list. False when the user picks "None"."""
        current_widget = item_props.get(slot, "") if item_props else ""
        preselect = -1
        overrides = self._icon_overrides()

        listitems = []
        none_item = xbmcgui.ListItem(xbmc.getLocalizedString(231), offscreen=True)
        none_icon = overrides.get("DefaultAddonNone.png", "DefaultAddonNone.png")
        none_item.setArt({"icon": resolve_label(none_icon)})
        listitems.append(none_item)

        for i, w in enumerate(widgets):
            listitem = xbmcgui.ListItem(resolve_label(w[1]), offscreen=True)
            icon = w[2] if len(w) > 2 and w[2] else "DefaultAddonNone.png"
            listitem.setArt({"icon": resolve_label(overrides.get(icon, icon))})
            if self.manager is not None:
                widget_obj = self.manager.config.get_widget(w[0])
                if widget_obj is not None:
                    stamp_picker_props(listitem, widget_obj)
            listitems.append(listitem)
            if preselect == -1 and w[0] == current_widget:
                preselect = i + 1  # +1 for "None" option

        selected = picker_select(
            "widget", LANGUAGE(32044), listitems, useDetails=True, preselect=preselect
        )

        if selected == -1:
            return None
        if selected == 0:
            return False

        widget_name = widgets[selected - 1][0]
        if self.manager is None:
            return None
        return self.manager.config.get_widget(widget_name)

    def _get_content_provider(self) -> ContentProvider:
        """One provider per dialog, so its cache outlives a single picker redraw."""
        if self._content_provider is None:
            self._content_provider = ContentProvider(icon_overrides=self._icon_overrides())
        return self._content_provider

    def _resolve_content_to_widgets(self, content: Content) -> list[Widget]:
        """Resolve a Content reference to a list of Widget objects for the picker.

        Script-only addons resolve to a launcher, which lists nothing, so they are
        offered as shortcuts but never as widget content.
        """
        resolved = self._get_content_provider().resolve(content)

        source = content.source.rstrip("s") if content.source.endswith("s") else content.source

        widgets = []
        for item in resolved:
            if content.source.lower() == "addons" and not item.browse_path:
                continue

            path = item.browse_path or extract_path_from_action(item.action)
            widget = Widget(
                name=f"dynamic-{content.source}-{len(widgets)}",
                label=item.label,
                path=path,
                type=item.content_type,
                target=self._widget_target_window(item, content.target),
                icon=item.icon,
                source=source,
                browse=bool(item.browse_path),
            )
            widgets.append(widget)

        return widgets

    def _resolve_content_to_shortcuts(self, content: Content) -> list[Shortcut]:
        """Resolve a Content reference to a list of Shortcut objects for the picker."""
        resolved = self._get_content_provider().resolve(content)

        shortcuts = []
        for item in resolved:
            shortcut = Shortcut(
                name=f"dynamic-{content.source}-{len(shortcuts)}",
                label=item.label,
                actions=[item.action] if item.action else [],
                path=item.browse_path,
                browse=item.browse_window,
                type=item.label2,
                icon=item.icon,
                action_play=item.action_play,
                action_party=item.action_party,
                source_media=item.source_media,
            )
            shortcuts.append(shortcut)

        return shortcuts

    def _map_target_to_window(self, target: str) -> str:
        """Map content target to widget target window."""
        if not target:
            return "videos"

        window = TARGET_MAP.get(target.lower())
        if window is None:
            log.debug(f"target '{target}' is not a known window, using videos")
            return "videos"
        return window

    def _widget_target_window(self, item: ResolvedShortcut, content_target: str) -> str:
        """Window the provider put this item in, falling back to the content target.

        Per item, because one content block can span windows: source="nodes"
        target="library" resolves to a video entry and a music entry. A favourite
        can name any window at all, so anything non-media takes the fallback.
        """
        window = item.browse_window or extract_window_from_action(item.action)
        mapped = TARGET_MAP.get(window.lower()) if window else None

        return mapped or self._map_target_to_window(content_target)

    def _pick_widget_type(self, addon_type: str) -> str | None:
        """Pick a widget content type for an addon category."""
        # one possible type, nothing to ask
        if addon_type in ("pictures", "games"):
            return addon_type

        if addon_type == "video":
            types = [
                ("movies", xbmc.getLocalizedString(342), "DefaultMovies.png"),
                ("tvshows", xbmc.getLocalizedString(20343), "DefaultTVShows.png"),
                ("episodes", xbmc.getLocalizedString(20360), "DefaultTVShows.png"),
                ("musicvideos", xbmc.getLocalizedString(20389), "DefaultMusicVideos.png"),
                ("videos", xbmc.getLocalizedString(3), "DefaultVideo.png"),
            ]
        elif addon_type == "audio":
            types = [
                ("songs", xbmc.getLocalizedString(134), "DefaultMusicSongs.png"),
                ("albums", xbmc.getLocalizedString(132), "DefaultMusicAlbums.png"),
                ("artists", xbmc.getLocalizedString(133), "DefaultMusicArtists.png"),
                ("music", xbmc.getLocalizedString(2), "DefaultAudio.png"),
            ]
        else:
            types = [
                ("programs", xbmc.getLocalizedString(350), "DefaultAddonProgram.png"),
                ("files", xbmc.getLocalizedString(744), "DefaultFile.png"),
            ]

        overrides = self._icon_overrides()
        listitems = []
        for _type_id, label, icon in types:
            listitem = xbmcgui.ListItem(label, offscreen=True)
            listitem.setArt({"icon": resolve_label(overrides.get(icon, icon))})
            listitems.append(listitem)

        selected = picker_select("widgettype", LANGUAGE(32140), listitems, useDetails=True)

        if selected == -1:
            return None

        return types[selected][0]

    def _map_widget_type_to_target(self, widget_type: str, default: str) -> str:
        """Map widget type to target window."""
        type_to_target = {
            "movies": "videos",
            "tvshows": "videos",
            "episodes": "videos",
            "musicvideos": "videos",
            "videos": "videos",
            "songs": "music",
            "albums": "music",
            "artists": "music",
            "music": "music",
            "programs": "programs",
            "files": "files",
            "pictures": "pictures",
            "games": "games",
        }
        return type_to_target.get(widget_type, default)

    def _is_browsable(self, obj) -> bool:
        """Object is opted in for browse-into via `browse` + `path`.

        Works for both Widget (`browse` is bool) and Shortcut (`browse` is window name).
        """
        return bool(obj.browse and obj.path)

    def _browse_widget_path(self, widget: Widget) -> Widget | None:
        """Browse into a widget's path and let user select location.

        A plugin:// path has to ask, its content type can't be read off the addon category.
        """
        result = self._browse_directory(widget.path, resolve_label(widget.label), icon=widget.icon)
        if result is None:
            return None

        path, label, icon = result

        addon_type = "video"
        if widget.target == "music":
            addon_type = "audio"
        elif widget.target == "programs":
            addon_type = "executable"
        elif widget.target in ("pictures", "games"):
            addon_type = widget.target

        widget_type = (
            widget.type or library_node_type(path) or self._pick_widget_type(addon_type)
        )
        if widget_type is None:
            return None

        widget_target = self._map_widget_type_to_target(widget_type, widget.target or "videos")

        return Widget(
            name=f"browse-{hash(path)}",
            label=label,
            path=path,
            type=widget_type,
            target=widget_target,
            icon=icon or widget.icon,
            source=widget.source,
        )

    def _pick_from_hierarchy(
        self,
        items: list,
        item_props: dict[str, str],
        *,
        title: str = "",
        leaf_types: tuple = (Shortcut,),
        group_types: tuple = (ShortcutGroup,),
        default_leaf_icon: str = "DefaultShortcut.png",
        default_group_icon: str = "DefaultFolder.png",
        show_none: bool = False,
        current_value: str = "",
        content_resolver: Callable[[Content], list] | None = None,
        create_folder_group: Callable[[str, list, str, str], Any] | None = None,
        custom_action: tuple[str, str, Callable[[], Any | None]] | None = None,
        positions: dict[str, int] | None = None,
    ) -> Any | None | Literal[False]:
        """Hierarchical picker with back navigation. False when the user picks "None"."""
        positions = {} if positions is None else positions
        start = time.monotonic()
        visible_items = self._filter_picker_items(
            items, item_props, leaf_types, group_types, content_resolver, create_folder_group
        )
        log.debug(
            f"picker: {picker_kind(leaf_types)} root rows={len(visible_items)} "
            f"built in {_ms(start):.0f}ms"
        )

        if not visible_items:
            xbmcgui.Dialog().notification(LANGUAGE(32141), LANGUAGE(32064))
            return None

        offset = 1 if show_none else 0
        preselect = positions.get("", -1)

        if preselect == -1:
            for i, vis_item in enumerate(visible_items):
                if hasattr(vis_item, "name") and vis_item.name == current_value:
                    preselect = i + offset
                    break

        overrides = self._icon_overrides()

        while True:
            listitems = []
            if show_none:
                none_item = xbmcgui.ListItem(xbmc.getLocalizedString(231), offscreen=True)
                none_icon = overrides.get("DefaultAddonNone.png", "DefaultAddonNone.png")
                none_item.setArt({"icon": resolve_label(none_icon)})
                listitems.append(none_item)

            for vis_item in visible_items:
                is_placeholder = (
                    isinstance(vis_item, (Shortcut, Widget))
                    and vis_item.name.startswith(PLACEHOLDER_PREFIX)
                )
                if is_placeholder:
                    label = LANGUAGE(32058)
                else:
                    label = resolve_label(vis_item.label)
                if isinstance(vis_item, group_types):
                    label = f"{label} >"
                    icon = vis_item.icon if vis_item.icon else default_group_icon
                else:
                    if not is_placeholder and _drills_down(vis_item):
                        label = f"{label} >"
                    icon = vis_item.icon if vis_item.icon else default_leaf_icon
                listitem = xbmcgui.ListItem(label, offscreen=True)
                listitem.setArt({"icon": resolve_label(overrides.get(icon, icon))})
                stamp_picker_props(listitem, vis_item, item_props, content_resolver)
                listitems.append(listitem)

            if custom_action:
                action_label, action_icon, _callback = custom_action
                action_item = xbmcgui.ListItem(action_label, offscreen=True)
                action_item.setArt({"icon": resolve_label(overrides.get(action_icon, action_icon))})
                listitems.append(action_item)

            selected = picker_select(
                picker_kind(leaf_types),
                title or LANGUAGE(32181),
                listitems,
                useDetails=True,
                preselect=preselect,
            )

            if selected == -1:
                return None

            if show_none and selected == 0:
                return False

            if custom_action and selected == len(listitems) - 1:
                _label, _icon, callback = custom_action
                result = callback()
                if result is not None:
                    return result
                continue

            preselect = selected
            positions[""] = selected
            selected_item = visible_items[selected - offset]

            if isinstance(selected_item, Input):
                result = self._handle_input_selection(selected_item)
                if result is not None:
                    return result
                continue

            if isinstance(selected_item, leaf_types):
                is_browsable_shortcut = (
                    isinstance(selected_item, Shortcut)
                    and not selected_item.name.startswith(PLACEHOLDER_PREFIX)
                    and self._is_browsable(selected_item)
                )
                if is_browsable_shortcut:
                    browse_info = self._get_browse_info_from_shortcut(selected_item)
                    if browse_info:
                        browse_path, target_window = browse_info
                        result = self._browse_path(
                            browse_path,
                            title=resolve_label(selected_item.label),
                            target_window=target_window,
                            source_media=selected_item.source_media,
                            icon=selected_item.icon,
                        )
                        if result is not None:
                            return result
                        continue

                if isinstance(selected_item, Widget) and self._is_browsable(selected_item):
                    result = self._browse_widget_path(selected_item)
                    if result is not None:
                        return result
                    continue

                return selected_item

            result = self._pick_from_hierarchy_group(
                selected_item,
                item_props,
                leaf_types=leaf_types,
                group_types=group_types,
                default_leaf_icon=default_leaf_icon,
                default_group_icon=default_group_icon,
                content_resolver=content_resolver,
                create_folder_group=create_folder_group,
                positions=positions,
                level=f"/{selected}",
            )

            if result is not None:
                return result

    def _pick_from_hierarchy_group(
        self,
        group,
        item_props: dict[str, str],
        *,
        leaf_types: tuple,
        group_types: tuple,
        default_leaf_icon: str,
        default_group_icon: str,
        content_resolver: Callable[[Content], list] | None = None,
        create_folder_group: Callable[[str, list, str, str], Any] | None = None,
        positions: dict[str, int],
        level: str,
    ) -> Any | None:
        """Pick from items within a group with back navigation."""
        start = time.monotonic()
        visible_items = self._filter_picker_items(
            group.items, item_props, leaf_types, group_types, content_resolver,
            create_folder_group, parent_label=group.label, parent_icon=group.icon,
        )
        log.debug(f"picker: {group.name} rows={len(visible_items)} built in {_ms(start):.0f}ms")

        if not visible_items:
            xbmcgui.Dialog().notification(LANGUAGE(32141), LANGUAGE(32142))
            return None

        overrides = self._icon_overrides()
        preselect = positions.get(level, -1)
        while True:
            listitems = []
            for vis_item in visible_items:
                is_placeholder = (
                    isinstance(vis_item, (Shortcut, Widget))
                    and vis_item.name.startswith(PLACEHOLDER_PREFIX)
                )
                if is_placeholder:
                    label = LANGUAGE(32058)
                else:
                    label = resolve_label(vis_item.label)
                if isinstance(vis_item, group_types):
                    label = f"{label} >"
                    icon = vis_item.icon if vis_item.icon else default_group_icon
                else:
                    if not is_placeholder and _drills_down(vis_item):
                        label = f"{label} >"
                    icon = vis_item.icon if vis_item.icon else default_leaf_icon
                listitem = xbmcgui.ListItem(label, offscreen=True)
                listitem.setArt({"icon": resolve_label(overrides.get(icon, icon))})
                stamp_picker_props(listitem, vis_item, item_props, content_resolver)
                listitems.append(listitem)

            title = resolve_label(group.label)
            selected = picker_select(
                picker_kind(leaf_types), title, listitems, useDetails=True, preselect=preselect
            )

            if selected == -1:
                return None  # Go back

            preselect = selected
            positions[level] = selected
            selected_item = visible_items[selected]

            if isinstance(selected_item, Input):
                result = self._handle_input_selection(selected_item)
                if result is not None:
                    return result
                continue

            if isinstance(selected_item, leaf_types):
                is_browsable_shortcut = (
                    isinstance(selected_item, Shortcut)
                    and not selected_item.name.startswith(PLACEHOLDER_PREFIX)
                    and self._is_browsable(selected_item)
                )
                if is_browsable_shortcut:
                    browse_info = self._get_browse_info_from_shortcut(selected_item)
                    if browse_info:
                        browse_path, target_window = browse_info
                        result = self._browse_path(
                            browse_path,
                            title=resolve_label(selected_item.label),
                            target_window=target_window,
                            source_media=selected_item.source_media,
                            icon=selected_item.icon,
                        )
                        if result is not None:
                            return result
                        continue

                if isinstance(selected_item, Widget) and self._is_browsable(selected_item):
                    result = self._browse_widget_path(selected_item)
                    if result is not None:
                        return result
                    continue

                return selected_item

            result = self._pick_from_hierarchy_group(
                selected_item,
                item_props,
                leaf_types=leaf_types,
                group_types=group_types,
                default_leaf_icon=default_leaf_icon,
                default_group_icon=default_group_icon,
                content_resolver=content_resolver,
                create_folder_group=create_folder_group,
                positions=positions,
                level=f"{level}/{selected}",
            )

            if result is not None:
                return result

    def _filter_picker_items(
        self,
        items: list,
        item_props: dict[str, str],
        leaf_types: tuple,
        group_types: tuple,
        content_resolver: Callable[[Content], list] | None = None,
        create_folder_group: Callable[[str, list, str, str], Any] | None = None,
        parent_label: str = "",
        parent_icon: str = "",
    ) -> list:
        """Filter and resolve picker items by condition and visibility."""
        visible_items = []

        for item in items:
            if isinstance(item, Content):
                if item.condition and not evaluate_condition(item.condition, item_props):
                    continue
                if item.visible and not _check_visible(item.visible):
                    continue
                if content_resolver:
                    start = time.monotonic()
                    resolved = content_resolver(item)
                    _log_slow_resolve(item, len(resolved), start)
                    placeholder = _browse_placeholder_for_content(
                        item,
                        as_widget=Widget in leaf_types,
                        parent_label=parent_label,
                        parent_icon=parent_icon,
                    )
                    overrides = self._icon_overrides()
                    if placeholder:
                        placeholder.icon = overrides.get(placeholder.icon, placeholder.icon)
                    if item.folder and (resolved or placeholder) and create_folder_group:
                        if placeholder:
                            resolved = [placeholder, *resolved]
                        visible_items.append(
                            create_folder_group(
                                item.folder, resolved, item.icon, _content_folder_path(item)
                            )
                        )
                    else:
                        if placeholder:
                            visible_items.append(placeholder)
                        if resolved:
                            visible_items.extend(resolved)
            elif isinstance(item, (Input, *leaf_types, *group_types)):
                if not _check_visible(getattr(item, "visible", "")):
                    continue
                condition = getattr(item, "condition", "")
                if condition and not evaluate_condition(condition, item_props):
                    continue
                if isinstance(item, group_types) and getattr(item, "flat", False):
                    expanded = self._filter_picker_items(
                        item.items,
                        item_props,
                        leaf_types,
                        group_types,
                        content_resolver,
                        create_folder_group,
                        parent_label=getattr(item, "label", "") or parent_label,
                        parent_icon=getattr(item, "icon", "") or parent_icon,
                    )
                    visible_items.extend(expanded)
                    continue
                visible_items.append(item)

        return visible_items

    def _handle_input_selection(self, input_item: Input) -> Shortcut | None:
        """Handle selection of an Input item by showing keyboard."""
        input_type_map = {
            "text": xbmcgui.INPUT_ALPHANUM,
            "numeric": xbmcgui.INPUT_NUMERIC,
            "ipaddress": xbmcgui.INPUT_IPADDRESS,
            "password": xbmcgui.INPUT_PASSWORD,
        }

        keyboard_type = input_type_map.get(input_item.type, xbmcgui.INPUT_ALPHANUM)
        heading = resolve_label(input_item.label)

        result = xbmcgui.Dialog().input(heading, type=keyboard_type)
        if not result:
            return None

        if input_item.for_ == "action":
            return Shortcut(
                name=f"custom-input-{hash(result)}",
                label=input_item.label,
                actions=[result],
                icon=input_item.icon,
            )
        if input_item.for_ == "label":
            return Shortcut(
                name=f"custom-input-{hash(result)}",
                label=result,
                actions=["noop"],
                icon=input_item.icon,
            )
        if input_item.for_ == "path":
            return Shortcut(
                name=f"custom-input-{hash(result)}",
                label=input_item.label,
                actions=[f"ActivateWindow(Videos,{result},return)"],
                icon=input_item.icon,
            )

        return None

    def _browse_directory(
        self,
        path: str,
        title: str = "",
        icon: str = "",
    ) -> tuple[str, str, str] | None:
        """Browse a path, navigating into folders, returning the picked location.

        A "Use this location" row sits at the top; picking it or a file returns
        (path, label, icon), None if cancelled.
        """
        browse_provider = get_browse_provider()
        browse_provider.set_icon_overrides(self._icon_overrides())
        current_path = path
        current_label = title
        history: list[tuple[str, str, str]] = []

        overrides = self._icon_overrides()
        folder_icon = overrides.get("DefaultFolder.png", "DefaultFolder.png")
        root_icon = icon or folder_icon
        current_icon = root_icon

        while True:
            xbmc.executebuiltin("ActivateWindow(busydialognocancel)")
            try:
                items = browse_provider.list_directory(current_path, include_art=True)
                if items is None:
                    xbmcgui.Dialog().notification(
                        LANGUAGE(32149), LANGUAGE(32150)
                    )
                    return None

                dialog_title = current_label or LANGUAGE(32151)

                listitems = []
                use_location_item = xbmcgui.ListItem(LANGUAGE(32058), offscreen=True)
                use_location_item.setArt({"icon": resolve_label(current_icon)})
                use_location_item.setProperty("path", current_path)
                use_location_item.setProperty("name", current_label)
                listitems.append(use_location_item)
                # label doubles as name for DialogSelect; browse rows have no slug or type
                for item in items:
                    label = item.label
                    if item.is_directory:
                        label = f"{label} >"
                    listitem = xbmcgui.ListItem(label, offscreen=True)
                    listitem.setArt({"icon": resolve_label(item.icon)})
                    listitem.setProperty("path", item.path)
                    listitem.setProperty("name", item.label)
                    listitems.append(listitem)
            finally:
                xbmc.executebuiltin("Dialog.Close(busydialognocancel)")

            selected = picker_select("browse", dialog_title, listitems, useDetails=True)

            if selected == -1:
                if history:
                    current_path, current_label, current_icon = history.pop()
                    continue
                return None

            if selected == 0:
                return (current_path, current_label or LANGUAGE(32182), current_icon)

            selected_item = items[selected - 1]

            if selected_item.is_directory:
                history.append((current_path, current_label, current_icon))
                current_path = selected_item.path
                current_label = selected_item.label
                # only the generic folder is worth replacing
                current_icon = (
                    root_icon if selected_item.icon == folder_icon else selected_item.icon
                )
                continue

            return (selected_item.path, selected_item.label, selected_item.icon)

    def _browse_path(
        self,
        path: str,
        title: str = "",
        target_window: str = "videos",
        source_media: str = "",
        icon: str = "",
    ) -> Shortcut | None:
        """Browse into a path and let user select location or navigate deeper."""
        result = self._browse_directory(path, title, icon=icon)
        if result is None:
            return None

        selected_path, label, icon = result
        return Shortcut(
            name=f"browse-{hash(selected_path)}",
            label=label,
            actions=[f"ActivateWindow({target_window},{selected_path},return)"],
            icon=icon,
            path=selected_path,
            source_media=source_media,
        )

    def _filter_widgets_by_slot(self, items: list, slot: str) -> list:
        """Filter widget items by slot. Widgets with no slot show for all slots."""
        from ..models.widget import Widget, WidgetGroup

        filtered = []
        for item in items:
            if isinstance(item, Widget):
                if not item.slot or item.slot == slot:
                    filtered.append(item)
            elif isinstance(item, WidgetGroup):
                filtered_children = self._filter_widgets_by_slot(item.items, slot)
                if filtered_children:
                    filtered_group = WidgetGroup(
                        name=item.name,
                        label=item.label,
                        icon=item.icon,
                        condition=item.condition,
                        visible=item.visible,
                        items=filtered_children,
                        flat=item.flat,
                    )
                    filtered.append(filtered_group)
            else:
                filtered.append(item)
        return filtered

    def _get_browse_info_from_shortcut(self, shortcut: Shortcut) -> tuple[str, str] | None:
        """Extract browsable path and target window from a shortcut.

        Returns (path, window) if the shortcut opted in via `browse` + `<path>`, else None.
        """
        if not self._is_browsable(shortcut):
            return None

        window = WINDOW_MAP.get(shortcut.browse.lower(), "Videos")
        return (shortcut.path, window)

    def _pick_background(
        self,
        item_props: dict[str, str],
        current_value: str = "",
        positions: dict[str, int] | None = None,
    ) -> Background | None | Literal[False]:
        """Pick a background from groupings. False when the user picks "None"."""
        if not self.manager:
            return None

        groupings = self.manager.config.background_groupings
        if not groupings:
            xbmcgui.Dialog().notification(LANGUAGE(32152), LANGUAGE(32153))
            return None

        return self._pick_from_hierarchy(
            groupings,
            item_props,
            title=LANGUAGE(32045),
            leaf_types=(Background,),
            group_types=(BackgroundGroup,),
            default_leaf_icon="DefaultPicture.png",
            default_group_icon="DefaultFolder.png",
            show_none=True,
            current_value=current_value,
            positions=positions,
        )
