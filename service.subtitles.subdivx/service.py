# -*- coding: utf-8 -*-
# Subdivx.com subtitles, based on a mod of Undertext subtitles
# Adaptation: enric_godes@hotmail.com | Please use email address for your
# comments
# Port to XBMC 13 Gotham subtitles infrastructure: cramm, Mar 2014

from __future__ import print_function
import os
from os.path import join as pjoin
from pprint import pformat
import re
import shutil
import sys
import time
import unicodedata
import urllib
from urlparse import parse_qs

try:
    import xbmc
except ImportError:
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        import unittest  # NOQA
        try:
            import mock  # NOQA
        except ImportError:
            print("You need to install the mock Python library to run "
                  "unit tests.\n")
            sys.exit(1)
else:
    import xbmcaddon
    import xbmcgui
    import xbmcplugin
    import xbmcvfs

__addon__ = xbmcaddon.Addon()
__author__     = __addon__.getAddonInfo('author')
__scriptid__   = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__    = __addon__.getAddonInfo('version')
__language__   = __addon__.getLocalizedString

__cwd__        = xbmc.translatePath(__addon__.getAddonInfo('path')).decode("utf-8")
__profile__    = xbmc.translatePath(__addon__.getAddonInfo('profile')).decode("utf-8")
__resource__   = xbmc.translatePath(pjoin(__cwd__, 'resources', 'lib')).decode("utf-8")
__temp__       = xbmc.translatePath(pjoin(__profile__, 'temp')).decode("utf-8")

sys.path.append(__resource__)


MAIN_SUBDIVX_URL = "http://www.subdivx.com/"
SEARCH_PAGE_URL = MAIN_SUBDIVX_URL + "index.php?accion=5&masdesc=&oxdown=1&pg=%(page)s&buscar=%(query)s"

INTERNAL_LINK_URL = "plugin://%(scriptid)s/?action=download&id=%(id)s&filename=%(filename)s"
SUB_EXTS = ['srt', 'sub', 'txt']
HTTP_USER_AGENT = "User-Agent=Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.2.3) Gecko/20100401 Firefox/3.6.3 ( .NET CLR 3.5.30729)"

PAGE_ENCODING = 'latin1'


def is_subs_file(fn):
    """Detect if the file has an extension we recognise as subtitle."""
    ext = fn.split('.')[-1]
    return ext.upper() in [e.upper() for e in SUB_EXTS]


# ============================
# Regular expression patterns
# ============================

# Subtitle pattern example:
# <div id="menu_titulo_buscador"><a class="titulo_menu_izq" href="http://www.subdivx.com/X6XMjEzMzIyX-iron-man-2-2010.html">Iron Man 2 (2010)</a></div>
# <img src="img/calif5.gif" class="detalle_calif">
# </div><div id="buscador_detalle">
# <div id="buscador_detalle_sub">Para la versión Iron.Man.2.2010.480p.BRRip.XviD.AC3-EVO, sacados de acá. ¡Disfruten!</div><div id="buscador_detalle_sub_datos"><b>Downloads:</b> 4673 <b>Cds:</b> 1 <b>Comentarios:</b> <a rel="nofollow" href="popcoment.php?idsub=MjEzMzIy" onclick="return hs.htmlExpand(this, { objectType: 'iframe' } )">14</a> <b>Formato:</b> SubRip <b>Subido por:</b> <a class="link1" href="http://www.subdivx.com/X9X303157">TrueSword</a> <img src="http://www.subdivx.com/pais/2.gif" width="16" height="12"> <b>el</b> 06/09/2010  </a></div></div>
# <div id="menu_detalle_buscador">

SUBTITLE_RE = re.compile(r'''<a\s+class="titulo_menu_izq2?"\s+
                         href="http://www.subdivx.com/(?P<id>.+?)\.html">
                         .+?<div\s+id="buscador_detalle_sub">(?P<comment>.*?)</div>
                         .+?<b>Downloads:</b>(?P<downloads>.+?)
                         <b>Cds:</b>
                         .+?<b>Subido\ por:</b>\s*<a.+?>(?P<uploader>.+?)</a>.+?</div></div>''',
                         re.IGNORECASE | re.DOTALL | re.VERBOSE | re.UNICODE |
                         re.MULTILINE)
