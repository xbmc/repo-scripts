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

"""Functions to interact with TVmaze API"""

from __future__ import absolute_import, unicode_literals

from pprint import pformat

import requests
from requests.exceptions import HTTPError

from . import cache_service as cache
from .data_service import process_episode_list
from .utils import logger

try:
    from typing import Text, Optional, Union, List, Dict, Any  # pylint: disable=unused-import
    InfoType = Dict[Text, Any]  # pylint: disable=invalid-name
except ImportError:
    pass

SEARCH_URL = 'http://api.tvmaze.com/search/shows'
SEARCH_BY_EXTERNAL_ID_URL = 'http://api.tvmaze.com/lookup/shows'
SHOW_INFO_URL = 'http://api.tvmaze.com/shows/{}'
EPISODE_LIST_URL = 'http://api.tvmaze.com/shows/{}/episodes'
EPISODE_INFO_URL = 'http://api.tvmaze.com/episodes/{}'
ALTERNATE_LISTS_URL = 'http://api.tvmaze.com/shows/{}/alternatelists'
ALTERNATE_EPISODES_URL = 'http://api.tvmaze.com/alternatelists/{}/alternateepisodes'

HEADERS = (
    ('User-Agent', 'Kodi scraper for tvmaze.com by Roman V.M.; roman1972@gmail.com'),
    ('Accept', 'application/json'),
)
SESSION = requests.Session()
SESSION.headers.update(dict(HEADERS))


def _load_info(url, params=None):
    # type: (Text, Optional[Dict[Text, Union[Text, List[Text]]]]) -> Union[dict, list]
    """
    Load info from TVmaze

    :param url: API endpoint URL
    :param params: URL query params
    :return: API response
    :raises requests.exceptions.HTTPError: if any error happens
    """
    logger.debug('Calling URL "{}" with params {}'.format(url, params))
    response = SESSION.get(url, params=params)
    if not response.ok:
        response.raise_for_status()
    json_response = response.json()
    logger.debug('TVmaze response:\n{}'.format(pformat(json_response)))
    return json_response


def search_show(title):
    # type: (Text) -> List[InfoType]
    """
    Search a single TV show

    :param title: TV show title to search
    :return: a list with found TV shows
    """
    try:
        return _load_info(SEARCH_URL, {'q': title})
    except HTTPError as exc:
        logger.error('TVmaze returned an error: {}'.format(exc))
        return []


def load_show_info(show_id):
    # type: (Text) -> Optional[InfoType]
    """
    Get full info for a single show

    :param show_id: TVmaze show ID
    :return: show info or None
    """
    show_info = cache.load_show_info_from_cache(show_id)
    if show_info is None:
        show_info_url = SHOW_INFO_URL.format(show_id)
        params = {'embed[]': ['cast', 'seasons', 'images', 'crew']}
        try:
            show_info = _load_info(show_info_url, params)
        except HTTPError as exc:
            logger.error('TVmaze returned an error: {}'.format(exc))
            return None
        if isinstance(show_info['_embedded']['images'], list):
            show_info['_embedded']['images'].sort(key=lambda img: img['main'],
                                                  reverse=True)
        cache.cache_show_info(show_info)
    return show_info


def load_show_info_by_external_id(provider, show_id):
    # type: (Text, Text) -> Optional[InfoType]
    """
    Load show info by external ID (TheTVDB or IMDB)

    :param provider: 'imdb' or 'thetvdb'
    :param show_id: show ID in the respective provider
    :return: show info or None
    """
    query = {provider: show_id}
    try:
        return _load_info(SEARCH_BY_EXTERNAL_ID_URL, query)
    except HTTPError as exc:
        logger.error('TVmaze returned an error: {}'.format(exc))
        return None


def _get_alternate_episode_list_id(show_id, episode_order):
    # type: (Text, Text) -> Optional[int]
    alternate_order_id = None
    url = ALTERNATE_LISTS_URL.format(show_id)
    try:
        alternate_lists = _load_info(url)
    except HTTPError as exc:
        logger.error('TVmaze returned an error: {}'.format(exc))
    else:
        for episode_list in alternate_lists:
            if episode_list.get(episode_order):
                alternate_order_id = episode_list['id']
                break
    return alternate_order_id


def load_alternate_episode_list(show_id, episode_order):
    # type: (Text, Text) -> Optional[List[InfoType]]
    alternate_episodes = None
    alternate_order_id = _get_alternate_episode_list_id(show_id, episode_order)
    if alternate_order_id is not None:
        url = ALTERNATE_EPISODES_URL.format(alternate_order_id)
        try:
            raw_alternate_episodes = _load_info(url, {'embed': 'episodes'})
        except HTTPError as exc:
            logger.error('TVmaze returned an error: {}'.format(exc))
        else:
            alternate_episodes = []
            for episode in raw_alternate_episodes:
                episode_info = episode['_embedded']['episodes'][0]
                episode_info['season'] = episode['season']
                episode_info['number'] = episode['number']
                alternate_episodes.append(episode_info)
    if alternate_episodes:
        alternate_episodes.sort(key=lambda ep: (ep['season'], ep['number']))
    return alternate_episodes


def load_episodes_map(show_id, episode_order):
    # type: (Text, Text) -> Optional[Dict[Text, InfoType]]
    """Load episode list from TVmaze API"""
    processed_episodes = cache.load_episodes_map_from_cache(show_id)
    if not processed_episodes:
        episode_list = None
        if episode_order != 'default':
            episode_list = load_alternate_episode_list(show_id, episode_order)
        if not episode_list:
            episode_list_url = EPISODE_LIST_URL.format(show_id)
            try:
                episode_list = _load_info(episode_list_url, {'specials': '1'})
            except HTTPError as exc:
                logger.error('TVmaze returned an error: {}'.format(exc))
        if episode_list:
            processed_episodes = process_episode_list(episode_list)
            cache.cache_episodes_map(show_id, processed_episodes)
    return processed_episodes


def load_episode_info(show_id, episode_id, season, episode, episode_order):
    # type: (Text, Text, Text, Text, Text) -> Optional[InfoType]
    """
    Load episode info

    :param show_id:
    :param episode_id:
    :param season:
    :param episode:
    :param episode_order:
    :return: episode info or None
    """
    episode_info = None
    episodes_map = load_episodes_map(show_id, episode_order)
    if episodes_map is not None:
        try:
            key = '{}_{}_{}'.format(episode_id, season, episode)
            episode_info = episodes_map[key]
        except KeyError as exc:
            logger.error('Unable to retrieve episode info: {}'.format(exc))
    if episode_info is None:
        url = EPISODE_INFO_URL.format(episode_id)
        try:
            episode_info = _load_info(url)
        except HTTPError as exc:
            logger.error('TVmaze returned an error: {}'.format(exc))
    return episode_info
