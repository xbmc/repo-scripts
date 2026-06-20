"""
api.py — HTTP client for the PunchPlay backend.

Responsibilities:
  • Attach Bearer token to every request.
  • Transparently refresh the access token on 401 and retry once.
  • Queue failed POST events in SQLite via Cache so nothing is lost offline.
  • Flush the offline queue on the next successful connection.
  • Device-code login flow with a Kodi progress dialog.
"""

from __future__ import annotations

import base64
import json
import os
import platform
import sys
import threading
import time
import uuid
import urllib.error
import urllib.request
from urllib.parse import urlparse, urlunparse
from typing import Any

import xbmc
import xbmcgui

from constants import (
    ADDON_NAME,
    ADDON_ID,
    AUTH_DEVICE_CODE_ENDPOINT,
    AUTH_DEVICE_TOKEN_ENDPOINT,
    AUTH_ME_ENDPOINT,
    AUTH_REFRESH_ENDPOINT,
    DEFAULT_BACKEND_URL,
    HEARTBEAT_INTERVAL_SECS,
    IDENTIFIER_NO_MATCH_CACHE_TTL_SECS,
    IDENTIFIER_SUCCESS_CACHE_TTL_SECS,
    IDENTIFY_ENDPOINT,
    IDENTIFY_MATCH_THRESHOLD,
    IDENTIFY_REQUEST_TIMEOUT_SECS,
    NOTIFICATION_TITLE,
    PERMANENT_HTTP_STATUS_CODES,
    REQUEST_TIMEOUT_SECS,
    TEST_CONNECTION_TIMEOUT_SECS,
    get_addon,
    get_addon_path,
    get_addon_version,
    get_profile_dir,
    localize,
    mask_value,
)


class BackendConfigurationError(ValueError):
    """Raised when the configured backend URL is unsafe or malformed."""


def _sanitise_url_for_display(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    host = parsed.hostname or parsed.netloc
    if parsed.port:
        host = "{0}:{1}".format(host, parsed.port)
    path = (parsed.path or "").rstrip("/")
    return urlunparse((parsed.scheme, host, path, "", "", ""))


def validate_backend_url(
    raw_url: str,
    *,
    developer_mode: bool = False,
    allow_insecure_http: bool = False,
) -> dict[str, Any]:
    configured = (raw_url or "").strip()
    if not configured:
        return {
            "valid": True,
            "url": DEFAULT_BACKEND_URL,
            "display_url": DEFAULT_BACKEND_URL,
            "error": None,
            "using_default": True,
        }

    parsed = urlparse(configured)
    if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
        return {
            "valid": False,
            "url": None,
            "display_url": _sanitise_url_for_display(configured),
            "error": "invalid_backend_url",
            "using_default": False,
        }
    if parsed.username or parsed.password:
        return {
            "valid": False,
            "url": None,
            "display_url": _sanitise_url_for_display(configured),
            "error": "backend_credentials_not_allowed",
            "using_default": False,
        }
    if parsed.scheme.lower() == "http" and not (developer_mode and allow_insecure_http):
        return {
            "valid": False,
            "url": None,
            "display_url": _sanitise_url_for_display(configured),
            "error": "backend_https_required",
            "using_default": False,
        }

    normalised = urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc,
            (parsed.path or "").rstrip("/"),
            "",
            "",
            "",
        )
    ).rstrip("/")
    return {
        "valid": True,
        "url": normalised,
        "display_url": _sanitise_url_for_display(normalised),
        "error": None,
        "using_default": False,
    }


