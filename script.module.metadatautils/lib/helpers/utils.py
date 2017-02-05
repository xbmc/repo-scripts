#!/usr/bin/python
# -*- coding: utf-8 -*-

'''Various generic helper methods'''

import xbmcgui
import xbmc
import xbmcvfs
import sys
from traceback import format_exc
import requests
import arrow
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import urllib
import unicodedata
import os

try:
    import simplejson as json
except Exception:
    import json

try:
    from multiprocessing.pool import ThreadPool
    SUPPORTS_POOL = True
except Exception:
    SUPPORTS_POOL = False


ADDON_ID = "script.module.metadatautils"
KODI_LANGUAGE = xbmc.getLanguage(xbmc.ISO_639_1)
if not KODI_LANGUAGE:
    KODI_LANGUAGE = "en"
KODI_VERSION = int(xbmc.getInfoLabel("System.BuildVersion").split(".")[0])

# setup requests with some additional options
requests.packages.urllib3.disable_warnings()
SESSION = requests.Session()
RETRIES = Retry(total=5, backoff_factor=2, status_forcelist=[500, 502, 503, 504])
SESSION.mount('http://', HTTPAdapter(max_retries=RETRIES))
SESSION.mount('https://', HTTPAdapter(max_retries=RETRIES))


def log_msg(msg, loglevel=xbmc.LOGDEBUG):
    '''log message to kodi logfile'''
    if isinstance(msg, unicode):
        msg = msg.encode('utf-8')
    xbmc.log("Metadata and Artwork module --> %s" % msg, level=loglevel)


def log_exception(modulename, exceptiondetails):
    '''helper to properly log an exception'''
    log_msg(format_exc(sys.exc_info()), xbmc.LOGWARNING)
    log_msg("ERROR in %s ! --> %s" % (modulename, exceptiondetails), xbmc.LOGERROR)


def get_json(url, params=None, retries=0):
    '''get info from a rest api'''
    result = {}
    if not params:
        params = {}
    try:
        response = requests.get(url, params=params, timeout=20)
        if response and response.content and response.status_code == 200:
            result = json.loads(response.content.decode('utf-8', 'replace'))
            if "results" in result:
                result = result["results"]
            elif "result" in result:
                result = result["result"]
        elif response.status_code == 503:
            result = None
    except Exception as exc:
        if "Read timed out" in str(exc):
            result = None
        else:
            log_exception(__name__, exc)
            return None
    # auto retry connection errors
    if result is None and retries < 5:
        xbmc.sleep(500 * retries)
        return get_json(url, params, retries + 1)
    # return result
    return result


def try_encode(text, encoding="utf-8"):
    '''helper to encode a string to utf-8'''
    try:
        return text.encode(encoding, "ignore")
    except Exception:
        return text


def try_decode(text, encoding="utf-8"):
    '''helper to decode a string to unicode'''
    try:
        return text.decode(encoding, "ignore")
    except Exception:
        return text


def urlencode(text):
    '''helper to properly urlencode a string'''
    blah = urllib.urlencode({'blahblahblah': try_encode(text)})
    blah = blah[13:]
    return blah


def formatted_number(number):
    '''try to format a number to formatted string with thousands'''
    try:
        number = int(number)
        if number < 0:
            return '-' + formatted_number(-number)
        result = ''
        while number >= 1000:
            number, number2 = divmod(number, 1000)
            result = ",%03d%s" % (number2, result)
        return "%d%s" % (number, result)
    except Exception:
        return ""


def process_method_on_list(method_to_run, items):
    '''helper method that processes a method on each listitem with pooling if the system supports it'''
    all_items = []
    if SUPPORTS_POOL:
        pool = ThreadPool()
        try:
            all_items = pool.map(method_to_run, items)
        except Exception:
            # catch exception to prevent threadpool running forever
            log_msg(format_exc(sys.exc_info()))
            log_msg("Error in %s" % method_to_run)
        pool.close()
        pool.join()
    else:
        all_items = [method_to_run(item) for item in items]
    all_items = filter(None, all_items)
    return all_items


