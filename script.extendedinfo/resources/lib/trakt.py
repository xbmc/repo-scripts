# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# Modifications copyright (C) 2022 - Scott Smart <scott967@kodi.tv>
# This program is Free Software see LICENSE file for details
"""Trakt module obtains data on TV Shows and Movies from Trakt.tv using
apiV2  If Trakt provides a TMDB id, additional data is retrieved from
TMDB

Public functions:
    get_episodes(content) gets upcoming episodes content shows or
                          premiering shows content premieres
                          returns a kutils131 ItemList
    get_shows(show_type)  gets tvshows for showtype trending/popular/anticipated
                          returns a kutils131 ItemList
    get_shows_from_time(show_type, period) gets tvshos for showtype collected/played/
                                           watched for previous month
                                           returns a kutils131 ItemList
    get_movies(movie_type) gets movies for movietype trending/popular/anticipated
                           returns a kutils131 ItemList
    get_movies_from_time(movie_type, period) gets movies forf movietype collected/
                                             played/watched for previous month
    get_similar(media_type, imdb_id) gets related mediatype show(s)/movie(s) from
                                     an imdb id.
"""

import datetime
import urllib.error
import urllib.parse
import urllib.request

from resources.kutil131 import ItemList, addon

from resources.kutil131 import VideoItem, local_db, utils
from resources.lib import themoviedb as tmdb

TRAKT_KEY = 'e9a7fba3fa1b527c08c073770869c258804124c5d7c984ce77206e695fbaddd5'
BASE_URL = "https://api.trakt.tv/"
HEADERS = {
    'Content-Type': 'application/json',
    'trakt-api-key': TRAKT_KEY,
    'trakt-api-version': '2'
}
PLUGIN_BASE = "plugin://script.extendedinfo/?info="


def get_episodes(content):
    """gets upcoming/premiering episodes from today

    Args:
        content (str): enum shows (upcoming) or premieres (new shows)

    Returns:
        ItemList: a kutils131 ItemList instance of VideoItems
    """
    shows = ItemList(content_type="episodes")
    url = ""
    if content == "shows":
        url = f'calendars/shows/{datetime.date.today()}/14'
    elif content == "premieres":
        url = f'calendars/shows/premieres/{datetime.date.today()}/14'
    results = get_data(url=url,
                       params={"extended": "full"},
                       cache_days=0.3)
    count = 1
    if not results:
        return None
    #results is a dict.  Each key is an ISO date string (day) with value as a
    #list of episodes for that date (episode), episode is a dict with keys airs-at,
    #episode (ep), and show (tv)  Get the first 20 episodes and create an ItemList
    #for each episode as VideoItem
    for day in results.items():
        for episode in day[1]: #dict of episode
            ep = episode["episode"]
            tv = episode["show"]
            title = ep["title"] if ep["title"] else ""
            label = f'{tv["title"]} - {ep["season"]}x{ep["number"]}. {title}'
            show = VideoItem(label=label,
                             path=f'{PLUGIN_BASE}extendedtvinfo&&tvdb_id={tv["ids"]["tvdb"]}')
            show.set_infos({'title': title,
                            'aired': ep["first_aired"],
                            'season': ep["season"],
                            'episode': ep["number"],
                            'tvshowtitle': tv["title"],
                            'mediatype': "episode",
                            'year': tv.get("year"),
                            'duration': tv["runtime"] * 60 if tv["runtime"] else "",
                            'studio': tv["network"],
                            'plot': tv["overview"],
                            'country': tv["country"],
                            'status': tv["status"],
                            'trailer': tv["trailer"],
                            'imdbnumber': ep["ids"]["imdb"],
                            'rating': tv["rating"],
                            'genre': " / ".join(tv["genres"]),
                            'mpaa': tv["certification"]})
            show.set_properties({'tvdb_id': ep["ids"]["tvdb"],
                                 'id': ep["ids"]["tvdb"],
                                 'imdb_id': ep["ids"]["imdb"],
                                 'homepage': tv["homepage"]})
            if tv["ids"].get("tmdb"):
                art_info = tmdb.get_tvshow(tv["ids"]["tmdb"], light=True)
                if art_info:
                    show.set_artwork(tmdb.get_image_urls(poster=art_info.get("poster_path", ""),
                                                     fanart=art_info.get("backdrop_path", "")))
            shows.append(show)
            count += 1
            if count > 20:
                break
        if count > 20:
            break
    return shows