# 'id' named group: ID to fetch the subs files
# 'comment' named group: Translation author comment, may contain filename
# 'downloads' named group: Downloads, used for ratings

DOWNLOAD_LINK_RE = re.compile(r'bajar.php\?id=(.*?)&u=(.*?)\"', re.IGNORECASE |
                              re.DOTALL | re.MULTILINE | re.UNICODE)

# ==========
# Functions
# ==========


def log(msg):
    s = u"SUBDIVX - %s" % msg
    xbmc.log(s.encode('utf-8'), level=xbmc.LOGDEBUG)


def get_url(url):
    class MyOpener(urllib.FancyURLopener):
        # version = HTTP_USER_AGENT
        version = ''
    my_urlopener = MyOpener()
    log(u"get_url(): Getting url %s" % url)
    try:
        response = my_urlopener.open(url)
        content = response.read()
    except Exception:
        log(u"get_url(): Failed to get url: %s" % url)
        content = None
    return content


def get_all_subs(searchstring, languageshort, languagelong, file_original_path):
    subs_list = []
    if languageshort == "es":
        log(u"Getting '%s' subs ..." % languageshort)
        page = 1
        while True:
            url = SEARCH_PAGE_URL % {'page': page,
                                     'query': urllib.quote_plus(searchstring)}
            content = get_url(url)
            if content is None or not SUBTITLE_RE.search(content):
                break
            for match in SUBTITLE_RE.finditer(content):
                id = match.groupdict()['id']
                dls = re.sub(r'[,.]', '', match.groupdict()['downloads'])
                downloads = int(dls)
                rating = downloads / 1000
                if rating > 10:
                    rating = 10
                description = match.groupdict()['comment']
                text = description.strip()
                # Remove new lines
                text = re.sub('\n', ' ', text)
                # Remove Google Ads
                text = re.sub(r'<script.+?script>', '', text,
                              re.IGNORECASE | re.DOTALL | re.MULTILINE |
                              re.UNICODE)
                # Remove HTML tags
                text = re.sub(r'<[^<]+?>', '', text)
                # If our actual video file's name appears in the description
                # then set sync to True because it has better chances of its
                # synchronization to match
                _, fn = os.path.split(file_original_path)
                name, _ = os.path.splitext(fn)
                sync = re.search(re.escape(name), text, re.I) is not None
                try:
                    log(u"Subtitles found: %s (id = %s)" % (text, id))
                except Exception:
                    pass
                item = {
                    'rating': str(rating),
                    'filename': text.decode(PAGE_ENCODING),
                    'sync': sync,
                    'id': id.decode(PAGE_ENCODING),
                    'language_name': languagelong,
                    'uploader': match.groupdict()['uploader'],
                }
                subs_list.append(item)
            page += 1

        # Put subs with sync=True at the top
        subs_list = sorted(subs_list, key=lambda s: s['sync'], reverse=True)

    log(u"get_all_subs(): Returning %s" % pformat(subs_list))
    return subs_list


def append_subtitle(item):
    if __addon__.getSetting('show_nick_in_place_of_lang') == 'true':
        item_label = item['uploader']
    else:
        item_label = item['language_name']
    listitem = xbmcgui.ListItem(
        label=item_label,
        label2=item['filename'],
        iconImage=item['rating'],
        thumbnailImage='es'
    )

    listitem.setProperty("sync", 'true' if item["sync"] else 'false')
    listitem.setProperty("hearing_imp",
                         'true' if item.get("hearing_imp", False) else 'false')

    # Below arguments are optional, it can be used to pass any info needed in
    # download function anything after "action=download&" will be sent to addon
    # once user clicks listed subtitle to download
    args = dict(item)
    args['scriptid'] = __scriptid__
    url = INTERNAL_LINK_URL % args

    # Add it to list, this can be done as many times as needed for all
    # subtitles found
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),
                                url=url,
                                listitem=listitem,
                                isFolder=False)


