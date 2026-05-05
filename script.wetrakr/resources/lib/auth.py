"""
auth.py — Device Code OAuth flow for WeTrakr with QR code dialog.

Flow:
  1. Request a device code from the API
  2. Download QR code for the activation URL
  3. Show custom dialog with QR + user code + URL
  4. Poll the API every 5s until the user authorizes
  5. Save the access_token in addon settings
"""

import json
import os
import struct
import time
import xbmc
import xbmcgui
import xbmcaddon

from resources.lib.notification import notify as _notify

try:
    from urllib.request import Request, urlopen
    from urllib.error import URLError, HTTPError
    from urllib.parse import quote
except ImportError:
    from urllib2 import Request, urlopen, URLError, HTTPError
    from urllib import quote

try:
    import xbmcvfs
    _TEMP_DIR = xbmcvfs.translatePath('special://temp/')
except Exception:
    _TEMP_DIR = '/tmp/'

ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log("[WeTrakr] {}".format(msg), level)


def _get_api_url():
    addon = xbmcaddon.Addon("script.wetrakr")
    return addon.getSetting("api_url") or "https://api.wetrakr.com"


def is_authenticated():
    """Check if we have a saved access token."""
    addon = xbmcaddon.Addon("script.wetrakr")
    token = addon.getSetting("api_token")
    return bool(token and token.strip())


def get_token():
    """Get the saved access token."""
    addon = xbmcaddon.Addon("script.wetrakr")
    return addon.getSetting("api_token") or ""


def logout():
    """Clear saved token."""
    addon = xbmcaddon.Addon("script.wetrakr")
    addon.setSetting("api_token", "")
    addon.setSetting("username", "")
    _log("Logged out")


# ─── Image helpers ────────────────────────────────────────────────

def _create_bg_image():
    """Create a 1x1 white BMP in temp for use as tintable backgrounds."""
    path = os.path.join(_TEMP_DIR, 'wetrakr_bg.bmp')
    if os.path.exists(path):
        return path
    bmp = bytearray(58)
    struct.pack_into('<2s', bmp, 0, b'BM')
    struct.pack_into('<I', bmp, 2, 58)      # file size
    struct.pack_into('<I', bmp, 10, 54)     # pixel data offset
    struct.pack_into('<I', bmp, 14, 40)     # DIB header size
    struct.pack_into('<i', bmp, 18, 1)      # width
    struct.pack_into('<i', bmp, 22, 1)      # height
    struct.pack_into('<H', bmp, 26, 1)      # planes
    struct.pack_into('<H', bmp, 28, 24)     # bits per pixel
    bmp[54:57] = b'\xff\xff\xff'            # white pixel (BGR)
    bmp[57] = 0                             # padding
    with open(path, 'wb') as f:
        f.write(bytes(bmp))
    return path


def _download_qr(url):
    """Download QR code PNG for the given URL. Returns file path or None."""
    qr_path = os.path.join(_TEMP_DIR, 'wetrakr_qr.png')
    encoded = quote(url, safe='')
    qr_url = (
        "https://api.qrserver.com/v1/create-qr-code/"
        "?size=200x200&format=png&margin=8&data={}".format(encoded)
    )

    try:
        req = Request(qr_url)
        req.add_header('User-Agent', 'WeTrakr-Kodi/1.0.0')

        try:
            import ssl
            ctx = ssl.create_default_context()
            resp = urlopen(req, timeout=10, context=ctx)
        except ImportError:
            resp = urlopen(req, timeout=10)

        data = resp.read()
        if len(data) > 100:  # valid PNG is at least a few hundred bytes
            with open(qr_path, 'wb') as f:
                f.write(data)
            _log("QR code downloaded ({} bytes)".format(len(data)))
            return qr_path
    except Exception as e:
        _log("QR download failed (will show text-only): {}".format(str(e)), xbmc.LOGWARNING)

    return None


# ─── Auth Dialog ──────────────────────────────────────────────────

