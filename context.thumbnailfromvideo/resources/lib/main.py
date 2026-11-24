import json
import os
import threading
import time

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from . import frametime
from .picker import XML_FILE, FramePicker

ADDON_ID = 'context.thumbnailfromvideo'
NETWORK_SCHEMES = ('smb', 'nfs', 'ftp', 'ftps', 'sftp', 'dav', 'davs', 'special')


def log(msg, level=xbmc.LOGINFO):
    xbmc.log('[%s] %s' % (ADDON_ID, msg), level)


def jsonrpc(method, params):
    req = {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}
    resp = json.loads(xbmc.executeJSONRPC(json.dumps(req)))
    if 'error' in resp:
        log('%s failed: %s' % (method, resp['error']), xbmc.LOGERROR)
        return None
    return resp.get('result')


# Library media types this add-on supports, with their JSON-RPC names
MEDIA = {
    'musicvideo': {'get': 'VideoLibrary.GetMusicVideoDetails',
                   'set': 'VideoLibrary.SetMusicVideoDetails',
                   'id': 'musicvideoid', 'result': 'musicvideodetails', 'extra': []},
    'episode': {'get': 'VideoLibrary.GetEpisodeDetails',
                'set': 'VideoLibrary.SetEpisodeDetails',
                'id': 'episodeid', 'result': 'episodedetails',
                'extra': ['showtitle', 'season', 'episode']},
    'movie': {'get': 'VideoLibrary.GetMovieDetails',
              'set': 'VideoLibrary.SetMovieDetails',
              'id': 'movieid', 'result': 'moviedetails', 'extra': ['year']},
}
# a video file that is not in the library (Videos > Files)
FILE = 'file'


def get_item(listitem):
    """Return (mediatype, dbid, path, title, state) for the selected library item."""
    dbid, path, title, mediatype = 0, '', '', ''
    if listitem is not None:
        try:
            tag = listitem.getVideoInfoTag()
            dbid = tag.getDbId()
            path = tag.getFilenameAndPath()
            title = tag.getTitle()
            mediatype = tag.getMediaType()
        except Exception:
            pass
        path = path or listitem.getPath()
        title = title or listitem.getLabel()
    if not dbid or dbid < 0:
        try:
            dbid = int(xbmc.getInfoLabel('ListItem.DBID') or 0)
        except ValueError:
            dbid = 0
    mediatype = mediatype or xbmc.getInfoLabel('ListItem.DBType')
    path = path or xbmc.getInfoLabel('ListItem.FileNameAndPath')
    title = title or xbmc.getInfoLabel('ListItem.Title')

    state = {}
    media = MEDIA.get(mediatype)
    if media and dbid > 0:
        res = jsonrpc(media['get'], {
            media['id']: dbid,
            'properties': ['file', 'title', 'playcount', 'lastplayed', 'resume'] + media['extra']})
        if res and media['result'] in res:
            d = res[media['result']]
            path = d.get('file') or path
            title = d.get('title') or title
            if mediatype == 'episode' and d.get('showtitle'):
                title = '%s  %dx%02d  %s' % (d['showtitle'], d.get('season', 0),
                                             d.get('episode', 0), title)
            elif mediatype == 'movie' and d.get('year'):
                title = '%s (%d)' % (title, d['year'])
            state = {'playcount': d.get('playcount', 0),
                     'lastplayed': d.get('lastplayed', ''),
                     'resume': d.get('resume') or {'position': 0, 'total': 0}}
    elif not media and path and not path.startswith('plugin://'):
        # plain video file, not in the library
        mediatype, dbid = FILE, 0
        if listitem is not None and listitem.getPath():
            path = listitem.getPath()
        title = title or os.path.splitext(path.replace('\\', '/').rsplit('/', 1)[-1])[0]
        # a file Kodi has never played has no record yet: treat it as unwatched,
        # so the resume point our playback leaves behind gets cleared again
        state = get_file_state(path) or {'playcount': 0, 'lastplayed': '',
                                         'resume': {'position': 0, 'total': 0}}
    return mediatype, dbid, path, title, state


def get_file_state(path):
    res = jsonrpc('Files.GetFileDetails', {
        'file': path, 'media': 'video', 'properties': ['playcount', 'lastplayed', 'resume']})
    d = (res or {}).get('filedetails')
    if not d:
        return {}
    return {'playcount': d.get('playcount', 0),
            'lastplayed': d.get('lastplayed', ''),
            'resume': d.get('resume') or {'position': 0, 'total': 0}}


