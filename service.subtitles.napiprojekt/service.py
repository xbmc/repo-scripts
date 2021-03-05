# -*- coding: utf-8 -*- 

from os import path
from sys import argv
from urllib.parse import unquote, quote_plus
from unicodedata import normalize
from hashlib import md5
from resources.lib.NapiProjekt import NapiProjektHelper, log

import xbmc
import xbmcvfs
import xbmcaddon
import xbmcgui
import xbmcplugin

__addon__ = xbmcaddon.Addon()
__scriptid__ = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')
__language__ = __addon__.getLocalizedString

__cwd__ = xbmcvfs.translatePath(__addon__.getAddonInfo('path'))
__profile__ = xbmcvfs.translatePath(__addon__.getAddonInfo('profile'))
__resource__ = xbmcvfs.translatePath(path.join(__cwd__, 'resources', 'lib'))
__temp__ = xbmcvfs.translatePath(path.join(__profile__, 'temp', ''))

def timeout(func, args=(), kwargs={}, timeout_duration=10, default=None):
    import threading

    class InterruptableThread(threading.Thread):
        def __init__(self):
            threading.Thread.__init__(self)
            self.result = "000000000000"

        def run(self):
            self.result = func(*args, **kwargs)

    it = InterruptableThread()
    it.start()
    it.join(timeout_duration)
    if it.is_alive():
        return it.result
    else:
        return it.result


def get_filehash(path, rar):
    d = md5()
    qpath = quote_plus(path, safe='')
    if rar:
        path = """rar://""" + qpath + '/'
        for file in xbmcvfs.listdir(path)[1]:
            if file.lower().endswith(('.avi', '.mkv', '.mp4')):
                path = path + file
                break

    with xbmcvfs.File(path, "rb") as file:
        d.update(file.readBytes(10485760))

    return d.hexdigest()


def get_file_token(file_md5hash):
    idx = [0xe, 0x3, 0x6, 0x8, 0x2]
    mul = [2, 2, 5, 4, 3]
    add = [0, 0xd, 0x10, 0xb, 0x5]

    b = []
    for i in range(len(idx)):
        a = add[i]
        m = mul[i]
        i = idx[i]

        t = a + int(file_md5hash[i], 16)
        v = int(file_md5hash[t:t + 2], 16)
        b.append(("%x" % (v * m))[-1])

    return ''.join(b)


def Search(item):
    md5hash = timeout(get_filehash, args=(item["file_original_path"], item["rar"]), timeout_duration=15)
    log("MD5: %s" % md5hash)

    file_token = get_file_token(md5hash)
    filename = '.'.join(path.basename(item["file_original_path"]).split(".")[:-1])

    napi_helper = NapiProjektHelper(md5hash)
    results = napi_helper.search(item, file_token)

    log("Results: %s" % results)

    for result in results:
        listitem = xbmcgui.ListItem(label=xbmc.convertLanguage(result["language"], xbmc.ENGLISH_NAME),
                                    label2=filename)
        listitem.setArt({'icon': "5", 'thumb': xbmc.convertLanguage(result["language"], xbmc.ISO_639_1)})
        listitem.setProperty("sync", "true")
        listitem.setProperty("hearing_imp", "false")

        ## below arguments are optional, it can be used to pass any info needed in download function
        ## anything after "action=download&" will be sent to addon once user clicks listed subtitle to download
        url = "plugin://%s/?action=download&l=%s&h=%s" % (__scriptid__, result["language"], md5hash)
        ## add it to list, this can be done as many times as needed for all subtitles found
        xbmcplugin.addDirectoryItem(handle=int(argv[1]), url=url, listitem=listitem, isFolder=False)


def Download(language, hash):
    ## Cleanup temp dir, we recomend you download/unzip your subs in temp folder and
    ## pass that to XBMC to copy and activate
    if xbmcvfs.exists(__temp__):
        (dirs, files) = xbmcvfs.listdir(__temp__)
        for file in files:
            xbmcvfs.delete(path.join(__temp__, file))
    else:
        xbmcvfs.mkdirs(__temp__)

    napi_helper = NapiProjektHelper(hash)
    subtitle_list = napi_helper.download(language)

    return subtitle_list


def normalizeString(str):
    return normalize('NFKD', str)


def get_params():
    param = []
    paramstring = argv[2]
    if len(paramstring) >= 2:
        params = paramstring
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


params = get_params()

if params['action'] == 'search':
    item = {}
    item['temp'] = False
    item['rar'] = False
    item['year'] = xbmc.getInfoLabel("VideoPlayer.Year")  # Year
    item['season'] = str(xbmc.getInfoLabel("VideoPlayer.Season"))  # Season
    item['episode'] = str(xbmc.getInfoLabel("VideoPlayer.Episode"))  # Episode
    item['tvshow'] = normalizeString(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))  # Show
    item['title'] = normalizeString(xbmc.getInfoLabel("VideoPlayer.OriginalTitle"))  # try to get original title
    item['file_original_path'] = unquote(xbmc.Player().getPlayingFile())  # Full path of a playing file
    item['3let_language'] = []
    item['preferredlanguage'] = unquote(params.get('preferredlanguage', ''))
    item['preferredlanguage'] = xbmc.convertLanguage(item['preferredlanguage'], xbmc.ISO_639_2)

    for lang in unquote(params['languages']).split(","):
        item['3let_language'].append(xbmc.convertLanguage(lang, xbmc.ISO_639_2))

    if item['title'] == "":
        item['title'] = normalizeString(xbmc.getInfoLabel("VideoPlayer.Title"))  # no original title, get just Title

    if item['episode'].lower().find("s") > -1:  # Check if season is "Special"
        item['season'] = "0"  #
        item['episode'] = item['episode'][-1:]

    if (item['file_original_path'].find("http") > -1):
        item['temp'] = True

    elif (item['file_original_path'].find("rar://") > -1):
        item['rar'] = True
        item['file_original_path'] = path.dirname(item['file_original_path'][6:])

    elif (item['file_original_path'].find("stack://") > -1):
        stackPath = item['file_original_path'].split(" , ")
        item['file_original_path'] = stackPath[0][8:]

    log("Item: %s" % item)

    Search(item)

elif params['action'] == 'download':
    ## we pickup all our arguments sent from def Search()
    subs = Download(params["l"], params["h"])
    ## we can return more than one subtitle for multi CD versions, for now we are still working out how to handle that in XBMC core
    for sub in subs:
        listitem = xbmcgui.ListItem(label=sub)
        xbmcplugin.addDirectoryItem(handle=int(argv[1]), url=sub, listitem=listitem, isFolder=False)

xbmcplugin.endOfDirectory(int(argv[1]))  ## send end of directory to XBMC
