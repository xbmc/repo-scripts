# -*- coding: utf-8 -*-
# Subdivx.com subtitles, based on a mod of Undertext subtitles
# Adaptation: enric_godes@hotmail.com | Please use email address for your
# comments
# Port to XBMC 13 Gotham subtitles infrastructure: cramm, Mar 2014

from __future__ import print_function
from json import loads
import os
from os.path import join as pjoin
import os.path
from pprint import pformat
import re
import shutil
import sys
import tempfile
import time
from unicodedata import normalize
from urllib import FancyURLopener, unquote, quote_plus, urlencode, quote
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
    from xbmc import (LOGDEBUG, LOGINFO, LOGNOTICE, LOGWARNING, LOGERROR,
                      LOGSEVERE, LOGFATAL, LOGNONE)
    import xbmcaddon
    import xbmcgui
    import xbmcplugin
    import xbmcvfs

import html2text


__addon__ = xbmcaddon.Addon()
__author__     = __addon__.getAddonInfo('author')
__scriptid__   = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__    = '0.3.0'
__language__   = __addon__.getLocalizedString

__cwd__        = xbmc.translatePath(__addon__.getAddonInfo('path')).decode("utf-8")
__profile__    = xbmc.translatePath(__addon__.getAddonInfo('profile')).decode("utf-8")


MAIN_SUBDIVX_URL = "http://www.subdivx.com/"
SEARCH_PAGE_URL = MAIN_SUBDIVX_URL + \
    "index.php?accion=5&masdesc=&oxdown=1&pg=%(page)s&buscar=%(query)s"

INTERNAL_LINK_URL_BASE = "plugin://%s/?"
SUB_EXTS = ['SRT', 'SUB', 'SSA']
HTTP_USER_AGENT = "User-Agent=Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.2.3) Gecko/20100401 Firefox/3.6.3 ( .NET CLR 3.5.30729)"
FORCED_SUB_SENTINELS = ['FORZADO', 'FORCED']

