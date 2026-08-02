"""Playback helpers for skin RunScript calls.

Provides playall and playrandom functionality using JSON-RPC Playlist methods.
"""
from __future__ import annotations

import xbmc
import xbmcgui

from lib.kodi.client import request, ADDON
from lib.infrastructure.dialogs import show_notification


def _detect_media_type(path: str) -> str:
    """Return `'music'` for `musicdb://` / `library://music` paths, else `'video'`."""
    path_lower = path.lower()
    if path_lower.startswith(('musicdb://', 'library://music')):
        return 'music'
    return 'video'


def _play_directory(path: str, shuffled: bool) -> None:
    """Build a recursive playlist from `path` and start playback. Auto-detects music vs video."""
    if not path:
        show_notification(xbmc.getLocalizedString(257), ADDON.getLocalizedString(32270),
                          xbmcgui.NOTIFICATION_ERROR, 3000)
        return

    media_type = _detect_media_type(path)
    playlistid = 0 if media_type == 'music' else 1

    items = request('Files.GetDirectory', {'directory': path, 'media': media_type})
    if not items or not items.get('files'):
        show_notification(xbmc.getLocalizedString(257), ADDON.getLocalizedString(32271),
                          xbmcgui.NOTIFICATION_ERROR, 3000)
        return

    request('Playlist.Clear', {'playlistid': playlistid})
    request('Playlist.Add', {
        'playlistid': playlistid,
        'item': {'directory': path, 'recursive': True},
    })
    request('Player.Open', {
        'item': {'playlistid': playlistid},
        'options': {'shuffled': shuffled},
    })


def playall(path: str) -> None:
    """Build a playlist from `path` (recursively) and play in order. Auto-detects music vs video."""
    _play_directory(path, shuffled=False)


def playrandom(path: str) -> None:
    """Same as `playall` but starts playback shuffled."""
    _play_directory(path, shuffled=True)