def ensure_paused(player):
    """Player.pause() is a toggle, so only call it when actually playing."""
    if not xbmc.getCondVisibility('Player.Paused'):
        player.pause()


class PausedStartPlayer(xbmc.Player):
    """Pauses the moment Kodi reports the video has started."""

    def __init__(self):
        super().__init__()
        self.started = threading.Event()

    def onAVStarted(self):
        if not self.started.is_set():
            self.started.set()
            ensure_paused(self)


POSITIONS_FILE = 'positions.json'
MAX_POSITIONS = 5000


def position_key(path):
    return path.replace('\\', '/').lower()


def _read_positions(profile):
    try:
        with open(os.path.join(profile, POSITIONS_FILE), encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def load_position(profile, path):
    """Seconds where the picker was left last time for this video, or None."""
    try:
        v = float(_read_positions(profile).get(position_key(path)) or 0)
    except (TypeError, ValueError):
        return None
    return v if v > 0 else None


def save_position(profile, path, seconds):
    """Remember the picker position for this video (most recent kept last;
    the oldest entries are dropped beyond MAX_POSITIONS)."""
    data = _read_positions(profile)
    key = position_key(path)
    data.pop(key, None)
    data[key] = round(float(seconds), 2)
    while len(data) > MAX_POSITIONS:
        data.pop(next(iter(data)))
    target = os.path.join(profile, POSITIONS_FILE)
    tmp = target + '.tmp'
    try:
        os.makedirs(profile, exist_ok=True)
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, target)
    except OSError as e:
        log('could not save position: %s' % e, xbmc.LOGWARNING)


def read_image_head(url):
    try:
        f = xbmcvfs.File(url)
        try:
            return bytes(f.readBytes(frametime.HEAD_BYTES))
        finally:
            f.close()
    except Exception:
        return b''


def thumb_time(mediatype, dbid, path):
    """Video time stored inside the video's current thumbnail (see frametime),
    looking at the library thumbnail first, then <video>-thumb.png/.jpg."""
    from .backup import decode_art
    candidates = []
    media = MEDIA.get(mediatype)
    if media and dbid > 0:
        res = jsonrpc(media['get'], {media['id']: dbid, 'properties': ['art']})
        art = ((res or {}).get(media['result']) or {}).get('art') or {}
        real = decode_art(art.get('thumb', ''))
        if real:
            candidates.append(real)
    parts = split_media_path(path)
    if parts:
        candidates += ['%s%s-thumb%s' % (parts[0], parts[1], ext) for ext in ('.png', '.jpg')]
    for url in candidates:
        if xbmcvfs.exists(url):
            t = frametime.parse(read_image_head(url))
            if t:
                return t
    return None


def _now(player):
    try:
        return player.getTime()
    except RuntimeError:
        return -1.0


def _settle(player, monitor, before, timeout=2.0):
    """Wait until the player's time changes from `before` (or timeout)."""
    waited = 0.0
    while waited < timeout:
        if monitor.waitForAbort(0.05):
            return _now(player)
        waited += 0.05
        t = _now(player)
        if abs(t - before) > 0.001:
            monitor.waitForAbort(0.1)  # let the picture follow the clock
            return _now(player)
    return _now(player)


def exact_seek(player, target, fps_hint=25.0):
    """Show exactly the frame at `target` seconds, paused. Returns the time
    the player reports afterwards.

    A normal seek is frame-accurate for most files, but for MPEG-2 (.mpg,
    .vob) Kodi lands on a later frame. Then: seek to a bit before the
    target and step forward frame by frame with PlayerControl(FrameAdvance).
    """
    monitor = xbmc.Monitor()
    try:
        fps = float(xbmc.getInfoLabel('Player.Process(videofps)') or 0) or fps_hint
    except ValueError:
        fps = fps_hint
    half = 0.5 / fps
    player.seekTime(target)
    monitor.waitForAbort(0.4)
    ensure_paused(player)
    t = _now(player)
    if abs(t - target) <= half:
        return t
    # land before the target: back off until the player is at or before it
    for back in (1.0, 2.5, 5.0):
        player.seekTime(max(0.0, target - back))
        monitor.waitForAbort(0.4)
        ensure_paused(player)
        t = _now(player)
        if t <= target + half:
            break
    else:
        return t
    # one frame first, to learn how far a step moves (fields vs frames)
    step = 1.0 / fps
    for _ in range(4):
        remaining = target - t
        if remaining <= half:
            break
        n = max(1, int(round(remaining / step)))
        before = t
        xbmc.executebuiltin('PlayerControl(FrameAdvance(%d))' % n)
        t = _settle(player, monitor, before)
        if t > before:
            step = max((t - before) / n, 0.005)
    ensure_paused(player)
    return t


