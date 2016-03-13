# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import urllib
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import xbmcplugin
import urllib2
import os
import time
import hashlib
import simplejson as json
import re
import threading
import datetime
from functools import wraps

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_ICON = ADDON.getAddonInfo('icon')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_PATH = ADDON.getAddonInfo('path').decode("utf-8")
ADDON_VERSION = ADDON.getAddonInfo('version')
ADDON_DATA_PATH = xbmc.translatePath("special://profile/addon_data/%s" % ADDON_ID).decode("utf-8")
HOME = xbmcgui.Window(10000)
SETTING = ADDON.getSetting


def LANG(label_id):
    if 31000 <= label_id <= 33000:
        return ADDON.getLocalizedString(label_id)
    else:
        return xbmc.getLocalizedString(label_id)


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


def busy_dialog(func):
    """
    Decorator to show busy dialog while function is running
    Only one of the decorated functions may run simultaniously
    """

    @wraps(func)
    def decorator(self, *args, **kwargs):
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        result = func(self, *args, **kwargs)
        xbmc.executebuiltin("Dialog.Close(busydialog)")
        return result

    return decorator


def dictfind(lst, key, value):
    for i, dic in enumerate(lst):
        if dic[key] == value:
            return dic
    return ""


def get_infolabel(name):
    return xbmc.getInfoLabel(name).decode("utf-8")


def format_time(time, format=None):
    """
    get formatted time
    format = h, m or None
    """
    try:
        intTime = int(time)
    except:
        return time
    hour = str(intTime / 60)
    minute = str(intTime % 60).zfill(2)
    if format == "h":
        return hour
    elif format == "m":
        return minute
    elif intTime >= 60:
        return hour + " h " + minute + " min"
    else:
        return minute + " min"


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
    if not SETTING("changelog_version") == ADDON_VERSION:
        xbmcgui.Dialog().textviewer(heading=LANG(24036),
                                    text=read_from_file(os.path.join(ADDON_PATH, "changelog.txt"), True))
        ADDON.setSetting("changelog_version", ADDON_VERSION)
    if not SETTING("first_start_infodialog"):
        ADDON.setSetting("first_start_infodialog", "True")
        xbmcgui.Dialog().ok(heading=ADDON_NAME,
                            line1=LANG(32140),
                            line2=LANG(32141))


def widget_selectdialog(filter=None, prefix="widget"):
    """
    show dialog including all video media lists (for widget selection)
    and set strings PREFIX.path and PREFIX.label with chosen values
    """
    movie = {"intheatermovies": "%s [I](RottenTomatoes)[/I]" % LANG(32042),
             "boxofficemovies": "%s [I](RottenTomatoes)[/I]" % LANG(32055),
             "openingmovies": "%s [I](RottenTomatoes)[/I]" % LANG(32048),
             "comingsoonmovies": "%s [I](RottenTomatoes)[/I]" % LANG(32043),
             "toprentalmovies": "%s [I](RottenTomatoes)[/I]" % LANG(32056),
             "currentdvdmovies": "%s [I](RottenTomatoes)[/I]" % LANG(32049),
             "newdvdmovies": "%s [I](RottenTomatoes)[/I]" % LANG(32053),
             "upcomingdvdmovies": "%s [I](RottenTomatoes)[/I]" % LANG(32054),
             # tmdb
             "incinemamovies": "%s [I](TheMovieDB)[/I]" % LANG(32042),
             "upcomingmovies": "%s [I](TheMovieDB)[/I]" % LANG(32043),
             "topratedmovies": "%s [I](TheMovieDB)[/I]" % LANG(32046),
             "popularmovies": "%s [I](TheMovieDB)[/I]" % LANG(32044),
             "accountlists": "%s [I](TheMovieDB)[/I]" % LANG(32045),
             # trakt
             "trendingmovies": "%s [I](Trakt.tv)[/I]" % LANG(32047),
             # tmdb
             "starredmovies": "%s [I](TheMovieDB)[/I]" % LANG(32134),
             "ratedmovies": "%s [I](TheMovieDB)[/I]" % LANG(32135),
             }
    tvshow = {"airingshows": "%s [I](Trakt.tv)[/I]" % LANG(32028),
              "premiereshows": "%s [I](Trakt.tv)[/I]" % LANG(32029),
              "trendingshows": "%s [I](Trakt.tv)[/I]" % LANG(32032),
              "airingtodaytvshows": "%s [I](TheMovieDB)[/I]" % LANG(32038),
              "onairtvshows": "%s [I](TheMovieDB)[/I]" % LANG(32039),
              "topratedtvshows": "%s [I](TheMovieDB)[/I]" % LANG(32040),
              "populartvshows": "%s [I](TheMovieDB)[/I]" % LANG(32041),
              "starredtvshows": "%s [I](TheMovieDB)[/I]" % LANG(32144),
              "ratedtvshows": "%s [I](TheMovieDB)[/I]" % LANG(32145),
              }
    image = {"xkcd": "XKCD webcomics",
             "cyanide": "Cyanide & Happiness webcomics",
             "dailybabe": "%s" % LANG(32057),
             "dailybabes": "%s" % LANG(32058),
             }
