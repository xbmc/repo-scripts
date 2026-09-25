"""Kodi's entry point for the subtitle module. The work is in resources/lib/kodi_side.py."""

import os
import sys

import xbmcaddon

sys.path.insert(0, os.path.join(xbmcaddon.Addon().getAddonInfo("path"), "resources", "lib"))

import kodi_side

if __name__ == "__main__":
    kodi_side.main()
