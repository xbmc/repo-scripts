"""Kodi-Sendspin service loop."""

import xbmc
import xbmcaddon

import kodi_bridge


class Monitor(xbmc.Monitor):
    def __init__(self):
        super().__init__()
        self.settings_changed = False

    def onSettingsChanged(self):  # noqa: N802
        self.settings_changed = True


REDISCOVER_AFTER_S = 120  # a discovered server unreachable this long: look for it again


def run():
    monitor = Monitor()
    told_missing = False
    while not monitor.abortRequested():
        addon = xbmcaddon.Addon()
        kodi_bridge.ADDON = addon
        kodi_bridge.setup_logging(addon.getSettingBool("debug"))
        bridge = None
        discovered = not addon.getSettingString("server_url").strip()
        if addon.getSettingBool("enabled"):
            url = kodi_bridge.resolve_server_url()
            if url:
                told_missing = False
                bridge = kodi_bridge.Bridge()
                bridge.start(url)
            elif not told_missing:  # once, not on every retry
                told_missing = True
                kodi_bridge.notify(kodi_bridge.L(30201), 8000)
        monitor.settings_changed = False
        retry_at = 60  # re-run discovery every minute if nothing was found
        offline_s = 0
        while not monitor.abortRequested() and not monitor.settings_changed:
            if monitor.waitForAbort(1):
                break
            if bridge is not None:
                try:
                    bridge.tick()
                except Exception:  # noqa: BLE001 - never let the service loop die
                    kodi_bridge.log.exception("tick failed")
                # Music Assistant may have moved (restart, new DHCP lease): discover it again
                offline_s = 0 if bridge.connected else offline_s + 1
                if discovered and offline_s >= REDISCOVER_AFTER_S:
                    kodi_bridge.log.info("server unreachable for %d s - rediscovering", offline_s)
                    break
            elif addon.getSettingBool("enabled"):
                retry_at -= 1
                if retry_at <= 0:
                    break
        if bridge is not None:
            bridge.stop()

