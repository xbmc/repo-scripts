# coding: utf-8
# Created on: 15.03.2016
# Author: Roman Miroshnychenko aka Roman V.M. (romanvm@yandex.ua)
# License: GPL v. 3 <http://www.gnu.org/licenses/gpl-3.0.en.html>

import json
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
    json_request = json.dumps(request)
    xbmc.log('next-episode-net: JSON-RPC request: {0}'.format(json_request), xbmc.LOGDEBUG)
    json_reply = xbmc.executeJSONRPC(json_request)
    xbmc.log('next-episode-net: JSON-RPC reply: {0}'.format(json_reply), xbmc.LOGDEBUG)
    return json.loads(json_reply)['result']


def get_movies():
    """
    Get the list of movies from the Kodi database

    :return: the list of movie data as Python dicts like this:
        ``{"label":"Frankenstein Created Woman","movieid":1,"playcount":1,"uniqueid":{"imdb":"tt0061683","tmdb":"3104"}}``
    :rtype: list
    :raises NoDataError: if the Kodi library has no movies
    """
    params = {
        'properties': ['playcount'],
        'sort': {'order': 'ascending', 'method': 'label'}
    }
    if xbmc.getInfoLabel('System.BuildVersion') >= '17.0':
        params['properties'].append('uniqueid')
    else:
        params['properties'].append('imdbnumber')
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
        ``{u'season': 4, u'playcount': 0, u'episode': 1, u'episodeid': 5, u'label': u'4x01. The Drone Queen'}``
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
    params = {'tvshowid': tvshowid, 'properties': ['imdbnumber']}
    return send_json_rpc('VideoLibrary.GetTVShowDetails', params)['tvshowdetails']['imdbnumber']


def get_recent_movies():
    """
    Get the list of recently added movies

    :return: the list of recent movies
    :rtype: list
    :raises NoDataError: if the Kodi library has no recent movies.
    """
    params = {'properties': ['imdbnumber', 'playcount']}
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


def get_item_details(id_, type):
    """
    Get video item details

    :param id_: movie or episode Kodi database ID
    :type id_: int
    :param type: items's type -- 'movie' or 'episode'
    :type type: str
    :return: item details
    :rtype: dict
    """
    params = {type + 'id': id_, 'properties': ['playcount']}
    if type == 'movie':
        method = 'VideoLibrary.GetMovieDetails'
        if xbmc.getInfoLabel('System.BuildVersion') >= '17.0':
            params['properties'].append('uniqueid')
        else:
            params['properties'].append('imdbnumber')
    else:
        method = 'VideoLibrary.GetEpisodeDetails'
        params['properties'] += ['tvshowid', 'season', 'episode']
    return send_json_rpc(method, params)[type + 'details']
