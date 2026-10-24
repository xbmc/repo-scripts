"""IMDb ratings from IMDb's ratings dataset, in one local store every add-on using it shares."""

import gzip
import sqlite3
import time
from typing import Callable, Iterable, Iterator, Optional, Tuple
from urllib.request import Request, urlopen

import xbmc
import xbmcvfs

_ADDON_ID = 'script.module.imdbratings'
_DATASET_URL = 'https://datasets.imdbws.com/title.ratings.tsv.gz'
_STORE = 'special://temp/imdbratings.db'
_HEADERS = {'User-Agent': _ADDON_ID, 'Accept-Encoding': 'identity'}
_CHECK_GAP = 15 * 60
_RETRY_GAP = 6 * 3600
_STOP_CHECK_LINES = 10000
_SCHEMA = 1

_conn = None
_next_check = 0.0


class _Stopped(Exception):
    """Stop request from Kodi or the caller, raised inside a load."""


def get_rating(imdb_id: Optional[str]) -> Optional[Tuple[float, int]]:
    """Get the rating and vote count of an IMDb title, updating the store first when it is due."""
    if not imdb_id or not imdb_id.startswith('tt'):
        return None
    try:
        title = int(imdb_id[2:])
    except ValueError:
        return None
    conn = _connect()
    if conn is None:
        return None
    if time.time() >= _next_check:
        _update(conn)
    try:
        row = conn.execute('SELECT rating, votes FROM ratings WHERE id = ?', (title,)).fetchone()
    except sqlite3.Error as exc:
        _log(f'lookup failed: {exc}', xbmc.LOGERROR)
        return None
    return (row[0] / 10, row[1]) if row else None


def refresh(abort: Optional[Callable[[], bool]] = None,
            on_download: Optional[Callable[[], None]] = None) -> bool:
    """Refresh the store when a shared check is due; True when this call loaded new data."""
    conn = _connect()
    return conn is not None and _update(conn, abort, on_download)


def dataset_date() -> Optional[str]:
    """Last-Modified date of the loaded IMDb file; None before a first load or on a store error."""
    conn = _connect()
    if conn is None:
        return None
    try:
        return _meta(conn, 'modified')
    except sqlite3.Error as exc:
        _log(f'date lookup failed: {exc}', xbmc.LOGERROR)
        return None


def _connect() -> Optional[sqlite3.Connection]:
    """Open the store once per interpreter, creating its tables on first use."""
    global _conn, _next_check
    if _conn is not None:
        return _conn
    try:
        conn = sqlite3.connect(xbmcvfs.translatePath(_STORE), timeout=5, isolation_level=None)
        conn.execute('PRAGMA journal_mode = WAL')
        _create(conn)
        _next_check = _due(conn)
    except sqlite3.Error as exc:
        _log(f'cannot open the store: {exc}', xbmc.LOGERROR)
        return None
    _conn = conn
    return conn


def _create(conn: sqlite3.Connection) -> None:
    """Create the tables empty when the store is new or holds another schema version."""
    if conn.execute('PRAGMA user_version').fetchone()[0] == _SCHEMA:
        return
    conn.execute('BEGIN IMMEDIATE')
    try:
        # another add-on may have created them while this one waited for the lock
        if conn.execute('PRAGMA user_version').fetchone()[0] != _SCHEMA:
            conn.execute('DROP TABLE IF EXISTS ratings')
            conn.execute('DROP TABLE IF EXISTS meta')
            conn.execute('CREATE TABLE ratings '
                         '(id INTEGER PRIMARY KEY, rating INTEGER, votes INTEGER)')
            conn.execute('CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)')
            conn.execute(f'PRAGMA user_version = {_SCHEMA}')
        conn.execute('COMMIT')
    except sqlite3.Error:
        if conn.in_transaction:
            conn.execute('ROLLBACK')
        raise


def _due(conn: sqlite3.Connection) -> float:
    """Time the next check falls due, past the check gap and any retry wait after a failed load."""
    return max(float(_meta(conn, 'checked') or 0) + _CHECK_GAP, float(_meta(conn, 'retry') or 0))


