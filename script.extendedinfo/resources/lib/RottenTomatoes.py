# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

from kodi65 import addon
from kodi65 import utils
from kodi65 import local_db
from kodi65 import VideoItem
from kodi65 import ItemList

RT_KEY = '63sbsudx936yedd2wdmt6tkn'
BASE_URL = "http://api.rottentomatoes.com/api/public/v1.0/lists/"
PLUGIN_BASE = "plugin://script.extendedinfo/?info="


def get_movies(movie_type):
    movies = ItemList(content_type="movies")
    url = '%s.json?apikey=%s' % (movie_type, RT_KEY)
    results = utils.get_JSON_response(BASE_URL + url, folder="RottenTomatoes")
    if "error" in results:
        utils.notify("Error", results["error"])
    if not results or "movies" not in results:
        return []
    for item in results["movies"]:
        if "alternate_ids" not in item:
            continue
        imdb_id = str(item["alternate_ids"]["imdb"])
        if addon.bool_setting("infodialog_onclick"):
            path = PLUGIN_BASE + 'extendedinfo&&imdb_id=%s' % imdb_id
        else:
            search_string = "%s %s trailer" % (item["title"], item["year"])
            path = PLUGIN_BASE + "playtrailer&&title=%s&&imdb_id=%s" % (search_string, imdb_id)
        movie = VideoItem(label=item.get('title'),
                          path=path)
        movie.set_infos({'title': item["title"],
                         'mediatype': "movie",
                         'duration': item["runtime"] * 60,
                         'year': item["year"],
                         'premiered': item["release_dates"].get("theater", ""),
                         'rating': item["ratings"]["audience_score"] / 10.0,
                         'plot': item["synopsis"],
                         'imdbnumber': imdb_id,
                         'mpaa': item["mpaa_rating"]})
        movie.set_properties({'imdb_id': imdb_id})
        movie.set_artwork({'thumb': item["posters"]["original"],
                           'poster': item["posters"]["original"]})
        movies.append(movie)
    return local_db.merge_with_local(media_type="movie",
                                     items=movies,
                                     library_first=False)
