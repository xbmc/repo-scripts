# -*- coding: utf-8 -*-
# Subdivx.com subtitles, based on a mod of Undertext subtitles
# Adaptation: enric_godes@hotmail.com | Please use email address for your
# comments
# Port to XBMC 13 Gotham subtitles infrastructure: cramm, Mar 2014
# Port to Kodi 19 Matrix/Python 3: pedrochiuaua, cramm, 2021-2022


import os
import os.path
import re
import shutil
from json import loads
from os.path import join as pjoin
from pprint import pformat

try:
    import StorageServer
except Exception:
    import storageserverdummy as StorageServer

import sys
import tempfile
import urllib.error
import urllib.request
from unicodedata import normalize
from urllib.parse import parse_qs, quote, quote_plus, unquote, urlencode

try:
    import xbmc
except ImportError:
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        import unittest  # NOQA

        try:
            import mock  # NOQA
        except ImportError:
            print("You need to install the mock Python library to run unit tests.\n")
            sys.exit(1)
else:
    from xbmc import (  # noqa: F401
        LOGDEBUG,
        LOGINFO,
        LOGWARNING,
        LOGERROR,
        LOGFATAL,
        LOGNONE,
    )
    import xbmcaddon
    import xbmcgui
    import xbmcplugin
    import xbmcvfs

import html2text

__addon__ = xbmcaddon.Addon()
__author__ = __addon__.getAddonInfo("author")
__scriptid__ = __addon__.getAddonInfo("id")
__scriptname__ = __addon__.getAddonInfo("name")
__version__ = "0.4.0"
__language__ = __addon__.getLocalizedString

__cwd__ = xbmcvfs.translatePath(__addon__.getAddonInfo("path"))
__profile__ = xbmcvfs.translatePath(__addon__.getAddonInfo("profile"))


MAIN_SUBDIVX_URL = "https://www.subdivx.com/"
SEARCH_PAGE_URL = MAIN_SUBDIVX_URL + "index.php"
QS_DICT = {
    "accion": "5",
    "masdesc": "",
    "oxdown": "1",
}
QS_KEY_QUERY = "buscar2"
QS_KEY_PAGE = "pg"
MAX_RESULTS_COUNT = 40

INTERNAL_LINK_URL_BASE = "plugin://%s/?"
SUB_EXTS = ["SRT", "SUB", "SSA"]
HTTP_USER_AGENT = (
    "User-Agent=Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/53.0.2785.21 Safari/537.36"
)
FORCED_SUB_SENTINELS = ["FORZADO", "FORCED"]

PAGE_ENCODING = "utf-8"

kodi_major_version = None


# ============================
# Regular expression patterns
# ============================

SUBTITLE_RE = re.compile(
    r"""<a\s+class="titulo_menu_izq2?"\s+
    href="https://www.subdivx.com/(?P<subdivx_id>.+?)\.html">
    .+?<img\s+src="img/calif(?P<calif>\d)\.gif"\s+class="detalle_calif"\s+name="detalle_calif">
    .+?<div\s+id="buscador_detalle_sub">(?P<comment>.*?)</div>
    .+?<b>Downloads:</b>(?P<downloads>.+?)
    <b>Cds:</b>
    .+?<b>Comentarios:</b>
    .+?<b>Subido\ por:</b>\s*<a.+?>(?P<uploader>.+?)</a>.+?</div></div>""",
    re.IGNORECASE | re.DOTALL | re.VERBOSE | re.UNICODE | re.MULTILINE,
)
# Named groups:
# 'subdivx_id': ID to fetch the subs files
# 'comment': Translation author comment, may contain filename
# 'downloads': Downloads, used for ratings
# 'uploader': Subdivx community member uploader nick

DETAIL_PAGE_LINK_RE = re.compile(
    r'<a rel="nofollow" class="detalle_link" href="http://www.subdivx.com/(?P<id>.*?)"><b>Bajar</b></a>',
    re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE,
)

DOWNLOAD_LINK_RE = re.compile(
    r'bajar.php\?id=(?P<id>.*?)&u=(?P<u>[^"\']+?)',
    re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE,
)


