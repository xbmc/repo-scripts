"""Actions behind the buttons on the "Backup / cache" settings page
(run through tools.py), plus a helper for Kodi art URLs.

- folderzip:       zip the thumbnails of the open video's folder (folderzip.py)
- folderrestore:   put them back from such a ZIP
- clearcache:      forget Kodi's cached copies of plain video files' thumbnails
- clearcache_mv:   the same for the music videos in the library
- clearcache_ep:   the same for the TV episodes in the library
- clearcache_open: the same for the open video only
"""
import os
from urllib.parse import unquote

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from . import main


def decode_art(url):
    """Kodi art URL -> path/URL of the real image, or None if there is no
    file behind it (e.g. thumbnails Kodi generates from the video itself)."""
    if not url:
        return None
    if url.startswith('image://'):
        inner = url[len('image://'):]
        if inner.endswith('/'):
            inner = inner[:-1]
        inner = unquote(inner)
        if inner.startswith(('video@', 'music@', 'pvrchannel', 'pvrrecording')):
            return None
        return inner
    return url


LOCAL_THUMB_ENDINGS = ('-thumb.jpg', '-thumb.png', '-thumb.jpeg', '-thumb.webp', '.tbn')

# library lists the cache buttons work on: (Get list method, result key)
LISTS = {'musicvideo': ('VideoLibrary.GetMusicVideos', 'musicvideos'),
         'episode': ('VideoLibrary.GetEpisodes', 'episodes')}


def local_thumb(video):
    """The <video>-thumb image next to the video file, or None."""
    parts = main.split_media_path(video or '')
    if not parts:
        return None
    for ending in LOCAL_THUMB_ENDINGS:
        candidate = parts[0] + parts[1] + ending
        if xbmcvfs.exists(candidate):
            return candidate
    return None


def relink_item(item, mediatype, copies, urls):
    """Make one library item's thumbnail follow the <video>-thumb image next
    to the video.

    An item whose thumbnail is this add-on's own copy (in userdata) or its
    -thumb file is pointed at the -thumb file next to the video when there is
    one. When there is none (e.g. you deleted it), the thumbnail is removed
    from the library, so Kodi shows its default picture. Web images and other
    artwork are left alone. Images to un-cache are added to urls.
    Returns 'linked', 'removed' or None (nothing changed)."""
    media = main.MEDIA[mediatype]
    dbid = item.get(media['id'])
    real = decode_art((item.get('art') or {}).get('thumb', ''))
    if not real or not dbid:
        return None
    urls.add(real)
    video = item.get('file') or ''
    local = local_thumb(video)
    own_copy = os.path.normcase(os.path.normpath(real)).startswith(copies)
    # a -thumb file in the video's own folder (web URLs give None here)
    video_dir = (main.split_media_path(video) or ('',))[0].lower()
    image_parts = main.split_media_path(real)
    is_local = (bool(image_parts) and image_parts[0].lower() == video_dir and
                real.lower().endswith(LOCAL_THUMB_ENDINGS))
    if not (own_copy or is_local):
        return None  # a web image or other artwork: not ours to change
    if local:
        urls.add(local)
        if real != local and main.jsonrpc(media['set'], {
                media['id']: dbid, 'art': {'thumb': local}}) is not None:
            return 'linked'
        return None
    if main.jsonrpc(media['set'], {media['id']: dbid, 'art': {'thumb': None}}) is not None:
        return 'removed'
    return None


def copies_folder(addon):
    copies = os.path.join(xbmcvfs.translatePath(addon.getAddonInfo('profile')), 'thumbs')
    return os.path.normcase(os.path.normpath(copies)) + os.sep


def relink_library(addon, mediatype):
    """relink_item for every music video / TV episode in the library.
    Returns (image URLs to un-cache, number linked, number removed)."""
    method, key = LISTS[mediatype]
    copies = copies_folder(addon)
    res = main.jsonrpc(method, {'properties': ['art', 'file']})
    urls = set()
    counts = {'linked': 0, 'removed': 0}
    for item in (res or {}).get(key) or []:
        done = relink_item(item, mediatype, copies, urls)
        if done:
            counts[done] += 1
    main.log('clear cache (%s): %d pointed at -thumb files, %d thumbnails removed'
             % (mediatype, counts['linked'], counts['removed']))
    return urls, counts['linked'], counts['removed']


def open_video():
    """(mediatype, dbid, path) of the video that is playing (e.g. in the
    picker); mediatype is main.FILE for a file that is not in the library.
    None when no video is open."""
    player = xbmc.Player()
    try:
        if not player.isPlayingVideo():
            return None
        path = player.getPlayingFile()
    except RuntimeError:
        return None
    res = main.jsonrpc('Player.GetItem', {'playerid': 1, 'properties': ['file']})
    item = (res or {}).get('item') or {}
    kind, dbid = item.get('type'), item.get('id') or 0
    if kind in main.MEDIA and dbid > 0:
        return kind, dbid, path
    return main.FILE, 0, path


