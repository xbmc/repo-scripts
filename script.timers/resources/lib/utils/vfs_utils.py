import os
import re

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
from resources.lib.player.mediatype import AUDIO, PICTURE, TYPES, VIDEO
from resources.lib.player.playlist import PlayList

_PVR_CHANNELS_MATCHER = "^pvr://channels/.*\.pvr$"
_PVR_TV_CHANNELS_MATCHER = "^pvr://channels/tv/.*\.pvr$"
_PVR_RADIO_CHANNELS_MATCHER = "^pvr://channels/radio/.*\.pvr$"
_PVR_RECORDINGS_MATCHER = "^pvr://recordings/.*\.pvr$"
_PVR_PREFIX = "pvr://"
_MUSIC_DB_PREFIX = "musicdb://"
_VIDEO_DB_PREFIX = "videodb://"
_AUDIO_PLUGIN_PREFIX = "plugin://plugin.audio."
_VIDEO_PLUGIN_PREFIX = "plugin://plugin.video."
_URI_MATCHER = "^[a-z]+://.+$"
_FAVOURITES_MATCHER = "^favourites://(PlayMedia|RunScript)\(%22(.+)%22\)/$"
_SCRIPT_MATCHER = "^((script|plugin)://)?script\..+$"

_PLAYLIST_TYPES = [".m3u", ".m3u8", ".pls"]

_EXTERNAL_PATHS = ["http://", "https://"]


def scan_dirs_with_filecount(path: str) -> 'tuple[int,list[tuple[str,int]]]':

    def _scan(path: str, result: 'list[tuple[str,int]]') -> 'tuple[int,list[tuple[str,int]]]':

        dirs, files = xbmcvfs.listdir(path)
        files_count = len(files)
        for d in dirs:
            _files_count, result = _scan("%s%s/" % (path, d), result=result)
            files_count += _files_count

        result.append((path, files_count))

        return files_count, result

    result = list()
    return _scan(path, result=result)


def is_folder(path: str) -> bool:

    dirs, files = xbmcvfs.listdir(path)
    return len(dirs) > 0 or len(files) > 0


def is_playlist(path: str) -> bool:

    ext = get_file_extension(path)
    if not ext:
        return False

    else:
        return ext in _PLAYLIST_TYPES


def is_external(path: str) -> bool:

    for ext in _EXTERNAL_PATHS:
        if path.startswith(ext):
            return True

    return False


def is_uri(path: str) -> bool:

    return None != re.match(_URI_MATCHER, path)


def is_musicdb(path: str) -> bool:

    return path.startswith(_MUSIC_DB_PREFIX)


def is_videodb(path: str) -> bool:

    return path.startswith(_VIDEO_DB_PREFIX)


def is_audio_plugin(path: str) -> bool:

    return path.startswith(_AUDIO_PLUGIN_PREFIX)


def is_video_plugin(path: str) -> bool:

    return path.startswith(_VIDEO_PLUGIN_PREFIX)


def is_script(path: str) -> bool:

    return None != re.match(_SCRIPT_MATCHER, path)


def is_pvr(path: str) -> bool:

    return path.startswith(_PVR_PREFIX)


def is_pvr_channel(path: str) -> bool:

    return None != re.match(_PVR_CHANNELS_MATCHER, path)


def is_pvr_tv_channel(path: str) -> bool:

    return None != re.match(_PVR_TV_CHANNELS_MATCHER, path)


def is_pvr_radio_channel(path: str) -> bool:

    return None != re.match(_PVR_RADIO_CHANNELS_MATCHER, path)


def is_pvr_recording(path: str) -> bool:

    return None != re.match(_PVR_RECORDINGS_MATCHER, path)


def is_favourites(path: str) -> bool:

    return None != re.match(_FAVOURITES_MATCHER, path)


def is_supported_media(path: str) -> bool:

    return get_media_type(path) != None


def get_favourites_target(path: str) -> str:

    m = re.match(_FAVOURITES_MATCHER, path)
    if not m:
        return None

    pattern = re.compile("(%[0-9a-f]{2})", re.S)
    return re.sub(pattern, lambda match: bytes.fromhex(match.group()[1:]).decode("latin1"), m.groups()[1])


def get_media_type(path: str) -> str:

    ext = get_file_extension(path)
    if is_musicdb(path) or is_audio_plugin(path) or is_pvr_radio_channel(path) or is_playlist(path) or ext and (ext + "|") in xbmc.getSupportedMedia("music"):
        return AUDIO

    elif is_videodb(path) or is_video_plugin(path) or is_pvr(path) or ext and (ext + "|") in xbmc.getSupportedMedia("video"):
        return VIDEO

    elif ext and (ext + "|") in xbmc.getSupportedMedia("picture"):
        return PICTURE

    else:
        paths, type = get_files_and_type(
            path, limit=100, no_leaves=True)
        return type


def get_file_name(path: str) -> str:

    if path.endswith("/"):
        return None

    m = re.match("^.*/([^/.]+)(\.[^\.]+)?$", "/%s" % path)
    if not m:
        return None

    else:
        return m.groups()[0]


