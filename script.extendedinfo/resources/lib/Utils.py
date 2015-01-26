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

addon = xbmcaddon.Addon()
addon_id = addon.getAddonInfo('id')
addon_icon = addon.getAddonInfo('icon')
addon_strings = addon.getLocalizedString
addon_name = addon.getAddonInfo('name')
addon_path = addon.getAddonInfo('path').decode("utf-8")


Addon_Data_Path = os.path.join(xbmc.translatePath("special://profile/addon_data/%s" % addon_id).decode("utf-8"))
homewindow = xbmcgui.Window(10000)
id_list = []
title_list = []
originaltitle_list = []
global windowstack
windowstack = []


def dictfind(lst, key, value):
    for i, dic in enumerate(lst):
        if dic[key] == value:
            return dic
    return ""

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
            self.getControl(10000).addItems(CreateListItems(self.imagelist))
            xbmc.executebuiltin("Control.SetFocus(10000,%s)" % self.index)
        else:
            listitem = {"label": self.image,
                        "Thumb": self.image}
            self.getControl(10000).addItems(CreateListItems([listitem]))

    def onAction(self, action):
        if action in self.ACTION_PREVIOUS_MENU:
            self.close()
        elif action in self.ACTION_LEFT:
            self.action = "left"
            self.close()
        elif action in self.ACTION_RIGHT:
            self.action = "right"
            self.close()


def WaitForVideoEnd():
    xbmc.sleep(1000)
    while xbmc.getCondVisibility("Player.HasVideo"):
        xbmc.sleep(400)


# def calculate_age(born):
#     age = ""
#     log(str(born))
#     if born and born is not None:
#         try:
#             born = datetime.datetime.strptime(born, '%Y-%m-%d')
#             today = datetime.date.today()
#             birthday = datetime.date(today.year, born.month, born.day)
#         except ValueError:
#             birthday = datetime.date(today.year, born.month, born.day - 1)
#         if birthday > today:
#             age = today.year - born.year - 1
#         else:
#             age = today.year - born.year
#     return age


def calculate_age(born):
    base_age = ""
    if born and born is not None:
        log(born)
        today = datetime.date.today()
        actor_born = born.split("-")
        base_age = today.year - int(actor_born[0])
        if len(actor_born) > 1:
            base_month = today.month - int(actor_born[1])
            base_day = today.day - int(actor_born[2])
            if base_month < 0:
                base_age -= 1
            elif base_month == 0 and base_day < 0:
                base_age -= 1
            elif base_month == 0 and base_day == 0:
                Notify("%s (%i)" % (addon.getLocalizedString(32158), base_age))
    return base_age


def PlayTrailer(youtube_id="", listitem=None, popstack=False):
    if not listitem:
        listitem = xbmcgui.ListItem(xbmc.getLocalizedString(20410))
        listitem.setInfo('video', {'Title': xbmc.getLocalizedString(20410), 'Genre': 'Youtube Video'})
    import YDStreamExtractor
    YDStreamExtractor.disableDASHVideo(True)
    vid = YDStreamExtractor.getVideoInfo(youtube_id, quality=1)
    if vid:
        stream_url = vid.streamURL()
        log("Youtube Trailer:" + stream_url)
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

        # Notify("time")
        # if self.popstack:
        #     PopWindowStack()

    def onPlayBackStopped(self):
        self.stopped = True

        # Notify("time")

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
                log("Youtube Trailer:" + stream_url)
                self.play(stream_url, listitem)
        else:
            Notify("no youtube id found")

    def WaitForVideoEnd(self):
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
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": {"directory": "%s", "media": "video", "properties": ["playcount", "resume"]}, "id": 1}' % (playlistpath))
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
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
            homewindow.setProperty('PlaylistWatched', str(played))
            homewindow.setProperty('PlaylistUnWatched', str(numitems - played))
            homewindow.setProperty('PlaylistInProgress', str(inprogress))
            homewindow.setProperty('PlaylistCount', str(numitems))


