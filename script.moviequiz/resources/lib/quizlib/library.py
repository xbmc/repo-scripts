#
#      Copyright (C) 2013 Tommy Winther
#      http://tommy.winther.nu
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this Program; see the file LICENSE.txt.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#

from typing import Dict
import json

import xbmc

from resources.lib.util import logger


# library item attribute keys
KEY_ACTOR =          'actor'
KEY_ART =            'art'
KEY_ARTIST =         'artist'
KEY_ARTIST_ID =      'artistid'
KEY_CAST =           'cast'
KEY_DIRECTOR =       'director'
KEY_EPISODE =        'episode'
KEY_FANART =         'fanart'
KEY_FIRST_AIRED =    'firstaired'
KEY_FILE =           'file'
KEY_GENRE =          'genre'
KEY_LABEL =          'label'
KEY_MOVIE_ID =       'movieid'
KEY_MPAA_RATING =    'mpaarating'
KEY_NAME =           'name'
KEY_PLAY_COUNT =     'playcount'
KEY_POSTER =         'poster'
KEY_ROLE =           'role'
KEY_RUNTIME =        'runtime'
KEY_STUDIO =         'studio'
KEY_SEASON =         'season'
KEY_SET =            'set'
KEY_SHOW_TITLE =     'showtitle'
KEY_TAGLINE =        'tagline'
KEY_THUMBNAIL =      'thumbnail'
KEY_TITLE =          'title'
KEY_TVSHOW =         'tvshow'
KEY_TVSHOW_ID =      'tvshowid'
KEY_TVSHOW_POSTER =  'tvshow.poster'
KEY_YEAR =           'year'

GENRE_ANIMATION = 'Animation'

MPAA_RATINGS = {
    'G': ['G', 'Rated G'],
    'PG': ['PG', 'Rated PG'],
    'PG-13': ['PG-13', 'Rated PG-13'],
    'R': ['R', 'Rated R'],
    'NR': ['NR', 'Rated NR', 'Not Rated'],
    'TV-Y': ['TV-Y', 'Rated TV-Y'],
    'TV-Y7': ['TV-Y7', 'Rated TV-Y7', 'TV-Y7-FV', 'Rated TV-Y7-FV'],
    'TV-G': ['TV-G', 'Rated TV-G'],
    'TV-PG': ['TV-PG', 'Rated TV-PG'],
    'TV-14': ['TV-14', 'Rated TV-14'],
    'TV-MA': ['TV-MA', 'Rated TV-MA'],
    'none': ['']
}

# filter operation strings
FILTER_OP_IS =               'is'
FILTER_OP_ISNOT =            'isnot'
FILTER_OP_CONTAINS =         'contains'
FILTER_OP_DOES_NOT_CONTAIN = 'doesnotcontain'
FILTER_OP_GREATER_THAN =     'greaterthan'
FILTER_OP_LESS_THAN =        'lessthan'


def _getFilter(operator: str, field: str, value: str) -> Dict:
    return {
        'operator': operator,
        'field': field,
        'value': value
    }


def _getParamsRandSort() -> Dict:
    return {'sort': {'method': 'random'}}


def getMovies(properties=None):
    params = _getParamsRandSort()
    return VideoQuery('VideoLibrary.GetMovies', params, properties, 'movies')


def getTVShows(properties=None):
    params = _getParamsRandSort()
    return VideoQuery('VideoLibrary.GetTVShows', params, properties, 'tvshows')


def getSeasons(tvShowId, properties=None):
    params = _getParamsRandSort()
    params['tvshowid'] = tvShowId
    return VideoQuery('VideoLibrary.GetSeasons', params, properties, 'seasons')


def getEpisodes(properties=None):
    params = _getParamsRandSort()
    return VideoQuery('VideoLibrary.GetEpisodes', params, properties, 'episodes')


def getSongs(properties=None):
    params = _getParamsRandSort()
    return AudioQuery('AudioLibrary.GetSongs', params, properties, 'songs')


def getAlbums(properties=None):
    params = _getParamsRandSort()
    return AudioQuery('AudioLibrary.GetAlbums', params, properties, 'albums')


def getArtists(properties=None):
    params = _getParamsRandSort()
    return AudioQuery('AudioLibrary.GetArtists', params, properties, 'artists')


def getArtistDetails(artistId, properties=None):
    params = {KEY_ARTIST_ID: artistId}
    return AudioQuery('AudioLibrary.GetArtistDetails', params, properties, 'artistdetails')


def hasMovies():
    return Query('XBMC.GetInfoBooleans', {'booleans': ['Library.HasContent(Movies)']},
                 resultKey='Library.HasContent(Movies)').asList()


def hasTVShows():
    return Query('XBMC.GetInfoBooleans', {'booleans': ['Library.HasContent(TVShows)']},
                 resultKey='Library.HasContent(TVShows)').asList()


def hasMusic():
    return Query('XBMC.GetInfoBooleans', {'booleans': ['Library.HasContent(Music)']},
                 resultKey='Library.HasContent(Music)').asList()


