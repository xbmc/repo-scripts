"""Texture cache URL filtering and parsing utilities."""
from __future__ import annotations

import re
import urllib.parse
from lib.kodi.client import decode_image_url

_SYSTEM_PATH_MARKERS = ('/addons/', '\\addons\\', '/system/', '\\system\\')


def _parse_image_url(url: str) -> str:
    """Strip the `image://` wrapper and trailing `/`. Returns the input unchanged if not wrapped."""
    if not url or not url.startswith('image://'):
        return url
    return url[8:-1] if url.endswith('/') else url[8:]


def _is_system_artwork(text: str) -> bool:
    """True if `text` looks like an addon/system path or a Kodi `Default*.png` placeholder."""
    if any(marker in text for marker in _SYSTEM_PATH_MARKERS):
        return True
    if 'Default' in text and text.endswith('.png'):
        return True
    return False


def should_precache_url(url: str) -> bool:
    """True for cacheable library artwork URLs.

    Skips auto-generated `video@`/`music@` thumbnails, addon icons, plugin URLs, and system files.
    """
    if not url:
        return False

    decoded = decode_image_url(url)

    if decoded.startswith('image://video@') or decoded.startswith('image://music@'):
        return False

    if 'plugin://' in decoded:
        return False

    return not _is_system_artwork(decoded)


# `D:` through `Z:` are valid library drive letters; `C:` is excluded because that's where
# Kodi (and addon system) lives; a path on `C:` is almost certainly system, not library.
_LIBRARY_DRIVE_RE = re.compile(r'^[D-Z]:', re.IGNORECASE)


def is_library_artwork_url(url: str) -> bool:
    """True if URL points at library artwork; False for addon icons, system files,
    or special folders.

    Recognised library: HTTP/HTTPS, `image://video@`/`music@`, drive-letter paths, SMB/NFS shares.
    """
    if not url:
        return False

    inner_url = _parse_image_url(url) if url.startswith('image://') else url
    decoded_url = urllib.parse.unquote(inner_url)

    if _is_system_artwork(decoded_url):
        return False

    special_folders = (
        '/.actors/', '\\.actors\\',
        '/.extrafanart/', '\\.extrafanart\\',
        '/.extrathumbs/', '\\.extrathumbs\\'
    )
    if any(marker in decoded_url for marker in special_folders):
        return False

    if decoded_url.startswith('http://') or decoded_url.startswith('https://'):
        return True

    if url.startswith('image://') and '@' in inner_url:
        return True

    if _LIBRARY_DRIVE_RE.match(decoded_url):
        return True

    if decoded_url.startswith('\\\\') or decoded_url.startswith('smb://') or decoded_url.startswith('nfs://'):
        return True

    return False
