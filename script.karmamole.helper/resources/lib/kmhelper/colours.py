# KarmaMole Skin Helper (script.karmamole.helper)
# Copyright (C) 2026 Omar Kamel
# SPDX-License-Identifier: GPL-2.0-or-later
"""Colour and soft-art maths. Pure Python + PIL (no numpy, no Kodi imports), so it is unit-testable on a PC.

The recipes are ports of the approved mockups (docs/skin.groove/mockups/_src/make_boards.py):
  main_colour()  saturation-weighted mean of a 64 px copy, lightness reset to L 0.55
  soft "wash"    art -> 12 px BOX, saturation x1.45, brightness x1.12, V capped at 0.50, upscaled + blurred (w/14)
  soft "halo"    same with x1.60 / x1.25 / V 0.72, then mixed 60/40 with main_colour()
  spine          main_colour() re-lit to L 0.36 (dark room, white ink) or L 0.80 (light room, dark ink)
"""
import colorsys
import io
import struct
import zlib

ALGO = 1          # bump when any output below changes: it is part of the soft-art file names
SAMPLE = 64       # main colour sample size
DRAFT = 128       # JPEG DCT-scaled decode target (fast path for big covers/fanart)
WASH_SIZE = (320, 180)   # full-screen wash: always 16:9, the skin stretches it to 1920x1080
HALO_LONG = 256          # halo keeps the art's aspect, long side 256
SPINE_W, SPINE_H = 40, 4  # spine strip: 40 px wide (the shelf's spine width), stretched vertically by the skin


def open_image(data, Image):
    """Decode cover bytes to an RGB image. JPEGs are decoded at reduced scale (draft). Alpha is flattened on black."""
    im = Image.open(io.BytesIO(data))
    try:
        im.draft('RGB', (DRAFT, DRAFT))
    except Exception:  # noqa: BLE001 - draft is a JPEG-only speed-up
        pass
    if im.mode in ('RGBA', 'LA', 'P', 'PA') or 'transparency' in im.info:
        rgba = im.convert('RGBA')
        bg = Image.new('RGBA', rgba.size, (0, 0, 0, 255))
        bg.alpha_composite(rgba)
        return bg.convert('RGB')
    return im.convert('RGB')


def _box(Image):
    return getattr(Image, 'Resampling', Image).BOX


def _bicubic(Image):
    return getattr(Image, 'Resampling', Image).BICUBIC


def _weighted(pixels):
    """[(r, g, b, weight, hue, sat)] in 0..1 floats with the mockups' weight: sat^2 * (0.25 + max) + 1e-4."""
    out = []
    for r8, g8, b8 in pixels:
        r, g, b = r8 / 255.0, g8 / 255.0, b8 / 255.0
        mx, mn = max(r, g, b), min(r, g, b)
        sat = (mx - mn) / mx if mx > 0 else 0.0
        w = sat * sat * (0.25 + mx) + 1e-4
        out.append((r, g, b, w, colorsys.rgb_to_hsv(r, g, b)[0], sat))
    return out


def _mean(px):
    tw = sum(p[3] for p in px)
    if tw <= 0:
        return None, 0.0
    return (sum(p[0] * p[3] for p in px) / tw, sum(p[1] * p[3] for p in px) / tw,
            sum(p[2] * p[3] for p in px) / tw), tw


GREY_HUE, GREY_SAT = 35 / 360.0, 0.10  # a colourless cover gets a faint warm tint (DESIGN.md fallback glow is warm white)


def _lift(rgb, lightness, sat_scale=1.25, sat_add=0.08, sat_max=1.0):
    h, _, s = colorsys.rgb_to_hls(*rgb)
    if s < 0.015:  # greys: hue is meaningless (0 = red); don't tint the room pink
        h, s, sat_scale, sat_add = GREY_HUE, GREY_SAT, 1.0, 0.0
    r, g, b = colorsys.hls_to_rgb(h, lightness, min(sat_max, s * sat_scale + sat_add))
    return int(r * 255), int(g * 255), int(b * 255)  # truncation, like make_boards.py


def palette(im, Image):
    """{'main', 'accent', 'shadow', 'average'} as (r, g, b) ints for an RGB image.
    main    = make_boards.main_colour (Groove.Color.Main)
    accent  = the same weighted mean over pixels whose hue is > 0.12 (43 deg) away from main and sat > 0.2,
              lifted to L 0.60; a near-monochrome cover gets main re-lit to L 0.70
    shadow  = main's hue at L 0.22, sat <= 0.55 (tinted shade for the light room)
    average = plain mean colour, unlifted (for skins that want the art's real tone)"""
    small = im.resize((SAMPLE, SAMPLE), _box(Image))
    b = small.tobytes()  # RGB triples (getdata() is deprecated in newer Pillow)
    raw = [(b[i], b[i + 1], b[i + 2]) for i in range(0, len(b), 3)]
    px = _weighted(raw)
    mean, total = _mean(px)
    main = _lift(mean, 0.55)
    h_main = colorsys.rgb_to_hls(main[0] / 255.0, main[1] / 255.0, main[2] / 255.0)[0]

    def hue_dist(h):
        d = abs(h - h_main)
        return min(d, 1.0 - d)

    far = [p for p in px if p[5] > 0.2 and hue_dist(p[4]) > 0.12]
    acc, acc_w = _mean(far) if far else (None, 0.0)
    if acc is not None and acc_w >= 0.03 * total:
        accent = _lift(acc, 0.60)
    else:
        accent = _lift(mean, 0.70, sat_scale=1.0, sat_add=0.0)
    shadow = _lift(mean, 0.22, sat_scale=1.0, sat_add=0.0, sat_max=0.55)
    n = float(len(raw)) or 1.0
    average = tuple(int(sum(p[i] for p in raw) / n + 0.5) for i in range(3))
    return {'main': main, 'accent': accent, 'shadow': shadow, 'average': average}


