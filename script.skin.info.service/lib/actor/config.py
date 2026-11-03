"""Actor image download configuration and constants."""
import sys
from typing import Final

ILLEGAL_CHARS_ALL: Final = "/\\?"
ILLEGAL_CHARS_WINDOWS: Final = ':*"<>|'
DEFAULT_EXTENSION: Final = ".jpg"


def sanitize_actor_filename(name: str, extension: str = DEFAULT_EXTENSION) -> str:
    """Convert actor name to Kodi-compatible filename, matching Kodi's GetSafeFile()."""
    filename = name.replace(" ", "_")

    for char in ILLEGAL_CHARS_ALL:
        filename = filename.replace(char, "_")

    if sys.platform == "win32":
        for char in ILLEGAL_CHARS_WINDOWS:
            filename = filename.replace(char, "_")
        filename = filename.rstrip(". ")

    return filename + extension
