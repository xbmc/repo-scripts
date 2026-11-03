"""Award wins and nominations per title, from the awards file the add-on ships and updates."""
from __future__ import annotations

import os
import re
import threading
from typing import Dict, Final, List, Optional, Tuple

import xbmc
import xbmcvfs

from lib.kodi.client import ADDON, log

SHIPPED_PATH: Final = os.path.join(
    xbmcvfs.translatePath(ADDON.getAddonInfo('path')), 'resources', 'awards.tsv')
DOWNLOADED_PATH: Final = xbmcvfs.translatePath(
    'special://profile/addon_data/script.skin.info.service/awards.tsv')

# the file's Oscar data is complete, and MDBList's Oscar tags include fan-vote awards
_COMPLETE: Final = ('Oscar',)
_DATE = re.compile(r'\d{4}-\d{2}-\d{2}')

_lock = threading.Lock()
_names: List[str] = []
_rows: Optional[Dict[str, List[str]]] = None


def data_date(first_line: str) -> str:
    """Date an awards file's data was built, from its first line; empty when it has none."""
    found = _DATE.search(first_line)
    return found.group() if found else ''


def file_date(path: str) -> str:
    """Date an awards file's data was built; empty when the file is missing or unreadable."""
    try:
        with open(path, encoding='utf-8') as f:
            return data_date(f.readline())
    except OSError:
        return ''


def _newest_path() -> str:
    """The shipped or downloaded awards file, whichever holds newer data."""
    if file_date(DOWNLOADED_PATH) > file_date(SHIPPED_PATH):
        return DOWNLOADED_PATH
    return SHIPPED_PATH


def _load() -> Tuple[List[str], Dict[str, List[str]]]:
    """Award names and each title's cells by IMDb and prefixed TMDB id, cached until forgotten."""
    global _names, _rows
    with _lock:
        if _rows is not None:
            return _names, _rows
        names: List[str] = []
        rows: Dict[str, List[str]] = {}
        path = _newest_path()
        try:
            with open(path, encoding='utf-8') as f:
                for line in f:
                    if line.startswith('#'):
                        continue
                    cells = line.rstrip('\n').split('\t')
                    if not names:
                        names = cells[3:]
                        continue
                    awards = cells[3:]
                    if cells[0]:
                        rows[cells[0]] = awards
                    for tmdb in cells[1].split(',') if len(cells) > 1 else ():
                        if tmdb:
                            rows[tmdb] = awards
        except OSError as e:
            log("General", f"Awards file unreadable ({path}): {e}", xbmc.LOGWARNING)
        _names, _rows = names, rows
        return _names, _rows


def forget() -> None:
    """Forget the loaded awards file once a newer copy is saved."""
    global _rows
    with _lock:
        _rows = None


def award_counts(media_type: str, imdb_id: str, tmdb_id: str) -> Dict[str, Tuple[int, int]]:
    """Wins and nominations per award for a movie or TV show; empty when it has none."""
    names, rows = _load()
    prefix = 'm' if media_type == 'movie' else 't'
    cells = rows.get(imdb_id or '') or rows.get(f'{prefix}{tmdb_id}' if tmdb_id else '')
    counts: Dict[str, Tuple[int, int]] = {}
    for name, cell in zip(names, cells or []):
        wins, _, noms = cell.partition('/')
        if noms.isdigit() and wins.isdigit():
            counts[name] = (int(wins), int(noms))
    return counts


def apply_awards(props: Dict[str, str], media_type: str, imdb_id: str,
                 tmdb_id: str) -> Dict[str, str]:
    """Apply award counts and flags to online properties, replacing old counts and Oscar flags."""
    if media_type not in ('movie', 'tvshow'):
        return props
    for key in [k for k in props
                if k.startswith('Awards.') and k.endswith(('.Wins', '.Nominations'))]:
        del props[key]
    for name in _COMPLETE:
        props.pop(f'Awards.{name}.Won', None)
        props.pop(f'Awards.{name}.Nominated', None)
    for name, (wins, noms) in award_counts(media_type, imdb_id, tmdb_id).items():
        props[f'Awards.{name}.Wins'] = str(wins)
        props[f'Awards.{name}.Nominations'] = str(noms)
        if wins:
            props[f'Awards.{name}.Won'] = 'true'
        if noms:
            props[f'Awards.{name}.Nominated'] = 'true'
    return props