def start_playback(path, start_pct, start_sec=None):
    player = PausedStartPlayer()
    monitor = xbmc.Monitor()
    if player.isPlaying():
        player.stop()
        for _ in range(40):
            if not player.isPlaying() or monitor.waitForAbort(0.25):
                break
    item = xbmcgui.ListItem(path=path)
    if start_sec:
        item.setProperty('StartOffset', '%.2f' % start_sec)  # last spot used for this video
    elif start_pct > 0:
        item.setProperty('StartPercent', str(start_pct))  # start right at the position
    player.play(path, item)
    # Kodi only delivers Player callbacks while the script sleeps in Kodi's own
    # waitForAbort/sleep, so poll with that (never threading.Event.wait), and also
    # check the player state directly in case onAVStarted is missed.
    # Prefer onAVStarted (first frame is actually playing; slow files such as
    # 1080p x265 episodes can take a while). If the callback never comes, fall
    # back to the player state after a few seconds.
    t0 = time.time()
    started = False
    while time.time() - t0 < 30:
        if player.started.is_set() or (time.time() - t0 > 5 and player.isPlayingVideo()):
            try:
                started = player.getTotalTime() > 0
            except RuntimeError:
                started = False
            if started:
                break
        if monitor.waitForAbort(0.02):
            return None
    if not started:
        return None
    player.started.set()  # a late onAVStarted must not act any more
    # make sure we end up paused (never toggles: checks the state first)
    for _ in range(20):
        ensure_paused(player)
        if monitor.waitForAbort(0.1) or xbmc.getCondVisibility('Player.Paused'):
            break
    return player


def split_media_path(path):
    """Return (dir_with_sep, basename_without_ext) if we can write next to it."""
    if '://' in path and path.split('://', 1)[0].lower() not in NETWORK_SCHEMES:
        return None
    sep = '/' if '/' in path else '\\'
    idx = path.rfind(sep)
    if idx < 0:
        return None
    return path[:idx + 1], os.path.splitext(path[idx + 1:])[0]


def remove_cached_texture(url):
    res = jsonrpc('Textures.GetTextures', {
        'filter': {'field': 'url', 'operator': 'is', 'value': url},
        'properties': ['url']})
    for t in (res or {}).get('textures', []):
        jsonrpc('Textures.RemoveTexture', {'textureid': t['textureid']})


def write_local(src, path, arttype, ext):
    """Copy the image next to the video as <video>-<arttype><ext>.
    Returns True when it is there."""
    parts = split_media_path(path)
    if not parts:
        log('cannot write next to %s' % path, xbmc.LOGWARNING)
        return False
    local = '%s%s-%s%s' % (parts[0], parts[1], arttype, ext)
    if xbmcvfs.copy(src, local) and xbmcvfs.exists(local):
        remove_cached_texture(local)
        # a <video>-thumb.png / .jpg from an earlier save in the other format
        # would compete with the new one (Kodi takes the first it finds)
        other = '.png' if ext == '.jpg' else '.jpg'
        old = '%s%s-%s%s' % (parts[0], parts[1], arttype, other)
        if xbmcvfs.exists(old):
            xbmcvfs.delete(old)
            remove_cached_texture(old)
        return True
    log('could not write %s' % local, xbmc.LOGWARNING)
    return False


def write_local_jpg(raw, path, arttype, workdir, frame_time=None):
    """Encode the frame as JPG and put it next to the video. Pure-Python JPEG
    encoding takes a second or two, so this runs after everything else,
    when the user is already back in the list. Returns True when written."""
    from . import jpeg
    data, w, h = raw
    tmp = os.path.join(workdir, 'local-%d.jpg' % int(time.time() * 1000))
    try:
        jpeg.write_bgra(tmp, w, h, data, 90,
                        frametime.jpeg_comment(frame_time) if frame_time else None)
        return write_local(tmp, path, arttype, '.jpg')
    except Exception as e:
        log('could not write JPG: %s' % e, xbmc.LOGERROR)
        return False
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def save_image(src, mediatype, dbid, path, arttype, location, profile, local_png=True,
               ext='.png'):
    """Save the frame and return the URL to store in the library.

    The library always gets a new, uniquely named file: re-using a fixed name
    (e.g. <video>-thumb.png) makes Kodi keep showing the old image it already
    has in memory for that URL. With "next to the video file" selected, the
    fixed-name copy is written as well (as PNG here; a JPG is written later by
    write_local_jpg), for rescans and other Kodi installs.
    """
    if location == 1 and local_png:
        write_local(src, path, arttype, ext)
    folder = os.path.join(profile, 'thumbs')
    os.makedirs(folder, exist_ok=True)
    # music video 5 and episode 5 are different items, so include the type
    if mediatype == FILE:  # no library id: name it after the file path
        import hashlib
        key = hashlib.md5(path.encode('utf-8')).hexdigest()[:12]
    else:
        key = str(dbid)
    prefix = '%s-%s-%s-' % (mediatype, key, arttype)
    dest = os.path.join(folder, '%s%d%s' % (prefix, int(time.time() * 1000), ext))
    # write the new image first; only when it is really there remove this
    # video's older copies (never leave the library pointing at nothing)
    if not (xbmcvfs.copy(src, dest) and os.path.exists(dest) and os.path.getsize(dest) > 0):
        log('could not save %s' % dest, xbmc.LOGERROR)
        return None
    for name in os.listdir(folder):
        if name.startswith(prefix) and name != os.path.basename(dest):
            try:
                os.remove(os.path.join(folder, name))
            except OSError:
                pass
    return dest


