# -*- coding: utf-8 -*-
# Service LegendasDivx.com version 0.4.0
# Code based on Undertext (FRODO) service
# Coded by HiGhLaNdR@OLDSCHOOL
# Ported to Gotham by HiGhLaNdR@OLDSCHOOL
# Help by VaRaTRoN
# Bugs & Features to highlander@teknorage.com
# http://www.teknorage.com
# License: GPL v2

import os
from os.path import join as pjoin
import re
import fnmatch
import shutil
import sys
import string
import time
import unicodedata
import urllib.request, urllib.parse, urllib.error
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs
import http.cookiejar
import uuid
import socket
from urllib.parse import unquote, quote_plus

_addon = xbmcaddon.Addon()
_author     = _addon.getAddonInfo('author')
_scriptid   = _addon.getAddonInfo('id')
_scriptname = _addon.getAddonInfo('name')
_version    = _addon.getAddonInfo('version')
_language   = _addon.getLocalizedString

_cwd        = xbmc.translatePath(_addon.getAddonInfo('path'))
_profile    = xbmc.translatePath(_addon.getAddonInfo('profile'))
_resource   = xbmc.translatePath(os.path.join(_cwd, 'resources', 'lib' ))
_temp       = xbmc.translatePath(os.path.join(_profile, 'temp'))

if os.path.isdir(_temp):shutil.rmtree(_temp)
xbmcvfs.mkdirs(_temp)
if not os.path.isdir(_temp):xbmcvfs.mkdir(_temp)

sys.path.append (_resource)

_descon = _addon.getSetting( 'DESC' )
_search = _addon.getSetting( 'SEARCH' )
debug = _addon.getSetting( 'DEBUG' )

main_url = "https://www.legendasdivx.pt/"
debug_pretext = "LegendasDivx"
#SEARCH_PAGE_URL = main_url + "modules.php?name=Downloads&file=jz&d_op=search_next&order=&form_cat=28&page=%(page)s&query=%(query)s"

INTERNAL_LINK_URL = "plugin://%(scriptid)s/?action=download&id=%(id)s&filename=%(filename)s"
SUB_EXTS = ['srt', 'sub', 'txt', 'ass', 'ssa', 'smi']
HTTP_USER_AGENT = "User-Agent=Kodi 19 Matrix"

#====================================================================================================================
# Regular expression patterns
#====================================================================================================================

"""
<div class="sub_box">
<div class="sub_header">
<b>The Dark Knight</b> (2008)   -   Enviada por: <a href='modules.php?name=User_Info&username=tck17'><b>tck17</b></a>   em 2010-02-03 02:44:09

</div>
<table class="sub_main color1" cellspacing="0">
<tr>
<th class="color2">Idioma:</th>
<td><img width="18" height="12" src="modules/Downloads/img/portugal.gif" /></td>
<th>CDs:</th>
<td>1 </td>
<th>Frame Rate:</th>
<td>23.976 </td>
<td rowspan="2" class="td_right color2">
<a href="?name=Downloads&d_op=ratedownload&lid=128943">
<img border="0" src="modules/Downloads/images/rank9.gif"><br>Classifique (3 votos)

</a>
</td>
</tr>
<tr>
<th class="color2">Hits:</th>
<td>1842</td>
<th>Pedidos:</th>
<td>77 </td>
<th>Origem:</th>
<td>DVD Rip </td>
</tr>

<tr>
<th class="color2">Descrição:</th>
<td colspan="5" class="td_desc brd_up">Não são minhas.<br />
<br />
Release: The.Dark.Knight.2008.720p.BluRay.DTS.x264-ESiR</td>
"""

