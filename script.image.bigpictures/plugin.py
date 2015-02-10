#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2012 Tristan Fischer (sphere@dersphere.de)
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

import sys
import urlparse

import xbmc
import xbmcgui
import xbmcplugin

from thebigpictures import ScraperManager


def show_photos(scraper_id, album_url):
    scraper_manager = ScraperManager()
    scraper_manager.switch(scraper_id)
    for photo in scraper_manager.get_photos(album_url):
        li = xbmcgui.ListItem(
            label=photo['title'],
            thumbnailImage=photo['pic']
        )
        li.setInfo(type='image', infoLabels={'Title': photo['title']})
        xbmcplugin.addDirectoryItem(
            handle=int(sys.argv[1]),
            url=photo['pic'],
            listitem=li,
            isFolder=False
        )
    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def decode_params():
    params = {}
    p = urlparse.parse_qs(sys.argv[2][1:])
    for key, value in p.iteritems():
        params[key] = value[0]
    log('params=%s' % params)
    return params


def log(msg):
    xbmc.log('TheBigPictures Plugin: %s' % msg)


if __name__ == '__main__':
    log('run started in photos-mode')
    params = decode_params()
    scraper_id = int(params['scraper_id'])
    album_url = params['album_url']
    show_photos(scraper_id, album_url)