PAGE_ENCODING = 'latin1'


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
                         href="http://www.subdivx.com/(?P<subdivx_id>.+?)\.html">
                         .+?<img\s+src="img/calif(?P<calif>\d)\.gif"\s+class="detalle_calif"\s+name="detalle_calif">
                         .+?<div\s+id="buscador_detalle_sub">(?P<comment>.*?)</div>
                         .+?<b>Downloads:</b>(?P<downloads>.+?)
                         <b>Cds:</b>
                         .+?<b>Subido\ por:</b>\s*<a.+?>(?P<uploader>.+?)</a>.+?</div></div>''',
                         re.IGNORECASE | re.DOTALL | re.VERBOSE | re.UNICODE |
                         re.MULTILINE)
# Named groups:
# 'subdivx_id': ID to fetch the subs files
# 'comment': Translation author comment, may contain filename
# 'downloads': Downloads, used for ratings

DETAIL_PAGE_LINK_RE = re.compile(r'<a rel="nofollow" class="detalle_link" href="http://www.subdivx.com/(?P<id>.*?)"><b>Bajar</b></a>',
                                 re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE)

DOWNLOAD_LINK_RE = re.compile(r'bajar.php\?id=(?P<id>.*?)&u=(?P<u>[^"\']+?)', re.IGNORECASE |
                              re.DOTALL | re.MULTILINE | re.UNICODE)

# ==========
# Functions
# ==========


def is_subs_file(fn):
    """Detect if the file has an extension we recognise as subtitle."""
    ext = fn.split('.')[-1]
    return ext.upper() in SUB_EXTS


def is_forced_subs_file(fn):
    """Detect if the file has some text in its filename we recognise as forced
    subtitle."""
    target = '.'.join(fn.split('.')[:-1]) if '.' in fn else fn
    return any(s in target.upper() for s in FORCED_SUB_SENTINELS)


def is_compressed_file(fname=None, contents=None):
    if contents is None:
        assert fname is not None
        contents = open(fname, 'rb').read()
    assert len(contents) > 4
    header = contents[:4]
    if header == 'Rar!':
        compression_type = 'RAR'
    elif header == 'PK\x03\x04':
        compression_type = 'ZIP'
    else:
        compression_type = None
    return compression_type


def log(msg, level=LOGDEBUG):
    fname = sys._getframe(1).f_code.co_name
    s = u"SUBDIVX - %s: %s" % (fname, msg)
    xbmc.log(s.encode('utf-8'), level=level)


def get_url(url):
    class MyOpener(FancyURLopener):
        # version = HTTP_USER_AGENT
        version = ''
    my_urlopener = MyOpener()
    log(u"Fetching %s" % url)
    try:
        response = my_urlopener.open(url)
        content = response.read()
    except Exception:
        log(u"Failed to fetch %s" % url, level=LOGWARNING)
        content = None
    return content


def cleanup_subdivx_comment(comment):
    """Convert the subtitle comment HTML to plain text."""
    parser = html2text.HTML2Text()
    parser.unicode_snob = True
    parser.ignore_emphasis = True
    parser.ignore_tables = True
    parser.ignore_links = True
    parser.body_width = 1000
    clean_text = parser.handle(comment)
    # Remove new lines manually
    clean_text = re.sub('\n', ' ', clean_text)
    return clean_text.rstrip(' \t')


def get_all_subs(searchstring, languageshort, file_orig_path):
    if languageshort != "es":
        return []
    subs_list = []
    page = 1
    while True:
        log(u"Trying page %d" % page)
        url = SEARCH_PAGE_URL % {'page': page,
                                 'query': quote_plus(searchstring)}
        content = get_url(url)
        if content is None or not SUBTITLE_RE.search(content):
            break
        for counter, match in enumerate(SUBTITLE_RE.finditer(content)):
            groups = match.groupdict()

            subdivx_id = groups['subdivx_id']

            dls = re.sub(r'[,.]', '', groups['downloads'])
            downloads = int(dls)

            descr = cleanup_subdivx_comment(groups['comment'].decode(PAGE_ENCODING))

            # If our actual video file's name appears in the description
            # then set sync to True because it has better chances of its
            # synchronization to match
            _, fn = os.path.split(file_orig_path)
            name, _ = os.path.splitext(fn)
            sync = re.search(re.escape(name), descr, re.I) is not None

            try:
                if not counter:
                    log(u'Subtitles found for subdivx_id = %s:' % subdivx_id)
                log(u'"%s"' % descr)
            except Exception:
                pass
            item = {
                'descr': descr,
                'sync': sync,
                'subdivx_id': subdivx_id.decode(PAGE_ENCODING),
                'uploader': groups['uploader'],
                'downloads': downloads,
                'score': int(groups['calif']),
            }
            subs_list.append(item)
        page += 1

    # Put subs with sync=True at the top
    subs_list = sorted(subs_list, key=lambda s: s['sync'], reverse=True)
    return subs_list


def compute_ratings(subs_list):
    """
    Calculate the rating figures (from zero to five) in a relative fashion
    based on number of downloads.

    This is later converted by XBMC/Kodi in a zero to five stars GUI.

    Ideally, we should be able to use a smarter number instead of just the
    download count of every subtitle but it seems in Subdivx the 'score' value
    has no reliable value and there isn't a user ranking system in place
    we could use to deduce the quality of a contribution.
    """
    max_dl_count = 0
    for sub in subs_list:
        dl_cnt = sub.get('downloads', 0)
        if dl_cnt > max_dl_count:
            max_dl_count = dl_cnt
    for sub in subs_list:
        if max_dl_count:
            sub['rating'] = int((sub['downloads'] / float(max_dl_count)) * 5)
        else:
            sub['rating'] = 0
    log(u"subs_list = %s" % pformat(subs_list))


def append_subtitle(item, filename):
    if __addon__.getSetting('show_nick_in_place_of_lang') == 'true':
        item_label = item['uploader']
    else:
        item_label = 'Spanish'
    listitem = xbmcgui.ListItem(
        label=item_label,
        label2=item['descr'],
        iconImage=str(item['rating']),
        thumbnailImage=''
    )
    listitem.setProperty("sync", 'true' if item["sync"] else 'false')
    listitem.setProperty("hearing_imp",
                         'true' if item.get("hearing_imp", False) else 'false')

    # Below arguments are optional, they can be used to pass any info needed in
    # download function. Anything after "action=download&" will be sent to
    # addon once user clicks listed subtitle to download
    url = INTERNAL_LINK_URL_BASE % __scriptid__
    xbmc_url = build_xbmc_item_url(url, item, filename)
    # Add it to list, this can be done as many times as needed for all
    # subtitles found
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),
                                url=xbmc_url,
                                listitem=listitem,
                                isFolder=False)


def build_xbmc_item_url(url, item, filename):
    """Return an internal Kodi pseudo-url for the provided sub search result"""
    try:
        xbmc_url = url + urlencode((('id', item['subdivx_id']),
                                    ('filename', filename.encode('utf-8'))))
    except UnicodeEncodeError:
        # Well, go back to trying it with its original latin1 encoding
        try:
            subdivx_id = item['subdivx_id'].encode(PAGE_ENCODING)
            xbmc_url = url + urlencode((('id', subdivx_id),
                                        ('filename', filename.encode('utf-8'))))
        except Exception:
            log('Problematic subdivx_id: %s' % subdivx_id)
            raise
    return xbmc_url


def build_tvshow_searchstring(item):
    parts = ['%s' % item['tvshow']]
    try:
        season = int(item['season'])
    except:
        pass
    else:
        parts.append(' S%#02d' % season)
        try:
            episode = int(item['episode'])
        except:
            pass
        else:
            parts.append('E%#02d' % episode)
    return ''.join(parts)


def Search(item):
    """Called when subtitle download is requested from XBMC."""
    log(u'item = %s' % pformat(item))
    # Do what's needed to get the list of subtitles from service site
    # use item["some_property"] that was set earlier.
    # Once done, set xbmcgui.ListItem() below and pass it to
    # xbmcplugin.addDirectoryItem()
    file_original_path = item['file_original_path']

    if item['manual_search']:
        searchstring = unquote(item['manual_search_string'])
    elif item['tvshow']:
        searchstring = build_tvshow_searchstring(item)
    else:
        searchstring = '%s%s' % (item['title'], ' (%s)' % item['year'].strip('()') if item.get('year') else '')
    log(u"Search string = %s" % searchstring)

    subs_list = get_all_subs(searchstring, "es", file_original_path)

    compute_ratings(subs_list)

    for sub in subs_list:
        append_subtitle(sub, file_original_path)


def _handle_compressed_subs(workdir, compressed_file, ext):
    """
    Uncompress 'compressed_file' in 'workdir'.
    """
    kodi_major_version = int(xbmc.getInfoLabel('System.BuildVersion').split('.')[0])
    if ext == 'rar' and kodi_major_version >= 18:
        src = 'archive' + '://' + quote_plus(compressed_file) + '/'
        (cdirs, cfiles) = xbmcvfs.listdir(src)
        for cfile in cfiles:
            fsrc = '%s%s' % (src, cfile)
            xbmcvfs.copy(fsrc, workdir + cfile)
    else:
        xbmc.executebuiltin("XBMC.Extract(%s, %s)" % (
                            compressed_file.encode("utf-8"),
                            workdir.encode("utf-8")), True)

    files = os.listdir(workdir)
    files = [f for f in files if is_subs_file(f)]
    found_files = []
    for fname in files:
        if not isinstance(fname, unicode):
            fname = fname.decode('utf-8')
        found_files.append({
            'forced': is_forced_subs_file(fname),
            'path': pjoin(workdir, fname)
        })
    if not found_files:
        log(u"Failed to unpack subtitles", level=LOGSEVERE)
    return found_files


def _save_subtitles(workdir, content):
    """
    Save dowloaded file whose content is in 'content' to a temporary file
    If it's a compressed one then uncompress it.

    Returns filename of saved file or None.
    """
    ctype = is_compressed_file(contents=content)
    is_compressed = ctype is not None
    # Never found/downloaded an unpacked subtitles file, but just to be sure ...
    # Assume unpacked sub file is a '.srt'
    cfext = {'RAR': 'rar', 'ZIP': 'zip'}.get(ctype, 'srt')
    tmp_fname = pjoin(workdir, "subdivx." + cfext)
    log(u"Saving subtitles to '%s'" % tmp_fname)
    try:
        with open(tmp_fname, "wb") as fh:
            fh.write(content)
    except Exception:
        log(u"Failed to save subtitles to '%s'" % tmp_fname, level=LOGSEVERE)
        return []
    else:
        if is_compressed:
            return _handle_compressed_subs(workdir, tmp_fname, cfext)
        return [{'path': tmp_fname, 'forced': False}]


def Download(subdivx_id, workdir):
    """Called when subtitle download is requested from XBMC."""
    # Get the page with the subtitle link,
    # i.e. http://www.subdivx.com/X6XMjE2NDM1X-iron-man-2-2010
    subtitle_detail_url = MAIN_SUBDIVX_URL + quote(subdivx_id)
    # Fetch and scrape [new] intermediate page
    html_content = get_url(subtitle_detail_url)
    if html_content is None:
        log(u"No content found in selected subtitle intermediate detail/final download page",
            level=LOGFATAL)
        return []
    match = DETAIL_PAGE_LINK_RE.search(html_content)
    if match is None:
        log(u"Intermediate detail page for selected subtitle or expected content not found. Handling it as final download page")
    else:
        id_ = match.group('id')
        # Fetch and scrape final page
        html_content = get_url(MAIN_SUBDIVX_URL + id_)
    if html_content is None:
        log(u"No content found in final download page", level=LOGFATAL)
        return []
    match = DOWNLOAD_LINK_RE.search(html_content)
    if match is None:
        log(u"Expected content not found in final download page")
        return []
    id_, u = match.group('id', 'u')
    actual_subtitle_file_url = MAIN_SUBDIVX_URL + "bajar.php?id=" + id_ + "&u=" + u
    content = get_url(actual_subtitle_file_url)
    if content is None:
        log(u"Got no content when downloading actual subtitle file",
            level=LOGFATAL)
        return []
    saved_fnames = _save_subtitles(workdir, content)
    return saved_fnames


def _double_dot_fix_hack(video_filename):
    """Corrects filename of downloaded subtitle from Foo-Blah..srt to Foo-Blah.es.srt"""

    log(u"video_filename = %s" % video_filename)

    work_path = video_filename
    if _subtitles_setting('storagemode'):
        custom_subs_path = _subtitles_setting('custompath')
        if custom_subs_path:
            _, fname = os.path.split(video_filename)
            work_path = pjoin(custom_subs_path, fname)

    log(u"work_path = %s" % work_path)
    parts = work_path.rsplit('.', 1)
    if len(parts) > 1:
        rest = parts[0]
        for ext in ('srt', 'ssa', 'sub', 'idx'):
            bad = rest + '..' + ext
            old = rest + '.es.' + ext
            if xbmcvfs.exists(bad):
                log(u"%s exists" % bad)
                if xbmcvfs.exists(old):
                    log(u"%s exists, removing" % old)
                    xbmcvfs.delete(old)
                log(u"renaming %s to %s" % (bad, old))
                xbmcvfs.rename(bad, old)


def _subtitles_setting(name):
    """
    Uses XBMC/Kodi JSON-RPC API to retrieve subtitles location settings values.
    """
    command = '''{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "Settings.GetSettingValue",
    "params": {
        "setting": "subtitles.%s"
    }
}'''
    result = xbmc.executeJSONRPC(command % name)
    py = loads(result)
    if 'result' in py and 'value' in py['result']:
        return py['result']['value']
    else:
        raise ValueError


def normalize_string(str):
    return normalize('NFKD', unicode(unicode(str, 'utf-8'))).encode('ascii',
                                                                    'ignore')


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


def debug_dump_path(victim, name):
    t = type(victim)
    xbmc.log("SUBDIVX - %s (%s): %s" % (name, t, victim), level=LOGDEBUG)


def _cleanup_tempdir(dir_path):
    try:
        shutil.rmtree(dir_path, ignore_errors=True)
    except Exception:
        log(u"Failed to remove %s" % dir_path, level=LOGWARNING)


def _cleanup_tempdirs(profile_path):
    dirs, _ = xbmcvfs.listdir(profile_path)
    for dir_path in dirs[:10]:
        _cleanup_tempdir(os.path.join(profile_path, dir_path))


def main():
    """Main entry point of the script when it is invoked by XBMC."""
    # Get parameters from XBMC and launch actions
    params = get_params(sys.argv)
    action = params.get('action', 'Unknown')
    xbmc.log(u"SUBDIVX - Version: %s -- Action: %s" % (__version__, action), level=LOGNOTICE)

    if action in ('search', 'manualsearch'):
        item = {
            'temp': False,
            'rar': False,
            'year': xbmc.getInfoLabel("VideoPlayer.Year"),
            'season': str(xbmc.getInfoLabel("VideoPlayer.Season")),
            'episode': str(xbmc.getInfoLabel("VideoPlayer.Episode")),
            'tvshow': normalize_string(xbmc.getInfoLabel("VideoPlayer.TVshowtitle")),
            # Try to get original title
            'title': normalize_string(xbmc.getInfoLabel("VideoPlayer.OriginalTitle")),
            # Full path of a playing file
            'file_original_path': unquote(xbmc.Player().getPlayingFile().decode('utf-8')),
            '3let_language': [],
            '2let_language': [],
            'manual_search': 'searchstring' in params,
        }

        if 'searchstring' in params:
            item['manual_search_string'] = params['searchstring']

        for lang in unquote(params['languages']).decode('utf-8').split(","):
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
        # Send end of directory to XBMC
        xbmcplugin.endOfDirectory(int(sys.argv[1]))

    elif action == 'download':
        debug_dump_path(xbmc.translatePath(__addon__.getAddonInfo('profile')),
                        "xbmc.translatePath(__addon__.getAddonInfo('profile'))")
        debug_dump_path(__profile__, '__profile__')
        xbmcvfs.mkdirs(__profile__)
        _cleanup_tempdirs(__profile__)
        workdir = tempfile.mkdtemp(dir=__profile__)
        # Make sure it ends with a path separator (Kodi 14)
        workdir = workdir + os.path.sep
        debug_dump_path(workdir, 'workdir')
        # We pickup our arguments sent from the Search() function
        subs = Download(params["id"], workdir)
        # We can return more than one subtitle for multi CD versions, for now
        # we are still working out how to handle that in XBMC core
        for sub in subs:
            # XXX: Kodi still can't handle multiple subtitles files returned
            # from an addon, it will always use the first file returned. So
            # there is no point in reporting a forced subtitle file to it.
            # See https://github.com/ramiro/service.subtitles.subdivx/issues/14
            if sub['forced']:
                continue
            listitem = xbmcgui.ListItem(label=sub['path'])
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=sub['path'],
                                        listitem=listitem, isFolder=False)
        # Send end of directory to XBMC
        xbmcplugin.endOfDirectory(int(sys.argv[1]))

        _cleanup_tempdir(workdir)
        if __addon__.getSetting('show_nick_in_place_of_lang') == 'true':
            time.sleep(2)
            _double_dot_fix_hack(params['filename'].encode('utf-8'))


if __name__ == '__main__':
    main()
