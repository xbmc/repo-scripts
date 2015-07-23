# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

from Utils import *

BASE_URL = "http://www.omdbapi.com/?tomatoes=true&plot=full&r=json&"


def get_omdb_movie_info(imdb_id):
    try:
        url = 'i=%s' % (imdb_id)
        results = get_JSON_response(BASE_URL + url, 20, "OMDB")
        for (key, value) in results.iteritems():
            if value == "N/A":
                results[key] = ""
        return results
    except:
        results = None
        log("Exception: Error when fetching Omdb data from net")
    if results is not None:
        return results
    else:
        return {}
