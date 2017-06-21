from os import path
from requests import get
from json import loads, load
from shutil import copyfileobj, rmtree
from time import time
from unicodedata import normalize
from urllib import urlretrieve, unquote_plus, unquote, urlopen, quote
from xbmcaddon import Addon
from xbmcplugin import endOfDirectory, addDirectoryItem
from xbmcgui import ListItem, Dialog
from xbmcvfs import listdir, exists, mkdirs
from xbmc import translatePath, executebuiltin, getInfoLabel, executeJSONRPC, Player, sleep, log, getCondVisibility
from re import sub
import sys

reload(sys)
sys.setdefaultencoding('utf8')

__addon__ = Addon()
__scriptid__ = __addon__.getAddonInfo('id')
__version__ = __addon__.getAddonInfo('version')
__temp__ = unicode(translatePath(__addon__.getAddonInfo('profile')), 'utf-8')
__subs__ = unicode(translatePath(path.join(__temp__, 'subs')), 'utf-8')
__scriptname__ = __addon__.getAddonInfo('name')
__language__ = __addon__.getLocalizedString


def convert_to_utf(file):
    try:
        with codecs.open(file, "r", "cp1255") as f:
            srt_data = f.read()

        with codecs.open(file, 'w', 'utf-8') as output:
            output.write(srt_data)
    except:
        pass


def normalizeString(str):
    return normalize('NFKD', unicode(unicode(str, 'utf-8'))).encode('utf-8', 'ignore')


def download(id):
    try:
        rmtree(__subs__)
    except:
        pass
    mkdirs(__subs__)
    subtitle_list = []
    exts = [".srt", ".sub", ".str"]
    archive_file = path.join(__temp__, 'wizdom.sub.' + id + '.zip')
    if not path.exists(archive_file):
        urlretrieve("http://zip.wizdom.xyz/" + id + ".zip", archive_file)
    executebuiltin(('XBMC.Extract("%s","%s")' % (archive_file, __subs__)).encode('utf-8'), True)
    for file_ in listdir(__subs__)[1]:
        ufile = file_.decode('utf-8')
        file_ = path.join(__subs__, ufile)
        if path.splitext(ufile)[1] in exts:
            convert_to_utf(file_)
            subtitle_list.append(file_)
    return subtitle_list


def getParams(arg):
    param = []
    paramstring = arg
    if len(paramstring) >= 2:
        params = arg
        cleanedparams = params.replace('?', '')
        if (params[len(params) - 1] == '/'):
            params = params[0:len(params) - 2]
        pairsofparams = cleanedparams.split('&')
        param = {}
        for i in range(len(pairsofparams)):
            splitparams = {}
            splitparams = pairsofparams[i].split('=')
            if (len(splitparams)) == 2:
                param[splitparams[0]] = splitparams[1]

    return param


def getParam(name, params):
    try:
        return unquote_plus(params[name])
    except:
        pass


def GetJson(imdb, season=0, episode=0, version=0):
    filename = 'wizdom.imdb.%s.%s.%s.json' % (imdb, season, episode)
    url = "http://api.wizdom.xyz/search.id.php?imdb=%s&season=%s&episode=%s&version=%s" % (
    imdb, season, episode, version)

    MyLog("GetJson:%s" % url)
    json_object = Caching(filename, url)
    subs_rate = []
    if json_object <> 0:
        for item_data in json_object:
            listitem = ListItem(label="Hebrew", label2=item_data["versioname"], thumbnailImage="he",
                                iconImage="%s" % (item_data["score"] / 2))
            if int(item_data["score"]) > 8:
                listitem.setProperty("sync", "true")
            url = "plugin://%s/?action=download&versioname=%s&id=%s" % (
            __scriptid__, item_data["versioname"], item_data["id"])
            addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=listitem, isFolder=False)


