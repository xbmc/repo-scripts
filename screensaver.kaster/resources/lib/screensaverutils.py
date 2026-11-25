# -*- coding: utf-8 -*-
"""
  Copyright (C) 2017-2020 enen92
  Copyright (C) 2026-2026 guss77
  This file is part of kaster

  SPDX-License-Identifier: GPL-2.0-or-later
  See LICENSE for more information.
"""
from . import kodiutils
from . import exifutils
import xbmcvfs
import xbmc
import os
import json

# Embedded photographer credits live at the beginning of a file. Reading a
# small header is enough and keeps network shares responsive.
METADATA_READ_SIZE = 131072

IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg')


class ScreenSaverUtils:

    def __init__(self):
        self.photographer_cache = {}
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
        folders, files = xbmcvfs.listdir(kodiutils.translate_path(path))
        for _file in files:
            self.__append_image(os.path.join(kodiutils.translate_path(path), _file))
        if folders:
            for folder in folders:
                path = os.path.join(path,folder)
                self.__get_images_recursively(path)

    def __get_photographer(self, path):
        """Return the photographer credit embedded in an image, if any."""
        if path in self.photographer_cache:
            return self.photographer_cache[path]
        name = None
        try:
            f = xbmcvfs.File(path)
            try:
                try:
                    data = f.readBytes(METADATA_READ_SIZE)
                except AttributeError:
                    data = f.read(METADATA_READ_SIZE)
            finally:
                f.close()
            if isinstance(data, bytearray):
                data = data.decode('latin-1').encode('latin-1')
            elif not isinstance(data, bytes):
                # Older Kodi builds hand back text from File.read()
                try:
                    data = data.encode('latin-1')
                except UnicodeEncodeError:
                    data = data.encode('utf-8', 'ignore')
            name = exifutils.get_photographer(data)
        except Exception:
            # Metadata is optional - never let a broken file stop the slideshow.
            name = None
        self.photographer_cache[path] = name
        return name

    def get_all_images(self):
        return self.images

    def get_own_pictures(self, path):
        self.__reset_images()
        images_dict = {}

        image_file = os.path.join(kodiutils.translate_path(path), "images.json")
        if xbmcvfs.exists(image_file):
            f = xbmcvfs.File(image_file)
            try:
               images_dict = json.loads(f.read())
            except ValueError:
               kodiutils.log(kodiutils.get_string(32010), xbmc.LOGERROR)
            f.close()

        self.__get_images_recursively(kodiutils.translate_path(path))

        for _file in self.get_all_images():
            if _file.lower().endswith(IMAGE_EXTENSIONS):
                returned_dict = {
                    "url": _file,
                    "private": True
                }
                if images_dict:
                    for image in images_dict:
                        if "image" in list(image.keys()) and os.path.join(kodiutils.translate_path(path),image["image"]) == _file:
                            if "line1" in list(image.keys()):
                                returned_dict["line1"] = image["line1"]
                            if "line2" in list(image.keys()):
                                returned_dict["line2"] = image["line2"]
                photographer = self.__get_photographer(_file)
                if photographer:
                    returned_dict["photographer"] = self.remove_unknown_author(photographer)
                yield returned_dict


