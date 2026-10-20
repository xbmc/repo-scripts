# SPDX-License-Identifier: GPL-2.0-only
"""Every setting, read in one place, as one immutable value.

The token is stored separately from the webhook URL and travels only in the
X-CrossWatch-Token header, so the credential never exists inside a URL that a logging path,
a proxy log or an error message could reach.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from resources.lib.constants import DEFAULT_INDEX_TTL_SECONDS, DEFAULT_PROGRESS_INTERVAL_SECONDS
from resources.lib.kodi import KodiApi

KEY_BASE_URL = "webhook_base_url"
KEY_TOKEN = "webhook_token"
KEY_STATUS = "connection_status"
KEY_DEVICE_ID = "device_id"
KEY_PROGRESS_INTERVAL = "progress_interval_seconds"
KEY_MOVIE_PROMPTS = "movie_prompts"
KEY_SKIP_PKC = "skip_pkc"
KEY_INDEX_TTL = "index_ttl_minutes"
KEY_DEBUG = "debug_logging"
KEY_RATING_ASK = "rating_ask"
KEY_RATING_WHEN = "rating_when"
KEY_RATING_SHARED = "rating_shared"
KEY_RATING_WRITE_LIBRARY = "rating_write_library"

# The "Ask for a rating" choice, by its position in settings.xml: Off, Films, Episodes, both.
_RATING_KINDS = {1: frozenset({"movie"}), 2: frozenset({"episode"}), 3: frozenset({"movie", "episode"})}


@dataclass(frozen=True)
class Settings:
    webhook_base_url: str = ""
    webhook_token: str = ""
    device_id: str = ""
    device_name: str = ""
    progress_interval_seconds: int = DEFAULT_PROGRESS_INTERVAL_SECONDS
    movie_prompts: bool = True
    skip_pkc: bool = True
    index_ttl_seconds: int = DEFAULT_INDEX_TTL_SECONDS
    debug_logging: bool = False
    rating_kinds: frozenset[str] = frozenset()
    rating_at_end: bool = False
    rating_shared: bool = False
    rating_write_library: bool = False

    def webhook_url(self) -> str | None:
        """The endpoint, never carrying the token. None until both halves are set."""
        if not self.webhook_base_url or not self.webhook_token:
            return None
        return self.webhook_base_url.rstrip("/")


def split_token(url: str) -> tuple[str, str]:
    """A pasted manual-setup URL as the plain endpoint and the token from its query.

    CrossWatch's manual option offers the full URL with ?token=, and the contract has the
    add-on accept that pasted whole. Other query parameters are kept. An empty token means
    there was none to take.
    """
    try:
        parts = urlsplit(url)
        pairs = parse_qsl(parts.query, keep_blank_values=True)
    except ValueError:
        return url, ""
    tokens = [value.strip() for key, value in pairs if key == "token"]
    if not tokens:
        return url, ""
    rest = urlencode([(key, value) for key, value in pairs if key != "token"])
    return urlunsplit(parts._replace(query=rest)), tokens[-1]


def write_back_pasted_url(kodi: KodiApi, settings: Settings) -> bool:
    """Store a token pasted inside the URL in its own setting, and the plain URL. Once.

    The token goes first: each write wakes the service's settings reload, and a URL with the
    token removed but no token stored yet would read as unconfigured. True when it wrote.
    """
    if kodi.setting(KEY_BASE_URL).strip() == settings.webhook_base_url:
        return False
    kodi.set_setting(KEY_TOKEN, settings.webhook_token)
    kodi.set_setting(KEY_BASE_URL, settings.webhook_base_url)
    return True


def _int(kodi: KodiApi, key: str, fallback: int) -> int:
    try:
        return kodi.setting_int(key) or fallback
    except Exception:
        return fallback


def _bool(kodi: KodiApi, key: str, fallback: bool) -> bool:
    try:
        raw = kodi.setting(key)
        return fallback if raw == "" else kodi.setting_bool(key)
    except Exception:
        return fallback


def read_settings(kodi: KodiApi) -> Settings:
    ttl_minutes = _int(kodi, KEY_INDEX_TTL, DEFAULT_INDEX_TTL_SECONDS // 60)
    base_url, pasted_token = split_token(kodi.setting(KEY_BASE_URL).strip())
    return Settings(
        webhook_base_url=base_url,
        # A token pasted with the URL is the newer of the two: the user just put it there.
        webhook_token=pasted_token or kodi.setting(KEY_TOKEN).strip(),
        device_id=kodi.setting(KEY_DEVICE_ID).strip(),
        device_name=kodi.info_label("System.FriendlyName"),
        progress_interval_seconds=_int(kodi, KEY_PROGRESS_INTERVAL, DEFAULT_PROGRESS_INTERVAL_SECONDS),
        movie_prompts=_bool(kodi, KEY_MOVIE_PROMPTS, True),
        skip_pkc=_bool(kodi, KEY_SKIP_PKC, True),
        index_ttl_seconds=ttl_minutes * 60,
        debug_logging=_bool(kodi, KEY_DEBUG, False),
        rating_kinds=_RATING_KINDS.get(_int(kodi, KEY_RATING_ASK, 0), frozenset()),
        rating_at_end=_int(kodi, KEY_RATING_WHEN, 0) == 1,
        rating_shared=_bool(kodi, KEY_RATING_SHARED, False),
        rating_write_library=_bool(kodi, KEY_RATING_WRITE_LIBRARY, False),
    )
