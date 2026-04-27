"""
Playlist builder for movie marathon mode.

Creates a Kodi video playlist from selected movies and
starts playback.

Logging:
    Logger: 'playback'
    Key events:
        - playlist.create (INFO): Playlist built
        - playlist.start (INFO): Playback started
    See LOGGING.md for full guidelines.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

import xbmc

if TYPE_CHECKING:
    from resources.lib.data.storage import StorageManager

from resources.lib.constants import PLAYLIST_ADD_DELAY_MS
from resources.lib.utils import get_logger, json_query, notify
from resources.lib.data.queries import (
    get_clear_video_playlist_query,
    build_add_movie_query,
    build_play_playlist_query,
)

# Module-level logger
log = get_logger('playback')


def build_and_play_playlist(
    movies: List[Dict[str, Any]],
    show_notifications: bool = True,
    prioritize_in_progress: bool = False,
    resume_from_position: bool = True,
    storage: Optional['StorageManager'] = None,
) -> bool:
    """Build a Kodi video playlist from movies and start playback.

    Args:
        movies: List of movie dicts to add to the playlist.
        show_notifications: Show progress notifications while building.
        prioritize_in_progress: Sort partially-watched movies first.
        resume_from_position: Resume movies from their last position.
        storage: If provided, records movies as EasyMovie-started.

    Returns:
        True if playlist was created and playback started.
    """
    if not movies:
        log.warning("No movies to build playlist", event="playlist.fail")
        return False

    # Optionally sort in-progress movies first
    if prioritize_in_progress:
        movies = _sort_in_progress_first(movies)

    # Record all playlist movies as EasyMovie-started
    if storage:
        for movie in movies:
            mid = movie.get("movieid", 0)
            if mid:
                storage.add_started(mid, movie.get("title", ""))

    # Clear existing video playlist
    json_query(get_clear_video_playlist_query(), return_result=False)

    # Add movies one by one
    total = len(movies)
    for i, movie in enumerate(movies):
        movie_id = movie.get("movieid", 0)
        title = movie.get("title", "Unknown")

        if show_notifications:
            notify(f"Building playlist... ({i + 1}/{total})")

        query = build_add_movie_query(movie_id)
        json_query(query, return_result=False)

        log.debug("Added movie to playlist",
                  title=title, movieid=movie_id,
                  position=i)

        # Small delay between additions to avoid overwhelming Kodi
        if i < total - 1:
            xbmc.sleep(PLAYLIST_ADD_DELAY_MS)

    log.info("Playlist created", event="playlist.create",
             movie_count=total,
             titles=[m.get("title", "") for m in movies[:5]])

    # Start playback
    query = build_play_playlist_query(position=0)
    json_query(query, return_result=False)

    log.info("Playlist playback started", event="playlist.start",
             movie_count=total)

    return True


def _sort_in_progress_first(
    movies: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Sort movies so partially-watched ones come first.

    Movies with a resume position are placed at the front,
    maintaining their relative order. Unwatched movies follow.

    Args:
        movies: List of movie dicts.

    Returns:
        Reordered list with in-progress movies first.
    """
    in_progress = []
    others = []

    for movie in movies:
        resume = movie.get("resume", {})
        if isinstance(resume, dict) and resume.get("position", 0) > 0:
            in_progress.append(movie)
        else:
            others.append(movie)

    return in_progress + others