# popularpeople
    artist = {"topartists": "LastFM: Top artists",
              }
    event = {}
    if True:
        listitems = merge_dicts(movie, tvshow, image, artist, event)
    keywords = [key for key in listitems.keys()]
    labels = [label for label in listitems.values()]
    ret = xbmcgui.Dialog().select(LANG(32151), labels)
    if ret > -1:
        notify(keywords[ret])
        set_skin_string("%s.path" % prefix, "plugin://script.extendedinfo?info=%s" % keywords[ret])
        set_skin_string("%s.label" % prefix, labels[ret])


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
            notify("%s (%i)" % (LANG(32158), base_age))
    return base_age


def get_playlist_stats(path):
    start_index = -1
    end_index = -1
    if (".xsp" in path) and ("special://" in path):
        start_index = path.find("special://")
        end_index = path.find(".xsp") + 4
    elif ("library://" in path):
        start_index = path.find("library://")
        end_index = path.rfind("/") + 1
    elif ("videodb://" in path):
        start_index = path.find("videodb://")
        end_index = path.rfind("/") + 1
    if (start_index > 0) and (end_index > 0):
        playlist_path = path[start_index:end_index]
        data = get_kodi_json(method="Files.GetDirectory",
                             params='{"directory": "%s", "media": "video", "properties": ["playcount", "resume"]}' % playlist_path)
        if "result" in data:
            played = 0
            in_progress = 0
            numitems = data["result"]["limits"]["total"]
            for item in data["result"]["files"]:
                if "playcount" in item:
                    if item["playcount"] > 0:
                        played += 1
                    if item["resume"]["position"] > 0:
                        in_progress += 1
            HOME.setProperty('PlaylistWatched', str(played))
            HOME.setProperty('PlaylistUnWatched', str(numitems - played))
            HOME.setProperty('PlaylistInProgress', str(in_progress))
            HOME.setProperty('PlaylistCount', str(numitems))


def get_sort_letters(path, focused_letter):
    """
    create string including all sortletters
    and put it into home window property "LetterList"
    """
    listitems = []
    letters = []
    HOME.clearProperty("LetterList")
    if SETTING("FolderPath") == path:
        letters = SETTING("LetterList").split()
    elif path:
        data = get_kodi_json(method="Files.GetDirectory",
                             params='{"directory": "%s", "media": "files"}' % path)
        if "result" in data and "files" in data["result"]:
            for movie in data["result"]["files"]:
                cleaned_label = movie["label"].replace("The ", "")
                if cleaned_label:
                    sortletter = cleaned_label[0]
                    if sortletter not in letters:
                        letters.append(sortletter)
        ADDON.setSetting("LetterList", " ".join(letters))
        ADDON.setSetting("FolderPath", path)
    HOME.setProperty("LetterList", "".join(letters))
    if not letters or not focused_letter:
        return None
    start_ord = ord("A")
    for i in range(0, 26):
        letter = chr(start_ord + i)
        if letter == focused_letter:
            label = "[B][COLOR FFFF3333]%s[/COLOR][/B]" % letter
        elif letter in letters:
            label = letter
        else:
            label = "[COLOR 55FFFFFF]%s[/COLOR]" % letter
        listitems.append({"label": label})
    return listitems


