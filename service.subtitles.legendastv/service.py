import os
import shutil
import sys
import uuid
from urllib.parse import unquote_plus

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

from resources.lib.LTVutilities import \
    getMovieIMDB, \
    getShowIMDB, \
    getShowId, \
    getTVShowOrginalTitle, \
    getMovieOriginalTitle, \
    extractArchiveToFolder
from resources.lib.LegendasTV import *

__addon__ = xbmcaddon.Addon()
__author__ = __addon__.getAddonInfo('author')
__scriptid__ = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')
__language__ = __addon__.getLocalizedString

__cwd__ = xbmcvfs.translatePath(__addon__.getAddonInfo('path'))
__profile__ = xbmcvfs.translatePath(__addon__.getAddonInfo('profile'))
__temp__ = xbmcvfs.translatePath(os.path.join(__profile__, 'temp', ''))

__search__ = __addon__.getSetting('SEARCH')
__username__ = __addon__.getSetting('USERNAME')
__password__ = __addon__.getSetting('PASSWORD')

if xbmcvfs.exists(__temp__):
    shutil.rmtree(__temp__)
xbmcvfs.mkdirs(__temp__)

LTV = LegendasTV()
LTV.Log = log


def Search(item):  # standard input

    enable_rar()
    enable_libarchive()

    try:
        subtitles = LTV.Search(title=item['title'],
                               tvshow=item['tvshow'],
                               year=item['year'],
                               season=item['season'],
                               episode=item['episode'],
                               lang=item['languages'],
                               imdb=item['imdb'])
    except:
        import traceback
        log("\n%s" % traceback.format_exc(), "ERROR")
        return 1

    if subtitles:
        for it in subtitles:
            if it['type'] == "destaque":
                label = "[COLOR FFDE7B18]%s[/COLOR]" % it["filename"]
            else:
                label = it["filename"]

            listitem = xbmcgui.ListItem(
                label=it["language_name"],
                label2=label)
            listitem.setArt({
                "icon": str(int(round(float(it["rating"]) / 2))),
                "thumb": it["language_flag"]
            })
            if it["sync"]:
                listitem.setProperty("sync", "true")
            else:
                listitem.setProperty("sync", "false")
            if it.get("hearing_imp", False):
                listitem.setProperty("hearing_imp", "true")
            else:
                listitem.setProperty("hearing_imp", "false")
            url = "plugin://%s/?action=download&download_url=%s&filename=%s" % (
                __scriptid__,
                it["url"],
                os.path.basename(item["file_original_path"]))

            xbmcplugin.addDirectoryItem(
                handle=int(sys.argv[1]),
                url=url,
                listitem=listitem,
                isFolder=False)

    if item['original_title'] != "true":
        listitem = xbmcgui.ListItem(label="",
                                    label2=__language__(32011))
        searchstring = "&searchstring=%s" % \
                       item['searchstring'] if "searchstring" in item else ""
        url = "plugin://%s/?action=search&original_title=true&languages=%s%s" % (
            __scriptid__,
            quote_plus(",".join(item["languages"])),
            quote_plus(searchstring)
        )
        xbmcplugin.addDirectoryItem(
            handle=int(sys.argv[1]),
            url=url,
            listitem=listitem,
            isFolder=False)


def xbmc_walk(DIR):
    LIST = []
    dirs, files = xbmcvfs.listdir(DIR)
    for file in files:
        ext = os.path.splitext(file)[1][1:].lower()
        if ext in sub_ext:
            LIST.append(os.path.join(DIR, file))
    for dir in dirs:
        LIST.extend(list(xbmc_walk(os.path.join(DIR, dir))))
    return LIST


