import json
import xbmc
import helper


def get_active_players_from_xbmc():
    rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'Player.GetActivePlayers', 'id': 1})

    result = xbmc.executeJSONRPC(rpccmd)
    result = json.loads(result)

    if 'error' in result:
        helper.debug("get_active_players_from_xbmc: " + str(result['error']))
        return None

    try:
        return result['result'][0]['playerid']
    except KeyError:
        helper.debug("get_active_players_from_xbmc: KeyError: result['result']['playerid']")
        return None


def get_currently_playing_from_xbmc(playerid):
    rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'Player.GetItem', 'params': {'playerid': playerid, 'properties': ['title']}, 'id': 1})

    result = xbmc.executeJSONRPC(rpccmd)
    result = json.loads(result)

    if 'error' in result:
        helper.debug("get_currently_playing_from_xbmc: " + str(result['error']))
        return None

    try:
        return result['result']['item']
    except KeyError:
        helper.debug("get_currently_playing_from_xbmc: KeyError: result['result']['movies']")
        return None


def get_movies_from_xbmc():
    rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetMovies', 'params': {'properties': ['title', 'year', 'originaltitle', 'imdbnumber', 'playcount', 'lastplayed']}, 'id': 1})

    result = xbmc.executeJSONRPC(rpccmd)
    result = json.loads(result)

    if 'error' in result:
        helper.debug("get_movies_from_xbmc: " + str(result['error']))
        return None

    try:
        return result['result']['movies']
    except KeyError:
        helper.debug("get_movies_from_xbmc: KeyError: result['result']['movies']")
        return None


def get_tv_shows_from_xbmc():
    rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetTVShows', 'params': {'properties': ['title', 'year', 'imdbnumber', 'playcount', 'season', 'watchedepisodes']}, 'id': 1})

    result = xbmc.executeJSONRPC(rpccmd)
    result = json.loads(result)

    if 'error' in result:
        helper.debug("get_tv_shows_from_xbmc: " + str(result['error']))
        return None

    try:
        return result['result']
    except KeyError:
        helper.debug("get_tv_shows_from_xbmc: KeyError: result['result']")
        return None


def get_seasons_from_xbmc(tvshow):
    if not 'tvshowid' in tvshow:
        return None
    rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetSeasons', 'params': {'tvshowid': tvshow['tvshowid'], 'properties': ['watchedepisodes']}, 'id': 1})

    result = xbmc.executeJSONRPC(rpccmd)
    result = json.loads(result)

    if 'error' in result:
        helper.debug("get_seasons_from_xbmc: " + str(result['error']))
        return None

    try:
        return result['result']
    except KeyError:
        helper.debug("get_seasons_from_xbmc: KeyError: result['result']")
        return None


def get_episodes_from_xbmc(tvshow, season):
    if not 'tvshowid' in tvshow:
        return None
    rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetEpisodes', 'params': {'tvshowid': tvshow['tvshowid'], 'season': season, 'properties': ['playcount', 'episode']}, 'id': 1})

    result = xbmc.executeJSONRPC(rpccmd)
    result = json.loads(result)

    if 'error' in result:
        helper.debug("get_episodes_from_xbmc: " + str(result['error']))
        return None

    try:
        return result['result']
    except KeyError:
        helper.debug("get_episodes_from_xbmc: KeyError: result['result']")
        return None


def get_movie_details_from_xbmc_by_title(title, year, fields):
    rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetMovieDetails', 'params': {'title': title, 'year': year, 'properties': fields}, 'id': 1})

    result = xbmc.executeJSONRPC(rpccmd)
    result = json.loads(result)

    if 'error' in result:
        helper.debug("get_movie_details_from_xbmc_by_title: " + str(result['error']))
        return None

    try:
        return result['result']['moviedetails']
    except KeyError:
        helper.debug("get_movie_details_from_xbmc_by_title: KeyError: result['result']['moviedetails']")
        return None


def get_movie_details_from_xbmc(library_id, fields):
    """ Get a single movie from xbmc given the id """
    rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetMovieDetails', 'params': {'movieid': library_id, 'properties': fields}, 'id': 1})

    result = xbmc.executeJSONRPC(rpccmd)
    result = json.loads(result)

    if 'error' in result:
        helper.debug("get_movie_details_from_xbmc: " + str(result['error']))
        return None

    try:
        return result['result']['moviedetails']
    except KeyError:
        helper.debug("get_movie_details_from_xbmc: KeyError: result['result']['moviedetails']")
        return None


def get_episode_details_from_xbmc(library_id, fields):
    rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetEpisodeDetails', 'params': {'episodeid': library_id, 'properties': fields}, 'id': 1})

    result = xbmc.executeJSONRPC(rpccmd)
    result = json.loads(result)

    if 'error' in result:
        helper.debug("get_episode_details_from_xbmc: " + str(result['error']))
        return None

    try:
        return result['result']['episodedetails']
    except KeyError:
        helper.debug("get_episode_details_from_xbmc: KeyError: result['result']['episodedetails']")
        return None


def get_show_details_from_xbmc(library_id, fields):
    rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetTVShowDetails', 'params': {'tvshowid': library_id, 'properties': fields}, 'id': 1})

    result = xbmc.executeJSONRPC(rpccmd)
    result = json.loads(result)

    if 'error' in result:
        helper.debug("get_show_details_from_xbmc: " + str(result['error']))
        return None

    try:
        return result['result']['tvshowdetails']
    except KeyError:
        helper.debug("get_show_details_from_xbmc: KeyError: result['result']['tvshowdetails']")
        return None
