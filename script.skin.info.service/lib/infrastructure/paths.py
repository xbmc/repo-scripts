"""VFS path helpers and artwork paths that follow Kodi's naming conventions."""
from __future__ import annotations

import threading
import urllib.parse

import xbmc
import xbmcgui
import xbmcvfs
from typing import Any, Optional, Tuple, Dict, List, Set

from lib.kodi.client import ADDON, request, get_library_items


def vfs_get_separator(path: str) -> str:
    """Detect separator used in path (backslash for Windows/SMB, forward slash otherwise)."""
    return '\\' if '\\' in path else '/'


def vfs_rstrip_sep(path: str) -> str:
    """Strip trailing separators from path."""
    return path.rstrip('/\\')


def vfs_ensure_dir_slash(path: str) -> str:
    """Ensure path has trailing separator. Required for xbmcvfs.exists() directory checks."""
    if not path:
        return path
    path = vfs_rstrip_sep(path)
    sep = vfs_get_separator(path)
    return path + sep


def vfs_split(path: str) -> Tuple[str, str]:
    """VFS-aware `os.path.split`. Handles both `/` and `\\`, strips trailing separators first."""
    path = vfs_rstrip_sep(path)
    if not path:
        return ('', '')

    last_sep = -1
    for i in range(len(path) - 1, -1, -1):
        if path[i] in '/\\':
            last_sep = i
            break

    if last_sep == -1:
        return ('', path)

    return (path[:last_sep], path[last_sep + 1:])


def vfs_dirname(path: str) -> str:
    """Get parent directory of path, VFS-aware."""
    return vfs_split(path)[0]


def vfs_basename(path: str) -> str:
    """Get filename/last component of path, VFS-aware."""
    return vfs_split(path)[1]


def vfs_splitext(path: str) -> Tuple[str, str]:
    """VFS-aware `os.path.splitext`. Only splits on the filename part, never on directory dots."""
    dir_part, filename = vfs_split(path)

    if not filename:
        return (path, '')

    dot_pos = filename.rfind('.')
    if dot_pos <= 0:
        return (path, '')

    ext = filename[dot_pos:]
    base = filename[:dot_pos]

    if dir_part:
        sep = vfs_get_separator(path)
        return (dir_part + sep + base, ext)
    return (base, ext)


def vfs_join(base: str, *parts: str) -> str:
    """Join path components using the separator from the base path."""
    if not base:
        return '/'.join(parts)

    sep = vfs_get_separator(base)
    result = vfs_rstrip_sep(base)

    for part in parts:
        if part:
            result = result + sep + part

    return result


def get_disc_file(path: str) -> str:
    """Get the index.bdmv or ISO a `bluray://` path plays from; any other path is returned as-is."""
    if not path.startswith('bluray://'):
        return path
    host = urllib.parse.unquote(path[len('bluray://'):].split('/', 1)[0])
    if host.startswith('udf://'):
        return urllib.parse.unquote(host[len('udf://'):].split('/', 1)[0])
    return vfs_join(host, 'BDMV', 'index.bdmv')


def build_actors_folder_path(media_type: str, file_path: str,
                             show_path: Optional[str] = None) -> Optional[str]:
    """Build the `.actors` folder path Kodi's scanner reads; an episode's sits at the show root."""
    if media_type == "movie":
        if not file_path:
            return None
        parent = vfs_dirname(get_disc_file(file_path))
        # Kodi reads a bluray:// item's actors beside BDMV, an index.bdmv item's inside it
        if file_path.startswith('bluray://') and vfs_basename(parent) == 'BDMV':
            parent = vfs_dirname(parent)
        return vfs_join(parent, ".actors")
    elif media_type in ("tvshow", "episode"):
        base_path = show_path if show_path else file_path
        if not base_path:
            return None
        base_path = base_path.rstrip("/\\")
        return vfs_join(base_path, ".actors")

    return None


def get_tvshow_paths() -> Dict[int, str]:
    """Get each show's path by tvshowid, for season items queried without their parent show."""
    paths: Dict[int, str] = {}
    for show in get_library_items(media_types=['tvshow'], properties=['file']):
        show_id = show.get('tvshowid') or show.get('dbid')
        if show_id and show.get('file'):
            paths[show_id] = show['file']
    return paths


