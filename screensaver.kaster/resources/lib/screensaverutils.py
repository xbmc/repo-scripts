# -*- coding: utf-8 -*-
"""
  Copyright (C) 2017-2020 enen92
  This file is part of kaster

  SPDX-License-Identifier: GPL-2.0-or-later
  See LICENSE for more information.
"""
from . import kodiutils
import xbmcvfs
import xbmc
import os
import json

class ScreenSaverUtils:

    def __init__(self):
        self.images = []

    @staticmethod
    def remove_unknown_author(author):
        if "unknown" in author.lower():
            return kodiutils.get_string(32007)
        else:
            return author

    def __reset_images(self):
        self.images = []

    def __append_image(self, image):
        self.images.append(image)

    def __get_images_recursively(self, path):
        folders, files = xbmcvfs.listdir(xbmc.translatePath(path))
        for _file in files:
            self.__append_image(os.path.join(xbmc.translatePath(path), _file))
        if folders:
            for folder in folders:
                path = os.path.join(path,folder)
                self.__get_images_recursively(path)

    def get_all_images(self):
        return self.images

    def get_own_pictures(self, path):
        self.__reset_images()
        images_dict = {}

        image_file = os.path.join(xbmc.translatePath(path), "images.json")
        if xbmcvfs.exists(image_file):
            f = xbmcvfs.File(image_file)
            try:
               images_dict = json.loads(f.read())
            except ValueError:
               kodiutils.log(kodiutils.get_string(32010), xbmc.LOGERROR)
            f.close()

        self.__get_images_recursively(xbmc.translatePath(path))

        for _file in self.get_all_images():
            if _file.lower().endswith(('.png', '.jpg', '.jpeg')):
                returned_dict = {
                    "url": _file,
                    "private": True
                }
                if images_dict:
                    for image in images_dict:
                        if "image" in list(image.keys()) and os.path.join(xbmc.translatePath(path),image["image"]) == _file:
                            if "line1" in list(image.keys()):
                                returned_dict["line1"] = image["line1"]
                            if "line2" in list(image.keys()):
                                returned_dict["line2"] = image["line2"]
                yield returned_dict


