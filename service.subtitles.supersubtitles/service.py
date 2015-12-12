# -*- coding: utf-8 -*- 

import time

start = time.time()

import os
import sys
import shutil
import unicodedata
import os.path
import re

import xbmc
import xbmcvfs
import xbmcaddon
import xbmcgui
import xbmcplugin

import json

import urllib
import urllib2

__addon__ = xbmcaddon.Addon()
#__author__ = __addon__.getAddonInfo('author')
__scriptid__ = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')
__language__ = __addon__.getLocalizedString

__cwd__ = xbmc.translatePath(__addon__.getAddonInfo('path')).decode("utf-8")
__profile__ = xbmc.translatePath(__addon__.getAddonInfo('profile')).decode("utf-8")
#__resource__   = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) ).decode("utf-8")
__temp__ = xbmc.translatePath(os.path.join(__profile__, 'temp', '')).decode("utf-8")

#sys.path.append (__resource__)

BASE_URL = 'http://www.feliratok.info/index.php'

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
    'BDRip'
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
    'KILLERS'
]

HEADERS = {'User-Agent': 'xbmc subtitle plugin'}

ARCHIVE_EXTENSIONS = [
    '.zip',
    '.cbz',
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


def recreate_dir(path):
    if xbmcvfs.exists(path):
        try:
            fse = sys.getfilesystemencoding()
            if fse:
                debuglog("with file system encoding: %s" % fse)
                shutil.rmtree(__temp__.encode(fse), ignore_errors=True)
            else:
                debuglog("with out file system encoding")
                shutil.rmtree(__temp__, ignore_errors=True)
        except Exception as e:
            errorlog("Exception while delete %s: %s" % (__temp__, e.message))

    if not xbmcvfs.exists(path):
        xbmcvfs.mkdirs(path)


def normalize_string(str):
    return unicodedata.normalize('NFKD', unicode(unicode(str, 'utf-8'))).encode('ascii', 'ignore')


def lang_hun2eng(hunlang):
    return LANGUAGES[hunlang.encode("utf-8").lower()]


def log(msg, level):
    xbmc.log((u"### [%s] - %s" % (__scriptid__, msg,)).encode('utf-8'), level=level)


def infolog(msg):
    log(msg, xbmc.LOGNOTICE)


def errorlog(msg):
    log(msg, xbmc.LOGERROR)


def debuglog(msg):
    log(msg, xbmc.LOGDEBUG)
    #log(msg, xbmc.LOGNOTICE)


def send_request(params):
    url = "%s?%s" % (BASE_URL, urllib.urlencode(params))
    try:
        debuglog(url)
        request = urllib2.Request(url, headers=HEADERS)
        return urllib2.urlopen(request)
    except urllib2.HTTPError as e:
        errorlog("HTTP Error: %s, %s" % (e.code, url))
    except urllib2.URLError as e:
        errorlog("URL Error %s, %s" % (e.reason, url))
    except Exception as e:
        errorlog("Unexpected exception: %s" % e.message)

    return None


def query_data(params):
    response = send_request(params)
    if response:
        try:
            return json.load(response, 'utf-8')
        except ValueError as e:
            errorlog("Json Decode Error: %s" % e.message)
        except Exception as e:
            errorlog("Unexpected exception: %s" % e.message)
    return None


def notification(id):
    xbmc.executebuiltin(u'Notification(%s,%s,%s,%s)' % (
        __scriptname__,
        __language__(id),
        2000,
        os.path.join(__cwd__, "icon.png")
    )
    )


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
                ret = map(lambda x: x['ID'], datas)
        if '-100x' in ret:
            ret = []

    ret.sort(reverse=True)

    return ret


def convert(item):
    ret = {'filename': item['fnev'], 'name': item['nev'].strip(), 'language_hun': item['language'], 'id': item['felirat'],
           'uploader': item['feltolto'].strip(), 'hearing': False, 'language_eng': lang_hun2eng(item['language'])}

    score = int(item['pontos_talalat'], 2)
    ret['score'] = score
    ret['rating'] = str(score * 5 / 7)
    ret['sync'] = score >= 6
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
    return ret.values()


def convert_and_filter(items, episode):
    data = filter(lambda x: int(x['ep']) == int(item['episode']) or x['evadpakk'] == '1', items)
    data = map(convert, data)
    data = filter(lambda x: x['language_eng'] in item['languages'], data)
    data = remove_duplications(data)
    return data


def search_subtitles_for_show(item, showid):
    #qparams = {'action': 'xbmc', 'sid': showid, 'ev': item['season'], 'rtol': item['episode']};
    qparams = {'action': 'xbmc', 'sid': showid, 'ev': item['season']}

    set_param_if_filename_contains(item, qparams, 'relj', TAGS)
    set_param_if_filename_contains(item, qparams, 'relf', QUALITIES)
    releaser = set_param_if_filename_contains(item, qparams, 'relr', RELEASERS)

    data = query_data(qparams)

    if not data:
        debuglog("No subtitle found for %s" % item['tvshow'])
        return None

    # convert dict to list
    if type(data) is dict:
        data = data.values()

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
            #label="%s | %s | %s"%(it['name'], it['filename'], it['uploader'])
            label = "%s [%s]" % (it['filename'], it['uploader'])

            if it['seasonpack']:
                label += (' (%s)' % (__language__(32503)))

            listitem = xbmcgui.ListItem(label=it['language_eng'],
                                        label2=label,
                                        iconImage=it['rating'],
                                        thumbnailImage=it['flag']
            )
            listitem.setProperty('sync', ('false', 'true')[it['sync']])
            listitem.setProperty('hearing_imp', ('false', 'true')[it.get('hearing', False)])

            qparams = {'action': 'download', 'actionsortorder': str(index).zfill(2), 'id': it['id'],
                       'filename': it['filename'].encode('utf8')}
            url = "plugin://%s/?%s" % (__scriptid__, urllib.urlencode(qparams))

            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=listitem, isFolder=False)


