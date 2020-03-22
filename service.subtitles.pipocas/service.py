# -*- coding: UTF-8 -*-
# Service Pipocas.tv
# Code based on Undertext (FRODO) service
# Coded by HiGhLaNdR@OLDSCHOOL
# Ported to Gotham by HiGhLaNdR@OLDSCHOOL
# Helped by VaRaTRoN, Mafarricos and Leinad4Mind
# Bugs & Features to highlander@teknorage.com
# https://www.teknorage.com
# License: GPL v2


import os
from os.path import join as pjoin
import re
import shutil
import sys
import string
import time
import urllib
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs
import uuid
import requests
from platform import system, architecture, machine, release, version
from operator import itemgetter

OS_SYSTEM = system()
OS_ARCH_BIT = architecture()[0]
OS_ARCH_LINK = architecture()[1]
OS_MACHINE = machine()
OS_RELEASE = release()
OS_VERSION = version()
OS_DETECT = OS_SYSTEM + '-' + OS_ARCH_BIT + '-' + OS_ARCH_LINK
OS_DETECT += ' | host: [%s][%s][%s]' %(OS_MACHINE, OS_RELEASE, OS_VERSION)

main_url = 'https://pipocas.tv/'
debug_pretext = 'Pipocas'

_addon      = xbmcaddon.Addon()
_author     = _addon.getAddonInfo('author')
_scriptid   = _addon.getAddonInfo('id')
_scriptname = _addon.getAddonInfo('name')
_version    = _addon.getAddonInfo('version')
_language   = _addon.getLocalizedString
_dialog     = xbmcgui.Dialog()

_cwd        = xbmc.translatePath(_addon.getAddonInfo('path')).decode('utf-8')
_profile    = xbmc.translatePath(_addon.getAddonInfo('profile')).decode('utf-8')
_resource   = xbmc.translatePath(pjoin(_cwd, 'resources', 'lib')).decode('utf-8')
_temp       = xbmc.translatePath(pjoin(_profile, 'temp'))

sys.path.append(_resource)
from pipocas import *

_search = _addon.getSetting('SEARCH')
debug   = _addon.getSetting('DEBUG')
# Grabbing login and pass from xbmc settings
username = _addon.getSetting('USERNAME')
password = _addon.getSetting('PASSWORD')

if os.path.isdir(_temp):
    shutil.rmtree(_temp)
xbmcvfs.mkdirs(_temp)
if not os.path.isdir(_temp):
    xbmcvfs.mkdir(_temp)


#SEARCH_PAGE_URL  = main_url + 'modules.php?name=Downloads&file=jz&d_op=search_next&order=&form_cat=28&page=%(page)s&query=%(query)s'
INTERNAL_LINK_URL = 'plugin://%(scriptid)s/?action=download&id=%(id)s&filename=%(filename)s'
HTTP_USER_AGENT   = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/525.13 (KHTML, like Gecko) Chrome/0.A.B.C Safari/525.13'

# ====================================================================================================================
# Regular expression patterns
# ====================================================================================================================

"""
"""
token_pattern = "<meta name=\"csrf-token\" content=\"(.+?)\">"
subtitle_pattern = "<a href=\"" + main_url + "legendas/info/(.+?)\" class=\"text-dark no-decoration\">"
name_pattern = "<h3 class=\"title\" style=\"word-break: break-all;\">Release: <span class=\"font-normal\">(.+?)<\/span><\/h3>"
id_pattern = "legendas/download/(.+?)\""
hits_pattern = "<span class=\"hits hits-pd\"><div><i class=\"fa fa-cloud-download\" aria-hidden=\"true\"></i> (.+?)</div></span>"
#desc_pattern = "<div class=\"description-box\">([\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*)<center><iframe"
uploader_pattern = "<span style=\"color:\s#[A-Za-z0-9]+?\"\s*>([A-Za-z0-9]+?)</span></a></b>"
release_pattern = "([^\W]\w{1,}\.{1,1}[^\.|^\ ][\w{1,}\.|\-|\(\d\d\d\d\)|\[\d\d\d\d\]]{3,}[\w{3,}\-|\.{1,1}]\w{2,})"
release_pattern1 = "([^\W][\w\ ]{4,}[^\Ws][x264|xvid]{1,}-[\w]{1,})"



