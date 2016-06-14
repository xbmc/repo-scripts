# -*- coding: utf-8 -*-
#from pydev import pydevd
#pydevd.settrace('localhost', port=5555, stdoutToServer=True, stderrToServer=True,
#                suspend=True,
#                trace_only_current_thread=False
#)


import os
import sys
import urllib2
import urlparse
import xbmc
import xbmcvfs
import xbmcaddon
import xbmcgui
import xbmcplugin
HAS_XBMC = True
import urllib
import shutil
import unicodedata
import re
import string
import difflib
import HTMLParser
from thaisubtitles import getallsubs, search_manual, search_movie

__addon__ = xbmcaddon.Addon()
__author__ = __addon__.getAddonInfo('author')
__scriptid__ = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')
__language__ = __addon__.getLocalizedString

__cwd__ = xbmc.translatePath(__addon__.getAddonInfo('path')).decode("utf-8")
__profile__ = xbmc.translatePath(__addon__.getAddonInfo('profile')).decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib')).decode("utf-8")
__temp__ = xbmc.translatePath(os.path.join(__profile__, 'temp')).decode("utf-8")

sys.path.append(__resource__)


# Seasons as strings for searching
seasons = ["Specials", "First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh", "Eighth", "Ninth", "Tenth"]
seasons = seasons + ["Eleventh", "Twelfth", "Thirteenth", "Fourteenth", "Fifteenth", "Sixteenth", "Seventeenth",
                     "Eighteenth", "Nineteenth", "Twentieth"]
seasons = seasons + ["Twenty-first", "Twenty-second", "Twenty-third", "Twenty-fourth", "Twenty-fifth", "Twenty-sixth",
                     "Twenty-seventh", "Twenty-eighth", "Twenty-ninth"]



def log(module, msg):
    xbmc.log((u"### [%s] - %s" % (module, msg,)).encode('utf-8'), level=xbmc.LOGDEBUG)


# from http://trac.buildbot.net/ticket/485
def rmdirRecursive(dir):
    """This is a replacement for shutil.rmtree that works better under
    windows. Thanks to Bear at the OSAF for the code."""
    if not os.path.exists(dir):
        log(__name__, "rmdirRecursive: dir doesn't exit")
        return

    if os.path.islink(dir.encode('utf8')):
        os.remove(dir.encode('utf8'))
        return

    # Verify the directory is read/write/execute for the current user
    os.chmod(dir, 0700)

    # os.listdir below only returns a list of unicode filenames if the parameter is unicode
    # Thus, if a non-unicode-named dir contains a unicode filename, that filename will get garbled.
    # So force dir to be unicode.
    try:
        dir = dir.decode('utf8','ignore')
    except:
        log(__name__, "rmdirRecursive: decoding from UTF-8 failed: %s" % dir)
        return

    for name in os.listdir(dir):
        try:
            name = name.decode('utf8','ignore')
        except:
            log(__name__, "rmdirRecursive: decoding from UTF-8 failed: %s" % name)
            continue
        full_name = os.path.join(dir, name)
        # on Windows, if we don't have write permission we can't remove
        # the file/directory either, so turn that on
        if os.name == 'nt':
            if not os.access(full_name, os.W_OK):
                # I think this is now redundant, but I don't have an NT
                # machine to test on, so I'm going to leave it in place
                # -warner
                os.chmod(full_name, 0600)

        if os.path.islink(full_name):
            os.remove(full_name) # as suggested in bug #792
        elif os.path.isdir(full_name):
            rmdirRecursive(full_name)
        else:
            if os.path.isfile(full_name):
                os.chmod(full_name, 0700)
            os.remove(full_name)
    os.rmdir(dir)



def append_subtitles(items):
    for item in items:
        listitem = xbmcgui.ListItem(label=item['lang']['name'],
                                    label2=item['filename'],
                                    iconImage=item['rating'],
                                    thumbnailImage=item['lang']['2let'])

        listitem.setProperty("sync",  'true' if item["sync"] else 'false')
        listitem.setProperty("hearing_imp", 'true' if item["hearing_imp"] else 'false')

        ## below arguments are optional, it can be used to pass any info needed in download function
        ## anything after "action=download&" will be sent to addon once user clicks listed subtitle to downlaod
        url = "plugin://%s/?%s" % (__scriptid__,
                                   urllib.urlencode(dict(
                                       action="download",
                                       link=item['link'],
                                       filename=item['filename'])))
        if 'find' in item:
            url += "&find=%s" % item['find']
        ## add it to list, this can be done as many times as needed for all subtitles found
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=listitem, isFolder=False)