def isAnyVideosWatched():
    return len(getMovies([]).minPlayCount(1).limitTo(1).asList()) > 0


def isAnyMPAARatingsAvailable():
    query = getMovies([]).limitTo(1)
    query.filters.append(_getFilter(FILTER_OP_ISNOT, KEY_MPAA_RATING, ''))
    return len(query.asList()) > 0


def isAnyContentRatingsAvailable():
    query = getTVShows([]).limitTo(1)
    query.filters.append(_getFilter(FILTER_OP_ISNOT, KEY_MPAA_RATING, ''))
    return len(query.asList()) > 0


def buildRatingsFilters(ratings):
    logger.debug(f"ratings string: {ratings}")
    ratings = [r.strip() for r in ratings.split('|') if r.strip()]
    filters = list()

    for rating in ratings:
        for ratingAlias in MPAA_RATINGS[rating]:
            filters.append(_getFilter(FILTER_OP_IS, KEY_MPAA_RATING, ratingAlias))

    logger.debug(f"ratings filters: {filters}")
    return [{
        'or': filters
    }]


def buildOnlyWatchedFilter():
    return [_getFilter(FILTER_OP_GREATER_THAN, KEY_PLAY_COUNT, '0')]


class Query:
    def __init__(self, method, params, properties=None, resultKey=None, queryId=1):
        self.properties = properties
        self.params = params
        self.filters = list()
        self.resultKey = resultKey
        self.query = {
            'jsonrpc': '2.0',
            'id': queryId,
            'method': method
        }

    def getResponse(self):
        if self.filters:
            self.params['filter'] = {'and': self.filters}
        if self.properties:
            self.params['properties'] = self.properties
        if self.params:
            self.query['params'] = self.params

        command = json.dumps(self.query)
        logger.debug(f'jsonrpc request: {command}')
        resp = xbmc.executeJSONRPC(command)
        logger.debug(f'jsonrpc response: {resp}')
        return json.loads(resp)

    def asList(self):
        response = self.getResponse()
        if 'result' in response and self.resultKey in response['result']:
            return response['result'][self.resultKey]
        else:
            return list()

    def asItem(self):
        result = self.asList()
        if type(result) == list:
            return result[0] if result else None
        else:
            return result

    def withFilters(self, filters):
        self.filters.extend(iter(filters))
        return self

    def limitTo(self, end):
        self.params['limits'] = {'start': 0, 'end': end}
        return self

    def excludeTitles(self, titles):
        if type(titles) == list:
            for title in titles:
                self.filters.append(_getFilter(FILTER_OP_DOES_NOT_CONTAIN, KEY_TITLE, title))
        else:
            self.filters.append(_getFilter(FILTER_OP_ISNOT, KEY_TITLE, titles))
        return self


class VideoQuery(Query):
    def inSet(self, setName):
        self.filters.append(_getFilter(FILTER_OP_IS, KEY_SET, setName))
        return self

    def inGenre(self, genre):
        self.filters.append(_getFilter(FILTER_OP_CONTAINS, KEY_GENRE, genre))
        return self

    def withActor(self, actor):
        self.filters.append(_getFilter(FILTER_OP_IS, KEY_ACTOR, actor))
        return self

    def withoutActor(self, actor):
        self.filters.append(_getFilter(FILTER_OP_ISNOT, KEY_ACTOR, actor))
        return self

    def fromYear(self, fromYear):
        self.filters.append(_getFilter(FILTER_OP_GREATER_THAN, KEY_YEAR, str(fromYear)))
        return self

    def toYear(self, toYear):
        self.filters.append(_getFilter(FILTER_OP_LESS_THAN, KEY_YEAR, str(toYear)))
        return self

    def directedBy(self, directedBy):
        self.filters.append(_getFilter(FILTER_OP_IS, KEY_DIRECTOR, directedBy))
        return self

    def notDirectedBy(self, notDirectedBy):
        self.filters.append(_getFilter(FILTER_OP_ISNOT, KEY_DIRECTOR, notDirectedBy))
        return self

    def minPlayCount(self, playCount):
        self.filters.append(_getFilter(FILTER_OP_GREATER_THAN, KEY_PLAY_COUNT, str(playCount - 1)))
        return self

    def fromShow(self, tvShow: str):
        self.filters.append(_getFilter(FILTER_OP_IS, KEY_TVSHOW, tvShow))
        return self

    def fromSeason(self, season):
        self.filters.append(_getFilter(FILTER_OP_IS, KEY_SEASON, str(season)))
        return self

    def episode(self, episode: int):
        self.filters.append(_getFilter(FILTER_OP_IS, KEY_EPISODE, str(episode)))
        return self


class AudioQuery(Query):
    def withArtist(self, artist):
        self.filters.append(_getFilter(FILTER_OP_IS, KEY_ARTIST, artist))
        return self

    def withoutArtist(self, artist):
        self.filters.append(_getFilter(FILTER_OP_ISNOT, KEY_ARTIST, artist))
        return self
