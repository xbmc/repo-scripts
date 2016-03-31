# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import urllib
import xbmc
import xbmcvfs
import os
import Utils
import addon
import PIL.Image
import PIL.ImageFilter
import threading

THUMBS_CACHE_PATH = xbmc.translatePath("special://profile/Thumbnails/Video")
IMAGE_PATH = os.path.join(addon.DATA_PATH, "images")


def filter_image(input_img, radius=25):
    if not input_img:
        return "", ""
    if not xbmcvfs.exists(IMAGE_PATH):
        xbmcvfs.mkdir(IMAGE_PATH)
    input_img = xbmc.translatePath(urllib.unquote(input_img.encode("utf-8"))).replace("image://", "")
    input_img.rstrip("/")
    cachedthumb = xbmc.getCacheThumbName(input_img)
    filename = "%s-radius_%i.png" % (cachedthumb, radius)
    targetfile = os.path.join(IMAGE_PATH, filename)
    xbmc_vid_cache_file = os.path.join("special://profile/Thumbnails/Video", cachedthumb[0], cachedthumb)
    xbmc_cache_file = os.path.join("special://profile/Thumbnails", cachedthumb[0], cachedthumb[:-4] + ".jpg")
    if not xbmcvfs.exists(targetfile):
        img = None
        for i in xrange(1, 4):
            try:
                if xbmcvfs.exists(xbmc_cache_file):
                    Utils.log("image already in xbmc cache: " + xbmc_cache_file)
                    img = PIL.Image.open(xbmc.translatePath(xbmc_cache_file))
                    break
                elif xbmcvfs.exists(xbmc_vid_cache_file):
                    Utils.log("image already in xbmc video cache: " + xbmc_vid_cache_file)
                    img = PIL.Image.open(xbmc.translatePath(xbmc_vid_cache_file))
                    break
                else:
                    xbmcvfs.copy(unicode(input_img, 'utf-8', errors='ignore'), targetfile)
                    img = PIL.Image.open(targetfile)
                    break
            except:
                Utils.log("Could not get image for %s (try %i)" % (input_img, i))
                xbmc.sleep(500)
        if not img:
            return "", ""
        try:
            img.thumbnail((200, 200), PIL.Image.ANTIALIAS)
            img = img.convert('RGB')
            imgfilter = MyGaussianBlur(radius=radius)
            img = img.filter(imgfilter)
            img.save(targetfile)
        except:
            Utils.log("PIL problem probably....")
            return "", ""
    else:
        Utils.log("blurred img already created: " + targetfile)
        img = PIL.Image.open(targetfile)
    imagecolor = get_colors(img)
    return targetfile, imagecolor


def get_cached_thumb(filename):
    if filename.startswith("stack://"):
        filename = filename[8:].split(" , ")[0]
    if filename.endswith("folder.jpg"):
        cachedthumb = xbmc.getCacheThumbName(filename)
        thumbpath = os.path.join(THUMBS_CACHE_PATH, cachedthumb[0], cachedthumb).replace("/Video", "")
    else:
        cachedthumb = xbmc.getCacheThumbName(filename)
        if ".jpg" in filename:
            cachedthumb = cachedthumb.replace("tbn", "jpg")
        elif ".png" in filename:
            cachedthumb = cachedthumb.replace("tbn", "png")
        thumbpath = os.path.join(THUMBS_CACHE_PATH, cachedthumb[0], cachedthumb).replace("/Video", "")
    return thumbpath


def get_colors(img):
    width, height = img.size
    try:
        pixels = img.load()
    except:
        return "FFF0F0F0"
    data = []
    for x in xrange(width/2):
        data += [pixels[x*2, y*2] for y in xrange(height/2)]
    r = 0
    g = 0
    b = 0
    counter = 0
    for x in data:
        brightness = x[0] + x[1] + x[2]
        if 150 < brightness < 720:
            r += x[0]
            g += x[1]
            b += x[2]
            counter += 1
    if counter == 0:
        return "FFF0F0F0"
    r_avg = int(r/counter)
    g_avg = int(g/counter)
    b_avg = int(b/counter)
    avg = (r_avg + g_avg + b_avg) / 3
    min_brightness = 130
    if avg < min_brightness:
        diff = min_brightness - avg
        for color in [r_avg, g_avg, b_avg]:
            color = color + diff if color <= (255 - diff) else 255
    imagecolor = "FF%s%s%s" % (format(r_avg, '02x'), format(g_avg, '02x'), format(b_avg, '02x'))
    Utils.log("Average Color: " + imagecolor)
    return imagecolor


class FilterImageThread(threading.Thread):

    def __init__(self, image="", radius=25):
        threading.Thread.__init__(self)
        self.image = image
        self.radius = radius

    def run(self):
        try:
            self.image, self.imagecolor = filter_image(self.image, self.radius)
        except:
            self.image = ""
            self.imagecolor = ""


class MyGaussianBlur(PIL.ImageFilter.Filter):
    name = "GaussianBlur"

    def __init__(self, radius=2):
        self.radius = radius

    def filter(self, image):
        return image.gaussian_blur(self.radius)