def handle_movies(results):
    """helper function creates kutils131 VideoItems and adds to an ItemList

    Args:
        results (list): a list of dicts, each dict is Trakt data for movie

    Returns:
        ItemList: a kutils131 ItemList of VideoItems
    """
    movies = ItemList(content_type="movies")
    path = 'extendedinfo&&id=%s' if addon.bool_setting(
        "infodialog_onclick") else "playtrailer&&id=%s"
    for i in results:
        item = i["movie"] if "movie" in i else i
        trailer = f'{PLUGIN_BASE}youtubevideo&&id={utils.extract_youtube_id(item["trailer"])}'
        movie = VideoItem(label=item["title"],
                          path=PLUGIN_BASE + path % item["ids"]["tmdb"])
        movie.set_infos({'title': item["title"],
                         'duration': item["runtime"] * 60 if item["runtime"] else "",
                         'tagline': item["tagline"],
                         'mediatype': "movie",
                         'trailer': trailer,
                         'year': item["year"],
                         'mpaa': item["certification"],
                         'plot': item["overview"],
                         'imdbnumber': item["ids"]["imdb"],
                         'premiered': item["released"],
                         'rating': round(item["rating"], 1),
                         'votes': item["votes"],
                         'genre': " / ".join(item["genres"])})
        movie.set_properties({'id': item["ids"]["tmdb"],
                              'imdb_id': item["ids"]["imdb"],
                              'trakt_id': item["ids"]["trakt"],
                              'watchers': item.get("watchers"),
                              'language': item.get("language"),
                              'homepage': item.get("homepage")})
        art_info = tmdb.get_movie(item["ids"]["tmdb"], light=True)
        if art_info:
            movie.set_artwork(tmdb.get_image_urls(poster=art_info.get("poster_path"),
                                              fanart=art_info.get("backdrop_path")))
        movies.append(movie)
    movies = local_db.merge_with_local(media_type="movie",
                                       items=movies,
                                       library_first=False)
    movies.set_sorts(["mpaa", "duration"])
    return movies


def handle_tvshows(results):
    """helper function creates kutils131 VideoItems and adds to an ItemList

    Args:
        results (list): a list of dicts, each dict is Trakt data for show

    Returns:
        ItemList: a kutils131 ItemList of VideoItems
    """
    shows = ItemList(content_type="tvshows")
    for i in results:
        item = i["show"] if "show" in i else i
        airs = item.get("airs", {})
        show = VideoItem(label=item["title"],
                         path=f'{PLUGIN_BASE}extendedtvinfo&&tvdb_id={item["ids"]["tvdb"]}')
        show.set_infos({'mediatype': "tvshow",
                        'title': item["title"],
                        'duration': item["runtime"] * 60 if item["runtime"] else "",
                        'year': item["year"],
                        'premiered': item["first_aired"][:10],
                        'country': item["country"],
                        'rating': round(item["rating"], 1),
                        'votes': item["votes"],
                        'imdbnumber': item['ids']["imdb"],
                        'mpaa': item["certification"],
                        'trailer': item["trailer"],
                        'status': item.get("status"),
                        'studio': item["network"],
                        'genre': " / ".join(item["genres"]),
                        'plot': item["overview"]})
        show.set_properties({'id': item['ids']["tmdb"],
                             'tvdb_id': item['ids']["tvdb"],
                             'imdb_id': item['ids']["imdb"],
                             'trakt_id': item['ids']["trakt"],
                             'language': item["language"],
                             'aired_episodes': item["aired_episodes"],
                             'homepage': item["homepage"],
                             'airday': airs.get("day"),
                             'airshorttime': airs.get("time"),
                             'watchers': item.get("watchers")})
        art_info = tmdb.get_tvshow(item["ids"]["tmdb"], light=True)
        if art_info:
            show.set_artwork(tmdb.get_image_urls(poster=art_info.get("poster_path"),
                                             fanart=art_info.get("backdrop_path")))
        shows.append(show)
    shows = local_db.merge_with_local(media_type="tvshow",
                                      items=shows,
                                      library_first=False)
    shows.set_sorts(["mpaa", "duration"])
    return shows