def GetSortLetters(path, focusedletter):
    listitems = []
    letterlist = []
    homewindow.clearProperty("LetterList")
    if addon.getSetting("FolderPath") == path:
        letterlist = addon.getSetting("LetterList")
        letterlist = letterlist.split()
    else:
        if path:
            json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": {"directory": "%s", "media": "files"}, "id": 1}' % (path))
            json_query = unicode(json_query, 'utf-8', errors='ignore')
            json_response = simplejson.loads(json_query)
            if "result" in json_response and "files" in json_response["result"]:
                for movie in json_response["result"]["files"]:
                    cleaned_label = movie["label"].replace("The ", "")
                    if cleaned_label:
                        sortletter = cleaned_label[0]
                        if not sortletter in letterlist:
                            letterlist.append(sortletter)
            addon.setSetting("LetterList", " ".join(letterlist))
            addon.setSetting("FolderPath", path)
    homewindow.setProperty("LetterList", "".join(letterlist))
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


def GetXBMCArtists():
    filename = Addon_Data_Path + "/XBMCartists.txt"
    if xbmcvfs.exists(filename) and time.time() - os.path.getmtime(filename) < 0:
        return read_from_file(filename)
    else:
        json_query = xbmc.executeJSONRPC(
            '{"jsonrpc": "2.0", "method": "AudioLibrary.GetArtists", "params": {"properties": ["musicbrainzartistid","thumbnail"]}, "id": 1}')
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_query = simplejson.loads(json_query)
        save_to_file(json_query, "XBMCartists", Addon_Data_Path)
        return json_query


def GetSimilarArtistsInLibrary(artistid):
    from LastFM import GetSimilarById
    simi_artists = GetSimilarById(artistid)
    if simi_artists is None:
        log('Last.fm didn\'t return proper response')
        return None
    xbmc_artists = GetXBMCArtists()
    artists = []
    for (count, simi_artist) in enumerate(simi_artists):
        for (count, xbmc_artist) in enumerate(xbmc_artists["result"]["artists"]):
            if xbmc_artist['musicbrainzartistid'] != '':
                if xbmc_artist['musicbrainzartistid'] == simi_artist['mbid']:
                    artists.append(xbmc_artist)
            elif xbmc_artist['artist'] == simi_artist['name']:
                json_query = xbmc.executeJSONRPC(
                    '{"jsonrpc": "2.0", "method": "AudioLibrary.GetArtistDetails", "params": {"properties": ["genre", "description", "mood", "style", "born", "died", "formed", "disbanded", "yearsactive", "instrument", "fanart", "thumbnail"], "artistid": %s}, "id": 1}' % str(xbmc_artist['artistid']))
                json_query = unicode(json_query, 'utf-8', errors='ignore')
                json_response = simplejson.loads(json_query)
                item = json_response["result"]["artistdetails"]
                newartist = {"Title": item['label'],
                             "Genre": " / ".join(item['genre']),
                             "Thumb": item['thumbnail'],  # remove
                             "Fanart": item['fanart'],  # remove
                             "Art(thumb)": item['thumbnail'],
                             "Art(fanart)": item['fanart'],
                             "Description": item['description'],
                             "Born": item['born'],
                             "Died": item['died'],
                             "Formed": item['formed'],
                             "Disbanded": item['disbanded'],
                             "YearsActive": " / ".join(item['yearsactive']),
                             "Style": " / ".join(item['style']),
                             "Mood": " / ".join(item['mood']),
                             "Instrument": " / ".join(item['instrument']),
                             "LibraryPath": 'musicdb://artists/' + str(item['artistid']) + '/'}
                artists.append(newartist)
    log('%i of %i artists found in last.FM is in XBMC database' %
        (len(artists), len(simi_artists)))
    return artists


