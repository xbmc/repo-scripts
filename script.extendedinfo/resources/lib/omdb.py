# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# Modifications copyright (C) 2022 - Scott Smart <scott967@kodi.tv>
# This program is Free Software see LICENSE file for details
"""Obtains movie info from OMDb query api

User must supply api key via addon settings

"""

from __future__ import annotations

from resources.kutil131 import addon

from resources.kutil131 import utils

BASE_URL = "http://www.omdbapi.com/?tomatoes=true&plot=full&r=json&"


def get_movie_info(imdb_id: str) -> dict | None:
    """gets tomato data from OMDb

    Args:
        imdb_id (str): imbd id

    Returns:
        dict | None: Json.loads response from OMDb or None if not available
    """
    omdb_key: str = addon.setting('OMDb API Key')
    url = f'apikey={omdb_key}&i={imdb_id}'
    results = utils.get_JSON_response(BASE_URL + url, 20, "OMDB")
    if not results:
        return None
    return {k: v for (k, v) in results.items() if v != "N/A"}
