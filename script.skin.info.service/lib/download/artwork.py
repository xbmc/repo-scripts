"""Artwork file downloads, backing off a host or the disk after repeated failures."""
from __future__ import annotations

import os
import time
import urllib.parse
import requests
import xbmc
import xbmcvfs
from typing import Optional, Tuple, Dict, Callable, Final

from lib.kodi.client import log, get_item_details, request, extract_result
from lib.kodi.settings import KodiSettings
from lib.data.api.client import ApiSession
from lib.data.api.client import RetryableError
from lib.infrastructure.paths import (
    vfs_ensure_dir_slash, vfs_dirname, DirectoryListing, PathBuilder, use_basename_for)


# every chunk costs an abort check and a VFS write into Kodi
_CHUNK_SIZE: Final = 256 * 1024
_STREAM_DEADLINE: Final = 120.0


class _StreamNetworkError(Exception):
    """Network failure while streaming the response body, distinct from a file-write error."""


class _DownloadAborted(Exception):
    """User/system abort during streaming; must not count toward provider or file-write blocking."""


class DownloadArtwork:
    """Single-file artwork downloader: streaming, content-type detect, per-provider error gating."""

    CONTENT_TYPE_MAP = {
        'image/jpeg': 'jpg',
        'image/png': 'png',
        'image/gif': 'gif',
        'image/webp': 'webp'
    }

    ERROR_INPUT = 'input'
    ERROR_NETWORK = 'network'
    ERROR_PROVIDER_BLOCKED = 'provider_blocked'
    ERROR_STORAGE_BLOCKED = 'storage_blocked'
    ERROR_DIRECTORY = 'directory'
    ERROR_BAD_CONTENT = 'bad_content'
    ERROR_UNEXPECTED = 'unexpected'
    ERROR_ABORTED = 'aborted'

    def __init__(self):
        self.provider_errors: Dict[str, int] = {}
        self.provider_blocked_until: Dict[str, float] = {}
        self.file_error_count = 0
        self.file_blocked_until = 0.0
        self.max_provider_errors = 3
        self.max_file_errors = 3
        self.block_cooldown = 30.0
        self.listing = DirectoryListing()

        self.session = ApiSession(
            service_name="Artwork",
            timeout=(5.0, 15.0),
            max_retries=2,
            backoff_factor=0.5,
            connect_retries=1,
            read_retries=1,
            default_headers={
                "User-Agent": "Kodi Artwork Addon/1.0",
                "Accept": "image/*"
            }
        )

    def close(self) -> None:
        """Release this downloader's pooled connections."""
        self.session.close()

    def _block_provider(self, hostname: str) -> None:
        """Count a provider failure; arm a cooldown once the host crosses the error limit."""
        count = self.provider_errors.get(hostname, 0) + 1
        self.provider_errors[hostname] = count
        if count >= self.max_provider_errors:
            self.provider_blocked_until[hostname] = time.time() + self.block_cooldown
            log("Download",
                f"Provider {hostname} blocked for {self.block_cooldown:.0f}s after {count} errors",
                xbmc.LOGWARNING)

    def _block_file_writes(self) -> None:
        """Count a file-write failure; arm a cooldown once writes cross the error limit."""
        self.file_error_count += 1
        if self.file_error_count >= self.max_file_errors:
            self.file_blocked_until = time.time() + self.block_cooldown
            log("Download", f"File writes blocked for {self.block_cooldown:.0f}s after "
                f"{self.file_error_count} errors (check disk space / permissions)", xbmc.LOGWARNING)

    def download_artwork(
        self,
        url: str,
        local_path: str,
        existing_file_mode: str = 'skip',
        alternate_path: Optional[str] = None,
        abort_flag=None,
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> Tuple[bool, Optional[str], int, Optional[str]]:
        """Download one artwork file, taking its extension from the response Content-Type."""
        if not url:
            log("Download", "Empty URL provided", xbmc.LOGERROR)
            return False, "Empty URL", 0, self.ERROR_INPUT

        if not local_path:
            log("Download", "Empty local_path provided", xbmc.LOGERROR)
            return False, "Empty local_path", 0, self.ERROR_INPUT

        hostname = urllib.parse.urlparse(url).netloc
        now = time.time()

        if now < self.provider_blocked_until.get(hostname, 0.0):
            return False, f"Provider {hostname} temporarily blocked", 0, self.ERROR_PROVIDER_BLOCKED

        if now < self.file_blocked_until:
            return False, "File writes temporarily blocked", 0, self.ERROR_STORAGE_BLOCKED

        if existing_file_mode == 'skip':
            paths_to_check = [local_path]
            if alternate_path:
                paths_to_check.append(alternate_path)

            for check_path in paths_to_check:
                if self._find_existing_with_extension(check_path):
                    return False, None, 0, None

        try:
            response = self.session.get_raw(
                url,
                abort_flag=abort_flag,
                stream=True,
                deadline_seconds=_STREAM_DEADLINE
            )

            if response is None:
                self._block_provider(hostname)
                return False, "Download failed", 0, self.ERROR_NETWORK

            ext = self._get_extension(response)
            if not ext:
                self._block_provider(hostname)
                response.close()
                return False, "Unknown image type", 0, self.ERROR_BAD_CONTENT

            full_path = xbmcvfs.validatePath(local_path + '.' + ext)
            parent_dir = os.path.dirname(full_path)
            parent_dir_check = vfs_ensure_dir_slash(parent_dir)
            if not xbmcvfs.exists(parent_dir_check):
                xbmcvfs.mkdirs(parent_dir)
                if not xbmcvfs.exists(parent_dir_check):
                    self._block_file_writes()
                    log("Download", f"Cannot create directory: {parent_dir}", xbmc.LOGERROR)
                    response.close()
                    return False, f"Cannot create directory: {parent_dir}", 0, self.ERROR_DIRECTORY

            bytes_written = self._write_file_stream(
                full_path, response, abort_flag, progress_callback
            )
            self.listing.note_written(local_path + '.' + ext)

            if existing_file_mode == 'overwrite':
                stale_bases = [local_path]
                if alternate_path:
                    stale_bases.append(alternate_path)
                for base in stale_bases:
                    for ext_type in self.CONTENT_TYPE_MAP.values():
                        stale_file = xbmcvfs.validatePath(base + '.' + ext_type)
                        if stale_file == full_path:
                            continue
                        if xbmcvfs.exists(stale_file):
                            if not xbmcvfs.delete(stale_file):
                                log("Download", f"Failed to delete old pattern file: {stale_file}",
                                    xbmc.LOGWARNING)

            self.provider_errors[hostname] = 0
            self.provider_blocked_until.pop(hostname, None)
            self.file_error_count = 0
            self.file_blocked_until = 0.0

            return True, None, bytes_written, None

        except _DownloadAborted as e:
            return False, str(e), 0, self.ERROR_ABORTED

        except _StreamNetworkError as e:
            self._block_provider(hostname)
            log("Download", f"Network error streaming {url}: {str(e)}", xbmc.LOGWARNING)
            return False, str(e), 0, self.ERROR_NETWORK

        except RetryableError as e:
            self._block_provider(hostname)
            log("Download", f"Network error for {url}: {str(e)}", xbmc.LOGWARNING)
            return False, str(e), 0, self.ERROR_NETWORK

        except Exception as e:
            self._block_file_writes()
            log("Download", f"Unexpected error downloading {url}: {str(e)}", xbmc.LOGERROR)
            return False, f"Unexpected error: {str(e)}", 0, self.ERROR_UNEXPECTED

    def _find_existing_with_extension(self, base_path: str) -> Optional[str]:
        """Find an existing file at this base path with any known image extension, or None."""
        return self.listing.find_with_extension(base_path, self.CONTENT_TYPE_MAP.values())

    def _get_extension(self, response) -> Optional[str]:
        """Get the file extension for the response's Content-Type, or None if unrecognized."""
        content_type = response.headers.get('Content-Type', '').split(';')[0].strip()
        return self.CONTENT_TYPE_MAP.get(content_type)

    def _write_file_stream(self, path: str, response, abort_flag=None,
                           progress_callback: Optional[Callable[[int], None]] = None) -> int:
        """Write the response body to a file, deleting it on failure; returns the bytes written."""
        bytes_written = 0
        cap = getattr(abort_flag, 'max_request_seconds', None) if abort_flag else None
        deadline = time.monotonic() + (cap or _STREAM_DEADLINE)

        try:
            f = xbmcvfs.File(path, 'wb')

            with f:
                iterator = response.iter_content(chunk_size=_CHUNK_SIZE)
                while True:
                    try:
                        chunk = next(iterator)
                    except StopIteration:
                        break
                    except requests.exceptions.RequestException as e:
                        # on cancel the watcher closes the socket, which raises here first
                        if abort_flag and abort_flag.is_requested():
                            raise _DownloadAborted("Download aborted") from None
                        raise _StreamNetworkError(str(e)) from e

                    if abort_flag and abort_flag.is_requested():
                        raise _DownloadAborted("Download aborted")

                    # the read timeout resets on every chunk
                    if time.monotonic() > deadline:
                        raise _StreamNetworkError("stream exceeded time limit")
                    if chunk:
                        written = f.write(chunk)
                        if not written:
                            raise IOError(f"Failed to write to {path}")
                        bytes_written += len(chunk)
                        if progress_callback:
                            progress_callback(len(chunk))
        except Exception:
            if xbmcvfs.exists(path):
                xbmcvfs.delete(path)
            raise
        finally:
            response.close()
        return bytes_written


def _item_location(media_type: str, dbid: int,
                   title: str) -> Tuple[str, Optional[int], Optional[str]]:
    """Locate the media file, season number and artist MBID an item's art path is built from."""
    if media_type == 'set':
        return title, None, None
    if media_type == 'artist':
        details = get_item_details('artist', dbid, ['musicbrainzartistid'])
        mbid = details.get('musicbrainzartistid', '') if isinstance(details, dict) else ''
        if isinstance(mbid, list):
            mbid = mbid[0] if mbid else ''
        return title, None, mbid or None
    if media_type == 'album':
        songs = extract_result(request('AudioLibrary.GetSongs', {
            'filter': {'albumid': dbid},
            'properties': ['file'],
            'limits': {'start': 0, 'end': 1},
        }), 'songs', [])
        if songs and songs[0].get('file'):
            return vfs_dirname(songs[0]['file']), None, None
        return '', None, None

    if media_type == 'season':
        properties = ['season', 'tvshowid']
    elif media_type == 'episode':
        properties = ['file', 'season']
    elif media_type in ('movie', 'tvshow', 'musicvideo'):
        properties = ['file']
    else:
        return '', None, None

    item = get_item_details(media_type, dbid, properties)
    if not isinstance(item, dict):
        return '', None, None
    media_file = item.get('file', '')
    if media_type == 'season' and item.get('tvshowid'):
        show = get_item_details('tvshow', item['tvshowid'], ['file'])
        if isinstance(show, dict):
            media_file = show.get('file', '')
    return media_file, item.get('season'), None


def download_item_art(media_type: str, dbid: int, title: str, art: dict,
                      existing_file_mode: str, downloader: Optional[DownloadArtwork] = None) -> int:
    """Download an item's art beside its media file; returns how many files were written."""
    urls = {art_type: url for art_type, url in art.items() if url and url.startswith('http')}
    if not urls:
        return 0

    media_file, season, mbid = _item_location(media_type, dbid, title)
    if not media_file:
        log("Download", f"No file path for {media_type} '{title}', skipping download")
        return 0

    use_basename = use_basename_for(
        media_type, KodiSettings.get_bool('download.savewith_basefilename'))
    path_builder = PathBuilder()
    own_downloader = downloader is None
    active = downloader or DownloadArtwork()
    written = 0

    try:
        for art_type, url in urls.items():
            local_path = path_builder.build_path(
                media_type, media_file, art_type, season, use_basename, mbid)
            if not local_path:
                log("Download",
                    f"Could not build download path for {media_type} '{title}' {art_type}")
                continue

            alternate_path = None
            if media_type in ('movie', 'musicvideo'):
                alternate_path = path_builder.build_path(
                    media_type, media_file, art_type, season, not use_basename, mbid)

            success, error, bytes_downloaded, _ = active.download_artwork(
                url=url,
                local_path=local_path,
                existing_file_mode=existing_file_mode,
                alternate_path=alternate_path,
            )
            if success:
                written += 1
                log("Download",
                    f"Downloaded {art_type} for '{title}': {local_path} ({bytes_downloaded} bytes)")
            elif error:
                log("Download", f"Failed to download {art_type} for '{title}': {error}")
    except Exception as e:
        log("Download", f"Error downloading art for '{title}': {e}", xbmc.LOGWARNING)
    finally:
        if own_downloader:
            active.close()

    return written
