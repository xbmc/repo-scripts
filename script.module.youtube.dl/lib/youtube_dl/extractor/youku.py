# coding: utf-8
from __future__ import unicode_literals

import itertools
import random
import re
import string
import time

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    get_element_by_class,
    js_to_json,
    str_or_none,
    strip_jsonp,
    urljoin,
)


class YoukuIE(InfoExtractor):
    IE_NAME = 'youku'
    IE_DESC = '优酷'
    _VALID_URL = r'''(?x)
        (?:
            https?://(
                (?:v|player)\.youku\.com/(?:v_show/id_|player\.php/sid/)|
                video\.tudou\.com/v/)|
            youku:)
        (?P<id>[A-Za-z0-9]+)(?:\.html|/v\.swf|)
    '''

    _TESTS = [{
        # MD5 is unstable
        'url': 'http://v.youku.com/v_show/id_XMTc1ODE5Njcy.html',
        'info_dict': {
            'id': 'XMTc1ODE5Njcy',
            'title': '★Smile﹗♡ Git Fresh -Booty Music舞蹈.',
            'ext': 'mp4',
            'duration': 74.73,
            'thumbnail': r're:^https?://.*',
            'uploader': '。躲猫猫、',
            'uploader_id': '36017967',
            'uploader_url': 'http://i.youku.com/u/UMTQ0MDcxODY4',
            'tags': list,
        }
    }, {
        'url': 'http://player.youku.com/player.php/sid/XNDgyMDQ2NTQw/v.swf',
        'only_matching': True,
    }, {
        'url': 'http://v.youku.com/v_show/id_XODgxNjg1Mzk2_ev_1.html',
        'info_dict': {
            'id': 'XODgxNjg1Mzk2',
            'ext': 'mp4',
            'title': '武媚娘传奇 85',
            'duration': 1999.61,
            'thumbnail': r're:^https?://.*',
            'uploader': '疯狂豆花',
            'uploader_id': '62583473',
            'uploader_url': 'http://i.youku.com/u/UMjUwMzMzODky',
            'tags': list,
        },
    }, {
        'url': 'http://v.youku.com/v_show/id_XMTI1OTczNDM5Mg==.html',
        'info_dict': {
            'id': 'XMTI1OTczNDM5Mg',
            'ext': 'mp4',
            'title': '花千骨 04',
            'duration': 2363,
            'thumbnail': r're:^https?://.*',
            'uploader': '放剧场-花千骨',
            'uploader_id': '772849359',
            'uploader_url': 'http://i.youku.com/u/UMzA5MTM5NzQzNg==',
            'tags': list,
        },
    }, {
        'url': 'http://v.youku.com/v_show/id_XNjA1NzA2Njgw.html',
        'note': 'Video protected with password',
        'info_dict': {
            'id': 'XNjA1NzA2Njgw',
            'ext': 'mp4',
            'title': '邢義田复旦讲座之想象中的胡人—从“左衽孔子”说起',
            'duration': 7264.5,
            'thumbnail': r're:^https?://.*',
            'uploader': 'FoxJin1006',
            'uploader_id': '322014285',
            'uploader_url': 'http://i.youku.com/u/UMTI4ODA1NzE0MA==',
            'tags': list,
        },
        'params': {
            'videopassword': '100600',
        },
    }, {
        # /play/get.json contains streams with "channel_type":"tail"
        'url': 'http://v.youku.com/v_show/id_XOTUxMzg4NDMy.html',
        'info_dict': {
            'id': 'XOTUxMzg4NDMy',
            'ext': 'mp4',
            'title': '我的世界☆明月庄主☆车震猎杀☆杀人艺术Minecraft',
            'duration': 702.08,
            'thumbnail': r're:^https?://.*',
            'uploader': '明月庄主moon',
            'uploader_id': '38465621',
            'uploader_url': 'http://i.youku.com/u/UMTUzODYyNDg0',
            'tags': list,
        },
    }, {
        'url': 'http://video.tudou.com/v/XMjIyNzAzMTQ4NA==.html?f=46177805',
        'info_dict': {
            'id': 'XMjIyNzAzMTQ4NA',
            'ext': 'mp4',
            'title': '卡马乔国足开大脚长传冲吊集锦',
            'duration': 289,
            'thumbnail': r're:^https?://.*',
            'uploader': '阿卜杜拉之星',
            'uploader_id': '2382249',
            'uploader_url': 'http://i.youku.com/u/UOTUyODk5Ng==',
            'tags': list,
        },
    }, {
        'url': 'http://video.tudou.com/v/XMjE4ODI3OTg2MA==.html',
        'only_matching': True,
    }]

    @staticmethod
    def get_ysuid():
        return '%d%s' % (int(time.time()), ''.join([
            random.choice(string.ascii_letters) for i in range(3)]))

    def get_format_name(self, fm):
        _dict = {
            '3gp': 'h6',
            '3gphd': 'h5',
            'flv': 'h4',
            'flvhd': 'h4',
            'mp4': 'h3',
            'mp4hd': 'h3',
            'mp4hd2': 'h4',
            'mp4hd3': 'h4',
            'hd2': 'h2',
            'hd3': 'h1',
        }
        return _dict.get(fm)

    def _real_extract(self, url):
        video_id = self._match_id(url)

        self._set_cookie('youku.com', '__ysuid', self.get_ysuid())
        self._set_cookie('youku.com', 'xreferrer', 'http://www.youku.com')

        _, urlh = self._download_webpage_handle(
            'https://log.mmstat.com/eg.js', video_id, 'Retrieving cna info')
        # The etag header is '"foobar"'; let's remove the double quotes
        cna = urlh.headers['etag'][1:-1]

        # request basic data
        basic_data_params = {
            'vid': video_id,
            'ccode': '0402' if 'tudou.com' in url else '0401',
            'client_ip': '192.168.1.1',
            'utid': cna,
            'client_ts': time.time() / 1000,
        }

        video_password = self._downloader.params.get('videopassword')
        if video_password:
            basic_data_params['password'] = video_password

        headers = {
            'Referer': url,
        }
        headers.update(self.geo_verification_headers())
        data = self._download_json(
            'https://ups.youku.com/ups/get.json', video_id,
            'Downloading JSON metadata',
            query=basic_data_params, headers=headers)['data']

        error = data.get('error')
        if error:
            error_note = error.get('note')
            if error_note is not None and '因版权原因无法观看此视频' in error_note:
                raise ExtractorError(
                    'Youku said: Sorry, this video is available in China only', expected=True)
            elif error_note and '该视频被设为私密' in error_note:
                raise ExtractorError(
                    'Youku said: Sorry, this video is private', expected=True)
            else:
                msg = 'Youku server reported error %i' % error.get('code')
                if error_note is not None:
                    msg += ': ' + error_note
                raise ExtractorError(msg)

        # get video title
        video_data = data['video']
        title = video_data['title']

        formats = [{
            'url': stream['m3u8_url'],
            'format_id': self.get_format_name(stream.get('stream_type')),
            'ext': 'mp4',
            'protocol': 'm3u8_native',
            'filesize': int(stream.get('size')),
            'width': stream.get('width'),
            'height': stream.get('height'),
        } for stream in data['stream'] if stream.get('channel_type') != 'tail']
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'duration': video_data.get('seconds'),
            'thumbnail': video_data.get('logo'),
            'uploader': video_data.get('username'),
            'uploader_id': str_or_none(video_data.get('userid')),
            'uploader_url': data.get('uploader', {}).get('homepage'),
            'tags': video_data.get('tags'),
        }


