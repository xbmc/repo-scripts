"""
notification.py — Branded WeTrakr notification popup.

Shows a small notification in the top-right corner with the WeTrakr
"We" logo, purple accent bar, and dark panel background.

Two render paths:

* During video playback we use Kodi's native ``Dialog().notification``.
  The native toast is drawn inside the current skin overlay, so it
  does not push a new entry onto the window stack. On bitstream
  passthrough setups (e.g. Vero 4K+ with E-AC3 passthrough) opening
  a ``WindowDialog`` mid-playback forces an audio sink renegotiation,
  which stalls the video stream for several seconds and ultimately
  ends playback.

* Outside of playback we still use the branded ``WeTrakrNotification``
  ``WindowDialog`` — built, shown, slept on and closed entirely on a
  background daemon thread so the caller never blocks.
"""

import os
import struct
import threading

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


def _native_notify(title, message, duration):
    """Use Kodi's built-in ``Dialog().notification`` toast.

    Renders inside the active skin overlay (no new window stack entry),
    so it's safe to call during bitstream-passthrough playback without
    forcing an audio sink renegotiation.
    """
    try:
        icon = os.path.join(
            xbmcaddon.Addon('script.wetrakr').getAddonInfo('path'),
            'resources', 'media', 'we.png',
        )
        xbmcgui.Dialog().notification(title, message, icon, duration, False)
    except Exception as e:
        xbmc.log(
            "[WeTrakr] native notify error: {}".format(str(e)),
            xbmc.LOGERROR,
        )


def _branded_notify(title, message, duration):
    """Show the branded ``WindowDialog`` popup on a background thread."""
    try:
        dialog = WeTrakrNotification(title, message)
        dialog.show()
        xbmc.sleep(duration)
        dialog.close()
    except Exception as e:
        xbmc.log(
            "[WeTrakr] notify error: {}".format(str(e)),
            xbmc.LOGERROR,
        )


def _is_video_playing():
    try:
        return xbmc.Player().isPlayingVideo()
    except Exception:
        return False


def notify(title, message, duration=3000, force=False):
    """Show a WeTrakr notification (fire-and-forget).

    Rendering ANY toast while a video is actively playing forces Kodi's skin
    overlay/compositor to repaint over the video, which stutters playback for
    1-2s on a wide range of devices — Android boxes, Nvidia Shield, Xiaomi,
    Linux Flatpak — regardless of audio passthrough. This was confirmed
    universal in the 2026-07 user survey (the native toast added in 1.1.8 did
    NOT eliminate it), and users reported the lag disappears entirely once
    notifications are disabled.

    So during playback we skip the toast altogether. Callers that must show a
    confirmation (the deferred "Scrobbled" toast) call again from
    onPlayBackEnded/onPlayBackStopped with force=True, when the video is already
    ending and a repaint is imperceptible.
    """
    playing = _is_video_playing()
    if playing and not force:
        return

    # Forced during the stop/end transition → use the lightweight native toast
    # (no window-stack push) to stay safe on passthrough setups. Outside of
    # playback we render the branded dialog.
    target = _native_notify if playing else _branded_notify

    t = threading.Thread(
        target=target,
        args=(title, message, duration),
        name='WeTrakrNotify',
    )
    t.daemon = True
    t.start()
