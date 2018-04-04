# -*- coding: utf-8 -*- 

import codecs
import glob
import os
import shutil
import sys
import time
import urllib

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

__addon__ = xbmcaddon.Addon()
__author__ = __addon__.getAddonInfo('author')
__scriptid__ = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')
__language__ = __addon__.getLocalizedString

__cwd__ = xbmc.translatePath(__addon__.getAddonInfo('path')).decode("utf-8")
__profile__ = xbmc.translatePath(
    __addon__.getAddonInfo('profile')
).decode("utf-8")
__resource__ = xbmc.translatePath(
    os.path.join(__cwd__, 'resources', 'lib')
).decode("utf-8")
__temp__ = xbmc.translatePath(
    os.path.join(__profile__, 'temp')
).decode("utf-8")

if xbmcvfs.exists(__temp__):
    shutil.rmtree(__temp__)
xbmcvfs.mkdirs(__temp__)

sys.path.append(__resource__)

from SubtitleHelper import log, normalize_string, convert_to_utf, check_and_parse_if_title_is_TVshow, take_title_from_focused_item, parse_rls_title, clean_title
from TorecSubtitlesDownloader import TorecSubtitlesDownloader

def search(item):
    best_match_id = None
    downloader = TorecSubtitlesDownloader()
    subtitles_options = None
    
    start_time = time.time()

    try:
        search_start_time = time.time()
        
        if (item['mansearch'] == False):
            if item['tvshow'] != "":
                subtitles_options = downloader.search_tvshow(item['tvshow'], item['season'], item['episode'])
            else:              
                title, year = xbmc.getCleanMovieTitle(item['title'])
                subtitles_options = downloader.search_movie(title)
        else:
            item['tvshow'], item['season'], item['episode'] = check_and_parse_if_title_is_TVshow(item['title'])
            if (item['tvshow'] == "NotTVShow"):
                item['title'] = item['title'].replace("%20", "%2b") # " " to "+"
                title, year = xbmc.getCleanMovieTitle(item['title'])
                subtitles_options = downloader.search_movie(title)
            else:
                subtitles_options = downloader.search_tvshow(item['tvshow'], int(item['season']), int(item['episode']))
                                    
        log(__name__, "search took %f" % (time.time() - search_start_time))
    except Exception as e:
        log(
            __name__,
            "failed to connect to service for subtitle search %s" % e
        )
        xbmc.executebuiltin(
            (u'Notification(%s,%s)' % (__scriptname__, __language__(32001))
             ).encode('utf-8'))
        return
    
    list_items = []
    if subtitles_options:
        best_match_option_id = downloader.get_best_match_id(
            os.path.basename(item['file_original_path']), subtitles_options
        )

        for item_data in subtitles_options:
            listitem = xbmcgui.ListItem(
                label="Hebrew", label2=item_data.name, iconImage="0",
                thumbnailImage="he"
            )
            url = (
                "plugin://%s/?action=download&sub_id=%s&option_id="
                "%s&filename=%s" % (
                    __scriptid__, item_data.sub_id, item_data.option_id, item_data.name
                )
            )

            if item_data.option_id == best_match_option_id:
                log(
                    __name__, "Found most relevant option to be : %s" %
                              item_data.name
                )
                listitem.setProperty("sync", "true")
                list_items.insert(0, (url, listitem, False,))
            else:
                list_items.append((url, listitem, False,))

    xbmcplugin.addDirectoryItems(handle=int(sys.argv[1]), items=list_items)
    log(__name__, "Overall search took %f" % (time.time() - start_time))


def delete_old_subs():
    files = glob.glob(os.path.join(__temp__, u"*.srt"))
    for f in files:
        log(__name__, "deleting %s" % f)
        os.remove(f)


