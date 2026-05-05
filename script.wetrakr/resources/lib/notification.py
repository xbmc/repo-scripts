"""
notification.py — Branded WeTrakr notification popup.

Shows a small notification in the top-right corner with the WeTrakr
"We" logo, purple accent bar, and dark panel background.
"""

import os
import struct

import xbmc
import xbmcgui
import xbmcaddon

try:
    import xbmcvfs
    _TEMP_DIR = xbmcvfs.translatePath('special://temp/')
except Exception:
    _TEMP_DIR = '/tmp/'


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


class WeTrakrNotification(xbmcgui.WindowDialog):
    """Small branded notification popup — top-right corner."""

    def __init__(self, title, message):
        super().__init__()
        self._build_ui(title, message)

    def _build_ui(self, title, message):
        W = self.getWidth()
        H = self.getHeight()
        bg = _ensure_bg()

        # Size and position — top-right
        nw = int(W * 0.30)
        nh = int(H * 0.10)
        nx = W - nw - int(W * 0.015)
        ny = int(H * 0.015)
        pad = int(nw * 0.05)

        # Panel background
        self.addControl(xbmcgui.ControlImage(nx, ny, nw, nh, bg, colorDiffuse='FF1a1a2e'))

        # Purple accent bar at top
        accent_h = max(int(H * 0.004), 2)
        self.addControl(xbmcgui.ControlImage(nx, ny, nw, accent_h, bg, colorDiffuse='FF6c63ff'))

        # "We" logo (left side, big)
        we_path = os.path.join(
            xbmcaddon.Addon('script.wetrakr').getAddonInfo('path'),
            'resources', 'media', 'we.png',
        )
        we_sz = int(nh * 0.55)
        we_x = nx + pad
        we_y = ny + (nh - we_sz) // 2
        self.addControl(xbmcgui.ControlImage(we_x, we_y, we_sz, we_sz, we_path))

        # Text area
        tx = we_x + we_sz + pad
        tw = nw - pad * 3 - we_sz

        # Title (bold, white)
        self.addControl(xbmcgui.ControlLabel(
            tx, ny + int(nh * 0.15), tw, int(nh * 0.40),
            u'[B]{}[/B]'.format(title),
            alignment=0x00000000, textColor='FFffffff', font='font13',
        ))

        # Message (lighter)
        self.addControl(xbmcgui.ControlLabel(
            tx, ny + int(nh * 0.50), tw, int(nh * 0.40),
            message,
            alignment=0x00000000, textColor='FFbbbbbb', font='font12',
        ))

    def onAction(self, action):
        self.close()


def notify(title, message, duration=3000):
    """Show a branded WeTrakr notification popup."""
    dialog = WeTrakrNotification(title, message)
    dialog.show()
    xbmc.sleep(duration)
    dialog.close()
    del dialog
