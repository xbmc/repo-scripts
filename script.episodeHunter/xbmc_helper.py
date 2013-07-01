import xbmc
from helper import *

try:
    import simplejson as json
except ImportError:
    import json


def getActivePlayersFromXBMC():
    rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'Player.GetActivePlayers', 'id': 1})

    result = xbmc.executeJSONRPC(rpccmd)
    result = json.loads(result)

    if 'error' in result:
        Debug("getActivePlayersFromXBMC: " + str(result['error']))
        return None

    try:
        return result['result'][0]['playerid']
    except KeyError:
        Debug("getActivePlayersFromXBMC: KeyError: result['result']['playerid']")
        return None


def getCurrentlyplayFromXBMC(playerid):
    rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'Player.GetItem', 'params': {'playerid': playerid, 'properties': ['title']}, 'id': 1})

    result = xbmc.executeJSONRPC(rpccmd)
    result = json.loads(result)

    if 'error' in result:
        Debug("getCurrentlyplayFromXBMC: " + str(result['error']))
        return None

    try:
        return result['result']['item']
    except KeyError:
        Debug("getCurrentlyplayFromXBMC: KeyError: result['result']['movies']")
        return None


def getMoviesFromXBMC():
    rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetMovies', 'params': {'properties': ['title', 'year', 'originaltitle', 'imdbnumber', 'playcount', 'lastplayed']}, 'id': 1})

    result = xbmc.executeJSONRPC(rpccmd)
    result = json.loads(result)

    if 'error' in result:
        Debug("getMoviesFromXBMC: " + str(result['error']))
        return None

    try:
        return result['result']['movies']
    except KeyError:
        Debug("getMoviesFromXBMC: KeyError: result['result']['movies']")
        return None


def getTVShowsFromXBMC():
    rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetTVShows', 'params': {'properties': ['title', 'year', 'imdbnumber', 'playcount', 'season', 'watchedepisodes']}, 'id': 1})

    result = xbmc.executeJSONRPC(rpccmd)
    result = json.loads(result)

    if 'error' in result:
        Debug("getTVShowsFromXBMC: " + str(result['error']))
        return None

    try:
        return result['result']
    except KeyError:
        Debug("getTVShowsFromXBMC: KeyError: result['result']")
        return None


def getSeasonsFromXBMC(tvshow):
    rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetSeasons', 'params': {'tvshowid': tvshow['tvshowid'], 'properties': ['watchedepisodes']}, 'id': 1})

    result = xbmc.executeJSONRPC(rpccmd)
    result = json.loads(result)

    if 'error' in result:
        Debug("getSeasonsFromXBMC: " + str(result['error']))
        return None

    try:
        return result['result']
    except KeyError:
        Debug("getSeasonsFromXBMC: KeyError: result['result']")
        return None


def getEpisodesFromXBMC(tvshow, season):
    rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetEpisodes', 'params': {'tvshowid': tvshow['tvshowid'], 'season': season, 'properties': ['playcount', 'episode']}, 'id': 1})

    result = xbmc.executeJSONRPC(rpccmd)
    result = json.loads(result)

    if 'error' in result:
        Debug("getEpisodesFromXBMC: " + str(result['error']))
        return None

    try:
        return result['result']
    except KeyError:
        Debug("getEpisodesFromXBMC: KeyError: result['result']")
        return None


def getMovieDetailsFromXbmcByTitle(title, year, fields):
    rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetMovieDetails', 'params': {'title': title, 'year': year, 'properties': fields}, 'id': 1})

    result = xbmc.executeJSONRPC(rpccmd)
    result = json.loads(result)

    if 'error' in result:
        Debug("getMovieDetailsFromXbmcByTitle: " + str(result['error']))
        return None

    try:
        return result['result']['moviedetails']
    except KeyError:
        Debug("getMovieDetailsFromXbmcByTitle: KeyError: result['result']['moviedetails']")
        return None


# get a single movie from xbmc given the id
def getMovieDetailsFromXbmc(libraryId, fields):
    rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetMovieDetails', 'params': {'movieid': libraryId, 'properties': fields}, 'id': 1})

    result = xbmc.executeJSONRPC(rpccmd)
    result = json.loads(result)

    if 'error' in result:
        Debug("getMovieDetailsFromXbmc: " + str(result['error']))
        return None

    try:
        return result['result']['moviedetails']
    except KeyError:
        Debug("getMovieDetailsFromXbmc: KeyError: result['result']['moviedetails']")
        return None


def getEpisodeDetailsFromXbmc(libraryId, fields):
    rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetEpisodeDetails', 'params': {'episodeid': libraryId, 'properties': fields}, 'id': 1})

    result = xbmc.executeJSONRPC(rpccmd)
    result = json.loads(result)

    if 'error' in result:
        Debug("getEpisodeDetailsFromXbmc: " + str(result['error']))
        return None

    try:
        return result['result']['episodedetails']
    except KeyError:
        Debug("getEpisodeDetailsFromXbmc: KeyError: result['result']['episodedetails']")
        return None


def getShowDetailsFromXbmc(libraryId, fields):
    rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetTVShowDetails', 'params': {'tvshowid': libraryId, 'properties': fields}, 'id': 1})

    result = xbmc.executeJSONRPC(rpccmd)
    result = json.loads(result)

    if 'error' in result:
        Debug("getShowDetailsFromXbmc: " + str(result['error']))
        return None

    try:
        return result['result']['tvshowdetails']
    except KeyError:
        Debug("getShowDetailsFromXbmc: KeyError: result['result']['tvshowdetails']")
        return None
