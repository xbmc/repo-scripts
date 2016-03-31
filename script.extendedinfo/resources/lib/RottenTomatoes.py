# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import Utils
import addon
from LocalDB import local_db

RT_KEY = '63sbsudx936yedd2wdmt6tkn'
BASE_URL = "http://api.rottentomatoes.com/api/public/v1.0/lists/"
PLUGIN_BASE = "plugin://script.extendedinfo/?info="


def get_movies(movie_type):
    movies = []
    url = '%s.json?apikey=%s' % (movie_type, RT_KEY)
    results = Utils.get_JSON_response(BASE_URL + url, folder="RottenTomatoes")
    if not results or "movies" not in results:
        return []
    for item in results["movies"]:
        if "alternate_ids" not in item:
            continue
        imdb_id = str(item["alternate_ids"]["imdb"])
        poster = "http://content6.flixster.com/" + item["posters"]["original"][93:]
        if addon.bool_setting("infodialog_onclick"):
            path = PLUGIN_BASE + 'extendedinfo&&imdb_id=%s' % imdb_id
        else:
            search_string = "%s %s trailer" % (item["title"], item["year"])
            path = PLUGIN_BASE + "playtrailer&&title=%s&&imdb_id=%s" % (search_string, imdb_id)
        movie = {'label': item["title"],
                 'path': path,
                 'title': item["title"],
                 'mediatype': "movie",
                 'duration': item["runtime"]*60,
                 'year': item["year"],
                 'Premiered': item["release_dates"].get("theater", ""),
                 'Rating': item["ratings"]["audience_score"] / 10.0,
                 'Plot': item["synopsis"],
                 'mpaa': item["mpaa_rating"]}
        movie["properties"] = {'imdb_id': imdb_id,
                               'duration(h)': Utils.format_time(item["runtime"], "h"),
                               'duration(m)': Utils.format_time(item["runtime"], "m")}
        movie["artwork"] = {'thumb': poster,
                            'poster': poster}
        movies.append(movie)
    return local_db.merge_with_local_movie_info(movies, False)
