# -*- coding: utf-8 -*- 

import time

start = time.time()

import os
import sys
import shutil
import unicodedata
import os.path
import re

import xbmc, xbmcvfs, xbmcaddon, xbmcgui, xbmcplugin

import json

from urllib.parse import unquote, unquote_plus, urlencode, quote_plus
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

from contextlib import closing

__addon__ = xbmcaddon.Addon()
__scriptid__ = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')
__language__ = __addon__.getLocalizedString

__cwd__ = xbmcvfs.translatePath(__addon__.getAddonInfo('path'))
__profile__ = xbmcvfs.translatePath(__addon__.getAddonInfo('profile'))
__temp__ = xbmcvfs.translatePath(os.path.join(__profile__, 'temp', ''))


BASE_URL = 'https://feliratok.eu/index.php'

TAGS = [
    'WEB-DL',
    'PROPER',
    'REPACK'
]

QUALITIES = [
    'HDTV',
    '720p',
    '1080p',
    'DVDRip',
    'BRRip',
    'BDRip',
    'WEB',
    'WEBRip'
]

RELEASERS = [
    '2HD',
    'AFG',
    'ASAP',
    'BiA',
    'DIMENSION',
    'EVOLVE',
    'FoV',
    'FQM',
    'IMMERSE',
    'KiNGS',
    'LOL',
    'REMARKABLE',
    'ORENJI',
    'TLA',

    '0SEC',
    'FLEET',
    'KILLERS',

    'AVS',
    'BATV'
    'SVA',

    'TBS'
]

HEADERS = {'User-Agent': 'xbmc subtitle plugin'}

ARCHIVE_EXTENSIONS = [
    '.zip',
    '.rar',
    '.cbr'
]

LANGUAGES = {
    "albán": "Albanian",
    "arab": "Arabic",
    "bolgár": "Bulgarian",
    "kínai": "Chinese",
    "horvát": "Croatian",
    "cseh": "Czech",
    "dán": "Danish",
    "holland": "Dutch",
    "angol": "English",
    "észt": "Estonian",
    "finn": "Finnish",
    "francia": "French",
    "német": "German",
    "görög": "Greek",
    "héber": "Hebrew",
    "hindi": "Hindi",
    "magyar": "Hungarian",
    "olasz": "Italian",
    "japán": "Japanese",
    "koreai": "Korean",
    "lett": "Latvian",
    "litván": "Lithuanian",
    "macedón": "Macedonian",
    "norvég": "Norwegian",
    "lengyel": "Polish",
    "portugál": "Portuguese",
    "román": "Romanian",
    "orosz": "Russian",
    "szerb": "Serbian",
    "szlovák": "Slovak",
    "szlovén": "Slovenian",
    "spanyol": "Spanish",
    "svéd": "Swedish",
    "török": "Turkish",
}

EPISODE_REGEXP = re.compile(r'S?(?P<season>\d+)([x_-]|\.)*E?(?P<episode>\d+)', re.IGNORECASE)

def recreate_tmp_dir():
    if xbmcvfs.exists(__temp__):
        try:
            fse = sys.getfilesystemencoding()
            if fse:
                debuglog("Remove %s directory with file system encoding: %s" % (__temp__, fse))
                shutil.rmtree(__temp__, ignore_errors=True)
            else:
                debuglog("Remove %s directory with out file system encoding" % __temp__)
                shutil.rmtree(__temp__, ignore_errors=True)
        except Exception as e:
            debuglog("Exception while delete %s: %s" % (__temp__, getattr(e, 'message', repr(e))))

    if not xbmcvfs.exists(__temp__):
        debuglog("Create %s directory" % __temp__)
        xbmcvfs.mkdirs(__temp__)

def normalize_string(str):
    return unicodedata.normalize('NFKD', str)


def lang_hun2eng(hunlang):
    return LANGUAGES[hunlang.lower()]


def debuglog(msg):
    xbmc.log(u"### [%s] - %s" % (__scriptid__, msg), level=xbmc.LOGDEBUG)


def send_request(params):
    url = "%s?%s" % (BASE_URL, urlencode(params))
    try:
        debuglog(url)
        request = Request(url, headers=HEADERS)
        return urlopen(request)
    except HTTPError as e:
        debuglog("HTTP Error: %s, %s" % (e.code, url))
    except URLError as e:
        debuglog("URL Error %s, %s" % (e.reason, url))
    except Exception as e:
        debuglog("Unexpected exception: %s" % getattr(e, 'message', repr(e)))

    return None


def query_data(params):
    with closing(send_request(params)) as response:
        if response:
            try:
                return json.loads(response.read())
            except ValueError as e:
                debuglog("Json Decode Error: %s" % getattr(e, 'msg', repr(e)))
            except Exception as e:
                debuglog("Unexpected exception: %s" % getattr(e, 'message', repr(e)))
    return None


def notification(id):
    xbmcgui.Dialog().notification(__scriptname__, __language__(id), os.path.join(__cwd__, "icon.png"), 2000)


