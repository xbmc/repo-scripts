"""Actor image download configuration and constants."""
import sys

ILLEGAL_CHARS_ALL = "/\\?"
ILLEGAL_CHARS_WINDOWS = ':*"<>|'
DEFAULT_EXTENSION = ".jpg"


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