def download(sub_id, option_id, filename, stack=False):
    result = None
    subtitle_list = []
    exts = [".srt", ".sub"]
    downloader = TorecSubtitlesDownloader()
    start_time = time.time()

    delete_old_subs()

    try:
        result = downloader.get_download_link(sub_id, option_id)
    except Exception as e:
        log(__name__,"failed to connect to service for subtitle download %s" % e)
        return subtitle_list
        
    if result is not None:
        log(__name__, "Downloading subtitles from '%s'" % result)
        
        (subtitle_data, subtitle_name) = downloader.download(result)
        (file_name, file_ext) = os.path.splitext(subtitle_name)
        archive_file = os.path.join(__temp__, "Torec%s" % file_ext)
        with open(archive_file, "wb") as subFile:
            subFile.write(subtitle_data)

        xbmc.executebuiltin(
            ('XBMC.Extract("%s","%s")' % (archive_file, __temp__,)
             ).encode('utf-8'), True)

        for file_ in xbmcvfs.listdir(__temp__)[1]:
            ufile = file_.decode('utf-8')
            log(__name__, "file=%s" % ufile)
            file_ = os.path.join(__temp__, ufile)
            if os.path.splitext(ufile)[1] in exts:
                convert_to_utf(file_)
                subtitle_list.append(file_)
      
    log(__name__, "Overall download took %f" % (time.time() - start_time))
    return subtitle_list
    
    
def get_params(string=""):
    param = []
    if string == "":
        paramstring = sys.argv[2]
    else:
        paramstring = string
    if len(paramstring) >= 2:
        params = paramstring
        cleanedparams = params.replace('?', '')
        if params[len(params)-1]=='/':
            params = params[0:len(params)-2]
        pairsofparams = cleanedparams.split('&')
        param = {}
        for i in range(len(pairsofparams)):
            splitparams = {}
            splitparams = pairsofparams[i].split('=')
            if len(splitparams) == 2:
                param[splitparams[0]] = splitparams[1]

    return param

params = get_params()

if params['action'] == 'search' or params['action'] == 'manualsearch':
    log(__name__, "action '%s' called" % params['action'])
    item = dict()

    if xbmc.Player().isPlaying():
        item['temp'] = False
        item['rar'] = False
        item['mansearch'] = False
        item['year'] = xbmc.getInfoLabel("VideoPlayer.Year")  # Year
        item['season'] = str(xbmc.getInfoLabel("VideoPlayer.Season"))  # Season
        item['episode'] = str(xbmc.getInfoLabel("VideoPlayer.Episode"))  # Episode
        item['tvshow'] = normalize_string(xbmc.getInfoLabel(
            "VideoPlayer.TVshowtitle")
        )  # Show
        item['title'] = normalize_string(xbmc.getInfoLabel(
            "VideoPlayer.OriginalTitle")
        )  # try to get original title
        item['file_original_path'] = urllib.unquote(
            xbmc.Player().getPlayingFile().decode('utf-8')
        )  # Full path of a playing file
        item['3let_language'] = []
    else:
        item['temp'] = False
        item['rar'] = False
        item['year'] = ""
        item['season'] = ""
        item['episode'] = ""
        item['tvshow'] = ""
        item['title'] = take_title_from_focused_item()
        item['mansearch'] = True
        item['file_original_path'] = ""
        item['3let_language'] = []

    if item['title'] == "":
        log(__name__, "VideoPlayer.OriginalTitle not found")
        item['title'] = normalize_string(xbmc.getInfoLabel("VideoPlayer.Title"))  # no original title, get just Title

    if 'searchstring' in params:
        item['mansearch'] = True
        item['title'] = params['searchstring']

    for lang in unicode(urllib.unquote(params['languages']), 'utf-8').split(","):
        item['3let_language'].append(xbmc.convertLanguage(lang, xbmc.ISO_639_2))

    if xbmc.Player().isPlaying():
        log(__name__, "Item before cleaning: \n    %s" % item)
        # clean title + tvshow params
        clean_title(item)
        parse_rls_title(item)

    if item['episode'].lower().find("s") > -1:  # Check if season is "Special"
        item['season'] = "0"
        item['episode'] = item['episode'][-1:]

    if item['file_original_path'].find("http") > -1:
        item['temp'] = True

    elif item['file_original_path'].find("rar://") > -1:
        item['rar'] = True
        item['file_original_path'] = os.path.dirname(
            item['file_original_path'][6:]
        )

    elif item['file_original_path'].find("stack://") > -1:
        stack_path = item['file_original_path'].split(" , ")
        item['file_original_path'] = stack_path[0][8:]

    log(__scriptname__, "%s" % item)
    search(item)

elif params['action'] == 'download':
    subs = download(params["sub_id"], params["option_id"], params["filename"])
    for sub in subs:
        listitem = xbmcgui.ListItem(label=sub)
        xbmcplugin.addDirectoryItem(
            handle=int(sys.argv[1]), url=sub, listitem=listitem,
            isFolder=False
        )

xbmcplugin.endOfDirectory(int(sys.argv[1]))

