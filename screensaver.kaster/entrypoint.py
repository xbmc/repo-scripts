# -*- coding: utf-8 -*-
"""
  Copyright (C) 2017-2020 enen92
  This file is part of kaster

  SPDX-License-Identifier: GPL-2.0-or-later
  See LICENSE for more information.
"""

from resources.lib.screensaver import Kaster
import xbmcaddon

PATH = xbmcaddon.Addon().getAddonInfo("path")

if __name__ == '__main__':
    screensaver = Kaster(
        'screensaver-kaster.xml',
        PATH,
        'default',
        '',
    )
    screensaver.doModal()
    del screensaver
