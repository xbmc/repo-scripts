"""
Genre/MPAA/Playlist Selector for EasyMovie.

Launched from settings via RunScript(script.easymovie,selector,genres),
RunScript(script.easymovie,selector,ignore_genres),
RunScript(script.easymovie,selector,mpaa), or
RunScript(script.easymovie,selector,playlist).

Queries the Kodi library for all unique values, shows a multi-select
dialog, and saves the selection back to settings as JSON.

Logging:
    Logger: 'selector'
    Key events:
        - selector.open (INFO): Selector dialog opened
        - selector.save (INFO): Selection saved
    See LOGGING.md for full guidelines.
"""
from __future__ import annotations

import json
import os
import sys
import xml.etree.ElementTree as ET
from typing import Optional

import xbmcaddon
import xbmcvfs

from resources.lib.utils import get_logger, json_query, lang
from resources.lib.data.queries import get_all_movies_query, get_playlist_files_query
from resources.lib.data.filters import extract_unique_genres, extract_unique_mpaa
from resources.lib.ui.dialogs import show_select_dialog

log = get_logger('selector')


def _get_selector_type() -> str:
    """Determine selector type from command-line arguments."""
    # When invoked via settings: argv = [script_path, 'selector', 'genres'|'mpaa']
    if len(sys.argv) >= 3:
        return sys.argv[2]
    # When invoked via default.py: argv = [script_path, 'selector', 'genres'|'mpaa']
    if len(sys.argv) >= 2:
        return sys.argv[1]
    return 'genres'


def _run_genre_selector() -> None:
    """Show genre selection dialog and save to settings."""
    log.info("Opening genre selector", event="selector.open", type="genres")

    # Query all movies to extract genres
    result = json_query(get_all_movies_query())
    movies = result.get("movies", [])
    if not movies:
        log.warning("No movies in library", event="selector.open")
        return

    all_genres = extract_unique_genres(movies)
    if not all_genres:
        return

    # Load previously selected genres
    addon = xbmcaddon.Addon()
    saved_json = addon.getSetting('selected_genres')
    saved_genres = []
    if saved_json:
        try:
            saved_genres = json.loads(saved_json)
        except (json.JSONDecodeError, TypeError):
            pass

    # Build preselected indices
    preselected = [i for i, g in enumerate(all_genres) if g in saved_genres]

    # Show dialog
    selected_indices = show_select_dialog(
        heading=lang(32200),  # "Select Genres"
        items=all_genres,
        multi_select=True,
        preselected=preselected,
    )

    if selected_indices is None:
        return  # Cancelled

    # Save selection
    selected_genres = [all_genres[i] for i in selected_indices]
    addon.setSetting('selected_genres', json.dumps(selected_genres))

    # Update display field
    display = ", ".join(selected_genres) if selected_genres else "-"
    addon.setSetting('selected_genres_display', display)

    log.info("Genres saved", event="selector.save",
             count=len(selected_genres), genres=selected_genres[:5])


def _run_ignore_genre_selector() -> None:
    """Show ignore-genre selection dialog and save to settings."""
    log.info("Opening ignore genre selector", event="selector.open",
             type="ignore_genres")

    result = json_query(get_all_movies_query())
    movies = result.get("movies", [])
    if not movies:
        log.warning("No movies in library", event="selector.open")
        return

    all_genres = extract_unique_genres(movies)
    if not all_genres:
        return

    # Load previously selected ignore genres
    addon = xbmcaddon.Addon()
    saved_json = addon.getSetting('selected_ignore_genres')
    saved_genres = []
    if saved_json:
        try:
            saved_genres = json.loads(saved_json)
        except (json.JSONDecodeError, TypeError):
            pass

    preselected = [i for i, g in enumerate(all_genres) if g in saved_genres]

    selected_indices = show_select_dialog(
        heading=lang(32204),  # "Ignore Genres"
        items=all_genres,
        multi_select=True,
        preselected=preselected,
    )

    if selected_indices is None:
        return  # Cancelled

    selected_genres = [all_genres[i] for i in selected_indices]
    addon.setSetting('selected_ignore_genres', json.dumps(selected_genres))

    display = ", ".join(selected_genres) if selected_genres else "-"
    addon.setSetting('ignore_genres_display', display)

    log.info("Ignore genres saved", event="selector.save",
             count=len(selected_genres), genres=selected_genres[:5])


