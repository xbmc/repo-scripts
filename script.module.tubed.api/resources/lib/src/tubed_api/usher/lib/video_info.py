# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2020 plugin.video.youtube
    Copyright (C) 2020 Tubed API (script.module.tubed.api)

    This file is part of script.module.tubed.api

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

import json
import os
import random
import traceback
from base64 import b64decode
from copy import deepcopy
from urllib.parse import quote

import requests
import xbmcaddon  # pylint: disable=import-error
import xbmcvfs  # pylint: disable=import-error

from ...constants.http import MOBILE_HEADERS
from ...exceptions import ContentNoResponse
from ...exceptions import ContentRestricted
from ...utils.logger import Log
from .mpeg_dash import ManifestGenerator
from .quality import Quality
from .subtitles import Subtitles

LOG = Log('usher', __file__)


class VideoInfo:

    def __init__(self, language='en-US', region='US'):
        from ... import ACCESS_TOKEN_TV  # pylint: disable=import-outside-toplevel
        from ... import API_KEY_TV  # pylint: disable=import-outside-toplevel

        self._access_token_tv = ACCESS_TOKEN_TV
        self._api_key_tv = b64decode(API_KEY_TV).decode('utf-8')
        self._language = language
        self._region = region
        self._itags = {}

        self.addon = xbmcaddon.Addon('script.module.tubed.api')

    @property
    def language(self):
        return self._language

    @property
    def region(self):
        return self._region

    @property
    def headers(self):
        return deepcopy(MOBILE_HEADERS.copy())

    @property
    def itags(self):
        if not self._itags:
            self._load_itags()
        return self._itags

    def _load_itags(self):
        filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'itags.json')
        with xbmcvfs.File(filename, 'r') as itag_file:
            self._itags = json.load(itag_file)

    @staticmethod
    def generate_cpn():
        # https://github.com/rg3/youtube-dl/blob/master/youtube_dl/extractor/youtube.py#L1381
        # LICENSE: The Unlicense
        # cpn generation algorithm is reverse engineered from base.js.
        # In fact it works even with dummy cpn.
        cpn_alphabet = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_'
        cpn = ''.join((cpn_alphabet[random.randint(0, 256) & 63] for _ in range(0, 16)))
        return cpn

    @staticmethod
    def make_curl_headers(headers, cookies=None):
        output = ''
        if cookies:
            output += 'Cookie={all_cookies}'.format(
                all_cookies=quote(
                    '; '.join('{0}={1}'.format(c.name, c.value) for c in cookies)
                )
            )
            output += '&'
        # Headers to be used in function 'to_play_item' of 'xbmc_items.py'.
        output += '&'.join('{0}={1}'.format(key, quote(headers[key]))
                           for key in headers)
        return output

    @staticmethod
    def image_map():
        return [
            {
                'from': 'iurlhq',
                'to': 'high',
                'image': 'hqdefault.jpg'
            },
            {
                'from': 'iurlmq',
                'to': 'medium',
                'image': 'mqdefault.jpg'
            },
            {
                'from': 'iurlsd',
                'to': 'standard',
                'image': 'sddefault.jpg'
            },
            {
                'from': 'thumbnail_url',
                'to': 'default',
                'image': 'default.jpg'
            }
        ]

    @staticmethod
    def playability(status):
        if ((status.get('fallback', True) and status.get('status', 'ok').lower() == 'ok') or
                status.get('desktopLegacyAgeGateReason', 1) == 1):
            return {
                'playable': True,
                'reason': ''
            }

        if status.get('status') == 'LIVE_STREAM_OFFLINE':
            reason = status.get('reason')
            if not reason:
                streamability = status.get('liveStreamability', {})
                renderer = streamability.get('liveStreamabilityRenderer', {})
                slate = renderer.get('offlineSlate', {})
                offline_slate_renderer = slate.get('liveStreamOfflineSlateRenderer', {})
                main_text = offline_slate_renderer.get('mainText', {})
                text_runs = main_text.get('runs', [{}])

                reason_text = []
                for text in text_runs:
                    reason_text.append(text.get('text', ''))

                if reason_text:
                    reason = ''.join(reason_text)
        else:
            reason = status.get('reason')

            if 'errorScreen' in status and 'playerErrorMessageRenderer' in status['errorScreen']:
                renderer = status['errorScreen']['playerErrorMessageRenderer']

                descript_reason = renderer.get('subreason', {}).get('simpleText')
                general_reason = renderer.get('reason', {}).get('simpleText')

                if descript_reason:
                    reason = descript_reason
                elif general_reason:
                    reason = general_reason

        if not reason:
            reason = 'UNKNOWN'

        try:
            reason = reason.encode('raw_unicode_escape').decode('utf-8')
        except:  # pylint: disable=bare-except
            pass

        LOG.error('Video is unplayable: %s' % reason)
        return {
            'playable': False,
            'reason': reason
        }

    def get_video(self, video_id, quality=None):  # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        LOG.debug('Retrieving video information for %s' % video_id)

        headers = self.headers.copy()

        params = None
        if self._access_token_tv:
            headers['Authorization'] = 'Bearer %s' % self._access_token_tv
        else:
            params = {
                'key': self._api_key_tv
            }
        video_info_url = 'https://youtubei.googleapis.com/youtubei/v1/player'
        # payload = {'videoId': video_id,
        #            'context': {'client': {'clientVersion': '1.20210909.07.00', 'gl': self.region,
        #                                   'clientName': 'WEB_CREATOR', 'hl': self.language}}}

        # payload = {'videoId': video_id,
        #            'context': {'client': {'clientVersion': '16.05', 'gl': self.region,
        #                                   'clientName': 'ANDROID', 'clientScreen': 'EMBED',
        #                                   'hl': self.language}}}

        payload = {
            'videoId': video_id,
            'context': {
                'client': {
                    'clientVersion': '16.05',
                    'gl': self.region,
                    'clientName': 'ANDROID',
                    'hl': self.language
                }
            }
        }

        player_response = {}
        for attempt in range(2):
            try:
                response_payload = requests.post(video_info_url, params=params,
                                                 json=payload, headers=headers,
                                                 cookies=None, allow_redirects=True,
                                                 timeout=60)
                response_payload.raise_for_status()
                player_response = response_payload.json()
                if player_response.get('playabilityStatus', {}).get('status', 'OK') == \
                        'AGE_CHECK_REQUIRED' and attempt == 0:
                    payload['context']['client']['clientScreen'] = 'EMBED'
                    continue
            except:
                error_message = 'Failed to get player response for video_id "%s"' % video_id
                LOG.error(error_message + '\n' + traceback.format_exc())

                raise ContentNoResponse(error_message)  # pylint: disable=raise-missing-from

        # Make a set of URL-quoted headers to be sent to Kodi when requesting
        # the stream during playback. The YT player doesn't seem to use any
        # cookies when doing that, so for now cookies are ignored.
        # curl_headers = self.make_curl_headers(headers, cookies)
        curl_headers = self.make_curl_headers(headers, cookies=None)

        playability_status = player_response.get('playabilityStatus', {})

        playback_tracking = player_response.get('playbackTracking', {})
        captions = player_response.get('captions', {})
        video_details = player_response.get('videoDetails', {})
        is_live_content = video_details.get('isLiveContent') is True
        streaming_data = player_response.get('streamingData', {})

        live_url = streaming_data.get('hlsManifestUrl', '')
        is_live = is_live_content and live_url

        metadata = {
            'video': {},
            'channel': {},
            'images': {},
            'subtitles': []
        }

        metadata['video']['id'] = video_details.get('videoId', video_id)
        metadata['video']['title'] = video_details.get('title', '')
        metadata['channel']['author'] = video_details.get('author', '')
        metadata['channel']['id'] = video_details.get('channelId', '')

        for image_meta in self.image_map():
            image_url = 'https://i.ytimg.com/vi/{video_id}/{image}' \
                .format(video_id=video_id, image=image_meta['image'])

            if is_live:
                image_url = image_url.replace('.jpg', '_live.jpg')

            metadata['images'][image_meta['to']] = image_url

        microformat = player_response.get('microformat', {}).get('playerMicroformatRenderer', {})
        metadata['video']['status'] = {
            'unlisted': microformat.get('isUnlisted', False),
            'private': video_details.get('isPrivate', False),
            'crawlable': video_details.get('isCrawlable', False),
            'family_safe': microformat.get('isFamilySafe', False),
            'live': is_live,
        }

        status = self.playability(playability_status)
        if not status['playable']:
            raise ContentRestricted({
                'error': 'content_restricted',
                'error_description': status['reason'],
                'code': '403'
            })

        metadata['subtitles'] = Subtitles(video_id, captions).retrieve()

        report = {
            'playback_url': '',
            'watchtime_url': ''
        }

        playback_url = playback_tracking.get('videostatsPlaybackUrl', {}).get('baseUrl', '')
        watchtime_url = playback_tracking.get('videostatsWatchtimeUrl', {}).get('baseUrl', '')

        if playback_url and playback_url.startswith('http'):
            report['playback_url'] = ''.join([
                playback_url,
                '&ver=2&fs=0&volume=100&muted=0',
                '&cpn={cpn}'.format(cpn=self.generate_cpn())
            ])

        if watchtime_url and watchtime_url.startswith('http'):
            report['watchtime_url'] = ''.join([
                watchtime_url,
                '&ver=2&fs=0&volume=100&muted=0',
                '&cpn={cpn}'.format(cpn=self.generate_cpn()),
                '&st={st}&et={et}&state={state}'
            ])

        stream_info = {}

        adaptive_formats = streaming_data.get('adaptiveFormats', [])
        # standard_formats = streaming_data.get('formats', [])

        mpd_url = streaming_data.get('dashManifestUrl', '')

        license_data = {
            'url': None,
            'proxy': None,
            'token': None
        }

        license_infos = streaming_data.get('licenseInfos', [])
        for license_info in license_infos:
            if license_info.get('drmFamily') == 'WIDEVINE':
                license_data['url'] = license_info.get('url', '')
                if license_data['url']:
                    license_data['proxy'] = 'http://127.0.0.1:%s/widevine||R{SSM}|' % self.addon \
                        .getSettingInt('httpd.port') or 52520
                    license_data['token'] = self._access_token_tv
                    break

        if not is_live:
            if not quality:
                quality = Quality('mp4')

            mpd_url, stream_info = \
                ManifestGenerator(self.itags, license_data).generate(
                    video_id,
                    adaptive_formats,
                    video_details.get('lengthSeconds', '0'),
                    quality
                )

        video_stream = {
            'url': mpd_url,
            'metadata': metadata,
            'headers': curl_headers,
            'license': license_data,
            'report': report
        }

        if is_live:
            video_stream['url'] = '&'.join([video_stream['url'], 'start_seq=$START_NUMBER$'])
            video_stream.update(self.itags.get('9998'))
            return video_stream

        if not stream_info:
            video_stream.update(self.itags.get('9999'))
            return video_stream

        has_video = (stream_info['video']['codec'] != '' and
                     int(stream_info['video']['bandwidth']) > 0)
        if has_video:
            video_stream.update(self.itags.get('9999'))
            video_stream['video']['height'] = stream_info['video']['height']
            video_stream['video']['encoding'] = stream_info['video']['codec']
        else:
            video_stream.update(self.itags.get('9997'))

        video_stream['audio']['encoding'] = stream_info['audio']['codec']
        if int(stream_info['audio'].get('bitrate', 0)) > 0:
            video_stream['audio']['bitrate'] = int(stream_info['audio'].get('bitrate', 0))

        if stream_info['video']['quality_label']:
            video_stream['title'] = stream_info['video']['quality_label']
            return video_stream

        if has_video:
            video_stream['title'] = '%sp%s' % \
                                    (stream_info['video']['height'],
                                     stream_info['video']['fps'])
            return video_stream

        video_stream['title'] = '%s@%s' % \
                                (stream_info['audio']['codec'],
                                 str(stream_info['audio'].get('bitrate', 0)))

        LOG.debug('Retrieved video information for %s: %s' % (video_id, video_stream))
        return video_stream
