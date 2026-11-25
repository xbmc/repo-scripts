"""Settings actions for the open video's folder:

- backup:  put the thumbnail images (<video>-thumb.jpg/.png/..., .tbn) into a
           "Thumbnails backup <date time>.zip" in that same folder
- restore: put the images from such a ZIP back into the folder

Only files named "<anything>-thumb.<image extension>" (or .tbn) are included;
videos, .nfo files and other pictures are left out. Sub-folders are not
included. Both show a window with the folder, the ZIP and the file list first,
and only start when "Start" is pressed.
"""
import os
import time
import zipfile

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from . import main

THUMB_EXTS = ('.jpg', '.jpeg', '.png', '.tbn', '.webp')


def is_thumbnail(name):
    base, ext = os.path.splitext(name.lower())
    if ext == '.tbn':  # <video>.tbn is Kodi's old thumbnail format
        return True
    return ext in THUMB_EXTS and base.endswith('-thumb')


def open_video_folder():
    """Folder of the video that is open (e.g. in the picker), or None."""
    player = xbmc.Player()
    try:
        if not player.isPlayingVideo():
            return None
        parts = main.split_media_path(player.getPlayingFile())
    except RuntimeError:
        return None
    return parts[0] if parts else None


def choose_folder(L):
    """The open video's folder; when no video is open (settings opened from
    the add-on page), ask for one. None if cancelled."""
    folder = open_video_folder()
    if not folder:
        folder = xbmcgui.Dialog().browse(0, L(30046), 'files')
        if not folder:
            return None
        if not folder.endswith(('/', '\\')):
            folder += '/' if '/' in folder else os.sep
    return folder


# shared with the picker: it hides while BUSY is set and closes on EXIT
from .picker import BUSY_PROP, EXIT_PROP  # noqa: E402


def run(action='backup'):
    addon = xbmcaddon.Addon(main.ADDON_ID)
    home = xbmcgui.Window(10000)
    home.setProperty(BUSY_PROP, '1')
    try:
        folder = choose_folder(addon.getLocalizedString)
        if not folder:
            return
        if action == 'restore':
            done = restore_folder(folder, addon)
        else:
            done = zip_folder(folder, addon)
        if done:  # Start was pressed: leave the thumbnail picker too
            home.setProperty(EXIT_PROP, '1')
    finally:
        home.clearProperty(BUSY_PROP)


ZIP_XML = 'script-framethumb-zip.xml'
START, CANCEL, FILE_LIST = 10, 11, 3


class ZipDialog(xbmcgui.WindowXMLDialog):
    """Heading, an explanation line, the file list, and Start / Cancel
    buttons. self.start is True when Start was pressed."""

    def setup(self, heading, info, start_label, items):
        from .picker import DEFAULT_FOCUS, skin_focus_color
        self.items = items
        self.start = False
        try:
            focus = skin_focus_color()
        except Exception:
            focus = DEFAULT_FOCUS
        self.setProperty('focus_color', focus)
        self.setProperty('heading', heading)
        self.setProperty('save_as', info)
        self.setProperty('start_label', start_label)

    def onInit(self):
        lst = self.getControl(FILE_LIST)
        lst.reset()
        lst.addItems(self.items)
        self.setFocusId(START)

    def onClick(self, control_id):
        if control_id == START:
            self.start = True
            self.close()
        elif control_id == CANCEL:
            self.close()

    def onAction(self, action):
        if action.getId() in (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK):
            self.close()


def confirm(addon, heading, info, start_label, items):
    """Show what will happen; True when Start is pressed."""
    win = ZipDialog(ZIP_XML, addon.getAddonInfo('path'), 'Default', '1080i')
    win.setup(heading, info, start_label, items)
    win.doModal()
    start = win.start
    del win
    return start


def list_files(folder):
    try:
        return xbmcvfs.listdir(folder)[1]
    except Exception:
        return []


