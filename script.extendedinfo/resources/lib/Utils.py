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
import simplejson
import re
import threading
import datetime

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_ICON = ADDON.getAddonInfo('icon')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_PATH = ADDON.getAddonInfo('path').decode("utf-8")
ADDON_DATA_PATH = os.path.join(xbmc.translatePath("special://profile/addon_data/%s" % ADDON_ID).decode("utf-8"))
HOME = xbmcgui.Window(10000)
global windowstack
windowstack = []


def dictfind(lst, key, value):
    for i, dic in enumerate(lst):
        if dic[key] == value:
            return dic
    return ""


def url_quote(url):
    try:
        url = urllib.quote_plus(url.encode('utf8', 'ignore'))
    except:
        url = urllib.quote_plus(unicode(url, "utf-8").encode("utf-8"))
    return url


class TextViewer_Dialog(xbmcgui.WindowXMLDialog):
    ACTION_PREVIOUS_MENU = [9, 92, 10]

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self)
        self.text = kwargs.get('text')
        self.header = kwargs.get('header')
        self.color = kwargs.get('color')

    def onInit(self):
        windowid = xbmcgui.getCurrentWindowDialogId()
        xbmcgui.Window(windowid).setProperty("WindowColor", self.color)
        self.getControl(1).setLabel(self.header)
        self.getControl(5).setText(self.text)

    def onAction(self, action):
        if action in self.ACTION_PREVIOUS_MENU:
            self.close()

    def onClick(self, controlID):
        pass

    def onFocus(self, controlID):
        pass


class SlideShow(xbmcgui.WindowXMLDialog):
    ACTION_PREVIOUS_MENU = [9, 92, 10]
    ACTION_LEFT = [1]
    ACTION_RIGHT = [2]

    def __init__(self, *args, **kwargs):
        self.imagelist = kwargs.get('imagelist')
        self.index = kwargs.get('index')
        self.image = kwargs.get('image')
        self.action = None

    def onInit(self):
        if self.imagelist:
            self.getControl(10000).addItems(create_listitems(self.imagelist))
            xbmc.executebuiltin("Control.SetFocus(10000,%s)" % self.index)
        else:
            listitem = {"label": self.image,
                        "Thumb": self.image}
            self.getControl(10000).addItems(create_listitems([listitem]))

    def onAction(self, action):
        if action in self.ACTION_PREVIOUS_MENU:
            self.close()
        elif action in self.ACTION_LEFT:
            self.action = "left"
            self.close()
        elif action in self.ACTION_RIGHT:
            self.action = "right"
            self.close()


def calculate_age(born, died=False):
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
            Notify("%s (%i)" % (ADDON.getLocalizedString(32158), base_age))
    return base_age


def play_trailer(youtube_id="", listitem=None, popstack=False):
    if not listitem:
        listitem = xbmcgui.ListItem(xbmc.getLocalizedString(20410))
        listitem.setInfo('video', {'Title': xbmc.getLocalizedString(20410), 'Genre': 'Youtube Video'})
    import YDStreamExtractor
    YDStreamExtractor.disableDASHVideo(True)
    vid = YDStreamExtractor.getVideoInfo(youtube_id, quality=1)
    if vid:
        stream_url = vid.streamURL()
        PlayMedia(stream_url, listitem, popstack)


def PlayMedia(path="", listitem=None, popstack=False):
    player = VideoPlayer(popstack=popstack)
    player.play(item=path, listitem=listitem)


class VideoPlayer(xbmc.Player):

    def __init__(self, *args, **kwargs):
        xbmc.Player.__init__(self)
        self.stopped = False
        self.popstack = kwargs.get("popstack", True)

    def onPlayBackEnded(self):
        self.stopped = True

    def onPlayBackStopped(self):
        self.stopped = True

    def onPlayBackStarted(self):
        self.stopped = False

    def playYoutubeVideo(self, youtube_id="", listitem=None, popstack=True):
        if not listitem:
            listitem = xbmcgui.ListItem(xbmc.getLocalizedString(20410))
            listitem.setInfo('video', {'Title': xbmc.getLocalizedString(20410), 'Genre': 'Youtube Video'})
        import YDStreamExtractor
        YDStreamExtractor.disableDASHVideo(True)
        if youtube_id:
            vid = YDStreamExtractor.getVideoInfo(youtube_id, quality=1)
            if vid:
                stream_url = vid.streamURL()
                self.play(stream_url, listitem)
        else:
            Notify("no youtube id found")

    def wait_for_video_end(self):
        while not self.stopped:
            xbmc.sleep(200)
        self.stopped = False


