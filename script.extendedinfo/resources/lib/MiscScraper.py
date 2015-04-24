import re
import random
import sys
import urllib
import xbmc
from Utils import *
import datetime
import simplejson

# TVRAGE_KEY = 'VBp9BuIr5iOiBeWCFRMG'
BANDSINTOWN_KEY = 'xbmc_open_source_media_center'


def GetXKCDInfo():
    now = datetime.datetime.now()
    filename = "xkcd" + str(now.month) + "x" + str(now.day) + "x" + str(now.year)
    path = xbmc.translatePath(ADDON_DATA_PATH + "/" + filename + ".txt")
    if xbmcvfs.exists(path):
        results = read_from_file(path)
        return results
    else:
        items = []
        for i in range(0, 10):
            try:
                base_url = 'http://xkcd.com/'
                url = '%i/info.0.json' % random.randrange(1, 1190)
                results = Get_JSON_response(base_url + url, 9999)
                item = {'Image': results["img"],
                        'Thumb': results["img"],
                        'Path': "plugin://script.extendedinfo?info=setfocus",
                        'Poster': results["img"],
                        'Title': results["title"],
                        'Description': results["alt"]}
                items.append(item)
            except:
                log("Error when setting XKCD info")
        save_to_file(items, filename, ADDON_DATA_PATH)
        return items


def GetCandHInfo():
    now = datetime.datetime.now()
    filename = "cyanide" + str(now.month) + "x" + str(now.day) + "x" + str(now.year)
    path = xbmc.translatePath(ADDON_DATA_PATH + "/" + filename + ".txt")
    if xbmcvfs.exists(path):
        results = read_from_file(path)
        return results
    else:
        items = []
        for i in range(1, 10):
            url = r'http://www.explosm.net/comics/%i/' % random.randrange(1, 3868)
            response = GetStringFromUrl(url)
            if response:
                keyword = re.search("<meta property=\"og:image\".*?content=\"([^\"]*)\"", response).group(1)
                url = re.search("<meta property=\"og:url\".*?content=\"([^\"]*)\"", response).group(1)
                newitem = {'Image': keyword,
                           'Thumb': keyword,
                           'Path': "plugin://script.extendedinfo?info=setfocus",
                           'Poster': keyword,
                           'Title': url}
                items.append(newitem)
        save_to_file(items, filename, ADDON_DATA_PATH)
        return items


def GetDailyBabes(single=False):
    now = datetime.datetime.now()
    if single is True:
        filename = "babe" + str(now.month) + "x" + str(now.day) + "x" + str(now.year)
    else:
        filename = "babes" + str(now.month) + "x" + str(now.day) + "x" + str(now.year)
    path = xbmc.translatePath(ADDON_DATA_PATH + "/" + filename + ".txt")
    if xbmcvfs.exists(path):
        results = read_from_file(path)
        return results
    else:
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
            newitem = {'Thumb': url,
                       'Path': "plugin://script.extendedinfo?info=setfocus",
                       'Title': "2014/" + str(month) + "/" + str(day) + " (Nr. " + str(image) + ")"}
            items.append(newitem)
        save_to_file(items, filename, ADDON_DATA_PATH)
        return items


def HandleBandsInTownResult(results):
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
            log("Exception in HandleBandsInTownResult")
            log(e)
            prettyprint(event)
    return events


def GetArtistNearEvents(Artists):  # not possible with api 2.0
    ArtistStr = ''
    count = 0
    for art in Artists:
        artist = art['artist']
        try:
            artist = urllib.quote(artist)
        except:
            artist = urllib.quote(artist.encode("utf-8"))
        if count < 49:
            if len(ArtistStr) > 0:
                ArtistStr = ArtistStr + '&'
            ArtistStr = ArtistStr + 'artists[]=' + artist
            count += 1
    base_url = 'http://api.bandsintown.com/events/search?format=json&location=use_geoip&radius=50&per_page=100&api_version=2.0'
    url = '&%sapp_id=%s' % (ArtistStr, BANDSINTOWN_KEY)
    results = Get_JSON_response(base_url + url)
    return HandleBandsInTownResult(results)
    if False:
        log("GetArtistNearEvents: error when getting artist data from " + url)
        log(results)
        return []
