"""Browse provider for navigating Kodi paths.

Uses Files.GetDirectory JSON-RPC to list directory contents and detect
browsable (directory) vs selectable (file) items.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import xbmc

from ..log import get_logger

log = get_logger("BrowseProvider")


@dataclass
class BrowseItem:
    """An item from a directory listing."""

    label: str
    path: str
    icon: str
    is_directory: bool
    mimetype: str = ""


class BrowseProvider:
    """Lists directory contents via JSON-RPC."""

    def __init__(self, icon_overrides: dict[str, str] | None = None) -> None:
        self._icon_overrides = icon_overrides or {}

    def set_icon_overrides(self, overrides: dict[str, str]) -> None:
        """Refresh the override map; setter exists for the module-level singleton."""
        self._icon_overrides = overrides or {}

    def list_directory(
        self, path: str, include_art: bool = False
    ) -> list[BrowseItem] | None:
        """List contents of a directory.

        Args:
            path: The path to list (plugin://, videodb://, library://, etc.)
            include_art: Ask Kodi for per-item `art` so BrowseItem.icon reflects
                each item's specific icon (e.g., DefaultMusicGenres.png). Leave
                False for large lists or plain-text display; fetching art for
                tens of thousands of library items is prohibitively slow.

        Returns:
            List of BrowseItem objects, empty list for empty directories,
            or None if path is not listable (error).
        """
        properties = ["file", "mimetype"]
        if include_art:
            properties.append("art")

        result = self._jsonrpc(
            "Files.GetDirectory",
            {
                "directory": path,
                "media": "files",
                "properties": properties,
            },
        )

        if result is None:
            return None

        if "files" not in result:
            return []

        items = []
        for file_info in result["files"]:
            label = file_info.get("label", "")
            file_path = file_info.get("file", "")
            filetype = file_info.get("filetype", "file")
            mimetype = file_info.get("mimetype", "")

            if not file_path:
                continue

            icon = ""
            if include_art:
                art = file_info.get("art", {})
                # Prefer per-item imagery. Skip art.icon - it's always the
                # generic Kodi default; our fallback provides a type-aware one.
                icon = (
                    art.get("poster", "")
                    or art.get("thumb", "")
                    or file_info.get("thumbnail", "")
                )
            if not icon:
                icon = self._get_icon_for_item(file_info, filetype)
                if self._icon_overrides:
                    icon = self._icon_overrides.get(icon, icon)

            items.append(
                BrowseItem(
                    label=label,
                    path=file_path,
                    icon=icon,
                    is_directory=(filetype == "directory"),
                    mimetype=mimetype,
                )
            )

        return items

    _TYPE_DEFAULTS: dict[str, str] = {
        "movie": "DefaultMovies.png",
        "tvshow": "DefaultTVShows.png",
        "season": "DefaultTVShows.png",
        "episode": "DefaultTVShows.png",
        "musicvideo": "DefaultMusicVideos.png",
        "album": "DefaultAlbumCover.png",
        "artist": "DefaultArtist.png",
        "song": "DefaultAudio.png",
        "genre": "DefaultGenre.png",
    }

    def _get_icon_for_item(self, file_info: dict, filetype: str) -> str:
        """Determine appropriate icon for an item."""
        item_type = file_info.get("type", "")
        if item_type in self._TYPE_DEFAULTS:
            return self._TYPE_DEFAULTS[item_type]

        if filetype == "directory":
            return "DefaultFolder.png"

        mimetype = file_info.get("mimetype", "")
        if mimetype.startswith("video/"):
            return "DefaultVideo.png"
        if mimetype.startswith("audio/"):
            return "DefaultAudio.png"
        if mimetype.startswith("image/"):
            return "DefaultPicture.png"

        return "DefaultFile.png"

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


_provider: BrowseProvider | None = None


def get_browse_provider() -> BrowseProvider:
    """Get the module-level browse provider instance."""
    global _provider
    if _provider is None:
        _provider = BrowseProvider()
    return _provider
