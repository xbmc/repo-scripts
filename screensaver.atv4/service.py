"""
   Copyright (C) 2015- enen92
   This file is part of screensaver.atv4 - https://github.com/enen92/screensaver.atv4

   SPDX-License-Identifier: GPL-2.0-only
   See LICENSE for more information.
"""

from resources.lib.commonatv import addon

# set locked setting back to false on startup just in case kodi had crashed during playback
addon.setSettingBool("is_locked", False)
