"""Build Kodi-compliant artwork file paths following naming conventions."""
from __future__ import annotations

import threading

import xbmcgui
import xbmcvfs
from typing import Any, Optional, Tuple, Dict, List, Set

from lib.kodi.client import request, get_library_items


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
    if dot_pos <= 0:  # No dot, or dot at start (hidden file)
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


def build_actors_folder_path(media_type: str, file_path: str,
                             show_path: Optional[str] = None) -> Optional[str]:
    """Build `.actors` folder path matching Kodi's VideoInfoScanner/VideoDatabase conventions.

    Movie: parent of movie file. TV/Episode: show root (shared).
    `show_path` is required for episodes.
    """
    if media_type == "movie":
        if not file_path:
            return None
        parent = vfs_dirname(file_path)
        return vfs_join(parent, ".actors")
    elif media_type in ("tvshow", "episode"):
        base_path = show_path if show_path else file_path
        if not base_path:
            return None
        base_path = base_path.rstrip("/\\")
        return vfs_join(base_path, ".actors")

    return None


def get_tvshow_paths() -> Dict[int, str]:
    """Map tvshowid to the show's path, for season items queried without their parent show."""
    paths: Dict[int, str] = {}
    for show in get_library_items(media_types=['tvshow'], properties=['file']):
        show_id = show.get('tvshowid') or show.get('dbid')
        if show_id and show.get('file'):
            paths[show_id] = show['file']
    return paths


def get_album_folders(album_ids: List[int]) -> Dict[int, str]:
    """Map each albumid to its folder, taken from the first song file seen per album."""
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
    """Per-directory filename cache, so existence checks cost one listing instead of a stat each.

    Every stat is a network round trip serialised behind Kodi's global NFS/SMB lock.
    """

    def __init__(self, max_dirs: int = 4096):
        self._dirs: Dict[str, Set[str]] = {}
        self.max_dirs = max_dirs

    def files(self, directory: str) -> Optional[Set[str]]:
        """Lowercased filenames in `directory`; None when it can't be listed or came back empty.

        listdir reports an unreachable share and an empty folder identically, so an empty
        result is never trusted or cached. Names are folded because xbmcvfs.exists is
        case-insensitive on NTFS and SMB.
        """
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
        """First existing `base_path.<ext>`, falling back to per-file stat when unlisted."""
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
    """True when art saves as `<mediafile>-<type>` rather than a bare `<type>` in the folder.

    Callers read the setting once per run and pass it, since it can't change mid-operation.
    """
    return (media_type in ('episode', 'musicvideo')
            or (media_type == 'movie' and savewith_basefilename))


def resolve_media_file(item: Dict[str, Any],
                       album_folders: Optional[Dict[int, str]] = None,
                       tvshow_paths: Optional[Dict[int, str]] = None) -> str:
    """Resolve the `media_file` input `PathBuilder.build_path` needs; '' when the item has none.

    Seasons fetched nested under their show already carry the show's `file`; standalone
    season queries have no path, so `tvshow_paths` (from `get_tvshow_paths`) fills it in.
    """
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
                "Folder configured successfully",
                xbmcgui.NOTIFICATION_INFO,
                3000
            )
            return folder

        dialog.ok(
            "Error",
            "Failed to save setting.[CR][CR]Please configure manually in Kodi settings."
        )
        return None

    @staticmethod
    def _movie_sets_folder() -> Optional[str]:
        """Configured movie sets folder, prompting once if unset."""
        return PathBuilder._resolve_named_item_folder(
            "videolibrary.moviesetsfolder",
            "Movie Set Information Folder Not Configured",
            "MSIF (Movie Set Information Folder) is not configured in Kodi settings.[CR][CR]"
            "This folder stores artwork for movie sets (like 'The Matrix Collection').[CR][CR]"
            "Would you like to select a folder now?",
            "Select Movie Sets Folder"
        )

    @staticmethod
    def _artist_folder() -> Optional[str]:
        """Configured artist information folder, prompting once if unset."""
        return PathBuilder._resolve_named_item_folder(
            "musiclibrary.artistsfolder",
            "Artist Information Folder Not Configured",
            "Artist Information Folder is not configured in Kodi settings.[CR][CR]"
            "This folder stores artwork and metadata for music artists.[CR][CR]"
            "Would you like to select a folder now?",
            "Select Artist Information Folder"
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
        """Get a Kodi folder setting; prompt the user to configure one if missing.

        Cached per setting: worker threads reach this per artwork, and the prompt is modal.
        """
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
        # Kodi discovers thumb art by matching filenames from this setting,
        # so we must save using a name from the user's configured list.
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
        """Sanitize `name` via `makeLegalFilename`; `parent_dir` triggers filesystem-aware mode."""
        if not name:
            return fallback
        # makeLegalFilename wraps CUtil::MakeLegalPath which skips
        # sanitization for bare names (no HD/SMB/NFS prefix detected).
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
        """Count how many library artists share `artist_name` (for MBID-based disambiguation).

        Cached: worker threads reach this once per artist art item.
        """
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
        """Walk up past BDMV/VIDEO_TS/STREAM/BACKUP directories to find the real movie root."""
        dir_path = vfs_dirname(path)

        check_path = dir_path
        for _ in range(3):
            dirname = vfs_basename(check_path)
            if dirname in ('BDMV', 'VIDEO_TS', 'STREAM', 'BACKUP'):
                check_path = vfs_dirname(check_path)
            else:
                break

        parent_name = vfs_basename(vfs_dirname(path))
        grandparent_name = vfs_basename(vfs_dirname(vfs_dirname(path)))

        if parent_name in ('BDMV', 'VIDEO_TS'):
            return vfs_dirname(vfs_dirname(path))
        elif grandparent_name in ('BDMV', 'VIDEO_TS'):
            return vfs_dirname(vfs_dirname(vfs_dirname(path)))
        elif parent_name == 'STREAM' and grandparent_name == 'BDMV':
            return vfs_dirname(vfs_dirname(vfs_dirname(path)))

        return dir_path

    @staticmethod
    def build_path(media_type: str, media_file: str, artwork_type: str,
                   season_number: Optional[int] = None,
                   use_basename: bool = True, mbid: Optional[str] = None) -> Optional[str]:
        """Build an extensionless artwork path for `media_type`.

        `media_file` is the media file path, or a title/name for `set`/`artist`.
        `use_basename=True` gives `Movie-poster`; False gives `poster` in the folder.
        `mbid` disambiguates duplicate artist names. Returns None if the path can't be built.
        """
        if not media_file:
            return None

        base_path, ext = vfs_splitext(media_file)
        dir_path, filename = vfs_split(base_path)

        if not ext:
            dir_path = vfs_rstrip_sep(media_file)
            filename = ''

        if media_type == 'movie':
            if use_basename and filename:
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