def is_archive(filename):
    if filename:
        for ext in ARCHIVE_EXTENSIONS:
            if filename.endswith(ext):
                return True
    return False


def extract(archive):
    basename = os.path.basename(archive).replace('.', '_').decode('utf-8')
    extracted = os.path.join(__temp__, basename, '')
    xbmc.executebuiltin(('XBMC.Extract("%s","%s")' % (archive, extracted)).encode('utf-8'), True)

    if xbmcvfs.exists(extracted):
        return extracted
    else:
        errorlog('Error while extracting %s' % archive)
        return None


def download_file(item):
    filename = urllib.unquote_plus(item['filename'].decode("utf-8")).replace(' ', '_').decode('utf-8')
    localfile = os.path.join(__temp__, filename)
    qparams = {'action': 'letolt', 'felirat': item['id']}

    response = send_request(qparams)

    if response:
        with open(localfile, 'wb') as fd:
            shutil.copyfileobj(response, fd)

        return localfile

    return None


def is_match(item, filename):
    pattern = r'S?(?P<season>\d+)([x_-]|\.)*E?(?P<episode>\d+)'
    regexp = re.compile(pattern,  re.IGNORECASE)
    for match in regexp.finditer(filename):
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
            file = os.path.join(path, file.decode('utf-8'))
            filename = os.path.basename(file)
            if is_match(item, filename):
                return file

    if dirs:
        for dir in dirs:
            file = recursive_search(os.path.join(path, dir.decode('utf-8')))
            if file:
                return file

    return None


def download(item):
    debuglog(item)
    subtitle = None
    downloaded = download_file(item)

    if is_archive(downloaded):
        debuglog('Downloaded file is an archive')
        extracted = extract(downloaded)
        if extracted:
            subtitle = recursive_search(extracted)
    else:
        subtitle = downloaded

    if subtitle:
        debuglog("Downloaded subtitle: %s" % subtitle)
        listitem = xbmcgui.ListItem(label=subtitle)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=subtitle, listitem=listitem, isFolder=False)
        #notification(32501)


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
    item['file_original_path'] = urllib.unquote(xbmc.Player().getPlayingFile().decode('utf-8'))
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



infolog("%s - %s" % (__scriptname__, __version__))
debuglog("start time %s" % (time.time() - start))

recreate_dir(__temp__)
params = get_params()
debuglog(params)

if params['action'] == 'search':
    item = {'temp': False, 'rar': False, 'stack': False, 'year': xbmc.getInfoLabel("VideoPlayer.Year"),
            'title': normalize_string(xbmc.getInfoLabel("VideoPlayer.OriginalTitle")),
            'languages': [], 'preferredlanguage': params.get('preferredlanguage')}

    for lang in urllib.unquote(params['languages']).decode('utf-8').split(","):
        item['languages'].append(lang)

    if not item['title']:
        item['title'] = normalize_string(xbmc.getInfoLabel("VideoPlayer.Title"))
    setup_path(item)
    item['filename'] = os.path.basename(item['file_original_path'])

    item = setup_tvshow_data(item)

    if item['episode'].lower().find("s") > -1:  # Check if season is "Special"
        item['season'] = "0"  #
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