def get_clean_image(image):
    '''helper to strip all kodi tags/formatting of an image path/url'''
    if not image:
        return ""
    if "music@" in image:
        # fix for embedded images
        thumbcache = xbmc.getCacheThumbName(image).replace(".tbn", ".jpg")
        thumbcache = "special://thumbnails/%s/%s" % (thumbcache[0], thumbcache)
        if not xbmcvfs.exists(thumbcache):
            xbmcvfs.copy(image, thumbcache)
        image = thumbcache
    if image and "image://" in image:
        image = image.replace("image://", "")
        image = urllib.unquote(image.encode("utf-8"))
        if image.endswith("/"):
            image = image[:-1]
    if not isinstance(image, unicode):
        image = image.decode("utf8")
    return image


def get_duration(duration):
    '''transform duration time in minutes to hours:minutes'''
    if not duration:
        return {}
    if isinstance(duration, (unicode, str)):
        duration.replace("min", "").replace("", "").replace(".", "")
    try:
        total_minutes = int(duration)
        if total_minutes < 60:
            hours = 0
        else:
            hours = total_minutes / 60
        minutes = total_minutes - (hours * 60)
        formatted_time = "%s:%s" % (hours, str(minutes).zfill(2))
    except Exception as exc:
        log_exception(__name__, exc)
        return {}
    return {
        "Duration": formatted_time,
        "Duration.Hours": hours,
        "Duration.Minutes": minutes,
        "Runtime": total_minutes,
        "RuntimeExtended": "%s %s" % (total_minutes, xbmc.getLocalizedString(12391)),
        "DurationAndRuntime": "%s (%s min.)" % (formatted_time, total_minutes),
        "DurationAndRuntimeExtended": "%s (%s %s)" % (formatted_time, total_minutes, xbmc.getLocalizedString(12391))
    }


def int_with_commas(number):
    '''helper to pretty format a number'''
    try:
        number = int(number)
        if number < 0:
            return '-' + int_with_commas(-number)
        result = ''
        while number >= 1000:
            number, number2 = divmod(number, 1000)
            result = ",%03d%s" % (number2, result)
        return "%d%s" % (number, result)
    except Exception:
        return ""


def try_parse_int(string):
    '''helper to parse int from string without erroring on empty or misformed string'''
    try:
        return int(string)
    except Exception:
        return 0


def extend_dict(org_dict, new_dict, allow_overwrite=None):
    '''Create a new dictionary with a's properties extended by b,
    without overwriting existing values.'''
    if not new_dict:
        return org_dict
    for key, value in new_dict.iteritems():
        if value:
            if not org_dict.get(key):
                # orginal dict doesn't has this key (or no value), just overwrite
                org_dict[key] = value
            else:
                # original dict already has this key, append results
                if isinstance(value, list):
                    # make sure that our original value also is a list
                    if isinstance(org_dict[key], list):
                        for item in value:
                            if item not in org_dict[key]:
                                org_dict[key].append(item)
                    # previous value was str, combine both in list
                    elif isinstance(org_dict[key], (str, unicode)):
                        org_dict[key] = org_dict[key].split(" / ")
                        for item in value:
                            if item not in org_dict[key]:
                                org_dict[key].append(item)
                elif isinstance(value, dict):
                    org_dict[key] = extend_dict(org_dict[key], value, allow_overwrite)
                elif allow_overwrite and key in allow_overwrite:
                    # value may be overwritten
                    org_dict[key] = value
                else:
                    # conflict, leave alone
                    pass
    return org_dict


def localdate_from_utc_string(timestring):
    '''helper to convert internal utc time (used in pvr) to local timezone'''
    utc_datetime = arrow.get(timestring)
    local_datetime = utc_datetime.to('local')
    return local_datetime.format("YYYY-MM-DD HH:mm:ss")


def localized_date_time(timestring):
    '''returns localized version of the timestring (used in pvr)'''
    date_time = arrow.get(timestring)
    local_date = date_time.strftime(xbmc.getRegion("dateshort"))
    local_time = date_time.strftime(xbmc.getRegion("time").replace(":%S", ""))
    return (local_date, local_time)


