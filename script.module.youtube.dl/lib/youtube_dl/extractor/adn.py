# coding: utf-8
from __future__ import unicode_literals

import json
import os

from .common import InfoExtractor
from ..aes import aes_cbc_decrypt
from ..compat import (
    compat_b64decode,
    compat_ord,
)
from ..utils import (
    bytes_to_intlist,
    ExtractorError,
    float_or_none,
    intlist_to_bytes,
    srt_subtitles_timecode,
    strip_or_none,
    urljoin,
)


class ADNIE(InfoExtractor):
    IE_DESC = 'Anime Digital Network'
    _VALID_URL = r'https?://(?:www\.)?animedigitalnetwork\.fr/video/[^/]+/(?P<id>\d+)'
    _TEST = {
        'url': 'http://animedigitalnetwork.fr/video/blue-exorcist-kyoto-saga/7778-episode-1-debut-des-hostilites',
        'md5': 'e497370d847fd79d9d4c74be55575c7a',
        'info_dict': {
            'id': '7778',
            'ext': 'mp4',
            'title': 'Blue Exorcist - Kyôto Saga - Épisode 1',
            'description': 'md5:2f7b5aa76edbc1a7a92cedcda8a528d5',
        }
    }
    _BASE_URL = 'http://animedigitalnetwork.fr'

    def _get_subtitles(self, sub_path, video_id):
        if not sub_path:
            return None

        enc_subtitles = self._download_webpage(
            urljoin(self._BASE_URL, sub_path),
            video_id, fatal=False, headers={
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:53.0) Gecko/20100101 Firefox/53.0',
            })
        if not enc_subtitles:
            return None

        # http://animedigitalnetwork.fr/components/com_vodvideo/videojs/adn-vjs.min.js
        dec_subtitles = intlist_to_bytes(aes_cbc_decrypt(
            bytes_to_intlist(compat_b64decode(enc_subtitles[24:])),
            bytes_to_intlist(b'\xc8\x6e\x06\xbc\xbe\xc6\x49\xf5\x88\x0d\xc8\x47\xc4\x27\x0c\x60'),
            bytes_to_intlist(compat_b64decode(enc_subtitles[:24]))
        ))
        subtitles_json = self._parse_json(
            dec_subtitles[:-compat_ord(dec_subtitles[-1])].decode(),
            None, fatal=False)
        if not subtitles_json:
            return None

        subtitles = {}
        for sub_lang, sub in subtitles_json.items():
            srt = ''
            for num, current in enumerate(sub):
                start, end, text = (
                    float_or_none(current.get('startTime')),
                    float_or_none(current.get('endTime')),
                    current.get('text'))
                if start is None or end is None or text is None:
                    continue
                srt += os.linesep.join(
                    (
                        '%d' % num,
                        '%s --> %s' % (
                            srt_subtitles_timecode(start),
                            srt_subtitles_timecode(end)),
                        text,
                        os.linesep,
                    ))

            if sub_lang == 'vostf':
                sub_lang = 'fr'
            subtitles.setdefault(sub_lang, []).extend([{
                'ext': 'json',
                'data': json.dumps(sub),
            }, {
                'ext': 'srt',
                'data': srt,
            }])
        return subtitles

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        player_config = self._parse_json(self._search_regex(
            r'playerConfig\s*=\s*({.+});', webpage, 'player config'), video_id)

        video_info = {}
        video_info_str = self._search_regex(
            r'videoInfo\s*=\s*({.+});', webpage,
            'video info', fatal=False)
        if video_info_str:
            video_info = self._parse_json(
                video_info_str, video_id, fatal=False) or {}

        options = player_config.get('options') or {}
        metas = options.get('metas') or {}
        links = player_config.get('links') or {}
        sub_path = player_config.get('subtitles')
        error = None
        if not links:
            links_url = player_config.get('linksurl') or options['videoUrl']
            links_data = self._download_json(urljoin(
                self._BASE_URL, links_url), video_id)
            links = links_data.get('links') or {}
            metas = metas or links_data.get('meta') or {}
            sub_path = sub_path or links_data.get('subtitles')
            error = links_data.get('error')
        title = metas.get('title') or video_info['title']

        formats = []
        for format_id, qualities in links.items():
            if not isinstance(qualities, dict):
                continue
            for load_balancer_url in qualities.values():
                load_balancer_data = self._download_json(
                    load_balancer_url, video_id, fatal=False) or {}
                m3u8_url = load_balancer_data.get('location')
                if not m3u8_url:
                    continue
                m3u8_formats = self._extract_m3u8_formats(
                    m3u8_url, video_id, 'mp4', 'm3u8_native',
                    m3u8_id=format_id, fatal=False)
                if format_id == 'vf':
                    for f in m3u8_formats:
                        f['language'] = 'fr'
                formats.extend(m3u8_formats)
        if not error:
            error = options.get('error')
        if not formats and error:
            raise ExtractorError('%s said: %s' % (self.IE_NAME, error), expected=True)
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'description': strip_or_none(metas.get('summary') or video_info.get('resume')),
            'thumbnail': video_info.get('image'),
            'formats': formats,
            'subtitles': self.extract_subtitles(sub_path, video_id),
            'episode': metas.get('subtitle') or video_info.get('videoTitle'),
            'series': video_info.get('playlistTitle'),
        }