def Download(url, filename):  # standard input
    # Create some variables
    subtitles = []
    random = uuid.uuid4().hex

    if xbmcvfs.exists(__temp__):
        shutil.rmtree(__temp__)
    xbmcvfs.mkdirs(__temp__)

    extractPath = os.path.join(__temp__, "Extracted")
    if not xbmcvfs.exists(extractPath):
        xbmcvfs.mkdirs(extractPath)

    FileContent, FileExt = LTV.Download(url)

    fname = "%s.%s" % (os.path.join(__temp__, random), FileExt)

    with open(fname, 'wb') as f:
        f.write(FileContent)

    path = quote_plus(xbmcvfs.translatePath(fname))
    protocol = FileExt if FileExt in ("zip", "rar") else "archive"

    if protocol == "rar" and not is_rar_enabled():
        dialog = xbmcgui.Dialog()
        dialog.ok(
            __language__(32012),
            "%s\n%s" % (__language__(32013), __language__(32014)))
        return []

    translated_archive_url = f'{protocol}://{path}'
    extractedFileList, success = extractArchiveToFolder(
        translated_archive_url,
        extractPath)

    files = xbmc_walk(extractPath)

    temp = []
    for file in files:
        file = unquote_plus(file)
        sub, ext = os.path.splitext(os.path.basename(file))
        sub_striped = LTV.CleanLTVTitle(sub)
        Ratio = LTV.CalculateRatio(sub_striped, LTV.CleanLTVTitle(filename))
        temp.append([Ratio, file, sub, ext])

    subtitles = sorted(temp, reverse=True)
    outputSub = []

    if len(subtitles) > 1:
        dialog = xbmcgui.Dialog()
        sel = dialog.select(
            "%s\n%s" % (__language__(32001), filename),
            [os.path.basename(b) for a, b, c, d in subtitles])
        if sel >= 0:
            subSelected = subtitles[sel][1]
            temp_sel = os.path.join(extractPath,
                                    "%s.%s" % (random, subtitles[sel][3]))
            xbmcvfs.copy(subSelected, temp_sel)
            outputSub.append(temp_sel)
    elif len(subtitles) == 1:
        subSelected = subtitles[0][1]
        temp_sel = os.path.join(extractPath,
                                "%s.%s" % (random, subtitles[0][3]))
        xbmcvfs.copy(subSelected, temp_sel)
        outputSub.append(temp_sel)

    return outputSub


def get_params(string=""):
    param = []
    if string == "":
        paramstring = sys.argv[2]
    else:
        paramstring = string
    if len(paramstring) >= 2:
        params = paramstring
        cleanedparams = params.replace('?', '')
        if params[len(params) - 1] == '/':
            params = params[0:len(params) - 2]
        pairsofparams = cleanedparams.split('&')
        param = {}
        for i in range(len(pairsofparams)):
            splitparams = pairsofparams[i].split('=')
            if (len(splitparams)) == 2:
                param[splitparams[0]] = splitparams[1]
    log("Parameters: %s" % param)
    return param

def is_rar_enabled():
    log("Checking if vfs.rar is enabled")
    q = '{' \
        '   "jsonrpc": "2.0",' \
        '   "method": "Addons.GetAddonDetails",' \
        '   "params": {' \
        '       "addonid": "vfs.rar",' \
        '       "properties": [' \
        '           "enabled"' \
        '       ]' \
        '   },' \
        '   "id": 0' \
        '}'
    r = json.loads(xbmc.executeJSONRPC(q))
    log(xbmc.executeJSONRPC(q))
    if "result" in r and "addon" in r["result"]:
        return r["result"]["addon"]["enabled"]
    return False


def enable_rar():
    if not is_rar_enabled():
        xbmc.executeJSONRPC(
            '{'
            '   "jsonrpc": "2.0",'
            '   "method": "Addons.SetAddonEnabled",'
            '   "params": {'
            '       "addonid": "vfs.rar",'
            '       "enabled": true'
            '   }'
            '}')
        xbmc.sleep(1000)
        if not is_rar_enabled():
            dialog = xbmcgui.Dialog()
            dialog.ok(
                __language__(32012),
                "%s\n%s" % (__language__(32013), __language__(32014)))


def is_libarchive_enabled():
    log("Checking if vfs.libarchive is enabled")
    q = '{' \
        '   "jsonrpc": "2.0",' \
        '   "method": "Addons.GetAddonDetails",' \
        '   "params": {' \
        '       "addonid": "vfs.libarchive",' \
        '       "properties": [' \
        '           "enabled"' \
        '       ]' \
        '   },' \
        '   "id": 0' \
        '}'
    r = json.loads(xbmc.executeJSONRPC(q))
    log(xbmc.executeJSONRPC(q))
    if "result" in r and "addon" in r["result"]:
        return r['result']["addon"]["enabled"]
    return False


def enable_libarchive():
    if not is_libarchive_enabled():
        xbmc.executeJSONRPC(
            '{'
            '   "jsonrpc": "2.0",'
            '   "method": "Addons.SetAddonEnabled",'
            '   "params": {'
            '       "addonid": "vfs.libarchive",'
            '       "enabled": true'
            '   }'
            '}')
        xbmc.sleep(1000)
        if not is_libarchive_enabled():
            log(
                "vfs.libarchive not enabled. Some archive types might not work",
                "INFO")