def SearchMovie(query, year):
    filename = 'wizdom.search.movie.%s.%s.json' % (normalizeString(query), year)
    if year > 0:
        url = "http://api.tmdb.org/3/search/movie?api_key=f7f51775877e0bb6703520952b3c7840&query=%s&year=%s&language=he" % (
        quote(query), year)
    else:
        url = "http://api.tmdb.org/3/search/movie?api_key=f7f51775877e0bb6703520952b3c7840&query=%s&language=he" % (
        quote(query))
    json = Caching(filename, url)
    try:
        tmdb_id = int(json["results"][0]["id"])
    except:
        return 0
        pass
    filename = 'wizdom.tmdb.%s.json' % (tmdb_id)
    url = "http://api.tmdb.org/3/movie/%s?api_key=f7f51775877e0bb6703520952b3c7840&language=en" % (tmdb_id)
    json = Caching(filename, url)
    try:
        imdb_id = json["imdb_id"]
    except:
        return 0
        pass
    return imdb_id


def Caching(filename, url):
    json_file = path.join(__temp__, filename)
    if not path.exists(json_file) or not path.getsize(json_file) > 20 or (time() - path.getmtime(json_file) > 30 * 60):
        urlretrieve(url, json_file)
    if path.exists(json_file) and path.getsize(json_file) > 20:
        with open(json_file) as json_data:
            json_object = load(json_data)
        return json_object
    else:
        return 0


def ManualSearch(title):
    filename = 'wizdom.search.filename.%s.json' % (quote(title))
    url = "http://api.wizdom.xyz/search.manual.php?filename=%s" % (normalizeString(title))
    try:
        json = Caching(filename, url)
        if json["type"] == "episode":
            imdb_id = urlopen("http://api.wizdom.xyz/search.tv.php?name=" + quote(json['title'])).read()
            if imdb_id <> '' and imdb_id <> 0:
                GetJson(str(imdb_id), json['season'], json['episode'], normalizeString(title))
        elif json["type"] == "movie":
            if "year" in json:
                imdb_id = SearchMovie(str(json['title']), json['year'])
            else:
                imdb_id = SearchMovie(str(json['title']), 0)
            if imdb_id:
                GetJson(str(imdb_id), 0, 0, normalizeString(title))
    except:
        pass


def MyLog(msg):
    log((u"##**## [%s] %s" % ("Wizdom Subs", msg,)).encode('utf-8'), level=xbmc.LOGDEBUG)


if not exists(__temp__):
    mkdirs(__temp__)

action = None
if len(sys.argv) >= 2:
    params = getParams(sys.argv[2])
    action = getParam("action", params)

MyLog("Version:%s" % __version__)
MyLog("Action:%s" % action)