def get_showids(item):
    ret = []
    pattern = r'^(?P<term>[^\(]*)(\s+\((?P<etc>\w{2,4})\))?$'
    match = re.search(pattern, item['tvshow'], re.I)
    if match:
        etc = match.group('etc')
        if etc and len(etc) == 4 and etc.isdigit():
            item['year'] = etc

        term = match.group('term')
        qparams = {'action': 'autoname', 'nyelv': '0', 'term': term}
        datas = query_data(qparams)
        if datas:
            if item['year']:
                year = str(item['year'])
                for data in datas:
                    if year in data['name']:
                        ret.append(data['ID'])
                        break
            else:
                ret = [x['ID'] for x in datas]
        if '-100x' in ret:
            ret = []

    ret.sort(reverse=True)

    return ret


def convert(item):
    ret = {'filename': item['fnev'], 'name': item['nev'].strip(), 'language_hun': item['language'], 'id': item['felirat'],
           'uploader': item['feltolto'].strip(), 'hearing': False, 'language_eng': lang_hun2eng(item['language'])}

    score = item['pontos_talalat'].count("1")
    ret['score'] = score
    ret['rating'] = str(score * 5 / 3)
    ret['sync'] = score == 5
    ret['flag'] = xbmc.convertLanguage(ret['language_eng'], xbmc.ISO_639_1)
    ret['seasonpack'] = item['evadpakk'] == '1'

    return ret


def set_param_if_filename_contains(data, params, paramname, items):
    compare = data['filename'].lower()
    for item in items:
        if item.lower() in compare:
            params[paramname] = item
            return item
    return None


def remove_duplications(items):
    ret = {}
    for item in items:
        new_item = ret.get(item['id'], item)
        if item['score'] > new_item['score']:
            new_item = item
        ret[item['id']] = new_item
    return list(ret.values())


def convert_and_filter(items, episode):
    data = [x for x in items if int(x['ep']) == int(item['episode']) or x['evadpakk'] == '1']
    data = list(map(convert, data))
    data = [x for x in data if x['language_eng'] in item['languages']]
    data = remove_duplications(data)
    return data


def search_subtitles_for_show(item, showid):
    qparams = {'action': 'xbmc', 'sid': showid, 'ev': item['season']}

    set_param_if_filename_contains(item, qparams, 'relj', TAGS)
    set_param_if_filename_contains(item, qparams, 'relf', QUALITIES)
    releaser = set_param_if_filename_contains(item, qparams, 'relr', RELEASERS)

    data = query_data(qparams)

    if not data:
        debuglog("No subtitle found for %s" % item['tvshow'])
        return None

    if type(data) is dict:
        data = list(data.values())

    searchlist = convert_and_filter(data, item['episode'])

    searchlist.sort(key=lambda x: (x['score'], x['language_eng'] == item['preferredlanguage'], x['language_eng'],
                                   releaser.lower() in x['filename'].lower() if releaser else x['filename']),
                    reverse=True)

    return searchlist


def search_subtitles(item, recursive=True):
    if not item['season'] and not item['episode']:
        debuglog("No season or episode info found for %s" % item['tvshow'])
        return None

    showids = get_showids(item)
    if not showids:
        debuglog("No ids found for %s" % item['tvshow'])
        if recursive and normalize_string(xbmc.getInfoLabel("VideoPlayer.TVshowtitle")):
            debuglog("Second try: search by filename")
            return search_subtitles(setup_tvshow_data(item, False), False)
        else:
            return None

    searchdict = {}
    for showid in showids:
        subtitles = search_subtitles_for_show(item, showid)
        if subtitles:
            avg = sum(x['score'] for x in subtitles) / float(len(subtitles))
            searchdict[(avg, showid)] = subtitles

    searchlist = []
    for key in sorted(searchdict, reverse=True):
        searchlist.extend(searchdict[key])

    return searchlist


def search(item):
    debuglog(item)
    subtitles_list = search_subtitles(item)

    if subtitles_list:
        index = 0
        for it in subtitles_list:
            index += 1
            label = "%s [%s]" % (it['filename'], it['uploader'])

            if it['seasonpack']:
                label += (' (%s)' % (__language__(32503)))

            listitem = xbmcgui.ListItem(label=it['language_eng'],label2=label)
            listitem.setArt({'icon': it['rating'],'thumb': it['flag']})
            listitem.setProperty('sync', ('false', 'true')[it['sync']])
            listitem.setProperty('hearing_imp', ('false', 'true')[it.get('hearing', False)])

            qparams = {'action': 'download', 'actionsortorder': str(index).zfill(2), 'id': it['id'],
                       'filename': it['filename']}
            url = "plugin://%s/?%s" % (__scriptid__, urlencode(qparams))

            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=listitem, isFolder=False)


def is_archive(filename):
    if filename:
        for ext in ARCHIVE_EXTENSIONS:
            if filename.endswith(ext):
                return True
    return False


def download_file(item):
    filename = unquote_plus(item['filename']).replace(' ', '_')
    localfile = os.path.join(__temp__, filename)
    qparams = {'action': 'letolt', 'felirat': item['id']}

    with closing(send_request(qparams)) as response:
        if response:
            with open(localfile, 'wb') as fd:
                shutil.copyfileobj(response, fd)
            return localfile
    return None