def millify(n):
    """
    make large numbers human-readable, return string
    """
    millnames = [' ', '.000', ' ' + LANG(32000), ' ' + LANG(32001), ' ' + LANG(32002)]
    if not n or n <= 100:
        return ""
    n = float(n)
    char_count = len(str(n))
    millidx = (char_count / 3) - 1
    if millidx == 3 or char_count == 9:
        return '%.2f%s' % (n / 10 ** (3 * millidx), millnames[millidx])
    else:
        return '%.0f%s' % (n / 10 ** (3 * millidx), millnames[millidx])


def media_streamdetails(filename, streamdetails):
    info = {}
    video = streamdetails['video']
    audio = streamdetails['audio']
    if video:
        if (video[0]['width'] <= 720 and video[0]['height'] <= 480):
            info['VideoResolution'] = "480"
        elif (video[0]['width'] <= 768 and video[0]['height'] <= 576):
            info['VideoResolution'] = "576"
        elif (video[0]['width'] <= 960 and video[0]['height'] <= 544):
            info['VideoResolution'] = "540"
        elif (video[0]['width'] <= 1280 and video[0]['height'] <= 720):
            info['VideoResolution'] = "720"
        elif (video[0]['width'] >= 1281 or video[0]['height'] >= 721):
            info['VideoResolution'] = "1080"
        else:
            info['videoresolution'] = ""
        info['VideoCodec'] = str(video[0]['codec'])
        if (video[0]['aspect'] < 1.4859):
            info['VideoAspect'] = "1.33"
        elif (video[0]['aspect'] < 1.7190):
            info['VideoAspect'] = "1.66"
        elif (video[0]['aspect'] < 1.8147):
            info['VideoAspect'] = "1.78"
        elif (video[0]['aspect'] < 2.0174):
            info['VideoAspect'] = "1.85"
        elif (video[0]['aspect'] < 2.2738):
            info['VideoAspect'] = "2.20"
        else:
            info['VideoAspect'] = "2.35"
    elif (('bluray' or 'blu-ray' or 'brrip' or 'bdrip' or 'hddvd' or 'hd-dvd') in filename):
        info['VideoResolution'] = '1080'
    elif ('dvd' in filename) or (filename.endswith('.vob' or '.ifo')):
        info['VideoResolution'] = '576'
    if audio:
        info['AudioCodec'] = audio[0]['codec']
        info['AudioChannels'] = audio[0]['channels']
    return info


def fetch(dictionary, key):
    if key in dictionary:
        if dictionary[key] is not None:
            return dictionary[key]
    return ""


def get_year(year_string):
    """
    return last 4 chars of string
    """
    if year_string and len(year_string) > 3:
        return year_string[:4]
    else:
        return ""


def fetch_musicbrainz_id(artist, artist_id=-1):
    """
    fetches MusicBrainz ID for given *artist and returns it
    uses musicbrainz.org
    """
    base_url = "http://musicbrainz.org/ws/2/artist/?fmt=json"
    url = '&query=artist:%s' % urllib.quote_plus(artist)
    results = get_JSON_response(url=base_url + url,
                                cache_days=30,
                                folder="MusicBrainz")
    if results and len(results["artists"]) > 0:
        log("found artist id for %s: %s" % (artist, results["artists"][0]["id"]))
        return results["artists"][0]["id"]
    else:
        return None


