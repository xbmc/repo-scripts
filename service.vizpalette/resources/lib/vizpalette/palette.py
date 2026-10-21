# Visualizer Palette (service.vizpalette)
# Copyright (C) 2026 Omar Kamel
# SPDX-License-Identifier: GPL-2.0-or-later
"""Album palette extraction + tiny PNG writer. Pure Python, no Kodi imports (unit-testable on a PC).

The algorithm is a line-for-line port of extractPalette()/setCover() in visualizers/preview/index.html, so the bench
and the Shield produce the same four colours in the same order:
  48x48 downscale (whole cover stretched, like canvas drawImage) -> k-means k=6, init at luminance quantiles,
  10 iterations -> c0 dominant, c1 second distinct, c2 accent (most vivid), c3 shadow (darkest).
JS semantics kept on purpose: stable sorts, strict '<' (first centroid wins ties), counts from the last assignment
pass, empty clusters keep their centroid, Math.round = floor(x + 0.5).
Deliberate differences from the bench (the skins read these as VizPalette.Color1..4, so each must be a usable,
distinct colour):
- 1.1.1: the shadow c3 is always a real darker shade (pale covers used to repeat the main colour).
- 1.1.3: no near-black colours. A black background is a k-means cluster like any other (JPEG noise makes it about
  0,0,1), and on a dark cover it used to become both Color2 and Color4 (Guns N' Roses "American Communism":
  FF000001 twice, Shield 2026-10-21). Now c0/c1/c2 are picked from clusters of at least MIN_L lightness (CIE L*),
  c2 is kept apart from c1, and c3 is the darkest swatch only if it is clearly darker than c0, close to its hue and
  at least SHADOW_MIN_L; otherwise c3 is c0 darkened (same hue). Anything still missing is a shade of c0.
"""
import math
import struct
import zlib

K = 6
ITERATIONS = 10
SAMPLE = 48
ART = 128
SHADOW_MAX = 0.75       # a darkest swatch counts as a shadow if its luminance is at most this fraction of the main's
SHADOW_DARK = 48        # ... or if it is this dark anyway (luminance 0..255)
MIN_L = 12              # Color1..3 are at least this light (CIE L*, 0..100); darker clusters are skipped
SHADOW_MIN_L = 8        # the shadow Color4 is never darker than this (no pure black)
SHADOW_L = 0.45         # a derived shadow is the main colour at this fraction of its L* (same hue)
SHADOW_HUE = 40         # a dark swatch is only a shadow if its hue is within this many degrees of the main's
APART = 24              # two colours closer than this (RGB distance) count as the same
HUGE = 2400  # covers above this many px on a side are decoded at reduced scale (Kodi's own cached thumbs are smaller)


