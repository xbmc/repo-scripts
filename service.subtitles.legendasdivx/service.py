# -*- coding: utf-8 -*-
# Service LegendasDivx.com version 0.0.1
# Code based on Undertext (FRODO) service and the download function encode fix from legendastv (FRODO) service
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
import urllib
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs
import cookielib
import urllib2
from operator import itemgetter, attrgetter
#import operator

__addon__ = xbmcaddon.Addon()
__author__     = __addon__.getAddonInfo('author')
__scriptid__   = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__    = __addon__.getAddonInfo('version')
__language__   = __addon__.getLocalizedString

__cwd__        = xbmc.translatePath(__addon__.getAddonInfo('path')).decode("utf-8")
__profile__    = xbmc.translatePath(__addon__.getAddonInfo('profile')).decode("utf-8")
__resource__   = xbmc.translatePath(pjoin(__cwd__, 'resources', 'lib' ) ).decode("utf-8")
__temp__       = xbmc.translatePath(pjoin(__profile__, 'temp')).decode("utf-8")

sys.path.append (__resource__)

main_url = "http://www.legendasdivx.com/"
debug_pretext = "LegendasDivx"
subext = ['srt', 'aas', 'ssa', 'sub', 'smi']
sub_ext = "srt,aas,ssa,sub,smi"
packext = ['rar', 'zip']


MAIN_SUBDIVX_URL = "http://www.legendasdivx.com/"
SEARCH_PAGE_URL = MAIN_SUBDIVX_URL + "modules.php?name=Downloads&file=jz&d_op=search_next&order=&form_cat=28&page=%(page)s&query=%(query)s"

INTERNAL_LINK_URL = "plugin://%(scriptid)s/?action=download&id=%(id)s&filename=%(filename)s"
SUB_EXTS = ['srt', 'sub', 'txt']
HTTP_USER_AGENT = "User-Agent=Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.2.3) Gecko/20100401 Firefox/3.6.3 ( .NET CLR 3.5.30729)"

#SUBTITLE_RE = re.compile(r'<div\sclass=\"sub_box\">[\r\n\t]{2}<div\sclass=\"sub_header\">[\r\n\t]{2}<b>(.+?)</b>\s\((\d\d\d\d)\)\s.+?[\r\n\t ]+?[\r\n\t]</div>[\r\n\t]{2}<table\sclass=\"sub_main\scolor1\"\scellspacing=\"0\">[\r\n\t]{2}<tr>[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}<th>CDs:</th>[\r\n\t ]{2}<td>(.+?)</td>[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}<a\shref=\"\?name=Downloads&d_op=ratedownload&lid=(.+?)\">[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}<th\sclass=\"color2\">Hits:</th>[\r\n\t]{2}<td>(.+?)</td>[\r\n\t ]{2}.+?[\r\n\t]{2}<td>(.+?)</td>[\r\n\t ]{2}.+?[\r\n\t ]{2}.+?[\r\n\t ]{2}.+?[\r\n\t ]{2}.+?.{2,5}[\r\n\t ]{2}.+?[\r\n\t ]{2}<td\scolspan=\"5\"\sclass=\"td_desc\sbrd_up\">((\n|.)*)</td>',
#                         re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE)
#DOWNLOAD_LINK_RE = re.compile(r'bajar.php\?id=(.*?)&u=(.*?)\"', re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE)


#====================================================================================================================
# Regular expression patterns
#====================================================================================================================

"""
<div class="sub_box">
<div class="sub_header">
<b>The Dark Knight</b> (2008) &nbsp; - &nbsp; Enviada por: <a href='modules.php?name=User_Info&username=tck17'><b>tck17</b></a> &nbsp; em 2010-02-03 02:44:09

</div>
<table class="sub_main color1" cellspacing="0">
<tr>
<th class="color2">Idioma:</th>
<td><img width="18" height="12" src="modules/Downloads/img/portugal.gif" /></td>
<th>CDs:</th>
<td>1&nbsp;</td>
<th>Frame Rate:</th>
<td>23.976&nbsp;</td>
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
<td>77&nbsp;</td>
<th>Origem:</th>
<td>DVD Rip&nbsp;</td>
</tr>

<tr>
<th class="color2">Descrição:</th>
<td colspan="5" class="td_desc brd_up">Não são minhas.<br />
<br />
Release: The.Dark.Knight.2008.720p.BluRay.DTS.x264-ESiR</td>
"""