def get_http(url=None, headers=False):
    """
    fetches data from *url, returns it as a string
    """
    succeed = 0
    if not headers:
        headers = {'User-agent': 'XBMC/16.0 ( phil65@kodi.tv )'}
    request = urllib2.Request(url)
    for (key, value) in headers.iteritems():
        request.add_header(key, value)
    while (succeed < 2) and (not xbmc.abortRequested):
        try:
            response = urllib2.urlopen(request, timeout=3)
            return response.read()
        except:
            log("get_http: could not get data from %s" % url)
            xbmc.sleep(1000)
            succeed += 1
    return None


def get_JSON_response(url="", cache_days=7.0, folder=False, headers=False):
    """
    get JSON response for *url, makes use of prop and file cache.
    """
    now = time.time()
    hashed_url = hashlib.md5(url).hexdigest()
    if folder:
        cache_path = xbmc.translatePath(os.path.join(ADDON_DATA_PATH, folder))
    else:
        cache_path = xbmc.translatePath(os.path.join(ADDON_DATA_PATH))
    path = os.path.join(cache_path, hashed_url + ".txt")
    cache_seconds = int(cache_days * 86400.0)
    prop_time = HOME.getProperty(hashed_url + "_timestamp")
    if prop_time and now - float(prop_time) < cache_seconds:
        try:
            prop = json.loads(HOME.getProperty(hashed_url))
            log("prop load for %s. time: %f" % (url, time.time() - now))
            if prop:
                return prop
        except:
            log("could not load prop data for %s" % url)
    if xbmcvfs.exists(path) and ((now - os.path.getmtime(path)) < cache_seconds):
        results = read_from_file(path)
        log("loaded file for %s. time: %f" % (url, time.time() - now))
    else:
        response = get_http(url, headers)
        try:
            results = json.loads(response)
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
        HOME.setProperty(hashed_url + "_timestamp", str(now))
        HOME.setProperty(hashed_url, json.dumps(results))
        return results
    else:
        return []


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


class GetFileThread(threading.Thread):

    def __init__(self, url):
        threading.Thread.__init__(self)
        self.url = url

    def run(self):
        self.file = get_file(self.url)


def get_file(url):
    clean_url = xbmc.translatePath(urllib.unquote(url)).replace("image://", "")
    if clean_url.endswith("/"):
        clean_url = clean_url[:-1]
    cached_thumb = xbmc.getCacheThumbName(clean_url)
    vid_cache_file = os.path.join("special://profile/Thumbnails/Video", cached_thumb[0], cached_thumb)
    cache_file_jpg = os.path.join("special://profile/Thumbnails/", cached_thumb[0], cached_thumb[:-4] + ".jpg").replace("\\", "/")
    cache_file_png = cache_file_jpg[:-4] + ".png"
    if xbmcvfs.exists(cache_file_jpg):
        log("cache_file_jpg Image: " + url + "-->" + cache_file_jpg)
        return xbmc.translatePath(cache_file_jpg)
    elif xbmcvfs.exists(cache_file_png):
        log("cache_file_png Image: " + url + "-->" + cache_file_png)
        return cache_file_png
    elif xbmcvfs.exists(vid_cache_file):
        log("vid_cache_file Image: " + url + "-->" + vid_cache_file)
        return vid_cache_file
    try:
        request = urllib2.Request(url)
        request.add_header('Accept-encoding', 'gzip')
        response = urllib2.urlopen(request, timeout=3)
        data = response.read()
        response.close()
        log('image downloaded: ' + url)
    except:
        log('image download failed: ' + url)
        return ""
    if not data:
        return ""
    if url.endswith(".png"):
        image = cache_file_png
    else:
        image = cache_file_jpg
    try:
        with open(xbmc.translatePath(image), "wb") as f:
            f.write(data)
        return xbmc.translatePath(image)
    except:
        log('failed to save image ' + url)
        return ""


def get_favs_by_type(fav_type):
    """
    returns dict list containing favourites with type *fav_type
    """
    return [fav for fav in get_favs() if fav["Type"] == fav_type]