def _update(conn: sqlite3.Connection, abort: Optional[Callable[[], bool]] = None,
            on_download: Optional[Callable[[], None]] = None) -> bool:
    """Update the ratings when a check is due and the lock is free; True when new data loaded."""
    global _next_check
    _next_check = time.time() + _CHECK_GAP
    try:
        conn.execute('BEGIN IMMEDIATE')
    except sqlite3.OperationalError:
        _log('store busy, update skipped')
        return False
    loaded = False
    try:
        if _due(conn) <= time.time():
            conn.execute("INSERT OR REPLACE INTO meta VALUES ('checked', ?)", (str(time.time()),))
            loaded = _reload(conn, abort, on_download)
        conn.execute('COMMIT')
        _next_check = _due(conn)
    except Exception as exc:
        _log(f'update failed: {exc}', xbmc.LOGERROR)
        loaded = False
        if conn.in_transaction:
            conn.execute('ROLLBACK')
    # else the WAL keeps a second copy of the ratings on disk
    conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    return loaded


def _reload(conn: sqlite3.Connection, abort: Optional[Callable[[], bool]],
            on_download: Optional[Callable[[], None]]) -> bool:
    """Reload the ratings if IMDb's file changed; True on a load, a failed one sets a retry wait."""
    modified = _remote_modified()
    if not modified or modified == _meta(conn, 'modified'):
        return False
    _log('downloading the ratings dataset', xbmc.LOGINFO)
    if on_download is not None:
        try:
            on_download()
        except Exception as exc:
            _log(f'download callback failed: {exc}', xbmc.LOGERROR)
    monitor = xbmc.Monitor()

    def stopped() -> bool:
        return monitor.abortRequested() or (abort is not None and abort())

    loaded = False
    conn.execute('SAVEPOINT reload')
    try:
        # rebuilt in place, another add-on may have the file open
        conn.execute('DELETE FROM ratings')
        request = Request(_DATASET_URL, headers=_HEADERS)
        with urlopen(request, timeout=30) as response, gzip.GzipFile(fileobj=response) as lines:
            rows = _rows(lines, stopped)
            count = conn.executemany('INSERT INTO ratings VALUES (?, ?, ?)', rows).rowcount
        if count <= 0:
            raise ValueError('the dataset held no ratings')
        conn.execute("INSERT OR REPLACE INTO meta VALUES ('modified', ?)", (modified,))
        _log(f'stored {count} ratings', xbmc.LOGINFO)
        loaded = True
    except _Stopped:
        _log('load stopped, old ratings kept', xbmc.LOGINFO)
        conn.execute('ROLLBACK TO reload')
    except Exception as exc:
        _log(f'download failed: {exc}', xbmc.LOGERROR)
        conn.execute('ROLLBACK TO reload')
        conn.execute("INSERT OR REPLACE INTO meta VALUES ('retry', ?)",
                     (str(time.time() + _RETRY_GAP),))
    conn.execute('RELEASE reload')
    return loaded


def _rows(lines: Iterable[bytes], stopped: Callable[[], bool]) -> Iterator[Tuple[int, int, int]]:
    """Title number, rating times ten and votes per line, skipping bad ones; raises on a stop."""
    for number, line in enumerate(lines):
        if number % _STOP_CHECK_LINES == 0 and stopped():
            raise _Stopped()
        fields = line.split(b'\t')
        try:
            yield int(fields[0][2:]), round(float(fields[1]) * 10), int(fields[2])
        except (ValueError, IndexError):
            continue


def _remote_modified() -> Optional[str]:
    """Last-Modified of IMDb's file, or None when the check fails."""
    request = Request(_DATASET_URL, method='HEAD', headers=_HEADERS)
    try:
        with urlopen(request, timeout=10) as response:
            return response.headers.get('Last-Modified')
    except OSError as exc:
        _log(f'dataset check failed: {exc}', xbmc.LOGERROR)
        return None


def _meta(conn: sqlite3.Connection, key: str) -> Optional[str]:
    """Value stored under a meta key, or None."""
    row = conn.execute('SELECT value FROM meta WHERE key = ?', (key,)).fetchone()
    return row[0] if row else None


def _log(message: str, level: int = xbmc.LOGDEBUG) -> None:
    """Log under the module's id."""
    xbmc.log(f'[{_ADDON_ID}] {message}', level)
