"""Path statistics calculator for video library content."""
from __future__ import annotations

from typing import Dict, Any, List
import xbmc
import xbmcgui
import xbmcplugin

from lib.kodi.client import log, request


def _process_items(stats: Dict[str, Any], items: List[dict]) -> None:
    """Count watched/unwatched/in-progress per item; TV shows use episode counts since there's no
    show-level resume."""
    for item in items:
        if item.get('type') == 'tvshow':
            episode_count = item.get('episode', 0)
            watched_count = item.get('watchedepisodes', 0)
            stats['episodes'] += episode_count
            stats['watched_episodes'] += watched_count
            stats['tvshow_count'] += 1
            if watched_count > 0 and watched_count >= episode_count:
                stats['watched'] += 1
            elif watched_count > 0:
                stats['in_progress'] += 1
            else:
                stats['unwatched'] += 1
            continue

        playcount = item.get('playcount', 0)
        resume = item.get('resume', {})
        resume_position = 0
        if isinstance(resume, dict) and resume.get('total'):
            resume_position = resume.get('position', 0)

        if resume_position > 0:
            stats['in_progress'] += 1
        elif playcount > 0:
            stats['watched'] += 1
        else:
            stats['unwatched'] += 1

    if stats['episodes']:
        stats['unwatched_episodes'] = stats['episodes'] - stats['watched_episodes']


def get_path_statistics(path: str) -> Dict[str, Any]:
    """Count watched/unwatched/in-progress items and episodes for a video library path."""
    stats = {
        'count': 0,
        'watched': 0,
        'unwatched': 0,
        'in_progress': 0,
        'tvshow_count': 0,
        'episodes': 0,
        'watched_episodes': 0,
        'unwatched_episodes': 0,
    }

    if not path:
        return stats

    result = request(
        'Files.GetDirectory',
        {
            'directory': path,
            'media': 'video',
            'properties': ['playcount', 'resume', 'episode', 'watchedepisodes'],
        }
    )

    if not result or 'result' not in result:
        return stats

    files = result['result'].get('files', [])
    stats['count'] = result['result'].get('limits', {}).get('total', len(files))

    _process_items(stats, files)

    return stats


def handle_path_stats(handle: int, params: dict) -> None:
    """Plugin entry for path stats; returns an invisible ListItem with `SkinInfo.PathStats.*`
    properties."""
    path = params.get('path', [''])[0]

    if not path:
        log("Plugin", "Path Statistics: Missing required parameter 'path'", xbmc.LOGWARNING)
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    log("Plugin", f"Path Statistics: Calculating statistics for path: {path}", xbmc.LOGDEBUG)

    stats = get_path_statistics(path)

    properties = [
        ('Count', stats['count']),
        ('Watched', stats['watched']),
        ('Unwatched', stats['unwatched']),
        ('InProgress', stats['in_progress']),
        ('TVShowCount', stats['tvshow_count']),
        ('Episodes', stats['episodes']),
        ('WatchedEpisodes', stats['watched_episodes']),
        ('UnWatchedEpisodes', stats['unwatched_episodes']),
    ]

    window = xbmcgui.Window(10000)
    for prop_name, value in properties:
        window.setProperty(f'SkinInfo.PathStats.{prop_name}', str(value))

    item = xbmcgui.ListItem(offscreen=True)
    for prop_name, value in properties:
        item.setProperty(f'SkinInfo.PathStats.{prop_name}', str(value))

    xbmcplugin.addDirectoryItem(handle, '', item, isFolder=False)
    xbmcplugin.endOfDirectory(handle, succeeded=True)
