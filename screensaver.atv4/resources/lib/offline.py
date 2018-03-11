# -*- coding: utf-8 -*-
"""
    screensaver.atv4
    Copyright (C) 2015-2017 enen92

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import xbmcvfs
import playlist
import downloader
from commonatv import dialog, addon, translate, places


def offline():
    if addon.getSetting("download-folder") != "" and xbmcvfs.exists(addon.getSetting("download-folder")):
        choose = dialog.select(translate(32014),places)
        if choose > -1:
            atv_playlist = playlist.AtvPlaylist()
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
                down = downloader.Downloader()
                down.downloadall(download_list)
            else:
                dialog.ok(translate(32000), translate(32012))
    else:
        dialog.ok(translate(32000), translate(32013))