# ==========
# Functions
# ==========
def is_subs_file(fn):
    """Detect if the file has an extension we recognise as subtitle."""
    ext = fn.split(".")[-1]
    return ext.upper() in SUB_EXTS


def is_forced_subs_file(fn):
    """Detect if the file has some text in its filename we recognise as forced
    subtitle."""
    target = ".".join(fn.split(".")[:-1]) if "." in fn else fn
    return any(s in target.upper() for s in FORCED_SUB_SENTINELS)


def is_compressed_file(fname=None, contents=None):
    if contents is None:
        assert fname is not None
        contents = open(fname, "rb").read()
    assert len(contents) > 4
    header = contents[:4]
    if header == b"Rar!":
        compression_type = "RAR"
    elif header == b"PK\x03\x04":
        compression_type = "ZIP"
    else:
        compression_type = None
    return compression_type


def log(msg, level=LOGDEBUG):
    fname = sys._getframe(1).f_code.co_name
    s = "SUBDIVX - %s: %s" % (fname, msg)
    xbmc.log(s, level=level)


def get_url(url, query_data=None):
    if query_data is None:
        req = urllib.request.Request(url)
        log("Fetching %s" % url)
    else:
        urlencoded_query_data = urlencode(query_data)
        req = urllib.request.Request(
            url, data=urlencoded_query_data.encode(PAGE_ENCODING)
        )
        log("Fetching %s POST data: %s" % (url, urlencoded_query_data))
    req.add_header("User-Agent", HTTP_USER_AGENT)
    try:
        response = urllib.request.urlopen(req)
        content = response.read()
    except urllib.error.HTTPError as e:
        log("Failed to fetch %s (HTTP status: %d)" % (url, e.code), level=LOGWARNING)
    except urllib.error.URLError as e:
        log("Failed to fetch %s (URL error %s)" % (url, e.reason), level=LOGWARNING)
    except Exception as e:
        log("Failed to fetch %s (generic error %s)" % (url, e), level=LOGWARNING)
    else:
        return content
    return None


def get_html_url(url, query_data=None):
    content = get_url(url, query_data=query_data)
    if content is None:
        return None
    # TODO: At some point subdivx.com started to declare UTF-8 encoding in the
    # Content-Type HTTP response header but meta HTML tag states latin1 and
    # actual encoding of HTML page contents seems to be inconsistent.
    # We might want to look at# BeatifulSoup UnicodeDammit detwingle (already
    # packed as a Kodi addon or python-ftfy for a more robust solution with
    # less risk of generating mojibake or dropping too much content
    return content.decode(PAGE_ENCODING, "ignore")


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
    clean_text = re.sub("\n", " ", clean_text)
    return clean_text.rstrip(" \t")


def process_page(page_nr, srch_str, file_orig_path):
    log("Trying page %d" % page_nr)
    qs_dict = QS_DICT.copy()
    qs_dict[QS_KEY_QUERY] = srch_str
    if page_nr > 1:
        qs_dict[QS_KEY_PAGE] = str(page_nr)
    content = get_html_url(SEARCH_PAGE_URL, qs_dict)
    if content is None:
        return [], set()
    if not SUBTITLE_RE.search(content):
        return [], set()
    subs = []
    descriptions = []
    for counter, match in enumerate(SUBTITLE_RE.finditer(content)):
        groups = match.groupdict()

        subdivx_id = groups["subdivx_id"]

        dls = re.sub(r"[,.]", "", groups["downloads"])
        downloads = int(dls)

        raw_desc = groups["comment"]
        descriptions.append(raw_desc)
        descr = cleanup_subdivx_comment(raw_desc)

        # If our actual video file's name appears in the description
        # then set sync to True because it has better chances of its
        # synchronization to match
        _, fn = os.path.split(file_orig_path)
        name, _ = os.path.splitext(fn)
        sync = re.search(re.escape(name), descr, re.I) is not None

        try:
            if not counter:
                log("Subtitles found for subdivx_id = %s:" % subdivx_id)
            log('"%s"' % descr)
        except Exception:
            pass
        item = {
            "descr": descr,
            "sync": sync,
            "subdivx_id": subdivx_id,
            "uploader": groups["uploader"],
            "downloads": downloads,
            "score": int(groups["calif"]),
        }
        subs.append(item)

    return subs, set(descriptions)


