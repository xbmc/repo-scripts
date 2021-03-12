import os
import time
from kodi_six import xbmc
import sys

import YoutubeDLWrapper

import YDStreamUtils as StreamUtils
from yd_private_libs import util, servicecontrol


PY3 = sys.version_info >= (3, 0)
if PY3:
    import urllib.parse as urlparse
    from urllib.parse import urlencode
    import http.client as httplib
else:
    import urlparse
    import httplib
    from urllib import urlencode
    

class DownloadResult:
    """
    Represents a download result. Evaluates as non-zero on success.
    Ex. usage:
    dr = handleDownload(url,formatID,title)
    if dr:
        print 'Successfully downloaded %s' % dr.filepath
    else:
        if not dr.status == 'canceled':
            print 'Download failed: %s' % dr.message

    """
    def __init__(self, success, message='', status='', filepath=''):
        self.success = success
        self.message = message
        self.status = status
        self.filepath = filepath

    def __nonzero__(self):
        return self.success


###############################################################################
# Private Methods
###############################################################################
def _getVideoFormat(info):
    """
    Quality is 0=SD, 1=720p, 2=1080p, 3=Highest Available
    and represents a maximum.
    """
    try:
        quality = info['quality']
    except KeyError:
        quality = util.getSetting('video_quality', 1)
    qualities = {0: 'worstvideo+bestaudio/worst',
                 1: 'bestvideo[height<=720]+bestaudio/best[height<=720]/bestvideo+bestaudio/best',
                 2: 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/bestvideo+bestaudio/best',
                 3: 'bestvideo+bestaudio/best'}
    return qualities[quality]


def _getQualityLimits(quality):
    minHeight = 0
    maxHeight = 480
    if quality > 2:
        minHeight = 1081
        maxHeight = 999999
    elif quality > 1:
        minHeight = 721
        maxHeight = 1080
    elif quality > 0:
        minHeight = 481
        maxHeight = 720
    return minHeight, maxHeight


def _selectVideoQuality(r, quality=None):
    if quality is None:
        quality = util.getSetting('video_quality', 1)

    disable_dash = util.getSetting('disable_dash_video', True)
    skip_no_audio = util.getSetting('skip_no_audio', True)

    entries = r.get('entries') or [r]

    minHeight, maxHeight = _getQualityLimits(quality)

    util.LOG('Quality: {0}'.format(quality), debug=True)
    urls = []
    idx = 0
    for entry in entries:
        defFormat = None
        defMax = 0
        defPref = -1000
        prefFormat = None
        prefMax = 0
        prefPref = -1000

        index = {}
        formats = entry.get('formats') or [entry]

        for i in range(len(formats)):
            index[formats[i]['format_id']] = i

        keys = sorted(index.keys())
        fallback = formats[index[keys[0]]]
        for fmt in keys:
            fdata = formats[index[fmt]]

            if 'height' not in fdata:
                continue
            elif disable_dash and 'dash' in fdata.get('format_note', '').lower():
                continue
            elif skip_no_audio and fdata.get('acodec', '').lower() == 'none':
                continue

            h = fdata['height']
            if h is None:
                h = 1
            p = fdata.get('preference', 1)
            if p is None:
                p = 1
            if h >= minHeight and h <= maxHeight:
                if (h >= prefMax and p > prefPref) or (h > prefMax and p >= prefPref):
                    prefMax = h
                    prefPref = p
                    prefFormat = fdata
            elif(h >= defMax and h <= maxHeight and p > defPref) or (h > defMax and h <= maxHeight and p >= defPref):
                defMax = h
                defFormat = fdata
                defPref = p
        formatID = None
        if prefFormat:
            info = prefFormat
            logBase = '[{3}] Using Preferred Format: {0} ({1}x{2})'
        elif defFormat:
            info = defFormat
            logBase = '[{3}] Using Default Format: {0} ({1}x{2})'
        else:
            info = fallback
            logBase = '[{3}] Using Fallback Format: {0} ({1}x{2})'
        url = info['url']
        formatID = info['format_id']
        util.LOG(logBase.format(formatID, info.get('width', '?'), info.get('height', '?'), entry.get('title', '').encode('ascii', 'replace')), debug=True)
        if url.find("rtmp") == -1:
            url += '|' + urlencode({'User-Agent': entry.get('user_agent') or YoutubeDLWrapper.std_headers['User-Agent']})
        else:
            url += ' playpath=' + fdata['play_path']
        new_info = dict(entry)
        new_info.update(info)
        urls.append(
            {
                'xbmc_url': url,
                'url': info['url'],
                'title': entry.get('title', ''),
                'thumbnail': entry.get('thumbnail', ''),
                'formatID': formatID,
                'idx': idx,
                'ytdl_format': new_info
            }
        )
        idx += 1
    return urls