def Search(item):
    """Called when subtitle download is requested from XBMC."""
    log(u'Search(): item = %s' % pformat(item))
    # Do what's needed to get the list of subtitles from service site
    # use item["some_property"] that was set earlier.
    # Once done, set xbmcgui.ListItem() below and pass it to
    # xbmcplugin.addDirectoryItem()
    file_original_path = item['file_original_path']
    title = item['title']
    tvshow = item['tvshow']
    season = item['season']
    episode = item['episode']

    if tvshow:
        searchstring = "%s S%#02dE%#02d" % (tvshow, int(season), int(episode))
    else:
        searchstring = title
    log(u"Search string = %s" % searchstring)

    subs_list = get_all_subs(searchstring, "es", "Spanish", file_original_path)

    for sub in subs_list:
        append_subtitle(sub)


def _wait_for_extract(base_filecount, base_mtime, limit):
    waittime = 0
    filecount = base_filecount
    newest_mtime = base_mtime
    while (filecount == base_filecount and waittime < limit and
           newest_mtime == base_mtime):
        # wait 1 second to let the builtin function 'XBMC.Extract' unpack
        time.sleep(1)
        files = os.listdir(__temp__)
        filecount = len(files)
        # Determine if there is a newer file created (marks that the extraction
        # has completed)
        for fname in files:
            if not is_subs_file(fname):
                continue
            fname = fname.decode('utf-8')
            mtime = os.stat(pjoin(__temp__, fname)).st_mtime
            if mtime > newest_mtime:
                newest_mtime = mtime
        waittime += 1
    return waittime != limit


def _empty_dir(dirname, compressed_file):
    for fname in os.listdir(dirname):
        fpath = pjoin(dirname, fname)
        try:
            if os.path.isfile(fpath) and fpath != compressed_file:
                os.unlink(fpath)
        except Exception as e:
            log(u"Error removing file %s: %s" % (fname, e))


def _handle_compressed_subs(compressed_file, type):
    MAX_UNZIP_WAIT = 15
    if type == '.rar':
        _empty_dir(__temp__, compressed_file)
    files = os.listdir(__temp__)
    filecount = len(files)
    max_mtime = 0
    subs_before = []
    # Determine the newest file
    for fname in files:
        if not is_subs_file(fname):
            continue
        subs_before.append(fname)
        mtime = os.stat(pjoin(__temp__, fname)).st_mtime
        if mtime > max_mtime:
            max_mtime = mtime
    subs_before = set(subs_before)
    base_mtime = max_mtime
    # Wait 2 seconds so that the unpacked files are at least 1 second newer
    time.sleep(2)
    xbmc.executebuiltin("XBMC.Extract(%s, %s)" % (
                        compressed_file.encode("utf-8"),
                        __temp__.encode("utf-8")))
    retval, fpath = False, None
    x = _wait_for_extract(filecount, base_mtime, MAX_UNZIP_WAIT)
    files = os.listdir(__temp__)
    subs_after = []
    for fname in files:
        # There could be more subtitle files in __temp__, so make
        # sure we get the newly created subtitle file
        if not is_subs_file(fname):
            continue
        fpath = pjoin(__temp__, fname.decode("utf-8"))
        subs_after.append(fname)
        if os.stat(fpath).st_mtime > base_mtime and x:
            # unpacked file is a newly created subtitle file
            retval = True
    subs_after = set(subs_after)
    # rar unpacking can extract files preserving their mtime so the above
    # detection fails, fallback to detect dir contents changes
    if type == '.rar' and not retval:
        log(u"Falling back to RAR file strategy")
        new_files = subs_after - subs_before
        if new_files:
            fpath = pjoin(__temp__, new_files.pop().decode("utf-8"))
            log(u"Choosing first new file detected: %s" % fpath)
            retval = True
        else:
            log(u"No new file(s) detected")

    if retval:
        log(u"Unpacked subtitles file '%s'" % fpath)
    else:
        log(u"Failed to unpack subtitles")
    return retval, fpath