def _run_mpaa_selector() -> None:
    """Show MPAA rating selection dialog and save to settings."""
    log.info("Opening MPAA selector", event="selector.open", type="mpaa")

    result = json_query(get_all_movies_query())
    movies = result.get("movies", [])
    if not movies:
        return

    all_ratings = extract_unique_mpaa(movies)
    if not all_ratings:
        return

    # Load previously selected ratings
    addon = xbmcaddon.Addon()
    saved_json = addon.getSetting('selected_mpaa')
    saved_ratings = []
    if saved_json:
        try:
            saved_ratings = json.loads(saved_json)
        except (json.JSONDecodeError, TypeError):
            pass

    preselected = [i for i, r in enumerate(all_ratings) if r in saved_ratings]

    selected_indices = show_select_dialog(
        heading=lang(32201),  # "Select Age Ratings"
        items=all_ratings,
        multi_select=True,
        preselected=preselected,
    )

    if selected_indices is None:
        return

    selected_ratings = [all_ratings[i] for i in selected_indices]
    addon.setSetting('selected_mpaa', json.dumps(selected_ratings))

    display = ", ".join(selected_ratings) if selected_ratings else "-"
    addon.setSetting('selected_mpaa_display', display)

    log.info("MPAA ratings saved", event="selector.save",
             count=len(selected_ratings))


def _get_playlist_type(filepath: str) -> Optional[str]:
    """Read a .xsp playlist file and return its type attribute.

    Returns:
        Playlist type ('movies', 'tvshows', etc.) or None if unreadable.
    """
    try:
        fh = xbmcvfs.File(filepath, 'r')
        try:
            content = fh.read()
        finally:
            fh.close()

        if not content:
            return None

        root = ET.fromstring(content)
        return root.get('type')
    except (ET.ParseError, Exception):
        return None


def _run_playlist_selector() -> None:
    """Show movie smart playlist selection and save to settings."""
    log.info("Opening playlist selector", event="selector.open", type="playlist")

    result = json_query(get_playlist_files_query())
    playlist_files = result.get('files') if result else None

    if not playlist_files:
        log.warning("No playlists found", event="selector.open")
        return

    # Filter to .xsp files with type 'movies'
    names = []
    paths = []
    for item in playlist_files:
        filepath = item.get('file', '')
        label = item.get('label', '')
        if not filepath.endswith('.xsp'):
            continue
        detected_type = _get_playlist_type(filepath)
        if detected_type != 'movies':
            continue
        names.append(label)
        paths.append(filepath)

    if not names:
        log.warning("No movie playlists found", event="selector.open")
        return

    selected_indices = show_select_dialog(
        heading=lang(32203),  # "Select Playlist"
        items=names,
        multi_select=False,
    )

    if selected_indices is None:
        return

    idx = selected_indices[0]
    selected_path = paths[idx]
    filename = os.path.basename(selected_path)
    if filename.endswith('.xsp'):
        filename = filename[:-4]

    addon = xbmcaddon.Addon()
    addon.setSetting('movie_pool_playlist_path', selected_path)
    addon.setSetting('pool_display', filename)

    log.info("Playlist saved", event="selector.save",
             path=selected_path, display=filename)


def main() -> None:
    """Entry point for the selector script."""
    selector_type = _get_selector_type()

    if selector_type == 'genres':
        _run_genre_selector()
    elif selector_type == 'ignore_genres':
        _run_ignore_genre_selector()
    elif selector_type == 'mpaa':
        _run_mpaa_selector()
    elif selector_type == 'playlist':
        _run_playlist_selector()
    else:
        log.warning("Unknown selector type", event="selector.open",
                    type=selector_type)


if __name__ == '__main__':
    main()
