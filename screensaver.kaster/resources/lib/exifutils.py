# -*- coding: utf-8 -*-
"""
  Copyright (C) 2026-2026 guss77
  This file is part of kaster

  SPDX-License-Identifier: GPL-2.0-or-later
  See LICENSE for more information.

  Tiny, dependency free reader for the photographer name embedded in an image
  file. It understands the metadata formats normally used to credit photos:

    * EXIF  - Artist (0x013B) and XPAuthor (0x9C9D)
    * IPTC  - By-line (record 2, dataset 25)
    * XMP   - dc:creator / photoshop:Authors

  in both JPEG (APP1/APP13) and PNG (eXIf/tEXt) files. The module deliberately
  has no Kodi imports so that it can be used with any byte source.
"""
import re
import struct
import xml.etree.ElementTree as ET

_JPEG_SOI = b'\xff\xd8'
_PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'
_EXIF_PREFIX = b'Exif\x00\x00'
_XMP_PREFIX = b'http://ns.adobe.com/xap/1.0/\x00'
_PHOTOSHOP_PREFIX = b'Photoshop 3.0\x00'

_EXIF_ARTIST = 0x013B
_EXIF_XPAUTHOR = 0x9C9D
_IPTC_RESOURCE = 0x0404
_IPTC_BYLINE = (2, 25)

# Size in bytes of each TIFF field type (0 means unknown).
_TIFF_TYPE_SIZES = {
    1: 1,   # BYTE
    2: 1,   # ASCII
    3: 2,   # SHORT
    4: 4,   # LONG
    5: 8,   # RATIONAL
    6: 1,   # SBYTE
    7: 1,   # UNDEFINED
    8: 2,   # SSHORT
    9: 4,   # SLONG
    10: 8,  # SRATIONAL
    11: 4,  # FLOAT
    12: 8,  # DOUBLE
}

_XMP_METADATA = re.compile(br'<x:xmpmeta[\s\S]*?</x:xmpmeta>', re.I)


def get_photographer(data):
    """Return the photographer name stored in *data*, or None when absent."""
    if not data:
        return None

    if data.startswith(_JPEG_SOI):
        for marker, payload in _iter_jpeg_segments(data):
            if marker == 0xE1:  # APP1
                if payload.startswith(_EXIF_PREFIX):
                    name = _from_tiff(payload[len(_EXIF_PREFIX):])
                    if name:
                        return name
                elif payload.startswith(_XMP_PREFIX):
                    name = _from_xmp(payload[len(_XMP_PREFIX):])
                    if name:
                        return name
            elif marker == 0xED and payload.startswith(_PHOTOSHOP_PREFIX):  # APP13
                name = _from_iptc(payload)
                if name:
                    return name
    elif data.startswith(_PNG_SIGNATURE):
        for chunk_type, chunk in _iter_png_chunks(data):
            if chunk_type == b'eXIf':
                name = _from_tiff(chunk)
                if name:
                    return name
            elif chunk_type in (b'tEXt', b'iTXt', b'zTXt'):
                name = _from_xmp(chunk)
                if name:
                    return name
    return None


def _iter_jpeg_segments(data):
    """Yield (marker, payload) for every JPEG segment before the image data."""
    pos = 2
    while pos + 4 <= len(data):
        if data[pos] != 0xFF:
            pos += 1
            continue
        marker = data[pos + 1]
        if marker == 0xFF:  # fill byte
            pos += 1
            continue
        if marker == 0xD9 or 0xD0 <= marker <= 0xD7:  # EOI / restart markers
            pos += 2
            continue
        if marker == 0xDA:  # SOS - compressed image data follows
            break
        length = struct.unpack_from('>H', data, pos + 2)[0]
        if length < 2 or pos + 2 + length > len(data):
            break
        yield marker, data[pos + 4:pos + 2 + length]
        pos += 2 + length


def _iter_png_chunks(data):
    """Yield (type, data) for every chunk of a PNG file."""
    pos = len(_PNG_SIGNATURE)
    while pos + 12 <= len(data):
        length = struct.unpack_from('>I', data, pos)[0]
        chunk_type = data[pos + 4:pos + 8]
        if pos + 12 + length > len(data):
            break
        yield chunk_type, data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if chunk_type == b'IEND':
            break


