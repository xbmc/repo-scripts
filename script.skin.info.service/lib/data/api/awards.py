"""Newer awards file from the add-on's GitHub repository, checked once a week."""
from __future__ import annotations

import json
import os
import time
from typing import Final

import xbmc

from lib.data.api.client import ApiSession, RateLimitHit, RetryableError
from lib.data.awards import DOWNLOADED_PATH, SHIPPED_PATH, data_date, file_date
from lib.kodi.client import log

URL: Final = ("https://raw.githubusercontent.com/MikeSiLVO/script.skin.info.service/"
              "main/resources/awards.tsv")
CHECK_INTERVAL: Final = 7 * 86400
_STATE_PATH: Final = DOWNLOADED_PATH + '.json'
_HEADER: Final = 'imdb\ttmdb\ttvdb\t'


def _read_state() -> dict:
    """Read the last check time and ETag; empty before the first check."""
    try:
        with open(_STATE_PATH, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _write_state(state: dict) -> None:
    """Write the last check time and ETag."""
    try:
        with open(_STATE_PATH, 'w', encoding='utf-8') as f:
            json.dump(state, f)
    except OSError as e:
        log("General", f"Awards check state not saved: {e}", xbmc.LOGWARNING)


def refresh_awards_file(abort_flag=None) -> bool:
    """Refresh the repository's awards file weekly when its data is newer; True when saved."""
    state = _read_state()
    if time.time() - state.get('checked', 0) < CHECK_INTERVAL:
        return False
    headers = {'If-None-Match': state['etag']} if state.get('etag') else None
    session = ApiSession(service_name="GitHub", timeout=(5.0, 30.0), max_retries=1)
    try:
        response = session.get_raw(URL, headers=headers, abort_flag=abort_flag)
    except (RetryableError, RateLimitHit) as e:
        log("General", f"Awards check failed: {e}", xbmc.LOGDEBUG)
        return False
    finally:
        session.close()

    state['checked'] = time.time()
    if response is None or response.status_code == 304:
        _write_state(state)
        return False
    try:
        text = response.text
        etag = response.headers.get('ETag', '')
    finally:
        response.close()

    lines = text.split('\n', 2)
    date = data_date(lines[0])
    current = max(file_date(DOWNLOADED_PATH), file_date(SHIPPED_PATH))
    if len(lines) < 3 or not lines[1].startswith(_HEADER) or not date or date <= current:
        state['etag'] = etag
        _write_state(state)
        return False
    partial = DOWNLOADED_PATH + '.part'
    try:
        with open(partial, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
        os.replace(partial, DOWNLOADED_PATH)
    except OSError as e:
        log("General", f"Awards file not saved: {e}", xbmc.LOGWARNING)
        return False
    state['etag'] = etag
    _write_state(state)
    log("General", f"Awards file updated to {date}", xbmc.LOGINFO)
    return True