def get_all_subs(searchstring, languageshort, file_orig_path):
    if languageshort != "es":
        return []
    subs_list = []
    page_nr = 1
    last_page = set()
    while True:
        page_results, current_page = process_page(page_nr, searchstring, file_orig_path)
        if not page_results:
            if page_nr == 1:
                log(
                    "No subtitle link regexp match found in page contents",
                    level=LOGFATAL,
                )
            break
        if current_page == last_page:
            break
        subs_list.extend(page_results)
        if len(subs_list) >= MAX_RESULTS_COUNT:
            break
        page_nr += 1
        last_page = current_page

    # Put subs with sync=True at the top
    subs_list = sorted(subs_list, key=lambda s: s["sync"], reverse=True)
    return subs_list


def compute_ratings(subs_list):
    """
    Calculate the rating figures (from zero to five) in a relative fashion
    based on number of downloads.

    This is later converted by Kodi into a zero to five stars GUI.

    Ideally, we should be able to use a smarter number instead of just the
    download count of every subtitle but it seems in Subdivx the 'score' value
    has no reliable value and there isn't a user ranking system in place
    we could use to deduce the quality of a contribution.
    """
    max_dl_count = 0
    for sub in subs_list:
        dl_cnt = sub.get("downloads", 0)
        if dl_cnt > max_dl_count:
            max_dl_count = dl_cnt
    for sub in subs_list:
        if max_dl_count:
            sub["rating"] = int((sub["downloads"] / float(max_dl_count)) * 5)
        else:
            sub["rating"] = 0
    log("subs_list = %s" % pformat(subs_list))


def append_subtitle(kodi_dir_handle, item, filename):
    if __addon__.getSetting("show_nick_in_place_of_lang") == "true":
        item_label = item["uploader"]
    else:
        item_label = "Spanish"
    if kodi_major_version >= 16:
        listitem = xbmcgui.ListItem(label=item_label, label2=item["descr"])
        listitem.setArt(
            {
                "icon": str(item["rating"]),
                "thumb": "",
            }
        )
    else:
        listitem = xbmcgui.ListItem(
            label=item_label,
            label2=item["descr"],
            iconImage=str(item["rating"]),
            thumbnailImage="",
        )
    listitem.setProperty("sync", "true" if item["sync"] else "false")
    listitem.setProperty(
        "hearing_imp", "true" if item.get("hearing_imp", False) else "false"
    )

    # Below arguments are optional, they can be used to pass any info needed in
    # download function. Anything after "action=download&" will be sent to
    # addon once user clicks listed subtitle to download
    url = INTERNAL_LINK_URL_BASE % __scriptid__
    xbmc_url = build_xbmc_item_url(url, item, filename)
    # Add it to list, this can be done as many times as needed for all
    # subtitles found
    xbmcplugin.addDirectoryItem(
        handle=kodi_dir_handle, url=xbmc_url, listitem=listitem, isFolder=False
    )


def build_xbmc_item_url(url, item, filename):
    """Return an internal Kodi pseudo-url for the provided sub search result"""
    try:
        xbmc_url = url + urlencode(
            (("id", item["subdivx_id"]), ("filename", filename.encode("utf-8")))
        )
    except UnicodeEncodeError:
        # Well, go back to trying it with its original latin1 encoding
        try:
            subdivx_id = item["subdivx_id"].encode(PAGE_ENCODING)
            xbmc_url = url + urlencode(
                (("id", subdivx_id), ("filename", filename.encode("utf-8")))
            )
        except Exception:
            log("Problematic subdivx_id: %s" % subdivx_id)
            raise
    return xbmc_url