def _from_tiff(tiff):
    """Read the EXIF artist fields from the IFD0 of a TIFF block."""
    if len(tiff) < 8:
        return None
    if tiff[:2] == b'II':
        endian = '<'
    elif tiff[:2] == b'MM':
        endian = '>'
    else:
        return None
    try:
        if struct.unpack_from(endian + 'H', tiff, 2)[0] != 42:
            return None
        offset = struct.unpack_from(endian + 'I', tiff, 4)[0]
    except struct.error:
        return None

    entries = _read_ifd(tiff, endian, offset)
    name = _clean(_text_value(tiff, endian, entries.get(_EXIF_ARTIST)))
    if name:
        return name
    # XPAuthor is stored as UTF-16LE, including a trailing null character.
    name = _clean(_entry_value(tiff, endian, entries.get(_EXIF_XPAUTHOR))
                  .decode('utf-16-le', 'ignore'))
    if name:
        return name
    return None


def _read_ifd(tiff, endian, offset):
    """Return {tag: (type, count, raw_value)} for the IFD at *offset*."""
    if offset <= 0 or offset + 2 > len(tiff):
        return {}
    try:
        count = struct.unpack_from(endian + 'H', tiff, offset)[0]
    except struct.error:
        return {}
    entries = {}
    for index in range(count):
        pos = offset + 2 + index * 12
        if pos + 12 > len(tiff):
            break
        try:
            tag, field_type, num = struct.unpack_from(endian + 'HHI', tiff, pos)
        except struct.error:
            break
        entries[tag] = (field_type, num, tiff[pos + 8:pos + 12])
    return entries


def _entry_value(tiff, endian, entry):
    """Resolve the bytes of a TIFF field, following offsets when necessary."""
    if not entry:
        return b''
    field_type, num, raw = entry
    size = _TIFF_TYPE_SIZES.get(field_type, 1)
    total = size * num
    if not total or total > len(tiff):
        return b''
    if total <= 4:
        return raw[:total]
    try:
        offset = struct.unpack(endian + 'I', raw)[0]
    except struct.error:
        return b''
    return tiff[offset:offset + total]


def _text_value(tiff, endian, entry):
    return _entry_value(tiff, endian, entry).decode('utf-8', 'ignore')


def _from_iptc(payload):
    """Walk Photoshop image resource blocks looking for the IPTC By-line."""
    pos = len(_PHOTOSHOP_PREFIX)
    while pos + 4 <= len(payload):
        if payload[pos:pos + 4] != b'8BIM':
            break
        pos += 4
        if pos + 2 > len(payload):
            break
        resource_id = struct.unpack_from('>H', payload, pos)[0]
        pos += 2
        name_length = payload[pos]
        pos += 1 + name_length
        if (name_length + 1) % 2:  # Pascal string is padded to an even length
            pos += 1
        if pos + 4 > len(payload):
            break
        size = struct.unpack_from('>I', payload, pos)[0]
        pos += 4
        block = payload[pos:pos + size]
        pos += size
        if size % 2:
            pos += 1
        if resource_id == _IPTC_RESOURCE:
            name = _iptc_byteline(block)
            if name:
                return name
    return None


def _iptc_byteline(block):
    """Find IPTC record 2, dataset 25 (photographer) in an IPTC-NAA block."""
    pos = 0
    while pos + 5 <= len(block):
        if block[pos] != 0x1C:
            pos += 1
            continue
        record, dataset = block[pos + 1], block[pos + 2]
        size = struct.unpack_from('>H', block, pos + 3)[0]
        value = block[pos + 5:pos + 5 + size]
        if (record, dataset) == _IPTC_BYLINE:
            try:
                return _clean(value.decode('utf-8'))
            except UnicodeDecodeError:
                return _clean(value.decode('latin-1', 'ignore'))
        pos += 5 + size
    return None


def _from_xmp(data):
    """Read dc:creator / photoshop:Authors from an XMP packet."""
    match = _XMP_METADATA.search(data)
    packet = match.group(0) if match else data
    try:
        root = ET.fromstring(packet)
    except Exception:
        return None
    for element in root.iter():
        tag = element.tag.lower()
        if tag.endswith('creator') or tag.endswith('authors'):
            names = []
            for child in element.iter():
                text = _clean(child.text or '')
                if text and text not in names:
                    names.append(text)
            if names:
                return ', '.join(names)
    return None


def _clean(text):
    return text.replace('\x00', '').strip()
