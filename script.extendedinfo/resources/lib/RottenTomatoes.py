# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

from Utils import *
from LocalDB import local_db

RT_KEY = '63sbsudx936yedd2wdmt6tkn'
BASE_URL = "http://api.rottentomatoes.com/api/public/v1.0/lists/"
PLUGIN_BASE = "plugin://script.extendedinfo/?info="


def get_movies(movie_type):
    movies = []
    url = '%s.json?apikey=%s' % (movie_type, RT_KEY)
    results = get_JSON_response(BASE_URL + url, folder="RottenTomatoes")
    if not results or "movies" not in results:
        return []
    for item in results["movies"]:
        if "alternate_ids" not in item:
            continue
        imdb_id = str(item["alternate_ids"]["imdb"])
        poster = "http://content6.flixster.com/" + item["posters"]["original"][93:]
        if SETTING("infodialog_onclick") != "false":
            path = PLUGIN_BASE + 'extendedinfo&&imdb_id=%s' % imdb_id
        else:
            search_string = "%s %s trailer" % (item["title"], item["year"])
            path = PLUGIN_BASE + "playtrailer&&title=%s&&imdb_id=%s" % (search_string, imdb_id)
        movies.append({'title': item["title"],
                       'imdb_id': imdb_id,
                       'thumb': poster,
                       'mediatype': "movie",
                       'poster': poster,
                       'Runtime': item["runtime"],
                       'duration': item["runtime"],
                       'duration(h)': format_time(item["runtime"], "h"),
                       'duration(m)': format_time(item["runtime"], "m"),
                       'year': item["year"],
                       'path': path,
                       'Premiered': item["release_dates"].get("theater", ""),
                       'mpaa': item["mpaa_rating"],
                       'Rating': item["ratings"]["audience_score"] / 10.0,
                       'Plot': item["synopsis"]})
    return local_db.merge_with_local_movie_info(movies, False)