def AddToWindowStack(window):
    windowstack.append(window)


def PopWindowStack():
    if windowstack:
        dialog = windowstack.pop()
        dialog.doModal()


def GetPlaylistStats(path):
    startindex = -1
    endindex = -1
    if (".xsp" in path) and ("special://" in path):
        startindex = path.find("special://")
        endindex = path.find(".xsp") + 4
    elif ("library://" in path):
        startindex = path.find("library://")
        endindex = path.rfind("/") + 1
    elif ("videodb://" in path):
        startindex = path.find("videodb://")
        endindex = path.rfind("/") + 1
    if (startindex > 0) and (endindex > 0):
        playlistpath = path[startindex:endindex]
    #    Notify(playlistpath)
    #   json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"filter": {"field": "path", "operator": "contains", "value": "%s"}, "properties": ["playcount", "resume"]}, "id": 1}' % (playlistpath))
        json_response = get_Kodi_JSON('"method": "Files.GetDirectory", "params": {"directory": "%s", "media": "video", "properties": ["playcount", "resume"]}' % playlistpath)
        if "result" in json_response:
            played = 0
            inprogress = 0
            numitems = json_response["result"]["limits"]["total"]
            for item in json_response["result"]["files"]:
                if "playcount" in item:
                    if item["playcount"] > 0:
                        played += 1
                    if item["resume"]["position"] > 0:
                        inprogress += 1
            HOME.setProperty('PlaylistWatched', str(played))
            HOME.setProperty('PlaylistUnWatched', str(numitems - played))
            HOME.setProperty('PlaylistInProgress', str(inprogress))
            HOME.setProperty('PlaylistCount', str(numitems))


def GetSortLetters(path, focusedletter):
    listitems = []
    letterlist = []
    HOME.clearProperty("LetterList")
    if ADDON.getSetting("FolderPath") == path:
        letterlist = ADDON.getSetting("LetterList")
        letterlist = letterlist.split()
    else:
        if path:
            json_response = get_Kodi_JSON('"method": "Files.GetDirectory", "params": {"directory": "%s", "media": "files"}' % path)
            if "result" in json_response and "files" in json_response["result"]:
                for movie in json_response["result"]["files"]:
                    cleaned_label = movie["label"].replace("The ", "")
                    if cleaned_label:
                        sortletter = cleaned_label[0]
                        if sortletter not in letterlist:
                            letterlist.append(sortletter)
            ADDON.setSetting("LetterList", " ".join(letterlist))
            ADDON.setSetting("FolderPath", path)
    HOME.setProperty("LetterList", "".join(letterlist))
    if letterlist and focusedletter:
        startord = ord("A")
        for i in range(0, 26):
            letter = chr(startord + i)
            if letter == focusedletter:
                label = "[B][COLOR FFFF3333]%s[/COLOR][/B]" % letter
            elif letter in letterlist:
                label = letter
            else:
                label = "[COLOR 55FFFFFF]%s[/COLOR]" % letter
            listitem = {"label": label}
            listitems.append(listitem)
    return listitems


def millify(n):
    millnames = [' ', '.000', ' Million', ' Billion', ' Trillion']
    if n and n > 100:
        n = float(n)
        char_count = len(str(n))
        millidx = (char_count / 3) - 1
        if millidx == 3 or char_count == 9:
            return '%.2f%s' % (n / 10 ** (3 * millidx), millnames[millidx])
        else:
            return '%.0f%s' % (n / 10 ** (3 * millidx), millnames[millidx])
    else:
        return ""


