# -*- coding: utf-8 -*-
# Service Pipocas.tv version 0.1.2
# Code based on Undertext (FRODO) service
# Coded by HiGhLaNdR@OLDSCHOOL
# Ported to Gotham by HiGhLaNdR@OLDSCHOOL
# Help by VaRaTRoN and Mafarricos
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
import urllib
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs
import cookielib
import urllib2

__addon__ = xbmcaddon.Addon()
__author__     = __addon__.getAddonInfo('author')
__scriptid__   = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__    = __addon__.getAddonInfo('version')
__language__   = __addon__.getLocalizedString

__cwd__        = xbmc.translatePath(__addon__.getAddonInfo('path')).decode("utf-8")
__profile__    = xbmc.translatePath(__addon__.getAddonInfo('profile')).decode("utf-8")
__resource__   = xbmc.translatePath(pjoin(__cwd__, 'resources', 'lib' ) ).decode("utf-8")
__temp__       = xbmc.translatePath(pjoin(__profile__, 'temp'))

sys.path.append (__resource__)

__search__ = __addon__.getSetting( 'SEARCH' )
debug = __addon__.getSetting( 'DEBUG' )

main_url = "http://pipocas.tv/"
debug_pretext = "Pipocas"
#SEARCH_PAGE_URL = main_url + "modules.php?name=Downloads&file=jz&d_op=search_next&order=&form_cat=28&page=%(page)s&query=%(query)s"

INTERNAL_LINK_URL = "plugin://%(scriptid)s/?action=download&id=%(id)s&filename=%(filename)s"
SUB_EXTS = ['srt', 'sub', 'txt', 'aas', 'ssa', 'smi']
HTTP_USER_AGENT = "User-Agent=Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.2.3) Gecko/20100401 Firefox/3.6.3 ( .NET CLR 3.5.30729)"

#Grabbing login and pass from xbmc settings
username = __addon__.getSetting( "PPuser" )
password = __addon__.getSetting( "PPpass" )

#====================================================================================================================
# Regular expression patterns
#====================================================================================================================

"""
"""
subtitle_pattern = "<a href=\"info.php(.+?)\" class=\"info\"></a>"
name_pattern = "<h1 class=\"title\">[\r\n\s]Release: (.+?)\s</h1>|<h1 class=\"title\">[\r\n\s]Release: (.+?)\s<img class=\".+?[\r\n\s]</h1>"
id_pattern = "download.php\?id=(.+?)\""
hits_pattern = "<li><span>Hits:</span> (.+?)</li>"
#desc_pattern = "<div class=\"description-box\">([\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*)<center><iframe"
uploader_pattern = "<a href=\"/my.php\?u.+?:normal;\"> (.+?)</font></a>"
release_pattern = "([^\W]\w{1,}\.{1,1}[^\.|^\ ][\w{1,}\.|\-|\(\d\d\d\d\)|\[\d\d\d\d\]]{3,}[\w{3,}\-|\.{1,1}]\w{2,})"
release_pattern1 = "([^\W][\w\ ]{4,}[^\Ws][x264|xvid]{1,}-[\w]{1,})"

#==========
# Functions
#==========

def _log(module, msg):
    s = u"### [%s] - %s" % (module, msg)
    xbmc.log(s.encode('utf-8'), level=xbmc.LOGDEBUG)

def log(msg=None):
    if debug == 'true': _log(__name__, msg)

def geturl(url):
    class MyOpener(urllib.FancyURLopener):
        #version = HTTP_USER_AGENT
        version = ''
    my_urlopener = MyOpener()
    log(u"Getting url: %s" % url)
    try:
        response = my_urlopener.open(url)
        content = response.read()
    except:
        log(u"Failed to get url:%s" % url)
        content = None
    return content