class AuthDialog(xbmcgui.WindowDialog):
    """Custom full-screen dialog showing QR code + device code for authorization."""

    def __init__(self, bg_path, qr_path, user_code, verification_url, expires_in):
        super().__init__()
        self.cancelled = False
        self._timer_label = None
        self._build_ui(bg_path, qr_path, user_code, verification_url, expires_in)

    def _build_ui(self, bg_path, qr_path, user_code, verification_url, expires_in):
        w = self.getWidth()
        h = self.getHeight()

        # Dialog box dimensions (centered panel)
        dw = int(w * 0.36)
        dh = int(h * 0.80) if qr_path else int(h * 0.55)
        dx = (w - dw) // 2
        dy = (h - dh) // 2
        pad = int(dw * 0.08)
        cw = dw - 2 * pad
        cx = dx + pad

        # Full-screen dark overlay
        self.addControl(
            xbmcgui.ControlImage(0, 0, w, h, bg_path, colorDiffuse='DD000000')
        )

        # Dialog panel background
        self.addControl(
            xbmcgui.ControlImage(dx, dy, dw, dh, bg_path, colorDiffuse='FF1a1a2e')
        )

        # Purple accent line at top
        self.addControl(
            xbmcgui.ControlImage(dx, dy, dw, int(h * 0.005), bg_path, colorDiffuse='FF6c63ff')
        )

        y = dy + int(h * 0.035)

        # Logo image (centered)
        logo_path = os.path.join(
            xbmcaddon.Addon("script.wetrakr").getAddonInfo("path"),
            "resources", "media", "logo.png"
        )
        logo_w = int(dw * 0.50)
        logo_h = int(logo_w / 3.54)  # actual aspect ratio 5337:1506
        logo_x = (w - logo_w) // 2
        self.addControl(xbmcgui.ControlImage(logo_x, y, logo_w, logo_h, logo_path))
        y += logo_h + int(h * 0.015)

        # Subtitle
        self.addControl(xbmcgui.ControlLabel(
            dx, y, dw, int(h * 0.035),
            'Connect Your Account',
            alignment=0x00000002,
            textColor='FFbbbbbb',
            font='font13'
        ))
        y += int(h * 0.05)

        # QR Code (centered, with white background)
        if qr_path:
            qr_size = int(min(dw * 0.48, h * 0.28))
            qr_pad = int(qr_size * 0.06)
            qr_total = qr_size + qr_pad * 2
            qr_x = (w - qr_total) // 2

            # White background behind QR
            self.addControl(
                xbmcgui.ControlImage(qr_x, y, qr_total, qr_total, bg_path, colorDiffuse='FFffffff')
            )
            # QR image
            self.addControl(
                xbmcgui.ControlImage(qr_x + qr_pad, y + qr_pad, qr_size, qr_size, qr_path)
            )
            y += qr_total + int(h * 0.025)
        else:
            y += int(h * 0.015)

        # "Scan QR code or visit:"
        scan_text = 'Scan the QR code or visit:' if qr_path else 'Visit this URL on your phone or computer:'
        self.addControl(xbmcgui.ControlLabel(
            dx, y, dw, int(h * 0.03),
            scan_text,
            alignment=0x00000002,
            textColor='FF888888',
            font='font12'
        ))
        y += int(h * 0.038)

        # URL (purple, bold)
        self.addControl(xbmcgui.ControlLabel(
            dx, y, dw, int(h * 0.04),
            '[B]{}[/B]'.format(verification_url),
            alignment=0x00000002,
            textColor='FF6c63ff',
            font='font13'
        ))
        y += int(h * 0.06)

        # "Enter next code" + countdown (updated during polling)
        mins = expires_in // 60
        secs = expires_in % 60
        self._timer_label = xbmcgui.ControlLabel(
            dx, y, dw, int(h * 0.03),
            'Enter next code ({}m {:02d}s)'.format(mins, secs),
            alignment=0x00000002,
            textColor='FF888888',
            font='font12'
        )
        self.addControl(self._timer_label)
        y += int(h * 0.038)

        # User code (large, white, bold, spaced out)
        spaced_code = '   '.join(user_code)
        self.addControl(xbmcgui.ControlLabel(
            dx, y, dw, int(h * 0.07),
            '[B]{}[/B]'.format(spaced_code),
            alignment=0x00000002,
            textColor='FFffffff',
            font='font_MainMenu'
        ))

    def update_timer(self, remaining):
        """Update the countdown timer text."""
        if not self._timer_label:
            return
        mins = remaining // 60
        secs = remaining % 60
        if mins > 0:
            text = 'Enter next code ({}m {:02d}s)'.format(mins, secs)
        else:
            text = 'Enter next code ({}s)'.format(secs)
        self._timer_label.setLabel(text)

    def show_connected(self, username):
        """Update dialog to show connected state."""
        if self._timer_label:
            self._timer_label.setLabel(
                '[COLOR FF00cc44]Connected as [B]{}[/B]![/COLOR]'.format(username)
            )

    def onAction(self, action):
        if action.getId() in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self.cancelled = True
            self.close()


