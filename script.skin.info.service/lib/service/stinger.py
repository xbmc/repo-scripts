"""Stinger (post-credits scene) detection for movies.

Detects and notifies about post-credits scenes during movie playback.
Uses TMDB keywords as primary source, Trakt as fallback.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, Tuple

import xbmc
import xbmcgui
import xbmcvfs

from lib.kodi.client import log, ADDON, get_item_details, KODI_MOVIE_PROPERTIES
from lib.kodi.utilities import extract_media_ids

# Default icon path (skinners can override via Skin.String)
DEFAULT_STINGER_ICON = xbmcvfs.translatePath(
    "special://home/addons/script.skin.info.service/resources/icons/stinger.png"
)


class StingerType(Enum):
    """Type of post-credits scene."""
    NONE = "none"
    DURING = "during"
    AFTER = "after"
    BOTH = "both"


@dataclass
class StingerInfo:
    """Information about post-credits scenes for a movie."""
    has_during: bool = False
    has_after: bool = False
    source: str = ""

    @property
    def stinger_type(self) -> StingerType:
        """Get the combined stinger type."""
        if self.has_during and self.has_after:
            return StingerType.BOTH
        if self.has_during:
            return StingerType.DURING
        if self.has_after:
            return StingerType.AFTER
        return StingerType.NONE

    @property
    def has_stinger(self) -> bool:
        """Check if any stinger exists."""
        return self.has_during or self.has_after


# TMDB keyword names for stinger detection
TMDB_KEYWORD_DURING = "duringcreditsstinger"
TMDB_KEYWORD_AFTER = "aftercreditsstinger"

# Kodi's fullscreen video window. Stinger properties live here so they're
# accessible during playback, surviving any focus changes in other windows.
FULLSCREEN_VIDEO_WINDOW_ID = 12901


def _skin_override(key: str) -> str:
    """Return `Skin.String(SkinInfo.Stinger.<key>)` if set, else empty string."""
    return xbmc.getInfoLabel(f"Skin.String(SkinInfo.Stinger.{key})") or ""

STR_HEADING = 32162
STR_DURING = 32163
STR_AFTER = 32164
STR_BOTH = 32165


def get_settings() -> Dict[str, Any]:
    """Return stinger settings as `{enabled, minutes_before_end, notification_duration}`."""
    return {
        "enabled": ADDON.getSettingBool("stinger_enabled"),
        "minutes_before_end": ADDON.getSettingInt("stinger_minutes_before_end") or 8,
        "notification_duration": ADDON.getSettingInt("stinger_notification_duration") or 4,
    }


def get_stinger_from_tmdb(ids: Dict[str, Optional[str]]) -> Optional[StingerInfo]:
    """Fetch stinger info from TMDB via cached complete movie data.

    Independent of the online service: fetches directly so stinger detection
    works whether or not the main service is enabled. Uses cached `get_complete_data`,
    so this hits the cache when the online service has already fetched.
    """
    tmdb_id = ids.get("tmdb")
    if not tmdb_id:
        return None

    try:
        from lib.data.api.tmdb import ApiTmdb
        api = ApiTmdb()
        data = api.get_complete_data("movie", int(tmdb_id))
    except Exception as e:
        log("Service", f"TMDB stinger fetch error: {e}", xbmc.LOGDEBUG)
        return None

    if not data:
        return None

    keywords = data.get("keywords") or {}
    keyword_list = keywords.get("keywords") or []
    if not keyword_list:
        return None

    keyword_names = {kw.get("name", "").lower() for kw in keyword_list if isinstance(kw, dict)}
    has_during = TMDB_KEYWORD_DURING in keyword_names
    has_after = TMDB_KEYWORD_AFTER in keyword_names

    if has_during or has_after:
        return StingerInfo(has_during=has_during, has_after=has_after, source="tmdb")

    return None


def get_stinger_from_trakt(ids: Dict[str, Optional[str]]) -> Optional[StingerInfo]:
    """Fetch stinger info from Trakt for a movie identified by IMDb/TMDB/Trakt-slug IDs."""
    from lib.data.api.trakt import ApiTrakt

    # Filter out None values for Trakt API
    clean_ids = {k: v for k, v in ids.items() if v is not None}
    if not clean_ids:
        return None

    trakt = ApiTrakt()
    data = trakt.fetch_data("movie", clean_ids)

    if not data:
        return None

    has_during = data.get("during_credits", False)
    has_after = data.get("after_credits", False)

    if has_during or has_after:
        return StingerInfo(has_during=has_during, has_after=has_after, source="trakt")

    return None


def get_stinger_from_kodi_tags(movie_details: Dict[str, Any]) -> Optional[StingerInfo]:
    """Check Kodi library tags for stinger keywords."""
    tags = movie_details.get("tag", [])
    if not tags:
        return None

    tag_names = {t.lower() for t in tags if isinstance(t, str)}

    has_during = TMDB_KEYWORD_DURING in tag_names
    has_after = TMDB_KEYWORD_AFTER in tag_names

    if has_during or has_after:
        return StingerInfo(has_during=has_during, has_after=has_after, source="kodi_tags")

    return None


def get_stinger_info(ids: Optional[Dict[str, Optional[str]]] = None,
                     movie_details: Optional[Dict[str, Any]] = None
                     ) -> Optional[StingerInfo]:
    """Check stinger sources in order: TMDB, Kodi library tags, Trakt."""
    if ids:
        info = get_stinger_from_tmdb(ids)
        if info:
            log("Service", f"Stinger info from TMDB: {info.stinger_type.value}", xbmc.LOGDEBUG)
            return info

    if movie_details:
        info = get_stinger_from_kodi_tags(movie_details)
        if info:
            log("Service", f"Stinger info from Kodi tags: {info.stinger_type.value}", xbmc.LOGDEBUG)
            return info

    if ids:
        info = get_stinger_from_trakt(ids)
        if info:
            log("Service", f"Stinger info from Trakt: {info.stinger_type.value}", xbmc.LOGDEBUG)
            return info

    return None


def set_stinger_properties(
        info: Optional[StingerInfo], window_id: int = FULLSCREEN_VIDEO_WINDOW_ID) -> None:
    """Set `SkinInfo.Stinger.*` on `window_id`. Pass `info=None` to clear.

    Properties: `HasDuring`, `HasAfter`, `Type` (during/after/both/none),
    `Source` (tmdb/trakt/kodi_tags).
    """
    window = xbmcgui.Window(window_id)

    if info and info.has_stinger:
        window.setProperty("SkinInfo.Stinger.HasDuring", "true" if info.has_during else "")
        window.setProperty("SkinInfo.Stinger.HasAfter", "true" if info.has_after else "")
        window.setProperty("SkinInfo.Stinger.Type", info.stinger_type.value)
        window.setProperty("SkinInfo.Stinger.Source", info.source)
    else:
        window.clearProperty("SkinInfo.Stinger.HasDuring")
        window.clearProperty("SkinInfo.Stinger.HasAfter")
        window.clearProperty("SkinInfo.Stinger.Type")
        window.clearProperty("SkinInfo.Stinger.Source")


def clear_stinger_properties(window_id: int = FULLSCREEN_VIDEO_WINDOW_ID) -> None:
    """Clear all stinger properties from window."""
    set_stinger_properties(None, window_id)


def set_notify_property(show: bool, window_id: int = FULLSCREEN_VIDEO_WINDOW_ID) -> None:
    """Set the ShowNotify property to trigger skin notification display."""
    window = xbmcgui.Window(window_id)
    if show:
        window.setProperty("SkinInfo.Stinger.ShowNotify", "true")
    else:
        window.clearProperty("SkinInfo.Stinger.ShowNotify")


def _get_notification_icon() -> str:
    """Icon path; honors `Skin.String(SkinInfo.Stinger.NotificationIcon)` override else default."""
    skin_icon = _skin_override("NotificationIcon")
    if skin_icon and xbmcvfs.exists(skin_icon):
        return skin_icon

    if xbmcvfs.exists(DEFAULT_STINGER_ICON):
        return DEFAULT_STINGER_ICON

    return ""


def _get_notification_text(stinger_type: StingerType) -> Tuple[str, str]:
    """Get notification heading and message, checking skin overrides first.

    Skinners can override via:
    - Skin.String(SkinInfo.Stinger.Heading)
    - Skin.String(SkinInfo.Stinger.MessageDuring)
    - Skin.String(SkinInfo.Stinger.MessageAfter)
    - Skin.String(SkinInfo.Stinger.MessageBoth)
    """
    heading = _skin_override("Heading") or ADDON.getLocalizedString(STR_HEADING)

    type_to_string_id = {
        StingerType.BOTH: ("MessageBoth", STR_BOTH),
        StingerType.DURING: ("MessageDuring", STR_DURING),
        StingerType.AFTER: ("MessageAfter", STR_AFTER),
    }
    override_key, default_id = type_to_string_id.get(stinger_type, ("", 0))
    if override_key:
        message = _skin_override(override_key) or ADDON.getLocalizedString(default_id)
    else:
        message = ""

    return heading, message


def _skin_handles_notification() -> bool:
    """Check if skin has opted in to handle stinger notifications.

    Skins can opt in by setting: Skin.SetBool(SkinInfo.Stinger.CustomNotification)

    When opted in, the addon skips Dialog().notification() and the skin
    handles display using window properties (SkinInfo.Stinger.ShowNotify, etc).
    """
    return xbmc.getCondVisibility("Skin.HasSetting(SkinInfo.Stinger.CustomNotification)")


def show_notification(info: StingerInfo, duration_seconds: int = 4) -> None:
    """Show Kodi notification for stinger.

    If skin has opted in via Skin.SetBool(SkinInfo.Stinger.CustomNotification),
    skips Kodi notification and relies on skin to display using properties.

    Otherwise, skinners can customize the Kodi notification via Skin.String:
    - SkinInfo.Stinger.NotificationIcon: Custom icon path
    - SkinInfo.Stinger.Heading: Custom heading text
    - SkinInfo.Stinger.MessageDuring: Custom message for during-credits scene
    - SkinInfo.Stinger.MessageAfter: Custom message for after-credits scene
    - SkinInfo.Stinger.MessageBoth: Custom message for both types
    """
    if info.stinger_type == StingerType.NONE:
        return

    # Skin handles its own notification display
    if _skin_handles_notification():
        log("Service", "Skin handles stinger notification, skipping Kodi dialog", xbmc.LOGDEBUG)
        return

    heading, message = _get_notification_text(info.stinger_type)
    if not message:
        return

    icon = _get_notification_icon()

    xbmcgui.Dialog().notification(
        heading,
        message,
        icon if icon else xbmcgui.NOTIFICATION_INFO,
        duration_seconds * 1000
    )


def is_near_credits(minutes_before_end: int = 8) -> bool:
    """Check if playback is near the end (credits).

    Uses chapter detection combined with time-based check. If chapters exist,
    requires both last chapter AND within configured minutes of end.
    """
    on_last_chapter = False
    has_chapters = False
    try:
        chapter_count_str = xbmc.getInfoLabel("Player.ChapterCount")
        if chapter_count_str:
            chapter_count = int(chapter_count_str)
            if chapter_count > 1:
                has_chapters = True
                current_chapter_str = xbmc.getInfoLabel("Player.Chapter")
                if current_chapter_str:
                    on_last_chapter = int(current_chapter_str) == chapter_count
    except (ValueError, TypeError):
        pass

    # Not on last chapter yet, no need to check time
    if has_chapters and not on_last_chapter:
        return False

    player = xbmc.Player()
    if not player.isPlayingVideo():
        return False

    try:
        total_time = player.getTotalTime()
        current_time = player.getTime()

        if total_time <= 0:
            return False

        time_remaining_minutes = (total_time - current_time) / 60
        return time_remaining_minutes < minutes_before_end
    except Exception as e:
        log("Service", f"Error checking playback position: {e}", xbmc.LOGDEBUG)
        return False


class StingerMonitor:
    """Monitors playback for stinger notification timing."""

    def __init__(self):
        self.current_movie_id: Optional[str] = None
        self.stinger_info: Optional[StingerInfo] = None
        self.notified: bool = False
        self._settings: Optional[Dict[str, Any]] = None

    def reset(self) -> None:
        """Reset state for new playback."""
        self.current_movie_id = None
        self.stinger_info = None
        self.notified = False
        self._settings = None
        clear_stinger_properties()
        set_notify_property(False)

    @property
    def settings(self) -> Dict[str, Any]:
        """Get cached settings."""
        if self._settings is None:
            self._settings = get_settings()
        return self._settings

    def on_playback_start(
        self,
        movie_id: str,
        ids: Optional[Dict[str, Optional[str]]] = None,
        movie_details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Handle movie playback start. Resolves stinger info via TMDB/Kodi tags/Trakt."""
        if not self.settings["enabled"]:
            return

        if movie_id == self.current_movie_id:
            return

        self.reset()
        self.current_movie_id = movie_id

        self.stinger_info = get_stinger_info(ids=ids, movie_details=movie_details)

        if self.stinger_info and self.stinger_info.has_stinger:
            set_stinger_properties(self.stinger_info)
            log("Service",
                f"Stinger detected (fallback): {self.stinger_info.stinger_type.value}",
                xbmc.LOGDEBUG)

    def check_notification(self) -> None:
        """Check if notification should be shown based on playback position."""
        if not self.settings["enabled"]:
            return

        if self.notified:
            return

        if not self.stinger_info or not self.stinger_info.has_stinger:
            return

        if not is_near_credits(self.settings["minutes_before_end"]):
            return

        self.notified = True
        set_notify_property(True)
        show_notification(self.stinger_info, self.settings["notification_duration"])

    def on_playback_stop(self) -> None:
        """Handle playback stop."""
        self.reset()


