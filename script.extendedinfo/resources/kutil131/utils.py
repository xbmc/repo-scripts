# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details
import datetime
import hashlib
import json
import os
import re
import sys
import threading
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from functools import wraps
from io import StringIO

import requests
import xbmc
import xbmcgui
import xbmcvfs

#import YDStreamExtractor
from resources.kutil131 import addon


def youtube_info_by_id(youtube_id) -> tuple:
    """Gets youtube video info from YDSStreamExtractor
    Currently inop due to YDSStreamextractor not maintained.

    Args:
        youtube_id (_type_): _description_

    Returns:
        _type_: _description_
    """
    #vid = get_youtube_info(youtube_id)
    vid = None #added
    if not vid:
        return None, None
    url = vid.streamURL()
    listitem = xbmcgui.ListItem(label=vid.title, path=url)
    listitem.setArt({'thumb': vid.thumbnail})
    listitem.setInfo(type='video',
                     infoLabels={"genre": vid.sourceName,
                                 "path": url,
                                 "plot": vid.description})
    listitem.setProperty("isPlayable", "true")
    return url, listitem


#def get_youtube_info(youtube_id):
#    return YDStreamExtractor.getVideoInfo(youtube_id,
#                                          quality=1)


def log(*args):
    for arg in args:
        message = '%s: %s' % (addon.ID, arg)
        xbmc.log(msg=message,
                 level=xbmc.LOGDEBUG)


def dump_all_threads(delay: float = None) -> None:
    """
        Dumps all Python stacks, including those in other plugins

    :param delay:
    :return:
    """
    if delay is None or delay == 0:
        _dump_all_threads()
    else:
        dump_threads = threading.Timer(delay, _dump_all_threads)
        dump_threads.setName('dump_threads')
        dump_threads.start()


def _dump_all_threads() -> None:
    """
        Worker method that dumps all threads.

    :return:
    """
    addon_prefix = f'{addon.ID}/'
    xbmc.log('dump_all_threads', xbmc.LOGDEBUG)
    sio = StringIO()
    sio.write('\n*** STACKTRACE - START ***\n\n')
    code = []
    #  Monitor.dump_wait_counts()
    #  for threadId, stack in sys._current_frames().items():
    for th in threading.enumerate():
        sio.write(f'\n# ThreadID: {th.name} Daemon: {th.isDaemon()}\n\n')
        stack = sys._current_frames().get(th.ident, None)
        if stack is not None:
            traceback.print_stack(stack, file=sio)

    string_buffer: str = sio.getvalue() + '\n*** STACKTRACE - END ***\n'
    sio.close()
    msg = addon.ID + ' : dump_all_threads'
    xbmc.log(msg, xbmc.LOGDEBUG)
    xbmc.log(string_buffer, xbmc.LOGDEBUG)

    '''
    try:
        dump_path = Constants.FRONTEND_DATA_PATH + '/stack_dump'

        dump_file = io.open(dump_path, mode='at', buffering=1, newline=None,
                            encoding='ascii')

        faulthandler.dump_traceback(file=dump_file, all_threads=True)
    except Exception as e:
         pass
    '''


def format_seconds(seconds):
    if not seconds:
        return None
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return '%02d:%02d:%02d' % (hours, minutes, seconds)


def dump_dict(dct):
    return json.dumps(dct,
                      ensure_ascii=False,
                      sort_keys=True,
                      indent=4,
                      separators=(',', ': '))


def pp(string):
    """
    prettyprint json
    """
    log(dump_dict(string))


def dictfind(lst, key, value):
    """
    searches through a list of dicts, returns dict where dict[key] = value
    """
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
    """
    get String with name *name
    """
    return xbmc.getInfoLabel(f"Skin.String({name})")


def set_skin_string(name, value):
    """
    Set String *name to value *value
    """
    xbmc.executebuiltin(f"Skin.SetString({name}, {value})")


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
    """
    pass list of tuples (index, label), get index
    """
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


# def download_video(youtube_id):
#     """
#     download youtube video with id *youtube_id
#     """
#     vid = YDStreamExtractor.getVideoInfo(youtube_id,
#                                          quality=1)
#     YDStreamExtractor.handleDownload(vid)


