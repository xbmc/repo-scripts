"""Post-credits scene detection and notice for the playing movie, from TMDB, tags or Trakt."""
from __future__ import annotations

import threading
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, Tuple, Final

import xbmc
import xbmcgui
import xbmcvfs

from lib.kodi.client import log, ADDON, get_item_details, KODI_MOVIE_PROPERTIES
from lib.kodi.utilities import extract_media_ids
from lib.infrastructure.tasks import ServiceAbortFlag

# a skin can override it through Skin.String
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


TMDB_KEYWORD_DURING: Final = "duringcreditsstinger"
TMDB_KEYWORD_AFTER: Final = "aftercreditsstinger"

# fullscreen video window, so the properties survive focus changes elsewhere
FULLSCREEN_VIDEO_WINDOW_ID: Final = 12901


def _skin_override(key: str) -> str:
    """Return `Skin.String(SkinInfo.Stinger.<key>)` if set, else empty string."""
    return xbmc.getInfoLabel(f"Skin.String(SkinInfo.Stinger.{key})") or ""


STR_HEADING: Final = 32162
STR_DURING: Final = 32163
STR_AFTER: Final = 32164
STR_BOTH: Final = 32165


def get_stinger_settings() -> Dict[str, Any]:
    """Return stinger settings as `{enabled, minutes_before_end, notification_duration}`."""
    return {
        "enabled": ADDON.getSettingBool("stinger_enabled"),
        "minutes_before_end": ADDON.getSettingInt("stinger_minutes_before_end") or 8,
        "notification_duration": ADDON.getSettingInt("stinger_notification_duration") or 4,
    }


def get_stinger_from_tmdb(ids: Dict[str, Optional[str]],
                          abort_flag=None) -> Tuple[Optional[StingerInfo], bool]:
    """Fetch stinger info from fresh TMDB keywords, cached ones on a failed fetch; True if fresh."""
    tmdb_id = ids.get("tmdb")
    if not tmdb_id:
        return None, True

    from lib.data.api.tmdb import ApiTmdb
    from lib.data.database.cache import get_cached_metadata
    try:
        data = ApiTmdb().get_complete_data("movie", int(tmdb_id), abort_flag=abort_flag,
                                           force_refresh=True)
    except Exception as e:
        log("Service", f"TMDB stinger fetch error: {e}", xbmc.LOGDEBUG)
        data = None

    fresh = data is not None
    if not fresh:
        data = get_cached_metadata("movie", str(tmdb_id))
    if not data:
        return None, fresh

    keywords = data.get("keywords") or {}
    keyword_list = keywords.get("keywords") or []
    if not keyword_list:
        return None, fresh

    keyword_names = {kw.get("name", "").lower() for kw in keyword_list if isinstance(kw, dict)}
    has_during = TMDB_KEYWORD_DURING in keyword_names
    has_after = TMDB_KEYWORD_AFTER in keyword_names

    if has_during or has_after:
        return StingerInfo(has_during=has_during, has_after=has_after, source="tmdb"), fresh

    return None, fresh


def get_stinger_from_trakt(ids: Dict[str, Optional[str]], abort_flag=None) -> Optional[StingerInfo]:
    """Fetch stinger info from fresh Trakt data, the cached copy when the fetch fails."""
    from lib.data.api.trakt import ApiTrakt

    clean_ids = {k: v for k, v in ids.items() if v is not None}
    if not clean_ids:
        return None

    trakt = ApiTrakt()
    data = trakt.fetch_data("movie", clean_ids, abort_flag, force_refresh=True)
    if not data:
        data = trakt.get_trakt_data("movie", clean_ids)

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
                     movie_details: Optional[Dict[str, Any]] = None,
                     abort_flag=None) -> Tuple[Optional[StingerInfo], bool]:
    """Check stinger sources in order: TMDB, Kodi library tags, Trakt; True if TMDB was fresh."""
    fresh = True
    if ids:
        info, fresh = get_stinger_from_tmdb(ids, abort_flag)
        if info:
            log("Service", f"Stinger info from TMDB: {info.stinger_type.value}", xbmc.LOGDEBUG)
            return info, fresh

    if movie_details:
        info = get_stinger_from_kodi_tags(movie_details)
        if info:
            log("Service", f"Stinger info from Kodi tags: {info.stinger_type.value}", xbmc.LOGDEBUG)
            return info, fresh

    if ids:
        info = get_stinger_from_trakt(ids, abort_flag)
        if info:
            log("Service", f"Stinger info from Trakt: {info.stinger_type.value}", xbmc.LOGDEBUG)
            return info, fresh

    return None, fresh


