"""Thunder HTTPS name lookup and bounded merging with the legacy CID API."""
from concurrent.futures import ThreadPoolExecutor
import json
import time
from urllib.parse import urlsplit

import requests

NAME_API = 'https://api-shoulei-ssl.xunlei.com/oracle/subtitle'
HOSTS = {'subtitle.v.geilijiasu.com', 'subtitle.xmp.sandai.net'}


class NameSearchError(Exception):
    pass


class SearchCancelled(NameSearchError):
    pass


def check_cancel(cancelled):
    if cancelled and cancelled():
        raise SearchCancelled('Search stopped')


def canonical_url(value, require_host=False):
    if not isinstance(value, str):
        return None
    try:
        parts = urlsplit(value)
        if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
            return None
        if require_host and (parts.hostname not in HOSTS or parts.port not in (None, 80, 443)):
            return None
        if parts.hostname in HOSTS and parts.port in (None, 80, 443):
            return parts._replace(scheme='https', netloc=parts.hostname).geturl()
        return value
    except ValueError:
        return None


def numeric(value):
    try:
        result = float(value)
        return result if 0 <= result < 1e12 else 0
    except (TypeError, ValueError):
        return 0


def merge_records(groups):
    merged = {}
    for origin, records in groups:
        for record in records:
            url = canonical_url(record.get('url'))
            if not url:
                continue
            current = dict(record, url=url, origin=origin)
            if url not in merged:
                merged[url] = current
                continue
            previous = merged[url]
            if previous['origin'] != origin and ('CID' in previous['origin'] or origin == 'CID'):
                previous['origin'] = 'CID＋名称'
            for field in ('duration_ms', 'query_name', 'language', 'name'):
                if not previous.get(field) and current.get(field):
                    previous[field] = current[field]
    return list(merged.values())


def search_name(name, cleaner, cancelled=None):
    name = cleaner(name).strip()
    if not name or len(name) > 512:
        raise NameSearchError('Invalid search name')
    for attempt in range(2):
        check_cancel(cancelled)
        try:
            with requests.get(NAME_API, params={'name': name}, timeout=(5, 10), stream=True,
                              allow_redirects=False) as response:
                response.raise_for_status()
                data, deadline = bytearray(), time.monotonic() + 30
                for chunk in response.iter_content(65536):
                    check_cancel(cancelled)
                    data.extend(chunk)
                    if len(data) > 2 * 1024 * 1024 or time.monotonic() > deadline:
                        raise NameSearchError('Name response limit exceeded')
                payload = json.loads(data.decode('utf-8-sig'))
            if not isinstance(payload, dict) or payload.get('code') != 0 or not isinstance(payload.get('data'), list):
                raise NameSearchError('Invalid name response')
            records = []
            for item in payload['data']:
                if not isinstance(item, dict):
                    continue
                url = canonical_url(item.get('url'), require_host=True)
                if not url:
                    continue
                languages = item.get('languages', [])
                language = '、'.join(cleaner(v) for v in languages if isinstance(v, str)) if isinstance(languages, list) else ''
                records.append({'name': cleaner(item.get('name') or 'Thunder subtitle'), 'url': url,
                                'language': language, 'rate': item.get('score'), 'votes': None,
                                'duration_ms': numeric(item.get('duration')), 'query_name': name})
            return merge_records([('名称', records)])
        except SearchCancelled:
            raise
        except (requests.RequestException, NameSearchError, ValueError, UnicodeError):
            if attempt == 1:
                raise NameSearchError('Thunder name lookup failed') from None
    return []


def combined_search(cid_search, names, cleaner, cancelled=None):
    """Query up to three distinct basenames. Never transmit a local directory."""
    unique = []
    for name in names:
        if not isinstance(name, str) or not name.strip():
            continue
        name = cleaner(name)
        if name and name.casefold() not in {n.casefold() for n in unique}:
            unique.append(name)
        if len(unique) == 3:
            break
    check_cancel(cancelled)
    if not cid_search and not unique:
        raise NameSearchError('No video identity available')
    groups, failures, successes = [], [], 0
    with ThreadPoolExecutor(max_workers=3) as executor:
        tasks = []
        if cid_search:
            tasks.append(('CID', executor.submit(cid_search)))
        tasks += [('名称', executor.submit(search_name, name, cleaner, cancelled)) for name in unique]
        for origin, future in tasks:
            try:
                records = future.result()
                check_cancel(cancelled)
                groups.append((origin, records))
                successes += 1
            except SearchCancelled:
                raise
            except Exception:
                # Do not expose filenames, credentials, or signed URLs from
                # a transport exception in user-visible messages.
                failures.append(origin)
    if not successes:
        raise NameSearchError('All Thunder lookups failed')
    return merge_records(groups), tuple(failures)
