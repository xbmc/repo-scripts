"""SkinInfo background service for property updates.

Coordinator for the library-focus service. Composes per-concern handlers
(refresh, blur, player, music_player, musicvideo, slideshow, focus) and
runs the main loop.
"""
from __future__ import annotations

import threading

import xbmc

from lib.kodi.client import log
from lib.service.library.refresh import RefreshTracker
from lib.service.library.blur import BlurHandler
from lib.service.library.player import PlayerVideoTracker, PlayerMusicTracker
from lib.service.library.musicvideo import MusicVideoArt
from lib.service.library.slideshow import SlideshowDriver
from lib.service.library.focus import FocusDispatcher

SERVICE_POLL_INTERVAL = 0.10
MAX_CONSECUTIVE_ERRORS = 10


class LibraryMonitor(xbmc.Monitor):
    """Routes Kodi library/audio notifications to the appropriate handler on `service_main`."""

    def __init__(self, service_main: 'ServiceMain'):
        super().__init__()
        self.service_main = service_main

    def onNotification(self, sender: str, method: str, data: str) -> None:
        """Route Kodi library/audio notifications to the matching handler."""
        if method in ('VideoLibrary.OnUpdate', 'VideoLibrary.OnScanFinished'):
            self.service_main.refresh.increment()
        if method == 'VideoLibrary.OnUpdate':
            self.service_main.focus.invalidate_asset_view()
            self._on_video_update(data)
        if method == 'Player.OnAVStop':
            self.service_main.focus.invalidate_asset_view()
        if method in ('AudioLibrary.OnUpdate', 'AudioLibrary.OnScanFinished',
                      'AudioLibrary.OnCleanFinished'):
            from lib.plugin.dbid import clear_musicvideo_library_art_cache
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
    def _sync_dbids() -> None:
        from lib.data.database.rollcall import sync_dbids
        sync_dbids()

    @staticmethod
    def _on_video_remove(data: str) -> None:
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
        if media_type == 'tvshow':
            from lib.data.database.runtime import invalidate_show_runtime
            invalidate_show_runtime(int(dbid))

    def _on_video_update(self, data: str) -> None:
        try:
            import json
            info = json.loads(data)
        except Exception:
            return
        if 'playcount' in info:
            return
        media_type = info.get('type', '')
        dbid = info.get('id')
        if not dbid:
            return
        if media_type == 'musicvideo':
            self.service_main.musicvideo.invalidate_for(int(dbid))
        elif media_type in ('movie', 'tvshow', 'episode'):
            from lib.service.online import invalidate_online_cache_for_dbid
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
        """One service tick: player blur, video/audio player tracking, focus dispatch."""
        self.blur.handle_player()
        self.player.handle()
        self.music_player.handle()
        self.focus.process()

    def _clear_media_type(self, media_type: str) -> None:
        """Compatibility shim that delegates to the focus dispatcher."""
        self.focus.clear_media_type(media_type)
