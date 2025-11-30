# Copyright (C) 2018 Alexander Seiler
#
#
# This file is part of script.module.srgssr.
#
# script.module.srgssr is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# script.module.srgssr is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with script.module.srgssr.
# If not, see <http://www.gnu.org/licenses/>.

import os
import json

import xbmcplugin
import xbmcgui
import xbmcvfs

import youtube_channels


class YoutubeBuilder:
    def __init__(self, srgssr_instance):
        self.srgssr = srgssr_instance
        self.handle = srgssr_instance.handle

    def _read_youtube_channels(self, fname):
        """
        Reads YouTube channel IDs from a specified file and returns a list
        of these channel IDs.

        Keyword arguments:
        fname  -- the path to the file to be read
        """
        data_file = os.path.join(xbmcvfs.translatePath(self.srgssr.data_uri), fname)
        with open(data_file, "r", encoding="utf-8") as f:
            ch_content = json.load(f)
            cids = [elem["channel"] for elem in ch_content.get("channels", [])]
            return cids
        return []

    def get_youtube_channel_ids(self):
        """
        Uses the cache to generate a list of the stored YouTube channel IDs.
        """
        cache_identifier = self.srgssr.addon_id + ".youtube_channel_ids"
        channel_ids = self.srgssr.cache.get(cache_identifier)
        if not channel_ids:
            self.srgssr.log(
                "get_youtube_channel_ids: Caching YouTube channel ids."
                "This log message should not appear too many times."
            )
            channel_ids = self._read_youtube_channels(
                self.srgssr.fname_youtube_channels
            )
            self.srgssr.cache.set(cache_identifier, channel_ids)
        return channel_ids

    def build_youtube_main_menu(self):
        """
        Builds the main YouTube menu.
        """
        items = [
            {
                "name": self.srgssr.language(30110),
                "mode": 31,
            },
            {
                "name": self.srgssr.language(30111),
                "mode": 32,
            },
        ]

        for item in items:
            list_item = xbmcgui.ListItem(label=item["name"])
            list_item.setProperty("IsPlayable", "false")
            list_item.setArt(
                {
                    "icon": self.srgssr.get_youtube_icon(),
                }
            )
            purl = self.srgssr.build_url(mode=item["mode"])
            xbmcplugin.addDirectoryItem(self.handle, purl, list_item, isFolder=True)

    def build_youtube_channel_overview_menu(self, mode):
        """
        Builds a menu of folders containing the plugin's
        YouTube channels.

        Keyword arguments:
        channel_ids  -- a list of YouTube channel IDs
        mode         -- the plugin's URL mode
        """
        channel_ids = self.get_youtube_channel_ids()
        youtube_channels.YoutubeChannels(
            self.handle, channel_ids, self.srgssr.addon_id, self.srgssr.debug
        ).build_channel_overview_menu()

    def build_youtube_channel_menu(self, cid, mode, page=1, page_token=""):
        """
        Builds a YouTube channel menu (containing a list of the
        most recent uploaded videos).

        Keyword arguments:
        channel_ids  -- a list of channel IDs
        cid          -- the channel ID of the channel to display
        mode         -- the number which specifies to trigger this
                        action in the plugin's URL
        page         -- the page number to display (first page
                        starts at 1)
        page_token   -- the page token specifies the token that
                        should be used on the the YouTube API
                        request
        """
        try:
            page = int(page)
        except TypeError:
            page = 1

        channel_ids = self.get_youtube_channel_ids()
        next_page_token = youtube_channels.YoutubeChannels(
            self.handle, channel_ids, self.srgssr.addon_id, self.srgssr.debug
        ).build_channel_menu(cid, page_token=page_token)
        if next_page_token:
            next_item = xbmcgui.ListItem(label=">> " + self.srgssr.language(30073))
            next_url = self.srgssr.build_url(
                mode=mode, name=cid, page_hash=next_page_token
            )
            next_item.setProperty("IsPlayable", "false")
            xbmcplugin.addDirectoryItem(self.handle, next_url, next_item, isFolder=True)

    def build_youtube_newest_videos_menu(self, mode, page=1):
        """
        Builds a YouTube menu containing the most recent uploaded
        videos of all the defined channels.

        Keyword arguments:
        channel_ids  -- a list of channel IDs
        mode         -- the mode to be used in the plugin's URL
        page         -- the page number (first page starts at 1)
        """
        try:
            page = int(page)
        except TypeError:
            page = 1

        channel_ids = self.get_youtube_channel_ids()
        next_page = youtube_channels.YoutubeChannels(
            self.handle, channel_ids, self.srgssr.addon_id, self.srgssr.debug
        ).build_newest_videos(page=page)
        if next_page:
            next_item = xbmcgui.ListItem(label=">> " + self.srgssr.language(30073))
            next_url = self.srgssr.build_url(mode=mode, page=next_page)
            next_item.setProperty("IsPlayable", "false")
            xbmcplugin.addDirectoryItem(self.handle, next_url, next_item, isFolder=True)
