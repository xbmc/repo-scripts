"""
api.py — HTTP client for the PunchPlay backend.

Responsibilities:
  • Attach Bearer token to every request.
  • Transparently refresh the access token on 401 and retry once.
  • Queue failed POST events in SQLite via Cache so nothing is lost offline.
  • Flush the offline queue on the next successful connection.
  • Device-code login flow with a Kodi progress dialog.
"""

import json
import os
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
_VERSION = "1.0.0"


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
        with open(self._device_id_file, "w") as f:
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
        with open(self._token_file, "w") as f:
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
            xbmc.log(
                f"[PunchPlay] HTTP {exc.code} on {path} — queuing", xbmc.LOGWARNING
            )
            if self._cache is not None:
                self._cache.enqueue_scrobble(path, payload)
            return None

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
                xbmc.log(
                    f"[PunchPlay] HTTP {exc.code} replaying id={scrobble_id} — dropping",
                    xbmc.LOGWARNING,
                )
                # Drop unrecoverable server errors (4xx) so they don't block the queue.
                if 400 <= exc.code < 500:
                    self._cache.delete_pending_scrobble(scrobble_id)

    # ------------------------------------------------------------------
    # Device-code login
    # ------------------------------------------------------------------

    def device_code_login(self) -> bool:
        """
        Run the full device-code OAuth flow with Kodi dialogs.
        Returns True on success, False on failure/cancellation.
        """
        dialog = xbmcgui.Dialog()

        # Step 1 — request a device code.
        try:
            resp = self._request(
                "POST", "/api/auth/device/code", {}, retry_on_401=False
            )
        except Exception as exc:
            dialog.ok("PunchPlay — Login", f"Could not reach the server:\n{exc}")
            return False

        user_code = resp.get("user_code", "")
        verification_uri = resp.get("verification_uri", self._base_url())
        device_code = resp.get("device_code", "")
        expires_in: int = int(resp.get("expires_in", 600))

        if not user_code or not device_code:
            dialog.ok("PunchPlay — Login", "Invalid response from server. Try again.")
            return False

        # Step 2 — show the code to the user.
        dialog.ok(
            "PunchPlay — Login",
            (
                f"Open your browser and visit:\n"
                f"[B]{verification_uri}[/B]\n\n"
                f"Enter this code:\n"
                f"[B]{user_code}[/B]\n\n"
                f"The code expires in [B]{expires_in // 60}[/B] minutes.\n"
                f"Press OK — then this dialog will wait for approval."
            ),
        )

        # Step 3 — poll for the token with a cancellable progress dialog.
        monitor = xbmc.Monitor()
        deadline = time.monotonic() + expires_in
        progress = xbmcgui.DialogProgress()
        progress.create("PunchPlay — Waiting for Login", "Waiting for approval…")

        try:
            while time.monotonic() < deadline and not monitor.abortRequested():
                if progress.iscanceled():
                    xbmc.log("[PunchPlay] Device-code login cancelled by user", xbmc.LOGINFO)
                    return False

                remaining = max(0, int(deadline - time.monotonic()))
                pct = int(100 * (1 - remaining / expires_in))
                progress.update(pct, f"Waiting for approval… ({remaining}s remaining)")

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
                            "PunchPlay",
                            "Login successful!",
                            xbmcgui.NOTIFICATION_INFO,
                            4000,
                        )
                        return True

                    error = token_resp.get("error", "")
                    if error in ("expired", "access_denied"):
                        progress.close()
                        dialog.ok("PunchPlay — Login", f"Login failed ({error}). Please try again.")
                        return False
                    # 'authorization_pending' or 'slow_down' → keep polling.

                except ConnectionError as exc:
                    xbmc.log(f"[PunchPlay] Poll error: {exc}", xbmc.LOGDEBUG)
                except urllib.error.HTTPError:
                    pass

                monitor.waitForAbort(5)
        finally:
            try:
                progress.close()
            except Exception:
                pass

        dialog.ok("PunchPlay — Login", "Login timed out. Please try again.")
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
            "PunchPlay", "Logged out.", xbmcgui.NOTIFICATION_INFO, 3000
        )

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def is_authenticated(self) -> bool:
        return bool(self._tokens.get("access_token"))
