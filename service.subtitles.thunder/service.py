# SPDX-License-Identifier: GPL-2.0-only
"""Kodi subtitle entry point (Kodi 19+, Python 3)."""
import os
import sys
import xbmcaddon
import xbmcvfs

sys.path.insert(0, xbmcvfs.translatePath(os.path.join(
    xbmcaddon.Addon().getAddonInfo('path'), 'resources', 'lib')))
from kodi_service import main

if __name__ == '__main__':
    main()
