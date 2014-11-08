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
from BeautifulSoup import BeautifulSoup

try:
    import xbmc
    import xbmcvfs
    import xbmcaddon
    import xbmcplugin
    import xbmcgui
except ImportError:
    from stubs import xbmc, xbmcgui, xbmcaddon, xbmcplugin, xbmcvfs

try:
    #Python 2.6 +
    from hashlib import md5
except ImportError:
    #Python 2.5 and earlier
    from md5 import new as md5

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
        'NFKD', unicode(unicode(str, 'utf-8'))
    ).encode('ascii', 'ignore')


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

main_url = "http://napisy24.pl/search.php?str="
base_download_url = "http://napisy24.pl/download/"
down_url = "%s%s/" % (base_download_url, subtitle_type)


def hashFile(file_path):
    log(__name__, "Hash Standard file")
    longlongformat = 'q'  # long long
    bytesize = struct.calcsize(longlongformat)
    f = xbmcvfs.File(file_path)

    filesize = f.size()
    hash = filesize

    if filesize < 65536 * 2:
        return "SizeError"

    buffer = f.read(65536)
    f.seek(max(0, filesize - 65536), 0)
    buffer += f.read(65536)
    f.close()
    for x in range((65536 / bytesize) * 2):
        size = x * bytesize
        (l_value,) = struct.unpack(longlongformat, buffer[size:size + bytesize])
        hash += l_value
        hash = hash & 0xFFFFFFFFFFFFFFFF

    returnHash = "%016x" % hash
    return filesize, returnHash


def getallsubs(content, item, subtitles_list):
    languages_map = {'Polski': 'pl', 'Angielski': 'en', 'Niemiecki': 'de'}

    soup = BeautifulSoup(content)
    soup = soup.find("div", {"id": "defaultTable"})
    subs = soup("tr")
    first_row = True
    for row in subs[1:]:
        sub_id_re = '<a href=\"/download/(\d+)/\"><strong>'
        title_re = '<a href="/download/\d+?/"><strong>(.+?)</strong></a>'
        release_re = '<td[^>]*>([^<]+)<br />'
        rating_re = 'rednia ocena: (\d\,\d\d)<br />'
        lang_re = 'zyk:.+?alt="(.+?)"'
        disc_amount_re = '<td.+?style="text-align: center;">[\r\n\t ]+?(\d)[\r\n\t ]+?</td>'
        video_file_size_re = 'Rozmiar pliku: <strong>(\d+?)</strong>'
        video_file_size_re_multi = 'Rozmiar pliku:<br />- CD1: <strong>(\d+?)</strong>'

        row_str = str(row)

        if first_row:
            sub_id = re.findall(sub_id_re, row_str)
            subtitle = re.findall(title_re, row_str)
            release = re.findall(release_re, row_str)
            disc_amount = re.findall(disc_amount_re, row_str)
            first_row = False
        else:
            file_size, SubHash = hashFile(item["file_original_path"])

            if len(disc_amount) and disc_amount[0] > '1':
                video_file_size = re.findall(video_file_size_re_multi, row_str)
            else:
                video_file_size = re.findall(video_file_size_re, row_str)

            if len(video_file_size) == 0:
                video_file_size.append('0')
                sync_value = False
            else:
                video_file_size = unicode(video_file_size[0], "UTF-8")
                video_file_size = video_file_size.replace(u"\u00A0", "")
                if file_size == video_file_size:
                    sync_value = True
                else:
                    sync_value = False

            rating = re.findall(rating_re, row_str)
            language = re.findall(lang_re, row_str)

            if len(language) and language[0] in languages_map:
                language = [languages_map[language[0]]]
            else:
                language = []

            if len(language) > 0:
                first_row = True
                link = "%s%s/" % (down_url, sub_id[0])
                log(__name__, "Subtitles found: %s %s (link=%s)" % (subtitle[0], release, link))
                if xbmc.convertLanguage(language[0], xbmc.ISO_639_2) in item["3let_language"]:
                    rating_dot = rating[0].replace(",", ".")
                    if rating_dot == '0.00':
                        sub_rating = 0
                    else:
                        sub_rating = int(round(float(rating_dot) * 0.5, 0))

                    releases = release[0].split("; ")

                    for rel in releases:
                        filename_release = "%s.%s" % (subtitle[0].replace(" ", "."), rel)

                        subtitles_list.append({'lang_index': item["3let_language"].index(
                            xbmc.convertLanguage(language[0], xbmc.ISO_639_2)),
                                               'filename': filename_release,
                                               'link': link,
                                               'language_name': xbmc.convertLanguage(language[0],
                                                                                     xbmc.ENGLISH_NAME),
                                               'language_flag': xbmc.convertLanguage(language[0],
                                                                                     xbmc.ISO_639_1),
                                               'rating': '%s' % (sub_rating,),
                                               'sync': sync_value,
                                               'hearing_imp': 0
                        })
                else:
                    continue
            else:
                continue


