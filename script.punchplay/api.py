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
import threading
import time
import uuid
import urllib.error
import urllib.request
from typing import Any

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

_ADDON_ID = "script.punchplay"
_VERSION = "1.1.0"


class APIClient:
    def __init__(self, cache=None) -> None:
        self._cache = cache

        addon = xbmcaddon.Addon(_ADDON_ID)
        self._data_dir: str = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
        os.makedirs(self._data_dir, exist_ok=True)

        self._token_file = os.path.join(self._data_dir, "tokens.json")
        self._device_id_file = os.path.join(self._data_dir, "device_id.txt")

        self._tokens: dict[str, str] = self._load_tokens()
        self.device_id: str = self._get_or_create_device_id()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _base_url(self) -> str:
        return xbmcaddon.Addon(_ADDON_ID).getSetting("backend_url").rstrip("/")

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
            "User-Agent": f"PunchPlayScrobble/{_VERSION} Kodi",
            "Accept": "application/json",
        }
        if self._tokens.get("access_token"):
            headers["Authorization"] = f"Bearer {self._tokens['access_token']}"
        return headers

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
        timeout: int = 15,
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
            url = f"{self._base_url()}/api/auth/refresh"
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
        except Exception as exc:
            xbmc.log(f"[PunchPlay] Token refresh failed: {exc}", xbmc.LOGWARNING)
            return False

    # ------------------------------------------------------------------
    # Scrobble POST (with offline queue fallback)
    # ------------------------------------------------------------------

    def _is_permanent_client_error(self, status_code: int) -> bool:
        """
        Return True when a client error is permanent and retrying will not help.

        401 is excluded: a queued event that still gets a 401 after the built-in
        refresh attempt should stay in the queue so it can be retried once the
        user logs in again.  All other 4xx errors are permanent.
        """
        return 400 <= status_code < 500 and status_code != 401

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        """
        POST *payload* to *path*.  On network error, writes the event to the
        offline queue — never silently drops it.  Returns the response dict on
        success, or None when the request was queued.
        """
        try:
            result = self._request("POST", path, payload)
            return result
        except ConnectionError as exc:
            xbmc.log(
                f"[PunchPlay] Network error ({exc}) — queuing {path}", xbmc.LOGWARNING
            )
            if self._cache is not None:
                self._cache.enqueue_scrobble(path, payload)
            return None
        except urllib.error.HTTPError as exc:
            if 500 <= exc.code < 600:
                # Transient server error — queue for retry.
                xbmc.log(
                    f"[PunchPlay] HTTP {exc.code} on {path} — queuing", xbmc.LOGWARNING
                )
                if self._cache is not None:
                    self._cache.enqueue_scrobble(path, payload)
            elif not self._is_permanent_client_error(exc.code):
                xbmc.log(
                    f"[PunchPlay] HTTP {exc.code} on {path} — preserving for retry",
                    xbmc.LOGWARNING,
                )
                if self._cache is not None:
                    self._cache.enqueue_scrobble(path, payload)
            else:
                # Permanent client error (4xx) — drop, retrying won't help.
                xbmc.log(
                    f"[PunchPlay] HTTP {exc.code} on {path} — dropping (permanent error)",
                    xbmc.LOGWARNING,
                )
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
        return self._request("POST", path, payload, timeout=timeout)

    # ------------------------------------------------------------------
    # Offline queue flush
    # ------------------------------------------------------------------

    def flush_queue(self) -> None:
        """Replay pending offline scrobbles in insertion order."""
        if self._cache is None:
            return
        pending = self._cache.get_pending_scrobbles()
        if not pending:
            return
        xbmc.log(
            f"[PunchPlay] Flushing {len(pending)} queued scrobble(s)", xbmc.LOGINFO
        )
        for scrobble_id, endpoint, payload in pending:
            try:
                self._request("POST", endpoint, payload)
                self._cache.delete_pending_scrobble(scrobble_id)
                xbmc.log(
                    f"[PunchPlay] Replayed queued scrobble id={scrobble_id} → {endpoint}",
                    xbmc.LOGDEBUG,
                )
            except ConnectionError:
                xbmc.log("[PunchPlay] Still offline — stopping queue flush", xbmc.LOGDEBUG)
                break  # remain offline; try again later
            except urllib.error.HTTPError as exc:
                if self._is_permanent_client_error(exc.code):
                    xbmc.log(
                        f"[PunchPlay] HTTP {exc.code} replaying id={scrobble_id} — dropping",
                        xbmc.LOGWARNING,
                    )
                    self._cache.delete_pending_scrobble(scrobble_id)
                    continue

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

            addon = xbmcaddon.Addon(_ADDON_ID)
            _s = addon.getLocalizedString
            bg_path = os.path.join(
                addon.getAddonInfo("path"),
                "resources", "media", "background.png",
            )
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
                            "/api/auth/device/token",
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
                    "PunchPlay",
                    addon.getLocalizedString(32011),
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
        addon = xbmcaddon.Addon(_ADDON_ID)
        _s = addon.getLocalizedString
        dialog = xbmcgui.Dialog()

        # Step 1 — request a device code.
        try:
            resp = self._request(
                "POST", "/api/auth/device/code", {}, retry_on_401=False
            )
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
                        "/api/auth/device/token",
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
                        xbmc.log("[PunchPlay] Device-code login succeeded", xbmc.LOGINFO)
                        xbmcgui.Dialog().notification(
                            "PunchPlay", _s(32011), xbmcgui.NOTIFICATION_INFO, 4000
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

    def logout(self) -> None:
        """Clear stored tokens from disk."""
        if os.path.exists(self._token_file):
            os.remove(self._token_file)
        self._tokens = {}
        xbmc.log("[PunchPlay] Tokens cleared (logged out)", xbmc.LOGINFO)
        xbmcgui.Dialog().notification(
            "PunchPlay", xbmcaddon.Addon(_ADDON_ID).getLocalizedString(32012),
            xbmcgui.NOTIFICATION_INFO, 3000
        )

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def is_authenticated(self) -> bool:
        return bool(self._tokens.get("access_token"))
