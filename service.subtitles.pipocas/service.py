# -*- coding: UTF-8 -*-
# Service Pipocas.tv
# Matrix READY!
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
from urllib.parse import unquote, quote_plus

OS_SYSTEM = system()
OS_ARCH_BIT = architecture()[0]
OS_ARCH_LINK = architecture()[1]
OS_MACHINE = machine()
OS_RELEASE = release()
OS_VERSION = version()
OS_DETECT = OS_SYSTEM + "-" + OS_ARCH_BIT + "-" + OS_ARCH_LINK
OS_DETECT += " | host: [%s][%s][%s]" % (OS_MACHINE, OS_RELEASE, OS_VERSION)

main_url = "https://pipocas.tv/"
debug_pretext = "Pipocas"

_addon = xbmcaddon.Addon()
_author = _addon.getAddonInfo("author")
_scriptid = _addon.getAddonInfo("id")
_scriptname = _addon.getAddonInfo("name")
_version = _addon.getAddonInfo("version")
_language = _addon.getLocalizedString
_dialog = xbmcgui.Dialog()

_cwd = xbmcvfs.translatePath(_addon.getAddonInfo("path"))
_profile = xbmcvfs.translatePath(_addon.getAddonInfo("profile"))
_resource = xbmcvfs.translatePath(pjoin(_cwd, "resources", "lib"))
_temp = xbmcvfs.translatePath(pjoin(_profile, "temp"))

sys.path.append(_resource)
from pipocas import *

_search = _addon.getSetting("SEARCH")
debug = _addon.getSetting("DEBUG")
# Grabbing login and pass from xbmc settings
username = _addon.getSetting("USERNAME")
password = _addon.getSetting("PASSWORD")

if os.path.isdir(_temp):
    shutil.rmtree(_temp)
xbmcvfs.mkdirs(_temp)
if not os.path.isdir(_temp):
    xbmcvfs.mkdir(_temp)


# SEARCH_PAGE_URL  = main_url + 'modules.php?name=Downloads&file=jz&d_op=search_next&order=&form_cat=28&page=%(page)s&query=%(query)s'
INTERNAL_LINK_URL = (
    "plugin://%(scriptid)s/?action=download&id=%(id)s&filename=%(filename)s"
)
HTTP_USER_AGENT = "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/525.13 (KHTML, like Gecko) Chrome/0.A.B.C Safari/525.13"

# ====================================================================================================================
# Regular expression patterns
# ====================================================================================================================

"""
"""
token_pattern = '<meta name="csrf-token" content="(.+?)">'
subtitle_pattern = (
    '<a href="' + main_url + 'legendas/info/(.+?)" class="text-dark no-decoration">'
)
name_pattern = '<h3 class="title" style="word-break: break-all;">Release:\s+?<span\s+?class="font-normal">(.+?)<\/span>\s*<\/h3>'
id_pattern = 'legendas/download/(.+?)"'
hits_pattern = '<span class="hits hits-pd">\s+?<div><i class="fa fa-cloud-download" aria-hidden="true"></i>\s+?([0-9]+?)</div>\s+?</span>'
# desc_pattern = "<div class=\"description-box\">([\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*)<center><iframe"
uploader_pattern = (
    '<span style="color:\s#[A-Za-z0-9]+?"\s*>([A-Za-z0-9]+?)</span></a></b>'
)
rating_pattern = '<h2 class="mt-3 text-center">\s+?([0-9])/[0-9]\s+?</h2>'
release_pattern = "([^\W]\w{1,}\.{1,1}[^\.|^\ ][\w{1,}\.|\-|\(\d\d\d\d\)|\[\d\d\d\d\]]{3,}[\w{3,}\-|\.{1,1}]\w{2,})"
release_pattern1 = "([^\W][\w\ ]{4,}[^\Ws][x264|xvid]{1,}-[\w]{1,})"


