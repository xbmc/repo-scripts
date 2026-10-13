"""Kodi-Sendspin service entry point (runs at Kodi login)."""
import os
import sys

import xbmcaddon

sys.path.insert(0, os.path.join(xbmcaddon.Addon().getAddonInfo("path"), "resources", "lib"))

from service_main import run  # noqa: E402

run()
