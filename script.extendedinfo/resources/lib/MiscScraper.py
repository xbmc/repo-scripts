# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import re
import random
import xbmc
from Utils import *
import datetime

# TVRAGE_KEY = 'VBp9BuIr5iOiBeWCFRMG'


def get_xkcd_images():
    now = datetime.datetime.now()
    filename = "xkcd%ix%ix%i" % (now.month, now.day, now.year)
    path = xbmc.translatePath(ADDON_DATA_PATH + "/" + filename + ".txt")
    if xbmcvfs.exists(path):
        return read_from_file(path)
    items = []
    for i in range(0, 10):
        try:
            base_url = 'http://xkcd.com/'
            url = '%i/info.0.json' % random.randrange(1, 1190)
            results = get_JSON_response(base_url + url, 9999, folder="XKCD")
            item = {'thumb': results["img"],
                    'path': "plugin://script.extendedinfo?info=setfocus",
                    'poster': results["img"],
                    'title': results["title"],
                    'Description': results["alt"]}
            items.append(item)
        except:
            log("Error when setting XKCD info")
    save_to_file(content=items,
                 filename=filename,
                 path=ADDON_DATA_PATH)
    return items


def get_cyanide_images():
    now = datetime.datetime.now()
    filename = "cyanide%ix%ix%i" % (now.month, now.day, now.year)
    path = xbmc.translatePath(ADDON_DATA_PATH + "/" + filename + ".txt")
    if xbmcvfs.exists(path):
        return read_from_file(path)
    items = []
    for i in range(1, 10):
        url = r'http://www.explosm.net/comics/%i/' % random.randrange(1, 3868)
        response = get_http(url)
        if response:
            keyword = re.search("<meta property=\"og:image\".*?content=\"([^\"]*)\"", response).group(1)
            url = re.search("<meta property=\"og:url\".*?content=\"([^\"]*)\"", response).group(1)
            newitem = {'thumb': keyword,
                       'path': "plugin://script.extendedinfo?info=setfocus",
                       'poster': keyword,
                       'title': url}
            items.append(newitem)
    save_to_file(content=items,
                 filename=filename,
                 path=ADDON_DATA_PATH)
    return items


def get_babe_images(single=False):
    now = datetime.datetime.now()
    filename = "babe%ix%ix%i" % (now.month, now.day, now.year)
    if single:
        filename= "single" + filename
    path = xbmc.translatePath(os.path.join(ADDON_DATA_PATH, "Babes", filename + ".txt"))
    if xbmcvfs.exists(path):
        return read_from_file(path)
    items = []
    for i in range(1, 10):
        if single:
            month = now.month
            day = now.day
            image = i
        else:
            month = random.randrange(1, 9)
            day = random.randrange(1, 28)
            image = random.randrange(1, 8)
        url = 'http://img1.demo.jsxbabeotd.dellsports.com/static/models/2014/%s/%s/%i.jpg' % (str(month).zfill(2), str(day).zfill(2), image)
        newitem = {'thumb': url,
                   'path': "plugin://script.extendedinfo?info=setfocus",
                   'title': "2014/%i/%i (Nr. %i)" % (month, day, image)
                   }
        items.append(newitem)
    save_to_file(content=items,
                 filename=filename,
                 path=os.path.join(ADDON_DATA_PATH, "Babes"))
    return items