def get_shows(show_type):
    """gets Trakt full data for shows of enumerated type

    Args:
        show_type (str): enum trending/popular/anticipated

    Returns:
        ItemList: a kutils131 ItemList of VideoItems
    """
    results = get_data(url=f'shows/{show_type}',
                       params={"extended": "full"})
    return handle_tvshows(results) if results else []


def get_shows_from_time(show_type, period="monthly"):
    """gets Trakt full data for shows of enumerated type for enumerated period

    Args:
        show_type (str): enum collected/played/watched
        period (str, optional): enum daily/weekly/monthly/yearly/all Defaults to "monthly"

    Returns:
        ItemList: a kutils131 ItemList of VideoItems
    """
    results = get_data(url=f'shows/{show_type}/{period}',
                       params={"extended": "full"})
    return handle_tvshows(results) if results else []


def get_movies(movie_type):
    """gets Trakt full data for movies of enumerated type

    Args:
        movie_type (str): enum trending/popular/anticipated

    Returns:
        ItemList: a kutils131 ItemList of VideoItems
    """
    results = get_data(url=f'movies/{movie_type}',
                       params={"extended": "full"})
    return handle_movies(results) if results else []


def get_movies_from_time(movie_type, period="monthly"):
    """gets Trakt full data for movies of enumerated type for enumerated period

    Args:
        movie_type (str): enum collected/played/watched
        period (str, optional): enum daily/weekly/monthly/yearly/all Defaults to "monthly"

    Returns:
        ItemList: a kutils131 ItemList of VideoItems
    """
    results = get_data(url=f'movies/{movie_type}/{period}',
                       params={"extended": "full"})
    return handle_movies(results) if results else []


def get_similar(media_type, imdb_id):
    """gets related movies or shows from imbd id

    Args:
        media_type (str): enum show/movie
        imdb_id (str): the imbd id for show or movie

    Returns:
        ItemList: a kutils131 ItemList of VideoItems
    """
    if not imdb_id or not media_type:
        return None
    results = get_data(url=f'{media_type}s/{imdb_id}/related',
                       params={"extended": "full"})
    if not results:
        return None
    if media_type == "show":
        return handle_tvshows(results)
    elif media_type == "movie":
        return handle_movies(results)


def get_data(url, params=None, cache_days=10):
    """helper function builds query and formats result.  First attempts to
    retrieve data from local cache and then issues a ResT GET to the api if cache
    data not available 

    Args:
        url (str): the url for GET operation on api
        params (dict, optional): GET query (?) Defaults to None.
        cache_days (int, optional): Max age of cached data before requesting new.
        Defaults to 10.

    Returns:
        dict: a dict from the deserialized JSON response from api or None
        Note: kutils131 does not return the GET failure code (ie if not 200)
    """
    params = params if params else {}
    params["limit"] = 10
    url = f"{BASE_URL}{url}?{urllib.parse.urlencode(params)}"
    return utils.get_JSON_response(url=url,
                                   folder="Trakt",
                                   headers=HEADERS,
                                   cache_days=cache_days)