def getallsubs(searchstring, languageshort, languagelong, file_original_path, searchstring_notclean):
    subtitles_list = []

    # LOGIN FIRST AND THEN SEARCH
    url = main_url + 'login'
    # GET CSRF TOKEN
    req_headers = {
        'User-Agent': HTTP_USER_AGENT,
        'Referer': url,
        'Keep-Alive': '300',
        'Connection': 'keep-alive'
    }
    sessionPipocasTv = requests.Session()
    result = sessionPipocasTv.get(url)

    if result.status_code != 200:
        _dialog.notification(_scriptname, _language(32019).encode('utf8'), xbmcgui.NOTIFICATION_ERROR)
        return []

    token = re.search(token_pattern, result.text)

    # LOGIN NOW
    payload = {
        "username": username,
        "password": password,
        "_token": token.group(1),
    }

    loginResult = sessionPipocasTv.post(
        url,
        data=payload,
        headers=req_headers
    )

    if loginResult.status_code != 200:
        _dialog.notification(_scriptname, _language(32019).encode('utf8'), xbmcgui.NOTIFICATION_ERROR)
        return []

    page = 1
    if languageshort == "pt":
        url = main_url + "legendas?t=rel&l=portugues&page=" + str(page) + "&s=" + urllib.quote_plus(searchstring)
    elif languageshort == "pb":
        url = main_url + "legendas?t=rel&l=brasileiro&page=" + str(page) + "&s=" + urllib.quote_plus(searchstring)
    elif languageshort == "es":
        url = main_url + "legendas?t=rel&l=espanhol&page=" + str(page) + "&s=" + urllib.quote_plus(searchstring)
    elif languageshort == "en":
        url = main_url + "legendas?t=rel&l=ingles&page=" + str(page) + "&s=" + urllib.quote_plus(searchstring)
    else:
        url = main_url + "home"

    content = sessionPipocasTv.get(url)

    if 'Cria uma conta' in content.text:
        _dialog.notification(_scriptname, _language(32019).encode('utf8'), xbmcgui.NOTIFICATION_ERROR)
        return []

    while re.search(subtitle_pattern, content.text, re.IGNORECASE | re.DOTALL) and page < 2:
        log("Getting '%s' inside while ..." % subtitle_pattern)
        for matches in re.finditer(subtitle_pattern, content.text, re.IGNORECASE | re.DOTALL):
            details = matches.group(1)
            content_details = sessionPipocasTv.get(main_url + "legendas/info/" + details)
            for namematch in re.finditer(name_pattern, content_details.text, re.IGNORECASE | re.DOTALL):
                filename = string.strip(namematch.group(1))
                desc = filename
                log("FILENAME match: '%s' ..." % namematch.group(1))
            for idmatch in re.finditer(id_pattern, content_details.text, re.IGNORECASE | re.DOTALL):
                id = idmatch.group(1)
                log("ID match: '%s' ..." % idmatch.group(1))
            uploader = ""
            for upmatch in re.finditer(uploader_pattern, content_details.text, re.IGNORECASE | re.DOTALL):
                uploader = upmatch.group(1)
            if uploader == "":
                uploader = "Bot-Pipocas"
            for hitsmatch in re.finditer(hits_pattern, content_details.text, re.IGNORECASE | re.DOTALL):
                hits = hitsmatch.group(1)
            downloads = int(hits) / 100
            if (downloads > 5):
                downloads = 5
            filename = re.sub('\n', ' ', filename)
            desc = re.sub('\n', ' ', desc)
            # Remove HTML tags on the commentaries
            filename = re.sub(r'<[^<]+?>', '', filename)
            desc = re.sub(r'<[^<]+?>|[~]', '', desc)
            # Find filename on the comentaries to show sync label using filename or dirname (making it global for further usage)
            global filesearch
            filesearch = os.path.abspath(file_original_path)
            filesearch = os.path.split(filesearch)
            dirsearch = filesearch[0].split(os.sep)
            dirsearch_check = string.split(dirsearch[-1], '.')
            # PARENT FOLDER TWEAK DEFINED IN THE ADD-ON SETTINGS (AUTO | ALWAYS ON (DEACTIVATED) | OFF)
            _parentfolder = _addon.getSetting('PARENT')
            if _parentfolder == '0':
                if re.search(release_pattern, dirsearch[-1], re.IGNORECASE):
                    _parentfolder = '1'
                else:
                    _parentfolder = '2'
            if _parentfolder == '1':
                if re.search(dirsearch[-1], desc, re.IGNORECASE):
                    sync = True
                else:
                    sync = False
            if _parentfolder == '2':
                if (searchstring_notclean != ""):
                    sync = False
                    if string.lower(searchstring_notclean) in string.lower(desc):
                        sync = True
                else:
                    if (string.lower(dirsearch_check[-1]) == "rar") or (string.lower(dirsearch_check[-1]) == "cd1") or (string.lower(dirsearch_check[-1]) == "cd2"):
                        sync = False
                        if len(dirsearch) > 1 and dirsearch[1] != '':
                            if re.search(filesearch[1][:len(filesearch[1])-4], desc, re.IGNORECASE) or re.search(dirsearch[-2], desc, re.IGNORECASE):
                                sync = True
                        else:
                            if re.search(filesearch[1][:len(filesearch[1])-4], desc, re.IGNORECASE):
                                sync = True
                    else:
                        sync = False
                        if len(dirsearch) > 1 and dirsearch[1] != '':
                            if re.search(filesearch[1][:len(filesearch[1])-4], desc) or re.search(dirsearch[-1], desc, re.IGNORECASE):
                                sync = True
                        else:
                            if re.search(filesearch[1][:len(filesearch[1])-4], desc, re.IGNORECASE):
                                sync = True
            filename = filename + "  " + "hits: " + hits + " uploader: " + uploader
            subtitles_list.append({'rating': str(downloads), 'filename': filename, 'hits': hits, 'desc': desc,
                                   'sync': sync, 'id': id, 'language_short': languageshort, 'language_name': languagelong})
        page = page + 1
        if languageshort == "pt":
            url = main_url + "legendas?t=rel&l=portugues&page=" + str(page) + "&s=" + urllib.quote_plus(searchstring)
        elif languageshort == "pb":
            url = main_url + "legendas?t=rel&l=brasileiro&page=" + str(page) + "&s=" + urllib.quote_plus(searchstring)
        elif languageshort == "es":
            url = main_url + "legendas?t=rel&l=espanhol&page=" + str(page) + "&s=" + urllib.quote_plus(searchstring)
        elif languageshort == "en":
            url = main_url + "legendas?t=rel&l=ingles&page=" + str(page) + "&s=" + urllib.quote_plus(searchstring)
        else:
            url = main_url + "home"
        content = sessionPipocasTv.get(url)

    # Bubble sort, to put syncs on top
    subtitles_list = bubbleSort(subtitles_list)
    return subtitles_list


