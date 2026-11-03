"""Run by the "Check my API key" button in the add-on settings.

Kodi starts this file with RunScript(path), outside the add-on's own context, where
xbmcaddon.Addon() only works when given the add-on id.
"""

import os
import sys

import xbmcaddon
import xbmcvfs

ADDON_PATH = xbmcvfs.translatePath(xbmcaddon.Addon("service.subtitles.subdl").getAddonInfo("path"))
sys.path.insert(0, os.path.join(ADDON_PATH, "resources", "lib"))

from subdl import addon  # noqa: E402

if __name__ == "__main__":
    addon.check_key()