def build_tvshow_searchstring(item):
    parts = ["%s" % item["tvshow"]]
    try:
        season = int(item["season"])
    except Exception:
        pass
    else:
        parts.append(" S%#02d" % season)
        try:
            episode = int(item["episode"])
        except Exception:
            pass
        else:
            parts.append("E%#02d" % episode)
    return "".join(parts)


def action_search(kodi_dir_handle, item):
    """Called when subtitle search is requested from Kodi."""
    log("item = %s" % pformat(item))
    # Do what's needed to get the list of subtitles from service site
    # use item["some_property"] that was set earlier.
    # Once done, set xbmcgui.ListItem() below and pass it to
    # xbmcplugin.addDirectoryItem()
    file_original_path = item["file_original_path"]

    if item["manual_search"]:
        searchstring = unquote(item["manual_search_string"])
    elif item["tvshow"]:
        searchstring = build_tvshow_searchstring(item)
    else:
        searchstring = "%s%s" % (
            item["title"],
            " (%s)" % item["year"].strip("()") if item.get("year") else "",
        )
    log("Search string = %s" % searchstring)

    cache_ttl_value = __addon__.getSetting("cache_ttl")
    try:
        cache_ttl = int(cache_ttl_value)
    except Exception:
        cache_ttl = 0
    if cache_ttl:
        cache = StorageServer.StorageServer(
            "service.subtitles.subdivx", cache_ttl / 60.0
        )
        subs_list = cache.cacheFunction(
            get_all_subs, searchstring, "es", file_original_path
        )
    else:
        subs_list = get_all_subs(searchstring, "es", file_original_path)

    compute_ratings(subs_list)

    for sub in subs_list:
        append_subtitle(kodi_dir_handle, sub, file_original_path)


def _handle_compressed_subs(workdir, compressed_file, ext):
    """
    Uncompress 'compressed_file' in 'workdir'.
    """
    if ext == "rar" and kodi_major_version >= 18:
        src = "archive" + "://" + quote_plus(compressed_file) + "/"
        (cdirs, cfiles) = xbmcvfs.listdir(src)
        for cfile in cfiles:
            fsrc = "%s%s" % (src, cfile)
            xbmcvfs.copy(fsrc, workdir + cfile)
    else:
        xbmc.executebuiltin("Extract(%s, %s)" % (compressed_file, workdir), True)

    files = os.listdir(workdir)
    files = [f for f in files if is_subs_file(f)]
    found_files = []
    for fname in files:
        found_files.append(
            {"forced": is_forced_subs_file(fname), "path": pjoin(workdir, fname)}
        )
    if not found_files:
        log("Failed to unpack subtitles", level=LOGFATAL)
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
    cfext = {"RAR": "rar", "ZIP": "zip"}.get(ctype, "srt")
    tmp_fname = pjoin(workdir, "subdivx." + cfext)
    log("Saving subtitles to '%s'" % tmp_fname)
    try:
        with open(tmp_fname, "wb") as fh:
            fh.write(content)
    except Exception:
        log("Failed to save subtitles to '%s'" % tmp_fname, level=LOGFATAL)
        return []
    else:
        if is_compressed:
            return _handle_compressed_subs(workdir, tmp_fname, cfext)
        return [{"path": tmp_fname, "forced": False}]


def method_traditional(sub_id, u):
    actual_subtitle_file_url = MAIN_SUBDIVX_URL + "bajar.php?id=" + sub_id + "&u=" + u
    return get_url(actual_subtitle_file_url)


def method_direct_download(sub_id, u):
    if u == "1":
        u = ""
    for ext in (".rar", ".zip"):
        actual_subtitle_file_url = MAIN_SUBDIVX_URL + "sub" + u + "/" + sub_id + ext
        content = get_url(actual_subtitle_file_url)
        if content is not None:
            break
    else:
        return None
    return content