def temp_path(addon, kind):
    workdir = os.path.join(xbmcvfs.translatePath(addon.getAddonInfo('profile')), 'tmp')
    os.makedirs(workdir, exist_ok=True)
    return os.path.join(workdir, '%s-%d.zip' % (kind, int(time.time() * 1000)))


def remove(path):
    try:
        os.remove(path)
    except OSError:
        pass


# ---- backup ---------------------------------------------------------------
def zip_folder(folder, addon):
    L = addon.getLocalizedString
    name = addon.getAddonInfo('name')
    dialog = xbmcgui.Dialog()
    thumbs = sorted(f for f in list_files(folder) if is_thumbnail(f))
    if not thumbs:
        dialog.notification(name, L(30041), xbmcgui.NOTIFICATION_INFO, 4000)
        return
    zip_name = '%s %s.zip' % (L(30044), time.strftime('%Y-%m-%d %H-%M-%S'))
    if not confirm(addon, L(30050) % folder, L(30049) % (len(thumbs), zip_name),
                   L(30048), thumbs):
        return

    tmp = temp_path(addon, 'folderzip')
    added = 0
    progress = xbmcgui.DialogProgressBG()
    progress.create(name, L(30045))
    try:
        # images are already compressed: store them as they are
        with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_STORED) as zf:
            for n, fname in enumerate(thumbs):
                progress.update(int(100 * n / len(thumbs)), message=fname)
                f = xbmcvfs.File(folder + fname)
                try:
                    data = bytes(f.readBytes())
                finally:
                    f.close()
                if data:
                    zf.writestr(fname, data)
                    added += 1
        ok = added and xbmcvfs.copy(tmp, folder + zip_name) and xbmcvfs.exists(folder + zip_name)
    except Exception as e:
        main.log('folder thumbnail ZIP failed: %s' % e, xbmc.LOGERROR)
        ok = False
    finally:
        progress.close()
        remove(tmp)
    if ok:
        dialog.notification(name, L(30042) % (added, zip_name), xbmcgui.NOTIFICATION_INFO, 5000)
    else:
        dialog.notification(name, L(30043), xbmcgui.NOTIFICATION_ERROR)
    return True


# ---- restore --------------------------------------------------------------
def backup_zips(folder, L):
    """The folder's backup ZIPs, newest first (the date is in the name)."""
    prefix = L(30044).lower()
    zips = [f for f in list_files(folder)
            if f.lower().endswith('.zip') and f.lower().startswith(prefix)]
    return sorted(zips, reverse=True)


def zip_thumbnails(zf):
    """Names of the thumbnail images in the ZIP. Entries inside folders (or
    with odd paths) are skipped, so nothing is written outside the folder."""
    names = []
    for info in zf.infolist():
        n = info.filename
        if info.is_dir() or '/' in n or '\\' in n or n in ('.', '..') or ':' in n:
            continue
        if is_thumbnail(n):
            names.append(n)
    return sorted(names)