subtitle_pattern = "<div\sclass=\"sub_box\">.+?<div\sclass=\"sub_header\">.+?<b>(.+?)</b>\s\((\d\d\d\d)\)\s.+?name=User_Info&username=(.+?)'><b>.+?</div>.+?<table\sclass=\"sub_main\scolor1\"\scellspacing=\"0\">.+?<tr>.+?<th>CDs:</th>.+?<td>(.+?)</td>.+?<a\shref=\"\?name=Downloads&d_op=ratedownload&lid=(.+?)\">.+?<th\sclass=\"color2\">Hits:</th>.+?<td>([^\s]+).+?<td>(.+?)</td>.+?<td\scolspan=\"5\"\sclass=\"td_desc\sbrd_up\">(.*?)</td>.+?<td\sclass"
release_pattern = "([^\W][\w\.]{1,}\w{1,}[\.]{1,1}[^\.|^\ |^\.org|^\.com|^\.net][^\Ws|^\.org|^\.com|^\.net][\w{1,}\.|\-|\(\d\d\d\d\)|\[\d\d\d\d\]]{3,}[^\Ws|^\.org|^\.com|^\.net][\w{3,}\-|\.{1,1}]\w{2,})"
release_pattern1 = "([^\W][\w\ |\]|[]{4,}[^\Ws][x264|xvid|ac3]{1,}-[\w\[\]]{1,})"
year_pattern = "(19|20)\d{2}$"
# group(1) = Name, group(2) = Year, group(3) = Uploader, group (4) = Number Files, group(5) = ID, group(6) = Hits, group(7) = Requests, group(8) = Description
#==========
# Functions
#==========

def _log(module, msg):
    s = "### [%s] - %s" % (module, msg)
    xbmc.log(s, level=xbmc.LOGDEBUG)

def log(msg):
    if debug == 'true': _log(_scriptname, msg)

def recursive_glob(treeroot, pattern):
    results = []
    for base, dirs, files in os.walk(treeroot):
        for extension in pattern:
            for filename in fnmatch.filter(files, '*.' + extension): results.append(os.path.join(base, filename))
    return results

def xbmc_extract(SRC, DEST):
    dd_ext, ff_ext = xbmcvfs.listdir(SRC)
    for ff in ff_ext:
        ext = os.path.splitext(ff)[1][1:].lower()
        if ext in SUB_EXTS:
            src_file = pjoin(SRC,ff).replace('\\','/')
            dst_file = pjoin(xbmc.translatePath(DEST),ff)
            success = xbmcvfs.copy(src_file,dst_file)
            if not success:
                log("Error extracting: '%s' to '%s'" % (src_file,dst_file))
            else:
                log("Extracting: '%s' to '%s'" % (src_file,dst_file))
        else:
            log("NO FILES YET...")
    for dd in dd_ext:
        dd_mk = pjoin(DEST,dd).replace('\\','/')
        success_mk = xbmcvfs.mkdir(dd_mk)
        if not success_mk:
            log("Error creating directory: '%s'" % dd_mk)
        else:
            log("Created directory: '%s'" % dd_mk)
        now_SRC = pjoin(SRC,dd,'').replace('\\','/')
        now_DEST = pjoin(DEST,dd)
        success_dd = xbmc_extract(now_SRC,now_DEST)
        if not success_dd:
            log("Error extracting inside dir: '%s' to '%s'" % (now_SRC,now_DEST))
        else:
            log("Extracting (back into the ff loop: '%s' to '%s'" % (now_SRC,now_DEST))

def login():
    username = _addon.getSetting( 'LDuser' )
    password = _addon.getSetting( 'LDpass' )
    login_postdata = urllib.parse.urlencode({'username' : username, 'password' : password, 'login' : 'Login', 'sid' : ''}).encode("utf-8")
    cj = http.cookiejar.CookieJar()
    my_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    urllib.request.install_opener(my_opener)
    request = urllib.request.Request(main_url + 'forum/ucp.php?mode=login', login_postdata)
    response = urllib.request.urlopen(request, None, 6.5).read().decode('ISO-8859-1')    
    return my_opener

def urlpost(query, lang, page):

    my_opener=login()
    
    postdata = urllib.parse.urlencode({'query' : query, 'form_cat' : lang}).encode("utf-8")

    my_opener.addheaders = [('Referer', main_url + 'modules.php?name=Downloads&file=jz&d_op=search&op=_jz00&page='+ str(page))]
    urllib.request.install_opener(my_opener)
    request = urllib.request.Request(main_url + 'modules.php?name=Downloads&file=jz&d_op=search&op=_jz00&page='+ str(page), postdata)
    log("POST url page: %s" % page)
    log("POST url data: %s" % postdata)
    try:
        response = urllib.request.urlopen(request, None, 6.5).read().decode('ISO-8859-1')
    except urllib.error.URLError as e:
        response = ''
        xbmc.executebuiltin(('Notification(%s,%s,%d)' % (_scriptname , _language(32025).encode('utf8'),5000)))
        log("Oops, site down?")
    except socket.timeout:
        response = ''
        xbmc.executebuiltin(('Notification(%s,%s,%d)' % (_scriptname , _language(32026).encode('utf8'),5000)))
        log("Timed out!")
    return response
        