def append_subtitle(item):

    listitem = xbmcgui.ListItem(
        label=item['language_name'],
        label2=item['filename'],
        iconImage=item['rating'],
        thumbnailImage=item['language_short']
    )
    listitem.setProperty("sync", 'true' if item["sync"] else 'false')
    listitem.setProperty("hearing_imp", 'true' if item.get("hearing_imp", False) else 'false')

    # below arguments are optional, it can be used to pass any info needed in download function
    # anything after "action=download&" will be sent to addon once user clicks listed subtitle to downlaod
    args = dict(item)
    args['scriptid'] = _scriptid
    url = INTERNAL_LINK_URL % args
    # add it to list, this can be done as many times as needed for all subtitles found
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=listitem, isFolder=False)


def Search(item):
    log("Host data '%s'" % OS_DETECT)
    """Called when searching for subtitles from XBMC."""
    # Do what's needed to get the list of subtitles from service site
    # use item["some_property"] that was set earlier
    # once done, set xbmcgui.ListItem() below and pass it to xbmcplugin.addDirectoryItem()
    # CHECKING FOR ANYTHING IN THE USERNAME AND PASSWORD, IF NULL IT STOPS THE SCRIPT WITH A WARNING
    username = _addon.getSetting('USERNAME')
    password = _addon.getSetting('PASSWORD')
    if username == '' or password == '':
        xbmcplugin.endOfDirectory(int(sys.argv[1]))
        if username == '' and password != '':
            _dialog.notification(_scriptname, _language(32016).encode('utf8'), xbmcgui.NOTIFICATION_ERROR)
        if username != '' and password == '':
            _dialog.notification(_scriptname, _language(32017).encode('utf8'), xbmcgui.NOTIFICATION_ERROR)
        if username == '' and password == '':
            _dialog.notification(_scriptname, _language(32018).encode('utf8'), xbmcgui.NOTIFICATION_ERROR)
    # PARENT FOLDER TWEAK DEFINED IN THE ADD-ON SETTINGS (AUTO | ALWAYS ON (DEACTIVATED) | OFF)
    file_original_path = item['file_original_path']
    _parentfolder = _addon.getSetting('PARENT')
    if _parentfolder == '0':
        filename = os.path.abspath(file_original_path)
        dirsearch = filename.split(os.sep)
        log(u"dirsearch_search string = %s" % dirsearch)
        if re.search(release_pattern, dirsearch[-2], re.IGNORECASE):
            _parentfolder = '1'
        else:
            _parentfolder = '2'
    if _parentfolder == '1':
        filename = os.path.abspath(file_original_path)
        dirsearch = filename.split(os.sep)
        filename = dirsearch[-2]
        log(u"_parentfolder1 = %s" % filename)
    if _parentfolder == '2':
        filename = os.path.splitext(os.path.basename(file_original_path))[0]
        log(u"_parentfolder2 = %s" % filename)

    filename = xbmc.getCleanMovieTitle(filename)[0]
    searchstring_notclean = os.path.splitext(
        os.path.basename(file_original_path))[0]
    searchstring = ""
    log(u"_searchstring_notclean = %s" % searchstring_notclean)
    log(u"_searchstring = %s" % searchstring)
    global israr
    israr = os.path.abspath(file_original_path)
    israr = os.path.split(israr)
    israr = israr[0].split(os.sep)
    israr = string.split(israr[-1], '.')
    israr = string.lower(israr[-1])

    title = xbmc.getCleanMovieTitle(item['title'])[0]
    tvshow = item['tvshow']
    season = item['season']
    episode = item['episode']
    log(u"Tvshow string = %s" % tvshow)
    log(u"Title string = %s" % title)
    subtitles_list = []

    if item['mansearch']:
        searchstring = item['mansearchstr']
        log(u"Manual Searchstring string = %s" % searchstring)
    else:
        if tvshow != '':
            searchstring = "%s S%#02dE%#02d" % (tvshow, int(season), int(episode))
        elif title != '' and tvshow != '':
            searchstring = title
        else:
            if 'rar' in israr and searchstring is not None:
                log(u"RAR Searchstring string = %s" % searchstring)
                if 'cd1' in string.lower(title) or 'cd2' in string.lower(title) or 'cd3' in string.lower(title):
                    dirsearch = os.path.abspath(file_original_path)
                    dirsearch = os.path.split(dirsearch)
                    dirsearch = dirsearch[0].split(os.sep)
                    if len(dirsearch) > 1:
                        searchstring_notclean = dirsearch[-3]
                        searchstring = xbmc.getCleanMovieTitle(dirsearch[-3])
                        searchstring = searchstring[0]
                        log(u"RAR MULTI1 CD Searchstring string = %s" % searchstring)
                    else:
                        searchstring = title
                else:
                    searchstring = title
                    log(u"RAR NO CD Searchstring string = %s" % searchstring)
            elif 'cd1' in string.lower(title) or 'cd2' in string.lower(title) or 'cd3' in string.lower(title):
                dirsearch = os.path.abspath(file_original_path)
                dirsearch = os.path.split(dirsearch)
                dirsearch = dirsearch[0].split(os.sep)
                if len(dirsearch) > 1:
                    searchstring_notclean = dirsearch[-2]
                    searchstring = xbmc.getCleanMovieTitle(dirsearch[-2])
                    searchstring = searchstring[0]
                    log(u"MULTI1 CD Searchstring string = %s" % searchstring)
                else:
                    #We are at the root of the drive!!! so there's no dir to lookup only file#
                    title = os.path.split(file_original_path)
                    searchstring = title[-1]
            else:
                if title == '':
                    title = os.path.split(file_original_path)
                    searchstring = title[-1]
                    log(u"TITLE NULL Searchstring string = %s" % searchstring)
                else:
                    if _search == '0':
                        if re.search("(.+?s[0-9][0-9]e[0-9][0-9])", filename, re.IGNORECASE):
                            searchstring = re.search("(.+?s[0-9][0-9]e[0-9][0-9])", filename, re.IGNORECASE)
                            searchstring = searchstring.group(0)
                            log(u"FilenameTV Searchstring = %s" % searchstring)
                        else:
                            searchstring = filename
                            log(u"Filename Searchstring = %s" % searchstring)
                    else:
                        if re.search("(.+?s[0-9][0-9]e[0-9][0-9])", title, re.IGNORECASE):
                            searchstring = re.search("(.+?s[0-9][0-9]e[0-9][0-9])", title, re.IGNORECASE)
                            searchstring = searchstring.group(0)
                            log(u"TitleTV Searchstring = %s" % searchstring)
                        else:
                            searchstring = title
                            log(u"Title Searchstring = %s" % searchstring)

    PT_ON   = _addon.getSetting('PT')
    PTBR_ON = _addon.getSetting('PTBR')
    ES_ON   = _addon.getSetting('ES')
    EN_ON   = _addon.getSetting('EN')

    if PT_ON == 'true':
        subtitles_list = getallsubs(searchstring, "pt", "Portuguese", file_original_path, searchstring_notclean)
        for sub in subtitles_list:
            append_subtitle(sub)
    if PTBR_ON == 'true':
        subtitles_list = getallsubs(searchstring, "pb", "Brazilian", file_original_path, searchstring_notclean)
        for sub in subtitles_list:
            append_subtitle(sub)
    if ES_ON == 'true':
        subtitles_list = getallsubs(searchstring, "es", "Spanish", file_original_path, searchstring_notclean)
        for sub in subtitles_list:
            append_subtitle(sub)
    if EN_ON == 'true':
        subtitles_list = getallsubs(searchstring, "en", "English", file_original_path, searchstring_notclean)
        for sub in subtitles_list:
            append_subtitle(sub)
    if PT_ON == 'false' and PTBR_ON == 'false' and ES_ON == 'false' and EN_ON == 'false':
        # xbmc.executebuiltin((u'Notification(%s,%s,%d)' % (_scriptname , normalizeString('Apenas Português | Português Brasil | English | Spanish.'),5000)))
        _dialog.notification(_scriptname, normalizeString('Apenas Português | Português Brasil | English | Spanish'), xbmcgui.NOTIFICATION_ERROR)