subtitle_pattern = "<div\sclass=\"sub_box\">[\r\n\t]{2}<div\sclass=\"sub_header\">[\r\n\t]{2}<b>(.+?)</b>\s\((\d\d\d\d)\)\s.+?[\r\n\t ]+?[\r\n\t]</div>[\r\n\t]{2}<table\sclass=\"sub_main\scolor1\"\scellspacing=\"0\">[\r\n\t]{2}<tr>[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}<th>CDs:</th>[\r\n\t ]{2}<td>(.+?)</td>[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}<a\shref=\"\?name=Downloads&d_op=ratedownload&lid=(.+?)\">[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}<th\sclass=\"color2\">Hits:</th>[\r\n\t]{2}<td>(.+?)</td>[\r\n\t ]{2}.+?[\r\n\t]{2}<td>(.+?)</td>[\r\n\t ]{2}.+?[\r\n\t ]{2}.+?[\r\n\t ]{2}.+?[\r\n\t ]{2}.+?.{2,5}[\r\n\t ]{2}.+?[\r\n\t ]{2}<td\scolspan=\"5\"\sclass=\"td_desc\sbrd_up\">((\n|.)*)</td>"
# group(1) = Name, group(2) = Year, group(3) = Number Files, group(4) = ID, group(5) = Hits, group(6) = Requests, group(7) = Description
#==========
# Functions
#==========

def _log(module, msg):
    s = u"### [%s] - %s" % (module, msg)
    xbmc.log(s.encode('utf-8'), level=xbmc.LOGDEBUG)

def log(msg):
    _log(__name__, msg)

def geturl(url):
    class MyOpener(urllib.FancyURLopener):
        #version = HTTP_USER_AGENT
        version = ''
    my_urlopener = MyOpener()
    log(u"Getting url: %s" % (url,))
    try:
        response = my_urlopener.open(url)
        content = response.read()
    except:
        log(u"Failed to get url:%s" % (url,))
        content = None
    return content

def getallsubs(searchstring, languageshort, languagelong, file_original_path, searchstring_notclean):
    subtitles_list = []

    #searchstring_notclean = searchstring
    log(u"_searchstring '%s' ..." % searchstring)
    log(u"_searchstring_notclean '%s' ..." % searchstring_notclean)
    page = 1
    if languageshort == "pt":
        url = main_url + "modules.php?name=Downloads&file=jz&d_op=search_next&order=&form_cat=28&page=" + str(page) + "&query=" + urllib.quote_plus(searchstring)
    elif languageshort == "pb":
        url = main_url + "modules.php?name=Downloads&file=jz&d_op=search_next&order=&form_cat=29&page=" + str(page) + "&query=" + urllib.quote_plus(searchstring)
    elif languageshort == "es":
        url = main_url + "modules.php?name=Downloads&file=jz&d_op=search_next&order=&form_cat=30&page=" + str(page) + "&query=" + urllib.quote_plus(searchstring)
    elif languageshort == "en":
        url = main_url + "modules.php?name=Downloads&file=jz&d_op=search_next&order=&form_cat=31&page=" + str(page) + "&query=" + urllib.quote_plus(searchstring)
    else:
        url = main_url + "index.php"

    content = geturl(url)
    #log( __name__ ,"%s Getting '%s' subs ..." % (debug_pretext, languageshort))
    log(u"Getting '%s' subs ..." % languageshort)
    while re.search(subtitle_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE) and page < 6:
        for matches in re.finditer(subtitle_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE):
            hits = matches.group(5)
            id = matches.group(4)
            movieyear = matches.group(2)
            no_files = matches.group(3)
            downloads = int(matches.group(5)) / 300
            if (downloads > 10):
                downloads=10
            filename = string.strip(matches.group(1))
            desc = string.strip(matches.group(7))
            #Remove new lines on the commentaries
            filename = re.sub('\n',' ',filename)
            desc = re.sub('\n',' ',desc)
            desc = re.sub(':.','',desc)
            desc = re.sub('br />','',desc)
            #Remove HTML tags on the commentaries
            filename = re.sub(r'<[^<]+?>','', filename)
            desc = re.sub(r'<[^<]+?>|[~]','', desc)
            #Find filename on the comentaries to show sync label using filename or dirname (making it global for further usage)
            global filesearch
            filesearch = os.path.abspath(file_original_path)
            #For DEBUG only uncomment next line
            #log( __name__ ,"%s abspath: '%s'" % (debug_pretext, filesearch))
            filesearch = os.path.split(filesearch)
            #For DEBUG only uncomment next line
            #log( __name__ ,"%s path.split: '%s'" % (debug_pretext, filesearch))
            dirsearch = filesearch[0].split(os.sep)
            #For DEBUG only uncomment next line
            #log( __name__ ,"%s dirsearch: '%s'" % (debug_pretext, dirsearch))
            dirsearch_check = string.split(dirsearch[-1], '.')
            #For DEBUG only uncomment next line
            #log( __name__ ,"%s dirsearch_check: '%s'" % (debug_pretext, dirsearch_check))
            if (searchstring_notclean != ""):
                sync = False
                if re.search(searchstring_notclean, desc):
                    sync = True
            else:
                if (string.lower(dirsearch_check[-1]) == "rar") or (string.lower(dirsearch_check[-1]) == "cd1") or (string.lower(dirsearch_check[-1]) == "cd2"):
                    sync = False
                    if len(dirsearch) > 1 and dirsearch[1] != '':
                        if re.search(filesearch[1][:len(filesearch[1])-4], desc) or re.search(dirsearch[-2], desc):
                            sync = True
                    else:
                        if re.search(filesearch[1][:len(filesearch[1])-4], desc):
                            sync = True
                else:
                    sync = False
                    if len(dirsearch) > 1 and dirsearch[1] != '':
                        if re.search(filesearch[1][:len(filesearch[1])-4], desc) or re.search(dirsearch[-1], desc):
                            sync = True
                    else:
                        if re.search(filesearch[1][:len(filesearch[1])-4], desc):
                            sync = True
            filename = filename + " " + "(" + movieyear + ")" + "  " + hits + "Hits" + " - " + desc
            subtitles_list.append({'rating': str(downloads), 'no_files': no_files, 'filename': filename, 'desc': desc, 'sync': sync, 'hits' : hits, 'id': id, 'language_short': languageshort, 'language_name': languagelong})
        page = page + 1
        
        if languageshort == "pt":
            url = main_url + "modules.php?name=Downloads&file=jz&d_op=search_next&order=&form_cat=28&page=" + str(page) + "&query=" + urllib.quote_plus(searchstring)
        elif languageshort == "pb":
            url = main_url + "modules.php?name=Downloads&file=jz&d_op=search_next&order=&form_cat=29&page=" + str(page) + "&query=" + urllib.quote_plus(searchstring)
        elif languageshort == "es":
            url = main_url + "modules.php?name=Downloads&file=jz&d_op=search_next&order=&form_cat=30&page=" + str(page) + "&query=" + urllib.quote_plus(searchstring)
        elif languageshort == "en":
            url = main_url + "modules.php?name=Downloads&file=jz&d_op=search_next&order=&form_cat=31&page=" + str(page) + "&query=" + urllib.quote_plus(searchstring)
        else:
            url = main_url + "index.php"
            
        content = geturl(url)

