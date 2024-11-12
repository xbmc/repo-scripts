# SPDX-License-Identifier: GPL-2.0-or-later
#
# XBMC LCDproc addon
# Copyright (C) 2012-2024 Team Kodi
# Copyright (C) 2012-2024 Daniel 'herrnst' Scheller
#
# Addon entry point
#

from resources.lib.xbmclcdproc import XBMCLCDproc

######
# script entry point
if __name__ == "__main__":
    xbmclcd = XBMCLCDproc()
    xbmclcd.RunLCD()
