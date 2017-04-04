#!/usr/bin/python
# -*- coding: utf-8 -*-

'''get metadata from omdb'''

from utils import get_json, formatted_number, int_with_commas, try_parse_int, KODI_LANGUAGE
from simplecache import use_cache
import arrow
import xbmc


class Omdb(object):
    '''get metadata from omdb'''
    base_url = 'http://www.omdbapi.com/'

    def __init__(self, simplecache=None):
        '''Initialize - optionaly provide simplecache object'''
        if not simplecache:
            from simplecache import SimpleCache
            self.cache = SimpleCache()
        else:
            self.cache = simplecache

    def get_details_by_imdbid(self, imdb_id):
        '''get omdb details by providing an imdb id'''
        params = {"i": imdb_id}
        data = self.get_data(params)
        return self.map_details(data) if data else {}

    def get_details_by_title(self, title, year="", media_type=""):
        ''' get omdb details by title
            title --> The title of the media to look for (required)
            year (str/int)--> The year of the media (optional, better results when provided)
            media_type --> The type of the media: movie/tvshow (optional, better results of provided)
        '''
        if "movie" in media_type:
            media_type = "movie"
        elif media_type in ["tvshows", "tvshow"]:
            media_type = "series"
        params = {"t": title, "y": year, "type": media_type}
        data = self.get_data(params)
        return self.map_details(data) if data else {}

    @use_cache(7)
    def get_data(self, params):
        '''helper method to get data from omdb json API'''
        params["plot"] = "short"
        params["tomatoes"] = True
        params["r"] = "json"
        data = get_json(self.base_url, params)
        if data is None:
            self.base_url = 'http://svr2.omdbapi.com/'  # fallback to temporary omdb server
            data = get_json(self.base_url, params)
        return data

    @staticmethod
    def map_details(data):
        '''helper method to map the details received from omdb to kodi compatible format'''
        result = {}
        for key, value in data.iteritems():
            # filter the N/A values
            if value == "N/A" or not value:
                continue
            if key == "Title":
                result["title"] = value
            elif key == "Year":
                try:
                    result["year"] = try_parse_int(value.split("-")[0])
                except Exception:
                    result["year"] = value
            elif key == "Year":
                result["year"] = value
            if key == "Rated":
                result["mpaa"] = value.replace("Rated", "")
            elif key == "Title":
                result["title"] = value
            elif key == "Released":
                date_time = arrow.get(value, "DD MMM YYYY")
                result["premiered"] = date_time.strftime(xbmc.getRegion("dateshort"))
                try:
                    result["premiered.formatted"] = date_time.format('DD MMM YYYY', locale=KODI_LANGUAGE)
                except Exception:
                    result["premiered.formatted"] = value
            elif key == "Runtime":
                result["runtime"] = try_parse_int(value.replace(" min", "")) * 60
            elif key == "Genre":
                result["genre"] = value.split(", ")
            elif key == "Director":
                result["director"] = value.split(", ")
            elif key == "Writer":
                result["writer"] = value.split(", ")
            elif key == "Country":
                result["country"] = value.split(", ")
            elif key == "Awards":
                result["awards"] = value
                result["RottenTomatoesAwards"] = value  # legacy
            elif key == "Poster":
                result["thumbnail"] = value
                result["art"] = {}
                result["art"]["thumb"] = value
            elif key == "Metascore":
                result["metacritic.rating"] = value
                result["rating.mc"] = value
            elif key == "imdbRating":
                result["rating.imdb"] = value
                result["rating"] = float(value)
                result["rating.percent.imdb"] = "%s" % (try_parse_int(float(value) * 10))
            elif key == "imdbVotes":
                result["votes.imdb"] = value
                result["votes"] = try_parse_int(value.replace(",", ""))
            elif key == "imdbID":
                result["imdbnumber"] = value
            elif key == "BoxOffice":
                result["boxoffice"] = value
            elif key == "DVD":
                date_time = arrow.get(value, "DD MMM YYYY")
                result["dvdrelease"] = date_time.format('YYYY-MM-DD')
                result["dvdrelease.formatted"] = date_time.format('DD MMM YYYY', locale=KODI_LANGUAGE)
            elif key == "Production":
                result["studio"] = value.split(", ")
            elif key == "Website":
                result["homepage"] = value
            # rotten tomatoes
            elif key == "tomatoMeter":
                result["rottentomatoes.meter"] = value
                result["rottentomatoesmeter"] = value
            if key == "tomatoRating":
                result["rottentomatoes.rating"] = value
                result["rottentomatoes.rating.percent"] = "%s" % (try_parse_int(float(value) * 10))
                result["rating.rt"] = value
            elif key == "tomatoFresh":
                result["rottentomatoes.fresh"] = value
                result["rottentomatoesfresh"] = value  # legacy
            elif key == "tomatoReviews":
                result["rottentomatoes.reviews"] = formatted_number(value)
                result["rottentomatoesreviews"] = formatted_number(value)  # legacy
            elif key == "tomatoRotten":
                result["rottentomatoes.rotten"] = value
                result["rottentomatoesrotten"] = value  # legacy
            elif key == "tomatoImage":
                result["rottentomatoes.image"] = value
                result["rottentomatoesimage"] = value  # legacy
            elif key == "tomatoConsensus":
                result["rottentomatoes.consensus"] = value
                result["rottentomatoesconsensus"] = value  # legacy
            elif key == "tomatoUserMeter":
                result["rottentomatoes.usermeter"] = value
            elif key == "tomatoUserRating":
                result["rottentomatoes.userrating"] = value
                result["rottentomatoes.userrating.percent"] = "%s" % (try_parse_int(float(value) * 10))
            elif key == "tomatoUserReviews":
                result["rottentomatoes.userreviews"] = int_with_commas(value)
            elif key == "tomatoURL":
                result["rottentomatoes.url"] = value
        return result
