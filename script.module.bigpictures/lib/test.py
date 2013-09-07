#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2013 Tristan Fischer (sphere@dersphere.de)
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

from thebigpictures import get_scrapers


def test():
    for scraper in get_scrapers():
        try:
            albums = scraper.get_albums()
        except Exception, e:
            print '=' * 80
            print 'get_albums Exception: %s' % e
            print '=' * 80
            continue
        for album in albums:
            try:
                scraper.get_photos(album.get('album_url'))
            except Exception, e:
                print '=' * 80
                print 'get_photos Exception: %s' % e
                print '=' * 80
                continue


if __name__ == '__main__':
    test()
