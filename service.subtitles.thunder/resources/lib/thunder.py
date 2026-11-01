# -*- coding: utf-8 -*-
"""Thunder CID lookup, bounded downloads, and subtitle conversion."""
import hashlib
import io
import os
import re
import zipfile
from urllib.parse import unquote, unquote_to_bytes, urlsplit

import requests
from name_search import NameSearchError, SearchCancelled, combined_search

API_URL = 'http://sub.xmp.sandai.net:8000/subxl/{}.json'
TIMEOUT = (5, 15)
MAX_BYTES = 20 * 1024 * 1024
EXTENSIONS = {'.srt', '.ass', '.ssa', '.smi', '.vtt', '.sub', '.txt'}


class SubtitleError(Exception):
    def __init__(self, message, message_id=32012):
        super().__init__(message)
        self.message_id = message_id


def cid_hash(stream):
    """Hash exactly the bytes required by Thunder, using a seekable Kodi VFS file."""
    size = stream.size()
    if size <= 0:
        raise SubtitleError('Empty or unreadable media', 32013)
    digest = hashlib.sha1()
    offsets = [0] if size < 0xF000 else [0, size // 3, size - 0x5000]
    for offset in offsets:
        if stream.seek(offset, 0) != offset:
            raise SubtitleError('Media is not seekable', 32013)
        length = size if size < 0xF000 else 0x5000
        data = bytearray()
        while len(data) < length:
            part = stream.readBytes(length - len(data))
            if not part:
                raise SubtitleError('Incomplete media read', 32013)
            data.extend(part)
        digest.update(data)
    return digest.hexdigest().upper()


def valid_url(url):
    try:
        parts = urlsplit(url)
        return parts.scheme in ('http', 'https') and bool(parts.hostname) and not parts.username and not parts.password
    except (ValueError, TypeError):
        return False


def subtitle_name(value, fallback='Thunder subtitle'):
    """Recover intact encodings; omit irreversibly damaged name fragments."""
    if not isinstance(value, str) or not value.strip():
        return fallback
    try:
        raw = value.encode('utf-8', errors='surrogateescape')
    except UnicodeEncodeError:
        raw = value.encode('utf-8', errors='replace')
    # Some records store an entire upload path as a percent-encoded name.
    if re.search(rb'%[0-9a-fA-F]{2}', raw):
        raw = unquote_to_bytes(raw)
    for encoding in ('utf-8', 'gb18030'):
        try:
            name = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        name = raw.decode('utf-8', errors='replace')
    try:
        repaired = name.encode('latin-1').decode('utf-8')
        name = repaired
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    name = name.replace('\\', '/').rsplit('/', 1)[-1]
    # A replacement character cannot be decoded back to the missing character.
    # Drop its bracketed annotation instead of displaying a wall of diamonds.
    for pattern in (r'\[[^\[\]]*\]', r'\([^()]*\)', r'【[^【】]*】', r'（[^（）]*）'):
        name = re.sub(pattern, lambda m: '' if '\ufffd' in m.group() else m.group(), name)
    name = re.sub(r'[?\ufffd]*\ufffd[?\ufffd]*', '', name)
    name = ''.join(c for c in name if c.isprintable())
    name = re.sub(r'\s+', ' ', name).strip(' -_')
    if name.lower() in EXTENSIONS:
        return fallback
    name = re.sub(r'\.{2,}', '.', name).strip(' .-_')
    stem, extension = os.path.splitext(name)
    if not any(c.isalnum() for c in (stem or name)):
        return fallback
    return name or fallback


def search_subtitles(cid, max_attempts=3, monitor=None):
    if not re.fullmatch(r'[A-Fa-f0-9]{40}', cid):
        raise SubtitleError('Invalid CID')
    for attempt in range(max(1, min(max_attempts, 3))):
        if monitor and monitor.abortRequested():
            return []
        try:
            with requests.get(API_URL.format(cid), timeout=TIMEOUT, stream=True) as response:
                response.raise_for_status()
                import json
                # Preserve malformed bytes until each name's encoding can be
                # checked; replacing bytes here would lose recoverable GBK.
                result = json.loads(read_response(response, 2 * 1024 * 1024).decode('utf-8', errors='surrogateescape'))
            if not isinstance(result, dict) or not isinstance(result.get('sublist'), list):
                raise ValueError('Invalid subtitle response')
            entries, seen = [], set()
            for sub in result['sublist']:
                if not isinstance(sub, dict):
                    continue
                url = sub.get('surl')
                if not isinstance(url, str) or not valid_url(url) or url in seen:
                    continue
                seen.add(url)
                name = subtitle_name(sub.get('sname'), 'Thunder subtitle {:02d}'.format(len(entries) + 1))
                entries.append({'surl': url, 'sname': name})
            return entries
        except (requests.RequestException, ValueError, SubtitleError):
            if attempt == max(1, min(max_attempts, 3)) - 1:
                raise SubtitleError('Thunder service unavailable', 32014)
            if monitor and monitor.waitForAbort(0.5 * (attempt + 1)):
                return []
    return []


def search_all_subtitles(cid=None, names=(), monitor=None):
    def legacy():
        return [{'url': item['surl'], 'name': item['sname']} for item in search_subtitles(cid, monitor=monitor)]
    try:
        records, failures = combined_search(legacy if cid else None, names, subtitle_name,
                                             monitor.abortRequested if monitor else None)
        if not records and failures:
            raise SubtitleError('Thunder lookup partially failed', 32014)
        return [dict(item, surl=item['url'], sname=item['name']) for item in records]
    except SearchCancelled:
        return []
    except NameSearchError:
        raise SubtitleError('Thunder service unavailable', 32014) from None


def read_response(response, limit=MAX_BYTES):
    data = bytearray()
    for chunk in response.iter_content(65536):
        data.extend(chunk)
        if len(data) > limit:
            raise SubtitleError('Response exceeds size limit', 32015)
    return bytes(data)


def download_subtitles(url, directory, name=''):
    if not valid_url(url):
        raise SubtitleError('Invalid subtitle URL', 32015)
    try:
        with requests.get(url, timeout=TIMEOUT, stream=True) as response:
            response.raise_for_status()
            data = read_response(response)
    except requests.RequestException:
        raise SubtitleError('Subtitle download failed', 32015)
    if not data:
        raise SubtitleError('Empty subtitle download', 32015)
    files = []
    if zipfile.is_zipfile(io.BytesIO(data)):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                members = [m for m in archive.infolist() if not m.is_dir() and os.path.splitext(m.filename)[1].lower() in EXTENSIONS]
                if len(members) > 100 or sum(m.file_size for m in members) > MAX_BYTES:
                    raise SubtitleError('Archive exceeds size limit', 32015)
                for index, member in enumerate(members):
                    # Never extract server-controlled paths to the filesystem.
                    base = member.filename.replace('\\', '/').rsplit('/', 1)[-1]
                    base = re.sub(r'[^\w. -]', '_', base)[:120]
                    path = os.path.join(directory, '{}_{}'.format(index, base))
                    with open(path, 'wb') as target:
                        target.write(archive.read(member))
                    files.append(path)
        except (zipfile.BadZipFile, RuntimeError, NotImplementedError, OSError):
            raise SubtitleError('Cannot read subtitle archive', 32015)
    else:
        if data.startswith((b'Rar!', b'7z\xbc\xaf\x27\x1c', b'PK\x03\x04')) or data.lstrip().lower().startswith((b'<!doctype html', b'<html')):
            raise SubtitleError('Unsupported archive or HTML response', 32015)
        extension = os.path.splitext(unquote(urlsplit(url).path))[1].lower()
        if extension not in EXTENSIONS:
            extension = os.path.splitext(name)[1].lower()
        if extension not in EXTENSIONS:
            extension = '.srt'
        path = os.path.join(directory, 'subtitle' + extension)
        with open(path, 'wb') as target:
            target.write(data)
        files.append(path)
    if not files:
        raise SubtitleError('Archive contains no subtitles', 32015)
    return files


def convert_encoding(path, conversion='0'):
    import chardet
    with open(path, 'rb') as source:
        data = source.read()
    # .sub may be a binary VobSub file. Preserve it as downloaded.
    if data.startswith(b'\x00\x00\x01\xba'):
        return
    encodings = ['utf-8-sig']
    if data.startswith((b'\xff\xfe', b'\xfe\xff')):
        encodings.insert(0, 'utf-16')
    detected = chardet.detect(data).get('encoding')
    if detected:
        encodings.append('gb18030' if detected.lower() in ('gb2312', 'gbk') else detected)
    for encoding in encodings:
        try:
            text = data.decode(encoding)
            break
        except (UnicodeError, LookupError):
            continue
    else:
        raise SubtitleError('Cannot decode subtitle', 32016)
    if conversion in ('1', '2'):
        from langconv import Converter
        text = Converter('zh-hans' if conversion == '1' else 'zh-hant').convert(text)
    with open(path, 'wb') as target:
        target.write(text.encode('utf-8'))
