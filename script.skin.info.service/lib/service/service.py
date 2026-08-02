"""Service entry point for script.skin.info.service."""
from __future__ import annotations

import threading

import xbmc

from lib.kodi.client import ADDON, log
from lib.kodi.utilities import clear_prop, set_prop, wait_for_kodi_ready
from lib.kodi.utilities import kodi_build_version

SKIN_BOOL = "SkinInfo.Service"
SKIN_BOOL_LIBRARY = "SkinInfo.Service.Library"
SKIN_BOOL_ONLINE = "SkinInfo.Service.Online"
POLL_INTERVAL = 1.0


class OrchestratorMonitor(xbmc.Monitor):
    """Monitor that flags when addon settings change."""

    def __init__(self) -> None:
        super().__init__()
        self.settings_dirty = True  # force initial evaluation

    def onSettingsChanged(self) -> None:
        from lib.kodi.settings import KodiSettings
        KodiSettings.clear_cache()
        self.settings_dirty = True


class Orchestrator:
    """Manages start/stop of all service threads based on skin bool and settings."""

    def __init__(self, monitor: OrchestratorMonitor) -> None:
        self.monitor = monitor
        self._online_thread = None
        self._library_thread = None
        self._imdb_thread = None
        self._stinger_thread = None

    def run(self) -> None:
        from lib.data.database._infrastructure import init_database
        from lib.data.database.music import init_music_database
        from lib.service.slideshow import SlideshowMonitor

        init_database()
        init_music_database()

        if not wait_for_kodi_ready(self.monitor):
            return

        self._start_housekeeping()

        slideshow_monitor = SlideshowMonitor()

        version = ADDON.getAddonInfo("version")
        kodi_ver = kodi_build_version() or "0.0.0"
        log("Service", f"Orchestrator started (version={version}, kodi={kodi_ver})", xbmc.LOGINFO)

        try:
            while not self.monitor.abortRequested():
                self._evaluate()
                if self.monitor.waitForAbort(POLL_INTERVAL):
                    break
        finally:
            self._stop_all()
            del slideshow_monitor
            log("Service", "Orchestrator stopped", xbmc.LOGINFO)

    def _start_housekeeping(self) -> None:
        """Expired cache cleanup in a daemon thread after startup."""
        def _run() -> None:
            # Delay so services get DB access first; avoids competing for locks during startup
            if self.monitor.waitForAbort(30):
                return
            from lib.data.database.cache import clear_expired_cache
            from lib.data.database.music import clear_expired_music_cache
            clear_expired_cache()
            clear_expired_music_cache()

        threading.Thread(target=_run, daemon=True).start()

    def _evaluate(self) -> None:
        library_enabled = xbmc.getCondVisibility(
            f'Skin.HasSetting({SKIN_BOOL}) | Skin.HasSetting({SKIN_BOOL_LIBRARY})'
        )
        online_enabled = xbmc.getCondVisibility(
            f'Skin.HasSetting({SKIN_BOOL}) | Skin.HasSetting({SKIN_BOOL_ONLINE})'
        )
        self._manage_skin_services(library_enabled, online_enabled)

        if self.monitor.settings_dirty:
            self.monitor.settings_dirty = False
            self._manage_setting_services()

    def _ensure_started(self, attr: str, factory) -> None:
        """Start thread on `self.<attr>` if not running. `factory` returns a new thread instance."""
        thread = getattr(self, attr)
        if thread is None or not thread.is_alive():
            thread = factory()
            setattr(self, attr, thread)
            thread.start()

    def _ensure_stopped(self, attr: str) -> None:
        """Signal abort, join, and clear the thread on `self.<attr>` if running."""
        thread = getattr(self, attr)
        if thread is None:
            return
        thread.abort.set()
        thread.join(timeout=2)
        setattr(self, attr, None)

    def _manage_skin_services(self, library_enabled: bool, online_enabled: bool) -> None:
        """Start/stop the library and online services per their skin bools."""
        if library_enabled:
            from lib.service.library.main import ServiceMain
            self._ensure_started('_library_thread', ServiceMain)
            set_prop("SkinInfo.Service.Library.Running", "true")
        else:
            self._ensure_stopped('_library_thread')
            clear_prop("SkinInfo.Service.Library.Running")

        if online_enabled:
            from lib.service.online import OnlineServiceMain
            self._ensure_started('_online_thread', OnlineServiceMain)
            set_prop("SkinInfo.Service.Online.Running", "true")
        else:
            self._ensure_stopped('_online_thread')
            clear_prop("SkinInfo.Service.Online.Running")

        if library_enabled or online_enabled:
            set_prop("SkinInfo.Service.Running", "true")
        else:
            clear_prop("SkinInfo.Service.Running")

    def _manage_setting_services(self) -> None:
        imdb_enabled = ADDON.getSetting("imdb_auto_update") != "off"
        stinger_enabled = ADDON.getSettingBool("stinger_enabled")

        if imdb_enabled:
            from lib.service.imdb import ImdbUpdateService
            self._ensure_started('_imdb_thread', ImdbUpdateService)
        else:
            self._ensure_stopped('_imdb_thread')

        if stinger_enabled:
            from lib.service.stinger import StingerService
            self._ensure_started('_stinger_thread', StingerService)
        else:
            self._ensure_stopped('_stinger_thread')

    def _stop_all(self) -> None:
        # Signal abort on all threads first so they can shut down in parallel,
        # then join to wait.
        for attr in ('_stinger_thread', '_imdb_thread', '_online_thread', '_library_thread'):
            thread = getattr(self, attr)
            if thread is not None:
                thread.abort.set()
        for attr in ('_stinger_thread', '_imdb_thread', '_online_thread', '_library_thread'):
            self._ensure_stopped(attr)


def main() -> None:
    """Service entry: start the orchestrator until Kodi aborts."""
    monitor = OrchestratorMonitor()
    Orchestrator(monitor).run()


if __name__ == "__main__":
    main()
