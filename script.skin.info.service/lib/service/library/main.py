"""Library service: the poll loop over the focus, player, blur, slideshow and refresh handlers."""
from __future__ import annotations

import threading
from typing import Final

import xbmc

from lib.kodi.client import log
from lib.kodi.utilities import LabelSnapshot
from lib.service.library.refresh import RefreshTracker
from lib.service.library.blur import SKIN_BOOL_LABELS, BlurHandler, ImageColorHandler
from lib.service.library.player import PlayerVideoTracker, PlayerMusicTracker
from lib.service.library.musicvideo import MusicVideoArt
from lib.service.library.slideshow import SlideshowDriver
from lib.service.library.focus import FOCUS_LABELS, FocusDispatcher

SERVICE_POLL_INTERVAL: Final = 0.10
MAX_CONSECUTIVE_ERRORS: Final = 10
LIBRARY_REFRESH_EVENTS: Final = ('VideoLibrary.OnUpdate', 'VideoLibrary.OnRemove',
                                 'VideoLibrary.OnRefresh', 'VideoLibrary.OnScanFinished',
                                 'VideoLibrary.OnCleanFinished')


class LibraryMonitor(xbmc.Monitor):
    """Routes Kodi library/audio notifications to the appropriate handler on `service_main`."""

    def __init__(self, service_main: 'ServiceMain'):
        super().__init__()
        self.service_main = service_main

    def onNotification(self, sender: str, method: str, data: str) -> None:
        """Route Kodi library/audio notifications to the matching handler."""
        if method in LIBRARY_REFRESH_EVENTS and not self._in_transaction(data):
            self.service_main.refresh.increment()
        if method == 'VideoLibrary.OnUpdate':
            self.service_main.focus.invalidate_asset_view()
            self._on_video_update(data)
        if method == 'Player.OnAVStop':
            self.service_main.focus.invalidate_asset_view()
        if method in ('AudioLibrary.OnUpdate', 'AudioLibrary.OnScanFinished',
                      'AudioLibrary.OnCleanFinished'):
            from lib.kodi.library import clear_musicvideo_library_art_cache
            clear_musicvideo_library_art_cache()
        if method == 'VideoLibrary.OnRemove':
            self._on_video_remove(data)
        if method in ('VideoLibrary.OnScanFinished', 'VideoLibrary.OnCleanFinished',
                      'AudioLibrary.OnScanFinished', 'AudioLibrary.OnCleanFinished'):
            threading.Thread(target=self._sync_dbids, daemon=True).start()
            self.service_main.slideshow.invalidate_playlists()
        if method in ('VideoLibrary.OnScanFinished', 'VideoLibrary.OnCleanFinished'):
            from lib.data.database.runtime import clear_all_runtime_cache
            clear_all_runtime_cache()

    @staticmethod
    def _in_transaction(data: str) -> bool:
        """True when Kodi sent the notification mid-scan or mid-clean."""
        try:
            import json
            return bool(json.loads(data).get('transaction'))
        except Exception:
            return False

    @staticmethod
    def _sync_dbids() -> None:
        """Sync the DBID registry off the notification thread."""
        from lib.data.database.rollcall import sync_dbids
        from lib.infrastructure.tasks import ShutdownAbortFlag
        sync_dbids(ShutdownAbortFlag())

    @staticmethod
    def _on_video_remove(data: str) -> None:
        """Drop cached data for an item removed from the library."""
        try:
            import json
            info = json.loads(data)
        except Exception:
            return
        media_type = info.get('type', '')
        dbid = info.get('id')
        if not media_type or not dbid:
            return
        from lib.data.database.rollcall import remove_dbid
        remove_dbid(media_type, dbid)
        if media_type in ('episode', 'tvshow'):
            from lib.kodi.library import forget_watch_minutes
            forget_watch_minutes(int(dbid) if media_type == 'tvshow' else None)
        if media_type == 'tvshow':
            from lib.data.database.runtime import invalidate_show_runtime
            invalidate_show_runtime(int(dbid))

    def _on_video_update(self, data: str) -> None:
        """Invalidate cached data for an updated item; a playcount-only change stops early."""
        try:
            import json
            info = json.loads(data)
        except Exception:
            return
        # playback and playcount updates nest the id and type under "item"
        item = info.get('item') or info
        media_type = item.get('type', '')
        dbid = item.get('id')
        if not dbid:
            return
        if media_type == 'episode' and ('playcount' in info or 'item' not in info):
            from lib.kodi.client import get_item_details
            from lib.kodi.library import forget_watch_minutes, watch_minutes_cached
            tvshowid = None
            if watch_minutes_cached():
                episode = get_item_details('episode', int(dbid), ['tvshowid'])
                tvshowid = episode.get('tvshowid') if isinstance(episode, dict) else None
            forget_watch_minutes(tvshowid if tvshowid and tvshowid > 0 else None)
        self.service_main.focus.invalidate_item(media_type, dbid)
        if 'playcount' in info or 'item' in info:
            return
        if media_type == 'musicvideo':
            self.service_main.musicvideo.invalidate_for(int(dbid))
        elif media_type in ('movie', 'tvshow', 'episode'):
            from lib.service.online.helpers import invalidate_online_cache_for_dbid
            invalidate_online_cache_for_dbid(media_type, str(dbid))
            if media_type == 'tvshow':
                from lib.data.database.runtime import invalidate_show_runtime
                invalidate_show_runtime(int(dbid))


