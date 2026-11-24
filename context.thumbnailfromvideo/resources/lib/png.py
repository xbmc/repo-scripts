"""Minimal pure-Python PNG writer (Kodi ships no imaging library)."""
import struct
import zlib

_SIG = b'\x89PNG\r\n\x1a\n'


def _chunk(tag, data):
    return (struct.pack('>I', len(data)) + tag + data +
            struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff))


def encode_rgb(width, height, rgb, text=None):
    """text: optional tEXt chunk data (keyword NUL value), placed before the image data."""
    stride = width * 3
    raw = b''.join(b'\x00' + rgb[y * stride:(y + 1) * stride] for y in range(height))
    ihdr = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    return (_SIG + _chunk(b'IHDR', ihdr) + (_chunk(b'tEXt', text) if text else b'') +
            _chunk(b'IDAT', zlib.compress(raw, 6)) + _chunk(b'IEND', b''))


def bgra_to_rgb(data, width, height):
    n = width * height
    src = bytes(data[:n * 4])
    rgb = bytearray(n * 3)
    rgb[0::3] = src[2::4]
    rgb[1::3] = src[1::4]
    rgb[2::3] = src[0::4]
    return bytes(rgb)


def find_content_box(data, width, height, max_mean=8, threshold=40, max_bright=0.02,
                     step=4, edge_skip=4, min_bar=4, grey_mean=28, grey_dev=12,
                     grey_outliers=0.03, grey_match=8, grey_step=20, grey_look=24):
    """Return (left, top, right, bottom) of the picture inside black bars.

    A row/column is a bar line when either
    - it is black: average channel value below `max_mean` and at most
      `max_bright` of the samples above `threshold` (digital bars, ~0-6), or
    - it is flat dark grey: average below `grey_mean`, at most `grey_outliers`
      of the samples more than `grey_dev` away from that average, and within
      `grey_match` of the bar's first line (analog/VHS "black", ~12-20).
    Dark scenes have texture and changing levels, so they are kept. Up to
    `edge_skip` non-bar lines at the very edge (DVD/VHS edge artefacts) are
    skipped before a bar.
    """
    stride = width * 4
    level = {}  # mean of the first bar line, per edge being scanned

    def kind(samples, key=None):
        """'black', 'grey' (flat dark grey bar line) or None."""
        n = len(samples)
        if not n:
            return None
        mean = sum(samples) / float(n)
        if mean < max_mean and sum(v > threshold for v in samples) <= n * max_bright:
            return 'black'
        if mean >= grey_mean:
            return None
        lo, hi = mean - grey_dev, mean + grey_dev
        if sum(1 for v in samples if v < lo or v > hi) > n * grey_outliers:
            return None
        ref = level.setdefault(key, mean)
        return 'grey' if abs(mean - ref) <= grey_match else None

    def line_mean(samples):
        return sum(samples) / float(len(samples)) if samples else 0.0

    def row_samples(y):
        row = data[y * stride:(y + 1) * stride]
        s = step * 4
        return row[0::s] + row[1::s] + row[2::s]

    def col_samples(x, top, bottom):
        s = stride * step
        a, b = top * stride + x * 4, bottom * stride
        return data[a:b:s] + data[a + 1:b:s] + data[a + 2:b:s]

    def edge(samples_at, limit, key):
        """How many lines to trim from one edge; samples_at(i) = line i from it."""
        # The bar starts at the first run of at least min_bar dark lines near
        # the edge. Lines before it are skipped: VHS/DVD edge noise and the
        # white dashes of teletext/VBI data lines that some videos show at the
        # very top (they can sit between a few black lines and the real bar).
        zone = max(edge_skip, limit // 25)  # ~1.6% of the frame
        first = None
        i = 0
        while i <= zone:
            level.pop(key, None)  # a grey bar's level is set by its first grey line
            j = i
            while j < limit and j - i < min_bar and kind(samples_at(j), key):
                j += 1
            if j - i >= min_bar:
                first = i
                break
            i = j + 1
        if first is None:
            return 0
        level.pop(key, None)
        i, black_run, used_grey = first, 0, False
        darkest = 255.0
        while i < limit:
            line = samples_at(i)
            k = kind(line, key)
            if not k:
                break
            darkest = min(darkest, line_mean(line))
            if k == 'black' and not used_grey:
                black_run += 1
            else:
                used_grey = True
            i += 1
        # the plain black part alone (digital bars), as a fallback
        black_only = first + black_run if black_run >= min_bar else 0
        if not used_grey:
            return black_only
        if i - first < min_bar:
            return black_only
        # A grey bar must end in a clear step up to the picture; a dark scene
        # just gets lighter gradually, so it is left alone. Analog bars often
        # fade out over a few dozen lines, so look a little further.
        # The step is measured from the bar's darkest line, and the window grows
        # with the frame size (a 1440-line capture needs more lines than 800).
        ref = darkest
        look = max(grey_look, limit // 8)
        after = [line_mean(samples_at(j)) for j in range(i, min(i + look, limit + look))]
        if not after or max(after) < ref + grey_step:
            return black_only
        # drop the fading transition lines too
        end = i + look
        while i < end and line_mean(samples_at(i)) < ref + grey_step / 2.0:
            i += 1
        return i

    limit_y, limit_x = int(height * 0.4), int(width * 0.4)
    top = edge(row_samples, limit_y, 't')
    bottom = height - edge(lambda i: row_samples(height - 1 - i), limit_y, 'b')
    left = edge(lambda i: col_samples(i, top, bottom), limit_x, 'l')
    right = width - edge(lambda i: col_samples(width - 1 - i, top, bottom), limit_x, 'r')

    # mostly-black frame (fade, night scene): don't crop at all
    if right - left < width * 0.3 or bottom - top < height * 0.3:
        return 0, 0, width, height
    # shave 2 px off cropped edges to drop the soft/greyish transition line
    if top:
        top = min(top + 2, bottom - 1)
    if bottom < height:
        bottom = max(bottom - 2, top + 1)
    if left:
        left = min(left + 2, right - 1)
    if right < width:
        right = max(right - 2, left + 1)
    # even dimensions
    right -= (right - left) % 2
    bottom -= (bottom - top) % 2
    return left, top, right, bottom


def crop_bgra(data, width, box):
    left, top, right, bottom = box
    stride = width * 4
    rows = (data[y * stride + left * 4:y * stride + right * 4] for y in range(top, bottom))
    return b''.join(bytes(r) for r in rows), right - left, bottom - top


def write_bgra(path, width, height, data, text=None):
    """Write a BGRA buffer (as returned by xbmc.RenderCapture) to a PNG file."""
    with open(path, 'wb') as f:
        f.write(encode_rgb(width, height, bgra_to_rgb(data, width, height), text))


def write_solid(path, size=8):
    """Write a small solid white PNG, used as a tintable background texture."""
    with open(path, 'wb') as f:
        f.write(encode_rgb(size, size, b'\xff' * (size * size * 3)))
