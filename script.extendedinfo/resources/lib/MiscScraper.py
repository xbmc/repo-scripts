# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import re
import random
import urllib
import xbmc
from Utils import *
import datetime

# TVRAGE_KEY = 'VBp9BuIr5iOiBeWCFRMG'
BANDSINTOWN_KEY = 'xbmc_open_source_media_center'


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
            item = {'Image': results["img"],
                    'thumb': results["img"],
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
            newitem = {'Image': keyword,
                       'thumb': keyword,
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
    if single is True:
        filename = "babe%ix%ix%i" % (now.month, now.day, now.year)
    else:
        filename = "babes%ix%ix%i" % (now.month, now.day, now.year)
    path = xbmc.translatePath(os.path.join(ADDON_DATA_PATH, "Babes", filename + ".txt"))
    if xbmcvfs.exists(path):
        return read_from_file(path)
    items = []
    for i in range(1, 10):
        if single is True:
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


def handle_bandsintown_events(results):
    events = []
    for event in results:
        try:
            venue = event['venue']
            artists = ''
            for art in event["artists"]:
                artists = artists + ' / ' + art['name']
                artists = artists.replace(" / ", "", 1)
            event = {'date': event['datetime'].replace("T", " - ").replace(":00", "", 1),
                     'city': venue['city'],
                     'lat': venue['latitude'],
                     'lon': venue['longitude'],
                     'id': venue['id'],
                     'url': venue['url'],
                     'name': venue['name'],
                     'region': venue['region'],
                     'country': venue['country'],
                     'artists': artists}
            events.append(event)
        except Exception as e:
            log("Exception in handle_bandsintown_events")
            log(e)
            prettyprint(event)
    return events


def get_artist_near_events(artists):  # not possible with api 2.0
    artist_str = ''
    count = 0
    for art in artists:
        artist = art['artist']
        try:
            artist = urllib.quote(artist)
        except:
            artist = urllib.quote(artist.encode("utf-8"))
        if count < 49:
            if len(artist_str) > 0:
                artist_str = artist_str + '&'
            artist_str = artist_str + 'artists[]=' + artist
            count += 1
    base_url = 'http://api.bandsintown.com/events/search?format=json&location=use_geoip&radius=50&per_page=100&api_version=2.0'
    url = '&%sapp_id=%s' % (artist_str, BANDSINTOWN_KEY)
    results = get_JSON_response(base_url + url, folder="BandsInTown")
    if results:
        return handle_bandsintown_events(results)
    log("get_artist_near_events: Could not get data from " + url)
    log(results)
    return []
