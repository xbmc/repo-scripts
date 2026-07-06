"""
api.py — HTTP client for the WeTrakr scrobble API.

Sends JSON payloads to POST /webhooks/kodi/:token.
Uses urllib (available in Kodi Python) to avoid external dependencies.
"""

import json
import xbmc
import xbmcaddon

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

        body = json.dumps(payload).encode("utf-8")

        req = Request(self.url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("User-Agent", "WeTrakr-Kodi/1.1.6")

        if debug:
            xbmc.log("[WeTrakr] POST {} | {}".format(self.url, payload), xbmc.LOGINFO)

        try:
            response = urlopen(req, timeout=self.timeout)
            status = response.getcode()
            if debug:
                xbmc.log("[WeTrakr] Response: {}".format(status), xbmc.LOGINFO)
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