def media_streamdetails(filename, streamdetails):
    info = {}
    video = streamdetails['video']
    audio = streamdetails['audio']
    info['VideoCodec'] = ''
    info['VideoAspect'] = ''
    info['VideoResolution'] = ''
    info['AudioCodec'] = ''
    info['AudioChannels'] = ''
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
    elif (('dvd') in filename and not ('hddvd' or 'hd-dvd') in filename) or (filename.endswith('.vob' or '.ifo')):
        info['VideoResolution'] = '576'
    elif (('bluray' or 'blu-ray' or 'brrip' or 'bdrip' or 'hddvd' or 'hd-dvd') in filename):
        info['VideoResolution'] = '1080'
    if audio:
        info['AudioCodec'] = audio[0]['codec']
        info['AudioChannels'] = audio[0]['channels']
    return info


def fetch(dictionary, key):
    if key in dictionary:
        if dictionary[key] is not None:
            return dictionary[key]
    return ""


def fetch_musicbrainz_id(artist, xbmc_artist_id=-1):
    base_url = "http://musicbrainz.org/ws/2/artist/?fmt=json"
    url = '&query=artist:%s' % urllib.quote_plus(artist)
    results = Get_JSON_response(base_url + url, 30)
    if results and len(results["artists"]) > 0:
        mbid = results["artists"][0]["id"]
        log("found artist id for " + artist.decode("utf-8") + ": " + mbid)
        return mbid
    else:
        return None


def GetStringFromUrl(url=None, headers=False):
    succeed = 0
    if not headers:
        headers = {'User-agent': 'XBMC/14.0 ( phil65@kodi.tv )'}
    request = urllib2.Request(url)
    for (key, value) in headers.iteritems():
        request.add_header(key, value)
    while (succeed < 5) and (not xbmc.abortRequested):
        try:
            response = urllib2.urlopen(request)
            data = response.read()
            return data
        except:
            log("GetStringFromURL: could not get data from %s" % url)
            xbmc.sleep(1000)
            succeed += 1
    return None


def Get_JSON_response(url="", cache_days=7.0, folder=False, headers=False):
    now = time.time()
    hashed_url = hashlib.md5(url).hexdigest()
    path = xbmc.translatePath(os.path.join(ADDON_DATA_PATH, hashed_url + ".txt"))
    cache_seconds = int(cache_days * 86400.0)
    prop_time = HOME.getProperty(hashed_url + "_timestamp")
    if prop_time and now - float(prop_time) < cache_seconds:
        try:
            prop = simplejson.loads(HOME.getProperty(hashed_url))
            log("prop load for %s. time: %f" % (url, time.time() - now))
            return prop
        except:
            log("could not load prop data")
    if xbmcvfs.exists(path) and ((now - os.path.getmtime(path)) < cache_seconds):
        results = read_from_file(path)
        log("loaded file for %s. time: %f" % (url, time.time() - now))
    else:
        response = GetStringFromUrl(url, headers)
        try:
            results = simplejson.loads(response)
            log("download %s. time: %f" % (url, time.time() - now))
            save_to_file(results, hashed_url, ADDON_DATA_PATH)
        except:
            log("Exception: Could not get new JSON data. Tryin to fallback to cache")
            log(response)
            if xbmcvfs.exists(path):
                results = read_from_file(path)
            else:
                results = []
    HOME.setProperty(hashed_url + "_timestamp", str(now))
    HOME.setProperty(hashed_url, simplejson.dumps(results))
    return results


class Get_File_Thread(threading.Thread):

    def __init__(self, url):
        threading.Thread.__init__(self)
        self.url = url

    def run(self):
        self.file = Get_File(self.url)