# Recursively follow redirects until there isn't a location header
# Credit to: Zachary Witte @ http://www.zacwitte.com/resolving-http-redirects-in-python
def resolve_http_redirect(url, depth=0):
    if depth > 10:
        raise Exception("Redirected " + depth + " times, giving up.")
    o = urlparse.urlparse(url, allow_fragments=True)
    conn = httplib.HTTPConnection(o.netloc)
    path = o.path
    if o.query:
        path += '?' + o.query
    conn.request("HEAD", path, headers={'User-Agent': YoutubeDLWrapper.std_headers['User-Agent']})
    res = conn.getresponse()
    headers = dict(res.getheaders())
    if 'location' in headers and headers['location'] != url:
        return resolve_http_redirect(headers['location'], depth + 1)
    else:
        return url


def _getYoutubeDLVideo(url, quality=None, resolve_redirects=False):
    if resolve_redirects:
        try:
            url = resolve_http_redirect(url)
        except Exception:
            util.ERROR('_getYoutubeDLVideo(): Failed to resolve URL')
            return None
    ytdl = YoutubeDLWrapper._getYTDL()
    ytdl.clearDownloadParams()
    try:
        r = ytdl.extract_info(url, download=False)
    except YoutubeDLWrapper.DownloadError:
        return None
    urls = _selectVideoQuality(r, quality)
    if not urls:
        return None
    info = YoutubeDLWrapper.VideoInfo(r.get('id', ''))
    info._streams = urls
    info.title = r.get('title', urls[0]['title'])
    info.description = r.get('description', '')
    info.thumbnail = r.get('thumbnail', urls[0]['thumbnail'])
    info.sourceName = r.get('extractor', '')
    info.info = r
    return info


def _convertInfo(info):
    import xbmcgui
    # If we have a VidInfo object or ListItem exctract or create info
    if isinstance(info, YoutubeDLWrapper.VideoInfo):
        dlID = info.downloadID
        info = info.selectedStream()['ytdl_format']
        if 'formats' in info:
            del info['formats']  # Remove possible circular reference
        info['media_type'] = 'video'
        info['download.ID'] = dlID
    elif isinstance(info, xbmcgui.ListItem):
        info = _infoFromListItem(info)
    return info


def _completeInfo(info):
    if 'ext' not in info:
        info['ext'] = _getExtension(info)
    if 'title' not in info:
        info['title'] = 'Unknown'
    if 'download.ID' not in info:
        info['download.ID'] = str(time.time())
    if 'url' not in info:
        info['url'] = info['requested_formats'][0]['url']


def _getExtension(info):
    ext = _actualGetExtension(info)
    if ext == 'm3u8':
        return 'mp4'
    return ext


def _actualGetExtension(info):
    url = info['url']
    initialURLExt = url.rsplit('.', 1)[-1]
    resolvedURLExt = None
    contentTypeExt = None
    try:
        url = resolve_http_redirect(url)
        o = urlparse.urlparse(url, allow_fragments=True)
        conn = httplib.HTTPConnection(o.netloc)
        conn.request("HEAD", o.path, headers={'User-Agent': YoutubeDLWrapper.std_headers['User-Agent']})
        res = conn.getresponse()

        headers = dict(res.getheaders())

        contentDisposition = headers.get('content-disposition')
        if contentDisposition:
            n, e = os.path.splitext(contentDisposition)
            if e:
                return e.strip('.')  # If we get this we're lucky
        else:
            n, e = os.path.splitext(url)  # Check the resolved url
            resolvedURLExt = e.strip('.')

        contentType = headers['content-type']
        import mimetypes
        ext = mimetypes.guess_extension(contentType)
        if ext:
            contentTypeExt = ext.strip('.')  # This is probabaly wrong
    except Exception:
        util.ERROR(hide_tb=True)

    extensions = [ex for ex in (resolvedURLExt, initialURLExt, contentTypeExt) if ex]
    if 'media_type' in info:
        for ext in extensions:
            return _validateExtension(ext, info)
    else:
        for ext in extensions:
            if _isValidMediaExtension(ext):
                return ext

    for ext in extensions:
        return ext

    return 'mp4'


