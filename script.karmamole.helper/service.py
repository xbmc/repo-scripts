# KarmaMole Skin Helper (script.karmamole.helper)
# Copyright (C) 2026 Omar Kamel
# SPDX-License-Identifier: GPL-2.0-or-later
"""Service entry point (code: resources/lib/kmhelper/service.py)."""
import os
import sys

import xbmcaddon
import xbmcvfs

sys.path.insert(0, os.path.join(xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('path')), 'resources', 'lib'))
from kmhelper.service import main  # noqa: E402

if __name__ == '__main__':
    main()