def get_fav_path(fav):
    if fav["type"] == "media":
        return "PlayMedia(%s)" % (fav["path"])
    elif fav["type"] == "script":
        return "RunScript(%s)" % (fav["path"])
    elif "window" in fav and "windowparameter" in fav:
        return "ActivateWindow(%s,%s)" % (fav["window"], fav["windowparameter"])
    else:
        log("error parsing favs")


def get_favs():
    """
    returns dict list containing favourites
    """
    items = []
    data = get_kodi_json(method="Favourites.GetFavourites",
                         params='{"type": null, "properties": ["path", "thumbnail", "window", "windowparameter"]}')
    if "result" not in data or data["result"]["limits"]["total"] == 0:
        return []
    for fav in data["result"]["favourites"]:
        path = get_fav_path(fav)
        items.append({'Label': fav["title"],
                      'thumb': fav["thumbnail"],
                      'Type': fav["type"],
                      'Builtin': path,
                      'path': "plugin://script.extendedinfo/?info=action&&id=" + path})
    return items


def get_icon_panel(number):
    """
    get icon panel with index *number, returns dict list based on skin strings
    """
    items = []
    offset = number * 5 - 5
    for i in range(1, 6):
        infopanel_path = get_skin_string("IconPanelItem%i.Path" % (i + offset))
        items.append({'Label': get_skin_string("IconPanelItem%i.Label" % (i + offset)),
                      'path': "plugin://script.extendedinfo/?info=action&&id=" + infopanel_path,
                      'thumb': get_skin_string("IconPanelItem%i.Icon" % (i + offset)),
                      'id': "IconPanelitem%i" % (i + offset),
                      'Type': get_skin_string("IconPanelItem%i.Type" % (i + offset))})
    return items


def get_skin_string(name):
    return xbmc.getInfoLabel("Skin.String(%s)").decode("utf-8")


def set_skin_string(name, value):
    xbmc.executebuiltin("Skin.SetString(%s, %s)" % (name, value))


def get_weather_images():
    items = []
    for i in range(1, 6):
        items.append({'Label': str(i),
                      'path': "plugin://script.extendedinfo/?info=action&&id=SetFocus(22222)",
                      'thumb': get_infolabel("Window(weather).Property(Map.%i.Area)" % i),
                      'Layer': get_infolabel("Window(weather).Property(Map.%i.Layer)" % i),
                      'Legend': get_infolabel("Window(weather).Property(Map.%i.Legend)" % i)})
    return items


def log(txt):
    if isinstance(txt, str):
        txt = txt.decode("utf-8", 'ignore')
    message = u'%s: %s' % (ADDON_ID, txt)
    xbmc.log(msg=message.encode("utf-8", 'ignore'),
             level=xbmc.LOGDEBUG)


def get_browse_dialog(default="", heading=LANG(1024), dlg_type=3, shares="files", mask="", use_thumbs=False, treat_as_folder=False):
    return xbmcgui.Dialog().browse(dlg_type, heading, shares, mask, use_thumbs, treat_as_folder, default)


def save_to_file(content, filename, path=""):
    """
    dump json and save to *filename in *path
    """
    if path == "":
        text_file_path = get_browse_dialog() + filename + ".txt"
    else:
        if not xbmcvfs.exists(path):
            xbmcvfs.mkdirs(path)
        text_file_path = os.path.join(path, filename + ".txt")
    now = time.time()
    text_file = xbmcvfs.File(text_file_path, "w")
    json.dump(content, text_file)
    text_file.close()
    log("saved textfile %s. Time: %f" % (text_file_path, time.time() - now))
    return True


def read_from_file(path="", raw=False):
    """
    return data from file with *path
    """
    if path == "":
        path = get_browse_dialog(dlg_type=1)
    if not xbmcvfs.exists(path):
        return False
    try:
        with open(path) as f:
            log("opened textfile %s." % (path))
            if not raw:
                result = json.load(f)
            else:
                result = f.read()
        return result
    except:
        log("failed to load textfile: " + path)
        return False