params = get_params()
log("Version: %s" % __version__)
log("Action '%s' called" % params['action'])

if params['action'] == 'search' or params['action'] == 'manualsearch':
    item = {}
    item['temp'] = False
    item['rar'] = False
    item['year'] = xbmc.getInfoLabel("VideoPlayer.Year")  # Year
    item['season'] = str(xbmc.getInfoLabel("VideoPlayer.Season"))  # Season
    item['episode'] = str(xbmc.getInfoLabel("VideoPlayer.Episode"))  # Episode
    item['tvshow'] = normalizeString(
        xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))  # Show
    # Try to get original title
    item['title'] = normalizeString(
        xbmc.getInfoLabel("VideoPlayer.OriginalTitle"))
    # Full path of a playing file
    item['file_original_path'] = unquote_plus(xbmc.Player().getPlayingFile())
    item['languages'] = []  # ['scc','eng']
    item["languages"].extend(unquote_plus(params['languages']).split(","))
    item["original_title"] = "true" if "original_title" in params else "false"

    if not item['title']:
        log("VideoPlayer.OriginalTitle not found")
        item['title'] = normalizeString(xbmc.getInfoLabel("VideoPlayer.Title"))

    if item['tvshow']:
        item["imdb"] = getShowIMDB()
    else:
        item["imdb"] = getMovieIMDB()

    if item["original_title"] == "true":
        if item['tvshow']:
            item['tvshow'] = getTVShowOrginalTitle(item["tvshow"], getShowId())
        else:
            item['title'] = getMovieOriginalTitle(item["title"], item["imdb"])

    if 'searchstring' in params:
        item["searchstring"] = unquote_plus(params['searchstring'])
        if item['tvshow']:
            item['tvshow'] = item["searchstring"]
        elif item['title']:
            item['title'] = item["searchstring"]

    langtemp = []
    for lang in item["languages"]:
        if __search__ == '0':
            if lang == "Portuguese (Brazil)":
                langtemp.append((0, lang))
            elif lang == "Portuguese":
                langtemp.append((1, lang))
            elif lang == "English":
                langtemp.append((2, lang))
            else:
                langtemp.append((3, lang))
        elif __search__ == '1':
            if lang == "Portuguese (Brazil)":
                langtemp.append((1, lang))
            elif lang == "Portuguese":
                langtemp.append((0, lang))
            elif lang == "English":
                langtemp.append((2, lang))
            else:
                langtemp.append((3, lang))
        elif __search__ == '2':
            if lang == "Portuguese (Brazil)":
                langtemp.append((1, lang))
            elif lang == "Portuguese":
                langtemp.append((2, lang))
            elif lang == "English":
                langtemp.append((0, lang))
            else:
                langtemp.append((3, lang))
        elif __search__ == '3':
            if lang == "Portuguese (Brazil)":
                langtemp.append((1, lang))
            elif lang == "Portuguese":
                langtemp.append((2, lang))
            elif lang == "English":
                langtemp.append((3, lang))
            else:
                langtemp.append((0, lang))
    langtemp = sorted(langtemp)
    item["languages"] = []
    for a, b in langtemp:
        item["languages"].append(b)

    if item['episode'].lower().find("s") > -1:  # Check if season is "Special"
        item['season'] = "0"
        item['episode'] = item['episode'][-1:]

    if item['file_original_path'].find("http") > -1:
        item['temp'] = True

    elif item['file_original_path'].find("rar://") > -1:
        item['rar'] = True
        item['file_original_path'] = os.path.dirname(
            item['file_original_path'][6:])

    elif item['file_original_path'].find("stack://") > -1:
        stackPath = item['file_original_path'].split(" , ")
        item['file_original_path'] = stackPath[0][8:]

    Search(item)

elif params['action'] == 'download':
    Cookie = LTV.login(__username__, __password__)
    
    if Cookie is None:  
        dialog = xbmcgui.Dialog()
        ok = dialog.ok('Kodi', 'Usuário ou senha inválidos.')
    else:
        try:
            subs = Download(
                params["download_url"],
                params["filename"])
        except:
            subs = Download(
                params["download_url"],
                'filename')
        for sub in subs:
            listitem = xbmcgui.ListItem(label2=os.path.basename(sub))
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=sub,
                                        listitem=listitem, isFolder=False)

xbmcplugin.endOfDirectory(int(sys.argv[1]))
