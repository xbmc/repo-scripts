# -*- coding: utf-8 -*-
"""
    screensaver.kaster
    Copyright (C) 2017 enen92

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import kodiutils
import xbmcvfs
import xbmc
import os
import json

def remove_unknown_author(author):
    if "unknown" in author.lower():
        return kodiutils.get_string(32007)
    else:
        return author

def get_own_pictures(path):
    _, files = xbmcvfs.listdir(xbmc.translatePath(path))
    images_dict = {}
    image_file = os.path.join(xbmc.translatePath(path), "images.json")
    if xbmcvfs.exists(image_file):
        with open(image_file, "r") as f:
            try:
                images_dict = json.loads(f.read())
            except ValueError:
                kodiutils.log(kodiutils.get_string(32010), xbmc.LOGERROR)
    for _file in files:
        if _file.endswith(('.png', '.jpg', '.jpeg')):
            returned_dict = {
                "url": os.path.join(xbmc.translatePath(path), _file),
                "private": True
            }
            if images_dict:
                for image in images_dict:
                    if "image" in image.keys() and image["image"] == _file:
                        if "line1" in image.keys():
                            returned_dict["line1"] = image["line1"]
                        if "line2" in image.keys():
                            returned_dict["line2"] = image["line2"]
            yield returned_dict


