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
import sys
import urllib

### import libraries
#from lib.provider.base import BaseProvider
from lib.language import *
from lib.script_exceptions import NoFanartError
from lib.utils import *
from operator import itemgetter

### get addon info
__localize__    = ( sys.modules[ '__main__' ].__localize__ )

API_KEY = '586118be1ac673f74963cc284d46bd8e'
API_URL_TV = 'http://webservice.fanart.tv/v3/tv/%s?api_key=%s'
API_URL_MOVIE = 'http://webservice.fanart.tv/v3/movies/%s?api_key=%s'

IMAGE_TYPES_MOVIES = ['clearlogo',
                      'clearart',
                      'hdclearart',
                      'movielogo',
                      'hdmovielogo',
                      'movieart',
                      'moviedisc',
                      'hdmovieclearart',
                      'moviethumb',
                      'moviebanner']

IMAGE_TYPES_SERIES = ['clearlogo',
                      'hdtvlogo',
                      'clearart',
                      'hdclearart',
                      'tvthumb',
                      'seasonthumb',
                      'characterart',
                      'tvbanner',
                      'seasonbanner']

class FTV_TVProvider():

    def __init__(self):
        self.name = 'fanart.tv - TV API'

    def get_image_list(self, media_id):
        data = get_data(API_URL_TV%(media_id, API_KEY), 'json')
        image_list = []
        if data == 'Empty' or not data:
            return image_list
        else:
            # split 'name' and 'data'
            for value in data.iteritems():
                for art in IMAGE_TYPES_SERIES:
                    if art == value[0]:
                        for item in value[1]:
                            # Check on what type and use the general tag
                            arttypes = {'clearlogo': 'clearlogo',
                                        'hdtvlogo': 'clearlogo',
                                        'clearart': 'clearart',
                                        'hdclearart': 'clearart',
                                        'tvthumb': 'landscape',
                                        'seasonthumb': 'seasonlandscape',
                                        'characterart': 'characterart',
                                        'tvbanner': 'banner',
                                        'seasonbanner': 'seasonbanner',
                                        }
                            if art in ['hdtvlogo', 'hdclearart']:
                                size = 'HD'
                            elif art in ['clearlogo', 'clearart']:
                                size = 'SD'
                            else:
                                size = ''
                            # Create GUI info tag
                            generalinfo = '%s: %s  |  ' %( __localize__(32141), get_language(item.get('lang')).capitalize())
                            if item.get('season'):
                                generalinfo += '%s: %s  |  ' %( __localize__(32144), item.get('season'))
                            generalinfo += '%s: %s  |  ' %( __localize__(32143), item.get('likes'))
                            if art in ['hdtvlogo', 'hdclearart', 'clearlogo', 'clearart']:
                                generalinfo += '%s: %s  |  ' %( __localize__(32145), size)
                            # Fill list
                            image_list.append({'url': urllib.quote(item.get('url'), ':/'),
                                               'preview': item.get('url') + '/preview',
                                               'id': item.get('id'),
                                               'art_type': [arttypes[art]],
                                               'size': size,
                                               'season': item.get('season','n/a'),
                                               'language': item.get('lang'),
                                               'votes': int(item.get('likes')),
                                               'generalinfo': generalinfo})
            if image_list == []:
                raise NoFanartError(media_id)
            else:
                # Sort the list before return. Last sort method is primary
                image_list = sorted(image_list, key=itemgetter('votes'), reverse=True)
                image_list = sorted(image_list, key=itemgetter('size'), reverse=False)
                image_list = sorted(image_list, key=itemgetter('language'))
                return image_list
            
class FTV_MovieProvider():

    def __init__(self):
        self.name = 'fanart.tv - Movie API'

    def get_image_list(self, media_id):
        data = get_data(API_URL_MOVIE%(media_id, API_KEY), 'json')
        image_list = []
        if data == 'Empty' or not data:
            return image_list
        else:
            for value in data.iteritems():
                for art in IMAGE_TYPES_MOVIES:
                    if art == value[0]:
                        for item in value[1]:
                            # Check on what type and use the general tag
                            arttypes = {'movielogo': 'clearlogo',
                                        'moviedisc': 'discart',
                                        'movieart': 'clearart',
                                        'hdmovielogo': 'clearlogo',
                                        'hdmovieclearart': 'clearart',
                                        'moviebanner': 'banner',
                                        'moviethumb': 'landscape'}
                            if art in ['hdmovielogo', 'hdmovieclearart']:
                                size = 'HD'
                            elif art in ['movielogo', 'movieart']:
                                size = 'SD'
                            else:
                                size = ''
                            # Create GUI info tag
                            generalinfo = '%s: %s  |  ' %( __localize__(32141), get_language(item.get('lang')).capitalize())
                            if item.get('disc_type'):
                                generalinfo += '%s: %s (%s)  |  ' %( __localize__(32146), item.get('disc'), item.get('disc_type'))
                            if art in ['hdmovielogo', 'hdmovieclearart', 'movielogo', 'movieclearart']:
                                generalinfo += '%s: %s  |  ' %( __localize__(32145), size)
                            generalinfo += '%s: %s  |  ' %( __localize__(32143), item.get('likes'))
                            # Fill list
                            image_list.append({'url': urllib.quote(item.get('url'), ':/'),
                                               'preview': item.get('url') + '/preview',
                                               'id': item.get('id'),
                                               'art_type': [arttypes[art]],
                                               'size': size,
                                               'season': item.get('season','n/a'),
                                               'language': item.get('lang'),
                                               'votes': int(item.get('likes')),
                                               'disctype': item.get('disc_type','n/a'),
                                               'discnumber': item.get('disc','n/a'),
                                               'generalinfo': generalinfo})
            if image_list == []:
                raise NoFanartError(media_id)
            else:
                # Sort the list before return. Last sort method is primary
                image_list = sorted(image_list, key=itemgetter('votes'), reverse=True)
                image_list = sorted(image_list, key=itemgetter('size'), reverse=False)
                image_list = sorted(image_list, key=itemgetter('language'))
                return image_list