def action_download(subdivx_id, workdir):
    """Called when subtitle download is requested from Kodi."""
    # Get the page with the subtitle link,
    # i.e. http://www.subdivx.com/X6XMjE2NDM1X-iron-man-2-2010
    subtitle_detail_url = MAIN_SUBDIVX_URL + quote(subdivx_id)
    # Fetch and scrape [new] intermediate page
    html_content = get_html_url(subtitle_detail_url)
    if html_content is None:
        log(
            "No content found in selected subtitle intermediate detail/final download page",
            level=LOGFATAL,
        )
        return []
    match = DETAIL_PAGE_LINK_RE.search(html_content)
    if match is None:
        log(
            "Intermediate detail page for selected subtitle or expected content not "
            "found. Handling it as final download page"
        )
    else:
        id_ = match.group("id")
        # Fetch and scrape final page
        html_content = get_html_url(MAIN_SUBDIVX_URL + id_)
    if html_content is None:
        log("No content found in final download page", level=LOGFATAL)
        return []
    match = DOWNLOAD_LINK_RE.search(html_content)
    if match is None:
        log("Expected content not found in final download page", level=LOGFATAL)
        return []
    id_, u = match.group("id", "u")
    methods = [
        method_direct_download,
        method_traditional,
    ]
    for method in methods:
        content = method(id_, u)
        if content is not None:
            saved_fnames = _save_subtitles(workdir, content)
            break
    else:
        log("Got no content when downloading actual subtitle file", level=LOGFATAL)
        return []
    return saved_fnames


def _double_dot_fix_hack(video_filename):
    """Corrects filename of downloaded subtitle from Foo-Blah..srt to Foo-Blah.es.srt"""

    log("video_filename = %s" % video_filename)

    work_path = video_filename
    if _subtitles_setting("storagemode"):
        custom_subs_path = _subtitles_setting("custompath")
        if custom_subs_path:
            _, fname = os.path.split(video_filename)
            work_path = pjoin(custom_subs_path, fname)

    log("work_path = %s" % work_path)
    parts = work_path.rsplit(".", 1)
    if len(parts) > 1:
        rest = parts[0]
        for ext in ("srt", "ssa", "sub", "idx"):
            bad = rest + ".." + ext
            old = rest + ".es." + ext
            if xbmcvfs.exists(bad):
                log("%s exists" % bad)
                if xbmcvfs.exists(old):
                    log("%s exists, removing" % old)
                    xbmcvfs.delete(old)
                log("renaming %s to %s" % (bad, old))
                xbmcvfs.rename(bad, old)


def _subtitles_setting(name):
    """
    Uses Kodi JSON-RPC API to retrieve subtitles location settings values.
    """
    command = """{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "Settings.GetSettingValue",
    "params": {
        "setting": "subtitles.%s"
    }
}"""
    result = xbmc.executeJSONRPC(command % name)
    py = loads(result)
    if "result" in py and "value" in py["result"]:
        return py["result"]["value"]
    else:
        raise ValueError


def get_params(argv):
    params = {}
    qs = argv[2].lstrip("?")
    if qs:
        if qs.endswith("/"):
            qs = qs[:-1]
        parsed = parse_qs(qs)
        for k, v in parsed.items():
            params[k] = v[0]
    return params


def debug_dump_path(victim, name):
    t = type(victim)
    xbmc.log("SUBDIVX - %s (%s): %s" % (name, t, victim))


def _cleanup_tempdir(dir_path, verbose=False):
    try:
        shutil.rmtree(dir_path, ignore_errors=True)
    except Exception:
        if verbose:
            log("Failed to remove %s" % dir_path, level=LOGWARNING)
        return False
    return True


def _cleanup_tempdirs(profile_path):
    dirs, _ = xbmcvfs.listdir(profile_path)
    total, ok = 0, 0
    for total, dir_path in enumerate(dirs[:10]):
        result = _cleanup_tempdir(os.path.join(profile_path, dir_path), verbose=False)
        if result:
            ok += 1
    log("Results: %d of %d dirs removed" % (ok, total + 1))


def sleep(secs):
    """Sleeps efficiently for secs seconds"""
    if kodi_major_version > 13:
        xbmc.Monitor().waitForAbort(secs)
    else:
        xbmc.sleep(1000 * secs)