def GetSimilarFromOwnLibrary(dbid):
    json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovieDetails", "params": {"properties": ["genre","director","country","year","mpaa"], "movieid":%s }, "id": 1}' % dbid)
    json_query = unicode(json_query, 'utf-8', errors='ignore')
    json_response = simplejson.loads(json_query)
    if "moviedetails" in json_response['result']:
        movieid = json_response['result']['moviedetails']['movieid']
        genres = json_response['result']['moviedetails']['genre']
        year = int(json_response['result']['moviedetails']['year'])
        countries = json_response['result']['moviedetails']['country']
        directors = json_response['result']['moviedetails']['director']
        mpaa = json_response['result']['moviedetails']['mpaa']
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties": ["genre","director","mpaa","country","year"], "sort": { "method": "random" } }, "id": 1}')
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_query = simplejson.loads(json_query)
        if "movies" in json_query['result']:
            quotalist = []
            for item in json_query['result']['movies']:
                difference = int(item['year']) - year
                hit = 0.0
                miss = 0.0
                quota = 0.0
                for genre in genres:
                    if genre in item['genre']:
                        hit += 1.0
                    else:
                        miss += 1.0
                miss += 0.00001
                if hit > 0.0:
                    quota = float(hit) / float(hit + miss)
                if genres[0] == item['genre'][0]:
                    quota += 0.3
                if difference < 6 and difference > -6:
                    quota += 0.15
                if difference < 3 and difference > -3:
                    quota += 0.15
                if countries[0] == item['country'][0]:
                    quota += 0.4
                if mpaa == item['mpaa']:
                    quota += 0.4
                if directors[0] == item['director'][0]:
                    quota += 0.6
                quotalist.append((quota, item["movieid"]))
            quotalist = sorted(quotalist, key=lambda quota: quota[0], reverse=True)
            count = 1
            for list_movie in quotalist:
                if movieid is not list_movie[1]:
                    movies = []
                    newmovie = GetMovieFromDB(list_movie[1])
                    movies.append(newmovie)
                    count += 1
                    if count > 20:
                        break
            return movies

def GetMovieFromDB(movieid):
    json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovieDetails", "params": {"properties": ["title", "originaltitle", "votes", "playcount", "year", "genre", "studio", "country", "tagline", "plot", "runtime", "file", "plotoutline", "lastplayed", "trailer", "rating", "resume", "art", "streamdetails", "mpaa", "director", "writer", "cast", "dateadded", "imdbnumber"], "movieid":%s }, "id": 1}' % str(movieid))
    json_query = unicode(json_query, 'utf-8', errors='ignore')
    json_response = simplejson.loads(json_query)
    movie = json_response["result"]["moviedetails"]
    newmovie = {'Art(fanart)': movie["art"].get('fanart', ""),
                'Art(poster)': movie["art"].get('poster', ""),
                'Fanart': movie["art"].get('fanart', ""),
                'Poster': movie["art"].get('poster', ""),
                'Title': movie.get('label', ""),
                'OriginalTitle': movie.get('originaltitle', ""),
                'ID': movie.get('imdbnumber', ""),
                'Path': "",
                'Play': "",
                'DBID': str(movie['movieid']),
                'Rating': str(round(float(movie['rating']), 1)),
                'Premiered': movie.get('year', "")}
    return newmovie


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


def GetXBMCAlbums():
    json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetAlbums", "params": {"properties": ["title"]}, "id": 1}')
    json_query = unicode(json_query, 'utf-8', errors='ignore')
    json_query = simplejson.loads(json_query)
    if "result" in json_query and "albums" in json_query['result']:
        return json_query['result']['albums']
    else:
        return []


def create_channel_list():
    json_response = xbmc.executeJSONRPC('{"jsonrpc":"2.0","id":1,"method":"PVR.GetChannels","params":{"channelgroupid":"alltv", "properties": [ "thumbnail", "locked", "hidden", "channel", "lastplayed" ]}}')
    json_response = unicode(json_response, 'utf-8', errors='ignore')
    json_response = simplejson.loads(json_response)
    if ('result' in json_response) and ("movies" in json_response["result"]):
        return json_response
    else:
        return False


