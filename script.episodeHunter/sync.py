import xbmc
import xbmcaddon
import xbmcgui
import time
from connection import Connection
from xbmc_helper import *
from helper import *

_settings = xbmcaddon.Addon("script.episodeHunter")
_language = _settings.getLocalizedString
_name = "EpisodeHunter"


def syncSeenMovies(gui=True):

    Debug('syncSeenMovies')

    if gui:
        progress = xbmcgui.DialogProgress()
        progress.create(_name, _language(10038))  # "Checking XBMC Database for new watched Movies"

    connection = Connection()

    EH_movies = connection.getMoviesFromEP()
    xbmc_movies = getMoviesFromXBMC()

    if xbmc_movies is None or EH_movies is None:
        if gui:
            progress.close()
        return

    i = -1                          # Iterator index
    num_movies = len(xbmc_movies)   # Number of movies in XBMC database
    set_as_seen = []                # List of movie to set as seen

    for movie in xbmc_movies:
        i += 1                                                  # Increase at beginning because of 'continue' and other fancy
        if xbmc.abortRequested:
            raise SystemExit()                                  # You heard the lady, get out of here!
        if gui:
            progress.update(100 / num_movies * i)
            if progress.iscanceled():
                xbmcgui.Dialog().ok(_name, _language(10039))    # "Progress Aborted"
                break
        try:
            imdb_id = movie['imdbnumber']
        except KeyError:
            Debug("Skipping a movie - no IMDb ID was found")
            continue

        if notSeenMovie(imdb_id, EH_movies):                    # Is the movie listed at EpisodeHunter as watched?
            try:
                playcount = movie['playcount']
                year = movie['year']
            except KeyError:
                continue

            if playcount > 0:                                   # Have the user watch it?
                if year > 0:                                    # I guess that this movie is newer then Jesus?
                    if 'lastplayed' in movie:                   # Do we have a date?
                        if 'originaltitle' in movie:            # It would be great if we have the orginal title
                            set_as_seen.append({
                                'imdb_id': imdb_id,
                                'title': movie['originaltitle'],
                                'year': movie['year'],
                                'plays': movie['playcount'],
                                'last_played': int(time.mktime(time.strptime(movie['lastplayed'], '%Y-%m-%d %H:%M:%S')))
                            })
                        else:                                   # No orginal title? Okey, send the 'ordinary' title
                            set_as_seen.append({
                                'imdb_id': imdb_id,
                                'title': movie['title'],
                                'year': movie['year'],
                                'plays': movie['playcount'],
                                'last_played': int(time.mktime(time.strptime(movie['lastplayed'], '%Y-%m-%d %H:%M:%S')))
                            })
                    else:                                       # No 'last-play'? :(
                        if 'originaltitle' in movie:            # It would be great if we have the orginal title
                            set_as_seen.append({
                                'imdb_id': imdb_id,
                                'title': movie['originaltitle'],
                                'year': movie['year'],
                                'plays': movie['playcount']
                            })
                        else:                                   # Do we have any data?
                            try:
                                set_as_seen.append({
                                    'imdb_id': imdb_id,
                                    'title': movie['title'],
                                    'year': movie['year'],
                                    'plays': movie['playcount']
                                })
                            except KeyError:
                                Debug('syncSeenMovies: What? It feels like movie is empty')
                else:
                    Debug("Skipping " + movie['title'] + " - The movie is to old")

    set_as_seen_title = ""
    for i in range(0, len(set_as_seen)):
        if i == 0:
            set_as_seen_title += set_as_seen[i]['title']
        elif i > 5:
            set_as_seen_title += ", ..."
            break
        else:
            set_as_seen_title += ", " + set_as_seen[i]['title']

    # Set movies as seen on EpisodeHunter:
    num_seen_movies = len(set_as_seen)

    if num_seen_movies > 0:
        if gui:
            choice = xbmcgui.Dialog().yesno(_name, str(num_seen_movies) + " " + _language(10040), set_as_seen_title)  # 'Movies will be added as watched on EpisodeHunter'
        else:
            choice = 0

        if choice == 1 or choice is True:                       # I belive this is OS bedending
            progress.update(50, _language(10065))               # 'Uploading movies to episodehunter'
            data = connection.setMoviesSeen(set_as_seen)

            if data is None:
                Debug("Error uploading seen movies: response is None")
                if gui:
                    xbmcgui.Dialog().ok(_name, _language(10041), "")  # 'Error uploading watched movies'
            elif 'status' in data:
                if data['status'] == 400:
                    Debug("successfully uploaded seen movies")
                    if gui:
                        xbmcgui.Dialog().ok(_name, _language(10058))    # 'Movie sucessfully updated to EpisodeHunter'
                elif data['status'] == 300:
                    Debug("Error uploading seen movies: " + str(data['data']))
                    if gui:
                        xbmcgui.Dialog().ok(_name, _language(10041), str(data['data']))  # 'Error uploading watched movies'
    else:
        if gui:
            xbmcgui.Dialog().ok(_name, _language(10042))  # 'No new watched movies to update for EpisodeHunter'

    if gui:
        progress.close()