def notify(header="", message="", icon=addon.ICON, ntime=5000, sound=True):
    """
    show kodi notification dialog
    """
    xbmcgui.Dialog().notification(heading=header,
                                  message=message,
                                  icon=icon,
                                  time=ntime,
                                  sound=sound)


def millify(n):
    """
    make large numbers human-readable, return string
    """
    millnames = [' ', ',000', ' ' + addon.LANG(32000), ' ' + addon.LANG(32001), ' ' + addon.LANG(32002)]
    if not n or n <= 100:
        return ""
    n = float(n)
    char_count = len(str(n))
    millidx = int(char_count / 3) - 1
    if millidx == 3 or char_count == 9:
        return '%.2f%s' % (n / 10 ** (3 * millidx), millnames[millidx])
    else:
        return '%.0f%s' % (n / 10 ** (3 * millidx), millnames[millidx])


def get_year(year_string):
    """
    return last 4 chars of string
    """
    return year_string[:4] if year_string else ""


def format_time(ftime:int, time_format=None):
    """
    get formatted time
    time (int): duration in secs
    time_format = h, m or None
    """
    try:
        intTime = int(ftime)
    except Exception:
        return ftime
    #hour = str(intTime / 60)
    #minute = str(intTime % 60).zfill(2)
    minute, second = divmod(ftime, 60)
    hour, minute = divmod(minute, 60)
    if time_format == "h":
        return str(hour)
    elif time_format == "m":
        return str(minute)
    elif time_format == 's':
        return str(second)
    elif intTime >= 3600:
        return hour + " h " + minute + " min"
    else:
        return minute + " min"


