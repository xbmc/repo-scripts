"""IMDb ratings from IMDb's ratings dataset, in one local store every add-on using it shares."""

import gzip
import io
import os
import sqlite3
import threading
import time
from email.utils import parsedate_to_datetime
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

_local = threading.local()
_next_check = 0.0
_stopped_until = 0.0
_logged = set()
# made at import, a Monitor created after Kodi's abort notice never reports it
_monitor = xbmc.Monitor()


class StoreError(Exception):
    """Store failure from lookup: the store can't be read or holds no dataset yet."""


class _Stopped(Exception):
    """Stop request from Kodi or the caller, raised inside a load."""


class _Holder:
    """One thread's store connection and the file it opened, closed when the thread ends."""

    def __init__(self, conn: sqlite3.Connection, inode: Optional[int]):
        self.conn = conn
        self.inode = inode

    def __del__(self):
        self.conn.close()


def get_rating(imdb_id: Optional[str]) -> Optional[Tuple[float, int]]:
    """Get the rating and vote count of an IMDb title, updating the store first when it is due."""
    title = _title_number(imdb_id)
    if title is None:
        return None
    conn = _connect()
    if conn is not None and time.time() >= _next_check:
        _update(conn)
        # an update that repaired a damaged store dropped the connection
        conn = _connect()
    if conn is None:
        return None
    try:
        return _stored(conn, title)
    except sqlite3.Error as exc:
        _log_error(f'lookup failed: {exc}')
        _mend(exc)
        return None


def lookup(imdb_id: Optional[str]) -> Optional[Tuple[float, int]]:
    """Look up a stored rating without updating; raises StoreError when the store can't answer."""
    title = _title_number(imdb_id)
    if title is None:
        return None
    conn = _open()
    try:
        rating = _stored(conn, title)
        loaded = rating is not None or _meta(conn, 'modified') is not None
    except sqlite3.Error as exc:
        _mend(exc)
        raise StoreError(f'lookup failed: {exc}') from exc
    if not loaded:
        raise StoreError('no dataset loaded yet')
    return rating


def refresh(abort: Optional[Callable[[], bool]] = None,
            on_download: Optional[Callable[[], None]] = None) -> bool:
    """Refresh store when shared check due and no stop lately; True when new data loaded."""
    if time.time() < _stopped_until:
        return False
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
        _log_error(f'date lookup failed: {exc}')
        _mend(exc)
        return None


def _title_number(imdb_id: Optional[str]) -> Optional[int]:
    """Number part of an IMDb title id, or None when it isn't one."""
    if not imdb_id:
        return None
    text = imdb_id.strip()
    if not text.startswith('tt'):
        return None
    digits = text[2:]
    # 18 digits always fit SQLite's 64-bit INTEGER
    if not (digits.isascii() and digits.isdigit()) or len(digits) > 18:
        return None
    return int(digits)


def _stored(conn: sqlite3.Connection, title: int) -> Optional[Tuple[float, int]]:
    """Rating and vote count stored for a title number, or None."""
    row = conn.execute('SELECT rating, votes FROM ratings WHERE id = ?', (title,)).fetchone()
    return (row[0] / 10, row[1]) if row else None


def _connect() -> Optional[sqlite3.Connection]:
    """Connect to the store, logging a failure and returning None instead of raising."""
    try:
        return _open()
    except StoreError as exc:
        _log_error(str(exc))
        return None


def _open(retry: bool = True) -> sqlite3.Connection:
    """Open the store once per thread; creates, repairs, seeds next check, raises StoreError."""
    global _next_check
    holder = getattr(_local, 'holder', None)
    if holder is not None:
        return holder.conn
    path = xbmcvfs.translatePath(_STORE)
    inode = _inode(path)
    conn = None
    try:
        conn = sqlite3.connect(path, timeout=5, isolation_level=None)
        conn.execute('PRAGMA journal_mode = WAL')
        _create(conn)
        if not _next_check:
            # once per interpreter, or each new thread waits out a busy store again
            _next_check = _due(conn)
    except sqlite3.Error as exc:
        if conn is not None:
            repaired = retry and _repair(conn, exc, inode)
            conn.close()
            if repaired:
                return _open(retry=False)
        raise StoreError(f'cannot open the store: {exc}') from exc
    except BaseException:
        if conn is not None:
            conn.close()
        raise
    _local.holder = _Holder(conn, _inode(path))
    return conn


def _inode(path: str) -> Optional[int]:
    """File id of the store, or None when there is no file yet."""
    try:
        return os.stat(path).st_ino
    except OSError:
        return None


def _damaged(exc: BaseException) -> bool:
    """Whether an error says the store file itself is damaged, not busy or misused."""
    # corrupt and not-a-database errors arrive as the base class, busy and locked as subclasses
    return type(exc) is sqlite3.DatabaseError