def getallsubs(searchstring, languageshort, languagelong, file_original_path, searchstring_notclean):
    subtitles_list = []

    # LOGIN FIRST AND THEN SEARCH
    url = main_url + 'vlogin.php'
    req_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/525.13 (KHTML, like Gecko) Chrome/0.A.B.C Safari/525.13',
    'Referer': main_url,
    'Keep-Alive': '300',
    'Connection': 'keep-alive'}
    request = urllib2.Request(url, headers=req_headers)
    cj = cookielib.CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    login_data = urllib.urlencode({'username' : username, 'password' : password})
    response = opener.open(request,login_data)

    page = 0
    if languageshort == "pt": url = main_url + "subtitles.php?grupo=rel&linguagem=portugues&page=" + str(page) + "&release=" + urllib.quote_plus(searchstring)
    elif languageshort == "pb": url = main_url + "subtitles.php?grupo=rel&linguagem=brasileiro&page=" + str(page) + "&release=" + urllib.quote_plus(searchstring)
    elif languageshort == "es": url = main_url + "subtitles.php?grupo=rel&linguagem=espanhol&page=" + str(page) + "&release=" + urllib.quote_plus(searchstring)
    elif languageshort == "en": url = main_url + "subtitles.php?grupo=rel&linguagem=ingles&page=" + str(page) + "&release=" + urllib.quote_plus(searchstring)
    else: url = main_url + "index.php"

    content = opener.open(url)
    content = content.read()
    content = content.decode('latin1')
    while re.search(subtitle_pattern, content, re.IGNORECASE | re.DOTALL) and page < 2:
        log("Getting '%s' inside while ..." % subtitle_pattern)
        for matches in re.finditer(subtitle_pattern, content, re.IGNORECASE | re.DOTALL):
            details = matches.group(1)
            content_details = opener.open(main_url + "info.php" + details)
            content_details = content_details.read()
            content_details = content_details.decode('latin1')
            for namematch in re.finditer(name_pattern, content_details, re.IGNORECASE | re.DOTALL):
                filename = string.strip(namematch.group(1))
                desc = filename
                log("FILENAME match: '%s' ..." % namematch.group(1))         
            for idmatch in re.finditer(id_pattern, content_details, re.IGNORECASE | re.DOTALL):
                id = idmatch.group(1)
                log("ID match: '%s' ..." % idmatch.group(1))         
            for upmatch in re.finditer(uploader_pattern, content_details, re.IGNORECASE | re.DOTALL):
                uploader = upmatch.group(1)
            for hitsmatch in re.finditer(hits_pattern, content_details, re.IGNORECASE | re.DOTALL):
                hits = hitsmatch.group(1)
            downloads = int(hits) / 150
            if (downloads > 5): downloads=5
            filename = re.sub('\n',' ',filename)
            desc = re.sub('\n',' ',desc)
            #Remove HTML tags on the commentaries
            filename = re.sub(r'<[^<]+?>','', filename)
            desc = re.sub(r'<[^<]+?>|[~]','', desc)
            #Find filename on the comentaries to show sync label using filename or dirname (making it global for further usage)
            global filesearch
            filesearch = os.path.abspath(file_original_path)
            filesearch = os.path.split(filesearch)
            dirsearch = filesearch[0].split(os.sep)
            dirsearch_check = string.split(dirsearch[-1], '.')
            #### PARENT FOLDER TWEAK DEFINED IN THE ADD-ON SETTINGS (AUTO | ALWAYS ON (DEACTIVATED) | OFF)
            __parentfolder__ = __addon__.getSetting( 'PARENT' )
            if __parentfolder__ == '0':
                if re.search(release_pattern, dirsearch[-1], re.IGNORECASE): __parentfolder__ = '1'
                else: __parentfolder__ = '2'
            if __parentfolder__ == '1':
                if re.search(dirsearch[-1], desc, re.IGNORECASE): sync = True
                else: sync = False
            if __parentfolder__ == '2':
                if (searchstring_notclean != ""):
                    sync = False
                    if string.lower(searchstring_notclean) in string.lower(desc): sync = True
                else:
                    if (string.lower(dirsearch_check[-1]) == "rar") or (string.lower(dirsearch_check[-1]) == "cd1") or (string.lower(dirsearch_check[-1]) == "cd2"):
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
            filename = filename + "  " + "hits: " + hits + " uploader: " + uploader
            subtitles_list.append({'rating': str(downloads), 'filename': filename, 'hits': hits, 'desc': desc, 'sync': sync, 'id': id, 'language_short': languageshort, 'language_name': languagelong})
        page = page + 1
        if languageshort == "pt": url = main_url + "subtitles.php?grupo=rel&linguagem=portugues&page=" + str(page) + "&release=" + urllib.quote_plus(searchstring)
        elif languageshort == "pb": url = main_url + "subtitles.php?grupo=rel&linguagem=brasileiro&page=" + str(page) + "&release=" + urllib.quote_plus(searchstring)
        elif languageshort == "es": url = main_url + "subtitles.php?grupo=rel&linguagem=espanhol&page=" + str(page) + "&release=" + urllib.quote_plus(searchstring)
        elif languageshort == "en": url = main_url + "subtitles.php?grupo=rel&linguagem=ingles&page=" + str(page) + "&release=" + urllib.quote_plus(searchstring)
        else: url = main_url + "index.php"
        content = opener.open(url)
        content = content.read()
        content = content.decode('latin1')

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
                   label2=item['filename'],
                   iconImage=item['rating'],
                   thumbnailImage=item['language_short']
               )
    listitem.setProperty("sync", 'true' if item["sync"] else 'false')
    listitem.setProperty("hearing_imp", 'true' if item.get("hearing_imp", False) else 'false')

    ## below arguments are optional, it can be used to pass any info needed in download function
    ## anything after "action=download&" will be sent to addon once user clicks listed subtitle to downlaod
    args = dict(item)
    args['scriptid'] = __scriptid__
    url = INTERNAL_LINK_URL % args
    ## add it to list, this can be done as many times as needed for all subtitles found
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=listitem, isFolder=False)

