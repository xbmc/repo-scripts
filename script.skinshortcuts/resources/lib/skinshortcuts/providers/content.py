"""Content provider for dynamic shortcut resolution.

Resolves <content> elements to actual shortcuts at runtime by querying
Kodi's JSON-RPC API and filesystem.
"""

from __future__ import annotations

import json
import urllib.parse
from dataclasses import dataclass
from typing import TYPE_CHECKING

import xbmc
import xbmcvfs

from ..log import get_logger
from ..playlists import unpack_multipath

if TYPE_CHECKING:
    from ..models.menu import Content

log = get_logger("ContentProvider")


PLAYLIST_EXTENSIONS = (".xsp", ".m3u", ".m3u8", ".pls")


# Target aliases: map skinner-facing target values to the canonical form each
# JSON-RPC endpoint expects.

# Files.Media accepts: video, music, pictures, files, programs.
_SOURCES_TARGET_ALIASES: dict[str, str] = {
    "video": "video",
    "videos": "video",
    "music": "music",
    "pictures": "pictures",
    "picture": "pictures",
    "files": "files",
    "file": "files",
    "programs": "programs",
    "program": "programs",
}

# Addons.GetAddons content accepts: video, audio, image, executable, game.
# Skinner-facing plural/window-name forms map to these.
_ADDONS_TARGET_ALIASES: dict[str, str] = {
    "video": "video",
    "videos": "video",
    "audio": "audio",
    "music": "audio",
    "image": "image",
    "images": "image",
    "picture": "image",
    "pictures": "image",
    "executable": "executable",
    "program": "executable",
    "programs": "executable",
    "game": "game",
    "games": "game",
}

# Smart-playlist directory scan filter: video or music only.
_PLAYLIST_TARGET_ALIASES: dict[str, str] = {
    "video": "video",
    "videos": "video",
    "music": "music",
}


@dataclass
class ResolvedShortcut:
    """A shortcut resolved from dynamic content."""

    label: str
    action: str
    icon: str = "DefaultShortcut.png"
    label2: str = ""
    action_play: str = ""
    action_party: str = ""
    content_type: str = ""
    # Set for browsable items (plugin-source addons, etc.). When populated, picker
    # offers browse-into and constructs ActivateWindow({browse_window},{browse_path},return).
    browse_path: str = ""
    browse_window: str = ""
    # Media of an originating file source (video/music/pictures/files/programs); marks a
    # source shortcut. The smart-playlist flow acts on video/music; other media fall back
    # to Files view. Empty for non-source shortcuts.
    source_media: str = ""


def _expand_playlist_dirs(directory: str) -> list[str]:
    """Expand a multipath alias to its component dirs; other dirs pass through.

    Appending a filename to the alias itself won't open; on a component dir it
    stays a resolvable special:// path.
    """
    translated = xbmcvfs.translatePath(directory)
    if not translated.startswith("multipath://"):
        return [directory]
    return [d if d.endswith("/") else d + "/" for d in unpack_multipath(translated)]


def scan_playlist_files(directory: str) -> list[tuple[str, str]]:
    """Scan directory for playlist files.

    Args:
        directory: Path to scan (e.g., "{playlists_base}/video/")

    Returns:
        List of (label, filepath) tuples for found playlists.
    """
    playlists = []

    for scan_dir in _expand_playlist_dirs(directory):
        try:
            _dirs, files = xbmcvfs.listdir(scan_dir)
        except Exception:
            continue

        for filename in files:
            if filename.endswith(PLAYLIST_EXTENSIONS):
                label = filename.rsplit(".", 1)[0]
                playlists.append((label, scan_dir + filename))

    return playlists


def _collection(result: dict | None, key: str) -> list:
    """Return result[key] as a list.

    Kodi could return null, missing, or empty.
    """
    if not result:
        return []
    return result.get(key) or []