def fetch(dictionary, key):
    if key in dictionary:
        if dictionary[key] is not None:
            return dictionary[key]
    return ""


def CompareWithLibrary(onlinelist=[], library_first=True, sortkey=False):
    global id_list
    global originaltitle_list
    global title_list
    if not title_list:
        now = time.time()
        id_list = xbmc.getInfoLabel("Window(home).Property(id_list.JSON)")
        if id_list and id_list != "[]":
            id_list = simplejson.loads(id_list)
            originaltitle_list = simplejson.loads(xbmc.getInfoLabel("Window(home).Property(originaltitle_list.JSON)"))
            title_list = simplejson.loads(xbmc.getInfoLabel("Window(home).Property(title_list.JSON)"))
        else:
            json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties": ["originaltitle", "imdbnumber", "file"], "sort": { "method": "none" } }, "id": 1}')
            json_query = simplejson.loads(unicode(json_query, 'utf-8', errors='ignore'))
            id_list = []
            originaltitle_list = []
            title_list = []
            if "movies" in json_query["result"]:
                for item in json_query["result"]["movies"]:
                    id_list.append(item["movieid"])
                    originaltitle_list.append(item["originaltitle"].lower())
                    title_list.append(item["label"].lower())
            homewindow.setProperty("id_list.JSON", simplejson.dumps(id_list))
            homewindow.setProperty("originaltitle_list.JSON", simplejson.dumps(originaltitle_list))
            homewindow.setProperty("title_list.JSON", simplejson.dumps(title_list))
        log("create_light_movielist: " + str(now - time.time()))
    now = time.time()
    local_items = []
    remote_items = []
    for online_item in onlinelist:
        found = False
        if online_item["Title"].lower() in title_list:
            index = title_list.index(online_item["Title"].lower())
            found = True
            # Notify("found title " + online_item["Title"])
        elif online_item["OriginalTitle"].lower() in originaltitle_list:
            index = originaltitle_list.index(online_item["OriginalTitle"].lower())
            found = True
            # Notify("found originaltitle_list " + online_item["Title"])
        if found:
            # prettyprint(id_list)
            # log(str(index))
            dbid = str(id_list[index])
            json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovieDetails", "params": {"properties": ["streamdetails", "resume", "year", "art", "writer", "file"], "movieid":%s }, "id": 1}' % dbid)
            json_query = unicode(json_query, 'utf-8', errors='ignore')
            json_response = simplejson.loads(json_query)
            if "moviedetails" in json_response["result"]:
                local_item = json_response['result']['moviedetails']
                try:
                    diff = abs(local_item["year"] - int(online_item["Year"]))
                    if diff > 1:
                        remote_items.append(online_item)
                        continue
                except:
                    pass
                if (local_item['resume']['position'] and local_item['resume']['total']) > 0:
                    resume = "true"
                    played = '%s' % int((float(local_item['resume']['position']) / float(local_item['resume']['total'])) * 100)
                else:
                    resume = "false"
                    played = '0'
                streaminfo = media_streamdetails(local_item['file'].encode('utf-8').lower(), local_item['streamdetails'])
                online_item["Play"] = local_item["movieid"]
                online_item["DBID"] = local_item["movieid"]
                online_item["Path"] = local_item['file']
                online_item["PercentPlayed"] = played
                online_item["Resume"] = resume
                online_item["Path"] = local_item['file']
                online_item["FilenameAndPath"] = local_item['file']
                online_item["Writer"] = " / ".join(local_item['writer'])
                online_item["Logo"] = local_item['art'].get("clearlogo", "")
                online_item["DiscArt"] = local_item['art'].get("discart", "")
                online_item["Banner"] = local_item['art'].get("banner", "")
                online_item["Poster"] = local_item['art'].get("poster", "")
                online_item["Thumb"] = local_item['art'].get("poster", "")
                online_item.update(streaminfo)
                audio = local_item['streamdetails']['audio']
                subtitles = local_item['streamdetails']['subtitle']
                for i in range(1, 20):
                    online_item['AudioLanguage.%d' % i] = ""
                    online_item['SubtitleLanguage.%d' % i] = ""
                count = 1
                streams = []
                for item in audio:
                    language = item['language']
                    if language not in streams and language != "und":
                        streams.append(language)
                        online_item['AudioLanguage.%d' % count] = language
                        online_item['AudioCodec.%d' % count] = item['codec']
                        online_item['AudioChannels.%d' % count] = str(item['channels'])
                        count += 1
                count = 1
                subs = []
                for item in subtitles:
                    language = item['language']
                    if language not in subs and language != "und":
                        subs.append(language)
                        online_item['SubtitleLanguage.%d' % count] = language
                        count += 1
                online_item['SubtitleLanguage'] = " / ".join(subs)
                online_item['AudioLanguage'] = " / ".join(streams)
                if library_first:
                    local_items.append(online_item)
                else:
                    remote_items.append(online_item)
            else:
                remote_items.append(online_item)
        else:
            remote_items.append(online_item)
    log("compare time: " + str(now - time.time()))
    if sortkey:
        return sorted(local_items, key=lambda k: k[sortkey], reverse=True) + sorted(remote_items, key=lambda k: k[sortkey], reverse=True)
    else:
        return local_items + remote_items