def _save_subtitles(content):
    header = content[:4]
    if header == 'Rar!':
        type = '.rar'
        is_compressed = True
    elif header == 'PK\x03\x04':
        type = '.zip'
        is_compressed = True
    else:
        # Never found/downloaded an unpacked subtitles file, but just to be
        # sure ...
        # Assume unpacked sub file is a '.srt'
        type = '.srt'
        is_compressed = False
    tmp_fname = pjoin(__temp__, "subdivx" + type)
    log(u"Saving subtitles to '%s'" % tmp_fname)
    try:
        with open(tmp_fname, "wb") as fh:
            fh.write(content)
    except Exception:
        log(u"Failed to save subtitles to '%s'" % tmp_fname)
        return None
    else:
        if is_compressed:
            rval, fname = _handle_compressed_subs(tmp_fname, type)
            if rval:
                return fname
        else:
            return tmp_fname


def Download(id, filename):
    """Called when subtitle download is requested from XBMC."""
    # Cleanup temp dir, we recommend you download/unzip your subs in temp
    # folder and pass that to XBMC to copy and activate
    if xbmcvfs.exists(__temp__):
        shutil.rmtree(__temp__)
    xbmcvfs.mkdirs(__temp__)

    subtitles_list = []
    # Get the page with the subtitle link,
    # i.e. http://www.subdivx.com/X6XMjE2NDM1X-iron-man-2-2010
    subtitle_detail_url = MAIN_SUBDIVX_URL + str(id)
    html_content = get_url(subtitle_detail_url)
    match = DOWNLOAD_LINK_RE.findall(html_content)

    actual_subtitle_file_url = MAIN_SUBDIVX_URL + "bajar.php?id=" + match[0][0] + "&u=" + match[0][1]
    content = get_url(actual_subtitle_file_url)
    if content is not None:
        saved_fname = _save_subtitles(content)
        if saved_fname:
            subtitles_list.append(saved_fname)
    return subtitles_list


def normalize_string(str):
    return unicodedata.normalize('NFKD', unicode(unicode(str, 'utf-8'))).encode('ascii', 'ignore')


def get_params(argv):
    params = {}
    qs = argv[2].lstrip('?')
    if qs:
        if qs.endswith('/'):
            qs = qs[:-1]
        parsed = parse_qs(qs)
        for k, v in parsed.iteritems():
            params[k] = v[0]
    return params


def main():
    """Main entry point of the script when it is invoked by XBMC."""

    # Get parameters from XBMC and launch actions
    params = get_params(sys.argv)

    if params['action'] == 'search':
        item = {}
        item['temp']               = False
        item['rar']                = False
        item['year']               = xbmc.getInfoLabel("VideoPlayer.Year")
        item['season']             = str(xbmc.getInfoLabel("VideoPlayer.Season"))
        item['episode']            = str(xbmc.getInfoLabel("VideoPlayer.Episode"))
        item['tvshow']             = normalize_string(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))
        # Try to get original title
        item['title']              = normalize_string(xbmc.getInfoLabel("VideoPlayer.OriginalTitle"))
        # Full path of a playing file
        item['file_original_path'] = urllib.unquote(xbmc.Player().getPlayingFile().decode('utf-8'))
        item['3let_language']      = []
        item['2let_language']      = []

        for lang in urllib.unquote(params['languages']).decode('utf-8').split(","):
            item['3let_language'].append(xbmc.convertLanguage(lang, xbmc.ISO_639_2))
            item['2let_language'].append(xbmc.convertLanguage(lang, xbmc.ISO_639_1))

        if not item['title']:
            # No original title, get just Title
            item['title'] = normalize_string(xbmc.getInfoLabel("VideoPlayer.Title"))

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
        # We pickup all our arguments sent from the Search() function
        subs = Download(params["id"], params["filename"])
        # We can return more than one subtitle for multi CD versions, for now
        # we are still working out how to handle that in XBMC core
        for sub in subs:
            listitem = xbmcgui.ListItem(label=sub)
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=sub,
                                        listitem=listitem, isFolder=False)

    # Send end of directory to XBMC
    xbmcplugin.endOfDirectory(int(sys.argv[1]))


if __name__ == '__main__':
    main()
