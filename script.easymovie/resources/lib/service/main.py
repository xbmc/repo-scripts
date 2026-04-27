"""
EasyMovie background service.

Lightweight service that monitors movie playback for set awareness.
No daemon loop — just a playback monitor and abort wait.

Logging:
    Logger: 'service'
    Key events:
        - service.start (INFO): Service started with version, device, Kodi build
        - service.stop (INFO): Service stopping
        - icon.restored (INFO): Custom icon restored after addon upgrade
    See LOGGING.md for full guidelines.
"""
import filecmp
import os
import socket

import xbmc
import xbmcaddon
import xbmcvfs

from resources.lib.constants import CUSTOM_ICON_BACKUP
from resources.lib.utils import get_logger, invalidate_icon_cache
from resources.lib.service.playback_monitor import MoviePlaybackMonitor


def _get_device_name() -> str:
    """Return the Kodi device friendly name, falling back to hostname."""
    try:
        name = xbmc.getInfoLabel('System.FriendlyName')
        if name:
            return name
        return socket.gethostname() or 'unknown'
    except Exception:
        return 'unknown'


def _restore_icon_if_needed(addon: xbmcaddon.Addon) -> None:
    """Restore custom icon after an addon upgrade overwrites icon.png.

    Checks if the user had a custom icon choice and whether the current
    icon.png matches icon_default.png (indicating an upgrade replaced it).
    If so, restores from the backup in addon_data.
    """
    log = get_logger('service')
    addon_id = addon.getAddonInfo('id')
    icon_choice = addon.getSetting('icon_choice')
    if not icon_choice:
        return

    addon_path = addon.getAddonInfo('path')
    icon_path = os.path.join(addon_path, 'icon.png')
    default_path = os.path.join(addon_path, 'icon_default.png')

    if not os.path.isfile(icon_path) or not os.path.isfile(default_path):
        return

    if not filecmp.cmp(icon_path, default_path, shallow=False):
        return  # Icon is already custom, no restore needed

    # Icon matches default — upgrade wiped it. Try to restore.
    addon_data = xbmcvfs.translatePath(
        f'special://profile/addon_data/{addon_id}/'
    )
    backup_path = os.path.join(addon_data, CUSTOM_ICON_BACKUP)

    if os.path.isfile(backup_path):
        xbmcvfs.copy(backup_path, icon_path)
        invalidate_icon_cache(addon_id)
        log.info("Custom icon restored after upgrade",
                 event="icon.restored", source="backup", addon_id=addon_id)
        return

    # No backup — try built-in fallback
    if icon_choice.startswith('built-in:'):
        filename = icon_choice.split(':', 1)[1]
        builtin_path = os.path.join(addon_path, 'resources', 'icons', filename)
        if os.path.isfile(builtin_path):
            xbmcvfs.copy(builtin_path, icon_path)
            # Re-create the missing backup
            xbmcvfs.copy(builtin_path, backup_path)
            invalidate_icon_cache(addon_id)
            log.info("Custom icon restored after upgrade",
                     event="icon.restored", source="built-in",
                     icon=filename, addon_id=addon_id)
            return

    # Custom image with no backup — can't restore
    log.warning("Custom icon backup missing, resetting to default",
                event="icon.restore_failed", choice=icon_choice,
                addon_id=addon_id)
    addon.setSetting('icon_choice', '')


def _get_kodi_version() -> str:
    """Return the Kodi build version (first word only)."""
    try:
        build = xbmc.getInfoLabel('System.BuildVersion')
        if build:
            return build.split()[0]
        return 'unknown'
    except Exception:
        return 'unknown'


def main() -> None:
    """Run the EasyMovie background service."""
    addon = xbmcaddon.Addon()
    version = addon.getAddonInfo('version')

    log = get_logger('service')
    log.info(
        "EasyMovie service started",
        event="service.start",
        version=version,
        device=_get_device_name(),
        kodi=_get_kodi_version(),
    )

    _restore_icon_if_needed(addon)

    monitor = xbmc.Monitor()
    # Must keep reference to prevent garbage collection — Kodi calls
    # the Player subclass callbacks as long as the object is alive.
    _player = MoviePlaybackMonitor()

    while not monitor.abortRequested():
        if monitor.waitForAbort(1):
            break

    del _player  # Explicit cleanup before service exit
    log.info(
        "EasyMovie service stopping",
        event="service.stop",
        version=version,
        device=_get_device_name(),
    )
