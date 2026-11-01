# -*- coding: utf-8 -*-
"""Kodi subtitle entry point (Kodi 19+, Python 3)."""
import os
import sys
import tempfile
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

ADDON = xbmcaddon.Addon()
from thunder import SubtitleError, cid_hash, search_all_subtitles, download_subtitles


def notify(message_id):
    xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'),
                                ADDON.getLocalizedString(message_id),
                                xbmcgui.NOTIFICATION_INFO)


def info_label(name):
    value = xbmc.getInfoLabel(name)
    return value.strip() if isinstance(value, str) else ''


def search_names(path, manual_name=None):
    if manual_name is not None:
        return [manual_name] if manual_name.strip() else []
    # Decode only the basename sent to the name API. Kodi VFS receives the
    # original URI, including percent escapes, in the file-reading path.
    name = unquote(urlsplit(path.split('|', 1)[0]).path).replace('\\', '/').rsplit('/', 1)[-1]
    names = [name] if name else []
    show = info_label('VideoPlayer.TVShowTitle')
    season, episode = info_label('VideoPlayer.Season'), info_label('VideoPlayer.Episode')
    if show:
        if season.isdigit() and episode.isdigit():
            names.append('%s S%02dE%02d' % (show, int(season), int(episode)))
    else:
        year = info_label('VideoPlayer.Year')
        year = ' ' + year if year.isdigit() and len(year) == 4 else ''
        for field in ('VideoPlayer.OriginalTitle', 'VideoPlayer.Title'):
            title = info_label(field)
            if title:
                names.append(title + year)
    return names


def search(handle, manual_name=None):
    try:
        path = xbmc.Player().getPlayingFile()
    except RuntimeError:
        path = ''
    if path.startswith('stack://'):
        path = path[8:].split(' , ')[0]
    # Preserve percent escapes: the VFS owns URI decoding, including SMB URLs.
    cid = None
    if path:
        try:
            with xbmcvfs.File(path, 'rb') as stream:
                cid = cid_hash(stream)
        except Exception:
            # Streams without random access can still use name lookup.
            pass
    names = search_names(path, manual_name)
    if not cid and not any(names):
        raise SubtitleError('No readable file or search name', 32013)
    subtitles = search_all_subtitles(cid, names, monitor=xbmc.Monitor())
    if not subtitles:
        notify(32010)
    for sub in subtitles:
        language = sub.get('language', '').lower()
        english = language in ('英语', '英語', 'english', 'eng', 'en')
        item = xbmcgui.ListItem(label='English' if english else 'Chinese', label2=sub['sname'])
        item.setArt({'icon': '0', 'thumb': 'en' if english else 'zh'})
        item.setProperty('sync', 'true' if 'CID' in sub.get('origin', 'CID') else 'false')
        item.setProperty('hearing_imp', 'false')
        query = urlencode({'action': 'download', 'filename': sub['surl'],
                           'name': sub['sname']})
        xbmcplugin.addDirectoryItem(handle, 'plugin://{}/?{}'.format(
            ADDON.getAddonInfo('id'), query), item, False)


def download(handle, params):
    profile = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
    os.makedirs(profile, exist_ok=True)
    # Each download owns its directory; searching never deletes an active subtitle.
    with tempfile.TemporaryDirectory(prefix='thunder-', dir=profile) as temp:
        paths = download_subtitles(params.get('filename', ''), temp,
                                   params.get('name', ''))
        if len(paths) > 1:
            choice = xbmcgui.Dialog().select(ADDON.getLocalizedString(32006),
                                             [os.path.basename(p) for p in paths])
            if choice < 0:
                return
            path = paths[choice]
        else:
            path = paths[0]
        if ADDON.getSetting('transUTF8') == 'true':
            from thunder import convert_encoding
            convert_encoding(path, ADDON.getSetting('transJianFan'))
        # Keep the chosen file available after the invocation returns.
        import shutil
        import uuid
        destination = os.path.join(profile, uuid.uuid4().hex + os.path.splitext(path)[1])
        shutil.copyfile(path, destination)
    item = xbmcgui.ListItem(label=destination)
    xbmcplugin.addDirectoryItem(handle, destination, item, False)


def main(argv=None):
    argv = sys.argv if argv is None else argv
    if len(argv) < 2:
        return
    handle = int(argv[1])
    success = True
    try:
        params = dict(parse_qsl(argv[2].lstrip('?'), keep_blank_values=True)) if len(argv) > 2 else {}
        action = params.get('action')
        if action == 'search':
            search(handle)
        elif action == 'manualsearch':
            name = params.get('searchstring', '').strip()
            if not name:
                name = xbmcgui.Dialog().input(ADDON.getLocalizedString(32011),
                                             defaultt=info_label('VideoPlayer.OriginalTitle') or info_label('VideoPlayer.Title'))
            if isinstance(name, str) and name.strip():
                search(handle, name.strip())
        elif action == 'download':
            download(handle, params)
    except Exception as exc:
        success = False
        # Exception messages may contain media credentials or signed download URLs.
        xbmc.log('{}: {} ({})'.format(ADDON.getAddonInfo('id'),
                 'subtitle operation failed', type(exc).__name__), xbmc.LOGDEBUG)
        notify(exc.message_id if isinstance(exc, SubtitleError) else 32012)
    finally:
        xbmcplugin.endOfDirectory(handle, succeeded=success)


if __name__ == '__main__':
    main()