def Download(id, filename):
    url = main_url + 'login'
    download = main_url + 'legendas/download/' + id
    # GET CSRF TOKEN
    req_headers = {
        'User-Agent': HTTP_USER_AGENT,
        'Referer': url,
        'Keep-Alive': '300',
        'Connection': 'keep-alive'
    }
    sessionPipocasTv = requests.Session()
    result = sessionPipocasTv.get(url)
    if not result.ok:
        return []
    token = re.search(token_pattern, result.text)

    # LOGIN NOW
    payload = {
        "username": username,
        "password": password,
        "_token": token.group(1),
    }

    loginResult = sessionPipocasTv.post(
        url,
        data=payload,
        headers=req_headers
    )
    if not loginResult.ok:
        return []

    content = sessionPipocasTv.get(download)
    if not content.ok:
        return []
    # If user is not registered or User\Pass is misspelled it will generate an error message and break the script execution!
    thecontent = content.content
    if 'Cria uma conta' in thecontent:
        xbmcplugin.endOfDirectory(int(sys.argv[1]))
        _dialog.notification(_scriptname, _language(32019).encode('utf8'), xbmcgui.NOTIFICATION_ERROR)
        return []

    if thecontent is not None:
        subtitles_list = []
        random = uuid.uuid4().hex
        cleanDirectory(_temp)

        # Check archive type (rar/zip/else) through the file header (rar=Rar!, zip=PK)
        log(u"Checking archive type")
        if thecontent[:4] == 'Rar!':
            extension = ".rar"
            archive_type = 'rar://'
            packed = True
            log(u"Discovered RAR Archive")
        elif thecontent[:2] == 'PK':
            extension = ".zip"
            archive_type = 'zip://'
            packed = True
            log(u"Discovered ZIP Archive")
        else:
            extension = ".srt"
            archive_type = ''
            packed = False
            log(u"Discovered a non-archive file")

        local_tmp_file = os.path.join(_temp, random + extension)

        try:
            log(u"Saving subtitles to '%s'" % local_tmp_file)

            with open(local_tmp_file,'wb') as local_file_handle:
                local_file_handle.write(thecontent)
            local_file_handle.close()

            log(u"Saving to %s" % local_tmp_file)
        except:
            log(u"Failed to save subtitle to %s" % local_tmp_file)

        if packed:
            time.sleep(2)
            extractedFileList, success = extract_it_all(local_tmp_file, _temp, archive_type, extension)

            temp = []
            for file in extractedFileList:
                sub = urllib.unquote_plus(file)
                sub, ext = os.path.splitext(os.path.basename(file))
                temp.append([file, sub, ext])

            subtitles = sorted(temp, key=itemgetter(1), reverse=False)
            subtitles_list = []

            if len(subtitles) > 1:
                sel = _dialog.select("FILES: %s" % filename, [y for x, y, z in subtitles])
                if sel >= 0:
                    subSelected = subtitles[sel][0]
                    subtitles_list.append(subSelected)
            elif len(subtitles) == 1:
                subSelected = subtitles[0][0]
                subtitles_list.append(subSelected)
        else:
            subtitles_list.append(local_tmp_file)

    return subtitles_list