class ContentProvider:
    """Resolves dynamic content references to shortcuts."""

    def __init__(self, icon_overrides: dict[str, str] | None = None) -> None:
        self._cache: dict[str, list[ResolvedShortcut]] = {}
        self._icon_overrides = icon_overrides or {}

    def resolve(self, content: Content) -> list[ResolvedShortcut]:
        """Resolve a content reference to a list of shortcuts.

        Args:
            content: Content object with source and target attributes.

        Returns:
            List of resolved shortcuts.

        Note:
            Condition (property) and visible (Kodi visibility) are checked
            by the caller (picker) before calling this method.
        """
        source = content.source.lower()
        target = content.target.lower() if content.target else ""

        if source == "sources":
            result = self._resolve_sources(target)
        elif source == "playlists":
            result = self._resolve_playlists(target, content.path)
        elif source == "addons":
            result = self._resolve_addons(target)
        elif source == "favourites":
            result = self._resolve_favourites()
        elif source == "pvr":
            result = self._resolve_pvr(target)
        elif source == "commands":
            result = self._resolve_commands()
        elif source == "settings":
            result = self._resolve_settings()
        elif source == "library":
            result = self._resolve_library(target)
        elif source == "nodes":
            result = self._resolve_nodes(target)
        else:
            return []

        if self._icon_overrides:
            for r in result:
                r.icon = self._icon_overrides.get(r.icon, r.icon)
        return result

    def clear_cache(self) -> None:
        """Clear the content cache."""
        self._cache.clear()

    def _resolve_sources(self, target: str) -> list[ResolvedShortcut]:
        """Resolve media sources. Empty target defaults to video for backward compat."""
        cache_key = f"sources_{target}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if not target:
            media = "video"
        else:
            media = _SOURCES_TARGET_ALIASES.get(target)
            if media is None:
                log.warning(
                    f"sources: unknown target '{target}'. Valid: "
                    "video/videos, music, pictures/picture, files/file, programs/program"
                )
                return []

        result = self._jsonrpc("Files.GetSources", {"media": media})
        sources = _collection(result, "sources")
        if not sources:
            return []

        window_map = {
            "video": "videos",
            "music": "music",
            "pictures": "pictures",
            "files": "files",
            "programs": "programs",
        }
        window = window_map[media]

        shortcuts = []
        for source in sources:
            path = source.get("file", "")
            label = source.get("label", "")
            if path and label:
                shortcuts.append(
                    ResolvedShortcut(
                        label=label,
                        action=f"ActivateWindow({window},{path},return)",
                        icon="DefaultFolder.png",
                        browse_path=path,
                        browse_window=window,
                        source_media=media,
                    )
                )

        self._cache[cache_key] = shortcuts
        return shortcuts

    def _get_playlists_base_path(self) -> str:
        """Get the playlist base path from Kodi settings.

        Returns the user-configured playlist path, or the default
        special://profile/playlists/ if not set.
        """
        result = self._jsonrpc(
            "Settings.GetSettingValue",
            {"setting": "system.playlistspath"},
        )
        if result and result.get("value"):
            base = result["value"]
            if not base.endswith("/"):
                base += "/"
            return base
        return "special://profile/playlists/"

    def _resolve_playlists(
        self, target: str, custom_path: str = ""
    ) -> list[ResolvedShortcut]:
        """Resolve playlists from standard or custom paths."""
        cache_key = f"playlists_{target}_{custom_path}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if target:
            normalized = _PLAYLIST_TARGET_ALIASES.get(target)
            if normalized is None:
                log.warning(
                    f"playlists: unknown target '{target}'. Valid: video/videos, music"
                )
                return []
        else:
            normalized = ""

        if custom_path:
            paths = [custom_path]
        else:
            base = self._get_playlists_base_path()
            if normalized == "video":
                paths = [f"{base}video/", f"{base}mixed/"]
            elif normalized == "music":
                paths = [f"{base}music/", f"{base}mixed/"]
            else:
                paths = [f"{base}video/", f"{base}music/", f"{base}mixed/"]

        default_window = "music" if normalized == "music" else "videos"

        shortcuts = []
        for path in paths:
            shortcuts.extend(self._scan_playlist_directory(path, default_window, normalized))

        self._cache[cache_key] = shortcuts
        return shortcuts

    def _scan_playlist_directory(
        self, directory: str, default_window: str, target: str = ""
    ) -> list[ResolvedShortcut]:
        """Scan a directory for playlist files and convert to shortcuts.

        `target` is the normalized form ("video", "music", or "") from
        `_resolve_playlists`; unknown values are already rejected upstream.
        """
        shortcuts = []
        filter_video = target == "video"
        filter_music = target == "music"

        video_types = ("movies", "tvshows", "episodes", "musicvideos")
        music_types = ("songs", "albums", "artists")

        for label, filepath in scan_playlist_files(directory):
            window = default_window
            display_label = label
            playlist_type = ""

            if filepath.endswith(".xsp"):
                playlist_type, playlist_name = self._parse_smart_playlist(filepath)
                if playlist_name:
                    display_label = playlist_name
                if playlist_type in music_types:
                    window = "music"
                elif playlist_type in video_types:
                    window = "videos"

            if filter_video and playlist_type and playlist_type not in video_types:
                continue
            if filter_music and playlist_type and playlist_type not in music_types:
                continue

            action_party = ""
            if window == "music":
                action_party = f"PlayerControl(PartyMode({filepath}))"

            shortcuts.append(
                ResolvedShortcut(
                    label=display_label,
                    action=f"ActivateWindow({window},{filepath},return)",
                    icon="DefaultPlaylist.png",
                    action_play=f"PlayMedia({filepath})",
                    action_party=action_party,
                    content_type=playlist_type,
                )
            )

        return shortcuts

    def _parse_smart_playlist(self, filepath: str) -> tuple[str, str]:
        """Parse a smart playlist (.xsp file) for type and name.

        Returns:
            Tuple of (type, name). Falls back to ("unknown", "") on error.
        """
        try:
            f = xbmcvfs.File(filepath)
            try:
                content = f.read()
            finally:
                f.close()

            import xml.etree.ElementTree as ET

            root = ET.fromstring(content)
            playlist_type = root.get("type") or "unknown"
            name_elem = root.find("name")
            name = name_elem.text if name_elem is not None and name_elem.text else ""
            return playlist_type, name
        except Exception:
            return "unknown", ""

    def _resolve_addons(self, target: str) -> list[ResolvedShortcut]:
        """Resolve installed addons by content type. Empty target defaults to video."""
        cache_key = f"addons_{target}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if not target:
            content = "video"
        else:
            content = _ADDONS_TARGET_ALIASES.get(target)
            if content is None:
                log.warning(
                    f"addons: unknown target '{target}'. Valid: "
                    "video/videos, audio/music, image/pictures, executable/programs, game/games"
                )
                return []

        window_map = {
            "video": "videos",
            "audio": "music",
            "image": "pictures",
            "executable": "programs",
            "game": "games",
        }

        result = self._jsonrpc(
            "Addons.GetAddons",
            {
                "content": content,
                "enabled": True,
                "properties": ["name", "thumbnail"],
            },
        )
        addons = _collection(result, "addons")
        if not addons:
            return []

        shortcuts = []
        for addon in addons:
            addon_id = addon.get("addonid", "")
            name = addon.get("name", addon_id)
            thumb = addon.get("thumbnail", "")
            if not addon_id:
                continue

            if addon.get("type") == "xbmc.python.pluginsource":
                window = window_map.get(content, "videos")
                shortcuts.append(
                    ResolvedShortcut(
                        label=name,
                        action="",
                        icon=thumb or "DefaultAddon.png",
                        browse_path=f"plugin://{addon_id}/",
                        browse_window=window,
                    )
                )
            else:
                shortcuts.append(
                    ResolvedShortcut(
                        label=name,
                        action=f"RunAddon({addon_id})",
                        icon=thumb or "DefaultAddon.png",
                    )
                )

        self._cache[cache_key] = shortcuts
        return shortcuts

    def _resolve_favourites(self) -> list[ResolvedShortcut]:
        """Resolve user favourites."""
        cache_key = "favourites"
        if cache_key in self._cache:
            return self._cache[cache_key]

        result = self._jsonrpc(
            "Favourites.GetFavourites",
            {"properties": ["thumbnail", "window", "windowparameter", "path"]},
        )
        favourites = _collection(result, "favourites")
        if not favourites:
            return []

        shortcuts = []
        for fav in favourites:
            title = fav.get("title", "")
            fav_type = fav.get("type", "")
            thumb = fav.get("thumbnail", "")

            action = ""
            if fav_type == "media":
                path = fav.get("path", "")
                if path:
                    action = f"PlayMedia({path})"
            elif fav_type == "window":
                window = fav.get("window", "")
                param = fav.get("windowparameter", "")
                if window:
                    if param:
                        action = f"ActivateWindow({window},{param},return)"
                    else:
                        action = f"ActivateWindow({window})"
            elif fav_type == "script":
                path = fav.get("path", "")
                if path:
                    action = f"RunScript({path})"
            elif fav_type == "androidapp":
                path = fav.get("path", "")
                if path:
                    action = f"StartAndroidActivity({path})"

            if title and action:
                shortcuts.append(
                    ResolvedShortcut(
                        label=title,
                        action=action,
                        icon=thumb or "DefaultFavourites.png",
                    )
                )

        self._cache[cache_key] = shortcuts
        return shortcuts

    def _resolve_pvr(self, target: str) -> list[ResolvedShortcut]:
        """Resolve PVR channels."""
        cache_key = f"pvr_{target}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if target in ("tv", "television"):
            if not xbmc.getCondVisibility("Pvr.HasTVChannels"):
                return []
            channel_group = "alltv"
        elif target == "radio":
            if not xbmc.getCondVisibility("Pvr.HasRadioChannels"):
                return []
            channel_group = "allradio"
        else:
            return []

        result = self._jsonrpc(
            "PVR.GetChannels",
            {
                "channelgroupid": channel_group,
                "properties": ["thumbnail", "channelnumber"],
            },
        )
        channels = _collection(result, "channels")
        if not channels:
            return []

        shortcuts = []
        for channel in channels:
            channel_id = channel.get("channelid", 0)
            label = channel.get("label", "")
            thumb = channel.get("thumbnail", "")
            number = channel.get("channelnumber", 0)

            if channel_id and label:
                display_label = f"{number}. {label}" if number else label
                shortcuts.append(
                    ResolvedShortcut(
                        label=display_label,
                        action=f"PlayPvrChannel({channel_id})",
                        icon=thumb or "DefaultTVShows.png",
                    )
                )

        self._cache[cache_key] = shortcuts
        return shortcuts

    def _resolve_commands(self) -> list[ResolvedShortcut]:
        """Resolve system commands."""
        commands = [
            ("$LOCALIZE[13012]", "Quit()", "DefaultProgram.png"),  # Quit
            ("$LOCALIZE[13005]", "Reboot()", "DefaultProgram.png"),  # Reboot
            ("$LOCALIZE[13009]", "Powerdown()", "DefaultProgram.png"),  # Power off
            ("$LOCALIZE[13014]", "Suspend()", "DefaultProgram.png"),  # Suspend
            ("$LOCALIZE[13015]", "Hibernate()", "DefaultProgram.png"),  # Hibernate
            ("$LOCALIZE[13016]", "RestartApp()", "DefaultProgram.png"),  # Restart
            ("$LOCALIZE[20183]", "ReloadSkin()", "DefaultProgram.png"),  # Reload skin
        ]

        return [
            ResolvedShortcut(label=label, action=action, icon=icon)
            for label, action, icon in commands
        ]

    def _resolve_settings(self) -> list[ResolvedShortcut]:
        """Resolve settings shortcuts."""
        settings = [
            ("$LOCALIZE[10004]", "ActivateWindow(Settings)", "DefaultAddonService.png"),
            ("$LOCALIZE[10035]", "ActivateWindow(SkinSettings)", "DefaultAddonService.png"),
            ("$LOCALIZE[14201]", "ActivateWindow(PlayerSettings)", "DefaultAddonService.png"),
            ("$LOCALIZE[14212]", "ActivateWindow(MediaSettings)", "DefaultAddonVideo.png"),
            ("$LOCALIZE[14205]", "ActivateWindow(PVRSettings)", "DefaultAddonPVRClient.png"),
            ("$LOCALIZE[14208]", "ActivateWindow(ServiceSettings)", "DefaultAddonService.png"),
            ("$LOCALIZE[10022]", "ActivateWindow(GameSettings)", "DefaultAddonGame.png"),
            ("$LOCALIZE[14207]", "ActivateWindow(InterfaceSettings)", "DefaultAddonService.png"),
            ("$LOCALIZE[14210]", "ActivateWindow(Profiles)", "DefaultUser.png"),
            ("$LOCALIZE[14209]", "ActivateWindow(SystemSettings)", "DefaultAddonService.png"),
            ("$LOCALIZE[10040]", "ActivateWindow(AddonBrowser)", "DefaultAddon.png"),
            ("$LOCALIZE[10003]", "ActivateWindow(FileManager)", "DefaultFolder.png"),
        ]

        return [
            ResolvedShortcut(label=label, action=action, icon=icon)
            for label, action, icon in settings
        ]

    def _resolve_library(self, target: str) -> list[ResolvedShortcut]:
        """Resolve library nodes (genres, years, studios, tags, actors).

        Args:
            target: Library content type. Valid values:
                - "genres", "moviegenres", "tvgenres", "musicgenres"
                - "years", "movieyears", "tvyears"
                - "studios", "moviestudios", "tvstudios"
                - "tags", "movietags", "tvtags"
                - "actors", "movieactors", "tvactors"
                - "directors", "moviedirectors", "tvdirectors"
                - "artists", "albums"
        """
        cache_key = f"library_{target}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        shortcuts: list[ResolvedShortcut] = []
        target_lower = target.lower()

        if target_lower in ("genres", "moviegenres"):
            shortcuts = self._get_video_genres("movie")
        elif target_lower == "tvgenres":
            shortcuts = self._get_video_genres("tvshow")
        elif target_lower == "musicgenres":
            shortcuts = self._get_music_genres()
        elif target_lower in ("years", "movieyears"):
            shortcuts = self._get_video_years("movie")
        elif target_lower == "tvyears":
            shortcuts = self._get_video_years("tvshow")
        elif target_lower in ("studios", "moviestudios"):
            shortcuts = self._get_video_property("movie", "studio", "Studios")
        elif target_lower == "tvstudios":
            shortcuts = self._get_video_property("tvshow", "studio", "Studios")
        elif target_lower in ("tags", "movietags"):
            shortcuts = self._get_video_property("movie", "tag", "Tags")
        elif target_lower == "tvtags":
            shortcuts = self._get_video_property("tvshow", "tag", "Tags")
        elif target_lower in ("actors", "movieactors"):
            shortcuts = self._get_video_actors("movie")
        elif target_lower == "tvactors":
            shortcuts = self._get_video_actors("tvshow")
        elif target_lower in ("directors", "moviedirectors"):
            shortcuts = self._get_video_directors("movie")
        elif target_lower == "tvdirectors":
            shortcuts = self._get_video_directors("tvshow")
        elif target_lower == "artists":
            shortcuts = self._get_music_artists()
        elif target_lower == "albums":
            shortcuts = self._get_music_albums()

        self._cache[cache_key] = shortcuts
        return shortcuts

    def _resolve_nodes(self, target: str) -> list[ResolvedShortcut]:
        """Resolve library nodes (navigation structure from XML files).

        Args:
            target: Library type (``video``, ``music``, ``video_flat``).
                    ``library`` / ``all`` / empty returns video and music
                    as two browsable parent entries.

        Returns:
            List of shortcuts for top-level library navigation nodes.
        """
        cache_key = f"nodes_{target}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        target_lower = target.lower()
        if target_lower in ("library", "all", ""):
            shortcuts = [
                ResolvedShortcut(
                    label=xbmc.getLocalizedString(3),  # "Videos"
                    action="ActivateWindow(videos,library://video/,return)",
                    icon="DefaultVideo.png",
                    browse_path="library://video/",
                    browse_window="videos",
                ),
                ResolvedShortcut(
                    label=xbmc.getLocalizedString(2),  # "Music"
                    action="ActivateWindow(music,library://music/,return)",
                    icon="DefaultMusicAlbums.png",
                    browse_path="library://music/",
                    browse_window="music",
                ),
            ]
            self._cache[cache_key] = shortcuts
            return shortcuts

        lib_type = "video" if target_lower == "videos" else target_lower
        shortcuts = self._collect_nodes_for_type(lib_type)
        self._cache[cache_key] = shortcuts
        return shortcuts

    def _collect_nodes_for_type(self, lib_type: str) -> list[ResolvedShortcut]:
        """Collect top-level library nodes for a single library type.

        Uses Kodi's Files.GetDirectory so user-customized nodes (via addons like
        plugin.library.node.editor) are merged with system defaults, and hidden
        nodes are excluded.
        """
        is_music = lib_type == "music"
        media = "music" if is_music else "video"
        window = "music" if is_music else "videos"
        directory = f"library://{lib_type}/"

        result = self._jsonrpc(
            "Files.GetDirectory",
            {
                "directory": directory,
                "media": media,
                "properties": ["title", "thumbnail", "art"],
            },
        )
        files = _collection(result, "files")
        if not files:
            return []

        shortcuts: list[ResolvedShortcut] = []
        for entry in files:
            path = entry.get("file", "")
            label = entry.get("label") or entry.get("title") or ""
            if not label or not path:
                continue
            icon = self._normalize_image(entry.get("art", {}).get("icon", ""))
            thumb = entry.get("thumbnail", "")
            shortcuts.append(
                ResolvedShortcut(
                    label=label,
                    action=f"ActivateWindow({window},{path},return)",
                    icon=icon or thumb or "DefaultFolder.png",
                    browse_path=path,
                    browse_window=window,
                )
            )
        return shortcuts

    @staticmethod
    def _normalize_image(path: str) -> str:
        """Unwrap Kodi's image:// form to a path setArt can render.

        Built-in textures (DefaultX.png) and external URLs both come wrapped;
        the inner content is URL-encoded. setArt expects the decoded form.
        """
        if not path.startswith("image://"):
            return path
        inner = path[len("image://"):]
        if inner.endswith("/"):
            inner = inner[:-1]
        return urllib.parse.unquote(inner)

    def _get_video_genres(self, media_type: str) -> list[ResolvedShortcut]:
        """Get video genres (movies or TV shows)."""
        result = self._jsonrpc(
            "VideoLibrary.GetGenres", {"type": media_type, "properties": ["thumbnail"]}
        )
        genres = _collection(result, "genres")
        if not genres:
            return []

        window = "videos"
        db_type = "movies" if media_type == "movie" else "tvshows"

        shortcuts = []
        for genre in genres:
            label = genre.get("label", "")
            thumb = genre.get("thumbnail", "")
            genre_id = genre.get("genreid", 0)
            if label:
                path = f"videodb://{db_type}/genres/{genre_id}/"
                shortcuts.append(
                    ResolvedShortcut(
                        label=label,
                        action=f"ActivateWindow({window},{path},return)",
                        icon=thumb or "DefaultGenre.png",
                    )
                )
        return shortcuts

    def _get_music_genres(self) -> list[ResolvedShortcut]:
        """Get music genres."""
        result = self._jsonrpc("AudioLibrary.GetGenres", {"properties": ["thumbnail"]})
        genres = _collection(result, "genres")
        if not genres:
            return []

        shortcuts = []
        for genre in genres:
            label = genre.get("label", "")
            thumb = genre.get("thumbnail", "")
            genre_id = genre.get("genreid", 0)
            if label:
                path = f"musicdb://genres/{genre_id}/"
                shortcuts.append(
                    ResolvedShortcut(
                        label=label,
                        action=f"ActivateWindow(Music,{path},return)",
                        icon=thumb or "DefaultMusicGenres.png",
                    )
                )
        return shortcuts

    def _get_video_years(self, media_type: str) -> list[ResolvedShortcut]:
        """Get years from video library."""
        if media_type == "movie":
            result = self._jsonrpc("VideoLibrary.GetMovies", {"properties": ["year"]})
            items = _collection(result, "movies")
            db_type = "movies"
        else:
            result = self._jsonrpc("VideoLibrary.GetTVShows", {"properties": ["year"]})
            items = _collection(result, "tvshows")
            db_type = "tvshows"

        years = sorted(
            {item.get("year", 0) for item in items if item.get("year", 0) > 0},
            reverse=True,
        )

        shortcuts = []
        for year in years:
            path = f"videodb://{db_type}/years/{year}/"
            shortcuts.append(
                ResolvedShortcut(
                    label=str(year),
                    action=f"ActivateWindow(Videos,{path},return)",
                    icon="DefaultYear.png",
                )
            )
        return shortcuts

    def _get_video_property(
        self, media_type: str, prop: str, icon_suffix: str
    ) -> list[ResolvedShortcut]:
        """Get video library property values (studios, tags)."""
        if media_type == "movie":
            result = self._jsonrpc("VideoLibrary.GetMovies", {"properties": [prop]})
            items = _collection(result, "movies")
            db_type = "movies"
        else:
            result = self._jsonrpc("VideoLibrary.GetTVShows", {"properties": [prop]})
            items = _collection(result, "tvshows")
            db_type = "tvshows"

        values: set[str] = set()
        for item in items:
            prop_value = item.get(prop, [])
            if isinstance(prop_value, list):
                values.update(prop_value)
            elif prop_value:
                values.add(prop_value)

        shortcuts = []
        for value in sorted(values):
            path = f"videodb://{db_type}/{prop}s/{value}/"
            shortcuts.append(
                ResolvedShortcut(
                    label=value,
                    action=f"ActivateWindow(Videos,{path},return)",
                    icon=f"Default{icon_suffix}.png",
                )
            )
        return shortcuts

    def _get_video_actors(self, media_type: str) -> list[ResolvedShortcut]:
        """Get actors from video library."""
        if media_type == "movie":
            result = self._jsonrpc(
                "VideoLibrary.GetMovies", {"properties": ["cast"], "limits": {"end": 100}}
            )
            items = _collection(result, "movies")
            db_type = "movies"
        else:
            result = self._jsonrpc(
                "VideoLibrary.GetTVShows", {"properties": ["cast"], "limits": {"end": 100}}
            )
            items = _collection(result, "tvshows")
            db_type = "tvshows"

        actors: dict[str, str] = {}
        for item in items:
            for actor in _collection(item, "cast"):
                name = actor.get("name", "")
                if name and name not in actors:
                    actors[name] = actor.get("thumbnail", "")

        shortcuts = []
        for name in sorted(actors.keys()):
            path = f"videodb://{db_type}/actors/{name}/"
            shortcuts.append(
                ResolvedShortcut(
                    label=name,
                    action=f"ActivateWindow(Videos,{path},return)",
                    icon=actors[name] or "DefaultActor.png",
                )
            )
        return shortcuts

    def _get_video_directors(self, media_type: str) -> list[ResolvedShortcut]:
        """Get directors from video library.

        Note: TV shows don't have directors - episodes do. For tvshow media type,
        we query episodes to get directors.
        """
        if media_type == "movie":
            result = self._jsonrpc(
                "VideoLibrary.GetMovies", {"properties": ["director"]}
            )
            items = _collection(result, "movies")
            db_type = "movies"
        else:
            result = self._jsonrpc(
                "VideoLibrary.GetEpisodes",
                {"properties": ["director"], "limits": {"end": 500}},
            )
            items = _collection(result, "episodes")
            db_type = "tvshows"

        directors: set[str] = set()
        for item in items:
            for director in _collection(item, "director"):
                if director:
                    directors.add(director)

        shortcuts = []
        for name in sorted(directors):
            path = f"videodb://{db_type}/directors/{name}/"
            shortcuts.append(
                ResolvedShortcut(
                    label=name,
                    action=f"ActivateWindow(Videos,{path},return)",
                    icon="DefaultDirector.png",
                )
            )
        return shortcuts

    def _get_music_artists(self) -> list[ResolvedShortcut]:
        """Get music artists."""
        result = self._jsonrpc(
            "AudioLibrary.GetArtists", {"properties": ["thumbnail"], "limits": {"end": 100}}
        )
        artists = _collection(result, "artists")
        if not artists:
            return []

        shortcuts = []
        for artist in artists:
            label = artist.get("label", "")
            artist_id = artist.get("artistid", 0)
            thumb = artist.get("thumbnail", "")
            if label and artist_id:
                path = f"musicdb://artists/{artist_id}/"
                shortcuts.append(
                    ResolvedShortcut(
                        label=label,
                        action=f"ActivateWindow(Music,{path},return)",
                        icon=thumb or "DefaultMusicArtists.png",
                    )
                )
        return shortcuts

    def _get_music_albums(self) -> list[ResolvedShortcut]:
        """Get music albums."""
        result = self._jsonrpc(
            "AudioLibrary.GetAlbums",
            {"properties": ["thumbnail", "artist"], "limits": {"end": 100}},
        )
        albums = _collection(result, "albums")
        if not albums:
            return []

        shortcuts = []
        for album in albums:
            label = album.get("label", "")
            album_id = album.get("albumid", 0)
            thumb = album.get("thumbnail", "")
            artists = _collection(album, "artist")
            artist_str = ", ".join(artists) if artists else ""
            if label and album_id:
                path = f"musicdb://albums/{album_id}/"
                shortcuts.append(
                    ResolvedShortcut(
                        label=label,
                        action=f"ActivateWindow(Music,{path},return)",
                        icon=thumb or "DefaultMusicAlbums.png",
                        label2=artist_str,
                    )
                )
        return shortcuts

    def _jsonrpc(self, method: str, params: dict | None = None) -> dict | None:
        """Execute a JSON-RPC request."""
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": 1,
        }

        try:
            response_str = xbmc.executeJSONRPC(json.dumps(request))
            response = json.loads(response_str)

            if "result" in response:
                return response["result"]
            if "error" in response:
                log.warning(f"JSON-RPC error for {method}: {response['error']}")
        except Exception as e:
            log.error(f"JSON-RPC exception for {method}: {e}")

        return None


_provider: ContentProvider | None = None


def resolve_content(content: Content) -> list[ResolvedShortcut]:
    """Resolve a content reference to shortcuts.

    Convenience function using module-level provider instance.
    """
    global _provider
    if _provider is None:
        _provider = ContentProvider()
    return _provider.resolve(content)


def clear_content_cache() -> None:
    """Clear the content provider cache.

    Call this when opening the management dialog to ensure fresh data
    (e.g., newly added favourites are visible in the picker).
    """
    if _provider is not None:
        _provider.clear_cache()