def Get_File(url):
    clean_url = xbmc.translatePath(urllib.unquote(url)).replace("image://", "")
    if clean_url.endswith("/"):
        clean_url = clean_url[:-1]
    cachedthumb = xbmc.getCacheThumbName(clean_url)
    xbmc_vid_cache_file = os.path.join("special://profile/Thumbnails/Video", cachedthumb[0], cachedthumb)
    xbmc_cache_file_jpg = os.path.join("special://profile/Thumbnails/", cachedthumb[0], cachedthumb[:-4] + ".jpg").replace("\\", "/")
    xbmc_cache_file_png = xbmc_cache_file_jpg[:-4] + ".png"
    if xbmcvfs.exists(xbmc_cache_file_jpg):
        log("xbmc_cache_file_jpg Image: " + url + "-->" + xbmc_cache_file_jpg)
        return xbmc.translatePath(xbmc_cache_file_jpg)
    elif xbmcvfs.exists(xbmc_cache_file_png):
        log("xbmc_cache_file_png Image: " + url + "-->" + xbmc_cache_file_png)
        return xbmc_cache_file_png
    elif xbmcvfs.exists(xbmc_vid_cache_file):
        log("xbmc_vid_cache_file Image: " + url + "-->" + xbmc_vid_cache_file)
        return xbmc_vid_cache_file
    else:
        try:
            request = urllib2.Request(url)
            request.add_header('Accept-encoding', 'gzip')
            response = urllib2.urlopen(request)
            data = response.read()
            response.close()
            log('image downloaded: ' + url)
        except:
            log('image download failed: ' + url)
            return ""
        if data != '':
            try:
                if url.endswith(".png"):
                    image = xbmc_cache_file_png
                else:
                    image = xbmc_cache_file_jpg
                tmpfile = open(xbmc.translatePath(image), 'wb')
                tmpfile.write(data)
                tmpfile.close()
                return xbmc.translatePath(image)
            except:
                log('failed to save image ' + url)
                return ""
        else:
            return ""


def GetFavouriteswithType(favtype):
    favs = GetFavourites()
    favlist = []
    for fav in favs:
        if fav["Type"] == favtype:
            favlist.append(fav)
    return favlist


def GetFavPath(fav):
    path = ""
    if fav["type"] == "media":
        path = "PlayMedia(%s)" % (fav["path"])
    elif fav["type"] == "script":
        path = "RunScript(%s)" % (fav["path"])
    elif "window" in fav and "windowparameter" in fav:
        path = "ActivateWindow(%s,%s)" % (fav["window"], fav["windowparameter"])
    else:
        log("error parsing favs")
    return path


def GetFavourites():
    items = []
    json_response = get_Kodi_JSON('"method": "Favourites.GetFavourites", "params": {"type": null, "properties": ["path", "thumbnail", "window", "windowparameter"]}')
    if json_response["result"]["limits"]["total"] > 0:
        for fav in json_response["result"]["favourites"]:
            path = GetFavPath(fav)
            newitem = {'Label': fav["title"],
                       'Thumb': fav["thumbnail"],
                       'Type': fav["type"],
                       'Builtin': path,
                       'Path': "plugin://script.extendedinfo/?info=action&&id=" + path}
            items.append(newitem)
    return items


def GetIconPanel(number):
    items = []
    offset = number * 5 - 5
    for i in range(1, 6):
        newitem = {'Label': xbmc.getInfoLabel("Skin.String(IconPanelItem" + str(i + offset) + ".Label)").decode("utf-8"),
                   'Path': "plugin://script.extendedinfo/?info=action&&id=" + xbmc.getInfoLabel("Skin.String(IconPanelItem" + str(i + offset) + ".Path)").decode("utf-8"),
                   'Thumb': xbmc.getInfoLabel("Skin.String(IconPanelItem" + str(i + offset) + ".Icon)").decode("utf-8"),
                   'ID': "IconPanelitem" + str(i + offset).decode("utf-8"),
                   'Type': xbmc.getInfoLabel("Skin.String(IconPanelItem" + str(i + offset) + ".Type)").decode("utf-8")}
        items.append(newitem)
    return items


def GetWeatherImages():
    items = []
    for i in range(1, 6):
        newitem = {'Label': "bla",
                   'Path': "plugin://script.extendedinfo/?info=action&&id=SetFocus(22222)",
                   'Thumb': xbmc.getInfoLabel("Window(weather).Property(Map." + str(i) + ".Area)"),
                   'Layer': xbmc.getInfoLabel("Window(weather).Property(Map." + str(i) + ".Layer)"),
                   'Legend': xbmc.getInfoLabel("Window(weather).Property(Map." + str(i) + ".Legend)")}
        items.append(newitem)
    return items


def log(txt):
    if isinstance(txt, str):
        txt = txt.decode("utf-8", 'ignore')
    message = u'%s: %s' % (ADDON_ID, txt)
    xbmc.log(msg=message.encode("utf-8", 'ignore'), level=xbmc.LOGDEBUG)


def get_browse_dialog(default="", heading="Browse", dlg_type=3, shares="files", mask="", use_thumbs=False, treat_as_folder=False):
    dialog = xbmcgui.Dialog()
    value = dialog.browse(dlg_type, heading, shares, mask, use_thumbs, treat_as_folder, default)
    return value