def getallsubs(searchstring, languageshort, languagelong, file_original_path, searchstring_notclean):
    subtitles_list = []

    log("getallsubs: Search String = '%s'" % searchstring)
    log("getallsubs: Search String Not Clean = '%s'" % searchstring_notclean)
    page = 1
    if languageshort == "pt": content = urlpost(searchstring, "28", page)
    elif languageshort == "pb": content = urlpost(searchstring, "29", page)
    elif languageshort == "es": content = urlpost(searchstring, "30", page)
    elif languageshort == "en": content = urlpost(searchstring, "31", page)
    log("getallsubs: LanguageShort = '%s'" % languageshort) 
    while re.search(subtitle_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE) and page < 6:
        for matches in re.finditer(subtitle_pattern, content, re.IGNORECASE | re.DOTALL | re.X):
            uploader = matches.group(3)
            hits = matches.group(6)
            id = matches.group(5)
            id = str.split(id, '"')
            id = id[0]
            movieyear = matches.group(2)
            no_files = matches.group(4)
            downloads = int(matches.group(6)) / 200
            if (downloads > 5): downloads=5
            filename = str.strip(matches.group(1))
            desc_ori = str.strip(matches.group(8))
            desc_ori = re.sub('www.legendasdivx.com','',desc_ori)
            log("getallsubs: Original Decription = '%s'" % desc_ori)
            #Remove new lines on the commentaries
            filename = re.sub('\n',' ',filename)
            _filenameon = "true"
            if _descon == "false":
                desc = re.findall(release_pattern, desc_ori, re.IGNORECASE | re.VERBOSE | re.DOTALL | re.UNICODE | re.MULTILINE)
                desc = " / ".join(desc)
                if desc != "": _filenameon = "false"
                if desc == "":
                    desc = re.findall(release_pattern1, desc_ori, re.IGNORECASE | re.VERBOSE | re.DOTALL | re.UNICODE | re.MULTILINE)
                    desc = " / ".join(desc)
                    if desc != "": _filenameon = "false"
                    if desc == "": desc = desc_ori; _filenameon = "true"
                    else: desc = desc; _filenameon = "false"
            else: desc = desc_ori; _filenameon = "true"
            desc = re.sub('<br />',' ',desc)
            desc = re.sub('<br>',' ',desc)
            desc = re.sub('\n',' ',desc)
            desc = re.sub(':.','',desc)
            #Remove HTML tags on the commentaries
            filename = re.sub('\n',' ',filename)
            desc = re.sub(r'<[^<]+?>|[~]','', desc)
            log("getallsubs: Final Description = '%s'" % desc)
            #Find filename on the comentaries to show sync label using filename or dirname (making it global for further usage)
            global filesearch
            filesearch = os.path.abspath(file_original_path)
            log("getallsubs: Filesearch String = '%s'" % filesearch)
            filesearch = os.path.split(filesearch)
            dirsearch = filesearch[0].split(os.sep)
            log("getallsubs: dirsearch = '%s'" % dirsearch)
            dirsearch_check = str.split(dirsearch[-1], '.')
            log("getallsubs: dirsearch_check = '%s'" % dirsearch_check)
            #### PARENT FOLDER TWEAK DEFINED IN THE ADD-ON SETTINGS (AUTO | ALWAYS ON (DEACTIVATED) | OFF)
            _parentfolder = _addon.getSetting( 'PARENT' )
            if _parentfolder == '0':
                if re.search(release_pattern, dirsearch[-1], re.IGNORECASE): _parentfolder = '1'
                else: _parentfolder = '2'
            if _parentfolder == '1':
                if re.search(dirsearch[-1], desc, re.IGNORECASE): sync = True
                else: sync = False
            if _parentfolder == '2':
                if (searchstring_notclean != ""):
                    sync = False
                    
                    if str.lower(searchstring_notclean) in str.lower(desc): sync = True
                else:
                    if (str.lower(dirsearch_check[-1]) == "rar") or (str.lower(dirsearch_check[-1]) == "cd1") or (str.lower(dirsearch_check[-1]) == "cd2"):
                        sync = False
                        if len(dirsearch) > 1 and dirsearch[1] != '':
                            if re.search(filesearch[1][:len(filesearch[1])-4], desc, re.IGNORECASE) or re.search(dirsearch[-2], desc, re.IGNORECASE): sync = True
                        else:
                            if re.search(filesearch[1][:len(filesearch[1])-4], desc, re.IGNORECASE): sync = True
                    else:
                        sync = False
                        if len(dirsearch) > 1 and dirsearch[1] != '':
                            if re.search(filesearch[1][:len(filesearch[1])-4], desc) or re.search(dirsearch[-1], desc, re.IGNORECASE): sync = True
                        else:
                            if re.search(filesearch[1][:len(filesearch[1])-4], desc, re.IGNORECASE): sync = True
            if _filenameon == "false": filename = "From: " + uploader + " - "  + desc + "  " + "hits: " + hits
            else: filename = "From: " + uploader + " - "  + filename + " " + "(" + movieyear + ")" + "  " + "hits: " + hits + " - " + desc
            subtitles_list.append({'rating': str(downloads), 'filename': filename, 'uploader': uploader, 'desc': desc, 'sync': sync, 'hits' : hits, 'id': id, 'language_short': languageshort, 'language_name': languagelong})
            log("getallsubs: SUBS LIST = '%s'" % subtitles_list)
        page = page + 1
        
        if languageshort == "pt": content = urlpost(searchstring, "28", page)
        elif languageshort == "pb": content = urlpost(searchstring, "29", page)
        elif languageshort == "es": content = urlpost(searchstring, "30", page)
        elif languageshort == "en": content = urlpost(searchstring, "31", page)