def get_album_folders(album_ids: List[int]) -> Dict[int, str]:
    """Get each album's folder by albumid, from the first song file seen per album."""
    wanted = set(album_ids)
    folders: Dict[int, str] = {}
    if not wanted:
        return folders

    page_size = 2000
    start = 0
    while True:
        resp = request("AudioLibrary.GetSongs", {
            "properties": ["file", "albumid"],
            "limits": {"start": start, "end": start + page_size},
        })
        result = (resp or {}).get("result") or {}
        songs = result.get("songs") or []
        for song in songs:
            album_id = song.get("albumid")
            if album_id in wanted and album_id not in folders and song.get("file"):
                folders[album_id] = vfs_dirname(song["file"])
        if len(folders) == len(wanted):
            break
        total = result.get("limits", {}).get("total", len(songs))
        start += page_size
        if not songs or start >= total:
            break
    return folders


class DirectoryListing:
    """Per-directory filename cache, so existence checks cost one listing instead of a stat each."""

    def __init__(self, max_dirs: int = 4096):
        self._dirs: Dict[str, Set[str]] = {}
        self.max_dirs = max_dirs

    def files(self, directory: str) -> Optional[Set[str]]:
        """Lowercased filenames in the folder; None when unlisted or empty, never cached."""
        cached = self._dirs.get(directory)
        if cached is not None:
            return cached

        try:
            _subdirs, names = xbmcvfs.listdir(vfs_ensure_dir_slash(directory))
        except Exception:
            return None

        if not names:
            return None

        listing = {name.lower() for name in names}
        if len(self._dirs) >= self.max_dirs:
            self._dirs.clear()
        self._dirs[directory] = listing
        return listing

    def note_written(self, full_path: str) -> None:
        """Record a file just created, so a later lookup in that folder sees it."""
        directory, filename = vfs_split(full_path)
        listing = self._dirs.get(directory)
        if listing is not None:
            listing.add(filename.lower())

    def find_with_extension(self, base_path: str, extensions) -> Optional[str]:
        """Find the first existing `base_path.<ext>`, falling back to a stat each when unlisted."""
        directory, filename = vfs_split(base_path)

        listing = self.files(directory) if directory else None
        if listing is not None:
            for ext in extensions:
                if (filename + '.' + ext).lower() in listing:
                    return xbmcvfs.validatePath(base_path + '.' + ext)
            return None

        for ext in extensions:
            candidate = xbmcvfs.validatePath(base_path + '.' + ext)
            if xbmcvfs.exists(candidate):
                return candidate
        return None


def use_basename_for(media_type: str, savewith_basefilename: bool) -> bool:
    """True when art saves as `<mediafile>-<type>` rather than a bare `<type>` in the folder."""
    return (media_type in ('episode', 'musicvideo')
            or (media_type == 'movie' and savewith_basefilename))


def resolve_media_file(item: Dict[str, Any],
                       album_folders: Optional[Dict[int, str]] = None,
                       tvshow_paths: Optional[Dict[int, str]] = None) -> str:
    """Resolve the `media_file` input `PathBuilder.build_path` needs; '' when the item has none."""
    file_path = item.get('file', '')
    if file_path:
        return file_path
    media_type = item.get('media_type', '')
    if media_type == 'set':
        return item.get('title', '')
    if media_type == 'artist':
        return item.get('label', '')
    if media_type == 'album' and album_folders:
        return album_folders.get(item.get('dbid', 0), '')
    if media_type == 'season' and tvshow_paths:
        return tvshow_paths.get(item.get('tvshowid', 0), '')
    return ''


