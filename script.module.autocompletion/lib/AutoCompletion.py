# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

from abc import ABC, abstractmethod
from urllib.parse import quote_plus
import os
import time
import hashlib
import requests
import json

import xbmc
import xbmcaddon
import xbmcvfs

SCRIPT_ID = "script.module.autocompletion"
SCRIPT_ADDON = xbmcaddon.Addon(SCRIPT_ID)
PLUGIN_ID = "plugin.program.autocompletion"
PLUGIN_ADDON = xbmcaddon.Addon(PLUGIN_ID)
SETTING = PLUGIN_ADDON.getSetting
ADDON_PATH = xbmcvfs.translatePath(SCRIPT_ADDON.getAddonInfo("path"))
ADDON_ID = SCRIPT_ADDON.getAddonInfo("id")
ADDON_DATA_PATH = xbmcvfs.translatePath(SCRIPT_ADDON.getAddonInfo("profile"))


def get_autocomplete_items(search_str, limit=10, provider=None):
    """
    get dict list with autocomplete
    """
    if xbmc.getCondVisibility("System.HasHiddenInput"):
        return []

    setting = SETTING("autocomplete_provider").lower()

    if setting == "youtube":
        provider = GoogleProvider(youtube=True, limit=limit)
    elif setting == "google":
        provider = GoogleProvider(limit=limit)
    elif setting == "bing":
        provider = BingProvider(limit=limit)
    elif setting == "tmdb":
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


class BaseProvider(ABC):

    HEADERS = {'User-agent': 'Mozilla/5.0'}

    def __init__(self, *args, **kwargs):
        self.limit = kwargs.get("limit", 10)
        self.language = SETTING("autocomplete_lang")

    @abstractmethod
    def build_url(self, query):
        pass

    def get_predictions(self, search_str):
        if not search_str:
            return []
        items = []
        result = self.fetch_data(search_str)
        for i, item in enumerate(result):
            li = {"label": item, "search_string": prep_search_str(item)}
            items.append(li)
            if i > int(self.limit):
                break
        return items

    def get_prediction_listitems(self, search_str):
        for item in self.get_predictions(search_str):
            li = {"label": item, "search_string": search_str}
            yield li

    def fetch_data(self, search_str):
        url = self.build_url(quote_plus(search_str))
        result = get_JSON_response(url=self.BASE_URL.format(endpoint=url), headers=self.HEADERS, folder=self.FOLDER)
        return self.process_result(result)

    def process_result(self, result):
        if not result or len(result) <= 1:
            return []
        else:
            return result[1] if isinstance(result[1], list) else result


class GoogleProvider(BaseProvider):

    BASE_URL = "http://clients1.google.com/complete/{endpoint}"
    FOLDER = "Google"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.youtube = kwargs.get("youtube", False)

    def build_url(self, query):
        url = f"search?hl={self.language}&q={query}&json=t&client=serp"
        if self.youtube:
            url += "&ds=yt"
        return url


class BingProvider(BaseProvider):

    BASE_URL = "http://api.bing.com/osjson.aspx?{endpoint}"
    FOLDER = "Bing"

    def __init__(self, *args, **kwargs):
        super(BingProvider, self).__init__(*args, **kwargs)

    def build_url(self, query):
        url = f"query={query}"
        return url


class TmdbProvider(BaseProvider):

    BASE_URL = "https://www.themoviedb.org/search/multi?{endpoint}"
    FOLDER = "TMDB"

    def __init__(self, *args, **kwargs):
        super(TmdbProvider, self).__init__(*args, **kwargs)

    def build_url(self, query):
        url = f"language={self.language}&query={query}"
        return url

    def process_result(self, result):
        if not result or not result.get("results"):
            return []
        out = []
        results = result.get("results")
        for i in results:
            title = None
            media_type = i.get("media_type")
            if media_type == "movie":
                title = i["title"]
            elif media_type in ["tv", "person"]:
                title = i["name"]
            else:
                title = i
            out.append(title)
        return out


class LocalDictProvider(BaseProvider):
    def __init__(self, *args, **kwargs):
        super(LocalDictProvider, self).__init__(*args, **kwargs)
        local = SETTING("autocomplete_lang_local")
        if local:
            self.language = local
        else:
            self.language = "en"

    def build_url(self, query):
        return super().build_url(query)

    def fetch_data(self, search_str):
        k = search_str.rfind(" ")
        if k >= 0:
            search_str = search_str[k + 1 :]

        path = os.path.join(ADDON_PATH, "resources", "data", f"common_{self.language}.txt")
        suggestions = []

        with xbmcvfs.File(path) as f:
            for line in f.read().split('\n'):
                if not line.startswith(search_str) or len(line) <= 2:
                    continue
                suggestions.append(line)
                if len(suggestions) > int(self.limit):
                    break

        return suggestions


def get_JSON_response(url="", cache_days=7.0, folder=False, headers=False):
    """
    get JSON response for *url, makes use of file cache.
    """
    now = time.time()
    hashed_url = hashlib.md5(url.encode("utf-8")).hexdigest()
    cache_path = xbmcvfs.translatePath(os.path.join(ADDON_DATA_PATH, folder) if folder else ADDON_DATA_PATH)
    path = os.path.join(cache_path, f"{hashed_url}.txt")
    cache_seconds = int(cache_days * 86400)
    results = []

    if xbmcvfs.exists(path) and ((now - os.path.getmtime(path)) < cache_seconds):
        results = read_from_file(path)
        log(f"loaded file for {url}. time: {float(time.time() - now)}")
    else:
        response = get_http(url, headers)
        try:
            results = json.loads(response)
            log(f"download {url}. time: {float(time.time() - now)}")
            save_to_file(results, hashed_url, cache_path)
        except Exception:
            log(f"Exception: Could not get new JSON data from {url}. Trying to fallback to cache")
            log(response)
            results = read_from_file(path)

    return results


def get_http(url, headers):
    """
    fetches data from *url, returns it as a string
    """
    succeed = 0
    monitor = xbmc.Monitor()
    while (succeed < 2) and (not monitor.abortRequested()):
        try:
            response = requests.get(url, headers=headers)
            if not response.ok:
                raise Exception
            return response.text
        except Exception:
            log(f"get_http: could not get data from {url}")
            monitor.waitForAbort(1)
            succeed += 1
    return None


def read_from_file(path="", raw=False):
    """
    return data from file with *path
    """
    if not xbmcvfs.exists(path):
        return []

    try:
        with xbmcvfs.File(path) as f:
            log(f"opened textfile {path}.")
            if raw:
                return f.read()
            else:
                return json.load(f)
    except Exception:
        log(f"failed to load textfile: {path}")
        return []


def log(txt):
    message = f"{ADDON_ID}: {txt}"
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)


def save_to_file(content, filename, path=""):
    """
    dump json and save to *filename in *path
    """
    if not xbmcvfs.exists(path):
        xbmcvfs.mkdirs(path)

    text_file_path = os.path.join(path, f"{filename}.txt")
    now = time.time()

    with xbmcvfs.File(text_file_path, "w") as text_file:
        json.dump(content, text_file)

    log(f"saved textfile {text_file_path}. Time: {float(time.time() - now)}")
    return True