class YoukuShowIE(InfoExtractor):
    _VALID_URL = r'https?://list\.youku\.com/show/id_(?P<id>[0-9a-z]+)\.html'
    IE_NAME = 'youku:show'

    _TEST = {
        'url': 'http://list.youku.com/show/id_zc7c670be07ff11e48b3f.html',
        'info_dict': {
            'id': 'zc7c670be07ff11e48b3f',
            'title': '花千骨 未删减版',
            'description': 'md5:a1ae6f5618571bbeb5c9821f9c81b558',
        },
        'playlist_count': 50,
    }

    _PAGE_SIZE = 40

    def _real_extract(self, url):
        show_id = self._match_id(url)
        webpage = self._download_webpage(url, show_id)

        entries = []
        page_config = self._parse_json(self._search_regex(
            r'var\s+PageConfig\s*=\s*({.+});', webpage, 'page config'),
            show_id, transform_source=js_to_json)
        for idx in itertools.count(0):
            if idx == 0:
                playlist_data_url = 'http://list.youku.com/show/module'
                query = {'id': page_config['showid'], 'tab': 'point'}
            else:
                playlist_data_url = 'http://list.youku.com/show/point'
                query = {
                    'id': page_config['showid'],
                    'stage': 'reload_%d' % (self._PAGE_SIZE * idx + 1),
                }
            query['callback'] = 'cb'
            playlist_data = self._download_json(
                playlist_data_url, show_id, query=query,
                note='Downloading playlist data page %d' % (idx + 1),
                transform_source=lambda s: js_to_json(strip_jsonp(s)))['html']
            video_urls = re.findall(
                r'<div[^>]+class="p-thumb"[^<]+<a[^>]+href="([^"]+)"',
                playlist_data)
            new_entries = [
                self.url_result(urljoin(url, video_url), YoukuIE.ie_key())
                for video_url in video_urls]
            entries.extend(new_entries)
            if len(new_entries) < self._PAGE_SIZE:
                break

        desc = self._html_search_meta('description', webpage, fatal=False)
        playlist_title = desc.split(',')[0] if desc else None
        detail_li = get_element_by_class('p-intro', webpage)
        playlist_description = get_element_by_class(
            'intro-more', detail_li) if detail_li else None

        return self.playlist_result(
            entries, show_id, playlist_title, playlist_description)