class StingerService(threading.Thread):
    """Polls every 5s during movie playback to detect post-credits scenes."""

    def __init__(self):
        super().__init__(daemon=True)
        self.abort = threading.Event()

    def run(self) -> None:
        """Service thread entry. Polls every 5s for movie playback + stinger detection."""
        monitor = xbmc.Monitor()
        log("Service", "Stinger service started", xbmc.LOGINFO)

        stinger = StingerMonitor()
        current_dbid: Optional[str] = None
        fetched = False

        while not monitor.waitForAbort(5):
            if self.abort.is_set():
                break

            movie_playing = (
                get_settings()["enabled"]
                and xbmc.getCondVisibility("Player.HasVideo")
                and xbmc.getCondVisibility("VideoPlayer.Content(movies)")
            )

            if not movie_playing:
                if current_dbid:
                    stinger.on_playback_stop()
                    current_dbid = None
                    fetched = False
                continue

            dbid = xbmc.getInfoLabel("VideoPlayer.DBID") or ""
            if not dbid or dbid == "-1":
                continue

            if dbid != current_dbid:
                if current_dbid:
                    stinger.reset()
                current_dbid = dbid
                fetched = False
                continue

            if not fetched:
                self._fetch_stinger_info(stinger, dbid)
                fetched = True

            stinger.check_notification()

        stinger.reset()
        log("Service", "Stinger service stopped", xbmc.LOGINFO)

    def _fetch_stinger_info(self, stinger: StingerMonitor, dbid: str) -> None:
        details = get_item_details(
            'movie',
            int(dbid),
            KODI_MOVIE_PROPERTIES,
            cache_key=f"player:movie:{dbid}:details",
        )
        if not isinstance(details, dict):
            return

        ids = extract_media_ids(details)
        stinger.on_playback_start(movie_id=dbid, ids=ids, movie_details=details)
