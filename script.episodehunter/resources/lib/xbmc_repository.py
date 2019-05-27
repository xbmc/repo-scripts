import json
import xbmc
from resources.lib import helper


def xbmc_rpc(arg):
    rpc_cmd = json.dumps(arg)
    result = xbmc.executeJSONRPC(rpc_cmd)
    result = json.loads(result)

    if 'error' in result:
        helper.debug('execute_rpc: ' + str(result['error']))
        return {'result': {}}

    return result


def execute_rpc(**kargs):
    kargs['jsonrpc'] = '2.0'
    return xbmc_rpc(kargs)['result']


def active_player():
    result = execute_rpc(method='Player.GetActivePlayers', id=1)

    try:
        return result[0]['playerid']
    except KeyError:
        helper.debug("Failing to fetch player id")
        helper.debug(result)
        return None


def currently_playing(playerid):
    result = execute_rpc(
        method='Player.GetItem',
        params={
            'playerid': playerid, 'properties': ['title']
        },
        id=1)

    try:
        return result['item']
    except KeyError:
        helper.debug(
            "Failing to fetch playing item for player id: " + str(playerid))
        helper.debug(result)
        return None


def get_movies(start=0, end=0, filt=None):
    params = {
        'properties': ['title', 'year', 'originaltitle', 'imdbnumber', 'lastplayed']
    }
    if end != 0:
        params['limits'] = {'start': start, 'end': end}
    if filt:
        params['filter'] = filt
    result = execute_rpc(
        method='VideoLibrary.GetMovies',
        params=params,
        id=1)

    return result['movies'] if 'movies' in result and isinstance(result['movies'], list) else []


def get_movie_chunks(size, filt):
    jumps = size
    start = 0
    end = jumps
    while True:
        movies = get_movies(start, end, filt)
        start = end
        end = start + jumps
        if not movies:
            return
        yield [movie for movie in movies if meet_movie_criteria(movie)]


def watched_movies(size):
    filter_by_playcount = {'field': 'playcount',
                           'operator': 'greaterthan', 'value': '0'}
    return get_movie_chunks(size, filter_by_playcount)


def unwatched_movies(size):
    filter_by_playcount = {'field': 'playcount',
                           'operator': 'lessthan', 'value': '1'}
    return get_movie_chunks(size, filter_by_playcount)


def number_of_movies(filt):
    params = {
        'limits': {'start': 0, 'end': 1}
    }

    if filt:
        params['filter'] = filt

    result = execute_rpc(
        method='VideoLibrary.GetMovies',
        params=params,
        id=1)

    return result['limits']['total'] if 'limits' in result else 0


def number_watched_movies():
    filter_by_playcount = {'field': 'playcount',
                           'operator': 'greaterthan', 'value': '0'}
    return number_of_movies(filter_by_playcount)


def number_unwatched_movies():
    filter_by_playcount = {'field': 'playcount',
                           'operator': 'lessthan', 'value': '1'}
    return number_of_movies(filter_by_playcount)


def get_show_chunks(size, filt):
    jumps = size
    start = 0
    end = jumps
    while True:
        shows = get_shows(start, end, filt)
        start = end
        end = start + jumps
        if not shows:
            return
        for show in shows:
            if meet_show_criteria(show):
                yield show


def watched_shows():
    filter_by_playcount = {'field': 'playcount',
                           'operator': 'greaterthan', 'value': '0'}
    return get_show_chunks(5, filter_by_playcount)


def unwatched_shows():
    filter_by_playcount = {'field': 'playcount',
                           'operator': 'lessthan', 'value': '1'}
    return get_show_chunks(5, filter_by_playcount)


def number_of_shows(filt):
    params = {
        'limits': {'start': 0, 'end': 1}
    }

    if filt:
        params['filter'] = filt

    result = execute_rpc(
        method='VideoLibrary.GetTVShows',
        params=params,
        id=1
    )

    return result['limits']['total'] if 'limits' in result else 0


def number_watched_shows():
    filter_by_playcount = {'field': 'playcount',
                           'operator': 'greaterthan', 'value': '0'}
    return number_of_shows(filter_by_playcount)


