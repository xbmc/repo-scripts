"""
Smart playlist movie ID extraction.

Queries a Kodi smart playlist (.xsp) file via Files.GetDirectory
and returns the set of movie IDs that match the playlist rules.

Logging:
    Logger: 'data'
    Key events:
        - pool.query (DEBUG): Playlist queried with result count
        - pool.empty (WARNING): Playlist returned no movies
    See LOGGING.md for full guidelines.
"""
import os
from typing import Set

from resources.lib.data.queries import build_playlist_get_movies_query
from resources.lib.utils import get_logger, json_query

log = get_logger('data')


def extract_movie_ids_from_playlist(playlist_path: str) -> Set[int]:
    """Extract movie IDs from a smart playlist file.

    Normalizes the path to special:// format, queries Kodi via
    Files.GetDirectory, and returns only items with type 'movie'.

    Args:
        playlist_path: Path to the .xsp file (absolute or special://).

    Returns:
        Set of Kodi movie IDs found in the playlist.
    """
    # Normalize to special:// path (Kodi expects this format)
    filename = os.path.basename(playlist_path)
    clean_path = "special://profile/playlists/video/" + filename

    query = build_playlist_get_movies_query(clean_path)
    result = json_query(query)

    files = result.get("files", [])
    movie_ids = {
        item["id"] for item in files
        if item.get("type") == "movie" and "id" in item
    }

    if movie_ids:
        log.debug("Playlist pool queried", event="pool.query",
                  path=filename, movie_count=len(movie_ids))
    else:
        log.warning("Playlist returned no movies", event="pool.empty",
                    path=filename)

    return movie_ids
