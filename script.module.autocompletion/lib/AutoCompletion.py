# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmcaddon
import xbmcvfs
import urllib
import codecs
import os
import time
import hashlib
import urllib2
import xbmc
import simplejson

ADDON = xbmcaddon.Addon()
SETTING = ADDON.getSetting
ADDON_PATH = os.path.join(os.path.dirname(__file__), "..")
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_DATA_PATH = xbmc.translatePath("special://profile/addon_data/%s" % ADDON_ID).decode("utf-8")
HEADERS = {'User-agent': 'Mozilla/5.0'}


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
    else:
        provider = LocalDictProvider(limit=limit)
    provider.limit = limit
    return provider.get_predictions(search_str)


class BaseProvider(object):

    def __init__(self, *args, **kwargs):
        self.limit = kwargs.get("limit", 10)

    def get_predictions(self, search_str):
        pass

    def prep_search_str(self, text):
        if type(text) != unicode:
            text = text.decode('utf-8')
        for chr in text:
            if ord(chr) >= 1488 and ord(chr) <= 1514:
                return text[::-1]
        return text

    def get_prediction_listitems(self, search_str):
        for item in self.get_predictions(search_str):
            li = {"label": item,
                  "search_string": search_str}
            yield li


class GoogleProvider(BaseProvider):

    def __init__(self, *args, **kwargs):
        super(GoogleProvider, self).__init__(*args, **kwargs)
        self.youtube = kwargs.get("youtube", False)

    def get_predictions(self, search_str):
        """
        get dict list with autocomplete labels from google
        """
        if not search_str:
            return []
        items = []
        result = self.fetch_data(search_str)
        for i, item in enumerate(result):
            li = {"label": item,
                  "search_string": self.prep_search_str(item)}
            items.append(li)
            if i > self.limit:
                break
        return items

    def fetch_data(self, search_str):
        base_url = "http://clients1.google.com/complete/"
        url = "search?hl=%s&q=%s&json=t&client=serp" % (SETTING("autocomplete_lang"), urllib.quote_plus(search_str))
        if self.youtube:
            url += "&ds=yt"
        result = get_JSON_response(url=base_url + url,
                                   headers=HEADERS,
                                   folder="Google")
        if not result or len(result) <= 1:
            return []
        else:
            return result[1]


class BingProvider(BaseProvider):

    def __init__(self, *args, **kwargs):
        super(BingProvider, self).__init__(*args, **kwargs)

    def get_predictions(self, search_str):
        """
        get dict list with autocomplete labels from bing
        """
        if not search_str:
            return []
        items = []
        result = self.fetch_data(search_str)
        for i, item in enumerate(result):
            li = {"label": item,
                  "search_string": self.prep_search_str(item)}
            items.append(li)
            if i > self.limit:
                break
        return items

    def fetch_data(self, search_str):
        base_url = "http://api.bing.com/osjson.aspx?"
        url = "query=%s" % (urllib.quote_plus(search_str))
        result = get_JSON_response(url=base_url + url,
                                   headers=HEADERS,
                                   folder="Bing")
        if not result:
            return []
        else:
            return result[1]


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
        path = os.path.join(ADDON_PATH, "resources", "data", "common_%s.txt" % SETTING("autocomplete_lang_local"))
        with codecs.open(path, encoding="utf8") as f:
            for i, line in enumerate(f.readlines()):
                if not line.startswith(search_str) or len(line) <= 2:
                    continue
                li = {"label": line,
                      "search_string": line}
                listitems.append(li)
                if len(listitems) > self.limit:
                    break
        return listitems


def get_JSON_response(url="", cache_days=7.0, folder=False, headers=False):
    """
    get JSON response for *url, makes use of file cache.
    """
    now = time.time()
    hashed_url = hashlib.md5(url).hexdigest()
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
            results = simplejson.loads(response)
            log("download %s. time: %f" % (url, time.time() - now))
            save_to_file(results, hashed_url, cache_path)
        except:
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
        headers = {'User-agent': 'XBMC/14.0 ( phil65@kodi.tv )'}
    request = urllib2.Request(url)
    for (key, value) in headers.iteritems():
        request.add_header(key, value)
    while (succeed < 2) and (not xbmc.abortRequested):
        try:
            response = urllib2.urlopen(request, timeout=3)
            data = response.read()
            return data
        except:
            log("get_http: could not get data from %s" % url)
            xbmc.sleep(1000)
            succeed += 1
    return None


def read_from_file(path="", raw=False):
    """
    return data from file with *path
    """
    if not xbmcvfs.exists(path):
        return False
    try:
        with open(path) as f:
            log("opened textfile %s." % (path))
            if raw:
                return f.read()
            else:
                return simplejson.load(f)
    except:
        log("failed to load textfile: " + path)
        return False


def log(txt):
    if isinstance(txt, str):
        txt = txt.decode("utf-8", 'ignore')
    message = u'%s: %s' % (ADDON_ID, txt)
    xbmc.log(msg=message.encode("utf-8", 'ignore'),
             level=xbmc.LOGDEBUG)


def save_to_file(content, filename, path=""):
    """
    dump json and save to *filename in *path
    """
    if not xbmcvfs.exists(path):
        xbmcvfs.mkdirs(path)
    text_file_path = os.path.join(path, filename + ".txt")
    now = time.time()
    text_file = xbmcvfs.File(text_file_path, "w")
    simplejson.dump(content, text_file)
    text_file.close()
    log("saved textfile %s. Time: %f" % (text_file_path, time.time() - now))
    return True
