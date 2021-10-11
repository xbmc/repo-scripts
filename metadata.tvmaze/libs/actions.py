# coding: utf-8
#
# Copyright (C) 2019, Roman Miroshnychenko aka Roman V.M. <roman1972@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Plugin route actions"""

from __future__ import absolute_import, unicode_literals

import json
import sys

import six
import xbmcgui
import xbmcplugin
from six.moves import urllib_parse

from . import tvmaze_api, data_service
from .utils import logger, get_episode_order

try:
    from typing import Optional, Text, Union, ByteString  # pylint: disable=unused-import
except ImportError:
    pass

HANDLE = int(sys.argv[1])  # type: int


def find_show(title, year=None):
    # type: (Union[Text, ByteString], Optional[Text]) -> None
    """Find a show by title"""
    if isinstance(title, bytes):
        title = title.decode('utf-8')
    logger.debug('Searching for TV show {} ({})'.format(title, year))
    search_results = tvmaze_api.search_show(title)
    if year is not None:
        search_result = data_service.filter_by_year(search_results, year)
        search_results = (search_result,) if search_result else ()
    for search_result in search_results:
        show_name = search_result['show']['name']
        if search_result['show']['premiered']:
            show_name += ' ({})'.format(search_result['show']['premiered'][:4])
        list_item = xbmcgui.ListItem(show_name, offscreen=True)
        list_item = data_service.add_main_show_info(list_item, search_result['show'], False)
        # Below "url" is some unique ID string (may be an actual URL to a show page)
        # that is used to get information about a specific TV show.
        xbmcplugin.addDirectoryItem(
            HANDLE,
            url=str(search_result['show']['id']),
            listitem=list_item,
            isFolder=True
        )


def get_show_id_from_nfo(nfo):
    # type: (Text) -> None
    """
    Get show ID by NFO file contents

    This function is called first instead of find_show
    if a NFO file is found in a TV show folder.

    :param nfo: the contents of a NFO file
    """
    if isinstance(nfo, bytes):
        nfo = nfo.decode('utf-8', 'replace')
    logger.debug('Parsing NFO file:\n{}'.format(nfo))
    parse_result = data_service.parse_nfo_url(nfo)
    if parse_result:
        if parse_result.provider == 'tvmaze':
            show_info = tvmaze_api.load_show_info(parse_result.show_id)
        else:
            show_info = tvmaze_api.load_show_info_by_external_id(
                parse_result.provider,
                parse_result.show_id
            )
        if show_info is not None:
            list_item = xbmcgui.ListItem(show_info['name'], offscreen=True)
            # "url" is some string that unique identifies a show.
            # It may be an actual URL of a TV show page.
            xbmcplugin.addDirectoryItem(
                HANDLE,
                url=str(show_info['id']),
                listitem=list_item,
                isFolder=True
            )


def get_details(show_id):
    # type: (Text) -> None
    """Get details about a specific show"""
    logger.debug('Getting details for show id {}'.format(show_id))
    show_info = tvmaze_api.load_show_info(show_id)
    if show_info is not None:
        list_item = xbmcgui.ListItem(show_info['name'], offscreen=True)
        list_item = data_service.add_main_show_info(list_item, show_info)
        xbmcplugin.setResolvedUrl(HANDLE, True, list_item)
    else:
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem(offscreen=True))


def get_episode_list(show_id, episode_order):  # pylint: disable=missing-docstring
    # type: (Text, Text) -> None
    logger.debug('Getting episode list for show id {}, order: {}'.format(
        show_id, episode_order))
    if not show_id.isdigit():
        # Kodi has a bug: when a show directory contains an XML NFO file with
        # episodeguide URL, that URL is always passed here regardless of
        # the actual parsing result in get_show_from_nfo()
        parse_result = data_service.parse_nfo_url(show_id)
        if not parse_result:
            return
        if parse_result.provider == 'tvmaze':
            show_info = tvmaze_api.load_show_info(parse_result.show_id)
        else:
            show_info = tvmaze_api.load_show_info_by_external_id(
                parse_result.provider,
                parse_result.show_id
            )
        if show_info:
            show_id = str(show_info['id'])
    if show_id.isdigit():
        episodes_map = tvmaze_api.load_episodes_map(show_id, episode_order)
        for episode in six.itervalues(episodes_map):
            list_item = xbmcgui.ListItem(episode['name'], offscreen=True)
            list_item = data_service.add_episode_info(list_item, episode, full_info=False)
            encoded_ids = urllib_parse.urlencode({
                'show_id': show_id,
                'episode_id': str(episode['id']),
                'season': str(episode['season']),
                'episode': str(episode['number']),
            })
            # Below "url" is some unique ID string (may be an actual URL to an episode page)
            # that allows to retrieve information about a specific episode.
            url = urllib_parse.quote(encoded_ids)
            xbmcplugin.addDirectoryItem(
                HANDLE,
                url=url,
                listitem=list_item,
                isFolder=True
            )


def get_episode_details(encoded_ids, episode_order):  # pylint: disable=missing-docstring
    # type: (Text, Text) -> None
    encoded_ids = urllib_parse.unquote(encoded_ids)
    decoded_ids = dict(urllib_parse.parse_qsl(encoded_ids))
    logger.debug('Getting episode details for {}'.format(decoded_ids))
    episode_info = tvmaze_api.load_episode_info(decoded_ids['show_id'],
                                                decoded_ids['episode_id'],
                                                decoded_ids['season'],
                                                decoded_ids['episode'],
                                                episode_order)
    if episode_info:
        list_item = xbmcgui.ListItem(episode_info['name'], offscreen=True)
        list_item = data_service.add_episode_info(list_item, episode_info, full_info=True)
        xbmcplugin.setResolvedUrl(HANDLE, True, list_item)
    else:
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem(offscreen=True))


def get_artwork(show_id):
    # type: (Text) -> None
    """
    Get available artwork for a show

    :param show_id: default unique ID set by setUniqueIDs() method
    """
    logger.debug('Getting artwork for show ID {}'.format(show_id))
    show_info = tvmaze_api.load_show_info(show_id)
    if show_info is not None:
        list_item = xbmcgui.ListItem(show_info['name'], offscreen=True)
        list_item = data_service.set_show_artwork(show_info, list_item)
        xbmcplugin.setResolvedUrl(HANDLE, True, list_item)
    else:
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem(offscreen=True))


def router(paramstring):
    # type: (Text) -> None
    """
    Route addon calls

    :param paramstring: url-encoded query string
    :raises RuntimeError: on unknown call action
    """
    params = dict(urllib_parse.parse_qsl(paramstring))
    logger.debug('Called addon with params: {}'.format(sys.argv))
    path_settings = json.loads(params['pathSettings'])
    episode_order = get_episode_order(path_settings)
    if params['action'] == 'find':
        find_show(params['title'], params.get('year'))
    elif params['action'].lower() == 'nfourl':
        get_show_id_from_nfo(params['nfo'])
    elif params['action'] == 'getdetails':
        get_details(params['url'])
    elif params['action'] == 'getepisodelist':
        get_episode_list(params['url'], episode_order)
    elif params['action'] == 'getepisodedetails':
        get_episode_details(params['url'], episode_order)
    elif params['action'] == 'getartwork':
        get_artwork(params['id'])
    else:
        raise RuntimeError('Invalid addon call: {}'.format(sys.argv))
    xbmcplugin.endOfDirectory(HANDLE)
