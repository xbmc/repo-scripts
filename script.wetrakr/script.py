"""
script.py — entry point of RunScript(script.wetrakr, <action>), used by the
buttons in the add-on settings. The work happens in the background service,
which listens to these notifications (resources/lib/sync_monitor.py).

  sync        full library sync now (with a progress dialog)
  sync_reset  forget the local sync state and start over
  login       connect (or reconnect) to WeTrakr with the QR code, here and now
"""

import sys

import xbmc
import xbmcgui

ACTIONS = {
    "sync": ("wetrakr_sync_now", "Library sync started"),
    "sync_reset": ("wetrakr_sync_reset", "Sync state reset, syncing again"),
}

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "sync"
    if action == "login":
        from resources.lib import auth
        result = auth.run_device_auth_flow(interactive=True)
        if result == auth.AUTH_BUSY:
            xbmcgui.Dialog().notification("WeTrakr", "The connect window is already open", xbmcgui.NOTIFICATION_INFO, 3000, False)
        sys.exit(0)
    signal, message = ACTIONS.get(action, ACTIONS["sync"])
    xbmc.executebuiltin('NotifyAll(script.wetrakr, {})'.format(signal))
    xbmcgui.Dialog().notification("WeTrakr", message, xbmcgui.NOTIFICATION_INFO, 3000, False)
