"""Refract's public API (https://getrefract.app/developers): device sign-in, tokens, lookups, writes.

Standard library only, so the add-on needs no dependency from the Kodi repository.
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from resources.lib import kodi

ORIGIN = "https://getrefract.app"
RESOURCE = ORIGIN + "/v1"
# A Client ID Metadata Document: the add-on is a public client, its code is open, so it holds no secret.
CLIENT_ID = ORIGIN + "/developers/clients/kodi.json"
SCOPES = "profile:read library:read history:write offline_access"
USER_AGENT = "service.refract/{0} (Kodi)".format(kodi.ADDON.getAddonInfo("version"))
TOKEN_FILE = os.path.join(kodi.PROFILE_DIR, "tokens.json")


class NotConnected(Exception):
    """No tokens, or the member revoked the add-on: they must connect again."""


class ApiError(Exception):
    def __init__(self, status, body):
        super().__init__("{0} {1}".format(status, (body or {}).get("code") or (body or {}).get("error") or ""))
        self.status = status
        self.body = body or {}


def _request(method, url, form=None, body=None, headers=None):
    data = None
    request_headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    if form is not None:
        data = urllib.parse.urlencode(form).encode("utf-8")
        request_headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif body is not None:
        data = json.dumps(body).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    request_headers.update(headers or {})
    request = urllib.request.Request(url, data=data, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read()
            return response.status, (json.loads(raw) if raw else None), response.headers
    except urllib.error.HTTPError as error:
        raw = error.read()
        try:
            parsed = json.loads(raw) if raw else None
        except ValueError:
            parsed = None
        return error.code, parsed, error.headers


# ── Tokens ─────────────────────────────────────────────────────────────────

def _load_tokens():
    try:
        with open(TOKEN_FILE, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def _save_tokens(tokens):
    os.makedirs(kodi.PROFILE_DIR, exist_ok=True)
    tokens = dict(tokens)
    tokens["expires_at"] = time.time() + int(tokens.get("expires_in") or 3600) - 60
    with open(TOKEN_FILE, "w", encoding="utf-8") as handle:
        json.dump(tokens, handle)


def forget_tokens():
    try:
        os.remove(TOKEN_FILE)
    except OSError:
        pass


def is_connected():
    return _load_tokens() is not None


def start_device_login():
    """Asks for a device code: the member approves it on getrefract.app/device."""
    status, body, _ = _request("POST", ORIGIN + "/api/auth/device/code",
                               form={"client_id": CLIENT_ID, "scope": SCOPES, "resource": RESOURCE})
    if status != 200:
        raise ApiError(status, body)
    return body


def poll_device_login(device_code):
    """One poll: the tokens once approved, None while pending; raises when refused or expired."""
    status, body, _ = _request("POST", ORIGIN + "/api/auth/oauth2/token", form={
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        "device_code": device_code,
        "client_id": CLIENT_ID,
    })
    if status == 200:
        _save_tokens(body)
        return body
    if (body or {}).get("error") == "authorization_pending":
        return None
    # `slow_down` too: the caller widens its interval and polls again.
    raise ApiError(status, body)


def _refresh(tokens):
    status, body, _ = _request("POST", ORIGIN + "/api/auth/oauth2/token", form={
        "grant_type": "refresh_token",
        "refresh_token": tokens.get("refresh_token", ""),
        "client_id": CLIENT_ID,
    })
    if status != 200:
        if status in (400, 401):
            forget_tokens()
            raise NotConnected()
        raise ApiError(status, body)
    # Refresh tokens rotate: the answer carries the new one.
    _save_tokens(body)
    return _load_tokens()


def revoke():
    tokens = _load_tokens()
    if tokens and tokens.get("refresh_token"):
        _request("POST", ORIGIN + "/api/auth/oauth2/revoke", form={
            "token": tokens["refresh_token"], "client_id": CLIENT_ID, "token_type_hint": "refresh_token",
        })
    forget_tokens()


# ── API calls ──────────────────────────────────────────────────────────────

def _call(method, path, body=None, headers=None):
    tokens = _load_tokens()
    if not tokens:
        raise NotConnected()
    if time.time() >= tokens.get("expires_at", 0):
        tokens = _refresh(tokens)
    for attempt in range(2):
        auth = {"Authorization": "Bearer " + tokens["access_token"]}
        auth.update(headers or {})
        status, payload, response_headers = _request(method, RESOURCE + path, body=body, headers=auth)
        if status == 401 and attempt == 0:
            tokens = _refresh(tokens)
            continue
        if status == 429 and attempt == 0:
            time.sleep(min(int(response_headers.get("Retry-After") or 1), 30))
            continue
        if status >= 400:
            raise ApiError(status, payload)
        return status, payload
    raise ApiError(status, payload)


def me():
    return _call("GET", "/me")[1]


def search(id_type, external_id, kind, **episode):
    """Titles Refract knows under a TMDB, IMDb or TVDB id; `kind` is movie, show or episode.

    An episode is found by its own id, or by its show's id with `season`, `number` and the
    `numbering` they are in (tmdb, tvdb or absolute); Refract answers in TMDB's numbering.
    """
    query = {"type": kind}
    query.update({key: value for key, value in episode.items() if value is not None})
    path = "/search/{0}/{1}?{2}".format(id_type, urllib.parse.quote(str(external_id), safe=""), urllib.parse.urlencode(query))
    try:
        return (_call("GET", path)[1] or {}).get("data") or []
    except ApiError as error:
        if error.status == 404:
            return []
        raise


def mark_episode(show_id, season, number):
    return _call("PUT", "/history/episodes/{0}/{1}/{2}".format(show_id, season, number), body={})


def log_movie(movie_id, watched_at, idempotency_key):
    """The key is kept per play, so a retry after a network failure never logs the movie twice."""
    return _call("POST", "/history/movies", body={"movie_id": movie_id, "watched_at": watched_at},
                 headers={"Idempotency-Key": '"{0}"'.format(idempotency_key)})


def new_idempotency_key():
    return str(uuid.uuid4())
