# -*- coding: utf-8 -*-

# Copyright (C) 2019 Alexander Seiler
#
#
# This file is part of script.module.youtube_channels.
#
# script.module.youtube_channels is free software: you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the License,
# or (at your option) any later version.
#
# script.module.youtube_channels is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with script.module.youtube_channels.
# If not, see <http://www.gnu.org/licenses/>.

import traceback

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon

from youtube_plugin.kodion.utils import datetime_parser
import youtube_requests

import simplecache


ADDON_ID = 'script.module.youtube_channels'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME = REAL_SETTINGS.getAddonInfo('name')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
ICON = REAL_SETTINGS.getAddonInfo('icon')
VIDEOS_PER_PAGE = 50


def try_get(dictionary, keys, data_type=str, default=''):
    """
    Accesses a nested dictionary in a save way.

    Keyword Arguments:
    dictionary   -- the dictionary to access
    keys         -- either a tuple/list containing the keys that should be
                    accessed, or a string/int if only one key should be
                    accessed
    data_type    -- the expected data type of the final element
                    (default: CompatStr)
    default      -- a default value to return (default: '')
    """
    d = dictionary
    try:
        if isinstance(keys, tuple) or isinstance(keys, list):
            for key in keys:
                d = d[key]
            if isinstance(d, data_type):
                return d
            return default
        if isinstance(d[keys], data_type):
            return d[keys]
        return default
    except (KeyError, IndexError, TypeError):
        return default