if action == 'search':
    item = {}

    MyLog("isPlaying:%s" % Player().isPlaying())
    if Player().isPlaying():
        item['year'] = getInfoLabel("VideoPlayer.Year")  # Year

        item['season'] = str(getInfoLabel("VideoPlayer.Season"))  # Season
        if item['season'] == '' or item['season'] < 1:
            item['season'] = 0
        item['episode'] = str(getInfoLabel("VideoPlayer.Episode"))  # Episode
        if item['episode'] == '' or item['episode'] < 1:
            item['episode'] = 0

        if item['episode'] == 0:
            item['title'] = normalizeString(getInfoLabel("VideoPlayer.Title"))  # no original title, get just Title
        else:
            item['title'] = normalizeString(getInfoLabel("VideoPlayer.TVshowtitle"))  # Show
        if item['title'] == "":
            item['title'] = normalizeString(getInfoLabel("VideoPlayer.OriginalTitle"))  # try to get original title
        item['file_original_path'] = unquote(unicode(Player().getPlayingFile(), 'utf-8'))  # Full path of a playing file
        item['file_original_path'] = item['file_original_path'].split("?")
        item['file_original_path'] = path.basename(item['file_original_path'][0])[:-4]
    else:  # Take item params from window when kodi is not playing
        labelIMDB = getInfoLabel("ListItem.IMDBNumber")
        item['year'] = getInfoLabel("ListItem.Year")
        item['season'] = getInfoLabel("ListItem.Season")
        item['episode'] = getInfoLabel("ListItem.Episode")
        item['file_original_path'] = ""
        labelType = getInfoLabel("ListItem.DBTYPE")  # movie/tvshow/season/episode
        isItMovie = labelType == 'movie' or getCondVisibility("Container.Content(movies)")
        isItEpisode = labelType == 'episode' or getCondVisibility("Container.Content(episodes)")

        if isItMovie:
            item['title'] = getInfoLabel("ListItem.OriginalTitle")
        elif isItEpisode:
            item['title'] = getInfoLabel("ListItem.TVShowTitle")
        else:
            item['title'] = "SearchFor..."  # In order to show "No Subtitles Found" result.

    MyLog("item:%s" % item)
    imdb_id = 0
    try:
        if Player().isPlaying():  # Enable using subtitles search dialog when kodi is not playing
            playerid_query = '{"jsonrpc": "2.0", "method": "Player.GetActivePlayers", "id": 1}'
            playerid = loads(executeJSONRPC(playerid_query))['result'][0]['playerid']
            imdb_id_query = '{"jsonrpc": "2.0", "method": "Player.GetItem", "params": {"playerid": ' + str(
                playerid) + ', "properties": ["imdbnumber"]}, "id": 1}'
            imdb_id = loads(executeJSONRPC(imdb_id_query))['result']['item']['imdbnumber']
            MyLog("imdb JSONPC:%s" % imdb_id)
        else:
            if labelIMDB:
                imdb_id = labelIMDB
            else:
                if isItMovie:
                    imdb_id = "ThisIsMovie"  # Search the movie by item['title'] for imdb_id
                elif isItEpisode:
                    imdb_id = "ThisIsEpisode"  # Search by item['title'] for tvdb_id
                else:
                    imdb_id = "tt0"  # In order to show "No Subtitles Found" result => Doesn't recognize movie/episode
    except:
        pass

    if imdb_id[:2] == "tt":  # Simple IMDB_ID
        GetJson(imdb_id, item['season'], item['episode'], item['file_original_path'])
    else:
        # Search TV Show by Title
        if item['season'] or item['episode']:
            try:
                imdb_id = urlopen("http://api.wizdom.xyz/search.tv.php?name=" + quote(item['title'])).read()
                MyLog("Search TV IMDB:%s [%s]" % (imdb_id, item['title']))
                if imdb_id <> '' and imdb_id <> 0:
                    GetJson(str(imdb_id), item['season'], item['episode'], item['file_original_path'])
            except:
                pass
        # Search Movie by Title+Year
        else:
            try:
                imdb_id = SearchMovie(query=item['title'], year=item['year'])
                MyLog("Search IMDB:%s" % imdb_id)
                if not imdb_id[:2] == "tt":
                    imdb_id = SearchMovie(query=item['title'], year=(int(item['year']) - 1))
                    MyLog("Search IMDB(2):%s" % imdb_id)
                if imdb_id[:2] == "tt":
                    GetJson(imdb_id, 0, 0, item['file_original_path'])
            except:
                pass

    # Search Local File
    if not imdb_id:
        ManualSearch(item['title'])
    endOfDirectory(int(sys.argv[1]))
    if __addon__.getSetting("Debug") == "true":
        if imdb_id[:2] == "tt":
            Dialog().ok("Debug " + __version__, str(item), "imdb: " + str(imdb_id))
        else:
            Dialog().ok("Debug " + __version__, str(item), "NO IDS")

elif action == 'manualsearch':
    searchstring = getParam("searchstring", params)
    ManualSearch(searchstring)
    endOfDirectory(int(sys.argv[1]))

elif action == 'download':
    id = getParam("id", params)
    MyLog("Download ID:%s" % id)
    subs = download(id)
    for sub in subs:
        listitem = ListItem(label=sub)
        addDirectoryItem(handle=int(sys.argv[1]), url=sub, listitem=listitem, isFolder=False)
    endOfDirectory(int(sys.argv[1]))
elif action == 'clean':
    try:
        rmtree(__temp__)
    except:
        pass
    executebuiltin((u'Notification(%s,%s)' % (__scriptname__, __language__(32004))).encode('utf-8'))