def main():
    """Main entry point of the script when it is invoked by Kodi."""
    global kodi_major_version
    # Get parameters from Kodi and launch actions
    kodi_dir_handle = int(sys.argv[1])
    params = get_params(sys.argv)
    action = params.get("action", "Unknown")
    xbmc.log(
        "SUBDIVX - Version: %s -- Action: %s" % (__version__, action), level=LOGINFO
    )
    kodi_major_version = int(xbmc.getInfoLabel("System.BuildVersion").split(".")[0])

    if action in ("search", "manualsearch"):
        item = {
            "temp": False,
            "rar": False,
            "year": xbmc.getInfoLabel("VideoPlayer.Year"),
            "season": xbmc.getInfoLabel("VideoPlayer.Season"),
            "episode": xbmc.getInfoLabel("VideoPlayer.Episode"),
            "tvshow": normalize("NFKD", xbmc.getInfoLabel("VideoPlayer.TVshowtitle")),
            # Try to get original title
            "title": normalize("NFKD", xbmc.getInfoLabel("VideoPlayer.OriginalTitle")),
            # Full path of a playing file
            "file_original_path": unquote(xbmc.Player().getPlayingFile()),
            "3let_language": [],
            "2let_language": [],
            "manual_search": "searchstring" in params,
        }

        if "searchstring" in params:
            item["manual_search_string"] = params["searchstring"]

        for lang in unquote(params["languages"]).split(","):
            item["3let_language"].append(xbmc.convertLanguage(lang, xbmc.ISO_639_2))
            item["2let_language"].append(xbmc.convertLanguage(lang, xbmc.ISO_639_1))

        if not item["title"]:
            # No original title, get just Title
            item["title"] = normalize("NFKD", xbmc.getInfoLabel("VideoPlayer.Title"))

        if "s" in item["episode"].lower():
            # Check if season is "Special"
            item["season"] = "0"
            item["episode"] = item["episode"][-1:]

        if "http" in item["file_original_path"]:
            item["temp"] = True

        elif "rar://" in item["file_original_path"]:
            item["rar"] = True
            item["file_original_path"] = os.path.dirname(item["file_original_path"][6:])

        elif "stack://" in item["file_original_path"]:
            stackPath = item["file_original_path"].split(" , ")
            item["file_original_path"] = stackPath[0][8:]

        action_search(kodi_dir_handle, item)
        # Send end of directory to Kodi
        xbmcplugin.endOfDirectory(kodi_dir_handle)

    elif action == "download":
        debug_dump_path(
            xbmcvfs.translatePath(__addon__.getAddonInfo("profile")),
            "xbmcvfs.translatePath(__addon__.getAddonInfo('profile'))",
        )
        debug_dump_path(__profile__, "__profile__")
        xbmcvfs.mkdirs(__profile__)
        _cleanup_tempdirs(__profile__)
        workdir = tempfile.mkdtemp(dir=__profile__)
        # Make sure it ends with a path separator (Kodi 14)
        workdir = workdir + os.path.sep
        debug_dump_path(workdir, "workdir")
        # We pickup our arguments sent from the action_search() function
        subs = action_download(params["id"], workdir)
        # We can return more than one subtitle for multi CD versions, for now
        # we are still working out how to handle that in Kodi core
        for sub in subs:
            # XXX: Kodi still can't handle multiple subtitles files returned
            # from an addon, it will always use the first file returned. So
            # there is no point in reporting a forced subtitle file to it.
            # See https://github.com/ramiro/service.subtitles.subdivx/issues/14
            if sub["forced"]:
                continue
            listitem = xbmcgui.ListItem(label=sub["path"])
            xbmcplugin.addDirectoryItem(
                handle=kodi_dir_handle,
                url=sub["path"],
                listitem=listitem,
                isFolder=False,
            )
        # Send end of directory to Kodi
        xbmcplugin.endOfDirectory(kodi_dir_handle)

        sleep(2)
        if __addon__.getSetting("show_nick_in_place_of_lang") == "true":
            _double_dot_fix_hack(params["filename"])
        _cleanup_tempdir(workdir, verbose=True)


if __name__ == "__main__":
    main()
