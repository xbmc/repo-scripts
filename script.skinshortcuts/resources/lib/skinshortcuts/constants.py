"""Constants for Skin Shortcuts."""

from __future__ import annotations

try:
    import xbmcvfs

    IN_KODI = True
except ImportError:
    IN_KODI = False

MENUS_FILE = "menus.xml"
WIDGETS_FILE = "widgets.xml"
BACKGROUNDS_FILE = "backgrounds.xml"
PROPERTIES_FILE = "properties.xml"
TEMPLATES_FILE = "templates.xml"
VIEWS_FILE = "views.xml"
INCLUDES_FILE = "script-skinshortcuts-includes.xml"
DATA_DIR = "special://profile/addon_data/script.skinshortcuts/"

DEFAULT_ICON = "DefaultShortcut.png"
DEFAULT_VIEW_PREFIX = "ShortcutView_"

WIDGET_SIBLINGS = ("Label", "Path", "Type", "Target", "Source")
BACKGROUND_SIBLINGS = ("Label", "Path", "Type", "PlaylistType")
WIDGET_EXTRAS = ("Limit", "SortBy", "SortOrder")

WINDOW_MAP: dict[str, str] = {
    "video": "Videos",
    "videos": "Videos",
    "music": "Music",
    "audio": "Music",
    "pictures": "Pictures",
    "images": "Pictures",
    "programs": "Programs",
    "executable": "Programs",
    "files": "Files",
    "games": "Games",
    "game": "Games",
    "pvr": "TVChannels",
    "tv": "TVChannels",
    "radio": "RadioChannels",
    "livetv": "TVChannels",
    "liveradio": "RadioChannels",
}

TARGET_MAP: dict[str, str] = {
    "video": "videos",
    "videos": "videos",
    "music": "music",
    "audio": "music",
    "pictures": "pictures",
    "images": "pictures",
    "image": "pictures",
    "programs": "programs",
    "executable": "programs",
    "games": "games",
    "game": "games",
    "files": "files",
    "file": "files",
    "tv": "tv",
    "radio": "radio",
}

ADDONS_SOURCE_MAP: dict[str, tuple[str, str]] = {
    "video": ("addons://sources/video/", "videos"),
    "videos": ("addons://sources/video/", "videos"),
    "audio": ("addons://sources/audio/", "music"),
    "music": ("addons://sources/audio/", "music"),
    "image": ("addons://sources/image/", "pictures"),
    "pictures": ("addons://sources/image/", "pictures"),
    "executable": ("addons://sources/executable/", "programs"),
    "programs": ("addons://sources/executable/", "programs"),
    "game": ("addons://sources/game/", "games"),
    "games": ("addons://sources/game/", "games"),
}


def get_shortcuts_path() -> str:
    """Path to the current skin's shortcuts folder."""
    if not IN_KODI:
        return ""
    return xbmcvfs.translatePath("special://skin/shortcuts/")


def split_params(params: str) -> list[str]:
    """Split builtin parameters; quotes and brackets keep commas, and outer quotes go."""

    def unquote(param: str) -> str:
        if len(param) > 1 and param[0] == '"' and param[-1] == '"':
            return param[1:-1]
        quote = param.find('"')
        if len(param) > 3 and param[-1] == '"' and 1 < quote < len(param) - 1:
            if param[quote - 1] == "=":
                return param[:quote] + param[quote + 1 : -1]
        return param

    parts: list[str] = []
    current = ""
    in_quotes = False
    last_escaped = False
    depth = 0
    space_at = 0
    for pos, ch in enumerate(params):
        escaped = pos > 0 and params[pos - 1] == "\\" and not last_escaped
        last_escaped = escaped
        if in_quotes:
            if ch == '"' and not escaped:
                in_quotes = False
        else:
            if ch == '"' and not escaped:
                in_quotes = True
            if depth and ch == ")":
                depth -= 1
            if ch == "(":
                depth += 1
            if not depth and ch == ",":
                parts.append(unquote(current[:space_at] if space_at else current))
                current, space_at = "", 0
                continue
        if ch in '"\\' and escaped:
            current = current[:-1] + ch
            continue
        if ch == " " and not in_quotes:
            if not current:
                continue
            if not space_at:
                space_at = len(current)
        else:
            space_at = 0
        current += ch
    last = unquote(current[:space_at] if space_at else current)
    if last or parts:
        parts.append(last)
    return parts


def extract_window_from_action(action: str) -> str:
    """Window an ActivateWindow action opens; empty for any other action."""
    if action.lower().startswith("activatewindow("):
        return next(iter(split_params(action[15:-1])), "")
    return ""


def extract_path_from_action(action: str) -> str:
    """Extract the bare content path from an action, or the action itself if it has no path."""
    lower = action.lower()
    if lower.startswith("activatewindow("):
        params = split_params(action[15:-1])
        if len(params) >= 2:
            return params[1]
    elif lower.startswith("playmedia("):
        return next(iter(split_params(action[10:-1])), "")
    elif lower.startswith("runaddon("):
        addon_id = action[9:-1]
        return f"plugin://{addon_id}/"
    return action
