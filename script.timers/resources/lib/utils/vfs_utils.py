import re

import xbmc
import xbmcvfs

_PVR_CHANNELS_MATCHER = "^pvr://channels/.*\.pvr$"
_PVR_RECORDINGS_MATCHER = "^pvr://recordings/.*\.pvr$"
_PVR_PREFIX = "pvr://"
_MUSIC_DB_URL_PREFIX = "musicdb://"
_VIDEO_DB_URL_PREFIX = "videodb://"

_PLAYLIST_TYPES = [".m3u", ".m3u8", ".pls"]

_AUDIO = "audio"
_VIDEO = "video"
_PICTURE = "picture"

_TYPES = [_AUDIO, _VIDEO, _PICTURE]


def is_folder(path: str) -> bool:

    dirs, files = xbmcvfs.listdir(path)
    return len(dirs) > 0 or len(files) > 0


def is_playlist(path: str) -> bool:

    ext = get_file_extension(path)
    if not ext:
        return False

    else:
        return ext in _PLAYLIST_TYPES


def is_musicdb(path: str) -> bool:

    return path.startswith(_MUSIC_DB_URL_PREFIX)


def is_videodb(path: str) -> bool:

    return path.startswith(_VIDEO_DB_URL_PREFIX)


def is_pvr(path: str) -> bool:

    return path.startswith(_PVR_PREFIX)


def is_pvr_channel(path: str) -> bool:

    return re.match(_PVR_CHANNELS_MATCHER, path)


def is_pvr_recording(path: str) -> bool:

    return re.match(_PVR_RECORDINGS_MATCHER, path)


def is_supported_media(url: str) -> bool:

    if is_pvr(url) or is_musicdb(url) or is_videodb(url):
        return True

    ext = get_file_extension(url)
    if not ext:
        return False

    else:
        return (ext + "|") in xbmc.getSupportedMedia("video") or (ext + "|") in xbmc.getSupportedMedia("music")


def build_path_to_ressource(path: str, file: str) -> str:

    if is_musicdb(path):
        return "%s%s" % (_MUSIC_DB_URL_PREFIX, file)

    elif is_videodb(path):
        return "%s%s" % (_VIDEO_DB_URL_PREFIX, file)

    else:
        return "%s%s" % (path, file)


def get_item_urls_from_path(path: str, limit=None) -> 'list[str]':

    urls = list()

    def _scan(path: str) -> None:

        if limit and len(urls) > limit:
            return

        dirs, files = xbmcvfs.listdir(path)
        for d in dirs:
            if d != "":
                _urls = _scan("%s%s/" % (path, d))
                if _urls:
                    urls.extend(_urls)

        for f in files:
            if not is_supported_media(f):
                continue

            if (not limit or len(urls) < limit):
                url = build_path_to_ressource(path, f)
                urls.append(url)

    if not path:
        pass

    elif is_playlist(path):
        urls.append(path)

    else:
        _scan(path)
        urls.sort()

    return urls


def get_file_extension(path: str) -> str:

    m = re.match("^.+(\.[^\.]+)$", path.lower())
    if not m:
        return None

    else:
        return m.groups()[0]


def has_items_in_path(path: str) -> bool:

    return len(get_item_urls_from_path(path, limit=1)) > 0


def build_playlist_from_urls(urls, type=_VIDEO) -> xbmc.PlayList:

    _type_id = _TYPES.index(type)
    playlist = xbmc.PlayList(_type_id)
    playlist.clear()

    for u in urls:
        playlist.add(u)

    return playlist


def build_playlist_from_url(url) -> xbmc.PlayList:

    if has_items_in_path(url):
        return build_playlist_from_urls(
            get_item_urls_from_path(url))
    else:
        return build_playlist_from_urls([url])