def Search(item):  #standard input
    subtitles_list = []
    msg = ""
    if len(item["tvshow"]) > 0:
        for year in re.finditer(' \(\d{4}\)', item["tvshow"]):
            year = year.group()
            if len(year) > 0:
                tvshow = item["tvshow"].replace(year, "")
            else:
                continue
        tvshow_plus = item["tvshow"].replace(" ", "+")

        season_full = str("%02d" % (int(item["season"]),))
        episode_full = str("%02d" % (int(item["episode"]),))

        url = '%s%s+%sx%s' % (main_url, tvshow_plus, season_full, episode_full)
    else:
        original_title = item["title"]
        if len(original_title) == 0:
            log(__name__, "Original title not set")
            movie_title_plus = item["title"].replace(" ", "+")
            url = '%s%s' % (main_url, movie_title_plus)
        else:
            log(__name__, "Original title: [%s]" % (original_title))
            movie_title_plus = original_title.replace(" ", "+")
            url = '%s%s' % (main_url, movie_title_plus)
    log(__name__, "Fetching from [ %s ]" % (url))
    response = urllib2.urlopen(url)
    content = response.read()
    re_pages_string = 'postAction%3DszukajZaawansowane">(\d)</a>'
    page_nr = re.findall(re_pages_string, content)

    getallsubs(content, item, subtitles_list)
    for i in page_nr:
        main_url_pages = 'http://napisy24.pl/szukaj/&stronaArch=1&strona='
        rest_url = '%26postAction%3DszukajZaawansowane'
        url_2 = '%s%s&szukajNapis=%s%s' % (main_url_pages, i, item["title"], rest_url)
        response = urllib2.urlopen(url_2)
        content = response.read()
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

            url = "plugin://%s/?action=download&link=%s&filename=%s&language=%s" % (
                __scriptid__, it["link"], it["filename"], it["language_flag"])
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=listitem, isFolder=False)


def Download(link, filename):  #standard input

    subtitle_list = []
    exts = [".srt", ".sub", ".txt"]

    ## Cleanup temp dir, we recomend you download/unzip your subs in temp folder and
    ## pass that to XBMC to copy and activate
    if xbmcvfs.exists(__temp__):
        shutil.rmtree(__temp__)
    xbmcvfs.mkdirs(__temp__)

    cj = CookieJar()
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Charset': 'UTF-8,*;q=0.5',
        'Accept-Encoding': 'gzip,deflate,sdch',
        'Accept-Language': 'pl,pl-PL;q=0.8,en-US;q=0.6,en;q=0.4',
        'Connection': 'keep-alive',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/21.0.1180.83 Safari/537.1',
        'Referer': 'http://napisy24.pl/'
    }
    values = {'form_logowanieMail': __addon__.getSetting("username"),
              'form_logowanieHaslo': __addon__.getSetting("password"), 'postAction': 'sendLogowanie'}
    data = urllib.urlencode(values)
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    request = urllib2.Request("http://napisy24.pl/logowanie/", data, headers)
    response = opener.open(request)
    request = urllib2.Request(link, "", headers)
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
    item['file_original_path'] = urllib.unquote(
        xbmc.Player().getPlayingFile().decode('utf-8'))  # Full path of a playing file
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

    log(__name__, "item: %s" %(item))

    Search(item)

elif params['action'] == 'download':
    ## we pickup all our arguments sent from def Search()
    subs = Download(params["link"], params["filename"])
    ## we can return more than one subtitle for multi CD versions, for now we are still working out how to handle that in XBMC core
    for sub in subs:
        listitem = xbmcgui.ListItem(label=sub)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=sub, listitem=listitem, isFolder=False)

xbmcplugin.endOfDirectory(int(sys.argv[1]))  ## send end of directory to XBMC