def _validateExtension(ext, info):
    # use Kodi's supported media to check for valid extension or return default
    if info.get('media_type') == 'video':
        if ext not in xbmc.getSupportedMedia('video'):
            return 'mp4'
    elif info.get('media_type') == 'audio':
        if ext not in xbmc.getSupportedMedia('music'):
            return 'mp3'
    elif info.get('media_type') == 'image':
        if ext not in xbmc.getSupportedMedia('picture'):
            return 'jpg'
    return ext


def _isValidMediaExtension(ext):
    # use Kodi's supported media to check for valid extension
    if ext in xbmc.getSupportedMedia('video') or ext in xbmc.getSupportedMedia('music') or ext in xbmc.getSupportedMedia('picture'):
        return True
    return False


def _infoFromListItem(listitem):
    url = listitem.getfilename()
    title = listitem.getProperty('title') or listitem.getLabel()
    description = listitem.getLabel2() or ''
    thumbnail = listitem.getProperty('iconImage') or listitem.getProperty('thumbnailImage') or ''  # Not sure if this works

    return {'url': url, 'title': title, 'description': description, 'thumbnail': thumbnail}


def _setDownloadDuration(duration=None):
    if duration:
        YoutubeDLWrapper._DOWNLOAD_START = time.time()
        YoutubeDLWrapper._DOWNLOAD_DURATION = duration
    else:
        YoutubeDLWrapper._DOWNLOAD_START = None
        YoutubeDLWrapper._DOWNLOAD_DURATION = None


def _cancelDownload(_cancel=True):
    YoutubeDLWrapper._DOWNLOAD_CANCEL = _cancel


def _handleDownload(vidinfo, path=None, filename=None, duration=None, bg=False):
    path = path or StreamUtils.getDownloadPath(use_default=True)  # this is already done in handleDownload...
    template = u'{}.%(ext)s'.format(filename or u'%(title)s-%(id)s')

    if bg:
        downloader = StreamUtils.DownloadProgressBG
    else:
        downloader = StreamUtils.DownloadProgress

    with downloader(line1='Starting download...') as prog:

        try:
            setOutputCallback(prog.updateCallback)
            _setDownloadDuration(duration)
            result = download(vidinfo, util.TMP_PATH, template=template)
        finally:
            setOutputCallback(None)
            _setDownloadDuration(duration)

    if not result and result.status != 'canceled':
        StreamUtils.showMessage(StreamUtils.T(32013), result.message, bg=bg)

    filePath = result.filepath
    part = filePath + u'.part'
    try:
        if os.path.exists(part):
            os.rename(part, filePath)
    except UnicodeDecodeError:
        part = part.encode('utf-8')
        if os.path.exists(part):
            os.rename(part, filePath)

    destpath = StreamUtils.moveFile(filePath, path)
    if not destpath:
        StreamUtils.showMessage(StreamUtils.T(32036), StreamUtils.T(32037), '', filePath, bg=bg)
    else:
        StreamUtils.showMessage(StreamUtils.T(32011), StreamUtils.T(32012), '', destpath, bg=bg)
        result.filepath = destpath

    return result


def downloadVideo(info, path):
    """
    Deprecated
    """
    return handleDownload(info, path=path)


###############################################################################
# Public Methods
###############################################################################
def setOutputCallback(callback):
    """
    Sets a callback for youtube-dl output or progress updates.
    Must return True to continue or False to cancel.
    Will be called with CallbackMessage object.
    If the callback raises an exception it will be disabled.
    """
    YoutubeDLWrapper._CALLBACK = callback


