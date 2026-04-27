"""
Movie playback controller.

Handles single movie playback, resume points, and
now-playing info display.

Logging:
    Logger: 'playback'
    Key events:
        - playback.start (INFO): Movie playback started
        - playback.resume (INFO): Resumed from position
    See LOGGING.md for full guidelines.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from resources.lib.data.storage import StorageManager

from resources.lib.constants import RESUME_REWIND_SECONDS
from resources.lib.utils import get_logger, json_query
from resources.lib.data.queries import build_play_movie_query

# Module-level logger
log = get_logger('playback')


def play_movie(
    movie: Dict[str, Any], resume: bool = False,
    storage: Optional['StorageManager'] = None,
) -> None:
    """Play a single movie.

    Args:
        movie: Movie dict with at minimum 'movieid' and 'title'.
        resume: If True, resume from the last position (with a small rewind
            for context). Kodi's Player.Open handles the start offset
            natively, so no post-play seek is needed.
        storage: Optional StorageManager to record started movies.
    """
    movie_id = movie.get("movieid", 0)
    title = movie.get("title", "Unknown")
    resume_seconds: Optional[int] = None

    # Record that EasyMovie started this movie (persists across restarts)
    if storage and movie_id:
        storage.add_started(movie_id, title)

    if resume:
        resume_info = movie.get("resume", {})
        position = resume_info.get("position", 0) if isinstance(resume_info, dict) else 0
        if position > 0:
            resume_seconds = max(0, int(position) - RESUME_REWIND_SECONDS)
            log.info("Resuming movie", event="playback.resume",
                     title=title, movieid=movie_id,
                     position_seconds=int(position),
                     start_seconds=resume_seconds)
        else:
            resume = False

    if not resume:
        log.info("Playing movie", event="playback.start",
                 title=title, movieid=movie_id)

    # Start playback via JSON-RPC. When resuming, Kodi applies the start
    # offset before the player initialises (single-item Player.Open path,
    # see Kodi's PlayerOperations.cpp Open() resume handling).
    query = build_play_movie_query(movie_id, resume_seconds=resume_seconds)
    json_query(query, return_result=False)


def get_resume_info(movie: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Get resume information for a movie.

    Args:
        movie: Movie dict with resume data.

    Returns:
        Dict with 'position' and 'total' keys, or None if no resume point.
    """
    resume = movie.get("resume", {})
    if not isinstance(resume, dict):
        return None

    position = resume.get("position", 0)
    total = resume.get("total", 0)

    if position > 0 and total > 0:
        remaining_seconds = int(total - position)
        remaining_minutes = remaining_seconds // 60
        return {
            "position": position,
            "total": total,
            "remaining_seconds": remaining_seconds,
            "remaining_minutes": remaining_minutes,
        }
    return None