def Search(item):
    """Called when searching for subtitles from XBMC."""
    #### Do what's needed to get the list of subtitles from service site
    #### use item["some_property"] that was set earlier
    #### once done, set xbmcgui.ListItem() below and pass it to xbmcplugin.addDirectoryItem()
    #### CHECKING FOR ANYTHING IN THE USERNAME AND PASSWORD, IF NULL IT STOPS THE SCRIPT WITH A WARNING
    username = __addon__.getSetting( 'PPuser' )
    password = __addon__.getSetting( 'PPpass' )
    if username == '' or password == '':
        xbmcplugin.endOfDirectory(int(sys.argv[1]))
        if username == '' and password != '': xbmc.executebuiltin(('Notification(%s,%s,%d)' % (__scriptname__ , __language__(32016).encode('utf-8'),5000)))
        if username != '' and password == '': xbmc.executebuiltin(('Notification(%s,%s,%d)' % (__scriptname__ , __language__(32017).encode('utf-8'),5000)))
        if username == '' and password == '': xbmc.executebuiltin(('Notification(%s,%s,%d)' % (__scriptname__ , __language__(32018).encode('utf-8'),5000)))
    #### PARENT FOLDER TWEAK DEFINED IN THE ADD-ON SETTINGS (AUTO | ALWAYS ON (DEACTIVATED) | OFF)
    file_original_path = item['file_original_path']
    __parentfolder__ = __addon__.getSetting( 'PARENT' )
    if __parentfolder__ == '0':
        filename = os.path.abspath(file_original_path)
        dirsearch = filename.split(os.sep)
        log(u"dirsearch_search string = %s" % dirsearch)
        if re.search(release_pattern, dirsearch[-2], re.IGNORECASE): __parentfolder__ = '1'
        else: __parentfolder__ = '2'
    if __parentfolder__ == '1':
        filename = os.path.abspath(file_original_path)
        dirsearch = filename.split(os.sep)
        filename = dirsearch[-2]
        log(u"__parentfolder1__ = %s" % filename)
    if __parentfolder__ == '2':   
        filename = os.path.splitext(os.path.basename(file_original_path))[0]
        log(u"__parentfolder2__ = %s" % filename)

    filename = xbmc.getCleanMovieTitle(filename)[0]
    searchstring_notclean = os.path.splitext(os.path.basename(file_original_path))[0]
    searchstring = ""
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
        if tvshow != '': searchstring = "%s S%#02dE%#02d" % (tvshow, int(season), int(episode))
        elif title != '' and tvshow != '': searchstring = title
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
                    else: searchstring = title
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
                    if __search__ == '0':
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

    PT_ON = __addon__.getSetting( 'PT' )
    PTBR_ON = __addon__.getSetting( 'PTBR' )
    ES_ON = __addon__.getSetting( 'ES' )
    EN_ON = __addon__.getSetting( 'EN' )
    
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
        xbmc.executebuiltin((u'Notification(%s,%s,%d)' % (__scriptname__ , 'Only Portuguese | Portuguese Brazilian | English | Spanish.',5000)))