def normalize_string(text):
    '''normalize string, strip all special chars'''
    text = text.replace(":", "")
    text = text.replace("/", "-")
    text = text.replace("\\", "-")
    text = text.replace("<", "")
    text = text.replace(">", "")
    text = text.replace("*", "")
    text = text.replace("?", "")
    text = text.replace('|', "")
    text = text.replace('(', "")
    text = text.replace(')', "")
    text = text.replace("\"", "")
    text = text.strip()
    text = text.rstrip('.')
    text = unicodedata.normalize('NFKD', try_decode(text))
    return text


def get_compare_string(text):
    '''strip all special chars in a string for better comparing of searchresults'''
    if not isinstance(text, unicode):
        text.decode("utf-8")
    text = text.lower()
    text = ''.join(e for e in text if e.isalnum())
    return text


def strip_newlines(text):
    '''strip any newlines from a string'''
    return text.replace('\n', ' ').replace('\r', '').rstrip()


def detect_plugin_content(plugin_path):
    '''based on the properties of a vfspath we try to detect the content type'''
    content_type = ""
    if not plugin_path:
        return ""
    # detect content based on the path
    if "listing" in plugin_path:
        content_type = "folder"
    elif "movie" in plugin_path.lower():
        content_type = "movies"
    elif "album" in plugin_path.lower():
        content_type = "albums"
    elif "show" in plugin_path.lower():
        content_type = "tvshows"
    elif "episode" in plugin_path.lower():
        content_type = "episodes"
    elif "song" in plugin_path.lower():
        content_type = "songs"
    elif "musicvideo" in plugin_path.lower():
        content_type = "musicvideos"
    elif "pvr" in plugin_path.lower():
        content_type = "pvr"
    elif "type=dynamic" in plugin_path.lower():
        content_type = "movies"
    elif "videos" in plugin_path.lower():
        content_type = "movies"
    elif "type=both" in plugin_path.lower():
        content_type = "movies"
    elif "media" in plugin_path.lower():
        content_type = "movies"
    elif "favourites" in plugin_path.lower():
        content_type = "movies"
    elif ("box" in plugin_path.lower() or "dvd" in plugin_path.lower() or
          "rentals" in plugin_path.lower() or "incinemas" in plugin_path.lower() or
          "comingsoon" in plugin_path.lower() or "upcoming" in plugin_path.lower() or
          "opening" in plugin_path.lower() or "intheaters" in plugin_path.lower()):
        content_type = "movies"
    # if we didn't get the content based on the path, we need to probe the addon...
    if not content_type and not xbmc.getCondVisibility("Window.IsMedia"):  # safety check
        from kodidb import KodiDb
        media_array = KodiDb().files(plugin_path, limits=(0, 1))
        for item in media_array:
            if item.get("filetype", "") == "directory":
                content_type = "folder"
                break
            elif item.get("type") and item["type"] != "unknown":
                content_type = item["type"] + "s"
                break
            elif "showtitle" not in item and "artist" not in item:
                # these properties are only returned in the json response if we're looking at actual file content...
                # if it's missing it means this is a main directory listing and no need to
                # scan the underlying listitems.
                content_type = "files"
                break
            if "showtitle" not in item and "artist" in item:
                # AUDIO ITEMS
                if item["type"] == "artist":
                    content_type = "artists"
                    break
                elif (isinstance(item["artist"], list) and len(item["artist"]) > 0 and
                      item["artist"][0] == item["title"]):
                    content_type = "artists"
                    break
                elif item["type"] == "album" or item["album"] == item["title"]:
                    content_type = "albums"
                    break
                elif ((item["type"] == "song" and "play_album" not in item["file"]) or
                      (item["artist"] and item["album"])):
                    content_type = "songs"
                    break
            else:
                # VIDEO ITEMS
                if item["showtitle"] and not item.get("artist"):
                    # this is a tvshow, episode or season...
                    if item["type"] == "season" or (item["season"] > -1 and item["episode"] == -1):
                        content_type = "seasons"
                        break
                    elif item["type"] == "episode" or item["season"] > -1 and item["episode"] > -1:
                        content_type = "episodes"
                        break
                    else:
                        content_type = "tvshows"
                        break
                elif item.get("artist"):
                    # this is a musicvideo!
                    content_type = "musicvideos"
                    break
                elif (item["type"] == "movie" or item.get("imdbnumber") or item.get("mpaa") or
                      item.get("trailer") or item.get("studio")):
                    content_type = "movies"
                    break
        log_msg("detect_plugin_path_content for: %s  - result: %s" % (plugin_path, content_type))
    return content_type