def syncSeenTVShows(gui=True):

    Debug('syncSeenTVShows')
    MAX_SEASON_NUMBER = 50

    if gui:                                       # Are we syncing in a GUI?
        progress = xbmcgui.DialogProgress()       # Create a dialog
        progress.create(_name, _language(10047))  # And put a title on it (Checking XBMC Database for new watched Episodes)

    connection = Connection()                     # Create a connection

    EH_tvshows = connection.getWatchedTVShowsFromEH()   # Get a list of set wached episodes
    xbmc_tvshows = getTVShowsFromXBMC()                 # Get all tv shows in XBMC

    if xbmc_tvshows is None or EH_tvshows is None:
        if gui:
            progress.close()
        return

    if len(EH_tvshows) <= 0:
        EH_tvshows = {}       # We will get a lot of errors. BUT we will catch them (with 'except')

    if 'tvshows' in xbmc_tvshows:
        xbmc_tvshows = xbmc_tvshows['tvshows']

    set_as_seen = []    # List of shows to set as seen
    tvshow = {}         # The current tvshow to add
    i = -1              # Iterator index
    count = 0           # Number of episode to set as watched

    number_tvshows = len(xbmc_tvshows)

    for xbmc_tvshow in xbmc_tvshows:
        i += 1                                                  # Increase at beginning because of 'continue' and other fancy
        if xbmc.abortRequested:
            raise SystemExit()                                  # You heard the lady, get out of here!
        if gui:
            progress.update(100 / number_tvshows * i)
            if progress.iscanceled():
                xbmcgui.Dialog().ok(_name, _language(10039))    # "Progress Aborted"
                break

        seasons = getSeasonsFromXBMC(xbmc_tvshow)               # Get a list of seasons

        try:
            tvshow['title'] = xbmc_tvshow['title']
            tvshow['year'] = xbmc_tvshow['year']
            tvshow['tvdb_id'] = xbmc_tvshow['imdbnumber']
            seasons = seasons['seasons']
        except KeyError:
            continue

        tvshow['episodes'] = []

        number_seasons = len(seasons)

        for j in range(0, number_seasons):
            seasonid = 0
            while True:
                episodes = getEpisodesFromXBMC(xbmc_tvshow, seasonid)
                if 'limits' in episodes and 'total' in episodes['limits'] and episodes['limits']['total'] > 0:
                    break
                if seasonid > MAX_SEASON_NUMBER:
                    break
                if xbmc.abortRequested:
                    raise SystemExit()
                seasonid += 1
            if seasonid > MAX_SEASON_NUMBER:
                continue

            # Okey, lets stop for a moment
            # What do we have?
            # We have show title, show year, tvdb_id, season id(s) and a list of episodes

            try:
                foundseason = False
                for season in EH_tvshows[str(xbmc_tvshow['imdbnumber'])]['seasons']:
                    foundseason = True
                    # Okey, we have seen some season (no KeyError). But have we seen them all?
                    if season['season'] == str(seasonid):
                        # Okey, we have seen some episode in the season, but have we seen them all?
                        for episode in episodes['episodes']:
                            if seenEpisode(episode['episode'], season['episodes']):
                                # We have seen the episode, lets continue
                                continue
                            else:
                                # Add the episode
                                try:
                                    if episode['playcount'] > 0:
                                        tvshow['episodes'].append({
                                            'season': seasonid,
                                            'episode': episode['episode']})
                                        count += 1
                                except KeyError:
                                    pass
                if not foundseason:
                    raise KeyError

            except KeyError:
                # Add season as seen (whole tv show may be missing)
                for episode in episodes['episodes']:
                    try:
                        if episode['playcount'] > 0:
                            tvshow['episodes'].append({
                                'season': seasonid,
                                'episode': episode['episode']})
                            count += 1
                    except KeyError:
                        pass
                # The season have now been added, lets continue
                continue

        # If there are episodes to add to EpisodeHunter - append to list
        if len(tvshow['episodes']) > 0:
            set_as_seen.append(tvshow)
        tvshow = {}

    set_as_seen_title = ""
    for i in range(0, len(set_as_seen)):
        if i == 0:
            set_as_seen_title += set_as_seen[i]['title']
        elif i > 5:
            set_as_seen_title += ", ..."
            break
        else:
            set_as_seen_title += ", " + set_as_seen[i]['title']

    if count > 0:
        if gui:
            choice = xbmcgui.Dialog().yesno(_name, str(count) + " " + _language(10048), set_as_seen_title)  # String: Episodes will be added as watched
        else:
            choice = 0

        if choice == 1 or choice is True:   # I belive this is OS bedending
            error = None

            n = len(set_as_seen)
            i = -1

            progress.update(0, _language(10064))  # Uploading shows to episodehunter

            for show in set_as_seen:
                i += 1
                if xbmc.abortRequested:
                    raise SystemExit()

                if gui:
                    progress.update(100 / n * i)

                data = connection.setTvSeen(show['tvdb_id'], show['title'], show['year'], show['episodes'])

                if data is None:
                    Debug("Error uploading tvshow: response is None")
                    error = ""
                elif data['status'] == 300:
                    Debug("Error uploading tvshow: " + show['title'] + ": " + str(data['data']))
                    error = data['data']
                else:
                    Debug("Successfully uploaded tvshow " + show['title'] + ": " + str(data['data']))

            if error is None:
                if gui:
                    xbmcgui.Dialog().ok(_name, _language(10049))            # Episodes sucessfully updated to EpisodeHunter
                else:
                    notification(_name, _language(10049))                   # Episodes sucessfully updated to EpisodeHunter
            else:
                if gui:
                    xbmcgui.Dialog().ok(_name, _language(10050), error)     # Error uploading watched TVShows
                else:
                    notification(_name, _language(10050) + str(error))      # Error uploading watched TVShows
    else:
        if gui:
            xbmcgui.Dialog().ok(_name, _language(10051))                    # No new watched episodes in XBMC library to update

    if gui:
        progress.close()
