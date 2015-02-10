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

#import lib
from lib.settings import get

### Create list for Artwork types to download
def arttype_list():
    setting = get()
    available_arttypes = [{'media_type': 'movie',
                           'bulk_enabled': setting.get('movie_poster'),
                           'solo_enabled': 'true',
                           'gui_string': 32128,
                           'art_type': 'poster',
                           'filename': 'poster.jpg'},

                          {'media_type': 'movie',
                           'bulk_enabled': setting.get('movie_fanart'),
                           'solo_enabled': 'true',
                           'gui_string': 32121,
                           'art_type': 'fanart',
                           'filename': 'fanart.jpg'},

                          {'media_type': 'movie',
                           'bulk_enabled': setting.get('movie_extrafanart'),
                           'solo_enabled': 'false',
                           'gui_string': 32122,
                           'art_type': 'extrafanart',
                           'filename': ''},

                          {'media_type': 'movie',
                           'bulk_enabled': setting.get('movie_extrathumbs'),
                           'solo_enabled': 'false',
                           'gui_string': 32131,
                           'art_type': 'extrathumbs',
                           'filename': 'thumb%s.jpg'},

                          {'media_type': 'movie',
                           'bulk_enabled': setting.get('movie_logo'),
                           'solo_enabled': 'true',
                           'gui_string': 32126,
                           'art_type': 'clearlogo',
                           'filename': 'logo.png'},

                          {'media_type': 'movie',
                           'bulk_enabled': setting.get('movie_clearart'),
                           'solo_enabled': 'true',
                           'gui_string': 32125,
                           'art_type': 'clearart',
                           'filename': 'clearart.png'},

                          {'media_type': 'movie',
                           'bulk_enabled': setting.get('movie_discart'),
                           'solo_enabled': 'true',
                           'gui_string': 32132,
                           'art_type': 'discart',
                           'filename': 'disc.png'},

                          {'media_type': 'movie',
                           'bulk_enabled': setting.get('movie_landscape'),
                           'solo_enabled': 'true',
                           'gui_string': 32130,
                           'art_type': 'landscape',
                           'filename': 'landscape.jpg'},
                          
                          {'media_type': 'movie',
                           'bulk_enabled': setting.get('movie_banner'),
                           'solo_enabled': 'true',
                           'gui_string': 32123,
                           'art_type': 'banner',
                           'filename': 'banner.jpg'},

                          # append tv show list
                          {'media_type': 'tvshow',
                           'bulk_enabled': setting.get('tvshow_poster'),
                           'solo_enabled': 'true',
                           'gui_string': 32128,
                           'art_type': 'poster',
                           'filename': 'poster.jpg'},

                          {'media_type': 'tvshow',
                           'bulk_enabled': setting.get('tvshow_seasonposter'),
                           'solo_enabled': 'true',
                           'gui_string': 32129,
                           'art_type': 'seasonposter',
                           'filename': 'season%02d-poster.jpg'},

                          {'media_type': 'tvshow',
                           'bulk_enabled': setting.get('tvshow_fanart'),
                           'solo_enabled': 'true',
                           'gui_string': 32121,
                           'art_type': 'fanart',
                           'filename': 'fanart.jpg'},

                          {'media_type': 'tvshow',
                           'bulk_enabled': setting.get('tvshow_extrafanart'),
                           'solo_enabled': 'false',
                           'gui_string': 32122,
                           'art_type': 'extrafanart',
                           'filename': ''},

                          {'media_type': 'tvshow',
                           'bulk_enabled': setting.get('tvshow_clearart'),
                           'solo_enabled': 'true',
                           'gui_string': 32125,
                           'art_type': 'clearart',
                           'filename': 'clearart.png'},

                          {'media_type': 'tvshow',
                           'bulk_enabled': setting.get('tvshow_logo'),
                           'solo_enabled': 'true',
                           'gui_string': 32126,
                           'art_type': 'clearlogo',
                           'filename': 'logo.png'},

                          {'media_type': 'tvshow',
                           'bulk_enabled': setting.get('tvshow_landscape'),
                           'solo_enabled': 'true',
                           'gui_string': 32130,
                           'art_type': 'landscape',
                           'filename': 'landscape.jpg'},

                          {'media_type': 'tvshow',
                           'bulk_enabled': setting.get('tvshow_seasonlandscape'),
                           'solo_enabled': 'true',
                           'gui_string': 32134,
                           'art_type': 'seasonlandscape',
                           'filename': 'season%02d-landscape.jpg'},

                          {'media_type': 'tvshow',
                           'bulk_enabled': setting.get('tvshow_showbanner'),
                           'solo_enabled': 'true',
                           'gui_string': 32123,
                           'art_type': 'banner',
                           'filename': 'banner.jpg'},

                          {'media_type': 'tvshow',
                           'bulk_enabled': setting.get('tvshow_seasonbanner'),
                           'solo_enabled': 'true',
                           'gui_string': 32124,
                           'art_type': 'seasonbanner',
                           'filename': 'season%02d-banner.jpg'},

                          {'media_type': 'tvshow',
                           'bulk_enabled': setting.get('tvshow_characterart'),
                           'solo_enabled': 'true',
                           'gui_string': 32127,
                           'art_type': 'characterart',
                           'filename': 'character.png'},

                          # Musicvideo
                          {'media_type': 'musicvideo',
                           'bulk_enabled': setting.get('musicvideo_poster'),
                           'solo_enabled': 'true',
                           'gui_string': 32128,
                           'art_type': 'poster',
                           'filename': 'poster.jpg'},

                          {'media_type': 'musicvideo',
                           'bulk_enabled': setting.get('musicvideo_fanart'),
                           'solo_enabled': 'true',
                           'gui_string': 32121,
                           'art_type': 'fanart',
                           'filename': 'fanart.jpg'},

                          {'media_type': 'musicvideo',
                           'bulk_enabled': setting.get('musicvideo_extrafanart'),
                           'solo_enabled': 'false',
                           'gui_string': 32122,
                           'art_type': 'extrafanart',
                           'filename': ''},

                          {'media_type': 'musicvideo',
                           'bulk_enabled': setting.get('musicvideo_extrathumbs'),
                           'solo_enabled': 'false',
                           'gui_string': 32131,
                           'art_type': 'extrathumbs',
                           'filename': 'thumb%s.jpg'},

                          {'media_type': 'musicvideo',
                           'bulk_enabled': setting.get('musicvideo_logo'),
                           'solo_enabled': 'true',
                           'gui_string': 32126,
                           'art_type': 'clearlogo',
                           'filename': 'logo.png'},

                          {'media_type': 'musicvideo',
                           'bulk_enabled': setting.get('musicvideo_clearart'),
                           'solo_enabled': 'true',
                           'gui_string': 32125,
                           'art_type': 'clearart',
                           'filename': 'clearart.png'},

                          {'media_type': 'musicvideo',
                           'bulk_enabled': setting.get('musicvideo_discart'),
                           'solo_enabled': 'true',
                           'gui_string': 32132,
                           'art_type': 'cdart',
                           'filename': 'disc.png'}]
    return available_arttypes