def download_artwork(folderpath, artwork):
    '''download artwork to local folder'''
    efa_path = ""
    new_dict = {}
    if not xbmcvfs.exists(folderpath):
        xbmcvfs.mkdir(folderpath)
    for key, value in artwork.iteritems():
        if key == "fanart":
            new_dict[key] = download_image(os.path.join(folderpath, "fanart.jpg"), value)
        elif key == "thumb":
            new_dict[key] = download_image(os.path.join(folderpath, "folder.jpg"), value)
        elif key == "discart":
            new_dict[key] = download_image(os.path.join(folderpath, "disc.png"), value)
        elif key == "banner":
            new_dict[key] = download_image(os.path.join(folderpath, "banner.jpg"), value)
        elif key == "clearlogo":
            new_dict[key] = download_image(os.path.join(folderpath, "logo.png"), value)
        elif key == "clearart":
            new_dict[key] = download_image(os.path.join(folderpath, "clearart.png"), value)
        elif key == "characterart":
            new_dict[key] = download_image(os.path.join(folderpath, "characterart.png"), value)
        elif key == "poster":
            new_dict[key] = download_image(os.path.join(folderpath, "poster.jpg"), value)
        elif key == "landscape":
            new_dict[key] = download_image(os.path.join(folderpath, "landscape.jpg"), value)
        elif key == "fanarts" and value:
            # copy extrafanarts only if the directory doesn't exist at all
            delim = "\\" if "\\" in folderpath else "/"
            efa_path = "%sextrafanart" % folderpath + delim
            if not xbmcvfs.exists(efa_path):
                xbmcvfs.mkdir(efa_path)
                images = []
                for count, image in enumerate(value):
                    image = download_image(os.path.join(efa_path, "fanart%s.jpg" % count), image)
                    images.append(image)
                new_dict[key] = images
        else:
            new_dict[key] = value
    if efa_path:
        new_dict["extrafanart"] = efa_path
    return new_dict


def download_image(filename, url):
    '''download specific image to local folder'''
    if not url:
        return url
    refresh_needed = False
    if xbmcvfs.exists(filename) and filename == url:
        # only overwrite if new image is different
        return filename
    else:
        if xbmcvfs.exists(filename):
            xbmcvfs.delete(filename)
            refresh_needed = True
        if xbmcvfs.copy(url, filename):
            if refresh_needed:
                refresh_image(filename)
            return filename

    return url


def refresh_image(imagepath):
    '''tell kodi texture cache to refresh a particular image'''
    import sqlite3
    dbpath = xbmc.translatePath("special://database/Textures13.db").decode('utf-8')
    connection = sqlite3.connect(dbpath, timeout=30, isolation_level=None)
    try:
        cache_image = connection.execute('SELECT cachedurl FROM texture WHERE url = ?', (imagepath,)).fetchone()
        if cache_image and isinstance(cache_image, (unicode, str)):
            if xbmcvfs.exists(cache_image):
                xbmcvfs.delete("special://profile/Thumbnails/%s" % cache_image)
            connection.execute('DELETE FROM texture WHERE url = ?', (imagepath,))
        connection.close()
    except Exception as exc:
        log_exception(__name__, exc)
    finally:
        del connection

# pylint: disable-msg=too-many-local-variables


