# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

from functools import wraps
import threading
import json
import os
import datetime
import time
import re
import hashlib
import urllib
import urllib2
import xbmc
import xbmcgui
import xbmcvfs
import requests

import YDStreamExtractor
from kodi65 import addon


def youtube_info_by_id(youtube_id):
    vid = get_youtube_info(youtube_id)
    if not vid:
        return None, None
    url = vid.streamURL()
    listitem = xbmcgui.ListItem(label=vid.title,
                                thumbnailImage=vid.thumbnail,
                                path=url)
    listitem.setInfo(type='video',
                     infoLabels={"genre": vid.sourceName,
                                 "path": url,
                                 "plot": vid.description})
    listitem.setProperty("isPlayable", "true")
    return url, listitem


def get_youtube_info(youtube_id):
    return YDStreamExtractor.getVideoInfo(youtube_id,
                                          quality=1)


def log(*args):
    for arg in args:
        if isinstance(arg, str):
            arg = arg.decode("utf-8", 'ignore')
        message = u'%s: %s' % (addon.ID, arg)
        xbmc.log(msg=message.encode("utf-8", 'ignore'),
                 level=xbmc.LOGDEBUG)


def format_seconds(seconds):
    if not seconds:
        return None
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return '%02d:%02d:%02d' % (hours, minutes, seconds)


def dump_dict(dct):
    return json.dumps(dct,
                      sort_keys=True,
                      indent=4,
                      separators=(',', ': '))


def pp(string):
    """
    prettyprint json
    """
    log(dump_dict(string))


def dictfind(lst, key, value):
    for i, dic in enumerate(lst):
        if dic[key] == value:
            return dic
    return ""


def merge_dicts(*dict_args):
    '''
    Given any number of dicts, shallow copy and merge into a new dict,
    precedence goes to key value pairs in latter dicts.
    '''
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result


def check_version():
    """
    check version, open TextViewer if update detected
    """
    pass
    # if not addon.setting("changelog_version") == addon.VERSION:
    #     xbmcgui.Dialog().textviewer(heading=addon.LANG(24036),
    #                                 text=read_from_file(addon.CHANGELOG, True))
    #     addon.set_setting("changelog_version", addon.VERSION)


def get_skin_string(name):
    return xbmc.getInfoLabel("Skin.String(%s)").decode("utf-8")


def set_skin_string(name, value):
    xbmc.executebuiltin("Skin.SetString(%s, %s)" % (name, value))


def run_async(func):
    """
    Decorator to run a function in a separate thread
    """
    @wraps(func)
    def async_func(*args, **kwargs):
        func_hl = threading.Thread(target=func,
                                   args=args,
                                   kwargs=kwargs)
        func_hl.start()
        return func_hl

    return async_func


def contextmenu(options):
    index = xbmcgui.Dialog().contextmenu(list=[i[1] for i in options])
    if index > -1:
        return [i[0] for i in options][index]


def extract_youtube_id(raw_string):
    """
    get youtube video id if from youtube URL
    """
    vid_ids = None
    if raw_string and 'youtube.com/v' in raw_string:
        vid_ids = re.findall('http://www.youtube.com/v/(.{11})\??', raw_string, re.DOTALL)
    elif raw_string and 'youtube.com/watch' in raw_string:
        vid_ids = re.findall('youtube.com/watch\?v=(.{11})\??', raw_string, re.DOTALL)
    if vid_ids:
        return vid_ids[0]
    else:
        return ""


def download_video(youtube_id):
    vid = YDStreamExtractor.getVideoInfo(youtube_id,
                                         quality=1)
    YDStreamExtractor.handleDownload(vid)


def notify(header="", message="", icon=addon.ICON, time=5000, sound=True):
    xbmcgui.Dialog().notification(heading=header,
                                  message=message,
                                  icon=icon,
                                  time=time,
                                  sound=sound)


def millify(n):
    """
    make large numbers human-readable, return string
    """
    millnames = [' ', '.000', ' ' + addon.LANG(32000), ' ' + addon.LANG(32001), ' ' + addon.LANG(32002)]
    if not n or n <= 100:
        return ""
    n = float(n)
    char_count = len(str(n))
    millidx = (char_count / 3) - 1
    if millidx == 3 or char_count == 9:
        return '%.2f%s' % (n / 10 ** (3 * millidx), millnames[millidx])
    else:
        return '%.0f%s' % (n / 10 ** (3 * millidx), millnames[millidx])


def get_year(year_string):
    """
    return last 4 chars of string
    """
    return year_string[:4] if year_string else ""