def restore_folder(folder, addon):
    L = addon.getLocalizedString
    name = addon.getAddonInfo('name')
    dialog = xbmcgui.Dialog()
    zips = backup_zips(folder, L)
    if not zips:
        dialog.notification(name, L(30052), xbmcgui.NOTIFICATION_INFO, 4000)
        return
    if len(zips) == 1:
        zip_name = zips[0]
    else:
        choice = dialog.select(L(30053), zips)
        if choice < 0:
            return
        zip_name = zips[choice]

    tmp = temp_path(addon, 'restore')
    started = False
    try:
        # read a local copy (the folder may be a network share)
        if not xbmcvfs.copy(folder + zip_name, tmp):
            raise IOError('could not copy %s' % zip_name)
        with zipfile.ZipFile(tmp) as zf:
            thumbs = zip_thumbnails(zf)
            if not thumbs:
                dialog.notification(name, L(30054), xbmcgui.NOTIFICATION_INFO, 4000)
                return
            existing = {f.lower() for f in list_files(folder)}
            replaced = sum(1 for t in thumbs if t.lower() in existing)
            info = L(30051) % (len(thumbs), zip_name, replaced)
            if not confirm(addon, L(30055) % folder, info, L(30056), thumbs):
                return False
            started = True
            restored = write_thumbnails(zf, thumbs, folder, name, L)
    except Exception as e:
        main.log('restoring %s failed: %s' % (zip_name, e), xbmc.LOGERROR)
        dialog.notification(name, L(30058), xbmcgui.NOTIFICATION_ERROR)
        return started
    finally:
        remove(tmp)

    # Kodi shows its cached copy of an image until that copy is removed
    for t in thumbs:
        main.remove_cached_texture(folder + t)
    try:
        update_library(folder, thumbs, addon)
    except Exception as e:
        main.log('updating library art after restore failed: %s' % e, xbmc.LOGERROR)
    main.refresh_widgets()
    xbmc.executebuiltin('Container.Refresh')
    if restored == len(thumbs):
        dialog.notification(name, L(30057) % restored, xbmcgui.NOTIFICATION_INFO, 5000)
    else:
        dialog.notification(name, L(30059) % (restored, len(thumbs)), xbmcgui.NOTIFICATION_ERROR)
    return True


# movies are left out: they show posters, not thumbnails
LIBRARY_LISTS = (('musicvideo', 'VideoLibrary.GetMusicVideos', 'musicvideos'),
                 ('episode', 'VideoLibrary.GetEpisodes', 'episodes'))


def video_base(thumb):
    """'Song-thumb.jpg' -> 'song', 'Song.tbn' -> 'song'."""
    base, ext = os.path.splitext(thumb)
    if ext.lower() != '.tbn' and base.lower().endswith('-thumb'):
        base = base[:-len('-thumb')]
    return base.lower()


def update_library(folder, thumbs, addon):
    """Point the library items of this folder at the restored images.

    Items changed with this add-on show its own uniquely named copy in
    userdata, not <video>-thumb.jpg, so putting that file back changes
    nothing on screen. Each matching item gets a new copy of the restored
    image (a new name, so Kodi does not reuse the old picture it has in
    memory) and its thumbnail is set to it."""
    by_base = {video_base(t): t for t in thumbs}
    profile = xbmcvfs.translatePath(addon.getAddonInfo('profile'))
    updated = 0
    for mediatype, method, key in LIBRARY_LISTS:
        media = main.MEDIA[mediatype]
        res = main.jsonrpc(method, {
            'properties': ['file'],
            'filter': {'field': 'path', 'operator': 'startswith', 'value': folder}})
        for item in (res or {}).get(key) or []:
            video = item.get('file') or ''
            parts = main.split_media_path(video)
            if not parts or parts[0].lower() != folder.lower():
                continue  # in a sub-folder
            thumb = by_base.get(parts[1].lower())
            dbid = item.get(media['id'])
            if not thumb or not dbid:
                continue
            ext = os.path.splitext(thumb)[1].lower()
            ext = '.jpg' if ext in ('.tbn', '.jpeg') else ext
            dest = main.save_image(folder + thumb, mediatype, dbid, video, 'thumb', 0,
                                   profile, local_png=False, ext=ext)
            if dest and main.jsonrpc(media['set'], {media['id']: dbid,
                                                    'art': {'thumb': dest}}) is not None:
                updated += 1
    main.log('restore: set the restored thumbnail on %d library items' % updated)
    return updated


def write_thumbnails(zf, thumbs, folder, name, L):
    restored = 0
    progress = xbmcgui.DialogProgressBG()
    progress.create(name, L(30060))
    try:
        for n, fname in enumerate(thumbs):
            progress.update(int(100 * n / len(thumbs)), message=fname)
            data = zf.read(fname)
            f = xbmcvfs.File(folder + fname, 'w')
            try:
                ok = f.write(bytearray(data))
            finally:
                f.close()
            if ok:
                restored += 1
            else:
                main.log('could not write %s' % (folder + fname), xbmc.LOGERROR)
    finally:
        progress.close()
    return restored
