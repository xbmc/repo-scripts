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

from urllib.parse import quote_plus, parse_qsl, ParseResult
from urllib.parse import urlparse as urlps

import os
import sys
import re
import traceback
import datetime
import json
import requests
import utils

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs

import inputstreamhelper
import simplecache
import youtube_channels


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
RECENT_MEDIA_SEARCHES_FILENAME = 'recently_searched_medias.json'


def get_params():
    """
    Parses the Kodi plugin URL and returns its parameters
    in a dictionary.
    """
    return dict(parse_qsl(sys.argv[2][1:]))


class SRGSSR:
    """
    Base class for all SRG SSR related plugins.
    Everything that can be done independently from the business unit
    (SRF, RTS, RSI, etc.) should be done here.
    """
    def __init__(self, plugin_handle, bu='srf', addon_id=ADDON_ID):
        self.handle = plugin_handle
        self.cache = simplecache.SimpleCache()
        self.real_settings = xbmcaddon.Addon(id=addon_id)
        self.bu = bu
        self.addon_id = addon_id
        self.icon = self.real_settings.getAddonInfo('icon')
        self.fanart = self.real_settings.getAddonInfo('fanart')
        self.language = LANGUAGE
        self.plugin_language = self.real_settings.getLocalizedString
        self.host_url = f'https://www.{bu}.ch'
        if bu == 'swi':
            self.host_url = 'https://play.swissinfo.ch'
        self.playtv_url = f'{self.host_url}/play/tv'
        self.apiv3_url = f'{self.host_url}/play/v3/api/{bu}/production/'
        self.data_regex = \
            r'<script>window.__SSR_VIDEO_DATA__\s*=\s*(.+?)</script>'
        self.data_uri = f'special://home/addons/{self.addon_id}/resources/data'
        self.media_uri = \
            f'special://home/addons/{self.addon_id}/resources/media'

        # Plugin options:
        self.debug = self.get_boolean_setting('Enable_Debugging')
        self.subtitles = self.get_boolean_setting('Extract_Subtitles')
        self.prefer_hd = self.get_boolean_setting('Prefer_HD')

        # Delete temporary subtitle files urn*.vtt
        clean_dir = 'special://temp'
        _, filenames = xbmcvfs.listdir(clean_dir)
        for filename in filenames:
            if filename.startswith('urn') and filename.endswith('.vtt'):
                xbmcvfs.delete(clean_dir + '/' + filename)

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
        try:
            mode = str(mode)
        except Exception:
            pass
        try:
            page = str(page)
        except Exception:
            pass
        added = False
        queries = (url, mode, name, page_hash, page)
        query_names = ('url', 'mode', 'name', 'page_hash', 'page')
        purl = sys.argv[0]
        for query, qname in zip(queries, query_names):
            if query:
                add = '?' if not added else '&'
                qplus = quote_plus(query)
                purl += f'{add}{qname}={qplus}'
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
                f'{ADDON_NAME}.open_url, url = {url}')
        if not cache_response:
            headers = {
                'User-Agent': ('Mozilla/5.0 (X11; Linux x86_64; rv:59.0)'
                               'Gecko/20100101 Firefox/59.0'),
            }
            response = requests.get(url, headers=headers)
            if not response.ok:
                self.log(f'open_url: Failed to open url {url}')
                xbmcgui.Dialog().notification(
                    ADDON_NAME, LANGUAGE(30100), ICON, 4000)
                return ''
            self.cache.set(
                f'{ADDON_NAME}.open_url, url = {url}',
                response.text,
                expiration=datetime.timedelta(hours=2))
            return response.text
        return self.cache.get(f'{ADDON_NAME}.open_url, url = {url}')

    def build_main_menu(self, identifiers=[]):
        """
        Builds the main menu of the plugin:

        Keyword arguments:
        identifiers  -- A list of strings containing the identifiers
                        of the menus to display.
        """
        self.log('build_main_menu')

        def display_item(item):
            return item in identifiers and self.get_boolean_setting(item)

        main_menu_list = [
            {
                # All shows
                'identifier': 'All_Shows',
                'name': self.plugin_language(30050),
                'mode': 10,
                'displayItem': display_item('All_Shows'),
                'icon': self.icon,
            }, {
                # Favourite shows
                'identifier': 'Favourite_Shows',
                'name': self.plugin_language(30051),
                'mode': 11,
                'displayItem': display_item('Favourite_Shows'),
                'icon': self.icon,
            }, {
                # Newest favourite shows
                'identifier': 'Newest_Favourite_Shows',
                'name': self.plugin_language(30052),
                'mode': 12,
                'displayItem': display_item('Newest_Favourite_Shows'),
                'icon': self.icon,
            }, {
                # Topics
                'identifier': 'Topics',
                'name': self.plugin_language(30058),
                'mode': 13,
                'displayItem': display_item('Topics'),
                'icon': self.icon,
            }, {
                # Most searched TV shows
                'identifier': 'Most_Searched_TV_Shows',
                'name': self.plugin_language(30059),
                'mode': 14,
                'displayItem': display_item('Most_Searched_TV_Shows'),
                'icon': self.icon,
            }, {
                # Shows by date
                'identifier': 'Shows_By_Date',
                'name': self.plugin_language(30057),
                'mode': 17,
                'displayItem': display_item('Shows_By_Date'),
                'icon': self.icon,
            }, {
                # Live TV
                'identifier': 'Live_TV',
                'name': self.plugin_language(30072),
                'mode': 26,
                'displayItem': False,  # currently not supported
                'icon': self.icon,
            }, {
                # SRF.ch live
                'identifier': 'SRF_Live',
                'name': self.plugin_language(30070),
                'mode': 18,
                'displayItem': False,  # currently not supported
                'icon': self.icon,
            }, {
                # Search
                'identifier': 'Search',
                'name': self.plugin_language(30085),
                'mode': 27,
                'displayItem': display_item('Search'),
                'icon': self.icon,
            }, {
                # Homepage
                'identifier': 'Homepage',
                'name': self.plugin_language(30060),
                'mode': 200,
                'displayItem': display_item('Homepage'),
                'icon': self.icon,
            }, {
                # YouTube
                'identifier': f'{self.bu.upper()}_YouTube',
                'name': self.plugin_language(30074),
                'mode': 30,
                'displayItem': display_item(f'{self.bu.upper()}_YouTube'),
                'icon': self.get_youtube_icon(),
            }
        ]
        folders = []
        for ide in identifiers:
            item = next((e for e in main_menu_list if
                         e['identifier'] == ide), None)
            if item:
                folders.append(item)
        self.build_folder_menu(folders)

    def build_folder_menu(self, folders):
        """
        Builds a menu from a list of folder dictionaries. Each dictionary
        must have the key 'name' and can have the keys 'identifier', 'mode',
        'displayItem', 'icon', 'purl' (a dictionary to build the plugin url).
        """
        for item in folders:
            if item.get('displayItem'):
                list_item = xbmcgui.ListItem(label=item['name'])
                list_item.setProperty('IsPlayable', 'false')
                list_item.setArt({
                    'thumb': item['icon'],
                    'fanart': self.fanart})
                purl_dict = item.get('purl', {})
                mode = purl_dict.get('mode') or item.get('mode')
                uname = purl_dict.get('name') or item.get('identifier')
                purl = self.build_url(
                    mode=mode, name=uname)
                xbmcplugin.addDirectoryItem(
                    handle=self.handle, url=purl,
                    listitem=list_item, isFolder=True)

    def build_menu_apiv3(self, queries, mode=1000, page=1, page_hash=None,
                         is_show=False, whitelist_ids=None):
        """
        Builds a menu based on the API v3, which is supposed to be more stable

        Keyword arguments:
        queries       -- the query string or a list of several queries
        mode          -- mode for the URL of the next folder
        page          -- current page; if page is set to 0, do not build
                         a next page button
        page_hash     -- cursor for fetching the next items
        is_show       -- indicates if the menu contains only shows
        whitelist_ids -- list of ids that should be displayed, if it is set
                         to `None` it will be ignored
        """
        if isinstance(queries, list):
            # Build a combined and sorted list for several queries
            items = []
            for query in queries:
                data = json.loads(self.open_url(self.apiv3_url + query))
                if data:
                    data = utils.try_get(data, ['data', 'data'], list, []) or \
                        utils.try_get(data, ['data', 'medias'], list, []) or \
                        utils.try_get(data, ['data', 'results'], list, []) or \
                        utils.try_get(data, 'data', list, [])
                    for item in data:
                        items.append(item)

            items.sort(key=lambda item: item['date'], reverse=True)
            for item in items:
                self.build_entry_apiv3(
                    item, is_show=is_show, whitelist_ids=whitelist_ids)
            return

        if page_hash:
            cursor = page_hash
        else:
            cursor = None

        if cursor:
            symb = '&' if '?' in queries else '?'
            url = f'{self.apiv3_url}{queries}{symb}next={cursor}'
            data = json.loads(self.open_url(url))
        else:
            data = json.loads(self.open_url(self.apiv3_url + queries))
        cursor = utils.try_get(data, 'next') or utils.try_get(
            data, ['data', 'next'])

        try:
            data = data['data']
        except Exception:
            self.log('No media found.')
            return

        items = utils.try_get(data, 'data', list, []) or \
            utils.try_get(data, 'medias', list, []) or \
            utils.try_get(data, 'results', list, []) or data

        for item in items:
            self.build_entry_apiv3(
                item, is_show=is_show, whitelist_ids=whitelist_ids)

        if cursor:
            if page == 0 or page == '0':
                return

            # Next page urls containing the string 'urns=' do not work
            # properly. So in this case prevent the next page button from
            # being created. Note that might lead to not having a next
            # page butten where there should be one.
            if 'urns=' in cursor:
                return

            if page:
                url = self.build_url(
                    mode=mode, name=queries, page=int(page)+1,
                    page_hash=cursor)
            else:
                url = self.build_url(
                    mode=mode, name=queries, page=2, page_hash=cursor)

            next_item = xbmcgui.ListItem(
                label='>> ' + LANGUAGE(30073))  # Next page
            next_item.setProperty('IsPlayable', 'false')
            xbmcplugin.addDirectoryItem(
                self.handle, url, next_item, isFolder=True)

    def read_all_available_shows(self):
        """
        Downloads a list of all available shows and returns this list.

        This works for the business units 'srf', 'rts', 'rsi' and 'rtr', but
        not for 'swi'.
        """
        data = json.loads(self.open_url(self.apiv3_url + 'shows'))
        return utils.try_get(data, 'data', list, [])

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
        self.build_menu_apiv3('shows', is_show=True, whitelist_ids=favids)

    def build_favourite_shows_menu(self):
        """
        Builds a list of folders for the favourite shows.
        """
        self.log('build_favourite_shows_menu')
        self.build_all_shows_menu(favids=self.read_favourite_show_ids())

    def build_topics_menu(self):
        """
        Builds a menu containing the topics from the SRGSSR API.
        """
        self.build_menu_apiv3('topics')

    def build_most_searched_shows_menu(self):
        """
        Builds a menu containing the most searched TV shows from
        the SRGSSR API.
        """
        self.build_menu_apiv3('search/most-searched-tv-shows', is_show=True)

    def build_newest_favourite_menu(self, page=1):
        """
        Builds a Kodi list of the newest favourite shows.

        Keyword arguments:
        page -- an integer indicating the current page on the
                list (default: 1)
        """
        self.log('build_newest_favourite_menu')
        show_ids = self.read_favourite_show_ids()

        queries = []
        for sid in show_ids:
            queries.append('videos-by-show-id?showId=' + sid)
        return self.build_menu_apiv3(queries)

    def build_homepage_menu(self):
        """
        Builds the homepage menu.
        """
        self.build_menu_from_page(self.playtv_url, (
            'initialData', 'pacPageConfigs', 'videoHomeSections'))

    def build_menu_from_page(self, url, path):
        """
        Builds a menu by extracting some content directly from a website.

        Keyword arguments:
        url     -- the url of the website
        path    -- the path to the relevant data in the json (as tuple
                   or list of strings)
        """
        html = self.open_url(url)
        m = re.search(self.data_regex, html)
        if not m:
            self.log('build_menu_from_page: No data found in html')
            return
        content = m.groups()[0]
        try:
            js = json.loads(content)
        except Exception:
            self.log('build_menu_from_page: Invalid json')
            return
        data = utils.try_get(js, path, list, [])
        if not data:
            self.log('build_menu_from_page: Could not find any data in json')
            return
        for elem in data:
            try:
                id = elem['id']
                section_type = elem['sectionType']
                title = utils.try_get(elem, ('representation', 'title'))
                if section_type in ('MediaSection', 'ShowSection',
                                    'MediaSectionWithShow'):
                    if section_type == 'MediaSection' and not title and \
                            utils.try_get(
                                elem, ('representation', 'name')
                            ) == 'HeroStage':
                        title = self.language(30053)
                    if not title:
                        continue
                    list_item = xbmcgui.ListItem(label=title)
                    list_item.setArt({
                        'thumb': self.icon,
                        'fanart': self.fanart,
                    })
                    if section_type == 'MediaSection':
                        name = f'media-section?sectionId={id}'
                    elif section_type == 'ShowSection':
                        name = f'show-section?sectionId={id}'
                    elif section_type == 'MediaSectionWithShow':
                        name = f'media-section-with-show?sectionId={id}'
                    url = self.build_url(mode=1000, name=name, page=1)
                    xbmcplugin.addDirectoryItem(
                        self.handle, url, list_item, isFolder=True)
            except Exception:
                pass

    def build_episode_menu(self, video_id_or_urn, include_segments=True,
                           segment_option=False, audio=False):
        """
        Builds a list entry for a episode by a given video id.
        The segment entries for that episode can be included too.
        The video id can be an id of a segment. In this case an
        entry for the segment will be created.

        Keyword arguments:
        video_id_or_urn  -- the video id or the urn
        include_segments -- indicates if the segments (if available) of the
                            video should be included in the list
                            (default: True)
        segment_option   -- Which segment option to use.
                            (default: False)
        audio            -- boolean value to indicate if the episode is a
                            radio show (default: False)
        """
        self.log(f'build_episode_menu, video_id_or_urn = {video_id_or_urn}')
        content_type = 'audio' if audio else 'video'
        if ':' in video_id_or_urn:
            json_url = 'https://il.srgssr.ch/integrationlayer/2.0/' \
                       f'mediaComposition/byUrn/{video_id_or_urn}.json'
            video_id = video_id_or_urn.split(':')[-1]
        else:
            json_url = f'https://il.srgssr.ch/integrationlayer/2.0/{self.bu}' \
                       f'/mediaComposition/{content_type}/{video_id_or_urn}' \
                        '.json'
            video_id = video_id_or_urn
        self.log(f'build_episode_menu. Open URL {json_url}')
        try:
            json_response = json.loads(self.open_url(json_url))
        except Exception:
            self.log(
                f'build_episode_menu: Cannot open json for {video_id_or_urn}.')
            return

        chapter_urn = utils.try_get(json_response, 'chapterUrn')
        segment_urn = utils.try_get(json_response, 'segmentUrn')

        chapter_id = chapter_urn.split(':')[-1] if chapter_urn else None
        segment_id = segment_urn.split(':')[-1] if segment_urn else None

        if not chapter_id:
            self.log(f'build_episode_menu: No valid chapter URN \
                available for video_id {video_id}')
            return

        show_image_url = utils.try_get(json_response, ['show', 'imageUrl'])
        show_poster_image_url = utils.try_get(
            json_response, ['show', 'posterImageUrl'])

        json_chapter_list = utils.try_get(
            json_response, 'chapterList', data_type=list, default=[])
        json_chapter = None
        chapter_index = -1
        for (ind, chapter) in enumerate(json_chapter_list):
            if utils.try_get(chapter, 'id') == chapter_id:
                json_chapter = chapter
                chapter_index = ind
                break
        if not json_chapter:
            self.log(f'build_episode_menu: No chapter ID found \
                for video_id {video_id}')
            return

        # TODO: Simplify
        json_segment_list = utils.try_get(
            json_chapter, 'segmentList', data_type=list, default=[])
        if video_id == chapter_id:
            if include_segments:
                # Generate entries for the whole video and
                # all the segments of this video.
                self.build_entry(
                    json_chapter, show_image_url=show_image_url,
                    show_poster_image_url=show_poster_image_url)

                if audio and chapter_index == 0:
                    for aid in json_chapter_list[1:]:
                        self.build_entry(
                            aid, show_image_url=show_image_url,
                            show_poster_image_url=show_poster_image_url)

                for segment in json_segment_list:
                    self.build_entry(
                        segment, show_image_url=show_image_url,
                        show_poster_image_url=show_poster_image_url)
            else:
                if segment_option and json_segment_list:
                    # Generate a folder for the video
                    self.build_entry(
                        json_chapter, is_folder=True,
                        show_image_url=show_image_url,
                        show_poster_image_url=show_poster_image_url)
                else:
                    # Generate a simple playable item for the video
                    self.build_entry(
                        json_chapter, show_image_url=show_image_url,
                        show_poster_image_url=show_poster_image_url)
        else:
            json_segment = None
            for segment in json_segment_list:
                if utils.try_get(segment, 'id') == segment_id:
                    json_segment = segment
                    break
            if not json_segment:
                self.log(f'build_episode_menu: No segment ID found \
                    for video_id {video_id}')
                return
            # Generate a simple playable item for the video
            self.build_entry(
                json_segment, show_image_url=show_image_url,
                show_poster_image_url=show_poster_image_url)

    def build_entry_apiv3(self, data, is_show=False, whitelist_ids=None):
        """
        Builds a entry from a APIv3 JSON data entry.

        Keyword arguments:
        data            -- The JSON entry
        whitelist_ids   -- If not `None` only items with an id that is in that
                           list will be generated (default: None)
        """
        urn = data['urn']
        self.log(f'build_entry_apiv3: urn = {urn}')
        title = utils.try_get(data, 'title')
        media_id = utils.try_get(data, 'id')
        if whitelist_ids is not None and media_id not in whitelist_ids:
            return
        description = utils.try_get(data, 'description')
        lead = utils.try_get(data, 'lead')
        image_url = utils.try_get(data, 'imageUrl')
        poster_image_url = utils.try_get(data, 'posterImageUrl')
        show_image_url = utils.try_get(data, ['show', 'imageUrl'])
        show_poster_image_url = utils.try_get(data, ['show', 'posterImageUrl'])
        duration = utils.try_get(data, 'duration', int, default=None)
        if duration:
            duration //= 1000
        date = utils.try_get(data, 'date')
        kodi_date_string = date
        dto = utils.parse_datetime(date)
        kodi_date_string = dto.strftime('%Y-%m-%d') if dto else None
        label = title or urn
        list_item = xbmcgui.ListItem(label=label)
        list_item.setInfo(
            'video',
            {
                'title': title,
                'plot': description or lead,
                'plotoutline': lead or description,
                'duration': duration,
                'aired': kodi_date_string,
            }
        )
        if is_show:
            poster = show_poster_image_url or poster_image_url or \
                show_image_url or image_url
        else:
            poster = image_url or poster_image_url or \
                show_poster_image_url or show_image_url
        list_item.setArt({
            'thumb': image_url,
            'poster': poster,
            'fanart': show_image_url or self.fanart,
            'banner': show_image_url or image_url,
        })
        url = self.build_url(mode=100, name=urn)
        is_folder = True

        xbmcplugin.addDirectoryItem(
            self.handle, url, list_item, isFolder=is_folder)

    def build_menu_by_urn(self, urn):
        """
        Builds a menu from an urn.

        Keyword arguments:
        urn     -- The urn (e.g. 'urn:srf:show:<id>' or 'urn:rts:video:<id>')
        """
        id = urn.split(':')[-1]
        if 'show' in urn:
            self.build_menu_apiv3(f'videos-by-show-id?showId={id}')
        elif 'swisstxt' in urn:
            # Do not include segments for livestreams,
            # they fail to play.
            self.build_episode_menu(urn, include_segments=False)
        elif 'video' in urn:
            self.build_episode_menu(id)
        elif 'topic' in urn:
            self.build_menu_from_page(self.playtv_url, (
                'initialData', 'pacPageConfigs', 'topicSections', urn))

    def build_entry(self, json_entry, is_folder=False, audio=False,
                    fanart=None, urn=None, show_image_url=None,
                    show_poster_image_url=None):
        """
        Builds an list item for a video or folder by giving the json part,
        describing this video.

        Keyword arguments:
        json_entry              -- the part of the json describing the video
        is_folder               -- indicates if the item is a folder
                                   (default: False)
        audio                   -- boolean value to indicate if the entry
                                   contains audio (default: False)
        fanart                  -- fanart to be used instead of default image
        urn                     -- override urn from json_entry
        show_image_url          -- url of the image of the show
        show_poster_image_url   -- url of the poster image of the show
        """
        self.log('build_entry')
        title = utils.try_get(json_entry, 'title')
        vid = utils.try_get(json_entry, 'id')
        description = utils.try_get(json_entry, 'description')
        lead = utils.try_get(json_entry, 'lead')
        image_url = utils.try_get(json_entry, 'imageUrl')
        poster_image_url = utils.try_get(json_entry, 'posterImageUrl')
        if not urn:
            urn = utils.try_get(json_entry, 'urn')

        # RTS image links have a strange appendix '/16x9'.
        # This needs to be removed from the URL:
        image_url = re.sub(r'/\d+x\d+', '', image_url)

        duration = utils.try_get(
            json_entry, 'duration', data_type=int, default=None)
        if duration:
            duration = duration // 1000
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

        if not fanart:
            fanart = image_url

        poster = image_url or poster_image_url or \
            show_poster_image_url or show_image_url
        list_item.setArt({
            'thumb': image_url,
            'poster': poster,
            'fanart': show_image_url or fanart,
            'banner': show_image_url or image_url,
        })

        if not audio:
            subs = utils.try_get(
                json_entry, 'subtitleList', data_type=list, default=[])
            if subs and self.subtitles:
                subtitle_list = [
                    utils.try_get(x, 'url') for x in subs
                    if utils.try_get(x, 'format') == 'VTT']
                if subtitle_list:
                    list_item.setSubtitles(subtitle_list)
                else:
                    self.log(f'No WEBVTT subtitles found for video id {vid}.')

        # TODO:
        # Prefer urn over vid as it contains already all data
        # (bu, media type, id) and will be used anyway for the stream lookup
        # name = urn if urn else vid
        name = vid

        if is_folder:
            list_item.setProperty('IsPlayable', 'false')
            url = self.build_url(mode=21, name=name)
        else:
            list_item.setProperty('IsPlayable', 'true')
            # TODO: Simplify this, use URN instead of video id everywhere
            if 'swisstxt' in urn:
                url = self.build_url(mode=50, name=urn)
            else:
                url = self.build_url(mode=50, name=name)
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
            list_item.setArt({'thumb': self.icon, 'fanart': self.fanart})
            name = dato.strftime('%d-%m-%Y')
            purl = self.build_url(mode=24, name=name)
            xbmcplugin.addDirectoryItem(
                handle=self.handle, url=purl,
                listitem=list_item, isFolder=True)

        choose_item = xbmcgui.ListItem(label=LANGUAGE(30071))  # Choose date
        choose_item.setArt({'thumb': self.icon, 'fanart': self.fanart})
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
        self.log(f'build_date_menu, date_string = {date_string}')

        # API v3 use the date in sortable format, i.e. year first
        elems = date_string.split('-')
        query = f'videos-by-date/{elems[2]}-{elems[1]}-{elems[0]}'
        return self.build_menu_apiv3(query)

    def build_search_menu(self):
        """
        Builds a menu for searches.
        """
        items = [
            {
                # 'Search videos'
                'name': LANGUAGE(30112),
                'mode': 28,
                'show': True,
                'icon': self.icon,
            }, {
                # 'Recently searched videos'
                'name': LANGUAGE(30116),
                'mode': 70,
                'show': True,
                'icon': self.icon,
            }
        ]
        for item in items:
            if not item['show']:
                continue
            list_item = xbmcgui.ListItem(label=item['name'])
            list_item.setProperty('IsPlayable', 'false')
            list_item.setArt({'thumb': item['icon'], 'fanart': self.fanart})
            url = self.build_url(item['mode'])
            xbmcplugin.addDirectoryItem(
                handle=self.handle, url=url, listitem=list_item, isFolder=True)

    def build_recent_search_menu(self):
        """
        Lists folders for the most recent searches.
        """
        recent_searches = self.read_searches(RECENT_MEDIA_SEARCHES_FILENAME)
        mode = 28
        for search in recent_searches:
            list_item = xbmcgui.ListItem(label=search)
            list_item.setProperty('IsPlayable', 'false')
            list_item.setArt({'thumb': self.icon})
            url = self.build_url(mode=mode, name=search)
            xbmcplugin.addDirectoryItem(
                handle=self.handle, url=url, listitem=list_item, isFolder=True)

    def build_search_media_menu(self, mode=28, name='', page=1, page_hash=''):
        """
        Sets up a search for media. If called without name, a dialog will
        show up for a search input. Then the search will be performed and
        the results will be shown in a menu.

        Keyword arguments:
        mode       -- the plugins mode (default: 28)
        name       -- the search name (default: '')
        page       -- the page number (default: 1)
        page_hash  -- the page hash when coming from a previous page
                      (default: '')
        """
        self.log(f'build_search_media_menu, mode = {mode}, name = {name}, \
            page = {page}, page_hash = {page_hash}')
        media_type = 'video'
        if name:
            # `name` is provided by `next_page` folder or
            # by previously performed search
            query_string = name
            if not page_hash:
                # `name` is provided by previously performed search, so it
                # needs to be processed first
                query_string = quote_plus(query_string)
                query = f'search/media?searchTerm={query_string}'
        else:
            dialog = xbmcgui.Dialog()
            query_string = dialog.input(LANGUAGE(30115))
            if not query_string:
                self.log('build_search_media_menu: No input provided')
                return
            self.write_search(RECENT_MEDIA_SEARCHES_FILENAME, query_string)
            query_string = quote_plus(query_string)
            query = f'search/media?searchTerm={query_string}'

        query = f'{query}&mediaType={media_type}&includeAggregations=false'
        cursor = page_hash if page_hash else ''
        return self.build_menu_apiv3(query, page_hash=cursor)

    def get_auth_url(self, url, segment_data=None):
        """
        Returns the authenticated URL from a given stream URL.

        Keyword arguments:
        url -- a given stream URL
        """
        self.log(f'get_auth_url, url = {url}')
        spl = urlps(url).path.split('/')
        token = json.loads(
            self.open_url(
                f'http://tp.srgssr.ch/akahd/token?acl=/{spl[1]}/{spl[2]}/*',
                use_cache=False)) or {}
        auth_params = token.get('token', {}).get('authparams')
        if auth_params:
            url += ('?' if '?' not in url else '&') + auth_params
        return url

    def play_video(self, media_id_or_urn):
        """
        Gets the stream information starts to play it.

        Keyword arguments:
        media_id_or_urn -- the urn or id of the media to play
        """
        if media_id_or_urn.startswith('urn:'):
            urn = media_id_or_urn
            media_id = media_id_or_urn.split(':')[-1]
        else:
            # TODO: Could fail for livestreams
            media_type = 'video'
            urn = 'urn:' + self.bu + ':' + media_type + ':' + media_id_or_urn
            media_id = media_id_or_urn
        self.log('play_video, urn = ' + urn + ', media_id = ' + media_id)

        detail_url = ('https://il.srgssr.ch/integrationlayer/2.0/'
                      'mediaComposition/byUrn/' + urn)
        json_response = json.loads(self.open_url(detail_url))
        title = utils.try_get(json_response, ['episode', 'title'], str, urn)

        chapter_list = utils.try_get(
            json_response, 'chapterList', data_type=list, default=[])
        if not chapter_list:
            self.log('play_video: no stream URL found (chapterList empty).')
            return

        first_chapter = utils.try_get(
            chapter_list, 0, data_type=dict, default={})
        chapter = next(
            (e for e in chapter_list if e.get('id') == media_id),
            first_chapter)
        resource_list = utils.try_get(
            chapter, 'resourceList', data_type=list, default=[])
        if not resource_list:
            self.log('play_video: no stream URL found. (resourceList empty)')
            return

        stream_urls = {
            'SD': '',
            'HD': '',
        }

        mf_type = 'hls'
        drm = False
        for resource in resource_list:
            if utils.try_get(resource, 'drmList', data_type=list, default=[]):
                drm = True
                break

            if utils.try_get(resource, 'protocol') == 'HLS':
                for key in ('SD', 'HD'):
                    if utils.try_get(resource, 'quality') == key:
                        stream_urls[key] = utils.try_get(resource, 'url')

        if drm:
            self.play_drm(urn, title, resource_list)
            return

        if not stream_urls['SD'] and not stream_urls['HD']:
            self.log('play_video: no stream URL found.')
            return

        stream_url = stream_urls['HD'] if (
            stream_urls['HD'] and self.prefer_hd)\
            or not stream_urls['SD'] else stream_urls['SD']
        self.log(f'play_video, stream_url = {stream_url}')

        auth_url = self.get_auth_url(stream_url)

        start_time = end_time = None
        if utils.try_get(json_response, 'segmentUrn'):
            segment_list = utils.try_get(
                chapter, 'segmentList', data_type=list, default=[])
            for segment in segment_list:
                if utils.try_get(segment, 'id') == media_id or \
                                utils.try_get(segment, 'urn') == urn:
                    start_time = utils.try_get(
                        segment, 'markIn', data_type=int, default=None)
                    if start_time:
                        start_time = start_time // 1000
                    end_time = utils.try_get(
                        segment, 'markOut', data_type=int, default=None)
                    if end_time:
                        end_time = end_time // 1000
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
                    ('start', str(start_time)))
                updated_query_list.append(
                    ('end', str(end_time)))
                new_query = utils.assemble_query_string(updated_query_list)
                surl_result = ParseResult(
                    parsed_url.scheme, parsed_url.netloc,
                    parsed_url.path, parsed_url.params,
                    new_query, parsed_url.fragment)
                auth_url = surl_result.geturl()
        self.log(f'play_video, auth_url = {auth_url}')
        play_item = xbmcgui.ListItem(title, path=auth_url)
        if self.subtitles:
            subs = self.get_subtitles(stream_url, urn)
            if subs:
                play_item.setSubtitles(subs)

        play_item.setProperty('inputstream', 'inputstream.adaptive')
        play_item.setProperty('inputstream.adaptive.manifest_type', mf_type)
        play_item.setProperty('IsPlayable', 'true')

        xbmcplugin.setResolvedUrl(self.handle, True, play_item)

    def play_drm(self, urn, title, resource_list):
        self.log(f'play_drm: urn = {urn}')
        preferred_quality = 'HD' if self.prefer_hd else 'SD'
        resource_data = {
            'url': '',
            'lic_url': '',
        }
        for resource in resource_list:
            url = utils.try_get(resource, 'url')
            if not url:
                continue
            quality = utils.try_get(resource, 'quality')
            lic_url = ''
            if utils.try_get(resource, 'protocol') == 'DASH':
                drmlist = utils.try_get(
                    resource, 'drmList', data_type=list, default=[])
                for item in drmlist:
                    if utils.try_get(item, 'type') == 'WIDEVINE':
                        lic_url = utils.try_get(item, 'licenseUrl')
                        resource_data['url'] = url
                        resource_data['lic_url'] = lic_url
            if resource_data['lic_url'] and quality == preferred_quality:
                break

        if not resource_data['url'] or not resource_data['lic_url']:
            self.log('play_drm: No stream found')
            return

        manifest_type = 'mpd'
        drm = 'com.widevine.alpha'
        helper = inputstreamhelper.Helper(manifest_type, drm=drm)
        if not helper.check_inputstream():
            self.log('play_drm: Unable to setup drm')
            return

        play_item = xbmcgui.ListItem(
            title, path=self.get_auth_url(resource_data['url']))
        ia = 'inputstream.adaptive'
        play_item.setProperty('inputstream', ia)
        lic_key = f'{resource_data["lic_url"]}|' \
                  'Content-Type=application/octet-stream|R{SSM}|'
        play_item.setProperty(f'{ia}.manifest_type', manifest_type)
        play_item.setProperty(f'{ia}.license_type', drm)
        play_item.setProperty(f'{ia}.license_key', lic_key)
        xbmcplugin.setResolvedUrl(self.handle, True, play_item)

    def get_subtitles(self, url, name):
        """
        Returns subtitles from an url
        Kodi does not accept m3u playlists for subtitles
        In this case a temporary with all chunks is built

        Keyword arguments:
        url      -- url with subtitle location
        name     -- name of temporary file if required
        """
        webvttbaseurl = None
        caption = None

        parsed_url = urlps(url)
        query_list = parse_qsl(parsed_url.query)
        for query in query_list:
            if query[0] == 'caption':
                caption = query[1]
            elif query[0] == 'webvttbaseurl':
                webvttbaseurl = query[1]

        if not caption or not webvttbaseurl:
            return None

        cap_comps = caption.split(':')
        lang = '.' + cap_comps[1] if len(cap_comps) > 1 else ''
        sub_url = ('http://' + webvttbaseurl + '/' + cap_comps[0])
        self.log('subtitle url: ' + sub_url)
        if not sub_url.endswith('.m3u8'):
            return [sub_url]

        # Build temporary local file in case of m3u playlist
        sub_name = 'special://temp/' + name + lang + '.vtt'
        if not xbmcvfs.exists(sub_name):
            m3u_base = sub_url.rsplit('/', 1)[0]
            m3u = self.open_url(sub_url, use_cache=False)
            sub_file = xbmcvfs.File(sub_name, 'w')

            # Concatenate chunks and remove header on subsequent
            first = True
            for line in m3u.splitlines():
                if line.startswith('#'):
                    continue
                subs = self.open_url(m3u_base + '/' + line, use_cache=False)
                if first:
                    sub_file.write(subs)
                    first = False
                else:
                    i = 0
                    while i < len(subs) and not subs[i].isnumeric():
                        i += 1
                    sub_file.write('\n')
                    sub_file.write(subs[i:])

            sub_file.close()

        return [sub_name]

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
                    self.log('Unexpected file structure '
                             f'for {FAVOURITE_SHOWS_FILENAME}.')
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

    def read_searches(self, filename):
        path = xbmc.translatePath(self.real_settings.getAddonInfo('profile'))
        file_path = os.path.join(path, filename)
        try:
            with open(file_path, 'r') as f:
                json_file = json.load(f)
            try:
                return[entry['search'] for entry in json_file]
            except KeyError:
                self.log(f'Unexpected file structure for {filename}.')
                return []
        except (IOError, TypeError):
            return []

    def write_search(self, filename, name, max_entries=10):
        searches = self.read_searches(filename)
        try:
            searches.remove(name)
        except ValueError:
            pass
        if len(searches) >= max_entries:
            searches.pop()
        searches.insert(0, name)
        write_dict_list = [{'search': entry} for entry in searches]
        path = xbmc.translatePath(self.real_settings.getAddonInfo('profile'))
        file_path = os.path.join(path, filename)
        if not os.path.exists(path):
            os.makedirs(path)
        with open(file_path, 'w') as f:
            json.dump(write_dict_list, f)

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

    def _read_youtube_channels(self, fname):
        """
        Reads YouTube channel IDs from a specified file and returns a list
        of these channel IDs.

        Keyword arguments:
        fname  -- the path to the file to be read
        """
        data_file = os.path.join(xbmc.translatePath(self.data_uri), fname)
        with open(data_file, 'r', encoding='utf-8') as f:
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
        youtube_channels.YoutubeChannels(
            self.handle, channel_ids,
            self.addon_id, self.debug).build_channel_overview_menu()

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