class ServiceMain(threading.Thread):
    """Library service coordinator. Runs the main poll loop and composes handlers."""

    def __init__(self):
        super().__init__(daemon=True)
        self.abort = threading.Event()
        self.refresh = RefreshTracker()
        self.blur = BlurHandler()
        self.color = ImageColorHandler()
        self.player = PlayerVideoTracker(self)
        self.music_player = PlayerMusicTracker()
        self.musicvideo = MusicVideoArt()
        self.slideshow = SlideshowDriver()
        self.focus = FocusDispatcher(self)

    def run(self) -> None:
        """Service thread entry. Polls every 100ms; halts after too many consecutive errors."""
        monitor = LibraryMonitor(self)
        log("Service", "Library service started", xbmc.LOGINFO)

        self.slideshow.populate_pool_if_needed()
        self.slideshow.update()

        consecutive_errors = 0

        try:
            while not monitor.waitForAbort(SERVICE_POLL_INTERVAL):
                if self.abort.is_set():
                    break
                try:
                    self._loop()
                    self.slideshow.update()
                    self.slideshow.reconcile_if_idle()
                    self.refresh.tick()
                    consecutive_errors = 0
                except (KeyError, ValueError, TypeError) as e:
                    log("Service", f"Data error in service loop: {e}", xbmc.LOGDEBUG)
                    consecutive_errors += 1
                except Exception as e:
                    import traceback
                    log("Service", f"Unexpected error in service loop: {str(e)}", xbmc.LOGERROR)
                    log("Service", traceback.format_exc(), xbmc.LOGERROR)
                    consecutive_errors += 1

                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    log(
                        "Service",
                        f"Too many consecutive errors ({MAX_CONSECUTIVE_ERRORS}), stopping service",
                        xbmc.LOGERROR,
                    )
                    break
        finally:
            self.slideshow.cleanup()
            log("Service", "Library service stopped", xbmc.LOGINFO)

    def _loop(self) -> None:
        """One service tick: player blur, video/audio player tracking, focus, image color."""
        labels = LabelSnapshot((*FOCUS_LABELS, *SKIN_BOOL_LABELS, *self.blur.focus_labels(),
                                *self.color.focus_labels()))
        self.blur.handle_player(labels)
        self.player.handle()
        self.music_player.handle()
        self.focus.process(labels)
        self.color.handle_focus(labels)
