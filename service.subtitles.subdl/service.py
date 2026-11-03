"""Kodi's entry point for the SubDL subtitle module. The work is in resources/lib/subdl."""

import os
import sys

import xbmcaddon
import xbmcvfs

sys.path.insert(0, os.path.join(xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo("path")), "resources", "lib"))

from subdl import addon  # noqa: E402

if __name__ == "__main__":
    addon.run(sys.argv)
