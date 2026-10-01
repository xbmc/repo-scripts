"""Kodi's entry point for the instant lookup. The work is in resources/lib/kodi_play.py."""

import os
import sys

import xbmcaddon

sys.path.insert(0, os.path.join(xbmcaddon.Addon().getAddonInfo("path"), "resources", "lib"))

import kodi_play

if __name__ == "__main__":
    kodi_play.main()