def argb(rgb, alpha=255):
    """Kodi colordiffuse format: AARRGGBB hex."""
    return '%02X%02X%02X%02X' % (alpha, rgb[0], rgb[1], rgb[2])


def _soft(im, size, sat, gain, vmax, pil):
    Image, ImageEnhance, ImageFilter = pil
    small = im.resize((12, 12), _box(Image))
    small = ImageEnhance.Color(small).enhance(sat)
    small = ImageEnhance.Brightness(small).enhance(gain)
    h, s, v = small.convert('HSV').split()
    cap = int(vmax * 255)
    v = v.point(lambda x: x if x < cap else cap)
    small = Image.merge('HSV', (h, s, v)).convert('RGB')
    w, hh = size
    return small.resize((w, hh), _bicubic(Image)).filter(ImageFilter.GaussianBlur(max(w, hh) / 14.0))


def wash_image(im, pil):
    """Groove.Art.Soft: the room wash (16:9, drawn full screen through the skin's wash mask)."""
    return _soft(im, WASH_SIZE, 1.45, 1.12, 0.50, pil)


def wash_light_image(im, pil):
    """Groove.Art.SoftLight: the light room's wash (DESIGN.md 12.4, make_boards_light.soft_art_light): 12 px art,
    saturation x1.4, then saturation capped at 0.62 and value FLOORED at 0.76, so every sleeve becomes a pastel of
    itself and a dark sleeve can't smudge the paper. 16:9 like the dark wash."""
    Image, ImageEnhance, ImageFilter = pil
    small = im.resize((12, 12), _box(Image))
    small = ImageEnhance.Color(small).enhance(1.4)
    h, s, v = small.convert('HSV').split()
    smax, vmin = int(0.62 * 255), int(0.76 * 255)
    s = s.point(lambda x: x if x < smax else smax)
    v = v.point(lambda x: x if x > vmin else vmin)
    small = Image.merge('HSV', (h, s, v)).convert('RGB')
    w, hh = WASH_SIZE
    return small.resize((w, hh), _bicubic(Image)).filter(ImageFilter.GaussianBlur(max(w, hh) / 14.0))


def halo_image(im, main, pil):
    """Groove.Art.Halo: soft art (x1.6, x1.25, V 0.72) mixed 60/40 with main colour, at the art's aspect."""
    Image = pil[0]
    w, h = im.size
    if w >= h:
        size = (HALO_LONG, max(2, int(round(HALO_LONG * h / float(w)))))
    else:
        size = (max(2, int(round(HALO_LONG * w / float(h)))), HALO_LONG)
    sa = _soft(im, size, 1.6, 1.25, 0.72, pil)
    return Image.blend(sa, Image.new('RGB', sa.size, tuple(main)), 0.4)


def png_bytes(img):
    buf = io.BytesIO()
    img.save(buf, format='PNG', compress_level=6)
    return buf.getvalue()


# ------------------------------------------------------------------------------------------------ spines (no PIL)
def spine_colour(main, room):
    """Spine fill for one album. room 'dark': L 0.36, sat <= 0.75 (white ink reads on it); 'light': L 0.80, sat <= 0.45
    (dark ink reads on it)."""
    h, _, s = colorsys.rgb_to_hls(main[0] / 255.0, main[1] / 255.0, main[2] / 255.0)
    if room == 'light':
        r, g, b = colorsys.hls_to_rgb(h, 0.80, min(0.45, s))
    else:
        r, g, b = colorsys.hls_to_rgb(h, 0.36, min(0.75, s))
    return int(r * 255), int(g * 255), int(b * 255)


def _mix(c, other, t):
    return tuple(int(round(c[i] * (1 - t) + other[i] * t)) for i in range(3))


def spine_png(main, room):
    """A SPINE_W x SPINE_H opaque PNG: the fill, a 1 px light edge at the left (white 10%) and a 2 px shade at the right
    (black 35%), as in the mockups' spine box-shadows. The skin stretches it to the spine height."""
    fill = spine_colour(main, room)
    row = bytearray()
    for x in range(SPINE_W):
        if x == 0:
            c = _mix(fill, (255, 255, 255), 0.10)
        elif x >= SPINE_W - 2:
            c = _mix(fill, (0, 0, 0), 0.35)
        else:
            c = fill
        row += bytes((c[0], c[1], c[2], 255))
    return png_rgba(SPINE_W, SPINE_H, bytes(row) * SPINE_H)


def png_rgba(width, height, rgba):
    """Encode 8-bit RGBA bytes (row 0 = top) as a PNG (same writer as service.vizpalette)."""
    raw = bytearray()
    stride = width * 4
    for y in range(height):
        raw.append(0)
        raw += rgba[y * stride:(y + 1) * stride]

    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)

    ihdr = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', zlib.compress(bytes(raw), 9)) + chunk(b'IEND', b'')