def recursive_glob(treeroot, pattern):
    results = []
    for base, dirs, files in os.walk(treeroot):
        for extension in pattern:
            for filename in fnmatch.filter(files, '*.' + extension): results.append(os.path.join(base, filename))
    return results

def get_download(url, download, id):
    req_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/525.13 (KHTML, like Gecko) Chrome/0.A.B.C Safari/525.13',
        'Referer': main_url,
        'Keep-Alive': '300',
        'Connection': 'keep-alive'}
    request = urllib2.Request(url, headers=req_headers)
    cj = cookielib.CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    login_data = urllib.urlencode({'username' : username, 'password' : password})
    response = opener.open(request,login_data)
    download_data = urllib.urlencode({'sid' : id, 'submit' : '+', 'action' : 'Download'})
    request1 = urllib2.Request(download, download_data, req_headers)
    f = opener.open(request1)
    return f
    
def Download(id, filename):
    """Called when subtitle download request from XBMC."""
    # Cleanup temp dir, we recomend you download/unzip your subs in temp folder and
    # pass that to XBMC to copy and activate
    if xbmcvfs.exists(__temp__): shutil.rmtree(__temp__)
    xbmcvfs.mkdirs(__temp__)

    subtitles_list = []

    url = main_url + 'vlogin.php'
    download = main_url + 'download.php?id=' + id
    req_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/525.13 (KHTML, like Gecko) Chrome/0.A.B.C Safari/525.13',
    'Referer': main_url,
    'Keep-Alive': '300',
    'Connection': 'keep-alive'}
    request = urllib2.Request(url, headers=req_headers)
    cj = cookielib.CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    login_data = urllib.urlencode({'username' : username, 'password' : password})
    response = opener.open(request,login_data)
    download_data = urllib.urlencode({'id' : id})
    request1 = urllib2.Request(download, download_data, req_headers)
    content = opener.open(request1)