class PathBuilder:
    """Build filesystem paths matching Kodi artwork naming conventions (movies, TV, music)."""

    _music_thumb_filename: Optional[str] = None
    _folder_cache: Dict[str, Optional[str]] = {}
    _folder_lock = threading.Lock()
    _artist_counts: Dict[str, int] = {}
    _artist_count_lock = threading.Lock()

    @staticmethod
    def _get_kodi_folder_setting(setting: str) -> str:
        """Read a Kodi folder-path setting value via `Settings.GetSettingValue`."""
        response = request("Settings.GetSettingValue", {"setting": setting})
        if response and "value" in response.get("result", {}):
            return response["result"]["value"]
        return ""

    @staticmethod
    def _configure_kodi_folder_setting(setting: str, heading: str, message: str,
                                       browse_heading: str) -> Optional[str]:
        """Prompt user to pick a folder, save it as a Kodi setting, return the chosen path."""
        dialog = xbmcgui.Dialog()

        if not dialog.yesno(heading, message):
            return None

        folder = dialog.browse(0, browse_heading, "files", "", False, False, "")
        if not folder or not isinstance(folder, str):
            return None

        response = request("Settings.SetSettingValue", {
            "setting": setting,
            "value": folder
        })

        if response and response.get("result") is True:
            dialog.notification(
                heading,
                ADDON.getLocalizedString(32738),
                xbmcgui.NOTIFICATION_INFO,
                3000
            )
            return folder

        dialog.ok(xbmc.getLocalizedString(257), ADDON.getLocalizedString(32739))
        return None

    @staticmethod
    def _movie_sets_folder() -> Optional[str]:
        """Configured movie sets folder, prompting once if unset."""
        return PathBuilder._resolve_named_item_folder(
            "videolibrary.moviesetsfolder",
            xbmc.getLocalizedString(20226),
            ADDON.getLocalizedString(32736),
            xbmc.getLocalizedString(20226),
        )

    @staticmethod
    def _artist_folder() -> Optional[str]:
        """Configured artist information folder, prompting once if unset."""
        return PathBuilder._resolve_named_item_folder(
            "musiclibrary.artistsfolder",
            xbmc.getLocalizedString(20223),
            ADDON.getLocalizedString(32737),
            xbmc.getLocalizedString(20223),
        )

    @staticmethod
    def prepare_named_item_folders(media_types) -> None:
        """Resolve set/artist folders up front; the prompt is modal and must not hit a worker."""
        if 'set' in media_types:
            PathBuilder._movie_sets_folder()
        if 'artist' in media_types:
            PathBuilder._artist_folder()

    @staticmethod
    def _resolve_named_item_folder(setting: str, heading: str, message: str,
                                   browse_heading: str) -> Optional[str]:
        """Get a Kodi folder setting, prompting once to configure it; a declined prompt is kept."""
        with PathBuilder._folder_lock:
            if setting in PathBuilder._folder_cache:
                return PathBuilder._folder_cache[setting]

            folder = PathBuilder._get_kodi_folder_setting(setting)
            if not folder:
                folder = PathBuilder._configure_kodi_folder_setting(
                    setting, heading, message, browse_heading
                )

            PathBuilder._folder_cache[setting] = folder
            return folder

    @staticmethod
    def _get_music_thumb_filename() -> str:
        """Return the extensionless filename Kodi expects for music thumbs (cached)."""
        if PathBuilder._music_thumb_filename is not None:
            return PathBuilder._music_thumb_filename
        # Kodi finds music thumbs only by the filenames listed in this setting
        value = PathBuilder._get_kodi_folder_setting("musiclibrary.musicthumbs")
        result = "folder"
        if value:
            first = value[0].strip() if isinstance(value, list) else value.split(",")[0].strip()
            dot = first.rfind(".")
            if dot > 0:
                result = first[:dot]
        PathBuilder._music_thumb_filename = result
        return result

    @staticmethod
    def _make_legal_filename(name: str, fallback: str = "Unknown", parent_dir: str = "") -> str:
        """Sanitize a name via `makeLegalFilename`, against the folder it will be written to."""
        if not name:
            return fallback
        # makeLegalFilename leaves a bare name unsanitized; it needs a path prefix
        full_path = vfs_join(parent_dir, name) if parent_dir else name
        sanitized = xbmcvfs.makeLegalFilename(full_path)
        sanitized = vfs_basename(sanitized)
        return sanitized if sanitized else fallback

    @staticmethod
    def _make_music_folder_name(name: str, fallback: str = "Unknown", parent_dir: str = "") -> str:
        """Like `_make_legal_filename` but collapses `" _ "` back to `"_"` for music folders."""
        sanitized = PathBuilder._make_legal_filename(name, fallback, parent_dir)
        sanitized = sanitized.replace(' _ ', '_')
        return sanitized

    @staticmethod
    def _count_library_artists(artist_name: str) -> int:
        """Count library artists sharing a name, cached per run, to decide on an MBID suffix."""
        with PathBuilder._artist_count_lock:
            cached = PathBuilder._artist_counts.get(artist_name)
        if cached is not None:
            return cached

        response = request("AudioLibrary.GetArtists", {
            "filter": {"field": "artist", "operator": "is", "value": artist_name}
        })
        count = 1
        if response and "artists" in response.get("result", {}):
            count = len(response["result"]["artists"])

        with PathBuilder._artist_count_lock:
            PathBuilder._artist_counts[artist_name] = count
        return count

    @staticmethod
    def _find_movie_root(path: str) -> str:
        """Find the folder holding a BDMV or VIDEO_TS structure, else the file's own folder."""
        dir_path = vfs_dirname(path)
        parent_dir = vfs_dirname(dir_path)

        if vfs_basename(dir_path) in ('BDMV', 'VIDEO_TS'):
            return parent_dir
        if vfs_basename(parent_dir) in ('BDMV', 'VIDEO_TS'):
            return vfs_dirname(parent_dir)
        return dir_path

    @staticmethod
    def build_path(media_type: str, media_file: str, artwork_type: str,
                   season_number: Optional[int] = None,
                   use_basename: bool = True, mbid: Optional[str] = None) -> Optional[str]:
        """Build an extensionless artwork path or None; a set or artist may prompt for a folder."""
        if not media_file:
            return None

        if media_type == 'movie':
            media_file = get_disc_file(media_file)
        base_path, ext = vfs_splitext(media_file)
        dir_path, filename = vfs_split(base_path)

        if not ext:
            dir_path = vfs_rstrip_sep(media_file)
            filename = ''

        if media_type == 'movie':
            # Kodi reads a disc's art from the disc root only
            on_disc = vfs_basename(dir_path) in ('BDMV', 'VIDEO_TS')
            if use_basename and filename and not on_disc:
                return base_path + '-' + artwork_type
            else:
                if ext:
                    movie_root = PathBuilder._find_movie_root(media_file)
                else:
                    movie_root = dir_path
                return vfs_join(movie_root, artwork_type)

        elif media_type == 'tvshow':
            return vfs_join(dir_path, artwork_type)

        elif media_type == 'season':
            if season_number is None:
                return None
            if season_number > 0:
                season_str = f"season{season_number:02d}"
            else:
                season_str = "season-specials"
            return vfs_join(dir_path, season_str + '-' + artwork_type)

        elif media_type == 'episode':
            if use_basename and filename:
                return base_path + '-' + artwork_type
            else:
                return vfs_join(dir_path, 'episode-' + artwork_type)

        elif media_type == 'musicvideo':
            if use_basename and filename:
                return base_path + '-' + artwork_type
            else:
                return vfs_join(dir_path, artwork_type)

        elif media_type == 'set':
            movie_sets_folder = PathBuilder._movie_sets_folder()
            if not movie_sets_folder:
                return None

            sanitized_title = PathBuilder._make_legal_filename(
                media_file, "Unnamed Set", movie_sets_folder
            )

            if artwork_type.startswith('set.'):
                clean_art_type = artwork_type[4:]
            else:
                clean_art_type = artwork_type

            return vfs_join(movie_sets_folder, sanitized_title, clean_art_type)

        elif media_type == 'artist':
            artist_folder = PathBuilder._artist_folder()
            if not artist_folder:
                return None

            folder_name = PathBuilder._make_music_folder_name(
                media_file, "Unknown Artist", artist_folder
            )

            if mbid and PathBuilder._count_library_artists(media_file) > 1:
                folder_name += '_' + mbid[:4]

            art_name = (
                PathBuilder._get_music_thumb_filename()
                if artwork_type == 'thumb' else artwork_type
            )
            return vfs_join(artist_folder, folder_name, art_name)

        elif media_type == 'album':
            art_name = (
                PathBuilder._get_music_thumb_filename()
                if artwork_type == 'thumb' else artwork_type
            )
            return vfs_join(vfs_rstrip_sep(media_file), art_name)

        return None