class YoutubeChannels(object):
    def __init__(self, plugin_handle, channel_ids,
                 plugin_id=None, debug=False):
        self.handle = plugin_handle
        self.channel_ids = channel_ids
        self.plugin_id = plugin_id
        self.video_ids = []

        self.cache = simplecache.SimpleCache()
        self.debug = debug

    def log(self, msg, level=xbmc.LOGDEBUG):
        """
        Logs a message using Kodi's logging interface.

        Keyword arguments:
        msg   -- the message to log
        level -- the logging level
        """
        if self.debug:
            if level == xbmc.LOGERROR:
                msg += ' ,' + traceback.format_exc()
        addon_id = self.plugin_id if self.plugin_id else ADDON_ID
        message = addon_id + '-' + '-' + msg
        xbmc.log(msg=message, level=level)

    def build_channel_overview_menu(self, plugin_channel_url=None):
        """
        Builds a menu containing all the given channels.

        Keyword arguments:
        plugin_channel_url  -- a plugin URL mask, where the channel ID
                               can be inserted to be used to proceed;
                               if not specified (or None) the plugin
                               'plugin.video.youtube' will be used
        """
        def get_channel(cid, channels):
            for ch in channels:
                if ch['id'] == cid:
                    return ch
            return {}
        channels_unsorted = youtube_requests.get_channels(self.channel_ids)
        channels = []
        if channels_unsorted and 'error' not in channels_unsorted[0]:
            for channel_id in self.channel_ids:
                try:
                    channels.append(next(
                        channel for channel in channels_unsorted
                        if channel_id == channel.get('id')))
                except StopIteration:
                    pass

        for channel in channels:
            name = try_get(channel, ('brandingSettings', 'channel', 'title'))
            list_item = xbmcgui.ListItem(label=name)
            thumbnail = try_get(
                channel, ('snippet', 'thumbnails', 'high', 'url'))
            banner = try_get(channel, ('brandingSettings',
                                       'image', 'bannerImageUrl'))
            poster = try_get(channel, ('brandingSettings',
                                       'image', 'bannerTvHighImageUrl'))
            list_item.setArt({
                'thumb': thumbnail,
                'banner': banner,
                'poster': poster,
                'fanart': poster,
            })
            description = try_get(channel, ('snippet', 'description'))
            list_item.setInfo('video', {'plot': description})
            list_item.setProperty('IsPlayable', 'false')
            yt_plugin_id = 'plugin.video.youtube'
            if plugin_channel_url:
                url = plugin_channel_url % channel['id']
            else:
                url = 'plugin://%s/channel/%s/' % (yt_plugin_id, channel['id'])
            xbmcplugin.addDirectoryItem(
                self.handle, url, list_item, isFolder=True)

    def build_newest_videos(self, page=1):
        """
        Builds a page containing the newest videos over all channels.

        Note that for each YouTube channel there will be at most 50
        videos in the list! To get a 'endless' list we would need to
        make additional YouTube API requests whenever we reach the last
        video of a YouTube channel. This is not implemented and we
        are restricted to up to 50 videos per YouTube channel.

        Returns the next page number (if there are videos left to
        display), otherwise 0.

        Keyword arguments:
        page  -- the page number to display
        """
        video_ids = self.cache.get(self.plugin_id + '.new_video_ids')
        if not video_ids:
            video_ids = self.retrieve_video_ids()
            self.cache.set(self.plugin_id + '.new_video_ids', video_ids)

        selected_vids = video_ids[(
            page-1)*VIDEOS_PER_PAGE:page*VIDEOS_PER_PAGE]
        self.build_video_menu(selected_vids)

        try:
            video_ids[page*VIDEOS_PER_PAGE]
        except IndexError:
            return 0
        return page+1

    def retrieve_video_ids(self):
        """
        Generates a list of YouTube video IDs of the most recently
        published videos of all the specified YouTube channels.

        The first YouTube API request retrieves the channel information
        of all the channels. Then, for each channel the 50 most recently
        published videos will be requested and their video ID will be
        sorted in reversed chronological order. Note that for each
        channel a YouTube API request is necessary, so that should be done
        too often.

        The final list of YouTube video IDs will be returned.
        """
        channels = youtube_requests.get_channels(self.channel_ids)
        playlist_ids = [try_get(
                ch, ('contentDetails', 'relatedPlaylists', 'uploads')
            ) for ch in channels]
        items = []
        for pid in playlist_ids:
            items += youtube_requests.get_playlist_items(pid)
        items = sorted(items, key=lambda x: try_get(
            x, ('snippet', 'publishedAt')), reverse=True)
        video_ids = [try_get(item, ('snippet', 'resourceId', 'videoId'))
                     for item in items]
        cleaned_video_ids = video_ids = [vid for vid in video_ids if vid]
        return cleaned_video_ids

    def build_video_menu(self, video_ids):
        """
        Builds a menu containing the YouTube videos specified by video_ids.

        Keyword arguments:
        video_ids  -- the list a YouTube video IDs
        """
        video_items = youtube_requests.get_videos(video_ids)

        items = []
        for item in video_items:
            title = try_get(item, ('snippet', 'title'))
            description = try_get(item, ('snippet', 'description'))
            thumbnail = try_get(item,
                                ('snippet', 'thumbnails', 'maxres', 'url')) or\
                try_get(item, ('snippet', 'thumbnails', 'high', 'url')) or\
                try_get(item, ('snippet', 'thumbnails', 'standard', 'url')) or\
                try_get(item, ('snippet', 'thumbnails', 'medium', 'url')) or\
                try_get(item, ('snippet', 'thumbnails', 'default', 'url'))
            list_item = xbmcgui.ListItem(label=title)
            list_item.setProperty('IsPlayable', 'true')
            duration_iso = try_get(item, ('contentDetails', 'duration'))
            try:
                duration = datetime_parser.parse(duration_iso).total_seconds()
            except Exception:
                duration = ''

            list_item.setInfo('video', {
                'plot': description,
                'duration': duration,
            })
            list_item.setArt({
                'thumb': thumbnail,
                'fanart': thumbnail,
                'poster': thumbnail,
            })
            video_id = try_get(item, 'id')
            items.append(
                ('plugin://plugin.video.youtube/play/?video_id=%s' % video_id,
                 list_item, False))

        xbmcplugin.addDirectoryItems(
            self.handle, items, totalItems=len(video_items))

    def build_channel_menu(self, channel_id, page_token=''):
        """
        Builds a menu containing the uploaded videos of a specified channel.

        Keyword arguments:
        channel_id  -- the YouTube channel ID
        page_token  -- the token of the page to display; an empty string
                       means that the first page will be displayed.
        """
        self.log('build_channel_menu: channel_id = %s, '
                 'page_token = %s' % (channel_id, page_token))
        channel = youtube_requests.get_channels(channel_id)
        if channel and 'error' not in channel[0]:
            pid = try_get(channel[0], ('contentDetails',
                                       'relatedPlaylists', 'uploads'))
            items = youtube_requests.get_playlist_items(
                pid, page_token=page_token)
            next_page_token = try_get(items[-1], 'nextPageToken')
            video_ids = [
                try_get(
                    item, ('snippet', 'resourceId', 'videoId')
                ) for item in items]
            vids = [vid for vid in video_ids if vid]
            self.build_video_menu(vids)
            return next_page_token
        else:
            self.log('build_channel_menu: Can not retrieve YouTube channel.')
