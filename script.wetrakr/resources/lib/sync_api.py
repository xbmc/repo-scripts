"""
sync_api.py — HTTP client for the library sync endpoints
(/integrations/kodi/*). Same token as the scrobble webhook, in Authorization.

  GET  /integrations/kodi/status                 settings, max_batch
  POST /integrations/kodi/import                 a batch Kodi -> WeTrakr
  GET  /integrations/kodi/import/<job_id>        batch progress
  GET  /integrations/kodi/snapshot?section=&cursor=
  GET  /integrations/kodi/changes?since=&full=1  what changed in WeTrakr
  GET  /integrations/kodi/lists                  lists mirrored as tags
  GET  /integrations/kodi/next-episodes?limit=   Next Episodes widget
"""

import json
import ssl
import time

import xbmc
import xbmcaddon

from resources.lib import utils

try:
    from urllib.request import Request, urlopen
    from urllib.error import URLError, HTTPError
    from urllib.parse import urlencode
except ImportError:  # Kodi 18
    from urllib2 import Request, urlopen, URLError, HTTPError
    from urllib import urlencode


class InvalidToken(Exception):
    """401: the token was regenerated or the connection removed in WeTrakr."""


class ApiError(Exception):
    def __init__(self, status, error, message=None):
        Exception.__init__(self, "HTTP {} {}{}".format(status, error, (": " + message) if message else ""))
        self.status = status
        self.error = error


class SyncApi(object):

    def __init__(self, base_url, token, timeout=60):
        self.base = base_url.rstrip("/") + "/integrations/kodi"
        self.token = token
        self.timeout = timeout
        addon = xbmcaddon.Addon("script.wetrakr")
        self._headers = {
            "Authorization": "Bearer " + token,
            "User-Agent": utils.user_agent(),
            "X-WeTrakr-Addon-Version": addon.getAddonInfo("version"),
            "X-Kodi-Version": (xbmc.getInfoLabel("System.BuildVersion") or "")[:40],
            "X-Kodi-Device": (xbmc.getInfoLabel("System.FriendlyName") or "")[:120],
        }

    def _request(self, method, path, body=None, query=None):
        url = self.base + path
        if query:
            url += "?" + urlencode(query)
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = Request(url, data=data)
        req.get_method = lambda: method
        for k, v in self._headers.items():
            req.add_header(k, v)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            ctx = ssl.create_default_context()
        except Exception:
            ctx = None
        try:
            resp = urlopen(req, timeout=self.timeout, context=ctx) if ctx else urlopen(req, timeout=self.timeout)
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
        except HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw)
            except ValueError:
                payload = {}
            if e.code == 401:
                raise InvalidToken(payload.get("error") or "invalid_token")
            if e.code == 429:
                # Daily cap: wait for tomorrow, not for the next tick.
                raise ApiError(429, payload.get("error") or "quota", payload.get("message"))
            raise ApiError(e.code, payload.get("error") or "http_error", payload.get("message"))
        except URLError as e:
            raise ApiError(0, "connection", str(e.reason))

    def status(self):
        return self._request("GET", "/status")

    def import_batch(self, session_id, mode, items, final):
        return self._request("POST", "/import", body={
            "session_id": session_id, "mode": mode, "final": final, "items": items,
            "server": {"kodi": self._headers["X-Kodi-Version"], "device": self._headers["X-Kodi-Device"]},
        })

    def import_job(self, job_id):
        return self._request("GET", "/import/" + job_id)

    def wait_for_batch(self, accepted, timeout=120):
        """The server answers 200 with the batch done, or 202 to poll."""
        if accepted.get("status") in ("done", "running", "failed") and accepted.get("batches_done") is not None:
            if accepted.get("batches_done", 0) >= accepted.get("batch", 1) or accepted.get("status") == "failed":
                return accepted
        job_id = accepted.get("job_id")
        wanted = accepted.get("batch", 1)
        deadline = time.time() + timeout
        monitor = xbmc.Monitor()
        while time.time() < deadline and not monitor.abortRequested():
            if monitor.waitForAbort(2):
                break
            job = self.import_job(job_id)
            if job.get("status") in ("failed", "canceled"):
                raise ApiError(500, "import_failed", job.get("error"))
            if job.get("batches_done", 0) >= wanted:
                return job
        raise ApiError(0, "import_timeout", "batch {} not processed in {} s".format(wanted, timeout))

    def snapshot(self, section, cursor=None):
        q = {"section": section}
        if cursor:
            q["cursor"] = cursor
        return self._request("GET", "/snapshot", query=q)

    def lists(self):
        """WeTrakr lists the user mirrors in Kodi: {rev, lists: [{id, name, items}]}."""
        return self._request("GET", "/lists")

    def next_episodes(self, limit=50):
        """WeTrakr Next Episodes: {items: [{show, episode, status, last_watched_at}]}."""
        return self._request("GET", "/next-episodes", query={"limit": limit})

    def changes(self, since, full=False):
        q = {"since": since}
        if full:
            q["full"] = "1"
        return self._request("GET", "/changes", query=q)
