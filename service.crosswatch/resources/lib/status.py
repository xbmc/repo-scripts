# SPDX-License-Identifier: GPL-2.0-only
"""The connection line in the add-on settings.

A stored setting the add-on writes, so the settings screen shows it without a network call.
The instance name and the address appear on the screen only, never in Kodi's shared log.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from resources.lib.config import KEY_STATUS
from resources.lib.constants import STATUS_NOT_PAIRED, STATUS_PAIRED
from resources.lib.kodi import KodiApi


def fill(template: str, *values: str) -> str:
    """Each %s in turn, so a translation that needs two placeholders keeps them in order."""
    for value in values:
        template = template.replace("%s", value, 1)
    return template


def address_of(url: str) -> str:
    """Scheme and host of an endpoint, without credentials, for showing to the household."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return url
    host = parts.netloc.rsplit("@", 1)[-1]
    return f"{parts.scheme}://{host}" if parts.scheme and host else url


def paired(kodi: KodiApi, instance: str, url: str) -> str:
    return fill(kodi.localised(STATUS_PAIRED), instance, address_of(url))


def not_paired(kodi: KodiApi) -> str:
    return kodi.localised(STATUS_NOT_PAIRED)


def write(kodi: KodiApi, text: str) -> bool:
    """Only when it changes: every write wakes the service's settings reload."""
    if kodi.setting(KEY_STATUS) == text:
        return False
    kodi.set_setting(KEY_STATUS, text)
    return True
