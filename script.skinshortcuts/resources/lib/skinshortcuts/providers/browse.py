"""Browse provider for navigating Kodi paths.

Uses Files.GetDirectory JSON-RPC to list directory contents and detect
browsable (directory) vs selectable (file) items.
"""

from __future__ import annotations

import json
import time
import urllib.parse
from dataclasses import dataclass

import xbmc

from ..log import get_logger

from ..models.menu import IconOverrides

log = get_logger("BrowseProvider")


def normalize_image(path: str) -> str:
    """Unwrap Kodi's image:// wrapper to the plain path inside.

    Embedded-media art (image://music@.../, video@...) stays wrapped: the
    <type>@ is a texture handler, and unwrapping it yields a dead path.
    """
    if not path.startswith("image://"):
        return path
    inner = path[len("image://"):]
    if inner.endswith("/"):
        inner = inner[:-1]
    if "@" in inner:
        return path
    return urllib.parse.unquote(inner)


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

    def __init__(self, icon_overrides: IconOverrides | None = None) -> None:
        self._icon_overrides = icon_overrides or {}

    def set_icon_overrides(self, overrides: IconOverrides) -> None:
        """Refresh the override map; setter exists for the module-level singleton."""
        self._icon_overrides = overrides or {}

    def list_directory(
        self, path: str, include_art: bool = False
    ) -> list[BrowseItem] | None:
        """List a directory's items, or None if the path isn't listable.

        include_art fetches per-item art for type-aware icons; skip it on big
        listings, art on tens of thousands of items is too slow.
        """
        properties = ["file", "mimetype"]
        if include_art:
            properties.append("art")

        start = time.monotonic()
        result = self._jsonrpc(
            "Files.GetDirectory",
            {
                "directory": path,
                "media": "files",
                "properties": properties,
            },
        )
        log.debug(
            f"list_directory: {path} rows={len((result or {}).get('files') or [])} "
            f"{(time.monotonic() - start) * 1000:.0f}ms"
        )

        if result is None:
            return None

        if "files" not in result:
            return []

        items = []
        for file_info in result["files"] or []:
            label = file_info.get("label", "")
            file_path = file_info.get("file", "")
            filetype = file_info.get("filetype", "file")
            mimetype = file_info.get("mimetype", "")

            if not file_path:
                continue

            icon = ""
            if include_art:
                art = file_info.get("art", {})
                # art.icon is always the generic Kodi default; the fallback below is type-aware
                icon = (
                    art.get("poster", "")
                    or art.get("thumb", "")
                    or file_info.get("thumbnail", "")
                )
                icon = normalize_image(icon)
            if not icon:
                icon = self._get_icon_for_item(file_info, filetype)
            # Overrides key on bare DefaultX.png names; real art paths match none.
            if icon and self._icon_overrides:
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
        """Fallback icon by media type, then filetype, then mimetype."""
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