def set_stinger_properties(
        info: Optional[StingerInfo], window_id: int = FULLSCREEN_VIDEO_WINDOW_ID) -> None:
    """Set `SkinInfo.Stinger.*` on the window, or clear them when there is no stinger."""
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
    """Get the notification heading and message, the skin's `SkinInfo.Stinger.*` strings first."""
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
    """True when the skin sets `SkinInfo.Stinger.CustomNotification` to show its own notice."""
    return xbmc.getCondVisibility("Skin.HasSetting(SkinInfo.Stinger.CustomNotification)")


def show_notification(info: StingerInfo, duration_seconds: int = 4) -> None:
    """Show Kodi's notification for the stinger, unless the skin shows its own."""
    if info.stinger_type == StingerType.NONE:
        return

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
    """True within the set minutes of the end, and on the last chapter when there are chapters."""
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


class StingerTracker:
    """Tracks movie playback to time the stinger notification."""

    def __init__(self):
        self.current_movie_id: Optional[str] = None
        self.stinger_info: Optional[StingerInfo] = None
        self.notified: bool = False
        self._settings: Optional[Dict[str, Any]] = None
        self._ids: Optional[Dict[str, Optional[str]]] = None
        self._details: Optional[Dict[str, Any]] = None
        self._stale: bool = False

    def reset(self) -> None:
        """Reset state for new playback."""
        self.current_movie_id = None
        self.stinger_info = None
        self.notified = False
        self._settings = None
        self._ids = None
        self._details = None
        self._stale = False
        clear_stinger_properties()
        set_notify_property(False)

    @property
    def settings(self) -> Dict[str, Any]:
        """Get cached settings."""
        if self._settings is None:
            self._settings = get_stinger_settings()
        return self._settings

    def on_playback_start(
        self,
        movie_id: str,
        ids: Optional[Dict[str, Optional[str]]] = None,
        movie_details: Optional[Dict[str, Any]] = None,
        abort_flag=None,
    ) -> None:
        """Handle movie playback start. Resolves stinger info via TMDB/Kodi tags/Trakt."""
        if not self.settings["enabled"]:
            return

        if movie_id == self.current_movie_id:
            return

        self.reset()
        self.current_movie_id = movie_id
        self._ids = ids
        self._details = movie_details
        self._resolve(abort_flag)

    def retry_if_stale(self, abort_flag=None) -> None:
        """Retry the lookup while TMDB has not answered fresh and the notice has not shown."""
        if self._stale and self.current_movie_id and not self.notified:
            self._resolve(abort_flag)

    def _resolve(self, abort_flag) -> None:
        """Look the stinger up and publish the result, from cache until TMDB answers fresh."""
        info, fresh = get_stinger_info(ids=self._ids, movie_details=self._details,
                                       abort_flag=abort_flag)
        self._stale = not fresh
        self.stinger_info = info

        if info and info.has_stinger:
            set_stinger_properties(info)
            log("Service", f"Stinger detected: {info.stinger_type.value}", xbmc.LOGDEBUG)
        else:
            clear_stinger_properties()

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

        stinger = StingerTracker()
        abort_flag = ServiceAbortFlag(self.abort)
        current_dbid: Optional[str] = None
        fetched = False

        while not monitor.waitForAbort(5):
            if self.abort.is_set():
                break

            movie_playing = (
                get_stinger_settings()["enabled"]
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
                self._fetch_stinger_info(stinger, dbid, abort_flag)
                fetched = True
            else:
                stinger.retry_if_stale(abort_flag)

            stinger.check_notification()

        stinger.reset()
        log("Service", "Stinger service stopped", xbmc.LOGINFO)

    def _fetch_stinger_info(self, stinger: StingerTracker, dbid: str, abort_flag) -> None:
        """Fetch the playing movie's details for the stinger lookup."""
        details = get_item_details(
            'movie',
            int(dbid),
            KODI_MOVIE_PROPERTIES,
            cache_key=f"movie:{dbid}:details",
        )
        if not isinstance(details, dict):
            return

        ids = extract_media_ids(details)
        stinger.on_playback_start(movie_id=dbid, ids=ids, movie_details=details,
                                  abort_flag=abort_flag)
