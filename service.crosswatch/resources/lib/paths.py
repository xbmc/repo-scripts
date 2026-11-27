# SPDX-License-Identifier: GPL-2.0-only
"""One owner for the addon_data layout.

Both entry points and the test harness derive their paths from here, so a change to the
layout cannot silently break one of them.
"""

from __future__ import annotations

import os

from resources.lib.constants import ADDON_ID
from resources.lib.kodi import KodiApi


def profile_dir(kodi: KodiApi) -> str:
    return kodi.translate(f"special://profile/addon_data/{ADDON_ID}")


def viewers_path(kodi: KodiApi) -> str:
    return os.path.join(profile_dir(kodi), "viewers.json")


def prompts_path(kodi: KodiApi) -> str:
    return os.path.join(profile_dir(kodi), "prompts.json")


def device_path(kodi: KodiApi) -> str:
    return os.path.join(profile_dir(kodi), "device.json")


def outbox_path(kodi: KodiApi) -> str:
    return os.path.join(profile_dir(kodi), "outbox.json")


def routes_path(kodi: KodiApi) -> str:
    return os.path.join(profile_dir(kodi), "routes.json")


def log_dir(kodi: KodiApi) -> str:
    return os.path.join(profile_dir(kodi), "logs")


def sync_db_path(kodi: KodiApi) -> str:
    return os.path.join(profile_dir(kodi), "sync.db")


def sync_inbox_path(kodi: KodiApi) -> str:
    return os.path.join(profile_dir(kodi), "sync_inbox.db")


def sync_started_path(kodi: KodiApi) -> str:
    return os.path.join(profile_dir(kodi), "sync_started.json")


def sync_requests_path(kodi: KodiApi) -> str:
    return os.path.join(profile_dir(kodi), "sync_requests.json")


def sync_status_path(kodi: KodiApi) -> str:
    return os.path.join(profile_dir(kodi), "sync_status.json")