def search_tvshow(tvshow, season, episode, languages, filename):
    tvshow = string.strip(tvshow)

    search_string = "%s s%#02de%#02d" % (tvshow, int(season), int(episode))
    log(__name__, "Search tvshow = %s" % search_string)
    res = search_manual(search_string, languages, filename)
    if res:
        return res
    # try and be less exact
    search_string = "%s %i %i" % (tvshow, int(season), int(episode))
    log(__name__, "Search tvshow = %s" % search_string)
    res = search_manual(search_string, languages, filename)
    return res



def search_movie(title, year, languages, filename):
    title = string.strip(title)

    log(__name__, "Search movie = %s" % title)
    res = search_manual(title, languages, filename)
    for result in res:
        rtitle, ryear = xbmc.getCleanMovieTitle(result['filename'])
        rtitle, ryear = rtitle.strip().lower(), ryear.strip().lower()
        log(__name__, "Got cleaned movie result of %s (%s) '%s'" % (rtitle, ryear, result['filename']))
        if (rtitle, ryear) == (title, year):
            yield result
        #TODO we should really return those that don't match the year in case all else fails


def search(item):
    res = []
    filename = os.path.splitext(os.path.basename(item['file_original_path']))[0]
    log(__name__, "Search_thaisubtitle='%s', filename='%s', addon_version=%s" % (item, filename, __version__))

    if item['mansearch']:
        res = search_manual(item['mansearchstr'], item['3let_language'], filename)
        return append_subtitles(res)
    elif item['tvshow']:
        res = search_tvshow(item['tvshow'], item['season'], item['episode'], item['3let_language'], filename)
        if res:
            return append_subtitles(res)
    elif item['title'] and item['year']:
        res = search_manual(item['title'], item['3let_language'], filename, )
        if res:
            return append_subtitles(res)

    title, year = xbmc.getCleanMovieTitle(filename)
    log(__name__, "clean title: \"%s\" (%s)" % (title, year))
    try:
        yearval = int(year)
    except ValueError:
        yearval = 0
    if title and yearval > 1900:
        res = search_movie(title, year, item['3let_language'], filename)
        if res:
            return append_subtitles(res)
    match = re.search(r'\WS(?P<season>\d\d)E(?P<episode>\d\d)', title, flags=re.IGNORECASE)
    if match is not None:
        tvshow = string.strip(title[:match.start('season')-1])
        season = string.lstrip(match.group('season'), '0')
        episode = string.lstrip(match.group('episode'), '0')
        res = search_tvshow(tvshow, season, episode, item['3let_language'], filename)
        if res:
            return append_subtitles(res)
    # last fall back
    res = search_manual(filename, item['3let_language'], filename)
    if res:
        return append_subtitles(res)
    return []


def download(link, search_string=""):
    exts = [".srt", ".sub", ".txt", ".smi", ".ssa", ".ass"]
    subtitle_list = []
    response = urllib2.urlopen(link)

    if os.path.exists(__temp__):
        rmdirRecursive(__temp__)
    xbmcvfs.mkdirs(__temp__)

    local_tmp_file = os.path.join(__temp__, "thaisubtitle.xxx")
    packed = False

    try:
        log(__name__, "Saving subtitles to '%s'" % local_tmp_file)
        local_file_handle = open(local_tmp_file, "wb")
        local_file_handle.write(response.read())
        local_file_handle.close()

        #Check archive type (rar/zip/else) through the file header (rar=Rar!, zip=PK)
        myfile = open(local_tmp_file, "rb")
        myfile.seek(0)
        if myfile.read(1) == 'R':
            typeid = "rar"
            packed = True
            log(__name__, "Discovered RAR Archive")
        else:
            myfile.seek(0)
            if myfile.read(1) == 'P':
                typeid = "zip"
                packed = True
                log(__name__, "Discovered ZIP Archive")
            else:
                typeid = "srt"
                packed = False
                log(__name__, "Discovered a non-archive file")
        myfile.close()
        local_tmp_file = os.path.join(__temp__, "thaisubtitle." + typeid)
        os.rename(os.path.join(__temp__, "thaisubtitle.xxx"), local_tmp_file)
        log(__name__, "Saving to %s" % local_tmp_file)
    except:
        log(__name__, "Failed to save subtitle to %s" % local_tmp_file)

    if packed:
        xbmc.sleep(500)
        xbmc.executebuiltin(('XBMC.Extract("%s","%s")' % (local_tmp_file, __temp__,)).encode('utf-8'), True)

    for file in xbmcvfs.listdir(__temp__)[1]:
        file = os.path.join(__temp__, file)
        if os.path.splitext(file)[1] in exts:
            if search_string and string.find(string.lower(file), string.lower(search_string)) == -1:
                continue
            log(__name__, "=== returning subtitle file %s" % file)

            # Convert file to utf8 from TIS-620
            f = open(file, 'r+')
            text = f.read().decode('TIS-620').encode('utf-8')
            f.seek(0)
            f.write(text)
            f.close()

            subtitle_list.append(file)

    if len(subtitle_list) == 0:
        if search_string:
            xbmc.executebuiltin((u'Notification(%s,%s)' % (__scriptname__ , __language__(32002))).encode('utf-8'))
        else:
            xbmc.executebuiltin((u'Notification(%s,%s)' % (__scriptname__ , __language__(32003))).encode('utf-8'))

    return subtitle_list