def is_match(item, filename):
    for match in EPISODE_REGEXP.finditer(filename):
        season = int(item['season'])
        episode = int(item['episode'])
        fs = int(match.group('season'))
        fe = int(match.group('episode'))
        if season == fs and episode == fe:
            return True

    return False


def recursive_search(path):
    (dirs, files) = xbmcvfs.listdir(path)
    if files:
        for file in files:
            if is_match(item, file):
                return "%s/%s" % (path, file)

    if dirs:
        for dir in dirs:
            file = recursive_search("%s/%s" % (path, dir, 'utf-8'))
            if file:
                return file
    return None


def download(item):
    debuglog(item)
    subtitle = None
    downloaded = download_file(item)

    if is_archive(downloaded):
        debuglog('%s downloaded file is an archive' % downloaded)
        archive = 'archive://%s' % quote_plus(downloaded)
        subtitle = recursive_search(archive)

        if not subtitle:
            debuglog("No subtitle found by search. Open dialog from %s" % archive)
    else:
        subtitle = downloaded

    if subtitle:
        debuglog("Downloaded subtitle: %s" % subtitle)
        listitem = xbmcgui.ListItem(label=subtitle)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=subtitle, listitem=listitem, isFolder=False)


def clean_movie_title(item, use_dir):
    debuglog("getCleanMovieTitle:  %s" % use_dir)
    infos = xbmc.getCleanMovieTitle(item['file_original_path'], use_dir)

    if not 'year' in item or not item['year']:
        item['year'] = infos[1]

    title_pattern = r'^(?P<title>.+)S(?P<season>\d+)E(?P<episode>\d+).*$'
    title_match = re.search(title_pattern, infos[0], re.IGNORECASE)

    if title_match:
        item['tvshow'] = title_match.group('title').strip()
        item['season'] = title_match.group('season')
        item['episode'] = title_match.group('episode')

    return infos, (title_match is not None)


def clean_title(item):
    infos, title_match = clean_movie_title(item, True)

    if not title_match:
        infos, title_match = clean_movie_title(item, False)

    return None if title_match else infos


def setup_tvshow_data(item, tryVideoPlayer=True):
    tvshow = normalize_string(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))
    if tryVideoPlayer and tvshow:
        item['tvshow'] = tvshow
        item['season'] = str(xbmc.getInfoLabel("VideoPlayer.Season"))
        item['episode'] = str(xbmc.getInfoLabel("VideoPlayer.Episode"))
    else:
        infos = clean_title(item)

        if infos:
            item['tvshow'] = infos[0]

            filename_pattern = r'^(.*)S(?P<season>\d+)E(?P<episode>\d+)(.*)$'
            filename_match = re.search(filename_pattern, item['filename'], re.IGNORECASE)

            if filename_match:
                item['season'] = filename_match.group('season')
                item['episode'] = filename_match.group('episode')

    return item


def setup_path(item):
    item['file_original_path'] = unquote(xbmc.Player().getPlayingFile())
    if item['file_original_path'].find("http") > -1:
        item['temp'] = True

    elif item['file_original_path'].find("rar://") > -1:
        item['rar'] = True
        item['file_original_path'] = os.path.dirname(item['file_original_path'][6:])

    elif item['file_original_path'].find("stack://") > -1:
        item['stack'] = True
        stackPath = item['file_original_path'].split(" , ")
        item['file_original_path'] = stackPath[0][8:]

    return item


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
            splitparams = {}
            splitparams = pairsofparams[i].split('=')
            if (len(splitparams)) == 2:
                param[splitparams[0]] = splitparams[1]

    return param



debuglog("%s - %s" % (__scriptname__, __version__))
debuglog("start time %s" % (time.time() - start))

recreate_tmp_dir()
params = get_params()
debuglog(params)

if params['action'] == 'search':
    item = {'temp': False, 'rar': False, 'stack': False, 'year': '',
            'title': normalize_string(xbmc.getInfoLabel("VideoPlayer.OriginalTitle")),
            'languages': [], 'preferredlanguage': params.get('preferredlanguage')}

    for lang in unquote(params['languages']).split(","):
        item['languages'].append(lang)

    if not item['title']:
        item['title'] = normalize_string(xbmc.getInfoLabel("VideoPlayer.Title"))
    setup_path(item)
    item['filename'] = os.path.basename(item['file_original_path'])

    item = setup_tvshow_data(item)

    if item['episode'].lower().find("s") > -1:
        item['season'] = "0"
        item['episode'] = item['episode'][-1:]

    search(item)

elif params['action'] == 'download':
    item = {'id': params['id'], 'filename': params['filename']}
    item = setup_tvshow_data(setup_path(item))
    download(item)

elif params['action'] == 'manualsearch':
    notification(32502)

debuglog("full time %s" % (time.time() - start))

xbmcplugin.endOfDirectory(int(sys.argv[1]))
