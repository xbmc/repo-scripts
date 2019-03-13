# -*- coding: utf-8 -*-

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
import sys
import re
import traceback

import datetime
import json
import requests

try:  # Python 3
    from urllib.parse import quote_plus, parse_qsl, ParseResult
    from urllib.parse import urlparse as urlps
except ImportError:  # Python 2
    from urllib import quote_plus
    from urlparse import parse_qsl, ParseResult
    from urlparse import urlparse as urlps

from kodi_six import xbmc, xbmcgui, xbmcplugin, xbmcaddon
import utils
import youtube_channels

# NOTE: As soon as script.module.simplecache is Python 3 compatible,
# we can remove the following condition and just import SimpleCache.
# See https://github.com/kodi-community-addons/script.module.simplecache/pull/7
if sys.version_info[0] >= 3:
    from dummycache import SimpleCache
else:
    from simplecache import SimpleCache

ADDON_ID = 'script.module.srgssr'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME = REAL_SETTINGS.getAddonInfo('name')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
ICON = REAL_SETTINGS.getAddonInfo('icon')
LANGUAGE = REAL_SETTINGS.getLocalizedString
TIMEOUT = 30

IDREGEX = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|\d+'

FAVOURITE_SHOWS_FILENAME = 'favourite_shows.json'
YOUTUBE_CHANNELS_FILENAME = 'youtube_channels.json'


def get_params():
    """
    Parses the Kodi plugin URL and returns its parameters
    in a dictionary.
    """
    return dict(parse_qsl(sys.argv[2][1:]))


