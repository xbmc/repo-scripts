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

### import libraries
from lib.settings import get_limit
limit = get_limit()

def filter(art_type, mediatype, artwork, downloaded_artwork, language, disctype = ''):

    data = {'art_type': art_type,
            'mediatype': mediatype,
            'artwork': artwork,
            'downloaded_artwork': downloaded_artwork,
            'language': language,
            'disctype': disctype}

    if data.get('art_type') == 'fanart':
        return fanart(data)

    elif data.get('art_type') == 'extrafanart':
        return extrafanart(data)

    elif data.get('art_type') == 'extrathumbs':
        return extrathumbs(data)

    elif data.get('art_type') == 'poster':
        return poster(data)

    elif data.get('art_type') == 'seasonposter':
        return seasonposter(data)

    elif data.get('art_type') == 'banner':
        return banner(data)

    elif data.get('art_type') == 'seasonbanner':
        return seasonbanner(data)

    elif data.get('art_type') == 'clearlogo':
        return clearlogo(data)

    elif data.get('art_type') == 'clearart':
        return clearart(data)

    elif data.get('art_type') == 'characterart':
        return characterart(data)

    elif data.get('art_type') == 'landscape':
        return landscape(data)

    elif data.get('art_type') == 'seasonlandscape':
        return seasonlandscape(data)

    elif data.get('art_type') == 'defaultthumb':
        return defaultthumb(data)

    elif data.get('art_type') == 'discart':
        return discart(data)

    else:
        return [False, 'Unrecognised art_type']

def fanart(data):
    limited = False
    reason = ''
    # Maximum number
    if data.get('downloaded_artwork') >= limit.get('limit_artwork_max'):
        reason = 'Max number fanart reached: %s' % limit.get('limit_artwork_max')
        limited = True
    # Minimal size
    elif limit.get('limit_artwork') and 'height' in data.get('artwork') and (data.get('mediatype') == 'movie' and data.get('artwork')['height'] < limit.get('limit_size_moviefanart')) or (data.get('mediatype') == 'tvshow' and data.get('artwork')['height'] < limit.get('limit_size_tvshowfanart')):
        reason = 'Size was to small: %s' % data.get('artwork')['height'] 
        limited = True
    # Minimal rating
    elif limit.get('limit_artwork') and data.get('artwork')['rating'] < limit.get('limit_extrafanart_rating'):
        reason = 'Rating too low: %s' % data.get('artwork')['rating']
        limited = True
    # Has text       
    elif limit.get('limit_artwork') and 'series_name' in data.get('artwork') and limit.get('limit_notext') and data.get('artwork')['series_name']:
        reason = 'Has text'
        limited = True
    # Correct language
    #elif not data.get('artwork')['language'] in [data.get('language'), 'n/a']:
    #    reason = "Doesn't match preferred language: %s" % limit.get('limit_preferred_language')
    #    limited = True
    return [limited, reason]
    
def extrafanart(data):
    limited = False
    reason = ''
    # Maximum number
    if limit.get('limit_artwork') and data.get('downloaded_artwork') >= limit.get('limit_extrafanart_max'):
        reason = 'Max number extrafanart reached: %s' % limit.get('limit_extrafanart_max')
        limited = True
    # Minimal size
    elif limit.get('limit_artwork') and 'height' in data.get('artwork') and (data.get('mediatype') == 'movie' and data.get('artwork')['height'] < limit.get('limit_size_moviefanart')) or (data.get('mediatype') == 'tvshow' and data.get('artwork')['height'] < limit.get('limit_size_tvshowfanart')):
        reason = 'Size was to small: %s' % data.get('artwork')['height'] 
        limited = True
    # Minimal rating
    elif limit.get('limit_artwork') and data.get('artwork')['rating'] < limit.get('limit_extrafanart_rating'):
        reason = 'Rating too low: %s' % data.get('artwork')['rating']
        limited = True
    # Has text
    elif limit.get('limit_artwork') and 'series_name' in data.get('artwork') and limit.get('limit_notext') and data.get('artwork')['series_name']:
        reason = 'Has text'
        limited = True
    return [limited, reason]

def extrathumbs(data):
    limited = False
    reason = ''
    # Maximum number
    if data.get('downloaded_artwork') >= limit.get('limit_extrathumbs_max'):
        reason = 'Max number extrathumbs reached: %s' % limit.get('limit_extrathumbs_max')
        limited = True
    # Minimal size
    elif limit.get('limit_extrathumbs') and 'height' in data.get('artwork') and data.get('artwork')['height'] < int('169'):
        reason = 'Size was to small: %s' % data.get('artwork')['height']
        limited = True
    return [limited, reason]
    
def poster(data):
    limited = False
    reason = ''
    # Maximum number
    if data.get('downloaded_artwork') >= limit.get('limit_artwork_max'):
        reason = 'Max number poster reached: %s' % limit.get('limit_artwork_max')
        limited = True
    # Minimal size
    elif limit.get('limit_extrathumbs') and 'height' in data.get('artwork') and data.get('artwork')['height'] < int('169'):
        reason = 'Size was to small: %s' % data.get('artwork')['height']
        limited = True
    # Correct language
    elif not data.get('artwork')['language'] in [data.get('language')]:
        reason = "Doesn't match preferred language: %s" % limit.get('limit_preferred_language')
        limited = True
    return [limited, reason]