class APIClient:
    def __init__(self, cache=None) -> None:
        self._cache = cache
        self._client_version = get_addon_version()
        self._data_dir: str = get_profile_dir()
        os.makedirs(self._data_dir, exist_ok=True)

        self._token_file = os.path.join(self._data_dir, "tokens.json")
        self._device_id_file = os.path.join(self._data_dir, "device_id.txt")

        self._tokens: dict[str, str] = self._load_tokens()
        self.device_id: str = self._get_or_create_device_id()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _backend_config(self) -> dict[str, Any]:
        addon = get_addon()
        return validate_backend_url(
            addon.getSetting("backend_url"),
            developer_mode=addon.getSettingBool("developer_mode"),
            allow_insecure_http=addon.getSettingBool("allow_insecure_backend_url"),
        )

    def _base_url(self) -> str:
        config = self._backend_config()
        if not config["valid"]:
            raise BackendConfigurationError(str(config["error"] or "invalid_backend_url"))
        return str(config["url"])

    def _extract_username(self, payload: dict[str, Any]) -> str | None:
        candidates = (
            payload.get("username"),
            payload.get("name"),
            payload.get("email"),
        )
        user_obj = payload.get("user")
        if isinstance(user_obj, dict):
            candidates += (
                user_obj.get("username"),
                user_obj.get("name"),
                user_obj.get("email"),
            )
        for value in candidates:
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def _record_success(self, endpoint: str, payload: dict[str, Any]) -> None:
        if self._cache is None:
            return
        try:
            self._cache.record_success(endpoint, str(payload.get("title", "")))
        except Exception as exc:
            xbmc.log(f"[PunchPlay] Status success update failed: {exc}", xbmc.LOGDEBUG)

    def _record_error(self, message: str) -> None:
        if self._cache is None:
            return
        try:
            self._cache.record_error(message)
        except Exception as exc:
            xbmc.log(f"[PunchPlay] Status error update failed: {exc}", xbmc.LOGDEBUG)

    def _record_identify_result(
        self,
        *,
        status: str,
        title: str = "",
        confidence: float | None = None,
    ) -> None:
        if self._cache is None:
            return
        try:
            self._cache.record_identify_result(
                status=status,
                title=title,
                confidence=confidence,
            )
        except Exception as exc:
            xbmc.log(f"[PunchPlay] Identify status update failed: {exc}", xbmc.LOGDEBUG)

    def _get_or_create_device_id(self) -> str:
        if os.path.exists(self._device_id_file):
            with open(self._device_id_file, "r") as f:
                device_id = f.read().strip()
            if device_id:
                return device_id
        device_id = str(uuid.uuid4())
        fd = os.open(self._device_id_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(device_id)
        return device_id

    def _load_tokens(self) -> dict[str, str]:
        if os.path.exists(self._token_file):
            try:
                with open(self._token_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_tokens(self, tokens: dict[str, str]) -> None:
        self._tokens = tokens
        fd = os.open(self._token_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(tokens, f, indent=2)

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": f"{ADDON_ID}/{self._client_version} Kodi",
            "Accept": "application/json",
        }
        if self._tokens.get("access_token"):
            headers["Authorization"] = f"Bearer {self._tokens['access_token']}"
        return headers

    def _identify_cache_key(
        self,
        metadata: dict[str, Any],
        *,
        raw_filename: str | None,
        duration_seconds: int | None,
    ) -> str:
        key_payload = {
            "media_type": metadata.get("media_type"),
            "title": metadata.get("title"),
            "year": metadata.get("year"),
            "season": metadata.get("season"),
            "episode": metadata.get("episode"),
            "episode_end": metadata.get("episode_end"),
            "absolute_episode": metadata.get("absolute_episode"),
            "anime": bool(metadata.get("anime")),
            "raw_filename": raw_filename or metadata.get("raw_filename"),
            "duration_bucket": int(duration_seconds or 0) // 300,
        }
        return "identify:{0}".format(json.dumps(key_payload, sort_keys=True, separators=(",", ":")))

    def identify_media(
        self,
        metadata: dict[str, Any],
        *,
        raw_filename: str | None = None,
        duration_seconds: int | None = None,
    ) -> dict[str, Any] | None:
        if any(metadata.get(key) for key in ("tmdb_id", "tvdb_id", "imdb_id")):
            return None
        if not metadata.get("title"):
            return None

        cache_key = self._identify_cache_key(
            metadata,
            raw_filename=raw_filename,
            duration_seconds=duration_seconds,
        )
        if self._cache is not None:
            cached = self._cache.get_identifier(cache_key)
            if cached:
                if cached.get("matched") is False:
                    xbmc.log(
                        "[PunchPlay] Identify cache no-match for {0!r}".format(
                            metadata.get("title")
                        ),
                        xbmc.LOGDEBUG,
                    )
                    return None
                xbmc.log(
                    "[PunchPlay] Identify cache hit for {0!r}".format(
                        metadata.get("title")
                    ),
                    xbmc.LOGDEBUG,
                )
                return cached

        payload: dict[str, Any] = {
            "media_type": metadata.get("media_type", "movie"),
            "title": metadata.get("title"),
            "year": metadata.get("year"),
            "raw_filename": raw_filename or metadata.get("raw_filename"),
            "duration_seconds": duration_seconds,
            "source": "kodi",
        }
        for key in ("season", "episode", "episode_end", "episode_title", "absolute_episode"):
            if metadata.get(key) is not None:
                payload[key] = metadata[key]
        if metadata.get("anime"):
            payload["anime"] = True

        try:
            response = self._request(
                "POST",
                IDENTIFY_ENDPOINT,
                payload,
                timeout=IDENTIFY_REQUEST_TIMEOUT_SECS,
            )
        except (BackendConfigurationError, ConnectionError, urllib.error.HTTPError, ValueError) as exc:
            xbmc.log(
                "[PunchPlay] Identify unavailable for {0!r}: {1}".format(
                    metadata.get("title"),
                    exc,
                ),
                xbmc.LOGDEBUG,
            )
            self._record_identify_result(status="error", title=str(metadata.get("title") or ""))
            return None
        except Exception as exc:
            xbmc.log(
                "[PunchPlay] Identify error for {0!r}: {1}".format(
                    metadata.get("title"),
                    exc,
                ),
                xbmc.LOGDEBUG,
            )
            self._record_identify_result(status="error", title=str(metadata.get("title") or ""))
            return None

        if not isinstance(response, dict):
            self._record_identify_result(status="invalid", title=str(metadata.get("title") or ""))
            return None

        confidence = response.get("confidence")
        try:
            confidence_value = float(confidence) if confidence is not None else 0.0
        except (TypeError, ValueError):
            confidence_value = 0.0

        if not response.get("matched") or confidence_value < IDENTIFY_MATCH_THRESHOLD:
            if self._cache is not None:
                self._cache.set_identifier(
                    cache_key,
                    {"matched": False, "confidence": confidence_value},
                    ttl_secs=IDENTIFIER_NO_MATCH_CACHE_TTL_SECS,
                )
            self._record_identify_result(
                status="no_match" if not response.get("matched") else "low_confidence",
                title=str(metadata.get("title") or ""),
                confidence=confidence_value,
            )
            xbmc.log(
                "[PunchPlay] Identify rejected for {0!r} at confidence {1:.2f}".format(
                    metadata.get("title"),
                    confidence_value,
                ),
                xbmc.LOGDEBUG,
            )
            return None

        canonical: dict[str, Any] = {
            "matched": True,
            "media_type": response.get("media_type") or metadata.get("media_type"),
            "title": response.get("title") or metadata.get("title"),
            "year": response.get("year") if response.get("year") is not None else metadata.get("year"),
            "season": response.get("season") if response.get("season") is not None else metadata.get("season"),
            "episode": response.get("episode") if response.get("episode") is not None else metadata.get("episode"),
            "episode_end": response.get("episode_end") if response.get("episode_end") is not None else metadata.get("episode_end"),
            "absolute_episode": response.get("absolute_episode") if response.get("absolute_episode") is not None else metadata.get("absolute_episode"),
            "episode_title": response.get("episode_title") or metadata.get("episode_title"),
            "tmdb_id": response.get("tmdb_id"),
            "tvdb_id": response.get("tvdb_id"),
            "imdb_id": response.get("imdb_id"),
            "punchplay_id": response.get("punchplay_id"),
            "anime": bool(response.get("anime") or metadata.get("anime")),
            "identify_source": "backend",
            "identify_confidence": confidence_value,
        }
        if self._cache is not None:
            self._cache.set_identifier(
                cache_key,
                canonical,
                ttl_secs=IDENTIFIER_SUCCESS_CACHE_TTL_SECS,
            )
        self._record_identify_result(
            status="matched",
            title=str(canonical.get("title") or ""),
            confidence=confidence_value,
        )
        xbmc.log(
            "[PunchPlay] Identify matched {0!r} at confidence {1:.2f}".format(
                canonical.get("title"),
                confidence_value,
            ),
            xbmc.LOGDEBUG,
        )
        return canonical

    # ------------------------------------------------------------------
    # Low-level request
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        retry_on_401: bool = True,
        timeout: int = REQUEST_TIMEOUT_SECS,
    ) -> dict[str, Any]:
        """
        Perform an HTTP request.  Returns the parsed JSON body.
        Raises ConnectionError on network failure, urllib.error.HTTPError on
        non-2xx responses.
        """
        url = f"{self._base_url()}{path}"
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(
            url, data=body, headers=self._headers(), method=method
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            if exc.code == 401 and retry_on_401:
                xbmc.log("[PunchPlay] 401 — attempting token refresh", xbmc.LOGDEBUG)
                if self._do_refresh():
                    return self._request(
                        method, path, payload, retry_on_401=False, timeout=timeout
                    )
            raise
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            raise ConnectionError(str(exc)) from exc

    # ------------------------------------------------------------------
    # Token refresh
    # ------------------------------------------------------------------

    def _do_refresh(self) -> bool:
        refresh_token = self._tokens.get("refresh_token")
        if not refresh_token:
            return False
        try:
            url = f"{self._base_url()}{AUTH_REFRESH_ENDPOINT}"
            body = json.dumps({"refresh_token": refresh_token}).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=body,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                new_tokens = json.loads(resp.read())
            self._save_tokens(new_tokens)
            xbmc.log("[PunchPlay] Token refreshed successfully", xbmc.LOGDEBUG)
            return True
        except BackendConfigurationError as exc:
            xbmc.log(f"[PunchPlay] Token refresh blocked: {exc}", xbmc.LOGWARNING)
            self._record_error(f"Backend configuration error: {exc}")
            return False
        except Exception as exc:
            xbmc.log(f"[PunchPlay] Token refresh failed: {exc}", xbmc.LOGWARNING)
            self._record_error(f"Token refresh failed: {exc}")
            return False

    # ------------------------------------------------------------------
    # Scrobble POST (with offline queue fallback)
    # ------------------------------------------------------------------

    def _is_permanent_client_error(self, status_code: int) -> bool:
        return status_code in PERMANENT_HTTP_STATUS_CODES

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        """
        POST *payload* to *path*.  On network error, writes the event to the
        offline queue — never silently drops it.  Returns the response dict on
        success, or None when the request was queued.
        """
        try:
            result = self._request("POST", path, payload)
            self._record_success(path, payload)
            return result
        except BackendConfigurationError as exc:
            xbmc.log(
                f"[PunchPlay] Backend URL invalid ({exc}) — preserving {path}",
                xbmc.LOGWARNING,
            )
            self._record_error(f"Backend configuration error: {exc}")
            if self._cache is not None:
                self._cache.enqueue_scrobble(path, payload)
            return None
        except ConnectionError as exc:
            xbmc.log(
                f"[PunchPlay] Network error ({exc}) — queuing {path}", xbmc.LOGWARNING
            )
            self._record_error(f"Network error on {path}: {exc}")
            if self._cache is not None:
                self._cache.enqueue_scrobble(path, payload)
            return None
        except urllib.error.HTTPError as exc:
            if 500 <= exc.code < 600:
                # Transient server error — queue for retry.
                xbmc.log(
                    f"[PunchPlay] HTTP {exc.code} on {path} — queuing", xbmc.LOGWARNING
                )
                self._record_error(f"HTTP {exc.code} on {path}")
                if self._cache is not None:
                    self._cache.enqueue_scrobble(path, payload)
            elif not self._is_permanent_client_error(exc.code):
                xbmc.log(
                    f"[PunchPlay] HTTP {exc.code} on {path} — preserving for retry",
                    xbmc.LOGWARNING,
                )
                self._record_error(f"HTTP {exc.code} on {path}")
                if self._cache is not None:
                    self._cache.enqueue_scrobble(path, payload)
            else:
                # Permanent client error (4xx) — drop, retrying won't help.
                xbmc.log(
                    f"[PunchPlay] HTTP {exc.code} on {path} — dropping (permanent error)",
                    xbmc.LOGWARNING,
                )
                self._record_error(f"HTTP {exc.code} on {path} (dropped)")
            return None

    def post_immediate(
        self,
        path: str,
        payload: dict[str, Any],
        timeout: int = 30,
    ) -> dict[str, Any]:
        """
        POST without offline queue fallback.  Raises on failure.
        Use for actions like rating where queuing doesn't make sense.
        """
        result = self._request("POST", path, payload, timeout=timeout)
        self._record_success(path, payload)
        return result

    # ------------------------------------------------------------------
    # Offline queue flush
    # ------------------------------------------------------------------

    def flush_queue(self) -> None:
        """Replay pending offline scrobbles in insertion order."""
        if self._cache is None:
            return
        expired = self._cache.drop_expired_pending_scrobbles()
        if expired:
            xbmc.log(
                f"[PunchPlay] Dropped {expired} expired queued scrobble(s)",
                xbmc.LOGINFO,
            )

        pending = self._cache.get_pending_scrobbles()
        if not pending:
            return
        xbmc.log(
            f"[PunchPlay] Flushing {len(pending)} queued scrobble(s)", xbmc.LOGINFO
        )
        for item in pending:
            scrobble_id = int(item["id"])
            endpoint = str(item["endpoint"])
            payload = dict(item["payload"])
            try:
                self._request("POST", endpoint, payload)
                self._cache.delete_pending_scrobble(scrobble_id)
                self._record_success(endpoint, payload)
                xbmc.log(
                    f"[PunchPlay] Replayed queued scrobble id={scrobble_id} → {endpoint}",
                    xbmc.LOGDEBUG,
                )
            except BackendConfigurationError as exc:
                self._cache.mark_pending_scrobble_attempt(
                    scrobble_id,
                    f"Backend config error: {exc}",
                )
                self._record_error(f"Backend configuration error replaying {endpoint}: {exc}")
                xbmc.log("[PunchPlay] Invalid backend URL — stopping queue flush", xbmc.LOGWARNING)
                break
            except ConnectionError as exc:
                self._cache.mark_pending_scrobble_attempt(
                    scrobble_id,
                    f"Network error: {exc}",
                )
                self._record_error(f"Network error replaying {endpoint}: {exc}")
                xbmc.log("[PunchPlay] Still offline — stopping queue flush", xbmc.LOGDEBUG)
                break  # remain offline; try again later
            except urllib.error.HTTPError as exc:
                if self._is_permanent_client_error(exc.code):
                    self._cache.mark_pending_scrobble_attempt(
                        scrobble_id,
                        f"HTTP {exc.code} (permanent)",
                    )
                    xbmc.log(
                        f"[PunchPlay] HTTP {exc.code} replaying id={scrobble_id} — dropping",
                        xbmc.LOGWARNING,
                    )
                    self._cache.delete_pending_scrobble(scrobble_id)
                    self._record_error(f"HTTP {exc.code} replaying {endpoint} (dropped)")
                    continue

                self._cache.mark_pending_scrobble_attempt(
                    scrobble_id,
                    f"HTTP {exc.code}",
                )
                self._record_error(f"HTTP {exc.code} replaying {endpoint}")
                xbmc.log(
                    f"[PunchPlay] HTTP {exc.code} replaying id={scrobble_id} — keeping queued",
                    xbmc.LOGWARNING,
                )
                break

    # ------------------------------------------------------------------
    # Device-code login — QR dialog helpers
    # ------------------------------------------------------------------

    def _write_qr_image(self, data_uri: str) -> str | None:
        """
        Decode a `data:image/png;base64,...` payload and write it to
        addon_data/login_qr.png.  Returns the absolute path on success or
        None if the payload is malformed / IO fails.
        """
        prefix = "data:image/png;base64,"
        if not data_uri.startswith(prefix):
            return None
        try:
            png_bytes = base64.b64decode(data_uri[len(prefix):], validate=True)
        except Exception as exc:
            xbmc.log(f"[PunchPlay] QR decode failed: {exc}", xbmc.LOGWARNING)
            return None

        # Use a unique filename each time so Kodi's texture cache doesn't
        # serve a stale QR from a previous login attempt.
        filename = f"login_qr_{int(time.time())}.png"
        path = os.path.join(self._data_dir, filename)

        # Clean up old QR images first.
        try:
            for old in os.listdir(self._data_dir):
                if old.startswith("login_qr_") and old.endswith(".png"):
                    try:
                        os.remove(os.path.join(self._data_dir, old))
                    except OSError:
                        pass
        except OSError:
            pass

        try:
            with open(path, "wb") as f:
                f.write(png_bytes)
        except OSError as exc:
            xbmc.log(f"[PunchPlay] QR write failed: {exc}", xbmc.LOGWARNING)
            return None
        return path

    def _show_qr_login_dialog(
        self,
        *,
        qr_path: str,
        verification_uri: str,
        user_code: str,
        device_code: str,
        expires_in: int,
    ) -> bool | None:
        """
        Present the QR LoginDialog while polling for approval in the
        background.

        Returns:
          True  — login succeeded (dialog auto-closed on approval)
          False — dialog could not be shown (caller should fall back)
          None  — user dismissed the dialog manually (caller should
                  continue with the DialogProgress poll loop)
        """
        try:
            from login_dialog import LoginDialog

            _s = localize
            bg_path = os.path.join(get_addon_path(), "resources", "media", "background.png")
            minutes = max(1, expires_in // 60)

            login_dialog = LoginDialog(
                bg_path=bg_path,
                qr_path=qr_path,
                title=_s(32015),
                scan_label=_s(32016),
                or_visit_label=_s(32017),
                uri=verification_uri,
                code_label=_s(32018),
                code=user_code,
                expires_label=_s(32005).format(minutes),
                dismiss_hint=_s(32019),
            )

            # Poll for approval in a background thread.  If the user
            # approves on their phone, the dialog auto-closes.
            stop_event = threading.Event()

            def poll_loop() -> None:
                monitor = xbmc.Monitor()
                deadline = time.monotonic() + expires_in
                while (
                    not stop_event.is_set()
                    and time.monotonic() < deadline
                    and not monitor.abortRequested()
                ):
                    try:
                        resp = self._request(
                            "POST",
                            AUTH_DEVICE_TOKEN_ENDPOINT,
                            {
                                "device_code": device_code,
                                "device_id": self.device_id,
                                "device_name": (
                                    xbmc.getInfoLabel("System.FriendlyName")
                                    or "Kodi"
                                ),
                            },
                            retry_on_401=False,
                        )
                        if resp.get("access_token"):
                            self._save_tokens(resp)
                            username = self._extract_username(resp)
                            if username and self._cache is not None:
                                self._cache.set_account_username(username)
                            xbmc.log(
                                "[PunchPlay] Device-code login succeeded (QR dialog)",
                                xbmc.LOGINFO,
                            )
                            login_dialog.approve()
                            return
                    except urllib.error.HTTPError as exc:
                        xbmc.log(f"[PunchPlay] QR poll: HTTP {exc.code}", xbmc.LOGDEBUG)
                    except Exception as exc:
                        xbmc.log(f"[PunchPlay] QR poll error: {exc}", xbmc.LOGWARNING)
                    # Sleep in short slices so we can react to stop_event.
                    for _ in range(6):
                        if stop_event.is_set():
                            return
                        time.sleep(0.5)

            thread = threading.Thread(
                target=poll_loop, name="PunchPlayQRPoll", daemon=True
            )
            thread.start()

            login_dialog.doModal()

            # Dialog closed — either by approve() or by the user.
            stop_event.set()
            thread.join(timeout=3)

            approved = login_dialog.was_approved
            del login_dialog

            if approved:
                xbmcgui.Dialog().notification(
                    NOTIFICATION_TITLE,
                    _s(32011),
                    xbmcgui.NOTIFICATION_INFO,
                    4000,
                )
                return True

            # User dismissed manually — caller can fall back to
            # DialogProgress poll.
            return None

        except Exception as exc:
            xbmc.log(f"[PunchPlay] QR dialog failed: {exc}", xbmc.LOGWARNING)
            return False

    # ------------------------------------------------------------------
    # Device-code login
    # ------------------------------------------------------------------

    def device_code_login(self) -> bool:
        """
        Run the full device-code OAuth flow with Kodi dialogs.
        Returns True on success, False on failure/cancellation.
        """
        _s = localize
        dialog = xbmcgui.Dialog()

        # Step 1 — request a device code.
        try:
            resp = self._request(
                "POST", AUTH_DEVICE_CODE_ENDPOINT, {}, retry_on_401=False
            )
        except BackendConfigurationError as exc:
            dialog.ok(_s(32000), _s(32087).format(str(exc)))
            return False
        except Exception as exc:
            dialog.ok(_s(32000), f"{_s(32001)}\n{exc}")
            return False

        user_code = resp.get("user_code", "")
        verification_uri = resp.get("verification_uri", self._base_url())
        verification_uri_qr = resp.get("verification_uri_qr", "")
        device_code = resp.get("device_code", "")
        expires_in: int = int(resp.get("expires_in", 600))

        if not user_code or not device_code:
            dialog.ok(_s(32000), _s(32002))
            return False

        # Step 2 — show the code to the user.  Prefer the QR window when
        # the backend provides one; otherwise fall back to a compact
        # text-only dialog that still fits on screen without scrolling.
        #
        # The QR dialog polls in the background and auto-closes on
        # approval.  Returns:
        #   True  → login completed, we're done
        #   None  → user dismissed manually, fall through to poll loop
        #   False → dialog failed to show, fall back to text dialog
        qr_result: bool | None = False
        if verification_uri_qr:
            qr_path = self._write_qr_image(verification_uri_qr)
            if qr_path:
                qr_result = self._show_qr_login_dialog(
                    qr_path=qr_path,
                    verification_uri=verification_uri,
                    user_code=user_code,
                    device_code=device_code,
                    expires_in=expires_in,
                )

        if qr_result is True:
            return True  # Already logged in via QR dialog.

        if qr_result is False:
            # QR not available or failed — show the compact text dialog.
            dialog.ok(
                _s(32000),
                (
                    f"{_s(32003)} [B]{verification_uri}[/B]\n"
                    f"{_s(32004)} [B]{user_code}[/B]\n\n"
                    + _s(32005).format(expires_in // 60)
                ),
            )

        # Step 3 — poll for the token with a cancellable progress dialog.
        # (Only reached if QR dialog was dismissed manually or not shown.)
        monitor = xbmc.Monitor()
        deadline = time.monotonic() + expires_in
        progress = xbmcgui.DialogProgress()
        progress.create(_s(32006), _s(32007))

        try:
            while time.monotonic() < deadline and not monitor.abortRequested():
                if progress.iscanceled():
                    xbmc.log("[PunchPlay] Device-code login cancelled by user", xbmc.LOGINFO)
                    return False

                remaining = max(0, int(deadline - time.monotonic()))
                pct = int(100 * (1 - remaining / expires_in))
                progress.update(pct, _s(32008).format(remaining))

                try:
                    token_resp = self._request(
                        "POST",
                        AUTH_DEVICE_TOKEN_ENDPOINT,
                        {
                            "device_code": device_code,
                            "device_id": self.device_id,
                            "device_name": xbmc.getInfoLabel("System.FriendlyName") or "Kodi",
                        },
                        retry_on_401=False,
                    )
                    if token_resp.get("access_token"):
                        progress.close()
                        self._save_tokens(token_resp)
                        username = self._extract_username(token_resp)
                        if username and self._cache is not None:
                            self._cache.set_account_username(username)
                        xbmc.log("[PunchPlay] Device-code login succeeded", xbmc.LOGINFO)
                        xbmcgui.Dialog().notification(
                            NOTIFICATION_TITLE, _s(32011), xbmcgui.NOTIFICATION_INFO, 4000
                        )
                        return True

                except ConnectionError as exc:
                    xbmc.log(f"[PunchPlay] Poll network error: {exc}", xbmc.LOGDEBUG)
                except urllib.error.HTTPError as exc:
                    # The /token endpoint returns 400 for all non-success
                    # states.  Read the body to distinguish between
                    # "authorization_pending" (keep polling) and terminal
                    # errors like "expired" or "access_denied".
                    error = ""
                    try:
                        body = json.loads(exc.read().decode("utf-8"))
                        error = body.get("error", "")
                    except Exception:
                        pass
                    xbmc.log(
                        f"[PunchPlay] Poll HTTP {exc.code}: {error or 'unknown'}",
                        xbmc.LOGDEBUG,
                    )
                    if error in ("expired", "access_denied"):
                        progress.close()
                        dialog.ok(_s(32000), _s(32009).format(error))
                        return False
                    if exc.code >= 500:
                        xbmc.log(
                            f"[PunchPlay] Server error {exc.code} during poll",
                            xbmc.LOGWARNING,
                        )
                    # authorization_pending or slow_down → keep polling.
                except Exception as exc:
                    # Catch-all for unexpected errors (JSON parse, file I/O
                    # in _save_tokens, etc.) so the loop doesn't crash.
                    xbmc.log(
                        f"[PunchPlay] Unexpected poll error: {exc}",
                        xbmc.LOGWARNING,
                    )

                monitor.waitForAbort(5)
        finally:
            try:
                progress.close()
            except Exception:
                pass

        dialog.ok(_s(32000), _s(32010))
        return False

    # ------------------------------------------------------------------
    # Logout
    # ------------------------------------------------------------------

    def logout(self) -> bool:
        """Clear stored tokens and queued offline data after confirmation."""
        pending_count = 0
        if self._cache is not None:
            try:
                pending_count = int(self._cache.get_queue_summary()["count"] or 0)
            except Exception:
                pending_count = 0

        if pending_count > 0:
            confirmed = xbmcgui.Dialog().yesno(
                ADDON_NAME,
                localize(32075).format(pending_count),
            )
            if not confirmed:
                return False

        if os.path.exists(self._token_file):
            os.remove(self._token_file)
        self._tokens = {}
        if self._cache is not None:
            try:
                self._cache.clear_pending_scrobbles()
                self._cache.set_account_username(None)
                xbmc.log("[PunchPlay] Offline queue cleared on logout", xbmc.LOGDEBUG)
            except Exception as exc:
                xbmc.log(f"[PunchPlay] Queue clear error: {exc}", xbmc.LOGDEBUG)
        xbmc.log("[PunchPlay] Tokens cleared (logged out)", xbmc.LOGINFO)
        xbmcgui.Dialog().notification(
            NOTIFICATION_TITLE, localize(32012),
            xbmcgui.NOTIFICATION_INFO, 3000
        )
        return True

    def clear_offline_queue(self) -> int:
        if self._cache is None:
            return 0
        count = int(self._cache.get_queue_summary()["count"] or 0)
        self._cache.clear_pending_scrobbles()
        return count

    def test_connection(self) -> dict[str, Any]:
        was_authenticated = self.is_authenticated()
        backend_config = self._backend_config()
        if not backend_config["valid"]:
            self._record_error("Invalid backend URL configuration")
            return {"status": "invalid_backend", "message": localize(32087).format(backend_config["display_url"] or localize(32071))}
        try:
            response = self._request(
                "GET",
                AUTH_ME_ENDPOINT,
                retry_on_401=was_authenticated,
                timeout=TEST_CONNECTION_TIMEOUT_SECS,
            )
            username = self._extract_username(response)
            if username and self._cache is not None:
                self._cache.set_account_username(username)
            self._record_success(AUTH_ME_ENDPOINT, {"title": username or ""})
            if username:
                return {
                    "status": "authenticated",
                    "message": localize(32055).format(username),
                    "username": username,
                }
            return {
                "status": "authenticated",
                "message": localize(32055).format(localize(32071)),
                "username": None,
            }
        except ConnectionError as exc:
            self._record_error(f"Connection test failed: {exc}")
            return {"status": "unreachable", "message": localize(32057)}
        except BackendConfigurationError as exc:
            self._record_error(f"Invalid backend URL: {exc}")
            return {"status": "invalid_backend", "message": localize(32087).format(str(exc))}
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                if was_authenticated:
                    self._record_error("Session expired")
                    return {"status": "expired", "message": localize(32058)}
                return {"status": "not_logged_in", "message": localize(32056)}
            self._record_error(f"Connection test HTTP {exc.code}")
            return {"status": "unreachable", "message": localize(32057)}
        except Exception as exc:
            self._record_error(f"Connection test failed: {exc}")
            return {"status": "unreachable", "message": localize(32057)}

    def get_status_snapshot(self) -> dict[str, Any]:
        backend_config = self._backend_config()
        queue_summary = {"count": 0, "oldest_age_secs": None}
        queue_endpoints: dict[str, int] = {}
        runtime_status: dict[str, Any] = {}
        identifier_cache_size = 0
        if self._cache is not None:
            try:
                queue_summary = self._cache.get_queue_summary()
                queue_endpoints = self._cache.get_queue_endpoint_summary()
                identifier_cache_size = self._cache.get_identifier_cache_size()
                runtime_status = self._cache.get_runtime_status()
            except Exception as exc:
                xbmc.log(f"[PunchPlay] Status snapshot error: {exc}", xbmc.LOGDEBUG)

        return {
            "connected": self.is_authenticated(),
            "account_username": runtime_status.get("account_username"),
            "backend_url": backend_config["display_url"],
            "backend_valid": backend_config["valid"],
            "backend_error": backend_config["error"],
            "device_id": mask_value(self.device_id),
            "queue_count": queue_summary.get("count"),
            "oldest_queue_age_secs": queue_summary.get("oldest_age_secs"),
            "queue_endpoints": queue_endpoints,
            "last_successful_event_at": runtime_status.get("last_successful_event_at"),
            "last_successful_event_type": runtime_status.get("last_successful_event_type"),
            "last_successful_title": runtime_status.get("last_successful_title"),
            "last_error_at": runtime_status.get("last_error_at"),
            "last_error": runtime_status.get("last_error"),
            "last_identify_at": runtime_status.get("last_identify_at"),
            "last_identify_status": runtime_status.get("last_identify_status"),
            "last_identify_title": runtime_status.get("last_identify_title"),
            "last_identify_confidence": runtime_status.get("last_identify_confidence"),
            "identifier_cache_size": identifier_cache_size,
            "addon_version": self._client_version,
            "kodi_version": xbmc.getInfoLabel("System.BuildVersion") or localize(32071),
            "platform": platform.platform(),
            "python_version": sys.version.split()[0],
        }

    def _settings_summary(self) -> dict[str, Any]:
        addon = get_addon()
        anime_setting = addon.getSetting("anime_episode_format") or "0"
        anime_format_map = {
            "0": "auto",
            "1": "season_episode",
            "2": "absolute",
            "auto": "auto",
            "season_episode": "season_episode",
            "absolute": "absolute",
        }
        return {
            "scrobble_movies": addon.getSettingBool("scrobble_movies"),
            "scrobble_tv": addon.getSettingBool("scrobble_tv"),
            "scrobble_anime": addon.getSettingBool("scrobble_anime"),
            "anime_episode_format": anime_format_map.get(anime_setting, "auto"),
            "watched_threshold": addon.getSettingInt("watched_threshold"),
            "min_length_minutes": addon.getSettingInt("min_length"),
            "heartbeat_interval": HEARTBEAT_INTERVAL_SECS,
            "rate_after_watching": addon.getSettingBool("rate_after_watching"),
            "rating_prompt_delay_secs": addon.getSettingInt("rating_prompt_delay"),
            "show_notifications": addon.getSettingBool("show_notifications"),
            "notify_during_playback": addon.getSettingBool("notify_during_playback"),
            "developer_mode": addon.getSettingBool("developer_mode"),
            "allow_insecure_backend_url": addon.getSettingBool("allow_insecure_backend_url"),
        }

    def export_debug_info(self, *, verbose: bool = False) -> str:
        payload = self.get_status_snapshot()
        payload["exported_at"] = int(time.time() * 1000)
        payload["authenticated"] = self.is_authenticated()
        payload["settings"] = self._settings_summary()
        payload["verbose"] = verbose
        if verbose and self._cache is not None:
            payload["pending_queue"] = [
                {
                    "endpoint": item["endpoint"],
                    "created_at": item["created_at"],
                    "attempt_count": item["attempt_count"],
                    "last_attempt_at": item["last_attempt_at"],
                    "last_error": item["last_error"],
                    "event_id": item["payload"].get("event_id"),
                    "playback_session_id": item["payload"].get("playback_session_id"),
                    "raw_filename": item["payload"].get("raw_filename"),
                }
                for item in self._cache.get_pending_scrobbles()
            ]
        path = os.path.join(
            self._data_dir,
            "punchplay-debug-verbose.json" if verbose else "punchplay-debug.json",
        )
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
        return path

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def is_authenticated(self) -> bool:
        return bool(self._tokens.get("access_token"))
