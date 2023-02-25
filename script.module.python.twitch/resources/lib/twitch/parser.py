# -*- encoding: utf-8 -*-
"""

    Copyright (C) 2012-2016 python-twitch (https://github.com/ingwinlu/python-twitch)
    Copyright (C) 2016-2018 script.module.python.twitch

    This file is part of script.module.python.twitch

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
"""

import re
from urllib.parse import urlencode

from . import keys
from .log import log

_m3u_pattern = re.compile(
    r'#EXT-X-MEDIA:TYPE=VIDEO.*'
    r'GROUP-ID="(?P<group_id>[^"]*)",'
    r'NAME="(?P<group_name>[^"]*)"[,=\w]*\n'
    r'#EXT-X-STREAM-INF:.*'
    r'BANDWIDTH=(?P<bandwidth>[0-9]+),'
    r'(?:.*RESOLUTION="*(?P<resolution>[0-9xX]+)"*,)?'
    r'(?:.*FRAME-RATE=(?P<fps>[0-9.]+))?.*\n'
    r'(?P<url>http.*)')

_error_pattern = re.compile(r'.*<tr><td><b>error</b></td><td>(?P<message>.+?)</td></tr>.*', re.IGNORECASE)


def _find_frame_rate(group_id, group_name):
    group_id = group_id.lower()

    if group_id == 'audio_only':
        return None
    elif group_id == 'chunked':
        group_id = group_name.lower().replace('(source)', '').strip()

    info = group_id.split('p')
    if len(info) > 1 and info[1]:
        fps = float(info[1])
    else:
        fps = 30.0

    return fps


def m3u8(f):
    def m3u8_wrapper(*args, **kwargs):
        results = f(*args, **kwargs)
        try:
            results = results.decode('utf-8')
        except AttributeError:
            pass
        if keys.ERROR in results:
            if isinstance(results, dict):
                return results
            else:
                error = re.search(_error_pattern, results)
                if error:
                    return {
                        'error': 'Error',
                        'message': error.group('message'),
                        'status': 404
                    }
        return m3u8_to_list(results)

    return m3u8_wrapper


def clip_embed(f):
    def clip_embed_wrapper(*args, **kwargs):
        return clip_embed_to_list(f(*args, **kwargs))

    return clip_embed_wrapper


def m3u8_to_dict(string):
    log.debug('m3u8_to_dict called for:\n{0}'.format(string))
    d = dict()
    matches = re.finditer(_m3u_pattern, string)
    for m in matches:
        if m.group('group_name') == 'audio_only':
            name = 'Audio Only'
        elif m.group('group_id') == 'chunked':
            name = 'Source'
        else:
            name = m.group('group_name')

        if m.group('fps'):
            fps = float(m.group('fps'))
        else:
            fps = _find_frame_rate(m.group('group_id'), m.group('group_name'))

        d[m.group('group_id')] = {
            'id': m.group('group_id'),
            'name': name,
            'url': m.group('url'),
            'bandwidth': int(m.group('bandwidth')),
            'fps': fps,
            'resolution': m.group('resolution')
        }
    log.debug('m3u8_to_dict result:\n{0}'.format(d))
    return d


def m3u8_to_list(string):
    log.debug('m3u8_to_list called for:\n{0}'.format(string))
    l = list()
    matches = re.finditer(_m3u_pattern, string)
    for m in matches:
        if m.group('group_name') == 'audio_only':
            name = 'Audio Only'
        elif m.group('group_id') == 'chunked':
            name = 'Source'
        else:
            name = m.group('group_name')

        if m.group('fps'):
            fps = float(m.group('fps'))
        else:
            fps = _find_frame_rate(m.group('group_id'), m.group('group_name'))

        l.append({
            'id': m.group('group_id'),
            'name': name,
            'url': m.group('url'),
            'bandwidth': int(m.group('bandwidth')),
            'fps': fps,
            'resolution': m.group('resolution')
        })

    log.debug('m3u8_to_list result:\n{0}'.format(l))
    return l


def clip_embed_to_list(response):
    log.debug('clip_embed_to_list called for:\n{0}'.format(response))

    clip_json = response.get('data', {}).get('clip', {})
    access_token = clip_json.get('playbackAccessToken', {})
    token = access_token.get('value', '')
    signature = access_token.get('signature', '')
    qualities = clip_json.get('videoQualities', [])

    params = urlencode({
        'sig': signature,
        'token': token
    })

    l = list()

    if isinstance(response, dict):
        clip = response.get('data', {}).get('clip', {})
        qualities = clip.get('videoQualities', list())

    if qualities:
        l = [{
            'id': item['quality'],
            'name': item['quality'],
            'url': item['sourceURL'] + '?' + params,
            'bandwidth': -1
        } for item in qualities]
        if l:
            l.insert(0, {
                'id': 'Source',
                'name': 'Source',
                'url': l[0]['url'],
                'bandwidth': -1
            })

    log.debug('clip_embed_to_list result:\n{0}'.format(l))
    return l
