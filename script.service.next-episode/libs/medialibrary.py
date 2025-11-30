# (c) Roman Miroshnychenko, 2023
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

import json
import logging
from pprint import pformat

import xbmc


class NoDataError(Exception):
    pass


def send_json_rpc(method, params=None):
    """
    Send JSON-RPC to Kodi

    :param method: Kodi JSON-RPC method
    :type method: str
    :param params: method parameters
    :type params: dict
    :return: JSON-RPC response
    :rtype: dict
    """
    request = {'jsonrpc': '2.0', 'method': method, 'id': '1'}
    if params is not None:
        request['params'] = params
    logging.debug('JSON-RPC request:\n%s', pformat(request))
    json_reply = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
    logging.debug('JSON-RPC reply:\n%s', pformat(json_reply))
    return json_reply['result']


def get_movies():
    """
    Get the list of movies from the Kodi database

    :return: the list of movie data as Python dicts like this:
        ``{"label":"Frankenstein Created Woman","movieid":1,"playcount":1,
        "uniqueid":{"imdb":"tt0061683","tmdb":"3104"}}``
    :rtype: list
    :raises NoDataError: if the Kodi library has no movies
    """
    params = {
        'properties': ['playcount', 'imdbnumber', 'uniqueid'],
        'sort': {'order': 'ascending', 'method': 'label'}
    }
    result = send_json_rpc('VideoLibrary.GetMovies', params)
    if not result.get('movies'):
        raise NoDataError
    return result['movies']


def get_tvshows():
    """
    Get te list of TV shows from the Kodi database

    :return: the list of TV show data as Python dicts like this:
        {u'imdbnumber': u'247897', u'tvshowid': 3, u'label': u'Homeland'}
    :rtype: list
    :raises NoDataError: if the Kodi library has no TV shows
    """
    params = {
        'properties': ['imdbnumber'],
        'sort': {'order': 'ascending', 'method': 'label'}
    }
    result = send_json_rpc('VideoLibrary.GetTVShows', params)
    if not result.get('tvshows'):
        raise NoDataError
    return result['tvshows']


def get_episodes(tvshowid):
    """
    Get the list of episodes from a specific TV show

    :param tvshowid: internal Kodi database ID for a TV show
    :type tvshowid: str
    :return: the liso of episode data as Python dicts like this:
        ``{u'season': 4, u'playcount': 0, u'episode': 1, u'episodeid': 5,
        u'label': u'4x01. The Drone Queen'}``
    :rtype: list
    :raises NoDataError: if a TV show has no episodes.
    """
    params = {
        'tvshowid': tvshowid,
        'properties': ['season', 'episode', 'playcount', 'tvshowid']
    }
    result = send_json_rpc('VideoLibrary.GetEpisodes', params)
    if not result.get('episodes'):
        raise NoDataError
    return result['episodes']


def get_tvdb_id(tvshowid):
    """
    Get TheTVDB ID for a TV show

    :param tvshowid: internal Kodi database ID for a TV show
    :type tvshowid: str
    :return: TheTVDB ID
    :rtype: str
    """
    params = {'tvshowid': tvshowid, 'properties': ['imdbnumber', 'uniqueid']}
    result = send_json_rpc('VideoLibrary.GetTVShowDetails',
                           params)['tvshowdetails']
    tvdbid = None
    if 'uniqueid' in result and result['uniqueid'].get('tvdb'):
        tvdbid = result['uniqueid']['tvdb']
    elif result.get('imdbnumber'):
        tvdbid = result['imdbnumber']
    return tvdbid


def get_recent_movies():
    """
    Get the list of recently added movies

    :return: the list of recent movies
    :rtype: list
    :raises NoDataError: if the Kodi library has no recent movies.
    """
    params = {'properties': ['imdbnumber', 'playcount', 'uniqueid']}
    result = send_json_rpc('VideoLibrary.GetRecentlyAddedMovies', params)
    if not result.get('movies'):
        raise NoDataError
    return result['movies']


def get_recent_episodes():
    """
    Get the list of recently added episodes

    :return: the list of recent episodes
    :rtype: list
    :raises NoDataError: if the Kodi library has no recent episodes
    """
    params = {'properties': ['playcount', 'tvshowid', 'season', 'episode']}
    result = send_json_rpc('VideoLibrary.GetRecentlyAddedEpisodes', params)
    if not result.get('episodes'):
        raise NoDataError
    return result['episodes']


def get_item_details(id_, type_):
    """
    Get video item details

    :param id_: movie or episode Kodi database ID
    :type id_: int
    :param type_: items's type -- 'movie' or 'episode'
    :type type_: str
    :return: item details
    :rtype: dict
    """
    params = {type_ + 'id': id_, 'properties': ['playcount']}
    if type_ == 'movie':
        method = 'VideoLibrary.GetMovieDetails'
        params['properties'].append('imdbnumber')
    else:
        method = 'VideoLibrary.GetEpisodeDetails'
        params['properties'] += ['tvshowid', 'season', 'episode', 'uniqueid']
    return send_json_rpc(method, params)[type_ + 'details']
