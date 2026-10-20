# SPDX-License-Identifier: GPL-2.0-only
"""This device's identity.

The id is generated once and persisted. Defaulting it to the addon id would give every
install in a household the same value, which defeats the per-device routing the whole
integration exists for.
"""

from __future__ import annotations

import json
import os
import uuid

from resources.lib.config import Settings
from resources.lib.kodi import KodiApi
from resources.lib.log import get_logger
from resources.lib.models import Device

_log = get_logger("device")


def _persisted_id(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as handle:
            stored = json.load(handle)
        existing = str(stored.get("device_id") or "").strip()
        if existing:
            return existing
    except (OSError, ValueError):
        pass

    generated = uuid.uuid4().hex
    try:
        os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"device_id": generated}, handle)
        os.chmod(path, 0o600)
    except OSError as exc:
        _log.warning("device.id_not_persisted", error=str(exc))
    return generated


def device_identity(kodi: KodiApi, settings: Settings, path: str) -> Device:
    device_id = settings.device_id or _persisted_id(path)
    name = settings.device_name or kodi.info_label("System.FriendlyName") or device_id
    return Device(id=device_id, name=name)