def getallsubs(
    searchstring, languageshort, languagelong, file_original_path, searchstring_notclean
):
    subtitles_list = []

    # LOGIN FIRST AND THEN SEARCH
    url = main_url + "login"
    # GET CSRF TOKEN
    req_headers = {
        "User-Agent": HTTP_USER_AGENT,
        "Referer": url,
        "Keep-Alive": "300",
        "Connection": "keep-alive",
    }
    sessionPipocasTv = requests.Session()
    result = sessionPipocasTv.get(url)

    if result.status_code != 200:
        _dialog.notification(
            _scriptname,
            _language(32019).encode("utf8"),
            xbmcgui.NOTIFICATION_ERROR,
            1500,
        )
        return []

    token = re.search(token_pattern, result.text)

    # LOGIN NOW
    payload = {
        "username": username,
        "password": password,
        "_token": token.group(1),
    }

    loginResult = sessionPipocasTv.post(url, data=payload, headers=req_headers)

    if loginResult.status_code != 200:
        _dialog.notification(
            _scriptname,
            _language(32019).encode("utf8"),
            xbmcgui.NOTIFICATION_ERROR,
            1500,
        )
        return []

    page = 1
    languages = {
        "pt": "portugues",
        "pb": "brasileiro",
        "es": "espanhol",
        "en": "ingles",
    }
    language_name = languages.get(languageshort, "home")
    url = f"{main_url}legendas?t=rel&l={language_name}&page={page}&s={searchstring}"
    print("URLURLURL: " + url)
    content = sessionPipocasTv.get(url)

    if "Cria uma conta" in content.text:
        _dialog.notification(
            _scriptname,
            _language(32019).encode("utf8"),
            xbmcgui.NOTIFICATION_ERROR,
            1500,
        )
        return []

    while (
        re.search(subtitle_pattern, content.text, re.IGNORECASE | re.DOTALL)
        and page < 2
    ):
        log("Getting '%s' inside while ..." % subtitle_pattern)
        for matches in re.finditer(
            subtitle_pattern, content.text, re.IGNORECASE | re.DOTALL
        ):
            details = matches.group(1)

            content_details = sessionPipocasTv.get(
                main_url + "legendas/info/" + details
            )
            filename = ""
            desc = ""
            for namematch in re.finditer(
                name_pattern, content_details.text, re.IGNORECASE | re.DOTALL
            ):
                filename = str.strip(namematch.group(1))
                desc = filename
                log("FILENAME match: '%s' ..." % namematch.group(1))
            if filename == "":
                _dialog.notification(
                    _scriptname,
                    "Bug on name_pattern regex, contact author",
                    xbmcgui.NOTIFICATION_ERROR,
                    300,
                )
            id = ""
            for idmatch in re.finditer(
                id_pattern, content_details.text, re.IGNORECASE | re.DOTALL
            ):
                id = idmatch.group(1)
                log("ID match: '%s' ..." % idmatch.group(1))
            if id == "":
                _dialog.notification(
                    _scriptname,
                    "Bug on id_pattern regex, contact author",
                    xbmcgui.NOTIFICATION_ERROR,
                    300,
                )
            uploader = ""
            for upmatch in re.finditer(
                uploader_pattern, content_details.text, re.IGNORECASE | re.DOTALL
            ):
                uploader = upmatch.group(1)
            if uploader == "":
                uploader = "Bot-Pipocas"
            hits = "0"
            for hitsmatch in re.finditer(
                hits_pattern, content_details.text, re.IGNORECASE | re.DOTALL
            ):
                hits = hitsmatch.group(1)
            if hits == "0":
                _dialog.notification(
                    _scriptname,
                    "Bug on hits_pattern regex, contact author",
                    xbmcgui.NOTIFICATION_ERROR,
                    300,
                )
            rating = ""
            for ratingmatch in re.finditer(
                rating_pattern, content_details.text, re.IGNORECASE | re.DOTALL
            ):
                rating = ratingmatch.group(1)
            if rating == "":
                _dialog.notification(
                    _scriptname,
                    "Bug on rating_pattern regex, contact author",
                    xbmcgui.NOTIFICATION_ERROR,
                    300,
                )
                rating = "0"

            if rating == "0":
                rate_downloads = 0
            else:
                rate_downloads = int(hits) / 100

            if rate_downloads > 5:
                rate_downloads = 5

            downloads = round((int(rating) + int(rate_downloads)) / 2)
            filename = re.sub("\n", " ", filename)
            desc = re.sub("\n", " ", desc)
            # Remove HTML tags on the commentaries
            filename = re.sub(r"<[^<]+?>", "", filename)
            desc = re.sub(r"<[^<]+?>|[~]", "", desc)
            # Find filename on the comentaries to show sync label using filename or dirname (making it global for further usage)
            global filesearch
            filesearch = os.path.abspath(file_original_path)
            filesearch = os.path.split(filesearch)
            dirsearch = filesearch[0].split(os.sep)
            dirsearch_check = str.split(dirsearch[-1], ".")
            # PARENT FOLDER TWEAK DEFINED IN THE ADD-ON SETTINGS (AUTO | ALWAYS ON (DEACTIVATED) | OFF)
            _parentfolder = _addon.getSetting("PARENT")
            if _parentfolder == "0":
                if re.search(release_pattern, dirsearch[-1], re.IGNORECASE):
                    _parentfolder = "1"
                else:
                    _parentfolder = "2"
            if _parentfolder == "1":
                if re.search(dirsearch[-1], desc, re.IGNORECASE):
                    sync = True
                else:
                    sync = False
            if _parentfolder == "2":
                if searchstring_notclean != "":
                    sync = False
                    if str.lower(searchstring_notclean) in str.lower(desc):
                        sync = True
                else:
                    if (
                        (str.lower(dirsearch_check[-1]) == "rar")
                        or (str.lower(dirsearch_check[-1]) == "cd1")
                        or (str.lower(dirsearch_check[-1]) == "cd2")
                    ):
                        sync = False
                        if len(dirsearch) > 1 and dirsearch[1] != "":
                            if re.search(
                                filesearch[1][: len(filesearch[1]) - 4],
                                desc,
                                re.IGNORECASE,
                            ) or re.search(dirsearch[-2], desc, re.IGNORECASE):
                                sync = True
                        else:
                            if re.search(
                                filesearch[1][: len(filesearch[1]) - 4],
                                desc,
                                re.IGNORECASE,
                            ):
                                sync = True
                    else:
                        sync = False
                        if len(dirsearch) > 1 and dirsearch[1] != "":
                            if re.search(
                                filesearch[1][: len(filesearch[1]) - 4], desc
                            ) or re.search(dirsearch[-1], desc, re.IGNORECASE):
                                sync = True
                        else:
                            if re.search(
                                filesearch[1][: len(filesearch[1]) - 4],
                                desc,
                                re.IGNORECASE,
                            ):
                                sync = True
            filename = filename + "  " + "hits: " + hits + " uploader: " + uploader
            subtitles_list.append(
                {
                    "rating": str(downloads),
                    "filename": filename,
                    "hits": hits,
                    "desc": desc,
                    "sync": sync,
                    "id": id,
                    "language_short": languageshort,
                    "language_name": languagelong,
                }
            )
        page = page + 1

        language_codes = {
            "pt": "portugues",
            "pb": "brasileiro",
            "es": "espanhol",
            "en": "ingles",
        }
        language = language_codes.get(languageshort, "home")
        url = f"{main_url}legendas?t=rel&l={language}&page={page}&s={searchstring}"

        content = sessionPipocasTv.get(url)

    # Bubble sort, to put syncs on top
    subtitles_list = bubbleSort(subtitles_list)
    return subtitles_list