#    content = get_download(main_url+'fazendologin.php', main_url+'downloadsub.php', id)

    content = content.read()
    #### If user is not registered or User\Pass is misspelled it will generate an error message and break the script execution!
    if '<title>Pipocas.TV - Login</title>' in content.decode('utf8', 'ignore'):
        xbmcplugin.endOfDirectory(int(sys.argv[1]))
        xbmc.executebuiltin(('Notification(%s,%s,%d)' % (__scriptname__ , __language__(32019).encode('utf8'),5000)))
    if content is not None:
        header = content[:4]
        if header == 'Rar!':
            local_tmp_file = pjoin(__temp__, "pipocas.rar")
            packed = True
        elif header == 'PK':
            local_tmp_file = pjoin(__temp__, "pipocas.zip")
            packed = True
        else:
            # never found/downloaded an unpacked subtitles file, but just to be sure ...
            # assume unpacked sub file is an '.srt'
            local_tmp_file = pjoin(__temp__, "pipocas.srt")
            subs_file = local_tmp_file
            packed = False
        log(u"Saving subtitles to '%s'" % (local_tmp_file,))
        try:
            local_file_handle = open(local_tmp_file, "wb")
            local_file_handle.write(content)
            local_file_handle.close()
        except: log(u"Failed to save subtitles to '%s'" % (local_tmp_file,))
        if packed:
            files = os.listdir(__temp__)
            init_filecount = len(files)
            log(u"pipocas: número de init_filecount %s" % (init_filecount,)) #EGO
            filecount = init_filecount
            max_mtime = 0
            # Determine the newest file from __temp__
            for file in files:
                if file.split('.')[-1] in SUB_EXTS:
                    mtime = os.stat(pjoin(__temp__, file)).st_mtime
                    if mtime > max_mtime: max_mtime =  mtime
            init_max_mtime = max_mtime
            # Wait 2 seconds so that the unpacked files are at least 1 second newer
            time.sleep(2)
            xbmc.executebuiltin("XBMC.Extract(" + local_tmp_file.encode("utf-8") + ", " + __temp__ +")")
            waittime  = 0
            while filecount == init_filecount and waittime < 20 and init_max_mtime == max_mtime: # nothing yet extracted
                time.sleep(1)  # wait 1 second to let the builtin function 'XBMC.extract' unpack
                files = os.listdir(__temp__)
                filecount = len(files)
                # determine if there is a newer file created in __temp__ (marks that the extraction had completed)
                for file in files:
                    if file.split('.')[-1] in SUB_EXTS:
                        mtime = os.stat(pjoin(__temp__, file)).st_mtime
                        if mtime > max_mtime: max_mtime =  mtime
                waittime  = waittime + 1
            if waittime == 20: log(u"Failed to unpack subtitles in '%s'" % (__temp__,))
            else:
                log(u"Unpacked files in '%s'" % (__temp__,))
                searchsubs = recursive_glob(__temp__, SUB_EXTS)
                searchsubscount = len(searchsubs)
                for file in searchsubs:
                    # There could be more subtitle files in __temp__, so make
                    # sure we get the newly created subtitle file
                    #if file.split('.')[-1] in SUB_EXTS and os.stat(pjoin(__temp__, file)).st_mtime > init_max_mtime:
                    if searchsubscount == 1:
                        # unpacked file is a newly created subtitle file
                        log(u"Unpacked subtitles file '%s'" % (file.decode('utf-8'),))
                        try:  subs_file = pjoin(__temp__, file.decode("utf-8"))
                        except: subs_file = pjoin(__temp__, file.decode("latin1"))
                        subtitles_list.append(subs_file)
                        break
                    else:
                    # If there are more than one subtitle in the temp dir, launch a browse dialog
                    # so user can choose. If only one subtitle is found, parse it to the addon.
                        if len(__temp__) > 1:
                            dialog = xbmcgui.Dialog()
                            subs_file = dialog.browse(1, 'XBMC', 'files', '.srt|.sub|.aas|.ssa|.smi|.txt', False, False, __temp__+'/')
                            subtitles_list.append(subs_file)
                            break
        else: subtitles_list.append(subs_file)
    return subtitles_list

def normalizeString(str):
    return unicodedata.normalize('NFKD', unicode(unicode(str, 'utf-8'))).encode('ascii', 'ignore')

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
    item['tvshow']             = normalizeString(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))   # Show
    item['title']              = normalizeString(xbmc.getInfoLabel("VideoPlayer.OriginalTitle")) # try to get original title
    item['file_original_path'] = urllib.unquote(xbmc.Player().getPlayingFile().decode('utf-8'))  # Full path of a playing file
    item['mansearch'] = False
    item['languages'] = []

    if 'searchstring' in params:
        item['mansearch'] = True
        item['mansearchstr'] = urllib.unquote(params['searchstring']).decode('utf-8')

    for lang in urllib.unquote(params['languages']).decode('utf-8').split(','): item['languages'].append(xbmc.convertLanguage(lang, xbmc.ISO_639_2))

    if not item['title']: item['title']  = normalizeString(xbmc.getInfoLabel("VideoPlayer.Title"))

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