def format_time(time, time_format=None):
    """
    get formatted time
    time_format = h, m or None
    """
    try:
        intTime = int(time)
    except Exception:
        return time
    hour = str(intTime / 60)
    minute = str(intTime % 60).zfill(2)
    if time_format == "h":
        return hour
    elif time_format == "m":
        return minute
    elif intTime >= 60:
        return hour + " h " + minute + " min"
    else:
        return minute + " min"


def input_userrating(preselect=-1):
    index = xbmcgui.Dialog().select(heading=addon.LANG(38023),
                                    list=[addon.LANG(10035)] + [str(i) for i in xrange(1, 11)],
                                    preselect=preselect)
    if index == preselect:
        return -1
    return index


def save_to_file(content, filename, path):
    """
    dump json and save to *filename in *path
    """
    if not xbmcvfs.exists(path):
        xbmcvfs.mkdirs(path)
    text_file_path = os.path.join(path, filename + ".txt")
    text_file = xbmcvfs.File(text_file_path, "w")
    json.dump(content, text_file)
    text_file.close()
    return True


def read_from_file(path, raw=False):
    """
    return data from file with *path
    """
    if not xbmcvfs.exists(path):
        return False
    try:
        with open(path) as f:
            # utils.log("opened textfile %s." % (path))
            if not raw:
                result = json.load(f)
            else:
                result = f.read()
        return result
    except Exception:
        log("failed to load textfile: " + path)
        return False


def create_listitems(data=None, preload_images=0):
    return [item.get_listitem() for item in data] if data else []


def translate_path(*args):
    return xbmc.translatePath(os.path.join(*args)).decode("utf-8")


def get_infolabel(name):
    return xbmc.getInfoLabel(name).decode("utf-8")


def calculate_age(born, died=False):
    """
    calculate age based on born / died
    display notification for birthday
    return death age when already dead
    """
    if died:
        ref_day = died.split("-")
    elif born:
        date = datetime.date.today()
        ref_day = [date.year, date.month, date.day]
    else:
        return ""
    actor_born = born.split("-")
    base_age = int(ref_day[0]) - int(actor_born[0])
    if len(actor_born) > 1:
        diff_months = int(ref_day[1]) - int(actor_born[1])
        diff_days = int(ref_day[2]) - int(actor_born[2])
        if diff_months < 0 or (diff_months == 0 and diff_days < 0):
            base_age -= 1
        elif diff_months == 0 and diff_days == 0 and not died:
            notify("%s (%i)" % (addon.LANG(32158), base_age))
    return base_age


def get_http(url, headers=False):
    """
    fetches data from *url, returns it as a string
    """
    succeed = 0
    if not headers:
        headers = {'User-agent': 'Kodi/17.0 ( phil65@kodi.tv )'}
    while (succeed < 2) and (not xbmc.abortRequested):
        try:
            request = requests.get(url, headers=headers)
            return request.text
        except Exception:
            log("get_http: could not get data from %s" % url)
            xbmc.sleep(1000)
            succeed += 1
    return None


def post(url, values, headers):
    request = requests.post(url=url,
                            data=json.dumps(values),
                            headers=headers)
    return json.loads(request.text)


def delete(url, values, headers):
    request = requests.delete(url=url,
                              data=json.dumps(values),
                              headers=headers)
    return json.loads(request.text)


def get_JSON_response(url="", cache_days=7.0, folder=False, headers=False):
    """
    get JSON response for *url, makes use of prop and file cache.
    """
    now = time.time()
    hashed_url = hashlib.md5(url).hexdigest()
    cache_path = translate_path(addon.DATA_PATH, folder) if folder else translate_path(addon.DATA_PATH)
    cache_seconds = int(cache_days * 86400.0)
    if not cache_days:
        addon.clear_global(hashed_url)
        addon.clear_global(hashed_url + "_timestamp")
    prop_time = addon.get_global(hashed_url + "_timestamp")
    if prop_time and now - float(prop_time) < cache_seconds:
        try:
            prop = json.loads(addon.get_global(hashed_url))
            if prop:
                return prop
        except Exception:
            # utils.log("could not load prop data for %s" % url)
            pass
    path = os.path.join(cache_path, hashed_url + ".txt")
    if xbmcvfs.exists(path) and ((now - os.path.getmtime(path)) < cache_seconds):
        results = read_from_file(path)
        # utils.log("loaded file for %s. time: %f" % (url, time.time() - now))
    else:
        response = get_http(url, headers)
        try:
            results = json.loads(response)
            # utils.log("download %s. time: %f" % (url, time.time() - now))
            save_to_file(results, hashed_url, cache_path)
        except Exception:
            log("Exception: Could not get new JSON data from %s. Tryin to fallback to cache" % url)
            log(response)
            results = read_from_file(path) if xbmcvfs.exists(path) else []
    if not results:
        return None
    addon.set_global(hashed_url + "_timestamp", str(now))
    addon.set_global(hashed_url, json.dumps(results))
    return results