SCAN_DIR = 'special://profile/addon_data/%s/scan/' % ADDON_ID


def refresh_widgets():
    """Make home-screen widgets reload so they show the new artwork.

    Widgets reload on VideoLibrary announcements such as "OnScanFinished", but
    an art-only change sends none (and JSON-RPC only announces a playcount that
    actually changed). Scanning an empty folder of our own adds nothing to the
    library, yet Kodi still announces OnScanFinished, so every widget reloads.
    """
    xbmcvfs.mkdirs(SCAN_DIR)
    jsonrpc('VideoLibrary.Scan', {'directory': SCAN_DIR, 'showdialogs': False})


def restore_state(media, dbid, state, path=''):
    """Undo watched-count / resume-point changes caused by our playback.

    Only writes when something really changed, because every write makes Kodi
    reload the whole list on screen. "Last played" alone is not worth that.
    """
    if not state:
        return
    if media is None:  # plain file
        now = get_file_state(path)
        if not now:
            return
    else:
        res = jsonrpc(media['get'], {media['id']: dbid, 'properties': ['playcount', 'resume']})
        if not res or media['result'] not in res:
            return
        now = res[media['result']]
    old_resume = state.get('resume') or {}
    new_resume = now.get('resume') or {}
    changed = (now.get('playcount', 0) != state.get('playcount', 0) or
               int(new_resume.get('position', 0)) != int(old_resume.get('position', 0)))
    if not changed:
        return
    if media is None:
        params = {'file': path, 'media': 'video', 'playcount': state.get('playcount', 0),
                  'resume': {'position': old_resume.get('position', 0),
                             'total': old_resume.get('total', 0)}}
        if state.get('lastplayed'):
            params['lastplayed'] = state['lastplayed']
        jsonrpc('Files.SetFileDetails', params)
    else:
        jsonrpc(media['set'], dict({media['id']: dbid}, **state))


WINDOW_HOME = 10000