#   Bubble sort, to put syncs on top
    for n in range(0,len(subtitles_list)):
        for i in range(1, len(subtitles_list)):
            temp = subtitles_list[i]
            if subtitles_list[i]["sync"] > subtitles_list[i-1]["sync"]:
                subtitles_list[i] = subtitles_list[i-1]
                subtitles_list[i-1] = temp

    #log(u"Search sorted LISTA = %s" % (subtitles_list,))
    return subtitles_list

def append_subtitle(item):
    
  #  log(u"Search string = %s" % (subtitles_list,))
    #log(u"Search sorted ITEM = %s" % (item,))
#    subtitles_list = sorted(subtitles_list, key=itemgetter('language_name'))
    listitem = xbmcgui.ListItem(
                   label=item['language_name'],
                   label2=item['filename']+ '-' +item['desc'],
                   iconImage=item['rating'],
                   thumbnailImage=item['language_short']
               )
    #listitem.sort(key=lambda x: x['language_short'], reverse=True)
    #sorted(listitem.keys(), key=lambda x: x['language_short'])
    log(u"Search sorted LISTITEM = %s" % (listitem,))
    listitem.setProperty("sync", 'true' if item["sync"] else 'false')
    listitem.setProperty("hearing_imp", 'true' if item.get("hearing_imp", False) else 'false')

    ## below arguments are optional, it can be used to pass any info needed in download function
    ## anything after "action=download&" will be sent to addon once user clicks listed subtitle to downlaod
    args = dict(item)
    args['scriptid'] = __scriptid__
    url = INTERNAL_LINK_URL % args
    #log(u"Search sorted string = %s" % (url,))
    #log(u"Search sorted ARGS = %s" % (args,))
    ## add it to list, this can be done as many times as needed for all subtitles found
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=listitem, isFolder=False)