def convert_youtube_url(raw_string):
    youtube_id = extract_youtube_id(raw_string)
    if youtube_id:
        return 'plugin://script.extendedinfo/?info=youtubevideo&&id=%s' % youtube_id
    return ""


def extract_youtube_id(raw_string):
    vid_ids = None
    if raw_string and 'youtube.com/v' in raw_string:
        vid_ids = re.findall('http://www.youtube.com/v/(.{11})\??', raw_string, re.DOTALL)
    elif raw_string and 'youtube.com/watch' in raw_string:
        vid_ids = re.findall('youtube.com/watch\?v=(.{11})\??', raw_string, re.DOTALL)
    if vid_ids:
        return vid_ids[0]
    else:
        return ""


def notify(header="", message="", icon=ADDON_ICON, time=5000, sound=True):
    xbmcgui.Dialog().notification(heading=header,
                                  message=message,
                                  icon=icon,
                                  time=time,
                                  sound=sound)


def get_kodi_json(method, params):
    json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "%s", "params": %s, "id": 1}' % (method, params))
    json_query = unicode(json_query, 'utf-8', errors='ignore')
    return json.loads(json_query)


def prettyprint(string):
    log(json.dumps(string,
                   sort_keys=True,
                   indent=4,
                   separators=(',', ': ')))


def pass_dict_to_skin(data=None, prefix="", debug=False, precache=False, window_id=10000):
    window = xbmcgui.Window(window_id)
    if not data:
        return None
    threads = []
    image_requests = []
    for (key, value) in data.iteritems():
        if not value:
            continue
        value = unicode(value)
        if precache:
            if value.startswith("http") and value.endswith((".jpg", ".png")):
                if value not in image_requests and value:
                    thread = GetFileThread(value)
                    threads += [thread]
                    thread.start()
                    image_requests.append(value)
        window.setProperty('%s%s' % (prefix, key), value)
        if debug:
            log('%s%s' % (prefix, key) + value)
    for x in threads:
        x.join()


def merge_dict_lists(items, key="job"):
    crew_ids = []
    crews = []
    for item in items:
        if item["id"] not in crew_ids:
            crew_ids.append(item["id"])
            crews.append(item)
        else:
            index = crew_ids.index(item["id"])
            if key in crews[index]:
                crews[index][key] = crews[index][key] + " / " + item[key]
    return crews


def pass_list_to_skin(name="", data=[], prefix="", handle=None, limit=False):
    if data and limit and int(limit) < len(data):
        data = data[:int(limit)]
    if not handle:
        set_window_props(name, data, prefix)
        return None
    HOME.clearProperty(name)
    if data:
        HOME.setProperty(name + ".Count", str(len(data)))
        items = create_listitems(data)
        items = [(i.getProperty("path"), i, bool(i.getProperty("directory"))) for i in items]
        xbmcplugin.addDirectoryItems(handle=handle,
                                     items=items,
                                     totalItems=len(items))
    xbmcplugin.endOfDirectory(handle)


def set_window_props(name, data, prefix="", debug=False):
    if not data:
        HOME.setProperty('%s%s.Count' % (prefix, name), '0')
        log("%s%s.Count = None" % (prefix, name))
        return None
    for (count, result) in enumerate(data):
        if debug:
            log("%s%s.%i = %s" % (prefix, name, count + 1, str(result)))
        for (key, value) in result.iteritems():
            value = unicode(value)
            HOME.setProperty('%s%s.%i.%s' % (prefix, name, count + 1, str(key)), value)
            if key.lower() in ["poster", "banner", "fanart", "clearart", "clearlogo", "landscape",
                               "discart", "characterart", "tvshow.fanart", "tvshow.poster",
                               "tvshow.banner", "tvshow.clearart", "tvshow.characterart"]:
                HOME.setProperty('%s%s.%i.Art(%s)' % (prefix, name, count + 1, str(key)), value)
            if debug:
                log('%s%s.%i.%s --> ' % (prefix, name, count + 1, str(key)) + value)
    HOME.setProperty('%s%s.Count' % (prefix, name), str(len(data)))


