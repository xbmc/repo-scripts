"""
rating.py — Custom rating dialog for WeTrakr Kodi addon.

Stars rendered via ControlImage tinted with colorDiffuse, so the
dialog is independent of which skin/font the user has installed.
(Previous Unicode-glyph approach failed on skins whose font_MainMenu
lacks U+2605 — the fallback box made the stars look like dots.)

Mouse hover via ACTION_MOUSE_MOVE with auto-scaled hit-testing.
Mouse coordinates are auto-calibrated to the layout coordinate space.
"""

import os
import struct
import zlib

import xbmc
import xbmcgui
import xbmcaddon

try:
    import xbmcvfs
    _TEMP_DIR = xbmcvfs.translatePath('special://temp/')
except Exception:
    _TEMP_DIR = '/tmp/'

ACTION_MOVE_LEFT = 1
ACTION_MOVE_RIGHT = 2
ACTION_SELECT_ITEM = 7
ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92
ACTION_MOUSE_LEFT_CLICK = 100
ACTION_MOUSE_MOVE = 107

RATING_COLORS = [
    'FFe74c3c', 'FFe74c3c', 'FFe67e22', 'FFf39c12', 'FFf1c40f',
    'FFf1c40f', 'FF2ecc71', 'FF27ae60', 'FF16a085', 'FF8e44ad',
]

RATING_NAMES = [
    'Terrible', 'Awful', 'Bad', 'Poor', 'Meh',
    'Fair', 'Good', 'Great', 'Superb', 'Masterpiece',
]

EMPTY_STAR_COLOR = 'FF555555'


def _ensure_bg():
    """Create/verify 1x1 white BMP for tintable backgrounds."""
    path = os.path.join(_TEMP_DIR, 'wetrakr_bg.bmp')
    if os.path.exists(path) and os.path.getsize(path) == 58:
        return path
    bmp = bytearray(58)
    struct.pack_into('<2s', bmp, 0, b'BM')
    struct.pack_into('<I', bmp, 2, 58)
    struct.pack_into('<I', bmp, 10, 54)
    struct.pack_into('<I', bmp, 14, 40)
    struct.pack_into('<i', bmp, 18, 1)
    struct.pack_into('<i', bmp, 22, 1)
    struct.pack_into('<H', bmp, 26, 1)
    struct.pack_into('<H', bmp, 28, 24)
    bmp[54:57] = b'\xff\xff\xff'
    bmp[57] = 0
    with open(path, 'wb') as f:
        f.write(bytes(bmp))
    return path


def _ensure_clear():
    """Create 1x1 transparent PNG for invisible button textures."""
    path = os.path.join(_TEMP_DIR, 'wetrakr_clear.png')
    if os.path.exists(path) and os.path.getsize(path) > 50:
        return path

    def _chunk(tag, data):
        c = tag + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xFFFFFFFF)

    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n')
        f.write(_chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 6, 0, 0, 0)))
        f.write(_chunk(b'IDAT', zlib.compress(b'\x00\x00\x00\x00\x00')))
        f.write(_chunk(b'IEND', b''))
    return path


