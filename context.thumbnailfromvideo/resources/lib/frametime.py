"""The video time a thumbnail was taken at, stored inside the image file.

PNG: a tEXt chunk   framethumb_time = 88.24
JPG: a COM segment  framethumb_time=88.24
Both are ignored by image viewers and by Kodi; only this add-on reads them.
"""
import struct

KEY = 'framethumb_time'
HEAD_BYTES = 65536  # the note sits near the start of the file


def png_chunk(seconds):
    """Data part of the PNG tEXt chunk (keyword NUL text)."""
    return KEY.encode('latin-1') + b'\0' + ('%.3f' % seconds).encode('latin-1')


def jpeg_comment(seconds):
    return ('%s=%.3f' % (KEY, seconds)).encode('latin-1')


def parse(head):
    """Seconds stored in the first bytes of a PNG/JPG file, or None."""
    try:
        if head[:8] == b'\x89PNG\r\n\x1a\n':
            pos = 8
            while pos + 8 <= len(head):
                length, tag = struct.unpack('>I4s', head[pos:pos + 8])
                if tag in (b'IDAT', b'IEND'):
                    return None
                if tag == b'tEXt':
                    key, _, text = head[pos + 8:pos + 8 + length].partition(b'\0')
                    if key.decode('latin-1') == KEY:
                        return _seconds(text.decode('latin-1'))
                pos += 12 + length
        elif head[:2] == b'\xff\xd8':
            pos = 2
            while pos + 4 <= len(head) and head[pos] == 0xFF:
                marker = head[pos + 1]
                if marker == 0xDA:  # image data starts: no more headers
                    return None
                length = struct.unpack('>H', head[pos + 2:pos + 4])[0]
                if marker == 0xFE:
                    text = head[pos + 4:pos + 2 + length].decode('latin-1')
                    if text.startswith(KEY + '='):
                        return _seconds(text[len(KEY) + 1:])
                pos += 2 + length
    except (struct.error, IndexError, UnicodeDecodeError):
        pass
    return None


def _seconds(text):
    try:
        v = float(text.strip())
    except ValueError:
        return None
    return v if v > 0 else None
