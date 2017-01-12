#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2012 Team-XBMC
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#    This script is based on service.skin.widgets
#    Thanks to the original authors

import sys
import xbmc
import xbmcgui
import xbmcaddon
from time import gmtime, strftime

if sys.version_info < (2, 7):
    import simplejson as json
else:
    import json

__addon__ = xbmcaddon.Addon()


class LibraryFunctions():
    def __init__(self):
        self.WINDOW = xbmcgui.Window(10000)
        self.LIMIT = 20


    # Common properties used by various types of queries
    tvepisode_properties = [
                            "title",
                            "playcount",
                            "season",
                            "episode",
                            "showtitle",
                            "plot",
                            "file",
                            "rating",
                            "resume",
                            "tvshowid",
                            "art",
                            "streamdetails",
                            "firstaired",
                            "runtime",
                            "director",
                            "writer",
                            "cast",
                            "dateadded",
                            "lastplayed"]
    tvshow_properties = [
                            "title",
                            "studio",
                            "mpaa",
                            "file",
                            "art"]

    # Common sort/filter arguments shared by multiple queries
    recent_sort = {"order": "descending", "method": "dateadded"}
    inprogress_filter = {"field": "inprogress", "operator": "true", "value": ""}
    unplayed_filter = {"field": "playcount", "operator": "lessthan", "value": "1"}
    specials_filter = {"field": "season", "operator": "greaterthan", "value": "0"}


    # Construct a JSON query string from the arguments, execute it, return UTF8
    def json_query(self, method, unplayed=False, include_specials=True, properties=None, sort=False,
                   query_filter=False, limit=False, params=False):
        # Set defaults if not all arguments are passed in
        if sort is False:
            sort = {"method": "random"}
        if properties is None:
            properties = self.tvshow_properties
        if unplayed:
            query_filter = self.unplayed_filter if not query_filter else {"and": [self.unplayed_filter, query_filter]}
        if not include_specials:
            query_filter = self.specials_filter if not query_filter else {"and": [self.specials_filter, query_filter]}

        json_query = {"jsonrpc": "2.0", "id": 1, "method": method, "params": {}}

        # As noted in the docstring, False = use a default, None=omit entirely
        if properties is not None:
            json_query["params"]["properties"] = properties
        if limit is not None:
            json_query["params"]["limits"] = {"end": limit if limit else self.LIMIT}
        if sort is not None:
            json_query["params"]["sort"] = sort
        if query_filter:
            json_query["params"]["filter"] = query_filter
        if params:
            json_query["params"].update(params)

        json_string = json.dumps(json_query)
        rv = xbmc.executeJSONRPC(json_string)

        return unicode(rv, 'utf-8', errors='ignore')

    # Recommended episodes: Earliest unwatched episode from in-progress shows
    def _fetch_recommended_episodes(self):
            # First we get a list of all the in-progress TV shows.
            json_query_string = self.json_query("VideoLibrary.GetTVShows", unplayed=True,
                                                properties=self.tvshow_properties,
                                                sort={"order": "descending",
                                                      "method": "lastplayed"},
                                                query_filter=self.inprogress_filter)
            json_query = json.loads(json_query_string)

            # If we found any, find the oldest unwatched show for each one.
            if "result" in json_query and 'tvshows' in json_query['result']:
                for item in json_query['result']['tvshows']:
                    if xbmc.abortRequested:
                        break
                    json_query2 = self.json_query("VideoLibrary.GetEpisodes", unplayed=True,
                                                  include_specials=True,
                                                  properties=self.tvepisode_properties,
                                                  sort={"method": "episode"}, limit=1,
                                                  params={"tvshowid": item['tvshowid']})
                    self.WINDOW.setProperty("recommended-episodes-data-%d"
                                            % item['tvshowid'], json_query2)
            return json_query_string