class RatingDialog(xbmcgui.WindowDialog):

    def __init__(self, title, year=None, poster_path=None):
        super().__init__()
        self.rating = 5
        self.confirmed = False
        self._name_label = None
        self._star_labels = []
        self._star_rects = []
        self._last_mx = 0.0
        self._last_my = 0.0
        self._close_rect = (0, 0, 0, 0)
        self._dialog_rect = (0, 0, 0, 0)
        self._scale_x = 1.0
        self._scale_y = 1.0
        self._scale_detected = False

        display = title
        if year:
            display = u'{} ({})'.format(title, year)

        self._build_ui(display, poster_path)
        self._detect_scale()
        self._update_stars()

    def _detect_scale(self):
        """Detect coordinate scale between mouse events and layout coords.
        On macOS Retina, mouse coords may differ from getWidth/getHeight."""
        W = self.getWidth()
        H = self.getHeight()
        try:
            sw = xbmc.getInfoLabel('System.ScreenWidth')
            sh = xbmc.getInfoLabel('System.ScreenHeight')
            if sw and sh:
                screen_w = int(sw.replace(',', '').strip())
                screen_h = int(sh.replace(',', '').strip())
                if screen_w > 0 and screen_h > 0 and screen_w != W:
                    self._scale_x = float(W) / screen_w
                    self._scale_y = float(H) / screen_h
                    self._scale_detected = True
        except Exception:
            pass
        xbmc.log("[WeTrakr-Rating] W={} H={} scale={:.3f},{:.3f} star0={}".format(
            W, H, self._scale_x, self._scale_y,
            self._star_rects[0] if self._star_rects else 'none'
        ), xbmc.LOGINFO)

    def _mouse_to_layout(self, mx, my):
        """Convert mouse coordinates to layout coordinate space."""
        return int(mx * self._scale_x), int(my * self._scale_y)

    def _build_ui(self, display_title, poster_path):
        W = self.getWidth()
        H = self.getHeight()
        bg = _ensure_bg()

        dw = int(W * 0.48)
        dh = int(H * 0.75) if poster_path else int(H * 0.50)
        dx = (W - dw) // 2
        dy = (H - dh) // 2
        pad = int(dw * 0.05)
        self._dialog_rect = (dx, dy, dw, dh)

        # ── Overlay + panel ──────────────────────────────────────────
        self.addControl(xbmcgui.ControlImage(0, 0, W, H, bg, colorDiffuse='CC000000'))
        self.addControl(xbmcgui.ControlImage(dx, dy, dw, dh, bg, colorDiffuse='FF1a1a2e'))

        accent_h = max(int(H * 0.005), 3)
        self.addControl(xbmcgui.ControlImage(dx, dy, dw, accent_h, bg, colorDiffuse='FF6c63ff'))

        # ── Header ───────────────────────────────────────────────────
        hdr_h = int(H * 0.08)
        hdr_y = dy + accent_h
        self.addControl(xbmcgui.ControlImage(dx, hdr_y, dw, hdr_h, bg, colorDiffuse='FF22223a'))

        sep_h = max(int(H * 0.002), 1)
        self.addControl(xbmcgui.ControlImage(
            dx, hdr_y + hdr_h, dw, sep_h, bg, colorDiffuse='FF3a3a5e'
        ))

        # "We" logo — left, square (PNG is 5689x5689)
        we_path = os.path.join(
            xbmcaddon.Addon('script.wetrakr').getAddonInfo('path'),
            'resources', 'media', 'we.png',
        )
        we_sz = int(hdr_h * 0.70)
        we_x = dx + pad
        we_y = hdr_y + (hdr_h - we_sz) // 2
        self.addControl(xbmcgui.ControlImage(we_x, we_y, we_sz, we_sz, we_path))

        # Title centered in header
        self.addControl(xbmcgui.ControlLabel(
            dx, hdr_y, dw, hdr_h,
            u'[B]What Did You Think?[/B]',
            alignment=6, textColor='FFffffff', font='font14',
        ))

        # X close label
        csz = int(hdr_h * 0.55)
        cx = dx + dw - pad - csz
        cy = hdr_y + (hdr_h - csz) // 2
        self.addControl(xbmcgui.ControlLabel(
            cx, cy, csz, csz, 'X',
            alignment=6, textColor='FF888888', font='font13',
        ))
        self._close_rect = (cx, cy, csz, csz)

        y = hdr_y + hdr_h + sep_h + int(H * 0.035)

        # ── Content ──────────────────────────────────────────────────

        # Poster centered, big
        if poster_path:
            ph = int(H * 0.33)
            pw = int(ph * 0.667)
            self.addControl(xbmcgui.ControlImage(
                dx + (dw - pw) // 2, y, pw, ph, poster_path
            ))
            y += ph + int(H * 0.02)

        # Title
        self.addControl(xbmcgui.ControlLabel(
            dx, y, dw, int(H * 0.04),
            u'[B]{}[/B]'.format(display_title),
            alignment=0x00000002, textColor='FFcccccc', font='font13',
        ))
        y += int(H * 0.06)

        # ── Stars — ControlImage tinted with colorDiffuse ────────────
        # PNGs shipped with the addon, so the look is identical on every
        # skin (no Unicode font dependency).
        addon_path = xbmcaddon.Addon('script.wetrakr').getAddonInfo('path')
        self._star_filled_path = os.path.join(addon_path, 'resources', 'media', 'star_filled.png')
        self._star_empty_path = os.path.join(addon_path, 'resources', 'media', 'star_empty.png')

        ssz = int(dw * 0.07)
        gap = int(dw * 0.012)
        tw = ssz * 10 + gap * 9
        sx = dx + (dw - tw) // 2

        for i in range(10):
            bx = sx + i * (ssz + gap)
            img = xbmcgui.ControlImage(
                bx, y, ssz, ssz, self._star_empty_path,
                aspectRatio=2, colorDiffuse=EMPTY_STAR_COLOR,
            )
            self.addControl(img)
            self._star_labels.append(img)
            self._star_rects.append((bx, y, ssz, ssz))

        y += ssz + int(H * 0.015)

        # Rating name
        self._name_label = xbmcgui.ControlLabel(
            dx, y, dw, int(H * 0.05),
            '', alignment=0x00000002, textColor='FFffffff', font='font14',
        )
        self.addControl(self._name_label)

        # Hint \u2014 plain ASCII so it renders on every skin/font.
        self.addControl(xbmcgui.ControlLabel(
            dx, dy + dh - int(H * 0.04), dw, int(H * 0.03),
            u'Use Left / Right to select   -   OK to confirm',
            alignment=0x00000002, textColor='FF555555', font='font10',
        ))

        # Ghost ControlButton spanning the dialog — Kodi only sends
        # ACTION_MOUSE_MOVE when a focusable control exists. Added LAST
        # so it's on top (captures focus/clicks); fully transparent.
        clear = _ensure_clear()
        self.addControl(xbmcgui.ControlButton(
            dx, dy, dw, dh, '',
            focusTexture=clear, noFocusTexture=clear,
            textColor='00000000', focusedColor='00000000', font='font10',
        ))

    # ── rendering ────────────────────────────────────────────────────

    def _update_stars(self):
        color = RATING_COLORS[self.rating - 1]
        for i, img in enumerate(self._star_labels):
            is_filled = (i + 1) <= self.rating
            img.setImage(self._star_filled_path if is_filled else self._star_empty_path)
            img.setColorDiffuse(color if is_filled else EMPTY_STAR_COLOR)

        nc = RATING_COLORS[self.rating - 1]
        self._name_label.setLabel(
            u'[COLOR {}][B]{}[/B][/COLOR]'.format(nc, RATING_NAMES[self.rating - 1])
        )

    # ── hit testing ──────────────────────────────────────────────────

    def _star_at(self, raw_x, raw_y):
        x, y = self._mouse_to_layout(raw_x, raw_y)
        for i, (sx, sy, sw, sh) in enumerate(self._star_rects):
            if sx <= x <= sx + sw and sy <= y <= sy + sh:
                return i + 1
        return None

    def _close_hit(self, raw_x, raw_y):
        x, y = self._mouse_to_layout(raw_x, raw_y)
        rx, ry, rw, rh = self._close_rect
        return rx <= x <= rx + rw and ry <= y <= ry + rh

    def _outside_dialog(self, raw_x, raw_y):
        x, y = self._mouse_to_layout(raw_x, raw_y)
        rx, ry, rw, rh = self._dialog_rect
        return not (rx <= x <= rx + rw and ry <= y <= ry + rh)

    # ── input ────────────────────────────────────────────────────────

    def onControl(self, control):
        """Ghost button click — use last tracked mouse position."""
        mx, my = self._last_mx, self._last_my
        star = self._star_at(mx, my)
        if star is not None:
            self.rating = star
            self.confirmed = True
            self.close()
        elif self._close_hit(mx, my):
            self.confirmed = False
            self.close()

    def onAction(self, action):
        aid = action.getId()

        if aid in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self.confirmed = False
            self.close()
            return

        if aid == ACTION_SELECT_ITEM:
            self.confirmed = True
            self.close()
            return

        if aid == ACTION_MOVE_LEFT and self.rating > 1:
            self.rating -= 1
            self._update_stars()
            return

        if aid == ACTION_MOVE_RIGHT and self.rating < 10:
            self.rating += 1
            self._update_stars()
            return

        # Mouse hover → preview rating
        if aid == ACTION_MOUSE_MOVE:
            try:
                mx, my = action.getAmount1(), action.getAmount2()
                self._last_mx = mx
                self._last_my = my
                star = self._star_at(mx, my)
                if star is not None and star != self.rating:
                    self.rating = star
                    self._update_stars()
            except Exception:
                pass
            return

        # Click outside dialog → cancel (clicks ON dialog go to onControl)
        if aid == ACTION_MOUSE_LEFT_CLICK:
            try:
                mx, my = action.getAmount1(), action.getAmount2()
                if self._outside_dialog(mx, my):
                    self.confirmed = False
                    self.close()
            except Exception:
                pass

    def get_rating(self):
        return self.rating if self.confirmed else None


def should_show_rating(media_type, progress):
    """Check if rating dialog should be shown based on settings."""
    addon = xbmcaddon.Addon("script.wetrakr")
    if media_type == "movie":
        if addon.getSetting("rate_after_movie") != "true":
            return False
    elif media_type == "episode":
        if addon.getSetting("rate_after_episode") != "true":
            return False
    else:
        return False
    return True


def show_rating_dialog(title, year=None, poster_path=None):
    """
    Show a star-based rating dialog (1-10).
    Returns the rating (1-10) or None if cancelled.
    """
    dialog = RatingDialog(title, year=year, poster_path=poster_path)
    dialog.doModal()
    rating = dialog.get_rating()
    del dialog

    if rating is not None:
        xbmc.log("[WeTrakr] Rated '{}': {}/10".format(title, rating), xbmc.LOGINFO)

    return rating