def dict_to_windowprops(data=None, prefix="", window_id=10000):
    window = xbmcgui.Window(window_id)
    if not data:
        return None
    for (key, value) in data.iteritems():
        value = unicode(value)
        window.setProperty('%s%s' % (prefix, key), value)


def get_file(url):
    clean_url = translate_path(urllib.unquote(url)).replace("image://", "")
    clean_url = clean_url.rstrip("/")
    cached_thumb = xbmc.getCacheThumbName(clean_url)
    vid_cache_file = os.path.join("special://profile/Thumbnails/Video", cached_thumb[0], cached_thumb)
    cache_file_jpg = os.path.join("special://profile/Thumbnails/", cached_thumb[0], cached_thumb[:-4] + ".jpg").replace("\\", "/")
    cache_file_png = cache_file_jpg[:-4] + ".png"
    if xbmcvfs.exists(cache_file_jpg):
        log("cache_file_jpg Image: " + url + "-->" + cache_file_jpg)
        return translate_path(cache_file_jpg)
    elif xbmcvfs.exists(cache_file_png):
        log("cache_file_png Image: " + url + "-->" + cache_file_png)
        return cache_file_png
    elif xbmcvfs.exists(vid_cache_file):
        log("vid_cache_file Image: " + url + "-->" + vid_cache_file)
        return vid_cache_file
    try:
        request = urllib2.Request(clean_url)
        request.add_header('Accept-encoding', 'gzip')
        response = urllib2.urlopen(request, timeout=3)
        data = response.read()
        response.close()
        log('image downloaded: ' + clean_url)
    except Exception:
        log('image download failed: ' + clean_url)
        return ""
    if not data:
        return ""
    image = cache_file_png if url.endswith(".png") else cache_file_jpg
    try:
        with open(translate_path(image), "wb") as f:
            f.write(data)
        return translate_path(image)
    except Exception:
        log('failed to save image ' + url)
        return ""


def fetch_musicbrainz_id(artist, artist_id=-1):
    """
    fetches MusicBrainz ID for given *artist and returns it
    uses musicbrainz.org
    """
    base_url = "http://musicbrainz.org/ws/2/artist/?fmt=json"
    url = '&query=artist:%s' % urllib.quote_plus(artist.encode('utf-8'))
    results = get_JSON_response(url=base_url + url,
                                cache_days=30,
                                folder="MusicBrainz")
    if results and len(results["artists"]) > 0:
        log("found artist id for %s: %s" % (artist, results["artists"][0]["id"]))
        return results["artists"][0]["id"]
    else:
        return None


class FunctionThread(threading.Thread):

    def __init__(self, function=None, param=None):
        threading.Thread.__init__(self)
        self.function = function
        self.param = param
        self.setName(self.function.__name__)
        log("init " + self.function.__name__)

    def run(self):
        self.listitems = self.function(self.param)
        return True


def reset_color(item):
    label = item.getLabel2()
    label = label.replace("[COLOR=FFFF3333]", "").replace("[/COLOR]", "")
    item.setLabel2(label)


def dict_to_listitems(data=None):
    if not data:
        return []
    itemlist = []
    for (count, result) in enumerate(data):
        listitem = xbmcgui.ListItem('%s' % (str(count)))
        for (key, value) in result.iteritems():
            if not value:
                continue
            value = unicode(value)
            if key.lower() in ["name", "label"]:
                listitem.setLabel(value)
            elif key.lower() in ["label2"]:
                listitem.setLabel2(value)
            elif key.lower() in ["path"]:
                listitem.setPath(path=value)
            listitem.setProperty('%s' % (key), value)
        listitem.setProperty("index", str(count))
        itemlist.append(listitem)
    return itemlist


def pretty_date(time=False):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
    # https://stackoverflow.com/questions/1551382/user-friendly-time-format-in-python
    """
    now = datetime.now()
    if type(time) is int:
        diff = now - datetime.fromtimestamp(time)
    elif isinstance(time, datetime):
        diff = now - time
    elif not time:
        diff = now - now
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(second_diff) + " seconds ago"
        if second_diff < 120:
            return "a minute ago"
        if second_diff < 3600:
            return str(second_diff / 60) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str(second_diff / 3600) + " hours ago"
    if day_diff == 1:
        return "Yesterday"
    if day_diff < 7:
        return str(day_diff) + " days ago"
    if day_diff < 31:
        return str(day_diff / 7) + " weeks ago"
    if day_diff < 365:
        return str(day_diff / 30) + " months ago"
    return str(day_diff / 365) + " years ago"
