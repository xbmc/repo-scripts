# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import datetime
import urllib
import TheMovieDB as tmdb

from kodi65 import addon
from kodi65 import utils
from kodi65 import local_db
from kodi65 import VideoItem
from kodi65 import ItemList

TRAKT_KEY = 'e9a7fba3fa1b527c08c073770869c258804124c5d7c984ce77206e695fbaddd5'
BASE_URL = "https://api-v2launch.trakt.tv/"
HEADERS = {
    'Content-Type': 'application/json',
    'trakt-api-key': TRAKT_KEY,
    'trakt-api-version': 2
}
PLUGIN_BASE = "plugin://script.extendedinfo/?info="


def get_episodes(content):
    shows = ItemList(content_type="episodes")
    url = ""
    if content == "shows":
        url = 'calendars/shows/%s/14' % datetime.date.today()
    elif content == "premieres":
        url = 'calendars/shows/premieres/%s/14' % datetime.date.today()
    results = get_data(url=url,
                       params={"extended": "full"},
                       cache_days=0.3)
    count = 1
    if not results:
        return None
    for day in results.iteritems():
        for episode in day[1]:
            ep = episode["episode"]
            tv = episode["show"]
            title = ep["title"] if ep["title"] else ""
            label = u"{0} - {1}x{2}. {3}".format(tv["title"],
                                                 ep["season"],
                                                 ep["number"],
                                                 title)
            show = VideoItem(label=label,
                             path=PLUGIN_BASE + 'extendedtvinfo&&tvdb_id=%s' % tv["ids"]["tvdb"])
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
                show.set_artwork(tmdb.get_image_urls(poster=art_info.get("poster_path"),
                                                     fanart=art_info.get("backdrop_path")))
            shows.append(show)
            count += 1
            if count > 20:
                break
    return shows


def handle_movies(results):
    movies = ItemList(content_type="movies")
    path = 'extendedinfo&&id=%s' if addon.bool_setting("infodialog_onclick") else "playtrailer&&id=%s"
    for i in results:
        item = i["movie"] if "movie" in i else i
        trailer = "%syoutubevideo&&id=%s" % (PLUGIN_BASE, utils.extract_youtube_id(item["trailer"]))
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
        movie.set_artwork(tmdb.get_image_urls(poster=art_info.get("poster_path"),
                                              fanart=art_info.get("backdrop_path")))
        movies.append(movie)
    movies = local_db.merge_with_local(media_type="movie",
                                       items=movies,
                                       library_first=False)
    movies.set_sorts(["mpaa", "duration"])
    return movies


def handle_tvshows(results):
    shows = ItemList(content_type="tvshows")
    for i in results:
        item = i["show"] if "show" in i else i
        airs = item.get("airs", {})
        show = VideoItem(label=item["title"],
                         path='%sextendedtvinfo&&tvdb_id=%s' % (PLUGIN_BASE, item['ids']["tvdb"]))
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
        show.set_artwork(tmdb.get_image_urls(poster=art_info.get("poster_path"),
                                             fanart=art_info.get("backdrop_path")))
        shows.append(show)
    shows = local_db.merge_with_local(media_type="tvshow",
                                      items=shows,
                                      library_first=False)
    shows.set_sorts(["mpaa", "duration"])
    return shows


def get_shows(show_type):
    results = get_data(url='shows/%s' % show_type,
                       params={"extended": "full"})
    return handle_tvshows(results) if results else []


def get_shows_from_time(show_type, period="monthly"):
    results = get_data(url='shows/%s/%s' % (show_type, period),
                       params={"extended": "full"})
    return handle_tvshows(results) if results else []


def get_movies(movie_type):
    results = get_data(url='movies/%s' % movie_type,
                       params={"extended": "full"})
    return handle_movies(results) if results else []


def get_movies_from_time(movie_type, period="monthly"):
    results = get_data(url='movies/%s/%s' % (movie_type, period),
                       params={"extended": "full"})
    return handle_movies(results) if results else []


def get_similar(media_type, imdb_id):
    if not imdb_id or not media_type:
        return None
    results = get_data(url='%ss/%s/related' % (media_type, imdb_id),
                       params={"extended": "full"})
    if not results:
        return None
    if media_type == "show":
        return handle_tvshows(results)
    elif media_type == "movie":
        return handle_movies(results)


def get_data(url, params=None, cache_days=10):
    params = params if params else {}
    params["limit"] = 10
    url = "%s%s?%s" % (BASE_URL, url, urllib.urlencode(params))
    return utils.get_JSON_response(url=url,
                                   folder="Trakt",
                                   headers=HEADERS,
                                   cache_days=cache_days)