def save_to_file(content, filename, path=""):
    if path == "":
        text_file_path = get_browse_dialog() + filename + ".txt"
    else:
        if not xbmcvfs.exists(path):
            xbmcvfs.mkdir(path)
        text_file_path = os.path.join(path, filename + ".txt")
    now = time.time()
    text_file = xbmcvfs.File(text_file_path, "w")
    simplejson.dump(content, text_file)
    text_file.close()
    log("saved textfile %s. Time: %f" % (path, time.time() - now))
    return True


def read_from_file(path=""):
    if path == "":
        path = get_browse_dialog(dlg_type=1)
    if not xbmcvfs.exists(path):
        return False
    now = time.time()
    try:
        f = open(path)
        fc = simplejson.load(f)
        log("loaded textfile %s. Time: %f" % (path, time.time() - now))
        return fc
    except:
        return False
        log("failed to load JSON textfile: " + path)


def ConvertYoutubeURL(string):
    if string and 'youtube.com/v' in string:
        vid_ids = re.findall(
            'http://www.youtube.com/v/(.{11})\??', string, re.DOTALL)
        for id in vid_ids:
            convertedstring = 'plugin://script.extendedinfo/?info=youtubevideo&&id=%s' % id
            return convertedstring
    if string and 'youtube.com/watch' in string:
        vid_ids = re.findall(
            'youtube.com/watch\?v=(.{11})\??', string, re.DOTALL)
        for id in vid_ids:
            convertedstring = 'plugin://script.extendedinfo/?info=youtubevideo&&id=%s' % id
            return convertedstring
    return ""


def ExtractYoutubeID(string):
    if string and 'youtube.com/v' in string:
        vid_ids = re.findall(
            'http://www.youtube.com/v/(.{11})\??', string, re.DOTALL)
        for id in vid_ids:
            return id
    if string and 'youtube.com/watch' in string:
        vid_ids = re.findall(
            'youtube.com/watch\?v=(.{11})\??', string, re.DOTALL)
        for id in vid_ids:
            return id
    return ""


def Notify(header="", message="", icon=ADDON_ICON, time=5000, sound=True):
    xbmcgui.Dialog().notification(heading=header, message=message, icon=icon, time=time, sound=sound)


def get_Kodi_JSON(params):
    json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", %s, "id": 1}' % params)
    json_query = unicode(json_query, 'utf-8', errors='ignore')
    return simplejson.loads(json_query)


def prettyprint(string):
    log(simplejson.dumps(string, sort_keys=True, indent=4, separators=(',', ': ')))


def passDictToSkin(data=None, prefix="", debug=False, precache=False, window=10000):
    skinwindow = xbmcgui.Window(window)
    if data is not None:
        threads = []
        image_requests = []
        for (key, value) in data.iteritems():
            value = unicode(value)
            if precache:
                if value.startswith("http://") and (value.endswith(".jpg") or value.endswith(".png")):
                    if value not in image_requests and value:
                        thread = Get_File_Thread(value)
                        threads += [thread]
                        thread.start()
                        image_requests.append(value)
            skinwindow.setProperty('%s%s' % (prefix, str(key)), value)
            if debug:
                log('%s%s' % (prefix, str(key)) + value)
        for x in threads:
            x.join()


def passListToSkin(name="", data=None, prefix="", controlwindow=None, handle=None, limit=False, debug=False):
    if limit and data:
        if limit < len(data):
            data = data[:limit]
    if handle:
        HOME.clearProperty(name)
        if data is not None:
            HOME.setProperty(name + ".Count", str(len(data)))
            items = create_listitems(data)
            xbmcplugin.setContent(handle, 'files')
            itemlist = list()
            for item in items:
                itemlist.append((item.getProperty("path"), item, False))
            xbmcplugin.addDirectoryItems(handle, itemlist, len(itemlist))
            xbmcplugin.endOfDirectory(handle)
    else:
        SetWindowProperties(name, data, prefix, debug)