def create_listitems(data=None, preload_images=0):
    INT_INFOLABELS = ["year", "episode", "season", "top250", "tracknumber", "playcount", "overlay"]
    FLOAT_INFOLABELS = ["rating"]
    STRING_INFOLABELS = ["genre", "director", "mpaa", "plot", "plotoutline", "title", "originaltitle",
                         "sorttitle", "duration", "studio", "tagline", "writer", "tvshowtitle", "premiered",
                         "status", "code", "aired", "credits", "lastplayed", "album", "votes", "trailer", "dateadded", "mediatype"]
    if not data:
        return []
    itemlist = []
    threads = []
    image_requests = []
    for (count, result) in enumerate(data):
        listitem = xbmcgui.ListItem('%s' % (str(count)))
        for (key, value) in result.iteritems():
            if not value:
                continue
            value = unicode(value)
            if count < preload_images:
                if value.startswith("http://") and value.endswith((".jpg", ".png")):
                    if value not in image_requests:
                        thread = GetFileThread(value)
                        threads += [thread]
                        thread.start()
                        image_requests.append(value)
            if key.lower() in ["name", "label"]:
                listitem.setLabel(value)
            elif key.lower() in ["label2"]:
                listitem.setLabel2(value)
            elif key.lower() in ["title"]:
                listitem.setLabel(value)
                listitem.setInfo('video', {key.lower(): value})
            elif key.lower() in ["thumb"]:
                listitem.setThumbnailImage(value)
                listitem.setArt({key.lower(): value})
            elif key.lower() in ["icon"]:
                listitem.setIconImage(value)
                listitem.setArt({key.lower(): value})
            elif key.lower() in ["path"]:
                listitem.setPath(path=value)
                # listitem.setProperty('%s' % (key), value)
            # elif key.lower() in ["season", "episode"]:
            #     listitem.setInfo('video', {key.lower(): int(value)})
            #     listitem.setProperty('%s' % (key), value)
            elif key.lower() in ["poster", "banner", "fanart", "clearart", "clearlogo", "landscape",
                                 "discart", "characterart", "tvshow.fanart", "tvshow.poster",
                                 "tvshow.banner", "tvshow.clearart", "tvshow.characterart"]:
                listitem.setArt({key.lower(): value})
            elif key.lower() in INT_INFOLABELS:
                try:
                    listitem.setInfo('video', {key.lower(): int(value)})
                except:
                    pass
            elif key.lower() in STRING_INFOLABELS:
                listitem.setInfo('video', {key.lower(): value})
            elif key.lower() in FLOAT_INFOLABELS:
                try:
                    listitem.setInfo('video', {key.lower(): "%1.1f" % float(value)})
                except:
                    pass
            # else:
            listitem.setProperty('%s' % (key), value)
        listitem.setProperty("index", str(count))
        itemlist.append(listitem)
    for x in threads:
        x.join()
    return itemlist


def clean_text(text):
    if not text:
        return ""
    text = re.sub('(From Wikipedia, the free encyclopedia)|(Description above from the Wikipedia.*?Wikipedia)', '', text)
    text = re.sub('<(.|\n|\r)*?>', '', text)
    text = text.replace('<br \/>', '[CR]')
    text = text.replace('<em>', '[I]').replace('</em>', '[/I]')
    text = text.replace('&amp;', '&')
    text = text.replace('&gt;', '>').replace('&lt;', '<')
    text = text.replace('&#39;', "'").replace('&quot;', '"')
    text = re.sub("\n\\.$", "", text)
    text = text.replace('User-contributed text is available under the Creative Commons By-SA License and may also be available under the GNU FDL.', '')
    while text:
        s = text[0]
        e = text[-1]
        if s in [u'\u200b', " ", "\n"]:
            text = text[1:]
        elif e in [u'\u200b', " ", "\n"]:
            text = text[:-1]
        elif s.startswith(".") and not s.startswith(".."):
            text = text[1:]
        else:
            break
    return text.strip()