def GetMusicBrainzIdFromNet(artist, xbmc_artist_id=-1):
    base_url = "http://musicbrainz.org/ws/2/artist/?fmt=json"
    url = '&query=artist:%s' % urllib.quote_plus(artist)
    results = Get_JSON_response(base_url + url, 30)
    if results and len(results["artists"]) > 0:
        mbid = results["artists"][0]["id"]
        log("found artist id for " + artist.decode("utf-8") + ": " + mbid)
        return mbid
    else:
        return None


def CompareAlbumWithLibrary(onlinelist):
    locallist = GetXBMCAlbums()
    for online_item in onlinelist:
        for localitem in locallist:
            if online_item["name"] == localitem["title"]:
                json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetAlbumDetails", "params": {"properties": ["thumbnail"], "albumid":%s }, "id": 1}' % str(localitem["albumid"]))
                json_query = unicode(json_query, 'utf-8', errors='ignore')
                json_query = simplejson.loads(json_query)
                album = json_query["result"]["albumdetails"]
                online_item.update({"DBID": album["albumid"]})
                online_item.update(
                    {"Path": 'XBMC.RunScript(service.skin.widgets,albumid=' + str(album["albumid"]) + ')'})
                if album["thumbnail"]:
                    online_item.update({"thumb": album["thumbnail"]})
                    online_item.update({"Icon": album["thumbnail"]})
                break
    return onlinelist


def GetStringFromUrl(url):
    succeed = 0
    while (succeed < 5) and (not xbmc.abortRequested):
        try:
            request = urllib2.Request(url)
            request.add_header('User-agent', 'XBMC/14.0 ( phil65@kodi.tv )')
            response = urllib2.urlopen(request)
            data = response.read()
            return data
        except:
            log("GetStringFromURL: could not get data from %s" % url)
            xbmc.sleep(1000)
            succeed += 1
    return None