def seasonposter(data):
    limited = False
    reason = ''
    # Maximum number
    if data.get('downloaded_artwork') >= limit.get('limit_artwork_max'):
        reason = 'Max number seasonposter reached: %s' % limit.get('limit_artwork_max')
        limited = True
    # Minimal size
    elif limit.get('limit_extrathumbs') and 'height' in data.get('artwork') and data.get('artwork')['height'] < int('169'):
        reason = 'Size was to small: %s' % data.get('artwork')['height']
        limited = True
    # Correct language
    elif not data.get('artwork')['language'] in [data.get('language')]:
        reason = "Doesn't match preferred language: %s" % limit.get('limit_preferred_language')
        limited = True
    return [limited, reason]

def banner(data):
    limited = False
    reason = ''
    # Maximum number
    if data.get('downloaded_artwork') >= limit.get('limit_artwork_max'):
        reason = 'Max number banner reached: %s' % limit.get('limit_artwork_max')
        limited = True
    # Correct language
    elif not data.get('artwork')['language'] in [data.get('language')]:
        reason = "Doesn't match preferred language: %s" % limit.get('limit_preferred_language')
        limited = True
    return [limited, reason]
    
def seasonbanner(data):
    limited = False
    reason = ''
    # Maximum number
    if data.get('downloaded_artwork') >= limit.get('limit_artwork_max'):
        reason = 'Max number seasonbanner reached: %s' % limit.get('limit_artwork_max')
        limited = True
    # Has season
    if not 'season' in data.get('artwork'):
        reason = 'No season'
        limited = True
    # Correct language
    elif not data.get('artwork')['language'] in [data.get('language')]:
        reason = "Doesn't match preferred language: %s" % limit.get('limit_preferred_language')
        limited = True
    return [limited, reason]
    
def clearlogo(data):
    limited = False
    reason = ''
    # Maximum number
    if data.get('downloaded_artwork') >= limit.get('limit_artwork_max'):
        reason = 'Max number logos reached: %s' % limit.get('limit_artwork_max')
        limited = True
    # Correct language
    elif not data.get('artwork')['language'] in [data.get('language'), 'n/a']:
        reason = "Doesn't match preferred language: %s" % limit.get('limit_preferred_language')
        limited = True
    return [limited, reason]
    
def clearart(data):
    limited = False
    reason = ''
    # Maximum number
    if data.get('downloaded_artwork') >= limit.get('limit_artwork_max'):
        reason = 'Max number clearart reached: %s' % limit.get('limit_artwork_max')
        limited = True
    # Correct language
    elif not data.get('artwork')['language'] in [data.get('language'), 'n/a']:
        reason = "Doesn't match preferred language: %s" % limit.get('limit_preferred_language')
        limited = True
    return [limited, reason]

def characterart(data):
    limited = False
    reason = ''
    # Maximum number
    if data.get('downloaded_artwork') >= limit.get('limit_artwork_max'):
        reason = 'Max number characterart reached: %s' % limit.get('limit_artwork_max')
        limited = True
    # Correct language
    elif not data.get('artwork')['language'] in [data.get('language'), 'n/a']:
        reason = "Doesn't match preferred language: %s" % limit.get('limit_preferred_language')
        limited = True
    return [limited, reason]
    
def landscape(data):
    limited = False
    reason = ''
    # Maximum number
    if data.get('downloaded_artwork') >= limit.get('limit_artwork_max'):
        reason = 'Max number landscape reached: %s' % limit.get('limit_artwork_max')
        limited = True
    # Correct language
    elif not data.get('artwork')['language'] in [data.get('language'), 'n/a']:
        reason = "Doesn't match preferred language: %s" % limit.get('limit_preferred_language')
        limited = True
    return [limited, reason]
    
def seasonlandscape(data):
    limited = False
    reason = ''
    # Maximum number
    if data.get('downloaded_artwork') >= limit.get('limit_artwork_max'):
        reason = 'Max number seasonthumb reached: %s' % limit.get('limit_artwork_max')
        limited = True
    # Correct language
    elif not data.get('artwork')['language'] in [data.get('language'), 'n/a']:
        reason = "Doesn't match preferred language: %s" % limit.get('limit_preferred_language')
        limited = True
    return [limited, reason]

def defaultthumb(data):
    limited = False
    reason = ''
    # Maximum number
    if data.get('downloaded_artwork') >= limit.get('limit_artwork_max'):
        reason = 'Max number defaultthumb reached: %s' % limit.get('limit_artwork_max')
        limited = True
    # Correct language
    elif not data.get('artwork')['language'] in [data.get('language'), 'n/a']:
        reason = "Doesn't match preferred language: %s" % limit.get('limit_preferred_language')
        limited = True
    return [limited, reason]        

def discart(data):
    limited = False
    reason = ''
    # Maximum number
    if data.get('downloaded_artwork') >= limit.get('limit_artwork_max'):
        reason = 'Max number discart reached: %s' % limit.get('limit_artwork_max')
        limited = True
    # Correct discnumber
    elif not data.get('artwork')['discnumber'] == '1':
        reason = "Doesn't match preferred discnumber: 1"
        limited = True
    # Correct discnumber
    elif not data.get('artwork')['disctype'] == data.get('disctype'):
        reason = "Doesn't match preferred disctype: %s" % data.get('disctype')
        limited = True
    # Correct language
    elif not data.get('artwork')['language'] in [data.get('language'), 'n/a']:
        reason = "Doesn't match preferred language: %s" % limit.get('limit_preferred_language')
        limited = True
    return [limited, reason]