def input_userrating(preselect=-1):
    """
    opens selectdialog and returns chosen userrating.
    """
    index = xbmcgui.Dialog().select(heading=addon.LANG(38023),
                                    list=[addon.LANG(10035)] + [str(i) for i in range(1, 11)],
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
    """
    returns list with xbmcgui listitems
    """
    return [item.get_listitem() for item in data] if data else []


def translate_path(arg1, *args):
    return xbmcvfs.translatePath(os.path.join(arg1, *args))


def get_infolabel(name):
    """
    returns infolabel with *name
    """
    return xbmc.getInfoLabel(name)


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
    try:
        base_age = int(ref_day[0]) - int(actor_born[0])
    except ValueError as err:
        log(f'utils.calculate_age fail for actor_born {actor_born} with error {err}')
        return ""
    if len(actor_born) > 1:
        diff_months = int(ref_day[1]) - int(actor_born[1])
        diff_days = int(ref_day[2]) - int(actor_born[2])
        if diff_months < 0 or (diff_months == 0 and diff_days < 0):
            base_age -= 1
        elif diff_months == 0 and diff_days == 0 and not died:
            notify(f"{addon.LANG(32158)} ({base_age})")
    return base_age


def get_http(url, headers=False):
    """
    fetches data from *url as http GET, returns it as a string
    """
    succeed = 0
    if not headers:
        headers = {'User-agent': 'Kodi/19.0 ( fbacher@kodi.tv )'}
    while (succeed < 2) and (not xbmc.Monitor().abortRequested()):
        try:
            request = requests.get(url, headers=headers, timeout=10)
            return request.text
        except requests.exceptions.RequestException as err:
            log(f"get_http: could not get data from {url} exception {err}")
            xbmc.sleep(1000)
            succeed += 1
    return None


def post(url, values, headers):
    """
    retuns answer to post request
    """
    try:
        request = requests.post(url=url,
                                data=json.dumps(values),
                                headers=headers,
                                timeout=10)
    except requests.exceptions.RequestException as err:
        log(f"get_http: could not get data from {url} exception {err}")
    return json.loads(request.text)


def delete(url, values, headers):
    """
    returns answer to delete request
    """
    try:
        request = requests.delete(url=url,
                                data=json.dumps(values),
                                headers=headers,
                                timeout=10)
    except requests.exceptions.RequestException as err:
        log(f"get_http: could not get data from {url} exception {err}")
    return json.loads(request.text)


def get_JSON_response(url="", cache_days=7.0, folder=False, headers=False) -> dict:
    """gets JSON response for *url, makes use of prop and file cache.

    Args:
        url (str, optional): search query URL. Defaults to "".
        cache_days (float, optional): Number of days to determine cache is stale. Defaults to 7.0.
        folder (bool, optional): folder on local system to cache query results. Defaults to False.
        headers (bool, optional): headers to use in https request. Defaults to False.

    Returns:
        dict: a deserialized JSON query response or None
    """
    now = time.time()
    hashed_url = hashlib.md5(url.encode("utf-8", "ignore")).hexdigest()
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
            pass
    path = os.path.join(cache_path, hashed_url + ".txt")
    if xbmcvfs.exists(path) and ((now - os.path.getmtime(path)) < cache_seconds):
        results = read_from_file(path)
    else:
        response = get_http(url, headers)
        try:
            results = json.loads(response)
            # utils.log("download %s. time: %f" % (url, time.time() - now))
            if "status_code" in results and results.get("status_code") == 1:
                save_to_file(results, hashed_url, cache_path)
        except Exception as err:
            log(f"Exception: Could not get new JSON data from {url} "
                f"with error {err}. Trying to fallback to cache")
            #log(f'kutils131.utils.get_JSON_response {response}')
            results = read_from_file(path) if xbmcvfs.exists(path) else []
    if not results:
        return None
    addon.set_global(hashed_url + "_timestamp", str(now))
    addon.set_global(hashed_url, json.dumps(results))
    return results


def dict_to_windowprops(data:dict=None, prefix="", window_id=10000):
    """Sets window property keys / values from dict

    Args:
        data (dict optional):  the data to be set as properties Defaults to None.
        prefix (str, optional): a prefix for the property key Defaults to "".
        window_id (int, optional): Kodi window id. Defaults to 10000.
    """
    window = xbmcgui.Window(window_id)
    if not data:
        return None
    for (key, value) in data.items():
        value = str(value)
        window.setProperty(f'{prefix}{key}', value)


def get_file(url):
    clean_url = translate_path(urllib.parse.unquote(url)).replace("image://", "")
    clean_url = clean_url.rstrip("/")
    cached_thumb = xbmc.getCacheThumbName(clean_url)
    vid_cache_file = os.path.join("special://profile/Thumbnails/Video",
                                  cached_thumb[0],
                                  cached_thumb)
    cache_file_jpg = os.path.join("special://profile/Thumbnails/",
                                  cached_thumb[0],
                                  cached_thumb[:-4] + ".jpg").replace("\\", "/")
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
        request = urllib.request.Request(clean_url)
        request.add_header('Accept-encoding', 'gzip')
        response = urllib.request.urlopen(request, timeout=3)
        data = response.read()
        response.close()
        log(f'image downloaded: {clean_url}')
    except Exception:
        log(f'image download failed: {clean_url}')
        return ""
    if not data:
        return ""
    image = cache_file_png if url.endswith(".png") else cache_file_jpg
    try:
        with open(translate_path(image), "wb") as f:
            f.write(data)
        return translate_path(image)
    except Exception:
        log(f'failed to save image {url}')
        return ""


def fetch_musicbrainz_id(artist, artist_id=-1):
    """
    fetches MusicBrainz ID for given *artist and returns it
    uses musicbrainz.org
    """
    base_url = "http://musicbrainz.org/ws/2/artist/?fmt=json"
    url = f'&query=artist:{urllib.parse.quote_plus(artist.encode("utf-8"))}'
    results = get_JSON_response(url=base_url + url,
                                cache_days=30,
                                folder="MusicBrainz")
    if results and len(results["artists"]) > 0:
        log(f'found artist id for {artist}: {results["artists"][0]["id"]}')
        return results["artists"][0]["id"]
    else:
        return None


class FunctionThread(threading.Thread):

    def __init__(self, function=None, param=None):
        super().__init__()
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
        listitem = xbmcgui.ListItem(f'{str(count)}')
        for (key, value) in result.items():
            if not value:
                continue
            value = str(value)
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


def pretty_date(btime=False):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
    # https://stackoverflow.com/questions/1551382/user-friendly-time-format-in-python
    """
    now = datetime.datetime.now()
    if isinstance(btime, int):
        diff = now - datetime.datetime.fromtimestamp(btime)
    elif isinstance(btime, datetime.datetime):
        diff = now - btime
    elif not btime:
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