def get_file_extension(path: str) -> str:

    m = re.match("^.+(\.[^\.]+)$", path.lower())
    if not m:
        return None

    else:
        return m.groups()[0]


def build_path_to_ressource(path: str, file: str) -> str:

    if is_musicdb(path):
        return "%s%s" % (_MUSIC_DB_PREFIX, file)

    elif is_videodb(path):
        return "%s%s" % (_VIDEO_DB_PREFIX, file)

    else:
        return "%s%s" % (path, file)


def has_items_in_path(path: str) -> bool:

    return len(scan_item_paths(path, limit=1)) > 0


def build_playlist(path: str, label: str) -> 'PlayList':

    if has_items_in_path(path):
        paths, type = get_files_and_type(path)
        return convert_to_playlist(paths, type=type, label=label)

    else:
        type = get_media_type(path)
        return convert_to_playlist([path], type=type, label=label)


def convert_to_playlist(paths: 'list[str]', type=VIDEO, label="") -> 'PlayList':

    _type_id = TYPES.index(type or VIDEO)
    playlist = PlayList(_type_id)
    playlist.clear()

    for path in paths:
        label = label if label and len(paths) == 1 else get_file_name(path)
        li = xbmcgui.ListItem(label=label, path=path)
        playlist.add(url=path, listitem=li)
        if is_pvr(path) or is_audio_plugin(path) or is_video_plugin(path):
            playlist.clear()
            playlist.directUrl = path
            break

    return playlist


def scan_item_paths(path: str, limit=None) -> 'list[str]':

    def _scan(path: str) -> 'list[str]':

        _result = list()

        dirs, files = xbmcvfs.listdir(path)
        for d in dirs:
            if d != "":
                _result.extend(_scan("%s%s/" % (path, d)))

        for f in files:
            if not is_supported_media(f):
                continue

            if (not limit or len(_result) < limit):
                _result.append(build_path_to_ressource(path, f))

        return _result

    if not path or is_pvr(path) or is_audio_plugin(path) or is_video_plugin(path):
        files = list()

    elif is_playlist(path):
        files = [path]

    else:
        files = _scan(path)
        files.sort()

    return files


def get_items_group_by_mediatype(path: str, limit=None) -> 'tuple[list[str], list[str], list[str], list[str]]':

    def _scan(path: str) -> 'tuple[list[str],list[str],list[str]]':

        _audio_files = list()
        _video_files = list()
        _pictures = list()

        dirs, files = xbmcvfs.listdir(path)
        for d in dirs:
            if d != "":
                _a, _v, _p = _scan("%s%s/" % (path, d))
                _audio_files.extend(_a)
                _video_files.extend(_v)
                _pictures.extend(_p)

        for f in files:
            _path = build_path_to_ressource(path, f)

            if (limit and (len(_audio_files) + len(_video_files) + len(_pictures)) >= limit):
                return _audio_files, _video_files, _pictures

            media_type = get_media_type(_path)
            if media_type == AUDIO:
                _audio_files.append(_path)

            elif media_type == VIDEO:
                _video_files.append(_path)

            elif media_type == PICTURE:
                _pictures.append(_path)

        return _audio_files, _video_files, _pictures

    if not path:
        audio_files = list()
        video_files = list()
        pictures = list()

    elif is_playlist(path):
        audio_files = [path]
        video_files = list()
        pictures = list()

    else:
        audio_files, video_files, pictures = _scan(path)
        audio_files.sort()
        video_files.sort()
        pictures.sort()

    return audio_files, video_files, pictures


def get_files_and_type(path: str, limit=None, no_leaves=False) -> 'tuple[list[str],str]':

    if has_items_in_path(path):
        a, v, p = get_items_group_by_mediatype(path, limit=limit)
    elif not no_leaves:
        return [path], get_media_type(path)
    else:
        return [path], None

    size = 0
    files = None
    type = -1
    for i, l in enumerate([a, v, p]):
        if len(l) > size:
            size = len(l)
            files = l
            type = i

    return files, TYPES[type] if type >= 0 else None


def get_longest_common_path(files: 'list[str]') -> str:

    if not files:
        return None

    elif len(files) == 1:
        return files[0]

    longest_common_path = None
    sep = ""
    for file in files:
        if sep == "":
            sep = "/" if is_uri(file) else os.sep
        breadcrumb = file.split(sep)[:-1]
        if not longest_common_path:
            longest_common_path = breadcrumb
        else:
            _idx = -1
            for i in range(min(len(breadcrumb), len(longest_common_path))):
                if breadcrumb[i] == longest_common_path[i]:
                    _idx = i
                else:
                    break

            if _idx > 0:
                longest_common_path = longest_common_path[:_idx + 1]
            else:
                return None

    return sep.join(longest_common_path) + sep if longest_common_path else None


def get_asset_path(asset: str) -> str:

    addon = xbmcaddon.Addon()
    return os.path.join(xbmcvfs.translatePath(addon.getAddonInfo('path')),
                        "resources",
                        "assets", asset)
