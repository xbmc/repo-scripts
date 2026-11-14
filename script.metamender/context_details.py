"""MetaMender context-menu entry point for "Details" in the context menu's
MetaMender submenu (declared as a kodi.context.item extension in
addon.xml). Reads the focused list item's DBTYPE and DBID and opens the
details window for it (service/details.py).
"""
from __future__ import annotations

import xbmc

from resources.lib.service.details import open_details

if __name__ == "__main__":
    open_details(xbmc.getInfoLabel("ListItem.DBTYPE"), xbmc.getInfoLabel("ListItem.DBID"))
