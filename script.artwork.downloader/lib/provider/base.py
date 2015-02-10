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

###required info labels in the imagelist: id, type, type2, url, preview, height, width, season, language, rating,series_name

class BaseProvider:

    """
    Creates general structure for all fanart providers.  This will allow us to
    very easily add multiple providers for the same media type.
    """
    name = ''
    api_key = ''
    api_limits = False
    url = ''
    data = {}
    fanart_element = ''
    fanart_root = ''
    url_prefix = ''

    def get_image_list(self, media_id):
        pass