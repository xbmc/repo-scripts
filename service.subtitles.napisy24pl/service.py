# -*- coding: utf-8 -*-
from cookielib import CookieJar

import os
import sys
import urllib
import unicodedata
import re
import urllib2
import struct
import shutil
import StringIO
import gzip
from BeautifulSoup import BeautifulSoup

try:
    import xbmc
    import xbmcvfs
    import xbmcaddon
    import xbmcplugin
    import xbmcgui
except ImportError:
    from stubs import xbmc, xbmcgui, xbmcaddon, xbmcplugin, xbmcvfs

__addon__ = xbmcaddon.Addon()
__scriptid__ = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')
__language__ = __addon__.getLocalizedString

__cwd__ = xbmc.translatePath(__addon__.getAddonInfo('path')).decode("utf-8")
__profile__ = xbmc.translatePath(__addon__.getAddonInfo('profile')).decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib')).decode("utf-8")
__temp__ = xbmc.translatePath(os.path.join(__profile__, 'temp', '')).decode("utf-8")

sys.path.append(__resource__)

def normalizeString(str):
    return unicodedata.normalize(
        'NFKD', unicode(unicode(str, 'latin-1'))
    ).encode('ascii', 'ignore').decode('latin-1').encode("utf-8")

def log(module, msg):
    xbmc.log((u"### [%s] - %s" % (module, msg,)).encode('utf-8'), level=xbmc.LOGDEBUG)

if __addon__.getSetting("subs_format") == "0":
    subtitle_type = "sr"
elif __addon__.getSetting("subs_format") == "1":
    subtitle_type = "tmp"
elif __addon__.getSetting("subs_format") == "2":
    subtitle_type = "mdvd"
elif __addon__.getSetting("subs_format") == "3":
    subtitle_type = "mpl2"

search_url = "http://napisy24.pl/szukaj?search=%s&page=%d&typ=%d&lang=0"
download_url = "http://napisy24.pl/download?napisId=%s&typ=%s"
login_url = "http://napisy24.pl/component/comprofiler/login"

http_headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Charset': 'UTF-8,*;q=0.5',
    'Accept-Encoding': 'gzip,deflate,sdch',
    'Accept-Language': 'pl,pl-PL;q=0.8,en-US;q=0.6,en;q=0.4',
    'Connection': 'keep-alive',
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/21.0.1180.83 Safari/537.1',
    'Referer': 'http://napisy24.pl/'
}

def http_response_content(response):
    if response.info().get('Content-Encoding') == 'gzip':
        buf = StringIO.StringIO(response.read())
        f = gzip.GzipFile(fileobj=buf)
        content = f.read()
    else:
        content = response.read()

    return content