#   Bubble sort, to put syncs on top
    for n in range(0,len(subtitles_list)):
        for i in range(1, len(subtitles_list)):
            temp = subtitles_list[i]
            if subtitles_list[i]["sync"] > subtitles_list[i-1]["sync"]:
                subtitles_list[i] = subtitles_list[i-1]
                subtitles_list[i-1] = temp
    return subtitles_list

def append_subtitle(item):
    
    listitem = xbmcgui.ListItem(
                   label=item['language_name'],
                   label2=item['filename']
               )
    listitem.setArt( { "icon": str(int(round(float(item["rating"])))), "thumb" : item["language_short"] } )
    listitem.setProperty("sync", 'true' if item["sync"] else 'false')
    listitem.setProperty("hearing_imp", 'true' if item.get("hearing_imp", False) else 'false')

    ## below arguments are optional, it can be used to pass any info needed in download function
    ## anything after "action=download&" will be sent to addon once user clicks listed subtitle to downlaod
    args = dict(item)
    args['scriptid'] = _scriptid
    url = INTERNAL_LINK_URL % args
    ## add it to list, this can be done as many times as needed for all subtitles found
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=listitem, isFolder=False)

class Main:

    def Search(item):
        """Called when searching for subtitles from KODI."""
        #### Do what's needed to get the list of subtitles from service site
        #### use item["some_property"] that was set earlier
        #### once done, set xbmcgui.ListItem() below and pass it to xbmcplugin.addDirectoryItem()
        #### CHECKING FOR ANYTHING IN THE USERNAME AND PASSWORD, IF NULL IT STOPS THE SCRIPT WITH A WARNING
        username = _addon.getSetting( 'LDuser' )
        password = _addon.getSetting( 'LDpass' )
        if username == '' or password == '':
            xbmcplugin.endOfDirectory(int(sys.argv[1]))
            if username == '' and password != '': xbmc.executebuiltin(('Notification(%s,%s,%d)' % (_scriptname , _language(32016).encode('utf-8'),5000)))
            if username != '' and password == '': xbmc.executebuiltin(('Notification(%s,%s,%d)' % (_scriptname , _language(32017).encode('utf-8'),5000)))
            if username == '' and password == '': xbmc.executebuiltin(('Notification(%s,%s,%d)' % (_scriptname , _language(32018).encode('utf-8'),5000)))
        #### PARENT FOLDER TWEAK DEFINED IN THE ADD-ON SETTINGS (AUTO | ALWAYS ON (DEACTIVATED) | OFF)
        file_original_path = item['file_original_path']
        _parentfolder = _addon.getSetting( 'PARENT' )
        if _parentfolder == '0':
            filename = os.path.abspath(file_original_path)
            dirsearch = filename.split(os.sep)
            log("getallsubs: dirsearch string _parentfolder is 0 = %s" % (dirsearch,))
            if re.search(release_pattern, dirsearch[-2], re.IGNORECASE): _parentfolder = '1'
            else: _parentfolder = '2'
        if _parentfolder == '1':
            filename = os.path.abspath(file_original_path)
            dirsearch = filename.split(os.sep)
            filename = dirsearch[-2]
            log("getallsubs: filename string _parentfolder is 1 = %s" % (filename,))
        if _parentfolder == '2':   
            filename = os.path.splitext(os.path.basename(file_original_path))[0]
            log("getallsubs: filename string _parentfolder is 2 = %s" % (filename,))
     
        filename = xbmc.getCleanMovieTitle(filename)[0] + " " + xbmc.getCleanMovieTitle(filename)[1]
        log("Search: FILENAME = %s" % (filename,))
        searchstring_notclean = os.path.splitext(os.path.basename(file_original_path))[0]
        searchstring = ""
        global israr
        israr = os.path.abspath(file_original_path)
        israr = os.path.split(israr)
        israr = israr[0].split(os.sep)
        israr = str.split(israr[-1], '.')
        israr = str.lower(israr[-1])


        title = xbmc.getCleanMovieTitle(item['title'])[0]
        year = item['year']
        ## REMOVING THE YEAR FROM THE TV SHOW FOR BETTER MATCH ##
        tvshow = item['tvshow']
        tvshow = tvshow.split('(')
        tvshow = tvshow[0]
        ##########################################################
        season = item['season']
        episode = item['episode']
        log("Search: Tvshow string = %s" % (tvshow,))
        log("Search: Title string = %s" % (title,))
        subtitles_list = []
        
        if item['mansearch']:
            searchstring = '"' + item['mansearchstr'] + '"'
            log("Search: Manual String = %s" % (searchstring,))
        else:
            if episode != '':
                searchstring = "%s S%#02dE%#02d" % (title, int(season), int(episode))
                log("Search: Title TV LIBRARY String = %s" % (searchstring,))
            elif title != '' and episode == '':
                searchstring = '"' + title + ' ' + year + '"'
                log("Search: Title MOVIE LIBRARY String = %s" % (searchstring,))
            else:
                if 'rar' in israr and searchstring is not None:
                    log("Search: RAR Filename String = %s" % (searchstring,))
                    if 'cd1' in str.lower(title) or 'cd2' in str.lower(title) or 'cd3' in str.lower(title):
                        dirsearch = os.path.abspath(file_original_path)
                        dirsearch = os.path.split(dirsearch)
                        dirsearch = dirsearch[0].split(os.sep)
                        if len(dirsearch) > 1:
                            searchstring_notclean = dirsearch[-3]
                            searchstring = xbmc.getCleanMovieTitle(dirsearch[-3])
                            searchstring = searchstring[0]
                            log("Search: RAR MULTI CD String = %s" % (searchstring,))
                        else: searchstring = title
                    else:
                        searchstring = filename
                        log("Search: RAR NO MULTI CD String = %s" % (searchstring,))
                elif 'cd1' in str.lower(title) or 'cd2' in str.lower(title) or 'cd3' in str.lower(title):
                    dirsearch = os.path.abspath(file_original_path)
                    dirsearch = os.path.split(dirsearch)
                    dirsearch = dirsearch[0].split(os.sep)
                    if len(dirsearch) > 1:
                        searchstring_notclean = dirsearch[-2]
                        searchstring = xbmc.getCleanMovieTitle(dirsearch[-2])
                        searchstring = searchstring[0]
                        log("Search: MULTI CD String = %s" % (searchstring,))
                    else:
                        #We are at the root of the drive!!! so there's no dir to lookup only file#
                        title = os.path.split(file_original_path)
                        searchstring = title[-1]
                else:
                    ########## TODO: EXTRACT THE YEAR FROM THE FILENAME AND ADD IT TO THE SEARCH ###########
                    if _search == '0':
                        if re.search("(.+?s[0-9][0-9]e[0-9][0-9])", filename, re.IGNORECASE):
                            searchstring = re.search("(.+?s[0-9][0-9]e[0-9][0-9])", filename, re.IGNORECASE)
                            searchstring = searchstring.group(0)
                            log("Search: Filename is TV String (search is 0) = %s" % (searchstring,))
                        else:
                            searchstring = '"' + filename + '"'
                            log("Search: Filename is Not TV String (search is 0) = %s" % (searchstring,))
                    else:
                        if re.search("(.+?s[0-9][0-9]e[0-9][0-9])", title, re.IGNORECASE):
                            searchstring = re.search("(.+?s[0-9][0-9]e[0-9][0-9])", title, re.IGNORECASE)
                            searchstring = searchstring.group(0)
                            log("Search: Title is TV String (search is 1) = %s" % (searchstring,))
                        else:
                            searchstring = title
                            log("Search: Title is Not TV String (search is 1) = %s" % (searchstring,))

        PT_ON = _addon.getSetting( 'PT' )
        PTBR_ON = _addon.getSetting( 'PTBR' )
        ES_ON = _addon.getSetting( 'ES' )
        EN_ON = _addon.getSetting( 'EN' )
        
        if 'por' in item['languages'] and PT_ON == 'true':
            subtitles_list = getallsubs(searchstring, "pt", "Portuguese", file_original_path, searchstring_notclean)
            for sub in subtitles_list: append_subtitle(sub)
        if 'por' in item['languages'] and PTBR_ON == 'true':
            subtitles_list = getallsubs(searchstring, "pb", "Brazilian", file_original_path, searchstring_notclean)
            for sub in subtitles_list: append_subtitle(sub)
        if 'spa' in item['languages'] and ES_ON == 'true':
            subtitles_list = getallsubs(searchstring, "es", "Spanish", file_original_path, searchstring_notclean)
            for sub in subtitles_list: append_subtitle(sub)
        if 'eng' in item['languages'] and EN_ON == 'true':
            subtitles_list = getallsubs(searchstring, "en", "English", file_original_path, searchstring_notclean)
            for sub in subtitles_list: append_subtitle(sub)
        if 'eng' not in item['languages'] and 'spa' not in item['languages'] and 'por' not in item['languages'] and 'por' not in item['languages']:
            xbmc.executebuiltin(('Notification(%s,%s,%d)' % (_scriptname , 'Only Portuguese | Portuguese Brazilian | English | Spanish.',5000)))
    
    def Download(id, filename):
        """Called when subtitle download request from KODI."""
        # Cleanup temp dir, we recomend you download/unzip your subs in temp folder and
        # pass that to XBMC to copy and activate
        if os.path.isdir(_temp):shutil.rmtree(_temp)
        xbmcvfs.mkdirs(_temp)
        if not os.path.isdir(_temp):xbmcvfs.mkdir(_temp)
        unpacked = 'ldivx-' + str(uuid.uuid4()).replace("-","")[0:6]
        xbmcvfs.mkdirs(pjoin(_temp,unpacked,''))
        _newtemp = os.path.join(_temp, xbmc.translatePath(unpacked).replace('\\','/'))

        subtitles_list = []
        my_opener = login()
        
        content = my_opener.open(main_url + 'modules.php?name=Downloads&d_op=getit&lid=' + id + '&username=' + _addon.getSetting( 'LDuser' ))
        content = content.read()
        #### If user is not registered or User\Pass is misspelled it will generate an error message and break the script execution!
        if 'url=sair.php?referer=login' in content.decode('ISO-8859-1'):
            xbmc.executebuiltin(('Notification(%s,%s,%d)' % (_scriptname , _language(32019).encode('utf8'),5000)))
            xbmcplugin.endOfDirectory(int(sys.argv[1]))
        if content.decode('ISO-8859-1') is not None:
            header = content[:4].decode('ISO-8859-1')
            if header == 'Rar!':
                tmp_file = str(uuid.uuid4())+".rar"
                local_tmp_file = pjoin(_temp, tmp_file)
                packed = True
            elif header == 'PK':
                local_tmp_file = pjoin(_temp, str(uuid.uuid4())+".zip")
                packed = True
            else:
                # never found/downloaded an unpacked subtitles file, but just to be sure ...
                # assume unpacked sub file is an '.srt'
                local_tmp_file = pjoin(_temp, "ldivx.srt")
                subs_file = local_tmp_file
                packed = False
            log("Trying to save subtitles to '%s'" % (local_tmp_file,))
            try:
                with open(local_tmp_file, "wb") as local_file_handle:

                    local_file_handle.write(content)
                local_file_handle.close()
                xbmc.sleep(500)
            except:
                log("Failed to save subtitles to '%s'" % (local_tmp_file,))
            if packed:
                try:
                    compressed_file = 'rar://' + quote_plus(local_tmp_file) + '/'
                    log("Will try to extract...")
                    xbmc_extract(compressed_file,_newtemp)
                except:
                    xbmc.executebuiltin("XBMC.Extract(%s, %s)" % (compressed_file, _newtemp), True)
                ## IF EXTRACTION FAILS, WHICH HAPPENS SOMETIMES ... BUG?? ... WE WILL BROWSE THE RAR FILE FOR MANUAL EXTRACTION ##
                searchsubs = recursive_glob(_newtemp, SUB_EXTS)
                searchsubscount = len(searchsubs)
                if searchsubscount == 0:
                    dialog = xbmcgui.Dialog()
                    subs_file = dialog.browse(1, _language(32024).encode('utf8'), 'files', '', False, True, _temp + '/')
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
                            subs_file = dialog.browse(1, _language(32024).encode('utf8'), 'files', '', False, True, _newtemp + '/')
                            subtitles_list.append(subs_file)
                            break
            else: subtitles_list.append(subs_file)
        return subtitles_list

    def get_params():
        param = []
        paramstring = sys.argv[2]
        if len(paramstring) >= 2:
            params = paramstring
            cleanedparams = params.replace('?', '')
            if params.endswith('/'): params = params[:-2] # XXX: Should be [:-1] ?
            pairsofparams = cleanedparams.split('&')
            param = {}
            for pair in pairsofparams:
                splitparams = {}
                splitparams = pair.split('=')
                if len(splitparams) == 2: param[splitparams[0]] = splitparams[1]
        return param

    # Get parameters from XBMC and launch actions
    params = get_params()

    if params['action'] == 'search' or params['action'] == 'manualsearch':
        item = {}
        item['temp']               = False
        item['rar']                = False
        item['year']               = xbmc.getInfoLabel("VideoPlayer.Year")                           # Year
        item['season']             = str(xbmc.getInfoLabel("VideoPlayer.Season"))                    # Season
        item['episode']            = str(xbmc.getInfoLabel("VideoPlayer.Episode"))                   # Episode
        item['tvshow']             = str(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))   # Show
        item['title']              = str(xbmc.getInfoLabel("VideoPlayer.OriginalTitle")) # try to get original title
        item['file_original_path'] = urllib.parse.unquote(xbmc.Player().getPlayingFile())  # Full path of a playing file
        item['mansearch'] = False
        item['languages'] = []

        if 'searchstring' in params:
            item['mansearch'] = True
            item['mansearchstr'] = urllib.parse.unquote(params['searchstring'])

        for lang in urllib.parse.unquote(params['languages']).split(','):
            item['languages'].append(xbmc.convertLanguage(lang, xbmc.ISO_639_2))


        if "s" in item['episode'].lower():
            # Check if season is "Special"
            item['season'] = "0"
            item['episode'] = item['episode'][-1:]

        if "http" in item['file_original_path']: item['temp'] = True

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