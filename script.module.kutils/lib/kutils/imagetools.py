# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import os
import threading
import urllib.parse

import PIL.Image
import PIL.ImageFilter

import xbmc
import xbmcvfs

from kutils import addon
from kutils import utils

THUMBS_CACHE_PATH = utils.translate_path("special://profile/Thumbnails/Video")
IMAGE_PATH = os.path.join(addon.DATA_PATH, "images")


def blur(input_img, radius=25):
    if not input_img:
        return {}
    if not xbmcvfs.exists(IMAGE_PATH):
        xbmcvfs.mkdir(IMAGE_PATH)
    input_img = utils.translate_path(urllib.parse.unquote(input_img))
    input_img = input_img.replace("image://", "").rstrip("/")
    cachedthumb = xbmc.getCacheThumbName(input_img)
    filename = "%s-radius_%i.png" % (cachedthumb, radius)
    targetfile = os.path.join(IMAGE_PATH, filename)
    vid_cache_file = os.path.join("special://profile/Thumbnails/Video", cachedthumb[0], cachedthumb)
    cache_file = os.path.join("special://profile/Thumbnails", cachedthumb[0], cachedthumb[:-4] + ".jpg")
    if xbmcvfs.exists(targetfile):
        img = PIL.Image.open(targetfile)
        return {"ImageFilter": targetfile,
                "ImageColor": get_colors(img)}
    try:
        if xbmcvfs.exists(cache_file):
            utils.log("image already in xbmc cache: " + cache_file)
            img = PIL.Image.open(utils.translate_path(cache_file))
        elif xbmcvfs.exists(vid_cache_file):
            utils.log("image already in xbmc video cache: " + vid_cache_file)
            img = PIL.Image.open(utils.translate_path(vid_cache_file))
        else:
            xbmcvfs.copy(input_img, targetfile)
            img = PIL.Image.open(targetfile)
        img.thumbnail((200, 200), PIL.Image.ANTIALIAS)
        imgfilter = MyGaussianBlur(radius=radius)
        img = img.convert('RGB').filter(imgfilter)
        img.save(targetfile)
    except Exception:
        utils.log("Could not get image for %s" % input_img)
        return {}
    return {"ImageFilter": targetfile,
            "ImageColor": get_colors(img)}


def get_cached_thumb(filename):
    if filename.startswith("stack://"):
        filename = filename[8:].split(" , ")[0]
    cachedthumb = xbmc.getCacheThumbName(filename)
    if not filename.endswith("folder.jpg"):
        if ".jpg" in filename:
            cachedthumb = cachedthumb.replace("tbn", "jpg")
        elif ".png" in filename:
            cachedthumb = cachedthumb.replace("tbn", "png")
    return os.path.join(THUMBS_CACHE_PATH, cachedthumb[0], cachedthumb).replace("/Video", "")


def get_colors(img):
    width, height = img.size
    try:
        pixels = img.load()
    except Exception:
        return "FFF0F0F0"
    data = []
    for x in range(width // 2):
        data += [pixels[x * 2, y * 2] for y in range(height // 2)]
    pix_values = [(x[0], x[1], x[2]) for x in data if 150 < (x[0] + x[1] + x[2]) < 720]
    if len(pix_values) == 0:
        return "FFF0F0F0"
    r_avg = int(sum([i[0] for i in pix_values]) / len(pix_values))
    g_avg = int(sum([i[1] for i in pix_values]) / len(pix_values))
    b_avg = int(sum([i[2] for i in pix_values]) / len(pix_values))
    avg = (r_avg + g_avg + b_avg) / 3
    min_brightness = 170
    if avg < min_brightness:
        diff = min_brightness - avg
        r_avg = int(min(r_avg + diff, 255))
        g_avg = int(min(g_avg + diff, 255))
        b_avg = int(min(b_avg + diff, 255))
    return f"FF{r_avg:02X}{g_avg:02X}{b_avg:02X}"


class FilterImageThread(threading.Thread):

    def __init__(self, image="", radius=25):
        super().__init__()
        self.image = image
        self.radius = radius
        self.info = {}

    def run(self):
        try:
            self.info = blur(self.image, self.radius)
        except Exception:
            pass


class MyGaussianBlur(PIL.ImageFilter.Filter):
    name = "GaussianBlur"

    def __init__(self, radius=2):
        self.radius = radius

    def filter(self, image):
        return image.gaussian_blur(self.radius)