def SetWindowProperties(name, data, prefix="", debug=False):
    if data is not None:
        # log("%s%s.Count = %s" % (prefix, name, str(len(data))))
        for (count, result) in enumerate(data):
            if debug:
                log("%s%s.%i = %s" % (prefix, name, count + 1, str(result)))
            for (key, value) in result.iteritems():
                value = unicode(value)
                HOME.setProperty('%s%s.%i.%s' % (prefix, name, count + 1, str(key)), value)
                if debug:
                    log('%s%s.%i.%s --> ' % (prefix, name, count + 1, str(key)) + value)
        HOME.setProperty('%s%s.Count' % (prefix, name), str(len(data)))
    else:
        HOME.setProperty('%s%s.Count' % (prefix, name), '0')
        log("%s%s.Count = None" % (prefix, name))


def create_listitems(data=None, preload_images=0):
    Int_InfoLabels = ["year", "episode", "season", "top250", "tracknumber", "playcount", "overlay"]
    Float_InfoLabels = ["rating"]
    String_InfoLabels = ["genre", "director", "mpaa", "plot", "plotoutline", "title", "originaltitle", "sorttitle", "duration", "studio", "tagline", "writer",
                         "tvshowtitle", "premiered", "status", "code", "aired", "credits", "lastplayed", "album", "votes", "trailer", "dateadded"]
    itemlist = []
    if data is not None:
        threads = []
        image_requests = []
        for (count, result) in enumerate(data):
            listitem = xbmcgui.ListItem('%s' % (str(count)))
            itempath = ""
            counter = 1
            for (key, value) in result.iteritems():
                if not value:
                    continue
                value = unicode(value)
                if counter <= preload_images:
                    if value.startswith("http://") and (value.endswith(".jpg") or value.endswith(".png")):
                        if value not in image_requests:
                            thread = Get_File_Thread(value)
                            threads += [thread]
                            thread.start()
                            image_requests.append(value)
                if key.lower() in ["name", "label", "title"]:
                    listitem.setLabel(value)
                elif key.lower() in ["thumb"]:
                    listitem.setThumbnailImage(value)
                elif key.lower() in ["icon"]:
                    listitem.setIconImage(value)
                elif key.lower() in ["path"]:
                    itempath = value
                if key.lower() in ["thumb", "poster", "banner", "fanart", "clearart", "clearlogo", "landscape", "discart", "characterart", "tvshow.fanart", "tvshow.poster", "tvshow.banner", "tvshow.clearart", "tvshow.characterart"]:
                    listitem.setArt({key.lower(): value})
                    # log("key: " + unicode(key) + "  value: " + unicode(value))
                if key.lower() in Int_InfoLabels:
                    try:
                        listitem.setInfo('video', {key.lower(): int(value)})
                    except:
                        pass
                if key.lower() in String_InfoLabels:
                    listitem.setInfo('video', {key.lower(): value})
                if key.lower() in Float_InfoLabels:
                    try:
                        listitem.setInfo('video', {key.lower(): "%1.1f" % float(value)})
                    except:
                        pass
                listitem.setProperty('%s' % (key), value)
            listitem.setPath(path=itempath)
            listitem.setProperty("index", str(counter))
            itemlist.append(listitem)
            counter += 1
        for x in threads:
            x.join()
    return itemlist


def cleanText(text):
    if text:
        text = re.sub('(From Wikipedia, the free encyclopedia)|(Description above from the Wikipedia.*?Wikipedia)', '', text)
        text = text.replace('<br \/>', '[CR]')
        text = re.sub('<(.|\n|\r)*?>', '', text)
        text = text.replace('&quot;', '"')
        text = text.replace('<em>', '[I]')
        text = text.replace('</em>', '[/I]')
        text = text.replace('&amp;', '&')
        text = text.replace('&gt;', '>')
        text = text.replace('&lt;', '<')
        text = text.replace('&#39;', "'")
        text = text.replace('User-contributed text is available under the Creative Commons By-SA License and may also be available under the GNU FDL.', '')
        while text:
            s = text[0]
            e = text[-1]
            if s == u'\u200b':
                text = text[1:]
            if text and e == u'\u200b':
                text = text[:-1]
            if s == " " or e == " ":
                text = text.strip()
            elif s == "." or e == ".":
                text = text.strip(".")
            elif s == "\n" or e == "\n":
                text = text.strip("\n")
            else:
                break
        return text.strip()
    else:
        return ""