def Get_JSON_response(url="", cache_days=7.0, folder=False):
    now = time.time()
    hashed_url = hashlib.md5(url).hexdigest()
    path = xbmc.translatePath(os.path.join(Addon_Data_Path, hashed_url + ".txt"))
    cache_seconds = int(cache_days * 86400.0)
    prop_time = homewindow.getProperty(hashed_url + "_timestamp")
    if prop_time and now - float(prop_time) < cache_seconds:
        try:
            prop = simplejson.loads(homewindow.getProperty(hashed_url))
            log("prop load for %s. time: %f" % (url, time.time() - now))
            return prop
        except:
            log("could not load prop data")
    if xbmcvfs.exists(path) and ((now - os.path.getmtime(path)) < cache_seconds):
        results = read_from_file(path)
        log("loaded file for %s. time: %f" % (url, time.time() - now))
    else:
        response = GetStringFromUrl(url)
        try:
            results = simplejson.loads(response)
            log("download %s. time: %f" % (url, time.time() - now))
            log("save to file: " + url)
            save_to_file(results, hashed_url, Addon_Data_Path)
        except:
            log("Exception: Could not get new JSON data. Tryin to fallback to cache")
            log(response)
            if xbmcvfs.exists(path):
                results = read_from_file(path)
            else:
                results = []
    homewindow.setProperty(hashed_url + "_timestamp", str(now))
    homewindow.setProperty(hashed_url, simplejson.dumps(results))
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
    # xbmc_cache_file_jpg = os.path.join(xbmc.translatePath("special://profile/Thumbnails/Video"), cachedthumb[0], cachedthumb)
    if xbmcvfs.exists(xbmc_cache_file_jpg):
        log("1: " + xbmc_cache_file_jpg)
        log("xbmc_cache_file_jpg Image: " + url)
        return xbmc.translatePath(xbmc_cache_file_jpg)
    elif xbmcvfs.exists(xbmc_cache_file_png):
        log("2: " + xbmc_cache_file_png)
        log("xbmc_cache_file_png Image: " + url)
        return xbmc_cache_file_png
    elif xbmcvfs.exists(xbmc_vid_cache_file):
        log("3: " + xbmc_vid_cache_file)
        log("xbmc_vid_cache_file Image: " + url)
        return xbmc_vid_cache_file
    else:
        try:
            log("Download: " + url)
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
    json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Favourites.GetFavourites", "params": {"type": null, "properties": ["path", "thumbnail", "window", "windowparameter"]}, "id": 1}')
    json_query = unicode(json_query, 'utf-8', errors='ignore')
    json_query = simplejson.loads(json_query)
    if json_query["result"]["limits"]["total"] > 0:
        for fav in json_query["result"]["favourites"]:
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
        txt = txt.decode("utf-8")
    message = u'%s: %s' % (addon_id, txt)
    xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)


def get_browse_dialog(default="", heading="Browse", dlg_type=3, shares="files", mask="", use_thumbs=False, treat_as_folder=False):
    dialog = xbmcgui.Dialog()
    value = dialog.browse(
        dlg_type, heading, shares, mask, use_thumbs, treat_as_folder, default)
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
    if xbmcvfs.exists(path):
        now = time.time()
        f = open(path)
        fc = simplejson.load(f)
        log("loaded textfile %s. Time: %f" % (path, time.time() - now))
        return fc
    else:
        return False


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


def Notify(header="", message="", icon=addon_icon, time=5000, sound=True):
    xbmcgui.Dialog().notification(heading=header, message=message, icon=icon, time=time, sound=sound)


def GetMovieSetName(dbid):
    json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovieDetails", "params": {"properties": ["setid"], "movieid":%s }, "id": 1}' % dbid)
    json_query = unicode(json_query, 'utf-8', errors='ignore')
    json_response = simplejson.loads(json_query)
    if "moviedetails" in json_response["result"]:
        dbsetid = json_response['result']['moviedetails'].get('setid', "")
        if dbsetid:
            json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovieSetDetails", "params": {"setid":%s }, "id": 1}' % dbsetid)
            json_query = unicode(json_query, 'utf-8', errors='ignore')
            json_response = simplejson.loads(json_query)
            return json_response['result']['setdetails'].get('label', "")
    return ""


def prettyprint(string):
    log(simplejson.dumps(string, sort_keys=True, indent=4, separators=(',', ': ')))