# Get parameters from XBMC and launch actions
params = get_params()

if params['action'] == 'search' or params['action'] == 'manualsearch':
    item = {}
    item['temp'] = False
    item['rar'] = False
    item['year'] = xbmc.getInfoLabel("VideoPlayer.Year")                             # Year
    item['season'] = str(xbmc.getInfoLabel("VideoPlayer.Season"))                    # Season
    item['episode'] = str(xbmc.getInfoLabel("VideoPlayer.Episode"))                  # Episode
    item['tvshow'] = normalizeString(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))   # Show
    item['title'] = normalizeString(xbmc.getInfoLabel("VideoPlayer.OriginalTitle"))  # Try to get original title
    item['file_original_path'] = urllib.unquote(xbmc.Player().getPlayingFile().decode('utf-8'))  # Full path of a playing file
    item['mansearch'] = False
    item['languages'] = []

    if 'searchstring' in params:
        item['mansearch'] = True
        item['mansearchstr'] = urllib.unquote(params['searchstring']).decode('utf-8')

    for lang in urllib.unquote(params['languages']).decode('utf-8').split(','):
        item['languages'].append(xbmc.convertLanguage(lang, xbmc.ISO_639_2))

    if not item['title']:
        item['title'] = normalizeString(xbmc.getInfoLabel("VideoPlayer.Title"))

    if "s" in item['episode'].lower():
        # Check if season is "Special"
        item['season'] = "0"
        item['episode'] = item['episode'][-1:]

    if "http" in item['file_original_path']:
        item['temp'] = True

    elif "rar://" in item['file_original_path']:
        item['rar'] = True
        item['file_original_path'] = os.path.dirname(item['file_original_path'][6:])

    elif "stack://" in item['file_original_path']:
        stackPath = item['file_original_path'].split(" , ")
        item['file_original_path'] = stackPath[0][8:]

    Search(item)

elif params['action'] == 'download':
    # we pickup all our arguments sent from def Search()
    subs = Download(params["id"], params["filename"])

    # we can return more than one subtitle for multi CD versions, for now we
    # are still working out how to handle that in XBMC core
    for sub in subs:
        listitem = xbmcgui.ListItem(label=sub)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=sub, listitem=listitem, isFolder=False)

# Send end of directory to XBMC
xbmcplugin.endOfDirectory(int(sys.argv[1]))