# ─── API calls ────────────────────────────────────────────────────

def request_device_code():
    """POST /oauth/device/code — returns device code data or None."""
    api_url = _get_api_url()
    url = "{}/oauth/device/code".format(api_url)

    try:
        import ssl
        ctx = ssl.create_default_context()
    except Exception:
        ctx = None

    req = Request(url, data=b'{}')
    req.add_header('Content-Type', 'application/json')
    req.add_header('User-Agent', 'WeTrakr-Kodi/1.0.0')

    try:
        if ctx:
            resp = urlopen(req, timeout=15, context=ctx)
        else:
            resp = urlopen(req, timeout=15)
        data = json.loads(resp.read().decode('utf-8'))
        _log("Device code requested: {}".format(data.get('user_code', '?')))
        return data
    except HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        _log("Device code request failed: HTTP {} — {}".format(e.code, body[:200]), xbmc.LOGERROR)
    except Exception as e:
        _log("Device code request failed: {}".format(str(e)), xbmc.LOGERROR)
    return None


def _poll_once(device_code):
    """Single poll attempt for device token. Returns parsed response or None."""
    api_url = _get_api_url()
    url = "{}/oauth/device/token".format(api_url)
    body = json.dumps({"device_code": device_code}).encode('utf-8')

    try:
        req = Request(url, data=body)
        req.add_header('Content-Type', 'application/json')
        req.add_header('User-Agent', 'WeTrakr-Kodi/1.0.0')

        try:
            import ssl
            ctx = ssl.create_default_context()
            resp = urlopen(req, timeout=10, context=ctx)
        except ImportError:
            resp = urlopen(req, timeout=10)

        return json.loads(resp.read().decode('utf-8'))

    except HTTPError as e:
        resp_body = e.read().decode('utf-8', errors='replace')
        try:
            return json.loads(resp_body)
        except Exception:
            return {"error": "http_{}".format(e.code)}
    except Exception as e:
        _log("Poll connection error: {}".format(str(e)), xbmc.LOGWARNING)
        return None


# ─── Main flow ────────────────────────────────────────────────────

def run_device_auth_flow():
    """
    Full device code authorization flow with custom QR code dialog.
    Returns True if authorized, False otherwise.
    """
    # 1. Request device code from API
    code_data = request_device_code()
    if not code_data:
        xbmcgui.Dialog().ok(
            "WeTrakr",
            "Could not connect to server.\nPlease try again later."
        )
        return False

    user_code = code_data.get('user_code', '')
    device_code = code_data.get('device_code', '')
    verification_url = code_data.get('verification_url', 'https://wetrakr.com/activate')
    expires_in = code_data.get('expires_in', 600)
    interval = code_data.get('interval', 5)

    # 2. Prepare QR code
    bg_path = _create_bg_image()
    qr_path = _download_qr(verification_url)

    # 3. Show custom dialog
    dialog = AuthDialog(bg_path, qr_path, user_code, verification_url, expires_in)
    dialog.show()

    # 4. Poll for authorization
    deadline = time.time() + expires_in
    monitor = xbmc.Monitor()
    result = None

    while time.time() < deadline and not monitor.abortRequested() and not dialog.cancelled:
        remaining = max(0, int(deadline - time.time()))
        dialog.update_timer(remaining)

        data = _poll_once(device_code)
        if data:
            if data.get('access_token'):
                result = data
                break
            error = data.get('error', '')
            if error == 'expired_token':
                _log("Device code expired")
                break
            elif error != 'authorization_pending':
                _log("Unexpected poll response: {}".format(error), xbmc.LOGWARNING)

        if monitor.waitForAbort(interval):
            break

    # 5. Handle result
    if result and result.get('access_token'):
        username = result.get('username', 'User')

        # Show "Connected!" briefly in the dialog
        dialog.show_connected(username)
        xbmc.sleep(2500)
        dialog.close()

        # Save credentials
        addon = xbmcaddon.Addon("script.wetrakr")
        addon.setSetting("api_token", result['access_token'])
        addon.setSetting("username", username)

        _notify("WeTrakr", "Connected as {}".format(username), 5000)
        _log("Device auth completed for user: {}".format(username))
        success = True
    else:
        dialog.close()
        if not dialog.cancelled:
            _notify("WeTrakr", "Authorization timed out. Try again.", 5000)
        success = False

    # Clean up temp QR file
    if qr_path:
        try:
            os.remove(qr_path)
        except Exception:
            pass

    return success