def _mend(exc: BaseException) -> None:
    """Mend a damaged store after a failed call; drops this thread's connection for a new one."""
    holder = getattr(_local, 'holder', None)
    if holder is not None and _repair(holder.conn, exc, holder.inode):
        del _local.holder


def _repair(conn: sqlite3.Connection, exc: BaseException, inode: Optional[int]) -> bool:
    """Repair a damaged store by rebuilding it empty; True when the caller should reconnect."""
    if not _damaged(exc):
        return False
    try:
        if conn.execute('PRAGMA quick_check(1)').fetchone()[0] == 'ok':
            return True
        _overwrite(conn)
    except sqlite3.Error as error:
        if not _damaged(error):
            return False
        # not readable as a database at all; only replacing the file helps
        conn.close()
        if not _discard(inode):
            return True
    _logged.clear()
    _log('the store was damaged, rebuilt it empty', xbmc.LOGWARNING)
    return True


def _overwrite(conn: sqlite3.Connection) -> None:
    """Overwrite the store in place with empty tables, under SQLite's locks for every add-on."""
    fresh = sqlite3.connect(':memory:', isolation_level=None)
    try:
        fresh.execute('BEGIN IMMEDIATE')
        _build(fresh)
        deadline = time.time() + 5

        def give_up(status: int, remaining: int, total: int) -> None:
            if time.time() > deadline:
                raise sqlite3.OperationalError('store busy')

        fresh.backup(conn, progress=give_up)
    finally:
        fresh.close()


def _discard(inode: Optional[int]) -> bool:
    """Discard an unreadable store file unless another add-on replaced it; True when gone."""
    path = xbmcvfs.translatePath(_STORE)
    if inode is None:
        return False
    if _inode(path) == inode:
        try:
            for name in (path, path + '-wal', path + '-shm'):
                if os.path.exists(name):
                    os.remove(name)
        except OSError as exc:
            _log_error(f'cannot replace the unreadable store: {exc}')
            return False
    return True


def _create(conn: sqlite3.Connection) -> None:
    """Create the tables empty when the store is new or older; raises StoreError on a newer one."""
    if _schema(conn) < _SCHEMA:
        try:
            conn.execute('BEGIN IMMEDIATE')
        except sqlite3.OperationalError:
            # lock held by another add-on's first load, which may have made the tables
            if _schema(conn) < _SCHEMA:
                raise
        else:
            _build(conn)
    if _schema(conn) > _SCHEMA:
        raise StoreError('the store was made by a newer version of the module')


def _build(conn: sqlite3.Connection) -> None:
    """Build empty tables unless another add-on just did, then commit the open transaction."""
    try:
        # another add-on may have created them while this one waited for the lock
        if _schema(conn) < _SCHEMA:
            conn.execute('DROP TABLE IF EXISTS ratings')
            conn.execute('DROP TABLE IF EXISTS meta')
            conn.execute('CREATE TABLE ratings '
                         '(id INTEGER PRIMARY KEY, rating INTEGER, votes INTEGER)')
            conn.execute('CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)')
            conn.execute(f'PRAGMA user_version = {_SCHEMA}')
        conn.execute('COMMIT')
    except BaseException:
        if conn.in_transaction:
            conn.execute('ROLLBACK')
        raise


def _schema(conn: sqlite3.Connection) -> int:
    """Schema version stored in the file."""
    return conn.execute('PRAGMA user_version').fetchone()[0]


def _due(conn: sqlite3.Connection) -> float:
    """Time the next check falls due, past the check gap and any retry wait after a failed load."""
    return max(float(_meta(conn, 'checked') or 0) + _CHECK_GAP, float(_meta(conn, 'retry') or 0))


def _update(conn: sqlite3.Connection, abort: Optional[Callable[[], bool]] = None,
            on_download: Optional[Callable[[], None]] = None) -> bool:
    """Update ratings when check is due and lock free, mending damage; True when new data loaded."""
    global _next_check, _stopped_until
    _next_check = time.time() + _CHECK_GAP
    try:
        conn.execute('BEGIN IMMEDIATE')
    except sqlite3.Error as exc:
        _log(f'update skipped: {exc}')
        _mend(exc)
        return False
    loaded = False
    try:
        if _due(conn) <= time.time():
            conn.execute("INSERT OR REPLACE INTO meta VALUES ('checked', ?)", (str(time.time()),))
            loaded = _reload(conn, abort, on_download)
        conn.execute('COMMIT')
        _next_check = _due(conn)
    except _Stopped:
        # rollback drops check stamp too, letting other add-ons check now
        _stopped_until = time.time() + _CHECK_GAP
        _log('load stopped, old ratings kept', xbmc.LOGINFO)
        conn.execute('ROLLBACK')
    except Exception as exc:
        _log(f'update failed: {exc}', xbmc.LOGERROR)
        loaded = False
        if conn.in_transaction:
            conn.execute('ROLLBACK')
        if _damaged(exc):
            _mend(exc)
            return False
    except BaseException:
        # Kodi's kill raises SystemExit anywhere; a caller that swallows it would keep the lock
        if conn.in_transaction:
            conn.execute('ROLLBACK')
        raise
    # else the WAL keeps a second copy of the ratings on disk
    conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    return loaded