def append_subtitle(item):
    listitem = xbmcgui.ListItem(
        label=item["language_name"], label2=item["filename"], offscreen=True
    )
    listitem.setArt(
        {
            "icon": str(int(round(float(item["rating"])))),
            "thumb": item["language_short"],
        }
    )
    listitem.setProperty("sync", "true" if item["sync"] else "false")
    listitem.setProperty(
        "hearing_imp", "true" if item.get("hearing_imp", False) else "false"
    )

    ## below arguments are optional, it can be used to pass any info needed in download function
    ## anything after "action=download&" will be sent to addon once user clicks listed subtitle to download
    args = dict(item)
    args["scriptid"] = _scriptid
    url = INTERNAL_LINK_URL % args
    ## add it to list, this can be done as many times as needed for all subtitles found
    xbmcplugin.addDirectoryItem(
        handle=int(sys.argv[1]), url=url, listitem=listitem, isFolder=False
    )


class Main:
    def Search(item):
        log("Host data '%s'" % OS_DETECT)
        """Called when searching for subtitles from KODI."""
        # Do what's needed to get the list of subtitles from service site
        # use item["some_property"] that was set earlier
        # once done, set xbmcgui.ListItem() below and pass it to xbmcplugin.addDirectoryItem()
        # CHECKING FOR ANYTHING IN THE USERNAME AND PASSWORD, IF NULL IT STOPS THE SCRIPT WITH A WARNING
        username = _addon.getSetting("USERNAME")
        password = _addon.getSetting("PASSWORD")
        if not username or not password:
            xbmcplugin.endOfDirectory(int(sys.argv[1]))
            if username == "" and password != "":
                _dialog.notification(
                    _scriptname,
                    _language(32016).encode("utf8"),
                    xbmcgui.NOTIFICATION_ERROR,
                    300,
                )
            elif username != "" and password == "":
                _dialog.notification(
                    _scriptname,
                    _language(32017).encode("utf8"),
                    xbmcgui.NOTIFICATION_ERROR,
                    300,
                )
            elif username == "" and password == "":
                _dialog.notification(
                    _scriptname,
                    _language(32018).encode("utf8"),
                    xbmcgui.NOTIFICATION_ERROR,
                    300,
                )
        # PARENT FOLDER TWEAK DEFINED IN THE ADD-ON SETTINGS (AUTO | ALWAYS ON (DEACTIVATED) | OFF)
        file_original_path = item["file_original_path"]
        _parentfolder = _addon.getSetting("PARENT")
        if _parentfolder == "0":
            filename = os.path.abspath(file_original_path)
            dirsearch = filename.split(os.sep)
            log("dirsearch_search string = %s" % dirsearch)
            if re.search(release_pattern, dirsearch[-2], re.IGNORECASE):
                _parentfolder = "1"
            else:
                _parentfolder = "2"
        if _parentfolder == "1":
            filename = os.path.abspath(file_original_path)
            dirsearch = filename.split(os.sep)
            filename = dirsearch[-2]
            log("_parentfolder1 = %s" % filename)
        if _parentfolder == "2":
            filename = os.path.splitext(os.path.basename(file_original_path))[0]
            log("_parentfolder2 = %s" % filename)

        filename = xbmc.getCleanMovieTitle(filename)[0]
        searchstring_notclean = os.path.splitext(os.path.basename(file_original_path))[
            0
        ]
        searchstring = ""
        log("_searchstring_notclean = %s" % searchstring_notclean)
        log("_searchstring = %s" % searchstring)
        global israr
        israr = os.path.abspath(file_original_path)
        israr = os.path.split(israr)
        israr = israr[0].split(os.sep)
        israr = str.split(israr[-1], ".")
        israr = str.lower(israr[-1])

        title = xbmc.getCleanMovieTitle(item["title"])[0]
        tvshow = item["tvshow"]
        season = item["season"]
        episode = item["episode"]
        log("Tvshow string = %s" % tvshow)
        log("Title string = %s" % title)
        subtitles_list = []

        if item["mansearch"]:
            searchstring = item["mansearchstr"]
            log("Manual Searchstring string = %s" % searchstring)
        else:
            if tvshow != "":
                searchstring = "%s S%#02dE%#02d" % (tvshow, int(season), int(episode))
            elif title != "" and tvshow != "":
                searchstring = title
            else:
                if "rar" in israr and searchstring is not None:
                    log("RAR Searchstring string = %s" % searchstring)
                    if (
                        "cd1" in str.lower(title)
                        or "cd2" in str.lower(title)
                        or "cd3" in str.lower(title)
                    ):
                        dirsearch = os.path.abspath(file_original_path)
                        dirsearch = os.path.split(dirsearch)
                        dirsearch = dirsearch[0].split(os.sep)
                        if len(dirsearch) > 1:
                            searchstring_notclean = dirsearch[-3]
                            searchstring = xbmc.getCleanMovieTitle(dirsearch[-3])
                            searchstring = searchstring[0]
                            log("RAR MULTI1 CD Searchstring string = %s" % searchstring)
                        else:
                            searchstring = title
                    else:
                        searchstring = title
                        log("RAR NO CD Searchstring string = %s" % searchstring)
                elif (
                    "cd1" in str.lower(title)
                    or "cd2" in str.lower(title)
                    or "cd3" in str.lower(title)
                ):
                    dirsearch = os.path.abspath(file_original_path)
                    dirsearch = os.path.split(dirsearch)
                    dirsearch = dirsearch[0].split(os.sep)
                    if len(dirsearch) > 1:
                        searchstring_notclean = dirsearch[-2]
                        searchstring = xbmc.getCleanMovieTitle(dirsearch[-2])
                        searchstring = searchstring[0]
                        log("MULTI1 CD Searchstring string = %s" % searchstring)
                    else:
                        # We are at the root of the drive!!! so there's no dir to lookup only file#
                        title = os.path.split(file_original_path)
                        searchstring = title[-1]
                else:
                    if title == "":
                        title = os.path.split(file_original_path)
                        searchstring = title[-1]
                        log("TITLE NULL Searchstring string = %s" % searchstring)
                    else:
                        if _search == "0":
                            if re.search(
                                "(.+?s[0-9][0-9]e[0-9][0-9])", filename, re.IGNORECASE
                            ):
                                searchstring = re.search(
                                    "(.+?s[0-9][0-9]e[0-9][0-9])",
                                    filename,
                                    re.IGNORECASE,
                                )
                                searchstring = searchstring.group(0)
                                log("FilenameTV Searchstring = %s" % searchstring)
                            else:
                                searchstring = filename
                                log("Filename Searchstring = %s" % searchstring)
                        else:
                            if re.search(
                                "(.+?s[0-9][0-9]e[0-9][0-9])", title, re.IGNORECASE
                            ):
                                searchstring = re.search(
                                    "(.+?s[0-9][0-9]e[0-9][0-9])", title, re.IGNORECASE
                                )
                                searchstring = searchstring.group(0)
                                log("TitleTV Searchstring = %s" % searchstring)
                            else:
                                searchstring = title
                                log("Title Searchstring = %s" % searchstring)

        LANGUAGES = {
            "pt": "Portuguese",
            "pb": "Brazilian",
            "es": "Spanish",
            "en": "English",
        }

        for lang, lang_name in LANGUAGES.items():
            if _addon.getSetting(lang.upper()) == "true":
                subtitles_list = getallsubs(
                    searchstring,
                    lang,
                    lang_name,
                    file_original_path,
                    searchstring_notclean,
                )
                for sub in subtitles_list:
                    append_subtitle(sub)

        if not any(
            _addon.getSetting(lang.upper()) == "true" for lang in LANGUAGES.keys()
        ):
            _dialog.notification(
                _scriptname,
                "Apenas Português | Português Brasil | English | Spanish",
                xbmcgui.NOTIFICATION_ERROR,
                1500,
            )

    def Download(id, filename):
        if os.path.isdir(_temp):
            shutil.rmtree(_temp)
        xbmcvfs.mkdirs(_temp)
        if not os.path.isdir(_temp):
            xbmcvfs.mkdir(_temp)
        unpacked = "ldivx-" + str(uuid.uuid4()).replace("-", "")[0:6]
        xbmcvfs.mkdirs(pjoin(_temp, unpacked, ""))
        _newtemp = os.path.join(
            _temp, xbmcvfs.translatePath(unpacked).replace("\\", "/")
        )

        url = main_url + "login"
        download = main_url + "legendas/download/" + id
        # GET CSRF TOKEN
        req_headers = {
            "User-Agent": HTTP_USER_AGENT,
            "Referer": url,
            "Keep-Alive": "300",
            "Connection": "keep-alive",
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

        loginResult = sessionPipocasTv.post(url, data=payload, headers=req_headers)
        if not loginResult.ok:
            return []

        content = sessionPipocasTv.get(download)
        if not content.ok:
            return []
        # If user is not registered or User\Pass is misspelled it will generate an error message and break the script execution!
        thecontent = content.content

        if "Cria uma conta" in content.text:
            xbmcplugin.endOfDirectory(int(sys.argv[1]))
            _dialog.notification(
                _scriptname,
                _language(32019).encode("utf8"),
                xbmcgui.NOTIFICATION_ERROR,
                1500,
            )
            return []

        if thecontent is not None:
            subtitles_list = []
            random = uuid.uuid4().hex
            cleanDirectory(_temp)

            # Check archive type (rar/zip/else) through the file header (rar=Rar!, zip=PK)
            log("Checking archive type")

            # Define dictionary of archive types and their file headers
            archive_types = {"rar": b"Rar!", "zip": b"PK"}

            # Check archive type through the file header
            file_header = thecontent[:4]
            for ext, header in archive_types.items():
                if file_header.startswith(header):
                    extension = f".{ext}"
                    archive_type = f"{ext}://"
                    packed = True
                    log(f"Discovered {ext.upper()} Archive")
                    break
            else:
                extension = ".srt"
                archive_type = ""
                packed = False
                log("Discovered a non-archive file")

            local_tmp_file = os.path.join(_temp, random + extension)

            try:
                log("Saving subtitles to '%s'" % local_tmp_file)

                with open(local_tmp_file, "wb") as local_file_handle:
                    local_file_handle.write(thecontent)
                local_file_handle.close()
                xbmc.sleep(500)

                log("Saving to %s" % local_tmp_file)
            except:
                log("Failed to save subtitle to %s" % local_tmp_file)

            if packed:
                try:
                    compressed_file = "rar://" + quote_plus(local_tmp_file) + "/"
                    log("Will try to extract...")
                    xbmc_extract(compressed_file, _newtemp)
                except:
                    xbmc.executebuiltin(
                        "XBMC.Extract(%s, %s)" % (compressed_file, _newtemp), True
                    )
                ## IF EXTRACTION FAILS, WHICH HAPPENS SOMETIMES ... BUG?? ... WE WILL BROWSE THE RAR FILE FOR MANUAL EXTRACTION ##
                searchsubs = recursive_glob(_newtemp, SUB_EXTS)
                searchsubscount = len(searchsubs)
                if searchsubscount == 0:
                    dialog = xbmcgui.Dialog()
                    subs_file = dialog.browse(
                        1,
                        _language(32024).encode("utf8"),
                        "files",
                        "",
                        False,
                        True,
                        _temp + "/",
                    )
                    subtitles_list.append(subs_file)
                ## ELSE WE WILL GO WITH THE NORMAL PROCEDURE ##
                else:
                    os.remove(local_tmp_file)
                    log("count: '%s'" % (searchsubscount,))
                    for file in searchsubs:
                        # There could be more subtitle files in _temp, so make
                        # sure we get the newly created subtitle file
                        if searchsubscount == 1:
                            # unpacked file is a newly created subtitle file
                            log("Unpacked subtitles file '%s'" % (file,))
                            try:
                                subs_file = pjoin(_newtemp, file)
                            except:
                                log("Failed to load subtitle file '%s'" % (file,))
                            subtitles_list.append(subs_file)
                            break
                        else:
                            # If there are more than one subtitle in the temp dir, launch a browse dialog
                            # so user can choose.
                            dialog = xbmcgui.Dialog()
                            subs_file = dialog.browse(
                                1,
                                _language(32024).encode("utf8"),
                                "files",
                                "",
                                False,
                                True,
                                _newtemp + "/",
                            )
                            subtitles_list.append(subs_file)
                            break
            else:
                subtitles_list.append(subs_file)
        return subtitles_list

    def get_params():
        param = []
        paramstring = sys.argv[2]
        if len(paramstring) >= 2:
            params = paramstring
            cleanedparams = params.replace("?", "")
            if params.endswith("/"):
                params = params[:-2]  # XXX: Should be [:-1] ?
            pairsofparams = cleanedparams.split("&")
            param = {}
            for pair in pairsofparams:
                splitparams = {}
                splitparams = pair.split("=")
                if len(splitparams) == 2:
                    param[splitparams[0]] = splitparams[1]
        return param

    # Get parameters from KODI and launch actions
    params = get_params()

    if params["action"] == "search" or params["action"] == "manualsearch":
        item = {}
        item["temp"] = False
        item["rar"] = False
        item["year"] = xbmc.getInfoLabel("VideoPlayer.Year")  # Year
        item["season"] = str(xbmc.getInfoLabel("VideoPlayer.Season"))  # Season
        item["episode"] = str(xbmc.getInfoLabel("VideoPlayer.Episode"))  # Episode
        item["tvshow"] = str(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))  # Show
        item["title"] = str(
            xbmc.getInfoLabel("VideoPlayer.OriginalTitle")
        )  # Try to get original title
        item["file_original_path"] = urllib.parse.unquote(
            xbmc.Player().getPlayingFile()
        )  # Full path of a playing file
        item["mansearch"] = False
        item["languages"] = []

        if "searchstring" in params:
            item["mansearch"] = True
            item["mansearchstr"] = urllib.parse.unquote(params["searchstring"])

        for lang in urllib.parse.unquote(params["languages"]).split(","):
            item["languages"].append(xbmc.convertLanguage(lang, xbmc.ISO_639_2))

        if not item["title"]:
            item["title"] = str(xbmc.getInfoLabel("VideoPlayer.Title"))

        if "s" in item["episode"].lower():
            # Check if season is "Special"
            item["season"] = "0"
            item["episode"] = item["episode"][-1:]

        if "http" in item["file_original_path"]:
            item["temp"] = True

        elif "rar://" in item["file_original_path"]:
            item["rar"] = True
            item["file_original_path"] = os.path.dirname(item["file_original_path"][6:])

        elif "stack://" in item["file_original_path"]:
            stackPath = item["file_original_path"].split(" , ")
            item["file_original_path"] = stackPath[0][8:]

        Search(item)

    elif params["action"] == "download":
        # we pickup all our arguments sent from def Search()
        subs = Download(params["id"], params["filename"])

        # we can return more than one subtitle for multi CD versions, for now we
        # are still working out how to handle that in KODI core
        for sub in subs:
            listitem = xbmcgui.ListItem(label=sub)
            xbmcplugin.addDirectoryItem(
                handle=int(sys.argv[1]), url=sub, listitem=listitem, isFolder=False
            )

    # Send end of directory to KODI
    xbmcplugin.endOfDirectory(int(sys.argv[1]))