def normalizeString(str):
    return unicodedata.normalize(
        'NFKD', unicode(unicode(str, 'utf-8'))
    ).encode('ascii', 'ignore')


def get_params():
    param = {}
    paramstring = sys.argv[2]

    if len(paramstring) >= 2:
        params = paramstring
        cleanedparams = params.replace('?', '')
        if (params[len(params) - 1] == '/'):
            params = params[0:len(params) - 2]
        param = dict(urlparse.parse_qsl(cleanedparams))

    return param


params = get_params()



if params['action'] == 'search' or params['action'] == 'manualsearch':

    item = {}
    item['temp'] = False
    item['rar'] = False
    item['mansearch'] = False
    item['year'] = xbmc.getInfoLabel("VideoPlayer.Year")                             # Year
    item['season'] = str(xbmc.getInfoLabel("VideoPlayer.Season"))                    # Season
    item['episode'] = str(xbmc.getInfoLabel("VideoPlayer.Episode"))                  # Episode
    item['tvshow'] = normalizeString(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))   # Show
    item['title'] = normalizeString(xbmc.getInfoLabel("VideoPlayer.OriginalTitle"))  # try to get original title
    item['file_original_path'] = urllib.unquote(xbmc.Player().getPlayingFile().decode('utf-8'))  # Full path
    item['3let_language'] = []
    preferred_language = params['preferredlanguage'].decode('utf-8') if 'preferredlanguage' in params else None

    if 'searchstring' in params:
        item['mansearch'] = True
        item['mansearchstr'] = params['searchstring']

    for lang in urllib.unquote(params['languages']).decode('utf-8').split(","):
        item['3let_language'].append(xbmc.convertLanguage(lang, xbmc.ISO_639_2))
    if preferred_language:
        log('main','Using preferred language: %s' % preferred_language)
        item['3let_language'].append(xbmc.convertLanguage(preferred_language, xbmc.ISO_639_2))

    if item['title'] == "":
        item['title'] = normalizeString(xbmc.getInfoLabel("VideoPlayer.Title"))      # no original title, get just Title

    if item['episode'].lower().find("s") > -1:                                      # Check if season is "Special"
        item['season'] = "0"                                                          #
        item['episode'] = item['episode'][-1:]

    if item['file_original_path'].find("http") > -1:
        item['temp'] = True
        # Not sure why its double quoted
        item['file_original_path'] = urlparse.unquote(item['file_original_path'])

    elif item['file_original_path'].find("rar://") > -1:
        item['rar'] = True
        item['file_original_path'] = os.path.dirname(item['file_original_path'][6:])

    elif item['file_original_path'].find("stack://") > -1:
        stackPath = item['file_original_path'].split(" , ")
        item['file_original_path'] = stackPath[0][8:]

    search(item)

elif params['action'] == 'download':
    ## we pickup all our arguments sent from def Search()
    if 'find' in params:
        subs = download(params["link"], params["find"])
    else:
        subs = download(params["link"])
    ## we can return more than one subtitle for multi CD versions, for now we are still working out how to handle that
    ## in XBMC core
    for sub in subs:
        listitem = xbmcgui.ListItem(label=sub)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=sub, listitem=listitem, isFolder=False)

xbmcplugin.endOfDirectory(int(sys.argv[1]))  # send end of directory to XBMC



  
  
  
  
  
  
  
    