def number_unwatched_shows():
    filter_by_playcount = {'field': 'playcount',
                           'operator': 'lessthan', 'value': '1'}
    return number_of_shows(filter_by_playcount)


def get_shows(start=0, end=0, filt=None):
    params = {
        'properties': ['title', 'year', 'imdbnumber', 'playcount', 'season', 'watchedepisodes']
    }
    if end != 0:
        params['limits'] = {'start': start, 'end': end}
    if filt:
        params['filter'] = filt

    result = execute_rpc(
        method='VideoLibrary.GetTVShows',
        params=params,
        id=1
    )

    return result['tvshows'] if 'tvshows' in result and isinstance(result['tvshows'], list) else []


def get_episodes(tvshow, season=None, filt=None):
    if 'tvshowid' not in tvshow or tvshow['tvshowid'] == '':
        return []

    params = {
        'tvshowid': tvshow['tvshowid'],
        'properties': ['playcount', 'episode', 'season']
    }

    if filt:
        params['filter'] = filt
    if season:
        params['season'] = season

    result = execute_rpc(
        method='VideoLibrary.GetEpisodes',
        params=params,
        id=1
    )

    return result['episodes'] if 'episodes' in result and isinstance(result['episodes'], list) else []


def watched_episodes(show, season=None):
    filter_by_playcount = {'field': 'playcount',
                           'operator': 'greaterthan', 'value': '0'}
    return get_episodes(show, season, filter_by_playcount)


def unwatched_episodes(show, season=None):
    filter_by_playcount = {'field': 'playcount',
                           'operator': 'lessthan', 'value': '1'}
    return get_episodes(show, season, filter_by_playcount)


def movie_details(movie_id):
    result = execute_rpc(
        method='VideoLibrary.GetMovieDetails',
        params={
            'movieid': movie_id,
            'properties': ['year', 'imdbnumber', 'originaltitle']
        },
        id=1)

    return result['moviedetails'] if 'moviedetails' in result else None


def get_episode_details(episode_id):
    result = execute_rpc(
        method='VideoLibrary.GetEpisodeDetails',
        params={
            'episodeid': episode_id,
            'properties': ['tvshowid', 'showtitle', 'season', 'episode']
        },
        id=1)

    return result['episodedetails'] if 'episodedetails' in result else None


def get_show_details(library_id):
    result = execute_rpc(
        method='VideoLibrary.GetTVShowDetails',
        params={
            'tvshowid': library_id,
            'properties': ['imdbnumber', 'year']
        },
        id=1)

    return result['tvshowdetails'] if 'tvshowdetails' in result else None


def set_movies_as_watched(movies_ids):
    movies_rpc = [{
        'jsonrpc': '2.0',
        'method': 'VideoLibrary.SetMovieDetails',
        'params': {'movieid': movie_id, 'playcount': 1},
        'id': i
    } for i, movie_id in enumerate(movies_ids)]

    map(xbmc_rpc, helper.chunks(movies_rpc, 50))


def set_episodes_as_watched(episodes_ids):
    episodes = [{
        'jsonrpc': '2.0',
        'method': 'VideoLibrary.SetEpisodeDetails',
        'params': {'episodeid': episode_id, 'playcount': 1},
        'id': i
    } for i, episode_id in enumerate(episodes_ids)]

    map(xbmc_rpc, helper.chunks(episodes, 50))


def meet_show_criteria(tvshow):
    if 'title' not in tvshow or not tvshow['title']:
        return False

    try:
        int(tvshow['imdbnumber'])
    except (ValueError, TypeError, KeyError):
        return False

    try:
        if 'year' not in tvshow or int(tvshow['year']) <= 0:
            return False
    except ValueError:
        return False

    return True


def meet_movie_criteria(movie):
    if 'imdbnumber' not in movie or movie['imdbnumber'] == '':
        return False

    if 'title' not in movie and 'originaltitle' not in movie:
        return False

    try:
        if 'year' not in movie or int(movie['year']) <= 0:
            return False
    except ValueError:
        return False

    return True