def getallsubs(content, item, subtitles_list):

    soup = BeautifulSoup(content)
    subs = soup.findAll('div', {'class': 'moreInfo'})

    for row in subs[0:]:
        row_str = str(row.parent.parent)

        sub_id_re = '\?napisId=(\d+)"><h2'
        title_re = '<div class="subtitle">.+>(.+?)</h2>.+</div>'
        release_re = '<div class="subtitle">.+>(.+?)</h3>.+</div>'
        lang_re = '<img src="/images/flags/(.+?).png" class="lang" />'

        infoColumn1 = re.findall("<div class=\"infoColumn1\">(.+?)</div>", row_str, re.DOTALL)[0].split('<br />')
        infoColumn2 = re.findall("<div class=\"infoColumn2\">(.+?)</div>", row_str, re.DOTALL)[0].split('<br />')
        infoColumn3 = re.findall("<div class=\"infoColumn3\">(.+?)</div>", row_str, re.DOTALL)[0].split('<br />')
        infoColumn4 = re.findall("<div class=\"infoColumn4\">(.+?)</div>", row_str, re.DOTALL)[0].split('<br />')

        sub_id = int(re.findall(sub_id_re, row_str)[0])
        subtitle = re.findall(title_re, row_str)[0]
        release = re.findall(release_re, row_str)[0]
        language = re.findall(lang_re, row_str)[0]

        rating = 0
        video_file_size = []

        for i, line in enumerate(infoColumn1):
            if 'Rozmiar' in line:
                video_file_size = re.findall("[\d.]+", infoColumn2[i])
                break

        for i, line in enumerate(infoColumn3):
            if 'ocena' in line:
                rating = float(infoColumn4[i].replace(',', '.'))
                break

        if rating != 0:
            rating = int(round(rating/1.2 , 0))

        if(len(video_file_size) > 0):
            video_file_size = float(video_file_size[0])
        else:
            video_file_size = 0

        if video_file_size == 0:
            sync = False
        else:
            file_size = round(item["file_original_size"] / float(1048576), 2)
            if file_size == video_file_size:
                sync = True
            else:
                sync = False

        releases = release.split(';')

        if(sync == False):
            for rel in releases:
                rel = rel.strip()
                if(re.findall(rel, item['file_original_name'], re.I)):
                    sync = True
                    break

        if len(language) > 0:

            if xbmc.convertLanguage(language, xbmc.ISO_639_2) in item["3let_language"]:
                link = download_url % (sub_id, subtitle_type)
                log(__name__, "Subtitles found: %s %s (link=%s)" % (subtitle, release, link))

                filename_release = "%s.%s" % (subtitle.replace(" ", "."), release)

                subtitles_list.append({'lang_index': item["3let_language"].index(
                    xbmc.convertLanguage(language, xbmc.ISO_639_2)),
                                       'id': sub_id,
                                       'filename': filename_release,
                                       'language_name': xbmc.convertLanguage(language, xbmc.ENGLISH_NAME),
                                       'language_flag': xbmc.convertLanguage(language, xbmc.ISO_639_1),
                                       'rating': '%s' % (rating,),
                                       'sync': sync,
                                       'hearing_imp': 0
                })
            else:
                continue
        else:
            continue

def Search(item):  #standard input
    subtitles_list = []
    if len(item["tvshow"]) > 0:
        for year in re.finditer(' \(\d{4}\)', item["tvshow"]):
            year = year.group()
            if len(year) > 0:
                tvshow = item["tvshow"].replace(year, "")
            else:
                continue
        tvshow_plus = item["tvshow"].replace(" ", "+")

        season_full = int(item["season"])
        episode_full = str("%02d" % (int(item["episode"]),))

        search_string = '%s+%sx%s' % (tvshow_plus, season_full, episode_full)
        search_type = 2
    else:
        original_title = item["title"]
        if len(original_title) == 0:
            log(__name__, "Original title not set")
            movie_title_plus = item["title"].replace(" ", "+")
            search_string = movie_title_plus
        else:
            log(__name__, "Original title: [%s]" % (original_title))
            movie_title_plus = original_title.replace(" ", "+")
            search_string = movie_title_plus
            search_type = 1

    url =  search_url % (search_string, 1, search_type)

    log(__name__, "Fetching from [ %s ]" % (url))

    request = urllib2.Request(url, None, http_headers)
    response = urllib2.urlopen(request)
    content = normalizeString(http_response_content(response))

    re_pages_string = 'href=".+page=(\d).+">.+</a><a class="page-next'
    pages = re.findall(re_pages_string, content)

    if(len(pages)):
        pages = int(pages[0])
    else:
        pages = 0

    getallsubs(content, item, subtitles_list)
    for page in range(1, pages):
        url =  search_url % (search_string, (page+1), search_type)
        request = urllib2.Request(url, None, http_headers)
        response = urllib2.urlopen(request)
        content = normalizeString(http_response_content(response))
        getallsubs(content, item, subtitles_list)
        
    if subtitles_list:
        for it in subtitles_list:
            listitem = xbmcgui.ListItem(label=it["language_name"],
                                        label2=it["filename"],
                                        iconImage=it["rating"],
                                        thumbnailImage=it["language_flag"]
            )
            if it["sync"]:
                listitem.setProperty("sync", "true")
            else:
                listitem.setProperty("sync", "false")

            if it.get("hearing_imp", False):
                listitem.setProperty("hearing_imp", "true")
            else:
                listitem.setProperty("hearing_imp", "false")

            url = "plugin://%s/?action=download&id=%d" % (__scriptid__, it["id"])
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=listitem, isFolder=False)