class SRGSSR(object):
    """
    Base class for all SRG SSR related plugins.
    Everything that can be done independently from the business unit
    (SRF, RTS, RSI, etc.) should be done here.
    """
    def __init__(self, plugin_handle, bu='srf', addon_id=ADDON_ID):
        self.handle = plugin_handle
        self.cache = SimpleCache()
        self.real_settings = xbmcaddon.Addon(id=addon_id)
        self.bu = bu
        self.addon_id = addon_id
        self.icon = self.real_settings.getAddonInfo('icon')
        self.fanart = self.real_settings.getAddonInfo('fanart')
        self.language = LANGUAGE
        self.plugin_language = self.real_settings.getLocalizedString
        self.host_url = 'https://www.%s.ch' % bu
        if bu == 'swi':
            self.host_url = 'https://play.swissinfo.ch'
        self.data_uri = ('special://home/addons/%s/resources/'
                         'data') % self.addon_id
        self.media_uri = ('special://home/addons/%s/resources/'
                          'media') % self.addon_id

        # Plugin options:
        self.debug = self.get_boolean_setting(
            'Enable_Debugging')
        self.segments = self.get_boolean_setting(
            'Enable_Show_Segments')
        self.segments_topics = self.get_boolean_setting(
            'Enable_Segments_Topics')
        self.subtitles = self.get_boolean_setting(
            'Extract_Subtitles')
        self.prefer_hd = self.get_boolean_setting(
            'Prefer_HD')
        self.number_of_episodes = 10

    def get_youtube_icon(self):
        path = os.path.join(
            xbmc.translatePath(self.media_uri), 'icon_youtube.png')
        if os.path.exists(path):
            return path
        return self.icon

    def get_boolean_setting(self, setting):
        """
        Returns the boolean value of a specified setting.

        Keyword arguments
        setting  -- the setting option to check
        """
        return self.real_settings.getSetting(setting) == 'true'

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
        message = ADDON_ID + '-' + ADDON_VERSION + '-' + msg
        xbmc.log(msg=message, level=level)

    @staticmethod
    def build_url(mode=None, name=None, url=None, page_hash=None, page=None):
        """Build a URL for the Kodi plugin.

        Keyword arguments:
        mode      -- an integer representing the mode
        name      -- a string containing some information, e.g. a video id
        url       -- a plugin URL, if another plugin/script needs to called
        page_hash -- a string (used to get additional videos through the API)
        page      -- an integer used to indicate the current page in
                     the list of items
        """
        if mode:
            mode = str(mode)
        if page:
            page = str(page)
        added = False
        queries = (url, mode, name, page_hash, page)
        query_names = ('url', 'mode', 'name', 'page_hash', 'page')
        purl = sys.argv[0]
        for query, qname in zip(queries, query_names):
            if query:
                add = '?' if not added else '&'
                purl += '%s%s=%s' % (add, qname, quote_plus(query))
                added = True
        return purl

    def open_url(self, url, use_cache=True):
        """Open and read the content given by a URL.

        Keyword arguments:
        url       -- the URL to open as a string
        use_cache -- boolean to indicate if the cache provided by the
                     Kodi module SimpleCache should be used (default: True)
        """
        self.log('open_url, url = ' + str(url))
        cache_response = None
        if use_cache:
            cache_response = self.cache.get(
                ADDON_NAME + '.open_url, url = %s' % url)
        if not cache_response:
            headers = {
                'User-Agent': ('Mozilla/5.0 (X11; Linux x86_64; rv:59.0)'
                               'Gecko/20100101 Firefox/59.0'),
            }
            response = requests.get(url, headers=headers)
            if not response.ok:
                self.log('open_url: Failed to open url %s' % url)
                xbmcgui.Dialog().notification(
                    ADDON_NAME, LANGUAGE(30100), ICON, 4000)
                return ''
            self.cache.set(
                ADDON_NAME + '.open_url, url = %s' % url,
                response.text,
                expiration=datetime.timedelta(hours=2))
            return response.text
        return self.cache.get(ADDON_NAME + '.open_url, url = %s' % url)

    def build_main_menu(self, identifiers=[]):
        """
        Builds the main menu of the plugin:

        Keyword arguments:
        identifiers  -- A list of strings containing the identifiers
                        of the menus to display.
        """
        self.log('build_main_menu')
        main_menu_list = [
            {
                # All shows
                'identifier': 'All_Shows',
                'name': self.plugin_language(30050),
                'mode': 10,
                'displayItem': self.get_boolean_setting('All_Shows'),
                'icon': self.icon,
            }, {
                # Favourite shows
                'identifier': 'Favourite_Shows',
                'name': self.plugin_language(30051),
                'mode': 11,
                'displayItem': self.get_boolean_setting('Favourite_Shows'),
                'icon': self.icon,
            }, {
                # Newest favourite shows
                'identifier': 'Newest_Favourite_Shows',
                'name': self.plugin_language(30052),
                'mode': 12,
                'displayItem': self.get_boolean_setting(
                    'Newest_Favourite_Shows'),
                'icon': self.icon,
            }, {
                # Recommendations
                'identifier': 'Recommendations',
                'name': self.plugin_language(30053),
                'mode': 16,
                'displayItem': self.get_boolean_setting('Recommendations'),
                'icon': self.icon,
            }, {
                # Newest shows
                'identifier': 'Newest_Shows',
                'name': self.plugin_language(30054),
                'mode': 13,
                'displayItem': self.get_boolean_setting('Newest_Shows'),
                'icon': self.icon,
            }, {
                # Most clicked shows
                'identifier': 'Most_Clicked_Shows',
                'name': self.plugin_language(30055),
                'mode': 14,
                'displayItem': self.get_boolean_setting('Most_Clicked_Shows'),
                'icon': self.icon,
            }, {
                # Soon offline
                'identifier': 'Soon_Offline',
                'name': self.plugin_language(30056),
                'mode': 15,
                'displayItem': self.get_boolean_setting('Soon_Offline'),
                'icon': self.icon,
            }, {
                # Shows by date
                'identifier': 'Shows_By_Date',
                'name': self.plugin_language(30057),
                'mode': 17,
                'displayItem': self.get_boolean_setting('Shows_By_Date'),
                'icon': self.icon,
            }, {
                # Live TV
                'identifier': 'Live_TV',
                'name': self.plugin_language(30072),
                'mode': 26,
                'displayItem': self.get_boolean_setting('Live_TV'),
                'icon': self.icon,
            }, {
                # SRF.ch live
                'identifier': 'SRF_Live',
                'name': self.plugin_language(30070),
                'mode': 18,
                'displayItem': self.get_boolean_setting('SRF_Live'),
                'icon': self.icon,
            }, {
                # SRF on YouTube
                'identifier': 'SRF_YouTube',
                'name': self.plugin_language(30074),
                'mode': 30,
                'displayItem': self.get_boolean_setting('SRF_YouTube'),
                'icon': self.get_youtube_icon(),
            }, {
                # RTS on YouTube
                'identifier': 'RTS_YouTube',
                'name': self.plugin_language(30074),
                'mode': 30,
                'displayItem': self.get_boolean_setting('RTS_YouTube'),
                'icon': self.get_youtube_icon(),
            }, {
                # RSI on YouTube
                'identifier': 'RSI_YouTube',
                'name': self.plugin_language(30074),
                'mode': 30,
                'displayItem': self.get_boolean_setting('RSI_YouTube'),
                'icon': self.get_youtube_icon(),
            }, {
                # RTR on YouTube
                'identifier': 'RTR_YouTube',
                'name': self.plugin_language(30074),
                'mode': 30,
                'displayItem': self.get_boolean_setting('RTR_YouTube'),
                'icon': self.get_youtube_icon(),
            }
        ]
        for item in main_menu_list:
            if item['displayItem'] and item['identifier'] in identifiers:
                list_item = xbmcgui.ListItem(item['name'])
                list_item.setProperty('IsPlayable', 'false')
                list_item.setArt({'thumb': item['icon']})
                purl = self.build_url(
                    mode=item['mode'], name=item['identifier'])
                xbmcplugin.addDirectoryItem(
                    handle=self.handle, url=purl,
                    listitem=list_item, isFolder=True)

    def read_all_available_shows(self):
        """
        Downloads a list of all available shows and returns this list.

        This works for the business units 'srf', 'rts', 'rsi' and 'rtr', but
        not for 'swi'.
        """
        json_url = ('http://il.srgssr.ch/integrationlayer/1.0/ue/%s/tv/'
                    'assetGroup/editorialPlayerAlphabetical.json') % self.bu
        json_response = json.loads(self.open_url(json_url))
        show_list = utils.try_get(
            json_response,
            ('AssetGroups', 'Show'), data_type=list, default=[])
        if not show_list:
            self.log('read_all_available_shows: No shows found.')
            return []
        return show_list

    def build_all_shows_menu(self, favids=None):
        """
        Builds a list of folders containing the names of all the current
        shows.

        Keyword arguments:
        favids -- A list of show ids (strings) respresenting the favourite
                  shows. If such a list is provided, only the folders for
                  the shows on that list will be build. (default: None)
        """
        self.log('build_all_shows_menu')
        show_list = self.read_all_available_shows()

        list_items = []
        for jse in show_list:
            title = utils.try_get(jse, 'title')
            show_id = utils.try_get(jse, 'id')
            if not (title and show_id):
                self.log(
                    'build_all_shows_menu: Skipping, no title or id found.')
                continue

            # Skip if we build the 'favourite show menu' and the current
            # show id is not in our favourites:
            if favids is not None and show_id not in favids:
                continue

            list_item = xbmcgui.ListItem(label=title)
            list_item.setProperty('IsPlayable', 'false')
            list_item.setInfo(
                'video',
                {
                    'title': title,
                    'plot': utils.try_get(
                        jse, 'lead') or utils.try_get(jse, 'description'),
                }
            )

            image_url = utils.try_get(
                jse,
                ('Image', 'ImageRepresentations',
                 'ImageRepresentation', 0, 'url'))
            if image_url:
                image_url = re.sub(r'/\d+x\d+', '', image_url)
                thumbnail = image_url + '/scale/width/688'
                banner = image_url.replace(
                    'WEBVISUAL',
                    'HEADER_SRF_PLAYER')
            else:
                image_url = self.fanart
                thumbnail = self.icon
                banner = None

            list_item.setArt({
                'thumb': thumbnail,
                'poster': image_url,
                'banner': banner,
            })
            url = self.build_url(mode=20, name=show_id)
            list_items.append((url, list_item, True))
        xbmcplugin.addDirectoryItems(
            self.handle, list_items, totalItems=len(list_items))

    def build_favourite_shows_menu(self):
        """
        Builds a list of folders for the favourite shows.
        """
        self.log('build_favourite_shows_menu')
        favourite_show_ids = self.read_favourite_show_ids()
        self.build_all_shows_menu(favids=favourite_show_ids)

    def build_newest_favourite_menu(self, page=1):
        """
        Builds a Kodi list of the newest favourite shows.

        Keyword arguments:
        page -- an integer indicating the current page on the
                list (default: 1)
        """
        self.log('build_newest_favourite_menu')
        number_of_days = 30
        show_ids = self.read_favourite_show_ids()

        # TODO: This depends on the local time settings
        now = datetime.datetime.now()
        current_month_date = datetime.date.today().strftime('%m-%Y')
        list_of_episodes_dict = []
        banners = {}
        for sid in show_ids:
            json_url = ('%s/play/tv/show/%s/latestEpisodes?numberOfEpisodes=%d'
                        '&tillMonth=%s') % (self.host_url, sid, number_of_days,
                                            current_month_date)
            self.log('build_newest_favourite_menu. Open URL %s.' % json_url)
            response = json.loads(self.open_url(json_url))
            banner_image = utils.try_get(
                response,
                ('show', 'bannerImageUrl'))
            if re.match(r'.+/\d+x\d+$', banner_image):
                banner_image += '/scale/width/1000'

            episode_list = utils.try_get(
                response, 'episodes', data_type=list, default=[])
            for episode in episode_list:
                date_time = utils.parse_datetime(
                    utils.try_get(episode, 'date'))
                if date_time and \
                        date_time >= now + datetime.timedelta(-number_of_days):
                    list_of_episodes_dict.append(episode)
                    banners.update(
                        {utils.try_get(episode, 'id'): banner_image})
        sorted_list_of_episodes_dict = sorted(
            list_of_episodes_dict, key=lambda k: utils.parse_datetime(
                utils.try_get(k, 'date')), reverse=True)
        try:
            page = int(page)
        except TypeError:
            page = 1
        reduced_list = sorted_list_of_episodes_dict[
            (page - 1)*self.number_of_episodes:page*self.number_of_episodes]
        for episode in reduced_list:
            segments = utils.try_get(
                episode, 'segments', data_type=list, default=[])
            is_folder = True if segments and self.segments else False
            self.build_entry(
                episode, banner=utils.try_get(episode, 'id'),
                is_folder=is_folder)

        if len(sorted_list_of_episodes_dict) > page * self.number_of_episodes:
            next_item = xbmcgui.ListItem(
                label='>> ' + LANGUAGE(30073))  # Next page
            next_item.setProperty('IsPlayable', 'false')
            purl = self.build_url(mode=12, page=page+1)
            xbmcplugin.addDirectoryItem(
                self.handle, purl, next_item, isFolder=True)

    def build_show_menu(self, show_id, page_hash=None):
        """
        Builds a list of videos (can be folders in case of segmented videos)
        for a show given by its show id.

        Keyword arguments:
        show_id   -- the id of the show
        page_hash -- the page hash to get the list of
                     another page (default: None)
        """
        self.log('build_show_menu, show_id = %s, page_hash=%s' % (show_id,
                                                                  page_hash))
        # TODO: This depends on the local time settings
        current_month_date = datetime.date.today().strftime('%m-%Y')
        if not page_hash:
            json_url = ('%s/play/tv/show/%s/latestEpisodes?numberOfEpisodes=%d'
                        '&tillMonth=%s') % (self.host_url, show_id,
                                            self.number_of_episodes,
                                            current_month_date)
        else:
            json_url = ('%s/play/tv/show/%s/latestEpisodes?nextPageHash=%s'
                        '&tillMonth=%s') % (self.host_url, show_id, page_hash,
                                            current_month_date)
        self.log('build_show_menu. Open URL %s' % json_url)
        json_response = json.loads(self.open_url(json_url))

        try:
            banner_image = utils.try_get(
                json_response, ('show', 'bannerImageUrl'))

            # Banner image urls sometimes end with '/3x1'. They are
            # only accesible if we append '/scale/width/\d+':
            if re.match(r'.+/\d+x\d+$', banner_image):
                banner_image += '/scale/width/1000'
        except KeyError:
            banner_image = None

        next_page_hash = None
        if 'nextPageUrl' in json_response:
            next_page_url = utils.try_get(json_response, 'nextPageUrl')
            next_page_hash_regex = r'nextPageHash=(?P<hash>[0-9a-f]+)'
            match = re.search(next_page_hash_regex, next_page_url)
            if match:
                next_page_hash = match.group('hash')

        json_episode_list = utils.try_get(
            json_response, 'episodes', data_type=list, default=[])
        if not json_episode_list:
            self.log('No episodes for show %s found.' % show_id)
            return

        for episode_entry in json_episode_list:
            segments = utils.try_get(
                episode_entry, 'segments', data_type=list, default=[])
            enable_segments = True if self.segments and segments else False
            self.build_entry(
                episode_entry, banner=banner_image, is_folder=enable_segments)

        if next_page_hash and page_hash != next_page_hash:
            self.log('page_hash: %s' % page_hash)
            self.log('next_hash: %s' % next_page_hash)
            next_item = xbmcgui.ListItem(
                label='>> ' + LANGUAGE(30073))  # Next page
            next_item.setProperty('IsPlayable', 'false')
            url = self.build_url(
                mode=20, name=show_id, page_hash=next_page_hash)
            xbmcplugin.addDirectoryItem(
                self.handle, url, next_item, isFolder=True)

    def build_topics_overview_menu(self, newest_or_most_clicked):
        """
        Builds a list of folders, where each folders represents a
        topic (e.g. News).

        Keyword arguments:
        newest_or_most_clicked -- a string (either 'Newest' or 'Most clicked')
        """
        self.log('build_topics_overview_menu, newest_or_most_clicked = %s' %
                 newest_or_most_clicked)
        if newest_or_most_clicked == 'Newest':
            mode = 22
        elif newest_or_most_clicked == 'Most clicked':
            mode = 23
        else:
            self.log('build_topics_overview_menu: Unknown mode, \
                must be "Newest" or "Most clicked".')
            return
        topics_url = self.host_url + '/play/tv/topicList'
        topics_json = json.loads(self.open_url(topics_url))
        if not isinstance(topics_json, list) or not topics_json:
            self.log('No topics found.')
            return
        for elem in topics_json:
            list_item = xbmcgui.ListItem(label=elem.get('title'))
            list_item.setProperty('IsPlayable', 'false')
            list_item.setArt({'thumb': self.icon})
            name = utils.try_get(elem, 'id')
            if name:
                purl = self.build_url(mode=mode, name=name)
                xbmcplugin.addDirectoryItem(
                    handle=self.handle, url=purl,
                    listitem=list_item, isFolder=True)

    def extract_id_list(self, url):
        """
        Opens a webpage and extracts video ids (of the form "id": "<vid>")
        from JavaScript snippets.

        Keyword argmuents:
        url -- the URL of the webpage
        """
        self.log('extract_id_list, url = %s' % url)
        response = self.open_url(url)
        string_response = utils.str_or_none(response, default='')
        if not string_response:
            self.log('No video ids found on %s' % url)
            return []
        readable_string_response = string_response.replace('&quot;', '"')
        id_regex = r'''(?x)
                        \"id\"
                        \s*:\s*
                        \"
                        (?P<id>
                            %s
                        )
                        \"
                    ''' % IDREGEX
        id_list = [m.group('id') for m in re.finditer(
            id_regex, readable_string_response)]
        return id_list

    def build_topics_menu(self, name, topic_id=None, page=1):
        """
        Builds a list of videos (can also be folders) for a given topic.

        Keyword arguments:
        name     -- the type of the list, can be 'Newest', 'Most clicked',
                    'Soon offline' or 'Trending'.
        topic_id -- the SRF topic id for the given topic, this is only needed
                    for the types 'Newest' and 'Most clicked' (default: None)
        page     -- an integer representing the current page in the list
        """
        self.log('build_topics_menu, name = %s, topic_id = %s, page = %s' %
                 (name, topic_id, page))
        number_of_videos = 50
        if name == 'Newest':
            url = '%s/play/tv/topic/%s/latest?numberOfVideos=%s' % (
                self.host_url, topic_id, number_of_videos)
            mode = 22
        elif name == 'Most clicked':
            url = '%s/play/tv/topic/%s/mostClicked?numberOfVideos=%s' % (
                self.host_url, topic_id, number_of_videos)
            mode = 23
        elif name == 'Soon offline':
            url = '%s/play/tv/videos/soon-offline-videos?numberOfVideos=%s' % (
                self.host_url, number_of_videos)
            mode = 15
        elif name == 'Trending':
            url = ('%s/play/tv/videos/trending?numberOfVideos=%s'
                   '&onlyEpisodes=true&includeEditorialPicks=true') % (
                       self.host_url, number_of_videos)
            mode = 16
        else:
            self.log('build_topics_menu: Unknown mode.')
            return

        id_list = self.extract_id_list(url)
        try:
            page = int(page)
        except TypeError:
            page = 1

        reduced_id_list = id_list[(page - 1) * self.number_of_episodes:
                                  page * self.number_of_episodes]
        for vid in reduced_id_list:
            self.build_episode_menu(
                vid, include_segments=False,
                segment_option=self.segments_topics)

        try:
            vid = id_list[page*self.number_of_episodes]
            next_item = xbmcgui.ListItem(
                label='>> ' + LANGUAGE(30073))  # Next page
            next_item.setProperty('IsPlayable', 'false')
            name = topic_id if topic_id else ''
            purl = self.build_url(mode=mode, name=name, page=page+1)
            xbmcplugin.addDirectoryItem(
                handle=self.handle, url=purl,
                listitem=next_item, isFolder=True)
        except IndexError:
            return

    def build_episode_menu(self, video_id, include_segments=True,
                           segment_option=False):
        """
        Builds a list entry for a episode by a given video id.
        The segment entries for that episode can be included too.
        The video id can be an id of a segment. In this case an
        entry for the segment will be created.

        Keyword arguments:
        video_id         -- the id of the video
        include_segments -- indicates if the segments (if available) of the
                            video should be included in the list
                            (default: True)
        segment_option   -- Which segment option to use.
                            (default: False)
        """
        self.log('build_episode_menu, video_id = %s, include_segments = %s' %
                 (video_id, include_segments))
        json_url = ('https://il.srgssr.ch/integrationlayer/2.0/%s/'
                    'mediaComposition/video/%s.json') % (self.bu, video_id)
        self.log('build_episode_menu. Open URL %s' % json_url)
        try:
            json_response = json.loads(self.open_url(json_url))
        except Exception:
            self.log('build_episode_menu: Cannot open media json for %s.'
                     % video_id)
            return

        chapter_urn = utils.try_get(json_response, 'chapterUrn')
        segment_urn = utils.try_get(json_response, 'segmentUrn')

        id_regex = r'[a-z]+:[a-z]+:[a-z]+:(?P<id>.+)'
        match_chapter_id = re.match(id_regex, chapter_urn)
        match_segment_id = re.match(id_regex, segment_urn)
        chapter_id = match_chapter_id.group('id') if match_chapter_id else None
        segment_id = match_segment_id.group('id') if match_segment_id else None

        if not chapter_id:
            self.log('build_episode_menu: No valid chapter URN \
                available for video_id %s' % video_id)
            return

        try:
            banner = utils.try_get(json_response, ('show', 'bannerImageUrl'))
            if re.match(r'.+/\d+x\d+$', banner):
                banner += '/scale/width/1000'
        except KeyError:
            banner = None

        json_chapter_list = utils.try_get(
            json_response, 'chapterList', data_type=list, default=[])
        json_chapter = None
        for chapter in json_chapter_list:
            if utils.try_get(chapter, 'id') == chapter_id:
                json_chapter = chapter
                break
        if not json_chapter:
            self.log('build_episode_menu: No chapter ID found \
                for video_id %s' % video_id)
            return

        json_segment_list = utils.try_get(
            json_chapter, 'segmentList', data_type=list, default=[])
        if video_id == chapter_id:
            if include_segments:
                # Generate entries for the whole video and
                # all the segments of this video.
                self.build_entry(json_chapter, banner)
                for segment in json_segment_list:
                    self.build_entry(segment, banner)
            else:
                if segment_option and json_segment_list:
                    # Generate a folder for the video
                    self.build_entry(json_chapter, banner, is_folder=True)
                else:
                    # Generate a simple playable item for the video
                    self.build_entry(json_chapter, banner)
        else:
            json_segment = None
            for segment in json_segment_list:
                if utils.try_get(segment, 'id') == segment_id:
                    json_segment = segment
                    break
            if not json_segment:
                self.log('build_episode_menu: No segment ID found \
                    for video_id %s' % video_id)
                return
            # Generate a simple playable item for the video
            self.build_entry(json_segment, banner)

    def build_entry(self, json_entry, banner=None, is_folder=False):
        """
        Builds an list item for a video or folder by giving the json part,
        describing this video.

        Keyword arguments:
        json_entry -- the part of the json describing the video
        banner     -- URL of the show's banner (default: None)
        is_folder  -- indicates if the item is a folder (default: False)
        """
        self.log('build_entry')
        title = utils.try_get(json_entry, 'title')
        vid = utils.try_get(json_entry, 'id')
        description = utils.try_get(json_entry, 'description')
        lead = utils.try_get(json_entry, 'lead')
        image = utils.try_get(json_entry, 'imageUrl')

        # RTS image links have a strange appendix '/16x9'.
        # This needs to be removed from the URL:
        image = re.sub(r'/\d+x\d+', '', image)

        duration = utils.try_get(
            json_entry, 'duration', data_type=int, default=None)
        if duration:
            duration = duration // 1000  # needs fix for Python 3
        else:
            duration = utils.get_duration(
                utils.try_get(json_entry, 'duration'))

        date_string = utils.try_get(json_entry, 'date')
        dto = utils.parse_datetime(date_string)
        kodi_date_string = dto.strftime('%Y-%m-%d') if dto else None

        list_item = xbmcgui.ListItem(label=title)
        list_item.setInfo(
            'video',
            {
                'title': title,
                'plot': description or lead,
                'plotoutline': lead,
                'duration': duration,
                'aired': kodi_date_string,
            }
        )
        list_item.setArt({
            'thumb': image,
            'poster': image,
            'banner': banner,
        })
        subs = utils.try_get(
            json_entry, 'subtitleList', data_type=list, default=[])
        if subs and self.subtitles:
            subtitle_list = [
                utils.try_get(x, 'url') for x in subs
                if utils.try_get(x, 'format') == 'VTT']
            if subtitle_list:
                list_item.setSubtitles(subtitle_list)
            else:
                self.log('No WEBVTT subtitles found for video id %s.' % vid)
        if is_folder:
            list_item.setProperty('IsPlayable', 'false')
            url = self.build_url(mode=21, name=vid)
        else:
            list_item.setProperty('IsPlayable', 'true')
            url = self.build_url(mode=50, name=vid)
        xbmcplugin.addDirectoryItem(
            self.handle, url, list_item, isFolder=is_folder)

    def build_dates_overview_menu(self):
        """
        Builds the menu containing the folders for episodes of
        the last 10 days.
        """
        self.log('build_dates_overview_menu')

        def folder_name(dato):
            """
            Generates a Kodi folder name from an date object.

            Keyword arguments:
            dato -- a date object
            """
            weekdays = (
                self.language(30060),  # Monday
                self.language(30061),  # Tuesday
                self.language(30062),  # Wednesday
                self.language(30063),  # Thursday
                self.language(30064),  # Friday
                self.language(30065),  # Saturday
                self.language(30066)   # Sunday
            )
            today = datetime.date.today()
            if dato == today:
                name = self.language(30058)  # Today
            elif dato == today + datetime.timedelta(-1):
                name = self.language(30059)  # Yesterday
            else:
                name = '%s, %s' % (weekdays[dato.weekday()],
                                   dato.strftime('%d.%m.%Y'))
            return name

        current_date = datetime.date.today()
        number_of_days = 7

        for i in range(number_of_days):
            dato = current_date + datetime.timedelta(-i)
            list_item = xbmcgui.ListItem(label=folder_name(dato))
            list_item.setArt({'thumb': self.icon})
            name = dato.strftime('%d-%m-%Y')
            purl = self.build_url(mode=24, name=name)
            xbmcplugin.addDirectoryItem(
                handle=self.handle, url=purl,
                listitem=list_item, isFolder=True)

        choose_item = xbmcgui.ListItem(label=LANGUAGE(30071))  # Choose date
        choose_item.setArt({'thumb': self.icon})
        purl = self.build_url(mode=25)
        xbmcplugin.addDirectoryItem(
            handle=self.handle, url=purl,
            listitem=choose_item, isFolder=True)

    def pick_date(self):
        """
        Opens a date choosing dialog and lets the user input a date.
        Redirects to the date menu of the chosen date.
        In case of failure or abortion redirects to the date
        overview menu.
        """
        date_picker = xbmcgui.Dialog().numeric(
            1, LANGUAGE(30071), None)  # Choose date
        if date_picker is not None:
            date_elems = date_picker.split('/')
            try:
                day = int(date_elems[0])
                month = int(date_elems[1])
                year = int(date_elems[2])
                chosen_date = datetime.date(year, month, day)
                name = chosen_date.strftime('%d-%m-%Y')
                self.build_date_menu(name)
            except (ValueError, IndexError):
                self.log('pick_date: Invalid date chosen.')
                self.build_dates_overview_menu()
        else:
            self.build_dates_overview_menu()

    def build_date_menu(self, date_string):
        """
        Builds a list of episodes of a given date.

        Keyword arguments:
        date_string -- a string representing date in the form %d-%m-%Y,
                       e.g. 12-03-2017
        """
        self.log('build_date_menu, date_string = %s' % date_string)

        url = self.host_url + '/play/tv/programDay/%s' % date_string
        id_list = self.extract_id_list(url)

        for vid in id_list:
            self.build_episode_menu(
                vid, include_segments=False,
                segment_option=self.segments)

    def get_auth_url(self, url, segment_data=None):
        """
        Returns the authenticated URL from a given stream URL.

        Keyword arguments:
        url -- a given stream URL
        """
        self.log('get_auth_url, url = %s' % url)
        # spl = urlparse.urlparse(url).path.split('/')
        spl = urlps(url).path.split('/')
        token = json.loads(
            self.open_url(
                'http://tp.srgssr.ch/akahd/token?acl=/%s/%s/*' %
                (spl[1], spl[2]), use_cache=False)) or {}
        auth_params = token.get('token', {}).get('authparams')
        if segment_data:
            # timestep_string = self._get_timestep_token(segment_data)
            # url += ('?' if '?' not in url else '&') + timestep_string
            pass
        if auth_params:
            url += ('?' if '?' not in url else '&') + auth_params
        return url

    def play_video(self, video_id):
        """
        Gets the video stream information of a video and starts to play it.

        Keyword arguments:
        video_id -- the video of the video to play
        """
        self.log('play_video, video_id = %s' % video_id)
        json_url = ('https://il.srgssr.ch/integrationlayer/2.0/%s/'
                    'mediaComposition/video/%s.json') % (self.bu, video_id)
        self.log('play_video. Open URL %s' % json_url)
        json_response = json.loads(self.open_url(json_url))

        chapter_list = utils.try_get(
            json_response, 'chapterList', data_type=list, default=[])
        if not chapter_list:
            self.log('play_video: no stream URL found.')
            return

        first_chapter = utils.try_get(
            chapter_list, 0, data_type=dict, default={})
        chapter = next(
            (e for e in chapter_list if e.get('id') == video_id),
            first_chapter)
        resource_list = utils.try_get(
            chapter, 'resourceList', data_type=list, default=[])
        if not resource_list:
            self.log('play_video: no stream URL found.')
            return

        stream_urls = {
            'SD': '',
            'HD': '',
        }
        for resource in resource_list:
            if utils.try_get(resource, 'protocol') == 'HLS':
                for key in ('SD', 'HD'):
                    if utils.try_get(resource, 'quality') == key:
                        stream_urls[key] = utils.try_get(resource, 'url')

        if not stream_urls['SD'] and not stream_urls['HD']:
            self.log('play_video: no stream URL found.')
            return

        stream_url = stream_urls['HD'] if (
            stream_urls['HD'] and self.prefer_hd)\
            or not stream_urls['SD'] else stream_urls['SD']
        self.log('play_video, stream_url = %s' % stream_url)
        auth_url = self.get_auth_url(stream_url)

        start_time = end_time = None
        if utils.try_get(json_response, 'segmentUrn'):
            segment_list = utils.try_get(
                chapter, 'segmentList', data_type=list, default=[])
            for segment in segment_list:
                if utils.try_get(segment, 'id') == video_id:
                    start_time = utils.try_get(
                        segment, 'markIn', data_type=int, default=None)
                    if start_time:
                        start_time = start_time // 1000  # fix it for Python 3
                    end_time = utils.try_get(
                        segment, 'markOut', data_type=int, default=None)
                    if end_time:
                        end_time = end_time // 1000  # fix it for Python 3
                    break

            if start_time and end_time:
                parsed_url = urlps(auth_url)
                query_list = parse_qsl(parsed_url.query)
                updated_query_list = []
                for query in query_list:
                    if query[0] == 'start' or query[0] == 'end':
                        continue
                    updated_query_list.append(query)
                updated_query_list.append(
                    ('start', utils.CompatStr(start_time)))
                updated_query_list.append(
                    ('end', utils.CompatStr(end_time)))
                new_query = utils.assemble_query_string(updated_query_list)
                surl_result = ParseResult(
                    parsed_url.scheme, parsed_url.netloc,
                    parsed_url.path, parsed_url.params,
                    new_query, parsed_url.fragment)
                auth_url = surl_result.geturl()
        self.log('play_video, auth_url = %s' % auth_url)
        play_item = xbmcgui.ListItem(video_id, path=auth_url)
        xbmcplugin.setResolvedUrl(self.handle, True, play_item)

    def play_livestream(self, stream_url):
        """
        Plays a livestream, given a unauthenticated stream url.

        Keyword arguments:
        stream_url -- the stream url
        """
        auth_url = self.get_auth_url(stream_url)
        play_item = xbmcgui.ListItem('Live', path=auth_url)
        xbmcplugin.setResolvedUrl(self.handle, True, play_item)

    def manage_favourite_shows(self):
        """
        Opens a Kodi multiselect dialog to let the user choose
        his/her personal favourite show list.
        """
        show_list = self.read_all_available_shows()
        stored_favids = self.read_favourite_show_ids()
        names = [x['title'] for x in show_list]
        ids = [x['id'] for x in show_list]

        preselect_inds = []
        for stored_id in stored_favids:
            try:
                preselect_inds.append(ids.index(stored_id))
            except ValueError:
                pass
        ancient_ids = [x for x in stored_favids if x not in ids]

        dialog = xbmcgui.Dialog()
        # Choose your favourite shows
        selected_inds = dialog.multiselect(
            LANGUAGE(30069), names, preselect=preselect_inds)

        if selected_inds is not None:
            new_favids = [ids[ind] for ind in selected_inds]
            # Keep the old show ids:
            new_favids += ancient_ids

            self.write_favourite_show_ids(new_favids)

    def read_favourite_show_ids(self):
        """
        Reads the show ids from the file defined by the global
        variable FAVOURITE_SHOWS_FILENAMES and returns a list
        containing these ids.
        An empty list will be returned in case of failure.
        """
        path = xbmc.translatePath(
            self.real_settings.getAddonInfo('profile'))
        file_path = os.path.join(path, FAVOURITE_SHOWS_FILENAME)
        try:
            with open(file_path, 'r') as f:
                json_file = json.load(f)
                try:
                    return [entry['id'] for entry in json_file]
                except KeyError:
                    self.log('Unexpected file structure for %s.' %
                             FAVOURITE_SHOWS_FILENAME)
                    return []
        except (IOError, TypeError):
            return []

    def write_favourite_show_ids(self, show_ids):
        """
        Writes a list of show ids to the file defined by the global
        variable FAVOURITE_SHOWS_FILENAME.

        Keyword arguments:
        show_ids -- a list of show ids (as strings)
        """
        show_ids_dict_list = [{'id': show_id} for show_id in show_ids]
        path = xbmc.translatePath(
            self.real_settings.getAddonInfo('profile'))
        file_path = os.path.join(path, FAVOURITE_SHOWS_FILENAME)
        if not os.path.exists(path):
            os.makedirs(path)
        with open(file_path, 'w') as f:
            json.dump(show_ids_dict_list, f)

    # Live TV is currently not supported due to recently added DRM protection:
    #
    # https://www.srf.ch/sendungen/hallosrf/weshalb-funktioniert-der-livestream-auf-srf-ch-nicht-mehr
    # https://rtsr.ch/digitalrightsmanagement/
    # https://www.rsi.ch/chi-siamo/mestieri/La-SSR-introduce-la-codifica-digitale-11038056.html
    #
    #
    # def build_tv_menu(self):
    #     """
    #     Builds the overview over the TV channels.
    #     """
    #     overview_url = '%s/play/tv/live/overview' % self.host_url
    #     overview_json = json.loads(
    #         self.open_url(overview_url, use_cache=False))
    #     urns = [utils.try_get(x, 'urn') for x in utils.try_get(
    #         overview_json, 'teaser', data_type=list, default=[])
    #         if utils.try_get(x, 'urn')]
    #     for urn in urns:
    #         json_url = ('https://il.srgssr.ch/integrationlayer/2.0/'
    #                     'mediaComposition/byUrn/%s.json') % urn
    #         info_json = json.loads(self.open_url(json_url, use_cache=False))
    #         json_entry = utils.try_get(
    #             info_json, ('chapterList', 0), data_type=dict, default={})
    #         if not json_entry:
    #             self.log('build_tv_menu: Unexpected json structure '
    #                      'for element %s' % urn)
    #             continue
    #         self.build_entry(json_entry)

    def build_live_menu(self, extract_srf3=False):
        """
        Builds the menu listing the currently available livestreams.
        """
        def get_live_ids():
            """
            Downloads the main webpage and scrapes it for
            possible livestreams. If some live events were found, a list
            of live ids will be returned, otherwise an empty list.
            """
            live_ids = []
            webpage = self.open_url(self.host_url, use_cache=False)
            event_id_regex = r'(?:data-sport-id=\"|eventId=)(?P<live_id>\d+)'
            try:
                for match in re.finditer(event_id_regex, webpage):
                    live_ids.append(match.group('live_id'))
            except StopIteration:
                pass
            return live_ids

        def get_srf3_live_ids():
            """
            Returns a list of Radio SRF 3 video streams.
            """
            url = 'https://www.srf.ch/radio-srf-3'
            webpage = self.open_url(url, use_cache=False)
            video_id_regex = r'''(?x)
                                   popupvideoplayer\?id=
                                   (?P<video_id>
                                       [a-f0-9]{8}-
                                       [a-f0-9]{4}-
                                       [a-f0-9]{4}-
                                       [a-f0-9]{4}-
                                       [a-f0-9]{12}
                                    )
                                '''
            live_ids = []
            try:
                for match in re.finditer(video_id_regex, webpage):
                    live_ids.append(match.group('video_id'))
            except StopIteration:
                pass
            return live_ids
        live_ids = get_live_ids()
        for lid in live_ids:
            api_url = ('https://event.api.swisstxt.ch/v1/events/'
                       '%s/byEventItemId/?eids=%s') % (self.bu, lid)
            live_json = json.loads(self.open_url(api_url))
            entry = utils.try_get(live_json, 0, data_type=dict, default={})
            if not entry:
                self.log('build_live_menu: No entry found '
                         'for live id %s.' % lid)
                continue
            if utils.try_get(entry, 'streamType') == 'noStream':
                continue
            title = utils.try_get(entry, 'title')
            stream_url = utils.try_get(entry, 'hls')
            image = utils.try_get(entry, 'imageUrl')
            item = xbmcgui.ListItem(label=title)
            item.setProperty('IsPlayable', 'true')
            item.setArt({'thumb': image})
            purl = self.build_url(mode=51, name=stream_url)
            xbmcplugin.addDirectoryItem(
                self.handle, purl, item, isFolder=False)
        if extract_srf3:
            srf3_ids = get_srf3_live_ids()
            for vid in srf3_ids:
                self.build_episode_menu(vid, include_segments=False)

    def _read_youtube_channels(self, fname):
        """
        Reads YouTube channel IDs from a specified file and returns a list
        of these channel IDs.

        Keyword arguments:
        fname  -- the path to the file to be read
        """
        data_file = os.path.join(xbmc.translatePath(self.data_uri), fname)
        with open(data_file, 'r') as f:
            ch_content = json.load(f)
            cids = [elem['channel'] for elem in ch_content.get('channels', [])]
            return cids
        return []

    def get_youtube_channel_ids(self):
        """
        Uses the cache to generate a list of the stored YouTube channel IDs.
        """
        cache_identifier = self.addon_id + '.youtube_channel_ids'
        channel_ids = self.cache.get(cache_identifier)
        if not channel_ids:
            self.log('get_youtube_channel_ids: Caching YouTube channel ids.'
                     'This log message should not appear too many times.')
            channel_ids = self._read_youtube_channels(
                YOUTUBE_CHANNELS_FILENAME)
            self.cache.set(cache_identifier, channel_ids)
        return channel_ids

    def build_youtube_main_menu(self):
        """
        Builds the main YouTube menu.
        """
        items = [{
            'name': LANGUAGE(30110),
            'mode': 31,
        }, {
            'name': LANGUAGE(30111),
            'mode': 32,
        }]

        for item in items:
            list_item = xbmcgui.ListItem(label=item['name'])
            list_item.setProperty('IsPlayable', 'false')
            list_item.setArt({
                'icon': self.get_youtube_icon(),
            })
            purl = self.build_url(mode=item['mode'])
            xbmcplugin.addDirectoryItem(
                self.handle, purl, list_item, isFolder=True)

    def build_youtube_channel_overview_menu(self, mode):
        """
        Builds a menu of folders containing the plugin's
        YouTube channels.

        Keyword arguments:
        channel_ids  -- a list of YouTube channel IDs
        mode         -- the plugin's URL mode
        """
        channel_ids = self.get_youtube_channel_ids()
        plugin_url = self.build_url(mode=mode, name='%s')
        youtube_channels.YoutubeChannels(
            self.handle, channel_ids,
            self.addon_id, self.debug).build_channel_overview_menu(
                plugin_channel_url=plugin_url)

    def build_youtube_channel_menu(self, cid, mode, page=1, page_token=''):
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
            self.handle, channel_ids,
            self.addon_id, self.debug).build_channel_menu(
                cid, page_token=page_token)
        if next_page_token:
            next_item = xbmcgui.ListItem(label='>> ' + LANGUAGE(30073))
            next_url = self.build_url(
                mode=mode, name=cid, page_hash=next_page_token)
            next_item.setProperty('IsPlayable', 'false')
            xbmcplugin.addDirectoryItem(
                self.handle, next_url, next_item, isFolder=True)

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
            self.handle, channel_ids,
            self.addon_id, self.debug).build_newest_videos(page=page)
        if next_page:
            next_item = xbmcgui.ListItem(label='>> ' + LANGUAGE(30073))
            next_url = self.build_url(mode=mode, page=next_page)
            next_item.setProperty('IsPlayable', 'false')
            xbmcplugin.addDirectoryItem(
                self.handle, next_url, next_item, isFolder=True)