def lum(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _hsv(c):
    r, g, b = c[0] / 255, c[1] / 255, c[2] / 255
    mx, mn = max(r, g, b), min(r, g, b)
    return ((mx - mn) / mx if mx else 0), mx


def _lin(v):
    v /= 255.0
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def lstar(c):
    """CIE L* (0..100) of an sRGB colour."""
    y = 0.2126 * _lin(c[0]) + 0.7152 * _lin(c[1]) + 0.0722 * _lin(c[2])
    return 116 * y ** (1 / 3.0) - 16 if y > 216 / 24389.0 else y * 24389 / 27.0


def _hue(c):
    r, g, b = c[0], c[1], c[2]
    mx, mn = max(r, g, b), min(r, g, b)
    if mx == mn:
        return None
    if mx == r:
        h = (g - b) / float(mx - mn) % 6
    elif mx == g:
        h = (b - r) / float(mx - mn) + 2
    else:
        h = (r - g) / float(mx - mn) + 4
    return h * 60


def _same_hue(a, b):
    """Close in hue; two greys (or near-greys) count as the same hue, a grey and a colour do not."""
    sa, sb = _hsv(a)[0], _hsv(b)[0]
    if sa < 0.15 or sb < 0.15:
        return sa < 0.15 and sb < 0.15
    d = abs(_hue(a) - _hue(b)) % 360
    return min(d, 360 - d) <= SHADOW_HUE


def shade(c, target):
    """c with its hue and saturation kept (RGB scaled) at lightness L* = target, as ints. Black becomes grey."""
    target = max(0.0, min(100.0, target))
    if max(c) < 1:
        c = (1, 1, 1)
    lo, hi = 0.0, 255.0 / max(c)
    for _ in range(30):
        k = (lo + hi) / 2
        if lstar([v * k for v in c]) < target:
            lo = k
        else:
            hi = k
    return [int(min(255, math.ceil(v * hi - 1e-9))) for v in c]  # rounded up: never below target


def _rgb(x):
    return [int(math.floor(v + 0.5)) for v in x['c']]


def extract_palette(px):
    """px: list of (r, g, b) ints in row-major order. Returns [[r, g, b]] * 4 (ints 0..255)."""
    n = len(px)
    srt = sorted(px, key=lum)  # stable, like Array.prototype.sort
    cents = [list(srt[(2 * i + 1) * n // (2 * K)]) for i in range(K)]
    counts = [0] * K
    for _ in range(ITERATIONS):
        sums = [[0.0, 0.0, 0.0, 0] for _ in range(K)]
        cs = [(c[0], c[1], c[2]) for c in cents]
        for p in px:
            r, g, b = p
            best, bd = 0, 1e18
            for k, (cr, cg, cb) in enumerate(cs):
                dr, dg, db = r - cr, g - cg, b - cb
                d = dr * dr + dg * dg + db * db  # monotonic in hypot(); same argmin, much cheaper
                if d < bd:
                    bd, best = d, k
            s = sums[best]
            s[0] += r
            s[1] += g
            s[2] += b
            s[3] += 1
        cents = [[s[0] / s[3], s[1] / s[3], s[2] / s[3]] if s[3] else c for c, s in zip(cents, sums)]
        counts = [s[3] for s in sums]

    cl = []
    for c, cnt in zip(cents, counts):
        if cnt > 0:
            s, v = _hsv(c)
            cl.append({'c': c, 'n': cnt, 's': s, 'v': v})

    def score(x):
        return x['n'] * (0.35 + x['s'])

    by_score = _sort_desc(cl, score)
    for x in cl:
        x['L'] = lstar(x['c'])
    usable = [x for x in by_score if x['L'] >= MIN_L]
    c0 = (next((x for x in usable if x['v'] > 0.12), None) or next((x for x in by_score if x['v'] > 0.12), None)
          or by_score[0])
    p0 = _rgb(c0) if c0['L'] >= MIN_L else shade(c0['c'], MIN_L)  # a dark cover's main colour, lifted
    l0 = lstar(p0)
    others = [x for x in usable if x is not c0]
    c1 = (next((x for x in others if dist(x['c'], p0) > 48), None)
          or next((x for x in others if dist(x['c'], p0) > APART), None))
    p1 = _rgb(c1) if c1 else shade(p0, l0 + 25 if l0 < 60 else l0 - 25)  # no second colour: a shade of the main
    rest = [x for x in others if x is not c1 and dist(x['c'], p0) > APART and dist(x['c'], p1) > APART]
    if rest:
        p2 = _rgb(_sort_desc(rest, lambda x: x['s'] * x['v'] + 1e-4 * x['n'])[0])
    else:  # a shade of the main as far from Color1 and Color2 as possible
        l1 = lstar(p1)
        p2 = shade(p0, max((t for t in (l0 + 45, l0 - 30, l0 + 25, l0 - 15, 90, MIN_L + 4) if MIN_L <= t <= 95),
                           key=lambda t: min(abs(t - l0), abs(t - l1))))
    c3 = sorted(cl, key=lambda x: lum(x['c']))[0]
    return [p0, p1, p2, shadow(p0, _rgb(c3), c3 is c0, (p1, p2))]


def shadow(main, darkest, same=False, avoid=()):
    """The shadow colour (Color4): the darkest swatch when it is clearly darker than the main colour, close to its
    hue, not near-black and not one of the other colours; else the main colour darkened (same hue). A pale cover
    gave Color4 == Color1 (Teen Dream, 1.1.1), a dark one gave black (American Communism, 1.1.3)."""
    lm, ld = lstar(main), lstar(darkest)
    if (not same and ld >= SHADOW_MIN_L and (lum(darkest) <= SHADOW_MAX * lum(main) or lum(darkest) <= SHADOW_DARK)
            and ld < lm - 5 and _same_hue(darkest, main) and all(dist(darkest, a) > APART for a in avoid)):
        return list(darkest)
    top = max(SHADOW_MIN_L, min(SHADOW_L * lm, lm - 5))
    tries = [shade(main, top - i * (top - SHADOW_MIN_L) / 8.0) for i in range(9)]  # darker until clear of Color2/3
    return next((c for c in tries if all(dist(c, a) > APART for a in avoid)),
                max(tries, key=lambda c: min([dist(c, a) for a in avoid] or [0])))


def _sort_desc(items, key):
    """JS `arr.sort((a, b) => key(b) - key(a))`: descending and stable (ties keep input order)."""
    return sorted(items, key=lambda x: -key(x))


# ------------------------------------------------------------------------------------------------ PNG writer
def png_rgba(width, height, rgba):
    """Encode 8-bit RGBA bytes (row 0 = top) as a PNG. Same layout lodepng hands to Shadertoy."""
    raw = bytearray()
    stride = width * 4
    for y in range(height):
        raw.append(0)
        raw += rgba[y * stride:(y + 1) * stride]

    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)

    ihdr = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', zlib.compress(bytes(raw), 9)) + chunk(b'IEND', b'')


def default_palette_png():
    return png_rgba(4, 1, bytes(16))


def default_art_png():
    return png_rgba(ART, ART, bytes(ART * ART * 4))


def palette_png(pal):
    return png_rgba(4, 1, bytes(v for c in pal for v in (c[0], c[1], c[2], 255)))


# ------------------------------------------------------------------------------------------------ PIL side
def cover_pngs(image_bytes, Image, ImageOps=None, with_art=True):
    """Decode a cover with PIL and return (palette, palette_png_bytes, art_png_bytes). art_png_bytes is None when
    with_art is False (no Shadertoy pack installed: only the palette is needed).

    Like the bench: EXIF orientation applied (browsers do), transparency flattened on black (getImageData of a
    transparent pixel reads 0,0,0), whole image stretched to 48x48 / 128x128 (no crop), alpha forced to 255.
    """
    import io
    im = Image.open(io.BytesIO(image_bytes))
    if max(im.size) > HUGE:  # memory guard only: a DCT-scaled decode no longer matches the bench bit for bit
        im.draft('RGB', (HUGE // 2, HUGE // 2))
    if ImageOps is not None:
        try:
            im = ImageOps.exif_transpose(im)
        except Exception:  # noqa: BLE001 - bad EXIF must not cost the palette
            pass
    if im.mode in ('RGBA', 'LA', 'P', 'PA') or 'transparency' in im.info:
        rgba = im.convert('RGBA')
        bg = Image.new('RGBA', rgba.size, (0, 0, 0, 255))
        bg.alpha_composite(rgba)
        im = bg.convert('RGB')
    else:
        im = im.convert('RGB')
    small = im.resize((SAMPLE, SAMPLE), RESAMPLE(Image))
    data = small.tobytes()
    px = [(data[i], data[i + 1], data[i + 2]) for i in range(0, len(data), 3)]
    pal = extract_palette(px)
    if not with_art:
        return pal, palette_png(pal), None
    art = im.resize((ART, ART), RESAMPLE(Image)).convert('RGBA')
    return pal, palette_png(pal), png_rgba(ART, ART, art.tobytes())


def RESAMPLE(Image):  # noqa: N802 - BOX: the bench's boxResize() is a bit-exact JS port of Pillow's BOX resize
    res = getattr(Image, 'Resampling', Image)
    return res.BOX