def GetImdbIDFromDatabase(type, dbid):
    if type == "movie":
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovieDetails", "params": {"properties": ["imdbnumber","title", "year"], "movieid":%s }, "id": 1}' % dbid)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        if "moviedetails" in json_response["result"]:
            return json_response['result']['moviedetails']['imdbnumber']
        else:
            return []
    elif type == "tvshow":
        json_query = xbmc.executeJSONRPC(
            '{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShowDetails", "params": {"properties": ["imdbnumber","title", "year"], "tvshowid":%s }, "id": 1}' % dbid)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        if "result" in json_response and "tvshowdetails" in json_response["result"]:
            return json_response['result']['tvshowdetails']['imdbnumber']
        else:
            return []


def GetImdbIDFromDatabasefromEpisode(dbid):
    json_query = xbmc.executeJSONRPC(
        '{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodeDetails", "params": {"properties": ["tvshowid"], "episodeid":%s }, "id": 1}' % dbid)
    json_query = unicode(json_query, 'utf-8', errors='ignore')
    json_response = simplejson.loads(json_query)
    if "episodedetails" in json_response["result"]:
        tvshowid = str(json_response['result']['episodedetails']['tvshowid'])
        return GetImdbIDFromDatabase("tvshow", tvshowid)


def passDictToSkin(data=None, prefix="", debug=False, precache=False, window=10000):
    skinwindow = xbmcgui.Window(window)
    if data is not None:
        threads = []
        image_requests = []
        for (key, value) in data.iteritems():
            value = unicode(value)
            if precache:
                if value.startswith("http://") and (value.endswith(".jpg") or value.endswith(".png")):
                    # Notify("download")
                    if not value in image_requests and value:
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
        homewindow.clearProperty(name)
        if data is not None:
            homewindow.setProperty(name + ".Count", str(len(data)))
            items = CreateListItems(data)
            xbmcplugin.setContent(handle, 'url')
            itemlist = list()
            for item in items:
                itemlist.append((item.getProperty("path"), item, False))
            xbmcplugin.addDirectoryItems(handle, itemlist, False)
    else:
        SetWindowProperties(name, data, prefix, debug)


def SetWindowProperties(name, data, prefix="", debug=False):
    if data is not None:
       # log( "%s%s.Count = %s" % (prefix, name, str(len(data)) ) )
        for (count, result) in enumerate(data):
            if debug:
                log("%s%s.%i = %s" % (prefix, name, count + 1, str(result)))
            for (key, value) in result.iteritems():
                value = unicode(value)
                homewindow.setProperty('%s%s.%i.%s' % (prefix, name, count + 1, str(key)), value)
                if debug:
                    log('%s%s.%i.%s --> ' % (prefix, name, count + 1, str(key)) + value)
        homewindow.setProperty('%s%s.Count' % (prefix, name), str(len(data)))
    else:
        homewindow.setProperty('%s%s.Count' % (prefix, name), '0')
        log("%s%s.Count = None" % (prefix, name))


def CreateListItems(data=None, preload_images=0):
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
                        if not value in image_requests:
                            thread = Get_File_Thread(value)
                            threads += [thread]
                            thread.start()
                            image_requests.append(value)
                if key.lower() in ["name", "label", "title"]:
                    listitem.setLabel(value)
                if key.lower() in ["thumb"]:
                    listitem.setThumbnailImage(value)
                if key.lower() in ["icon"]:
                    listitem.setIconImage(value)
                if key.lower() in ["thumb", "poster", "banner", "fanart", "clearart", "clearlogo", "landscape", "discart", "characterart", "tvshow.fanart", "tvshow.poster", "tvshow.banner", "tvshow.clearart", "tvshow.characterart"]:
                    listitem.setArt({key.lower(): value})
                if key.lower() in ["path"]:
                    itempath = value
           #     log("key: " + unicode(key) + "  value: " + unicode(value))
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
