"""Hyperion JSON RPC/HTTP(S) API client."""
from __future__ import annotations

import contextlib
import random
import string
from json import JSONDecodeError
from typing import Any

import requests
from requests.exceptions import ConnectTimeout

from resources.lib.interfaces import GuiHandler
from resources.lib.interfaces import Logger
from resources.lib.interfaces import SettingsManager


class ApiClient:
    """Manages the request to the hyperion server."""

    def __init__(
        self, logger: Logger, gui: GuiHandler, settings: SettingsManager
    ) -> None:
        self._settings = settings
        self._logger = logger
        self._gui = gui
        self._session = requests.Session()

    @property
    def headers(self) -> dict[str, str]:
        """Request headers."""
        headers = {"Content-type": "application/json"}
        if self._settings.auth_token:
            headers["Authorization"] = f"token {self._settings.auth_token}"
        return headers

    def _send(
        self, body: dict[str, Any], timeout: float = 0.5
    ) -> dict[str, Any] | None:
        url = self._settings.base_url
        logger = self._logger
        logger.log(f"Send to: {url} payload: {body}")
        with contextlib.suppress(ConnectTimeout, JSONDecodeError):
            response = self._session.post(
                url, json=body, headers=self.headers, timeout=timeout
            )
            json_content = response.json()
            if json_content.get("success"):
                return json_content.get("info")
            if json_content["error"] == "No Authorization":
                self._gui.notify_text("Error: No Authorization, API Token required")
            logger.error(json_content["error"])
        return None

    def needs_auth(self) -> bool:
        """Whether the hyperion server needs API authentication."""
        if res := self._send({"command": "authorize", "subcommand": "tokenRequired"}):
            return res["required"]
        return False

    def get_token(self) -> str:
        """Requests the authentication token."""
        pool = string.ascii_uppercase + string.ascii_lowercase + string.digits
        control_code = "".join(random.choice(pool) for _ in range(16))
        message = {
            "command": "authorize",
            "subcommand": "requestToken",
            "comment": "Kodi Hyperion Control",
            "id": control_code,
        }
        return res["token"] if (res := self._send(message, timeout=180)) else ""

    def send_component_state(self, component: str, state: bool) -> None:
        """Sends the component state."""
        body = {
            "command": "componentstate",
            "componentstate": {"component": component, "state": state},
        }
        if component == "FORWARDER":
            self.switch_to_instance(0)
            self._send(body)
        else:
            self.send_to_all_instances(body)

    def send_video_mode(self, mode: str) -> None:
        """Sends the current video mode."""
        self._send({"command": "videoMode", "videoMode": mode})

    def get_server_info(self) -> dict[str, Any] | None:
        """Gets the server info."""
        return self._send({"command": "serverinfo"})

    def get_instances(self) -> list[dict[str, Any]]:
        """Gets the server info."""
        server_info = self.get_server_info()
        return server_info["instance"] if server_info else []

    def switch_to_instance(self, instance_num: int) -> None:
        """Switches to the specified instance."""
        self._send(
            {"command": "instance", "subcommand": "switchTo", "instance": instance_num}
        )

    def send_to_all_instances(self, body: dict[str, Any]) -> None:
        """Sends a command to all instances."""
        for instance in self.get_instances():
            self.switch_to_instance(instance["instance"])
            self._send(body)
