# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

from Utils import *
from local_db import merge_with_local_movie_info

RT_KEY = '63sbsudx936yedd2wdmt6tkn'
BASE_URL = "http://api.rottentomatoes.com/api/public/v1.0/lists/"


def get_rottentomatoes_movies(movietype):
    movies = []
    url = movietype + '.json?apikey=%s' % (RT_KEY)
    results = get_JSON_response(BASE_URL + url, folder="RottenTomatoes")
    if not results or "movies" not in results:
        return []
    for item in results["movies"]:
        if "alternate_ids" in item:
            imdb_id = str(item["alternate_ids"]["imdb"])
        else:
            imdb_id = ""
        poster = "http://" + item["posters"]["original"].replace("tmb", "ori")[64:]
        if SETTING("infodialog_onclick") != "false":
            path = 'plugin://script.extendedinfo/?info=extendedinfo&&imdb_id=%s' % imdb_id
        else:
            search_string = "%s %s trailer" % (item["title"], str(item["year"]))
            path = "plugin://script.extendedinfo/?info=playtrailer&&title=%s&&imdb_id=%s" % (search_string, imdb_id)
        movie = {'title': item["title"],
                 'imdb_id': imdb_id,
                 'thumb': poster,
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
                 'Plot': item["synopsis"]}
        if imdb_id:
            movies.append(movie)
    return merge_with_local_movie_info(movies, False)
