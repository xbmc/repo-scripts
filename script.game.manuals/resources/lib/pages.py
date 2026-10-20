# -*- coding: utf-8 -*-
"""A manual's pages, as pictures Kodi can show.

A PDF is opened through vfs.pdf, which presents it as a folder of page
pictures; a comic archive through Kodi's own zip and rar folders. Either way
the viewer is left with an ordered list of picture paths.
"""

import re
import struct
from urllib.parse import quote

PICTURES = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")

#: The folder Kodi shows each kind of manual's pages through
PROTOCOLS = {".pdf": "pdf", ".cbz": "zip", ".cbr": "rar"}
#: The add-ons that provide those folders, where Kodi has none of its own
PROTOCOL_ADDONS = {"pdf": "vfs.pdf", "rar": "vfs.rar"}


def pages_folder(manual_path):
    """The folder holding a manual's pages, or "" for a kind that has none."""
    dot = manual_path.rfind(".")
    protocol = PROTOCOLS.get(manual_path[dot:].lower()) if dot > 0 else None
    if not protocol:
        return ""
    # Kodi's archive folders name the archive in the hostname, URL encoded, and
    # Kodi writes the escapes in lower case
    encoded = re.sub(r"%[0-9A-F]{2}", lambda m: m.group(0).lower(), quote(manual_path, safe="-_.!()"))
    return "%s://%s/" % (protocol, encoded)


def reader_addon(manual_path):
    """The add-on a manual's pages are read through, or "" when Kodi reads them itself."""
    dot = manual_path.rfind(".")
    protocol = PROTOCOLS.get(manual_path[dot:].lower()) if dot > 0 else None
    return PROTOCOL_ADDONS.get(protocol, "")


def natural_key(name):
    """Sorts "page2" before "page10", as a person would number them."""
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", name)]


def ordered_pictures(names):
    """The pictures among a folder's names, in reading order."""
    return sorted((n for n in names if n.lower().endswith(PICTURES)), key=natural_key)


def picture_size(header):
    """A picture's width and height from its first bytes, or None.

    Enough of the file to reach the size: a PNG's first 24 bytes, while a JPEG
    may need its first few kilobytes to get past its metadata.
    """
    if header[:8] == b"\x89PNG\r\n\x1a\n" and len(header) >= 24:
        return struct.unpack(">II", header[16:24])
    if header[:6] in (b"GIF87a", b"GIF89a") and len(header) >= 10:
        return struct.unpack("<HH", header[6:10])
    if header[:2] == b"BM" and len(header) >= 26:
        width, height = struct.unpack("<ii", header[18:26])
        return width, abs(height)
    if header[:2] == b"\xff\xd8":
        return _jpeg_size(header)
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP" and len(header) >= 30:
        return _webp_size(header)
    return None


def _webp_size(data):
    chunk = data[12:16]
    if chunk == b"VP8 " and data[23:26] == b"\x9d\x01\x2a":
        width, height = struct.unpack("<HH", data[26:30])
        return width & 0x3FFF, height & 0x3FFF
    if chunk == b"VP8L" and data[20:21] == b"\x2f":
        bits = struct.unpack("<I", data[21:25])[0]
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    if chunk == b"VP8X":
        width = int.from_bytes(data[24:27], "little") + 1
        height = int.from_bytes(data[27:30], "little") + 1
        return width, height
    return None


def _jpeg_size(data):
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            return None
        marker = data[i + 1]
        if marker == 0xFF:
            i += 1
            continue
        length = struct.unpack(">H", data[i + 2:i + 4])[0]
        # Every start-of-frame marker, baseline, progressive or otherwise
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            height, width = struct.unpack(">HH", data[i + 5:i + 9])
            return width, height
        i += 2 + length
    return None