def remove_cached(urls, addon, L):
    """Remove Kodi's cached copies of these images; returns how many."""
    res = main.jsonrpc('Textures.GetTextures', {'properties': ['url']})
    ids = [t['textureid'] for t in (res or {}).get('textures', []) if t.get('url') in urls]
    progress = xbmcgui.DialogProgress()
    progress.create(addon.getAddonInfo('name'), L(30036))
    removed = 0
    try:
        for n, tid in enumerate(ids):
            if progress.iscanceled():
                break
            progress.update(int(100 * n / max(len(ids), 1)))
            if main.jsonrpc('Textures.RemoveTexture', {'textureid': tid}) is not None:
                removed += 1
    finally:
        progress.close()
    main.refresh_widgets()
    xbmc.executebuiltin('Container.Refresh')
    return removed


LIBRARY_THUMBS = (('VideoLibrary.GetMusicVideos', 'musicvideos'),
                  ('VideoLibrary.GetEpisodes', 'episodes'),
                  ('VideoLibrary.GetMovies', 'movies'))


def plain_file_thumbs():
    """Images Kodi has cached that look like a plain video file's thumbnail:
    a <video>-thumb image (or .tbn) that no library item uses as its
    thumbnail. Only Kodi's JSON-RPC interface is used."""
    res = main.jsonrpc('Textures.GetTextures', {'properties': ['url']})
    cached = {t.get('url') for t in (res or {}).get('textures', []) if t.get('url')}
    candidates = {u for u in cached if u.lower().endswith(LOCAL_THUMB_ENDINGS)}
    if not candidates:
        return set()
    used = set()
    for method, key in LIBRARY_THUMBS:
        res = main.jsonrpc(method, {'properties': ['art']})
        for item in (res or {}).get(key) or []:
            real = decode_art((item.get('art') or {}).get('thumb', ''))
            if real:
                used.add(real)
    return candidates - used


def clear_cache(addon, L, kind='files'):
    """Forget Kodi's cached copies of thumbnails, so Kodi reads each image
    file again the next time it is shown (e.g. after you replaced a
    <video>-thumb.jpg yourself). The images themselves are not touched.

    kind 'files':       plain video files (Videos > Files, not in the
                        library): the <video>-thumb images that no library
                        item uses (see plain_file_thumbs)
    kind 'musicvideo' / 'episode': the thumbnails of the music videos / TV
                        episodes in the library; they also follow the -thumb
                        files next to the videos (see relink_item). Other
                        artwork and movies are left alone."""
    name = addon.getAddonInfo('name')
    dialog = xbmcgui.Dialog()
    question = {'musicvideo': 30063, 'episode': 30066}.get(kind, 30035)
    if not dialog.yesno(name, L(question)):
        return
    linked = art_removed = 0
    if kind in LISTS:
        urls, linked, art_removed = relink_library(addon, kind)
    else:
        urls = plain_file_thumbs()
    message = L(30037) % remove_cached(urls, addon, L)
    if kind in LISTS:
        message += '[CR]' + L({'musicvideo': 30064, 'episode': 30067}[kind]) % (linked, art_removed)
    dialog.ok(name, message)


def clear_open(addon, L):
    """Clear the cached thumbnail of the open video only (as above, for
    whatever kind of video it is)."""
    name = addon.getAddonInfo('name')
    dialog = xbmcgui.Dialog()
    video = open_video()
    if not video:
        dialog.ok(name, L(30070))
        return
    mediatype, dbid, path = video
    title = os.path.basename(path)
    if not dialog.yesno(name, L(30069) % title):
        return
    urls = set()
    done = None
    if mediatype in LISTS:
        media = main.MEDIA[mediatype]
        res = main.jsonrpc(media['get'], {media['id']: dbid, 'properties': ['art', 'file']})
        item = (res or {}).get(media['result']) or {}
        item.setdefault(media['id'], dbid)
        done = relink_item(item, mediatype, copies_folder(addon), urls)
    elif mediatype == main.FILE:
        # Kodi shows a plain file's <video>-thumb image (also forget the
        # cached copy of one that was deleted, so Kodi stops showing it)
        parts = main.split_media_path(path)
        if parts:
            urls = {parts[0] + parts[1] + ending for ending in LOCAL_THUMB_ENDINGS}
    else:  # e.g. a movie: just its thumbnail's cached copy
        media = main.MEDIA[mediatype]
        res = main.jsonrpc(media['get'], {media['id']: dbid, 'properties': ['art']})
        real = decode_art(((res or {}).get(media['result']) or {}).get('art', {}).get('thumb', ''))
        if real:
            urls.add(real)
    message = L(30037) % remove_cached(urls, addon, L)
    if done == 'linked':
        message += '[CR]' + L(30072)
    elif done == 'removed':
        message += '[CR]' + L(30073)
    dialog.ok(name, message)


def run(action):
    addon = xbmcaddon.Addon(main.ADDON_ID)
    L = addon.getLocalizedString
    from .picker import BUSY_PROP
    home = xbmcgui.Window(10000)
    home.setProperty(BUSY_PROP, '1')  # the picker hides while this runs
    try:
        if action == 'clearcache':
            clear_cache(addon, L)
        elif action == 'clearcache_mv':
            clear_cache(addon, L, 'musicvideo')
        elif action == 'clearcache_ep':
            clear_cache(addon, L, 'episode')
        elif action == 'clearcache_open':
            clear_open(addon, L)
        elif action in ('folderzip', 'folderrestore'):
            from . import folderzip
            folderzip.run('restore' if action == 'folderrestore' else 'backup')
    finally:
        home.clearProperty(BUSY_PROP)
