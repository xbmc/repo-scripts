"""
api.py — HTTP client for the WeTrakr scrobble API.

Sends JSON payloads to POST /webhooks/kodi/:token.
Uses urllib (available in Kodi Python) to avoid external dependencies.
"""

import json
import xbmc
import xbmcaddon

from resources.lib import utils

try:
    from urllib.request import Request, urlopen
    from urllib.error import URLError, HTTPError
except ImportError:
    # Python 2 fallback (Kodi 18 Leia and earlier)
    from urllib2 import Request, urlopen, URLError, HTTPError


def _flag_auth_invalid():
    """Persist that the saved token was rejected by the server (HTTP 401/403).

    The background service watches this flag and forces a fresh device-code
    login. Without it, a stale/orphaned token keeps "working" locally (the
    add-on still fires events and shows the Scrobbling popup) while every event
    is silently dropped server-side. See Tigerman58, 2026-06-27.
    """
    try:
        xbmcaddon.Addon("script.wetrakr").setSetting("auth_invalid", "true")
    except Exception:
        pass


def local_threshold():
    """The add-on's own scrobble threshold (%) from its settings."""
    try:
        return int(xbmcaddon.Addon("script.wetrakr").getSetting("scrobble_threshold") or "80")
    except Exception:
        return 80


def remember_server_threshold(value):
    """Store the watched threshold WeTrakr says to apply (Settings > Kodi in the
    web). None = the user did not set one there: the local one applies.

    There is a single threshold and it lives in WeTrakr. The add-on sends its
    local one with every event so WeTrakr can show it until the user picks one
    in the web, and from then on applies the web's (see player._get_settings).
    """
    try:
        if value is None:
            stored = ""
        else:
            stored = str(max(50, min(100, int(round(float(value))))))
        addon = xbmcaddon.Addon("script.wetrakr")
        if addon.getSetting("server_threshold") != stored:
            addon.setSetting("server_threshold", stored)
    except Exception:
        pass


def _read_server_threshold(response):
    """Pick watched_percent from a webhook response, if the API sent it
    (WeTrakr API from 2026-11)."""
    try:
        data = json.loads(response.read().decode("utf-8") or "{}")
        if isinstance(data, dict) and "watched_percent" in data:
            remember_server_threshold(data["watched_percent"])
    except Exception:
        pass


class WeTrakrAPI:
    """Simple HTTP client for the WeTrakr Kodi webhook endpoint."""

    def __init__(self, base_url, token):
        self.url = "{}/webhooks/kodi/{}".format(base_url.rstrip("/"), token)
        self.timeout = 10

    def send_event(self, payload, debug=False):
        """
        POST a scrobble event payload to WeTrakr.

        Args:
            payload: dict with event data (event, media_type, ids, etc.)
            debug: if True, log request/response details

        Returns: True on success (2xx), False on failure
        """
        if not self.url or "/webhooks/kodi/" not in self.url:
            xbmc.log("[WeTrakr] API URL not configured", xbmc.LOGWARNING)
            return False

        if "threshold" not in payload:
            payload = dict(payload, threshold=local_threshold())
        body = json.dumps(payload).encode("utf-8")

        req = Request(self.url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("User-Agent", utils.user_agent())

        if debug:
            xbmc.log("[WeTrakr] POST {} | {}".format(self.url, payload), xbmc.LOGINFO)

        try:
            response = urlopen(req, timeout=self.timeout)
            status = response.getcode()
            if debug:
                xbmc.log("[WeTrakr] Response: {}".format(status), xbmc.LOGINFO)
            if 200 <= status < 300:
                _read_server_threshold(response)
            return 200 <= status < 300
        except HTTPError as e:
            if e.code in (401, 403):
                # The server no longer recognises this token (orphaned/expired).
                # Flag it so the service triggers a re-login instead of looping
                # forever sending events that get dropped.
                xbmc.log(
                    "[WeTrakr] Auth rejected (HTTP {}): saved token no longer valid "
                    "— re-login required".format(e.code),
                    xbmc.LOGWARNING
                )
                _flag_auth_invalid()
                return False
            xbmc.log(
                "[WeTrakr] HTTP error {}: {}".format(e.code, e.reason),
                xbmc.LOGWARNING
            )
            return False
        except URLError as e:
            xbmc.log(
                "[WeTrakr] Connection error: {}".format(e.reason),
                xbmc.LOGWARNING
            )
            # Retry once
            try:
                response = urlopen(req, timeout=self.timeout)
                return 200 <= response.getcode() < 300
            except Exception:
                return False
        except Exception as e:
            xbmc.log(
                "[WeTrakr] Unexpected error: {}".format(str(e)),
                xbmc.LOGERROR
            )
            return False

    def send_rating(self, media_type, title, ids, rating, year=None,
                    show_title=None, show_ids=None, season=None, episode=None):
        """Send a rating event to WeTrakr."""
        payload = {
            "event": "rating",
            "media_type": media_type,
            "title": title,
            "ids": ids,
            "rating": rating
        }
        if year:
            payload["year"] = year
        if show_title:
            payload["show_title"] = show_title
        if show_ids:
            payload["show_ids"] = show_ids
        if season is not None:
            payload["season"] = season
        if episode is not None:
            payload["episode"] = episode

        settings = self._debug_check()
        return self.send_event(payload, debug=settings)

    def _debug_check(self):
        try:
            import xbmcaddon
            return xbmcaddon.Addon("script.wetrakr").getSetting("debug") == "true"
        except Exception:
            return False
