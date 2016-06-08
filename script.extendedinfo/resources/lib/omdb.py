# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

from kodi65 import utils

BASE_URL = "http://www.omdbapi.com/?tomatoes=true&plot=full&r=json&"


def get_movie_info(imdb_id):
    url = 'i=%s' % (imdb_id)
    results = utils.get_JSON_response(BASE_URL + url, 20, "OMDB")
    if not results:
        return None
    return {k: v for (k, v) in results.iteritems() if v != "N/A"}
