"""Service entry point for script.skin.info.service."""
from __future__ import annotations

import threading
from typing import Final

import xbmc

from lib.kodi.client import ADDON, log
from lib.kodi.utilities import clear_prop, set_prop, wait_for_kodi_ready, skin_bool
from lib.kodi.utilities import kodi_build_version

SKIN_BOOL: Final = "SkinInfo.Service"
SKIN_BOOL_LIBRARY: Final = "SkinInfo.Service.Library"
SKIN_BOOL_ONLINE: Final = "SkinInfo.Service.Online"
POLL_INTERVAL: Final = 1.0
_CLEANUP_INTERVAL: Final = 24 * 3600


class OrchestratorMonitor(xbmc.Monitor):
    """Monitor that flags when addon settings change."""

    def __init__(self) -> None:
        super().__init__()
        self.settings_dirty = True  # force initial evaluation

    def onSettingsChanged(self) -> None:
        """Drop the cached settings and flag them for re-evaluation."""
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
        self._top250_thread = None
        self._stinger_thread = None

    def run(self) -> None:
        """Run the service orchestrator until Kodi aborts, then stop everything it started."""
        from lib.data.database._infrastructure import init_database
        from lib.service.slideshow import SlideshowMonitor

        init_database()

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
            from lib.data.database._infrastructure import close_connections
            close_connections()
            log("Service", "Orchestrator stopped", xbmc.LOGINFO)

    def _start_housekeeping(self) -> None:
        """Start housekeeping 30s in: a first DBID sync, then daily cleanup and an awards check."""
        def _refresh_awards() -> None:
            from lib.data.api.awards import refresh_awards_file
            from lib.infrastructure.tasks import ShutdownAbortFlag
            try:
                if refresh_awards_file(ShutdownAbortFlag()):
                    from lib.data.awards import forget
                    forget()
            except Exception as e:
                log("Service", f"Awards check stopped: {e}", xbmc.LOGDEBUG)

        def _run() -> None:
            # the services get the database first
            if self.monitor.waitForAbort(30):
                return
            from lib.data.database.cache import clear_expired_cache
            from lib.data.database.rollcall import needs_id_backfill, sync_dbids
            from lib.infrastructure.tasks import ShutdownAbortFlag
            clear_expired_cache()
            if self.monitor.abortRequested():
                return
            if needs_id_backfill():
                sync_dbids(ShutdownAbortFlag())
            _refresh_awards()
            while not self.monitor.waitForAbort(_CLEANUP_INTERVAL):
                clear_expired_cache()
                _refresh_awards()

        threading.Thread(target=_run, daemon=True).start()

    def _evaluate(self) -> None:
        """Start or stop each sub-service to match the skin bools and settings."""
        any_enabled = skin_bool(SKIN_BOOL)
        library_enabled = any_enabled or skin_bool(SKIN_BOOL_LIBRARY)
        online_enabled = any_enabled or skin_bool(SKIN_BOOL_ONLINE)
        self._manage_skin_services(library_enabled, online_enabled)

        if self.monitor.settings_dirty:
            self.monitor.settings_dirty = False
            self._manage_setting_services()

    def _ensure_started(self, attr: str, factory) -> None:
        """Start a service thread unless the one in that slot is still running."""
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
        if thread.is_alive():
            log("Service", f"{type(thread).__name__} still running after abort", xbmc.LOGWARNING)
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
            from lib.service.online.main import OnlineServiceMain
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
        """Start or stop the services that only settings control."""
        imdb_enabled = ADDON.getSetting("imdb_auto_update") != "off"
        top250_enabled = ADDON.getSetting("top250_auto_update") not in ("", "off")
        stinger_enabled = ADDON.getSettingBool("stinger_enabled")

        if imdb_enabled:
            from lib.service.imdb import ImdbUpdateService
            self._ensure_started('_imdb_thread', ImdbUpdateService)
        else:
            self._ensure_stopped('_imdb_thread')

        if top250_enabled:
            from lib.service.top250 import Top250UpdateService
            self._ensure_started('_top250_thread', Top250UpdateService)
        else:
            self._ensure_stopped('_top250_thread')

        if stinger_enabled:
            from lib.service.stinger import StingerService
            self._ensure_started('_stinger_thread', StingerService)
        else:
            self._ensure_stopped('_stinger_thread')

    def _stop_all(self) -> None:
        """Abort every service thread, then wait for them all."""
        attrs = ('_stinger_thread', '_top250_thread', '_imdb_thread',
                 '_online_thread', '_library_thread')
        for attr in attrs:
            thread = getattr(self, attr)
            if thread is not None:
                thread.abort.set()
        for attr in attrs:
            self._ensure_stopped(attr)


def main() -> None:
    """Service entry: start the orchestrator until Kodi aborts."""
    monitor = OrchestratorMonitor()
    Orchestrator(monitor).run()


if __name__ == "__main__":
    main()