def Download(sub_id):  #standard input

    subtitle_list = []
    exts = [".srt", ".sub", ".txt"]
    link = download_url % (sub_id, subtitle_type)

    ## Cleanup temp dir, we recomend you download/unzip your subs in temp folder and
    ## pass that to XBMC to copy and activate
    if xbmcvfs.exists(__temp__):
        shutil.rmtree(__temp__.encode(sys.getfilesystemencoding()))
    xbmcvfs.mkdirs(__temp__)

    cj = CookieJar()

    request = urllib2.Request(login_url, None, http_headers)
    response = urllib2.urlopen(request)
    content = normalizeString(http_response_content(response))
    cbsecuritym3 = re.findall('name="cbsecuritym3" value="(.+?)"', content)[0]

    values = {
        'username': __addon__.getSetting("username"),
        'passwd': __addon__.getSetting("password"),
        'cbsecuritym3': cbsecuritym3,
    }

    data = urllib.urlencode(values)
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    request = urllib2.Request(login_url, data, http_headers)
    response = opener.open(request)

    request = urllib2.Request(link, "", http_headers)
    f = opener.open(request)
    local_tmp_file = os.path.join(__temp__, "zipsubs.zip")
    log(__name__, "Saving subtitles to '%s'" % (local_tmp_file))

    zip_filename = os.path.join(__temp__, "subs.zip")

    with open(zip_filename, "wb") as subFile:
        subFile.write(f.read())
    subFile.close()

    xbmc.sleep(500)

    xbmc.executebuiltin(('XBMC.Extract("%s","%s")' % (zip_filename, __temp__,)).encode('utf-8'), True)

    for file in xbmcvfs.listdir(__temp__)[1]:
        full_path = os.path.join(__temp__, file)
        if os.path.splitext(full_path)[1] in exts and file != 'Napisy24.pl.srt':
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
    item['file_original_path'] = urllib.unquote(xbmc.Player().getPlayingFile().decode('utf-8'))  # Full path of a playing file
    item['file_original_name'] = os.path.basename(item['file_original_path']) # Name of playing file
    item['3let_language'] = []
    item['preferredlanguage'] = unicode(urllib.unquote(params.get('preferredlanguage', '')), 'utf-8')
    item['preferredlanguage'] = xbmc.convertLanguage(item['preferredlanguage'], xbmc.ISO_639_2)

    for lang in urllib.unquote(params['languages']).decode('utf-8').split(","):
        item['3let_language'].append(xbmc.convertLanguage(lang, xbmc.ISO_639_2))

    if item['title'] == "":
        item['title'] = normalizeString(xbmc.getInfoLabel("VideoPlayer.Title"))  # no original title, get just Title

    if item['episode'].lower().find("s") > -1:  # Check if season is "Special"
        item['season'] = "0"  #
        item['episode'] = item['episode'][-1:]

    if ( item['file_original_path'].find("http") > -1 ):
        item['temp'] = True

    elif ( item['file_original_path'].find("rar://") > -1 ):
        item['rar'] = True
        item['file_original_path'] = os.path.dirname(item['file_original_path'][6:])

    elif ( item['file_original_path'].find("stack://") > -1 ):
        stackPath = item['file_original_path'].split(" , ")
        item['file_original_path'] = stackPath[0][8:]

    if item['tvshow'] and params['action'] == "manualsearch":
        item['tvshow'] = params['searchstring']
    elif params['action'] == "manualsearch":
        item['title'] = params['searchstring']

    item["file_original_size"] = xbmcvfs.File(item["file_original_path"]).size()

    log(__name__, "item: %s" %(item))

    Search(item)

elif params['action'] == 'download':
    ## we pickup all our arguments sent from def Search()
    subs = Download(params["id"])
    ## we can return more than one subtitle for multi CD versions, for now we are still working out how to handle that in XBMC core
    for sub in subs:
        listitem = xbmcgui.ListItem(label=sub)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=sub, listitem=listitem, isFolder=False)

xbmcplugin.endOfDirectory(int(sys.argv[1]))  ## send end of directory to XBMC