def manual_set_artwork(artwork, mediatype, header=None):
    '''Allow user to manually select the artwork with a select dialog'''
    changemade = False
    if mediatype == "artist":
        art_types = ["thumb", "poster", "fanart", "banner", "clearart", "clearlogo", "landscape"]
    elif mediatype == "album":
        art_types = ["thumb", "discart"]
    else:
        art_types = ["thumb", "poster", "fanart", "banner", "clearart",
                     "clearlogo", "discart", "landscape", "characterart"]

    if not header:
        header = xbmc.getLocalizedString(13511)

    # show dialogselect with all artwork options
    abort = False
    while not abort:
        listitems = []
        for arttype in art_types:
            img = artwork.get(arttype, "")
            listitem = xbmcgui.ListItem(label=arttype, label2=img, iconImage=img)
            listitem.setProperty("icon", img)
            listitems.append(listitem)
        dialog = DialogSelect("DialogSelect.xml", "", listing=listitems,
                              window_title=header, multiselect=False)
        dialog.doModal()
        selected_item = dialog.result
        del dialog
        if selected_item == -1:
            abort = True
        else:
            # show results for selected art type
            artoptions = []
            selected_item = listitems[selected_item]
            image = selected_item.getProperty("icon").decode("utf-8")
            label = selected_item.getLabel().decode("utf-8")
            subheader = "%s: %s" % (header, label)
            if image:
                # current image
                listitem = xbmcgui.ListItem(label=xbmc.getLocalizedString(13512), iconImage=image, label2=image)
                listitem.setProperty("icon", image)
                artoptions.append(listitem)
                # none option
                listitem = xbmcgui.ListItem(label=xbmc.getLocalizedString(231), iconImage="DefaultAddonNone.png")
                listitem.setProperty("icon", "DefaultAddonNone.png")
                artoptions.append(listitem)
            # browse option
            listitem = xbmcgui.ListItem(label=xbmc.getLocalizedString(1024), iconImage="DefaultFolder.png")
            listitem.setProperty("icon", "DefaultFolder.png")
            artoptions.append(listitem)

            # add remaining images as option
            allarts = artwork.get(label + "s", [])
            for item in allarts:
                listitem = xbmcgui.ListItem(label=item, iconImage=item)
                listitem.setProperty("icon", item)
                artoptions.append(listitem)

            dialog = DialogSelect("DialogSelect.xml", "", listing=artoptions, window_title=subheader)
            dialog.doModal()
            selected_item = dialog.result
            del dialog
            if image and selected_item == 1:
                # set image to None
                artwork[label] = ""
                changemade = True
            elif (image and selected_item > 2) or (not image and selected_item > 0):
                # one of the optional images is selected as new default
                artwork[label] = artoptions[selected_item].getProperty("icon")
                changemade = True
            elif (image and selected_item == 2) or (not image and selected_item == 0):
                # manual browse...
                dialog = xbmcgui.Dialog()
                image = dialog.browse(2, xbmc.getLocalizedString(1030),
                                      'files', mask='.gif|.png|.jpg').decode("utf-8")
                del dialog
                if image:
                    artwork[label] = image
                    changemade = True

    # return endresult
    return changemade, artwork

# pylint: enable-msg=too-many-local-variables


class DialogSelect(xbmcgui.WindowXMLDialog):
    '''wrapper around Kodi dialogselect to present a list of items'''

    list_control = None

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self)
        self.listing = kwargs.get("listing")
        self.window_title = kwargs.get("window_title", "")
        self.result = -1

    def onInit(self):
        '''called when the dialog is drawn'''
        self.list_control = self.getControl(6)
        self.getControl(1).setLabel(self.window_title)
        self.getControl(3).setVisible(False)
        try:
            self.getControl(7).setLabel(xbmc.getLocalizedString(222))
        except Exception:
            pass

        self.getControl(5).setVisible(False)

        # add our items to the listing  and focus the control
        self.list_control.addItems(self.listing)
        self.setFocus(self.list_control)

    def onAction(self, action):
        '''On kodi action'''
        if action.getId() in (9, 10, 92, 216, 247, 257, 275, 61467, 61448, ):
            self.result = -1
            self.close()

    def onClick(self, control_id):
        '''Triggers if our dialog is clicked'''
        if control_id in (6, 3,):
            num = self.list_control.getSelectedPosition()
            self.result = num
        else:
            self.result = -1
        self.close()