@util.busyDialog
def getVideoInfo(url, quality=None, resolve_redirects=False):
    """
    Returns a VideoInfo object or None.
    Quality is 0=SD, 1=720p, 2=1080p, 3=Highest Available
    and represents a maximum.
    """
    try:
        info = _getYoutubeDLVideo(url, quality, resolve_redirects)
        if not info:
            return None
    except Exception:
        util.ERROR('_getYoutubeDLVideo() failed', hide_tb=True)
        return None
    return info


def handleDownload(info, duration=None, bg=False, path=None, filename=None):
    """
    Download the selected video to a path the user chooses.
    Displays a progress dialog and ok/error message when finished.
    Set bg=True to download in the background.
    Returns a DownloadResult object for foreground transfers.
    """
    if isinstance(info, YoutubeDLWrapper.VideoInfo):  # backward compatibility
        info = info.info
        info['url'] = info['webpage_url']
    path = path or StreamUtils.getDownloadPath()
    if bg:
        servicecontrol.ServiceControl().download(info, path, filename, duration)
    else:
        return _handleDownload(info, path=path, filename=filename, duration=duration, bg=False)


def download(info, path, template='%(title)s-%(id)s.%(ext)s'):
    """
    Download the selected video in info to path.
    Template sets the youtube-dl format which defaults to TITLE-ID.EXT.
    Returns a DownloadResult object.
    """

    # kept temporarily for backward compatibilty with xbmcgui.ListItem objects (any test examples?)
    info = _convertInfo(info)  # Get the right format

    _cancelDownload(_cancel=False)
    path_template = os.path.join(path, template)
    ytdl = YoutubeDLWrapper._getYTDL()
    ytdl.clearDownloadParams()
    ytdl.params.update({'outtmpl': path_template, 'format': _getVideoFormat(info)})

    ie_result = ytdl.extract_info(info['url'], download=False)
    filepath = ytdl.prepare_filename(ie_result)
    _completeInfo(ie_result)  # Make sure we have the needed bits

    import AddonSignals
    signalPayload = {'title': ie_result['title'], 'url': ie_result['url'], 'download.ID': ie_result['download.ID']}

    try:
        AddonSignals.sendSignal('download.started', signalPayload, source_id='script.module.youtube.dl')
        dl_result = YoutubeDLWrapper.download(ie_result)
    except YoutubeDLWrapper.youtube_dl.DownloadError as e:
        return DownloadResult(False, e.message, filepath=filepath)
    except YoutubeDLWrapper.DownloadCanceledException:
        return DownloadResult(False, status='canceled', filepath=filepath)
    finally:
        ytdl.clearDownloadParams()
        signalPayload['path'] = filepath
        AddonSignals.sendSignal('download.finished', signalPayload, source_id='script.module.youtube.dl')

    return DownloadResult(True, filepath=filepath)


def mightHaveVideo(url, resolve_redirects=False):
    """
    Returns True if the url matches against one of the handled site URLs.
    """
    if resolve_redirects:
        try:
            url = resolve_http_redirect(url)
        except Exception:
            util.ERROR('mightHaveVideo(): Failed to resolve URL')
            return False

    ytdl = YoutubeDLWrapper._getYTDL()
    for ies in ytdl._ies:
        if ies.suitable(url):
            return True
    return False


def disableDASHVideo(disable=True):
    """
    DEPRECATED: Now handled by module settings
    """
    import warnings
    warnings.warn("External use of disableDASHVideo() is deprecated. It is now handled by module settings")


def overrideParam(key, val):
    """
    Override a youtube_dl parmeter.
    """
    YoutubeDLWrapper._OVERRIDE_PARAMS[key] = val


def generateBlacklist(regexs):
    """
    Generate a blacklist of extractors based on IE_NAME.
    regexs is a list or tuple of regular expressions.
    Extractors that match any of the regular expressions are added.
    """
    import re
    from youtube_dl.extractor import gen_extractors
    for ie in gen_extractors():
        for r in regexs:
            if re.search(r, ie.IE_NAME):
                YoutubeDLWrapper._BLACKLIST.append(ie.IE_NAME)


def manageDownloads():
    """
    Open the download manager.
    """
    xbmc.executebuiltin('RunScript(script.module.youtube.dl)')


def isDownloading():
    """
    Returns true if background download service is handling downloads.
    """
    return servicecontrol.ServiceControl().isDownloading()