def _reload(conn: sqlite3.Connection, abort: Optional[Callable[[], bool]],
            on_download: Optional[Callable[[], None]]) -> bool:
    """Reload newer IMDb ratings; True on load, stop or damage raises, else failure sets retry."""
    modified = _remote_modified()
    if not modified or not _newer(modified, _meta(conn, 'modified')):
        return False

    callback = abort

    def stopped() -> bool:
        nonlocal callback
        if _monitor.abortRequested():
            return True
        try:
            return callback is not None and bool(callback())
        except Exception as exc:
            _log(f'abort callback failed, ignoring it: {exc}', xbmc.LOGERROR)
            callback = None
            return False

    if stopped():
        raise _Stopped()
    _log('downloading the ratings dataset', xbmc.LOGINFO)
    if on_download is not None:
        try:
            on_download()
        except Exception as exc:
            _log(f'download callback failed: {exc}', xbmc.LOGERROR)
    loaded = False
    conn.execute('SAVEPOINT reload')
    try:
        # rebuilt in place, another add-on may have the file open
        conn.execute('DELETE FROM ratings')
        request = Request(_DATASET_URL, headers=_HEADERS)
        with urlopen(request, timeout=30) as response, gzip.GzipFile(fileobj=response) as data:
            lines = io.TextIOWrapper(data, encoding='utf-8', errors='replace')
            rows = _rows(lines, stopped)
            count = conn.executemany('INSERT INTO ratings VALUES (?, ?, ?)', rows).rowcount
        if count <= 0:
            raise ValueError('the dataset held no ratings')
        conn.execute("INSERT OR REPLACE INTO meta VALUES ('modified', ?)", (modified,))
        _log(f'stored {count} ratings', xbmc.LOGINFO)
        loaded = True
    except _Stopped:
        raise
    except Exception as exc:
        if _damaged(exc):
            raise
        _log(f'download failed: {exc}', xbmc.LOGERROR)
        conn.execute('ROLLBACK TO reload')
        gap = _RETRY_GAP
        if _meta(conn, 'modified') is None:
            last = _meta(conn, 'retry_gap')
            gap = min(float(last) * 2, _RETRY_GAP) if last else _CHECK_GAP
            conn.execute("INSERT OR REPLACE INTO meta VALUES ('retry_gap', ?)", (str(gap),))
        conn.execute("INSERT OR REPLACE INTO meta VALUES ('retry', ?)", (str(time.time() + gap),))
    conn.execute('RELEASE reload')
    return loaded


def _rows(lines: Iterable[str], stopped: Callable[[], bool]) -> Iterator[Tuple[int, int, int]]:
    """Title number, rating times ten and votes per line, skipping bad ones; raises on a stop."""
    for number, line in enumerate(lines):
        if number % _STOP_CHECK_LINES == 0 and stopped():
            raise _Stopped()
        fields = line.split('\t')
        title = _title_number(fields[0])
        if title is None:
            continue
        try:
            rating, votes = round(float(fields[1]) * 10), int(fields[2])
        except (ValueError, IndexError, OverflowError):
            continue
        # one out-of-range value aborts the whole executemany
        if max(abs(rating), abs(votes)) < 2 ** 63:
            yield title, rating, votes


def _remote_modified() -> Optional[str]:
    """Last-Modified of IMDb's file, or None when the check fails."""
    request = Request(_DATASET_URL, method='HEAD', headers=_HEADERS)
    try:
        with urlopen(request, timeout=10) as response:
            return response.headers.get('Last-Modified')
    except OSError as exc:
        _log(f'dataset check failed: {exc}', xbmc.LOGERROR)
        return None


def _newer(remote: str, stored: Optional[str]) -> bool:
    """Whether IMDb's date is later than the stored one, or differs when either won't parse."""
    if stored is None:
        return True
    try:
        return parsedate_to_datetime(remote) > parsedate_to_datetime(stored)
    except (TypeError, ValueError):
        return remote != stored


def _meta(conn: sqlite3.Connection, key: str) -> Optional[str]:
    """Value stored under a meta key, or None."""
    row = conn.execute('SELECT value FROM meta WHERE key = ?', (key,)).fetchone()
    return row[0] if row else None


def _log(message: str, level: int = xbmc.LOGDEBUG) -> None:
    """Log under the module's id."""
    xbmc.log(f'[{_ADDON_ID}] {message}', level)


def _log_error(message: str) -> None:
    """Log a store error at error level the first time this interpreter sees it, then at debug."""
    level = xbmc.LOGDEBUG if message in _logged else xbmc.LOGERROR
    _logged.add(message)
    _log(message, level)
