# -*- coding: utf-8 -*-
import os
import sys
from urllib.parse import unquote

try:
    import xbmc
    import xbmcvfs
    import xbmcaddon
    import xbmcplugin
    import xbmcgui
except ImportError:
    from tests.stubs import xbmc, xbmcgui, xbmcaddon, xbmcplugin, xbmcvfs

__addon__ = xbmcaddon.Addon()
__scriptid__ = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')
__language__ = __addon__.getLocalizedString

__cwd__ = xbmc.translatePath(__addon__.getAddonInfo('path'))
__profile__ = xbmc.translatePath(__addon__.getAddonInfo('profile'))
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib'))
__temp__ = xbmc.translatePath(os.path.join(__profile__, 'temp', ''))


from resources.lib.NapisyUtils import NapisyHelper, log, normalizeString, clean_title, parse_rls_title


def search(item):
    helper = NapisyHelper()
    subtitles_list = helper.get_subtitle_list(item)

    if subtitles_list:
        for it in subtitles_list:
            listitem = xbmcgui.ListItem(label=it["language_name"],
                                        label2=it["filename"])
            listitem.setArt({'icon': str(it["rating"]), 'thumb': it["language_flag"]})

            if it["sync"]:
                listitem.setProperty("sync", "true")
            else:
                listitem.setProperty("sync", "false")

            if it.get("hearing_imp", False):
                listitem.setProperty("hearing_imp", "true")
            else:
                listitem.setProperty("hearing_imp", "false")

            url = "plugin://%s/?action=download&id=%s" % (__scriptid__, it["id"])
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=listitem, isFolder=False)
    return


def download(sub_id):  # standard input
    subtitle_list = []
    exts = [".srt", ".sub", ".txt"]

    zip_filename = os.path.join(__temp__, "subs.zip")

    helper = NapisyHelper()
    helper.download(sub_id, zip_filename)

    for file in xbmcvfs.listdir(__temp__)[1]:
        full_path = os.path.join(__temp__, file)
        if os.path.splitext(full_path)[1] in exts:
            subtitle_list.append(full_path)

    return subtitle_list


def get_params():
    param = []
    paramstring = sys.argv[2]
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

if params['action'] in ['search', 'manualsearch']:
    item = {}
    item['temp'] = False
    item['rar'] = False
    item['year'] = xbmc.getInfoLabel("VideoPlayer.Year")  # Year
    item['season'] = str(xbmc.getInfoLabel("VideoPlayer.Season"))  # Season
    item['episode'] = str(xbmc.getInfoLabel("VideoPlayer.Episode"))  # Episode
    item['tvshow'] = normalizeString(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))  # Show
    item['title'] = normalizeString(xbmc.getInfoLabel("VideoPlayer.OriginalTitle"))  # try to get original title
    item['file_original_path'] = unquote(xbmc.Player().getPlayingFile())  # Full path of a playing file
    item['file_original_name'] = os.path.basename(item['file_original_path'])  # Name of playing file
    item['3let_language'] = []
    item['preferredlanguage'] = unquote(params.get('preferredlanguage', ''))
    item['preferredlanguage'] = xbmc.convertLanguage(item['preferredlanguage'], xbmc.ISO_639_2)

    for lang in unquote(params['languages']).split(","):
        item['3let_language'].append(xbmc.convertLanguage(lang, xbmc.ISO_639_2))

    if item['title'] == "":
        log("VideoPlayer.OriginalTitle not found")
        item['title'] = normalizeString(xbmc.getInfoLabel("VideoPlayer.Title"))  # no original title, get just Title

    if params['action'] == 'manualsearch':
        if item['season'] != '' or item['episode']:
            item['tvshow'] = unquote(params['searchstring'])
        else:
            item['title'] = unquote(params['searchstring'])

    for lang in unquote(params['languages']).split(","):
        item['3let_language'].append(xbmc.convertLanguage(lang, xbmc.ISO_639_2))

    log("Item before cleaning: \n    %s" % item)

    # clean title + tvshow params
    clean_title(item)
    parse_rls_title(item)

    if item['episode'].lower().find("s") > -1:  # Check if season is "Special"
        item['season'] = "0"
        item['episode'] = item['episode'][-1:]

    if (item['file_original_path'].find("http") > -1):
        item['temp'] = True

    elif (item['file_original_path'].find("rar://") > -1):
        item['rar'] = True
        item['file_original_path'] = os.path.dirname(item['file_original_path'][6:])

    elif (item['file_original_path'].find("stack://") > -1):
        stackPath = item['file_original_path'].split(" , ")
        item['file_original_path'] = stackPath[0][8:]

    item["file_original_size"] = xbmcvfs.File(item["file_original_path"]).size()

    log("item: %s" % (item))

    search(item)

elif params['action'] == 'download':
    ## we pickup all our arguments sent from def search()
    subs = download(params["id"])

    ## we can return more than one subtitle for multi CD versions, for now we are still working out how to handle that in XBMC core
    for sub in subs:
        listitem = xbmcgui.ListItem(label=sub)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=sub, listitem=listitem, isFolder=False)

elif params['action'] == 'login':
    helper = NapisyHelper()
    helper.login(True)
    __addon__.openSettings()

xbmcplugin.endOfDirectory(int(sys.argv[1]))  ## send end of directory to XBMC
