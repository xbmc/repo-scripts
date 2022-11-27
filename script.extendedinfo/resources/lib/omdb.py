# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# Modifications copyright (C) 2022 - Scott Smart <scott967@kodi.tv>
# This program is Free Software see LICENSE file for details
"""Obtains movie info from OMDb query api

User must supply api key via addon settings

"""

from typing import Optional

from kutils import addon, utils

BASE_URL = "http://www.omdbapi.com/?tomatoes=true&plot=full&r=json&"


def get_movie_info(imdb_id: str) -> Optional[dict]:
    """gets tomato data from OMDb

    Args:
        imdb_id (str): imbd id

    Returns:
        Optional[dict]: Json.loads response from OMDb
    """
    omdb_key: str = addon.setting('OMDb API Key')
    url = 'apikey={0}&i={1}'.format(omdb_key, imdb_id)
    results = utils.get_JSON_response(BASE_URL + url, 20, "OMDB")
    if not results:
        return None
    return {k: v for (k, v) in results.items() if v != "N/A"}