def Search(item):
    """Called when searching for subtitles from XBMC."""
    #### Do what's needed to get the list of subtitles from service site
    #### use item["some_property"] that was set earlier
    #### once done, set xbmcgui.ListItem() below and pass it to xbmcplugin.addDirectoryItem()
    filename = os.path.splitext(os.path.basename(item['file_original_path']))[0]
    file_original_path = item['file_original_path']
    filename = xbmc.getCleanMovieTitle(filename)
    searchstring_notclean = ""
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
    log(u"Tvshow string = %s" % (tvshow,))
    log(u"Title string = %s" % (title,))
    subtitles_list = []
    
    if item['mansearch']:
        searchstring = item['mansearchstr']
        log(u"Manual Searchstring string = %s" % (searchstring,))
    if tvshow != '':
        searchstring = "%s S%#02dE%#02d" % (tvshow, int(season), int(episode))
        log(u"TV Searchstring string = %s" % (searchstring,))
    if tvshow == '':
        if 'rar' in israr and searchstring is not None:
            log(u"RAR Searchstring string = %s" % (searchstring,))
            if 'cd1' in string.lower(title) or 'cd2' in string.lower(title) or 'cd3' in string.lower(title):
                dirsearch = os.path.abspath(file_original_path)
                dirsearch = os.path.split(dirsearch)
                dirsearch = dirsearch[0].split(os.sep)
                if len(dirsearch) > 1:
                    searchstring_notclean = dirsearch[-3]
                    searchstring = xbmc.getCleanMovieTitle(dirsearch[-3])
                    searchstring = searchstring[0]
                    log(u"RAR MULTI1 CD Searchstring string = %s" % (searchstring,))
                else:
                    searchstring = title
            else:
                searchstring = title
                log(u"RAR NO CD Searchstring string = %s" % (searchstring,))
        elif 'cd1' in string.lower(title) or 'cd2' in string.lower(title) or 'cd3' in string.lower(title):
            dirsearch = os.path.abspath(file_original_path)
            dirsearch = os.path.split(dirsearch)
            dirsearch = dirsearch[0].split(os.sep)
            if len(dirsearch) > 1:
                searchstring_notclean = dirsearch[-2]
                searchstring = xbmc.getCleanMovieTitle(dirsearch[-2])
                searchstring = searchstring[0]
                log(u"MULTI1 CD Searchstring string = %s" % (searchstring,))
            else:
                #We are at the root of the drive!!! so there's no dir to lookup only file#
                title = os.path.split(file_original_path)
                searchstring = title[-1]
        else:
            if title == "":
                title = os.path.split(file_original_path)
                searchstring = title[-1]
                log(u"TITLE NULL Searchstring string = %s" % (searchstring,))
            else:
                searchstring = title
                log(u"TITLE Searchstring string = %s" % (searchstring,))

    PT_ON = __addon__.getSetting( 'PT' )
    PTBR_ON = __addon__.getSetting( 'PTBR' )
    ES_ON = __addon__.getSetting( 'ES' )
    EN_ON = __addon__.getSetting( 'EN' )
    
    if 'por' in item['languages'] and PT_ON == 'true':
        subtitles_list = getallsubs(searchstring, "pt", "Portuguese", file_original_path, searchstring_notclean)
        for sub in subtitles_list:
            append_subtitle(sub)
    if 'por' in item['languages'] and PTBR_ON == 'true':
        subtitles_list = getallsubs(searchstring, "pb", "Brazilian", file_original_path, searchstring_notclean)
        for sub in subtitles_list:
            append_subtitle(sub)
    if 'spa' in item['languages'] and ES_ON == 'true':
        subtitles_list = getallsubs(searchstring, "es", "Spanish", file_original_path, searchstring_notclean)
        for sub in subtitles_list:
            append_subtitle(sub)
    if 'eng' in item['languages'] and EN_ON == 'true':
        subtitles_list = getallsubs(searchstring, "en", "English", file_original_path, searchstring_notclean)
        for sub in subtitles_list:
            append_subtitle(sub)
    #else:
        #xbmc.executebuiltin((u'Notification(%s,%s)' % (__scriptname__ , 'only works for Portuguese,Brazilian,English,Spanish')).encode('utf-8'))

def recursive_glob(treeroot, pattern):
    results = []
    for base, dirs, files in os.walk(treeroot):
        for extension in pattern:
            for filename in fnmatch.filter(files, '*.' + extension):
                results.append(os.path.join(base, filename))
    return results

