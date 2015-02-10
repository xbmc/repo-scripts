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

#import libraries
import xml.etree.ElementTree as ET
from operator import itemgetter
from lib.language import *
from lib.script_exceptions import NoFanartError
from lib.utils import *

API_URL = 'http://www.thetvdb.com/api/%s/series/%s/banners.xml'

### get addon info
__localize__    = ( sys.modules[ "__main__" ].__localize__ )

class TVDBProvider():
    """
    Setup provider for TheTVDB.com
    """
    def __init__(self):
        self.name = 'TVDB'
        self.api_key = '1A41A145E2DA0053'
        
        self.url_prefix = 'http://www.thetvdb.com/banners/'

    def get_image_list(self, media_id):
        image_list = []
        data = get_data(API_URL%(self.api_key, media_id), 'xml')
        try:
            tree = ET.fromstring(data)
            for image in tree.findall('Banner'):
                info = {}
                if image.findtext('BannerPath'):
                    info['url'] = self.url_prefix + image.findtext('BannerPath')
                    if image.findtext('ThumbnailPath'):
                        info['preview'] = self.url_prefix + image.findtext('ThumbnailPath')
                    else:
                        info['preview'] = self.url_prefix + image.findtext('BannerPath')
                    info['language'] = image.findtext('Language')
                    info['id'] = image.findtext('id')
                    # process fanarts
                    if image.findtext('BannerType') == 'fanart':
                        info['art_type'] = ['fanart','extrafanart']
                    # process posters
                    elif image.findtext('BannerType') == 'poster':
                        info['art_type'] = ['poster']
                    # process banners
                    elif image.findtext('BannerType') == 'series' and image.findtext('BannerType2') == 'graphical':
                        info['art_type'] = ['banner']
                    # process seasonposters
                    elif image.findtext('BannerType') == 'season' and image.findtext('BannerType2') == 'season':
                        info['art_type'] = ['seasonposter']
                    # process seasonbanners
                    elif image.findtext('BannerType') == 'season' and image.findtext('BannerType2') == 'seasonwide':
                        info['art_type'] = ['seasonbanner']
                    else:
                        info['art_type'] = ['']
                    # convert image size ...x... in Bannertype2
                    if image.findtext('BannerType2'):
                        try:
                            x,y = image.findtext('BannerType2').split('x')
                            info['width'] = int(x)
                            info['height'] = int(y)
                        except:
                            info['type2'] = image.findtext('BannerType2')

                    # check if fanart has text
                    info['series_name'] = image.findtext('SeriesName') == 'true'

                    # find image ratings
                    if int(image.findtext('RatingCount')) >= 1:
                        info['rating'] = float( "%.1f" % float( image.findtext('Rating')) ) #output string with one decimal
                        info['votes'] = image.findtext('RatingCount')
                    else:
                        info['rating'] = 'n/a'
                        info['votes'] = 'n/a'

                    # find season info
                    if image.findtext('Season'):
                        info['season'] = image.findtext('Season')
                    else:
                        info['season'] = 'n/a'

                    # Create Gui string to display
                    info['generalinfo'] = '%s: %s  |  ' %( __localize__(32141), get_language(info['language']).capitalize())
                    if info['season'] != 'n/a':
                        info['generalinfo'] += '%s: %s  |  ' %( __localize__(32144), info['season'] )
                    if 'height' in info:
                        info['generalinfo'] += '%s: %sx%s  |  ' %( __localize__(32145), info['height'], info['width'] )
                    info['generalinfo'] += '%s: %s  |  %s: %s  |  ' %( __localize__(32142), info['rating'], __localize__(32143), info['votes'] )

                if info:
                    image_list.append(info)
        except:
            raise NoFanartError(media_id)
        if image_list == []:
            raise NoFanartError(media_id)
        else:
            # Sort the list before return. Last sort method is primary
            image_list = sorted(image_list, key=itemgetter('rating'), reverse=True)
            image_list = sorted(image_list, key=itemgetter('season'))
            image_list = sorted(image_list, key=itemgetter('language'))
            return image_list
