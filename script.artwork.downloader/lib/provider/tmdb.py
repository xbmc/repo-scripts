#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2011-2014 Martijn Kaijser
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 2 of the License, or
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

#import modules
import xbmc
import sys

### import libraries
from lib.language import *
from lib.script_exceptions import NoFanartError
from lib.utils import *
from operator import itemgetter

### get addon info
__localize__    = ( sys.modules[ "__main__" ].__localize__ )

API_KEY = '4be68d7eab1fbd1b6fd8a3b80a65a95e'
API_CFG = 'http://api.themoviedb.org/3/configuration?api_key=%s'
API_URL = 'http://api.themoviedb.org/3/movie/%s/images?api_key=%s'

class TMDBProvider():

    def __init__(self):
        self.name = 'TMDB'

    def get_image_list(self, media_id):
        image_list = []
        api_cfg = get_data(API_CFG%(API_KEY), 'json')
        if api_cfg == "Empty" or not api_cfg:
            return image_list
        BASE_IMAGEURL = api_cfg['images'].get('base_url')
        data = get_data(API_URL%(media_id, API_KEY), 'json')
        if data == "Empty" or not data:
            return image_list
        else:
            # Get fanart
            try:
                for item in data['backdrops']:
                    if int(item.get('vote_count')) >= 1:
                        rating = float( "%.1f" % float( item.get('vote_average'))) #output string with one decimal
                        votes = item.get('vote_count','n/a')
                    else:
                        rating = 'n/a'
                        votes = 'n/a'
                    image_list.append({'url': BASE_IMAGEURL + 'original' + item['file_path'],
                                       'preview': BASE_IMAGEURL + 'w300' + item['file_path'],
                                       'id': item.get('file_path').lstrip('/').replace('.jpg', ''),
                                       'art_type': ['fanart','extrafanart'],
                                       'height': item.get('height'),
                                       'width': item.get('width'),
                                       'language': item.get('iso_639_1','n/a'),
                                       'rating': rating,
                                       'votes': votes,
                                       # Create Gui string to display
                                       'generalinfo': ('%s: %s  |  %s: %s  |  %s: %s  |  %s: %sx%s  |  ' 
                                                       %( __localize__(32141), get_language(item.get('iso_639_1','n/a')).capitalize(),
                                                          __localize__(32142), rating,
                                                          __localize__(32143), votes,
                                                          __localize__(32145), item.get('width'), item.get('height')))})
            except Exception, e:
                log( 'Problem report: %s' %str( e ), xbmc.LOGNOTICE )
            # Get thumbs
            try:
                for item in data['backdrops']:
                    if int(item.get('vote_count')) >= 1:
                        rating = float( "%.1f" % float( item.get('vote_average'))) #output string with one decimal
                        votes = item.get('vote_count','n/a')
                    else:
                        rating = 'n/a'
                        votes = 'n/a'
                    # Fill list
                    image_list.append({'url': BASE_IMAGEURL + 'w780' + item['file_path'],
                                       'preview': BASE_IMAGEURL + 'w300' + item['file_path'],
                                       'id': item.get('file_path').lstrip('/').replace('.jpg', ''),
                                       'art_type': ['extrathumbs'],
                                       'height': item.get('height'),
                                       'width': item.get('width'),
                                       'language': item.get('iso_639_1','n/a'),
                                       'rating': rating,
                                       'votes': votes,
                                       # Create Gui string to display
                                       'generalinfo': ('%s: %s  |  %s: %s  |  %s: %s  |  %s: %sx%s  |  ' 
                                                       %( __localize__(32141), get_language(item.get('iso_639_1','n/a')).capitalize(),
                                                          __localize__(32142), rating,
                                                          __localize__(32143), votes,
                                                          __localize__(32145), item.get('width'), item.get('height')))})
            except Exception, e:
                log( 'Problem report: %s' %str( e ), xbmc.LOGNOTICE )
            # Get posters
            try:
                for item in data['posters']:
                    if int(item.get('vote_count')) >= 1:
                        rating = float( "%.1f" % float( item.get('vote_average'))) #output string with one decimal
                        votes = item.get('vote_count','n/a')
                    else:
                        rating = 'n/a'
                        votes = 'n/a'
                    # Fill list
                    image_list.append({'url': BASE_IMAGEURL + 'original' + item['file_path'],
                                       'preview': BASE_IMAGEURL + 'w185' + item['file_path'],
                                       'id': item.get('file_path').lstrip('/').replace('.jpg', ''),
                                       'art_type': ['poster'],
                                       'height': item.get('height'),
                                       'width': item.get('width'),
                                       'language': item.get('iso_639_1','n/a'),
                                       'rating': rating,
                                       'votes': votes,
                                       # Create Gui string to display
                                       'generalinfo': ('%s: %s  |  %s: %s  |  %s: %s  |  %s: %sx%s  |  ' 
                                                       %( __localize__(32141), get_language(item.get('iso_639_1','n/a')).capitalize(),
                                                          __localize__(32142), rating,
                                                          __localize__(32143), votes,
                                                          __localize__(32145), item.get('width'), item.get('height')))})
            except Exception, e:
                log( 'Problem report: %s' %str( e ), xbmc.LOGNOTICE )
            if image_list == []:
                raise NoFanartError(media_id)
            else:
                # Sort the list before return. Last sort method is primary
                image_list = sorted(image_list, key=itemgetter('rating'), reverse=True)
                image_list = sorted(image_list, key=itemgetter('language'))
                return image_list


def _search_movie(medianame,year=''):
    medianame = normalize_string(medianame)
    log('TMDB API search criteria: Title[''%s''] | Year[''%s'']' % (medianame,year) )
    illegal_char = ' -<>:"/\|?*%'
    for char in illegal_char:
        medianame = medianame.replace( char , '+' ).replace( '++', '+' ).replace( '+++', '+' )

    search_url = 'http://api.themoviedb.org/3/search/movie?query=%s+%s&api_key=%s' %( medianame, year, API_KEY )
    tmdb_id = ''
    log('TMDB API search:   %s ' % search_url)
    try:
        data = get_data(search_url, 'json')
        if data == "Empty":
            tmdb_id = ''
        else:
            for item in data['results']:
                if item['id']:
                    tmdb_id = item['id']
                    break
    except Exception, e:
        log( str( e ), xbmc.LOGERROR )
    if tmdb_id == '':
        log('TMDB API search found no ID')
    else:
        log('TMDB API search found ID: %s' %tmdb_id)
    return tmdb_id