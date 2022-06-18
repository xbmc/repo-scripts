# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

from urllib.parse import quote_plus
import os
import time
import hashlib
import requests
import json

import xbmc
import xbmcaddon
import xbmcvfs

HEADERS = {'User-agent': 'Mozilla/5.0'}

ADDON = xbmcaddon.Addon()
SETTING = ADDON.getSetting
ADDON_PATH = os.path.join(os.path.dirname(__file__), "..")
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_DATA_PATH = xbmcvfs.translatePath("special://profile/addon_data/%s" % ADDON_ID)


def get_autocomplete_items(search_str, limit=10, provider=None):
    """
    get dict list with autocomplete
    """
    if xbmc.getCondVisibility("System.HasHiddenInput"):
        return []
    if SETTING("autocomplete_provider") == "youtube":
        provider = GoogleProvider(youtube=True, limit=limit)
    elif SETTING("autocomplete_provider") == "google":
        provider = GoogleProvider(limit=limit)
    elif SETTING("autocomplete_provider") == "bing":
        provider = BingProvider(limit=limit)
    elif SETTING("autocomplete_provider") == "tmdb":
        provider = TmdbProvider(limit=limit)
    else:
        provider = LocalDictProvider(limit=limit)
    provider.limit = limit
    return provider.get_predictions(search_str)


def prep_search_str(text):
    for char in text:
        if 1488 <= ord(char) <= 1514:
            return text[::-1]
    return text


class BaseProvider(object):
    def __init__(self, *args, **kwargs):
        self.limit = kwargs.get("limit", 10)

    def get_predictions(self, search_str):
        if not search_str:
            return []
        items = []
        result = self.fetch_data(search_str)
        for i, item in enumerate(result):
            li = {"label": item,
                  "search_string": prep_search_str(item)}
            items.append(li)
            if i > int(self.limit):
                break
        return items

    def get_prediction_listitems(self, search_str):
        for item in self.get_predictions(search_str):
            li = {"label": item,
                  "search_string": search_str}
            yield li


class GoogleProvider(BaseProvider):

    BASE_URL = "http://clients1.google.com/complete/"

    def __init__(self, *args, **kwargs):
        super(GoogleProvider, self).__init__(*args, **kwargs)
        self.youtube = kwargs.get("youtube", False)

    def fetch_data(self, search_str):
        url = "search?hl=%s&q=%s&json=t&client=serp" % (
            SETTING("autocomplete_lang"),
            quote_plus(search_str),
        )
        if self.youtube:
            url += "&ds=yt"
        result = get_JSON_response(url=self.BASE_URL + url,
                                   headers=HEADERS,
                                   folder="Google")
        if not result or len(result) <= 1:
            return []
        else:
            return result[1]


class BingProvider(BaseProvider):

    BASE_URL = "http://api.bing.com/osjson.aspx?"

    def __init__(self, *args, **kwargs):
        super(BingProvider, self).__init__(*args, **kwargs)

    def fetch_data(self, search_str):
        url = "query=%s" % (quote_plus(search_str))
        result = get_JSON_response(
            url=self.BASE_URL + url, headers=HEADERS, folder="Bing"
        )
        if not result:
            return []
        else:
            return result[1]


class TmdbProvider(BaseProvider):

    BASE_URL = "https://www.themoviedb.org/search/multi?"

    def __init__(self, *args, **kwargs):
        super(TmdbProvider, self).__init__(*args, **kwargs)

    def fetch_data(self, search_str):
        url = "language=%s&query=%s" % (
            SETTING("autocomplete_lang"),
            quote_plus(search_str),
        )
        result = get_JSON_response(
            url=self.BASE_URL + url, headers=HEADERS, folder="TMDB"
        )
        if not result or "results" not in result:
            return []
        out = []
        for i in result["results"]:
            title = None
            if "media_type" in i:
                if i["media_type"] == "movie":
                    title = i["title"]
                elif i["media_type"] in ["tv", "person"]:
                    title = i["name"]
            else:
                title = i
            out.append(title)
        return out


class LocalDictProvider(BaseProvider):
    def __init__(self, *args, **kwargs):
        super(LocalDictProvider, self).__init__(*args, **kwargs)

    def get_predictions(self, search_str):
        """
        get dict list with autocomplete labels from locally saved lists
        """
        listitems = []
        k = search_str.rfind(" ")
        if k >= 0:
            search_str = search_str[k + 1:]
        local = SETTING("autocomplete_lang_local")
        path = os.path.join(ADDON_PATH, "resources", "data", "common_%s.txt" % (local if local else "en"))
        with xbmcvfs.File(path) as f:
            for line in f.read().split('\n'):
                if not line.startswith(search_str) or len(line) <= 2:
                    continue
                li = {"label": line,
                      "search_string": line}
                listitems.append(li)
                if len(listitems) > int(self.limit):
                    break
        return listitems


def get_JSON_response(url="", cache_days=7.0, folder=False, headers=False):
    """
    get JSON response for *url, makes use of file cache.
    """
    now = time.time()
    hashed_url = hashlib.md5(url.encode('utf-8')).hexdigest()
    if folder:
        cache_path = xbmc.translatePath(os.path.join(ADDON_DATA_PATH, folder))
    else:
        cache_path = xbmc.translatePath(os.path.join(ADDON_DATA_PATH))
    path = os.path.join(cache_path, hashed_url + ".txt")
    cache_seconds = int(cache_days * 86400.0)
    if xbmcvfs.exists(path) and ((now - os.path.getmtime(path)) < cache_seconds):
        results = read_from_file(path)
        log("loaded file for %s. time: %f" % (url, time.time() - now))
    else:
        response = get_http(url, headers)
        try:
            results = json.loads(response)
            log("download %s. time: %f" % (url, time.time() - now))
            save_to_file(results, hashed_url, cache_path)
        except Exception:
            log("Exception: Could not get new JSON data from %s. Tryin to fallback to cache" % url)
            log(response)
            if xbmcvfs.exists(path):
                results = read_from_file(path)
            else:
                results = []
    if results:
        return results
    else:
        return []


def get_http(url=None, headers=False):
    """
    fetches data from *url, returns it as a string
    """
    succeed = 0
    if not headers:
        headers = {'User-agent': 'XBMC/16.0 ( phil65@kodi.tv )'}
    monitor = xbmc.Monitor()
    while (succeed < 2) and (not monitor.abortRequested()):
        try:
            r = requests.get(url, headers=headers)
            if r.status_code != 200:
                raise Exception
            return r.text
        except Exception:
            log("get_http: could not get data from %s" % url)
            monitor.waitForAbort(1)
            succeed += 1
    return None


def read_from_file(path="", raw=False):
    """
    return data from file with *path
    """
    if not xbmcvfs.exists(path):
        return False

    try:
        with xbmcvfs.File(path) as f:
            log("opened textfile %s." % (path))
            if raw:
                return f.read()
            else:
                return json.load(f)
    except Exception:
        log("failed to load textfile: " + path)
        return False


def log(txt):
    message = u'%s: %s' % (ADDON_ID, txt)
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)


def save_to_file(content, filename, path=""):
    """
    dump json and save to *filename in *path
    """
    if not xbmcvfs.exists(path):
        xbmcvfs.mkdirs(path)

    text_file_path = os.path.join(path, filename + ".txt")
    now = time.time()

    with xbmcvfs.File(text_file_path, "w") as text_file:
        json.dump(content, text_file)

    log("saved textfile %s. Time: %f" % (text_file_path, time.time() - now))
    return True
