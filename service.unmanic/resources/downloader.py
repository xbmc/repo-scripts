#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     08 Dec 2020, (22:30 PM)

    Copyright:
        Copyright (C) 2021 Josh Sunnex

        This program is free software: you can redistribute it and/or modify it under the terms of the GNU General
        Public License as published by the Free Software Foundation, version 3.

        This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the
        implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
        for more details.

        You should have received a copy of the GNU General Public License along with this program.
        If not, see <https://www.gnu.org/licenses/>.

"""

import xbmc
import xbmcgui
from urllib import request


def download(url, dest, dp=None):
    if not dp:
        dp = xbmcgui.DialogProgress()
        dp.create("Unmanic", "Downloading & Copying File", ' ', ' ')
    dp.update(0)
    request.urlretrieve(url, dest, lambda nb, bs, fs, url=url: _pbhook(nb, bs, fs, url, dp))


def _pbhook(numblocks, blocksize, filesize, url, dp):
    try:
        percent = int(min((numblocks * blocksize * 100) / filesize, 100))
        dp.update(percent)
    except Exception as e:
        xbmc.log('Unmanic: Completed file download - {}'.format(str(e)), level=xbmc.LOGDEBUG)
        percent = 100
        dp.update(percent)
    if dp.iscanceled():
        raise Exception("Canceled")
        dp.close()
