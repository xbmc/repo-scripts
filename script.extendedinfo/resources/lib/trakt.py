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
    get_shows_from_time(show_type, period) gets tvshows for showtype collected/played/
                                           watched for previous month
                                           returns a kutils131 ItemList
    get_movies(movie_type) gets movies for movietype trending/popular/anticipated
                           returns a kutils131 ItemList
    get_movies_from_time(movie_type, period) gets movies forf movietype collected/
                                             played/watched for previous month
    get_similar(media_type, imdb_id) gets related mediatype show(s)/movie(s) from
                                     an imdb id.
"""

from __future__ import annotations

import datetime
import urllib.error
import urllib.parse
import urllib.request

import xbmc

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


def get_episodes(content:str) -> ItemList[VideoItem]:
    """gets upcoming 14 days/premiering episodes from today

    Args:
        content (str): enum shows (upcoming) or premieres (new shows)

    Returns:
        ItemList: a kutil131 ItemList instance of VideoItems
    """
    shows = ItemList(content_type="episodes")
    url = ""
    if content == "shows":
        url = f'calendars/all/shows/{datetime.date.today()}/14'
    elif content == "premieres":
        url = f'calendars/all/shows/premieres/{datetime.date.today()}/14'
    results = get_data(url=url,
                       params={"extended": "full"},
                       cache_days=0.3)
    if not results:
        return None
    #results is a list of dict.  Each dict contains "first aired" an ISO date string (day),
    #episode is a dict,
    #show is a dict.  Get the first 20 episodes and create an ItemList
    #for each episode as VideoItem
    count = 1
    for airing_episode in results:
        air_date = airing_episode["first_aired"]
        ep:dict = airing_episode["episode"]
        tv:dict = airing_episode["show"]
        title = airing_episode["episode"].get("title", xbmc.getLocalizedString(231))
        label = f'{tv["title"]} - {ep["season"]}x{ep["number"]}. {title}'
        show = VideoItem(label=label,
                            path=f'{PLUGIN_BASE}extendedtvinfo&&tvdb_id={tv["ids"]["tvdb"]}')
        show.set_infos({'title': title,
                        'aired': air_date,
                        'season': ep["season"],
                        'episode': ep["number"],
                        'tvshowtitle': tv["title"],
                        'mediatype': "episode",
                        'year': tv.get("year"),
                        'duration': tv.get("runtime", 0) * 60,
                        'studio': tv["network"],
                        'plot': tv["overview"],
                        'country': tv["country"],
                        'status': tv["status"],
                        'trailer': tv["trailer"],
                        'imdbnumber': ep["ids"]["imdb"],
                        'rating': tv["rating"],
                        'genre': " / ".join(tv["genres"]),
                        'mpaa': tv.get("certification","")})
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
    return shows


def handle_movies(results:list[dict]) -> ItemList[VideoItem]:
    """helper function creates kutil131 VideoItems and adds to an ItemList

    Args:
        results (list): a list of dicts, each dict is Trakt data for movie

    Returns:
        ItemList: a kutil131 ItemList of VideoItems
    """
    movies = ItemList(content_type="movies")
    path = 'extendedinfo&&id=%s' if addon.bool_setting(
        "infodialog_onclick") else "playtrailer&&id=%s"
    for i in results:
        item:dict = i["movie"] if "movie" in i else i
        trailer = f'{PLUGIN_BASE}youtubevideo&&id={utils.extract_youtube_id(item["trailer"])}'
        movie = VideoItem(label=item["title"],
                          path=PLUGIN_BASE + path % item["ids"]["tmdb"])
        movie.set_infos({'title': item.get("title", ""),
                         'duration': item["runtime"] * 60 if item["runtime"] else "",
                         'tagline': item.get("tagline", ""),
                         'mediatype': "movie",
                         'trailer': trailer,
                         'year': item.get("year", ""),
                         'mpaa': item.get("certification", ""),
                         'plot': item.get("overview", ""),
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
        if item["ids"].get("tmdb"):
            utils.log('trakt.handle_movies get art from tmdb')
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
    """helper function creates kutil131 VideoItems and adds to an ItemList

    Args:
        results (list): a list of dicts, each dict is Trakt data for show

    Returns:
        ItemList: a kutil131 ItemList of VideoItems
    """
    shows = ItemList(content_type="tvshows")
    for i in results:
        item = i["show"] if "show" in i else i
        airs = item.get("airs", {})
        show = VideoItem(label=item["title"],
                         path=f'{PLUGIN_BASE}extendedtvinfo&&tvdb_id={item["ids"]["tvdb"]}')
        show.set_infos({'mediatype': "tvshow",
                        'title': item.get("title", ""),
                        'duration': item["runtime"] * 60 if item["runtime"] else "",
                        'year': item["year"],
                        'premiered': item["first_aired"][:10],
                        'country': item.get("country", ""),
                        'rating': round(item["rating"], 1),
                        'votes': item["votes"],
                        'imdbnumber': item['ids']["imdb"],
                        'mpaa': item.get("certification", ""),
                        'trailer': item.get("trailer", ""),
                        'status': item.get("status"),
                        'studio': item.get("network", ""),
                        'genre': " / ".join(item["genres"]),
                        'plot': item.get("overview", "")})
        show.set_properties({'id': item['ids']["tmdb"],
                             'tvdb_id': item['ids']["tvdb"],
                             'imdb_id': item['ids']["imdb"],
                             'trakt_id': item['ids']["trakt"],
                             'language': item.get("language", ""),
                             'aired_episodes': item["aired_episodes"],
                             'homepage': item.get("homepage", ""),
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
        ItemList: a kutil131 ItemList of VideoItems
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


def get_movies(movie_type:str) -> ItemList[VideoItem]:
    """gets Trakt full data for movies of enumerated type

    Args:
        movie_type (str): enum trending/popular/anticipated

    Returns:
        ItemList: a kutil131 ItemList of VideoItems
    """
    results = get_data(url=f'movies/{movie_type}',
                       params={"extended": "full"})
    return handle_movies(results) if results else []


def get_movies_from_time(movie_type:str, period="monthly") -> ItemList[VideoItem]:
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


def get_data(url:str, params:dict=None, cache_days:int=10) -> list[dict]:
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
        Note: kutil131 does not return the GET failure code (ie if not 200)
    """
    params = params if params else {}
    params["limit"] = 10
    url = f"{BASE_URL}{url}?{urllib.parse.urlencode(params)}"
    return utils.get_JSON_response(url=url,
                                   folder="Trakt",
                                   headers=HEADERS,
                                   cache_days=cache_days)
