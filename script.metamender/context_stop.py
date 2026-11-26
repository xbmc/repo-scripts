"""MetaMender context-menu entry point for "Stop scan" in the context menu's
MetaMender submenu (declared as a kodi.context.item extension in addon.xml,
shown only while a scan holds the scan lock). Asks the running background
scan to stop before its next item (service/stopscan.py).
"""
from __future__ import annotations

from resources.lib.service.stopscan import request_stop
from resources.lib.utils import lang, notify

if __name__ == "__main__":
    request_stop()
    notify(lang(32639))
