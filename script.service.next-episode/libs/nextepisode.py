# coding: utf-8
# Created on: 15.03.2016
# Author: Roman Miroshnychenko aka Roman V.M. (romanvm@yandex.ua)
# License: GPL v. 3 <http://www.gnu.org/licenses/gpl-3.0.en.html>

from __future__ import absolute_import, unicode_literals

import json
from copy import deepcopy
from pprint import pformat

from future.utils import python_2_unicode_compatible
from requests import post

from . import logger
from .medialibrary import get_tvdb_id

__all__ = ['prepare_movies_list', 'prepare_episodes_list', 'update_data']

UPDATE_DATA = 'https://next-episode.net/api/kodi/v1/update_data'
LOGIN = 'https://next-episode.net/api/kodi/v1/login'


class LoginError(Exception):
    pass


@python_2_unicode_compatible
class DataUpdateError(Exception):
    """
    Exception that carries information about movies and/or TV shows
    that failed update to next-episode.net
    """
    def __init__(self, failed_movies=None, failed_shows=None):
        super(DataUpdateError, self).__init__()
        self._failed_movies = failed_movies
        self._failed_shows = failed_shows

    @property
    def failed_movies(self):
        """
        :return: Comma-separated list of movie IDs that failed update
        :rtype: str
        """
        if self._failed_movies is not None:
            return ', '.join(self._failed_movies)
        return 'none'

    @property
    def failed_shows(self):
        """
        :return: Comma-separated list of TV show IDs that failed update
        :rtype: str
        """
        if self._failed_shows is not None:
            return ', '.join(self._failed_shows)
        return 'none'

    def __str__(self):
        return (
            'Data update error! '
            'Failed movies: {0}. Failed TV shows: {1}'.format(
                self.failed_movies,
                self.failed_shows)
        )


def web_client(url, data=None):
    """
    Send/receive data to/from next-episode.net

    :param url: url to open
    :type url: str
    :param data: data to be sent in a POST request
    :type data: dict
    :return. website JSON response
    :rtype: dict
    """
    reply = post(url, json=data, verify=False)
    result = json.loads(reply.text)
    logged_data = deepcopy(result)
    if 'hash' in logged_data:
        logged_data['hash'] = '*****'
    logger.log_debug('next-episode reply:\n{0}'.format(pformat(logged_data)))
    return result


def update_data(data):
    """
    Update movies/tvshows data

    :param data: data to be send to next-episode.net
    :type data: dict
    :return: next-episode.net response
    :rtype: dict
    :raises LoginError: if authentication failed
    :raises DataUpdateError: if movies or episodes fail to update.
    """
    response = web_client(UPDATE_DATA, data)
    if 'error' in response and response['error']['code'] == '3':
        raise LoginError
    else:
        failed_movies = None
        failed_shows = None
        if 'movies' in response and response['movies'].get('error'):
            failed_movies = response['movies']['error']['message']
        if 'tv_shows' in response and response['tv_shows'].get('error'):
            failed_shows = response['tv_shows']['error']['message']
        if failed_movies is not None or failed_shows is not None:
            raise DataUpdateError(failed_movies, failed_shows)
    return response


def get_password_hash(username, password):
    """
    Get password hash from next-episode.net

    :param username: next-episode username
    :type username: str
    :param password: next-episode password
    :type password: str
    :return: password hash
    :rtype: str
    :raises LoginError: if login fails
    """
    response = web_client(LOGIN, {'username': username, 'password': password})
    if 'error' in response:
        raise LoginError
    return response['hash']


def prepare_movies_list(raw_movies):
    """
    Prepare the list of movies to be sent to next-episodes.net

    :param raw_movies: raw movie list from Kodi
    :type raw_movies: list
    :return: prepared list
    :rtype: list
    """
    listing = []
    for movie in raw_movies:
        imdb_id = None
        if 'tt' in movie['imdbnumber']:
            imdb_id = movie['imdbnumber']
        elif 'uniqueid' in movie and movie['uniqueid'].get('imdb'):
            imdb_id = movie['uniqueid']['imdb']
        if imdb_id is not None:
            watched = '1' if movie['playcount'] else '0'
            listing.append({'imdb_id': imdb_id, 'watched': watched})
    return listing


def prepare_episodes_list(raw_episodes):
    """
    Prepare the list of TV episodes to be sent to next-episode.net

    :param raw_episodes: raw episode list for a TV show from Kodi
    :type raw_episodes: list
    :return: prepared list
    :rtype: list
    """
    listing = []
    thetvdb_id_map = {}
    for episode in raw_episodes:
        if episode['tvshowid'] not in thetvdb_id_map:
            tvdb_id = get_tvdb_id(episode['tvshowid'])
            thetvdb_id_map[episode['tvshowid']] = tvdb_id
        else:
            tvdb_id = thetvdb_id_map[episode['tvshowid']]
        if tvdb_id is not None:
            season_num = str(episode['season'])
            episode_num = str(episode['episode'])
            watched = '1' if episode['playcount'] else '0'
            listing.append(
                {'thetvdb_id': tvdb_id,
                 'season': season_num,
                 'episode': episode_num,
                 'watched': watched}
            )
    return listing
