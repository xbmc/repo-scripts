"""
   Copyright (C) 2015- enen92
   This file is part of screensaver.atv4 - https://github.com/enen92/screensaver.atv4

   SPDX-License-Identifier: GPL-2.0-only
   See LICENSE for more information.
"""

import xbmcvfs
from .commonatv import dialog, addon, translate, places
from .playlist import AtvPlaylist
from .downloader import Downloader

def offline():
    if addon.getSetting("download-folder") and xbmcvfs.exists(addon.getSetting("download-folder")):
        choose = dialog.select(translate(32014),places)
        if choose > -1:
            atv_playlist = AtvPlaylist()
            playlist_dict = atv_playlist.getPlaylistJson()
            download_list = []
            if playlist_dict:
                for block in playlist_dict:
                    for video in block['assets']:
                        if places[choose].lower() == "all":
                            download_list.append(video['url'])
                        else:
                            if places[choose].lower() == video['accessibilityLabel'].lower():
                                download_list.append(video['url'])
            # call downloader
            if download_list:
                down = Downloader()
                down.downloadall(download_list)
            else:
                dialog.ok(translate(32000), translate(32012))
    else:
        dialog.ok(translate(32000), translate(32013))