def Download(id, filename):
    """Called when subtitle download request from XBMC."""
    # Cleanup temp dir, we recomend you download/unzip your subs in temp folder and
    # pass that to XBMC to copy and activate
    if xbmcvfs.exists(__temp__):
        shutil.rmtree(__temp__)
    xbmcvfs.mkdirs(__temp__)

    subtitles_list = []
    username = __addon__.getSetting( 'LDuser' )
    password = __addon__.getSetting( 'LDpass' )
    login_postdata = urllib.urlencode({'username' : username, 'user_password' : password, 'op' : 'login'})
    cj = cookielib.CookieJar()
    my_opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    my_opener.addheaders = [('Referer', 'http://www.legendasdivx.com/modules.php?name=Your_Account')]
    urllib2.install_opener(my_opener)
    request = urllib2.Request('http://www.legendasdivx.com/modules.php?name=Your_Account', login_postdata)
    response = urllib2.urlopen(request).read()


    content = my_opener.open('http://www.legendasdivx.com/modules.php?name=Downloads&d_op=getit&lid=' + id + '&username=' + username)
    content = content.read()
    if content is not None:
        header = content[:4]
        if header == 'Rar!':
            local_tmp_file = pjoin(__temp__, "ldivx.rar")
            packed = True
        elif header == 'PK':
            local_tmp_file = pjoin(__temp__, "ldivx.zip")
            packed = True
        else:
            # never found/downloaded an unpacked subtitles file, but just to be sure ...
            # assume unpacked sub file is an '.srt'
            local_tmp_file = pjoin(__temp__, "ldivx.srt")
            subs_file = local_tmp_file
            packed = False
        log(u"Saving subtitles to '%s'" % (local_tmp_file,))
        try:
            local_file_handle = open(local_tmp_file, "wb")
            local_file_handle.write(content)
            local_file_handle.close()
        except:
            log(u"Failed to save subtitles to '%s'" % (local_tmp_file,))
        if packed:
            files = os.listdir(__temp__)
            init_filecount = len(files)
            log(u"legendasdivx: número de init_filecount %s" % (init_filecount,)) #EGO
            filecount = init_filecount
            max_mtime = 0
            # Determine the newest file from __temp__
            for file in files:
                if file.split('.')[-1] in SUB_EXTS:
                    mtime = os.stat(pjoin(__temp__, file)).st_mtime
                    if mtime > max_mtime:
                        max_mtime =  mtime
            init_max_mtime = max_mtime
            # Wait 2 seconds so that the unpacked files are at least 1 second newer
            time.sleep(2)
            xbmc.executebuiltin("XBMC.Extract(" + local_tmp_file.encode("utf-8") + ", " + __temp__.encode("utf-8") +")")
            waittime  = 0
            while filecount == init_filecount and waittime < 20 and init_max_mtime == max_mtime: # nothing yet extracted
                time.sleep(1)  # wait 1 second to let the builtin function 'XBMC.extract' unpack
                files = os.listdir(__temp__)
                filecount = len(files)
                # determine if there is a newer file created in __temp__ (marks that the extraction had completed)
                for file in files:
                    if file.split('.')[-1] in SUB_EXTS:
                        mtime = os.stat(pjoin(__temp__, file.decode("utf-8"))).st_mtime
                        if mtime > max_mtime:
                            max_mtime =  mtime
                waittime  = waittime + 1
            if waittime == 20:
                log(u"Failed to unpack subtitles in '%s'" % (__temp__,))
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
                        log(u"Unpacked subtitles file '%s'" % (file,))
                        subs_file = pjoin(__temp__, file.decode("utf-8"))
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
        else:
            subtitles_list.append(subs_file)
    return subtitles_list

def normalizeString(str):
    return unicodedata.normalize('NFKD', unicode(unicode(str, 'utf-8'))).encode('ascii', 'ignore')

def get_params():
    param = []
    paramstring = sys.argv[2]
    if len(paramstring) >= 2:
        params = paramstring
        cleanedparams = params.replace('?', '')
        if params.endswith('/'):
            params = params[:-2] # XXX: Should be [:-1] ?
        pairsofparams = cleanedparams.split('&')
        param = {}
        for pair in pairsofparams:
            splitparams = {}
            splitparams = pair.split('=')
            if len(splitparams) == 2:
                param[splitparams[0]] = splitparams[1]

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
        #print params['searchstring']

    for lang in urllib.unquote(params['languages']).decode('utf-8').split(','):
        item['languages'].append(xbmc.convertLanguage(lang, xbmc.ISO_639_2))

    if not item['title']:
        # no original title, get just Title
        item['title']  = normalizeString(xbmc.getInfoLabel("VideoPlayer.Title"))

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