def run(listitem):
    # remember where the context menu was opened (before playback changes it)
    from_home = xbmcgui.getCurrentWindowId() == WINDOW_HOME
    addon = xbmcaddon.Addon(ADDON_ID)
    L = addon.getLocalizedString
    name = addon.getAddonInfo('name')
    profile = xbmcvfs.translatePath(addon.getAddonInfo('profile'))
    workdir = os.path.join(profile, 'tmp')
    os.makedirs(workdir, exist_ok=True)
    for f in os.listdir(workdir):
        if f.startswith(('frame-', 'preview-', 'local-')):
            try:
                os.remove(os.path.join(workdir, f))
            except OSError:
                pass

    settings = addon.getSettings()
    location = settings.getInt('save_location')
    width = settings.getInt('capture_width') or 1920
    start_pct = settings.getInt('start_percent')
    dialog = xbmcgui.Dialog()

    mediatype, dbid, path, title, state = get_item(listitem)
    media = MEDIA.get(mediatype)
    is_file = mediatype == FILE
    if not path or (not is_file and (not media or dbid <= 0)):
        dialog.notification(name, L(30300), xbmcgui.NOTIFICATION_ERROR)
        return

    remember = True  # always reopen at the last spot used, if there is one
    store_time = True  # the frame time is always stored inside the thumbnail
    # where to start: the frame the current thumbnail was taken from, then the
    # last spot used in the picker, then "Start position"
    start_sec = thumb_time(mediatype, dbid, path) if store_time else None
    if not start_sec and remember:
        start_sec = load_position(profile, path)
    player = start_playback(path, start_pct, start_sec)
    if not player:
        dialog.notification(name, L(30301), xbmcgui.NOTIFICATION_ERROR)
        return

    # Start offsets land on the nearest key frame (or are ignored by some
    # builds): seek to the exact spot while staying paused.
    total = player.getTotalTime()
    if start_sec:
        target = min(start_sec, max(total - 0.5, 0))
    else:
        target = total * start_pct / 100.0 if start_pct > 0 else 0
    # A remembered spot / the thumbnail's frame must be hit exactly (a start
    # offset lands on a key frame, which can be up to a second or more away);
    # for "Start position" (a percentage) being close is enough.
    # Kodi's start offset / start percent jumps to a key frame but already
    # reports the asked time, so the picture and the time disagree (and a
    # thumbnail made right away would store the wrong time). Always finish
    # with a real, frame-accurate seek to the target.
    if target > 0 and total > 0:
        landed = exact_seek(player, target)
        log('opened at %.3f s (%s; player reports %.3f s)'
            % (target, 'saved frame' if start_sec else 'start position', landed))

    texts = {'heading': L(30117), 'capture_failed': L(30302)}
    picker = FramePicker(XML_FILE, addon.getAddonInfo('path'), 'Default', '1080i')
    # A plain video file's thumbnail always goes next to the video
    # (<video>-thumb.jpg/.png): Kodi finds it there by itself, and there is no
    # Kodi interface for pointing a plain file at an image elsewhere.
    picker.setup(player, workdir, width, title, texts,
                 auto_crop=settings.getBool('auto_crop'), store_time=store_time,
                 want_jpg=(is_file or location == 1) and settings.getInt('image_format') == 1,
                 local_only=is_file)
    picker.doModal()
    frame = picker.result
    raw = picker.raw_jpg  # pixels for the JPG next to the video (<= 1280 wide)
    frame_time = picker.frame_time if picker.store_time else None
    del picker
    if remember:
        # where the picker was left (Make thumbnail, Cancel or Back)
        try:
            t = player.getTime() if player.isPlayingVideo() else 0
        except RuntimeError:
            t = 0
        if t > 0:
            save_position(profile, path, t)
    # settings may have been changed from the picker's Settings button
    settings = xbmcaddon.Addon(ADDON_ID).getSettings()
    location = settings.getInt('save_location')
    want_jpg = settings.getInt('image_format') == 1 and raw is not None
    local_jpg = location == 1 and want_jpg

    # Every Set*Details call for a music video/episode makes Kodi reload the
    # whole *active* list (all pictures blink). Kodi skips that reload for a
    # window that is not on screen, so the art is saved now, while the video is
    # still in front, and the list just shows the new picture when we return.
    ok = True
    error = 30304
    if frame and is_file:
        # Kodi shows <video>-thumb.jpg/.png of a plain file by itself; it must
        # hold the new picture (and Kodi's cached copy of it must be gone)
        # before the file list is shown again.
        if want_jpg:
            ok = write_local_jpg(raw, path, 'thumb', workdir, frame_time)
        else:
            ok = write_local(frame, path, 'thumb', '.png')
        os.remove(frame)
        error = 30075
        local_jpg = False
    elif frame:
        dest = save_image(frame, mediatype, dbid, path, 'thumb', location, profile,
                          local_png=not local_jpg)
        os.remove(frame)
        if not dest:
            ok = False  # nothing saved: leave the library as it was
        else:
            remove_cached_texture(dest)
            ok = jsonrpc(media['set'], {media['id']: dbid, 'art': {'thumb': dest}}) is not None

    if player.isPlaying():
        player.stop()
        # wait until playback has really ended, then a moment for Kodi to save
        # its playback state (watched/resume) before restore_state() checks it
        monitor = xbmc.Monitor()
        for _ in range(60):
            if not player.isPlaying() or monitor.waitForAbort(0.05):
                break
        monitor.waitForAbort(0.3)
    restore_state(media, dbid, state, path)

    if not frame:
        return
    if not ok:
        dialog.notification(name, L(error), xbmcgui.NOTIFICATION_ERROR)
        return
    if is_file:
        # the file list keeps the old picture until it is loaded again
        xbmc.executebuiltin('Container.Refresh')
    if from_home:
        # home-screen widgets only reload on a library announcement
        refresh_widgets()
    if local_jpg:
        # library items: last, so nobody waits for it - Kodi already shows the
        # new thumbnail (from the PNG in userdata); this only writes <video>-thumb.jpg
        write_local_jpg(raw, path, 'thumb', workdir, frame_time)
