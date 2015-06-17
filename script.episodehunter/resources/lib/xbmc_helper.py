import json

import xbmc
import helper
from resources.model.series_model import Series


def xbmc_rpc(arg):
    rpc_cmd = json.dumps(arg)
    result = xbmc.executeJSONRPC(rpc_cmd)
    result = json.loads(result)

    if 'error' in result:
        helper.debug('execute_rpc: ' + str(result['error']))
        return None

    return result


def execute_rpc(**kargs):
    """
    :rtype : dict
    """
    kargs['jsonrpc'] = '2.0'
    return xbmc_rpc(kargs)['result']


def get_active_players_from_xbmc():
    result = execute_rpc(method='Player.GetActivePlayers', id=1)

    try:
        return result[0]['playerid']
    except KeyError:
        helper.debug("Failing to fetch player id")
        helper.debug(result)
        return None


def get_currently_playing_from_xbmc(playerid):
    result = execute_rpc(method='Player.GetItem', params={'playerid': playerid, 'properties': ['title']}, id=1)

    try:
        return result['item']
    except KeyError:
        helper.debug("Failing to fetch playing item for player id: " + str(playerid))
        helper.debug(result)
        return None


def get_movies_from_xbmc():
    """
    :rtype : dict
    """
    result = execute_rpc(
        method='VideoLibrary.GetMovies',
        params={
            'properties': ['title', 'year', 'originaltitle', 'imdbnumber', 'playcount', 'lastplayed']
        },
        id=1
    )

    try:
        return result['movies']
    except KeyError:
        helper.debug("Failing to fetch movies from xbmc library")
        helper.debug(result)
        return []


def get_tv_shows_from_xbmc():
    result = execute_rpc(
        method='VideoLibrary.GetTVShows',
        params={
            'properties': ['title', 'year', 'imdbnumber', 'playcount', 'season', 'watchedepisodes']
        },
        id=1
    )

    try:
        return result['tvshows']
    except KeyError:
        helper.debug("Failing to fetch tv shows from xbmc library")
        helper.debug(result)
        return []


def get_seasons_from_xbmc(tvshow):
    if 'tvshowid' not in tvshow:
        return None
    result = execute_rpc(method='VideoLibrary.GetSeasons', params={'tvshowid': tvshow['tvshowid'], 'properties': ['watchedepisodes', 'season']}, id=1)

    try:
        return result['seasons']
    except KeyError:
        helper.debug("Failing to fetch seasons for TV show with id: " + str(tvshow))
        helper.debug(result)
        return []


def get_episodes_from_xbmc(tvshow, season):
    if 'tvshowid' not in tvshow:
        return None
    result = execute_rpc(method='VideoLibrary.GetEpisodes', params={'tvshowid': tvshow['tvshowid'], 'season': season, 'properties': ['playcount', 'episode', 'season']}, id=1)

    try:
        return result['episodes']
    except KeyError:
        helper.debug("Failing to fetch episodes in season " + str(season) + ", tvshow id: " + str(tvshow))
        helper.debug(result)
        return []


def get_movie_details_from_xbmc_by_title(title, year, fields):
    result = execute_rpc(method='VideoLibrary.GetMovieDetails', params={'title': title, 'year': year, 'properties': fields}, id=1)

    try:
        return result['moviedetails']
    except KeyError:
        helper.debug("Failing to fetch movie from xbmc library by title")
        helper.debug(result)
        return None


def get_movie_details_from_xbmc(library_id):
    """
    Get a single movie from xbmc given id
    :param library_id:int
    :rtype : dict
    """
    result = execute_rpc(
        method='VideoLibrary.GetMovieDetails',
        params={
            'movieid': library_id,
            'properties': ['year', 'imdbnumber', 'originaltitle']
        }, id=1)

    try:
        return result['moviedetails']
    except KeyError:
        helper.debug("Failing to fetch movie details from xbmc library")
        helper.debug(result)
        return None


def get_episode_details_from_xbmc(library_id):
    """
    Get a single movie from xbmc given id
    :param library_id:int
    :rtype : dict
    """
    result = execute_rpc(
        method='VideoLibrary.GetEpisodeDetails',
        params={
            'episodeid': library_id,
            'properties': ['tvshowid', 'showtitle', 'season', 'episode']
        }, id=1)

    try:
        return result['episodedetails']
    except KeyError:
        helper.debug("Failing to fetch episode details from xbmc library")
        helper.debug(result)
        return None


def get_show_details_from_xbmc(library_id):
    result = execute_rpc(
        method='VideoLibrary.GetTVShowDetails',
        params={
            'tvshowid': library_id,
            'properties': ['imdbnumber', 'year']
        }, id=1)

    try:
        return result['tvshowdetails']
    except KeyError:
        helper.debug("Failing to fetch tv show details from xbmc library")
        helper.debug(result)
        return None


def set_movie_as_watched(movie_id):
    execute_rpc(method='VideoLibrary.SetMovieDetails', params={'movieid': movie_id, "playcount": 1}, id=1)


def set_movies_as_watched(movies):
    """
    Set movies as watched
    :param movies: list of Movies
    """
    movies_rpc = [{
                      'jsonrpc': '2.0',
                      'method': 'VideoLibrary.SetMovieDetails',
                      'params': {'movieid': m.xbmc_id, 'playcount': 1},
                      'id': i
                  } for i, m in enumerate(movies)]

    map(xbmc_rpc, helper.chunks(movies_rpc, 50))


def set_series_as_watched(series):
    episodes = []
    for s in series:
        assert isinstance(s, Series)
        episodes = episodes + [{
                'jsonrpc': '2.0',
                'method': 'VideoLibrary.SetEpisodeDetails',
                'params': {'episodeid': e.xbmc_id, 'playcount': 1},
                'id': i
            } for i, e in enumerate(s.episodes)]

    map(xbmc_rpc, helper.chunks(episodes, 50))
