"""
This file contains API functions for the usage of WatchedList with other Kodi addons
"""

import xbmc
import time
from watchedlist import WatchedList
import utils

def change_watched_movie(imdb_id, playCount=1, name=''):
    """
    Change the watched state of one movie in the WL database

    Args:
    imdb_id: ID of the movie in the imdb. Format: Integer, numbers after 'tt0012345'
    playCount: Unsigned Integer
    name: Title of the movie (optional)

    Returns:
    Error Code (0=No error)
    """

    if len(name) == 0:
        name = 'tt%d' % imdb_id
    if playCount == 0:
        lastPlayed=0
    else:
        lastPlayed=int(time.time())
    row_xbmc = [imdb_id, 0, 0, lastPlayed, playCount, name, 0] # 0imdbnumber, 1empty, 2empty, 3lastPlayed, 4playCount, 5title, 6empty, 7movieid
    saveanyway = True
    commit = True
    lastChange = lastPlayed
    with WatchedList(True) as WL:
        if WL.get_watched_wl(1): # Read the WL database
            utils.showNotification(utils.getString(32102), utils.getString(32602), xbmc.LOGERROR)
            return 1
        WL.wl_update_media('movie', row_xbmc, saveanyway, commit, lastChange)
    return 0

def change_watched_episode(tvdb_id, season, episode, playCount=1, name=''):
    """
    Change the watched state of one episode in the WL database

    Args:
    tvdb_id: ID of the tv show in tvdb. Format: Integer
    season: Number of the season (Integer) within the show
    episode: Number of the episode within the season (Integer)
    playCount: Unsigned Integer
    name: Name of the Episode (optional)

    Returns:
    Error Code (0=No error)
    """

    if len(name) == 0:
        name = 'tvdb%d S%02dE%02d' % (tvdb_id, season, episode)
    if playCount == 0:
        lastPlayed=0
    else:
        lastPlayed=int(time.time())
    row_xbmc = [tvdb_id, season, episode, lastPlayed, playCount, name, 0] # 0imdbnumber, 1empty, 2empty, 3lastPlayed, 4playCount, 5title, 6empty, 7movieid
    saveanyway = True
    commit = True
    lastChange = lastPlayed
    with WatchedList(True) as WL:
        if WL.get_watched_wl(1): # Read the WL database
            utils.showNotification(utils.getString(32102), utils.getString(32602), xbmc.LOGERROR)
            return 1
        WL.wl_update_media('episode', row_xbmc, saveanyway, commit, lastChange)
    return 0

def change_watched_episodes(tvdb_id, seasons, episodes, playCount, names=[]):
    """
    Change the watched state of multiple episodes of one tv show in the WL database

    Args:
    tvdb_id: ID of the tv show in tvdb. Format: Integer
    seasons: Number of the seasons for the affected episodes (list of Integers)
    episodes: Number of the episodes within the seasons (list of Integers, same length as seasons list).
    playCount: Unsigned Integer
    names: Names of the Episodes (optional, list of strings, same length as lists above)

    Returns:
    Error Code (0=No error)
    """

    if playCount == 0:
        lastPlayed=0
    else:
        lastPlayed=int(time.time())
    with WatchedList(True) as WL:
        if WL.get_watched_wl(1): # Read the WL database
            utils.showNotification(utils.getString(32102), utils.getString(32602), xbmc.LOGERROR)
            return 1
        for i in range(len(seasons)):
            row_xbmc_i = [tvdb_id, seasons[i], episodes[i], lastPlayed, playCount, names[i], 0] # 0imdbnumber, 1empty, 2empty, 3lastPlayed, 4playCount, 5title, 6empty, 7movieid
            saveanyway = True
            if i == len(seasons)-1:
                commit = True # Only commit the last row to reduce file access to the database
            else:
                commit = False
            lastChange = lastPlayed

            WL.wl_update_media('episode', row_xbmc_i, saveanyway, commit, lastChange)
    return 0